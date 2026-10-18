#!/usr/bin/env python3
"""bsptrace.py - read-only BSP collision tracer for MOHAA maps (planes/brushes/nodes), used to PLACE props on walls.

Loads maps/<map>.bsp (loose in a mod tree first, then the retail pk3s, later paks win) and answers:
    B = BSP.load("m4l3")
    B.trace(p0, p1)            -> (frac, normal, shaderidx, brushidx) of the first SOLID hit, or None   (world brushes only)
    B.trace_box(p0, p1, mins, maxs)  same with an AABB swept (player-hull style)
    B.entities()               -> list of {key: value} dicts from the entity lump
    B.model_bounds(n)          -> (mins, maxs) of submodel n ("model *n" doors, movers, ...)
Contents: only brushes whose shader contentFlags include CONTENTS_SOLID (1) block a trace; sides whose shader is
nodraw/sky/clip (surfaceFlags) are reported with visible=False so a placer can refuse to mount on an invisible face.
Terrain patches (LUMP_TERRAIN) are NOT traced - outdoor floors on terrain come back as a miss.
Reads packs READ-ONLY; writes nothing. Layout: openmohaa-hzm/code/qcommon/qfiles.h (see aircraft_bsp.py for the same lumps).
"""
import glob
import math
import os
import struct
import zipfile

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD_MAPS = os.path.join(ROOT, "hzm-mohaa-coop-mod", "maps")
CONTENTS_SOLID = 1
SURF_SKY = 0x4
SURF_NODRAW = 0x80
EPS = 0.125


def _paks():
    out = []
    for s in ("main", "mainta", "maintt"):
        out += sorted(glob.glob(os.path.join(GOG, s, "*.pk3")), key=lambda p: os.path.basename(p).lower())
    return out


def find_bsp(m):
    loose = os.path.join(MOD_MAPS, m + ".bsp")
    if os.path.exists(loose):
        return open(loose, "rb").read()
    hit = None
    for p in _paks():
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower() == "maps/%s.bsp" % m.lower():
                hit = (p, n)
        z.close()
    if not hit:
        raise FileNotFoundError(m)
    with zipfile.ZipFile(hit[0]) as z:
        return z.read(hit[1])


class BSP:
    @classmethod
    def load(cls, m):
        return cls(find_bsp(m))

    def __init__(s, b):
        s.b = b
        s.ver = struct.unpack_from("<i", b, 4)[0]

        def L(i):
            if s.ver <= 18 and i > 12:
                i += 1
            off, ln = struct.unpack_from("<ii", b, 12 + i * 8)
            return b[off:off + ln]
        sh = L(0)
        s.shaders = []
        for i in range(len(sh) // 140):
            name = sh[i * 140:i * 140 + 64].split(b"\0")[0].decode("latin-1")
            sf, cf = struct.unpack_from("<ii", sh, i * 140 + 64)
            s.shaders.append((name, sf, cf))
        pl = L(1)
        s.planes = [struct.unpack_from("<4f", pl, i * 16) for i in range(len(pl) // 16)]
        nd = L(9)
        s.nodes = [struct.unpack_from("<3i", nd, i * 36) for i in range(len(nd) // 36)]
        lf = L(8)
        lsz = 64 if len(lf) % 64 == 0 and s.ver > 17 else 48
        if len(lf) % lsz:
            lsz = 48 if lsz == 64 else 64
        s.leafs = []
        for i in range(len(lf) // lsz):
            fb, nb = struct.unpack_from("<2i", lf, i * lsz + 40)
            s.leafs.append((fb, nb))
        lb = L(6)
        s.leafbrushes = struct.unpack_from("<%di" % (len(lb) // 4), lb, 0)
        br = L(12)
        s.brushes = [struct.unpack_from("<3i", br, i * 12) for i in range(len(br) // 12)]
        bs = L(11)
        s.sides = [struct.unpack_from("<3i", bs, i * 12) for i in range(len(bs) // 12)]
        md = L(13)
        s.models = [struct.unpack_from("<6f4i", md, i * 40) for i in range(len(md) // 40)]
        s._ents = L(14).decode("latin-1", "replace")
        # terrain patches (outdoor ground): 512 u squares, 9x9 heights, z = h*2 + base, spacing 64 (navigation_bsp_load_terrain.cpp)
        s.terrain = {}
        tr = L(22)
        for psz in (388, 372, 369):
            if len(tr) and len(tr) % psz == 0:
                for i in range(len(tr) // psz):
                    o = i * psz
                    x, y = struct.unpack_from("<2b", tr, o + 20)
                    base = struct.unpack_from("<h", tr, o + 22)[0]
                    s.terrain[(x << 6, y << 6)] = (base, tr[o + psz - 81:o + psz])
                break
        s._solid = {}

    def surfaces(s):
        """visible draw surfaces as (shader name lower, mins, maxs): planar / patch / triangle soup (windows, doors, signs live here,
        not in the collision brushes)."""
        if getattr(s, "_surfs", None) is not None:
            return s._surfs
        def L(i):
            if s.ver <= 18 and i > 12:
                i += 1
            off, ln = struct.unpack_from("<ii", s.b, 12 + i * 8)
            return s.b[off:off + ln]
        sf, dv = L(3), L(4)
        out = []
        for i in range(len(sf) // 108):
            shn, fog, typ, fv, nv = struct.unpack_from("<5i", sf, i * 108)
            if typ not in (1, 2, 3) or nv <= 0 or not (0 <= shn < len(s.shaders)):
                continue
            xs, ys, zs = [], [], []
            for k in range(fv, fv + nv):
                x, y, z = struct.unpack_from("<3f", dv, k * 44)
                xs.append(x); ys.append(y); zs.append(z)
            out.append((s.shaders[shn][0].lower(), (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))))
        s._surfs = out
        return out

    def terrain_z(s, x, y):
        """terrain surface height at (x, y) or None where there is no patch (bilinear over the 64 u grid)."""
        k = (int(math.floor(x / 512.0)) * 512, int(math.floor(y / 512.0)) * 512)
        t = s.terrain.get(k)
        if not t:
            return None
        base, hm = t
        fx, fy = (x - k[0]) / 64.0, (y - k[1]) / 64.0
        i, j = min(int(fx), 7), min(int(fy), 7)
        u, v = fx - i, fy - j
        h00, h10 = hm[j * 9 + i], hm[j * 9 + i + 1]
        h01, h11 = hm[(j + 1) * 9 + i], hm[(j + 1) * 9 + i + 1]
        h = h00 * (1 - u) * (1 - v) + h10 * u * (1 - v) + h01 * (1 - u) * v + h11 * u * v
        return base + 2.0 * h

    # ---- entities
    def entities(s):
        out = []
        t = s._ents
        i = 0
        while True:
            a = t.find("{", i)
            if a < 0:
                break
            e = t.find("}", a)
            blk = t[a + 1:e]
            d = {}
            for ln in blk.split("\n"):
                ln = ln.strip()
                if not ln.startswith('"'):
                    continue
                q = ln.split('"')
                if len(q) >= 4:
                    d[q[1].lower()] = q[3]
            out.append(d)
            i = e + 1
        return out

    def model_bounds(s, n):
        m = s.models[n]
        return (m[0], m[1], m[2]), (m[3], m[4], m[5])

    # ---- brush helpers
    def brush_solid(s, bi):
        v = s._solid.get(bi)
        if v is None:
            f, n, shn = s.brushes[bi]
            cf = s.shaders[shn][2] if 0 <= shn < len(s.shaders) else 1
            v = bool(cf & CONTENTS_SOLID)
            s._solid[bi] = v
        return v

    def side_visible(s, side_idx):
        sn = s.sides[side_idx][1]
        if not (0 <= sn < len(s.shaders)):
            return False
        name, sf, cf = s.shaders[sn]
        low = name.lower()
        if sf & (SURF_SKY | SURF_NODRAW):
            return False
        if "clip" in low or "nodraw" in low or "caulk" in low or "sky" in low:
            return False
        return True

    # ---- tracing
    def _clip_brush(s, bi, p0, p1, ext, best):
        f, n, shn = s.brushes[bi]
        if n == 0 or not s.brush_solid(bi):
            return
        enter, leave = -1.0, 1.0
        hit_side = None
        for k in range(f, f + n):
            pn = s.sides[k][0]
            nx, ny, nz, d = s.planes[pn]
            dist = d + (abs(nx * ext[0]) + abs(ny * ext[1]) + abs(nz * ext[2]) if ext else 0.0)
            d0 = nx * p0[0] + ny * p0[1] + nz * p0[2] - dist
            d1 = nx * p1[0] + ny * p1[1] + nz * p1[2] - dist
            if d0 > 0 and d1 >= d0:
                return
            if d0 <= 0 and d1 <= 0:
                continue
            if d0 > d1:
                t = (d0 - EPS) / (d0 - d1)
                if t > enter:
                    enter, hit_side = t, k
            else:
                t = (d0 + EPS) / (d0 - d1)
                if t < leave:
                    leave = t
        if hit_side is not None and enter < leave and 0 <= enter < best[0]:
            pn = s.sides[hit_side][0]
            nx, ny, nz, d = s.planes[pn]
            best[:] = [enter, (nx, ny, nz), hit_side, bi]

    def trace_box(s, p0, p1, mins=(0, 0, 0), maxs=(0, 0, 0)):
        ext = None
        if any(mins) or any(maxs):
            ext = (max(abs(mins[0]), abs(maxs[0])), max(abs(mins[1]), abs(maxs[1])), max(abs(mins[2]), abs(maxs[2])))
        best = [1.0, None, -1, -1]
        seen = set()

        def rec(n, a, b, f0, f1):
            if f0 > best[0]:
                return
            if n < 0:
                fb, nb = s.leafs[-n - 1]
                for k in range(fb, fb + nb):
                    bi = s.leafbrushes[k]
                    if bi in seen:
                        continue
                    seen.add(bi)
                    s._clip_brush(bi, p0, p1, ext, best)
                return
            pn, c0, c1 = s.nodes[n]
            nx, ny, nz, d = s.planes[pn]
            off = (abs(nx * ext[0]) + abs(ny * ext[1]) + abs(nz * ext[2]) + 1.0) if ext else 1.0
            da = nx * a[0] + ny * a[1] + nz * a[2] - d
            db = nx * b[0] + ny * b[1] + nz * b[2] - d
            if da >= off and db >= off:
                rec(c0, a, b, f0, f1)
                return
            if da < -off and db < -off:
                rec(c1, a, b, f0, f1)
                return
            # straddles (or near): test both sides over the full span
            fm = f0 + (f1 - f0) * 0.5
            rec(c0, a, b, f0, f1)
            rec(c1, a, b, f0, f1)
        rec(0, p0, p1, 0.0, 1.0)
        if best[1] is None:
            return None
        return best[0], best[1], s.sides[best[2]][1], best[3], best[2]

    def trace(s, p0, p1):
        return s.trace_box(p0, p1)

    def hit_point(s, p0, p1, r):
        f = r[0]
        return tuple(p0[i] + (p1[i] - p0[i]) * f for i in range(3))

    def point_solid(s, p):
        """True when p lies inside a solid brush (zero-length trace test)."""
        r = s.trace_box(p, (p[0], p[1], p[2] + 0.01))
        # a start-inside brush never 'enters'; test containment directly over the leaf
        n = 0
        while n >= 0:
            pn, c0, c1 = s.nodes[n]
            nx, ny, nz, d = s.planes[pn]
            n = c0 if nx * p[0] + ny * p[1] + nz * p[2] - d >= 0 else c1
        fb, nb = s.leafs[-n - 1]
        for k in range(fb, fb + nb):
            bi = s.leafbrushes[k]
            if not s.brush_solid(bi):
                continue
            f, cnt, shn = s.brushes[bi]
            inside = True
            for j in range(f, f + cnt):
                nx, ny, nz, d = s.planes[s.sides[j][0]]
                if nx * p[0] + ny * p[1] + nz * p[2] - d > 0:
                    inside = False
                    break
            if inside:
                return True
        return False


def vec(sv, n=3):
    try:
        v = [float(x) for x in sv.replace(",", " ").split()]
    except Exception:
        return None
    return tuple(v[:n]) if len(v) >= n else None

"""gunmesh.py - a weapon TIKI's mesh in the gun's ENTITY space (what cg_engrave.c's anchors are written in).

entity space = what the cgame sees: world = refEntity.origin + p[i] * refEntity.axis[i]. The renderer builds it from
the skd's bone-local vertex offsets, posed by the tik's idle animation (frame 0), times the tik's setup scale.
Bone transforms compose as row vectors: p = off @ R + t, world = local * parent (skx.py's convention).
"""
import os, re, struct, sys
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import vfs  # noqa: E402


def q2m(q):
    x, y, z, w = q
    # column-vector rotation matrix; row-vector use is p @ M.T
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def read_tik(path, depth=0):
    """-> dict(scale, path, skelmodel, anims{name: file}, surfaces{name: shader}, includes)"""
    t = vfs.read(path)
    if t is None:
        return None
    t = t.decode("latin-1")
    t = re.sub(r"//[^\n]*", "", t)
    out = dict(scale=1.0, path="", skelmodel=None, anims={}, surfaces={})
    m = re.search(r"(?im)^\s*scale\s+([-\d.]+)", t)
    if m:
        out["scale"] = float(m.group(1))
    m = re.search(r"(?im)^\s*path\s+(\S+)", t)
    if m:
        out["path"] = m.group(1)
    m = re.search(r"(?im)^\s*skelmodel\s+(\S+)", t)
    if m:
        out["skelmodel"] = m.group(1)
    for s, sh in re.findall(r"(?im)^\s*surface\s+(\S+)\s+shader\s+(\S+)", t):
        out["surfaces"][s.lower()] = sh
    am = re.search(r"(?is)\banimations\s*\{(.*?)\n\}", t)
    if am:
        for name, f in re.findall(r"(?im)^\s*(\w+)\s+(\S+\.sk[ca])", am.group(1)):
            out["anims"].setdefault(name.lower(), f)
    # $include: inherit what this file did not set
    for inc in re.findall(r"(?im)^\s*\$include\s+(\S+)", t):
        if depth < 4:
            sub = read_tik(inc, depth + 1)
            if sub:
                for k in ("path", "skelmodel"):
                    if not out[k]:
                        out[k] = sub[k]
                if not re.search(r"(?im)^\s*scale\s", t):
                    out["scale"] = sub["scale"]
                for k, v in sub["anims"].items():
                    out["anims"].setdefault(k, v)
                for k, v in sub["surfaces"].items():
                    out["surfaces"].setdefault(k, v)
    return out


def _join(base, f):
    if "/" in f and f.lower().startswith("models/"):
        return f
    return (base.rstrip("/") + "/" + f) if base else f


def read_skd(b):
    nsurf, nbones, ofsb, ofss, ofse = struct.unpack_from("<5i", b, 72)
    bones = []
    off = ofsb
    for i in range(nbones):
        name = b[off:off + 32].split(b"\0")[0].decode("latin-1")
        par = b[off + 32:off + 64].split(b"\0")[0].decode("latin-1")
        typ, ofsdata, ofschan, ofsref, ofsend = struct.unpack_from("<5i", b, off + 64)
        bones.append((name, par))
        off += ofsend
    surfs = []
    off = ofss
    for _ in range(nsurf):
        name = b[off + 4:off + 68].split(b"\0")[0].decode("latin-1")
        ntri, nv, _sp, ofst, ofsv, ofsc, ofsend, ofsci = struct.unpack_from("<8i", b, off + 68)
        tris = np.array([struct.unpack_from("<3i", b, off + ofst + i * 12) for i in range(ntri)], int).reshape(-1, 3)
        verts = []
        p = off + ofsv
        for _v in range(nv):
            nx, ny, nz, u, v, nw, nm = struct.unpack_from("<5f2i", b, p)
            p += 28 + 16 * nm
            ws = []
            for _w in range(nw):
                bi, bw, ox, oy, oz = struct.unpack_from("<if3f", b, p)
                p += 20
                ws.append((bi, bw, np.array((ox, oy, oz))))
            verts.append(((nx, ny, nz), (u, v), ws))
        surfs.append(dict(name=name, tris=tris, verts=verts))
        off += ofsend
    return bones, surfs


def read_skc_frame0(b):
    nc, o_ch = struct.unpack_from("<2i", b, 36)
    if not (0 < nc <= 4096) or not (0 < o_ch < len(b)) or o_ch + 32 * nc > len(b):
        # another SKAN layout: garbage counts here once spun for ten minutes a gun (bug-10714); the measured bones are used
        raise ValueError("unexpected SKAN header")
    chans = [b[o_ch + 32 * i:o_ch + 32 * i + 32].split(b"\0")[0].decode("latin-1") for i in range(nc)]
    ov = struct.unpack_from("<i", b, 48 + 44)[0]
    vals = [struct.unpack_from("<4f", b, ov + 16 * c) for c in range(nc)]
    return dict(zip(chans, vals))


def bone_world(bones, chan):
    """-> list of (R, t) per bone in model space; R applied as p @ R"""
    out = {}
    res = []
    for name, par in bones:
        pos = chan.get(name + " pos", (0, 0, 0, 0))[:3]
        rot = chan.get(name + " rot", (0, 0, 0, 1))
        Rl = q2m(rot)  # (matches the engine's tag positions in x and z; the engine's measured bones are preferred)
        tl = np.array(pos)
        if par in out:
            Rp, tp = out[par]
            R = Rl @ Rp
            t = tl @ Rp + tp
        else:
            R, t = Rl, tl
        out[name] = (R, t)
        res.append((R, t))
    return res


def load(tikpath, anim="idle", engine_bones=None):
    """-> dict(tik, scale, surfaces=[dict(name, shader, tris (T,3), pos (V,3) entity space, nrm (V,3), uv (V,2))])
    engine_bones: {bone name: (origin (3,), axes (3,3))} measured in game (ENGRAVETAG): the bones exactly as the engine posed
    them in first person - used instead of the offline idle pose when given (p = origin + scale * off @ axes)."""
    tk = read_tik(tikpath)
    if not tk or not tk["skelmodel"]:
        return None
    b = vfs.read(_join(tk["path"], tk["skelmodel"]))
    if b is None:
        return None
    bones, surfs = read_skd(b)
    chan = {}
    a = tk["anims"].get(anim) or (next(iter(tk["anims"].values())) if tk["anims"] else None)
    if a:
        cb = vfs.read(_join(tk["path"], a))
        if cb is not None and cb[:4] == b"SKAN":
            try:
                chan = read_skc_frame0(cb)
            except Exception:
                chan = {}   # an older / compressed SKAN layout: the engine's measured bones are used instead anyway
    BW = bone_world(bones, chan)
    sc = tk["scale"]
    if engine_bones:
        EB = []
        for (name, par), (R, t) in zip(bones, BW):
            e = engine_bones.get(name) or engine_bones.get(name.strip())
            EB.append((np.asarray(e[1]), np.asarray(e[0]) / sc) if e else (R, t))
        BW = EB
    out = []
    for s in surfs:
        P, N, UV = [], [], []
        for (n, uv, ws) in s["verts"]:
            p = np.zeros(3)
            nn = np.zeros(3)
            for bi, bw, o in ws:
                R, t = BW[bi] if bi < len(BW) else (np.eye(3), np.zeros(3))
                p += bw * (o @ R + t)
                nn += bw * (np.array(n) @ R)
            P.append(p * sc)
            N.append(nn / (np.linalg.norm(nn) + 1e-9))
            UV.append(uv)
        out.append(dict(name=s["name"], shader=tk["surfaces"].get(s["name"].lower(), ""), tris=s["tris"],
                        pos=np.array(P), nrm=np.array(N), uv=np.array(UV)))
    return dict(tik=tikpath, scale=tk["scale"], anim=a, surfaces=out)


if __name__ == "__main__":
    m = load(sys.argv[1])
    allp = np.vstack([s["pos"] for s in m["surfaces"]])
    print(m["tik"], "scale", m["scale"], "anim", m["anim"], "bbox", allp.min(0).round(2), allp.max(0).round(2))
    for s in m["surfaces"]:
        print(" ", s["name"], s["shader"], len(s["pos"]), s["pos"].min(0).round(2), s["pos"].max(0).round(2))

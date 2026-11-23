#!/usr/bin/env python3
"""European Assault AI navigation (level_a.str), decoded. Our own code, stdlib only (decode audit gap 2, 2026-11-23).

Two chunk types carry the original's AI navigation (chunk header {u32 id, u32 type, u32 size, u32 ?}; the type is
CRC32 of the type name, named from the XBE's strings):

  0x99503409  (x1, ~100 KB) the AREA NAVMESH ("Ai\\Pathfinding\\AreaPathNode.cpp"). After the 0x20-byte chunk
              header, offsets are relative to chunk+0x20:
                +0x00 u32 13 (version?), zeros, +0x58 u32 off_polys, +0x5c u32 npolys, +0x60 u32 off_verts,
                +0x64 u32 nverts, +0x68 u32 off_tree (2D BSP for point location), +0x6c u32 ?
                verts: f32 xyz metres (the .cdb frame, Z up)
                polys (20 B): u32 flags, u8 nwall, u8 nlink, u8 area(1), u8 0, u32 off_idx, u32 off_links, f32 cost
                  idx: u16[nwall + nlink] vertex indices, convex, in order
                  links: u32[nlink] = (poly | 0x8000) | edge_from << 16 | edge_to << 24, edge = position in idx
                         (the shared edge idx[e_from] -> idx[e_to]; links are mutual)
                tree: {f32 nx, ny, 0, d, i32 front, i32 back} nodes, negative child = leaf (not needed here)
  0xa760df16  RuntimeRigInstanceType (x882): COVER POINTS. TLV records {u32 field crc, u32 type, u32 len, data}:
                bf5a86a3 pos (f32 xyz m), d00afaa7 rotation quaternion (x y z w, yaw only), 276d2c08 -> the rig
                definition (all 882: the cover rig, entries COVER_STAND_ENTER_CENTER / LEFT / RIGHT / STAND, CROUCH),
                b31066e2 -> the rig collection (all 882 in one), 2d3c0eb7 tag list (Left / Right / Back + nine
                unnamed crcs), 6dfd3ee1 {id crc, side crc Left|Right} on 613 (the lean side), c09fb315 = 2 on 155.

Nothing here is EA data; run it on the player's own disc only, and keep its output local.
"""
import math
import struct
import zlib

NAV_TYPE = 0x99503409
RIG_TYPE = 0xa760df16
_C = {zlib.crc32(s.encode()) & 0xffffffff: s for s in ("Left", "Right", "Back", "")}


def chunks(d):
    n = struct.unpack_from("<I", d, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(d):
        cid, typ, sz, _x = struct.unpack_from("<4I", d, p)
        if sz < 16:
            break
        yield p, cid, typ, sz
        p += sz


def navmesh(stream):
    """-> {"verts": [(x, y, z) m], "polys": [{"idx": [...], "links": [(poly, e_from, e_to)], "nwall", "flags",
    "area", "cost"}]} or None"""
    for p, _cid, typ, sz in chunks(stream):
        if typ == NAV_TYPE:
            c = stream[p + 0x20:p + sz]
            break
    else:
        return None
    op, npo, ov, nv = struct.unpack_from("<4I", c, 0x58)
    verts = [struct.unpack_from("<3f", c, ov + 12 * i) for i in range(nv)]
    polys = []
    for i in range(npo):
        fl, nw, nl, area, b3, oi, ol, cost = struct.unpack_from("<I4BIIf", c, op + 20 * i)
        idx = list(struct.unpack_from("<%dH" % (nw + nl), c, oi))
        links = []
        for k in range(nl):
            w = struct.unpack_from("<I", c, ol + 4 * k)[0]
            links.append((w & 0x7fff, (w >> 16) & 0xff, (w >> 24) & 0xff, (w >> 15) & 1))
        polys.append({"idx": idx, "links": links, "nwall": nw, "flags": fl, "area": area, "b3": b3, "cost": cost})
    return {"verts": verts, "polys": polys, "hdr": struct.unpack_from("<4I", c, 0x58), "tree_off": struct.unpack_from("<I", c, 0x68)[0]}


def _tlv(stream, p):
    nf = struct.unpack_from("<I", stream, p + 16)[0]
    q, out = p + 20, {}
    for _ in range(nf):
        k, t, n = struct.unpack_from("<3I", stream, q)
        out[k] = (t, stream[q + 12:q + 12 + n])
        q += 12 + n
    return out


def cover(stream):
    """the cover rig instances -> [{"pos" (m), "yaw" (deg, the rig's facing = its +X axis), "side" ("Left" / "Right" /
    None), "tags" [names or hex], "c09": int or None, "id"}]"""
    out = []
    for p, cid, typ, _sz in chunks(stream):
        if typ != RIG_TYPE:
            continue
        f = _tlv(stream, p)
        pos = struct.unpack("<3f", f[0xbf5a86a3][1][:12])
        qx, qy, qz, qw = struct.unpack("<4f", f[0xd00afaa7][1][:16])
        yaw = math.degrees(2 * math.atan2(qz, qw)) % 360 if abs(qx) + abs(qy) < 1e-3 else \
            math.degrees(math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))) % 360
        side = None
        if 0x6dfd3ee1 in f and len(f[0x6dfd3ee1][1]) >= 8:
            side = _C.get(struct.unpack("<2I", f[0x6dfd3ee1][1][:8])[1])
        tl = f.get(0x2d3c0eb7, (0, b""))[1]
        tags = [_C.get(w, "%08x" % w) for w in struct.unpack("<%dI" % (len(tl) // 4), tl)]
        c09 = struct.unpack("<I", f[0xc09fb315][1][:4])[0] if 0xc09fb315 in f else None
        out.append({"id": cid, "pos": pos, "yaw": yaw, "side": side, "tags": [t for t in tags if t], "c09": c09})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# conversion to MOHAA path nodes (map units). The engine links two info_pathnodes when they are under 384u apart and
# its CheckMove walks the line (navigate.cpp CheckPathToDefault), so the original's walkable polygons become nodes:
#   portal nodes   on every shared edge (one per <= PORTAL_STEP of edge, inset from the edge's ends),
#   area nodes     on a LATTICE-spaced grid inside each polygon, kept INSET from its wall edges (the original's own
#                  wall clearance is ~0; a MOHAA body is 30u wide), plus the centroid of a polygon no lattice point hit.
# Every node is dropped to our collision floor (the disc's own .cdb, so it agrees to a few units) and must fit a
# standing MOHAA body there; a node that does not fit is moved up to FIT_R or dropped (counted in the stats).
# Cover: the 882 cover rigs become cover nodes (MOHAA spawnflags, the convention measured on the stock maps, see
# docs/tools/frontline/flcover.py): the rig's threat facing F = its quaternion yaw + 90 (the wall is on the rig's +Y:
# 98 % of rigs hit collision within 1.2 m that way at 0.6 m height, 0-12 % any other way). Wall at 1.45 m -> high
# cover: disc side Left -> corner_left (16), Right -> corner_right (32) (geometry agrees: "Left" rigs are open on the
# right as you face the threat 54:19, "Right" ones on the left 72:25 - the MOHAA naming), node yaw F + 180, when the
# open side is clear for a body; else plain cover (4), yaw F. Low wall -> crate (128, fire over it), yaw F.
# ---------------------------------------------------------------------------------------------------------------------
SCALE = 48.0
PORTAL_STEP = 192.0
LATTICE = 176.0
WALL_INSET = 22.0
FIT_R = 40
CHAIN_STEP = 128.0
AI_COVER, AI_CORNER_LEFT, AI_CORNER_RIGHT, AI_CRATE = 4, 16, 32, 128


def _in_poly(pt, poly):
    """pt inside convex poly (CCW, map xy) by at least 0 -> min signed distance to its edges (negative = outside)"""
    best = 1e9
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        L = math.hypot(ex, ey) or 1e-9
        d = (ex * (pt[1] - a[1]) - ey * (pt[0] - a[0])) / L
        best = min(best, d)
    return best


def _wall_dist(pt, poly, walls):
    """distance from pt to the nearest WALL edge (edge k = poly[k] -> poly[k+1] in walls) of a convex poly"""
    best = 1e9
    n = len(poly)
    for k in walls:
        a, b = poly[k], poly[(k + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        L2 = ex * ex + ey * ey or 1e-9
        t = max(0.0, min(1.0, ((pt[0] - a[0]) * ex + (pt[1] - a[1]) * ey) / L2))
        best = min(best, math.hypot(pt[0] - a[0] - t * ex, pt[1] - a[1] - t * ey))
    return best


def _z_in(pt, poly3):
    """height of the polygon's surface at pt (fan triangles; the nearest vertex height outside them)"""
    a = poly3[0]
    for k in range(1, len(poly3) - 1):
        b, c = poly3[k], poly3[k + 1]
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (pt[0] - c[0]) + (c[0] - b[0]) * (pt[1] - c[1])) / den
        l2 = ((c[1] - a[1]) * (pt[0] - c[0]) + (a[0] - c[0]) * (pt[1] - c[1])) / den
        l3 = 1 - l1 - l2
        if min(l1, l2, l3) >= -1e-3:
            return l1 * a[2] + l2 * b[2] + l3 * c[2]
    return min(poly3, key=lambda v: (v[0] - pt[0]) ** 2 + (v[1] - pt[1]) ** 2)[2]


def _fit(grid, x, y, z, max_r=FIT_R):
    """our floor under (x, y) nearest the navmesh height z, where a standing MOHAA body fits; nearest such spot within
    max_r (rings of 8u) -> (x, y, floor) or None"""
    # first with 10u of room (a node hugging a wall links to nothing along it: the east gallery), then 2u
    for mg, mr in ((10.0, 32), (2.0, max_r)):
        for r in range(0, mr + 1, 8):
            n = 1 if r == 0 else max(8, int(2 * math.pi * r / 8))
            for k in range(n):
                a = 2 * math.pi * k / n
                px, py = x + r * math.cos(a), y + r * math.sin(a)
                g = grid.ground(px, py, z + 40.0, z - 56.0)
                if g is None:
                    continue
                if grid.box_free(px, py, g, lift=18.0, margin=mg):
                    return (round(px), round(py), round(g, 1))
    return None


def build(stream, X, grid, level_spec=None):
    """the original's navigation as MOHAA nodes. X = the converter's disc->map transform, grid = flgeom.TriGrid of the
    converted collision. -> (nodes [(x, y, floor z)], cover [(x, y, floor z, spawnflags, yaw)], stats)"""
    N = navmesh(stream)
    if N is None:
        return [], [], {"navmesh": 0}
    V = [X(v) for v in N["verts"]]
    P = N["polys"]
    st = {"navmesh_polys": len(P), "navmesh_verts": len(V), "navmesh_area_m2": 0.0}
    # the four island polygons outside the play space (no collision under them) fall out at _fit
    raw = []          # (x, y, nav z, kind)
    for i, p in enumerate(P):
        poly = [V[k] for k in p["idx"]]
        n = len(poly)
        area = sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n)) / 2
        if area < 0:             # keep CCW for _in_poly
            poly = poly[::-1]
            linked_edges = {(n - 1 - b) % n for (_j, a, b, _f) in p["links"]}
        else:
            linked_edges = {a % n for (_j, a, b, _f) in p["links"]}
        st["navmesh_area_m2"] += abs(area) / SCALE ** 2
        walls = [k for k in range(n) if k not in linked_edges]
        # portals (each once, from the lower poly index)
        for (j, a, b, _f) in p["links"]:
            if j < i:
                continue
            A, B = V[p["idx"][a % len(p["idx"])]], V[p["idx"][b % len(p["idx"])]]
            L = math.hypot(B[0] - A[0], B[1] - A[1])
            if L < 2 * WALL_INSET + 8:
                ts = [0.5]
            else:
                m = max(1, int(math.ceil((L - 2 * WALL_INSET) / PORTAL_STEP)))
                ts = [(WALL_INSET + (L - 2 * WALL_INSET) * (k + 0.5) / m) / L for k in range(m)]
            for t in ts:
                raw.append((A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t, "portal"))
        # area lattice
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        hit = False
        for gx in range(int(min(xs) // LATTICE), int(max(xs) // LATTICE) + 1):
            for gy in range(int(min(ys) // LATTICE), int(max(ys) // LATTICE) + 1):
                pt = (gx * LATTICE + LATTICE / 2, gy * LATTICE + LATTICE / 2)
                if _in_poly(pt, poly) < 0 or _wall_dist(pt, poly, walls) < WALL_INSET:
                    continue
                raw.append((pt[0], pt[1], _z_in(pt, poly), "area"))
                hit = True
        # chains: between every two of this polygon's portal midpoints (a straight line inside a convex polygon),
        # a node every <= CHAIN_STEP - a long narrow polygon (a stair strip) gets no lattice point otherwise
        mids = []
        for (j, a, b, _f) in p["links"]:
            A, B = V[p["idx"][a % len(p["idx"])]], V[p["idx"][b % len(p["idx"])]]
            mids.append(((A[0] + B[0]) / 2, (A[1] + B[1]) / 2, (A[2] + B[2]) / 2))
        for u in range(len(mids)):
            for w in range(u + 1, len(mids)):
                P0, P1 = mids[u], mids[w]
                L = math.hypot(P1[0] - P0[0], P1[1] - P0[1])
                m = int(L // CHAIN_STEP)
                for k in range(1, m + 1):
                    t = k / (m + 1)
                    pt = (P0[0] + (P1[0] - P0[0]) * t, P0[1] + (P1[1] - P0[1]) * t)
                    raw.append((pt[0], pt[1], _z_in(pt, poly), "chain"))
        if not hit:
            # a narrow polygon (a gallery strip, a stair): half the lattice step and half the inset
            for gx in range(int(min(xs) // (LATTICE / 2)), int(max(xs) // (LATTICE / 2)) + 1):
                for gy in range(int(min(ys) // (LATTICE / 2)), int(max(ys) // (LATTICE / 2)) + 1):
                    pt = (gx * LATTICE / 2 + LATTICE / 4, gy * LATTICE / 2 + LATTICE / 4)
                    if _in_poly(pt, poly) < 0 or _wall_dist(pt, poly, walls) < WALL_INSET / 2:
                        continue
                    raw.append((pt[0], pt[1], _z_in(pt, poly), "area"))
                    hit = True
        if not hit:
            cx, cy = sum(xs) / n, sum(ys) / n
            if _wall_dist((cx, cy), poly, walls) >= WALL_INSET * 0.5:
                raw.append((cx, cy, _z_in((cx, cy), poly), "centre"))
    st["raw"] = len(raw)
    # thin: a node within 80u (same floor) of an earlier one is dropped; portals first so edges keep theirs
    raw.sort(key=lambda r: {"portal": 0, "centre": 1, "area": 2, "chain": 3}[r[3]])
    cell, kept = {}, []
    for r in raw:
        ck = (int(r[0] // 128), int(r[1] // 128))
        if any((q[0] - r[0]) ** 2 + (q[1] - r[1]) ** 2 < 80.0 ** 2 and abs(q[2] - r[2]) < 64
               for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in cell.get((ck[0] + dx, ck[1] + dy), ())):
            continue
        cell.setdefault(ck, []).append(r)
        kept.append(r)
    st["thinned"] = len(kept)
    nodes, nofit, moved = [], 0, 0
    seen = set()
    for x, y, z, kind in kept:
        f = _fit(grid, x, y, z)
        if f is None:
            nofit += 1
            continue
        if (f[0], f[1]) in seen:
            continue
        seen.add((f[0], f[1]))
        moved += (abs(f[0] - x) > 1 or abs(f[1] - y) > 1)
        nodes.append(f)
    st.update({"nodes": len(nodes), "nofit_dropped": nofit, "nudged": moved})
    # cover
    cov, ck = [], {"crate": 0, "corner_left": 0, "corner_right": 0, "cover": 0, "nofit": 0}
    for c in cover(stream):
        p = X(c["pos"])
        F = c["yaw"] + 90.0
        f_ = math.radians(F)
        fx, fy = math.cos(f_), math.sin(f_)
        hi = _blocked(grid, p, fx, fy, 1.45 * SCALE)
        if not hi:
            flags, yaw, kind = AI_CRATE, F, "crate"
        elif c["side"] in ("Left", "Right"):
            # the open side: right of the threat facing for Left (MOHAA corner_left), left for Right
            sg = -1.0 if c["side"] == "Left" else 1.0
            ox, oy = p[0] + sg * -fy * 40.0, p[1] + sg * fx * 40.0
            if _blocked(grid, (ox, oy, p[2]), fx, fy, 1.0 * SCALE):
                flags, yaw, kind = AI_COVER, F, "cover"
            else:
                flags = AI_CORNER_LEFT if c["side"] == "Left" else AI_CORNER_RIGHT
                yaw, kind = F + 180.0, "corner_" + c["side"].lower()
        else:
            flags, yaw, kind = AI_COVER, F, "cover"
        # stand the body clear of the wall: search outward from the rig, away from its cover first
        spot = None
        for r in range(0, 49, 6):
            for da in (0, 30, -30, 60, -60, 90, -90):
                a_ = math.radians(F + 180 + da)
                x_, y_ = p[0] + r * math.cos(a_), p[1] + r * math.sin(a_)
                g = grid.ground(x_, y_, p[2] + 24, p[2] - 48)
                if g is not None and grid.box_free(x_, y_, g, lift=18.0, margin=2.0):
                    spot = (round(x_), round(y_), round(g, 1))
                    break
                if r == 0:
                    break
            if spot:
                break
        if spot is None:
            ck["nofit"] += 1
            continue
        ck[kind] += 1
        cov.append((spot[0], spot[1], spot[2], flags, yaw % 360))
    st["cover"] = ck
    return nodes, cov, st


def walk(grid, p, q, margin=2.0):
    """[as flconvert's node-link test, ~navigate.cpp CheckMove] a body walks p -> q (floor points) in a straight line:
    every 16u a floor within 17u up / 30u down and free standing room"""
    n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / 16.0))
    z = p[2]
    for k in range(1, n + 1):
        x = p[0] + (q[0] - p[0]) * k / n
        y = p[1] + (q[1] - p[1]) * k / n
        g = grid.ground(x, y, z + 17.0, z - 30.0)
        if g is None or not grid.box_free(x, y, g, lift=18.0, margin=margin):
            return False
        z = g
    return abs(z - q[2]) < 20.0


def _link(grid, p, q):
    return abs(p[2] - q[2]) < 200 and (walk(grid, p, q) or walk(grid, q, p))


def repair_portals(stream, X, grid, nodes, max_pairs=8):
    """every navmesh portal whose two sides' nearby nodes do not link (our collision is not the original's: the MOHAA
    body is wider than EA's eroded agent, door frames and sills differ) gets a crossing pair: a node each side of the
    portal, 24-48u off it, at the first spot along the edge (from its middle outward, up to 64u past its ends) where
    the pair walks across. -> (added nodes, stats)"""
    N = navmesh(stream)
    V = [X(v) for v in N["verts"]]
    P = N["polys"]
    polys = []
    for p in P:
        poly = [V[k] for k in p["idx"]]
        n = len(poly)
        if sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n)) < 0:
            poly = poly[::-1]
        polys.append(poly)
    cell = {}

    def add(q):
        cell.setdefault((int(q[0] // 128), int(q[1] // 128)), []).append(q)
    for q in nodes:
        add(q)

    def near(x, y, z, r):
        k = int(r // 128) + 1
        out = []
        for dx in range(-k, k + 1):
            for dy in range(-k, k + 1):
                for q in cell.get((int(x // 128) + dx, int(y // 128) + dy), ()):
                    if (q[0] - x) ** 2 + (q[1] - y) ** 2 < r * r and abs(q[2] - z) < 200:
                        out.append(q)
        return sorted(out, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2)

    def side_of(q, ax, ay, nx, ny):
        return (q[0] - ax) * nx + (q[1] - ay) * ny

    added, st = [], {"portals": 0, "linked": 0, "repaired": 0, "unrepaired": []}
    for i, p in enumerate(P):
        for (j, a, b, _f) in p["links"]:
            if j < i:
                continue
            st["portals"] += 1
            A, B = V[p["idx"][a % len(p["idx"])]], V[p["idx"][b % len(p["idx"])]]
            ex, ey = B[0] - A[0], B[1] - A[1]
            L = math.hypot(ex, ey) or 1e-6
            ux, uy = ex / L, ey / L
            # normal pointing into j: poly i is CCW-left of its own edge, so j lies on the right
            nx, ny = uy, -ux
            mx, my, mz = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2, (A[2] + B[2]) / 2
            cand = near(mx, my, mz, 384.0)
            # the nodes standing in each polygon (grown 40u), off the portal line itself
            si = [q for q in cand if side_of(q, mx, my, nx, ny) < -4 and _in_poly(q, polys[i]) > -40][:max_pairs]
            sj = [q for q in cand if side_of(q, mx, my, nx, ny) > 4 and _in_poly(q, polys[j]) > -40][:max_pairs]
            if not si:
                si = [q for q in cand if side_of(q, mx, my, nx, ny) < -4][:2]
            if not sj:
                sj = [q for q in cand if side_of(q, mx, my, nx, ny) > 4][:2]
            if any(_link(grid, u, v) for u in si[:4] for v in sj[:4]):
                st["linked"] += 1
                continue
            done = False
            offs = [0.0]
            for k in range(1, int((L / 2 + 64) // 6) + 1):
                offs += [6.0 * k, -6.0 * k]
            for o in offs:
                cx, cy = mx + ux * o, my + uy * o
                for d in (24.0, 36.0, 48.0):
                    pa = (cx - nx * d, cy - ny * d)
                    pb = (cx + nx * d, cy + ny * d)
                    ga = grid.ground(pa[0], pa[1], mz + 40, mz - 56)
                    gb = grid.ground(pb[0], pb[1], mz + 40, mz - 56)
                    if ga is None or gb is None:
                        continue
                    qa, qb = (round(pa[0]), round(pa[1]), round(ga, 1)), (round(pb[0]), round(pb[1]), round(gb, 1))
                    if not (grid.box_free(qa[0], qa[1], qa[2], lift=18.0, margin=2.0)
                            and grid.box_free(qb[0], qb[1], qb[2], lift=18.0, margin=2.0)):
                        continue
                    if not _link(grid, qa, qb):
                        continue
                    if not (any(_link(grid, qa, v) for v in si[:6]) or not si) or \
                            not (any(_link(grid, qb, v) for v in sj[:6]) or not sj):
                        continue
                    added += [qa, qb]
                    add(qa)
                    add(qb)
                    done = True
                    break
                if done:
                    break
            if done:
                st["repaired"] += 1
            else:
                st["unrepaired"].append((round(mx), round(my), round(mz)))
                st.setdefault("unrepaired_pairs", []).append((i, j))
    return added, st


def chain_repair(stream, X, grid, pairs, margin=1.0, step=16.0, spacing=64.0):
    """a narrow crossing (a cellar stair a body passes with ~1u to spare): for each uncrossed portal (i, j), a straight
    chain from the far portal of i or j, across this portal, 64u on - shifted sideways (to 48u) to where every 16u a
    floor follows (17u up / 30u down) and the ENGINE's body fits: margin 1 = MOHAA's +-15 actor against the 2u
    collision slabs (repair_portals and flconvert test at 2). A node every `spacing` along it. -> (nodes, stats)"""
    N = navmesh(stream)
    V = [X(v) for v in N["verts"]]
    P = N["polys"]

    def mid(p, a, b):
        A, B = V[p["idx"][a % len(p["idx"])]], V[p["idx"][b % len(p["idx"])]]
        return ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2, (A[2] + B[2]) / 2)

    out, st = [], {"chains": 0, "failed": []}
    for i, j in pairs:
        pi = P[i]
        m = next(mid(pi, a, b) for (jj, a, b, _f) in pi["links"] if jj == j)
        done = False
        for near_, far_ in ((i, j), (j, i)):
            for (k, a, b, _f) in P[far_]["links"]:
                if k == near_:
                    continue
                F = mid(P[far_], a, b)
                dx, dy = m[0] - F[0], m[1] - F[1]
                L = math.hypot(dx, dy)
                if L < 8:
                    continue
                ux, uy = dx / L, dy / L
                E = (m[0] + ux * 64.0, m[1] + uy * 64.0)
                tot = L + 64.0
                for o in [0.0] + [s_ * d for d in range(2, 49, 2) for s_ in (1, -1)]:
                    ox, oy = -uy * o, ux * o
                    z = F[2]
                    pts = []
                    ok = True
                    n = int(tot // step) + 1
                    for q in range(n + 1):
                        x = F[0] + ox + (E[0] - F[0]) * q / n
                        y = F[1] + oy + (E[1] - F[1]) * q / n
                        g = grid.ground(x, y, z + (40.0 if q == 0 else 17.0), z - (56.0 if q == 0 else 30.0))
                        if g is None or not grid.box_free(x, y, g, lift=18.0, margin=margin):
                            ok = False
                            break
                        z = g
                        pts.append((round(x), round(y), round(g, 1)))
                    if not ok:
                        continue
                    every = max(1, int(spacing // (tot / n)))
                    out += pts[::every] + [pts[-1]]
                    done = True
                    break
                if done:
                    break
            if done:
                break
        if done:
            st["chains"] += 1
        else:
            st["failed"].append((i, j))
    return out, st


def on_mesh(stream, X, pts, tol=32.0, dz=64.0):
    """the points (x, y, floor z, map units) that stand on the original's navmesh: inside a polygon (grown by tol) and
    within dz of its surface -> list of bools"""
    N = navmesh(stream)
    polys = []
    for p in N["polys"]:
        poly = [X(N["verts"][k]) for k in p["idx"]]
        n = len(poly)
        if sum(poly[k][0] * poly[(k + 1) % n][1] - poly[(k + 1) % n][0] * poly[k][1] for k in range(n)) < 0:
            poly = poly[::-1]
        xs, ys = [q[0] for q in poly], [q[1] for q in poly]
        polys.append((min(xs) - tol, max(xs) + tol, min(ys) - tol, max(ys) + tol, poly))
    cell = {}
    for k, b in enumerate(polys):
        for gx in range(int(b[0] // 256), int(b[1] // 256) + 1):
            for gy in range(int(b[2] // 256), int(b[3] // 256) + 1):
                cell.setdefault((gx, gy), []).append(k)
    out = []
    for x, y, z in pts:
        ok = False
        for k in cell.get((int(x // 256), int(y // 256)), ()):
            b = polys[k]
            if b[0] <= x <= b[1] and b[2] <= y <= b[3] and _in_poly((x, y), b[4]) >= -tol \
                    and abs(_z_in((x, y), b[4]) - z) < dz:
                ok = True
                break
        out.append(ok)
    return out


def merge(stream, X, nav_nodes, gen_nodes, min_d=80.0):
    """the generated lattice's nodes that stand ON the original's navmesh and not within min_d of a navmesh node:
    they carry the links our collision denies the navmesh's own nodes (door sills and stairs a MOHAA body walks only
    in shorter hops). Nodes off the original's walkable area are left out. -> (extra nodes, stats)"""
    on = on_mesh(stream, X, gen_nodes)
    cell = {}
    for q in nav_nodes:
        cell.setdefault((int(q[0] // 128), int(q[1] // 128)), []).append(q)
    out, off = [], 0
    for p, ok in zip(gen_nodes, on):
        if not ok:
            off += 1
            continue
        ck = (int(p[0] // 128), int(p[1] // 128))
        if any((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < min_d * min_d and abs(q[2] - p[2]) < 64
               for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in cell.get((ck[0] + dx, ck[1] + dy), ())):
            continue
        out.append(p)
    return out, {"gen_on_mesh_added": len(out), "gen_off_mesh_dropped": off, "gen_total": len(gen_nodes)}


def _blocked(grid, p, fx, fy, h, dist=1.2 * SCALE):
    """collision within `dist` of p (x, y, floor z) along (fx, fy) at height h above the floor (a thin probe box)"""
    import flgeom
    for k in range(1, 9):
        x, y = p[0] + fx * dist * k / 8, p[1] + fy * dist * k / 8
        c = (x, y, p[2] + h)
        for i in grid.near(x, y, 6):
            if flgeom.tri_box(c, (3.0, 3.0, 3.0), *grid.tris[i]):
                return True
    return False


def borrow(stream, X, gen_nodes, unrepaired, r=176.0, dz=96.0):
    """the generated lattice's nodes (its 40u fine nodes and bridge chains, made for our collision) within r of a
    portal repair_portals could not cross: the crossing the original makes there (a sill, a narrow stair foot, a
    cellar stair) is walked on the generated nodes. Only nodes on or within 48u of the original's navmesh."""
    near = [q for q in gen_nodes if any((q[0] - u[0]) ** 2 + (q[1] - u[1]) ** 2 < r * r and abs(q[2] - u[2]) < dz
                                        for u in unrepaired)]
    ok = on_mesh(stream, X, near, tol=48.0, dz=72.0)
    return [q for q, k in zip(near, ok) if k]

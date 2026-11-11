#!/usr/bin/env python3
"""The original's AI routes stay open (our code; runs inside the converter on the player's PC).

Frontline's navigation points are linked where its characters walk. Its body is ~20u wide; MOHAA's box is 30u, so
a gap the original walks through can be too narrow for a MOHAA player or actor (walk audit: 28 such gaps on the
routes), and collision we add ourselves (flsheets' drawn-geometry slabs) can end up across a route the original
kept open (13 route blocks).

A ROUTE here is a pair of navigation points at most `reach` apart, within `rise` in height, whose straight line (at
40u and 60u above the floor) crosses none of the level's own collision - the original's characters walk it. Then:
  * drawn-geometry collision (flsheets) that the route crosses is not added (`keep_drawn`);
  * where a MOHAA box cannot stand on the route (sampled every `step` u), the collision within the box's reach is cut
    away above the step height - collision only, nothing drawn changes (`carve`), the same way flclear carves
    crouch headroom.
"""
import math

import flclear
import flgeom


def flclear_normal(t):
    a, b, c = t
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    return None if ln < 1e-9 else (n[0] / ln, n[1] / ln, n[2] / ln)


def routes(navs, grid, reach=200.0, rise=40.0):
    """navs: [(x, y, z)] MOHAA-unit navigation points; grid: TriGrid over the level's own collision.
    Returns [((x0, y0, floor0), (x1, y1, floor1))] open routes."""
    pts = []
    for p in navs:
        g = grid.ground(p[0], p[1], p[2] + 32, p[2] - 96)
        if g is not None:
            pts.append((p[0], p[1], g))
    cell = {}
    for i, p in enumerate(pts):
        cell.setdefault((int(p[0] // reach), int(p[1] // reach)), []).append(i)
    out = []
    for i, p in enumerate(pts):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cell.get((int(p[0] // reach) + dx, int(p[1] // reach) + dy), ()):
                    if j <= i:
                        continue
                    q = pts[j]
                    if math.hypot(q[0] - p[0], q[1] - p[1]) > reach or abs(q[2] - p[2]) > rise:
                        continue
                    ok = True
                    for h in (40.0, 60.0):
                        a = (p[0], p[1], p[2] + h)
                        b = (q[0], q[1], q[2] + h)
                        idx = grid.near((a[0] + b[0]) / 2, (a[1] + b[1]) / 2,
                                        math.hypot(b[0] - a[0], b[1] - a[1]) / 2 + 8)
                        if flclear._seg_hits(grid.tris, idx, a, b):
                            ok = False
                            break
                    if ok:
                        out.append((p, q))
    return out


def keep_drawn(drawn, segs, heights=(24.0, 36.0, 48.0, 72.0)):
    """drop the drawn-geometry collision triangles an open route crosses"""
    if not drawn or not segs:
        return drawn, 0
    G = flgeom.TriGrid(drawn, cell=128.0)
    bad = set()
    for p, q in segs:
        for h in heights:
            a = (p[0], p[1], p[2] + h)
            b = (q[0], q[1], q[2] + h)
            idx = G.near((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, math.hypot(b[0] - a[0], b[1] - a[1]) / 2 + 8)
            d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            for i in idx:
                if i not in bad and flclear._seg_hits(G.tris, [i], a, b):
                    bad.add(i)
    return [t for i, t in enumerate(drawn) if i not in bad], len(bad)


def carve(tris, tags, segs, step_h=38.0, top=96.0, half=19.0, spacing=12.0, keep=lambda f: False):
    """cut the collision that keeps a MOHAA box off an open route, above the step height (collision only)"""
    G = flgeom.TriGrid(tris)
    boxes = []
    for p, q in segs:
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        n = max(1, int(L // spacing))
        for k in range(n + 1):
            f = k / n
            x, y = p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f
            z = p[2] + (q[2] - p[2]) * f
            # a standing MOHAA box (15u + the 2u half-slab of each collision prism + 1, up to 96u) above the step
            hz_ = (top - step_h) / 2
            if not any(flgeom.tri_box((x, y, z + step_h + hz_), (18.0, 18.0, hz_), *G.tris[i_])
                       for i_ in G.near(x, y, 20)):
                continue
            # from 6u under the step: the cut piece below keeps a 2u half-slab, which must stay climbable
            boxes.append(((x - half, y - half, z + step_h - 6.0), (x + half, y + half, z + top)))
    if not boxes:
        return tris, tags, {"routes": len(segs), "blocked_samples": 0, "tris_cut": 0}
    B = flgeom.TriGrid([((lo[0], lo[1], lo[2]), (hi[0], lo[1], lo[2]), (hi[0], hi[1], hi[2])) for lo, hi in boxes])
    out_t, out_f, cut = [], [], 0
    for t, f in zip(tris, tags):
        n_ = flclear_normal(t)
        edge = False
        if n_ is not None and abs(n_[2]) < 0.7:
            # a wall with nothing under its far side bounds the level: never cut (a hedge along the north lane, cut
            # for the route beside it, let the walk out over the void)
            c_ = [sum(v[k] for v in t) / 3 for k in range(3)]
            hl_ = math.hypot(n_[0], n_[1]) or 1.0
            zlo_ = min(v[2] for v in t)
            for sg in (1.0, -1.0):
                px, py = c_[0] + sg * n_[0] / hl_ * 24.0, c_[1] + sg * n_[1] / hl_ * 24.0
                if G.ground(px, py, zlo_ + 48.0, zlo_ - 2048.0) is None:
                    edge = True
                    break
        flat = n_ is not None and abs(n_[2]) >= 0.7
        if flat:
            # a flat piece is a floor - never cut - unless it hangs as a CEILING 60-96u over a route's floor (a lintel
            # Frontline's 86u body walks under and MOHAA's 94u one does not)
            zmin_ = min(v[2] for v in t)
            c2 = [sum(v[k] for v in t) / 3 for k in range(2)]
            flat = not any(lo[2] + 28.0 <= zmin_ <= hi[2] and lo[0] <= c2[0] <= hi[0] and lo[1] <= c2[1] <= hi[1]
                           for lo, hi in (boxes[j] for j in B.near(c2[0], c2[1], half)))
        if keep(f) or edge or n_ is None or flat:
            # the level's boundaries are never cut, and no floor is: a route on a lower level cut holes into the floor
            # of the level above it (walk audit: fall-outs in the north lane over the jeep road)
            out_t.append(t)
            out_f.append(f)
            continue
        c = [sum(v[k] for v in t) / 3 for k in range(3)]
        r = max(math.dist(t[0], t[1]), math.dist(t[1], t[2]), math.dist(t[2], t[0]))
        polys = [list(t)]
        hit = False
        for j in B.near(c[0], c[1], r + half):
            lo, hi = boxes[j]
            if max(v[2] for v in t) < lo[2] or min(v[2] for v in t) > hi[2]:
                continue
            nxt = []
            for poly in polys:
                if all(lo[k] <= max(v[k] for v in poly) and min(v[k] for v in poly) <= hi[k] for k in range(3)):
                    pieces = flclear.subtract_box(poly, lo, hi)
                    if len(pieces) != 1 or pieces[0] != poly:
                        hit = True
                    nxt += pieces
                else:
                    nxt.append(poly)
            polys = nxt
        if not hit:
            out_t.append(t)
            out_f.append(f)
            continue
        cut += 1
        for poly in polys:
            if len(poly) < 3 or flclear._area(poly) < 1.0:
                continue
            for k in range(1, len(poly) - 1):
                out_t.append((tuple(poly[0]), tuple(poly[k]), tuple(poly[k + 1])))
                out_f.append(f)
    return out_t, out_f, {"routes": len(segs), "blocked_samples": len(boxes), "tris_cut": cut}

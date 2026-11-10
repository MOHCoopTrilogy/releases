#!/usr/bin/env python3
"""Headroom normalisation for converted collision (our code; runs on the player's PC inside the converter).

Frontline's player is smaller than MOHAA's: its crouch fits a ~49u crawl hole and its stand fits a ~86u doorway (at
the converter's 48 u/m), while the MOHAA player box is 30 wide and 54u crouched / 94u standing (bg_pmove.cpp
PM_CheckDuck, protocol >= MOHTA). The user's playtest (2026-11-10): "you can't crouch through holes in the walls" -
every crawl passage of 1_1 measured 46-50u of clearance, so only a prone player got through.

This pass finds every LOW CEILING over a walkable floor from the collision mesh alone (vertical column samples on an
8u grid: a near-horizontal floor triangle, then the next near-horizontal triangle above it):
    gap in [crawl_min, crawl_to)   -> a crawl passage: carve the collision between floor+carve_lo and floor+crawl_to
                                      and put a thin nodraw cap at floor+crawl_to (so it stays a crouch passage -
                                      nobody stands up inside the wall)
    gap in [door_min, door_to)     -> a doorway/beam the Frontline player walked under upright: carve up to door_to
                                      and cap there
Carving = every collision triangle minus the carve boxes (exact convex-polygon subtraction), so only collision changes;
the drawn geometry is untouched. The boxes reach `margin` past the low cells so the faces of the lintel above the
opening are carved too. Floors are never touched (the band starts above the step height).
"""
import math

import numpy as np

DEFAULTS = {"cell": 8.0, "crawl_min": 24.0, "crawl_to": 60.0, "door_min": 78.0, "door_to": 98.0,
            "carve_lo": 22.0, "margin": 12.0, "floor_nz": 0.7, "ceil_nz": 0.3, "slab": 2.0}


def _tri_columns(tris, cell):
    """every (column, z, |nz|, tri) where a near-horizontal-ish triangle covers an 8u column centre"""
    cols, zs, nzs, ids = [], [], [], []
    for t, (a, b, c) in enumerate(tris):
        a, b, c = np.asarray(a), np.asarray(b), np.asarray(c)
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln < 1e-9 or abs(n[2]) / ln < 0.3:
            continue
        lo = np.minimum(np.minimum(a, b), c)
        hi = np.maximum(np.maximum(a, b), c)
        ix = np.arange(math.floor(lo[0] / cell), math.floor(hi[0] / cell) + 1)
        iy = np.arange(math.floor(lo[1] / cell), math.floor(hi[1] / cell) + 1)
        if len(ix) * len(iy) > 400000:
            continue
        gx, gy = np.meshgrid(ix, iy)
        px = (gx.ravel() + 0.5) * cell
        py = (gy.ravel() + 0.5) * cell
        # barycentric inside test in xy
        v0 = b[:2] - a[:2]
        v1 = c[:2] - a[:2]
        d = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(d) < 1e-9:
            continue
        wx, wy = px - a[0], py - a[1]
        u = (wx * v1[1] - v1[0] * wy) / d
        v = (v0[0] * wy - wx * v0[1]) / d
        k = (u >= 0) & (v >= 0) & (u + v <= 1)
        if not k.any():
            continue
        z = a[2] + u[k] * (b[2] - a[2]) + v[k] * (c[2] - a[2])
        cols.append(np.stack([gx.ravel()[k], gy.ravel()[k]], 1))
        zs.append(z)
        nzs.append(np.full(k.sum(), n[2] / ln))       # signed: the converter's wound collision faces outward
        ids.append(np.full(k.sum(), t))
    if not cols:
        return None
    return np.concatenate(cols), np.concatenate(zs), np.concatenate(nzs), np.concatenate(ids)


def low_cells(tris, o):
    """{(ix, iy): (floor_z, top_z_wanted, kind)} for every column with a low ceiling over a walkable floor"""
    cell = o["cell"]
    r = _tri_columns(tris, cell)
    if r is None:
        return {}
    col, z, nz, _ids = r
    order = np.lexsort((z, col[:, 1], col[:, 0]))
    col, z, nz = col[order], z[order], nz[order]
    same = (col[1:, 0] == col[:-1, 0]) & (col[1:, 1] == col[:-1, 1])
    gap = z[1:] - z[:-1] - 2 * o["slab"]
    out = {}
    # a walkable floor facing UP, then a ceiling facing DOWN (stair treads and table tops face up: never a ceiling)
    for i in np.nonzero(same & (nz[:-1] >= o["floor_nz"]) & (nz[1:] <= -o["ceil_nz"]))[0]:
        g = gap[i]
        key = (int(col[i, 0]), int(col[i, 1]))
        if o["crawl_min"] <= g < o["crawl_to"]:
            kind, top = "crawl", z[i] + o["slab"] + o["crawl_to"]
        elif o["door_min"] <= g < o["door_to"]:
            kind, top = "door", z[i] + o["slab"] + o["door_to"]
        else:
            continue
        prev = out.get(key)
        if prev is None or z[i] > prev[0]:
            out[key] = (float(z[i]) + o["slab"], float(top), kind)
    return out


def merge_boxes(cells, o):
    """runs of cells in x with the same (floor band, top, kind) -> boxes; then rows merged in y"""
    cell = o["cell"]
    q = {}
    for (ix, iy), (fz, top, kind) in cells.items():
        q.setdefault((round(fz / 4), round(top / 4), kind), []).append((ix, iy))
    boxes = []
    for (fq, tq, kind), cs in sorted(q.items()):
        rows = {}
        for ix, iy in sorted(cs):
            rows.setdefault(iy, []).append(ix)
        runs = []
        for iy in sorted(rows):
            xs = sorted(rows[iy])
            s = p = xs[0]
            for x in xs[1:] + [None]:
                if x is not None and x == p + 1:
                    p = x
                    continue
                runs.append((s, p, iy))
                if x is not None:
                    s = p = x
        # merge identical x-runs on consecutive rows
        open_ = {}
        for s, e, iy in sorted(runs, key=lambda r: (r[0], r[1], r[2])):
            k = (s, e)
            if k in open_ and open_[k][1] == iy - 1:
                open_[k][1] = iy
            else:
                if k in open_:
                    boxes.append((s, e, open_[k][0], open_[k][1], fq * 4.0, tq * 4.0, kind))
                open_[k] = [iy, iy]
        for (s, e), (y0, y1) in open_.items():
            boxes.append((s, e, y0, y1, fq * 4.0, tq * 4.0, kind))
    out = []
    for s, e, y0, y1, fz, top, kind in boxes:
        out.append({"lo": (s * cell, y0 * cell, fz), "hi": ((e + 1) * cell, (y1 + 1) * cell, top), "kind": kind})
    return out


def _split(poly, n, d):
    """poly (list of xyz) split by plane n.p = d -> (inside n.p<=d, outside)"""
    ins, out = [], []
    m = len(poly)
    for i in range(m):
        p, q = poly[i], poly[(i + 1) % m]
        dp = n[0] * p[0] + n[1] * p[1] + n[2] * p[2] - d
        dq = n[0] * q[0] + n[1] * q[1] + n[2] * q[2] - d
        if dp <= 0:
            ins.append(p)
        if dp >= 0:
            out.append(p)
        if (dp < 0 < dq) or (dq < 0 < dp):
            t = dp / (dp - dq)
            x = (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]), p[2] + t * (q[2] - p[2]))
            ins.append(x)
            out.append(x)
    return (ins if len(ins) >= 3 else None), (out if len(out) >= 3 else None)


def subtract_box(poly, lo, hi):
    """convex polygon minus an axis-aligned box -> list of convex polygons (outside parts)"""
    planes = [((1, 0, 0), hi[0]), ((-1, 0, 0), -lo[0]), ((0, 1, 0), hi[1]), ((0, -1, 0), -lo[1]),
              ((0, 0, 1), hi[2]), ((0, 0, -1), -lo[2])]
    pieces = []
    cur = poly
    for n, d in planes:
        ins, out = _split(cur, n, d)
        if out:
            pieces.append(out)
        if not ins:
            return pieces
        cur = ins
    return pieces          # cur (inside the box) is dropped


def _area(poly):
    a = np.zeros(3)
    p0 = np.asarray(poly[0])
    for i in range(1, len(poly) - 1):
        a += np.cross(np.asarray(poly[i]) - p0, np.asarray(poly[i + 1]) - p0)
    return np.linalg.norm(a) / 2


def _seg_hits(grid_tris, idx, a, b):
    """True when segment a-b crosses any of the triangles idx (Moeller-Trumbore)"""
    d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    for i in idx:
        v0, v1, v2 = grid_tris[i]
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        p = (d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0])
        det = e1[0] * p[0] + e1[1] * p[1] + e1[2] * p[2]
        if abs(det) < 1e-9:
            continue
        inv = 1.0 / det
        t = (a[0] - v0[0], a[1] - v0[1], a[2] - v0[2])
        u = (t[0] * p[0] + t[1] * p[1] + t[2] * p[2]) * inv
        if u < 0 or u > 1:
            continue
        q = (t[1] * e1[2] - t[2] * e1[1], t[2] * e1[0] - t[0] * e1[2], t[0] * e1[1] - t[1] * e1[0])
        v = (d[0] * q[0] + d[1] * q[1] + d[2] * q[2]) * inv
        if v < 0 or u + v > 1:
            continue
        f = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) * inv
        if 0 <= f <= 1:
            return True
    return False


def passages(cells, tris, o):
    """keep only low cells that belong to a PASSAGE: a group of low cells (connected where nothing stands between
    their centres at crawl height) that opens onto standing room (a neighbour column with no low ceiling, reached
    without crossing a face, at the same floor +-18). Low cells enclosed by faces - the inside of a hollow wall under
    a moulding, the inside of a crate - are dropped: carving them cut a slot through the wall (measured: a 48u slot
    beside 1_1's crawl hole)."""
    import collections
    import flgeom
    cell = o["cell"]
    grid = flgeom.TriGrid(tris, cell=64.0)

    def blocked(k1, k2, z):
        a = ((k1[0] + 0.5) * cell, (k1[1] + 0.5) * cell, z)
        b = ((k2[0] + 0.5) * cell, (k2[1] + 0.5) * cell, z)
        return _seg_hits(grid.tris, grid.near((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, cell), a, b)

    par = {k: k for k in cells}

    def f(k):
        while par[k] != k:
            par[k] = par[par[k]]
            k = par[k]
        return k
    opens = collections.Counter()
    for k, (fz, top, kind) in cells.items():
        z = fz + 30.0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (k[0] + dx, k[1] + dy)
            if n in cells:
                if abs(cells[n][0] - fz) < 18 and not blocked(k, n, z):
                    par[f(k)] = f(n)
            elif not blocked(k, n, z) and not blocked(k, n, fz + 10.0):
                # a column outside the low area, open at crawl height: standing room if it has floor at this level
                g = grid.ground((n[0] + 0.5) * cell, (n[1] + 0.5) * cell, fz + 18, fz - 18)
                if g is not None:
                    opens[k] += 1
    comp_open = collections.Counter()
    for k in cells:
        comp_open[f(k)] += opens[k]
    return {k: v for k, v in cells.items() if comp_open[f(k)] > 0}


def _zs_at(grid, x, y):
    """z of every triangle of grid covering (x, y)"""
    out = []
    for i in grid.near(x, y, 1):
        a, b, c = grid.tris[i]
        v0 = (b[0] - a[0], b[1] - a[1])
        v1 = (c[0] - a[0], c[1] - a[1])
        d = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(d) < 1e-9:
            continue
        wx, wy = x - a[0], y - a[1]
        u = (wx * v1[1] - v1[0] * wy) / d
        v = (v0[0] * wy - wx * v0[1]) / d
        if u >= 0 and v >= 0 and u + v <= 1:
            out.append(a[2] + u * (b[2] - a[2]) + v * (c[2] - a[2]))
    return out


def _ray(grid, a, b):
    """fraction along a->b to the first triangle of grid (1.0 = none)"""
    d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    best = 1.0
    for i in grid.near((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(d[0]) + abs(d[1]) + 1):
        v0, v1, v2 = grid.tris[i]
        e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
        p = (d[1] * e2[2] - d[2] * e2[1], d[2] * e2[0] - d[0] * e2[2], d[0] * e2[1] - d[1] * e2[0])
        det = e1[0] * p[0] + e1[1] * p[1] + e1[2] * p[2]
        if abs(det) < 1e-9:
            continue
        inv = 1.0 / det
        t = (a[0] - v0[0], a[1] - v0[1], a[2] - v0[2])
        u = (t[0] * p[0] + t[1] * p[1] + t[2] * p[2]) * inv
        if u < 0 or u > 1:
            continue
        q = (t[1] * e1[2] - t[2] * e1[1], t[2] * e1[0] - t[0] * e1[2], t[0] * e1[1] - t[1] * e1[0])
        v = (d[0] * q[0] + d[1] * q[1] + d[2] * q[2]) * inv
        if v < 0 or u + v > 1:
            continue
        f = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) * inv
        if 0 <= f < best:
            best = f
    return best


def visible_ceiling(cells, render_tris, o):
    """drop low cells that lie INSIDE a drawn wall: drawn faces within 48u on both sides along x or along y at crawl
    height. The collision of a lintel or moulding runs on inside the wall past the drawn opening, and carving there
    cut a slot through the wall beside 1_1's crawl hole. Low cells under an undrawn (invisible) slab stay: they are
    open around, and carving them removes an invisible obstacle on the town route."""
    import flgeom
    if not render_tris:
        return cells
    cell = o["cell"]
    keep = {}
    rg = flgeom.TriGrid(render_tris, cell=64.0)
    R = 40.0
    for k, (fz, top, kind) in cells.items():
        x, y, z = (k[0] + 0.5) * cell, (k[1] + 0.5) * cell, fz + 30.0
        inside = False
        for ax, ay in ((1, 0), (0, 1)):
            d1 = _ray(rg, (x, y, z), (x + ax * R, y + ay * R, z)) * R
            d2 = _ray(rg, (x, y, z), (x - ax * R, y - ay * R, z)) * R
            if d1 + d2 < 48:
                inside = True
                break
        if not inside:
            keep[k] = (fz, top, kind)
    return keep


def normalise(tris, opts=None, tags=None, render_tris=None):
    """tris: [(a, b, c)] in MOHAA units, WOUND the converter's way (outward faces: floors face up). Returns (new_tris, caps[(lo, hi)], report)."""
    o = dict(DEFAULTS)
    o.update(opts or {})
    cells = low_cells(tris, o)
    n_low = len(cells)
    cells = visible_ceiling(cells, render_tris, o)
    n_vis = len(cells)
    cells = passages(cells, tris, o)
    boxes = merge_boxes(cells, o)
    m = o["margin"]
    carve = [((b["lo"][0] - m, b["lo"][1] - m, b["lo"][2] + o["carve_lo"] - o["slab"]),
              (b["hi"][0] + m, b["hi"][1] + m, b["hi"][2] + o["slab"] + 0.5)) for b in boxes]
    # bucket carve boxes for the overlap test
    out = []
    otags = []
    touched = 0
    tags = tags if tags is not None else [None] * len(tris)
    for (a, b, c), tg in zip(tris, tags):
        n = np.cross(np.subtract(b, a), np.subtract(c, a))
        ln = np.linalg.norm(n)
        if ln > 1e-9 and n[2] / ln >= o["floor_nz"]:
            out.append((a, b, c))          # floors / treads / table tops are never carved
            otags.append(tg)
            continue
        lo = [min(a[k], b[k], c[k]) for k in range(3)]
        hi = [max(a[k], b[k], c[k]) for k in range(3)]
        hit = [bx for bx in carve if all(lo[k] < bx[1][k] and hi[k] > bx[0][k] for k in range(3))]
        if not hit:
            out.append((a, b, c))
            otags.append(tg)
            continue
        polys = [[tuple(a), tuple(b), tuple(c)]]
        for blo, bhi in hit:
            nxt = []
            for p in polys:
                nxt += subtract_box(p, blo, bhi)
            polys = nxt
        touched += 1
        for p in polys:
            if _area(p) < 0.5:
                continue
            for i in range(1, len(p) - 1):
                out.append((p[0], p[i], p[i + 1]))
                otags.append(tg)
    caps = [((b["lo"][0], b["lo"][1], b["hi"][2]), (b["hi"][0], b["hi"][1], b["hi"][2] + 4.0)) for b in boxes]
    rep = {"low_cells": n_low, "drawn_ceiling_cells": n_vis, "passage_cells": len(cells), "crawl_cells": sum(1 for v in cells.values() if v[2] == "crawl"),
           "door_cells": sum(1 for v in cells.values() if v[2] == "door"), "boxes": len(boxes),
           "tris_carved": touched, "tris_in": len(tris), "tris_out": len(out)}
    rep["tags"] = otags
    return out, caps, rep


def ledge_ramps(tris, opts=None):
    """[flpolish] Frontline's player steps over curbs, rubble lips and kerbs up to ~0.7 m (34u at 48 u/m); MOHAA's
    STEPSIZE is 18, so every 19-34u lip stopped a walking player dead ("you get caught on objects while moving").
    For every 8u column whose walkable floor meets a neighbour's floor 18-34u higher (and the neighbour has no floor
    at the low level - a real lip, not an overhang), a thin sloped clip strip is laid on the low side: from the low
    floor `run`x the rise out, up to the lip - under 45 degrees, so it is walkable, and the player glides over
    (the stock maps' clip-ramp recipe). Returns [(a, b, c)] ramp triangles (one quad per lip cell) and a report."""
    o = dict(DEFAULTS)
    o.update({"lip_min": 18.5, "lip_max": 34.0, "run": 1.25})
    o.update(opts or {})
    cell = o["cell"]
    r = _tri_columns(tris, cell)
    if r is None:
        return [], {"lip_cells": 0}
    col, z, nz, _ids = r
    floors = {}
    order = np.lexsort((z, col[:, 1], col[:, 0]))
    col, z, nz = col[order], z[order], nz[order]
    for i in range(len(z)):
        if nz[i] < o["floor_nz"]:
            continue
        key = (int(col[i, 0]), int(col[i, 1]))
        # headroom above this floor in the same column (next surface)
        top = z[i + 1] if i + 1 < len(z) and col[i + 1, 0] == col[i, 0] and col[i + 1, 1] == col[i, 1] else 1e9
        if top - z[i] < 60:
            continue
        floors.setdefault(key, []).append(float(z[i]))
    out = []
    n = 0
    for (ix, iy), fl in floors.items():
        for f1 in fl:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nb = floors.get((ix + dx, iy + dy))
                if not nb:
                    continue
                if any(abs(f - f1) < 6 for f in nb):
                    continue
                hi = [f for f in nb if o["lip_min"] < f - f1 <= o["lip_max"]]
                if not hi:
                    continue
                f2 = min(hi)
                rise = f2 - f1
                run = rise * o["run"]
                # the lip line: the shared cell edge; the strip runs back into this column's side
                ex = (ix + (1 if dx > 0 else 0)) * cell if dx else None
                ey = (iy + (1 if dy > 0 else 0)) * cell if dy else None
                if dx:
                    x_top, x_bot = ex, ex - dx * run
                    y0, y1 = iy * cell, (iy + 1) * cell
                    a, b = (x_bot, y0, f1), (x_bot, y1, f1)
                    c, d = (x_top, y1, f2 + 1), (x_top, y0, f2 + 1)
                else:
                    y_top, y_bot = ey, ey - dy * run
                    x0, x1 = ix * cell, (ix + 1) * cell
                    a, b = (x0, y_bot, f1), (x1, y_bot, f1)
                    c, d = (x1, y_top, f2 + 1), (x0, y_top, f2 + 1)
                # wound so the ramp faces up
                tri1, tri2 = (a, b, c), (a, c, d)
                nzz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                if nzz < 0:
                    tri1, tri2 = (a, c, b), (a, d, c)
                out += [tri1, tri2]
                n += 1
    return out, {"lip_cells": n, "ramp_tris": len(out)}

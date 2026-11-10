#!/usr/bin/env python3
"""Edges of the world (our code; runs inside the converter on the player's PC).

Frontline streams its level in cells and leaves no floor at all past the edges of the playable area - the ground
simply ends. Its own player never got there; once the invisible volumes and the crawl-hole headroom were fixed
(flconvert COLL_VOLUME, flclear.py) a MOHAA player could walk off such an edge and fall out of the world (geoaudit:
340 void falls along the town's west edge). Every boundary edge of a walkable floor triangle whose outside has no
collision at all below it (2048u) gets a thin clip wall (nodraw, the player's and the AI's) 160u high - out of jump
reach - so the edge holds like the stock maps' clip brushes do. Ledges with ground below are left open.
"""
import math


def _key(p):
    return (round(p[0], 1), round(p[1], 1), round(p[2], 1))


def walls(tris, grid, floor_nz=0.7, probe=20.0, height=160.0, depth=2048.0):
    """tris: wound collision [(a, b, c)] (floors face up); grid: flgeom.TriGrid over the same collision.
    Returns ([(a, b, c)] wall triangles, report)."""
    edges = {}
    floors = []
    for t in tris:
        a, b, c = t
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if ln < 1e-9 or n[2] / ln < floor_nz:
            continue
        fi = len(floors)
        floors.append(t)
        for p, q in ((a, b), (b, c), (c, a)):
            k = tuple(sorted((_key(p), _key(q))))
            edges.setdefault(k, []).append(fi)
    out = []
    n_edge = 0
    for (p, q), fs in sorted(edges.items()):
        if len(fs) != 1:
            continue
        t = floors[fs[0]]
        cx = sum(v[0] for v in t) / 3
        cy = sum(v[1] for v in t) / 3
        mx, my, mz = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2
        ex, ey = q[0] - p[0], q[1] - p[1]
        el = math.hypot(ex, ey)
        if el < 2:
            continue
        ox, oy = -ey / el, ex / el
        if ox * (mx - cx) + oy * (my - cy) < 0:
            ox, oy = -ox, -oy
        # probe just outside the edge, at both ends and the middle: any collision below within `depth` = not the void
        void = True
        for f in (0.15, 0.5, 0.85):
            px = p[0] + (q[0] - p[0]) * f + ox * probe
            py = p[1] + (q[1] - p[1]) * f + oy * probe
            pz = p[2] + (q[2] - p[2]) * f
            if grid.ground(px, py, pz + 24, pz - depth) is not None:
                void = False
                break
            if any(True for _ in grid.near(px, py, 4)) and _wall_near(grid, px, py, pz):
                void = False
                break
        if not void:
            continue
        n_edge += 1
        a = (p[0], p[1], p[2] - 8)
        b = (q[0], q[1], q[2] - 8)
        c = (q[0], q[1], q[2] + height)
        d = (p[0], p[1], p[2] + height)
        out += [(a, b, c), (a, c, d)]
    return out, {"void_edges": n_edge, "wall_tris": len(out), "floor_tris": len(floors)}


def _wall_near(grid, x, y, z):
    """a vertical collision face already stands at the probe (a wall on the edge): no extra clip needed"""
    for i in grid.near(x, y, 6):
        a, b, c = grid.tris[i]
        if max(a[2], b[2], c[2]) < z + 16 or min(a[2], b[2], c[2]) > z + 60:
            continue
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if ln < 1e-9 or abs(n[2]) / ln > 0.3:
            continue
        d = abs(n[0] * (x - a[0]) + n[1] * (y - a[1]) + n[2] * (z - a[2])) / ln
        if d < 8:
            return True
    return False

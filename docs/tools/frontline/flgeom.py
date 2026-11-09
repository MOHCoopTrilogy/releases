#!/usr/bin/env python3
"""Geometry helpers for the converter (our own code): a triangle grid over the converted collision mesh,
a player-box vs triangle overlap test (separating axes, Akenine-Moeller), a deterministic "nearest free spot"
search for placements, and a 2.5D occluder ray test used by the visibility build.
"""
import math

PLAYER_HALF = 16.0          # MOHAA player box is 30 wide; 1u of margin
PLAYER_H = 72.0


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def tri_box(c, h, v0, v1, v2):
    """True when triangle (v0,v1,v2) overlaps the AABB centre c, half-size h (3-tuple)."""
    a = _sub(v0, c)
    b = _sub(v1, c)
    d = _sub(v2, c)
    for k in range(3):
        if min(a[k], b[k], d[k]) > h[k] or max(a[k], b[k], d[k]) < -h[k]:
            return False
    e = (_sub(b, a), _sub(d, b), _sub(a, d))
    n = _cross(e[0], e[1])
    r = h[0] * abs(n[0]) + h[1] * abs(n[1]) + h[2] * abs(n[2])
    if abs(_dot(n, a)) > r:
        return False
    axes = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    for ed in e:
        for ax in axes:
            L = _cross(ax, ed)
            if L == (0.0, 0.0, 0.0):
                continue
            p = (_dot(L, a), _dot(L, b), _dot(L, d))
            r = h[0] * abs(L[0]) + h[1] * abs(L[1]) + h[2] * abs(L[2])
            if min(p) > r or max(p) < -r:
                return False
    return True


class TriGrid:
    def __init__(self, tris, cell=256.0):
        self.cell = cell
        self.tris = tris
        self.g = {}
        for i, (a, b, c) in enumerate(tris):
            x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
            y0, y1 = min(a[1], b[1], c[1]), max(a[1], b[1], c[1])
            for gx in range(int(x0 // cell), int(x1 // cell) + 1):
                for gy in range(int(y0 // cell), int(y1 // cell) + 1):
                    self.g.setdefault((gx, gy), []).append(i)

    def near(self, x, y, r):
        out = set()
        for gx in range(int((x - r) // self.cell), int((x + r) // self.cell) + 1):
            for gy in range(int((y - r) // self.cell), int((y + r) // self.cell) + 1):
                out.update(self.g.get((gx, gy), ()))
        return sorted(out)

    def ground(self, x, y, ztop, zbot):
        """highest walkable-ish triangle height under (x,y) between zbot and ztop, else None"""
        best = None
        for i in self.near(x, y, 1):
            a, b, c = self.tris[i]
            n = _cross(_sub(b, a), _sub(c, a))
            if abs(n[2]) < 1e-9:
                continue
            l = math.sqrt(_dot(n, n))
            if abs(n[2]) / l < 0.5:
                continue
            def s(p1, p2, p3):
                return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
            d1, d2, d3 = s((x, y), a, b), s((x, y), b, c), s((x, y), c, a)
            if (d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0):
                continue
            z = a[2] - (n[0] * (x - a[0]) + n[1] * (y - a[1])) / n[2]
            if zbot <= z <= ztop and (best is None or z > best):
                best = z
        return best

    def box_free(self, x, y, zfloor):
        """player box standing on zfloor (feet lifted 20u, i.e. above a step) clear of every triangle"""
        c = (x, y, zfloor + 20 + (PLAYER_H - 20) / 2)
        h = (PLAYER_HALF, PLAYER_HALF, (PLAYER_H - 20) / 2)
        for i in self.near(x, y, PLAYER_HALF + 2):
            if tri_box(c, h, *self.tris[i]):
                return False
        return True

    def free_spot(self, p, max_r=96, step=8):
        """deterministic nearest free standing spot around p (x,y,z ~ ground); returns (spot, moved)"""
        x0, y0, z0 = p
        g = self.ground(x0, y0, z0 + 48, z0 - 96)
        zf = g if g is not None else z0
        if self.box_free(x0, y0, zf):
            return (x0, y0, zf), 0.0
        for r in range(step, max_r + 1, step):
            n = max(8, int(2 * math.pi * r / step))
            for k in range(n):
                a = 2 * math.pi * k / n
                x, y = x0 + r * math.cos(a), y0 + r * math.sin(a)
                g = self.ground(x, y, zf + 24, zf - 48)
                if g is None:
                    continue
                if self.box_free(x, y, g):
                    return (round(x), round(y), g), float(r)
        return (x0, y0, zf), -1.0

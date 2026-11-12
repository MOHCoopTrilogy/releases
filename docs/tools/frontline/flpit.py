"""flpit - floorless pockets inside the level, closed with a flat lid of the original's own void colour.

Frontline builds most houses as shells: walls, roof, window openings, and NO ground floor (its player never walks in).
Through a window the original shows its sky box there, and below the horizon that box is one flat dark colour
(TRACE_sky_fog.md: the -z face and the lower band of the side faces, about 83 81 76). The converter draws a cobble
skirt and a cobble ground 512u under the level so a look over the level's EDGE lands on ground; through a window into
a floorless house the same fill read as "under the map" (user, 2026-11-12, Sealed Orders, window by the jeep road).

A pocket = cells whose lowest horizontal drawn face is well above the ground just outside (or that have none), cut
off from the level's outside by drawn walls and lower ground. Each pocket gets a render-only lid in the void colour a
little under the surrounding ground, so a look through a window meets what the original showed: flat dark. Pockets
that reach the edge of the grid (the world outside the level, through any gap) are left alone - the edge keeps its
skirt and ground. Our code; it reads only the triangles the converter already has.
"""
import math

import numpy as np


def _cells_of_tri(t, x0, y0, C, nx, ny):
    """cell indexes (ix, iy) whose centre lies inside the xy projection of triangle t, and the plane z there"""
    xs, ys = t[:, 0], t[:, 1]
    i0 = max(0, int(math.floor((xs.min() - x0) / C)))
    i1 = min(nx - 1, int(math.floor((xs.max() - x0) / C)))
    j0 = max(0, int(math.floor((ys.min() - y0) / C)))
    j1 = min(ny - 1, int(math.floor((ys.max() - y0) / C)))
    if i1 < i0 or j1 < j0:
        return None
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
    px = x0 + (ii + 0.5) * C
    py = y0 + (jj + 0.5) * C
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-9:
        return None
    l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
    l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
    l3 = 1.0 - l1 - l2
    k = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
    if not k.any():
        return None
    return ii[k], jj[k], (l1 * az + l2 * bz + l3 * cz)[k]


def _minfilter(a, r):
    out = a.copy()
    nx, ny = a.shape
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            s = np.full_like(a, np.inf)
            s[max(0, dx):nx + min(0, dx), max(0, dy):ny + min(0, dy)] = \
                a[max(0, -dx):nx + min(0, -dx), max(0, -dy):ny + min(0, -dy)]
            np.minimum(out, s, out=out)
    return out


def lids(tris, cell=32.0, rise=96.0, look=8, reach=3, drop=4.0, under=2):
    """tris: iterable of 3x3 point lists (the drawn level). Returns (rects, stats): rects = [(z, x0, y0, x1, y1)]"""
    T = np.asarray(list(tris), np.float64).reshape(-1, 3, 3)
    st = {"pockets": 0, "pocket_cells": 0, "rejected_open": 0}
    if not len(T):
        return [], st
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-9
    nz = np.zeros(len(T))
    nz[ok] = np.abs(n[ok, 2]) / ln[ok]
    C = float(cell)
    x0, y0 = T[:, :, 0].min() - 2 * C, T[:, :, 1].min() - 2 * C
    nx = int((T[:, :, 0].max() + 2 * C - x0) // C) + 1
    ny = int((T[:, :, 1].max() + 2 * C - y0) // C) + 1
    L = np.full((nx, ny), np.inf)
    for t in T[ok & (nz >= 0.7)]:
        r = _cells_of_tri(t, x0, y0, C, nx, ny)
        if r is not None:
            ii, jj, z = r
            np.minimum.at(L, (ii, jj), z)
    # the lowest drawn non-wall surface anywhere in a cell (sloped banks too, and faces smaller than a cell: their
    # corners, edge midpoints and centroid count): the lid never covers any of it
    Lany = L.copy()
    for t in T[ok & (nz >= 0.3)]:
        r = _cells_of_tri(t, x0, y0, C, nx, ny)
        if r is not None:
            ii, jj, z = r
            np.minimum.at(Lany, (ii, jj), z)
        pts = np.vstack([t, (t + np.roll(t, 1, 0)) / 2.0, t.mean(0, keepdims=True)])
        ii = np.clip(((pts[:, 0] - x0) // C).astype(int), 0, nx - 1)
        jj = np.clip(((pts[:, 1] - y0) // C).astype(int), 0, ny - 1)
        np.minimum.at(Lany, (ii, jj), pts[:, 2])
    # walls: every cell a standing face passes through (its footprint is a segment; its edges sampled every 8u)
    wall = np.zeros((nx, ny), bool)
    for t in T[ok & (nz < 0.3)]:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            m = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // 8.0))
            s = np.linspace(0.0, 1.0, m + 1)
            ii = ((a[0] + (b[0] - a[0]) * s - x0) // C).astype(int)
            jj = ((a[1] + (b[1] - a[1]) * s - y0) // C).astype(int)
            wall[ii, jj] = True
    # 'raised' = the lowest drawn floor is well above the lowest one within `look` cells: a house up to ~500u across
    # (walls, roof, no ground floor) is raised over its whole width
    near = _minfilter(L, look)
    high = np.isinf(L) | (L >= near + rise)
    comp = high & ~wall
    seen = np.zeros((nx, ny), bool)
    rects = []
    for si, sj in zip(*np.nonzero(comp)):
        if seen[si, sj]:
            continue
        cells, stack, edge = [], [(si, sj)], False
        seen[si, sj] = True
        while stack:
            i, j = stack.pop()
            cells.append((i, j))
            if i == 0 or j == 0 or i == nx - 1 or j == ny - 1:
                edge = True
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p, q = i + di, j + dj
                if 0 <= p < nx and 0 <= q < ny and comp[p, q] and not seen[p, q]:
                    seen[p, q] = True
                    stack.append((p, q))
        if edge:
            st["rejected_open"] += 1
            continue
        # the ground around the pocket: lowest drawn floor within reach that is not part of a pocket
        ci = np.array(cells)
        mask = np.zeros((nx, ny), bool)
        mask[ci[:, 0], ci[:, 1]] = True
        ring = np.zeros_like(mask)
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                ring[max(0, dx):nx + min(0, dx), max(0, dy):ny + min(0, dy)] |= \
                    mask[max(0, -dx):nx + min(0, -dx), max(0, -dy):ny + min(0, -dy)]
        g = L[ring & ~high & np.isfinite(L)]
        if not len(g):
            st["rejected_open"] += 1
            continue
        z = float(g.min()) - drop
        # the lid runs on under the pocket's walls and the ground just outside them (`under` cells, hidden below that
        # ground): a wall whose foot stands a few units above the lid leaves a slit a look through the window passes
        # (the far wall of the jeep-road house: foot -174, ground -170)
        lid = mask.copy()
        for _ in range(under):
            g_ = lid.copy()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                g_[max(0, di):nx + min(0, di), max(0, dj):ny + min(0, dj)] |= \
                    lid[max(0, -di):nx + min(0, -di), max(0, -dj):ny + min(0, -dj)]
            lid = g_ & (mask | wall | np.isfinite(L))      # never out over open void
        # never above a drawn floor: a cell whose own lowest floor is near the lid keeps that floor
        lid &= ~(np.isfinite(Lany) & (Lany < z + 8.0))
        st["pockets"] += 1
        st["pocket_cells"] += int(lid.sum())
        for i in np.unique(np.nonzero(lid)[0]):
            col = lid[i]
            j = 0
            while j < ny:
                if col[j]:
                    k = j
                    while k + 1 < ny and col[k + 1]:
                        k += 1
                    rects.append((z, x0 + i * C, y0 + j * C, x0 + (i + 1) * C, y0 + (k + 1) * C))
                    j = k + 1
                else:
                    j += 1
    return rects, st

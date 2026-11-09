#!/usr/bin/env python3
"""Seam bridges for converted Frontline levels. Our own code.

Frontline's render mesh leaves hairline gaps between some neighbouring floor draws (on 1_1, ~20u between the
hedge-bed edge and the alley ground). On the console a dark clear colour hid them; in MOHAA the sky box shows
through and they read as bright white strips. A bridge is built only where all of these hold:
  - two FLAT render boundary edges (each used by exactly one triangle) of DIFFERENT draws face each other,
  - across a gap of 2..GAP units, within DZ in height and overlapping sideways,
  - the gap is in a walkable floor (collision within 24u), and each end of the bridge spans <= MAX_ACROSS,
  - and NOTHING is rendered across the gap from DZ above down to OPEN_BELOW below (a gap over water or a lower
    floor is a real gap and stays open).
The bridge is a quad between the two edges in the lower surface's shader, with that edge's UVs and colours.
Deterministic: inputs are walked in mesh/triangle order and every choice breaks ties by index."""
import math
from collections import defaultdict

import flgeom

GAP = 32.0
DZ = 10.0
FLAT = 0.8          # |normal z| above which a triangle edge counts as a floor edge
OPEN_BELOW = 200.0
MAX_ACROSS = 48.0


def _k(p):
    return (round(p[0] * 2), round(p[1] * 2), round(p[2] * 2))


def _affine_uv(a, b, c):
    """UV as an affine function of world x/y from one (near-flat) triangle; None when degenerate in x/y."""
    (x1, y1, _), (x2, y2, _), (x3, y3, _) = a[0], b[0], c[0]
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    if abs(det) < 1e-6:
        return None

    def solve(k):
        u1, u2, u3 = a[1][k], b[1][k], c[1][k]
        gx = ((u2 - u1) * (y3 - y1) - (u3 - u1) * (y2 - y1)) / det
        gy = ((u3 - u1) * (x2 - x1) - (u2 - u1) * (x3 - x1)) / det
        return gx, gy, u1 - gx * x1 - gy * y1
    su, sv = solve(0), solve(1)
    return lambda p: (su[0] * p[0] + su[1] * p[1] + su[2], sv[0] * p[0] + sv[1] * p[1] + sv[2])


def bridges(draws, on_floor=None, why=None):
    """draws: list of (shader_id, verts[(xyz, uv, nrm, rgba)], tris[(a,b,c)]) in final MOHAA coordinates.
    on_floor(x, y, z) -> True when walkable collision is near: only floor gaps are bridged (a seam on a roof
    or a ledge is never seen against the sky from below, and bridging it could only cover a real opening).
    -> list of (shader_id, verts, tris) bridge quads"""
    cnt = defaultdict(int)
    info = {}
    rtris = []
    for di, (sh, verts, tris) in enumerate(draws):
        for a, b, c in tris:
            A, B, C = verts[a][0], verts[b][0], verts[c][0]
            rtris.append((A, B, C))
            u = [B[i] - A[i] for i in range(3)]
            v = [C[i] - A[i] for i in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            flat = abs(n[2] / ln) > FLAT
            for i, j, r in ((a, b, c), (b, c, a), (c, a, b)):
                e = tuple(sorted((_k(verts[i][0]), _k(verts[j][0]))))
                cnt[e] += 1
                if flat and e not in info:
                    info[e] = (di, sh, verts[i], verts[j], verts[r][0], verts[r])
    bnd = sorted(e for e, n in cnt.items() if n == 1 and e in info)
    grid = defaultdict(list)
    for e in bnd:
        p, q = info[e][2][0], info[e][3][0]
        grid[(int(((p[0] + q[0]) / 2) // 64), int(((p[1] + q[1]) / 2) // 64))].append(e)
    rg = flgeom.TriGrid(rtris, cell=128.0)
    used = set()
    out = []
    for e in bnd:
        if e in used:
            continue
        di, sh, vp, vq, r, _vr = info[e]
        p, q = vp[0], vq[0]
        ex, ey = q[0] - p[0], q[1] - p[1]
        el = math.hypot(ex, ey)
        if el < 4:
            continue
        nx, ny = -ey / el, ex / el
        mx, my, mz = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2
        if (r[0] - mx) * nx + (r[1] - my) * ny > 0:
            nx, ny = -nx, -ny
        best = None
        gx, gy = int(mx // 64), int(my // 64)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for f in grid.get((gx + dx, gy + dy), ()):
                    if f == e or f in used or info[f][0] == di:
                        continue
                    a, b = info[f][2][0], info[f][3][0]
                    fx, fy, fz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2
                    d = (fx - mx) * nx + (fy - my) * ny
                    lat = abs(-(fx - mx) * ny + (fy - my) * nx)
                    if 2 < d < GAP and abs(fz - mz) < DZ and lat < max(el, 16):
                        cand = (d, lat, f)
                        if best is None or cand < best:
                            best = cand
        if best is None:
            if why is not None:
                why.append(('no_partner', mx, my, mz))
            continue
        d, _lat, f = best
        # open across the gap? (sample 3 points between the edge midpoints)
        a, b = info[f][2][0], info[f][3][0]
        fx, fy, fz = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2
        hole = True
        for t in (0.25, 0.5, 0.75):
            x, y, z = mx + (fx - mx) * t, my + (fy - my) * t, mz + (fz - mz) * t
            if rg.ground(x, y, z + DZ, z - OPEN_BELOW) is not None:
                hole = False
                break
        if not hole:
            if why is not None:
                why.append(('covered', mx, my, mz))
            continue
        if on_floor is not None and not on_floor((mx + fx) / 2, (my + fy) / 2, (mz + fz) / 2):
            if why is not None:
                why.append(('not_floor', mx, my, mz))
            continue
        # clip to the stretch where the two edges overlap along the seam, so each end of the bridge only spans
        # the gap; positions, UVs and colours are interpolated along both edges
        va, vb = info[f][2], info[f][3]

        def s_of(pt):
            return ((pt[0] - p[0]) * ex + (pt[1] - p[1]) * ey) / (el * el)
        sa, sb = s_of(va[0]), s_of(vb[0])
        if sa > sb:
            va, vb, sa, sb = vb, va, sb, sa
        s0, s1 = max(0.0, sa), min(1.0, sb)
        if (s1 - s0) * el < 4 or sb - sa < 1e-6:
            if why is not None:
                why.append(('no_overlap', mx, my, mz))
            continue

        def lerp(v1, v2, t):
            return (tuple(v1[0][i] + (v2[0][i] - v1[0][i]) * t for i in range(3)),
                    tuple(v1[1][i] + (v2[1][i] - v1[1][i]) * t for i in range(2)),
                    tuple(int(round(v1[3][i] + (v2[3][i] - v1[3][i]) * t)) for i in range(4)))
        e0, e1 = lerp(vp, vq, s0), lerp(vp, vq, s1)
        f0, f1 = lerp(va, vb, (s0 - sa) / (sb - sa)), lerp(va, vb, (s1 - sa) / (sb - sa))
        if math.dist(e0[0][:2], f0[0][:2]) > MAX_ACROSS or math.dist(e1[0][:2], f1[0][:2]) > MAX_ACROSS:
            if why is not None:
                why.append(('too_wide', mx, my, mz))
            continue          # a seam, not a span: both ends of the bridge stay short
        # shader and colours of the LOWER edge; its triangle's own UV mapping (affine in x/y) continues across
        # the gap, so the texture carries on instead of smearing one row of texels
        low_e = mz <= fz
        lsh = sh if low_e else info[f][1]
        n0, n1 = (e0, e1) if low_e else (f0, f1)
        quad = [e0[0], e1[0], f1[0], f0[0]]
        own = info[e] if low_e else info[f]
        uvmap = _affine_uv(own[2], own[3], own[5])
        uvs = [uvmap(pt) for pt in quad] if uvmap else [n0[1], n1[1], n1[1], n0[1]]
        cols = [n0[2], n1[2], n1[2], n0[2]]
        out.append((lsh, [(quad[i], uvs[i], (0.0, 0.0, 1.0), cols[i]) for i in range(4)], [(0, 1, 2), (0, 2, 3)]))
        used.add(e)
        used.add(f)
    return out

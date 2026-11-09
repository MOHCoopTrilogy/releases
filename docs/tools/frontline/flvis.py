#!/usr/bin/env python3
"""Occluder-based cluster visibility for converted maps (our own code; numpy).

Frontline levels are streets between solid buildings, so a 2.5D test is a good cull:
  occluders  = near-vertical collision triangles, as 2D segments with their own bottom/top height
  clusters   = the PVS grid cells (flbsp vis_cell), each with a floor height and a top height
  A sees B   when ANY sample ray from A's eye points (floor+70, and the cell's top for upper storeys)
             to B's target points (B floor .. B top) crosses no occluder at a height inside that occluder.
Conservative by sampling (5x5 points, 2 eye heights, 2 target heights); anything within NEAR is always
visible. Deterministic: fixed sample pattern, no randomness.
"""
import math

import numpy as np

NEAR = 1536.0


def occluders(tris, min_height=96.0):
    segs = []
    for a, b, c in tris:
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        l = math.sqrt(nx * nx + ny * ny + nz * nz)
        if l < 1e-6 or abs(nz) / l > 0.3:
            continue
        zs = (a[2], b[2], c[2])
        if max(zs) - min(zs) < min_height:
            continue
        pts = sorted((a, b, c), key=lambda p: (p[0] * ny - p[1] * nx))   # along the wall
        p0, p1 = pts[0], pts[-1]
        if math.hypot(p1[0] - p0[0], p1[1] - p0[1]) < 16:
            continue
        # the part of the wall that is solid at all heights between zlo and zhi is ~ the triangle's middle band
        zlo = sorted(zs)[0]
        zhi = sorted(zs)[1]          # conservative: the lower of the two upper corners
        if zhi - zlo < min_height:
            continue
        segs.append((p0[0], p0[1], p1[0], p1[1], zlo, zhi))
    return np.array(segs, dtype=np.float64) if segs else np.zeros((0, 6))


def visible(segs, A, B):
    """A, B: (x0, y0, x1, y1, zfloor, ztop). True when some sample ray is not blocked."""
    def pts(c, n=5):
        xs = np.linspace(c[0] + 64, c[2] - 64, n)
        ys = np.linspace(c[1] + 64, c[3] - 64, n)
        return np.array([(x, y) for x in xs for y in ys])
    pa, pb = pts(A), pts(B)
    ea = [A[4] + 70.0, min(A[4] + 250.0, max(A[4] + 70.0, A[5] - 40.0))]   # ground and first-floor eyes
    tb = [B[4] + 40.0, B[5]]
    lo = np.minimum(np.minimum(A[0], A[2]), np.minimum(B[0], B[2]))
    hi = np.maximum(np.maximum(A[0], A[2]), np.maximum(B[0], B[2]))
    loy = min(A[1], A[3], B[1], B[3])
    hiy = max(A[1], A[3], B[1], B[3])
    s = segs[(np.maximum(segs[:, 0], segs[:, 2]) >= lo) & (np.minimum(segs[:, 0], segs[:, 2]) <= hi) &
             (np.maximum(segs[:, 1], segs[:, 3]) >= loy) & (np.minimum(segs[:, 1], segs[:, 3]) <= hiy)]
    if len(s) == 0:
        return True
    P = np.repeat(pa, len(pb), axis=0)
    Q = np.tile(pb, (len(pa), 1))
    for za in ea:
        for zb in tb:
            r = Q - P                                   # rays (n,2)
            d = s[:, 2:4] - s[:, 0:2]                   # segs (m,2)
            w = s[None, :, 0:2] - P[:, None, :]         # (n,m,2)
            den = r[:, None, 0] * d[None, :, 1] - r[:, None, 1] * d[None, :, 0]
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (w[..., 0] * d[None, :, 1] - w[..., 1] * d[None, :, 0]) / den
                u = (w[..., 0] * r[:, None, 1] - w[..., 1] * r[:, None, 0]) / den
            hit = (np.abs(den) > 1e-9) & (t > 0.0) & (t < 1.0) & (u >= 0.0) & (u <= 1.0)
            z = za + (zb - za) * t
            hit &= (z >= s[None, :, 4]) & (z <= s[None, :, 5])
            if not hit.any(axis=1).all():
                return True
    return False

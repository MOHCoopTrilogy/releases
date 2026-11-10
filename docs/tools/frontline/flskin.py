#!/usr/bin/env python3
"""Player-clip skins (our code; runs inside the converter on the player's PC).

Frontline wraps much of its town in a second, smooth player-only collision layer (material 3 + the special-surface
bit, flconvert.COLL_SPECIAL): sheets standing 16-60u in front of the facades, over door and window recesses, across
rubble. Its player slid along them; in MOHAA - first person, wider view, a box hull - they read as invisible walls
an arm's length before every wall (geoaudit: 419 of the 982 invisible contacts on the original's routes, 281 with
drawn floor and path points right behind them).

A vertical sheet is a SKIN when the level's ordinary collision (every other material - the walls, crates, kerbs that
are also drawn) stands within `reach` behind it along its normal at every sample point, on the same side, with the
player's side open: the skin only keeps the player off a wall that already blocks him. Skins are dropped; the player
then meets the drawn wall itself (180 of 1071 vertical sheets on 1_1).

Everything else of the material is kept: sloped sheets (Frontline's ramps over stairs and rubble) and sheets with no
collision behind them. Those are the ONLY collision of what stands behind them (rubble, facades without collision of
their own) or boundaries closing side streets - the original player stopped at them too. A pass that re-seated them
onto the drawn surface (2026-11-10, removed) either let the walk audit out of the town through one-sided facade cards
or closed passages, for no gain on the routes: see docs/proposals/flpolish_2026-11-10/README.md.
"""
import math

import numpy as np


def _tri_arrays(tris):
    t = np.asarray(tris, np.float64).reshape(-1, 3, 3)
    return t


class RayGrid:
    """2D grid over triangles for ray casts (numpy Moller-Trumbore over the candidates of the cells a ray crosses)"""

    def __init__(self, tris, cell=128.0):
        self.t = _tri_arrays(tris)
        self.cell = cell
        self.g = {}
        if not len(self.t):
            return
        lo = self.t[:, :, :2].min(1)
        hi = self.t[:, :, :2].max(1)
        for i in range(len(self.t)):
            for gx in range(int(lo[i, 0] // cell), int(hi[i, 0] // cell) + 1):
                for gy in range(int(lo[i, 1] // cell), int(hi[i, 1] // cell) + 1):
                    self.g.setdefault((gx, gy), []).append(i)

    def cast(self, o, d, maxd):
        """distance to the nearest triangle along the ray, or None"""
        c = self.cell
        cand = set()
        n = max(1, int(math.ceil(maxd / (c * 0.5))))
        for k in range(n + 1):
            p = (o[0] + d[0] * maxd * k / n, o[1] + d[1] * maxd * k / n)
            for gx in (int(p[0] // c) - 1, int(p[0] // c), int(p[0] // c) + 1):
                for gy in (int(p[1] // c) - 1, int(p[1] // c), int(p[1] // c) + 1):
                    cand.update(self.g.get((gx, gy), ()))
        if not cand:
            return None
        t = self.t[list(cand)]
        o = np.asarray(o, np.float64)
        d = np.asarray(d, np.float64)
        e1 = t[:, 1] - t[:, 0]
        e2 = t[:, 2] - t[:, 0]
        p = np.cross(d, e2)
        det = (e1 * p).sum(1)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = o - t[:, 0]
        u = (s * p).sum(1) * inv
        q = np.cross(s, e1)
        v = (q * d).sum(1) * inv
        tt = (e2 * q).sum(1) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (tt > 0.5) & (tt <= maxd)
        if not hit.any():
            return None
        return float(tt[hit].min())

    def cast_id(self, o, d, maxd):
        """(distance, triangle index) of the nearest hit, or None"""
        c = self.cell
        cand = set()
        n = max(1, int(math.ceil(maxd / (c * 0.5))))
        for k in range(n + 1):
            p = (o[0] + d[0] * maxd * k / n, o[1] + d[1] * maxd * k / n)
            for gx in (int(p[0] // c) - 1, int(p[0] // c), int(p[0] // c) + 1):
                for gy in (int(p[1] // c) - 1, int(p[1] // c), int(p[1] // c) + 1):
                    cand.update(self.g.get((gx, gy), ()))
        if not cand:
            return None
        ids = np.fromiter(cand, np.int64)
        t = self.t[ids]
        o = np.asarray(o, np.float64)
        d = np.asarray(d, np.float64)
        e1 = t[:, 1] - t[:, 0]
        e2 = t[:, 2] - t[:, 0]
        p = np.cross(d, e2)
        det = (e1 * p).sum(1)
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = o - t[:, 0]
        u = (s * p).sum(1) * inv
        q = np.cross(s, e1)
        v = (q * d).sum(1) * inv
        tt = (e2 * q).sum(1) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (tt > 0.5) & (tt <= maxd)
        if not hit.any():
            return None
        j = int(np.argmin(np.where(hit, tt, np.inf)))
        return float(tt[j]), int(ids[j])


def _normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    if ln < 1e-9:
        return None
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def skins(tris, tags, is_skin_material, reach=64.0, body=(24.0, 56.0, 88.0)):
    """tris/tags: wound collision and its flag words. Returns (keep_mask, report). A vertical skin-material sheet is
    dropped when other collision stands within `reach` behind it at every sample (its lower body band only: the
    sheets run 450u up, the walls behind them often stop at the eaves)."""
    other = [t for t, f in zip(tris, tags) if not is_skin_material(f)]
    G = RayGrid(other)
    keep = [True] * len(tris)
    rep = {"skin_material": 0, "vertical": 0, "dropped": 0, "kept_open": 0}
    for i, (t, f) in enumerate(zip(tris, tags)):
        if not is_skin_material(f):
            continue
        rep["skin_material"] += 1
        n = _normal(*t)
        if n is None or abs(n[2]) > 0.3:
            continue
        rep["vertical"] += 1
        zlo = min(v[2] for v in t)
        zhi = max(v[2] for v in t)
        hd = math.hypot(n[0], n[1])
        nh = (n[0] / hd, n[1] / hd, 0.0)
        samples = []
        a, b, c = t
        for wa, wb, wc in ((1 / 3, 1 / 3, 1 / 3), (0.7, 0.15, 0.15), (0.15, 0.7, 0.15), (0.15, 0.15, 0.7)):
            p = tuple(a[k] * wa + b[k] * wb + c[k] * wc for k in range(3))
            samples.append(p)
        # the body band of the sheet: samples projected to 24/56/88 above the sheet's foot where the sheet reaches
        pts = []
        for p in samples:
            for h in body:
                z = zlo + h
                if z <= zhi:
                    pts.append((p[0], p[1], z))
        if not pts:
            pts = samples
        # every sample must find the wall on the SAME side (the back), and the other side (the player's) must be open
        # for at least a body width: a sheet with collision on both sides, or behind it only in places, is a boundary
        # or a gap filler, not a skin
        covered = False
        for sgn in (1.0, -1.0):
            ok = True
            for p in pts:
                o = (p[0] - nh[0] * sgn * 2, p[1] - nh[1] * sgn * 2, p[2])
                if G.cast(o, (nh[0] * sgn, nh[1] * sgn, 0.0), reach) is None:
                    ok = False
                    break
                o2 = (p[0] + nh[0] * sgn * 2, p[1] + nh[1] * sgn * 2, p[2])
                if G.cast(o2, (-nh[0] * sgn, -nh[1] * sgn, 0.0), 40.0) is not None:
                    ok = False
                    break
            if ok:
                covered = True
                break
        if covered:
            keep[i] = False
            rep["dropped"] += 1
        else:
            rep["kept_open"] += 1
    return keep, rep


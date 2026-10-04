# -*- coding: utf-8 -*-
"""Periodic (torus) image quilting - Efros & Freeman 2001 - single process, deterministic.

Builds a SEAMLESS tile from real photographic exemplars: every output pixel is a real exemplar pixel (no
upscaling, no sharpening, no generated detail); patches meet along minimum-error cuts. The torus layout makes
the last column/row match the first, so the result tiles without a wrap seam.

    out = quilt(exemplars, size=1024, P=80, O=16, seed=1, blob_w=..., reuse_w=...)
exemplars: list of HxWx3 float arrays (already colour-normalised and at the target world scale).
"""
import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve


def _orient(a, k):
    t = a.transpose(1, 0, 2) if a.ndim == 3 else a.T
    return [a, a[:, ::-1], a[::-1], a[::-1, ::-1], t, t[:, ::-1], t[::-1], t[::-1, ::-1]][k]


def _cut_path(err):
    """min vertical path through err (h x w): returns column index per row."""
    h, w = err.shape
    C = err.copy()
    for y in range(1, h):
        prev = C[y - 1]
        l = np.r_[np.inf, prev[:-1]]
        r = np.r_[prev[1:], np.inf]
        C[y] += np.minimum(np.minimum(l, prev), r)
    path = np.zeros(h, int)
    path[-1] = int(np.argmin(C[-1]))
    for y in range(h - 2, -1, -1):
        x = path[y + 1]
        lo, hi = max(0, x - 1), min(w, x + 2)
        path[y] = lo + int(np.argmin(C[y, lo:hi]))
    return path


def quilt(exemplars, size=1024, P=80, O=16, seed=1, blob_w=0.0, blob_maps=None, reuse_w=0.0, tol=0.08, log=None,
          ban=0.15, stats=None):
    rng = np.random.default_rng(seed)
    S = P - O
    assert size % S == 0, "size must be a multiple of the step"
    n = size // S
    out = np.zeros((size, size, 3), np.float64)
    done = np.zeros((size, size), bool)
    srcs = []                                   # (array, blobcost map over valid positions, usage map)
    # CLONE BAN: every exemplar pixel carries a 'used' flag in ITS OWN coordinates, shared by all 8 orientations, so
    # a spot already placed cannot come back mirrored or rotated either. A candidate whose window is more than
    # `ban` used is excluded; only if every candidate is excluded (pool exhausted) does the least-used one win.
    used = [np.zeros(e.shape[:2], bool) for e in exemplars]
    ids = [np.arange(e.shape[0] * e.shape[1]).reshape(e.shape[:2]) for e in exemplars]
    if stats is not None:
        stats.update(exhausted=0, placements=0)
    for e_i, e in enumerate(exemplars):
        for k in range(8):
            a = np.ascontiguousarray(_orient(e, k))
            H, W = a.shape[:2]
            if H < P or W < P:
                continue
            bc = np.zeros((H - P + 1, W - P + 1))
            if blob_maps is not None:
                bm = _orient(blob_maps[e_i], k)
                # mean blob score inside the patch window
                bc = fftconvolve(bm, np.ones((P, P)) / (P * P), mode="valid")
            srcs.append(dict(a=a, a2=(a ** 2).sum(-1), bc=bc, use=np.zeros_like(bc), id=(e_i, k),
                             ids=np.ascontiguousarray(_orient(ids[e_i], k)), e=e_i, k=k))
    order = [(i, j) for i in range(n) for j in range(n)]
    for (i, j) in order:
        y0, x0 = i * S - O, j * S - O                       # window top-left (may be negative: torus)
        ys = (np.arange(P) + y0) % size
        xs = (np.arange(P) + x0) % size
        T = out[np.ix_(ys, xs)]
        M = done[np.ix_(ys, xs)].astype(np.float64)
        best = []
        if M.sum() == 0:
            s = srcs[rng.integers(len(srcs))]
            H, W = s["bc"].shape
            yy, xx = int(rng.integers(H)), int(rng.integers(W))
            best = [(0.0, s, yy, xx)]
        else:
            cand = []
            Mf = M[::-1, ::-1]
            TMf = (T * M[..., None])[::-1, ::-1]
            tt = (T ** 2).sum(-1)
            const = (tt * M).sum()
            box = np.ones((P, P)) / (P * P)
            for s in srcs:
                a = s["a"]
                uf = fftconvolve(_orient(used[s["e"]], s["k"]).astype(np.float64), box, mode="valid")
                e2 = fftconvolve(s["a2"], Mf, mode="valid")
                cross = sum(fftconvolve(a[..., c], TMf[..., c], mode="valid") for c in range(3))
                ssd = np.maximum(e2 - 2 * cross + const, 0) / M.sum()
                cost = ssd * (1 + blob_w * s["bc"]) + reuse_w * s["use"]
                s["uf"] = uf
                cost = np.where(uf > ban, np.inf, cost)
                k = np.argmin(cost)
                yy, xx = np.unravel_index(k, cost.shape)
                cand.append((cost[yy, xx], s, cost))
            mn = min(c[0] for c in cand)
            if not np.isfinite(mn):                         # pool exhausted: least-used window anywhere
                if stats is not None:
                    stats["exhausted"] += 1
                cand = []
                for s in srcs:
                    cost = s["uf"] * 1e6 + 0.0
                    k = np.argmin(cost)
                    yy, xx = np.unravel_index(k, cost.shape)
                    cand.append((cost[yy, xx], s, cost))
                mn = min(c[0] for c in cand)
            pool = []
            for c0, s, cost in cand:
                if c0 <= mn * (1 + tol):
                    idx = np.argwhere(cost <= mn * (1 + tol))
                    if len(idx) > 40:
                        idx = idx[rng.choice(len(idx), 40, replace=False)]
                    for yy, xx in idx:
                        pool.append((cost[yy, xx], s, int(yy), int(xx)))
            pick = pool[int(rng.integers(len(pool)))]
            best = [pick]
        _, s, yy, xx = best[0]
        patch = s["a"][yy:yy + P, xx:xx + P]
        used[s["e"]].flat[s["ids"][yy:yy + P, xx:xx + P].ravel()] = True
        if stats is not None:
            stats["placements"] += 1
        # usage penalty around the chosen spot
        H, W = s["use"].shape
        s["use"][max(0, yy - P // 2):yy + P // 2, max(0, xx - P // 2):xx + P // 2] += 1.0
        # minimum-error cuts on every overlap strip that is already written
        mask = np.ones((P, P), bool)
        err = ((patch - T) ** 2).sum(-1)
        if M[:, :O].mean() > 0.5:
            p = _cut_path(err[:, :O])
            for y in range(P):
                mask[y, :p[y]] = False
        if M[:, P - O:].all() and j == n - 1:
            p = _cut_path(err[:, P - O:][:, ::-1])
            for y in range(P):
                mask[y, P - p[y]:] = False
        if M[:O, :].mean() > 0.5:
            p = _cut_path(err[:O, :].T)
            for x in range(P):
                mask[:p[x], x] &= False
        if M[P - O:, :].all() and i == n - 1:
            p = _cut_path(err[P - O:, :][::-1].T)
            for x in range(P):
                mask[P - p[x]:, x] = False
        # a one-pixel feather along the cut only (no wide blending - no ghosting bands)
        m = ndimage.uniform_filter(mask.astype(np.float64), 3)
        m = np.where(M > 0, m, 1.0)
        blended = patch * m[..., None] + T * (1 - m[..., None])
        out[np.ix_(ys, xs)] = blended
        done[np.ix_(ys, xs)] = True
        if log and (i * n + j) % 32 == 0:
            log("quilt %d/%d" % (i * n + j, n * n))
    return out

"""Clip boxes that follow the m2l3 finale fuel tanks (models/static/fuel_tanks.tik) instead of their one big bounding box.

user, 2026-11-01: "There are still invisible walls around these fuel tanks we need to make them perfect like sandbags."
A script_model collides as ONE axis-aligned box. For fuel_tanks (two upright cylinders on legs, pipework overhead) that box is
388 x 180 u at scale 0.4 and blocks the floor well outside the tanks.

Footprint = the model's own triangles that reach below BODY_Z (what a standing player can touch), projected top-down in the
ANIMATED pose (the idle skc turns the rest pose 90 degrees: x' = -y, y' = x - see bug-10277), holes filled. It is covered the same way
gen_sandbag_arcclip.py covers the sandbags: each box sits inside the footprint at ANY yaw (half-width r/sqrt 2, r = distance to the
outline), greedy, with gaps narrower than any hull.

Prints the Morpheus table finale_m2l3.scr::fin_tankclip reads: offsets in the model frame at tik scale x entity scale 1 (multiply by
the entity scale), z = box top.
    python docs/tools/gen_fueltank_clip.py
"""
import math
import os
import struct
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "hzm-mohaa-coop-mod", "_research", "nohat"))
import skdlib as K  # noqa: E402

PAK = "G:/GOG/Medal of Honor - Allied Assault War Chest/maintt/pak1.pk3"
TIK_SCALE = 2.5
BODY_Z = 96.0       # model units x tik scale, at entity scale 1 (240 u at 0.4 = well over a standing player)
MARGIN = 20.0
MINR = 12.0
GAP = 30.0          # at entity scale 1; x 0.4 in the finale = 12 u, under a 30 u AI / 32 u player hull


def pose_points():
    z = zipfile.ZipFile(PAK)
    m = K.read_skd(z.read("models/static/fuel_tanks/fuel_tanks.skd"))
    W = {}
    for b in m.bones:
        loc = K.mat4(K.quat_to_mat3((0, 0, 0, 1)), (0, 0, 0))
        W[b.name] = K.mat4_mul(loc, W[b.parent]) if b.parent in W else loc
    names = [b.name for b in m.bones]
    tris = []
    for s in m.surfaces:
        P = []
        for (n, t, wl, ml) in s.verts:
            p = [0.0, 0.0, 0.0]
            for (bi, bw, off) in wl:
                q = K.xform_point(off, W[names[bi]])
                for k in range(3):
                    p[k] += bw * q[k]
            x, y, zz = (c * TIK_SCALE for c in p)
            P.append((-y, x, zz))   # the animated pose
        idx = struct.unpack("<%di" % (len(s.tri_bytes) // 4), s.tri_bytes)
        for i in range(0, len(idx), 3):
            tris.append((P[idx[i]], P[idx[i + 1]], P[idx[i + 2]]))
    return tris


def main():
    alltris = pose_points()
    tris = [t for t in alltris if min(v[2] for v in t) < BODY_Z]
    allp = [v for t in tris for v in t]
    lo = np.floor([min(v[0] for v in allp) - 4, min(v[1] for v in allp) - 4])
    hi = np.ceil([max(v[0] for v in allp) + 4, max(v[1] for v in allp) + 4])
    st = 2.0
    xs = np.arange(lo[0], hi[0] + st, st)
    ys = np.arange(lo[1], hi[1] + st, st)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    inside = np.zeros(X.shape, bool)
    for (a, b, c) in tris:
        # rasterize the triangle's top-down projection (degenerate vertical walls: thicken by one cell)
        x0, x1 = min(a[0], b[0], c[0]) - st, max(a[0], b[0], c[0]) + st
        y0, y1 = min(a[1], b[1], c[1]) - st, max(a[1], b[1], c[1]) + st
        i0, i1 = np.searchsorted(xs, x0), np.searchsorted(xs, x1)
        j0, j1 = np.searchsorted(ys, y0), np.searchsorted(ys, y1)
        sx, sy = X[i0:i1, j0:j1], Y[i0:i1, j0:j1]
        if sx.size == 0:
            continue
        # distance from cell centre to the triangle's projected edges <= st, or inside it
        def side(p, q):
            return (q[0] - p[0]) * (sy - p[1]) - (q[1] - p[1]) * (sx - p[0])
        d1, d2, d3 = side(a, b), side(b, c), side(c, a)
        inn = ((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))
        near = np.zeros(sx.shape, bool)
        for (p, q) in ((a, b), (b, c), (c, a)):
            ex, ey = q[0] - p[0], q[1] - p[1]
            L = ex * ex + ey * ey
            if L < 1e-9:
                dd = np.hypot(sx - p[0], sy - p[1])
            else:
                t = np.clip(((sx - p[0]) * ex + (sy - p[1]) * ey) / L, 0, 1)
                dd = np.hypot(sx - (p[0] + t * ex), sy - (p[1] + t * ey))
            near |= dd <= st * 0.75
        inside[i0:i1, j0:j1] |= inn | near
    # fill holes: anything not reachable from the border is inside
    out = np.zeros(X.shape, bool)
    stack = [(i, j) for i in range(X.shape[0]) for j in (0, X.shape[1] - 1)] + \
            [(i, j) for j in range(X.shape[1]) for i in (0, X.shape[0] - 1)]
    while stack:
        i, j = stack.pop()
        if i < 0 or j < 0 or i >= X.shape[0] or j >= X.shape[1] or out[i, j] or inside[i, j]:
            continue
        out[i, j] = True
        stack += [(i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)]
    inside = ~out
    if "--slabs" in sys.argv:
        return slabs(X, Y, inside, st, alltris)
    edge = inside & ~(np.roll(inside, 1, 0) & np.roll(inside, -1, 0) & np.roll(inside, 1, 1) & np.roll(inside, -1, 1))
    ex, ey = X[edge], Y[edge]
    dist = np.zeros(X.shape)
    ix, iy = X[inside], Y[inside]
    dist[inside] = np.sqrt(((ix[:, None] - ex[None, :]) ** 2 + (iy[:, None] - ey[None, :]) ** 2).min(axis=1)) + st / 2
    mx = dist.copy()
    for di in (-2, -1, 0, 1, 2):
        for dj in (-2, -1, 0, 1, 2):
            mx = np.maximum(mx, np.roll(np.roll(dist, di, 0), dj, 1))
    # thick parts (the cylinders) are covered whole down to MARGIN; thin parts (pipes, legs) along their middle line
    target = inside & (dist >= MARGIN)
    cov = np.zeros(X.shape, bool)
    cand = np.argwhere(inside & (dist >= MINR))
    boxes = []
    while (target & ~cov).sum() > 0:
        unc = target & ~cov
        best, bg = None, 0
        for (i, j) in cand:
            h = dist[i, j] / math.sqrt(2)
            hc = h + GAP / 2 if dist[i, j] < 2 * MINR else h
            g = (unc & ((X - X[i, j]) ** 2 + (Y - Y[i, j]) ** 2 <= hc * hc)).sum()
            if g > bg:
                best, bg = (i, j), g
        if best is None:
            break
        i, j = best
        h = dist[i, j] / math.sqrt(2)
        hc = h + GAP / 2 if dist[i, j] < 2 * MINR else h
        cov |= (X - X[i, j]) ** 2 + (Y - Y[i, j]) ** 2 <= hc * hc
        boxes.append((X[i, j], Y[i, j], h))
    left = (target & ~cov).sum()
    print("// fuel_tanks: %d tris under %.0f u, %d boxes, uncovered %d cells (margin %.0f, gap %.0f; scale 1 units)"
          % (len(tris), BODY_Z, len(boxes), left, MARGIN, GAP))
    for k, (x, y, h) in enumerate(boxes):
        print("\tlocal.cx[%d] = %.1f; local.cy[%d] = %.1f; local.ch[%d] = %.1f" % (k, x, k, y, k, h))
    np.save(os.path.join(os.environ.get("TEMP", "."), "tankclip_inside.npy"), np.stack([X, Y, inside.astype(float)]))


def slabs(X, Y, inside, st, alltris):
    """Right-angle placements (the finale's tanks are at 0/90/180/270): greedy largest axis-aligned rectangles that lie wholly
    inside the footprint, until every cell more than SLAB_MISS from the outline is covered. A 90-degree turn keeps them exact."""
    import scipy.ndimage as ndi
    lab, n = ndi.label(inside)
    dist = ndi.distance_transform_edt(inside) * st
    I = np.pad(inside.astype(int), ((1, 0), (1, 0))).cumsum(0).cumsum(1)

    def full(i0, i1, j0, j1):
        return I[i1, j1] - I[i0, j1] - I[i1, j0] + I[i0, j0] == (i1 - i0) * (j1 - j0)
    out = []
    for b in range(1, n + 1):
        m = lab == b
        if m.sum() * st * st < 40 * 40:
            continue        # leg feet and bolts: too small to stop anyone
        target = m & (dist >= SLAB_MISS)
        cov = np.zeros(m.shape, bool)
        ii, jj = np.where(m)
        lo_i, hi_i, lo_j, hi_j = ii.min(), ii.max() + 1, jj.min(), jj.max() + 1
        step = 2
        while (target & ~cov).any():
            best, bg = None, 0
            for i0 in range(lo_i, hi_i, step):
                for i1 in range(i0 + step, hi_i + 1, step):
                    # widest j-run for rows i0..i1 inside: scan
                    j0 = lo_j
                    while j0 < hi_j:
                        if not full(i0, i1, j0, j0 + 1):
                            j0 += 1
                            continue
                        j1 = j0 + 1
                        while j1 < hi_j and full(i0, i1, j1, j1 + 1):
                            j1 += 1
                        g = (target[i0:i1, j0:j1] & ~cov[i0:i1, j0:j1]).sum()
                        if g > bg:
                            best, bg = (i0, i1, j0, j1), g
                        j0 = j1
            if best is None:
                break
            i0, i1, j0, j1 = best
            cov[i0:i1, j0:j1] = True
            x0, x1 = X[i0, 0] - st / 2, X[i1 - 1, 0] + st / 2
            y0, y1 = Y[0, j0] - st / 2, Y[0, j1 - 1] + st / 2
            out.append(((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2))
        print("// blob %d: uncovered %d" % (b, (target & ~cov).sum()))
    # each box's top: the highest model vertex standing over it, so a box never rises above what is drawn there
    V = np.array([v for t in alltris for v in t])
    print("// fuel_tanks: %d boxes (scale 1 units: centre x y, half x y, top z; miss <= %.0f)" % (len(out), SLAB_MISS))
    for k, (x, y, hx, hy) in enumerate(out):
        sel = (np.abs(V[:, 0] - x) <= hx) & (np.abs(V[:, 1] - y) <= hy)
        top = float(V[sel, 2].max()) if sel.any() else BODY_Z
        print("	local.cx[%d] = %.1f; local.cy[%d] = %.1f; local.hx[%d] = %.1f; local.hy[%d] = %.1f; local.ct[%d] = %.1f"
              % (k, x, k, y, k, hx, k, hy, k, top))


SLAB_MISS = 16.0   # scale-1 units: a player can sink at most ~6 u into a 0.4 tank anywhere



if __name__ == "__main__":
    main()

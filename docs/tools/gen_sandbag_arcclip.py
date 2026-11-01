"""Clip boxes that follow the retail sandbag semicircle's own clip brushes (models/static/sandbag_*_semicircle.map).

user, 2026-11-01: "The mg42 sandbags ... have messed up clipping. You can't actually walk into the semicircle ... ensure that the
clipping is absolutely perfect". A script_model's collision is ONE axis-aligned box: for a semicircle that is a solid block over
the whole arc, seat included. The retail model ships its real clip as brushes in a .map; this covers those brushes with small
boxes. Each box is centred at c with half-width r/sqrt(2), r = c's distance to the brush outline, so the box stays inside the bags
at ANY yaw (an axis-aligned box rotated with the model would not). Greedy cover of the outline eroded by MARGIN: a player can sink
at most a few units into the bags, and never meets an invisible wall. Only the wall's middle line is covered, with gaps of at
most GAP between boxes: narrower than any player or AI hull, so nothing passes, at a third of the entity count.

Prints the Morpheus table bunker.scr::arcclip_<name> reads (offsets in the model's frame at tik scale; z = box top).
    python docs/tools/gen_sandbag_arcclip.py
"""
import math
import zipfile
import numpy as np

PAK = "G:/GOG/Medal of Honor - Allied Assault War Chest/main/Pak0.pk3"
MARGIN = 6.0
MINR = 9.0
GAP = 14.0     # largest gap left between neighbouring boxes; a player is 32 u wide, an AI 30 - neither fits


def brushes(text):
    out, cur = [], None
    for ln in text.splitlines():
        s = ln.strip()
        if s == "{" and cur is None and out is not None:
            cur = [] if "classname" in "".join(text[:0]) else []
            continue
        if s.startswith("("):
            nums = s.replace("(", " ").replace(")", " ").split()
            p = [tuple(float(nums[i * 3 + k]) for k in range(3)) for i in range(3)]
            cur.append(p)
        elif s == "}" and cur:
            out.append(cur)
            cur = []
    return [b for b in out if len(b) >= 4]


def planes(b):
    pl = []
    for (p0, p1, p2) in b:
        a = np.array(p1) - np.array(p0)
        c = np.array(p2) - np.array(p0)
        n = np.cross(a, c)
        n = n / np.linalg.norm(n)
        pl.append((n, float(np.dot(n, p0))))
    return pl


def verts(pl):
    vs = []
    for i in range(len(pl)):
        for j in range(i + 1, len(pl)):
            for k in range(j + 1, len(pl)):
                A = np.array([pl[i][0], pl[j][0], pl[k][0]])
                if abs(np.linalg.det(A)) < 1e-6:
                    continue
                x = np.linalg.solve(A, np.array([pl[i][1], pl[j][1], pl[k][1]]))
                if all(np.dot(n, x) - d <= 0.05 for (n, d) in pl) or all(np.dot(n, x) - d >= -0.05 for (n, d) in pl):
                    vs.append(x)
    return vs


def inside_sign(pl, vs):
    c = np.mean(vs, axis=0)
    return 1 if all(np.dot(n, c) - d <= 0 for (n, d) in pl) else -1


def main():
    z = zipfile.ZipFile(PAK)
    for name in ("sandbag_large_semicircle", "sandbag_small_semicircle"):
        bs = brushes(z.read("models/static/%s.map" % name).decode("latin-1"))
        solids = []
        for b in bs:
            pl = planes(b)
            vs = verts(pl)
            if len(vs) < 4:
                continue
            sg = inside_sign(pl, vs)
            vs = np.array(vs)
            solids.append((pl, sg, vs))
        lo = np.floor(np.min([s[2].min(axis=0) for s in solids], axis=0)) - 2
        hi = np.ceil(np.max([s[2].max(axis=0) for s in solids], axis=0)) + 2
        xs = np.arange(lo[0], hi[0] + 0.5, 1.0)
        ys = np.arange(lo[1], hi[1] + 0.5, 1.0)
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        inside = np.zeros(X.shape, bool)
        top = np.full(X.shape, -1.0)
        for (pl, sg, vs) in solids:
            # footprint: the brush's 2D extent tested against its side planes (|n.z| < 0.5) only
            m = np.ones(X.shape, bool)
            for (n, d) in pl:
                if abs(n[2]) < 0.5:
                    m &= sg * (n[0] * X + n[1] * Y - d) <= 1e-6
            inside |= m
            top = np.where(m, np.maximum(top, vs[:, 2].max()), top)
        # distance to the outline (brute force over outline pixels)
        edge = inside & ~(np.roll(inside, 1, 0) & np.roll(inside, -1, 0) & np.roll(inside, 1, 1) & np.roll(inside, -1, 1))
        ex, ey = X[edge], Y[edge]
        ix, iy = X[inside], Y[inside]
        dist = np.zeros(X.shape)
        dv = np.sqrt(((ix[:, None] - ex[None, :]) ** 2 + (iy[:, None] - ey[None, :]) ** 2).min(axis=1)) + 0.5
        dist[inside] = dv
        # the wall's middle line: pixels at (near) the largest distance in their neighbourhood
        mx = dist.copy()
        for di in (-2, -1, 0, 1, 2):
            for dj in (-2, -1, 0, 1, 2):
                mx = np.maximum(mx, np.roll(np.roll(dist, di, 0), dj, 1))
        target = inside & (dist >= MARGIN) & (dist >= mx - 1.0)
        cov = np.zeros(X.shape, bool)
        cand = np.argwhere(inside & (dist >= MINR))
        boxes = []
        while (target & ~cov).sum() > 0:
            best, bg = None, 0
            unc = target & ~cov
            for (i, j) in cand[::2]:
                h = dist[i, j] / math.sqrt(2)
                cx, cy = X[i, j], Y[i, j]
                # the inscribed circle of the box (radius h) is what is covered at any yaw
                h = h + GAP / 2
                r = int(math.ceil(h))
                sub = unc[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1]
                sx = X[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1]
                sy = Y[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1]
                g = (sub & ((sx - cx) ** 2 + (sy - cy) ** 2 <= h * h)).sum()
                if g > bg:
                    best, bg = (i, j), g
            if best is None:
                break
            i, j = best
            h = dist[i, j] / math.sqrt(2)
            cov |= (X - X[i, j]) ** 2 + (Y - Y[i, j]) ** 2 <= (h + GAP / 2) ** 2
            cov |= (X - X[i, j]) ** 2 + (Y - Y[i, j]) ** 2 <= h * h
            boxes.append((X[i, j], Y[i, j], h, top[i, j]))
        left = (target & ~cov).sum()
        print("// %s: %d brushes, %d boxes, uncovered %d px (margin %.0f)" % (name, len(solids), len(boxes), left, MARGIN))
        for k, (x, y, h, t) in enumerate(boxes):
            print("\tlocal.c[%d] = ( %.1f %.1f %.1f )\tlocal.t[%d] = %.1f" % (k, x, y, h, k, t))


if __name__ == "__main__":
    main()

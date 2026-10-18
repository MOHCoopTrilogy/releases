"""fit2_lib.py - measure a gun's real side-profile bounds in the armory slot-1 card thumbnail AND the big inspect preview.
Both are in every screenshot; the empty baseline (fit_000) is subtracted. 960x540 window, the 640x480 menu is stretched (x1.5, y1.125)."""
import os
import numpy as np
from PIL import Image

SX, SY = 1.5, 1.125
# Thumbnail box in 640x480 menu units. Re-solve for another box (redesign hero/card sizes): BOXX/BOXY/BOXW/BOXH env, or edit these.
BX, BY = float(os.environ.get("BOXX", 160)), float(os.environ.get("BOXY", 60))
BW, BH = float(os.environ.get("BOXW", 92)), float(os.environ.get("BOXH", 50))
RECTS = {
    "T": (int(BX * SX), int(BY * SY), int((BX + BW) * SX), int((BY + BH) * SY)),      # cardthumb1 rect 160 60 92 50
    "W": (int(478 * SX), int(44 * SY), int((478 + 152) * SX), int((44 + 100) * SY)),    # prevC* rect 478 44 152 100
}
THR = 10


def load(path, view):
    return np.asarray(Image.open(path).convert("RGB").crop(RECTS[view])).astype(int)


def mask(img, base, thr=None):
    m = (np.abs(img - base).sum(axis=2) > (THR if thr is None else thr))
    # drop isolated specks: keep a pixel only if >= 3 of its 8 neighbours are set
    p = np.pad(m, 1)
    n = sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx].astype(int) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx))
    return m & (n >= 3)


def measure(img, base):
    m = mask(img, base)
    if m.sum() < 220:   # faint / dark gun on the dark card (26, 32, 52, 61 ...): retry with a lower threshold
        m = mask(img, base, 4)
    ys, xs = np.nonzero(m)
    if len(xs) < 12:
        return None
    H, W = m.shape
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    cols = m.sum(axis=0)[x0:x1]
    q = max(1, (x1 - x0) // 4)
    tl, tr = cols[:q].mean(), cols[-q:].mean()
    return dict(x0=x0 / W, x1=x1 / W, y0=y0 / H, y1=y1 / H, w=(x1 - x0) / W, h=(y1 - y0) / H, cx=(x0 + x1) / 2 / W, cy=(y0 + y1) / 2 / H,
                my=ys.mean() / H, tl=float(tl), tr=float(tr), n=int(m.sum()))


def clipped(b, e=0.012):
    return b["x0"] < e or b["x1"] > 1 - e or b["y0"] < e or b["y1"] > 1 - e


def run(d, views=("T",)):
    out = {}
    bases = {v: load(os.path.join(d, "fit_000.jpg"), v) for v in views}
    for f in sorted(os.listdir(d)):
        if f.startswith("fit_") and f != "fit_000.jpg":
            p = os.path.join(d, f)
            out[f[4:-4]] = {v: measure(load(p, v), bases[v]) for v in views}
    return out

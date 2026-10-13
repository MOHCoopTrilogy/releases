"""rainpix.py - how much of a picture is rain streak, by height on the screen.
A streak pixel = a pixel brighter (luma) than the per-pixel MEDIAN of the stills of the same view by more than THR.
The stills must be of one fixed view; a streak is in a different place in each, the scene is not."""
import numpy as np
from PIL import Image
THR = 9.0


def _luma(fn, crop=None):
    im = Image.open(fn).convert("RGB")
    a = np.asarray(im, dtype=np.float32)
    y = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    return y


def masks(files):
    """streak masks of the frames that are NOT lit differently from the others (a lightning flash or a fog step
    lifts the whole picture and would count as streak everywhere): a frame whose median difference from the
    per-pixel median exceeds FLASH luma is left out"""
    st = np.stack([_luma(f) for f in files])
    med = np.median(st, axis=0)
    d = st - med
    keep = [i for i in range(len(files)) if abs(float(np.median(d[i]))) <= FLASH and float((d[i] > THR).mean()) < 0.45]
    if len(keep) < 2:
        keep = list(range(len(files)))
    st = st[keep]
    bg = np.sort(st, axis=0)[(len(keep) - 1) // 2]      # the lower median of the frames that are kept
    return st - bg > THR


FLASH = 1.5


def profile(files, bands=10):
    m = masks(files)
    n, h, w = m.shape
    # the HUD corner (top right icons) is left out
    m[:, : int(h * 0.09), int(w * 0.86):] = False
    out = []
    for b in range(bands):
        r0, r1 = h * b // bands, h * (b + 1) // bands
        out.append(100.0 * float(m[:, r0:r1, :].mean()))
    return {"n": n, "total_pct": 100.0 * float(m.mean()), "bands_pct": out}


if __name__ == "__main__":
    import sys
    p = profile(sys.argv[1:])
    print("%.2f %% | %s" % (p["total_pct"], " ".join("%.1f" % v for v in p["bands_pct"])))

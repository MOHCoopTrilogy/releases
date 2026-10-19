"""build_cutouts.py <runDir> - difference-matte the harness renders into RGBA cut-outs (assets/*.png).

    K = C*a            (render over opaque black)
    W = C*a + (1-a)    (render over opaque white)       =>  a = 1 - mean(W-K),  C = K / a
Nothing is painted or generated: every pixel is the game's own render of the real model.
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "assets")


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32) / 255.0


def main():
    d = sys.argv[1]
    man = json.load(open(os.path.join(d, "manifest.json")))
    os.makedirs(OUT, exist_ok=True)
    cnt = 0
    for grp in ("gun", "char"):
        for tag, info in man[grp].items():
            if not info.get("ok"):
                continue
            k = os.path.join(d, "shots", tag + "_K.tga")
            w = os.path.join(d, "shots", tag + "_W.tga")
            if not (os.path.isfile(k) and os.path.isfile(w)):
                continue
            K, W = load(k), load(w)
            if grp == "char":
                # the operator idles (breathes) between the two frames: take the mask from the black-background frame only
                m = K.max(axis=2) > 0.035
                m = ndi.binary_closing(m, iterations=2)
                m = ndi.binary_fill_holes(m)
                lab, n = ndi.label(m)
                if n > 1:
                    sz = ndi.sum(m, lab, range(1, n + 1))
                    keep = [i + 1 for i, v in enumerate(sz) if v >= 0.05 * max(sz)]
                    m = np.isin(lab, keep)
                m = ndi.binary_erosion(m, iterations=1)
                a = ndi.gaussian_filter(m.astype(np.float32), 0.8)
                C = K
            else:
                a = np.clip(1.0 - (W - K).mean(axis=2), 0, 1)
                a[a < 0.03] = 0
                lab, n = ndi.label(a > 0.05, structure=np.ones((3, 3)))
                if n > 1:     # drop floating bits (the ammo clip the model carries at its origin)
                    sz = ndi.sum(a > 0.05, lab, range(1, n + 1))
                    keep = [i + 1 for i, v in enumerate(sz) if v >= 0.25 * max(sz)]
                    a = np.where(np.isin(lab, keep), a, 0)
                C = np.where(a[..., None] > 0.02, K / np.maximum(a[..., None], 0.02), 0)
                C = np.clip(C, 0, 1)
            rgba = np.dstack([C, a])
            ys, xs = np.nonzero(a > 0.05)
            if len(xs) < 50:
                continue
            x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
            pad = 4
            rgba = rgba[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
            Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(OUT, tag + ".png"))
            cnt += 1
    print("cutouts", cnt, "->", OUT)


if __name__ == "__main__":
    main()

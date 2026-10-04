"""qa_sampling.py - what the GPU actually does to a 512 card drawn at tile size.

    python tools/qa_sampling.py    # ../samples/qa/sampling_<W>x<H>.png

Row 1: bare image path in the cfg (today's wiring). RE_RegisterShaderNoMip -> no mipmaps: plain bilinear taps at each
       screen pixel centre (emulated here exactly), so a 2.5x minification skips texels.
Row 2: explicit shader with mipmaps (scripts/coop_tileart.shader, nopicmip): trilinear ~ a box-filtered mip chain
       (emulated by an area-average to the nearest mip + bilinear, blended).
"""
import glob
import os

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)


def bilinear(a, ow, oh):
    h, w = a.shape[:2]
    ys = (np.arange(oh) + 0.5) * h / oh - 0.5
    xs = (np.arange(ow) + 0.5) * w / ow - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1); y1 = np.clip(y0 + 1, 0, h - 1); fy = (ys - np.floor(ys))[:, None, None]
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1); x1 = np.clip(x0 + 1, 0, w - 1); fx = (xs - np.floor(xs))[None, :, None]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def trilinear(im, ow, oh):
    a = np.asarray(im, np.float32)
    lod = np.log2(max(im.width / ow, im.height / oh))
    lo = int(np.floor(lod)); t = lod - lo
    m0 = np.asarray(im.resize((im.width >> lo, im.height >> lo), Image.BOX), np.float32)
    m1 = np.asarray(im.resize((im.width >> (lo + 1), im.height >> (lo + 1)), Image.BOX), np.float32)
    return bilinear(m0, ow, oh) * (1 - t) + bilinear(m1, ow, oh) * t


def main():
    fs = sorted(glob.glob(os.path.join(PROP, "samples", "game", "*.jpg")))
    for W, H in ((1920, 1080), (1280, 720)):
        tw, th = int(W / 640 * 100), int(H / 480 * 100)
        S = Image.new("RGB", (len(fs) * (tw + 6) + 6, 2 * (th + 6) + 6), (10, 30, 10))
        for k, f in enumerate(fs):
            im = Image.open(f).convert("RGB")
            a = np.asarray(im, np.float32)
            r1 = Image.fromarray(np.clip(bilinear(a, tw, th), 0, 255).astype(np.uint8))
            r2 = Image.fromarray(np.clip(trilinear(im, tw, th), 0, 255).astype(np.uint8))
            S.paste(r1, (6 + k * (tw + 6), 6))
            S.paste(r2, (6 + k * (tw + 6), th + 12))
        S.save(os.path.join(PROP, "samples", "qa", "sampling_%dx%d.png" % (W, H)), optimize=True)
        print("sampling", W, H)


if __name__ == "__main__":
    main()

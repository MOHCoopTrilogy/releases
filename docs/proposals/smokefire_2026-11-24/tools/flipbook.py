"""flipbook.py <layer_dir> <out_tex_dir> <name> --kind fire|smoke [--px 256] [--gain 1.0] [--n 36] [--sheet out.jpg]

Blender 16-bit RGBA PNG frames -> game flipbook TGAs  <out_tex_dir>/<name>NNN.tga  (+ contact sheet).
  fire  : additive layer. RGB on black (alpha ignored by `blendfunc add`; written opaque white-alpha). Highlights are
          soft-clipped (filmic shoulder) so the core is hot-white without banding in 8 bit.
  smoke : blend layer. straight alpha, colour bled into the transparent border (no dark fringe under bilinear filtering).
A single crop box (union over all frames) keeps the sprite centre fixed across the flipbook; frames are resampled
to --n evenly spaced frames when the render has more.
"""
import sys, os, glob, argparse
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("name")
ap.add_argument("--kind", default="fire"); ap.add_argument("--px", type=int, default=256)
ap.add_argument("--gain", type=float, default=1.0); ap.add_argument("--n", type=int, default=0)
ap.add_argument("--sheet", default=""); ap.add_argument("--pad", type=float, default=0.04)
ap.add_argument("--square", action="store_true"); ap.add_argument("--basefade", type=float, default=0.0); ap.add_argument("--cap", type=float, default=0.0); ap.add_argument("--skip", type=int, default=0); ap.add_argument("--edge", type=float, default=0.10); ap.add_argument("--fmt", default="tga"); ap.add_argument("--loopblend", type=int, default=0); ap.add_argument("--bright", type=float, default=1.0); ap.add_argument("--floor", type=float, default=0.0); ap.add_argument("--neutral", action="store_true")
ap.add_argument("--keepbottom", action="store_true", help="do not crop below the lowest lit pixel of frame 1 (flames sit on the ground)")
a = ap.parse_args()

files = sorted(glob.glob(os.path.join(a.src, "*.png")))[a.skip:]
if a.n and len(files) > a.n:
    idx = np.linspace(0, len(files) - 1, a.n).round().astype(int)
    files = [files[i] for i in idx]
frames = []
for f in files:
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535.0   # BGRA
    frames.append(im[..., [2, 1, 0, 3]])                                      # RGBA
if a.loopblend > 0:   # seamless loop: the last K frames are cross-faded into the first K, then dropped
    K = a.loopblend; L = len(frames) - K
    frames = [((1 - i / K) * frames[L + i] + (i / K) * frames[i]) if i < K else frames[i] for i in range(L)]
H, W = frames[0].shape[:2]
# union crop
mask = np.zeros((H, W), bool)
for fr in frames:
    lum = fr[..., :3].max(-1) if a.kind == "fire" else fr[..., 3]
    mask |= lum > (0.02 if a.kind == "fire" else 0.01)
ys, xs = np.where(mask)
y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
half = max(x1 - x0, y1 - y0) / 2 * (1 + a.pad)
if a.square or True:
    x0, x1, y0, y1 = int(cx - half), int(cx + half), int(cy - half), int(cy + half)
x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
side = min(x1 - x0, y1 - y0)
x1, y1 = x0 + side, y0 + side
os.makedirs(a.out, exist_ok=True)


def shoulder(x):
    x = np.maximum(x * a.gain, 0)
    return np.where(x < 0.6, x, 0.6 + 0.4 * (1 - np.exp(-(x - 0.6) / 0.4)))


outs = []
for k, fr in enumerate(frames):
    c = fr[y0:y1, x0:x1]
    c = cv2.resize(c, (a.px, a.px), interpolation=cv2.INTER_AREA)
    if a.kind == "fire":
        rgb = np.clip(shoulder(c[..., :3] * (1.0)), 0, 1)
        rgb = rgb ** (1 / 1.0)
        if a.basefade > 0:
            ramp = np.clip((1 - np.linspace(0, 1, a.px)) / a.basefade, 0, 1)[:, None, None] ** 1.5
            rgb = rgb * ramp
        out = np.dstack([rgb, np.ones(rgb.shape[:2], np.float32)])
    else:
        al = np.clip(c[..., 3], 0, 1)
        rgb = c[..., :3]
        if a.cap > 0:
            lum = rgb.mean(-1, keepdims=True)
            rgb = rgb * np.minimum(1.0, a.cap / np.maximum(lum, 1e-4))   # lit-core clamp: smoke must never out-shine the sky
        if a.neutral:   # the Blender smoke core is lit warm by the fireball light and reads as a flat tan disc: keep only its luminance
            lm = np.minimum(rgb.mean(-1, keepdims=True), a.cap if a.cap > 0 else 1.0)
            rgb = (0.07 + 0.22 * (1 - al[..., None]) ** 1.4 + 0.16 * lm) * np.array([1.0, 0.97, 0.93], np.float32)   # dense = dark, thin edge = lighter
        # bleed colour outward so transparent border pixels carry the nearby smoke colour
        w = (al > 0.02).astype(np.float32)
        acc = rgb * w[..., None]
        for r in (3, 9, 25):
            k_ = cv2.GaussianBlur(w, (0, 0), r) + 1e-6
            blur = np.dstack([cv2.GaussianBlur(acc[..., i], (0, 0), r) for i in range(3)]) / k_[..., None]
            rgb = np.where((w > 0)[..., None], rgb, blur)
            acc = rgb * np.maximum(w, (k_ > 1e-3).astype(np.float32))[..., None]
            w = np.maximum(w, (k_ > 1e-3).astype(np.float32))
        rgb = np.clip(rgb * a.bright + a.floor, 0, 1)
        out = np.dstack([np.clip(rgb, 0, 1), al])
    # border window: no sprite may reach its quad edge (a non-zero edge pixel draws the rectangle)
    wv = np.clip(np.minimum(np.arange(a.px), a.px - 1 - np.arange(a.px)) / (a.edge * a.px), 0, 1)
    wv = wv * wv * (3 - 2 * wv)
    win = np.outer(wv, wv).astype(np.float32)
    if a.kind == "fire":
        out[..., :3] *= win[..., None]
    else:
        out[..., 3] *= win
    u8 = (np.clip(out, 0, 1) ** 1.0 * 255 + 0.5).astype(np.uint8)
    p = os.path.join(a.out, "%s%03d.tga" % (a.name, k + 1))
    from PIL import Image as _I
    if a.fmt == "jpg":
        p = p[:-4] + ".jpg"
        _I.fromarray(u8[..., :3], 'RGB').save(p, quality=92, subsampling=0)
    else:
        _I.fromarray(u8, 'RGBA').save(p)
    outs.append(u8)
print("wrote", len(outs), "frames", a.px, "px ->", a.out, "crop", (x0, y0, x1, y1), "of", (W, H))
if a.sheet:
    n = len(outs); cols = min(n, 10); rows = (n + cols - 1) // cols; t = 128
    sh = np.full((rows * t, cols * t, 3), 18, np.uint8)
    for i, o in enumerate(outs):
        th = cv2.resize(o, (t, t), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        bg = np.full((t, t, 3), 0.07 if a.kind == "fire" else 0.45, np.float32)
        comp = th[..., :3] + bg if a.kind == "fire" else th[..., :3] * th[..., 3:] + bg * (1 - th[..., 3:])
        sh[(i // cols) * t:(i // cols + 1) * t, (i % cols) * t:(i % cols + 1) * t] = (np.clip(comp, 0, 1) * 255).astype(np.uint8)
    cv2.imwrite(a.sheet, sh[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 90])

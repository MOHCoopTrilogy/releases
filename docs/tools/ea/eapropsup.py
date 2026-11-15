#!/usr/bin/env python3
"""OPTIONAL local HD pass for the converted European Assault PROP textures (eaprops.py output) - runs on the PLAYER's
PC only, after the conversion, with the same upscaler as eacharup.py (Real-ESRGAN x4plus, ncnn-vulkan). Output goes
into its own pak (zzzz_ea_hdprops_<level>.pk3) that overrides the map pak's prop TGAs by load order.

The disc's prop textures are tiny (32-128 px) and ESRGAN alone is not enough for all of them (user 2026-11-15:
online CC0 sources allowed for the props, tinted to the disc). Recipes per texture (RECIPES, keyed by file name):
  * detail  - the disc texture is the picture: a tile-aware bicubic resample keeps its layout, colours, camouflage and
              markings exactly; only the fine high band (a Gaussian high-pass, luminance only, colourless) of a CC0
              material is added on top, at a fixed small amplitude. No new features: chips, rust and colour of the
              CC0 source never show. Sources (CC0 1.0, ambientCG) in hd/, listed in hd/CREDITS.txt.
  * esrgan  - eacharup.upscale_one (ESRGAN x4, colour-matched, clamped to the source's neighbourhood); then optionally
              a mild unsharp mask and CC0 grain masked to the dark rubber (tyres) or the rest (metal).
  * keep    - insignia and markings (the Balkenkreuz decal): a plain bicubic resample, never generated detail.
Any failure, no Vulkan GPU, a rejected texture -> that texture keeps its original.
usage: eapropsup.py <converted.pk3> <level> <out_pk3> <upscaler_dir>
"""
import json
import os
import sys
import tempfile
import zipfile

import numpy as np
from PIL import Image, ImageFilter

import eacharup

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP_TIME = (2002, 5, 28, 0, 0, 0)

# file name (without .tga) -> recipe. Approved per prop by the user (sheet SHEET_ea_panzer_offline_v2, 2026-11-15)
RECIPES = {
    "panzer_002": {"mode": "detail", "size": (1024, 1024),
                   "layers": [("PaintedMetal012", 7.0, 3.0, (1, 1)), ("Metal016", 4.0, 1.5, (1, 1))]},
    "panzer_001": {"mode": "detail", "size": (512, 1024),
                   "layers": [("PaintedMetal012", 7.0, 3.0, (1, 2)), ("Metal016", 4.0, 1.5, (1, 2))]},
    "panzer_003": {"mode": "esrgan", "size": 256, "sharpen": True,
                   "grain": [("Rubber004", 5.0, 1.2, "tyre"), ("Metal063", 6.0, 1.5, "metal")]},
    "panzer_004": {"mode": "esrgan", "size": 512, "sharpen": True,
                   "grain": [("Rubber004", 5.0, 1.2, "tyre"), ("Metal063", 6.0, 1.5, "metal")]},
    "panzer_005": {"mode": "esrgan"},
    "panzer_006": {"mode": "keep"},
}


def _cc0(name, size):
    p = os.path.join(HERE, "hd", "%s_1K_Color.jpg" % name)
    return np.asarray(Image.open(p).convert("L").resize(size, Image.LANCZOS)).astype(np.float32)


def _wrap_up(a, w, h):
    t = np.tile(a, (3, 3, 1))
    up = np.asarray(Image.fromarray(t).resize((3 * w, 3 * h), Image.BICUBIC)).astype(np.float32)
    return up[h:2 * h, w:2 * w]


def _hf_wrap(L, sigma):
    h, w = L.shape
    t = np.tile(L, (3, 3))
    b = np.asarray(Image.fromarray(t.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma))).astype(
        np.float32)
    return (t - b)[h:2 * h, w:2 * w]


def _detail(base, name, amp, sigma, reps=(1, 1), mask=None):
    H, W = base.shape[:2]
    L = _cc0(name, (max(1, W // reps[0]), max(1, H // reps[1])))
    L = np.tile(L, (reps[1], reps[0]))[:H, :W]
    d = _hf_wrap(L, sigma)
    d /= (d.std() + 1e-6)
    m = 1.0 if mask is None else mask[..., None]
    out = base.copy()
    out[..., :3] = base[..., :3] + amp * d[..., None] * m
    return out


def process(key, a, exe, tmp):
    """a: HxWx4 uint8 -> (HxWx4 uint8 or None, why)"""
    r = RECIPES.get(key)
    if not r:
        return None, "no recipe"
    h, w = a.shape[:2]
    if r["mode"] == "keep":
        return np.asarray(Image.fromarray(a).resize((w * 4, h * 4), Image.BICUBIC)), "kept (bicubic)"
    if r["mode"] == "detail":
        W, H = r["size"]
        b = _wrap_up(a, W, H)
        for name, amp, sig, reps in r["layers"]:
            b = _detail(b, name, amp, sig, reps)
        b[..., 3] = _wrap_up(a, W, H)[..., 3]
        return b.clip(0, 255).astype(np.uint8), "ok detail"
    if not exe:
        return None, "no upscaler"
    up, why = eacharup.upscale_one(exe, a, [], tmp)
    if up is None:
        return None, why
    up = up.astype(np.float32)
    if r.get("size"):
        s = r["size"]
        up = np.asarray(Image.fromarray(up.clip(0, 255).astype(np.uint8)).resize((s, s), Image.LANCZOS)).astype(np.float32)
    if r.get("sharpen"):
        im = Image.fromarray(up[..., :3].clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.UnsharpMask(radius=up.shape[1] / 64.0, percent=90, threshold=2))
        up[..., :3] = np.asarray(im).astype(np.float32)
    if r.get("grain"):
        lum = up[..., :3].mean(-1)
        mx, mn = up[..., :3].max(-1), up[..., :3].min(-1)
        sat = (mx - mn) / np.maximum(mx, 1.0)
        tyre = np.clip((60 - lum) / 25, 0, 1) * np.clip((0.35 - sat) / 0.2, 0, 1)
        for name, amp, sig, where in r["grain"]:
            up = _detail(up, name, amp, sig, mask=tyre if where == "tyre" else 1 - tyre)
    return up.clip(0, 255).astype(np.uint8), "ok esrgan"


def main(pk3, level, out_pk3, exe_dir):
    exe = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe") if exe_dir else None
    if exe and not os.path.exists(exe):
        exe = None
    z = zipfile.ZipFile(pk3)
    pre = "textures/ea_%s_props/" % level
    names = sorted(n for n in z.namelist() if n.startswith(pre) and n.endswith(".tga"))
    tmp = tempfile.mkdtemp(prefix="eapropsup_")
    report, files = {}, {}
    for n in names:
        key = n.rsplit("/", 1)[-1][:-4]
        try:
            res, why = process(key, eacharup.load_tga(z.read(n)), exe, tmp)
        except Exception as e:  # never fail the conversion
            res, why = None, "error %s" % e
        report[key] = why
        if res is not None:
            files[n] = eacharup.save_tga(res)
    if files:
        with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED) as o:
            for n in sorted(files):
                zi = zipfile.ZipInfo(n, ZIP_TIME)
                zi.compress_type = zipfile.ZIP_DEFLATED
                o.writestr(zi, files[n])
    with open(out_pk3 + ".report.json", "w") as f:
        json.dump(report, f, indent=0, sort_keys=True)
    print("props HD", sum(1 for v in report.values() if v.startswith(("ok", "kept"))), "of", len(report), "->", out_pk3)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3] if len(a) > 3 else None)

#!/usr/bin/env python3
"""OPTIONAL local upscale of converted Frontline textures - runs on the PLAYER's PC only (BYO disc: we never ship
Frontline-derived pixels). Output goes into its own pak (zzzz_fl_hdtex_<level>.pk3) that overrides the map pak's
TGAs by load order, so the map pak itself stays byte-identical for every player.

Upscaler: realesrgan-ncnn-vulkan (MIT; ncnn BSD-3; realesrgan-x4plus weights BSD-3, Real-ESRGAN repo), official
release v0.2.5.0 realesrgan-ncnn-vulkan-20220424-windows.zip sha256
abc02804e17982a3be33675e4d471e91ea374e65b70167abc09e31acb412802d.

Rules (docs/DECISIONS.md "ESRGAN is for photos and text, not chrome", TRAPS row 90):
  * skip signs / lettering / decals with text (fl_texmap.json "noupscale" per level) and textures with a
    texmap upgrade (those already use a mod-shipped HD texture)
  * tile-aware: wrap-pad by 1/4 on every side, upscale, crop - no seams on tiling textures
  * alpha is NOT sent through the network: nearest x4 + light blur, re-thresholded at 128 for cut-outs
  * reject (keep the original) on: black/blown frames, brightness drift > 12 %, a downscale-back mismatch, or
    hallucinated high-frequency "worm" detail (Laplacian energy far above a bicubic upscale)
  * 4x cap, then resampled to 512..1024 on the long side
  * no Vulkan / no GPU / any failure -> the level simply keeps its original textures
usage: flupscale.py <converted.pk3> <level> <out_pk3> <upscaler_dir> [--threads 1:1:1]
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP_TIME = (2002, 5, 28, 0, 0, 0)


def lap_energy(a):
    g = a.astype(np.float32).mean(axis=2)
    l = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float((l * l).mean())


def run_esrgan(exe, src, dst, threads):
    r = subprocess.run([exe, "-i", src, "-o", dst, "-n", "realesrgan-x4plus", "-s", "4", "-t", "128", "-j", threads],
                       cwd=os.path.dirname(exe), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=0x08000000, timeout=600)
    return r.returncode == 0 and os.path.exists(dst)


def upscale_one(exe, im, tmp, threads):
    rgba = im.convert("RGBA")
    w, h = rgba.size
    a = np.asarray(rgba)
    pw, ph = max(4, w // 4), max(4, h // 4)
    rgb = np.pad(a[:, :, :3], ((ph, ph), (pw, pw), (0, 0)), mode="wrap")
    src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
    Image.fromarray(rgb).save(src)
    if os.path.exists(dst):
        os.remove(dst)
    if not run_esrgan(exe, src, dst, threads):
        return None, "esrgan failed"
    up = np.asarray(Image.open(dst).convert("RGB"))
    up = up[ph * 4: ph * 4 + h * 4, pw * 4: pw * 4 + w * 4]
    up_im = Image.fromarray(up)
    # checks against the original
    orig = a[:, :, :3].astype(np.float32)
    back = np.asarray(up_im.resize((w, h), Image.BOX)).astype(np.float32)
    m0, m1 = orig.mean(), back.mean()
    if m1 < 8 or m1 > 247:
        return None, "black/blown frame"
    if abs(m1 - m0) / max(1.0, m0) > 0.12:
        return None, "brightness drift"
    if np.abs(back - orig).mean() > 14:
        return None, "downscale-back mismatch"
    bic = np.asarray(Image.fromarray(a[:, :, :3]).resize((w * 4, h * 4), Image.BICUBIC))
    if lap_energy(up) > 6.0 * max(1.0, lap_energy(bic)):
        return None, "worm-noise"
    long_side = max(w, h) * 4
    target = min(1024, max(512, max(w, h) * 4)) if long_side >= 512 else long_side
    sc = target / float(max(w, h) * 4)
    tw, th = max(1, int(round(w * 4 * sc))), max(1, int(round(h * 4 * sc)))
    out = up_im.resize((tw, th), Image.LANCZOS)
    alpha = a[:, :, 3]
    if alpha.min() < 250:
        al = Image.fromarray(alpha).resize((tw, th), Image.NEAREST).filter(ImageFilter.GaussianBlur(1.0))
        al_a = np.asarray(al)
        soft = ((alpha > 0) & (alpha < 250)).mean() > 0.10
        if not soft:
            al_a = np.where(al_a >= 128, 255, 0).astype(np.uint8)
        out = Image.fromarray(np.dstack([np.asarray(out), al_a]))
    return out, "ok"


def main(pk3, level, out_pk3, exe_dir, threads="1:1:1"):
    exe = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe")
    if not os.path.exists(exe):
        print("no upscaler - skipped")
        return 0
    tm = {}
    p = os.path.join(HERE, "fl_texmap.json")
    if os.path.exists(p):
        tm = json.load(open(p)).get(level, {})
    skip = set(tm.get("noupscale", [])) | {k for k in tm if not k.startswith("_") and k != "noupscale"}
    z = zipfile.ZipFile(pk3)
    names = sorted(n for n in z.namelist() if n.startswith(f"textures/fl/{level}/") and n.endswith(".tga"))
    tmp = tempfile.mkdtemp(prefix="flup_")
    report, files = {}, {}
    for n in names:
        key = n.rsplit("/", 1)[-1][:-4]
        if key in skip or key == "untextured":
            report[key] = "skipped (list)"
            continue
        try:
            im = Image.open(io.BytesIO(z.read(n)))
            res, why = upscale_one(exe, im, tmp, threads)
        except Exception as e:  # never fail the conversion
            res, why = None, "error %s" % e
        report[key] = why
        if res is not None:
            b = io.BytesIO()
            res.save(b, "TGA")
            files[n] = b.getvalue()
    if files:
        with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED) as o:
            for n in sorted(files):
                zi = zipfile.ZipInfo(n, ZIP_TIME)
                zi.compress_type = zipfile.ZIP_DEFLATED
                o.writestr(zi, files[n])
    with open(out_pk3 + ".report.json", "w") as f:
        json.dump(report, f, indent=0, sort_keys=True)
    ok = sum(1 for v in report.values() if v == "ok")
    print("upscaled", ok, "of", len(report), "->", out_pk3)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], a[a.index("--threads") + 1] if "--threads" in a else "1:1:1")

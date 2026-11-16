#!/usr/bin/env python3
"""OPTIONAL local upscale of the converted Frontline CHARACTER textures (flchar.py output) - runs on the
PLAYER's PC only, same upscaler and safety checks as flupscale.py (world textures). Output goes into its own pak
(zzzz_fl_hdchr_<level>.pk3) that overrides the map pak's character TGAs by load order.

The European Assault rules (eacharup.py, user decision 2026-11-13, option C), approved for Frontline 2026-11-15. Rules on top of flupscale's:
  * 4x, then capped at 2048 on the long side (a character atlas is 512..1024 already: the world cap would give
    nothing)
  * atlases do not tile: edge padding instead of wrap
  * ESRGAN x4plus smooths skin stubble and cloth weave to plastic: half of its own fine band is swapped for the
    bicubic original's fine band at the final size, and only 70 % of the difference to a plain bicubic is kept
  * QA clamp: no texel brighter or darker than the original's 3x3 neighbourhood (+-6) - no new highlights, and no
    faint pattern turned into hard lines (the German helmet cover's stripes)
  * lettering and insignia stay a plain bicubic resample: rectangles per texture in fl_charprotect.json
  * the alpha channel (blended '#a' pieces) is only resampled, never upscaled
  * any failure, no Vulkan GPU, a rejected texture -> that texture keeps its original
usage: flcharup.py <converted.pk3> <level> <out_pk3> <upscaler_dir>
"""
import io
import json
import os
import struct
import sys
import tempfile
import zipfile

import numpy as np
from PIL import Image, ImageFilter

import flupscale as fu

HERE = os.path.dirname(os.path.abspath(__file__))
ZIP_TIME = (2002, 5, 28, 0, 0, 0)
CAP = 2048
CAREFUL_SHARPEN = 0.6      # unsharp amount on the clean (bicubic) enlargement
CAREFUL_ESRGAN = 0.2       # share of the ESRGAN detail on top


def load_tga(b):
    w, h = struct.unpack_from("<HH", b, 12)
    a = np.frombuffer(b[18:18 + w * h * 4], np.uint8).reshape(h, w, 4)[:, :, [2, 1, 0, 3]]
    if not b[17] & 0x20:
        a = a[::-1]
    return np.ascontiguousarray(a)


def save_tga(a):
    """bottom-up rows (the engine ignores the TGA top-down flag; bug-11142)"""
    h, w = a.shape[:2]
    return (struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x08)
            + np.ascontiguousarray(a[::-1][:, :, [2, 1, 0, 3]]).tobytes())


def upscale_one(exe, a, protect, tmp, careful=()):
    h, w = a.shape[:2]
    pw, ph = max(4, w // 4), max(4, h // 4)
    rgb = np.pad(a[:, :, :3], ((ph, ph), (pw, pw), (0, 0)), mode="edge")
    src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
    Image.fromarray(rgb).save(src)
    if os.path.exists(dst):
        os.remove(dst)
    if not fu.run_esrgan(exe, src, dst, "1:1:1"):
        return None, "esrgan failed"
    up = np.asarray(Image.open(dst).convert("RGB"))[ph * 4: ph * 4 + h * 4, pw * 4: pw * 4 + w * 4]
    up = fu.colour_match(up, a[:, :, :3])
    orig = a[:, :, :3].astype(np.float32)
    back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
    if back.mean() < 8 or back.mean() > 247:
        return None, "black/blown frame"
    if abs(back.mean() - orig.mean()) / max(1.0, orig.mean()) > fu.DRIFT_LIMIT:
        return None, "brightness drift"
    if np.abs(back - orig).mean() > 14:
        return None, "downscale-back mismatch"
    bic = np.asarray(Image.fromarray(a[:, :, :3]).resize((w * 4, h * 4), Image.BICUBIC))
    if fu.lap_energy(up) > fu.WORM_LIMIT * max(1.0, fu.lap_energy(bic)):
        return None, "worm-noise"
    src_im = Image.fromarray(a[:, :, :3])
    mx = np.asarray(src_im.filter(ImageFilter.MaxFilter(3)).resize((w * 4, h * 4), Image.BILINEAR)).astype(np.int16)
    mn = np.asarray(src_im.filter(ImageFilter.MinFilter(3)).resize((w * 4, h * 4), Image.BILINEAR)).astype(np.int16)
    up = np.maximum(np.minimum(up.astype(np.int16), mx + 6), mn - 6).clip(0, 255).astype(np.uint8)
    for x0, y0, x1, y1 in protect:
        X0, Y0, X1, Y1 = int(x0 * w * 4), int(y0 * h * 4), int(x1 * w * 4), int(y1 * h * 4)
        up[Y0:Y1, X0:X1] = bic[Y0:Y1, X0:X1]
    sc = min(1.0, float(CAP) / (max(w, h) * 4))
    tw, th = int(round(w * 4 * sc)), int(round(h * 4 * sc))
    E = np.asarray(Image.fromarray(up).resize((tw, th), Image.LANCZOS)).astype(np.float32)
    Bf = np.asarray(src_im.resize((tw, th), Image.BICUBIC)).astype(np.float32)
    sig = 2.0 * tw / (w * 4.0)

    def hf(X):
        return X - np.asarray(Image.fromarray(X.clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(sig))).astype(np.float32)
    H = E - 0.7 * hf(E) + 1.0 * hf(Bf)
    out = (Bf + 0.7 * (H - Bf)).clip(0, 255).astype(np.uint8)
    if careful:
        # [user 2026-11-15] "careful" regions (a 32 px decal, the ammo belt): a clean enlargement, light unsharp
        # sharpening, a small share (20 %) of the ESRGAN detail, then held to the SOURCE's local colour range
        # (3x3 min/max, no margin) - nothing brighter or darker than the original texels around it, so no invented
        # feathers, letters or highlights. Same recipe as the world pass (shared with the look agent).
        r = max(0.6, 0.5 * tw / float(w))
        blur = np.asarray(Image.fromarray(Bf.clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(r))).astype(np.float32)
        C = Bf + CAREFUL_SHARPEN * (Bf - blur) + CAREFUL_ESRGAN * (E - Bf)
        cmx = np.asarray(src_im.filter(ImageFilter.MaxFilter(3)).resize((tw, th), Image.BILINEAR)).astype(np.float32)
        cmn = np.asarray(src_im.filter(ImageFilter.MinFilter(3)).resize((tw, th), Image.BILINEAR)).astype(np.float32)
        C = np.minimum(np.maximum(C, cmn), cmx).clip(0, 255).astype(np.uint8)
        for x0, y0, x1, y1 in careful:
            X0, Y0, X1, Y1 = int(x0 * tw), int(y0 * th), int(x1 * tw), int(y1 * th)
            out[Y0:Y1, X0:X1] = C[Y0:Y1, X0:X1]
    al = np.asarray(Image.fromarray(a[:, :, 3]).resize((tw, th), Image.BILINEAR))
    return np.dstack([out, al]), "ok"


def main(pk3, level, out_pk3, exe_dir):
    exe = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe")
    if not os.path.exists(exe):
        print("no upscaler - skipped")
        return 0
    p = os.path.join(HERE, "fl_charprotect.json")
    protect = json.load(open(p)) if os.path.exists(p) else {}
    z = zipfile.ZipFile(pk3)
    names = sorted(n for n in z.namelist() if n.startswith("textures/fl_%s_chr/" % level) and n.endswith(".tga"))
    tmp = tempfile.mkdtemp(prefix="flchup_")
    report, files = {}, {}
    for n in names:
        key = n.rsplit("/", 1)[-1][:-4]
        try:
            res, why = upscale_one(exe, load_tga(z.read(n)), protect.get(key, []), tmp,
                                   protect.get("_careful", {}).get(key, ()))
        except Exception as e:  # never fail the conversion
            res, why = None, "error %s" % e
        report[key] = why
        if res is not None:
            files[n] = save_tga(res)
    if files:
        with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED) as o:
            for n in sorted(files):
                zi = zipfile.ZipInfo(n, ZIP_TIME)
                zi.compress_type = zipfile.ZIP_DEFLATED
                o.writestr(zi, files[n])
    with open(out_pk3 + ".report.json", "w") as f:
        json.dump(report, f, indent=0, sort_keys=True)
    print("characters upscaled", sum(1 for v in report.values() if v == "ok"), "of", len(report), "->", out_pk3)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3])

#!/usr/bin/env python3
"""[flfix2] Tier-1 texture pass (user approved 2026-11-11, docs/proposals/flpolish_2026-11-10/TEXTURES.md).

Two treatments, both listed per level in fl_levels.json "hd":

  "swap"    homogeneous, tiling materials (cobbles, earth, slates, planks, rough stone) are redrawn with a CC0
            texture shipped beside the converter (hd/<asset>.jpg, Poly Haven, see hd/CREDITS.txt): see bake(). The
            new detail is tinted to the disc texture's mean colour and carries the disc texture's own low-frequency
            stains and patches, so the surface keeps its dirt instead of looking newly built. Geometry and texture
            coordinates are not touched.
  "cutout"  alpha-tested tree / bush cards: 4x Lanczos of the disc's own image, done here on the player's machine.
            The leaf colour is bled into the clear texels first, so the resample cannot pull the key colour into the
            edge (no dark or magenta halo), and the alpha is resampled with the colour so the cut edge is round
            instead of stair-stepped. No learned upscaler: nothing is invented.

Nothing disc-derived leaves the player's machine; a missing hd file or any failure keeps the disc's texture.
Runs on the converter's `files` dict just before the pak is written.
"""
import io
import os

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
HD_DIR = os.path.join(HERE, "hd")


def _tga(im):
    b = io.BytesIO()
    im.save(b, "TGA")
    return b.getvalue()


def tint(new_rgb, orig_mean, contrast=0.85):
    """the CC0 image carrying the original's mean colour; a little of its contrast is taken off so a sharp 1k
    texture does not read harsher than the soft level around it"""
    a = np.asarray(new_rgb, np.float64)
    m = a.reshape(-1, 3).mean(0)
    o = np.asarray(orig_mean, np.float64)
    a = (a - m) * contrast * (o.mean() / max(m.mean(), 1.0)) ** 0.5 + m * (o / np.maximum(m, 1.0))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def bleed(im, rounds=8):
    """RGBA cut-out: push the opaque texels' colour outwards into the clear ones (alpha untouched)"""
    a = np.asarray(im, np.float64)
    al = (a[:, :, 3:4] > 127).astype(np.float64)
    rgb = a[:, :, :3] * al
    w = al.copy()
    for _ in range(rounds):
        p = np.asarray(Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1)), np.float64)
        q = np.asarray(Image.fromarray(np.clip(w[:, :, 0] * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1)),
                       np.float64)[:, :, None] / 255.0
        fill = np.where(q > 1e-3, p / np.maximum(q, 1e-3), 0.0)
        got = w > 0.5
        rgb = np.where(got, rgb, fill)
        w = np.where(got, w, (q > 1e-3).astype(np.float64))
    rgb = np.where(w > 0.5, rgb, a[:, :, :3])
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a[:, :, 3]]).astype(np.uint8), "RGBA")


def upscale_cutout(im, k=4):
    im = bleed(im.convert("RGBA"))
    big = im.resize((im.width * k, im.height * k), Image.LANCZOS)
    rgb = big.convert("RGB").filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    rgb.putalpha(big.getchannel("A"))
    return rgb


def _wrap_blur(im, sigma):
    """Gaussian blur of a tiling image that wraps at the edges"""
    w, h = im.size
    big = Image.new("RGB", (3 * w, 3 * h))
    for x in range(3):
        for y in range(3):
            big.paste(im, (x * w, y * h))
    return big.filter(ImageFilter.GaussianBlur(sigma)).crop((w, h, 2 * w, 2 * h))


def bake(orig, tile, sw):
    """One repeat of the DISC texture, redrawn with the CC0 material: the new tile is repeated `repeat` times inside
    it (so the surfaces' texture coordinates stay the disc's), laid in `rows` offset courses when the original is
    built that way, and the original's own low-frequency colour (its stains, moss, dirt, lichen - a blur of the disc
    texture divided by its mean) is multiplied over it. The detail is new; where it is light and dark is the level's."""
    rx, ry = int(sw["repeat"][0]), int(sw["repeat"][1])
    rows = int(sw.get("rows", 1))
    o = orig.convert("RGB")
    mean = np.asarray(o, np.float64).reshape(-1, 3).mean(0)
    t = tint(tile.convert("RGB"), mean)
    px = min(1024, max(256, 4096 // max(rx, ry)))
    t = t.resize((px, px), Image.LANCZOS)
    W, H = px * rx, px * ry
    out = Image.new("RGB", (W, H))
    for x in range(rx):
        for y in range(ry):
            out.paste(t, (x * px, y * px))
    if rows > 1:                                     # courses of boards: each course a shifted copy, a shadow line between
        a = np.asarray(out, np.float64)
        rh = H // rows
        res = np.empty_like(a)
        for r in range(rows):
            band = np.asarray(out.resize((W, rh), Image.LANCZOS), np.float64)
            band = np.roll(band, (r * W * 5) // (rows * 8), axis=1)
            y = np.arange(rh, dtype=np.float64)
            sh = 1.0 - 0.55 * np.exp(-y / (rh * 0.012)) - 0.18 * np.exp(-(rh - 1 - y) / (rh * 0.03))
            res[r * rh:(r + 1) * rh] = band * sh[:, None, None]
        out = Image.fromarray(np.clip(res[:rows * rh], 0, 255).astype(np.uint8), "RGB").resize((W, H), Image.LANCZOS)
    k = float(sw.get("overlay", 1.0))
    if k > 0:
        lo = _wrap_blur(o, max(0.8, float(sw.get("blur", 0.045)) * o.width)).resize((W, H), Image.BICUBIC)
        ratio = np.asarray(lo, np.float64) / np.maximum(mean, 1.0)
        ratio = 1.0 + k * (np.clip(ratio, 0.45, 1.8) - 1.0)
        out = Image.fromarray(np.clip(np.asarray(out, np.float64) * ratio, 0, 255).astype(np.uint8), "RGB")
    if W > 4096 or H > 4096:
        out = out.resize((min(W, 4096), min(H, 4096)), Image.LANCZOS)
    return out


def _jpg(im):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=92, subsampling=0)
    return b.getvalue()


def apply(files, level, spec, mapname, log=print, hd_dir=HD_DIR):
    """files: the pak's name -> bytes dict (changed in place). Returns a small report."""
    rep = {"swapped": [], "cutouts": [], "skipped": []}
    hd = (spec or {}).get("hd")
    if not hd:
        return rep
    pre = "textures/fl/%s/" % level
    shn = "scripts/fl_%s.shader" % level
    sh = files[shn].decode("latin-1") if shn in files else None
    for key, sw in sorted(hd.get("swap", {}).items()):
        src = os.path.join(hd_dir, sw["asset"] + ".jpg")
        name = pre + key + ".tga"
        ref = "map " + name
        if name not in files or not os.path.isfile(src) or sh is None or sh.count(ref) != 1:
            rep["skipped"].append(key)
            continue
        try:                                         # stored as JPEG (opaque, large); the shader's map line follows
            img = _jpg(bake(Image.open(io.BytesIO(files[name])), Image.open(src), sw))
        except Exception as e:                       # keep the disc's texture
            log("flhd: swap %s failed: %s" % (key, e))
            rep["skipped"].append(key)
            continue
        del files[name]
        files[pre + key + ".jpg"] = img
        sh = sh.replace(ref, "map " + pre + key + ".jpg")
        rep["swapped"].append(key)
    if sh is not None:
        files[shn] = sh.encode("latin-1")
    for key in hd.get("cutout", []):
        name = pre + key + ".tga"
        if name not in files:
            rep["skipped"].append(key)
            continue
        try:
            files[name] = _tga(upscale_cutout(Image.open(io.BytesIO(files[name]))))
            rep["cutouts"].append(key)
        except Exception as e:
            log("flhd: cutout %s failed: %s" % (key, e))
            rep["skipped"].append(key)
    log("flhd: %d swapped, %d cut-outs upscaled, %d skipped" % (len(rep["swapped"]), len(rep["cutouts"]), len(rep["skipped"])))
    return rep

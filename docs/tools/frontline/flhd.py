#!/usr/bin/env python3
"""[flfix2] Tier-1 texture pass (user approved 2026-11-11, docs/proposals/flpolish_2026-11-10/TEXTURES.md).

Two treatments, both listed per level in fl_levels.json "hd":

  "swap"    homogeneous, tiling materials (cobbles, earth, slates, planks, rough stone) are replaced by a CC0
            texture shipped beside the converter (hd/<asset>.jpg, Poly Haven, see hd/CREDITS.txt). The replacement is
            tinted to the mean colour of the disc's own texture, so hue and value stay the level's, and the UVs of
            the surfaces that use it are multiplied by "repeat" so one tile covers about "tile" world units.
  "cutout"  alpha-tested tree / bush cards: 4x Lanczos of the disc's own image, done here on the player's machine.
            The leaf colour is bled into the clear texels first, so the resample cannot pull the key colour into the
            edge (no dark or magenta halo), and the alpha is resampled with the colour so the cut edge is round
            instead of stair-stepped. No learned upscaler: nothing is invented.

Nothing disc-derived leaves the player's machine; a missing hd file or any failure keeps the disc's texture.
Runs on the converter's `files` dict just before the pak is written.
"""
import io
import os
import struct

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
HD_DIR = os.path.join(HERE, "hd")
SHADER_SIZE = 140
VERT_SIZE = 44
SURF_FMT = "<12i3f9f2if"


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


def retile(bsp, scale):
    """multiply the texture coordinates of every surface whose shader is in `scale` (name -> (su, sv))"""
    bsp = bytearray(bsp)
    lumps = [struct.unpack_from("<ii", bsp, 12 + 8 * i) for i in range(28)]
    sh_o, sh_l = lumps[0]
    sf_o, sf_l = lumps[3]
    dv_o, dv_l = lumps[4]
    names = [bytes(bsp[sh_o + i:sh_o + i + 64]).split(b"\0")[0].decode("latin-1") for i in range(0, sh_l, SHADER_SIZE)]
    ssz = struct.calcsize(SURF_FMT)
    owner = {}
    n = 0
    for i in range(0, sf_l - ssz + 1, ssz):
        s = struct.unpack_from("<12i", bsp, sf_o + i)
        if not 0 <= s[0] < len(names):
            raise ValueError("surface shader index out of range")
        sc = scale.get(names[s[0]])
        for v in range(s[3], s[3] + s[4]):
            prev = owner.get(v)
            if prev is not None:
                if prev != sc:
                    raise ValueError("a vertex is shared by surfaces with different tiling")
                continue
            owner[v] = sc
            if sc:
                o = dv_o + v * VERT_SIZE + 12
                u, w = struct.unpack_from("<2f", bsp, o)
                struct.pack_into("<2f", bsp, o, u * sc[0], w * sc[1])
                n += 1
    return bytes(bsp), n


def apply(files, level, spec, mapname, log=print, hd_dir=HD_DIR):
    """files: the pak's name -> bytes dict (changed in place). Returns a small report."""
    rep = {"swapped": [], "cutouts": [], "skipped": []}
    hd = (spec or {}).get("hd")
    if not hd:
        return rep
    pre = "textures/fl/%s/" % level
    new = {}
    scale = {}
    for key, sw in sorted(hd.get("swap", {}).items()):
        src = os.path.join(hd_dir, sw["asset"] + ".jpg")
        name = pre + key + ".tga"
        if name not in files or not os.path.isfile(src):
            rep["skipped"].append(key)
            continue
        try:
            o = np.asarray(Image.open(io.BytesIO(files[name])).convert("RGB"), np.float64).reshape(-1, 3).mean(0)
            new[name] = _tga(tint(Image.open(src).convert("RGB"), o))
            scale[pre + key] = (int(sw["repeat"][0]), int(sw["repeat"][1]))
            rep["swapped"].append(key)
        except Exception as e:                       # keep the disc's texture
            log("flhd: swap %s failed: %s" % (key, e))
            rep["skipped"].append(key)
    for key in hd.get("cutout", []):
        name = pre + key + ".tga"
        if name not in files:
            rep["skipped"].append(key)
            continue
        try:
            new[name] = _tga(upscale_cutout(Image.open(io.BytesIO(files[name]))))
            rep["cutouts"].append(key)
        except Exception as e:
            log("flhd: cutout %s failed: %s" % (key, e))
            rep["skipped"].append(key)
    bspn = "maps/%s.bsp" % mapname
    try:
        bsp, n = retile(files[bspn], {k: v for k, v in scale.items() if v != (1, 1)})
    except Exception as e:                           # all or nothing: tiling and image must change together
        log("flhd: re-tile failed (%s) - swaps dropped, cut-outs kept" % e)
        for key in rep["swapped"]:
            new.pop(pre + key + ".tga", None)
        rep["skipped"] += rep["swapped"]
        rep["swapped"] = []
        bsp, n = files[bspn], 0
    files[bspn] = bsp
    files.update(new)
    rep["retiled_verts"] = n
    log("flhd: %d swapped, %d cut-outs upscaled, %d skipped, %d verts re-tiled" % (
        len(rep["swapped"]), len(rep["cutouts"]), len(rep["skipped"]), n))
    return rep

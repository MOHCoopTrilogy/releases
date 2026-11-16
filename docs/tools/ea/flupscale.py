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
  * alpha-tested cut-out cards (foliage, tree cards) are NOT upscaled: ESRGAN erodes and thins the leaf clusters
  * the output is colour-matched to the original (per-channel mean/std) - ESRGAN darkens bark and hedges
  * reject (keep the original) on: black/blown frames, brightness drift > 12 % after the match, a
    downscale-back mismatch, or hallucinated "worm" detail (Laplacian energy > 60x a bicubic upscale)
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
GAME = os.environ.get("HZM_GAME", "fl")     # fl = Frontline, ea = European Assault (same pipeline)
ZIP_TIME = (2002, 5, 28, 0, 0, 0)



def careful_up(src_rgb, up_rgb, share=0.2):
    """[user 2026-11-15 "You can upscale the ones you are worried about inventing as long as you are careful about it"]
    a conservative 4x for textures whose plain or soft upscale invented shapes (glyphs, swirls, holes, cracks, sparkle):
    mostly a clean enlargement (Lanczos plus a light unsharp mask), with only `share` of ESRGAN's own fine band on top,
    the result held tightly to the source's local colour range (its 3x3 min / max, smoothed, +-4). up_rgb may be None
    (no ESRGAN detail at all). -> uint8 (4h, 4w, 3)"""
    h, w = src_rgb.shape[:2]
    lz = np.asarray(Image.fromarray(src_rgb).resize((w * 4, h * 4), Image.LANCZOS)).astype(np.float32)
    bl = np.asarray(Image.fromarray(np.clip(lz, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)
    out = lz + 0.5 * (lz - bl)
    if up_rgb is not None and share > 0:
        u = up_rgb.astype(np.float32)
        ub = np.asarray(Image.fromarray(np.clip(u, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)
        out = out + share * (u - ub)
    s = Image.fromarray(src_rgb)

    def _sm(im):
        return np.asarray(im.resize((w * 4, h * 4), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)
    lo_ = _sm(s.filter(ImageFilter.MinFilter(3))) - 4.0
    hi_ = _sm(s.filter(ImageFilter.MaxFilter(3))) + 4.0
    return np.clip(np.minimum(np.maximum(out, lo_), hi_), 0, 255).astype(np.uint8)


def lap_energy(a):
    g = a.astype(np.float32).mean(axis=2)
    l = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float((l * l).mean())


# [flfix2 2026-11-12, upscale on by default] ONE ESRGAN process per level. Starting the exe per texture cost ~1.8 s of
# GPU and model start-up each (543 textures: 16 min on an RTX 5070 Ti). main() now runs every texture twice: pass
# "collect" files each ESRGAN input under its texture key, one batch run upscales the folder, pass "use" reads the result.
BATCH = {"mode": None, "key": None, "in": None, "out": None}


def _esrgan(exe, src, dst, threads, timeout):
    try:
        # [look QA 2026-11-12] 512 px tiles: 128 px tiles left square seams in noisy ground (EA PUfh_NMVX)
        r = subprocess.run([exe, "-i", src, "-o", dst, "-n", "realesrgan-x4plus", "-s", "4", "-t", "512", "-j", threads,
                            "-f", "png"], cwd=os.path.dirname(exe), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=0x08000000 | 0x00000040, timeout=timeout)   # no window, IDLE_PRIORITY_CLASS
    except Exception:
        return False
    return r.returncode == 0 and os.path.exists(dst)


def run_esrgan(exe, src, dst, threads):
    if BATCH["mode"] == "collect":
        import shutil
        shutil.copyfile(src, os.path.join(BATCH["in"], BATCH["key"] + ".png"))
        return False
    if BATCH["mode"] == "use":
        import shutil
        got = os.path.join(BATCH["out"], BATCH["key"] + ".png")
        if not os.path.exists(got):
            return False
        shutil.copyfile(got, dst)
        return True
    return _esrgan(exe, src, dst, threads, 600)


def gpu_ok(exe, tmp, threads):
    """the upscaler needs a Vulkan GPU (this build has no CPU path: -g -1 is 'invalid gpu device'). A 16 px probe
    decides once; no GPU, no driver, a crash or a hang -> the pass is skipped and the conversion goes on."""
    src, dst = os.path.join(tmp, "probe_in.png"), os.path.join(tmp, "probe_out.png")
    Image.new("RGB", (16, 16), (90, 80, 70)).save(src)
    return _esrgan(exe, src, dst, threads, 60)


WORM_LIMIT = 60.0      # Laplacian energy vs a bicubic x4; real ESRGAN detail on 64-256px textures sits ~5..40x
DRIFT_LIMIT = 0.12     # mean brightness drift allowed AFTER the colour match


def colour_match(up, orig):
    """per-channel mean/std transfer of the ESRGAN output onto the original's statistics (ESRGAN darkens
    dark organic textures - bark, hedges); statistics are taken on the downscaled-back image vs the original"""
    h, w = orig.shape[:2]
    back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
    o = orig.astype(np.float32)
    out = up.astype(np.float32)
    for c in range(3):
        bm, bs = back[:, :, c].mean(), back[:, :, c].std()
        om, osd = o[:, :, c].mean(), o[:, :, c].std()
        g = (osd / bs) if bs > 1e-3 else 1.0
        g = min(2.0, max(0.5, g))
        out[:, :, c] = (out[:, :, c] - bm) * g + om
    return np.clip(out, 0, 255).astype(np.uint8)


def is_cutout(a):
    """alpha-tested card (foliage, tree cards, fences): a real share of fully transparent texels"""
    al = a[:, :, 3]
    return al.min() < 250 and (al < 128).mean() > 0.05


# [look 2026-11-12] ported from the Frontline flupscale (same rules, same QA clamp)
def _bleed(im, rounds=8):
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


def upscale_cutout(exe, a, tmp, threads, pre=1):
    """[flfix2 look 2026-11-12] alpha-tested cards (tree lines, branches, bushes): ESRGAN on the COLOUR only, the cut
    edge from the original alpha. ESRGAN run on the whole card ate the leaf clusters (fewer, smaller leaves) because the
    key colour around them read as background; here the leaf colour is bled into the clear texels first (flhd.bleed), so
    ESRGAN sees one continuous foliage picture and only adds needle and leaf detail. The silhouette is the original's
    alpha resampled smoothly and cut at 128 (what alphaFunc GE128 draws): round edges, no stair steps, nothing eroded.
    pre: the card in the pak is already a flhd 4x Lanczos copy - it is boxed back down by `pre` first."""
    im = Image.fromarray(a, "RGBA")
    if pre > 1:
        im = im.resize((max(1, im.width // pre), max(1, im.height // pre)), Image.BOX)
    w, h = im.size
    a0 = np.asarray(im)[:, :, 3]
    if pre > 1:     # a flhd card is alpha-tested (GE128): its Lanczos-softened edge is not a blend
        im.putalpha(Image.fromarray(np.where(a0 >= 128, 255, 0).astype(np.uint8)))
        a0 = np.asarray(im)[:, :, 3]
    if ((a0 > 8) & (a0 < 247)).mean() > 0.10:
        # shadow blobs, scorch decals, haze cards, fire / smoke / flare sprites: the soft-alpha pass (upscale_blended)
        if pre > 1 or os.environ.get("FLUP_NO_BLENDED") or NOSOFT.get("cur"):
            return None, "cutout: blended (soft alpha) kept original"
        return upscale_blended(exe, np.asarray(im), tmp, threads)
    # [look QA 2026-11-12] fine leaf sprays stay as they are: on cards that are mostly leaf edge (more than 55 % of the solid
    # texels touch a clear one) and leaf-coloured, ESRGAN plus the rounded cut turned single leaves into blobs ('AI look' on
    # 12c380, 1dd980, c0_16dc00, 15b680, 124280). Dense foliage (tree lines, hedges), ruins, fences and iron work still pass.
    sol_ = a0 >= 128
    in_ = sol_.copy()
    in_[1:, :] &= sol_[:-1, :]; in_[:-1, :] &= sol_[1:, :]; in_[:, 1:] &= sol_[:, :-1]; in_[:, :-1] &= sol_[:, 1:]
    if sol_.sum() and (sol_ & ~in_).sum() / float(sol_.sum()) > 0.55:
        rgb_ = np.asarray(im)[:, :, :3][sol_].astype(np.float32)
        mr, mg, mb = rgb_.mean(0)
        if mg >= 0.9 * mr and mg > mb * 1.1:
            return None, "cutout: fine leaf spray kept original"
    base = np.asarray(_bleed(im))
    pw, ph = max(4, w // 4), max(4, h // 4)
    rgb = np.pad(base[:, :, :3], ((ph, ph), (pw, pw), (0, 0)), mode="wrap")
    src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
    Image.fromarray(rgb).save(src)
    if os.path.exists(dst):
        os.remove(dst)
    if not run_esrgan(exe, src, dst, threads):
        return None, "esrgan failed"
    up = np.asarray(Image.open(dst).convert("RGB"))[ph * 4: ph * 4 + h * 4, pw * 4: pw * 4 + w * 4]
    al0 = base[:, :, 3]
    solid = al0 >= 128
    # colour statistics on the leaves only (the bled border is not part of the picture)
    back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
    o = base[:, :, :3].astype(np.float32)
    out = up.astype(np.float32)
    if solid.sum() < 16:
        return None, "cutout: no solid texels"
    for c in range(3):
        bm, bs = back[:, :, c][solid].mean(), back[:, :, c][solid].std()
        om, osd = o[:, :, c][solid].mean(), o[:, :, c][solid].std()
        g = min(2.0, max(0.5, (osd / bs) if bs > 1e-3 else 1.0))
        out[:, :, c] = (out[:, :, c] - bm) * g + om
    # [look QA 2026-11-12] no new highlights or colours: every output texel stays inside the range of the source texels
    # around it (3x3 min / max of the bled card, smoothly enlarged). ESRGAN otherwise lit leaf edges with bright yellow-green
    # speckles and rounded the leaves into blobs ('AI look' on 12c380, 1dd980, c0_16dc00, 15b680).
    src_rgb = Image.fromarray(base[:, :, :3])
    lo_ = np.asarray(src_rgb.filter(ImageFilter.MinFilter(3)).resize((w * 4, h * 4), Image.BILINEAR)).astype(np.float32)
    hi_ = np.asarray(src_rgb.filter(ImageFilter.MaxFilter(3)).resize((w * 4, h * 4), Image.BILINEAR)).astype(np.float32)
    out = np.minimum(np.maximum(out, lo_), hi_)
    up = np.clip(out, 0, 255).astype(np.uint8)
    back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
    m0, m1 = o[solid].mean(), back[solid].mean()

    def _sat(a):
        mx_, mn_ = a.max(axis=-1), a.min(axis=-1)
        return (mx_ - mn_) / np.maximum(mx_, 1.0)
    # and no card gets more saturated or brighter in its top end than the source (the speckle tell)
    big_solid = np.asarray(Image.fromarray((solid * 255).astype(np.uint8)).resize((w * 4, h * 4), Image.NEAREST)) > 127
    if _sat(up.astype(np.float32))[big_solid].mean() > _sat(o)[solid].mean() * 1.08 + 0.01:
        return None, "cutout: more saturated than the source"
    if np.percentile(up.astype(np.float32).mean(-1)[big_solid], 99) > np.percentile(o.mean(-1)[solid], 99) + 6:
        return None, "cutout: brighter highlights than the source"
    if abs(m1 - m0) / max(1.0, m0) > DRIFT_LIMIT:
        return None, "cutout: brightness drift"
    if np.abs(back - o)[solid].mean() > 14:
        return None, "cutout: downscale-back mismatch"
    bic = np.asarray(Image.fromarray(base[:, :, :3]).resize((w * 4, h * 4), Image.BICUBIC))
    ratio = lap_energy(up) / max(1.0, lap_energy(bic))
    # dense foliage carries real high-frequency detail: the fir tree-line card measured 107x and showed needles, not worms,
    # on the QA sheet (H:/hzm_work/flpolish/look/cut_qa.jpg), so cards get a wider limit than opaque surfaces
    if ratio > 2.5 * WORM_LIMIT and not os.environ.get("FLUP_DEBUG"):
        return None, "cutout: worm-noise %.0fx" % ratio
    al = Image.fromarray(al0).resize((w * 4, h * 4), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2.4))   # half a source texel: rounds the stair steps
    al = np.where(np.asarray(al) >= 128, 255, 0).astype(np.uint8)
    # the same share of the card must stay solid (an eroded or swollen silhouette is a reject)
    if abs(float((al > 0).mean()) - float(solid.mean())) > 0.03:
        return None, "cutout: silhouette changed"
    # thin features (wrought iron, twigs, fence wires) must survive: boxed back down, every solid texel stays solid
    kept = np.asarray(Image.fromarray(al).resize((w, h), Image.BOX)) >= 64
    if solid.sum() and float((solid & ~kept).sum()) / float(solid.sum()) > 0.05:
        return None, "cutout: thin features lost"
    t = min(1024, w * 4) / float(w * 4)
    res = Image.fromarray(np.dstack([up, al]), "RGBA")
    if t < 1.0:
        res = res.resize((int(round(w * 4 * t)), int(round(h * 4 * t))), Image.LANCZOS)
        r_ = np.asarray(res).copy()
        r_[:, :, 3] = np.where(r_[:, :, 3] >= 128, 255, 0)
        res = Image.fromarray(r_, "RGBA")
    return res, "ok cutout"


def _gblur(x, s):
    return np.asarray(Image.fromarray(np.clip(x, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s))).astype(np.float32)


def _soft_bleed(a, thr=24, rounds=12):
    """[2026-11-15] edge padding for a soft-alpha sprite: the colour of the texels that show (alpha >= thr) pushed out
    into the near-clear ones, so ESRGAN and bilinear filtering never pull the key colour (black / white) into the rim"""
    al = a[:, :, 3]
    im = Image.fromarray(np.dstack([a[:, :, :3], np.where(al >= thr, 255, 0).astype(np.uint8)]).astype(np.uint8), "RGBA")
    return np.asarray(_bleed(im, rounds))[:, :, :3]


def upscale_blended(exe, a, tmp, threads):
    """[user 2026-11-15 "everything", coordinator: the stock-HD agent's sprite fix] soft-alpha cards and effect sprites
    (fire, smoke, flares, glows, haze): ESRGAN on the edge-padded colour, the alpha enlarged smoothly (Lanczos - a blend,
    not a cut), the colour kept inside the source's own local range (no new highlights or hues) and matched on the texels
    that show. A sprite's world size is its image width x spritescale (tr_sprite.c): main() re-emits every spriteGen
    shader whose stage-0 image grew with spritescale * old_w / new_w, so the particles keep their size."""
    h, w = a.shape[:2]
    al0 = a[:, :, 3].astype(np.float32)
    vis = al0 >= 24
    if vis.sum() < 16:
        return None, "blended: almost clear"
    base = _soft_bleed(a)
    pw, ph = max(4, w // 4), max(4, h // 4)
    rgb = np.pad(base, ((ph, ph), (pw, pw), (0, 0)), mode="edge")
    src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
    Image.fromarray(rgb).save(src)
    if os.path.exists(dst):
        os.remove(dst)
    if not run_esrgan(exe, src, dst, threads):
        return None, "esrgan failed"
    up = np.asarray(Image.open(dst).convert("RGB"))[ph * 4: ph * 4 + h * 4, pw * 4: pw * 4 + w * 4].astype(np.float32)
    o = base.astype(np.float32)
    wgt = al0 / 255.0
    back = np.asarray(Image.fromarray(np.clip(up, 0, 255).astype(np.uint8)).resize((w, h), Image.BOX)).astype(np.float32)
    for c in range(3):
        sw = max(1e-3, wgt.sum())
        bm, om = (back[:, :, c] * wgt).sum() / sw, (o[:, :, c] * wgt).sum() / sw
        bs = np.sqrt(((back[:, :, c] - bm) ** 2 * wgt).sum() / sw); osd = np.sqrt(((o[:, :, c] - om) ** 2 * wgt).sum() / sw)
        g = min(2.0, max(0.5, (osd / bs) if bs > 1e-3 else 1.0))
        up[:, :, c] = (up[:, :, c] - bm) * g + om
    src_rgb = Image.fromarray(base)
    lo_ = np.asarray(src_rgb.filter(ImageFilter.MinFilter(3)).resize((w * 4, h * 4), Image.BILINEAR)).astype(np.float32)
    hi_ = np.asarray(src_rgb.filter(ImageFilter.MaxFilter(3)).resize((w * 4, h * 4), Image.BILINEAR)).astype(np.float32)
    up = np.clip(np.minimum(np.maximum(up, lo_), hi_), 0, 255).astype(np.uint8)
    al = np.asarray(Image.fromarray(a[:, :, 3]).resize((w * 4, h * 4), Image.LANCZOS))
    # what the sprite draws (colour x alpha), boxed back, against the source's
    pm_up = up.astype(np.float32) * (al[:, :, None] / 255.0)
    pm_back = np.asarray(Image.fromarray(np.clip(pm_up, 0, 255).astype(np.uint8)).resize((w, h), Image.BOX)).astype(np.float32)
    pm_o = a[:, :, :3].astype(np.float32) * (al0[:, :, None] / 255.0)
    m0, m1 = pm_o.mean(), pm_back.mean()
    if abs(m1 - m0) / max(1.0, m0) > DRIFT_LIMIT:
        return None, "blended: brightness drift"
    if np.abs(pm_back - pm_o).mean() > 10:
        return None, "blended: downscale-back mismatch"
    bic = np.asarray(Image.fromarray(base).resize((w * 4, h * 4), Image.BICUBIC))
    ratio = lap_energy(up) / max(1.0, lap_energy(bic))
    if ratio > 2.5 * WORM_LIMIT:
        return None, "blended: worm-noise %.0fx" % ratio
    res = Image.fromarray(np.dstack([up, al]), "RGBA")
    t = min(1024, w * 4) / float(w * 4)
    if t < 1.0:
        res = res.resize((int(round(w * 4 * t)), int(round(h * 4 * t))), Image.LANCZOS)
    return res, "ok blended"


def _soft_retry(a, up, bic, why):
    """[2026-11-15, user: "everything ... if it doesn't look bad"] an opaque texture the plain upscale failed on gets
    softer blends of the same ESRGAN output, each through the same checks: grain lost -> the source's own grain
    (bicubic high band) laid back over it; worm noise -> ESRGAN's detail damped toward the bicubic; the rest -> a half
    mix. None passing keeps the original. -> (uint8 image, label) or (None, None)"""
    up = up.astype(np.float32); bic = bic.astype(np.float32)
    if why.startswith("detail lost"):
        cands = [("grain", up + 1.0 * (bic - _gblur(bic, 3.0))), ("grain+", up + 1.6 * (bic - _gblur(bic, 3.0))),
                 ("mix50", 0.5 * up + 0.5 * bic)]
    elif why.startswith("worm"):
        cands = [("damp35", bic + 0.35 * (up - _gblur(up, 2.0))), ("mix50", 0.5 * up + 0.5 * bic),
                 ("damp20", bic + 0.2 * (up - _gblur(up, 2.0)))]
    else:
        cands = [("mix50", 0.5 * up + 0.5 * bic)]
    # no new highlights or hues: every texel stays inside the source's own 3x3 min / max, enlarged (the cut-out rule).
    # The QA sheet showed sparkle specks on lichen and chrome (ZSsw_*, zrKa, bkKs) without it.
    # The corridor is the 5x5 min / max, smoothed and widened by a margin: a tight 3x3 corridor drew a cell mosaic
    # over ground grain (second QA sheet, ir4r / nTAR).
    h, w = a.shape[:2]
    src_rgb = Image.fromarray(a[:, :, :3])
    lo_ = _gblur(np.asarray(src_rgb.filter(ImageFilter.MinFilter(5)).resize((w * 4, h * 4), Image.BICUBIC)), 3.0) - 10.0
    hi_ = _gblur(np.asarray(src_rgb.filter(ImageFilter.MaxFilter(5)).resize((w * 4, h * 4), Image.BICUBIC)), 3.0) + 10.0
    for nm, c in cands:
        c8 = np.clip(np.minimum(np.maximum(c, lo_), hi_), 0, 255).astype(np.uint8)
        if _opaque_qa(c8, a) is None:
            return c8, nm
    return None, None


def _opaque_qa(up, a):
    h, w = a.shape[:2]
    orig = a[:, :, :3].astype(np.float32)
    back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
    m0, m1 = orig.mean(), back.mean()
    if m1 < 8 or m1 > 247:
        return "black/blown frame"
    if abs(m1 - m0) / max(1.0, m0) > DRIFT_LIMIT:
        return "brightness drift"
    if np.abs(back - orig).mean() > 14:
        return "downscale-back mismatch"
    # [look QA 2026-11-12] ESRGAN reads fine gravel / snow grain as noise and smooths it away: keep the original when the
    # result, boxed back to the source size, has lost more than half of the source's fine detail
    if lap_energy(back) < 0.5 * lap_energy(orig):
        return "detail lost (smoothed)"
    bic = np.asarray(Image.fromarray(a[:, :, :3]).resize((w * 4, h * 4), Image.BICUBIC))
    if lap_energy(up) > WORM_LIMIT * max(1.0, lap_energy(bic)):
        return "worm-noise"
    return None


def upscale_one(exe, im, tmp, threads):
    rgba = im.convert("RGBA")
    w, h = rgba.size
    a = np.asarray(rgba)
    if is_cutout(a):
        # alpha-tested cards: colour-only pass, original silhouette (upscale_cutout); fine leaf sprays keep the original
        return upscale_cutout(exe, a, tmp, threads, 1)
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
    up = colour_match(up, a[:, :, :3])
    # checks against the original (after the colour match); a failed plain upscale gets the soft retry (_soft_retry)
    why = _opaque_qa(up, a)
    how = "ok"
    if why:
        bic = np.asarray(Image.fromarray(a[:, :, :3]).resize((w * 4, h * 4), Image.BICUBIC))
        up, lab = (None, None) if (os.environ.get("FLUP_NO_SOFT") or NOSOFT.get("cur")) else _soft_retry(a, up, bic, why)
        if up is None:
            return None, why
        how = "ok soft %s (was %s)" % (lab, why.split(" (")[0])
    up_im = Image.fromarray(up)
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
    return out, how


NOSOFT = {"keys": set(), "cur": False}     # texmap "nosoft": keep the original rather than a soft retry (QA sheet)



def careful_one(exe, im, tmp, threads, share=0.2):
    """[user 2026-11-15: "upscale the ones you are worried about inventing as long as you are careful about it", "Just
    double check the text"] the conservative 4x for held-back textures (texmap "nosoft" and the lettered "noupscale"
    sheets): careful_up on the colour (Lanczos + light unsharp + `share` of ESRGAN's fine band, held to the source's
    3x3 colour range; share 0 = a plain enlargement), the alpha resampled (smooth for blended sprites, the original
    silhouette cut at 128 for alpha-tested cards). Checked per item on side-by-side sheets (letters must read the same)."""
    a = np.asarray(im.convert("RGBA"))
    h, w = a.shape[:2]
    al0 = a[:, :, 3]
    has_a = al0.min() < 250
    soft = has_a and ((al0 > 8) & (al0 < 247)).mean() > 0.10
    rgb = _soft_bleed(a) if has_a else a[:, :, :3].copy()
    up = None
    if share > 0:
        pw, ph = max(4, w // 4), max(4, h // 4)
        src, dst = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
        Image.fromarray(np.pad(rgb, ((ph, ph), (pw, pw), (0, 0)), mode="edge" if has_a else "wrap")).save(src)
        if os.path.exists(dst):
            os.remove(dst)
        if run_esrgan(exe, src, dst, threads):
            up = colour_match(np.asarray(Image.open(dst).convert("RGB"))[ph * 4: ph * 4 + h * 4, pw * 4: pw * 4 + w * 4], rgb)
        elif BATCH["mode"] == "collect":
            return None, "collect"
    c = careful_up(rgb, up, share if up is not None else 0.0)
    res = Image.fromarray(c)
    if has_a:
        if soft:
            al = Image.fromarray(al0).resize((w * 4, h * 4), Image.LANCZOS)
        else:
            al = Image.fromarray(al0).resize((w * 4, h * 4), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2.4))
            al = Image.fromarray(np.where(np.asarray(al) >= 128, 255, 0).astype(np.uint8))
        res = Image.fromarray(np.dstack([c, np.asarray(al)]), "RGBA")
    t = min(1024, w * 4) / float(w * 4)
    if t < 1.0:
        res = res.resize((int(round(w * 4 * t)), int(round(h * 4 * t))), Image.LANCZOS)
    return res, "ok careful%s" % ("" if share > 0 and up is not None else " plain")



KEEPDISC, PLAINTEXT, CAREFUL_TEXT = set(), set(), set()   # texmap "keepdisc" / "plaintext"; noupscale keys that get careful_one

def _main_one(z, n, key, skip, report, files, exe, tmp, threads, cut_pre):
    NOSOFT["cur"] = key in NOSOFT["keys"]
    if key in KEEPDISC or key == "untextured" or (key in skip and key not in CAREFUL_TEXT):
        report[key] = "skipped (list)"
        return
    try:
        im = Image.open(io.BytesIO(z.read(n)))
        if key in skip or NOSOFT["cur"]:
            # held back (lettered sheets, or a soft retry that invented shapes): the careful 4x
            res, why = careful_one(exe, im, tmp, threads, 0.0 if key in PLAINTEXT else 0.2)
        else:
            res, why = upscale_one(exe, im, tmp, threads, )
    except Exception as e:  # never fail the conversion
        res, why = None, "error %s" % e
    if BATCH["mode"] == "collect":
        return
    if res is None and not why.startswith(("skipped", "error", "esrgan failed")) and not os.environ.get("FLUP_NO_CAREFUL"):
        # [user 2026-11-15 "everything", "as long as you are careful about it"] anything the normal passes rejected (snow
        # masks, leaf sprays, over-saturated cards, a drifting sprite) takes the careful 4x rather than the disc image
        try:
            res, w2 = careful_one(exe, Image.open(io.BytesIO(z.read(n))), tmp, threads, 0.0 if key in PLAINTEXT else 0.2)
            why = "%s (was %s)" % (w2, why)
        except Exception as e:
            res, why = None, "%s; careful error %s" % (why, e)
    report[key] = why
    if res is not None:
        b = io.BytesIO()
        res.save(b, "TGA")
        files[n] = b.getvalue()


def sprite_shaders(z, files):
    """[2026-11-15] a sprite's world size is its stage-0 image width x spritescale (tr_sprite.c, TRAPS row 294): every
    spriteGen shader of the map pak whose stage-0 image this pass enlarged is re-emitted with spritescale * old_w / new_w
    (the highest-priority pak's definition wins on both renderers), so an upscaled fire or smoke particle keeps its size"""
    import re
    grown = {}
    for n, b in files.items():
        if n.lower().endswith(".tga"):
            try:
                ow = Image.open(io.BytesIO(z.read(n))).width
                nw = Image.open(io.BytesIO(b)).width
            except Exception:
                continue
            if nw != ow:
                grown[n[:-4].lower()] = ow / float(nw)
    if not grown:
        return ""
    out = []
    for sn in z.namelist():
        if not (sn.lower().startswith("scripts/") and sn.lower().endswith(".shader")):
            continue
        txt = z.read(sn).decode("latin-1")
        for m in re.finditer(r"(?ms)^([^\s{}/][^\n{}]*?)\s*\n\{(.*?)\n\}", txt):
            name, body = m.group(1).strip(), m.group(2)
            if not re.search(r"(?i)\bspritegen\b", body):
                continue
            mm = re.search(r"(?im)^\s*(?:map|clampmap|animmap\s+[\d.]+|animmapphase\s+[\d.]+\s+[\d.]+)\s+(\S+)", body)
            if not mm:
                continue
            img = mm.group(1).lower()
            img = img[:-4] if img.endswith((".tga", ".jpg", ".png")) else img
            if img not in grown:
                continue
            old = re.search(r"(?im)^\s*spritescale\s+([-\d.]+)", body)
            new = (float(old.group(1)) if old else 1.0) * grown[img]
            if old:
                body2 = re.sub(r"(?im)^(\s*spritescale\s+)[-\d.]+", lambda q: q.group(1) + "%.5f" % new, body, count=1)
            else:
                body2 = re.sub(r"(?i)(\bspritegen\b[^\n]*\n)", lambda q: q.group(1) + "\tspritescale %.5f\n" % new, body, count=1)
            out.append("%s\n{%s\n}\n" % (name, body2))
    return ("// HZM: spritescale-compensated copies of this level's sprite shaders whose image the upscale enlarged\n"
            + "\n".join(out)) if out else ""


def main(pk3, level, out_pk3, exe_dir, threads="1:1:1", progress=None):
    exe = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe")
    if not os.path.exists(exe):
        print("no upscaler - skipped")
        return 0
    tm = {}
    p = os.path.join(HERE, f"{GAME}_texmap.json")
    if os.path.exists(p):
        tm = json.load(open(p)).get(level, {})
    skip = set(tm.get("noupscale", [])) | {k for k in tm if not k.startswith("_") and k not in ("noupscale", "nosoft", "keepdisc", "plaintext")}
    NOSOFT["keys"] = set(tm.get("nosoft", []))
    KEEPDISC.clear(); KEEPDISC.update(tm.get("keepdisc", []))
    PLAINTEXT.clear(); PLAINTEXT.update(tm.get("plaintext", []))
    CAREFUL_TEXT.clear(); CAREFUL_TEXT.update(tm.get("noupscale", []))
    z = zipfile.ZipFile(pk3)
    names = sorted(n for n in z.namelist() if n.startswith(f"textures/{GAME}/{level}/") and n.endswith(".tga"))
    tmp = tempfile.mkdtemp(prefix="flup_")
    report, files = {}, {}
    if not gpu_ok(exe, tmp, threads):
        print("no usable Vulkan GPU for the upscaler - skipped (the level keeps its own textures)")
        if progress:
            progress(step="upscale", skipped="no Vulkan graphics card")
        with open(out_pk3 + ".report.json", "w") as f:
            json.dump({"_skipped": "no usable Vulkan GPU"}, f)
        return 0
    import time as _t
    budget = float(os.environ.get("HZM_UPSCALE_BUDGET", "1200"))     # seconds; past it the pass stops, nothing fails
    t0 = _t.time()
    BATCH["in"], BATCH["out"] = os.path.join(tmp, "batch_in"), os.path.join(tmp, "batch_out")
    os.makedirs(BATCH["in"]), os.makedirs(BATCH["out"])
    for BATCH["mode"] in ("collect", "use"):
        if BATCH["mode"] == "use":
            if progress:
                progress(step="upscale", phase="gpu", textures=len(os.listdir(BATCH["in"])))
            ok_ = _esrgan(exe, BATCH["in"], BATCH["out"], threads, max(60, budget - (_t.time() - t0)))
            if not ok_ and not os.listdir(BATCH["out"]):
                print("upscaler batch failed - skipped (the level keeps its own textures)")
                return 0
        for i_, n in enumerate(names):
            key = BATCH["key"] = n.rsplit("/", 1)[-1][:-4]
            if progress and BATCH["mode"] == "use" and i_ % 25 == 0:
                progress(step="upscale", phase="finish", done=i_, total=len(names))
            if BATCH["mode"] == "use" and _t.time() - t0 > budget + 120:
                report[key] = "skipped (time budget)"
                continue
            _main_one(z, n, key, skip, report, files, exe, tmp, threads, 1)
    BATCH["mode"] = None
    sh_txt = sprite_shaders(z, files)
    if sh_txt:
        files[f"scripts/zzzz_{GAME}_hdtex_{level}_sprites.shader"] = sh_txt.encode("latin-1")
    if files:
        with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED) as o:
            for n in sorted(files):
                zi = zipfile.ZipInfo(n, ZIP_TIME)
                zi.compress_type = zipfile.ZIP_DEFLATED
                o.writestr(zi, files[n])
    with open(out_pk3 + ".report.json", "w") as f:
        json.dump(report, f, indent=0, sort_keys=True)
    ok = sum(1 for v in report.values() if v.startswith("ok"))
    print("upscaled", ok, "of", len(report), "->", out_pk3)
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], a[a.index("--threads") + 1] if "--threads" in a else "1:1:1")

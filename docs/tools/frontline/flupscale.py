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
ZIP_TIME = (2002, 5, 28, 0, 0, 0)


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
        r = subprocess.run([exe, "-i", src, "-o", dst, "-n", "realesrgan-x4plus", "-s", "4", "-t", "128", "-j", threads,
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


def upscale_cutout(exe, a, tmp, threads, pre=1):
    """[flfix2 look 2026-11-12] alpha-tested cards (tree lines, branches, bushes): ESRGAN on the COLOUR only, the cut
    edge from the original alpha. ESRGAN run on the whole card ate the leaf clusters (fewer, smaller leaves) because the
    key colour around them read as background; here the leaf colour is bled into the clear texels first (flhd.bleed), so
    ESRGAN sees one continuous foliage picture and only adds needle and leaf detail. The silhouette is the original's
    alpha resampled smoothly and cut at 128 (what alphaFunc GE128 draws): round edges, no stair steps, nothing eroded.
    pre: the card in the pak is already a flhd 4x Lanczos copy - it is boxed back down by `pre` first."""
    import flhd
    im = Image.fromarray(a, "RGBA")
    if pre > 1:
        im = im.resize((max(1, im.width // pre), max(1, im.height // pre)), Image.BOX)
    w, h = im.size
    a0 = np.asarray(im)[:, :, 3]
    if pre > 1:     # a flhd card is alpha-tested (GE128): its Lanczos-softened edge is not a blend
        im.putalpha(Image.fromarray(np.where(a0 >= 128, 255, 0).astype(np.uint8)))
        a0 = np.asarray(im)[:, :, 3]
    if ((a0 > 8) & (a0 < 247)).mean() > 0.10:
        return None, "cutout: blended (soft alpha) kept original"     # shadow blobs, scorch decals, haze cards
    base = np.asarray(flhd.bleed(im))
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
    up = np.clip(out, 0, 255).astype(np.uint8)
    back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
    m0, m1 = o[solid].mean(), back[solid].mean()
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


def upscale_one(exe, im, tmp, threads, cut_pre=0):
    rgba = im.convert("RGBA")
    w, h = rgba.size
    a = np.asarray(rgba)
    if is_cutout(a):
        # ESRGAN on the whole card erodes and thins leaf clusters: only cards the level lists get the colour-only pass
        if cut_pre:
            return upscale_cutout(exe, a, tmp, threads, cut_pre)
        return None, "cutout kept original"
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
    up_im = Image.fromarray(up)
    # checks against the original (after the colour match)
    orig = a[:, :, :3].astype(np.float32)
    back = np.asarray(up_im.resize((w, h), Image.BOX)).astype(np.float32)
    m0, m1 = orig.mean(), back.mean()
    if m1 < 8 or m1 > 247:
        return None, "black/blown frame"
    if abs(m1 - m0) / max(1.0, m0) > DRIFT_LIMIT:
        return None, "brightness drift"
    if np.abs(back - orig).mean() > 14:
        return None, "downscale-back mismatch"
    bic = np.asarray(Image.fromarray(a[:, :, :3]).resize((w * 4, h * 4), Image.BICUBIC))
    if lap_energy(up) > WORM_LIMIT * max(1.0, lap_energy(bic)):
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


def _main_one(z, n, key, skip, report, files, exe, tmp, threads, cut_pre):
    if key in skip or key == "untextured":
        report[key] = "skipped (list)"
        return
    try:
        im = Image.open(io.BytesIO(z.read(n)))
        res, why = upscale_one(exe, im, tmp, threads, cut_pre=cut_pre)
    except Exception as e:  # never fail the conversion
        res, why = None, "error %s" % e
    if BATCH["mode"] == "collect":
        return
    report[key] = why
    if res is not None:
        b = io.BytesIO()
        res.save(b, "TGA")
        files[n] = b.getvalue()


def main(pk3, level, out_pk3, exe_dir, threads="1:1:1", progress=None):
    exe = os.path.join(exe_dir, "realesrgan-ncnn-vulkan.exe")
    if not os.path.exists(exe):
        print("no upscaler - skipped")
        return 0
    tm = {}
    p = os.path.join(HERE, "fl_texmap.json")
    if os.path.exists(p):
        tm = json.load(open(p)).get(level, {})
    skip = set(tm.get("noupscale", [])) | {k for k in tm if not k.startswith("_") and k != "noupscale"}
    # cards flhd already enlarged 4x (fl_levels.json "hd" -> "cutout"): boxed back down before the colour-only pass
    lv = {}
    p = os.path.join(HERE, "fl_levels.json")
    if os.path.exists(p):
        lv = json.load(open(p)).get(level, {})
    flhd_cut = set((lv.get("hd") or {}).get("cutout", []))
    z = zipfile.ZipFile(pk3)
    names = sorted(n for n in z.namelist() if n.startswith(f"textures/fl/{level}/") and n.endswith(".tga"))
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
            _main_one(z, n, key, skip, report, files, exe, tmp, threads, 4 if key in flhd_cut else 1)
    BATCH["mode"] = None
    if False:
        pass
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

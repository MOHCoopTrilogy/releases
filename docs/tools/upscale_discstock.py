# -*- coding: utf-8 -*-
"""[user 2026-11-15] "Just make sure we upscale the stock stuff coming in ... If not that find replacements."

4x pass over the STOCK textures the two own-disc missions draw (Sealed Orders coop_fl_1_1, Their Dying Breath
coop_ea_1_11) that have no HD copy anywhere in the VFS yet. Same recipe and shipping route as the m3l1a pass
(docs/tools/upscale_m3l1a.py, zzzzzzzzzz_coop_hd_m3l1a.pk3): our own Real-ESRGAN x4 of the stock image the engine
loads TODAY (the winning file), validator + fallback, DXT .dds WITH A FULL MIP CHAIN, capped at 2048, in a ten-z
out-of-band pak (zzzzzzzzzz_coop_hd_discstock.pk3) that out-sorts every .dds that could shadow it. Nothing from a
disc is read or written here; the inputs are stock MOHAA / mod-pak images only.

Target list: docs/tools/discstock_targets.json (paths only; copied from the stock-HD inventory under H:/hzm_work/stockhd), built by the inventory tools (static closure of the
converted BSP + map scripts + BYO pak tiks, filtered by the engine's runtime imagelist/tikilist; see the
inventory table). Rows carrying "exclude" are skipped with their reason.

Differences from m3l1a, and why:
1. TILE-AWARE + COLOUR-MATCHED, from flupscale.py: wrap-pad by 1/4, upscale, crop (no seams on tiling sheets);
   per-channel mean/std transfer back onto the source (ESRGAN darkens dark organic art); reject on brightness
   drift, a downscale-back mismatch or worm noise -> the stock image stays (a Lanczos copy is a visual no-op next to
   GPU bilinear, 12-asset-conventions, so nothing is shipped). Alpha-tested cards use flupscale.upscale_cutout.
2. ALPHA: a real alpha channel is upscaled separately (smooth Lanczos for soft alpha - smoke, flame - and the
   original silhouette resampled and cut at 128 for alpha-tested cards). An all-0 / all-255 alpha is dropped
   (tnt.tga ships a fully clear alpha its shader never reads).
3. SPRITES KEEP THEIR SIZE: a sprite's world size is its stage-0 image width x spritescale (tr_sprite.c
   SPR_RegisterSprite / RB_DrawSprite), so a 4x image would draw a 4x bigger particle. Every `spritegen` shader
   whose stage-0 image is upscaled here is re-emitted in scripts/zz_hd_discstock.shader with
   spritescale *= old_w / new_w. Name overrides of retail shaders win on both renderers since the gl2
   FindShaderInShaderText fix (highest-priority pak); the pak sorts after every pak that defines these names.
4. TEXT AND INSIGNIA ARE PROTECTED: rectangles in PROTECT (fractions of the sheet) are taken from a Lanczos 4x +
   light unsharp instead of ESRGAN (DECISIONS "ESRGAN is for photos and text, not chrome": it invents strokes).
   A whole-sheet protect (dial faces, radio panels) keeps the stock sheet. Where ESRGAN fails and nothing better
   exists, REPLACE grades a CC0 photo (docs/tools/ea/hd, CREDITS.txt) to the stock sheet's colour statistics.
5. TINY SOURCES (< 64 px short side) are Lanczos-doubled before ESRGAN and boxed back (12-asset-conventions:
   ESRGAN outputs noise on tiny inputs).

  python docs/tools/upscale_discstock.py              run (resumable: skips staged outputs)
  python docs/tools/upscale_discstock.py --pack       rebuild the pk3 from the stage
  python docs/tools/upscale_discstock.py --only <substr>
"""
import io
import json
import os
import re
import struct
import subprocess
import sys
import time
import zipfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ea"))
import flupscale as FU  # noqa: E402  (colour_match, lap_energy, upscale_cutout rules)

import discstock_vfs as V  # noqa: E402  (read-only model of the engine VFS + R_LoadImage order)

ESR = r"C:\mohaa-coop-dev\_tools\realesrgan\realesrgan-ncnn-vulkan.exe"
GAPS = os.path.join(HERE, "discstock_targets.json")
STAGE = r"C:\mohaa-coop-dev\_hd_discstock"          # outside the mod tree: never swept into a pak
MODROOT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
PAK = os.path.join(MODROOT, "zzzzzzzzzz_coop_hd_discstock.pk3")
WORK = r"H:\hzm_work\stockhd\up"
CAP = 2048
SHADER_FILE = "scripts/zz_hd_discstock.shader"

# fractions (x0, y0, x1, y1) of the sheet drawn from Lanczos, not ESRGAN: lettering, stencils, insignia
PROTECT = {
    "textures/models/crates/explosive1.tga": [(0.0, 0.0, 1.0, 0.5)],          # stencilled warning text
    "textures/models/crates/nazi_crate.tga": [(0.0, 0.0, 0.76, 0.43)],        # "Oben / Nicht werfen", eagle
    "textures/models/items/dial.tga": [(0.0, 0.0, 1.0, 1.0)],                 # dial letters
    "textures/models/items/phone1.tga": [(0.3, 0.45, 0.75, 0.95)],            # the dial face
    "textures/models/submodels/radiostation1.tga": [(0.0, 0.0, 1.0, 1.0)],    # labels and gauges all over
    "textures/models/submodels/radiostation2.tga": [(0.0, 0.0, 1.0, 1.0)],
    "textures/models/submodels/miscpieces.tga": [(0.25, 0.72, 1.0, 1.0)],     # emblem discs
    "textures/models/submodels/deckcannon.tga": [(0.25, 0.35, 0.65, 0.75)],   # eagles
    "textures/models/vehicles/stuka/stuka.tga": [(0.30, 0.0, 0.50, 0.30), (0.45, 0.28, 1.0, 1.0)],  # crosses, tail
    "textures/models/vehicles/panzer_iv/undercarriage.tga": [],
}


# where ESRGAN fails AND nothing in the VFS is better: a CC0 photo source (docs/tools/ea/hd, CREDITS.txt there), resized
# to 4x the stock sheet and graded to the stock sheet's per-channel mean/std so it keeps the stock look
REPLACE = {
    # winter trunk bark of tree_caskawinter: ESRGAN turned the 128 px frosted bark into white speckle noise
    "textures/models/natural/tree1_1winter.tga": "bark_willow_02_diff_1k.jpg",
}


def log(m):
    print(m, flush=True)
    os.makedirs(WORK, exist_ok=True)
    with io.open(os.path.join(WORK, "log.txt"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")


def save_dds_mipped(img, path, fmt):
    """DXT with a full mip chain (upscale_m3l1a.save_dds_mipped, verbatim recipe)."""
    levels = []
    w, h = img.size
    cur = img
    while True:
        buf = io.BytesIO()
        cur.save(buf, format="DDS", pixel_format=fmt)
        levels.append(buf.getvalue())
        if w == 1 and h == 1:
            break
        w, h = max(1, w // 2), max(1, h // 2)
        cur = img.resize((w, h), Image.LANCZOS)
    head = bytearray(levels[0][:128])
    struct.pack_into("<I", head, 8, struct.unpack_from("<I", head, 8)[0] | 0x20000)
    struct.pack_into("<I", head, 28, len(levels))
    struct.pack_into("<I", head, 108, struct.unpack_from("<I", head, 108)[0] | 0x8 | 0x400000)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "wb") as f:
        f.write(bytes(head))
        for lv in levels:
            f.write(lv[128:])


def esrgan(rgb):
    """one process per file (12-asset-conventions: batch runs go black), idle priority, no window"""
    ti, to = os.path.join(WORK, "in.png"), os.path.join(WORK, "out.png")
    for f in (ti, to):
        if os.path.exists(f):
            os.remove(f)
    Image.fromarray(rgb).save(ti)
    try:
        subprocess.run([ESR, "-i", ti, "-o", to, "-n", "realesrgan-x4plus", "-s", "4", "-t", "256", "-j", "1:1:1",
                        "-f", "png"], cwd=os.path.dirname(ESR), capture_output=True, timeout=600,
                       creationflags=0x08000000 | 0x00000040)
    except Exception:
        return None
    if not os.path.exists(to):
        return None
    return np.asarray(Image.open(to).convert("RGB"))


def lanczos_sharp(rgb, w4, h4):
    im = Image.fromarray(rgb).resize((w4, h4), Image.LANCZOS)
    return np.asarray(im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=2)))


def up_rgb(rgb, key):
    """-> (4x rgb, how). wrap-pad, ESRGAN, crop, colour match, validate; Lanczos on any reject"""
    h, w = rgb.shape[:2]
    pre = 2 if min(w, h) < 64 else 1
    src = np.asarray(Image.fromarray(rgb).resize((w * pre, h * pre), Image.LANCZOS)) if pre > 1 else rgb
    sh, sw = src.shape[:2]
    pw, ph = max(4, sw // 4), max(4, sh // 4)
    pad = np.pad(src, ((ph, ph), (pw, pw), (0, 0)), mode="wrap")
    out = esrgan(pad)
    how = "esrgan"
    if out is not None and out.shape[0] == pad.shape[0] * 4:
        up = out[ph * 4: ph * 4 + sh * 4, pw * 4: pw * 4 + sw * 4]
        if pre > 1:
            up = np.asarray(Image.fromarray(up).resize((w * 4, h * 4), Image.BOX))
        up = FU.colour_match(up, rgb)
        back = np.asarray(Image.fromarray(up).resize((w, h), Image.BOX)).astype(np.float32)
        o = rgb.astype(np.float32)
        m0, m1 = o.mean(), back.mean()
        bic = np.asarray(Image.fromarray(rgb).resize((w * 4, h * 4), Image.BICUBIC))
        why = None
        if m1 < 2 and m0 > 10:
            why = "black frame"
        elif abs(m1 - m0) / max(1.0, m0) > FU.DRIFT_LIMIT and m0 > 10:
            why = "brightness drift"
        elif np.abs(back - o).mean() > 14:
            why = "downscale-back mismatch"
        elif FU.lap_energy(up) > FU.WORM_LIMIT * max(1.0, FU.lap_energy(bic)):
            why = "worm noise"
        if why is None:
            return up, how
        how = "lanczos (%s)" % why
    else:
        how = "lanczos (esrgan failed)"
    return lanczos_sharp(rgb, w * 4, h * 4), how


def protect(up, rgb, key):
    rects = PROTECT.get(key)
    if not rects:
        return up, ""
    h4, w4 = up.shape[:2]
    lz = lanczos_sharp(rgb, w4, h4)
    out = up.copy()
    for x0, y0, x1, y1 in rects:
        a, b, c, d = int(x0 * w4), int(y0 * h4), int(x1 * w4), int(y1 * h4)
        out[b:d, a:c] = lz[b:d, a:c]
    return out, " +protect%d" % len(rects)


def process(vfs, row):
    key = row["image"]
    f, e = vfs.resolve_image(key)
    im = Image.open(io.BytesIO(vfs.read(e)))
    im.load()
    rgba = np.asarray(im.convert("RGBA"))
    h, w = rgba.shape[:2]
    al = rgba[:, :, 3]
    has_alpha = al.min() < 250 and al.max() > 5
    rgb = rgba[:, :, :3].copy()
    soft = has_alpha and ((al > 8) & (al < 247)).mean() > 0.10
    if key in REPLACE:
        src = Image.open(os.path.join(HERE, "ea", "hd", REPLACE[key])).convert("RGB").resize((w * 4, h * 4), Image.LANCZOS)
        # luminance only from the photo (its own hues - moss, rust - would read as a different tree); the stock sheet's
        # per-channel mean/std give the colour, so the frosted grey look stays
        lum = np.asarray(src.convert("L"), np.float32)
        z = (lum - lum.mean()) / max(1e-3, lum.std())
        ref = rgba[:, :, :3].astype(np.float32)
        a = np.dstack([z * ref[:, :, c].std() + ref[:, :, c].mean() for c in range(3)])
        res = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        out = os.path.join(STAGE, os.path.splitext(key)[0].replace("/", os.sep) + ".dds")
        save_dds_mipped(res, out, "DXT1")
        qa = os.path.join(WORK, "qa", os.path.splitext(key)[0].replace("/", "__") + ".png")
        res.save(qa)
        return {"image": key, "from": "%s@%s" % (f, os.path.basename(e[1])), "src": [w, h], "out": list(res.size),
                "fmt": "DXT1", "how": "CC0 replacement %s, graded to the stock sheet" % REPLACE[key]}
    keep = {"image": key, "from": "%s@%s" % (f, os.path.basename(e[1])), "src": [w, h], "out": [w, h], "fmt": None}
    if PROTECT.get(key) == [(0.0, 0.0, 1.0, 1.0)]:
        # all lettering: a Lanczos sheet is a visual no-op next to GPU bilinear (12-asset-conventions), so no file
        return dict(keep, how="kept stock (lettering over the whole sheet)")
    if has_alpha and not soft:
        # alpha-tested card (tree cards, branches): flupscale's cutout pass - colour-only ESRGAN, original silhouette,
        # thin features kept, no new highlights; on any reject the stock card stays (nothing staged)
        res, why = FU.upscale_cutout(ESR, rgba, WORK, "1:1:1", 1)
        if res is None:
            return {"image": key, "from": "%s@%s" % (f, os.path.basename(e[1])), "src": [w, h], "out": [w, h],
                    "fmt": None, "how": "kept stock (%s)" % why}
        if res.size[0] <= w:
            return {"image": key, "from": "%s@%s" % (f, os.path.basename(e[1])), "src": [w, h], "out": [w, h],
                    "fmt": None, "how": "kept stock (cutout pass caps at 1024; source already 1024)"}
        out = os.path.join(STAGE, os.path.splitext(key)[0].replace("/", os.sep) + ".dds")
        save_dds_mipped(res, out, "DXT5")
        qa = os.path.join(WORK, "qa", os.path.splitext(key)[0].replace("/", "__") + ".png")
        os.makedirs(os.path.dirname(qa), exist_ok=True)
        res.save(qa)
        return {"image": key, "from": "%s@%s" % (f, os.path.basename(e[1])), "src": [w, h], "out": list(res.size),
                "fmt": "DXT5", "how": "esrgan cutout (%s)" % why}
    if has_alpha:
        # bleed the colour into clear texels so ESRGAN and the mips never pull in the key colour
        rgb = np.asarray(FU._bleed(Image.fromarray(rgba, "RGBA")))[:, :, :3].copy()
    up, how = up_rgb(rgb, key)
    if how.startswith("lanczos"):
        # the ESRGAN result was rejected; a Lanczos copy adds nothing over GPU bilinear, so ship nothing
        return dict(keep, how="kept stock (esrgan rejected: %s)" % how[len("lanczos ("):-1])
    up, prot = protect(up, rgb, key)
    w4, h4 = w * 4, h * 4
    if has_alpha:
        a4 =Image.fromarray(al).resize((w4, h4), Image.LANCZOS if soft else Image.BICUBIC)
        if not soft:
            a4 = a4.filter(ImageFilter.GaussianBlur(2.0))
            a4 = Image.fromarray(np.where(np.asarray(a4) >= 128, 255, 0).astype(np.uint8))
        res = Image.fromarray(np.dstack([up, np.asarray(a4)]), "RGBA")
        fmt = "DXT5"
    else:
        res = Image.fromarray(up, "RGB")
        fmt = "DXT1"
    s = min(1.0, CAP / float(max(w4, h4)))
    if s < 1.0:
        res = res.resize((int(w4 * s), int(h4 * s)), Image.LANCZOS)
    out = os.path.join(STAGE, os.path.splitext(key)[0].replace("/", os.sep) + ".dds")
    save_dds_mipped(res, out, fmt)
    # QA copy (png) for the before/after crops
    qa = os.path.join(WORK, "qa", os.path.splitext(key)[0].replace("/", "__") + ".png")
    os.makedirs(os.path.dirname(qa), exist_ok=True)
    res.save(qa)
    return {"image": key, "from": "%s@%s" % (f, os.path.basename(e[1])), "src": [w, h], "out": list(res.size),
            "fmt": fmt, "how": how + prot}


def sprite_shaders(vfs, sh, done):
    """spritegen shaders whose stage-0 image was upscaled -> override text with spritescale compensated"""
    out = []
    names = sorted({s for r in json.load(open(GAPS)) for s in r["shaders"]})
    for n in names:
        d = sh.get(n)
        if not d:
            continue
        body = d[4]
        if not re.search(r"(?i)\bspritegen\b", body):
            continue
        imgs = V.shader_images(body)
        if not imgs:
            continue
        first = imgs[0][1].lower()
        rec = done.get(first)
        if not rec:
            continue
        ratio = rec["src"][0] / float(rec["out"][0])
        old = V.shader_spritescale(body) or 1.0
        new = old * ratio
        if re.search(r"(?im)^\s*spritescale\s+[-\d.]+", body):
            body2 = re.sub(r"(?im)^(\s*spritescale\s+)[-\d.]+", lambda m: m.group(1) + "%.5f" % new, body, count=1)
        else:
            body2 = re.sub(r"(?i)(\bspritegen\b[^\n]*\n)", lambda m: m.group(1) + "\tspritescale %.5f\n" % new, body,
                           count=1)
        out.append("// %s (was %s@%s): stage-0 %s %dx%d -> %dx%d, spritescale %.4f -> %.5f\n%s\n%s\n" % (
            d[3], d[1], os.path.basename(d[2]), first, rec["src"][0], rec["src"][1], rec["out"][0], rec["out"][1],
            old, new, d[3], body2.strip()))
    return out


def build_pak(shader_text=None):
    files = []
    for root, _, fs in os.walk(STAGE):
        for f in fs:
            p = os.path.join(root, f)
            files.append((os.path.relpath(p, STAGE).replace(os.sep, "/"), p))
    files.sort()
    tmp = PAK + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, p in files:
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            z.writestr(zi, io.open(p, "rb").read())
    if os.path.exists(PAK):
        os.remove(PAK)
    os.rename(tmp, PAK)
    log("packed %d files -> %s (%.1f MB)" % (len(files), PAK, os.path.getsize(PAK) / 1048576.0))


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(STAGE, exist_ok=True)
    rep_p = os.path.join(WORK, "report.json")
    report = json.load(open(rep_p)) if os.path.exists(rep_p) else {}
    vfs = V.VFS(drop={os.path.basename(PAK).lower()})
    if "--pack" not in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
        rows = [r for r in json.load(open(GAPS)) if not r.get("exclude")]
        for r in rows:
            k = r["image"]
            if only and only not in k:
                continue
            out = os.path.join(STAGE, os.path.splitext(k)[0].replace("/", os.sep) + ".dds")
            if k in report and not only and (os.path.exists(out) or report[k].get("fmt") is None):
                continue
            if os.path.exists(out):
                os.remove(out)
            try:
                report[k] = process(vfs, r)
                log("%-62s %s -> %s %s" % (k, report[k]["src"], report[k]["out"], report[k]["how"]))
                if report[k].get("fmt") is None and os.path.exists(out):
                    os.remove(out)
            except Exception as ex:
                log("FAIL %s %s" % (k, ex))
            json.dump(report, open(rep_p, "w"), indent=1)
            time.sleep(1.0)      # 12-asset-conventions: sustained ESRGAN runs corrupt outputs on this GPU
    sh = V.Shaders(vfs)
    blocks = sprite_shaders(vfs, sh, {k.lower(): v for k, v in report.items()})
    sp = os.path.join(STAGE, SHADER_FILE.replace("/", os.sep))
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with io.open(sp, "w", newline="\n") as f:
        f.write("// HZM coop: spritescale-compensated copies of retail sprite shaders whose stage-0 image is upscaled 4x\n"
                "// in zzzzzzzzzz_coop_hd_discstock.pk3 (docs/tools/upscale_discstock.py). Same look, same world size.\n\n")
        f.write("\n".join(blocks))
    log("%d sprite shaders compensated" % len(blocks))
    build_pak()


if __name__ == "__main__":
    main()

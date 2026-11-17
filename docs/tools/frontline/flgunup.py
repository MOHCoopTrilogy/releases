"""[flguns] the disc guns' texture upscale, on the PLAYER's PC with the converter's own realesrgan-ncnn-vulkan
(tools/upscaler). The European Assault character recipe (eacharup.upscale_one, here with the Frontline flupscale
helpers it calls - identical run_esrgan / colour_match / lap_energy / DRIFT_LIMIT / WORM_LIMIT): ESRGAN x4,
colour-matched, worm / drift / brightness rejects, fine band blended back toward bicubic, +-6 neighbourhood clamp.
FL 256 -> 1024. Markings and text stay a PLAIN bicubic resample inside the PROTECT boxes (fractions of the texture,
checked letter by letter on the private before/after sheet). A rejected texture, no Vulkan GPU or any error keeps the
disc original: the upscale never fails a conversion."""
import os
import struct
import tempfile

import numpy as np
from PIL import Image, ImageFilter

import flupscale as fu

CAP = 2048
# texture (lower-case file name) -> [(x0, y0, x1, y1)] fractions: stamped legends, selector markings
PROTECT = {
    # Thompson metal: MODEL stamp + AUTO-ORDNANCE legend + FIRE <-> SAFE in one box; the selector letters
    "tom_02met256.tga": [(0.37, 0.18, 0.93, 0.39), (0.55, 0.39, 0.67, 0.49)],
    # Hi-Standard frame: the script logo + HIGH STANDARD block; SUPERMATIC + the line under it (batch 2, 2026-11-16)
    "hs_sides_256.tga": [(0.33, 0.12, 0.75, 0.21), (0.30, 0.24, 0.53, 0.32)],
    "hs_back_256.tga": [(0.31, 0.68, 0.50, 0.80)],          # the small stamp under the grip screw
    "col_sid_256_4.tga": [(0.38, 0.06, 0.66, 0.22)],        # the (faint, 128 px) slide legend
    "baz_scope_256.tga": [(0.60, 0.08, 0.69, 0.26)],        # the FIRE / SAFE letters on the grip plate
    # M1 receiver heel: the (illegible at 256 px) receiver stamp - kept as the disc drew it, never re-drawn
    "m1top_256.tga": [(0.75, 0.06, 0.96, 0.24)],
    # European Assault (2026-11-16): EA texture names are per-gun indices (p036 is the Mosin AND a different sniper sheet),
    # so these rows are keyed "<stub>/<name>" (tried before the bare name); checked letter by letter on the private sheets
    "bar_ea/p016.tga": [(0.12, 0.0, 0.42, 0.38)],                                     # receiver stamp block
    "bazooka_ea/p068.tga": [(0.23, 0.71, 0.32, 0.85), (0.67, 0.67, 0.86, 0.89)],      # ON / OFF, the star
    "bazooka_ea2/p018.tga": [(0.74, 0.39, 1.0, 0.67), (0.64, 0.77, 0.89, 0.87)],      # range scale, blue label
    "bazooka_ea2/p020.tga": [(0.10, 0.23, 0.96, 0.34)],                               # stencilled legend
    "colt45_ea/h025.tga": [(0.58, 0.19, 0.67, 0.73), (0.78, 0.19, 0.87, 0.73)],       # slide legends
    "coop_g43_irons_ea/p067.tga": [(0.71, 0.61, 0.84, 1.0)],                          # rear sight leaf numbers
    "g43_ea/p067.tga": [(0.71, 0.61, 0.84, 1.0)],
    "kar98_ea/p010.tga": [(0.0, 0.13, 0.19, 0.25)],                                   # serial 4452
    "mills_grenade_sp_start_ea/p048.tga": [(0.09, 0.55, 0.19, 0.81)],                 # M / G
    "mosin_nagant_rifle_ea/p036.tga": [(0.0, 0.40, 0.11, 0.55)],                      # rear sight ladder
    "nagant_sniper_ea/p036.tga": [(0.0, 0.40, 0.11, 0.55)],
    "mp40_ea/p044.tga": [(0.42, 0.76, 0.66, 0.87), (0.41, 0.88, 0.71, 1.0),           # MP40 bnz.43, 1110 b,
                         (0.22, 0.23, 0.44, 0.29)],                                   # the sight scale
    "ppsh_smg_ea/p009.tga": [(0.34, 0.66, 0.74, 0.72)],                               # receiver stamp line
    "steilhandgranate_start_ea/p033.tga": [(0.72, 0.52, 0.93, 1.0)],                  # VOR GEBRAUCH ... EINSETZEN
    "thompsonsmg_ea/h019.tga": [(0.17, 0.89, 0.46, 0.99)],                            # FULL AUTO / SINGLE
    "thompsonsmg_ea/h020.tga": [(0.07, 0.27, 0.19, 0.83)],                            # model legend + FIRE / SAFE
}


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


def upscale_one(exe, a, protect, tmp):
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
    al = np.asarray(Image.fromarray(a[:, :, 3]).resize((tw, th), Image.BILINEAR))
    return np.dstack([out, al]), "ok"


def upscale_files(files, exe, progress=lambda **kv: None):
    """files = {pak path: bytes}: every textures/byo_guns/*/*.tga replaced in place by its upscale (or kept)."""
    names = sorted(n for n in files if n.startswith("textures/byo_guns/") and n.endswith(".tga"))
    if not names or not exe or not os.path.exists(exe):
        return {}
    tmp = tempfile.mkdtemp(prefix="flgunup_")
    rep = {}
    try:
        if not fu.gpu_ok(exe, tmp, "1:1:1"):
            progress(step="guns_upscale", skipped="no usable Vulkan GPU")
            return {}
        for n in names:
            a = load_tga(files[n])
            key = "/".join(n.split("/")[-2:]).lower()
            res, why = upscale_one(exe, a, PROTECT.get(key, PROTECT.get(os.path.basename(n).lower(), [])), tmp)
            if res is not None:
                files[n] = save_tga(res)
            rep[n] = why
            progress(step="guns_upscale", texture=os.path.basename(n), result=why)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return rep

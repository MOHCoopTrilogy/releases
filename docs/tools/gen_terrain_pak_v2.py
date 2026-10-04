# -*- coding: utf-8 -*-
"""Terrain pak v2 - Phase 1 of the vetted ground-seam plan (bug-2950, bug-2951).

Plan: docs/proposals/seams_2026-09-25/vet_seams.md (Phase 1, F1-F5, F10, F11, F23).

Reads TODAY'S zzzzzzzzz_coop_terrain.pk3 (sha256 72979342..., asserted) and writes one candidate pak
per relief TARGET. Each candidate is today's pak with exactly these changes:

1. RELIEF BAKED INTO THE THREE OMAHA-FREE NORMAL MAPS ONLY
   (m3l3grass_1rough_nh, grndset_2af_nh, forstsnow_lite256_nh).
   The cvar r_hzmNormalStrength stays 1.25 (it is CVAR_ARCHIVE and GLOBAL - it reaches the Omaha-coupled
   rubble2c_nh / rubblebase_nh / nu_earth_set3grassa_nh too, vet F4). Instead the tangent-space xy of
   these three is scaled by TARGET/1.25, so at the unchanged 1.25 they render exactly like the cvar set
   to TARGET: lightall_fp.glsl:441-446 computes
       N.xy = (tex.rg - 0.5) * u_NormalScale.xy ;  N.z = sqrt(clamp(0.25 - |N.xy|^2, 0, 1))
   with u_NormalScale.xy = r_baseNormalX/Y (1.0) * r_hzmNormalStrength (tr_shade.c:961-966).
   z (blue) is renormalised; the shader never reads it. ALPHA (measured height) is kept BIT-EXACT: it
   is read only for parallax (lightall_fp.glsl:164-170, LIGHTDEF_USE_PARALLAXMAP needs r_parallaxMapping,
   tr_shader.c:3244), which is 0 live - so each DXT5 block's 8-byte alpha half is copied verbatim from
   today's file at every mip level and only the 8-byte colour half is re-encoded.
   Mips: 2x2 BOX chain in float, down to 1x1 (NOT Lanczos, NOT build_terrain_pack.save_dds_mipped;
   vet F10/F17). xy is averaged linearly (as texture filtering does) and z recomputed per level.
   Colour blocks come from bc_colour_blocks() below (R,G-weighted least-squares fit), not Pillow's
   encoder, whose error on these low-amplitude maps is 3-6x the achievable limit (visible block grain).
   The other four normal maps (rubble2c_nh, rubblebase_nh, nu_earth_set3grassa_nh - they draw on Omaha
   maps - and the dead m3l3grass_bocroad_nh) stay byte-identical.

2. BLACK-TRIM FIX (bug-2951): adds textures/mohtest/conctrmdrk.dds.
   hdmem's DXT5 copy (and AA_HD_Project_Pak4's TGA it came from) is RGBA 0 everywhere; retail's 64x32
   TGA has real RGB under an all-zero alpha and scripts/mohtest.shader draws it OPAQUE, so t3l1/t3l2
   show a black trim. Rebuilt from the RETAIL TGA's RGB: 4x Lanczos to 256x128 + mild unsharp (the
   bug-1129 recipe, radius 1.2 / 55% / threshold 3), done on a padded canvas (horizontal WRAP - the trim
   tiles along S; vertical edge-replicate) and clamped to the source range (bug-1247). No ESRGAN.
   DXT1, no alpha, full box mip chain. R_LoadImage tries .dds first (tr_image.c:2462), and the terrain
   pak (9 z) sorts above hdmem (7 z) - checked here against the real pak stacks.

3. Every other member byte-identical. CREDITS_terrain.txt kept. omaha_set4_shoreline never re-added
   (bug-2223). Entries sorted; unchanged members keep their original timestamp, changed/added members get
   FIXED_TS - so two runs produce the same sha256 (asserted in-process by building everything twice).

Every gate is an assert; the script exits non-zero if any fails. Nothing here writes outside --out.
It never touches hzm-mohaa-coop-mod or a game folder; deploying a candidate is a separate, manual step:
copy it over hzm-mohaa-coop-mod\\zzzzzzzzz_coop_terrain.pk3, then run build.ps1 (game closed).

  python docs/tools/gen_terrain_pak_v2.py --out <dir>                  both candidates (0.6, 0.25)
  python docs/tools/gen_terrain_pak_v2.py --out <dir> --targets 0.4    another level
  --no-previews   skip the PNG contact sheets     --no-stack-check   skip the pak-stack resolve check
  --delean        OFF-SPEC alternative (v2d_* paks): subtract level 0's encoder lean before scaling.

FOUND WHILE BUILDING (2026-09-25): today's _nh level 0 carries a +x lean put there by Pillow's DXT5
encoder (see dc_excess). The spec'd box chain is built from level 0, so it carries that lean (and the
encoder's block noise) down every mip; today's own mips do not have it. Result: the spec candidates match
the cvar test at level 0 (gated), but their distant mips keep more relief than the cvar test shows (printed
as [INFO] per-mip lines, and in gates.json). --delean removes the lean; the block noise cannot be undone
without the original ambientCG source.
"""
import argparse, functools, hashlib, io, json, os, re, shutil, struct, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DEFAULT = os.path.join(REPO, "hzm-mohaa-coop-mod", "zzzzzzzzz_coop_terrain.pk3")
SRC_SHA = "7297934269f842d2d1c4b64915a89db694a628487812a60eb0ccee1ea38f0e04"   # 1.9.2 manifest (vet F1)
PAK_NAME = "zzzzzzzzz_coop_terrain.pk3"
GOG_DEFAULT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LIVE_BASE = r"G:\mohaa-gl2"                     # PLAY-GL2.bat fs_basepath (maintt is a junction into GOG)
LIVE_HOME = r"G:\mohaa-gl2\home"                # PLAY-GL2.bat fs_homepath
APPDATA_HOME = os.path.join(os.environ["APPDATA"], "openmohaa") if os.environ.get("APPDATA") else ""   # plain GOG launch

CUR_STRENGTH = 1.25        # r_hzmNormalStrength default + live saved value (tr_init.c:1711), times r_baseNormalX 1.0
TILT_TOL_DEG = 0.5
FIXED_TS = (2026, 9, 25, 0, 0, 0)
NEW_ATTR = 0x81B60000      # same external_attr as today's DDS members

# rebaked _nh -> its colour texture (for the preview only)
REBAKE = {
    "textures/wilderness/m3l3grass_1rough_nh.dds": "textures/wilderness/m3l3grass_1rough.dds",
    "textures/algiers/grndset_2af_nh.dds": "textures/algiers/grndset_2af.dds",
    "textures/central_europe_winter/forstsnow_lite256_nh.dds": "textures/central_europe_winter/forstsnow_lite256.dds",
}
# Omaha-coupled (vet F4/F24) or dead (F3): must stay byte-identical
FROZEN_NH = [
    "textures/mohtest/rubble2c_nh.dds",
    "textures/models/items/rubblebase_nh.dds",
    "textures/mohtest/nu_earth_set3grassa_nh.dds",
    "textures/wilderness/m3l3grass_bocroad_nh.dds",
]
CONC = "textures/mohtest/conctrmdrk.dds"
CONC_RETAIL = (os.path.join("main", "Pak2.pk3"), "textures/mohtest/conctrmdrk.tga",
               "45cb4cf1ad6001db25e4f206443f903fd59f13cd9fc5d3c33e93369d56f33bd5")
CONC_HDMEM = (os.path.join("maintt", "zzzzzzz_dds_hdmem.pk3"), "textures/mohtest/conctrmdrk.dds")
CONC_MEAN_TOL = 6.0
OMAHA = re.compile(r"(omaha|obeach|ocean|seabed|wetsand|shoreline|surf|wake|m3l1a|m3l1b|e3l1|e3l2)", re.I)

EXPECTED_MEMBERS = 24      # today's pak: 23 DDS + CREDITS_terrain.txt

DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE, DDSCAPS_COMPLEX, DDSCAPS_MIPMAP = 0x20000, 0x80000, 0x8, 0x400000

GATES = []


def gate(name, ok, detail=""):
    GATES.append(dict(gate=name, ok=bool(ok), detail=detail))
    print("  [%s] %s  %s" % ("PASS" if ok else "FAIL", name, detail))
    return ok


def sha(b):
    return hashlib.sha256(b).hexdigest()


# ------------------------------------------------------------------------------------------------ DDS
def dds_parse(b):
    assert b[:4] == b"DDS ", "not a DDS"
    size, flags, h, w = struct.unpack_from("<4I", b, 4)
    mips = struct.unpack_from("<I", b, 28)[0]
    fourcc = b[84:88]
    assert size == 124 and fourcc in (b"DXT1", b"DXT5"), (size, fourcc)
    bpb = 8 if fourcc == b"DXT1" else 16
    n = max(1, mips) if flags & DDSD_MIPMAPCOUNT else 1
    levels, off, cw, ch = [], 128, w, h
    for _ in range(n):
        sz = max(1, (cw + 3) // 4) * max(1, (ch + 3) // 4) * bpb
        levels.append((cw, ch, off, sz))
        off += sz
        cw, ch = max(1, cw // 2), max(1, ch // 2)
    return dict(fourcc=fourcc, w=w, h=h, mips=n, bpb=bpb, levels=levels, end=off)


def full_mips(w, h):
    n, m = 0, max(w, h)
    while m:
        n += 1
        m >>= 1
    return n


def dds_decode_level(b, info, k):
    """RGBA uint8 of stored level k (Pillow decodes level 0 only, so re-wrap the level in its own header)."""
    w, h, off, sz = info["levels"][k]
    hdr = bytearray(b[:128])
    struct.pack_into("<II", hdr, 12, h, w)
    struct.pack_into("<I", hdr, 20, sz)
    struct.pack_into("<I", hdr, 28, 1)
    struct.pack_into("<I", hdr, 8, struct.unpack_from("<I", hdr, 8)[0] & ~DDSD_MIPMAPCOUNT)
    im = Image.open(io.BytesIO(bytes(hdr) + b[off:off + sz]))
    im.load()
    return np.asarray(im.convert("RGBA"))


def encode_level(arr_u8, fmt):
    """Pillow BCn encode of one level -> (header, block bytes)."""
    mode = "RGBA" if arr_u8.shape[2] == 4 else "RGB"
    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(arr_u8), mode).save(buf, format="DDS", pixel_format=fmt)
    r = buf.getvalue()
    h, w = arr_u8.shape[:2]
    bpb = 8 if fmt == "DXT1" else 16
    want = max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * bpb
    assert len(r) - 128 == want, (fmt, w, h, len(r) - 128, want)
    return r[:128], r[128:]


def _expand565(q):
    r, g, b = q[..., 0], q[..., 1], q[..., 2]
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.float64)


def _palette(e0, e1):
    c0, c1 = _expand565(e0), _expand565(e1)
    return np.stack([c0, c1, (2 * c0 + c1) / 3.0, (c0 + 2 * c1) / 3.0], 1)          # (N,4,3), 4-colour mode


def _assign(P, e0, e1, W):
    d = (((P[:, :, None, :] - _palette(e0, e1)[:, None, :, :]) ** 2) * W).sum(-1)    # (N,16,4)
    return d.argmin(-1), d.min(-1).sum(-1)


def _quant(e):
    s = np.array([31.0, 63.0, 31.0]) / 255.0
    return np.clip(np.round(e * s), 0, [31, 63, 31]).astype(np.int64)


def _lsfit(P, idx, W):
    """Least-squares endpoints for fixed indices (per channel 2x2 normal equations)."""
    wa = np.array([1.0, 0.0, 2 / 3.0, 1 / 3.0])[idx]            # weight of e0 per texel
    wb = 1.0 - wa
    aa, ab, bb = (wa * wa).sum(1), (wa * wb).sum(1), (wb * wb).sum(1)
    ap = (wa[..., None] * P).sum(1)
    bp = (wb[..., None] * P).sum(1)
    det = aa * bb - ab * ab
    ok = det > 1e-9
    detc = np.where(ok, det, 1.0)[:, None]
    e0 = np.where(ok[:, None], (bb[:, None] * ap - ab[:, None] * bp) / detc, P.mean(1))
    e1 = np.where(ok[:, None], (aa[:, None] * bp - ab[:, None] * ap) / detc, P.mean(1))
    return np.clip(e0, 0, 255), np.clip(e1, 0, 255)


def bc_colour_blocks(img, W=(1.0, 1.0, 0.02)):
    """Deterministic BC1/BC3 COLOUR-block encoder for a float (H,W,3) image in 0..255 units.

    Why not Pillow's encoder: on these low-amplitude normal maps its RG error was 3-6x the limit a
    4-point line allows (RMS R 2.65 vs ~0.9 levels at TARGET 0.25), which shows up as 4x4 block grain in
    the lit render. Here: PCA line -> 565 quantise -> nearest-palette indices -> least-squares refit ->
    coordinate descent (+-1 step on R0/R1/G0/G1). Error weighted to R,G (the only channels the shader
    reads, lightall_fp.glsl:443); B (z) is then least-squares fitted with the final indices. Always emits
    4-colour mode (c0 > c1, or c0 == c1 with all indices 0), so no decoder can fall into the 3-colour
    black/transparent entry. Returns bytes, 8 per block, blocks row-major."""
    H, Wd = img.shape[:2]
    H4, W4 = max(4, (H + 3) // 4 * 4), max(4, (Wd + 3) // 4 * 4)
    img = np.pad(img, ((0, H4 - H), (0, W4 - Wd), (0, 0)), mode="edge")
    P = img.reshape(H4 // 4, 4, W4 // 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3).astype(np.float64)
    Wv = np.asarray(W, np.float64)
    m = P.mean(1, keepdims=True)
    C = (P - m) * np.sqrt(Wv)
    cov = np.einsum("nki,nkj->nij", C, C)
    ax = np.linalg.eigh(cov)[1][:, :, -1] / np.sqrt(Wv)           # principal axis back in colour units
    ax /= np.maximum(np.linalg.norm(ax, axis=1, keepdims=True), 1e-12)
    t = ((P - m) * ax[:, None, :]).sum(-1)
    e0q = _quant(m[:, 0] + t.min(1)[:, None] * ax)
    e1q = _quant(m[:, 0] + t.max(1)[:, None] * ax)
    idx, err = _assign(P, e0q, e1q, Wv)
    for _ in range(2):
        f0, f1 = _lsfit(P, idx, Wv)
        c0q, c1q = _quant(f0), _quant(f1)
        c0q[:, 2], c1q[:, 2] = e0q[:, 2], e1q[:, 2]
        cidx, cerr = _assign(P, c0q, c1q, Wv)
        better = cerr < err
        e0q[better], e1q[better], idx[better], err[better] = c0q[better], c1q[better], cidx[better], cerr[better]
        for which, ch in ((0, 0), (1, 0), (0, 1), (1, 1)):
            for step in (-1, 1):
                t0, t1 = e0q.copy(), e1q.copy()
                tgt = t0 if which == 0 else t1
                tgt[:, ch] = np.clip(tgt[:, ch] + step, 0, 31 if ch == 0 else 63)
                cidx, cerr = _assign(P, t0, t1, Wv)
                better = cerr < err
                e0q[better], e1q[better], idx[better], err[better] = t0[better], t1[better], cidx[better], cerr[better]
    # B (z): least squares with the final indices; does not change the R,G reconstruction
    f0, f1 = _lsfit(P, idx, Wv)
    e0q[:, 2] = _quant(f0)[:, 2]
    e1q[:, 2] = _quant(f1)[:, 2]
    c0 = (e0q[:, 0] << 11) | (e0q[:, 1] << 5) | e0q[:, 2]
    c1 = (e1q[:, 0] << 11) | (e1q[:, 1] << 5) | e1q[:, 2]
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    idx = np.where(swap[:, None], np.array([1, 0, 3, 2])[idx], idx)
    idx = np.where((c0 == c1)[:, None], 0, idx)
    bits = (idx.astype(np.uint64) << (2 * np.arange(16, dtype=np.uint64))).sum(1)
    out = np.zeros((P.shape[0], 8), np.uint8)
    out[:, 0], out[:, 1] = c0 & 255, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 255, c1 >> 8
    for k in range(4):
        out[:, 4 + k] = (bits >> np.uint64(8 * k)) & np.uint64(255)
    return out.tobytes()


def box_half(a):
    """2x2 box average (degenerates to 2x1 / 1x2 on the last levels)."""
    H, W = a.shape[:2]
    C = a.shape[2]
    if H > 1 and W > 1:
        return a.reshape(H // 2, 2, W // 2, 2, C).mean((1, 3))
    if H == 1 and W > 1:
        return a.reshape(1, W // 2, 2, C).mean(2)
    if W == 1 and H > 1:
        return a.reshape(H // 2, 2, 1, C).mean(1)
    return a


# --------------------------------------------------------------------------------------- shader maths
def shader_tilt(rgba, s):
    """Degrees between the shaded normal and the surface normal, exactly as lightall_fp.glsl:443-446."""
    t = rgba[..., :2].astype(np.float64) / 255.0 - 0.5
    nxy = t * s
    r2 = (nxy ** 2).sum(-1)
    nz = np.sqrt(np.clip(0.25 - r2, 0.0, 1.0))
    return np.degrees(np.arctan2(np.sqrt(r2), nz))


def shader_normal(rgba, s):
    t = rgba[..., :2].astype(np.float64) / 255.0 - 0.5
    nxy = t * s
    nz = np.sqrt(np.clip(0.25 - (nxy ** 2).sum(-1), 0.0, 1.0))
    n = np.dstack([nxy, nz])
    return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)


# ---------------------------------------------------------------------------------------- relief bake
def dc_excess(src, info):
    """Level 0's mean xy minus the mean of today's 32x32 stored mip.

    Today's _nh were encoded by Pillow's DXT5 encoder, which pushes R up on high-variance blocks (a zero-mean
    synthetic normal field comes back with mean x +0.117). Today's mips were resized from the UNENCODED image
    and encoded per level, and their variance - hence their bias - falls with size: m3l3grass_1rough mean x
    is +0.196 at 1024 but +0.006 at 32x32. A ground normal map should average to straight up, so the level-0
    excess is an encoder LEAN, not relief: at cvar 1.25 it tilts the whole m3l3grass_1rough patch ~14 deg
    toward +s, which the lightmap path turns into a patch-wide brightness shift (lightall_fp.glsl:475-491)."""
    ref = max(0, info["mips"] - 6)                                   # 1024 -> level 5 (32x32)
    l0 = dds_decode_level(src, info, 0)[..., :2].astype(np.float64) / 255.0 * 2.0 - 1.0
    lr = dds_decode_level(src, info, ref)[..., :2].astype(np.float64) / 255.0 * 2.0 - 1.0
    return l0.mean((0, 1)) - lr.mean((0, 1))


def tilt_xy(xy, s):
    r = s * 0.5 * np.linalg.norm(xy, axis=-1)
    return np.degrees(np.arctan2(r, np.sqrt(np.clip(0.25 - r * r, 0.0, 1.0))))


def rebake_nh(src, target, delean=False):
    """Scale xy by target/CUR_STRENGTH, renormalise z, box mips, DXT5 colour re-encode, alpha verbatim.
    delean: first subtract dc_excess() (off-spec alternative; see there)."""
    info = dds_parse(src)
    assert info["fourcc"] == b"DXT5" and info["end"] == len(src)
    assert info["mips"] == full_mips(info["w"], info["h"])
    f = target / CUR_STRENGTH
    lv0 = dds_decode_level(src, info, 0).astype(np.float64)
    xy = lv0[..., :2] / 255.0 * 2.0 - 1.0
    dc = dc_excess(src, info) if delean else np.zeros(2)
    cur = (xy - dc) * f
    out = bytearray(src[:128])            # today's header: same format, size and mip count
    finite = True
    maxr2 = 0.0
    for k, (w, h, off, sz) in enumerate(info["levels"]):
        if k:
            cur = box_half(cur)
        assert cur.shape[:2] == (h, w), (cur.shape, w, h)
        finite &= bool(np.isfinite(cur).all())
        r2 = (cur ** 2).sum(-1)
        maxr2 = max(maxr2, float(r2.max()))
        z = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
        px = np.clip((np.dstack([cur, z]) + 1.0) * 0.5 * 255.0, 0.0, 255.0)         # float, unrounded
        colour = np.frombuffer(bc_colour_blocks(px), np.uint8).reshape(-1, 8)
        old = np.frombuffer(src[off:off + sz], np.uint8).reshape(-1, 16)
        assert colour.shape[0] == old.shape[0]
        new = np.concatenate([old[:, :8], colour], axis=1)      # BC3 block = 8 B alpha (verbatim) + 8 B colour
        out += new.tobytes()
    assert len(out) == len(src)
    return bytes(out), dict(finite=finite, max_xy_len=round(maxr2 ** 0.5, 4), dc=dc)


def check_nh(name, src, new, target, stats):
    si, ni = dds_parse(src), dds_parse(new)
    tag = "%s @%.2f" % (name.split("/")[-1][:-4], target)
    ok = True
    ok &= gate("mips complete " + tag, ni["mips"] == full_mips(ni["w"], ni["h"]) and ni["end"] == len(new)
               and ni["levels"][-1][:2] == (1, 1) and new[:128] == src[:128],
               "%d levels %dx%d -> %dx%d, header == today's" % (ni["mips"], ni["w"], ni["h"], *ni["levels"][-1][:2]))
    o0 = dds_decode_level(src, si, 0)
    n0 = dds_decode_level(new, ni, 0)
    dc = stats["dc"]
    xy0 = o0[..., :2].astype(np.float64) / 255.0 * 2.0 - 1.0 - dc
    t_today = float(shader_tilt(o0, CUR_STRENGTH).mean())
    t_cvar = float(shader_tilt(o0, target).mean())
    t_map = tilt_xy(xy0, target)
    t_target = float(t_map.mean())
    t_got = float(shader_tilt(n0, CUR_STRENGTH).mean())
    err = np.abs(shader_tilt(n0, CUR_STRENGTH) - t_map)
    what = "today@%.2f" % target if not dc.any() else "today minus lean (%+.3f,%+.3f) @%.2f; plain today@%.2f = %.2f" % (
        dc[0], dc[1], target, target, t_cvar)
    ok &= gate("mean tilt " + tag, abs(t_got - t_target) <= TILT_TOL_DEG,
               "today@1.25 %.2f deg | target (%s) %.2f | v2@1.25 %.2f | delta %+.3f | per-texel |err| mean %.2f p95 %.2f"
               % (t_today, what, t_target, t_got, t_got - t_target, err.mean(), np.percentile(err, 95)))
    if dc.any():
        m = (dds_decode_level(new, ni, 0)[..., :2].astype(np.float64) / 255.0 * 2.0 - 1.0).mean((0, 1)) / (target / CUR_STRENGTH)
        r = dds_decode_level(src, si, max(0, si["mips"] - 6))[..., :2].astype(np.float64).mean((0, 1)) / 255.0 * 2.0 - 1.0
        ok &= gate("lean removed " + tag, np.all(np.abs(m - r) <= 0.02),
                   "level-0 mean xy (unscaled) %+.3f,%+.3f vs today's 32x32 mip %+.3f,%+.3f" % (m[0], m[1], r[0], r[1]))
    per_level, zbad, nzbad, normbad, alpha_same = [], 0, 0, 0, True
    nmin, nmax = 9.0, 0.0
    for k in range(ni["mips"]):
        nk = dds_decode_level(new, ni, k)
        ok_k = dds_decode_level(src, si, k)
        v = nk[..., :3].astype(np.float64) / 255.0 * 2.0 - 1.0
        norm = np.linalg.norm(v, axis=-1)
        nmin, nmax = min(nmin, float(norm.min())), max(nmax, float(norm.max()))
        zbad += int((nk[..., 2] < 128).sum())                                        # stored z <= 0
        t = nk[..., :2].astype(np.float64) / 255.0 - 0.5
        nzbad += int((((CUR_STRENGTH * t) ** 2).sum(-1) >= 0.25).sum())              # shader N.z == 0
        normbad += int(((norm < 0.85) | (norm > 1.15)).sum())
        alpha_same &= bool((nk[..., 3] == ok_k[..., 3]).all())
        if k < 6:
            per_level.append(dict(level=k, size=int(nk.shape[1]),
                                  today_at_target=round(float(shader_tilt(ok_k, target).mean()), 2),
                                  v2_at_125=round(float(shader_tilt(nk, CUR_STRENGTH).mean()), 2)))
    ok &= gate("no NaN/zero normals, z>0 " + tag, stats["finite"] and zbad == 0 and nzbad == 0 and normbad == 0,
               "finite=%s, stored z<=0: %d, shader N.z==0: %d, |n| outside 0.85-1.15: %d (|n| %.3f-%.3f), max |xy| %.3f"
               % (stats["finite"], zbad, nzbad, normbad, nmin, nmax, stats["max_xy_len"]))
    ok &= gate("alpha (height) unchanged " + tag, alpha_same, "decoded alpha identical at every level")
    three = 0
    for (w, h, off, sz) in ni["levels"]:
        blk = np.frombuffer(new[off:off + sz], np.uint8).reshape(-1, 16)
        c0 = blk[:, 8].astype(np.int32) | (blk[:, 9].astype(np.int32) << 8)
        c1 = blk[:, 10].astype(np.int32) | (blk[:, 11].astype(np.int32) << 8)
        ix = blk[:, 12:16].astype(np.int64)
        three += int(((c0 < c1) | ((c0 == c1) & (ix.sum(1) != 0))).sum())
    ok &= gate("colour blocks 4-colour mode " + tag, three == 0, "blocks that a c0<=c1-honouring decoder would misread: %d" % three)
    print("  [INFO] per-mip mean tilt %s, today@%.2f (= the cvar test) / v2@1.25: %s" % (tag, target, "  ".join(
        "%d:%.2f/%.2f" % (d["size"], d["today_at_target"], d["v2_at_125"]) for d in per_level)))
    return ok, dict(today_125=round(t_today, 2), today_at_target=round(t_cvar, 2), target=round(t_target, 2),
                    v2_125=round(t_got, 2), lean_removed=[round(float(x), 4) for x in dc],
                    err_mean=round(float(err.mean()), 2), err_p95=round(float(np.percentile(err, 95)), 2),
                    levels=per_level)


# ------------------------------------------------------------------------------------------ conctrmdrk
def load_retail_conc(gog):
    pak, member, want = CONC_RETAIL
    with zipfile.ZipFile(os.path.join(gog, pak)) as z:
        real = [n for n in z.namelist() if n.lower() == member]
        assert len(real) == 1, real
        b = z.read(real[0])
    assert sha(b) == want, "retail conctrmdrk.tga changed: %s" % sha(b)
    im = Image.open(io.BytesIO(b))
    im.load()
    return np.asarray(im.convert("RGBA"))


def build_conc(retail_rgba):
    assert retail_rgba.shape == (32, 64, 4), retail_rgba.shape
    assert (retail_rgba[..., 3] == 0).all(), "retail alpha is expected to be all zero"
    rgb = retail_rgba[..., :3]
    P, S = 8, 4
    pad = np.pad(rgb, ((0, 0), (P, P), (0, 0)), mode="wrap")        # S tiles: wrap horizontally
    pad = np.pad(pad, ((P, P), (0, 0), (0, 0)), mode="edge")        # T: no cross-bleed top<->bottom
    ph, pw = pad.shape[:2]
    up = Image.fromarray(pad, "RGB").resize((pw * S, ph * S), Image.LANCZOS)
    up = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=3))      # bug-1129 recipe
    a = np.asarray(up)[P * S:P * S + 32 * S, P * S:P * S + 64 * S].astype(np.int32)
    lo = rgb.reshape(-1, 3).min(0)
    hi = rgb.reshape(-1, 3).max(0)
    a = np.clip(a, lo, hi).astype(np.uint8)                         # bug-1247: clamp to source range
    assert a.shape == (128, 256, 3)
    levels, hdr0 = [], None
    cur = a.astype(np.float64)
    while True:
        u8 = np.clip(np.round(cur), 0, 255).astype(np.uint8)
        hdr, data = encode_level(u8, "DXT1")
        if hdr0 is None:
            hdr0 = bytearray(hdr)
        levels.append(data)
        if cur.shape[0] == 1 and cur.shape[1] == 1:
            break
        cur = box_half(cur)
    struct.pack_into("<I", hdr0, 8, struct.unpack_from("<I", hdr0, 8)[0] | DDSD_MIPMAPCOUNT | DDSD_LINEARSIZE)
    struct.pack_into("<I", hdr0, 20, len(levels[0]))                # correct linear size (Pillow writes junk)
    struct.pack_into("<I", hdr0, 28, len(levels))
    struct.pack_into("<I", hdr0, 108, struct.unpack_from("<I", hdr0, 108)[0] | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP)
    assert struct.unpack_from("<I", hdr0, 80)[0] & 1 == 0, "DDPF_ALPHAPIXELS must not be set"
    return bytes(hdr0) + b"".join(levels), a


def dxt1_index3_blocks(b, info):
    """Blocks in 3-colour mode (c0 <= c1) that USE index 3 = black (and transparent in gl1's RGBA_DXT1)."""
    bad = 0
    for (w, h, off, sz) in info["levels"]:
        blk = np.frombuffer(b[off:off + sz], np.uint8).reshape(-1, 8)
        c0 = blk[:, 0].astype(np.int32) | (blk[:, 1].astype(np.int32) << 8)
        c1 = blk[:, 2].astype(np.int32) | (blk[:, 3].astype(np.int32) << 8)
        idx = (blk[:, 4:8].astype(np.uint32) << np.array([0, 8, 16, 24], np.uint32)).sum(1)
        for i in np.nonzero(c0 <= c1)[0]:
            v = int(idx[i])
            bw, bh = min(4, w), min(4, h)
            used = [(v >> (2 * (y * 4 + x))) & 3 for y in range(bh) for x in range(bw)]
            bad += 3 in used
    return bad


def check_conc(dds, retail_rgba):
    info = dds_parse(dds)
    ok = True
    ok &= gate("conctrmdrk mips complete", info["fourcc"] == b"DXT1" and info["w"] == 256 and info["h"] == 128
               and info["mips"] == full_mips(256, 128) and info["end"] == len(dds) and info["levels"][-1][:2] == (1, 1),
               "DXT1 %dx%d, %d levels -> %dx%d, %d bytes" % (info["w"], info["h"], info["mips"], *info["levels"][-1][:2], len(dds)))
    d0 = dds_decode_level(dds, info, 0)
    rm = retail_rgba[..., :3].reshape(-1, 3).astype(np.float64).mean(0)
    nm = d0[..., :3].reshape(-1, 3).astype(np.float64).mean(0)
    luma = lambda a: a[..., :3].astype(np.float64) @ np.array([0.299, 0.587, 0.114])
    ok &= gate("conctrmdrk mean RGB within +-%g of retail" % CONC_MEAN_TOL, np.all(np.abs(nm - rm) <= CONC_MEAN_TOL),
               "retail %.1f/%.1f/%.1f  v2 %.1f/%.1f/%.1f" % (*rm, *nm))
    dark_r = float((luma(retail_rgba) < 16).mean())
    dark_n = float((luma(d0) < 16).mean())
    ok &= gate("conctrmdrk not black", luma(d0).mean() > 40 and dark_n <= dark_r + 0.05,
               "mean luma %.1f (retail %.1f); luma<16 %.1f%% (retail %.1f%%)" % (luma(d0).mean(), luma(retail_rgba).mean(),
                                                                                   100 * dark_n, 100 * dark_r))
    a_ok = all((dds_decode_level(dds, info, k)[..., 3] == 255).all() for k in range(info["mips"]))
    i3 = dxt1_index3_blocks(dds, info)
    ok &= gate("conctrmdrk opaque (no alpha, no 3-colour black texels)", a_ok and i3 == 0,
               "alpha 255 at every level: %s; index-3 blocks: %d" % (a_ok, i3))
    # horizontal wrap: step across the S seam vs the interior column steps (informative + loose gate)
    L = luma(d0)
    steps = np.abs(np.roll(L, -1, axis=1) - L).mean(0)
    ok &= gate("conctrmdrk S-wrap seamless", steps[-1] <= 2.0 * np.median(steps[:-1]) + 1.0,
               "wrap step %.2f vs median interior %.2f" % (steps[-1], np.median(steps[:-1])))
    return ok, dict(retail_mean=[round(x, 1) for x in rm], v2_mean=[round(x, 1) for x in nm])


# ------------------------------------------------------------------------------------------------ pak
def read_pak(path):
    out = {}
    with zipfile.ZipFile(path) as z:
        for zi in z.infolist():
            out[zi.filename] = (z.read(zi), zi.date_time, zi.external_attr)
    return out


def write_pak(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(members):
            data, dt, ea = members[name]
            zi = zipfile.ZipInfo(name, date_time=dt)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = ea
            zi.create_system = 0
            z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buf.getvalue()


def build_candidate(src_members, target, conc_dds, delean=False):
    members = dict(src_members)
    stats = {}
    for nh in REBAKE:
        data, _, ea = src_members[nh]
        new, st = rebake_nh(data, target, delean)
        members[nh] = (new, FIXED_TS, ea)
        stats[nh] = st
    assert CONC not in members
    members[CONC] = (conc_dds, FIXED_TS, NEW_ATTR)
    return write_pak(members), stats


# ------------------------------------------------------------------------------------ pak stack check
def fs_key(name):
    """files.cpp:2834 FS_PathCmp: ASCII-lowercase, '\\' and ':' -> '/', ordinal compare."""
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else ("/" if c in "\\:" else c) for c in name)


def search_order(base, home, gog):
    """Highest priority first. FS_Startup adds main, then mainta (HZM unify), then maintt; per game
    gog -> base -> home; FS_AddGameDirectory prepends each sorted pak, then the loose dir (files.cpp:3083-3155)."""
    add, seen = [], set()
    for game in ("main", "mainta", "maintt"):
        for root in (gog, base, home):
            if not root:
                continue
            d = os.path.join(root, game)
            key = os.path.normcase(os.path.abspath(d))
            if key in seen or not os.path.isdir(d):
                continue
            seen.add(key)
            for p in sorted((f for f in os.listdir(d) if f.lower().endswith(".pk3")), key=fs_key):
                add.append(("pak", os.path.join(d, p)))
            add.append(("dir", d))
    return list(reversed(add))


_names = {}


def pak_members(path, candidate_names):
    if os.path.basename(path).lower() == PAK_NAME:
        return candidate_names                                     # the candidate replaces it in place
    if path not in _names:
        with zipfile.ZipFile(path) as z:
            _names[path] = {n.lower().replace("\\", "/") for n in z.namelist()}
    return _names[path]


def stack_check(label, order, candidate_names, paths):
    ok = True
    for p in paths:
        hits = []
        for kind, loc in order:
            if kind == "dir":
                if os.path.isfile(os.path.join(loc, *p.split("/"))):
                    hits.append("LOOSE " + loc)
            elif p in pak_members(loc, candidate_names):
                hits.append(loc)
        win = hits[0] if hits else None
        good = bool(win) and not win.startswith("LOOSE") and os.path.basename(win).lower() == PAK_NAME
        ok &= gate("resolve %s: %s" % (label, p.split("/")[-1]), good,
                   "winner %s; all .dds copies high->low: %s" % (win, " > ".join(
                       os.path.relpath(h, os.path.dirname(os.path.dirname(h))) if not h.startswith("LOOSE") else h
                       for h in hits)))
    return ok


# --------------------------------------------------------------------------------------------- previews
def _font(sz):
    try:
        return ImageFont.load_default(size=sz)
    except Exception:
        return ImageFont.load_default()


def lit(rgba_nh, s, albedo, el=28.0, az=135.0, amb=0.3):
    n = shader_normal(rgba_nh, s)
    e, a = np.radians(el), np.radians(az)
    L = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    sh = (amb + (1 - amb) * np.clip(n @ L, 0, None)) / (amb + (1 - amb) * L[2])      # flat texel == albedo
    return np.clip(albedo * sh[..., None], 0, 255).astype(np.uint8), np.clip(160 * sh, 0, 255).astype(np.uint8)


def preview_relief(out_png, nh_name, src_members, cands, crop=256):
    col_b = src_members[REBAKE[nh_name]][0]
    col = dds_decode_level(col_b, dds_parse(col_b), 0)[..., :3]
    today_b = src_members[nh_name][0]
    today = dds_decode_level(today_b, dds_parse(today_b), 0)
    H, W = today.shape[:2]
    if col.shape[:2] != (H, W):
        col = np.asarray(Image.fromarray(col, "RGB").resize((W, H), Image.BOX))
    y0, x0 = H // 2 - crop // 2, W // 2 - crop // 2
    sl = (slice(y0, y0 + crop), slice(x0, x0 + crop))
    alb = col[sl].astype(np.float64)
    panels = [("colour texture (unchanged)", col[sl], None)]
    c1, g1 = lit(today[sl], CUR_STRENGTH, alb)
    panels.append(("TODAY, cvar 1.25: %.1f deg" % shader_tilt(today, 1.25).mean(), c1, g1))
    for tgt, b in cands:
        d = dds_decode_level(b, dds_parse(b), 0)
        c, g = lit(d[sl], CUR_STRENGTH, alb)
        panels.append(("v2 %.2f, cvar 1.25: %.1f deg" % (tgt, shader_tilt(d, 1.25).mean()), c, g))
    gap, top = 8, 44
    sheet = Image.new("RGB", (len(panels) * crop + (len(panels) + 1) * gap, top + 2 * crop + 3 * gap + 20), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    f, fb = _font(12), _font(13)
    dr.text((gap, 6), "%s  -  lit with lightall_fp.glsl maths, sun 28 deg elev, ambient 0.3; centre %dpx crop of level 0"
            % (nh_name, crop), fill=(235, 235, 235), font=fb)
    for i, (lab, c, g) in enumerate(panels):
        x = gap + i * (crop + gap)
        dr.text((x, top - 18), lab, fill=(220, 220, 150), font=f)
        sheet.paste(Image.fromarray(c, "RGB"), (x, top))
        if g is not None:
            sheet.paste(Image.fromarray(g, "L").convert("RGB"), (x, top + crop + gap + 18))
    dr.text((gap, top + crop + gap), "row 2: lighting only (same maths, grey albedo)", fill=(200, 200, 200), font=f)
    sheet.save(out_png, optimize=True)


def preview_conc(out_png, retail_rgba, hdmem_rgba, v2_dds):
    v2 = dds_decode_level(v2_dds, dds_parse(v2_dds), 0)[..., :3]
    rows = [("RETAIL 64x32 TGA RGB (alpha is all 0, shader is opaque) - nearest x4",
             np.asarray(Image.fromarray(retail_rgba[..., :3], "RGB").resize((256, 128), Image.NEAREST))),
            ("TODAY: zzzzzzz_dds_hdmem.pk3 DXT5 256x128 - RGB is 0 = black trim on t3l1/t3l2", hdmem_rgba[..., :3]),
            ("v2: zzzzzzzzz_coop_terrain.pk3 DXT1 256x128 (retail RGB, 4x Lanczos + mild unsharp)", v2)]
    f = _font(14)
    Z, gap = 2, 10
    w = 2 * 256 * Z + 2 * gap
    sheet = Image.new("RGB", (w, len(rows) * (128 * Z + 24 + gap) + gap), (24, 24, 28))
    dr = ImageDraw.Draw(sheet)
    y = gap
    for lab, a in rows:
        dr.text((gap, y), lab + "   (tiled 2x along S)", fill=(235, 235, 235), font=f)
        tile = np.concatenate([a, a], axis=1)
        sheet.paste(Image.fromarray(np.ascontiguousarray(tile), "RGB").resize((512 * Z, 128 * Z), Image.NEAREST), (gap, y + 22))
        y += 128 * Z + 24 + gap
    sheet.save(out_png, optimize=True)


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="staging dir (never the mod tree or a game folder)")
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--gog", default=GOG_DEFAULT)
    ap.add_argument("--targets", default="0.6,0.25")
    ap.add_argument("--no-previews", action="store_true")
    ap.add_argument("--no-stack-check", action="store_true")
    ap.add_argument("--delean", action="store_true",
                    help="OFF-SPEC alternative: remove level 0's encoder lean first (dc_excess); writes v2d_* paks")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    for forbidden in (os.path.join(REPO, "hzm-mohaa-coop-mod"), a.gog, LIVE_BASE, APPDATA_HOME):
        if forbidden:
            fa = os.path.normcase(os.path.abspath(forbidden))
            assert not os.path.normcase(out).startswith(fa), "refusing to write into " + forbidden
    os.makedirs(out, exist_ok=True)
    targets = [float(t) for t in a.targets.split(",")]

    print("== source")
    src_bytes = open(a.src, "rb").read()
    gate("source pak is today's (sha256 72979342...)", sha(src_bytes) == SRC_SHA, sha(src_bytes))
    if sha(src_bytes) != SRC_SHA:
        sys.exit(2)
    src = read_pak(a.src)
    names = sorted(src)
    gate("source member set", len(names) == EXPECTED_MEMBERS and "CREDITS_terrain.txt" in src
         and all(n in src for n in REBAKE) and all(n in src for n in FROZEN_NH) and CONC not in src
         and not any("omaha_set4_shoreline" in n.lower() for n in names), "%d members" % len(names))
    changed = set(REBAKE) | {CONC}
    gate("no Omaha asset touched", not any(OMAHA.search(n) for n in changed), ", ".join(sorted(changed)))

    print("== conctrmdrk")
    retail = load_retail_conc(a.gog)
    conc, conc_rgb = build_conc(retail)
    conc2, _ = build_conc(retail)
    gate("conctrmdrk deterministic", conc == conc2, sha(conc)[:16])
    conc_ok, conc_stats = check_conc(conc, retail)

    report = dict(source=dict(path=a.src, sha256=SRC_SHA), conctrmdrk=conc_stats, candidates={})
    cand_bytes = []
    for t in targets:
        tag = ("d" if a.delean else "") + "s%03d" % round(t * 100)
        print("== candidate TARGET %.2f (%s): xy scale %.4f" % (t, tag, t / CUR_STRENGTH))
        pak, stats = build_candidate(src, t, conc, a.delean)
        pak2, _ = build_candidate(src, t, conc, a.delean)
        gate("deterministic rebuild " + tag, pak == pak2, sha(pak))
        with zipfile.ZipFile(io.BytesIO(pak)) as z:
            gate("zip CRC test " + tag, z.testzip() is None)
            cm = {zi.filename: z.read(zi) for zi in z.infolist()}
            order = [zi.filename for zi in z.infolist()]
        gate("entries sorted " + tag, order == sorted(order))
        gate("member set = today + conctrmdrk " + tag, set(cm) == set(src) | {CONC} and "CREDITS_terrain.txt" in cm
             and not any("omaha_set4_shoreline" in n.lower() for n in cm), "%d members" % len(cm))
        unchanged = [n for n in src if n not in REBAKE]
        diff = [n for n in unchanged if cm[n] != src[n][0]]
        gate("unchanged members byte-identical " + tag, not diff,
             "%d/%d identical incl. %s" % (len(unchanged) - len(diff), len(unchanged), ", ".join(x.split("/")[-1] for x in FROZEN_NH)))
        gate("frozen (Omaha-coupled/dead) _nh byte-identical " + tag, all(cm[n] == src[n][0] for n in FROZEN_NH))
        gate("rebaked _nh actually changed " + tag, all(cm[n] != src[n][0] for n in REBAKE))
        gate("conctrmdrk member == built " + tag, cm[CONC] == conc)
        tilt = {}
        for nh in REBAKE:
            _, tilt[nh] = check_nh(nh, src[nh][0], cm[nh], t, stats[nh])
        if not a.no_stack_check:
            cand_names = {n.lower() for n in cm}
            paths = sorted(changed)
            stack_check("live G:/mohaa-gl2 " + tag, search_order(LIVE_BASE, LIVE_HOME, a.gog), cand_names, paths)
            if APPDATA_HOME and os.path.isdir(APPDATA_HOME):
                stack_check("plain GOG launch " + tag, search_order(a.gog, APPDATA_HOME, None), cand_names, paths)
        fn = "zzzzzzzzz_coop_terrain.v2%s.pk3" % ("d_" + tag[1:] if a.delean else "_" + tag)
        with open(os.path.join(out, fn), "wb") as fh:
            fh.write(pak)
        cand_bytes.append((t, cm))
        report["candidates"][tag] = dict(file=fn, target=t, xy_scale=round(t / CUR_STRENGTH, 6), sha256=sha(pak),
                                         bytes=len(pak), tilt=tilt,
                                         member_sha256={n: sha(cm[n]) for n in sorted(changed)})

    gate("players' layout: terrain pak sorts above hdmem (both staged to home/maintt)",
         fs_key("zzzzzzz_dds_hdmem.pk3") < fs_key(PAK_NAME), "%r < %r" % (fs_key("zzzzzzz_dds_hdmem.pk3"), fs_key(PAK_NAME)))

    bk = os.path.join(out, "zzzzzzzzz_coop_terrain.v1_72979342.pk3")
    if not (os.path.isfile(bk) and sha(open(bk, "rb").read()) == SRC_SHA):
        shutil.copyfile(a.src, bk)
    gate("rollback copy of today's pak", sha(open(bk, "rb").read()) == SRC_SHA, os.path.basename(bk))

    if not a.no_previews:
        print("== previews")
        for nh in REBAKE:
            png = os.path.join(out, "sheet_%s%s.png" % (nh.split("/")[-1][:-4], "_delean" if a.delean else ""))
            preview_relief(png, nh, src, [(t, cm[nh]) for t, cm in cand_bytes])
            print("  ", png)
        pak, member = CONC_HDMEM
        with zipfile.ZipFile(os.path.join(a.gog, pak)) as z:
            real = [n for n in z.namelist() if n.lower() == member][0]
            hb = z.read(real)
        hd = dds_decode_level(hb, dds_parse(hb), 0)
        png = os.path.join(out, "conctrmdrk_before_after.png")
        preview_conc(png, retail, hd, conc)
        print("  ", png)

    report["gates"] = GATES
    with open(os.path.join(out, "gates%s.json" % ("_delean" if a.delean else "")), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1)
    bad = [g for g in GATES if not g["ok"]]
    print("\n%d gates, %d failed" % (len(GATES), len(bad)))
    for tag, c in report["candidates"].items():
        print("  %s  %s  %s" % (c["file"], c["sha256"], c["bytes"]))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

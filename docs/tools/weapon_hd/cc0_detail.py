"""CC0 scan DETAIL layers for the weapon-HD MATERIAL step (build_sheets.py, step 5).

Why: every pilot sheet is an upscale. The best weapon art on disk is HRRTM's 1536 px TGA (Kar98 1536x768); 251 of
the 298 jobs start from <= 1024 px. At the 4096 target nothing above the source's Nyquist exists in the art, so the
pilot filled that band with Gaussian noise (steel: two blurred normal-noise fields; wood: blurred noise streaked
along the structure tensor). This module fills the same band from real CC0 surface scans instead
(docs/tools/assets/weapon_detail_src, made by prep_cc0_detail.py; provenance in its SOURCES.json).

What reaches the sheet is only the BAND-PASSED luma of a scan (zero mean, unit std, soft-clipped at 3 sigma),
applied by build_sheets.py exactly where the procedural grain used to go, as a multiplicative / small additive
term inside the existing material masks. The art's colour, tone, markings and coarse grain figure are untouched,
so the luma-correlation and mean gates are unaffected by construction.

No tiling, no seams: a sheet-sized field is assembled from random crops of the master on a half-overlapping grid
of Hann-windowed cells, combined variance-preservingly (sum w*X / sqrt(sum w^2)). For band-passed (noise-like)
detail this is seamless and never repeats a crop at a fixed period. Directional detail (wood grain, machining
lines) is built at 6 orientations and chosen per texel by the ART's own structure-tensor angle - the same
selector the procedural oriented_streaks() used - so pores run along the grain the artist painted.
"""
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "weapon_detail_src")
NEEDED = ("wood_walnut_a.jpg", "wood_walnut_b.jpg", "wood_walnut_c.jpg", "wood_oak.jpg",
          "steel_pits.jpg", "steel_scuff.jpg", "steel_brushed.jpg", "steel_scratch.jpg")
WOOD = {"walnut": ("wood_walnut_a.jpg", "wood_walnut_b.jpg", "wood_walnut_c.jpg"), "oak": ("wood_oak.jpg",)}
ANGLES = 6
_cache = {}


def available():
    return all(os.path.exists(os.path.join(SRC, n)) for n in NEEDED)


def master(name):
    if name not in _cache:
        _cache[name] = np.asarray(Image.open(os.path.join(SRC, name)).convert("L"), np.float32)
    return _cache[name]


def _bandpass(a, lo, hi):
    b = ndimage.gaussian_filter(a, lo) - ndimage.gaussian_filter(a, hi)
    s = float(np.median(np.abs(b - np.median(b)))) * 1.4826 + 1e-6      # robust sigma: specks do not set the scale
    b = (b - float(np.median(b))) / s
    return 3.0 * np.tanh(b / 3.0)                                         # soft clip at 3 sigma (no lone hot pixels)


def _prepared(name, angle, zoom, lo, hi):
    """the master turned by `angle` (deg), scaled by `zoom` (sheet px per master px), band-passed IN SHEET PX."""
    key = (name, round(angle, 2), round(zoom, 4), lo, hi)
    if key in _cache:
        return _cache[key]
    a = master(name)
    if angle % 180:
        r = ndimage.rotate(a, angle, reshape=False, order=3, mode="reflect")
        h, w = a.shape
        t = math.radians(angle % 90)
        side = int(min(h, w) / (math.cos(t) + math.sin(t))) - 4                 # largest axis-aligned square inside
        y0, x0 = (h - side) // 2, (w - side) // 2
        a = r[y0:y0 + side, x0:x0 + side]
    if abs(zoom - 1.0) > 1e-3:
        a = ndimage.zoom(a, zoom, order=3, mode="reflect")
    b = _bandpass(a, lo, hi).astype(np.float32)
    _cache[key] = b
    return b


def _window(c):
    w = np.sin(np.pi * (np.arange(c) + 0.5) / c) ** 2
    return np.outer(w, w).astype(np.float32)


def tiled(name, H, W, rng, zoom, angle=0.0, lo=0.5, hi=6.0, iso=False, cell=None):
    """sheet-sized, never-repeating field of the master's band, zero mean / unit std.
    iso: the detail has no direction, so each cell is also randomly flipped / turned by 90 deg."""
    m = _prepared(name, angle, zoom, lo, hi)
    mh, mw = m.shape
    c = int(min(cell or 1024, mh, mw)) & ~1
    st = c // 2
    acc = np.zeros((H + 3 * c, W + 3 * c), np.float32)
    wsq = np.zeros_like(acc)
    win = _window(c)
    for y in range(-st, H + st, st):
        for x in range(-st, W + st, st):
            oy, ox = int(rng.integers(0, mh - c + 1)), int(rng.integers(0, mw - c + 1))
            p = m[oy:oy + c, ox:ox + c]
            if iso:
                p = np.rot90(p, int(rng.integers(4)))
                if rng.random() < 0.5:
                    p = p[:, ::-1]
            acc[y + c:y + 2 * c, x + c:x + 2 * c] += win * p
            wsq[y + c:y + 2 * c, x + c:x + 2 * c] += win * win
    f = acc[c:c + H, c:c + W] / np.sqrt(np.maximum(wsq[c:c + H, c:c + W], 1e-6))
    f -= f.mean()
    return f / (f.std() + 1e-6)


def art_theta(L):
    """grain / part direction per texel from the art (the selector oriented_streaks() used): radians, 0 = along x"""
    gx = ndimage.sobel(L, 1); gy = ndimage.sobel(L, 0)
    jxx = ndimage.gaussian_filter(gx * gx, 6.0); jyy = ndimage.gaussian_filter(gy * gy, 6.0)
    jxy = ndimage.gaussian_filter(gx * gy, 6.0)
    return 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2


def oriented(names, H, W, rng, zoom, theta, lo=0.5, hi=6.0):
    """directional field following theta: ANGLES orientations of the master(s), blended per texel by cos^8 and
    renormalised by sqrt(sum w^2) so the strength does not dip between two orientations"""
    out = np.zeros((H, W), np.float32); wsq = np.zeros((H, W), np.float32)
    name = names[int(rng.integers(len(names)))]     # ONE scan per sheet: mixing species per angle read as patches
    for k in range(ANGLES):
        ang = k * 180.0 / ANGLES
        # master grain runs along +x; image rows grow downward, so a texel angle theta needs a CW turn of theta
        f = tiled(name, H, W, rng, zoom, angle=-ang, lo=lo, hi=hi)
        w = (np.cos(theta - math.radians(ang)) ** 8).astype(np.float32)
        out += f * w; wsq += w * w
    f = out / np.sqrt(np.maximum(wsq, 1e-6))
    f -= f.mean()
    return f / (f.std() + 1e-6)


def steel_fields(kind, H, W, S, rng, theta):
    """(mult grain, additive floor, scratch layer) for blued | parkerized | painted, all zero-mean unit-std.
    Zooms are in sheet px per master px at a 4096 sheet (S = W / 4096): a 2048 master spans half a 4096 sheet."""
    z = lambda v: max(0.25, v * S)
    pits = tiled("steel_pits.jpg", H, W, rng, z(0.9), lo=0.5, hi=5.0, iso=True)
    scuff = tiled("steel_scuff.jpg", H, W, rng, z(0.7), lo=0.5, hi=4.0, iso=True)
    if kind == "blued":
        brushed = oriented(("steel_brushed.jpg",), H, W, rng, z(0.8), theta, lo=0.5, hi=4.0)
        mult = 0.65 * pits + 0.55 * brushed
    elif kind == "parkerized":
        mult = 0.8 * scuff + 0.45 * pits
    else:                                   # painted
        mult = 0.75 * scuff + 0.4 * pits
    mult /= mult.std() + 1e-6
    floor = tiled("steel_scuff.jpg", H, W, rng, z(0.5), lo=0.5, hi=2.5, iso=True)
    scratch = tiled("steel_scratch.jpg", H, W, rng, z(1.0), lo=0.5, hi=3.0, iso=True, cell=384)   # small master: small cells or its few long scratches recur
    return mult, floor, scratch


def wood_field(H, W, S, rng, theta, scan="walnut"):
    return oriented(WOOD.get(scan, WOOD["walnut"]), H, W, rng, max(0.25, 1.5 * S), theta, lo=0.5, hi=6.0 * max(S, 0.5))


def sources():
    p = os.path.join(SRC, "SOURCES.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

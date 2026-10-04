"""tile_treat.py - the "recon print" finish for coop mission tiles. PIL + numpy + scipy, deterministic, ONE parameter set.

A tile is a print CARD: a photographic print (the level, from a real in-engine frame or the retail briefing film)
on cream paper, with the level's name printed in the lower margin in the game's own button face.

    card(spec) -> PIL RGB 1024x1024

spec keys:
  src        path of the source frame (in-engine screenshot or retail briefing-film frame)
  crop       (x0, y0, x1, y1) in source pixels; aspect should be ~PHOTO_W/PHOTO_H (it is fitted, never stretched)
  paint      [(x0, y0, x1, y1), ...] source rects to remove (engine chat/kill-feed text) by diffusion fill
  key        median-luminance target after levelling (default 0.42; night scenes ~0.30)
  title      big line (the level's name)
  seed       grain/paper seed (default: hash of title)

No text is generated inside the photograph, no figures or props are added, moved or duplicated: the photo pass is
tone, grain and optics only, so everything in the picture is what the engine (or the archive film) drew.
"""
import hashlib
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontfit  # noqa: E402

S = 1024                        # card master size
MARGIN = 34
PHOTO_W, PHOTO_H = S - 2 * MARGIN, 752
BAND_Y = MARGIN + PHOTO_H       # caption band top
PAPER = np.array([232, 223, 197], np.float32) / 255     # war-room 'paper' (THEME.md 233 224 198), a touch aged
INK = (41, 23, 8)               # THEME ink
# toning ramp: silver-gelatin print, warm black -> neutral mid -> cream highlight
RAMP = [(0.00, (22, 17, 14)), (0.18, (52, 42, 34)), (0.50, (124, 109, 90)), (0.82, (203, 191, 166)), (1.00, (238, 230, 208))]
CHROMA = 0.16                   # share of the scene's own colour kept (desert/snow/green still read at thumbnail size)


def _seed(s):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)


def _lum(a):
    return a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722


def _diffuse_fill(a, rects):
    """Remove small overlays (chat / kill-feed lines) by harmonic fill from the surrounding pixels."""
    if not rects:
        return a
    m = np.zeros(a.shape[:2], bool)
    for x0, y0, x1, y1 in rects:
        m[y0:y1, x0:x1] = True
    out = a.copy()
    # seed with a wide blur of the unmasked image, then relax
    w = (~m).astype(np.float32)
    for c in range(3):
        num = ndimage.gaussian_filter(out[..., c] * w, 25)
        den = ndimage.gaussian_filter(w, 25) + 1e-6
        out[..., c][m] = (num / den)[m]
    for _ in range(300):
        for c in range(3):
            sm = ndimage.uniform_filter(out[..., c], 3)
            out[..., c][m] = sm[m]
    return out


def _ramp(l):
    xs = np.array([p for p, _ in RAMP], np.float32)
    out = np.zeros(l.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(l, xs, np.array([col[c] for _, col in RAMP], np.float32) / 255)
    return out


def photo(spec, W=PHOTO_W, H=PHOTO_H, crop=None):
    im = Image.open(spec["src"]).convert("RGB")
    a = np.asarray(im, np.float32) / 255
    a = _diffuse_fill(a, spec.get("paint", []))
    x0, y0, x1, y1 = crop or spec["crop"]
    # fit the requested box to the print aspect around its centre (never stretch)
    cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    asp = W / H
    if w / h > asp:
        w = h * asp
    else:
        h = w / asp
    box = [int(round(cx - w / 2)), int(round(cy - h / 2)), int(round(cx + w / 2)), int(round(cy + h / 2))]
    img = Image.fromarray((a * 255).clip(0, 255).astype(np.uint8)).crop(box).resize((W, H), Image.LANCZOS)
    a = np.asarray(img, np.float32) / 255
    rng = np.random.default_rng(spec.get("seed", _seed(spec["title"])))

    L = _lum(a)
    lo, hi = np.percentile(L, 0.5), np.percentile(L, 99.7)
    Ln = np.clip((L - lo) / max(hi - lo, 1e-3), 0, 1) * 0.94 + 0.03
    key = spec.get("key", 0.42)
    g = np.log(key) / np.log(max(np.median(Ln), 1e-3))
    g = float(np.clip(g, 0.55, 1.8))
    Ln = Ln ** g
    # clarity (large-radius local contrast) + fine sharpening, luminance only. Round 2 (review 2026-09-29): both eased -
    # at 0.30/0.35 they speckled dense foliage and haloed every edge.
    Ln = Ln + 0.20 * (Ln - ndimage.gaussian_filter(Ln, 16))
    Ln = Ln + 0.20 * (Ln - ndimage.gaussian_filter(Ln, 1.1))
    # print shoulder: highlights roll off instead of clipping (sunlit canvas read as a glowing box)
    Ln = np.where(Ln > 0.78, 0.78 + (Ln - 0.78) * 0.55, Ln)
    Ln = np.clip(Ln, 0, 1)
    # toned monochrome + a little of the scene's own chroma
    col = np.clip((a - lo) / max(hi - lo, 1e-3), 0, 1) ** g
    chroma = np.clip(col - _lum(col)[..., None], -0.035, 0.035)    # capped: no card may carry a colour cast
    out = _ramp(Ln) + CHROMA * chroma
    # halation around highlights (print from a slightly soft negative)
    hl = ndimage.gaussian_filter(np.clip(Ln - 0.80, 0, 1), 10)
    out += hl[..., None] * np.array([0.18, 0.14, 0.10], np.float32)
    # lens falloff
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / np.sqrt(2)
    out *= (1 - 0.20 * r ** 2.2)[..., None]
    # silver grain: two scales, strongest in the mid-tones
    gw = (4 * Ln * (1 - Ln) + 0.25)
    coarse = ndimage.zoom(rng.normal(0, 1, (H // 2 + 1, W // 2 + 1)).astype(np.float32), 2, order=1)[:H, :W]
    fine = rng.normal(0, 1, (H, W)).astype(np.float32)
    grain = ndimage.gaussian_filter(0.024 * coarse + 0.016 * fine, 0.55) * gw
    out += grain[..., None]
    # print density limits
    out = np.clip(out, np.array([18, 14, 12]) / 255, np.array([240, 232, 211]) / 255)
    return out


# On-screen shape of each widget, per menu layout (uiwidget.cpp SetVirtualScale): ui_menuCenter 1 scales uniformly, so a
# 100x100-unit tile is SQUARE; the default stretch scales x by W/640 and y by H/480, so at 16:9 the tile shows at 4:3 and
# the remaster's 164x123-unit print at 16:9. Each variant is AUTHORED at its on-screen shape and then squeezed into the
# texture, so the engine's own stretch restores it. 16:9 is the stretched target, as in the menu remaster's renders.
LAYOUT_ASPECT = {"c": 1.0, "s": 4.0 / 3.0}
PRINT_ASPECT = {"c": 4.0 / 3.0, "s": 16.0 / 9.0}


def paper(rng, w=S, h=S):
    base = np.ones((h, w, 3), np.float32) * PAPER
    mott = ndimage.gaussian_filter(rng.normal(0, 1, (h // 8 + 1, w // 8 + 1)).astype(np.float32), 3)
    mott = ndimage.zoom(mott, 8, order=1)[:h, :w]
    fib = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), 0.7)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx / w, 1 - xx / w), np.minimum(yy / h, 1 - yy / h))
    age = 1 - 0.05 * np.exp(-edge / 0.035)          # faint handling tone at the card's edge
    return base * (1 + 0.035 * mott[..., None] / (mott.std() + 1e-6) * 0.5 + 0.012 * fib[..., None]) * age[..., None]


def widest(spec, aspect):
    """The widest box of `aspect` on the card crop's centre, as tall as the card crop, kept inside the frame."""
    fw, fh = Image.open(spec["src"]).size
    x0, y0, x1, y1 = spec["crop"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    h = min(y1 - y0, fh)
    w = h * aspect
    if w > fw:
        w, h = fw, fw / aspect
    cx = min(max(cx, w / 2), fw - w / 2)
    cy = min(max(cy, h / 2), fh - h / 2)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def card(spec, layout="c"):
    """The tile card for one menu layout, returned as the S x S texture master."""
    cw = int(round(S * LAYOUT_ASPECT[layout]))
    pw = cw - 2 * MARGIN
    # a source narrower than the window (a 4:3 retail still) is printed at its own shape, centred, paper either side
    if "max_aspect" in spec:
        pw = min(pw, int(PHOTO_H * spec["max_aspect"]))
    px0 = (cw - pw) // 2
    rng = np.random.default_rng(spec.get("seed", _seed(spec["title"])) + 7)
    c = paper(rng, cw, S)
    box = spec.get("crop_" + layout) or (spec["crop"] if layout == "c" else widest(spec, pw / PHOTO_H))
    c[MARGIN:MARGIN + PHOTO_H, px0:px0 + pw] = photo(spec, pw, PHOTO_H, crop=box)
    im = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    caption(im, spec["title"])
    return im.resize((S, S), Image.LANCZOS) if cw != S else im


def caption(im, title):
    """The level's name in the lower margin: Bahnschrift SemiBold Condensed (the facfont HD face), ink on paper.
    One line at 104 px (96 if needed), else a balanced two-line wrap at <= 92 px. No kicker line: at 720p it drew
    ~4 px letters (review 2026-09-29) and the mission header already names the mission."""
    d = ImageDraw.Draw(im)
    cw = im.width
    # wrap by the NARROW (square) layout's width for BOTH layouts, so a title breaks identically in c and s
    # ("Return to Schmerzen Briefing" used to wrap in c and run on one line in s)
    maxw = S - 2 * MARGIN - 24
    # one size across the grid: 104 px, 96 only when a single line needs it, else two lines at <= 92
    px, lines = fontfit.fit_title(title, maxw, sizes=[104, 96, 92, 88, 84, 80, 76, 72], min_one=96, max_two=92)
    f = fontfit.caption_font(px, weight=600, width=75)
    band_top, band_bottom = BAND_Y + 8, S - 14
    lh = px * (0.98 if len(lines) == 1 else 0.92)
    block = lh * len(lines)
    top = band_top + max(0, (band_bottom - band_top - block) / 2) - px * 0.14
    for i, ln in enumerate(lines):
        tw = fontfit.text_w(f, ln)
        bx = f.getbbox(ln)
        d.text(((cw - tw) / 2 - bx[0], top + i * lh), ln, font=f, fill=INK)


def game_texture(card_im, layout="c", size=512):
    """The shipped texture: 512 JPEG. Downsample with a gentle post-sharpen so the caption stays crisp at 225 px."""
    t = card_im.resize((size, size), Image.LANCZOS)
    a = np.asarray(t, np.float32)
    a = a + 0.12 * (a - ndimage.gaussian_filter(a, (0.8, 0.8, 0)))
    # menu art is registered no-mip (RE_RegisterShaderNoMip), so at 200-300 px the GPU's bilinear taps skip texels and
    # fine grain sparkles in dark areas: pre-soften the PHOTO only (qa_sampling.py); the caption keeps its edge
    cw = S * LAYOUT_ASPECT[layout]
    kx, ky = size / cw, size / S
    y0, y1 = int(MARGIN * ky), int((MARGIN + PHOTO_H) * ky)
    x0, x1 = int(MARGIN * kx), int((cw - MARGIN) * kx)          # (a pillarboxed photo softens a little paper too)
    a[y0:y1, x0:x1] = ndimage.gaussian_filter(a[y0:y1, x0:x1], (0.75, 0.75, 0))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def print_photo(spec, layout="c", H=768):
    """War-room print: the same frame and finish, caption-free (the remaster's engine caption sits BELOW the rect,
    station_layouts.py COOPOPS tiles_large 164x123 / tiles 92x69 menu units). Authored at the on-screen shape
    (4:3 centred, 16:9 stretched) and returned squeezed to a 4:3 1024x768 master. spec['pcrop_<layout>'] overrides."""
    asp = PRINT_ASPECT[layout]
    W = int(round(H * asp))
    pa = min(asp, spec.get("max_aspect", asp))
    pw = int(round(H * pa))
    box = spec.get("pcrop_" + layout) or widest(spec, pa)
    p = photo(spec, pw, H, crop=box)
    if pw < W:              # narrower source: print at its own shape on paper (the print's own white border)
        rng = np.random.default_rng(spec.get("seed", _seed(spec["title"])) + 11)
        full = paper(rng, W, H)
        full[:, (W - pw) // 2:(W - pw) // 2 + pw] = p
        p = full
    im = Image.fromarray((np.clip(p, 0, 1) * 255).astype(np.uint8))
    return im.resize((1024, 768), Image.LANCZOS) if W != 1024 else im


def fit_box(aspect, focus, frame, allow=None):
    """Smallest box of `aspect` that contains `focus` (x0,y0,x1,y1), grown symmetrically, kept inside `allow`
    (default: the whole frame). If the allowed region cannot hold it, the box is the largest one of `aspect` inside
    `allow`, centred on the focus (the focus is then trimmed - reported by the builder)."""
    fw, fh = frame
    ax0, ay0, ax1, ay1 = allow or (0, 0, fw, fh)
    fx0, fy0, fx1, fy1 = focus
    w, h = fx1 - fx0, fy1 - fy0
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    maxw, maxh = ax1 - ax0, ay1 - ay0
    if w > maxw or h > maxh:
        s = min(maxw / w, maxh / h)
        w, h = w * s, h * s
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    x0 = min(max(cx - w / 2, ax0), ax1 - w)
    y0 = min(max(cy - h / 2, ay0), ay1 - h)
    return (x0, y0, x0 + w, y0 + h)

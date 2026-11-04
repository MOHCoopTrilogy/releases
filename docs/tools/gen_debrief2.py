#!/usr/bin/env python3
"""gen_debrief2.py - art + tables for the END-OF-MISSION debrief, take two (v1.10.62/63, branch debrief2).

user (2026-11-03): "Can we do an overhaul of the progression at the end of each level, make a more visually appealing
rank up bar, make sure the rank insignia look crisp. The unlock items would be nice if it came on screen one at a
time with a picture of what it unlocked... like modern games do."

The debrief is DRAWN by cgame (code/cgame/cg_coopdebrief.c) from data the server sends (coop_mod/debrief2.scr).
Everything it draws that is a picture comes from here. Nothing is AI art: every shape is a vector built in code
(PIL polygons / ellipses, supersampled 4x and box-reduced) from the real WW2 US Army insignia patterns, and the
weapon pictures are the use-to-loot silhouettes (docs/proposals/use_pickup_2026-10-05/tools/build_icons.py), which
are the guns' own world-model outlines.

  fixes  textures/hud/coop_db2/*.tga      new files -> the small fixes pak (docs/tools/gen_fixes_pak.py), never the
                                           1.3 GB texture pak (bug-3901 gate)
  mod    scripts/coop_debrief2.shader     every texture above: nomipmaps + nopicmip, rgbGen/alphaGen global
  mod    coop_mod/debrief2_gen.scr        reward token -> picture table (weapons by their own silhouette)

    python docs/tools/gen_debrief2.py                       write all of it (defaults below)
    python docs/tools/gen_debrief2.py --check               exit 1 when any output is stale
    python docs/tools/gen_debrief2.py --preview out.png     contact sheet of every texture (QA)
    --mod <tree> --eng <tree> --fixes <dir>

Rank insignia (index = xp.scr coop_xp_rankName): 0 Private (no stripes: the enlisted "U.S." collar disc), 1 PFC, 2 T/5,
3 Cpl, 4 T/4, 5 Sgt, 6 T/3, 7 SSgt, 8 TSgt, 9 1st Sgt, 10 MSgt (1942 pattern: khaki chevrons on dark blue), then
2nd Lt gold bar, 1st Lt silver bar, Capt two silver bars, Maj gold oak leaf, Lt Col silver oak leaf, Col silver eagle,
Brig Gen 1 star ... Gen 4 stars, General of the Army 5 stars in a ring.
"""
import argparse, io, json, math, os, re, sys, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SS = 4
TEX = "textures/hud/coop_db2"
FONTS = "C:/Windows/Fonts/"

# ---------------------------------------------------------------------------------------------- helpers
def down(im, size):
    return im.resize(size, Image.LANCZOS)


def mask_poly(W, H, polys, ellipses=(), sub=()):
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon([(float(x), float(y)) for x, y in p], fill=255)
    for e in ellipses:
        d.ellipse(e, fill=255)
    for p in sub:
        if len(p) == 4 and not isinstance(p[0], tuple):
            d.ellipse(p, fill=0)
        else:
            d.polygon([(float(x), float(y)) for x, y in p], fill=0)
    return np.array(im).astype(np.float32) / 255.0


def emboss(m, blur, light=(-0.6, -0.8)):
    """relief from a coverage mask: positive on edges facing the light (top-left)"""
    b = ndimage.gaussian_filter(m, blur)
    gy, gx = np.gradient(b)
    n = -(gx * light[0] + gy * light[1])
    return n / (np.abs(n).max() + 1e-6)


def rgba(rgb, a):
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def over(dst, src):
    """alpha-over two float RGBA arrays (H,W,4) in 0..1"""
    a = src[..., 3:4] + dst[..., 3:4] * (1 - src[..., 3:4])
    rgb = (src[..., :3] * src[..., 3:4] + dst[..., :3] * dst[..., 3:4] * (1 - src[..., 3:4])) / np.maximum(a, 1e-6)
    return np.dstack([rgb, a])


def layer(mask, rgb):
    """float layer: rgb (H,W,3) 0..255 or a colour, coverage mask"""
    H, W = mask.shape
    if np.ndim(rgb) == 1:
        rgb = np.broadcast_to(np.array(rgb, float), (H, W, 3))
    return np.dstack([rgb / 255.0, mask])


def to_img(f):
    return Image.fromarray((np.clip(f, 0, 1) * 255).astype(np.uint8), "RGBA")


def fit_center(img, size, margin):
    """crop to content, scale to fit (size - 2 margin) keeping aspect, centre on a transparent canvas"""
    bb = img.getbbox()
    img = img.crop(bb)
    k = min((size - 2 * margin) / img.width, (size - 2 * margin) / img.height)
    img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return out


# ---------------------------------------------------------------------------------------------- metal
GOLD = ((250, 226, 150), (212, 166, 66), (120, 82, 26))
SILVER = ((250, 250, 246), (196, 200, 204), (104, 108, 114))
BRASS = ((236, 204, 128), (182, 142, 62), (98, 70, 26))


def metal(mask, pal, engrave=None, bevel=None):
    """mask float HxW at supersample. Returns float RGBA."""
    H, W = mask.shape
    ys = np.where(mask.max(1) > 0.5)[0]
    y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, H - 1)
    t = np.clip((np.arange(H) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    top, mid, bot = (np.array(c, float) for c in pal)
    base = np.where(t < 0.45, top + (mid - top) * (t / 0.45), mid + (bot - mid) * ((t - 0.45) / 0.55))
    base = np.broadcast_to(base, (H, W, 3)).copy()
    bev = bevel or max(3.0, W * 0.006)
    e = emboss(mask, bev)
    base += e[..., None] * 70
    # rim: darken the outer few pixels for a struck edge
    dist = ndimage.distance_transform_edt(mask > 0.5)
    rim = np.clip(1 - dist / (bev * 1.6), 0, 1)
    base *= (1 - 0.35 * rim)[..., None]
    if engrave is not None:
        g = ndimage.gaussian_filter(engrave, 1.2)
        base *= (1 - 0.55 * g)[..., None]
        hl = ndimage.shift(ndimage.gaussian_filter(engrave, 1.2), (2.5, 2.5), order=1)
        base += (np.clip(hl - g, 0, 1) * 60)[..., None]
    out = layer(mask, base)
    # dark keyline + soft drop shadow so the shape reads on paper and on dark
    key = np.clip(ndimage.gaussian_filter((ndimage.distance_transform_edt(mask < 0.5) <= W * 0.006).astype(np.float32), 1.0), 0, 1)
    sh = ndimage.shift(ndimage.gaussian_filter(key, W * 0.012), (W * 0.012, W * 0.008), order=1) * 0.55
    under = layer(np.maximum(key * 0.95, sh), (22, 18, 12))
    return over(under, out)


# ---------------------------------------------------------------------------------------------- enlisted
NAVY = (26, 32, 58)
KHAKI_TOP = (214, 198, 148)
KHAKI_BOT = (150, 132, 86)


def chevron_poly(cx, yA, W, R, T):
    """inverted V, apex at (cx, yA), arms to (cx +/- W/2, yA + R), stripe thickness T (perpendicular)"""
    th = math.atan2(R, W / 2)
    dT = T / math.cos(th)
    xl, xr, ye = cx - W / 2, cx + W / 2, yA + R
    return [(xl, ye), (cx, yA), (xr, ye), (xr, ye + dT), (cx, yA + dT), (xl, ye + dT)]


def rocker_poly(cx, yE, W, D, T, n=48):
    """arc band, ends at y = yE, sagging D at the centre (smile), thickness T"""
    top, bot = [], []
    for i in range(n + 1):
        u = -1 + 2 * i / n
        x = cx + u * W / 2
        y = yE + D * (1 - u * u)
        top.append((x, y))
        bot.append((x, y + T))
    return top + bot[::-1]


def enlisted(chev, rock, tech=False, lozenge=False, S=1024):
    cx = S / 2
    W, R, T, G = 0.80 * S, 0.27 * S, 0.075 * S, 0.034 * S
    polys = []
    y = 0.0
    for k in range(chev):
        polys.append(chevron_poly(cx, y, W, R, T))
        y += T / math.cos(math.atan2(R, W / 2)) + G
    ends_y = R + (chev - 1) * (T / math.cos(math.atan2(R, W / 2)) + G) + T / math.cos(math.atan2(R, W / 2))
    D = 0.24 * S
    ry = ends_y + G
    for k in range(rock):
        polys.append(rocker_poly(cx, ry, W, D, T))
        ry += T + G
    extra = []
    apex_inner = (chev - 1) * (T / math.cos(math.atan2(R, W / 2)) + G) + T / math.cos(math.atan2(R, W / 2))
    if tech:
        # the T sits in the open angle under the lowest chevron (T/5, T/4) or in the lens above the rocker (T/3)
        # the bar must clear the V: at depth y under the inner apex the opening is y * (W/2) / R wide each side
        ty = apex_inner + (0.15 if rock else 0.165) * S
        tw, tb, sw, sh = 0.20 * S, 0.054 * S, 0.062 * S, 0.14 * S
        extra.append([(cx - tw / 2, ty), (cx + tw / 2, ty), (cx + tw / 2, ty + tb), (cx + sw / 2, ty + tb),
                      (cx + sw / 2, ty + sh), (cx - sw / 2, ty + sh), (cx - sw / 2, ty + tb), (cx - tw / 2, ty + tb)])
    if lozenge:
        ly = apex_inner + 0.075 * S
        lh, lw = 0.20 * S, 0.15 * S
        extra.append([(cx, ly), (cx + lw / 2, ly + lh / 2), (cx, ly + lh), (cx - lw / 2, ly + lh / 2)])
    allp = polys + extra
    maxy = max(p[1] for poly in allp for p in poly)
    H = int(maxy + 0.12 * S)
    off = 0.06 * S
    allp = [[(x, yy + off) for x, yy in p] for p in allp]
    Wc = S
    stripes = mask_poly(Wc, H + int(off), allp)
    # dark blue backing, cut close round every stripe (the 1942 pattern: khaki on dark blue)
    back = (ndimage.distance_transform_edt(stripes < 0.5) <= 0.022 * S).astype(np.float32)
    back = ndimage.gaussian_filter(back, 1.2)
    Hh, Ww = stripes.shape
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:Hh, 0:Ww]
    twill = (np.sin((xx + yy) * 0.55) * 0.5 + 0.5)
    navy = np.array(NAVY, float)[None, None, :] * (0.92 + 0.12 * twill[..., None])
    backf = layer(back, navy)
    # khaki stripes: vertical gradient, embroidered diagonal thread, raised edge
    t = (yy / max(1, Hh))[..., None]
    kh = np.array(KHAKI_TOP, float) * (1 - t) + np.array(KHAKI_BOT, float) * t
    thread = np.sin((xx - yy) * 0.9) * 0.5 + 0.5
    kh = kh * (0.94 + 0.08 * thread[..., None])
    e = emboss(stripes, 5.0)
    kh = kh + e[..., None] * 55
    dist = ndimage.distance_transform_edt(stripes > 0.5)
    kh = kh * (1 - 0.25 * np.clip(1 - dist / 9.0, 0, 1))[..., None]
    stf = layer(stripes, kh)
    sh = ndimage.shift(ndimage.gaussian_filter(back, 10), (10, 7), order=1) * 0.5
    f = over(over(layer(sh, (10, 8, 6)), backf), stf)
    return to_img(f)


def collar_disc(S=1024):
    """Private: no stripes - the enlisted man's brass "U.S." collar disc"""
    r = 0.40 * S
    c = S / 2
    disc = mask_poly(S, S, [], ellipses=[(c - r, c - r, c + r, c + r)])
    inner = mask_poly(S, S, [], ellipses=[(c - r * 0.86, c - r * 0.86, c + r * 0.86, c + r * 0.86)])
    ring = np.clip(disc - inner, 0, 1)
    txt = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(txt)
    f = ImageFont.truetype(FONTS + "georgiab.ttf", int(0.30 * S))
    s = "U.S."
    bb = d.textbbox((0, 0), s, font=f)
    d.text((c - (bb[2] + bb[0]) / 2, c - (bb[3] + bb[1]) / 2), s, font=f, fill=255)
    letters = np.array(txt).astype(np.float32) / 255
    # field slightly recessed: engrave the ring boundary, letters raised
    eng = np.clip(ndimage.distance_transform_edt(inner < 0.5) <= 3, 0, 1).astype(np.float32) * inner.max()
    eng = np.clip((np.abs(ndimage.distance_transform_edt(inner > 0.5)) < 4) & (disc > 0.5), 0, 1).astype(np.float32)
    base = metal(disc, BRASS, engrave=eng)
    let = metal(letters, BRASS, bevel=4.0)
    return to_img(over(base, let))


# ---------------------------------------------------------------------------------------------- officers
def bar_shape(S, cx, cy, w, h):
    r = h * 0.22
    im = Image.new("L", (S, S), 0)
    ImageDraw.Draw(im).rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=r, fill=255)
    m = np.array(im).astype(np.float32) / 255
    im2 = Image.new("L", (S, S), 0)
    i = h * 0.16
    ImageDraw.Draw(im2).rounded_rectangle([cx - w / 2 + i, cy - h / 2 + i, cx + w / 2 - i, cy + h / 2 - i], radius=r * 0.6, outline=255, width=max(2, int(S * 0.006)))
    return m, np.array(im2).astype(np.float32) / 255


def bars(n, pal, S=1024):
    w, h = 0.78 * S, 0.22 * S
    gap = 0.07 * S
    tot = n * h + (n - 1) * gap
    out = np.zeros((S, S, 4))
    for k in range(n):
        cy = S / 2 - tot / 2 + h / 2 + k * (h + gap)
        m, eng = bar_shape(S, S / 2, cy, w, h)
        out = over(out, metal(m, pal, engrave=eng))
    return to_img(out)


def oak_leaf(pal, S=1024):
    L = 0.80 * S
    top = 0.08 * S
    cx = S / 2
    pts_r, pts_l = [], []
    n = 400
    for i in range(n + 1):
        t = i / n
        env = math.sin(math.pi * min(1.0, t * 1.05)) ** 0.75 if t < 0.95 else 0.0
        env = max(env, 0.0)
        lob = 0.70 + 0.30 * abs(math.sin(math.pi * 4.5 * (t - 0.03)))
        w = 0.25 * S * env * lob
        if t > 0.86:
            w *= max(0.0, (0.95 - t) / 0.09)
        y = top + t * L * 0.86
        pts_r.append((cx + w, y))
        pts_l.append((cx - w, y))
    leaf = pts_r + pts_l[::-1]
    stem = [(cx - 0.018 * S, top + 0.80 * L), (cx + 0.018 * S, top + 0.80 * L), (cx + 0.03 * S, top + L), (cx - 0.005 * S, top + L)]
    m = mask_poly(S, S, [leaf, stem])
    eng = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(eng)
    lw = max(3, int(S * 0.008))
    d.line([(cx, top + 0.05 * L), (cx, top + 0.84 * L)], fill=255, width=lw)
    for k in range(4):
        tk = 0.16 + k * 0.16
        y = top + tk * L * 0.86
        for sgn in (-1, 1):
            d.line([(cx, y + 0.05 * L), (cx + sgn * 0.15 * S, y)], fill=255, width=lw)
    eng = np.array(eng).astype(np.float32) / 255 * m
    return fit_center(to_img(metal(m, pal, engrave=eng)), 1024, 40)


def eagle(pal, S=1024):
    """Colonel: spread eagle, wings up, head to its right, shield on the breast - heraldic, symmetric save the head"""
    k = S / 1000.0
    lw = [(430, 470), (380, 380), (330, 300), (265, 225), (190, 160), (105, 120), (60, 128),
          (88, 168), (52, 196), (98, 222), (64, 258), (118, 280), (88, 320), (150, 336), (128, 378), (196, 386),
          (186, 430), (258, 430), (268, 470), (340, 476), (400, 530), (440, 560)]
    rw = [(1000 - x, y) for x, y in lw][::-1]
    body = [(440, 560), (420, 470), (452, 430), (548, 430), (580, 470), (560, 560), (560, 690), (440, 690)]
    tail = [(445, 680), (555, 680), (612, 800), (575, 792), (560, 838), (528, 806), (500, 850), (472, 806),
            (440, 838), (425, 792), (388, 800)]
    neck = [(462, 445), (500, 352), (540, 330), (566, 360), (540, 450)]
    head_c, head_r = (548, 318), 52
    beak = [(586, 300), (652, 322), (618, 336), (598, 352), (584, 340)]
    polys = [[(x * k, y * k) for x, y in p] for p in (lw, rw, body, tail, neck, beak)]
    ell = [((head_c[0] - head_r) * k, (head_c[1] - head_r) * k, (head_c[0] + head_r) * k, (head_c[1] + head_r) * k)]
    m = mask_poly(S, S, polys, ellipses=ell)
    eng = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(eng)
    w = max(3, int(S * 0.007))
    # shield: chief band + pales
    sh = [(452, 470), (548, 470), (548, 600), (500, 650), (452, 600)]
    d.polygon([(x * k, y * k) for x, y in sh], outline=255, width=w)
    d.line([(452 * k, 505 * k), (548 * k, 505 * k)], fill=255, width=w)
    for x in (470, 487, 504, 521, 536):
        d.line([(x * k, 505 * k), (x * k, (630 - abs(x - 500) * 0.9) * k)], fill=255, width=max(2, w - 1))
    # wing feathers: a few long strokes following the wing
    for side in (1, -1):
        for a0, a1 in (((420, 455), (150, 210)), ((410, 470), (130, 300)), ((415, 490), (175, 390)), ((425, 510), (250, 450))):
            x0, y0 = a0
            x1, y1 = a1
            if side < 0:
                x0, x1 = 1000 - x0, 1000 - x1
            d.line([(x0 * k, y0 * k), (x1 * k, y1 * k)], fill=255, width=w)
    # tail feather splits
    for x in (472, 500, 528):
        d.line([(x * k, 700 * k), (x * k + (x - 500) * 0.8 * k, 800 * k)], fill=255, width=w)
    # eye
    d.ellipse([(560 - 9) * k, (306 - 9) * k, (560 + 9) * k, (306 + 9) * k], fill=255)
    eng = np.array(eng).astype(np.float32) / 255 * m
    return fit_center(to_img(metal(m, pal, engrave=eng)), 1024, 36)


def star_layers(S, cx, cy, r, pal):
    """five-pointed star with ten facets (each point split light / dark) - the struck-metal look"""
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.40
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    m = mask_poly(S, S, [pts])
    top, mid, bot = (np.array(c, float) for c in pal)
    rgb = np.zeros((S, S, 3))
    for i in range(10):
        tri = [(cx, cy), pts[i], pts[(i + 1) % 10]]
        tm = mask_poly(S, S, [tri])
        # light from the top-left: facet normal angle
        a = -math.pi / 2 + (i + 0.5) * math.pi / 5
        lit = 0.5 + 0.5 * math.cos(a - math.radians(-135))
        c = bot + (top - bot) * (0.25 + 0.75 * lit)
        rgb += tm[..., None] * c
    out = layer(m, rgb)
    key = ndimage.gaussian_filter((ndimage.distance_transform_edt(m < 0.5) <= S * 0.006).astype(np.float32), 1.0)
    sh = ndimage.shift(ndimage.gaussian_filter(key, S * 0.01), (S * 0.01, S * 0.007), order=1) * 0.5
    return over(layer(np.maximum(key * 0.95, sh), (22, 18, 12)), out)


def stars(n, S=1024):
    out = np.zeros((S, S, 4))
    if n <= 4:
        r = {1: 0.40, 2: 0.25, 3: 0.17, 4: 0.13}[n] * S
        step = 2.05 * r * 0.98
        x0 = S / 2 - step * (n - 1) / 2
        for k in range(n):
            out = over(out, star_layers(S, x0 + k * step, S / 2 + r * 0.08, r, SILVER))
    else:
        R = 0.27 * S
        r = 0.165 * S
        for k in range(5):
            a = -math.pi / 2 + k * 2 * math.pi / 5
            out = over(out, star_layers(S, S / 2 + R * math.cos(a), S / 2 + 0.02 * S + R * math.sin(a), r, SILVER))
    return to_img(out)


def rank_art(i):
    if i == 0:
        return collar_disc()
    table = {1: (1, 0, 0, 0), 2: (2, 0, 1, 0), 3: (2, 0, 0, 0), 4: (3, 0, 1, 0), 5: (3, 0, 0, 0), 6: (3, 1, 1, 0),
             7: (3, 1, 0, 0), 8: (3, 2, 0, 0), 9: (3, 3, 0, 1), 10: (3, 3, 0, 0)}
    if i in table:
        c, r, t, l = table[i]
        return enlisted(c, r, tech=bool(t), lozenge=bool(l))
    if i == 11:
        return bars(1, GOLD)
    if i == 12:
        return bars(1, SILVER)
    if i == 13:
        return bars(2, SILVER)
    if i == 14:
        return oak_leaf(GOLD)
    if i == 15:
        return oak_leaf(SILVER)
    if i == 16:
        return eagle(SILVER)
    return stars(i - 16)


def insignia(i, size=256):
    big = rank_art(i)
    return fit_center(big, size * 4, int(size * 4 * 0.05)).resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------- category pictures (loot style)
CREAM_TOP = np.array([246, 240, 224], float)
CREAM_BOT = np.array([228, 219, 198], float)
INK = np.array([16, 14, 12], float)


def loot_style(mask, grow=1.4, key=4.5, halo=7.0, seed=1):
    """the use-to-loot icon finish (build_icons.py finish(), copied so this file has no untracked dependency): flat
    cream fill, crisp dark keyline, soft dark halo; mask = bool array at SS x, returns RGBA at 1x"""
    H, W = mask.shape
    d_out = ndimage.distance_transform_edt(~mask)
    fill = d_out <= grow * SS
    d2 = ndimage.distance_transform_edt(~fill)
    keyl = d2 <= key * SS
    halo_a = ndimage.gaussian_filter(keyl.astype(np.float32), halo * SS * 0.5)
    halo_a = ndimage.shift(halo_a, (1.5 * SS, 0), order=1)   # shift, not roll: a roll wraps the bottom edge's halo to the top

    def dn(a):
        return a.astype(np.float32).reshape(H // SS, SS, W // SS, SS).mean((1, 3))
    f, k, h = dn(fill), dn(keyl), dn(halo_a)
    h1, w1 = f.shape
    rng = np.random.default_rng(seed)
    slow = ndimage.gaussian_filter(rng.standard_normal((h1, w1)), 14)
    slow = slow / (np.abs(slow).max() + 1e-6)
    grain = ndimage.gaussian_filter(rng.standard_normal((h1, w1)), 0.8)
    grain = grain / (np.abs(grain).max() + 1e-6)
    ys = np.where(f.any(1))[0]
    y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, h1 - 1)
    t = np.clip((np.arange(h1) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    col = CREAM_TOP * (1 - t) + CREAM_BOT * t
    col = col * (1.0 + 0.035 * slow[..., None] + 0.015 * grain[..., None])
    rgb = INK * (1 - f[..., None]) + col * f[..., None]
    a = np.maximum(f, np.maximum(k * 0.92, h * 0.55))
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.clip(a, 0, 1) * 255]).astype(np.uint8), "RGBA")


def sil(draw_fn, W=512, H=256):
    """draw_fn(ImageDraw, k) on a W*SS x H*SS L canvas -> loot-style cream icon"""
    im = Image.new("L", (W * SS, H * SS), 0)
    draw_fn(ImageDraw.Draw(im), SS)
    return loot_style(np.array(im) > 127, grow=1.4, key=4.5, halo=7.0, seed=zlib.crc32(draw_fn.__name__.encode()) % 9999)


def _bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        e = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return out


def ic_helmet(d, k):
    # M1 helmet, side view: the dome, the flared rim (lower at the back), the chin strap loop hanging under it
    dome = _bez((120, 178), (128, 66), (300, 34), (392, 120), 40) + _bez((392, 120), (408, 150), (414, 168), (420, 182), 10)
    rim = [(420, 182), (436, 196), (430, 204), (300, 198), (180, 196), (98, 206), (92, 198), (120, 178)]
    d.polygon([(x * k, y * k) for x, y in dome + rim], fill=255)
    # strap: a hanging loop drawn as a thick open curve
    loop = _bez((210, 198), (220, 250), (300, 250), (318, 199), 30)
    d.line([(x * k, y * k) for x, y in loop], fill=255, width=9 * k)
    # rivet / bale
    d.ellipse([(196 - 9) * k, (183 - 9) * k, (196 + 9) * k, (183 + 9) * k], fill=0)


def ic_uniform(d, k):
    # field jacket front: body, sleeves, collar notch, two breast pockets cut out as lines, button line
    body = [(176, 52), (226, 40), (256, 64), (286, 40), (336, 52), (392, 78), (432, 196), (402, 206), (372, 120),
            (366, 228), (146, 228), (140, 120), (110, 206), (80, 196), (120, 78)]
    d.polygon([(x * k, y * k) for x, y in body], fill=255)
    d.polygon([(x * k, y * k) for x, y in [(226, 40), (256, 64), (286, 40), (270, 96), (256, 82), (242, 96)]], fill=0)
    for x0 in (170, 278):
        d.rectangle([x0 * k, 104 * k, (x0 + 64) * k, 110 * k], fill=0)
        d.line([(x0 * k, 104 * k), (x0 * k, 156 * k), ((x0 + 64) * k, 156 * k), ((x0 + 64) * k, 104 * k)], fill=0, width=5 * k)
    d.line([(256 * k, 96 * k), (256 * k, 228 * k)], fill=0, width=5 * k)
    for y in (120, 158, 196):
        d.ellipse([(250 - 6 + 18) * k, (y - 6) * k, (250 + 6 + 18) * k, (y + 6) * k], fill=0)


def ic_gloves(d, k):
    # one leather glove, palm out, fingers up, a cuff
    palm = [(196, 230), (190, 150), (176, 112), (186, 104), (214, 140), (214, 64), (238, 64), (242, 124),
            (250, 46), (274, 46), (276, 124), (284, 54), (308, 56), (306, 130), (316, 78), (338, 82), (330, 168),
            (318, 230)]
    d.polygon([(x * k, y * k) for x, y in palm], fill=255)
    for x in (226, 262, 296):
        d.line([(x * k, 132 * k), (x * k, 150 * k)], fill=0, width=4 * k)
    d.rectangle([188 * k, 196 * k, 324 * k, 204 * k], fill=0)


def ic_perk(d, k):
    # two dog tags on a bead chain
    def tag(cx, cy, ang):
        w, h, r = 150, 90, 26
        c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pts = []
        for (x, y) in [(-w / 2 + r, -h / 2), (w / 2 - r, -h / 2), (w / 2, -h / 2 + r), (w / 2, h / 2 - r), (w / 2 - r, h / 2),
                       (-w / 2 + r, h / 2), (-w / 2, h / 2 - r), (-w / 2, -h / 2 + r)]:
            pts.append((cx + x * c - y * s, cy + x * s + y * c))
        d.polygon([(x * k, y * k) for x, y in pts], fill=255)
        hx, hy = cx + (-w / 2 + 18) * c, cy + (-w / 2 + 18) * s
        d.ellipse([(hx - 8) * k, (hy - 8) * k, (hx + 8) * k, (hy + 8) * k], fill=0)
        for j in range(3):
            yy = -22 + j * 20
            x0, x1 = -38, 50
            d.line([((cx + x0 * c - yy * s) * k, (cy + x0 * s + yy * c) * k), ((cx + x1 * c - yy * s) * k, (cy + x1 * s + yy * c) * k)], fill=0, width=5 * k)
    for i in range(26):
        t = i / 25
        x = 120 + 270 * t
        y = 40 + 40 * math.sin(math.pi * t) * -1 + 50 * t
        d.ellipse([(x - 5) * k, (y - 5) * k, (x + 5) * k, (y + 5) * k], fill=255)
    tag(218, 146, -18)
    tag(300, 168, 10)


def ic_attach(d, k):
    # rifle scope: tube, objective bell, eyepiece, turret, rings
    d.rectangle([150 * k, 110 * k, 380 * k, 146 * k], fill=255)
    d.polygon([(x * k, y * k) for x, y in [(380, 110), (420, 92), (450, 92), (450, 164), (420, 164), (380, 146)]], fill=255)
    d.polygon([(x * k, y * k) for x, y in [(150, 110), (120, 98), (64, 98), (64, 158), (120, 158), (150, 146)]], fill=255)
    d.rectangle([246 * k, 84 * k, 282 * k, 110 * k], fill=255)
    d.rectangle([238 * k, 74 * k, 290 * k, 86 * k], fill=255)
    for x in (190, 330):
        d.rectangle([(x - 12) * k, 146 * k, (x + 12) * k, 178 * k], fill=255)
    d.line([(160 * k, 128 * k), (370 * k, 128 * k)], fill=0, width=3 * k)


def ic_challenge(d, k):
    # a commendation: a sheet with a folded corner, ruled lines and a seal with two ribbon tails
    d.polygon([(x * k, y * k) for x, y in [(150, 30), (330, 30), (370, 70), (370, 228), (150, 228)]], fill=255)
    d.polygon([(x * k, y * k) for x, y in [(330, 30), (330, 70), (370, 70)]], fill=0)
    d.line([(330 * k, 30 * k), (330 * k, 70 * k), (370 * k, 70 * k)], fill=255, width=4 * k)
    for y in (78, 104, 130):
        d.rectangle([182 * k, y * k, 320 * k, (y + 7) * k], fill=0)
    d.ellipse([300 * k, 150 * k, 380 * k, 230 * k], fill=0)
    d.ellipse([306 * k, 156 * k, 374 * k, 224 * k], fill=255)
    d.polygon([(x * k, y * k) for x, y in [(318, 214), (306, 252), (326, 240), (340, 254), (340, 220)]], fill=255)
    d.polygon([(x * k, y * k) for x, y in [(362, 214), (374, 252), (354, 240), (340, 254), (340, 220)]], fill=255)
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = 22 if i % 2 == 0 else 9
        pts.append(((340 + rr * math.cos(a)) * k, (190 + rr * math.sin(a)) * k))
    d.polygon(pts, fill=0)


def ic_emote(d, k):
    # a hand at the salute: flat hand, fingers together, thumb tucked, angled to the brow
    c, s = math.cos(math.radians(-28)), math.sin(math.radians(-28))

    def R(x, y):
        return ((256 + x * c - y * s) * k, (140 + x * s + y * c) * k)
    hand = [(-150, -28), (40, -36), (126, -30), (150, -16), (150, 10), (120, 24), (40, 30), (-30, 34), (-90, 60),
            (-150, 64)]
    d.polygon([R(x, y) for x, y in hand], fill=255)
    for y in (-14, 2, 16):
        d.line([R(40, y), R(140, y)], fill=0, width=4 * k)
    d.line([R(-60, 34), R(30, 30)], fill=0, width=5 * k)


def ic_prestige(d, k):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = 112 if i % 2 == 0 else 44
        pts.append(((256 + rr * math.cos(a)) * k, (136 + rr * math.sin(a)) * k))
    d.polygon(pts, fill=255)


CATS = {"cat_helmet": ic_helmet, "cat_uniform": ic_uniform, "cat_gloves": ic_gloves, "cat_perk": ic_perk,
        "cat_attach": ic_attach, "cat_challenge": ic_challenge, "cat_emote": ic_emote, "cat_prestige": ic_prestige}

# ---------------------------------------------------------------------------------------------- finishes (gun outline, filled with the finish)
FIN = [("finish_gold", "fin_gold"), ("finish_chrome", "fin_chrome"), ("finish_blued", "fin_blued"),
       ("finish_bloody", "fin_bloody"), ("finish_camo_woodland", "fin_woodland"), ("finish_camo_winter", "fin_winter"),
       ("finish_camo_desert", "fin_desert")]


def camo(H, W, cols, seed, scale):
    rng = np.random.default_rng(seed)
    out = np.zeros((H, W, 3))
    out[:] = cols[0]
    for j, c in enumerate(cols[1:]):
        n = ndimage.gaussian_filter(rng.standard_normal((H, W)), scale)
        n = n / (np.abs(n).max() + 1e-6)
        sel = n > 0.18 + 0.05 * j
        out[sel] = c
    return out


def finish_pic(kind, assets):
    g = Image.open(os.path.join(assets, "textures", "hud", "loot", "coop_loot_gun.tga")).convert("RGBA")
    a = np.array(g).astype(float)
    alpha = a[..., 3] / 255
    lum = a[..., :3].mean(2) / 255
    body = np.clip((lum - 0.35) / 0.4, 0, 1) * alpha     # the cream fill, not the keyline / halo
    H, W = alpha.shape
    yy = np.linspace(0, 1, H)[:, None, None]
    if kind == "fin_gold":
        rgb = np.array(GOLD[0]) * (1 - yy) + np.array(GOLD[2]) * yy
    elif kind == "fin_chrome":
        band = 0.5 + 0.5 * np.cos(yy * 9.0)
        rgb = np.array((120, 126, 134.0)) + band * 125
    elif kind == "fin_blued":
        rgb = np.array((70, 84, 112.0)) * (1 - yy) + np.array((22, 28, 44.0)) * yy
    elif kind == "fin_bloody":
        rgb = np.broadcast_to(np.array((96, 96, 100.0)) * (1 - yy) + np.array((50, 50, 54.0)) * yy, (H, W, 3)).copy()
        rng = np.random.default_rng(11)
        n = ndimage.gaussian_filter(rng.standard_normal((H, W)), 3)
        rgb[n > 0.09] = (118, 14, 12)
    elif kind == "fin_woodland":
        rgb = camo(H, W, [(86, 92, 58), (52, 64, 40), (110, 88, 58), (30, 30, 24)], 3, 6)
    elif kind == "fin_winter":
        rgb = camo(H, W, [(222, 224, 226), (176, 182, 188), (120, 126, 132)], 4, 7)
    else:
        rgb = camo(H, W, [(196, 170, 120), (160, 128, 86), (120, 96, 66)], 5, 7)
    rgb = np.broadcast_to(rgb, (H, W, 3)).astype(float)
    # keep a hint of the icon's own shading
    rgb = rgb * (0.85 + 0.15 * lum[..., None])
    out = a[..., :3] * (1 - body[..., None]) + rgb * body[..., None]
    return Image.fromarray(np.dstack([np.clip(out, 0, 255), a[..., 3]]).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------------------------------------- UI pieces
def paper(S=512):
    rng = np.random.default_rng(42)

    def tile_noise(scale):
        n = rng.standard_normal((S, S))
        return ndimage.gaussian_filter(n, scale, mode="wrap")
    slow = tile_noise(40)
    slow /= np.abs(slow).max()
    mid = tile_noise(6)
    mid /= np.abs(mid).max()
    fine = tile_noise(0.7)
    fine /= np.abs(fine).max()
    fib = ndimage.gaussian_filter(rng.standard_normal((S, S)), (0.6, 9), mode="wrap")
    fib /= np.abs(fib).max()
    base = np.array((226, 210, 172.0))
    v = 1 + 0.05 * slow + 0.025 * mid + 0.02 * fine + 0.02 * fib
    rgb = base[None, None, :] * v[..., None]
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), np.full((S, S), 255)]).astype(np.uint8), "RGBA")


def grad_bar(top, bot, hl=None, W=256, H=32):
    yy = np.linspace(0, 1, H)[:, None, None]
    rgb = np.array(top, float) * (1 - yy) + np.array(bot, float) * yy
    rgb = np.broadcast_to(rgb, (H, W, 3)).copy()
    if hl is not None:
        y = int(H * hl)
        rgb[y:y + 2] = np.clip(rgb[y:y + 2] * 1.25 + 20, 0, 255)
    return Image.fromarray(np.dstack([rgb, np.full((H, W), 255.0)]).astype(np.uint8), "RGBA")


def glow(S=256):
    yy, xx = np.mgrid[0:S, 0:S]
    r = np.hypot(xx - S / 2 + 0.5, yy - S / 2 + 0.5) / (S / 2)
    a = np.clip(1 - r, 0, 1) ** 2.2
    return Image.fromarray(np.dstack([np.full((S, S, 3), 255.0), a * 255]).astype(np.uint8), "RGBA")


def vignette(S=256):
    yy, xx = np.mgrid[0:S, 0:S]
    r = np.hypot((xx - S / 2 + 0.5) / (S / 2), (yy - S / 2 + 0.5) / (S / 2)) / math.sqrt(2)
    a = 0.55 + 0.45 * np.clip((r - 0.25) / 0.75, 0, 1) ** 1.4
    return Image.fromarray(np.dstack([np.full((S, S, 3), 6.0), a * 255]).astype(np.uint8), "RGBA")


def soft_shadow(S=128):
    yy, xx = np.mgrid[0:S, 0:S]
    m = np.minimum(np.minimum(xx, S - 1 - xx), np.minimum(yy, S - 1 - yy)) / (S * 0.5)
    a = np.clip(m / 0.35, 0, 1) ** 1.5
    return Image.fromarray(np.dstack([np.zeros((S, S, 3)), a * 255 * 0.85]).astype(np.uint8), "RGBA")


def stamp(text, W=640, H=220, ang=-7, seed=1):
    S = 4
    im = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONTS + "STENCIL.TTF", int(H * S * 0.50))
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    bw = tw + int(H * S * 0.32)
    bh = int(H * S * 0.78)
    x0, y0 = (W * S - bw) // 2, (H * S - bh) // 2
    lw = int(H * S * 0.045)
    d.rectangle([x0, y0, x0 + bw, y0 + bh], outline=255, width=lw)
    d.rectangle([x0 + lw * 2, y0 + lw * 2, x0 + bw - lw * 2, y0 + bh - lw * 2], outline=255, width=max(2, lw // 3))
    d.text(((W * S - tw) // 2 - bb[0], (H * S - th) // 2 - bb[1]), text, font=f, fill=255)
    im = im.rotate(ang, resample=Image.BICUBIC, expand=False)
    m = np.array(im).astype(np.float32) / 255
    rng = np.random.default_rng(seed)
    # rubber-stamp ink: uneven coverage and a few dry specks, never so worn the word is hard to read
    n = ndimage.gaussian_filter(rng.standard_normal(m.shape), 6 * S)
    n /= np.abs(n).max()
    speck = ndimage.gaussian_filter(rng.standard_normal(m.shape), 1.2 * S)
    speck /= np.abs(speck).max()
    cov = np.clip(0.88 + 0.16 * n - 0.5 * (speck > 0.55), 0, 1)
    a = m * cov
    a = a.reshape(H, S, W, S).mean((1, 3))
    rgb = np.broadcast_to(np.array((168, 26, 22.0)), (H, W, 3))
    return Image.fromarray(np.dstack([rgb, a * 255 * 0.92]).astype(np.uint8), "RGBA")


def tick(S=64):
    """the card's 'NEW' corner pip / bullet: a small brass lozenge"""
    m = mask_poly(S * 4, S * 4, [[(S * 2, S * 0.4), (S * 3.6, S * 2), (S * 2, S * 3.6), (S * 0.4, S * 2)]])
    return to_img(metal(m, BRASS)).resize((S, S), Image.LANCZOS)


# ---------------------------------------------------------------------------------------------- tables
def roster(mod):
    src = open(os.path.join(mod, "coop_mod", "loadoutroster.scr"), encoding="latin-1").read()
    out = {}
    for blk in re.split(r'case "', src)[1:]:
        g = re.search(r'local\.r\["give"\] = "([^"]+)"', blk)
        c = re.search(r'local\.r\["class"\] = "([^"]+)"', blk)
        if g:
            out[g.group(1)] = c.group(1) if c else "rifle"
    return out


def weapon_tokens(mod):
    toks = set(roster(mod))
    for f in ("challenges.scr", "xp.scr"):
        toks |= set(re.findall(r'models/weapons/[A-Za-z0-9_\-]+\.tik', open(os.path.join(mod, "coop_mod", f), encoding="latin-1").read()))
    return sorted(toks)


def loot_table(eng):
    h = open(os.path.join(eng, "code", "cgame", "cg_coopfeed_loot.h"), encoding="latin-1").read()
    return {m.group(1): m.group(2) for m in re.finditer(r'\{"([^"]+)", "([^"]+)"', h)}


# tik stem -> use-to-loot silhouette. Snapshot of docs/proposals/use_pickup_2026-10-05/tools/weapons.json (item -> tik)
# joined with cg_coopfeed_loot.h (item -> texture) on 2026-11-03: that tool tree is not in git, so the join is kept here.
STEM2TEX = {'arisaka': 'w_arisakatype99', 'arisakasniper': 'w_arisakasniper', 'bar': 'w_bar', 'bar_bar1918': 'w_lewisgun',
    'bazooka': 'w_bazooka', 'berettasilenced': 'w_silencedberetta', 'carbine': 'w_m1carbine', 'carcanosniper': 'w_carcanosniper',
    'colt45': 'w_colt45', 'colt45_colt1911w': 'w_webleymkvi', 'colt_silenced': 'w_silencedcolt45', 'coop_g43_irons': 'w_g43irons',
    'delisle': 'w_delisle', 'dp28': 'w_dp28', 'enfield': 'w_leeenfield', 'enfieldsniper': 'w_leeenfieldsniper', 'fg42': 'w_fg42',
    'g43': 'w_g43', 'g43sniper': 'w_g43sniper', 'garand_scoped': 'w_m1garandsniper', 'garand_silenced': 'w_silencedm1garand',
    'greasegun': 'w_m3greasegun', 'greasegun_silenced': 'w_silencedgreasegun', 'it_w_beretta': 'w_beretta', 'it_w_breda': 'w_breda',
    'it_w_carcano': 'w_carcano', 'it_w_moschetto': 'w_moschetto', 'johnson_m1941': 'w_johnsonm1941', 'kar98': 'w_mauserkar98k',
    'kar98_mortar': 'w_gewehrgranate', 'kar98sniper': 'w_kar98sniper', 'kar98snipersilenced': 'w_silencedkar98sniper',
    'lugerp08': 'w_lugerp08', 'lugerp08silenced': 'w_silencedlugerp08', 'm10_revolver': 'w_swm1038', 'm1_garand': 'w_m1garand',
    'mauser_c96': 'w_mauserc96', 'moschetto': 'w_berettam38', 'mosin_nagant_rifle': 'w_mosinnagantrifle', 'mp40': 'w_mp40',
    'mp40silenced': 'w_silencedmp40', 'mp44': 'w_stg44', 'mp44scoped': 'w_stg44scoped', 'nagant_revolver': 'w_nagantrevolver',
    'nagant_sniper': 'w_mosinnagantsniper', 'nagant_snipersilenced': 'w_silencedmosinsniper', 'nambu': 'w_nambutype14',
    'p38': 'w_waltherp38', 'p38silenced': 'w_silencedwaltherp38', 'panzerschreck': 'w_panzerschreck', 'ppk': 'w_waltherppk',
    'ppsh43silenced': 'w_silencedpps43', 'ppsh_smg': 'w_ppshsmg', 'shotgun': 'w_shotgun', 'silencedpistol': 'w_histandardsilenced',
    'springfield': 'w_springfield03sniper', 'springfield_unscoped': 'w_springfieldm1903', 'sten': 'w_stenmarkii',
    'svt_rifle': 'w_svt40', 'thompson50': 'w_thompson50rd', 'thompsonsmg': 'w_thompson', 'tt33': 'w_tt33tokarev',
    'tt33silenced': 'w_silencedtt33', 'type100smg': 'w_type100smg', 'uk_w_l42a1': 'w_enfieldl42a1', 'uk_w_piat': 'w_piat',
    'uk_w_vickers': 'w_vickersberthier', 'webley_revolver': 'w_webleyrevolver', 'welrod': 'w_welrod',
    'coop_dbshotgun': 'w_dbshotgun'}


def weapon_pics(mod, eng):
    loot = set(loot_table(eng).values())
    stem2tex = {k: v for k, v in STEM2TEX.items() if v in loot}
    ros = roster(mod)
    out, fallback = {}, []
    for tok in weapon_tokens(mod):
        stem = os.path.basename(tok)[:-4].lower()
        tex = None
        cands = [stem, stem.replace("coop_", ""), stem.replace("_start", ""), stem.replace("_sp_start", "")]
        s2 = stem.replace("coop_", "")
        if "_" in s2:
            cands += [s2.rsplit("_", 1)[0], s2.split("_", 1)[0]]
        for c in cands:
            if c in stem2tex:
                tex = "textures/hud/loot/" + stem2tex[c]
                break
        if tex is None:
            if "grenade" in stem or "granate" in stem or "bomba" in stem:
                tex = "textures/hud/weap_grenade"
            else:
                cls = ros.get(tok, "")
                if cls == "pistol" or any(p in stem for p in ("colt45", "p38", "luger", "pistol", "revolver", "webley", "tt33", "nambu", "beretta", "ppk")):
                    tex = "textures/hud/loot/coop_loot_pistol"
                elif cls in ("smg", "heavy") or any(p in stem for p in ("mp40", "thompson", "sten", "bar", "mg", "ppsh", "greasegun", "type100")):
                    tex = "textures/hud/loot/coop_loot_mg"
                else:
                    tex = "textures/hud/loot/coop_loot_gun"
                fallback.append((tok, tex))
        out[tok] = tex
    return out, fallback


def medal_names(mod):
    src = open(os.path.join(mod, "coop_mod", "medals.scr"), encoding="latin-1").read()
    return re.findall(r'waitthread medal_def "[^"]+"\s+"[^"]+"\s+"([^"]+)"', src)


GEN_HEAD = "//=========================================================================\n// GENERATED by docs/tools/gen_debrief2.py - do not edit by hand.\n"


_sr = None


def medal_pic(mod, i):
    """the Service Record's own medal design (gen_service_record.py draw_medal_icon + RIBBON_COLORS, lifted out of that
    file with ast so the two cannot drift), drawn at 384 px and cropped to the medal. The shipped coop_sr/medalN.tga is a
    466x208 canvas with a ~110 px medal in it: fitted into a card's picture box it came out small and soft."""
    global _sr
    if _sr is None:
        import ast
        src = open(os.path.join(ROOT, "docs", "tools", "gen_service_record.py"), encoding="utf-8").read()
        tree = ast.parse(src)
        keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in ("lerp", "draw_medal_icon")) or
                (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "RIBBON_COLORS" for t in n.targets))]
        code = "\n".join(ast.get_source_segment(src, n) for n in keep)
        # its design is a 200-unit canvas drawn at 3x and reduced to 200 px: draw it at 12x and reduce to 600 px instead
        hi = code.replace("S=3; W=size*S", "S=12; W=size*S").replace("return im.resize((size,size),Image.LANCZOS)",
                                                                   "return im.resize((size*3,size*3),Image.LANCZOS)")
        assert hi.count("S=12") == 1 and hi.count("size*3,size*3") == 1, "gen_service_record.draw_medal_icon changed shape"
        _sr = {"Image": Image, "ImageDraw": ImageDraw, "math": math}
        exec(compile(hi, "gen_service_record.py (draw_medal_icon at 600 px)", "exec"), _sr)
    msrc = open(os.path.join(mod, "coop_mod", "medals.scr"), encoding="latin-1").read()
    cats = re.findall(r'waitthread medal_def "[^"]+"\s+"([^"]+)"', msrc)
    im = _sr["draw_medal_icon"](cats[i], size=200)
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    im = im.crop(bb)
    pad = max(4, im.height // 12)
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    out.paste(im, (pad, pad))
    return out


def gen_scr(mod, eng):
    pics, fb = weapon_pics(mod, eng)
    L = [GEN_HEAD + "// Reward token -> picture for the end-of-mission unlock cards (coop_mod/debrief2.scr::db2_card).\n"
         "// Weapons: their own use-to-loot silhouette (textures/hud/loot), else the class silhouette. Medals: the Service\n"
         "// Record medal art, in medals.scr medal_def order. Every other kind uses a category picture (textures/hud/coop_db2).\n"
         "//=========================================================================", "main:{",
         "\tif( level.coop_db2GenInit == 1 ){ end }", "\tlevel.coop_db2GenInit = 1"]
    for tok in sorted(pics):
        L.append('\tlevel.coop_db2Pic["%s"] = "%s"' % (tok, pics[tok]))
    for i, n in enumerate(medal_names(mod)):
        L.append('\tlevel.coop_db2Medal["%s"] = "%s/medal_%02d"' % (n, TEX, i))
    for tok, name in FIN:
        L.append('\tlevel.coop_db2Pic["%s"] = "%s/%s"' % (tok, TEX, name))
    L.append("}end")
    return ("\n".join(L) + "\n").replace("\n", "\r\n").encode("latin-1"), fb


def shader_text(names):
    out = ["// GENERATED by docs/tools/gen_debrief2.py - do not edit by hand.",
           "// End-of-mission debrief art (cgame/cg_coopdebrief.c). nomipmaps + nopicmip: drawn near native size, so a mip",
           "// chain only blurs it and r_picmip must never halve it (the old 128 px rank emblems were both too small and stretched).",
           "// rgbGen / alphaGen global: the draw colour (R_SetColor) tints and fades every layer.", ""]
    for n in names:
        tile = n == "db2_paper"
        add = n in ("db2_glow",)
        out += ["%s/%s" % (TEX, n), "{", "\tnomipmaps", "\tnopicmip", "\t{",
                "\t\t%s %s/%s.tga" % ("map" if tile else "clampmap", TEX, n),
                "\t\tblendFunc %s" % ("GL_SRC_ALPHA GL_ONE" if add else "GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA"),
                "\t\trgbGen global", "\t\talphaGen global", "\t}", "}", ""]
    return ("\r\n".join(out)).encode("latin-1")


def build(mod, eng, assets):
    """returns {relpath under the fixes root or mod tree: bytes} and the mod file set"""
    tex = {}

    def put(name, img):
        b = io.BytesIO()
        img.save(b, "TGA", compression="tga_rle")
        tex["%s/%s.tga" % (TEX, name)] = b.getvalue()
    for i in range(22):
        put("rank_%02d" % i, insignia(i))
    for n, fn in CATS.items():
        put(n, sil(fn))
    for tok, n in FIN:
        put(n, finish_pic(n, assets))
    for i in range(len(medal_names(mod))):
        put("medal_%02d" % i, medal_pic(mod, i))
    put("db2_paper", paper())
    put("db2_fill", grad_bar((246, 214, 132), (150, 104, 34), hl=0.18))
    put("db2_track", grad_bar((16, 14, 10), (52, 46, 34)))
    put("db2_glow", glow())
    put("db2_vignette", vignette())
    put("db2_shadow", soft_shadow())
    put("db2_stamp_promoted", stamp("PROMOTED"))
    put("db2_pip", tick())
    names = sorted(os.path.splitext(os.path.basename(k))[0] for k in tex)
    scr, fb = gen_scr(mod, eng)
    modf = {"scripts/coop_debrief2.shader": shader_text(names), "coop_mod/debrief2_gen.scr": scr}
    return tex, modf, fb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", default=r"C:\mohaa-coop-dev\hzm-mod-debrief2")
    ap.add_argument("--eng", default=r"H:\hzm_work\debrief2_eng")
    ap.add_argument("--fixes", default=os.path.join(ROOT, "docs", "tools", "assets", "fixes"))
    ap.add_argument("--assets", default=r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod", help="a mod tree WITH textures (worktrees carry none)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preview")
    a = ap.parse_args()
    tex, modf, fb = build(a.mod, a.eng, a.assets)
    stale = []
    for rel, b in list(tex.items()):
        p = os.path.join(a.fixes, *rel.split("/"))
        old = open(p, "rb").read() if os.path.isfile(p) else None
        if old != b:
            stale.append(p)
            if not a.check:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(b)
    for rel, b in modf.items():
        p = os.path.join(a.mod, *rel.split("/"))
        old = open(p, "rb").read() if os.path.isfile(p) else None
        if old != b:
            stale.append(p)
            if not a.check:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "wb").write(b)
    man_p = os.path.join(a.fixes, "fixes_manifest.json")
    man = json.load(open(man_p, encoding="utf-8"))
    missing = [rel for rel in tex if rel not in man]
    if missing:
        stale.append(man_p)
        if not a.check:
            for rel in missing:
                man[rel] = {"new": True, "why": "end-of-mission debrief art (docs/tools/gen_debrief2.py)"}
            raw = open(man_p, "rb").read()
            nl = "\r\n" if b"\r\n" in raw else "\n"
            end = "\n" if raw.endswith(b"\n") else ""
            # the manifest's own layout (insertion order, 2-space indent), so the diff is only the new entries
            open(man_p, "wb").write((json.dumps(man, indent=2) + end).replace("\n", nl).encode("utf-8"))
    for tok, t in fb:
        print("weapon picture by class:", tok, "->", t)
    if a.preview:
        ims = [Image.open(io.BytesIO(b)).convert("RGBA") for _, b in sorted(tex.items())]
        cw, ch = 280, 170
        cols = 7
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * ch * 2), (0, 0, 0))
        for r, bg in enumerate([(226, 210, 172), (38, 40, 34)]):
            for i, im in enumerate(ims):
                cell = Image.new("RGB", (cw, ch), bg)
                t = im.copy()
                t.thumbnail((cw - 10, ch - 10), Image.LANCZOS)
                cell.paste(t, ((cw - t.width) // 2, (ch - t.height) // 2), t)
                sheet.paste(cell, ((i % cols) * cw, (r * rows + i // cols) * ch))
        sheet.save(a.preview)
    print("%s: %d textures, %d mod files, %d stale" % ("check" if a.check else "write", len(tex), len(modf), len(stale)))
    for s in stale:
        print("  ", s)
    return 1 if (a.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())

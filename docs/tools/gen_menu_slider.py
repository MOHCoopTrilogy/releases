#!/usr/bin/env python3
"""Crisp, high-res menu SLIDER chrome overrides (track + thumb + left/right arrows).

[user 2026-09-21] "the entire slider still looks ugly and low res." The stock mohmenu slider art is tiny -
slider_thumb.tga is 8x16, arrow_left/right 16x16, SLIDER track 192x16 - so on a 3440x1440 screen every part
is magnified 5-6x and reads as mush. UPSCALING those fuzzy sources (the first attempt) only made them soft.
This REDRAWS each part vector-clean at high res, supersampled 4x -> LANCZOS down for smooth anti-aliased
edges. Files (all referenced by the retail scripts/mohmenu.shader entries, which already force32bit, so a
same-path .tga override in the coop pak wins; no stock .dds exists to shadow them - verified 2026-09-21):

  textures/mohmenu/slider.tga            768x64   the rail/track (clampMap, alpha-faded ends)
  textures/mohmenu/slider_thumb.tga      48x96    the draggable handle (grip notches + highlight)
  textures/mohmenu/slider_thumb_sel.tga  48x96    handle, pressed/hover (warm accent)
  textures/mohmenu/arrow_left.tga        64x64    prev arrow
  textures/mohmenu/arrow_left_sel.tga    64x64    prev arrow, pressed
  textures/mohmenu/arrow_right.tga       64x64    next arrow
  textures/mohmenu/arrow_right_sel.tga   64x64    next arrow, pressed

Aspect ratios match the stock files (12:1 track, 1:2 thumb, 1:1 arrows) so the engine's stretch does not
distort them. Palette = neutral steel with the mod's muted-gold accent (matches the HUD's 0.80 0.72 0.35).

Run:  python docs/tools/gen_menu_slider.py [--preview]
"""

import os
import sys
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "hzm-mohaa-coop-mod", "textures", "mohmenu")
SS = 4  # supersample factor for anti-aliasing

STEEL_HI = (214, 220, 230, 255)
STEEL    = (162, 170, 182, 255)
STEEL_LO = (120, 128, 142, 255)
INK      = (18, 20, 26, 255)
GOLD     = (212, 190, 120, 255)
GOLD_HI  = (240, 224, 160, 255)


def _mk(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def _down(img, w, h):
    return img.resize((w, h), Image.LANCZOS)


def _vgrad(draw, x0, y0, x1, y1, c_top, c_bot):
    """Fill a vertical gradient rectangle (supersampled coords)."""
    span = max(1, y1 - y0)
    for i in range(span):
        t = i / float(span)
        c = tuple(int(c_top[k] + (c_bot[k] - c_top[k]) * t) for k in range(4))
        draw.line([(x0, y0 + i), (x1, y0 + i)], fill=c)


def track():
    W, H = 768, 64
    im = _mk(W, H)
    d = ImageDraw.Draw(im)
    w, h = W * SS, H * SS
    r = 14 * SS
    # inset channel, centred, ~22px tall of a 64px texture
    top = int(h * 0.31)
    bot = int(h * 0.69)
    # outer dark rail
    d.rounded_rectangle([r, top, w - r, bot], radius=(bot - top) // 2, fill=(26, 29, 36, 235))
    # inner recessed groove (slightly darker, inset) with a soft vertical gradient for depth
    gi_top, gi_bot = top + 3 * SS, bot - 3 * SS
    grad = _mk(W, H)
    gd = ImageDraw.Draw(grad)
    _vgrad(gd, 0, gi_top, w, gi_bot, (14, 16, 21, 255), (40, 44, 54, 255))
    gmask = _mk(W, H)
    ImageDraw.Draw(gmask).rounded_rectangle(
        [r + 3 * SS, gi_top, w - r - 3 * SS, gi_bot], radius=(gi_bot - gi_top) // 2, fill=255
    )
    im.paste(grad, (0, 0), gmask.getchannel("A"))
    d = ImageDraw.Draw(im)
    # top highlight line along the rail lip
    d.line([(r + 6 * SS, top + 2 * SS), (w - r - 6 * SS, top + 2 * SS)], fill=(190, 196, 208, 90), width=SS)
    return _down(im, W, H)


def _thumb(sel):
    W, H = 48, 96
    im = _mk(W, H)
    d = ImageDraw.Draw(im)
    w, h = W * SS, H * SS
    pad = 4 * SS
    r = 12 * SS
    body_hi = GOLD_HI if sel else STEEL_HI
    body_lo = GOLD if sel else STEEL_LO
    edge = (250, 236, 176, 255) if sel else (30, 34, 42, 255)
    # soft drop shadow
    sh = _mk(W, H)
    ImageDraw.Draw(sh).rounded_rectangle([pad + 2 * SS, pad + 3 * SS, w - pad + 2 * SS, h - pad + 3 * SS],
                                         radius=r, fill=(0, 0, 0, 130))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(3 * SS))
    im.alpha_composite(sh)
    # body: vertical steel gradient inside a rounded rect
    grad = _mk(W, H)
    _vgrad(ImageDraw.Draw(grad), 0, pad, w, h - pad, body_hi, body_lo)
    mask = _mk(W, H)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, w - pad, h - pad], radius=r, fill=255)
    im.paste(grad, (0, 0), mask.getchannel("A"))
    d = ImageDraw.Draw(im)
    # crisp border
    d.rounded_rectangle([pad, pad, w - pad, h - pad], radius=r, outline=edge, width=2 * SS)
    # left specular highlight
    d.rounded_rectangle([pad + 3 * SS, pad + 4 * SS, pad + 9 * SS, h - pad - 4 * SS],
                        radius=4 * SS, fill=(255, 255, 255, 70))
    # three grip notches across the middle
    cx0, cx1 = pad + 12 * SS, w - pad - 12 * SS
    cyc = h // 2
    for off in (-10 * SS, 0, 10 * SS):
        d.line([(cx0, cyc + off), (cx1, cyc + off)], fill=(20, 22, 28, 150), width=2 * SS)
        d.line([(cx0, cyc + off + 2 * SS), (cx1, cyc + off + 2 * SS)], fill=(255, 255, 255, 55), width=SS)
    return _down(im, W, H)


def _arrow(direction, sel):
    """direction: -1 = points left, +1 = points right."""
    W, H = 64, 64
    im = _mk(W, H)
    d = ImageDraw.Draw(im)
    w, h = W * SS, H * SS
    fill = GOLD_HI if sel else STEEL_HI
    edge = (250, 236, 176, 255) if sel else (26, 30, 38, 255)
    m = 16 * SS  # margin
    cy = h // 2
    if direction < 0:
        pts = [(m, cy), (w - m, m), (w - m, h - m)]
    else:
        pts = [(w - m, cy), (m, m), (m, h - m)]
    # shadow
    from PIL import ImageFilter
    sh = _mk(W, H)
    ImageDraw.Draw(sh).polygon([(x + 2 * SS, y + 3 * SS) for x, y in pts], fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(2 * SS))
    im.alpha_composite(sh)
    d = ImageDraw.Draw(im)
    d.polygon(pts, fill=fill, outline=edge)
    # thicken the outline a touch for crispness
    d.line(pts + [pts[0]], fill=edge, width=2 * SS, joint="curve")
    return _down(im, W, H)


NAMES = {
    "slider.tga": lambda: track(),
    "slider_thumb.tga": lambda: _thumb(False),
    "slider_thumb_sel.tga": lambda: _thumb(True),
    "arrow_left.tga": lambda: _arrow(-1, False),
    "arrow_left_sel.tga": lambda: _arrow(-1, True),
    "arrow_right.tga": lambda: _arrow(1, False),
    "arrow_right_sel.tga": lambda: _arrow(1, True),
}


def build():
    out = {}
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, fn in NAMES.items():
        img = fn()
        path = os.path.normpath(os.path.join(OUT_DIR, name))
        img.save(path, format="TGA")
        out[name] = img
        print("wrote %s %dx%d" % (path, img.size[0], img.size[1]))
    return out


def preview(imgs, png):
    im = Image.new("RGBA", (520, 220), (22, 25, 31, 255))
    d = ImageDraw.Draw(im)
    # a mock slider row: arrows + track + thumb
    track_img = imgs["slider.tga"].resize((300, 26), Image.LANCZOS)
    im.alpha_composite(track_img, (110, 70))
    im.alpha_composite(imgs["arrow_left.tga"].resize((26, 26), Image.LANCZOS), (78, 70))
    im.alpha_composite(imgs["arrow_right.tga"].resize((26, 26), Image.LANCZOS), (416, 70))
    im.alpha_composite(imgs["slider_thumb.tga"].resize((16, 32), Image.LANCZOS), (250, 67))
    # a second, selected row
    im.alpha_composite(track_img, (110, 140))
    im.alpha_composite(imgs["arrow_left_sel.tga"].resize((26, 26), Image.LANCZOS), (78, 140))
    im.alpha_composite(imgs["arrow_right_sel.tga"].resize((26, 26), Image.LANCZOS), (416, 140))
    im.alpha_composite(imgs["slider_thumb_sel.tga"].resize((16, 32), Image.LANCZOS), (330, 137))
    im.convert("RGB").save(png)
    print("preview", png)


if __name__ == "__main__":
    imgs = build()
    if "--preview" in sys.argv:
        preview(imgs, os.path.join(os.path.dirname(__file__), "slider_preview.png"))

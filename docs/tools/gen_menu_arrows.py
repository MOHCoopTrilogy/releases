# -*- coding: utf-8 -*-
"""Main-menu theme picker arrow buttons (ui/main.urc menuMusicPrev / menuMusicNext).

[user 2026-09-13] "your left and right buttons look terrible they need upscaled big time". They were the retail
16x16 textures/mohmenu/arrow_left/right stretched to 22x22 - a 16-pixel bevel is soft and blocky at any modern
resolution. Upscaling a 16-pixel icon only enlarges the blur, so these are DRAWN, not upscaled.

LOOK: they sit either side of the song-title box, and the box and REPORT A BUG beside it are the mod's own dark brown
panels (bgcolor 0.14 0.10 0.06 0.94, 3D_BORDER, beige 0.90 0.84 0.66 text). So each arrow is the same bevelled brown
plate with a bevelled beige arrow, and the three read as one control. Hover warms the plate and whitens the arrow,
like the retail sign buttons lighten on hover.

SIZE: 128x128. UI materials load with RegisterShaderNoMip (code/client/cl_ui.cpp:3893) - no mipmaps - so the texture
should sit near its largest on-screen size: a 30-unit widget is ~67 px at 1080p and ~135 px at 4K. Drawn at 8x and
downsampled with Lanczos for clean edges. Textures are gitignored in the mod repo, so this script is the source.

    python docs/tools/gen_menu_arrows.py            # write the four TGAs
    python docs/tools/gen_menu_arrows.py --preview <png>   # also write a preview on the real menu background
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

OUT_DIR = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\textures\mohmenu"
SIZE = 128
SS = 8  # supersample factor
BIG = SIZE * SS

PLATE = (36, 26, 15, 240)        # 0.14 0.10 0.06 0.94
PLATE_HOVER = (62, 45, 26, 245)
BEIGE_TOP, BEIGE_BOT = (242, 228, 190), (196, 180, 136)
WHITE_TOP, WHITE_BOT = (255, 248, 222), (236, 220, 176)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def _vertical_gradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGBA", (w, h))
    px = grad.load()
    for y in range(h):
        c = _lerp(top, bottom, y / float(max(1, h - 1))) + (255,)
        for x in range(w):
            px[x, y] = c
    return grad


def _plate(hover):
    img = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base = PLATE_HOVER if hover else PLATE
    d.rectangle([0, 0, BIG - 1, BIG - 1], fill=base)
    # 3D_BORDER-style bevel: a 1-unit engine border is ~4 texels here
    t = 4 * SS
    light = (104, 82, 56, 255) if not hover else (150, 118, 78, 255)
    shade = (12, 8, 4, 255)
    d.polygon([(0, 0), (BIG, 0), (BIG - t, t), (t, t), (t, BIG - t), (0, BIG)], fill=light)
    d.polygon([(BIG, BIG), (0, BIG), (t, BIG - t), (BIG - t, BIG - t), (BIG - t, t), (BIG, 0)], fill=shade)
    # a thin inner line so the face reads as recessed, like the engine's inner border
    i = t + SS
    d.rectangle([i, i, BIG - 1 - i, BIG - 1 - i], outline=(20, 14, 8, 200), width=SS)
    if hover:
        # faint warm glow on the face
        glow = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([BIG * 0.18, BIG * 0.18, BIG * 0.82, BIG * 0.82], fill=(255, 196, 110, 60))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(BIG * 0.12)))
    return img


def _arrow(right, hover):
    # arrow triangle, centred on the face
    cx, cy = BIG / 2.0, BIG / 2.0
    half_h = BIG * 0.27
    half_w = BIG * 0.21
    if right:
        pts = [(cx - half_w, cy - half_h), (cx + half_w + BIG * 0.03, cy), (cx - half_w, cy + half_h)]
    else:
        pts = [(cx + half_w, cy - half_h), (cx - half_w - BIG * 0.03, cy), (cx + half_w, cy + half_h)]

    layer = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))

    # drop shadow
    sh = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
    off = 3 * SS
    ImageDraw.Draw(sh).polygon([(x + off, y + off) for x, y in pts], fill=(0, 0, 0, 170))
    layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(2 * SS)))

    if hover:
        halo = Image.new("RGBA", (BIG, BIG), (0, 0, 0, 0))
        ImageDraw.Draw(halo).polygon(pts, fill=(255, 210, 140, 150))
        layer.alpha_composite(halo.filter(ImageFilter.GaussianBlur(5 * SS)))

    # dark outline, then the gradient fill inset inside it
    ImageDraw.Draw(layer).polygon(pts, fill=(16, 11, 6, 255))
    mask = Image.new("L", (BIG, BIG), 0)
    inset = 3.2 * SS
    # shrink the triangle towards its centroid for the fill
    gx = sum(p[0] for p in pts) / 3.0
    gy = sum(p[1] for p in pts) / 3.0
    inner = []
    for x, y in pts:
        vx, vy = x - gx, y - gy
        ln = (vx * vx + vy * vy) ** 0.5
        k = max(0.0, (ln - inset * 1.9) / ln)
        inner.append((gx + vx * k, gy + vy * k))
    ImageDraw.Draw(mask).polygon(inner, fill=255)
    top, bot = (WHITE_TOP, WHITE_BOT) if hover else (BEIGE_TOP, BEIGE_BOT)
    fill = _vertical_gradient((BIG, BIG), top, bot)
    layer.paste(fill, (0, 0), mask)

    # bevel on the arrow face: light along the upper edge, a darker lower facet
    facet = Image.new("L", (BIG, BIG), 0)
    lower = [inner[0], inner[1], inner[2]]
    lower = [(inner[1][0], inner[1][1]), (inner[2][0], inner[2][1]), ((inner[0][0] + inner[2][0]) / 2, cy)]
    ImageDraw.Draw(facet).polygon(lower, fill=70)
    dark = Image.new("RGBA", (BIG, BIG), (60, 44, 24, 255))
    layer.paste(dark, (0, 0), Image.composite(facet, Image.new("L", (BIG, BIG), 0), mask))
    hl = Image.new("L", (BIG, BIG), 0)
    ImageDraw.Draw(hl).line([inner[0], inner[1]], fill=150, width=int(1.6 * SS))
    light = Image.new("RGBA", (BIG, BIG), (255, 252, 236, 255))
    layer.paste(light, (0, 0), Image.composite(hl, Image.new("L", (BIG, BIG), 0), mask))
    return layer


def make(right, hover):
    img = _plate(hover)
    img.alpha_composite(_arrow(right, hover))
    return img.resize((SIZE, SIZE), Image.LANCZOS)


NAMES = {
    ("left", False): "coop_theme_left.tga",
    ("left", True): "coop_theme_left_sel.tga",
    ("right", False): "coop_theme_right.tga",
    ("right", True): "coop_theme_right_sel.tga",
}


def build():
    out = {}
    for (side, hover), name in NAMES.items():
        img = make(side == "right", hover)
        path = os.path.join(OUT_DIR, name)
        img.save(path, format="TGA")
        out[(side, hover)] = img
        print("wrote %s %dx%d" % (path, img.size[0], img.size[1]))
    return out


def preview(imgs, png):
    """The picker row on the real menu background, at a 1080p-like scale (x2.25) and zoomed, next to the old arrows."""
    import glob
    import io
    import zipfile

    scale = 2.25
    bg_png = os.path.join(os.path.dirname(png), "menu_bg_2x.png")
    band = None
    if os.path.exists(bg_png):
        full = Image.open(bg_png).convert("RGBA")  # 1280x960 = 640x480 at x2
        full = full.resize((int(640 * scale), int(480 * scale)), Image.LANCZOS)
        band = full.crop((0, int(436 * scale), int(640 * scale), int(480 * scale)))
    if band is None:
        band = Image.new("RGBA", (int(640 * scale), int(44 * scale)), (30, 30, 30, 255))

    def U(v):
        return int(round(v * scale))

    def box(im, x, y, w, h):
        d = ImageDraw.Draw(im)
        d.rectangle([U(x), U(y - 436), U(x + w) - 1, U(y - 436 + h) - 1], fill=PLATE)
        d.line([U(x), U(y - 436), U(x + w) - 1, U(y - 436)], fill=(104, 82, 56, 255), width=2)
        d.line([U(x), U(y - 436), U(x), U(y - 436 + h) - 1], fill=(104, 82, 56, 255), width=2)
        d.line([U(x), U(y - 436 + h) - 1, U(x + w) - 1, U(y - 436 + h) - 1], fill=(12, 8, 4, 255), width=2)
        d.line([U(x + w) - 1, U(y - 436), U(x + w) - 1, U(y - 436 + h) - 1], fill=(12, 8, 4, 255), width=2)
        d.text((U(x + w / 2.0) - 60, U(y - 436) + 6), "Main Theme", fill=(230, 214, 168, 255))
        d.text((U(x + w / 2.0) - 90, U(y - 436) + 36), "Medal of Honor: Frontline", fill=(168, 158, 132, 255))

    def row(hover_left, hover_right, old=False):
        im = band.copy()
        box(im, 138, 444, 200, 30)
        if old:
            retail = {}
            for r in (r"G:\GOG\Medal of Honor - Allied Assault War Chest\main",):
                for p in glob.glob(os.path.join(r, "*.pk3")):
                    z = zipfile.ZipFile(p)
                    for n in z.namelist():
                        ln = n.lower()
                        if ln in ("textures/mohmenu/arrow_left.tga", "textures/mohmenu/arrow_right.tga"):
                            retail[ln] = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
            l = retail["textures/mohmenu/arrow_left.tga"].resize((U(22), U(22)), Image.BILINEAR)
            rr = retail["textures/mohmenu/arrow_right.tga"].resize((U(22), U(22)), Image.BILINEAR)
            im.alpha_composite(l, (U(114), U(448 - 436)))
            im.alpha_composite(rr, (U(340), U(448 - 436)))
        else:
            l = imgs[("left", hover_left)].resize((U(30), U(30)), Image.BILINEAR)
            rr = imgs[("right", hover_right)].resize((U(30), U(30)), Image.BILINEAR)
            im.alpha_composite(l, (U(106), U(444 - 436)))
            im.alpha_composite(rr, (U(340), U(444 - 436)))
        return im.crop((U(96), 0, U(380), band.size[1]))

    rows = [("OLD (retail 16x16 at 22x22)", row(False, False, old=True)), ("NEW", row(False, False)),
            ("NEW, left hovered", row(True, False))]
    zoom = Image.new("RGBA", (SIZE * 4 + 20, SIZE * 2 + 30), (24, 24, 24, 255))
    zoom.alpha_composite(imgs[("left", False)], (5, 5))
    zoom.alpha_composite(imgs[("left", True)], (SIZE + 10, 5))
    zoom.alpha_composite(imgs[("right", False)], (2 * SIZE + 15, 5))
    zoom.alpha_composite(imgs[("right", True)], (3 * SIZE + 20 - 5, 5))
    w = max(max(r[1].size[0] for r in rows), zoom.size[0]) + 20
    h = sum(r[1].size[1] + 30 for r in rows) + zoom.size[1] + 40
    sheet = Image.new("RGBA", (w, h), (18, 18, 18, 255))
    d = ImageDraw.Draw(sheet)
    y = 10
    for label, im in rows:
        d.text((10, y), label, fill=(220, 220, 220, 255))
        sheet.alpha_composite(im, (10, y + 16))
        y += im.size[1] + 30
    d.text((10, y), "128x128 textures: normal / hover, left and right", fill=(220, 220, 220, 255))
    sheet.alpha_composite(zoom, (10, y + 16))
    sheet.save(png)
    print("preview", png)


if __name__ == "__main__":
    imgs = build()
    if "--preview" in sys.argv:
        preview(imgs, sys.argv[sys.argv.index("--preview") + 1])

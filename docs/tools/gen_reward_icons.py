"""gen_reward_icons.py - the two officer-reward icons of the item readout row (cgame cg_coopfeed.c CG_DrawCoopItems).

User 2026-10-12: "those icons [paradrop, airstrike] could also be made smaller and higher def like your new icons
you just did with hotkeys". The old art (textures/hud/coop_paradrop_icon, textures/hud/artillery) was an upscaled
pixel sprite / a retail HUD picture drawn at 16x16 virtual units by the script HUD.

    python docs/tools/gen_reward_icons.py            write the TGAs into the mod (gitignored there by design)
    python docs/tools/gen_reward_icons.py check      exit 1 when a TGA in the mod is missing or differs
    python docs/tools/gen_reward_icons.py sheet <png> a QA sheet: each icon at 1:1 for 480 / 720 / 1080 / 1440 and at 8x

Style = the existing readout icons (coop_medkit_icon, coop_cover_icon, coop_ammobox_icon): flat fills, one darker
outline of the same hue, a single lighter facet. Designed on a 128 grid, drawn at 8x and reduced once (Lanczos)
to 64 x 64 RGBA. 64, not the 128 of the older icons, on purpose: the HUD picture has no mip levels, so the engine
reduces it with plain bilinear sampling, and a 128 px picture drawn at 21-32 px (720p-1080p) skips three of every
four texels - thin lines came out as dark blotches in the first engine stills. At 64 the reduction is 2:1 at 1080p
and the picture is still 1:1 at 4K. For the same reason no feature is thinner than 3.5 grid units. No texture is
read: shapes only. The QA sheet reduces the icons the way the engine does (point-sampled bilinear), not with a
resize filter that would flatter them.

  coop_reward_paradrop  a canopy with three gores and scalloped hem, four lines, a supply crate (the sandbag tan)
  coop_reward_strike    a falling bomb, nose down-right: olive body, brass nose band, steel fins
"""
import io
import math
import os
import sys

MOD = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hzm-mohaa-coop-mod"))
OUT = os.path.join(MOD, "textures", "hud")
N = 128                 # design grid
OUTN = 64               # the picture that is written
SS = 8
S = N * SS

CREAM, CREAM_HI, CREAM_SH = (238, 228, 198), (252, 246, 226), (206, 192, 156)
BROWN = (86, 62, 34)
TAN, TAN_HI = (200, 160, 110), (226, 194, 150)
OLIVE, OLIVE_HI, OLIVE_DK = (112, 128, 70), (150, 166, 100), (40, 48, 24)
BRASS = (222, 176, 44)
STEEL, STEEL_DK = (168, 174, 178), (58, 62, 66)


def _pil():
    from PIL import Image, ImageDraw
    return Image, ImageDraw


def tga(im):
    """PIL RGBA image -> uncompressed 32-bit TGA, bottom-up (the engine's loaders ignore the top-down bit)"""
    im = im.convert("RGBA")
    w, h = im.size
    out = bytearray([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, w & 255, w >> 8, h & 255, h >> 8, 32, 8])
    px = im.load()
    for y in range(h - 1, -1, -1):
        for x in range(w):
            r, g, b, a = px[x, y]
            out += bytes((b, g, r, a))
    return bytes(out)


def u(v):
    """128-space coordinate -> supersampled pixel"""
    return int(round(v * SS))


def P(pts):
    return [(u(x), u(y)) for x, y in pts]


def finish(big):
    Image, _ = _pil()
    im = big.resize((OUTN, OUTN), Image.LANCZOS)
    # colour under fully transparent pixels = the nearest outline colour, so bilinear sampling has no dark fringe
    px = im.load()
    for y in range(OUTN):
        for x in range(OUTN):
            r, g, b, a = px[x, y]
            if a == 0:
                px[x, y] = (60, 56, 44, 0)
    return im


def paradrop():
    Image, ImageDraw = _pil()
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, top, hem, rx = 64.0, 6.0, 62.0, 56.0
    ol = 5.0                                           # outline, 128-space
    # canopy: outline dome, then the fill dome, then the scalloped hem cut out of the bottom
    d.pieslice([u(cx - rx), u(top), u(cx + rx), u(top + 2 * (hem - top))], 180, 360, fill=BROWN + (255,))
    d.pieslice([u(cx - rx + ol), u(top + ol), u(cx + rx - ol), u(top + 2 * (hem - top) - ol)], 180, 360, fill=CREAM + (255,))
    # a lighter facet on the upper left, a shaded one on the right gore
    d.pieslice([u(cx - rx + ol), u(top + ol), u(cx + rx - ol), u(top + 2 * (hem - top) - ol)], 180, 245, fill=CREAM_HI + (255,))
    d.pieslice([u(cx - rx + ol), u(top + ol), u(cx + rx - ol), u(top + 2 * (hem - top) - ol)], 312, 360, fill=CREAM_SH + (255,))
    # gores: two seams from the crown to the hem
    for gx in (-rx / 2.6, rx / 2.6):
        d.line(P([(cx + gx * 0.18, top + ol), (cx + gx, hem)]), fill=BROWN + (255,), width=u(3.6))
    # hem band and scallops (three bites out of the bottom edge)
    d.rectangle([u(cx - rx), u(hem - ol), u(cx + rx), u(hem)], fill=BROWN + (255,))
    w3 = (2 * rx) / 3.0
    for i in range(3):
        x0 = cx - rx + i * w3
        d.ellipse([u(x0 + 3.0), u(hem - 9.0), u(x0 + w3 - 3.0), u(hem + 9.0)], fill=(0, 0, 0, 0))
        d.arc([u(x0 + 3.0), u(hem - 9.0), u(x0 + w3 - 3.0), u(hem + 9.0)], 180, 360, fill=BROWN + (255,), width=u(ol * 0.8))
    # two bold lines, from the ends of the hem (after the scallops, which would bite their tops off) to the crate.
    # Four thin ones were tried: at the size the row draws them they merged into a dark patch under the canopy.
    for x0, x1 in ((cx - rx + 3.0, cx - 13), (cx + rx - 3.0, cx + 13)):
        d.line(P([(x0, hem - 1.5), (x1, 91)]), fill=BROWN + (255,), width=u(5.0))
    # crate
    bx0, by0, bx1, by1 = cx - 21, 88.0, cx + 21, 122.0
    d.rectangle([u(bx0), u(by0), u(bx1), u(by1)], fill=BROWN + (255,))
    d.rectangle([u(bx0 + ol), u(by0 + ol), u(bx1 - ol), u(by1 - ol)], fill=TAN + (255,))
    d.rectangle([u(bx0 + ol), u(by0 + ol), u(bx1 - ol), u(by0 + ol + 5)], fill=TAN_HI + (255,))
    d.line(P([(bx0 + ol, (by0 + by1) / 2 + 3), (bx1 - ol, (by0 + by1) / 2 + 3)]), fill=BROWN + (255,), width=u(3.6))
    return finish(im)


def strike():
    Image, ImageDraw = _pil()
    # the bomb is drawn upright (nose down) on a larger sheet, then turned so the nose points down-right
    B = S * 2
    im = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = B / 2.0

    def q(x, y):                      # 128-space offsets from the sheet centre
        return (int(round(c + x * SS)), int(round(c + y * SS)))

    ol = 4.6
    bw = 22.0                                  # body half width
    y_sh, y_cyl, y_tip = -30.0, 14.0, 54.0     # top of the shoulder, end of the straight part, tip of the nose

    def half(y):                               # half width of the body at height y
        if y < y_sh + bw * 0.9:                # rounded shoulder
            t = (y_sh + bw * 0.9 - y) / (bw * 0.9)
            return bw * math.sqrt(max(0.0, 1.0 - t * t))
        if y <= y_cyl:
            return bw
        t = (y - y_cyl) / (y_tip - y_cyl)      # ogive nose
        return bw * max(0.0, 1.0 - t ** 1.9)

    ys = [y_sh + i * (y_tip - y_sh) / 80.0 for i in range(81)]
    outline = [q(half(y), y) for y in ys] + [q(-half(y), y) for y in reversed(ys)]

    def shape(pts, fill, edge):
        d.polygon(pts, fill=edge)
        d.line(pts + [pts[0]], fill=edge, width=int(2 * ol * SS), joint="curve")
        d.polygon(pts, fill=fill)

    # tail: a stem and two swept fins, steel with a dark edge (drawn first, the body covers the root)
    shape([q(-5, -54), q(5, -54), q(5, -24), q(-5, -24)], STEEL_DK + (255,), STEEL_DK + (255,))
    shape([q(-7, -50), q(-24, -54), q(-24, -38), q(-7, -24)], STEEL + (255,), STEEL_DK + (255,))
    shape([q(7, -50), q(24, -54), q(24, -38), q(7, -24)], STEEL + (255,), STEEL_DK + (255,))
    # body
    shape(outline, OLIVE + (255,), OLIVE_DK + (255,))
    # a lighter facet down the left side
    d.polygon([q(-bw + 4.5, y_sh + 15), q(-bw + 10.5, y_sh + 11), q(-bw + 10.5, y_cyl - 3), q(-bw + 4.5, y_cyl - 1)],
              fill=OLIVE_HI + (255,))
    # brass nose band between two dark lines
    b0, b1 = y_cyl + 2.0, y_cyl + 13.0
    d.polygon([q(-half(b0), b0), q(half(b0), b0), q(half(b1), b1), q(-half(b1), b1)], fill=BRASS + (255,))
    for yb in (b0, b1):
        d.line([q(-half(yb), yb), q(half(yb), yb)], fill=OLIVE_DK + (255,), width=int(2.6 * SS))
    im = im.rotate(45, resample=Image.BICUBIC, center=(c, c))          # counter-clockwise: nose to the lower right
    big = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    big.alpha_composite(im, (0, 0), (int(c - S / 2), int(c - S / 2), int(c + S / 2), int(c + S / 2)))
    return finish(big)


ICONS = {"coop_reward_paradrop.tga": paradrop, "coop_reward_strike.tga": strike}


def build():
    out = {name: fn() for name, fn in sorted(ICONS.items())}
    for name, im in out.items():
        # QA gate: nothing may touch the edge of the picture (a clipped shape), and it must fill the frame
        box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        assert box and box[0] >= 1 and box[1] >= 1 and box[2] <= OUTN - 1 and box[3] <= OUTN - 1, (name, "clipped", box)
        assert box[2] - box[0] >= OUTN * 3 // 4 or box[3] - box[1] >= OUTN * 3 // 4, (name, "too small in its frame", box)
    return out


def sheet(path):
    Image, ImageDraw = _pil()
    ims = build()
    # the pixel sizes the row draws an icon at: 14 virtual-480 units, never under 14 px
    sizes = [(480, 14), (720, 21), (1080, 32), (1440, 42)]
    W, H = 60 + len(ims) * 1090, 1100
    out = Image.new("RGB", (W, H), (0, 0, 0))
    grounds = [(34, 38, 34), (120, 128, 112), (226, 230, 236)]            # night, day, snow
    for gi, g in enumerate(grounds):
        out.paste(g, (0, gi * (H // 3), W, (gi + 1) * (H // 3)))
    for k, (name, im) in enumerate(ims.items()):
        x0 = 30 + k * 1090
        for gi in range(3):
            y0 = gi * (H // 3) + 20
            x = x0
            for _, px in sizes:
                k = float(OUTN) / px        # as the engine draws it: bilinear, one sample per screen pixel
                s = im.transform((px, px), Image.AFFINE, (k, 0, (k - 1) / 2.0, 0, k, (k - 1) / 2.0), resample=Image.BILINEAR)
                out.paste(s, (x, y0 + 4), s)
                s3 = s.resize((px * 3, px * 3), Image.NEAREST)
                out.paste(s3, (x, y0 + 60), s3)
                x += px * 3 + 24
            b8 = im.resize((320, 320), Image.LANCZOS)
            out.paste(b8, (x0 + 700, y0 + 10), b8)
    out.save(path)
    print("sheet ->", path)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "write"
    if mode == "sheet":
        sheet(sys.argv[2])
        return 0
    data = {name: tga(im) for name, im in build().items()}
    if mode == "check":
        bad = [n for n, dta in data.items()
               if not os.path.exists(os.path.join(OUT, n)) or io.open(os.path.join(OUT, n), "rb").read() != dta]
        print("DRIFT: " + ", ".join(bad) + " - run gen_reward_icons.py" if bad else "OK: %d reward icons current" % len(data))
        return 1 if bad else 0
    for n, dta in data.items():
        io.open(os.path.join(OUT, n), "wb").write(dta)
        print("wrote", os.path.join(OUT, n), len(dta), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Launch memorial card: "In Memory of Vince Zampella" (user 2026-09-27). Renders the art the engine shows on black
before the main menu, plus review previews.

  ui/hzm_memorial/memorial.tga   2048x1024, 24-bit, uncompressed, BOTTOM-UP rows (this engine ignores the TGA
                                 top-down bit - bug-3019; Pillow honours it, so never trust a PIL preview of a
                                 top-down file). Opaque on black like the retail intro cards (mohaa_title/legal):
                                 the engine fades it by colour (shader rgbGen global).
  Layout: the MOHAA.exe icon, name, role, dates, a gap, the two poem lines (italic, lighter). The text is BAKED in:
  the game fonts are ASCII-only, and the dates need an en dash. The poem is deliberately NOT attributed - its
  authorship is disputed.
  The canvas is 1:1 at 1440p: the engine draws it 0.711 x screen height tall (1024/1440), centred, aspect-correct.

  --icon A   (default) faithful HD redraw of the MOHAA.exe desktop icon: black medallion, thin gold rim, a ring of
             gold lettering, a faceted five-point star (cream / gold / steel-grey facets, lit from the top-left) with
             a bronze centre.
  --icon B   the original 32x32 icon pixels, nearest-neighbour upscaled.

usage: python docs/tools/gen_memorial.py OUTDIR [--icon A|B] [--previews PREVIEWDIR] [--check]
"""
import argparse
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 2048, 1024
SS = 3  # supersampling for the icon and text
ICON_32 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "mohaa_exe_32.png")  # MOHAA.exe icon, 32x32 (extracted from the exe resources)
FONTS = {
    "serif": [r"C:\Windows\Fonts\pala.ttf", r"C:\Windows\Fonts\georgia.ttf"],
    "italic": [r"C:\Windows\Fonts\palai.ttf", r"C:\Windows\Fonts\georgiai.ttf"],
    "caps": [r"C:\Windows\Fonts\palab.ttf", r"C:\Windows\Fonts\georgiab.ttf"],
}
TITLE = "In Memory of Vince Zampella"
ROLE = "Lead Designer, Medal of Honor: Allied Assault"
DATES = "October 1, 1969 \u2013 December 21, 2025"
POEM = ["And when he gets to Heaven, to St. Peter he will tell:",
        "One more soldier reporting, sir, I've served my time in Hell"]
RING_WORDS = ["MEDAL", "OF", "HONOR", "ALLIED", "ASSAULT"]  # one per gap, clockwise from the upper right

INK = (236, 230, 212)      # warm off-white (title)
GOLD = (201, 160, 82)      # muted gold (role)
DIM = (176, 168, 150)      # dates
POEMC = (158, 151, 136)    # poem, lighter weight


def font(kind, px):
    for p in FONTS[kind]:
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    raise SystemExit("no font for %s" % kind)


# ------------------------------------------------------------------------------------------ icon A (HD redraw)
def icon_a(size, parts=("disk", "ring", "star")):
    """parts: any of disk (medallion + rim), ring (the lettering), star (star + boss) - the loading-medal morph
    fades the lettered ring separately from the star. The default (all three) is the memorial icon."""
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = S / 2.0
    R = S / 2.0 - 2 * SS

    def circ(r, **kw):
        d.ellipse([c - r, c - r, c + r, c + r], **kw)

    if "disk" in parts:
        circ(R, fill=(8, 7, 5, 255))                                  # black medallion
        circ(R, outline=(150, 112, 44, 255), width=int(R * 0.035))     # thin gold rim
        circ(R * 0.955, outline=(70, 52, 20, 255), width=max(1, int(R * 0.008)))
        circ(R * 0.70, outline=(70, 52, 20, 255), width=max(1, int(R * 0.008)))
    # ring of gold lettering. The star's points reach the rim (as in the original), so the words sit in the five gaps
    # between them - one word per gap, so no letter is ever hidden under a point. Top-half words read clockwise with
    # letter tops outward; bottom-half words read left-to-right with tops toward the centre (coin convention).
    band_r = R * 0.83
    fnt = font("caps", int(R * 0.13))
    step = 9.0  # degrees per letter
    for word, gap in zip(RING_WORDS if "ring" in parts else [], (-54.0, 18.0, 90.0, 162.0, 234.0)):
        bottom = 0.0 < (gap % 360.0) < 180.0
        n = len(word)
        for k, ch in enumerate(word):
            off = (k - (n - 1) / 2.0) * step
            ang = gap - off if bottom else gap + off
            tile = Image.new("RGBA", (int(R * 0.3), int(R * 0.3)), (0, 0, 0, 0))
            td = ImageDraw.Draw(tile)
            td.text((tile.width / 2, tile.height / 2), ch, font=fnt, fill=(224, 182, 82, 255), anchor="mm")
            rot = -(ang + 90.0) if not bottom else -(ang - 90.0)
            tile = tile.rotate(rot, resample=Image.BICUBIC)
            x = c + band_r * math.cos(math.radians(ang)) - tile.width / 2
            y = c + band_r * math.sin(math.radians(ang)) - tile.height / 2
            img.alpha_composite(tile, (int(round(x)), int(round(y))))
    # faceted five-point star, lit from the top-left; points reach into the lettering ring
    RT, RI = R * 0.97, R * 0.40
    light = -135.0
    stops = [(0.0, (60, 60, 58)), (0.45, (150, 118, 52)), (0.72, (226, 189, 85)), (1.0, (255, 243, 220))]

    def shade(b):
        for (b0, c0), (b1, c1) in zip(stops, stops[1:]):
            if b <= b1:
                t = (b - b0) / (b1 - b0)
                return tuple(int(round(c0[j] + (c1[j] - c0[j]) * t)) for j in range(3)) + (255,)
        return stops[-1][1] + (255,)

    def pt(r, deg):
        return (c + r * math.cos(math.radians(deg)), c + r * math.sin(math.radians(deg)))

    for i in range(5 if "star" in parts else 0):
        th = -90 + 72 * i
        T, A, B = pt(RT, th), pt(RI, th - 36), pt(RI, th + 36)
        for poly, phi in (((c, c), A, T), th - 60), (((c, c), T, B), th + 60):
            b = 0.5 + 0.5 * math.cos(math.radians(phi - light))
            d.polygon(poly, fill=shade(b ** 1.1))
        d.line([(c, c), T], fill=(40, 34, 24, 255), width=max(1, SS))   # the ridge between the two facets
    # bronze centre boss
    if "star" in parts:
        circ(R * 0.17, fill=(138, 90, 32, 255))
        circ(R * 0.17, outline=(226, 189, 85, 255), width=max(1, int(R * 0.02)))
        circ(R * 0.08, fill=(92, 58, 20, 255))
    return img.resize((size, size), Image.LANCZOS)


def icon_b(size):
    src = Image.open(ICON_32).convert("RGBA")
    k = max(1, size // 32)
    big = src.resize((32 * k, 32 * k), Image.NEAREST)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(big, ((size - big.width) // 2, (size - big.height) // 2))
    return out


# ------------------------------------------------------------------------------------------ card
def render(icon_kind):
    card = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 255))
    d = ImageDraw.Draw(card)
    cx = W * SS / 2
    # icon
    isz = 352 if icon_kind == "A" else 352  # B: 11x of 32 px
    # [user 2026-10-12] "only one badge, at the top, and it should be the animated one": by default the card carries NO
    # baked badge any more. Its 352 px slot (top 44) stays in the layout and the exe draws the animated medal there
    # (client/cl_ui.cpp UI_MemorialDraw, ICON_TOP / ICON_PX below; art: gen_memorial_medal.py).
    if icon_kind != "none":
        ic = icon_a(isz) if icon_kind == "A" else icon_b(isz)
        ic = ic.resize((isz * SS, isz * SS), Image.NEAREST if icon_kind == "B" else Image.LANCZOS)
        card.alpha_composite(ic, (int(cx - ic.width / 2), 44 * SS))
    y = (44 + isz + 52) * SS
    # text block (baseline-free: anchor "mt" = middle-top)
    for text, kind, px, col, gap in ((TITLE, "serif", 78, INK, 30), (ROLE, "serif", 38, GOLD, 16),
                                     (DATES, "serif", 38, DIM, 64)):
        f = font(kind, px * SS)
        d.text((cx, y), text, font=f, fill=col + (255,), anchor="mt")
        y += int((f.getbbox(text)[3] - f.getbbox(text)[1]) + gap * SS)
    f = font("italic", 37 * SS)
    for line in POEM:
        d.text((cx, y), line, font=f, fill=POEMC + (255,), anchor="mt")
        y += int(52 * SS)
    assert y < H * SS - 20 * SS, "layout overflows the canvas"
    return card.convert("RGB").resize((W, H), Image.LANCZOS)


def tga_bytes(img):
    """24-bit uncompressed TGA, BOTTOM-UP rows (descriptor 0) - see the module docstring."""
    w, h = img.size
    hdr = bytes([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, w & 255, w >> 8, h & 255, h >> 8, 24, 0])
    r, g, b = img.transpose(Image.FLIP_TOP_BOTTOM).split()
    return hdr + Image.merge("RGB", (b, g, r)).tobytes()


# ------------------------------------------------------------------------------------------ previews
def engine_rect(sw, sh):
    """Must match the engine: height 1024/1440 of the screen, 2:1, centred; clamped to 98% of the width."""
    hh = sh * (1024.0 / 1440.0)
    ww = hh * 2.0
    if ww > sw * 0.98:
        ww = sw * 0.98
        hh = ww / 2.0
    return (sw - ww) / 2.0, (sh - hh) / 2.0, ww, hh


def preview(card, sw, sh, alpha=1.0):
    scr = Image.new("RGB", (sw, sh), (0, 0, 0))
    x, y, ww, hh = engine_rect(sw, sh)
    pic = card.resize((int(round(ww)), int(round(hh))), Image.LANCZOS)
    if alpha < 1.0:
        pic = Image.eval(pic, lambda v: int(v * alpha))
    scr.paste(pic, (int(round(x)), int(round(y))))
    return scr


def fade_alpha(t, fin=1.0, hold=4.0, fout=1.0):
    if t < fin:
        return t / fin
    if t < fin + hold:
        return 1.0
    return max(0.0, 1.0 - (t - fin - hold) / fout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--icon", choices=["none", "A", "B"], default="none")
    ap.add_argument("--previews")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    card = render(a.icon)
    data = tga_bytes(card)
    path = os.path.join(a.outdir, "memorial.tga")
    if a.check:
        ok = os.path.exists(path) and open(path, "rb").read() == data
        print("check:", "OK" if ok else "STALE")
        return 0 if ok else 1
    os.makedirs(a.outdir, exist_ok=True)
    open(path, "wb").write(data)
    print("wrote", path, len(data))
    if a.previews:
        os.makedirs(a.previews, exist_ok=True)
        tag = a.icon
        for sw, sh in ((1920, 1080), (3440, 1440), (1024, 768)):
            preview(card, sw, sh).save(os.path.join(a.previews, "memorial_%s_%dx%d.png" % (tag, sw, sh)))
        # icon close-up and a fade-timing GIF (10 fps: 1 s in, 4 s hold, 1 s out)
        ic = icon_b(512) if tag == "B" else icon_a(512)
        bg = Image.new("RGBA", ic.size, (0, 0, 0, 255))
        bg.alpha_composite(ic)
        bg.convert("RGB").save(os.path.join(a.previews, "memorial_icon_%s_closeup.png" % tag))
        frames = [preview(card, 960, 540, fade_alpha(i / 10.0)) for i in range(0, 61)]
        frames[0].save(os.path.join(a.previews, "memorial_%s_fade_6s.gif" % tag), save_all=True,
                       append_images=frames[1:], duration=100, loop=0)
        print("previews in", a.previews)
    return 0


if __name__ == "__main__":
    sys.exit(main())

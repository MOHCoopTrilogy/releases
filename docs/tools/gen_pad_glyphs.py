"""gen_pad_glyphs.py - procedural controller-button glyph atlas for the on-screen key prompts (gamepad-next).

    python docs/tools/gen_pad_glyphs.py     -> docs/tools/assets/fixes/textures/hud/coop_padglyphs.tga  (256x256 RGBA)

4 x 4 cells of 64 px, left to right, top to bottom. The ORDER is shared with cgame (cg_coopfeed.c s_padGlyphs):
  0 A  1 B  2 X  3 Y  | 4 LB  5 RB  6 LT  7 RT | 8 DPAD-UP  9 DPAD-DOWN  10 DPAD-LEFT  11 DPAD-RIGHT | 12 L3  13 R3  14 VIEW  15 MENU
Face buttons carry the Xbox colours (A green, B red, X blue, Y yellow), the rest are neutral dark with white marks.
Everything is drawn at 4x and reduced, so the edges are clean at the small sizes the HUD uses."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fixes", "textures", "hud", "coop_padglyphs.tga")
S = 4                      # supersample
C = 64 * S
FONT = None
for f in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"):
    if os.path.exists(f):
        FONT = f
        break


def font(px):
    return ImageFont.truetype(FONT, int(px * S)) if FONT else ImageFont.load_default()


def text_c(d, cx, cy, s, px, fill):
    f = font(px)
    bb = d.textbbox((0, 0), s, font=f)
    d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), s, font=f, fill=fill)


def cell():
    im = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def face(letter, col):
    im, d = cell()
    m = 4 * S
    d.ellipse((m, m, C - m, C - m), fill=(24, 26, 30, 255))
    d.ellipse((m + 3 * S, m + 3 * S, C - m - 3 * S, C - m - 3 * S), fill=col + (255,))
    text_c(d, C / 2, C / 2 + 1 * S, letter, 38, (255, 255, 255, 255))
    return im


def bumper(label, trigger=False):
    im, d = cell()
    x0, x1 = 3 * S, C - 3 * S
    y0, y1 = (14 if not trigger else 8) * S, (50 if not trigger else 56) * S
    d.rounded_rectangle((x0, y0, x1, y1), radius=(10 if not trigger else 14) * S, fill=(24, 26, 30, 255))
    d.rounded_rectangle((x0 + 3 * S, y0 + 3 * S, x1 - 3 * S, y1 - 3 * S), radius=(8 if not trigger else 11) * S,
                        fill=(92, 98, 108, 255))
    text_c(d, C / 2, (y0 + y1) / 2 + 1 * S, label, 26 if not trigger else 26, (255, 255, 255, 255))
    return im


def dpad(dirn):
    im, d = cell()
    a, b = 21 * S, 43 * S           # arm thickness band
    lo, hi = 4 * S, C - 4 * S
    plus = [(a, lo), (b, lo), (b, a), (hi, a), (hi, b), (b, b), (b, hi), (a, hi), (a, b), (lo, b), (lo, a), (a, a)]
    d.polygon(plus, fill=(24, 26, 30, 255))
    pad = 2 * S
    inner = [(a + pad, lo + pad), (b - pad, lo + pad), (b - pad, a + pad), (hi - pad, a + pad), (hi - pad, b - pad),
             (b - pad, b - pad), (b - pad, hi - pad), (a + pad, hi - pad), (a + pad, b - pad), (lo + pad, b - pad),
             (lo + pad, a + pad), (a + pad, a + pad)]
    d.polygon(inner, fill=(58, 63, 72, 255))
    hl = (255, 196, 36, 255)
    if dirn == "u":
        d.polygon([(a + pad, lo + pad), (b - pad, lo + pad), (b - pad, a - 1 * S), (a + pad, a - 1 * S)], fill=hl)
    elif dirn == "d":
        d.polygon([(a + pad, b + 1 * S), (b - pad, b + 1 * S), (b - pad, hi - pad), (a + pad, hi - pad)], fill=hl)
    elif dirn == "l":
        d.polygon([(lo + pad, a + pad), (a - 1 * S, a + pad), (a - 1 * S, b - pad), (lo + pad, b - pad)], fill=hl)
    else:
        d.polygon([(b + 1 * S, a + pad), (hi - pad, a + pad), (hi - pad, b - pad), (b + 1 * S, b - pad)], fill=hl)
    return im


def stick(label):
    im, d = cell()
    m = 4 * S
    d.ellipse((m, m, C - m, C - m), fill=(24, 26, 30, 255))
    d.ellipse((m + 3 * S, m + 3 * S, C - m - 3 * S, C - m - 3 * S), fill=(92, 98, 108, 255))
    d.ellipse((m + 10 * S, m + 10 * S, C - m - 10 * S, C - m - 10 * S), outline=(200, 205, 212, 255), width=2 * S)
    text_c(d, C / 2, C / 2 + 1 * S, label, 26, (255, 255, 255, 255))
    return im


def view():
    im, d = cell()
    m = 4 * S
    d.ellipse((m, m, C - m, C - m), fill=(24, 26, 30, 255))
    d.ellipse((m + 3 * S, m + 3 * S, C - m - 3 * S, C - m - 3 * S), fill=(92, 98, 108, 255))
    w = 11 * S
    d.rectangle((21 * S, 25 * S, 21 * S + w, 25 * S + w), outline=(255, 255, 255, 255), width=2 * S)
    d.rectangle((29 * S, 29 * S, 29 * S + w + 1 * S, 29 * S + w + 1 * S), outline=(255, 255, 255, 255), width=2 * S,
                fill=(92, 98, 108, 255))
    return im


def menu():
    im, d = cell()
    m = 4 * S
    d.ellipse((m, m, C - m, C - m), fill=(24, 26, 30, 255))
    d.ellipse((m + 3 * S, m + 3 * S, C - m - 3 * S, C - m - 3 * S), fill=(92, 98, 108, 255))
    for k in range(3):
        y = (23 + k * 9) * S
        d.rounded_rectangle((20 * S, y, 44 * S, y + 4 * S), radius=2 * S, fill=(255, 255, 255, 255))
    return im


def ps_face(shape, col):
    """[v1.10.45] PlayStation face button: a dark disc with the coloured symbol drawn as a shape (no letter)"""
    im, d = cell()
    m = 4 * S
    d.ellipse((m, m, C - m, C - m), fill=(24, 26, 30, 255))
    d.ellipse((m + 3 * S, m + 3 * S, C - m - 3 * S, C - m - 3 * S), fill=(46, 50, 58, 255))
    c, r, wd = C / 2, 13 * S, 4 * S
    if shape == "cross":
        d.line((c - r, c - r, c + r, c + r), fill=col + (255,), width=wd)
        d.line((c - r, c + r, c + r, c - r), fill=col + (255,), width=wd)
    elif shape == "circle":
        d.ellipse((c - r, c - r, c + r, c + r), outline=col + (255,), width=wd)
    elif shape == "square":
        d.rectangle((c - r + 1 * S, c - r + 1 * S, c + r - 1 * S, c + r - 1 * S), outline=col + (255,), width=wd)
    else:
        d.polygon([(c, c - r - 1 * S), (c + r + 1 * S, c + r - 2 * S), (c - r - 1 * S, c + r - 2 * S)], outline=col + (255,), width=wd)
    return im


# [v1.10.45] the same 16 cells for a PlayStation pad (cgame picks coop_padglyphs_ps when in_padType is "ps")
GLYPHS_PS = [
    lambda: ps_face("cross", (110, 160, 232)), lambda: ps_face("circle", (232, 92, 92)), lambda: ps_face("square", (222, 120, 190)),
    lambda: ps_face("triangle", (80, 200, 150)),
    lambda: bumper("L1"), lambda: bumper("R1"), lambda: bumper("L2", True), lambda: bumper("R2", True),
    lambda: dpad("u"), lambda: dpad("d"), lambda: dpad("l"), lambda: dpad("r"),
    lambda: stick("L3"), lambda: stick("R3"), view, menu,
]

GLYPHS = [
    lambda: face("A", (92, 184, 60)), lambda: face("B", (217, 69, 59)), lambda: face("X", (59, 127, 217)),
    lambda: face("Y", (224, 181, 43)),
    lambda: bumper("LB"), lambda: bumper("RB"), lambda: bumper("LT", True), lambda: bumper("RT", True),
    lambda: dpad("u"), lambda: dpad("d"), lambda: dpad("l"), lambda: dpad("r"),
    lambda: stick("L3"), lambda: stick("R3"), view, menu,
]

if __name__ == "__main__":
    ps = "--ps" in sys.argv
    if ps:
        GLYPHS = GLYPHS_PS
        OUT = OUT.replace("coop_padglyphs.tga", "coop_padglyphs_ps.tga")
        if len(sys.argv) > 2:
            OUT = sys.argv[2]
    atlas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    for i, g in enumerate(GLYPHS):
        im = g().resize((64, 64), Image.LANCZOS)
        atlas.paste(im, ((i % 4) * 64, (i // 4) * 64))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    atlas.save(OUT, format="TGA")
    atlas.save(os.path.join(os.path.dirname(__file__), "..", "proposals", "gamepad_2026-10-18", "padglyphs%s_preview.png" % ("_ps" if ps else "")))
    print("wrote", OUT)

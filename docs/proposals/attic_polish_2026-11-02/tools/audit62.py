"""audit62.py <runs dir> <out dir> - v1.10.62 QA: before (v1.10.61 survey sv_after_<res>) | after (sv_v62_<res>) 100 % crops of every
audit number the re-bake touched, per 16:9 resolution (1080 boxes, scaled for 720), plus whole-frame before | after pairs at 21:9 / 4:3
(their framing differs, so a fixed box would not match) and the 4:3 centred layout with the WHAT'S NEW twin."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

runs, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
F = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 20)
F2 = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
AUDIT = [  # n, what changed, box at 1080
    (1, "#1 work table: glossy red + card table -> stock table baked, clipboards", (0, 740, 640, 1080)),
    (2, "#2 cabinet / safe / typewriter -> stock filing cabinets + typewriter", (170, 500, 420, 710)),
    (5, "#5 / #17 lamp shades -> bottle-green enamel", (560, 300, 1110, 720)),
    (6, "#6 / #7 trays, loose sheets, card box -> stock folders", (940, 580, 1220, 820)),
    (8, "#8 reels -> REPORT A BUG toolbox", (1140, 720, 1380, 860)),
    (9, "phones -> black bakelite", (1020, 520, 1400, 720)),
    (10, "#10 projector -> stock projector", (1380, 560, 1580, 800)),
    (13, "#13 / #14 rifles gone, BRIEFING door moved there, doorway filled", (1060, 320, 1340, 620)),
    (15, "#15 fan cage + MP door light leak", (1320, 320, 1540, 660)),
    (16, "#16 lower chalkboard: AWAITING ORDERS", (640, 240, 930, 400)),
    (22, "FIELD REPORT board (= WHAT'S NEW) on the post", (1700, 440, 1920, 660)),
    (23, "right wall: chair / phone shadow retouch", (1560, 600, 1920, 900)),
    (19, "gramophone corner + tone arm", (580, 760, 1000, 1070)),
]


def shot(tag, res, name="00idle"):
    p = os.path.join(runs, "sv_%s_%s" % (tag, res), "sv_%s_%s_%s.tga" % (tag, res, name))
    return Image.open(p).convert("RGB") if os.path.exists(p) else None


def pair_sheet(res, k):
    b, a = shot("after", res), shot("v62", res)
    if a is None:
        return None
    TW = 520
    rows = []
    for n, lab, box in AUDIT:
        bx = tuple(int(round(v * k)) for v in box)
        ims = [(im.crop(bx) if im is not None else Image.new("RGB", (bx[2] - bx[0], bx[3] - bx[1]), (40, 0, 0))) for im in (b, a)]
        s = min(TW / ims[0].width, 300 / ims[0].height, 2.5)
        rows.append((lab, [im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS) for im in ims]))
    H = sum(r[1][0].height + 34 for r in rows) + 50
    S = Image.new("RGB", (2 * TW + 48, H), (22, 22, 22))
    d = ImageDraw.Draw(S)
    d.text((16, 12), "%s   before = v1.10.61 (left)   after = v1.10.62 (right)" % res, font=F, fill=(240, 225, 190))
    y = 44
    for lab, (i0, i1) in rows:
        d.text((16, y), lab, font=F2, fill=(255, 210, 150))
        S.paste(i0, (16, y + 22))
        S.paste(i1, (32 + TW, y + 22))
        y += i0.height + 34
    p = os.path.join(out, "audit62_%s.jpg" % res)
    S.save(p, quality=88)
    return p


def whole(res, label):
    b, a = shot("after", res), shot("v62", res)
    if a is None:
        return None
    W = 900
    ims = [(im if im is not None else Image.new("RGB", a.size, (40, 0, 0))) for im in (b, a)]
    ims = [im.resize((W, int(im.height * W / im.width)), Image.LANCZOS) for im in ims]
    S = Image.new("RGB", (2 * W + 48, ims[0].height + 60), (22, 22, 22))
    d = ImageDraw.Draw(S)
    d.text((16, 12), "%s   before = v1.10.61 | after = v1.10.62" % label, font=F, fill=(240, 225, 190))
    S.paste(ims[0], (16, 44))
    S.paste(ims[1], (32 + W, 44))
    p = os.path.join(out, "whole62_%s.jpg" % res)
    S.save(p, quality=88)
    return p


print(pair_sheet("1080", 1.0), pair_sheet("720", 720 / 1080))
print(whole("219", "1920x804 (21:9)"), whole("43", "1440x1080 (4:3, wide layout)"), whole("43c", "1440x1080 (4:3, ui_menuCenter 1)"))

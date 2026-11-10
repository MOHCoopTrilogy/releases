"""audit_sheet.py <runs dir> <out.jpg> [notes.json] - numbered 100 % crops of every prop in the attic home view and its zooms
(radio shelf, New Game map), each captioned with its source and the problems found (notes.json: {"<n>": "text"})."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

runs, out = sys.argv[1], sys.argv[2]
notes = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
H = os.path.join(runs, "sv_after_1080", "sv_after_1080_00idle.tga")
SH = os.path.join(runs, "sv_after_1080", "sv_after_1080_20shelf.tga")
MP = os.path.join(runs, "sv_after_1080", "sv_after_1080_30map.tga")
PROPS = [  # n, label, image, box (1080p)
    (1, "work table + papers (stock models)", H, (0, 760, 600, 1080)),
    (2, "safe, filing cabinet, typewriter", H, (180, 520, 400, 700)),
    (3, "radio shelf, home view (baked)", H, (490, 460, 840, 610)),
    (4, "crates + jerrycan under the radio table (baked)", H, (530, 610, 810, 700)),
    (5, "green desk lamps (baked)", H, (980, 520, 1110, 700)),
    (6, "long desk: trays, papers, mug, stamp (baked)", H, (960, 590, 1200, 800)),
    (7, "card-index box (baked)", H, (1080, 660, 1210, 750)),
    (8, "film reels on the desk (baked)", H, (1180, 760, 1340, 880)),
    (9, "telephones + leather case (baked, recoloured)", H, (1040, 530, 1400, 710)),
    (10, "projector (baked, own atlas)", H, (1390, 570, 1560, 790)),
    (11, "windsor chair, mid floor (baked)", H, (740, 660, 900, 810)),
    (12, "chair, far right (baked)", H, (1620, 700, 1820, 820)),
    (13, "clock, rota, notice board, wall phone", H, (1110, 340, 1330, 580)),
    (14, "rifle rack (baked)", H, (1110, 390, 1180, 560)),
    (15, "fan + the two doors (baked)", H, (1320, 340, 1520, 650)),
    (16, "hanging chalk sign (baked chalk boards)", H, (640, 240, 930, 380)),
    (17, "ceiling lamps, green shades (baked)", H, (360, 300, 660, 420)),
    (18, "wall map (re-baked theatre map)", H, (580, 170, 920, 470)),
    (19, "gramophone corner (stock models)", H, (580, 750, 980, 1060)),
    (20, "radio shelf close-up (baked radio atlas)", SH, (300, 300, 1650, 900)),
    (21, "New Game wall map close-up", MP, (300, 60, 1500, 1000)),
]
F = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 22)
F2 = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 18)
TW = 600
cells = []
for n, lab, src, box in PROPS:
    im = Image.open(src).convert("RGB").crop(box)
    s = min(TW / im.width, 420 / im.height, 2.0)
    cells.append((n, lab, im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)))
cols = 3
rows = (len(cells) + cols - 1) // cols
CH = 420 + 120
S = Image.new("RGB", (cols * (TW + 16) + 16, rows * CH + 16), (22, 22, 22))
d = ImageDraw.Draw(S)
for i, (n, lab, im) in enumerate(cells):
    x, y = 16 + (i % cols) * (TW + 16), 16 + (i // cols) * CH
    S.paste(im, (x, y))
    d.text((x, y + 425), "%d. %s" % (n, lab), font=F, fill=(240, 225, 190))
    note = notes.get(str(n), "")
    words, line, ly = note.split(), "", y + 452
    for w in words:
        if len(line) + len(w) > 62:
            d.text((x, ly), line, font=F2, fill=(255, 150, 120))
            line, ly = "", ly + 20
        line += w + " "
    d.text((x, ly), line, font=F2, fill=(255, 150, 120))
S.save(out, quality=88)
print(out, S.size)

"""make_sheet.py <out jpg>: BEFORE / AFTER contact sheet for the HD hold-progress ring.
Per action and per background (bright = m3l2 courtyard, dark = m1l1 train car) four cells:
  BEFORE 1080p (native-pixel crop) | AFTER 1080p (native-pixel crop) | BEFORE 4x (nearest-neighbour) | AFTER 4x
Frames: /g/mohaa-hdring-out/hd_{old,new}_<map>/{old,hd}_<scene>.tga (engine `screenshot`, 1920x1080, lossless).
The 1080p cells are crops, not downscales, so the pixels are the engine's own; the 4x cells are 150x85 regions blown up 4x."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
ROOT = r"G:\mohaa-hdring-out"
CW, CH = 600, 340
# action -> (label, scene, before 1x centre, after 1x centre, before 4x centre, after 4x centre)
ACTIONS = [
    ("DBNO bleed-out ring (70 % left)", "ringa", (960, 540), (960, 540), (1001, 553), (1001, 553)),
    ("DBNO bleed-out ring (22 % left)", "ringb", (960, 540), (960, 540), (911, 531), (911, 531)),
    ("Heal (self / teammate)", "heal", (960, 900), (960, 540), (975, 962), (944, 588)),
    ("Revive", "revive", (960, 900), (960, 540), (975, 962), (989, 580)),
    ("Place / remove sandbag", "place", (960, 960), (960, 540), (1003, 994), (926, 576)),
    ("Objective (sabotage / plant)", "objective", (960, 900), (960, 540), (960, 962), (960, 590)),
    ("Weapon pickup hold", "pickup", (960, 740), (960, 540), (930, 760), (944, 588)),
]
BLOCKS = [("BRIGHT  (m3l2 courtyard)", "m3l2"), ("DARK  (m1l1 train car)", "m1l1")]


def crop(im, c, w, h):
    x0 = int(min(max(c[0] - w // 2, 0), im.width - w))
    y0 = int(min(max(c[1] - h // 2, 0), im.height - h))
    return im.crop((x0, y0, x0 + w, y0 + h))


def find_fill(im, rgb, tol=40):
    """right end of the old flat bar's fill: the bbox of pixels within tol of its script colour, bottom half only"""
    px = im.load()
    xs, ys = [], []
    for y in range(700, im.height, 2):
        for x in range(0, im.width, 2):
            p = px[x, y]
            if abs(p[0] - rgb[0]) < tol and abs(p[1] - rgb[1]) < tol and abs(p[2] - rgb[2]) < tol:
                xs.append(x); ys.append(y)
    return (max(xs) - 30, (min(ys) + max(ys)) // 2) if len(xs) > 30 else None


def load(look, mp, scene):
    f = os.path.join(ROOT, "hd_%s_%s" % ("old" if look == "old" else "new", mp), "%s_%s.tga" % ("old" if look == "old" else "hd", scene))
    return Image.open(f).convert("RGB")


try:
    font = ImageFont.truetype("arial.ttf", 22)
    big = ImageFont.truetype("arial.ttf", 28)
except OSError:
    font = big = ImageFont.load_default()

rows = len(ACTIONS) * len(BLOCKS)
HEAD = 52
W = CW * 4 + 5 * 6
H = HEAD + len(BLOCKS) * 44 + rows * (CH + 6) + 20
sheet = Image.new("RGB", (W, H), (24, 24, 26))
d = ImageDraw.Draw(sheet)
y = 8
for i, t in enumerate(("BEFORE  1080p", "AFTER  1080p", "BEFORE  4x", "AFTER  4x")):
    d.text((6 + i * (CW + 6) + 8, y), t, fill=(240, 232, 214), font=big)
y = HEAD
for bl, mp in BLOCKS:
    d.rectangle((0, y, W, y + 38), fill=(48, 46, 40))
    d.text((12, y + 6), bl, fill=(255, 168, 51), font=big)
    y += 44
    for lab, sc, b1, a1, b4, a4 in ACTIONS:
        old, new = load("old", mp, sc), load("hd", mp, sc)
        b4 = b4
        col = {"heal": (26, 230, 26), "revive": (26, 230, 26), "place": (26, 230, 26), "objective": (230, 191, 51)}.get(sc)
        if col:
            f = find_fill(old, col)
            if f:
                b4 = f
                b1 = (960, min(f[1] + 20, 960))
        cells = [crop(old, b1, CW, CH), crop(new, (1030, a1[1]), CW, CH),
                 crop(old, b4, CW // 4, CH // 4).resize((CW, CH), Image.NEAREST),
                 crop(new, a4, CW // 4, CH // 4).resize((CW, CH), Image.NEAREST)]
        for i, c in enumerate(cells):
            sheet.paste(c, (6 + i * (CW + 6), y))
        d.rectangle((6, y, 6 + 360, y + 28), fill=(0, 0, 0))
        d.text((12, y + 3), lab, fill=(240, 232, 214), font=font)
        y += CH + 6
sheet.save(OUT, quality=93)
sheet.save(OUT.replace(".jpg", ".png"))
print(OUT, sheet.size, os.path.getsize(OUT) // 1024, "KB")

"""make_crops.py <runs dir> <out.jpg> - before | after 100 % crops of each fixed defect (the contact sheets are too small for them)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv, (runs, out) = sys.argv[:1], sys.argv[1:3]
import attic_run as A  # noqa: E402
import mphub_run as M  # noqa: E402

ncam, nhot, nbox = M.scene_info(M.urc("hzm_newgame3d.urc"), "ngscene")
sx, sy = M.hot_px(ncam, nhot["sicily"], None, 1920, 1080)
CROPS = [  # label, run res, shot, box
    ("D-A2 theme box -> the gramophone corner", "1080", "00idle", (300, 620, 1100, 1080)),
    ("D-A6 ghost \"X\" lettering on the floor left of the chair (plank texture streak)", "1080", "00idle", (520, 680, 800, 800)),
    ("D-A3 / A3b telephones: plastics -> bakelite, teal chrome", "1080", "00idle", (1050, 450, 1700, 750)),
    ("D-A4 roof speck", "1080", "00idle", (0, 170, 300, 330)),
    ("D-A1 phantom chair / phone shadow (21:9)", "219", "00idle", (1480, 430, 1920, 804)),
    ("D-A5 hover glow (records desk)", "1080", "14_records", (560, 560, 1360, 1000)),
    ("D-N2 / N4 New Game tag + caption", "1080", "32_sicily", (sx - 260, sy - 110, sx + 260, sy + 130)),
]
F = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 20)
rows = []
for lab, res, shot, box in CROPS:
    pair = []
    for tag in ("before", "after"):
        p = os.path.join(runs, "sv_%s_%s" % (tag, res), "sv_%s_%s_%s.tga" % (tag, res, shot))
        pair.append(Image.open(p).convert("RGB").crop(tuple(int(v) for v in box)) if os.path.exists(p) else None)
    if all(pair):
        rows.append((lab, pair))
W = max(p[0].width * 2 + 36 for _, p in rows)
H = sum(p[0].height + 44 for _, p in rows) + 12
S = Image.new("RGB", (W, H), (22, 22, 22))
d = ImageDraw.Draw(S)
y = 8
for lab, (b, a) in rows:
    d.text((12, y), lab + "   (before | after, 100 %)", font=F, fill=(235, 225, 200))
    S.paste(b, (12, y + 30))
    S.paste(a, (24 + b.width, y + 30))
    y += b.height + 44
S.save(out, quality=90)
print(out, S.size, len(rows))

"""fit4_sheet.py <runDir> <jobs.json> <out.jpg> - contact sheet of the REAL armory slot card per gun (slot per class) from the verify run + measured stats."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit2_lib as L
D, JF, OUT = sys.argv[1:4]
J = json.load(open(JF))
SX, SY = 1.5, 1.125
base = np.asarray(Image.open(os.path.join(D, "fit_000.jpg")).convert("RGB")).astype(int)
tiles, stats = [], []
for nm, tik, lab, xt, xw, pid, sl in J:
    p = os.path.join(D, "fit_%s.jpg" % nm)
    if not os.path.isfile(p):
        continue
    im = Image.open(p).convert("RGB")
    a = np.asarray(im).astype(int)
    off = 76 * (int(sl) - 1)
    th = (int(L.BX * SX), int((L.BY + off) * SY), int((L.BX + L.BW) * SX), int((L.BY + L.BH + off) * SY))
    m = L.mask(a[th[1]:th[3], th[0]:th[2]], base[th[1]:th[3], th[0]:th[2]])
    ys, xs = np.nonzero(m)
    if len(xs) > 12:
        w, h = (xs.max() - xs.min() + 1) / m.shape[1], (ys.max() - ys.min() + 1) / m.shape[0]
        cx, cy = (xs.min() + xs.max()) / 2 / m.shape[1], (ys.min() + ys.max()) / 2 / m.shape[0]
        stats.append((nm, round(cx, 2), round(cy, 2), round(w, 2), round(h, 2)))
    else:
        stats.append((nm, None))
    card = im.crop((int(153 * SX), int((41 + off) * SY), int(301 * SX), int((117 + off) * SY)))
    ImageDraw.Draw(card).text((3, 2), nm, fill=(255, 235, 80))
    tiles.append(card)
cols = 8
tw, th_ = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * th_), (0, 0, 0))
for n, t in enumerate(tiles):
    sheet.paste(t, ((n % cols) * tw, (n // cols) * th_))
sheet.save(OUT, quality=85)
print(sheet.size, os.path.getsize(OUT))
bad = [s for s in stats if s[1] is None or abs(s[1] - .5) > .06 or abs(s[2] - .5) > .08 or max(s[3] / .88, s[4] / .8) > 1.12 or max(s[3] / .88, s[4] / .8) < .75]
print("outliers", len(bad), bad)
json.dump(stats, open(os.path.join(os.path.dirname(OUT), "fit_v2_stats.json"), "w"))

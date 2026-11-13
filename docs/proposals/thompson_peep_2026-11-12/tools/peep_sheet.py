"""peep_sheet.py - contact sheet: one in-game ADS still per Thompson variant + a 3x crop of the sight picture.

    python peep_sheet.py <out.jpg> <label>=<still.jpg>[|<label2>=<still2.jpg>] ...

Each argument is one row; `|` puts a second (after) still beside the first. The red tick marks the screen centre (where
the bullet goes); it is drawn on the sheet, not in the game.
"""
import sys
from PIL import Image, ImageDraw

TW = 560                     # full-frame thumbnail width
CW = 420                     # 3x crop tile width


def tile(path, label):
    im = Image.open(path).convert('RGB')
    W, H = im.size
    th = im.resize((TW, int(TW * H / W)))
    cw, ch = W // 6, int(W // 6 * 0.75)
    crop = im.crop((W // 2 - cw // 2, H // 2 - ch // 2, W // 2 + cw // 2, H // 2 + ch // 2)).resize((CW, int(CW * 0.75)), Image.LANCZOS)
    for I in (th, crop):
        d = ImageDraw.Draw(I); w, h = I.size
        d.line([(w / 2 - 7, h / 2), (w / 2 - 3, h / 2)], fill=(255, 40, 40)); d.line([(w / 2 + 3, h / 2), (w / 2 + 7, h / 2)], fill=(255, 40, 40))
    hh = max(th.size[1], crop.size[1]) + 22
    t = Image.new('RGB', (TW + CW + 6, hh), (24, 24, 24))
    t.paste(th, (0, 22)); t.paste(crop, (TW + 6, 22))
    ImageDraw.Draw(t).text((4, 4), label, fill=(255, 230, 120))
    return t


rows = []
for a in sys.argv[2:]:
    parts = [p.split('=', 1) for p in a.split('|')]
    ts = [tile(p, l) for l, p in parts]
    r = Image.new('RGB', (sum(t.size[0] for t in ts) + 8 * (len(ts) - 1), max(t.size[1] for t in ts)), (0, 0, 0))
    x = 0
    for t in ts:
        r.paste(t, (x, 0)); x += t.size[0] + 8
    rows.append(r)
S = Image.new('RGB', (max(r.size[0] for r in rows), sum(r.size[1] + 6 for r in rows)), (0, 0, 0))
y = 0
for r in rows:
    S.paste(r, (0, y)); y += r.size[1] + 6
S.save(sys.argv[1], quality=90)
print(sys.argv[1], S.size)

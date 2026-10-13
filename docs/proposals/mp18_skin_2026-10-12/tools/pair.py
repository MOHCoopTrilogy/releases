"""before | after pairs.  python pair.py <tagB> <tagA> <map> <spot> [scale] [views...]
tags are run tags (t2 -> work/shots/t2_before_<map>_..., t2_after_<map>_...). -> work/pair_<map>_<spot>.jpg
python pair.py crop <tagB> <tagA> <map> <spot> <view> x0 y0 x1 y1 [zoom]  -> work/pc_<spot>_<view>.png (1:1 pair)"""
import os, sys
from PIL import Image
PROP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SH = os.path.join(PROP, "work", "shots")


def load(tag, mode, mp, spot, view):
    return Image.open(os.path.join(SH, "%s_%s_%s_%s_%s.png" % (tag, mode, mp, spot, view)))


if sys.argv[1] == "crop":
    tb, ta, mp, spot, view = sys.argv[2:7]
    box = tuple(int(v) for v in sys.argv[7:11])
    zoom = float(sys.argv[11]) if len(sys.argv) > 11 else 1.0
    a = load(tb, "before", mp, spot, view).crop(box); b = load(ta, "after", mp, spot, view).crop(box)
    if zoom != 1.0:
        a = a.resize((int(a.size[0] * zoom), int(a.size[1] * zoom)), Image.LANCZOS); b = b.resize(a.size, Image.LANCZOS)
    s = Image.new("RGB", (a.size[0] * 2 + 6, a.size[1]), (255, 0, 255)); s.paste(a, (0, 0)); s.paste(b, (a.size[0] + 6, 0))
    o = os.path.join(PROP, "work", "pc_%s_%s.png" % (spot, view)); s.save(o); print(o, s.size)
else:
    tb, ta, mp, spot = sys.argv[1:5]
    sc = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
    views = sys.argv[6:] or ["mp18_hip", "mp18_ads", "ground"]
    rows = [(load(tb, "before", mp, spot, v), load(ta, "after", mp, spot, v)) for v in views]
    w, h = int(rows[0][0].size[0] * sc), int(rows[0][0].size[1] * sc)
    s = Image.new("RGB", (w * 2, h * len(rows)))
    for i, (a, b) in enumerate(rows):
        s.paste(a.resize((w, h), Image.LANCZOS), (0, i * h)); s.paste(b.resize((w, h), Image.LANCZOS), (w, i * h))
    o = os.path.join(PROP, "work", "pair_%s_%s.jpg" % (mp, spot)); s.save(o, quality=90); print(o)

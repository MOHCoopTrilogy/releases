"""Quick look contact of one session: python quick.py <prefix e.g. t1_after_m3l2> <spot> [scale]
2 x 2: MP18 hip | MP18 aiming / MP40 hip | ground. -> work/quick_<prefix>_<spot>.jpg
python quick.py crop <png> x0 y0 x1 y1 [out]   1:1 crop -> work/crop_*.png"""
import os, sys
from PIL import Image
PROP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SH = os.path.join(PROP, "work", "shots")
if sys.argv[1] == "crop":
    im = Image.open(os.path.join(SH, sys.argv[2])).crop(tuple(int(x) for x in sys.argv[3:7]))
    o = os.path.join(PROP, "work", sys.argv[7] if len(sys.argv) > 7 else "crop_out.png")
    im.save(o); print(o, im.size)
else:
    pre, spot = sys.argv[1], sys.argv[2]
    sc = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
    names = ["%s_%s_mp18_hip", "%s_%s_mp18_ads", "%s_%s_mp40_hip", "%s_%s_ground"]
    ims = [Image.open(os.path.join(SH, (n % (pre, spot)) + ".png")) for n in names]
    w, h = int(ims[0].size[0] * sc), int(ims[0].size[1] * sc)
    sheet = Image.new("RGB", (w * 2, h * 2))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h), Image.LANCZOS), ((i % 2) * w, (i // 2) * h))
    o = os.path.join(PROP, "work", "quick_%s_%s.jpg" % (pre, spot))
    sheet.save(o, quality=90); print(o)

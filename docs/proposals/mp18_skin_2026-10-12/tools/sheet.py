"""The report sheet + 1:1 crops from the run_mp18.py stills (engine screenshots, 1920x1080).

    python sheet.py <before tag m3l2> <after tag m3l2> <before tag m4l1> <after tag m4l1>
-> evidence/mp18_skin_sheet.jpg  (per backdrop: MP18 hip before | after | MP40 hip yardstick, then MP18 aiming
   before | after | on the ground before, after) and evidence/crop_<backdrop>_<view>.jpg (1:1, before | after)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
PROP = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SH = os.path.join(PROP, "work", "shots")
EVI = os.path.join(PROP, "evidence")
TW, TH = 800, 436
HIP = (420, 480, 1520, 1080)        # 1100 x 600
ADS = (0, 240, 1540, 1080)          # 1540 x 840
GRD = (600, 380, 1260, 860)         # 660 x 480
try:
    FONT = ImageFont.truetype("arial.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()


def load(tag, mode, mp, spot, view):
    return Image.open(os.path.join(SH, "%s_%s_%s_%s_%s.png" % (tag, mode, mp, spot, view))).convert("RGB")


def tile(im, box, label, w=TW, h=TH):
    t = im.crop(box).resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(t)
    tw = d.textlength(label, font=FONT)
    d.rectangle([0, 0, tw + 14, 30], fill=(0, 0, 0))
    d.text((7, 3), label, fill=(255, 255, 255), font=FONT)
    return t


def main():
    tb3, ta3, tb4, ta4 = sys.argv[1:5]
    os.makedirs(EVI, exist_ok=True)
    rows = []
    for mp, spot, tb, ta, name in (("m3l2", "light", tb3, ta3, "light wall, day"), ("m3l2", "dark", tb3, ta3, "dark backdrop, day"),
                                   ("m4l1", "night", tb4, ta4, "night map")):
        b = lambda v: load(tb, "before", mp, spot, v)
        a = lambda v: load(ta, "after", mp, spot, v)
        rows.append([tile(b("mp18_hip"), HIP, "MP18 hip - BEFORE - " + name), tile(a("mp18_hip"), HIP, "MP18 hip - AFTER"),
                     tile(a("mp40_hip"), HIP, "MP40 hip (yardstick, same light)")])
        g = Image.new("RGB", (TW, TH), (0, 0, 0))
        g.paste(tile(b("ground"), GRD, "ground - BEFORE", TW // 2 - 2, TH), (0, 0))
        g.paste(tile(a("ground"), GRD, "ground - AFTER", TW // 2 - 2, TH), (TW // 2 + 2, 0))
        rows.append([tile(b("mp18_ads"), ADS, "MP18 aiming - BEFORE"), tile(a("mp18_ads"), ADS, "MP18 aiming - AFTER"), g])
        # 1:1 pairs
        for view, box in (("mp18_hip", (560, 560, 1480, 1080)), ("mp18_ads", (0, 380, 960, 900)), ("ground", GRD)):
            x, y = b(view).crop(box), a(view).crop(box)
            p = Image.new("RGB", (x.size[0] * 2 + 6, x.size[1]), (255, 0, 255)); p.paste(x, (0, 0)); p.paste(y, (x.size[0] + 6, 0))
            p.save(os.path.join(EVI, "crop_%s_%s.jpg" % (spot, view)), quality=92)
    G = 6
    sheet = Image.new("RGB", (TW * 3 + G * 2, len(rows) * TH + (len(rows) - 1) * G), (30, 30, 30))
    for r, row in enumerate(rows):
        for c, t in enumerate(row):
            sheet.paste(t, (c * (TW + G), r * (TH + G)))
    o = os.path.join(EVI, "mp18_skin_sheet.jpg")
    for q in (88, 84, 80, 75):
        sheet.save(o, quality=q)
        if os.path.getsize(o) < 2_900_000:
            break
    print(o, sheet.size, os.path.getsize(o), "q", q)


if __name__ == "__main__":
    main()

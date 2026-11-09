"""before / after sheet of the FG 42 Irons: viewer (base + woodland), Armory hero, hip, ADS, reload, ADS reload, world model
    python compare.py <out.jpg>"""
import os, sys
from PIL import Image, ImageDraw
R = r"H:\hzm_work\wpnviewer\runs"
ROWS = [("viewer", "shots_720_%s", "x_00.jpg", (420, 150, 940, 560)), ("viewer woodland", "shots_720_%s", "x_01.jpg", (420, 150, 940, 560)),
        ("Armory hero", "shots_720_%s", "x_03.jpg", None), ("hip (after a reload)", "fg_%s", "f_07_reload_c.jpg", None), ("ADS", "fg_%s", "f_03_ads.jpg", None),
        ("reload", "fg_%s", "f_06_reload_b.jpg", None), ("ADS reload", "fg_%s", "f_08_adsreload.jpg", None), ("third person", "fg_%s", "f_10_third.jpg", None)]
TAGS = {"shots_720_%s": ("fg42before", "fg42after"), "fg_%s": ("before", "after")}
W, H = 640, 360
sh = Image.new("RGB", (W * 2 + 130, (H + 4) * len(ROWS) + 24), (14, 14, 14))
d = ImageDraw.Draw(sh)
d.text((130 + 4, 4), "BEFORE (v1.10.66 shipped)", fill=(200, 200, 200)); d.text((130 + W + 4, 4), "AFTER (fg42hd)", fill=(255, 210, 90))
for k, (lab, pat, f, crop) in enumerate(ROWS):
    y = 24 + k * (H + 4)
    d.text((4, y + H // 2), lab, fill="yellow")
    for c, tag in enumerate(TAGS[pat]):
        p = os.path.join(R, pat % tag, f)
        if not os.path.isfile(p):
            d.text((130 + c * W + 10, y + 10), "(missing)", fill="red"); continue
        im = Image.open(p).convert("RGB")
        if crop:
            im = im.crop(crop)
        im.thumbnail((W, H))
        sh.paste(im, (130 + c * W, y))
sh.save(sys.argv[1], quality=86)
print("wrote", sys.argv[1], sh.size)

"""make_map_sheet.py <map> - one sheet per map of the side-on contact shots of every surviving spot (media/spots/<map>_<i>.jpg),
captions from spotcheck/<map>.json (z before / after, air under feet, edge, clip)."""
import json, os, sys, re
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__))
mp = sys.argv[1]
res = [r for r in json.load(open(os.path.join(H, "spotcheck", mp + ".json"))) if r["verdict"] == "PASS"]
W, HT, COLS = 640, 360, 3
rows = (len(res) + COLS - 1) // COLS
sheet = Image.new("RGB", (W * COLS, (HT + 22) * max(rows, 1) + 20), (20, 20, 20))
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype("arial.ttf", 14)
lifted = []
for n, r in enumerate(res):
    p = os.path.join(H, "..", "media", "spots", "%s_%d.jpg" % (mp, r["i"]))
    x, y = (n % COLS) * W, (n // COLS) * (HT + 22)
    if os.path.exists(p):
        im = Image.open(p).convert("RGB").resize((W, HT))
        lum = sum(im.convert("L").resize((32, 18)).get_flattened_data()) / (32 * 18) if hasattr(im, "get_flattened_data") else sum(im.convert("L").resize((32, 18)).getdata()) / (32 * 18)
        if lum < 70:
            im = im.point([int(255 * ((i / 255.0) ** 0.5)) for i in range(256)] * 3)
            lifted.append(r["i"])
        sheet.paste(im, (x, y + 22))
    m = re.search(r"z0=(\S+) z1=(\S+) dz=(\S+) air=(\S+)", r["line"])
    d.text((x + 4, y + 3), "%s spot %d  z0 %s -> z1 %s  air %s u  PASS" % (mp, r["i"], m.group(1), m.group(2), m.group(4)) if m else "%s spot %d" % (mp, r["i"]), fill=(255, 255, 255), font=f)
if lifted:
    d.text((4, sheet.height - 18), "tiles %s gamma-lifted (dark night scene)" % lifted, fill=(255, 200, 80), font=f)
out = os.path.join(H, "..", "media", "sheet_spots_%s.jpg" % mp)
sheet.save(out, quality=88)
print(out, sheet.size)

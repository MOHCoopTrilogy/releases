"""contact.py <run dir> <out prefix> [res] - contact sheets of the viewer box of every entry (w_NNN.jpg), labelled from entries.json"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

run, out = sys.argv[1], sys.argv[2]
res = sys.argv[3] if len(sys.argv) > 3 else "720"
W, H = {"720": (1280, 720), "1080": (1920, 1080), "43": (1440, 1080), "219": (1920, 804)}[res]
s = H / 480.0
ox = (W - 640 * s) / 2
box = (int(ox + 172 * s), int(98 * s), int(ox + 462 * s), int(314 * s))
E = {e["n"]: e for e in json.load(open(os.path.join(os.path.dirname(__file__), "..", "entries.json")))}
TW, TH, COLS, ROWS = 232, 196, 10, 6
font = ImageFont.truetype("arial.ttf", 11)
shots = sorted(f for f in os.listdir(run) if f.startswith("w_"))
for p in range(0, len(shots), COLS * ROWS):
    sheet = Image.new("RGB", (COLS * TW, ROWS * TH), (40, 36, 30))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(shots[p:p + COLS * ROWS]):
        n = int(f[2:5])
        im = Image.open(os.path.join(run, f)).crop(box).resize((TW - 4, TH - 34))
        x, y = (i % COLS) * TW, (i // COLS) * TH
        sheet.paste(im, (x + 2, y + 2))
        e = E[n]
        d.text((x + 3, y + TH - 31), "%03d %s" % (n, e["name"][:30]), fill=(240, 225, 190), font=font)
        d.text((x + 3, y + TH - 17), e["variant"][:36], fill=(200, 190, 160), font=font)
    sheet.save("%s_%02d.jpg" % (out, p // (COLS * ROWS) + 1), quality=82)
    print("%s_%02d.jpg" % (out, p // (COLS * ROWS) + 1))

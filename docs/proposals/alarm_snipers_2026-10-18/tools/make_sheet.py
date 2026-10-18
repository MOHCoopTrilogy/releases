"""make_sheet.py <out.jpg> <label:k> ... - contact sheet: per row the close view of sniper k at its spot (left) and the view from the player's place (right).
media/<label>_s<k>_close.jpg and media/<label>_s<k>_player.jpg are written by asn_run.py shots."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
out = sys.argv[1]
rows = [(a.split(":") + [""])[:3] for a in sys.argv[2:]]
W, H = 640, 360
sheet = Image.new("RGB", (W * 2, (H + 22) * len(rows)), (20, 20, 20))
d = ImageDraw.Draw(sheet)
try:
    f = ImageFont.truetype("arial.ttf", 15)
except Exception:
    f = ImageFont.load_default()
for r, (label, k, typ) in enumerate(rows):
    for c, kind in enumerate(("close", "player")):
        p = os.path.join(MEDIA, "%s_s%s_%s.jpg" % (label, k, kind))
        im = Image.open(p).convert("RGB").resize((W, H))
        lum = sum(im.convert("L").resize((32, 18)).getdata()) / (32 * 18)
        if lum < 60:   # night maps: gamma lift so the figure can be judged (rows marked "brightened")
            g = 0.5
            im = im.point([int(255 * ((i / 255.0) ** g)) for i in range(256)] * 3)
            bright = True
        else:
            bright = False
        sheet.paste(im, (c * W, r * (H + 22) + 22))
        d.text((c * W + 6, r * (H + 22) + 3), "%s sniper %s [%s] - %s" % (label, k, typ, ("sniper at its spot (floor visible)" if kind == "close" else "view from the player's place (zoomed)") + (" [gamma-lifted]" if bright else "")), fill=(255, 255, 255), font=f)
sheet.save(out, quality=88)
print("wrote", out, sheet.size)

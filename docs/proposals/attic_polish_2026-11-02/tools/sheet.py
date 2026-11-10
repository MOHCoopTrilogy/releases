"""sheet.py <out.jpg> <cols> <thumb_w> <img> [img ...] - labelled contact sheet (file stem under each frame)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

out, cols, tw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
paths = sys.argv[4:]
ims = [Image.open(p).convert("RGB") for p in paths]
th = max(int(tw * im.height / im.width) for im in ims)
f = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
rows = (len(ims) + cols - 1) // cols
S = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 30) + 8), (24, 24, 24))
d = ImageDraw.Draw(S)
for i, (p, im) in enumerate(zip(paths, ims)):
    x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 30)
    t = im.resize((tw, int(tw * im.height / im.width)), Image.LANCZOS)
    S.paste(t, (x, y))
    d.text((x, y + th + 4), os.path.splitext(os.path.basename(p))[0][-48:], font=f, fill=(220, 220, 200))
S.save(out, quality=88)
print(out, S.size)

"""fit2_sheet.py <dir> <out.jpg> - ONE contact sheet of the armory slot-1 CARD exactly as the menu draws it (frame, title, thumbnail, real name label),
no debug boxes. Only a small yellow gun id in the corner of each tile. Inspect samples: fit_inspect_<id>.jpg are full frames, saved beside it."""
import io, os, sys
from PIL import Image, ImageDraw

D, OUT = sys.argv[1], sys.argv[2]
SX, SY = 1.5, 1.125
CARD = (int(153 * SX), int(41 * SY), int((153 + 148) * SX), int((41 + 76) * SY))   # cardhl1 rect 153 41 148 76
rows = [l.rstrip("\n").split("\t") for l in io.open(r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv", encoding="latin-1") if not l.startswith("#")]
h = rows[0]
ids = [dict(zip(h, r))["id"] for r in rows[1:]]
tiles = []
for i in ids:
    f = os.path.join(D, "fit_%s.jpg" % i)
    if not os.path.isfile(f):
        continue
    im = Image.open(f).convert("RGB").crop(CARD)
    ImageDraw.Draw(im).text((3, 2), i, fill=(255, 235, 80))
    tiles.append(im)
cols = 6
tw, th = tiles[0].size
rowsn = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rowsn * th), (0, 0, 0))
for n, t in enumerate(tiles):
    sheet.paste(t, ((n % cols) * tw, (n // cols) * th))
sheet.save(OUT, quality=82)
print("tiles", len(tiles), "sheet", sheet.size, os.path.getsize(OUT))

"""mk_sheet.py <rundir> <tag> <step> [cols] - contact sheet of <tag>_NNNN.jpg frames (every <step>th) for QA."""
import sys, os, glob
from PIL import Image, ImageDraw
d, tag, step = sys.argv[1], sys.argv[2], int(sys.argv[3])
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 4
fs = sorted(glob.glob(os.path.join(d, tag + "_[0-9][0-9][0-9][0-9].jpg")))[::step]
if not fs:
    print("no frames"); sys.exit(1)
W = int(os.environ.get("SHEETW", "480"))
ims = []
for f in fs:
    im = Image.open(f).convert("RGB"); h = int(im.height * W / im.width); im = im.resize((W, h))
    ImageDraw.Draw(im).text((6, 6), os.path.basename(f)[-8:-4], fill=(255, 255, 0))
    ims.append(im)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rows * ims[0].height))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * W, (i // cols) * ims[0].height))
out = os.path.join(d, tag + "_sheet.jpg"); sheet.save(out, quality=80); print(out, len(ims))

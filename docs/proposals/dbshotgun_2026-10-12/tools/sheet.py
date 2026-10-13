# contact sheet:  python -I tools/sheet.py out.jpg cols cellw img1 img2 ...   (labels = file stems)
import sys, os
from PIL import Image, ImageDraw

out, cols, cw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
files = sys.argv[4:]
ims = []
for f in files:
    im = Image.open(f).convert('RGB')
    h = round(im.height * cw / im.width)
    im = im.resize((cw, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    lab = os.path.splitext(os.path.basename(f))[0]
    d.rectangle([0, 0, 8 + 7 * len(lab), 16], fill=(0, 0, 0))
    d.text((4, 2), lab, fill=(255, 255, 0))
    ims.append(im)
rows = (len(ims) + cols - 1) // cols
ch = max(i.height for i in ims)
sh = Image.new('RGB', (cols * cw, rows * ch), (20, 20, 20))
for n, im in enumerate(ims):
    sh.paste(im, ((n % cols) * cw, (n // cols) * ch))
sh.save(out, quality=88)
print('WROTE', out, sh.size)

"""Labelled sheet of the unlock / armory stills of run_unlock_h.py runs (files unl__<session>__<n>_<name>.jpg).

    python unlsheet.py <out.jpg> [--cols 3] [--w 640] [--crop x0,y0,x1,y1] <session>:<n>_<name>[:label] ...
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('--cols', type=int, default=3); ap.add_argument('--w', type=int, default=640)
ap.add_argument('--crop'); ap.add_argument('items', nargs='+')
a = ap.parse_args()
crop = [int(x) for x in a.crop.split(',')] if a.crop else None
ims = []
for it in a.items:
    p = it.split(':', 2)
    im = Image.open('%s/%s/unl__%s__%s.jpg' % (hv.RUNS, p[0], p[0], p[1])).convert('RGB')
    if crop:
        im = im.crop(crop)
    im = im.resize((a.w, a.w * im.size[1] // im.size[0]), Image.LANCZOS)
    lab = '%s %s' % (p[0], p[2] if len(p) > 2 else p[1])
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 8 + 6 * len(lab), 15), fill=(0, 0, 0)); d.text((4, 2), lab, fill=(255, 255, 0))
    ims.append(im)
w, h = ims[0].size
cols = min(a.cols, len(ims))
S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), (20, 20, 20))
for i, im in enumerate(ims):
    S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(a.out, quality=88)
print(a.out, len(ims), 'cells')

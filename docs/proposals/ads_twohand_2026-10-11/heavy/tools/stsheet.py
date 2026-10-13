"""Labelled sheet of chosen ENGINE frames from one or more lane runs (stance rows, crops), centre box drawn.

    python stsheet.py <out.jpg> [--cols 4] [--w 400] [--crop x0,y0,x1,y1] [--nobox] <sess>:<tag substring>:<frame>[:label] ...
A frame given as +N counts from the capture's `DEMO reload` mark.
"""
import sys, os, re, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('--cols', type=int, default=4); ap.add_argument('--w', type=int, default=400)
ap.add_argument('--crop'); ap.add_argument('--nobox', action='store_true'); ap.add_argument('items', nargs='+')
a = ap.parse_args()
crop = [int(x) for x in a.crop.split(',')] if a.crop else None
logs = {}
ims = []
for it in a.items:
    p = it.split(':', 3)
    sess, sub, fr = p[0], p[1], p[2]
    lab = p[3] if len(p) > 3 else ''
    fs = sorted(glob.glob('%s/%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (hv.RUNS, sess, sub)))
    assert fs, it
    if fr.startswith('+'):
        if sess not in logs:
            logs[sess] = open('%s/%s/qconsole.log' % (hv.RUNS, sess), encoding='latin-1', errors='replace').read()
        tag = os.path.basename(fs[0])[:-10]
        seg = logs[sess][logs[sess].find('ABSCEN begin ' + tag):]
        i = int(re.search(r'DEMO reload (\d+)', seg).group(1)) + int(fr[1:])
    else:
        i = int(fr)
    i = min(i, len(fs) - 1)
    im = Image.open(fs[i]).convert('RGB')
    W, H = im.size
    if not a.nobox:
        ImageDraw.Draw(im).rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0), width=2)
    if crop:
        im = im.crop(crop)
    im = im.resize((a.w, a.w * im.size[1] // im.size[0]), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    txt = '%s %s f%d %s' % (sess, sub.split('__')[0], i, lab)
    d.rectangle((0, 0, 8 + 6 * len(txt), 13), fill=(0, 0, 0)); d.text((3, 1), txt, fill=(255, 255, 255))
    ims.append(im)
cols = min(a.cols, len(ims))
w, h = ims[0].size
S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), 'white')
for k, im in enumerate(ims):
    S.paste(im, ((k % cols) * w, (k // cols) * h))
S.save(a.out, quality=86)
print(a.out, len(ims), 'cells')

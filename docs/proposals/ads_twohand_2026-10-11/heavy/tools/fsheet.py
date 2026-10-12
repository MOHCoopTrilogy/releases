"""Contact sheet of captured engine frames of a lane run, centre box drawn, frame numbers printed.

    python fsheet.py <session> <tag substring> <a:b:step> <out.jpg> [--w 320] [--cols 8] [--crop x0,y0,x1,y1]
"""
import sys, os, glob, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('sess'); ap.add_argument('sub'); ap.add_argument('frames'); ap.add_argument('out')
ap.add_argument('--w', type=int, default=320); ap.add_argument('--cols', type=int, default=8); ap.add_argument('--crop')
a = ap.parse_args()
fs = sorted(glob.glob('%s/%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (hv.RUNS, a.sess, a.sub)))
assert fs, 'no frames'
p = [int(x) for x in a.frames.split(':')]
idx = list(range(p[0], min(p[1], len(fs)), p[2] if len(p) > 2 else 1))
crop = [int(x) for x in a.crop.split(',')] if a.crop else None
ims = []
for i in idx:
    im = Image.open(fs[i]).convert('RGB')
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0), width=2)
    if crop:
        im = im.crop(crop)
    im = im.resize((a.w, a.w * im.size[1] // im.size[0]), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 44, 12), fill=(0, 0, 0)); d.text((2, 0), 'f%d' % i, fill=(255, 255, 255))
    ims.append(im)
cols = min(a.cols, len(ims))
h = ims[0].size[1]
S = Image.new('RGB', (a.w * cols, h * ((len(ims) + cols - 1) // cols)), 'white')
for k, im in enumerate(ims):
    S.paste(im, ((k % cols) * a.w, (k // cols) * h))
S.save(a.out, quality=85)
print(a.out, len(ims), 'frames')

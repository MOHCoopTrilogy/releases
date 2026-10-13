"""Full-resolution crops of a capture's frames (what the GIF shrinks away): is the finger ON the handle, does a hand pop?

    python capcrop.py <session> <tag substring> <out.jpg> --frames 405:431:2 [--crop 300,300,760,720] [--cols 6] [--scale 1.0]
"""
import sys, glob, argparse
from PIL import Image, ImageDraw
RUNS = 'G:/mohaa-adsanim3/runs/'

ap = argparse.ArgumentParser()
ap.add_argument('sess'); ap.add_argument('sub'); ap.add_argument('out'); ap.add_argument('--frames', required=True)
ap.add_argument('--crop', default='300,300,760,720'); ap.add_argument('--cols', type=int, default=6); ap.add_argument('--scale', type=float, default=1.0)
a = ap.parse_args()
fs = sorted(f for f in glob.glob(RUNS + a.sess + '/*%s*__[0-9][0-9][0-9][0-9].jpg' % a.sub))
tags = sorted(set(f.rsplit('__', 1)[0] for f in fs))
assert len(tags) == 1, tags
p = [int(x) for x in a.frames.split(':')] if ':' in a.frames else None
fr = list(range(*p)) if p else [int(x) for x in a.frames.split(',')]
box = tuple(int(x) for x in a.crop.split(','))
ims = []
for k in fr:
    if k >= len(fs):
        break
    im = Image.open(fs[k]).convert('RGB').crop(box)
    if a.scale != 1.0:
        im = im.resize((int(im.width * a.scale), int(im.height * a.scale)))
    ImageDraw.Draw(im).text((4, 4), 'c%d' % k, fill=(255, 255, 0))
    ims.append(im)
W, H = ims[0].size
cols = min(a.cols, len(ims))
S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)))
for i, im in enumerate(ims):
    S.paste(im, ((i % cols) * W, (i // cols) * H))
S.save(a.out, quality=88)
print(a.out, S.size, len(ims), 'frames of', len(fs))

"""Frames of a harness run -> contact sheet + GIF.
    python mkgif.py <frames_dir> <glob-ish prefix> <out_base> [--a N] [--b N] [--step K] [--crop x0,y0,x1,y1 (fractions)] [--w 480] [--cols 6] [--ms 60]
Frames are <prefix>_NNNN.jpg. Writes <out_base>_sheet.jpg and <out_base>.gif (the GIF only with --gif).
"""
import os, sys, re, argparse
from PIL import Image, ImageDraw
import imageio.v2 as iio

ap = argparse.ArgumentParser()
ap.add_argument('dir'); ap.add_argument('prefix'); ap.add_argument('out')
ap.add_argument('--a', type=int, default=0); ap.add_argument('--b', type=int, default=10 ** 6); ap.add_argument('--step', type=int, default=1)
ap.add_argument('--crop', default='0,0,1,1'); ap.add_argument('--w', type=int, default=480); ap.add_argument('--cols', type=int, default=6)
ap.add_argument('--ms', type=int, default=60); ap.add_argument('--gif', action='store_true'); ap.add_argument('--sheetstep', type=int, default=0)
ap.add_argument('--label', action='store_true')
a = ap.parse_args()
fr = {}
for f in os.listdir(a.dir):
    m = re.match(re.escape(a.prefix) + r'_+(\d{4})\.jpg$', f)
    if m:
        fr[int(m.group(1))] = os.path.join(a.dir, f)
idx = [i for i in sorted(fr) if a.a <= i <= a.b][::a.step]
print(len(fr), 'frames found,', len(idx), 'used')
cr = [float(x) for x in a.crop.split(',')]
ims = []
for i in idx:
    im = Image.open(fr[i]).convert('RGB')
    W, H = im.size
    im = im.crop((int(W * cr[0]), int(H * cr[1]), int(W * cr[2]), int(H * cr[3])))
    im = im.resize((a.w, int(im.size[1] * a.w / im.size[0])), Image.LANCZOS)
    if a.label:
        ImageDraw.Draw(im).text((4, 3), 'f%d' % i, fill=(255, 255, 0))
    ims.append(im)
ss = a.sheetstep or 1
sh = ims[::ss]
cols = min(a.cols, len(sh))
rows = (len(sh) + cols - 1) // cols
S = Image.new('RGB', (sh[0].size[0] * cols, sh[0].size[1] * rows))
for k, im in enumerate(sh):
    S.paste(im, ((k % cols) * im.size[0], (k // cols) * im.size[1]))
S.save(a.out + '_sheet.jpg', quality=88)
print('sheet', S.size)
if a.gif:
    iio.mimsave(a.out + '.gif', [__import__('numpy').asarray(im) for im in ims], duration=a.ms / 1000.0, loop=0)
    print('gif', a.out + '.gif', len(ims), 'frames', os.path.getsize(a.out + '.gif') // 1024, 'KB')

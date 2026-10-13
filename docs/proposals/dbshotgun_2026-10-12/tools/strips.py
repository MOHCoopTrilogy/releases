"""rows of cropped frames from one run, one row per capture tag:
    python tools/strips.py <session> out.jpg [--crop x0,y0,x1,y1] [--w 300] tag:start:stop:step [tag:start:stop:step ...]"""
import sys, glob, os
from PIL import Image, ImageDraw
import dbslib as L

a = sys.argv[1:]
sess, out = a.pop(0), a.pop(0)
crop = None; w = 300
while a and a[0].startswith('--'):
    k = a.pop(0); v = a.pop(0)
    if k == '--crop':
        crop = tuple(int(x) for x in v.split(','))
    elif k == '--w':
        w = int(v)
rows = []
for spec in a:
    tag, s0, s1, st = spec.split(':')
    fs = sorted(glob.glob('%s/%s/%s__[0-9]*.jpg' % (L.RUNS, sess, tag)))
    ims = []
    for i in range(int(s0), min(int(s1), len(fs)), int(st)):
        im = Image.open(fs[i]).convert('RGB')
        if crop:
            im = im.crop(crop)
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        ImageDraw.Draw(im).text((4, 2), '%s %d' % (tag.split('__')[-1] if '__' in tag else tag, i), fill=(255, 255, 0))
        ims.append(im)
    if ims:
        rows.append(ims)
W = max(len(r) for r in rows) * w; H = sum(r[0].height for r in rows)
sh = Image.new('RGB', (W, H), (20, 20, 20)); y = 0
for r in rows:
    for k, im in enumerate(r):
        sh.paste(im, (k * w, y))
    y += r[0].height
sh.save(out, quality=86)
print('wrote', out, sh.size)

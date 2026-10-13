"""One sheet of chosen capture frames from several guns / tags of a run, the centre box drawn.

    python picks.py <session> <out.jpg> <tag substring>:f,f,f [...] [--w 300] [--crop x0,y0,x1,y1] [--cols 8]
"""
import sys, os, glob
from PIL import Image, ImageDraw
RUNS_DIR = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')
args = [a for a in sys.argv[1:]]
w, crop, cols = 300, (340, 160, 940, 720), 8
for o in ('--w', '--crop', '--cols'):
    if o in args:
        i = args.index(o); v = args[i + 1]; del args[i:i + 2]
        if o == '--w':
            w = int(v)
        elif o == '--cols':
            cols = int(v)
        else:
            crop = tuple(int(x) for x in v.split(','))
sess, out = args[0], args[1]
tiles = []
for spec in args[2:]:
    sub, fr = spec.split(':')
    for f in fr.split(','):
        g = glob.glob('%s/%s/*%s*__%04d.jpg' % (RUNS_DIR, sess, sub, int(f)))
        if not g:
            print('missing', sub, f); continue
        im = Image.open(g[0]).convert('RGB')
        W, H = im.size
        ImageDraw.Draw(im).rectangle([W * 0.4, H * 0.4, W * 0.6, H * 0.6], outline=(255, 230, 0), width=2)
        t = im.crop(crop).resize((w, w * (crop[3] - crop[1]) // (crop[2] - crop[0])))
        ImageDraw.Draw(t).text((3, 2), '%s f%s' % (sub.replace('__yaw160', ''), f), fill=(255, 255, 0))
        tiles.append(t)
th = tiles[0].size[1]
rows = (len(tiles) + cols - 1) // cols
sh = Image.new('RGB', (w * cols, th * rows), (40, 40, 40))
for i, t in enumerate(tiles):
    sh.paste(t, ((i % cols) * w, (i // cols) * th))
sh.save(out, quality=84)
print(out, sh.size)

"""One sheet per gun of a run_2h `reloads` session: rows = stances, columns = chosen capture frames of the aimed reload
(the frames a look needs: hand leaving, magazine / work low, seat, action, return), the centre box drawn.

    python stsheet.py <session> <gun> <out.jpg> [--stances crouch,prone,standL,standR,braced] [--frames 30,60,85,105,120,150]
                      [--empty] [--w 240] [--crop x0,y0,x1,y1]
"""
import sys, os, glob, argparse
from PIL import Image, ImageDraw
RUNS_DIR = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')
ap = argparse.ArgumentParser()
ap.add_argument('sess'); ap.add_argument('gun'); ap.add_argument('out')
ap.add_argument('--stances', default='crouch,prone,standL,standR,braced'); ap.add_argument('--frames', default='30,60,85,105,120,150')
ap.add_argument('--empty', action='store_true'); ap.add_argument('--w', type=int, default=240); ap.add_argument('--crop', default='240,120,1040,720')
a = ap.parse_args()
x0, y0, x1, y1 = [int(v) for v in a.crop.split(',')]
fr = [int(v) for v in a.frames.split(',')]
sts = a.stances.split(',')
th = a.w * (y1 - y0) // (x1 - x0)
sh = Image.new('RGB', (a.w * len(fr), th * len(sts)), (40, 40, 40))
miss = 0
for r, st in enumerate(sts):
    fs = sorted(glob.glob('%s/%s/ab__%s__%s__%s%s__reload__after__*.jpg' % (RUNS_DIR, a.sess, a.sess, a.gun, st, 'E' if a.empty else '')))
    idx = {int(os.path.basename(f)[:-4].rsplit('__', 1)[1]): f for f in fs}
    for c, k in enumerate(fr):
        if not idx:
            miss += 1; continue
        kk = min(idx, key=lambda v: abs(v - k))
        im = Image.open(idx[kk]).convert('RGB')
        W, H = im.size
        d = ImageDraw.Draw(im); d.rectangle([W * 0.4, H * 0.4, W * 0.6, H * 0.6], outline=(255, 230, 0), width=2)
        t = im.crop((x0, y0, x1, y1)).resize((a.w, th))
        ImageDraw.Draw(t).text((3, 2), '%s%s f%d' % (st, 'E' if a.empty else '', kk), fill=(255, 255, 0))
        sh.paste(t, (c * a.w, r * th))
sh.save(a.out, quality=82)
print(a.out, sh.size, 'missing', miss)

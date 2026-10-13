"""Every stance of one gun's aimed EMPTY reload on one sheet (a row per stance): the magazine going out, the new one
shown, the seat, the hand on the handle, mid pull, handle back, settled. Frames are taken from where the reload really
starts in each capture (the probe's anim field, as reloadbox.py). The sheet is what gets LOOKED AT per stance.

    python stancesheet.py <session> <harness gun key> <out.jpg> [--at 33,68,95,116,122,130,150] [--scale 0.3] [--case E]
"""
import sys, os, re, argparse
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reloadbox as RBX

ap = argparse.ArgumentParser()
ap.add_argument('sess'); ap.add_argument('gun'); ap.add_argument('out'); ap.add_argument('--at', default='33,68,95,116,122,130,150')
ap.add_argument('--scale', type=float, default=0.3); ap.add_argument('--case', default='E')
a = ap.parse_args()
at = [int(x) for x in a.at.split(',')]
rows = []
for ln in open(RBX.RUNS + a.sess + '/qconsole.log', encoding='latin-1', errors='replace'):
    m = re.search(r'ABSCEN end (ab__%s__%s__(\w*?)ads%s__demo__after)' % (re.escape(a.sess), re.escape(a.gun), a.case), ln)
    if not m or 'echo' in ln:
        continue
    stance = m.group(2) or 'stand'
    run, tag, marks, prow, fs = RBX.load(a.sess, '%s__%sads%s__' % (a.gun, m.group(2), a.case))
    mk = {n: (f, si) for n, f, si in marks}
    import numpy as np
    o = int(round(np.median([si - f for n, f, si in marks])))
    low = mk['lower'][0] if 'lower' in mk else len(fs)
    anim = lambda i: prow[min(len(prow) - 1, max(0, i + o))][1]
    settled = anim(low - 3)
    first = [n for n in marks if n[0] == 'fire'][0][1]
    i1 = low - 1
    while i1 > first and anim(i1) == settled:
        i1 -= 1
    i0 = i1
    while i0 > first and anim(i0 - 1) == anim(i1):
        i0 -= 1
    if i1 - i0 < 100:
        print(stance, 'no reload in this capture - left out')
        continue
    ims = []
    for k in at:
        im = Image.open(fs[min(len(fs) - 1, i0 + k)]).convert('RGB')
        im = im.resize((int(im.width * a.scale), int(im.height * a.scale)))
        ImageDraw.Draw(im).text((4, 3), '%s +%d' % (stance, k), fill=(255, 255, 0))
        ims.append(im)
    rows.append(ims)
W, H = rows[0][0].size
S = Image.new('RGB', (W * len(at), H * len(rows)))
for r, ims in enumerate(rows):
    for c, im in enumerate(ims):
        S.paste(im, (c * W, r * H))
S.save(a.out, quality=85)
print(a.out, S.size, len(rows), 'stances')

"""offline check: the new skd over the shipped one, bone-local side view (x muzzle right, z down) and top view -> build/cmp_side.png"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools"); sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import gen_wpnfix_pak as W
import skd as K
HERE = os.path.dirname(os.path.abspath(__file__))
new = K.read(open(os.path.join(HERE, '..', 'ship', 'models', 'weapons', 'fg42', sys.argv[1] if len(sys.argv) > 1 else 'coop_fg42hd_irons.skd'), 'rb').read())
old = K.read(W.carriers('models/weapons/fg42/coop_fg42_irons.skd')[-1][1])
SC, X0, Z0 = 9, -45, -14
Wd, Hd = int(115 * SC), int(36 * SC)


def draw(dr, m, col, ax, skip=('coop_handle',)):
    for s in m['surfaces']:
        if s['name'] in skip:
            continue
        P = [v['pos'] for v in s['verts']]
        for t in s['tris']:
            pts = [((P[i][0] - X0) * SC, (P[i][ax] - Z0) * SC) for i in t]
            dr.polygon(pts, outline=col)


out = Image.new('RGB', (Wd, Hd * 2), 'white')
for k, ax in enumerate((2, 1)):
    im = Image.new('RGB', (Wd, Hd), 'white'); dr = ImageDraw.Draw(im)
    draw(dr, old, (230, 120, 120), ax); draw(dr, new, (60, 60, 160), ax)
    out.paste(im, (0, k * Hd))
out.save(os.path.join(HERE, '..', 'build', 'cmp_side.png'))
print('ok')

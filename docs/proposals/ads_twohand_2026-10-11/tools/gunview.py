"""The gun mesh alone in its tag frame at given (anim, frame) states: left side, rear (from the eye side), top.
    python gunview.py <tik> <out.jpg> anim:frame [anim:frame ...]      prints bbox of every surface per state
"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
import raster
os.chdir(_c)
PR = V.PR
from PIL import Image, ImageDraw
np.set_printoptions(precision=2, suppress=True)
tik, out = sys.argv[1], sys.argv[2]
W, H = 420, 300
rows = []
for spec in sys.argv[3:]:
    anim, fr = spec.split(':')
    g = PR.gungeo.load_gun(tik, anim=anim, frame=int(fr)) if anim != 'rest' else PR.gungeo.load_gun(tik)
    surfs = [dict(s) for s in g['surfs']]
    for s in surfs:
        print(spec, '%-16s min %s max %s' % (s['name'], s['P'].min(0), s['P'].max(0)))
        s.setdefault('shader', s.get('shader', 'x'))
    c = np.array([4.0, -0.7, -1.0])
    tiles = []
    for label, off, up in (('left side', (0, -30, 0), (0, 0, -1)), ('from the eye (rear, 12 deg above)', (-30, 0, -6), (0, 0, -1)),
                           ('top', (0, 0.01, -30), (1, 0, 0))):
        rgb, ids, dep = raster.render({'surfs': surfs}, c + np.array(off, float), c, np.array(up, float), fov=30, W=W, H=H,
                                      bg=(150, 160, 170), znear=1.0, tex=True)
        im = Image.fromarray(rgb.astype(np.uint8)); ImageDraw.Draw(im).text((4, 4), '%s  %s' % (spec, label), fill=(0, 0, 0))
        tiles.append(im)
    rows.append(tiles)
S = Image.new('RGB', (W * 3, H * len(rows)))
for i, r in enumerate(rows):
    for j, im in enumerate(r):
        S.paste(im, (j * W, i * H))
S.save(out, quality=88); print(out)

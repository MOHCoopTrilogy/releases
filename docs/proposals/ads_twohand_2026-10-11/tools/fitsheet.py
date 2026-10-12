"""Offline fit check of ONE aim clip on several gun meshes that share it: per gun the shooter's eye (that gun's own
sight row = its own rig correction) and a left-side close-up.

    python fitsheet.py <out.jpg> <pose.skc>:<sight gun>[,<sight gun>...] [<pose.skc>:<guns> ...]
"""
import sys, os, json, math
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
import raster
os.chdir(_c)
R = V.R
from PIL import Image, ImageDraw
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
W, H = 420, 236
tiles = []
for spec in sys.argv[2:]:
    clip, guns = spec.split(':')
    a = R.load(clip)
    pd = R.pose_dict(a, a.numFrames - 1)
    for gun in guns.split(','):
        sight = V.SIGHTS[gun]
        corr = V.rig_target(V.evaluate_ctl(pd, CTL), sight)
        surfs, E, Wb = V.scene2(pd, gun, sight['tik'], 'idle', 0.0, CTL, corr)
        rgb, _, _ = V.shade_render(surfs, E, V.weapon_fov(), W, H)
        im1 = Image.fromarray(rgb)
        c = np.vstack([s['P'] for s in surfs if s['name'] == 'triggerhand']).mean(0)
        out = []
        for off in ((0, 22, 2), (16, 16, 4)):
            rgb2, ids, dep = raster.render({'surfs': surfs}, c + np.array(off, float), c, np.array([0, 0, 1.0]), fov=40, W=W, H=H,
                                           bg=(150, 160, 170), znear=1.0, tex=True)
            out.append(Image.fromarray(rgb2.astype(np.uint8)))
        ImageDraw.Draw(im1).text((4, 4), '%s  (%s)' % (gun, os.path.basename(clip)), fill=(0, 0, 0))
        tiles.append([im1] + out)
        print(gun, flush=True)
S = Image.new('RGB', (W * 3, H * len(tiles)), 'white')
for i, row in enumerate(tiles):
    for j, im in enumerate(row):
        S.paste(im, (j * W, i * H))
S.save(sys.argv[1], quality=88)
print(sys.argv[1], S.size)

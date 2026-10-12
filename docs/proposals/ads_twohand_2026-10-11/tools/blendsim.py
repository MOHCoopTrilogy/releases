"""offline look at the hip<->aim crossblend: per-channel nlerp between the hip idle and the aim pose, eye camera of the
aim pose scaled by the blend (approximation: the rig correction is applied with weight w)"""
import sys, os, json, math
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R
from PIL import Image, ImageDraw
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
hipn, aimf, gun, out = sys.argv[1:5]
hip = R.load(R.ANIM + hipn); aim = R.load(aimf)
ph = R.pose_dict(hip, 0); pa = R.pose_dict(aim, aim.numFrames - 1)
sight = V.SIGHTS[gun]
corr = V.rig_target(V.evaluate_ctl(pa, CTL), sight)
W, H = 480, 270
ims = []
for w in (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0):
    s = w * w * (3 - 2 * w)
    pd = {}
    for k in pa:
        a, b = ph.get(k, pa[k]), pa[k]
        if k.endswith(' rot'):
            if a @ b < 0:
                b = -b
            q = (1 - s) * a + s * b
            pd[k] = q / np.linalg.norm(q)
        else:
            pd[k] = (1 - s) * a + s * b
    c = dict(corr); c['ang'] = corr['ang'] * s; c['T'] = corr['T'] * s; c['cant'] = corr['cant'] * s; c['relief'] = corr['relief'] * s
    surfs, E, Wb = V.scene2(pd, gun, sight['tik'], 'idle', 0.0, CTL, c)
    fov = V.weapon_fov(gate=s)
    rgb, _, _ = V.shade_render(surfs, E, fov, W, H)
    im = Image.fromarray(rgb); ImageDraw.Draw(im).text((4, 4), 'blend %.2f' % w, fill=(0, 0, 0))
    ims.append(im)
S = Image.new('RGB', (W * 4, H * 2))
for i, im in enumerate(ims):
    S.paste(im, ((i % 4) * W, (i // 4) * H))
S.save(out, quality=88); print(out)

"""Offline first-person look (the ads_bolt calibrated rig, no game launch): a view clip's frames with a gun tik, textured.
Overlay paks: set IRONSIGHT_EXTRA_PAKS=<pk3> (mkov.py builds one from this worktree's wpnfix sources).
    python vmview.py <view clip (models/human/animation/...)> <tik> <out.jpg> --frames 0,10 [--gunanim idle] [--w 960]
           [--ads <sights key>] [--cmp <second tik>]
"""
import sys, os, math, argparse
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T)
_cwd = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa: E402
os.chdir(_cwd)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
R = V.R
SIDE = 0.0


def frame(c, f, tik, gunanim, W, H, fov, sight=None):
    t = f * c.frameTime
    pd = R.pose_dict(c, f)
    corr = None
    if sight:
        Wb = R.evaluate(pd)
        corr = V.rig_target(Wb, sight)
    surfs, E, Wb = V.scene(pd, tik, gunanim, t, corr=corr)
    if SIDE:   # look at the rig from its RIGHT side (camera on -y looking +y): x' = y, y' = -x, z' = z
        C = np.vstack([s['P'] for s in surfs]).mean(0)
        surfs = [dict(s, P=np.stack([s['P'][:, 1] - C[1] + SIDE, -(s['P'][:, 0] - C[0]), s['P'][:, 2] - C[2]], 1)) for s in surfs]
        E = np.zeros(3)
    rgb, _, _ = V.shade_render(surfs, E, fov, W, H)
    return Image.fromarray(rgb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('clip'); ap.add_argument('tik'); ap.add_argument('out')
    ap.add_argument('--frames', default='0'); ap.add_argument('--gunanim', default='idle')
    ap.add_argument('--w', type=int, default=960); ap.add_argument('--ads'); ap.add_argument('--cmp')
    ap.add_argument('--fov', type=float, default=0); ap.add_argument('--side', type=float, default=0)
    a = ap.parse_args()
    global SIDE
    SIDE = a.side
    c = R.load(a.clip)
    W, H = a.w, a.w * 9 // 16
    fov = a.fov or V.weapon_fov(W, H, gun_zoom=0.0)
    sight = None
    if a.ads and a.ads.endswith('.json'):     # a custom row: {F_root, R_root, up_root, relief, frame_used: root}
        import json
        sight = json.load(open(a.ads))
    elif a.ads:
        sight = V.SIGHTS[a.ads]
    ims = []
    for tik in [a.tik] + ([a.cmp] if a.cmp else []):
        for f in [int(x) for x in a.frames.split(',')]:
            im = frame(c, f, tik, a.gunanim, W, H, fov, sight)
            ImageDraw.Draw(im).text((6, 6), '%s f%d' % (os.path.basename(tik), f), fill=(0, 0, 0))
            ims.append(im)
    cols = min(len(a.frames.split(',')), 4)
    S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * W, (i // cols) * H))
    S.save(a.out, quality=90)
    print(a.out)


if __name__ == '__main__':
    main()

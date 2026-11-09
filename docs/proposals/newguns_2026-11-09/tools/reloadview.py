"""Offline reload frames with the server's ammo prop (vmcam.scene2 + PROP): the gun on the OFF hand inside the attachtohand window,
the prop tik on tag_weapon_right while it is shown, the gun's own magazine surface hidden meanwhile.
    python reloadview.py <view clip> <gun tik> <gun anim> <prop tik> <f0> <f1> <hide surf> <out.jpg> --frames a,b,c [--side D] [--off f0,f1]
"""
import sys, os, argparse
T = r'C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools'
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa
os.chdir(_c)
import numpy as np
from PIL import Image, ImageDraw
R = V.R


def main():
    ap = argparse.ArgumentParser()
    for a in ('clip', 'tik', 'anim', 'prop', 'f0', 'f1', 'hide', 'out'):
        ap.add_argument(a)
    ap.add_argument('--frames', required=True); ap.add_argument('--side', type=float, default=0); ap.add_argument('--w', type=int, default=640)
    ap.add_argument('--off', default='')
    a = ap.parse_args()
    c = R.load(a.clip)
    ft = c.frameTime
    V.PROP.update(tik=a.prop, anim='idle', tag='tag_weapon_right', t0=int(a.f0) * ft, t1=int(a.f1) * ft, hide=a.hide)
    off = tuple(int(x) * ft for x in a.off.split(',')) if a.off else (0.0, c.numFrames * ft)
    W, H = a.w, a.w * 9 // 16
    fov = 45 if a.side else V.weapon_fov(W, H, gun_zoom=0.0)
    ims = []
    for f in [int(x) for x in a.frames.split(',')]:
        t = f * ft
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), 'vickers', a.tik, a.anim, t, None, None, off, None)
        surfs = [s for s in surfs if np.abs(s['P']).max() < 1e3]
        if a.side:
            C = np.vstack([s['P'] for s in surfs]).mean(0)
            surfs = [dict(s, P=np.stack([s['P'][:, 1] - C[1] + a.side, -(s['P'][:, 0] - C[0]), s['P'][:, 2] - C[2]], 1)) for s in surfs]
            E = np.zeros(3)
        rgb, _, _ = V.shade_render(surfs, E, fov, W, H)
        im = Image.fromarray(rgb); ImageDraw.Draw(im).text((4, 4), 'f%d' % f, fill=(0, 0, 0)); ims.append(im)
    cols = min(4, len(ims))
    S = Image.new('RGB', (W * cols, H * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * W, (i // cols) * H))
    S.save(a.out, quality=88); print(a.out)


if __name__ == '__main__':
    main()

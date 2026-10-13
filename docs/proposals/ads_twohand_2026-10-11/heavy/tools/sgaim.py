r"""Offline look at the SHOTGUN's settled aim picture for sight design (the calibrated ADS camera of vmcam, textured):
variants of the sight row (delta, eye relief - unclamped here, the engine clamps the rig's own move to +-4 u) and of the
aim clip, each as a full frame + a 3x crop of the centre.  Staged mesh / tiks / shader come through
IRONSIGHT_EXTRA_PAKS=<overlay pk3> (set it BEFORE running).

    cd heavy/assets; python ../tools/sgaim.py <out.jpg> [--v delta:relief[:label] ...] [--aim clip] [--w 1280]
          [--bg r,g,b] [--info]
    relief = the rig's eye-relief MOVE in units (0 = the animation's own eye, + = the gun pushed away from the eye)
"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--v', action='append'); ap.add_argument('--aim', default='viewmodel/idle_shotgun00.skc')
    ap.add_argument('--w', type=int, default=1280); ap.add_argument('--bg', default='150,160,170'); ap.add_argument('--info', action='store_true')
    ap.add_argument('--gun', default='shotgun'); ap.add_argument('--zoom', type=float, default=3.0)
    a = ap.parse_args()
    bg = tuple(int(x) for x in a.bg.split(','))
    aimc = hv.staged('models/human/animation/' + a.aim)
    aim = R.load(aimc if os.path.isfile(aimc) else R.ANIM + a.aim)
    pd = R.pose_dict(aim, aim.numFrames - 1)
    W = a.w; Hh = W * 9 // 16
    fov = V.weapon_fov()
    rows = []
    for v in (a.v or ['18:0']):
        p = v.split(':')
        sight = dict(V.SIGHTS[a.gun]); sight['delta_mrad'] = float(p[0])
        corr = V.rig_target(V.evaluate_ctl(pd, CTL), sight)
        corr['relief'] = float(p[1])
        surfs, E, Wb = V.scene2(pd, a.gun, sight['tik'], 'idle', 0.0, CTL, corr, None)
        if a.info:
            Fc = V.apply_corr(np.atleast_2d(corr['F'] - 0), corr)[0]; Rc = V.apply_corr(np.atleast_2d(corr['R']), corr)[0]
            print('%s: eye->F %.2f u, eye->R %.2f u (along the view), F %.2f / R %.2f u below the axis' % (v, (Fc - E)[0], (Rc - E)[0], -(Fc - E)[2], -(Rc - E)[2]))
        rgb, ids, _ = V.shade_render(surfs, E, fov, W, Hh, bg=bg)
        im = Image.fromarray(rgb)
        z = a.zoom
        BW = int(W * z); BH = BW * 9 // 16
        rgb2, _, _ = V.shade_render(surfs, E, fov, BW, BH, bg=bg)
        c = Image.fromarray(rgb2).crop(((BW - W) // 2, (BH - Hh) // 2, (BW + W) // 2, (BH + Hh) // 2))
        ImageDraw.Draw(im).rectangle((int(W * 0.4), int(Hh * 0.4), int(W * 0.6), int(Hh * 0.6)), outline=(255, 230, 0))
        lab = p[2] if len(p) > 2 else 'delta %s mrad, relief move %s u' % (p[0], p[1])
        ImageDraw.Draw(im).text((6, 6), lab, fill=(0, 0, 0))
        ImageDraw.Draw(c).text((6, 6), 'centre %gx' % z, fill=(0, 0, 0))
        row = Image.new('RGB', (W * 2, Hh)); row.paste(im, (0, 0)); row.paste(c, (W, 0))
        rows.append(row)
    S = Image.new('RGB', (W * 2, Hh * len(rows)))
    for i, r in enumerate(rows):
        S.paste(r, (0, i * Hh))
    if S.size[0] > 2560:
        S = S.resize((2560, S.size[1] * 2560 // S.size[0]), Image.LANCZOS)
    S.save(a.out, quality=88)
    print(a.out)


if __name__ == '__main__':
    main()

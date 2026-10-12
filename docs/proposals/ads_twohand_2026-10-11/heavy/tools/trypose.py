"""Try gun WORK POSES offline: the aim pose with the gun moved in the camera frame (hold_bake's 5-DOF `dip`: drop u,
roll deg (+ = top to the right), pitch deg (+ = muzzle down), side u (+ = left), back u; about a pivot `pv` u down the
sight line - negative = behind the eye, e.g. the butt in the shoulder), both hands riding the gun in their aim grip.
One eye-view cell per variant with the centre box and the EXTRA box cover against the settled aim.

    cd heavy/assets; python ../tools/trypose.py <prefix> <out.jpg> [--pv -8] [--aim clip] [--lhand off] d,r,p,s,b [d,r,p,s,b ...]
"""
import sys, os, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
from PIL import Image, ImageDraw
import handpose


def grow(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return o


def pose_clip(p, aim, dip, pv, lhand=True, gun_anim=None, T=None):
    """-> pose dict of the aim pose with the gun moved by `dip` (5-DOF) or put at the gun_abs pose T"""
    g = hv.GUNS[p]
    rows = H.fps_rows()
    rc = H.auto_recipe(g['idle'], gun=g['sight'], charge=aim, enter=0, exit=0, fixed_right=True, weight=dict(on=False),
                       handover=False, free_tag=False, dip={0: tuple(dip), 1: tuple(dip)}, dip_pivot=pv)
    if T is not None:
        rc['gun_abs'] = dict(T=T, keys={0: 1.0, 1: 1.0})
    rc['hip'] = rows[g['idle']]
    k = dict(aim=1, fing='pose') if lhand else dict(cam=(5.0, 9.0, -15.0), rot='aim', fing='pose')
    rc['left_path'] = {0: k, 1: k}
    H.RECIPES[g['idle']] = rc
    sk, _ = H.bake(g['idle'], CTL)
    return sk


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('out'); ap.add_argument('poses', nargs='+')
    ap.add_argument('--pv', type=float, default=-8.0); ap.add_argument('--aim'); ap.add_argument('--lhand', default='on')
    ap.add_argument('--w', type=int, default=480); ap.add_argument('--cols', type=int, default=3); ap.add_argument('--anim', default='idle'); ap.add_argument('--pivot', default='-10.8,-0.3,-4.0')
    a = ap.parse_args()
    g = hv.GUNS[a.gun]
    aimp = a.aim or hv.staged('models/human/animation/' + handpose.out_clip(a.gun))
    aimp = aimp if os.path.isfile(aimp) else aimp
    aim = R.load(aimp if os.path.isfile(aimp) else R.ANIM + aimp)
    sight = V.SIGHTS[g['sight']]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    W, Hh = a.w, a.w * 9 // 16
    fov = V.weapon_fov()
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(Hh * 0.4), int(Hh * 0.6)
    _, ids, _ = V.shade_render(V.scene2(R.pose_dict(aim, aim.numFrames - 1), g['sight'], sight['tik'], 'idle', 0.0, CTL, corr, None)[0],
                               V.scene2(R.pose_dict(aim, aim.numFrames - 1), g['sight'], sight['tik'], 'idle', 0.0, CTL, corr, None)[1], fov, W, Hh)
    aimmask = grow((ids >= 0)[y0:y1, x0:x1], max(1, int(round(6 * W / 1280.0))))
    ims = []
    aimarg = aimp if not os.path.isfile(aimp) else os.path.relpath(aimp, os.path.join(os.getcwd(), hv.ANIMDIR)).replace(os.sep, '/')
    for ps in a.poses:
        if '=' in ps:                      # roll=55,pitch=4.6,yaw=0,mv=f/l/u  about --pivot x,y,z (camera frame)
            import heavylib as HL
            kv = dict(x.split('=') for x in ps.split(','))
            d = {k: float(v) for k, v in kv.items() if k != 'mv'}
            if 'mv' in kv:
                d['move'] = tuple(float(x) for x in kv['mv'].split('/'))
            T = HL.work_T(aimp, g['sight'], d, tuple(float(x) for x in a.pivot.split(',')))
            sk = pose_clip(a.gun, aimarg, (0, 0, 0, 0, 0), a.pv, a.lhand == 'on', T=T)
        else:
            dip = [float(x) for x in ps.split(',')]
            sk = pose_clip(a.gun, aimarg, dip, a.pv, a.lhand == 'on')
        surfs, E, Wb = V.scene2(R.pose_dict(sk, 0), g['sight'], sight['tik'], a.anim, 0.0, CTL, corr, None)
        rgb, ids, _ = V.shade_render(surfs, E, fov, W, Hh)
        e = float(((ids >= 0)[y0:y1, x0:x1] & ~aimmask).mean())
        im = Image.fromarray(rgb); d = ImageDraw.Draw(im)
        d.rectangle((x0, y0, x1, y1), outline=(255, 230, 0) if e <= 0.02 else (255, 0, 0))
        d.text((4, 4), '%s  %s  extra %.1f %%' % (a.gun, ps, 100 * e), fill=(0, 0, 0))
        ims.append(im)
        print(ps, 'extra %.1f %%' % (100 * e))
    cols = min(a.cols, len(ims))
    S = Image.new('RGB', (W * cols, Hh * ((len(ims) + cols - 1) // cols)), 'white')
    for i, im in enumerate(ims):
        S.paste(im, ((i % cols) * W, (i // cols) * Hh))
    S.save(a.out, quality=88)
    print(a.out)


if __name__ == '__main__':
    main()

"""[2026-10-12, corrected by the user: "reload without losing your target"] the gun STAYS UP IN THE AIM: a dip of well
under a unit and a few degrees of cant while the magazine is swapped, the work happens low (the support hand leaves
downward and returns from below), the centre of the screen stays clear.

Aimed reloads of the MAGAZINE pistols on the two-handed aim (coordinator 2026-10-12: "I cannot see a magazine leave or
enter ... give the pistols the treatment the SMGs got: a small dip / cant so the old magazine dropping and the new one
going in are visible, then back to the exact aim pose").

The firing hand keeps its aim grip (fixed_right, bug-3467). The gun is eased to a WORK pose in front of the face - canted
so the magazine well opens to the lower left - and back onto the sights; the support hand leaves the grip, does the
retail magazine exchange relative to the gun (so the magazine prop and the gun's own slide / magazine animation line up)
and returns to the grip (left_grip). First and last frame = the aim pose exactly.

    python pistolbake.py <gun|all> <out root>        guns: colt45 p38 histandard beretta
"""
import sys, os, json, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
H = RB.H; R = RB.R

D = tuple(float(x) for x in os.environ.get('PB_D', '0.6,5,0,0,0').split(','))        # drop, roll (+ = top to the right), pitch, left, yaw
TAG = [float(x) for x in os.environ.get('PB_TAG', '').split(',') if x] or None     # None = the aim pose's own place (ON TARGET, user 2026-10-12)
WAY = (0.3, -1.6, 0.4)
EW = float(os.environ.get('PB_EW', '0'))
GUNS = {
    # row, sight gun, aim clip, out clip, frames of the gun pose ramp (in0, in1, out0, out1), left_grip (fa, fb, hold)
    'colt45': dict(row='colt45_reload', sight='colt_45', aim='viewmodel/pistol/colt45_ads2h.skc',
                   out='viewmodel/pistol/colt45_reload_ads.skc', ramp=(2, 11, 57, 68), lg=(12, 61, 2),
                   # the slide is locked back through the reload and runs forward at f57-60: the firing thumb drops the slide stop
                   extra=dict(finger_add={'Bip01 R Finger01 rot': [(52, 0.0), (56, 30.0), (60, 30.0), (64, 0.0)],
                                          'Bip01 R Finger02 rot': [(52, 0.0), (56, 18.0), (60, 18.0), (64, 0.0)]})),
    'p38': dict(row='p38_reload', sight='walther_p38', aim='viewmodel/pistol/p38_ads2h.skc',
                out='viewmodel/pistol/p38_reload_ads.skc', ramp=(2, 11, 57, 68), lg=(12, 61, 2)),
    'histandard': dict(row='histandard_reload', sight='hi_standard_silenced', aim='viewmodel/pistol/histandard_ads2h.skc',
                       out='viewmodel/pistol/histandard_reload_ads.skc', ramp=(2, 11, 57, 68), lg=(12, 61, 2)),
    'beretta': dict(row='beretta_reload', sight='beretta', aim='viewmodel/beretta/beretta_ads2h.skc',
                    out='viewmodel/beretta/beretta_reload_ads.skc', ramp=(1, 6, 52, 60), lg=(5, 37, 6),
                    # the gun's own slide runs forward at f48-52 with no hand on it: the firing thumb presses the release
                    extra=dict(finger_add={'Bip01 R Finger01 rot': [(43, 0.0), (47, 30.0), (51, 30.0), (55, 0.0)],
                                           'Bip01 R Finger02 rot': [(43, 0.0), (47, 18.0), (51, 18.0), (55, 0.0)]})),
}


def bake(name, root):
    g = GUNS[name]
    Tw = RB.work_T(g['aim'], g['sight'], D, TAG)
    a, b, c, d = g['ramp']
    hip = R.load(R.ANIM + H.fps_rows()[g['row']])
    n = hip.numFrames - 1
    kw = dict(gun=g['sight'], charge=g['aim'], fixed_right=True,
              gun_abs=dict(T=Tw, keys={0: 0.0, a: 0.0, b: 1.0, c: 1.0, d: 0.0, n: 0.0}),
              left_grip=dict(fa=g['lg'][0], fb=g['lg'][1], way=WAY, hold=g['lg'][2], finger_in_pow=2.5), weight=dict(on=False),
              # the firing arm's elbow swings out to the right while the gun is up, so the forearm comes in from the
              # right edge instead of filling the lower right of the frame
              elbow_vec={'R': tuple(float(x) for x in os.environ.get('PB_ELBR', '0,-1,-0.2').split(',')), 'L': (0.0, 0.0, -1.0)},
              elbow_down={'R': [(0, 0.0), (a, 0.0), (b, EW), (c, EW), (d, 0.0), (n, 0.0)]})
    kw.update(g.get('extra', {}))
    rc = H.auto_recipe(g['row'], **kw)
    H.RECIPES[g['row']] = rc
    sk, rep = H.bake(g['row'], RB.CTL)
    bts = R.skc_io.write(sk)
    dst = os.path.join(root, 'models', 'human', 'animation', g['out'].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bts)
    print(name, '->', g['out'], sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])


if __name__ == '__main__':
    for nm in (list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(',')):
        bake(nm, sys.argv[2])

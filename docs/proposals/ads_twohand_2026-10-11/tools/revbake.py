"""Hand-keyed revolver reloads (user 2026-10-12: open as the model opens / dump the cases when empty / one round
from the pouch per _single / close), HIP and AIMED from one choreography.

On top of hold_bake: the firing hand keeps its grip; the GUN is eased to one absolute work pose in the view (lowered
and tipped muzzle-up so the open cylinder's face turns to the eye) - the same pose whether the clip starts at the hip
or on the sights; the support hand is keyed on points of the gun (left_path / gunpt), goes down out of frame to the
pouch for every round and comes back with a cartridge in its fingers (ltag: the prop the server attaches).

    python revbake.py <set> <out root> [--only row]       set = webley_ads | webley_hip
Run from the staging dir (the aim clips are looked up under ./models/human/animation first).
"""
import sys, os, json, argparse, hashlib, copy
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import hold_bake as H
os.chdir(_c)
R = H.R; V = H.V
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))

REFAIM = 'viewmodel/coltpose00.skc'    # the retail aim clip: its left shoulder is low and forward
POUCH = (5.0, 9.0, -15.0)              # camera frame (fwd, left, up): the belt, well under the frame
ELB = 3.0                              # support elbow swung under: the forearm rises from below, not across
ROUND = 'models/ammo/nagant_pistol_shell.tik'


def work_T(aim_clip, gun, D):
    """gun-in-camera (rows, u) at the open-action work pose: the AIMED gun dropped D[0] u, rolled D[1], pitched D[2]
    deg (negative = muzzle up) about a point 12 u down the sight line, shifted D[3] u to the left"""
    a = R.load(R.ANIM + aim_clip)
    pc = R.pose_dict(a, a.numFrames - 1)
    Wc = R.evaluate(pc)
    Wcc = V.evaluate_ctl(pc, CTL)
    corr = V.rig_target(Wcc, V.SIGHTS[gun])
    C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']; C[3, 0:3] *= R.S
    Mcam = C @ V.model_to_cam(corr)
    Rr = R.axis_angle_rows((1, 0, 0), D[1]) @ R.axis_angle_rows((0, 1, 0), D[2])
    pv = 12.0
    P = np.eye(4); P[3, 0:3] = (-pv, 0, 0)
    Q = np.eye(4); Q[0:3, 0:3] = Rr
    Pi = np.eye(4); Pi[3, 0:3] = (pv, D[3] if len(D) > 3 else 0.0, -D[0])
    Gs = Wc['tag_weapon_right'].copy(); Gs[3, 0:3] *= R.S
    return Gs @ Mcam @ (P @ Q @ Pi)


# ------------------------------------------------------------------------------------------------ Webley (top-break)
# points in the weapon-tag frame (u; x forward, y right, z down), read off the mesh (gunview.py)
WEB_C = (9.75, -0.8, -4.4)      # the mouth of the top-left chamber of the OPEN cylinder (its face looks up)
WEB_B = (8.6, -0.75, -2.6)      # the barrel just ahead of the cylinder, gun closed
WEB_BO = (8.4, -0.75, 2.1)      # the same spot with the barrel tipped down (hinge about (6.0, -0.4))
WEB_D = (9.0, 0.0, -42.0, -1.0)
PINCH = ('mix', 4, 0.18)        # fingers: the grip's curl opened a little toward the retail open hand = holding a round
LTAG = dict(pinch=(10.0, 3.0, -2.6), hold=1.0)     # thumb / forefinger pinch point in the hand (pre-scale) + the round below it
SEAT = dict(gunpt=WEB_C, off=(-1.2, 5.4, -2.4), rot='aim', fing=PINCH, pinch_at=1, above=0.5)
LIFT = dict(gunpt=WEB_C, off=(-1.2, 5.4, -2.4), rot='aim', fing=PINCH, pinch_at=1, above=2.6)
ONB = dict(gunpt=WEB_B, off=(-3.0, 3.4, -2.4), rot='aim')
ONBO = dict(gunpt=WEB_BO, off=(-3.0, 3.4, -2.0), rot='aim')


def webley(kind):
    aim2h = 'viewmodel/webley/webley_ads2h.skc'
    Tw = work_T(aim2h, 'webley_revolver', WEB_D)
    common = dict(gun='webley_revolver', fixed_right=True)
    if kind == 'ads':
        common.update(charge=aim2h)
        sh = lambda keys: dict(shoulder_ref=dict(clip=REFAIM, keys=keys))
        out = lambda part: 'viewmodel/webley/webley_%s_ads.skc' % part
    else:
        common.update(charge='viewmodel/nagantrev/idle.skc', hip_cam=True, left_ref=dict(clip=aim2h))
        sh = lambda keys: {}
        out = lambda part: 'viewmodel/webley/coop_webley_%s.skc' % part
    ga = lambda keys: dict(gun_abs=dict(T=Tw, keys=keys))
    rows = {
        # OPEN: grip -> the barrel, from the left and below (7) -> tips it down with the gun's own animation (11-15;
        # the weapon's clip is started 3 frames into the torso clip). The loop row blends in over 0.1 s from here.
        'webley_reload': dict(out=out('reload'), **ga({0: 0.0, 2: 0.0, 9: 1.0, 15: 1.0}),
                              left_path={0: dict(aim=1), 7: ONB, 11: ONB, 15: ONBO},
                              elbow_down={'L': [(0, 0.0), (5, ELB), (15, ELB)]},
                              **sh([(0, 0.0), (6, 1.0), (15, 1.0)])),
        # ONE ROUND: at the chamber (0) -> off and down to the pouch, out of frame (5-8) -> back with the round in the
        # fingers (11) -> seated (13)
        'webley_reload_single': dict(out=out('reload_single'), **ga({0: 1.0, 15: 1.0}), ltag=LTAG,
                                     left_path={0: SEAT, 2: LIFT, 5: dict(cam=POUCH, rot='aim', fing='aim'),
                                                8: dict(cam=POUCH, rot='aim', fing='aim'), 11: LIFT, 13: SEAT, 15: SEAT},
                                     elbow_down={'L': [(0, ELB), (15, ELB)]}, **sh([(0, 1.0), (15, 1.0)])),
        # CLOSE: the hand drops to the tipped barrel (4), swings it shut with the gun's animation (9-13) and goes
        # back to where the clip started as the gun comes up
        'webley_reload_end': dict(out=out('reload_end'), **ga({0: 1.0, 6: 1.0, 13: 0.0, 15: 0.0}),
                                  left_path={0: SEAT, 4: ONBO, 9: ONBO, 12: dict(gunpt=WEB_B, off=(-3.4, 3.4, -3.2), rot='aim'),
                                             15: dict(aim=1)},
                                  elbow_down={'L': [(0, ELB), (10, ELB), (15, 0.0)]}, **sh([(0, 1.0), (9, 1.0), (15, 0.0)])),
    }
    return dict(common=common, rows=rows)


SETS = {'webley_ads': lambda: webley('ads'), 'webley_hip': lambda: webley('hip')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('set'); ap.add_argument('root'); ap.add_argument('--only')
    a = ap.parse_args()
    st = SETS[a.set]()
    for row, rc0 in st['rows'].items():
        if a.only and row != a.only:
            continue
        kw = dict(st['common']); kw.update({k: v for k, v in rc0.items() if k != 'out'})
        rc = H.auto_recipe(row, **kw)
        H.RECIPES[row] = rc
        sk, rep = H.bake(row, CTL)
        b = R.skc_io.write(sk)
        dst = os.path.join(a.root, 'models', 'human', 'animation', rc0['out'].replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(b)
        print(row, '->', rc0['out'], sk.numFrames, 'frames', hashlib.md5(b).hexdigest()[:8])


if __name__ == '__main__':
    main()

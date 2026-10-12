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
ELB = float(os.environ.get('WEB_ELBW', '3.0'))                              # support elbow swung under: the forearm rises from below, not across
ROUND = 'models/ammo/nagant_pistol_shell.tik'


def work_T(aim_clip, gun, D, tag=None, ref_pt=None):
    """gun-in-camera (rows, u) at the open-action work pose: the AIMED gun dropped D[0] u, rolled D[1], pitched D[2]
    deg (negative = muzzle up) about a point 12 u down the sight line, shifted D[3] u to the left, yawed D[4] deg about
    the view's up axis; tag = explicit place of the weapon tag in the camera frame (fwd, left, up)"""
    a = R.load(R.ANIM + aim_clip)
    pc = R.pose_dict(a, a.numFrames - 1)
    Wc = R.evaluate(pc)
    Wcc = V.evaluate_ctl(pc, CTL)
    corr = V.rig_target(Wcc, V.SIGHTS[gun])
    C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']; C[3, 0:3] *= R.S
    Mcam = C @ V.model_to_cam(corr)
    Rr = R.axis_angle_rows((1, 0, 0), D[1]) @ R.axis_angle_rows((0, 1, 0), D[2])
    if len(D) > 4:
        Rr = Rr @ R.axis_angle_rows((0, 0, 1), D[4])
    pv = 12.0
    P = np.eye(4); P[3, 0:3] = (-pv, 0, 0)
    Q = np.eye(4); Q[0:3, 0:3] = Rr
    Pi = np.eye(4); Pi[3, 0:3] = (pv, D[3] if len(D) > 3 else 0.0, -D[0])
    Gs = Wc['tag_weapon_right'].copy(); Gs[3, 0:3] *= R.S
    Tm = Gs @ Mcam @ (P @ Q @ Pi)
    if tag:
        Tm[3, 0:3] = tag
    if ref_pt is not None:
        cyl = np.r_[np.array(ref_pt), 1.0] @ Tm
        print('work pose: tag cam %s  ref point cam %s  gun x in cam %s' % (np.round(Tm[3, 0:3], 1), np.round(cyl[0:3], 1), np.round(Tm[0, 0:3], 2)))
    return Tm


# ------------------------------------------------------------------------------------------------ Webley (top-break)
# points in the weapon-tag frame (u; x forward, y right, z down), read off the mesh (gunview.py)
WEB_C = (9.75, -0.8, -4.4)      # the mouth of the top-left chamber of the OPEN cylinder (its face looks up)
WEB_B = (8.6, -0.75, -2.6)      # the barrel just ahead of the cylinder, gun closed
WEB_BO = (8.4, -0.75, 2.1)      # the same spot with the barrel tipped down (hinge about (6.0, -0.4))
WEB_D = tuple(float(x) for x in os.environ.get('WEB_D', '0,-40,-35,0').split(','))
_SO = tuple(float(x) for x in os.environ.get('WEB_SEAT', '-0.5,3.5,-4.0').split(','))
PINCH = ('mix', 4, 0.18)        # fingers: the grip's curl opened a little toward the retail open hand = holding a round
LTAG = dict(pinch=(10.0, 3.0, -2.6), hold=1.0)     # thumb / forefinger pinch point in the hand (pre-scale) + the round below it
SEAT = dict(gunpt=WEB_C, off=_SO, rot='aim', fing=PINCH, pinch_at=1, above=0.5)
LIFT = dict(gunpt=WEB_C, off=_SO, rot='aim', fing=PINCH, pinch_at=1, above=2.6)
# the loop's first / last frame: the hand just off the chamber, a little down-left of it (never touching: the loop row
# blends in from the open, so there is no extra visit to the cylinder before the first trip to the pouch)
REST = dict(gunpt=WEB_C, off=_SO, rot='aim', fing=PINCH, pinch_at=1, above=1.6, cam_add=(-0.5, 1.8, -2.2))
ONB = dict(gunpt=WEB_B, off=(-3.0, 3.4, -2.4), rot='aim')
ONBO = dict(gunpt=WEB_BO, off=(-3.0, 3.4, -2.0), rot='aim')


TIME = lambda d: d        # the slow variant re-times the loop keys (see webley_slow)


def webley(kind, slow=False):
    """slow: the loop lasts 24 frames (0.8 s) instead of 16 (0.53 s) - the hand has time to go to the pouch and back"""
    aim2h = 'viewmodel/webley/webley_ads2h.skc'
    Tw = work_T(aim2h, 'webley_revolver', WEB_D, [float(x) for x in os.environ.get('WEB_TAG', '13.5,-4.2,-6.0').split(',')], WEB_C)
    common = dict(gun='webley_revolver', fixed_right=True, elbow_vec=tuple(float(x) for x in os.environ.get('WEB_ELB', '0,0,-1').split(',')))
    sfx = '_slow' if slow else ''
    if kind == 'ads':
        common.update(charge=aim2h)
        sh = lambda keys: dict(shoulder_ref=dict(clip=REFAIM, keys=keys))
        out = lambda part: 'viewmodel/webley/webley_%s_ads%s.skc' % (part, sfx if part == 'reload_single' else '')
    else:
        common.update(charge='viewmodel/nagantrev/idle.skc', hip_cam=True, left_ref=dict(clip=aim2h))
        sh = lambda keys: {}
        out = lambda part: 'viewmodel/webley/coop_webley_%s%s.skc' % (part, sfx if part == 'reload_single' else '')
    ga = lambda keys: dict(gun_abs=dict(T=Tw, keys=keys))
    PO = dict(cam=POUCH, rot='aim', fing='aim')
    if slow:
        N = 23
        loop = {0: REST, 6: PO, 12: PO, 17: LIFT, 20: SEAT, 21: SEAT, 23: REST}
        lsrc = dict(hip='viewmodel/webley/coop_webley_tp_single_slow.skc')      # the retail loop resampled to 24 frames
    else:
        N = 15
        loop = {0: REST, 4: PO, 7: PO, 10: LIFT, 12: SEAT, 13: SEAT, 15: REST}
        lsrc = {}
    rows = {
        # OPEN: grip -> the barrel, from the left and below (7) -> tips it down with the gun's own animation (11-15;
        # the weapon's clip is started 3 frames into the torso clip). The loop row blends in over 0.1 s from here.
        'webley_reload': dict(out=out('reload'), **ga({0: 0.0, 2: 0.0, 9: 1.0, 15: 1.0}),
                              left_path={0: dict(aim=1), 7: ONB, 11: ONB, 15: ONBO},
                              elbow_down={'L': [(0, 0.0), (5, ELB), (15, ELB)]},
                              **sh([(0, 0.0), (6, 1.0), (15, 1.0)])),
        # ONE ROUND: just off the chamber (0) -> down and out to the pouch, out of frame -> back with the round in
        # the fingers -> seated -> off the chamber again
        'webley_reload_single': dict(out=out('reload_single'), **ga({0: 1.0, N: 1.0}), ltag=LTAG, left_path=loop,
                                     elbow_down={'L': [(0, ELB), (N, ELB)]}, **sh([(0, 1.0), (N, 1.0)]), **lsrc),
        # CLOSE: the hand drops to the tipped barrel (4), swings it shut with the gun's animation (9-13) and goes
        # back to where the clip started as the gun comes up
        'webley_reload_end': dict(out=out('reload_end'), **ga({0: 1.0, 6: 1.0, 13: 0.0, 15: 0.0}),
                                  left_path={0: REST, 4: ONBO, 9: ONBO, 12: dict(gunpt=WEB_B, off=(-3.4, 3.4, -3.2), rot='aim'),
                                             15: dict(aim=1)},
                                  elbow_down={'L': [(0, ELB), (10, ELB), (15, 0.0)]}, **sh([(0, 1.0), (9, 1.0), (15, 0.0)])),
    }
    if slow:
        rows = {'webley_reload_single': rows['webley_reload_single']}
    return dict(common=common, rows=rows)


# ------------------------------------------------------------------------------------------------ Nagant (gate loader)
# The gun is handed to the LEFT hand (the server's attachtohand offhand, torso frame 11 of the start clip) and the
# RIGHT hand loads through the gate on the right of the frame, one round at a time; a fired case drops out of the gate
# at the start of every loop (there is no group ejection on this gun). Both weapon tags stay on the gun in the start
# and end clips, so the hand-off frame does not show; in the loop the right tag carries the cartridge.
NAG_C = (2.75, 0.10, -1.05)     # mouth of the chamber behind the open gate (rear face of the cylinder, right side)
NAG_D = tuple(float(x) for x in os.environ.get('NAG_D', '0,-85,0,0,25').split(','))
NAG_TAG = [float(x) for x in os.environ.get('NAG_TAG', '13.5,0.5,-2.5').split(',')]
NAG_HOLD = tuple(float(x) for x in os.environ.get('NAG_HOLD', '2.4,0.0,-1.3').split(','))
NAG_OFF = tuple(float(x) for x in os.environ.get('NAG_OFF', '-3.0,-3.5,-2.5').split(','))
POUCH_R = (5.0, -9.0, -15.0)
RTAG = dict(pinch=(10.0, 3.0, 2.6), hold_vec=(0.3, 0.0, 0.0), axes=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]])


def nagant(kind):
    """The retail clips already hold the gun the right way for a gate loader: the LEFT hand over the top of the frame
    (its thumb turns the cylinder), the RIGHT hand feeds a round into the gate. Both hands keep that retail relation
    to the gun; what is keyed here is the GUN (eased to a work pose where the gate side faces the eye), the support
    hand's way from / to the two-handed grip, and a trip to the pouch between rounds."""
    aim2h = 'viewmodel/nagantrev/nagantrev_ads2h.skc'
    Tw = work_T(aim2h, 'nagant_revolver', NAG_D, NAG_TAG, NAG_C)
    NE = float(os.environ.get('NAG_ELB', '3.0'))
    common = dict(gun='nagant_revolver', weight=dict(on=False))
    if kind == 'ads':
        common.update(charge=aim2h)
        out = lambda part: 'viewmodel/nagantrev/nagantrev_%s_ads.skc' % part
        lg0 = dict(left_grip=dict(fa=9, fb=None, way=(0.0, -1.5, -1.0)))
        lg1 = dict(left_grip=dict(fa=None, fb=6, way=(0.0, -1.5, -1.0), hold=2))
    else:
        common.update(charge='viewmodel/nagantrev/idle.skc', hip_cam=True)
        out = lambda part: 'viewmodel/nagantrev/coop_nagant_%s.skc' % part
        lg0 = lg1 = {}
    ga = lambda keys: dict(gun_abs=dict(T=Tw, keys=keys))
    POR = dict(cam=POUCH_R, rot=17, fing=17)
    loopR = {k: dict(rel=k) for k in range(0, 8)}                 # the retail feed, frame for frame (round in at 6)
    loopR.update({10: POR, 13: POR, 17: dict(rel=17)})            # then down to the pouch and back for the next
    rows = {
        'nagantrev_reload': dict(out=out('reload'), offhand=(11, 30), free_tag=False, **ga({0: 0.0, 3: 0.0, 13: 1.0, 30: 1.0}), elbow_down={'L': [(0, 0.0), (8, NE), (30, NE)]}, **lg0),
        'nagantrev_reload_single': dict(out=out('reload_single'), offhand=(0, 17), **ga({0: 1.0, 17: 1.0}), right_path=loopR, elbow_down={'L': [(0, NE), (17, NE)]}),
        'nagantrev_reload_end': dict(out=out('reload_end'), offhand=(0, 9), free_tag=False, **ga({0: 1.0, 7: 1.0, 19: 0.0, 22: 0.0}), elbow_down={'L': [(0, NE), (8, NE), (16, 0.0), (22, 0.0)]}, **lg1),
    }
    return dict(common=common, rows=rows)


SETS = {'webley_ads': lambda: webley('ads'), 'webley_hip': lambda: webley('hip'),
        'nagant_ads': lambda: nagant('ads'), 'nagant_hip': lambda: nagant('hip'),
        'webley_ads_slow': lambda: webley('ads', True), 'webley_hip_slow': lambda: webley('hip', True)}


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

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
    # [2026-10-12, user: "rework revolvers" to the on-target rule] AIMED: the gun is worked LOW - the open cylinder under
    # the centre box, the grip below the bottom edge, the hands coming up from below - so the target stays in view.
    # The hip reload keeps the approved work pose.
    if kind == 'ads':
        Tw = work_T(aim2h, 'webley_revolver', tuple(float(x) for x in os.environ.get('WEB_AD', '0,-28,-30,0').split(',')),
                    [float(x) for x in os.environ.get('WEB_ATAG', '12.0,-3.5,-13.5').split(',')], WEB_C)
    else:
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
NAG_TAG = [float(x) for x in os.environ.get('NAG_TAG', '16.0,-2.2,-3.6').split(',')]
NAG_HOLD = tuple(float(x) for x in os.environ.get('NAG_HOLD', '2.4,0.0,-1.3').split(','))
NAG_OFF = tuple(float(x) for x in os.environ.get('NAG_OFF', '-3.0,-3.5,-2.5').split(','))
POUCH_R = (5.0, -9.0, -15.0)
RTAG = dict(pinch=(10.0, 3.0, 2.6), hold_vec=(0.3, 0.0, 0.0), axes=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]])


def nagant(kind, slow=False):
    """The retail clips already hold the gun the right way for a gate loader: the LEFT hand over the top of the frame
    (its thumb turns the cylinder), the RIGHT hand feeds a round into the gate. Both hands keep that retail relation
    to the gun; what is keyed here is the GUN (eased to a work pose where the gate side faces the eye), the support
    hand's way from / to the two-handed grip, and a trip to the pouch between rounds."""
    aim2h = 'viewmodel/nagantrev/nagantrev_ads2h.skc'
    # aimed: worked LOW, under the centre box (user 2026-10-12 "rework revolvers"); the hip reload keeps its pose
    if kind == 'ads':
        Tw = work_T(aim2h, 'nagant_revolver', tuple(float(x) for x in os.environ.get('NAG_AD', '0,-85,0,0,25').split(',')),
                    [float(x) for x in os.environ.get('NAG_ATAG', '15.0,-1.0,-5.8').split(',')], NAG_C)
    else:
        Tw = work_T(aim2h, 'nagant_revolver', NAG_D, NAG_TAG, NAG_C)
    NE = float(os.environ.get('NAG_ELB', '3.0'))
    common = dict(gun='nagant_revolver', weight=dict(on=False),
                  elbow_vec={'R': tuple(float(x) for x in os.environ.get('NAG_ELBR', '0,-1,-0.3').split(',')), 'L': (0.0, 0.0, -1.0)})
    if kind == 'ads':
        common.update(charge=aim2h)
        out = lambda part: 'viewmodel/nagantrev/nagantrev_%s_ads.skc' % part
        lg0 = dict(left_grip=dict(fa=9, fb=None, way=(0.0, -1.5, -1.0)))
        lg1 = dict(left_grip=dict(fa=None, fb=9, way=(0.0, -1.5, -1.0), hold=2))
    else:
        common.update(charge='viewmodel/nagantrev/idle.skc', hip_cam=True)
        out = lambda part: 'viewmodel/nagantrev/coop_nagant_%s.skc' % part
        lg0 = lg1 = {}
    ga = lambda keys: dict(gun_abs=dict(T=Tw, keys=keys))
    POR = dict(cam=POUCH_R, rot=0, fing=0)
    POR9 = dict(cam=POUCH_R, rot=0, fing=0)
    # ONE ROUND (re-timed; the choreography is ours now): the hand leaves the gate, goes down out of frame to the pouch
    # (3-6), comes up WITH the round (the prop is attached at 7) and feeds it as the retail art does (retail frames
    # 0-6 on 10-16)
    loopR = {0: dict(rel=6), 3: POR, 6: POR}
    loopR.update({10 + k: dict(rel=k) for k in range(0, 7)})
    loopR[17] = dict(rel=6)
    tmap = {0: 6, 6: 0, 10: 0, 16: 6, 17: 6}
    ER = {'R': [(0, NE), (17, NE)], 'L': [(0, NE), (17, NE)]}      # both elbows under: hand and wrist in view, not sleeve
    READY = dict(rel=30)                                           # the right hand beside the gate, as the retail start ends
    rows = {
        # HAND-OVER: the left hand takes the gun over the frame, the right hand lets go and waits beside the gate (the
        # retail start sends it to the pouch here; the loop does that now, with the round visible)
        'nagantrev_reload': dict(out=out('reload'), offhand=(11, 30), free_tag=False, **ga({0: 0.0, 3: 0.0, 13: 1.0, 30: 1.0}),
                                 right_path={0: dict(aim=1), 16: dict(aim=1), 28: READY, 30: READY},   # no waiting at the gate: it lets go late and goes straight on
                                 elbow_down={'L': [(0, 0.0), (8, NE), (30, NE)], 'R': [(0, 0.0), (18, 0.0), (28, NE), (30, NE)]}, **lg0),
        'nagantrev_reload_single': dict(out=out('reload_single'), offhand=(0, 17), **ga({0: 1.0, 17: 1.0}), right_path=loopR,
                                        tag_map=tmap, elbow_down=ER),
        # CLOSE, one motion: the right hand goes back to the grip first (0-7), then the left hand rolls the gun upright
        # into it (8-18) and returns to the support grip
        'nagantrev_reload_end': dict(out=out('reload_end'), offhand=(0, 9), free_tag=False, **ga({0: 1.0, 8: 1.0, 18: 0.0, 22: 0.0}),
                                     right_path={0: dict(rel=6), 7: dict(aim=1), 22: dict(aim=1)},
                                     elbow_down={'L': [(0, NE), (10, NE), (18, 0.0), (22, 0.0)], 'R': [(0, NE), (7, 0.0), (22, 0.0)]}, **lg1),
    }
    if slow:
        # 27 frames (0.9 s): the retail loop resampled x1.5 is the `hip` clip, so the feed (retail 0-6) is its frames 0-9
        NS = 26
        lp = {0: dict(rel=9), 4: POR9, 10: POR9}
        lp.update({16 + j: dict(rel=j) for j in range(0, 10)})
        lp[NS] = dict(rel=9)
        rows = {'nagantrev_reload_single': dict(out=out('reload_single_slow'), hip='viewmodel/nagantrev/coop_nagant_tp_loop_slow.skc',
                                                offhand=(0, NS), **ga({0: 1.0, NS: 1.0}), right_path=lp,
                                                tag_map={0: 9, 10: 0, 16: 0, 25: 9, NS: 9},
                                                elbow_down={'R': [(0, NE), (NS, NE)], 'L': [(0, NE), (NS, NE)]})}
    return dict(common=common, rows=rows)


# ------------------------------------------------------------------------------------------------ S&W M10 (swing-out)
# The mesh had no moving cylinder: m10probe.py / m10build.py split cylinder + crane + ejector rod onto their own bone
# and key the swing in the GUN's clips. Choreography as the Webley's (the firing hand keeps the gun, the support hand
# works): push the cylinder out to the left -> [empty: muzzle up, thumb on the ejector rod, six cases fall] -> muzzle
# down -> one round from the pouch per loop into the rear of the open cylinder -> push it shut.
_M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'm10_points.json')))
M10_CC = tuple(_M['c_closed']); M10_CO = tuple(_M['c_open']); M10_R = _M['radius']
M10_PUSH = (M10_CC[0], M10_CC[1] - M10_R, M10_CC[2])                 # left face of the closed cylinder
M10_OPENF = (M10_CO[0], M10_CO[1] - M10_R, M10_CO[2])                # outer face of the open cylinder
M10_CH = tuple(_M['feed']) if 'feed' in _M else (_M['rear_x'], M10_CO[1], M10_CO[2] - 0.62 * M10_R)   # mouth of the lower-left chamber of the open cylinder (m10build)
M10_ROD = tuple(_M['rod_tip'])
M10_DL = tuple(float(x) for x in os.environ.get('M10_DL', '0,0,8,0,0').split(','))      # load: muzzle down, left side up
M10_DD = tuple(float(x) for x in os.environ.get('M10_DD', '0,0,-50,0,0').split(','))     # dump: muzzle up
M10_TAG = [float(x) for x in os.environ.get('M10_TAG', '13.5,-1.2,-4.2').split(',') if x] or None
M10_OFF = tuple(float(x) for x in os.environ.get('M10_OFF', '-3.0,3.4,-2.4').split(','))
M10_SO = tuple(float(x) for x in os.environ.get('M10_SO', '-1.0,5.0,-3.5').split(','))
M10_LTAG = dict(pinch=(10.0, 3.0, -2.6), hold_vec=(0.3, 0.0, 0.0), axes=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]])


def m10(kind, empty=False, slow=False):
    aim2h = 'viewmodel/coop_m10/m10_ads2h.skc'
    # aimed: worked LOW, under the centre box (user 2026-10-12 "rework revolvers"); the hip reload keeps its poses
    if kind == 'ads':
        Tl = work_T(aim2h, 's_w_m10_38', M10_DL, [float(x) for x in os.environ.get('M10_ATAG', '13.0,-1.0,-6.0').split(',')], M10_CH)
        Td = work_T(aim2h, 's_w_m10_38', M10_DD, [float(x) for x in os.environ.get('M10_ADTAG', '13.0,-2.5,-13.0').split(',')], M10_ROD)
    else:
        Tl = work_T(aim2h, 's_w_m10_38', M10_DL, M10_TAG, M10_CH)
        Td = work_T(aim2h, 's_w_m10_38', M10_DD, [float(x) for x in os.environ.get('M10_DTAG', '13.5,-3.0,-6.0').split(',')], M10_ROD)
    RO = tuple(float(x) for x in os.environ.get('M10_ROFF', '-1.5,3.5,2.5').split(','))
    EK = [float(x) for x in os.environ.get('M10_EK', '3,3').split(',')]
    common = dict(gun='s_w_m10_38', fixed_right=True)
    if empty:
        common['elbow_vec'] = {'L': tuple(float(x) for x in os.environ.get('M10_ELBL', '0,1,0.3').split(','))}
    if kind == 'ads':
        common.update(charge=aim2h)
        sh = lambda keys: dict(shoulder_ref=dict(clip=REFAIM, keys=keys))
        out = lambda part: 'viewmodel/coop_m10/m10_%s_ads.skc' % part
    else:
        common.update(charge='viewmodel/pistol/coltpose.skc', hip_cam=True, left_ref=dict(clip=aim2h))
        sh = lambda keys: {}
        out = lambda part: 'viewmodel/coop_m10/coop_m10_%s.skc' % part
    PUSH = dict(gunpt=M10_PUSH, off=M10_OFF, rot='aim')
    OPENF = dict(gunpt=M10_OPENF, off=M10_OFF, rot='aim')
    ROD = dict(gunpt=M10_ROD, off=RO, rot='aim')
    RODIN = dict(gunpt=(M10_ROD[0] - 1.3, M10_ROD[1], M10_ROD[2]), off=RO, rot='aim')
    SEAT = dict(gunpt=M10_CH, off=M10_SO, rot='aim', fing=PINCH, pinch_at=1, above_vec=(-0.4, 0.0, 0.0))
    LIFT = dict(gunpt=M10_CH, off=M10_SO, rot='aim', fing=PINCH, pinch_at=1, above_vec=(-2.2, 0.0, 0.0), cam_add=(-0.5, 2.2, -2.2))
    REST = dict(gunpt=M10_CH, off=M10_SO, rot='aim', fing=PINCH, pinch_at=1, above_vec=(-1.8, 0.0, -0.2), cam_add=(-0.5, 1.8, -2.2))
    PO = dict(cam=POUCH, rot='aim', fing='aim')
    start = 'viewmodel/coop_m10/coop_m10_tp_start.skc'              # the retail Webley start resampled to 30 frames (1.0 s)
    if empty:
        gun0 = [dict(T=Td, keys={0: 0.0, 3: 0.0, 13: 1.0, 23: 1.0, 28: 0.0, 29: 0.0}), dict(T=Tl, keys={0: 0.0, 23: 0.0, 29: 1.0})]
        left0 = {0: dict(aim=1), 8: PUSH, 10: PUSH, 16: OPENF, 19: ROD, 22: RODIN, 25: ROD, 29: REST}
        name0 = 'reload_empty'
    else:
        gun0 = [dict(T=Tl, keys={0: 0.0, 3: 0.0, 14: 1.0, 29: 1.0})]
        left0 = {0: dict(aim=1), 8: PUSH, 10: PUSH, 16: OPENF, 22: OPENF, 29: REST}
        name0 = 'reload'
    if slow:
        N = 23
        loop = {0: REST, 5: PO, 9: PO, 15: LIFT, 20: SEAT, 21: SEAT, 23: REST}     # in view from ~11: the hand is SEEN arriving with the round
        lsrc = dict(hip='viewmodel/webley/coop_webley_tp_single_slow.skc')
        lname = 'reload_single_slow'
    else:
        N = 15
        loop = {0: REST, 4: PO, 7: PO, 10: LIFT, 12: SEAT, 13: SEAT, 15: REST}
        lsrc = {}
        lname = 'reload_single'
    rows = {
        'webley_reload': dict(out=out(name0), hip=start, gun_abs=gun0, left_path=left0,
                              elbow_down={'L': ([(0, 0.0), (6, ELB), (15, ELB), (18, EK[0]), (25, EK[1]), (29, ELB)] if empty else [(0, 0.0), (6, ELB), (29, ELB)])},
                              **sh([(0, 0.0), (7, 1.0), (29, 1.0)])),
        'webley_reload_single': dict(out=out(lname), gun_abs=dict(T=Tl, keys={0: 1.0, N: 1.0}), ltag=M10_LTAG, left_path=loop,
                                     elbow_down={'L': [(0, ELB), (N, ELB)]}, **sh([(0, 1.0), (N, 1.0)]), **lsrc),
        'webley_reload_end': dict(out=out('reload_end'), gun_abs=dict(T=Tl, keys={0: 1.0, 6: 1.0, 13: 0.0, 15: 0.0}),
                                  left_path={0: REST, 4: OPENF, 6: OPENF, 11: PUSH, 13: dict(gunpt=M10_PUSH, off=(-3.4, 4.2, -3.2), rot='aim'),
                                             15: dict(aim=1)},
                                  elbow_down={'L': [(0, ELB), (10, ELB), (15, 0.0)]}, **sh([(0, 1.0), (9, 1.0), (15, 0.0)])),
    }
    if empty:
        rows = {'webley_reload': rows['webley_reload']}
    if slow:
        rows = {'webley_reload_single': rows['webley_reload_single']}
    return dict(common=common, rows=rows)


SETS = {'webley_ads': lambda: webley('ads'), 'webley_hip': lambda: webley('hip'),
        'nagant_ads': lambda: nagant('ads'), 'nagant_hip': lambda: nagant('hip'),
        'nagant_ads_slow': lambda: nagant('ads', True), 'nagant_hip_slow': lambda: nagant('hip', True),
        'm10_ads': lambda: m10('ads'), 'm10_hip': lambda: m10('hip'),
        'm10_ads_empty': lambda: m10('ads', empty=True), 'm10_hip_empty': lambda: m10('hip', empty=True),
        'm10_ads_slow': lambda: m10('ads', slow=True), 'm10_hip_slow': lambda: m10('hip', slow=True),
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

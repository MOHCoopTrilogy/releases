"""First-person HAND clips of the double-barrel shotgun (rows `coopr_shotgun_double_barrel_<row>[_ads]`).

    python tools/dbs_hands.py bake                -> assets/models/human/animation/viewmodel/coop_dbshotgun/dbs_*.skc
                                                     + build/hand_paths.json (the carried shells, for dbs_anim.py)
    python tools/dbs_hands.py sheet <clip> f,f,f out.jpg [eye|close|side|top]      offline look (arms + gun)
    python tools/dbs_hands.py report              numbers only (IK clamps per clip, pinch fit, physics peaks)

Version 2 (2026-10-12 b). Everything is keyed in the VIEW (the camera is the eyes bone, its axes the rig's: forward +x,
left +y, up +z) or in the GUN frame (scaled game units: +x muzzle, +y right, +z down); the arms are solved by the
lanes' two-bone IK (ads_bolt key_bolt.solve_arms). The body / eye channels are ONE retail pose per family (hip clips:
the pump gun's idle frame; aimed clips: its aim frame), so nothing moves that is not keyed here.

  HOLD    the gun out in front and low, the forend hand on the rear half of the forend
  AIM     the eye behind and above the breech, looking down the rib to the bead (the `charge` row; same numbers as the
          sight row in sights_override.json, so the engine's own sight-line correction is near zero)
  WORK    where the OPEN gun is loaded - hip and aimed. Aimed: under the centre box (the middle 20 % of the screen),
          pitched up so the dropped barrels point down and away and the chambers face the eye
  the reload, hip and aimed alike (lengths = the pump gun's rows: the server's timing is the shared shotgun state):
    reload (23)         the right thumb goes up over the tang onto the top lever and pushes it right, the barrels drop
                        (the forend hand rides them down), the fired cases are thrown out, the left hand goes for a shell
    reload_single (20)  RIGHT chamber;  reload_single_l (20)  LEFT chamber (the engine picks `_l` when the row
                        starts on an empty clip; `_first` made the aimed alias 51 characters - a tiki alias holds 47): the shell comes up from the belt pinched between the thumb and the
                        first two fingers (hand to the left, palm to the shooter, the brass head in plain view), is laid
                        into its chamber, the thumb goes behind the head and pushes it home, the hand goes back down
    reload_end (32)     the left hand takes the forend, the barrels are swung shut and latch with a jolt, lever back,
                        the gun returns to the hold / the exact aim
  WEIGHT  the gun is a mass on a damped spring (ads_twohand gunphys.simulate, class PHYS): lever, the barrels stopping
          on the hinge, each shell pushed home, the snap shut and the shot are impulses; the motion is the response.
"""
import os, sys, json, math
import numpy as np
from scipy.optimize import minimize
import dbslib as L
import dbs_skx as X
import dbs_rig as D
import dbs_anim as GA
import gunphys as GP                                   # ads_twohand_2026-10-11/tools (on the path via dbs_rig)

R, V, K, B = D.R, D.V, D.K, D.B
S = R.S
FT = 1.0 / 30.0
ODIR = os.path.join(L.ASSETS, 'models', 'human', 'animation', 'viewmodel', 'coop_dbshotgun')
TIK = 'models/weapons/coop_dbshotgun.tik'

# ---------------------------------------------------------------------------------------------------- the numbers
# breech / cham: where that gun point sits in the view (forward, left, up), game units; yaw + = left, pitch + = up,
# roll - = the top leans to the left (toward the eye at the hip)
HOLD = dict(breech=(13.8, -6.0, -3.2), yaw=5.0, pitch=2.5, roll=-8.0)     # run hold2: the engine draws the hip gun ~1.6 u lower than the offline camera
AIM = dict(relief=11.0, delta=0.131)
SIGHT_R = (4.7932, -1.05, -5.0074)        # top of the breech end, centre line (build/model.json sight.R)
SIGHT_F = (21.5216, -1.05, -5.3041)       # top of the bead
WORK = {'hip': dict(cham=(10.8, -2.6, -1.1), yaw=6.0, pitch=16.0, roll=-8.0),      # run rh1: at -2.6 up the hip reload played on the screen's bottom edge
        'ads': dict(cham=(9.6, -0.2, -3.0), yaw=0.0, pitch=18.0, roll=-4.0)}
LH_BACK = 6.6         # u the forend hand sits nearer than on the pump gun: wrist at 9.1 u, palm under the rear half
LH_UP = float(os.environ.get('DBS_LH_UP', -0.7))
LH_ROLL = float(os.environ.get('DBS_LH_ROLL', 0.0))
LH_AXIS = (-1.05, -3.2)
GRIP = (-4.0, -1.05, 0.5)
LOWERED = (15.0, 12.0, 38.0, -2.0, 3.0)      # the gun put away / before it is raised: drop u, roll deg, pitch deg (muzzle down), side u, back u
# the gun as a mass on a spring (gunphys class): a 2.3 kg sawn-off; no one-handed sag (the work pose IS the one-handed pose)
PHYS = dict(m=2.3, f2=3.4, f1=2.4, z=0.62, sag=(0.0, 0.0, 0.0, 0.0, 0.0), magw=0.0, tr=(0.020, 0.16, 0.16, 0.020, 0.008), tr2=0.25)
GP.ACTIONS.update({
    'dbs_lever': ((1.0, 22.0, 6.0, -2.0, 0.0), 2.0),        # the thumb shoves the lever to the right
    'dbs_open':  ((34.0, 0.0, 380.0, 0.0, -22.0), 2.5),    # the barrels fall and stop on the hinge: the muzzle end jerks down
    'dbs_eject': ((2.0, 0.0, -60.0, 0.0, 14.0), 1.5),       # the ejectors fire the cases back
    'dbs_shell': ((30.0, 0.0, 150.0, 0.0, -30.0), 1.5),       # a shell thumbed home, down the chamber
    'dbs_shut':  ((30.0, 0.0, 330.0, 0.0, 22.0), 2.0),     # snapped shut by bringing the grip UP to the barrels: the
                                                           # action's mass stops on them - the muzzle end nods down, the
                                                           # gun comes back at the shooter (and never over the sight line)
    'dbs_fire':  ((-7.0, 14.0, -760.0, 0.0, 140.0), 1.5),  # a 12-bore from 33 cm tubes: flips up about the grip, shoves back
})
# the shell in the fingers
SHELL_DIA = 1.13      # game u
GAP = SHELL_DIA + 0.62          # thumb bone tip to the finger tips' line across the shell (pads 0.31 u each side)
HOLD_AT = 1.25        # u the pinch (thumb opposite the two fingers) sits ahead of the shell's head
FACE_AT = 1.15        # u the pinch stops short of the breech face (the index finger is on the nose side of it)
SHELL_LEN = 5.9       # skd units
TIPLEN = {0: 1.3, 1: 0.9, 2: 1.0}          # last phalanx, game u
LEVER_SHIFT = (2.5, 0.0, -1.0)             # the grip hand slides this far up the grip to reach the lever (gun frame, u)
BELT_VIEW = (5.0, 5.5, -9.5)               # where the hand goes for a shell: below and left of the view
WRIST_VIEW_HIP = (-0.20, 0.50, -0.84)      # (tried -0.25 0.12 -0.96, the hand from straight below: it stood in front of the whole gun; same side as aimed)

WRIST_VIEW = (-0.20, 0.50, -0.84)          # the loading hand lies to this side of the shell in the view (unit-ish)


def zq(deg):
    return np.array([0.0, 0.0, math.sin(math.radians(deg) / 2), math.cos(math.radians(deg) / 2)])


def qmul_rows(q_extra, q):
    """`q` turned first by `q_extra` in the joint's own frame"""
    return np.asarray(R.rows_to_quat(R.quat_to_rows(q_extra) @ R.quat_to_rows(q)), float)


def xg(roll=0.0, pitch=0.0, yaw=0.0, move=(0, 0, 0), pivot=GRIP):
    """gun-local rigid move, 4x4 row form in RIG units: rotations about the gun's x (roll), y (pitch, - = muzzle up),
    z (yaw) through `pivot`, then `move` (scaled units)"""
    Rm = GA.rot((1, 0, 0), roll) @ GA.rot((0, 1, 0), pitch) @ GA.rot((0, 0, 1), yaw)
    pv = np.asarray(pivot, float) / S
    Xm = np.eye(4); Xm[0:3, 0:3] = Rm
    Xm[3, 0:3] = -pv @ Rm + pv + np.asarray(move, float) / S
    return Xm


def hold_G(E, breech, yaw, pitch, roll, at=None):
    """gun matrix (rig world, row form) with the gun point `at` (default: the breech top) at view place `breech`"""
    y, p, r = (math.radians(v) for v in (yaw, pitch, roll))
    gx = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    gy0 = np.array([math.sin(y), -math.cos(y), 0.0])                # the gun's right
    gz0 = np.cross(gx, gy0)                                         # the gun's down
    gy = gy0 * math.cos(r) + gz0 * math.sin(r); gz = -gy0 * math.sin(r) + gz0 * math.cos(r)
    G = np.eye(4); G[0:3, 0:3] = np.array([gx, gy, gz])
    at = SIGHT_R if at is None else at
    G[3, 0:3] = np.asarray(E, float) + np.asarray(breech, float) / S - (np.asarray(at, float) / S) @ G[0:3, 0:3]
    return G


def aim_G(E, relief=None, delta=None):
    """the aimed gun: bead top on the view axis, the breech top `relief` u from the eye and `delta` rad under it"""
    relief = AIM['relief'] if relief is None else relief; delta = AIM['delta'] if delta is None else delta
    fr = np.asarray(SIGHT_F) - np.asarray(SIGHT_R)
    Lfr = float(np.linalg.norm(fr))
    Rv = relief * np.array([math.cos(delta), 0.0, -math.sin(delta)])
    dF = Rv[0] + math.sqrt(Lfr * Lfr - Rv[2] * Rv[2])
    v = np.array([dF, 0.0, 0.0]) - Rv                              # breech top -> bead top in the view
    pitch = math.degrees(math.atan2(v[2], v[0]) - math.atan2(-fr[2], fr[0]))
    return hold_G(E, tuple(Rv), 0.0, pitch, 0.0)


def lh_fix():
    """the pump gun's forend hand (gun frame) -> this gun's forend: back, up, turned about the forend's axis"""
    return tr((-LH_BACK, 0, -LH_UP)) @ xg(roll=LH_ROLL, pivot=(0.0, LH_AXIS[0], LH_AXIS[1]))


def tr(move):
    Xm = np.eye(4); Xm[3, 0:3] = np.asarray(move, float) / S
    return Xm


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lerpX(A, Bm, w):
    return B.blend_H(A, Bm, w)


def blend2(A, Bm, wr, wt):
    """A -> Bm with the turn at wr and the move at wt (the gun's GRIP point is what moves: the turn is about it)"""
    o = B.blend_H(A, Bm, wr)
    g = np.asarray(GRIP, float) / S
    ga = g @ A[0:3, 0:3] + A[3, 0:3]; gb = g @ Bm[0:3, 0:3] + Bm[3, 0:3]
    o[3, 0:3] = ga + (gb - ga) * wt - g @ o[0:3, 0:3]
    return o


def keyf(keys, f):
    """{frame: value} -> (a, b, w) for frame f, smoothstep"""
    ks = sorted(keys)
    if f <= ks[0]:
        return ks[0], ks[0], 0.0
    for a, b in zip(ks[:-1], ks[1:]):
        if f <= b:
            return a, b, ease((f - a) / float(b - a))
    return ks[-1], ks[-1], 0.0


def keyX(keys, f):
    a, b, w = keyf(keys, f)
    return keys[a] if a == b else lerpX(keys[a], keys[b], w)


def keyQ(keys, f):
    """{frame: {channel: quat}} blended"""
    a, b, w = keyf(keys, f)
    if a == b:
        return dict(keys[a])
    return {k: R.qslerp(np.asarray(keys[a][k], float), np.asarray(keys[b][k], float), w) for k in keys[a]}


def apply_dip(G, dip, pivot_w):
    """the physics response (drop, roll, pitch, side, back; camera frame) on a gun matrix, about `pivot_w` (rig world)"""
    drop, roll, pitch, side, back = dip
    Rm = GA.rot((1, 0, 0), roll) @ GA.rot((0, 1, 0), pitch)
    o = np.eye(4)
    o[0:3, 0:3] = G[0:3, 0:3] @ Rm
    o[3, 0:3] = (G[3, 0:3] - pivot_w) @ Rm + pivot_w + np.array([-back, side, -drop]) / S
    return o


class Rig:
    def __init__(self):
        self.idle = D.load('idle')
        self.pd0 = R.pose_dict(self.idle, 0)
        self.W0 = R.evaluate(self.pd0)
        self.G0 = self.W0['tag_weapon_right']
        gi = R.inv(self.G0)
        self.HRrel = self.W0['Bip01 R Hand'] @ gi                  # hand in gun frame (rig units)
        self.HLrel = self.W0['Bip01 L Hand'] @ gi
        self.HLfor = self.HLrel @ lh_fix()                         # on THIS gun's forend
        self.E0 = self.W0['eyes bone'][3, 0:3].copy()
        self.Gidle = hold_G(self.E0, **HOLD)
        self.Dl = self.Gidle @ R.inv(self.G0)                      # the hold as a gun-local move of the pump gun's place
        self.Gaim = aim_G(self.E0)
        self.chg = D.load('charge')
        self.pdc = R.pose_dict(self.chg, 0)
        self.Ec = R.evaluate(self.pdc)['eyes bone'][3, 0:3].copy()
        self.fL = {k: np.asarray(v, float) for k, v in self.pd0.items() if k.startswith('Bip01 L Finger')}
        self.fR = {k: np.asarray(v, float) for k, v in self.pd0.items() if k.startswith('Bip01 R Finger')}
        fill = R.pose_dict(D.load('reload_single'), 10)
        self.fLfill = {k: np.asarray(fill[k], float) for k in self.fL}
        # the open gun: chamber axis and seats, rig units in the gun frame
        Rb, c_r = GA.chambered('dbs_shell_r', GA.OPEN); _, c_l = GA.chambered('dbs_shell_l', GA.OPEN)
        self.Rb = Rb; self.ax = Rb[0]
        self.cham = {'r': c_r, 'l': c_l}
        self.cham_mid = (c_r + c_l) / 2 * S                        # game units, for hold_G(at=)
        self.Gwork = {m: hold_G(self.E0 if m == 'hip' else self.Ec, w['cham'], w['yaw'], w['pitch'], w['roll'], at=self.cham_mid)
                      for m, w in WORK.items()}
        self.fit_pinch()
        self.loads = {m: self.fit_load_frame(m) for m in ('ads', 'hip')}
        self.load = self.loads['ads']
        # the thumb leaves the shell's side, goes behind its head and pushes it the rest of the way home; the hand
        # itself stays where its fingers met the breech face (first try: the whole hand moved back to bring the thumb
        # behind the head - 1.5 u nearer the eye its fingers stood up into the centre box)
        hs, a = self.load['hs'], self.pin['a']
        self.fBack, eb = self.fit_thumb('L', self.fPush, hs - a * (0.30 / S))
        self.fHome, eh = self.fit_thumb('L', self.fPush, hs + a * ((HOLD_AT + FACE_AT - 0.30) / S))
        self.push_report = 'thumb behind the shell head: off by %.2f u, pushed home: off by %.2f u' % (eb, eh)
        self.clamps = 0

    # ------------------------------------------------------------------------------------------------ fingers
    def hand_local(self, side, fq):
        pd = dict(self.pd0); pd.update(fq)
        W = R.evaluate(pd)
        Hm = W['Bip01 %s Hand' % side]

        def loc(b):
            return (W['Bip01 %s %s' % (side, b)][3, 0:3] - Hm[3, 0:3]) @ Hm[0:3, 0:3].T
        return loc

    @staticmethod
    def tip(loc, k):
        p2, p1 = loc('Finger%d2' % k), loc('Finger%d1' % k)
        d = (p2 - p1) / np.linalg.norm(p2 - p1)
        return p2 + d * TIPLEN[k] / S, d

    def pinch_fingers(self, x, opened=0.0):
        """left-hand finger quats from the nine pinch parameters; opened: the first two fingers let go (0..1)"""
        w0, t1, t2, ib, i1, i2, mb, m1, m2 = x
        f = dict(self.fL)
        f['Bip01 L Finger0 rot'] = R.qslerp(self.fL['Bip01 L Finger0 rot'], self.fLfill['Bip01 L Finger0 rot'], w0)
        f['Bip01 L Finger01 rot'] = zq(t1); f['Bip01 L Finger02 rot'] = zq(t2)
        o = opened
        f['Bip01 L Finger1 rot'] = qmul_rows(zq(ib + 22 * o), self.fL['Bip01 L Finger1 rot'])
        f['Bip01 L Finger11 rot'] = zq(i1 + 25 * o); f['Bip01 L Finger12 rot'] = zq(i2 + 12 * o)
        f['Bip01 L Finger2 rot'] = qmul_rows(zq(mb + 22 * o), self.fL['Bip01 L Finger2 rot'])
        f['Bip01 L Finger21 rot'] = zq(m1 + 25 * o); f['Bip01 L Finger22 rot'] = zq(m2 + 12 * o)
        # ring and little finger folded into the palm, out of the way
        f['Bip01 L Finger3 rot'] = qmul_rows(zq(-22), self.fL['Bip01 L Finger3 rot'])
        f['Bip01 L Finger31 rot'] = zq(-98); f['Bip01 L Finger32 rot'] = zq(-62)
        f['Bip01 L Finger4 rot'] = qmul_rows(zq(-16), self.fL['Bip01 L Finger4 rot'])
        f['Bip01 L Finger41 rot'] = zq(-96); f['Bip01 L Finger42 rot'] = zq(-58)
        return f

    def fit_pinch(self):
        """thumb against the first two fingers across a shell: nine joint angles by a small search"""
        x0 = np.array([0.6, 15.0, 25.0, -35.0, -35.0, -25.0, -35.0, -35.0, -25.0])
        sc = np.array([0.5, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0, 30.0])
        bnd = [(-0.2, 1.4), (-40, 55), (-10, 55), (-70, 12), (-95, -8), (-65, -5), (-70, 12), (-95, -8), (-65, -5)]
        zh = np.array([0.0, 0.0, 1.0])                     # hand frame: -z = the thumb's side, +y = the palm's side

        def geo(x):
            loc = self.hand_local('L', self.pinch_fingers(x))
            T, _ = self.tip(loc, 0); I, di = self.tip(loc, 1); M, dm = self.tip(loc, 2)
            return T * S, I * S, M * S, (di + dm) / np.linalg.norm(di + dm)

        def cost(x):
            T, I, M, df = geo(x)
            C2 = (I + M) / 2
            u = T - C2; gap = np.linalg.norm(u); u = u / gap
            im = (M - I) / np.linalg.norm(M - I)
            return (4.0 * (gap - GAP) ** 2 + (np.linalg.norm(I - M) - 1.2) ** 2 + 2.0 * float(u @ zh) ** 2
                    + 2.0 * (1.0 - float(im @ zh)) ** 2 + 0.05 * float((((x - x0) / sc) ** 2).sum()))
        r = minimize(cost, x0, method='Powell', bounds=bnd, options=dict(maxiter=4000, xtol=1e-3, ftol=1e-5))
        self.px = r.x
        T, I, M, df = geo(r.x)
        C2 = (I + M) / 2
        u = (T - C2) / np.linalg.norm(T - C2)
        self.fPinch = self.pinch_fingers(r.x)
        self.fPush = self.pinch_fingers(r.x, opened=0.25)
        self.px_done = True
        a = -zh - float(-zh @ u) * u                       # the shell's nose: out of the thumb's side, square to the pinch
        self.pin = dict(T=T / S, C=(T + C2) / 2 / S, u=u, a=a / np.linalg.norm(a))
        self.pinch_report = 'pinch fit: thumb tip to the two finger tips %.2f u (wanted %.2f), tips apart %.2f u, angles %s' % (
            np.linalg.norm(T - C2), GAP, np.linalg.norm(I - M), np.round(r.x, 1).tolist())

    def fit_load_frame(self, mode='ads'):
        """how the pinching hand sits on a shell that is in line with its chamber: the shell lies ACROSS the finger
        tips (thumb on top, two fingers under it, the hand to one side). Two ways round and every turn about the
        chamber axis are tried; kept: the one that puts the wrist where WRIST_VIEW says in the aimed work pose."""
        G = self.Gwork[mode]
        want = np.asarray(WRIST_VIEW if mode == 'ads' else WRIST_VIEW_HIP, float) @ G[0:3, 0:3].T      # view direction -> gun frame
        want /= np.linalg.norm(want)
        u = self.pin['u']
        best = None
        for sgn in (1.0,):
            a = self.pin['a']                                             # the shell's nose, hand frame
            Rsh = np.array([a, u, np.cross(a, u)])                        # shell frame rows in the hand frame
            hs = self.pin['C'] - a * HOLD_AT / S                          # the shell's head centre, hand frame
            for psi in range(0, 360, 4):
                Rt = self.Rb @ GA.rot(self.ax, psi)                       # the chambered frame turned about its own axis
                Hrot = Rsh.T @ Rt
                wrist = -hs @ Hrot                                        # from the head to the wrist, gun frame
                sc = float(wrist @ want) / np.linalg.norm(wrist)
                if best is None or sc > best[0]:
                    best = (sc, Rsh, hs, Rt, sgn, psi)
        self.load_report = getattr(self, 'load_report', '') + 'loading hand (%s): turned %d deg about the chamber axis, wrist direction fit %.2f; ' % (mode, best[5], best[0])
        return dict(Rsh=best[1], hs=best[2], Rt=best[3])

    def hand_on_shell(self, head, tilt=0.0, turn=0.0, mode='ads'):
        """left hand (gun frame, rig units) pinching a shell whose head centre is at `head`; tilt: nose up (deg about
        the gun's y), turn: about the gun's z"""
        ld = self.loads[mode]
        Rt = ld['Rt'] @ GA.rot((0, 1, 0), tilt) @ GA.rot((0, 0, 1), turn)
        Hm = np.eye(4); Hm[0:3, 0:3] = ld['Rsh'].T @ Rt
        Hm[3, 0:3] = np.asarray(head, float) - ld['hs'] @ Hm[0:3, 0:3]
        return Hm, Rt

    def shell_of(self, Hm, Rt):
        """the carried shell (rotation rows, head position; gun frame) for a pinching hand"""
        return Rt, self.load['hs'] @ Hm[0:3, 0:3] + Hm[3, 0:3]

    def fit_thumb(self, side, f0, tl):
        """thumb quats (from the finger set f0) that put its tip on `tl` (hand frame, rig units) -> (finger set, miss u)"""
        key = 'Bip01 %s Finger0' % side
        M0 = R.quat_to_rows(f0[key + ' rot'])
        a1 = 2 * math.degrees(math.atan2(f0[key + '1 rot'][2], f0[key + '1 rot'][3]))
        a2 = 2 * math.degrees(math.atan2(f0[key + '2 rot'][2], f0[key + '2 rot'][3]))

        def quats(x):
            ang = float(np.linalg.norm(x[0:3]))
            Rx = GA.rot(x[0:3] / ang, ang) if ang > 1e-6 else np.eye(3)
            return {key + ' rot': np.asarray(R.rows_to_quat(Rx @ M0), float), key + '1 rot': zq(a1 + x[3]), key + '2 rot': zq(a2 + x[4])}

        def tip_of(x):
            f = dict(f0); f.update(quats(x))
            return self.tip(self.hand_local(side, f), 0)[0]

        def cost(x):
            return float(((tip_of(x) - tl) ** 2).sum()) * S * S + 0.0004 * float((x[0:3] ** 2).sum()) + 0.0002 * float((x[3:] ** 2).sum())
        r = minimize(cost, np.array([1.0, 1.0, 1.0, 0.0, 0.0]), method='Powell', options=dict(maxiter=3000, xtol=1e-2, ftol=1e-5))
        f = dict(f0); f.update(quats(r.x))
        return f, float(np.linalg.norm(tip_of(r.x) - tl)) * S

    def thumb_gun(self, HRg, target):
        """the same for the RIGHT thumb and a target in the gun frame (game u), the hand at HRg"""
        return self.fit_thumb('R', self.fR, (np.asarray(target, float) / S - HRg[3, 0:3]) @ HRg[0:3, 0:3].T)

    def forend_hand(self, theta):
        """left hand on the forend of barrels dropped by theta deg (rides the hinge)"""
        Rb = GA.barrels_R(theta)
        Xm = np.eye(4); Xm[0:3, 0:3] = Rb; Xm[3, 0:3] = -GA.PIN @ Rb + GA.PIN
        return self.HLfor @ Xm

    def solve(self, pd, G, HLg, HRg=None, fl=None, fr=None):
        """pd: base channels; G: gun (rig world); HLg / HRg: hands in the gun frame; fl / fr: finger quats"""
        pd = dict(pd)
        Wc = R.evaluate(pd)
        for f in (fl, fr):
            if f:
                pd.update(f)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            K.solve_arms(pd, Wc, (self.HRrel if HRg is None else HRg) @ G, HLg @ G, G)
        self.clamps += buf.getvalue().count('IK clamp')
        return pd


def lever_tail(lever_deg):
    """the top lever's thumb piece (its rear end), gun frame game u, for a lever turned lever_deg"""
    piv = GA.W0['dbs_lever'] * S
    tail0 = np.array([1.40, -1.05, -4.62])
    return (tail0 - piv) @ GA.rot((0, 0, 1), lever_deg) + piv


def phys(n, support, events):
    r = GP.simulate(n, FT, PHYS, support=support, events=events)
    return r


def build(rig, mode):
    """-> ({clip: (base clip, [pose dict], [gun matrix])}, shell paths, report lines)"""
    ads = mode == 'ads'
    base = rig.chg if ads else rig.idle
    pdb = rig.pdc if ads else rig.pd0
    E = rig.Ec if ads else rig.E0
    Gb = aim_G(E) if ads else rig.Gidle
    Gw = rig.Gwork[mode]
    sfx = '_ads' if ads else ''
    clips, paths, rep = {}, {}, []

    def grip_w(G):
        return D.gun_pt(G, GRIP)

    def add(nm, frames, Gs, c0):
        clips[nm + sfx] = (base, frames, Gs)
        rep.append('%-26s %2d frames, IK clamps %d' % (nm + sfx, len(frames), rig.clamps - c0))

    # ---- reload (23): lever, barrels drop, cases out, the left hand goes for a shell
    n = 23
    ph = phys(n, [(0, 1), (14, 1), (20, 0.25)], [(3, 'dbs_lever'), (GA.EJECT_F, 'dbs_eject'), (11, 'dbs_open')])
    rep.append('reload%s physics: %s' % (sfx, ph['report']))
    HRl = rig.HRrel @ tr(LEVER_SHIFT)
    f_on, e1 = rig.thumb_gun(HRl, lever_tail(0.0) + np.array([-0.1, -0.42, -0.15]))
    f_psh, e2 = rig.thumb_gun(HRl, lever_tail(GA.LEVER) + np.array([-0.1, -0.42, -0.15]))
    rep.append('thumb on the lever: tip off its place by %.2f u (lever shut) / %.2f u (pushed over)' % (e1, e2))
    HRk = {0: rig.HRrel, 2: HRl, 8: HRl, 12: rig.HRrel}
    fRk = {0: rig.fR, 2: f_on, 5: f_psh, 8: f_psh, 12: rig.fR}
    belt = ((E + np.asarray(BELT_VIEW) / S) - Gw[3, 0:3]) @ Gw[0:3, 0:3].T          # gun frame, rig units (of the AIMED work pose: one gun-space path for both)
    Gwa = rig.Gwork['ads']
    belt = ((rig.Ec + np.asarray(BELT_VIEW) / S) - Gwa[3, 0:3]) @ Gwa[0:3, 0:3].T
    Hbelt, Rbelt = rig.hand_on_shell(belt, tilt=-28.0, mode=mode)
    ld = rig.loads[mode]
    c0 = rig.clamps; fr = []; Gs = []
    for f in range(n):
        th = GA.key(GA.THETA_OPEN, f)
        # the gun comes DOWN first and turns muzzle-up only as far as the barrels have dropped: the barrels never
        # point above the line they left (the aimed reload stays under the centre box)
        G = blend2(Gb, Gw, min(1.0, th / GA.OPEN), ease(f / 8.0))
        G = apply_dip(G, ph['dip'][f], grip_w(G))
        wl = ease((f - 14) / 8.0)
        HLg = lerpX(rig.forend_hand(th), Hbelt, wl)
        fl = {k: R.qslerp(rig.fL[k], rig.fPinch[k], wl) for k in rig.fL}
        fr.append(rig.solve(pdb, G, HLg, keyX(HRk, f), fl, keyQ(fRk, f))); Gs.append(G)
    add('reload', fr, Gs, c0)

    # ---- reload_single (RIGHT chamber) / reload_single_first (LEFT chamber), 20 frames each
    n = 20
    ph = phys(n, [(0, 0.25), (20, 0.25)], [(13, 'dbs_shell')])
    rep.append('reload_single%s physics: %s' % (sfx, ph['report']))
    for nm, side in (('reload_single', 'r'), ('reload_single_l', 'l')):
        c = rig.cham[side]; ax = rig.ax
        behind = c - ax * (SHELL_LEN + 1.1)
        near = c - ax * ((HOLD_AT + FACE_AT) / S)           # the fingers reach the breech face: the head is this far out
        Hk = {0: Hbelt, 6: rig.hand_on_shell(behind, mode=mode)[0], 8: rig.hand_on_shell(behind + (c - behind) * 0.12, mode=mode)[0],
              11: rig.hand_on_shell(near, mode=mode)[0], 15: rig.hand_on_shell(near, mode=mode)[0], 19: Hbelt}
        Fk = {0: rig.fPinch, 11: rig.fPinch, 13: rig.fBack, 15: rig.fHome, 16: rig.fHome, 19: rig.fPinch}
        c0 = rig.clamps; fr = []; Gs = []; sp = {}
        for f in range(n):
            G = apply_dip(Gw, ph['dip'][f], grip_w(Gw))
            Hm = keyX(Hk, f)
            fr.append(rig.solve(pdb, G, Hm, None, keyQ(Fk, f), rig.fR)); Gs.append(G)
            if f <= 13:                                      # carried, then held at the breech face while the thumb goes behind it
                a, b, w = keyf({0: 0, 7: 1}, f)
                Rs = Hm[0:3, 0:3].T                           # (unused) hand rows
                Rsh = ld['Rsh'] @ Hm[0:3, 0:3]
                sp[str(f)] = [Rsh.tolist(), (ld['hs'] @ Hm[0:3, 0:3] + Hm[3, 0:3]).tolist()]
            elif f < 15:                                     # let go of, then thumbed home along the chamber
                a, b, w = keyf({13: 0, 15: 1}, f)
                p = near + (c - near) * (0.0 if f <= 13 else w)
                sp[str(f)] = [ld['Rt'].tolist(), p.tolist()]
            else:
                sp[str(f)] = 'in'
        if not ads:
            paths['reload_single_first' if nm == 'reload_single_l' else nm] = sp
        add(nm, fr, Gs, c0)

    # ---- reload_end (32): the left hand takes the forend, swung shut with a jolt, back to the hold / the aim
    n = 32
    ph = phys(n, [(0, 0.25), (5, 0.25), (8, 1)], [(6, 'hand_on'), (GA.SHUT_F, 'dbs_shut')])
    rep.append('reload_end%s physics: %s' % (sfx, ph['report']))
    c0 = rig.clamps; fr = []; Gs = []
    for f in range(n):
        th = GA.key(GA.THETA_CLOSE, f)
        # the grip comes up to the barrels: the gun turns back exactly as the barrels close and rises to its place
        G = blend2(Gw, Gb, 1.0 - min(1.0, th / GA.OPEN), ease((f - 6) / 9.0))
        G = apply_dip(G, ph['dip'][f], grip_w(G))
        wl = ease(f / 6.0)
        HLg = lerpX(Hbelt, rig.forend_hand(th), wl)
        fl = {k: R.qslerp(rig.fPinch[k], rig.fL[k], wl) for k in rig.fL}
        fr.append(rig.solve(pdb, G, HLg, None, fl, rig.fR)); Gs.append(G)
    add('reload_end', fr, Gs, c0)
    return clips, paths, rep


def bake_all():
    rig = Rig()
    rep = [rig.pinch_report, rig.load_report, rig.push_report]
    clips = {}
    # ---- idle (1 frame) / pullout (35) / putaway (17): the gun comes up from / goes down under the view in both
    # hands, about the grip. (First version: the pump gun's raise / lower clips blended into the hold - half way
    # the gun stood on end in front of the camera, 8 IK clamps; run tp1.) Frame counts = the retail rows'.
    clips['idle'] = (rig.idle, [rig.solve(rig.pd0, rig.Gidle, rig.HLfor)], [rig.Gidle])
    rep.append('%-26s  1 frame,  IK clamps %d' % ('idle', rig.clamps))
    for nm, n in (('pullout', 35), ('putaway', 17)):
        fr = []; Gs = []; c0 = rig.clamps
        ph = phys(n, [(0, 1), (n, 1)], [(13, 'hand_on')] if nm == 'pullout' else [])
        for f in range(n):
            w = (1.0 - ease(f / 13.0)) if nm == 'pullout' else ease(f / 13.0)
            G = apply_dip(rig.Gidle, (LOWERED[0] * w, LOWERED[1] * w, LOWERED[2] * w, LOWERED[3] * w, LOWERED[4] * w), D.gun_pt(rig.Gidle, GRIP))
            if nm == 'pullout':
                G = apply_dip(G, ph['dip'][f], D.gun_pt(G, GRIP))
            fr.append(rig.solve(rig.pd0, G, rig.HLfor)); Gs.append(G)
        clips[nm] = (rig.idle, fr, Gs)
        rep.append('%-26s %2d frames, IK clamps %d' % (nm, n, rig.clamps - c0))
    # ---- fire (16): the shot is an impulse on the sprung gun
    ph = phys(16, [(0, 1), (16, 1)], [(0, 'dbs_fire')])
    rep.append('fire physics: %s' % ph['report'])
    fr = []; Gs = []; c0 = rig.clamps
    for f in range(16):
        G = apply_dip(rig.Gidle, ph['dip'][f], D.gun_pt(rig.Gidle, GRIP))
        fr.append(rig.solve(rig.pd0, G, rig.HLfor)); Gs.append(G)
    clips['fire'] = (rig.idle, fr, Gs)
    rep.append('%-26s %2d frames, IK clamps %d' % ('fire', 16, rig.clamps - c0))
    # ---- charge (the aim pose, 1 frame)
    G = aim_G(rig.Ec)
    c0 = rig.clamps
    clips['charge'] = (rig.chg, [rig.solve(rig.pdc, G, rig.HLfor)], [G])
    rep.append('%-26s  1 frame,  IK clamps %d; eye in the gun frame %s' % ('charge', rig.clamps - c0, np.round(D.in_gun(G, rig.Ec), 2)))
    paths = {}
    for mode in ('hip', 'ads'):
        c, p, r = build(rig, mode)
        clips.update(c); paths.update(p); rep += r
    return clips, paths, rep


def write(clips, paths):
    os.makedirs(ODIR, exist_ok=True)
    for nm, (a, fr, Gs) in clips.items():
        names = a.names
        vals = []
        for f, pd in enumerate(fr):
            row = []
            for c, n in enumerate(names):
                v = np.asarray(pd[n], float)
                if n.endswith(' pos'):
                    v = np.array([v[0], v[1], v[2], 0.0])
                elif vals and float(v @ np.asarray(vals[-1][c])) < 0:
                    v = -v
                row.append(tuple(v))
            vals.append(row)
        b = a.frames[0]['bounds']
        data = X.build_skc(names, vals, FT if len(fr) > 1 else a.frameTime, b[0:3], b[3:6], a.frames[0]['radius'])
        open(os.path.join(ODIR, 'dbs_%s.skc' % nm), 'wb').write(data)
    json.dump(paths, open(os.path.join(L.BUILD, 'hand_paths.json'), 'w'))


def gun_anim(nm):
    nm = nm[:-4] if nm.endswith('_ads') else nm
    nm = 'reload_single_first' if nm == 'reload_single_l' else nm          # the gun's own row keeps its name
    return nm if nm in ('fire', 'reload', 'reload_single', 'reload_single_first', 'reload_end') else 'idle'


def sheet(clips, nm, frames, out, cam='eye', W=None, H=None, fov=None, cols=4):
    from PIL import Image, ImageDraw
    W = W or int(os.environ.get('DBS_W', 560)); H = H or int(os.environ.get('DBS_H', 340))
    fov = fov or float(os.environ.get('DBS_FOV', 74.0 if nm.endswith('_ads') or nm == 'charge' else 90.0))
    a, fr, Gs = clips[nm]
    rig_ax = GA.barrels_R(GA.OPEN)
    ims = []
    for f in frames:
        f = min(f, len(fr) - 1)
        pd = fr[f]
        surfs, E, Wb = V.scene(pd, TIK, gun_anim(nm), f / 30.0)
        G = Gs[f]
        cham = D.gun_pt(G, (GA.chambered('dbs_shell_r', GA.OPEN)[1] + GA.chambered('dbs_shell_l', GA.OPEN)[1]) / 2 * S) * S
        up = np.array([0, 0, 1.0])
        if cam == 'eye':
            eye, look, fv = E, E + np.array([1.0, 0, 0]), fov
        elif cam == 'close':
            eye, look, fv = E, cham, 30.0
        elif cam == 'side':
            eye, look, fv = cham + np.array([-1.0, 16.0, 2.0]), cham, 50.0
        elif cam == 'right':
            eye, look, fv = cham + np.array([-1.0, -16.0, 3.0]), cham, 50.0
        else:
            eye, look, fv, up = cham + np.array([-3.0, 0.0, 17.0]), cham, 50.0, np.array([1.0, 0, 0])
        rgb, ids, dep = V.raster.render({'surfs': surfs}, eye, look, up, fov=fv, W=W, H=H, bg=(150, 160, 170), znear=1.0, tex=True)
        Lt = np.array([0.4, 0.5, 0.75]); Lt /= np.linalg.norm(Lt)
        shade = np.ones(ids.shape); m = ids >= 0
        for si, s in enumerate(surfs):
            P = s['P']; t_ = s['tri']
            nn = np.cross(P[t_[:, 1]] - P[t_[:, 0]], P[t_[:, 2]] - P[t_[:, 0]])
            nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
            k = 0.45 + 0.55 * np.abs(nn @ Lt)
            sel = m & (ids // 1000000 == si)
            shade[sel] = k[ids[sel] % 1000000]
        im = Image.fromarray(np.clip(rgb * shade[:, :, None], 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        if cam == 'eye':                                  # the centre box (middle 20 %)
            d.rectangle([W * 0.4, H * 0.4, W * 0.6, H * 0.6], outline=(255, 255, 0))
        d.text((4, 2), '%s f%d %s' % (nm, f, cam), fill=(255, 255, 0))
        ims.append(im)
    cols = min(cols, len(ims)); rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGB', (cols * W, rows * H))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * W, (i // cols) * H))
    sh.save(out, quality=85)
    print('wrote', out)


def main():
    cmd = sys.argv[1]
    clips, paths, rep = bake_all()
    if cmd == 'bake':
        write(clips, paths)
        print('\n'.join(rep))
    elif cmd == 'report':
        print('\n'.join(rep))
    else:
        nm = sys.argv[2]
        sheet(clips, nm, [int(x) for x in sys.argv[3].split(',')], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else 'eye')


if __name__ == '__main__':
    main()

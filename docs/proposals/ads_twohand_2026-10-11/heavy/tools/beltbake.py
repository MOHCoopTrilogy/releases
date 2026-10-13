"""Belt-fed guns: the reloads to the acceptance rules - M1919 .30 cal portable (30calportable.tik, name "M1919 30cal").
HIP rows coopr_m1919_30cal_reload / _reload_empty, AIMED rows coopr_m1919_30cal_reload_ads / _reload_empty_ads.

The gun (gun frame x forward, y right, z DOWN, tik-scaled u): top cover x 4.9..16.6 on the bone `cover`, hinged at
its FRONT end, opens 75 deg; the belt hangs from the feedway on the LEFT (surface belt x 12.1..16.5, y -3.2..-1.5,
z -4.6..2.2; the server hides it clip frames 34-56 and shows the prop models/ammo/coop_belt_30cal.tik on the off-hand
tag frames 32-58); charging handle = a bar out of the RIGHT side (bone `chandle`, x 9.05..9.89, y 0.72..3.58,
z -3.1..-2.26, travel 3.2 u). The released hands clip (viewmodel/coop_reload/m1919_reload.skc, reload audit
2026-10-05) worked all of it with OPEN, FLAT hands (bug-3872) and threw the muzzle up through the centre of the view.

Technique (the released choreography, its order kept; every hold a closed hand):
  * the LEFT hand leaves its support under the receiver, takes the cover's rear end from above (palm down over it,
    thumb toward the shooter, fingers over its top down the right flank) and swings it open, riding the cover;
  * it takes the old belt's end at the feedway (a fist, thumb up, the belt hanging from it), strips it out to the
    left and down to the pouch, brings a fresh belt up, lays its end on the feed tray and seats it;
  * it takes the open cover's rear end again, swings it down and presses it shut;
  * rounds left = a round is chambered: back to the support, nothing more;
  * EMPTY: the gun is brought back up into the aim on both hands; there the left hand under the receiver holds it,
    the RIGHT hand leaves the pistol grip, hooks the charging handle overhand (palm down on the bar, the wrist behind it), hauls
    it back and lets it fly; back to the grip. ONE pull (the released gun clip pulled twice in 0.4 s in EVERY reload).
  * AIMED: the open cover stands 11 u above the receiver - it cannot be worked on the sights. The gun comes straight
    down out of the aim to a work pose under the centre box, muzzle down so that the open cover stays under the
    box, and returns to the exact aim. The same hand work as at the hip (one choreography, two gun places).
  * weight: gunphys class `m1919` (14 kg).

GUN CLIPS (same length as the released one, 98 frames - the server reads the `reload` row):
  coop_30cal_reload_loaded.skc  cover open f14-21, shut f63-69, the handle does not move   -> tik row `reload`
  coop_30cal_reload_empty.skc   the same + one handle pull f84-87, home f90               -> rows `reload_empty`,
                                                                                             `reload_ads_empty` (cgame only)

    cd heavy/assets; python ../tools/beltbake.py [hip|ads|gun|all] [--only loaded|empty] [--set k=v ...] [--root dir]
"""
import sys, os, json, hashlib, argparse, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
import heavybake as HB
import heavylib as HL
import gunphys
import gunskc
H, R, V, CTL = HB.H, HB.R, HB.V, HB.CTL
K = H.K
SIGHT = 'm1919'
TIK = 'models/weapons/30calportable.tik'
GUNPATH = 'models/weapons/30calportable'
GUNSRC = 'coop_30cal_reload.skc'                         # the released gun clip (cover + handle channels)
SRC = 'viewmodel/coop_reload/m1919_reload.skc'           # the released hands clip: channel set, frame count, frame time
HIPPOSE = 'viewmodel/mg/barpose.skc'
AIMPOSE = 'viewmodel/mg/coop_m1919_ads_hand.skc'         # handpose.py m1919 (row coopr_m1919_30cal_charge)
VDIR = 'viewmodel/coop_m1919'
N = 97
NG = 98
TRAVEL = 3.2                                             # handle travel, u (released clip: 2.91 x the tik's scale 1.1)
COVJ = os.path.join(hv.LANE, 'm1919cover.json')

gunphys.CLASSES['m1919'] = dict(m=14.0, f2=1.6, f1=1.0, z=0.68, sag=(0.20, 0.0, 3.0, 0.0, 0.0), magw=0.06,
                                tr=(0.030, 0.08, 0.11, 0.018, 0.010), tr2=0.25)
gunphys.ACTIONS.update({
    # (drop, roll, pitch, side, back) velocity change for mass 1, pulse length in frames; + roll = top to the right,
    # + pitch = muzzle down, + side = to the left, + back = toward the shooter
    'bf_cover_up':    ((-10.0, -20.0, -50.0, 0.0, 0.0), 3.0),    # the cover hauled up and thrown open: the rear end follows the hand
    'bf_cover_stop':  ((6.0, 10.0, 60.0, 0.0, -10.0), 1.5),      # it hits its stop past the vertical
    'bf_belt_out':    ((0.0, -60.0, 0.0, 40.0, 0.0), 3.0),       # the old belt stripped out to the left
    'bf_belt_in':     ((14.0, 40.0, 20.0, -30.0, 0.0), 3.0),     # the fresh belt laid on the tray and pushed against the stop
    'bf_cover_shut':  ((40.0, 20.0, 150.0, 0.0, 0.0), 2.0),      # the cover slapped shut: the muzzle is knocked down
    'bf_hand_on':     ((-16.0, 0.0, -60.0, -3.0, 3.0), 4.0),     # the support hand comes up under the receiver and lifts
    'bf_grip_off':    ((8.0, -20.0, 30.0, 4.0, -4.0), 3.0),      # the firing hand lets go of the grip
    'bf_handle_back': ((6.0, 110.0, -40.0, -14.0, 190.0), 3.5),  # the handle hauled back against the spring
    'bf_handle_stop': ((0.0, 40.0, -60.0, 0.0, 90.0), 1.5),      # the bolt hits the rear
    'bf_handle_fwd':  ((6.0, -70.0, 110.0, 8.0, -230.0), 2.0),   # let go: the bolt runs home, the gun is thrown forward
    'bf_grip_on':     ((-8.0, 10.0, -30.0, 0.0, 8.0), 3.0),      # the firing hand takes the grip again
})

# clip frames (30 / s). The server: prop on the off-hand tag 32-58, the gun's belt hidden 34-56.
T_LOADED = dict(off=(6, 10), cov_on=13, cov_open=(14, 21), cov_let=23, belt_on=30, belt_out=(34, 38), pouch=(41, 44), lay=49,
                seat=53, belt_off=58, cov2_on=62, cov_shut=(63, 69), press=71, cov_off=73, on=(79, 86),
                down=(1, 7), turn_in=(4, 11), turn_out=(75, 86), up=(82, 94))
# EMPTY: the cover shut, the gun turns upright and comes back up INTO THE AIM on both hands; the handle (right side,
# 5 u under the sight line: under the centre box) is worked there, the gun on target (run e1: worked at the `down`
# pose the handle sat on the frame's bottom edge and the hand under it was out of view)
T_EMPTY = dict(T_LOADED, cov_off=71, on=(74, 79), turn_out=(70, 78), up=(73, 82), reach=(79, 83), pull=(84, 87), fwd=(89, 90),
               rleave=92, grip=(92, 96))

KINDS = {
    # HIP: the eye is the hip pose's eyes bone (above and LEFT of the gun). For the cover and the belt the gun is rolled
    # top-to-the-right (the feed side up, as aimed) and brought toward the middle; for the handle (EMPTY) it is rolled
    # the other way so that its right side shows (`hwork`)
    'hip': dict(hip=True, pose=HIPPOSE, pivot_pt=(-5.0, 0.0, 0.0),
                work=dict(roll=30.0, pitch=6.0, yaw=8.0, move=(0.0, 3.0, 2.0)),
                hwork=dict(roll=-35.0, pitch=4.0, yaw=6.0, move=(0.0, 2.5, 2.0)),
                pouch=(4.0, 10.0, -17.0), out='coop_m1919_reload_hip%s.skc'),
    # AIMED: straight down out of the aim, muzzle down, the open cover's end under the centre box
    'ads': dict(hip=False, pose=AIMPOSE, pivot_pt=(-5.0, 0.0, 0.0),
                down=dict(roll=0.0, pitch=0.0, yaw=0.0, move=(0.5, 0.0, -4.0)),
                work=dict(roll=55.0, pitch=10.0, yaw=0.0, move=(2.0, 0.8, -1.0)),
                pouch=(4.0, 10.0, -17.0), out='m1919_reload_%sads.skc'),
}


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def mkrel(xdir, ydir, grip_pt, grip_local):
    """hand-to-gun relation (rows, skc units): the hand's local x (along the fingers) and y (out of the palm) as gun
    frame directions, its local point `grip_local` (u) on the gun point `grip_pt` (u)"""
    x = unit(xdir); y = np.asarray(ydir, float); y = unit(y - (y @ x) * x); z = np.cross(x, y)
    M = np.eye(4); M[0, :3] = x; M[1, :3] = y; M[2, :3] = z
    M[3, :3] = (np.asarray(grip_pt, float) - np.asarray(grip_local, float) @ M[:3, :3]) / R.S
    return M


def rmap(f):
    """our clip frame -> the released gun clip's frame whose COVER pose it shows (opens 2 frames earlier, shuts 1 earlier)"""
    a, b = T_LOADED['cov_open']; c, d = T_LOADED['cov_shut']
    if f < a:
        return 0
    if f <= b:
        return f + 16 - a
    if f < c:
        return 30
    if f <= d:
        return f + 1
    return 97


def covers():
    """the cover's rigid move in the gun frame for every frame of the RELEASED gun clip (rows 4x4, u; Kabsch on the
    vertices that the clip moves) -> m1919cover.json"""
    if os.path.isfile(COVJ):
        return [np.array(m) for m in json.load(open(COVJ))]
    RT = os.path.normpath(os.path.join(hv.LANE, '..', 'rifles', 'tools'))
    sys.path.insert(0, RT)
    import g43irons as G
    g0 = G.gungeo.load_gun(TIK, 'reload', 0); g1 = G.gungeo.load_gun(TIK, 'reload', 30)
    P0 = np.vstack([s['P'] for s in g0['surfs']]); P1 = np.vstack([s['P'] for s in g1['surfs']])
    mv = np.linalg.norm(P1 - P0, axis=1) > 0.3
    out = []
    for f in range(NG):
        Pf = np.vstack([s['P'] for s in G.gungeo.load_gun(TIK, 'reload', f)['surfs']])[mv]
        A = P0[mv]; ca, cb = A.mean(0), Pf.mean(0)
        U, S_, Vt = np.linalg.svd((A - ca).T @ (Pf - cb))
        d = np.sign(np.linalg.det(U @ Vt))
        Rm = U @ np.diag([1, 1, d]) @ Vt                   # rows: p' = p @ Rm + t
        M = np.eye(4); M[:3, :3] = Rm; M[3, :3] = cb - ca @ Rm
        assert np.abs(A @ Rm + M[3, :3] - Pf).max() < 0.05, f
        out.append(M)
    json.dump([m.tolist() for m in out], open(COVJ, 'w'))
    return out


def cover_M(f):
    M = covers()[rmap(f)].copy()
    M[3, :3] /= R.S
    return M


def handle_u(t, f):
    if 'pull' not in t or f <= t['pull'][0]:
        return 0.0
    if f <= t['pull'][1]:
        return HB.ease((f - t['pull'][0]) / float(t['pull'][1] - t['pull'][0]))
    if f <= t['fwd'][0]:
        return 1.0
    if f <= t['fwd'][1]:
        u = (f - t['fwd'][0]) / float(t['fwd'][1] - t['fwd'][0])
        return 1.0 - u * u
    return 0.0


def cam(pose, hip):
    if not hip:
        return HL.cam_of(pose, SIGHT)
    a = R.load(R.ANIM + pose)
    pc = R.pose_dict(a, a.numFrames - 1)
    Wc = R.evaluate(pc)
    Wcc = V.evaluate_ctl(pc, CTL)
    corr = V.rig_target(Wcc, V.SIGHTS[SIGHT])
    corr = dict(ax=np.array([0, 0, 1.0]), ang=0.0, T=np.zeros(3), cant=0.0, relief=0.0, E=Wcc['eyes bone'][3, 0:3] * R.S, F=corr['F'], R=corr['R'])
    C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']; C[3, 0:3] *= R.S
    Mcam = C @ V.model_to_cam(corr)
    Gs = Wc['tag_weapon_right'].copy(); Gs[3, 0:3] *= R.S
    return Gs, Mcam


def V3(o, k, d):
    v = o.get(k, d)
    return np.array(v, float)


def spec(kind, empty, o):
    g = dict(KINDS[kind])
    t = dict(T_EMPTY if empty else T_LOADED); t.update({k[2:]: v for k, v in o.items() if k.startswith('t.')})
    n = N - 1
    hip = g['hip']
    Gs, Mcam = cam(g['pose'], hip)

    def gpt(p):
        return (np.r_[np.asarray(p, float), 1.0] @ Gs @ Mcam)[0:3]
    pivot = gpt(g['pivot_pt'])
    AIM = dict(aim=1, fing='pose')
    # ---- the three holds (gun frame) ----
    # cover: palm down over the cover's rear end, thumb to the shooter, fingers over the top and down the right flank
    REL_COV = mkrel(V3(o, 'cov_x', (0.15, 0.80, -0.58)), V3(o, 'cov_y', (0.0, 0.58, 0.80)),
                    V3(o, 'cov_pt', (6.6, -0.5, -4.7)), V3(o, 'cov_loc', (4.3, 1.5, 0.2)))
    # belt: a fist on the belt's lower rear corner, thumb up, palm to the gun - the belt's upper end stands out of it
    # (held at its top end the belt was hidden behind the fist: the eye looks along it)
    REL_BELT = mkrel(V3(o, 'belt_x', (0.85, 0.35, -0.38)), V3(o, 'belt_y', (-0.3, 0.93, 0.2)),
                     V3(o, 'belt_pt', (12.3, -2.6, 1.0)), V3(o, 'belt_loc', (4.6, 1.2, -0.2)))
    # handle: OVERHAND - palm down on the bar, the wrist behind it, fingers hooked down over its front (palm up, the
    # service drill, showed the eye an open palm and a raised thumb beside the receiver: offline sheet e2)
    REL_HND = mkrel(V3(o, 'hnd_x', (0.98, -0.17, 0.05)), V3(o, 'hnd_y', (-0.05, 0.0, 1.0)),
                    V3(o, 'hnd_pt', (9.45, 2.9, -2.70)), V3(o, 'hnd_loc', (5.6, 1.5, 0.1)))

    def Kc(f, **kw):
        return dict(dict(relT=REL_COV @ cover_M(f), fing='pose'), **kw)

    def Kb(add=(0, 0, 0), **kw):
        return dict(dict(relT=REL_BELT, gun_add=tuple(add), fing='pose'), **kw)

    def Cb(p, **kw):
        return dict(dict(relT=REL_BELT, cam=tuple(p), fing='pose'), **kw)
    POUCH = tuple(o.get('pouch', g['pouch']))
    co, cs, on = t['cov_open'], t['cov_shut'], t['on']
    lp = {0: AIM, t['off'][0]: AIM,
          t['off'][1]: Kc(0, gun_add=tuple(V3(o, 'cov_app', (-2.0, -3.0, 0.5)))),
          t['cov_on']: Kc(0)}
    for f in range(co[0], co[1] + 1):
        lp[f] = Kc(f)
    lp[t['cov_let']] = Kc(co[1], gun_add=(-1.0, -2.0, 0.5))
    lp[t['belt_on'] - 4] = Kb((-1.5, -2.5, 0.0))
    lp[t['belt_on']] = Kb()
    lp[t['belt_out'][0]] = Kb()
    lp[t['belt_out'][1]] = Kb(tuple(V3(o, 'belt_outv', (-0.5, -3.5, 1.5))))
    lp[t['pouch'][0]] = Cb(POUCH); lp[t['pouch'][1]] = Cb(POUCH)
    lp[t['lay']] = Kb(tuple(V3(o, 'belt_lay', (0.0, -2.5, -2.5))))
    lp[t['seat']] = Kb()
    lp[t['belt_off']] = Kb()
    for f in range(t['cov2_on'], cs[1] + 1):
        lp[f] = Kc(f)
    lp[min(t['press'], t['cov_off'] - 1)] = Kc(cs[1], gun_add=(0.0, 0.0, 0.15))
    lp[t['cov_off'] + 1] = Kc(cs[1], gun_add=(-0.8, -2.0, -1.5))
    lp[on[1] - 3] = dict(aim=1, cam_add=(-0.5, 0.8, -1.5), fing='pose')
    for f in range(on[1], n + 1):
        lp[f] = AIM
    rp = {0: AIM, n: AIM}
    fa = {}
    # the left hand: its support cup, closed further - on the cover (an overhand grasp), round the belt's end (a fist)
    cg, bg = float(o.get('cov_curl', 1.0)), float(o.get('belt_curl', 1.0))
    lk = [(t['off'][0], 0.0), (t['cov_on'] - 1, 0.7 * cg), (t['cov_on'], cg), (co[1], cg), (t['cov_let'], 0.8 * cg), (t['belt_on'] - 3, 0.6 * bg),
          (t['belt_on'], 1.4 * bg), (t['belt_off'], 1.4 * bg), (t['belt_off'] + 2, 0.7 * cg), (t['cov2_on'], cg), (t['cov_off'], cg),
          (t['cov_off'] + 3, 0.5 * cg), (on[1] - 2, 0.0)]
    for fg in range(5):
        for seg, dg in ((tuple(zip(('', '1', '2'), o.get('thumb', (22.0, 48.0, 40.0))))) if fg == 0 else (('', 14.0), ('1', 38.0), ('2', 28.0))):
            fa['Bip01 L Finger%d%s rot' % (fg, seg)] = [(k_, w_ * dg) for k_, w_ in lk]
    ev = [(co[0] + 1, 'bf_cover_up'), (co[1], 'bf_cover_stop'), (t['belt_out'][0] + 1, 'bf_belt_out'), (t['seat'] - 2, 'bf_belt_in'),
          (cs[1], 'bf_cover_shut')]
    sup = float(o.get('sup', 0.45))
    support = [(0, 1), (t['off'][0], 1), (t['off'][1], sup)]
    if empty:
        TR = float(o.get('travel', TRAVEL))

        def Hd(back, extra=(0, 0, 0), **kw):
            return dict(dict(relT=REL_HND, gun_add=tuple(np.array([-back, 0.0, 0.0]) + np.array(extra, float)), fing='pose'), **kw)
        rp[t['reach'][0]] = AIM
        rp[t['reach'][0] + 2] = dict(aim=1, gun_add=(0.4, 1.2, 0.2), fing='pose')
        rp[t['reach'][1] - 1] = Hd(0.0, tuple(V3(o, 'hnd_app', (-1.5, 1.0, 1.0))))
        rp[t['reach'][1] + 1] = Hd(0.0)
        for f in range(t['pull'][0], t['fwd'][0] + 1):
            rp[f] = Hd(TR * handle_u(t, f))
        rp[t['fwd'][1] + 1] = Hd(TR, (-0.5, 0.8, 1.4))
        rp[t['grip'][1] - 2] = dict(aim=1, gun_add=(0.2, 0.8, 0.3), fing='pose')
        for f in range(t['grip'][1], n + 1):
            rp[f] = AIM
        c0, c1, c2, c3 = t['reach'][1] - 2, t['pull'][0] - 1, t['fwd'][1] + 1, t['grip'][1] - 1
        hc = float(o.get('hnd_curl', 1.0))
        for fg in (0, 1, 2, 3, 4):
            for seg, dg in ((('', 20.0), ('1', 40.0), ('2', 35.0)) if fg == 0 else (('', 26.0), ('1', 60.0), ('2', 40.0)) if fg == 1 else (('', 8.0), ('1', 18.0), ('2', 14.0))):
                fa['Bip01 R Finger%d%s rot' % (fg, seg)] = [(c0, 0.0), (c1, dg * hc), (c2, dg * hc), (c3, 0.0)]
        # the support hand is back under the receiver before the firing hand lets go: one hand and the shoulder strap of
        # the arm hold 14 kg at the aim for a third of a second
        rs = float(o.get('rsup', 0.6))
        support += [(on[0], sup), (on[1], 1), (t['reach'][0], 1), (t['reach'][0] + 3, rs), (t['grip'][0], rs), (t['grip'][1], 1)]
        ev += [(on[1] - 4, 'bf_hand_on'), (t['reach'][0] + 1, 'bf_grip_off'), (t['pull'][0], 'bf_handle_back'), (t['pull'][1] - 1, 'bf_handle_stop'),
               (t['fwd'][1] - 1, 'bf_handle_fwd'), (t['grip'][1] - 2, 'bf_grip_on')]
    else:
        support += [(on[0], sup), (on[1], 1)]
        ev += [(on[1] - 4, 'bf_hand_on')]
    ph = gunphys.simulate(n + 1, 1 / 30.0, 'm1919', support=support, mag=[(0, 1), (t['belt_out'][0], 1), (t['belt_out'][1], 0), (t['lay'], 0), (t['seat'], 1)],
                          events=sorted(ev), strength=float(o.get('strength', g.get('strength', 1.0))), fade=10)
    X = ph['X'].copy()
    ph['X'] = X
    dip = {f: tuple(float(v) for v in X[f]) for f in range(n + 1)}
    def pose_T(key):
        d = dict(g[key]); d.update({k[len(key) + 1:]: (tuple(v) if isinstance(v, list) else float(v)) for k, v in o.items() if k.startswith(key + '.')})
        return Gs @ Mcam @ HL.xform(d, pivot)
    dn, up, ti, to = t['down'], t['up'], t['turn_in'], t['turn_out']
    gun_abs = []
    if g.get('down'):          # AIMED: straight down out of the aim first, turned to the work pose only under the box; back the same way
        gun_abs.append(dict(T=pose_T('down'), keys={0: 0.0, dn[0]: 0.0, dn[1]: 1.0, up[0]: 1.0, up[1]: 0.0, n: 0.0}))
    gun_abs.append(dict(T=pose_T('work'), keys={0: 0.0, ti[0]: 0.0, ti[1]: 1.0, to[0]: 1.0, to[1]: 0.0, n: 0.0}))
    if empty and g.get('hwork'):
        gun_abs.append(dict(T=pose_T('hwork'), keys={0: 0.0, to[0]: 0.0, to[1]: 1.0, t['fwd'][1] + 1: 1.0, n: 0.0}))
    hvec = -REL_BELT[3, 0:3] * R.S                 # the prop's own frame IS the gun's: its origin on the gun's while the hand holds the seated belt
    kw = dict(gun=SIGHT, charge=g['pose'], hip=SRC, fixed_right=True, weight=dict(on=False), handover=False,
              dip=dip, dip_after=True, gun_abs=gun_abs, left_path=lp, right_path=rp,
              ltag=dict(pinch=(0.0, 0.0, 0.0), hold_vec=tuple(hvec), axes=np.eye(3)),
              elbow_vec={'L': (0.0, 0.6, -1.0), 'R': (0.0, -0.6, -1.0)},
              elbow_down={'L': [(0, 0.0), (t['cov_on'], 2.0), (on[0], 2.0), (n, 0.0)]},
              finger_add=fa, dip_pivot=float(pivot[0]))
    if hip:
        kw['hip_cam'] = True
    if empty:
        kw['elbow_down']['R'] = [(0, 0.0), (t['reach'][1], 1.5), (t['rleave'], 1.5), (n, 0.0)]
    return kw, ph, n + 1, t, g


def gun_clips(root):
    """the two gun clips (98 frames as the released one): cover re-timed, the handle still / pulled once"""
    raw = R.vfs.read(GUNPATH + '/' + GUNSRC)
    a = R.skc_io.read(raw)
    assert a.numFrames == NG, a.numFrames
    ci = {nm: i for i, nm in enumerate(a.names)}
    for name, t in (('loaded', T_LOADED), ('empty', T_EMPTY)):
        keyed = {'cover rot': [], 'cover pos': [], 'chandle pos': []}
        for f in range(NG):
            r = rmap(min(f, N - 1))
            keyed['cover rot'].append(list(a.values[r][ci['cover rot']]))
            keyed['cover pos'].append(list(a.values[r][ci['cover pos']]))
            keyed['chandle pos'].append([-(TRAVEL / 1.1) * handle_u(t, f), 0.0, 0.0, 0.0])
        dst = os.path.join(root, (GUNPATH + '/coop_30cal_reload_%s.skc' % name).replace('/', os.sep))
        gunskc.write(dst, raw, NG, keyed, frame_time=a.frameTime)
        print('gun clip ->', GUNPATH + '/coop_30cal_reload_%s.skc' % name, NG, 'frames', hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8])


def tik():
    """the staged tik: m1919sights.tik() (new skelmodel + sight surface) + the reload rows"""
    import m1919sights
    p = m1919sights.tik()
    t = open(p, 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in t else '\n'
    a = t.index('\treload \t\tcoop_30cal_reload.skc'); b = t.index('\tfire\t\t30cal.skc')
    blk = t[a:b]
    m = re.search(r'\t\tclient\s*\{.*?\n\t\t\}', blk, re.S); assert m
    srv = blk[:m.start()].replace('coop_30cal_reload.skc', 'coop_30cal_reload_loaded.skc')
    new = ('\t//HZM coop [ads heavy 2026-10-13] (tools/beltbake.py) the server-read row keeps its LENGTH (98 frames) and its commands;' + nl
           + '\t//its clip: cover open f14-21 / shut f63-69, the charging handle does not move (rounds left = a round is chambered)' + nl
           + srv + blk[m.start():]
           + '\t//cgame-only rows (an EMPTY gun, hip / aimed): the same + ONE pull of the charging handle f84-90' + nl
           + '\treload_empty\t\tcoop_30cal_reload_empty.skc' + nl + '\treload_ads_empty\tcoop_30cal_reload_empty.skc' + nl)
    t = t[:a] + new + t[b:]
    code = re.sub(r'//[^\n]*', '', t); dpt = 0
    for ln in code.splitlines():
        dpt += ln.count('{') - ln.count('}'); assert dpt >= 0
    assert dpt == 0
    open(p, 'wb').write(t.encode('latin-1'))
    print('tik ->', p)


def bake(kind, root, only=None, o=None):
    rep = {}
    for empty in (False, True):
        key = 'empty' if empty else 'loaded'
        if only and only != key:
            continue
        kw, ph, n, t, g = spec(kind, empty, dict(o or {}))
        rc = H.auto_recipe('bar_reload', **kw)
        H.RECIPES['bar_reload'] = rc
        sk, _ = H.bake('bar_reload', CTL)
        assert sk.numFrames == n, (sk.numFrames, n)
        bts = R.skc_io.write(sk)
        out = VDIR + '/' + (g['out'] % (('_empty' if kind == 'hip' else 'empty_') if empty else ''))
        dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        X = ph['X']
        print('m1919', kind, key, '->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])
        print('   ', ph['report'])
        rep['%s_%s' % (kind, key)] = dict(peak_deg=round(ph['peak_deg'], 2), settle_s=round(ph['settle_s'], 2))
    return rep


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', nargs='?', default='all'); ap.add_argument('--only'); ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--root', default='.')
    a = ap.parse_args()
    o = {}
    for kv in a.set:
        k, v = kv.split('=', 1)
        try:
            o[k] = json.loads(v)
        except ValueError:
            o[k] = v
    rep = {}
    if a.kind in ('all', 'gun'):
        gun_clips(a.root)
        if a.root == '.':
            tik()
    for kind in (['hip', 'ads'] if a.kind == 'all' else [a.kind]):
        if kind == 'gun':
            continue
        rep.update(bake(kind, a.root, a.only, o))
    if a.root == '.' and not o and rep:
        p = os.path.join(hv.LANE, 'heavyphys.json')
        d = json.load(open(p)) if os.path.isfile(p) else {}
        d.setdefault('m1919', {}).update(rep)
        json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)

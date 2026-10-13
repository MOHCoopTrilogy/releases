"""Aimed bolt cycle of a bolt rifle to the 2026-10-12 standard: the HANDS are key_bolt's (the right hand rides the
gun's own bolt bone from the retail knob grip - the action really works, by the hand on the real control side), the
GUN no longer takes hand-set keys: its motion is the response of gunphys (a mass on a damped spring in the shoulder) to

  * where the shooter HOLDS the rifle while he works the bolt (`hold`: eased off the cheek along the sight line so the
    bolt has room to come back, canted toward the working hand) - the spring follows it, so the rifle lags and settles;
  * the bolt's four strokes as impulses at the frames the gun's own rechamber animation makes them (lift, back,
    forward, down);
  * the firing hand leaving the grip and landing on it again (support track + `grip_on`).

    cd rifles/assets; python ../tools/boltphys.py kar98 [--set k=v ...] [--print]
writes models/human/animation/<out> under the current directory (the staging root).
"""
import sys, os, json, argparse, hashlib, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(HERE, '..', '..', 'tools')
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); sys.path.insert(0, SHARED); sys.path.insert(0, HERE)
import staged      # the staged tiks / gun clips (rechamber_ads, boltcap.py) are read as loose files
_c = os.getcwd(); os.chdir(T)
import key_bolt as K
import anahip, boltgrip
os.chdir(_c)
import gunphys
R = K.R
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))

# a bolt rifle in the shoulder: heavier and slower-settling than the pistols (4.6 Hz) and the shared 'rifle' class's
# two-handed hold; "support" here is the FIRING hand (1 = on the grip, 0 = off it: butt in the shoulder + the left
# hand on the fore-end alone - the rifle rolls a little toward the missing hand and the butt settles)
# 2026-10-12 (user: "bolt actions should ideally not move much from locking onto target", "you can have weight etc
# but ideally it stays primarily on target"): the firing hand off the grip no longer lets the muzzle sag (pitch 0.35
# -> 0.10 deg) - the butt stays in the shoulder and the left hand holds the fore-end steady
RIFLE = dict(m=4.1, f2=2.6, f1=2.0, z=0.62, sag=(0.04, 0.8, 0.10, -0.03, -0.04), magw=0.0,
             tr=(0.012, 0.10, 0.07, 0.010, 0.004), tr2=0.5)
# impulses for mass 1 (drop u/s, roll deg/s, pitch deg/s, side u/s, back u/s), length in frames.
# roll + = top to the RIGHT (toward the working hand), pitch + = muzzle down, back + = into the shoulder
# 2026-10-12, on target: the PITCH share of every stroke is about half of the first version's - a muzzle swing about
# the butt is what takes the front sight off the target (x1.6: the front sight is 65 u from the butt, 40 u from the
# eye). The weight is carried by the ROLL toward the hand and the tug back / shove forward along the sight line,
# which leave the front sight where it is.
gunphys.ACTIONS.update({
    'rb_up':    ((-1.2, -26.0, -2.5, -0.8, 0.0), 2.5),    # knob lifted on the right: that side is pushed up
    'rb_back':  ((0.4, 30.0, -7.0, -1.5, 11.0), 2.5),     # dragged rearward, high and right of the bore: into the shoulder, round to the hand
    'rb_stop':  ((0.0, 6.0, -3.5, 0.0, 6.0), 1.5),        # the bolt hits its stop
    'rb_fwd':   ((0.3, -12.0, 7.0, 0.8, -13.0), 2.5),     # shoved forward: the rifle goes forward, muzzle dips a little
    'rb_down':  ((1.5, 16.0, 4.0, 1.0, -2.0), 2.0),       # knob slapped down: the right side is pushed down, into battery
    'rb_grip':  ((0.4, 5.0, 1.0, 0.4, 1.0), 3.0),         # the firing hand lands on the grip again
})

GUNS = {
    # frames are the view clip's; up / back / fwd / down = (first, last) frame of that stroke in the gun's own clip
    'kar98': dict(recipe='kar98_rechamber', out='viewmodel/rifle/kar98_rechamber_ads.skc',
                  sight='kar98', aim='viewmodel/kar_stand00.skc', anim='rechamber_ads',
                  off=(2, 7), up=(8, 10), back=(13, 15), fwd=(23, 24), down=(27, 29), on=(36, 42),
                  hold=(0, 11, 27, 42),       # the hold eases in over 0-11 (receiver down first, forward as the bolt opens; 0-7 read as a snap forward in run rb5), out over 27-42
                  ease=0.0, hold_set=dict(back=-3.0),   # A as shown to the user (run rb8): head 3 u back off the comb
                  # 1c (2026-10-12): the knob sits IN the curled fingers while it is hauled back; the grip opens to the
                  # fingertips for the shove forward and the turn-down, where the hand would cross the box's rim
                  rc=dict(knob_off={8: (0.0, 1.15, 0.55), 12: (0.0, 1.15, 0.55), 15: (0.0, 0.75, 0.3), 21: (0.0, 0.75, 0.3), 24: (0.0, 1.2, 0.6), 30: (0.0, 1.2, 0.6)})),
    # Springfield M1903 (56 x 1/30 s): lift 8-10, back 15-17, forward 27-28, down 30-32, hand on the knob 8-31
    'springfield': dict(recipe='springfield_rechamber', out='viewmodel/rifle/springfield_rechamber_ads.skc',
                        sight='springfield_unscoped', aim='viewmodel/sprng_stand00.skc', anim='rechamber_ads',
                        off=(2, 7), up=(8, 10), back=(15, 17), fwd=(27, 28), down=(30, 32), on=(38, 44), hold=(0, 11, 30, 45),
                        ease=0.0, # 90 deg lift (boltcap.py): the open knob stands at the box's right rim - fingertips there, deeper in the hand while the bolt is back
                        rc=dict(knob_off={8: (0.0, 1.6, 0.95), 14: (0.0, 1.6, 0.95), 18: (0.0, 1.2, 0.6), 25: (0.0, 1.2, 0.6), 28: (0.0, 1.6, 0.95), 33: (0.0, 1.6, 0.95)})),
    # Mosin-Nagant (45 x 1/30 s): lift 7-12, back 12-15, forward + down 26-27
    'mosin': dict(recipe='mosin_rechamber', out='viewmodel/mosin_nagant/mosin_rechamber_ads.skc',
                  sight='mosin_nagant_rifle', aim='viewmodel/kar_stand00.skc', anim='rechamber_ads',
                  off=(1, 6), up=(7, 12), back=(12, 15), fwd=(26, 26), down=(27, 27), on=(34, 40), hold=(0, 10, 27, 41),
                  ease=0.0, rc=dict(knob_off=(0.0, 0.5, 0.25))),
    # Lee-Enfield (45 x 1/30 s): lift 7-12, back 12-15, forward + down 24-27; the rear sight sits on the receiver
    # bridge just ahead of the eye, so the rifle is eased further forward than the Kar98
    'enfield': dict(recipe='enfield_rechamber', out='viewmodel/enfield/enfield_rechamber_ads.skc',
                    sight='lee_enfield', aim='viewmodel/kar_stand00.skc', anim='rechamber_ads',
                    off=(1, 6), up=(7, 12), back=(12, 15), fwd=(24, 25), down=(26, 27), on=(34, 40), hold=(0, 10, 27, 41),
                    ease=0.0, hold_set=dict(back=-1.0),   # 3.3 u read as a pump (run rb13): the rifle stays put
                    rc=dict(knob_off=(0.0, 0.3, 0.15))),
}
# the hold while the bolt is worked: (drop u, roll deg, pitch deg, side u, back u).
# ON TARGET (2026-10-12, user: "bolt actions should ideally not move much from locking onto target when the bolt is
# pulled back", "you can have weight etc but ideally it stays primarily on target"). The first version of this lane
# (drop 1.2 u, muzzle 2.3 deg DOWN) took the sights 3.4 deg off the target for a second per shot - rejected.
# Facts the hold answers (offline, rpart.py, Kar98):
#   * fully locked (`--set drop=0 --set pitch=0`, variant A): the rifle's OWN open bolt handle stands in the right
#     half of the centre box - 8 % at the lift, 17-20 % with the bolt back, 19 frames; no hand in the box.
#   * a cant does not clear it (up to 30 deg either way: 11-15 %) - the handle's root is on the bolt body, on the
#     centre line. Only lowering the RECEIVER does: 0.75 u reads 1.4 %, 1.1 u 0.1 %.
#   * so the default lowers the receiver and NOT the front sight: the butt eases down 2.5 u while the muzzle comes
#     up 2.2 deg about it - the front sight stays on the target (65 u from the butt: -2.5 + 65 * tan 2.2 = 0), the
#     rear sight / receiver / bolt sink 1.25 u under the box, the shooter looks over the rear sight at the front one.
#     The head comes back off the comb (3 u forward along the sight line) and the rifle cants 2 deg to the hand.
#   * PER GUN (`ease`, u the receiver comes down; drop = ease * 65 / 32, pitch = -atan(ease / 32)): the Kar98's
#     turned-down handle stands highest when open (1.25); the Springfield's and the Mosin's need 0.4 (0.5 staged);
#     the Lee-Enfield's handle is at the rear and stays under the sight line: fully locked (0), 1.1 % offline.
#     `--set ease=x` / `--set drop=.. --set pitch=..` override.
HOLD = dict(drop=None, roll=2.0, pitch=None, side=0.0, back=-2.0)
EASE = 1.25
# USER DECISION 2026-10-12 (after the A / C GIF): **variant A - the rifle stays LOCKED on the sights while the hand
# works the bolt**; the open bolt handle / bolt body in the middle of the view is accepted, for every bolt-action
# rifle. No easing of the receiver for the between-shot cycle: every gun's `ease` is 0 now. Variant C stays
# reproducible and unused: `--set ease=1.25` (Kar98; 0.5 Springfield / Mosin) `--set back=-2`.
EASE = 0.0
# THE FRONT SIGHT IS THE PIVOT (2026-10-12 late; user: "weight yes, drift no"). gunphys turns the rifle about the butt,
# so every stroke's pitch and the spring's overshoot swung the MUZZLE: the staged Kar98 clip itself put the front
# sight 0.67 deg above the target with the bolt back and 0.23 deg under it at the turn-down (rpart.py --track) - most
# of what read as "leaving the target", and it was the clip, not the shot's recoil. The support hand holds the
# fore-end on the target; what gives is the butt in the shoulder. So after the simulation the DROP of every frame is
# re-solved so the front sight keeps only FS_KEEP of its excursion (height of the front sight against the aim =
# -drop - FS_LEN * sin(pitch); FS_LEN = butt pivot to front sight). The reaction stays in full at the receiver end,
# in the roll and in the fore-aft tug. `--set fskeep=1` = the unconstrained simulation.
FS_KEEP = 0.25
FS_LEN = 73.6      # calibrated on the Kar98 with rpart.py --track (65 left the front sight 0.35 deg HIGH in the hold)
RCV_LEN = 33.0     # butt pivot to the receiver / rear sight
SC = dict(k=1.0)


def slerp_x(q0, q1, s):
    """slerp that extrapolates (s outside 0..1 keeps turning about the same axis)"""
    q0 = np.asarray(q0, float); q1 = np.asarray(q1, float)
    d = float(q0 @ q1)
    if d < 0:
        q1, d = -q1, -d
    th = np.arccos(min(1.0, d))
    if th < 1e-6:
        return q0.copy()
    return (np.sin((1 - s) * th) * q0 + np.sin(s * th) * q1) / np.sin(th)


def phys(g, n, ft, hold=HOLD, sc=1.0):
    a0, a1 = g['off']; o0, o1 = g['on']; h0, h1, h2, h3 = g['hold']
    hv = (hold['drop'], hold['roll'], hold['pitch'], hold['side'], hold['back'])
    z = (0.0,) * 5
    ev = [(g['up'][0], 'rb_up', sc), (g['back'][0], 'rb_back', sc), (g['back'][1], 'rb_stop', sc),
          (g['fwd'][0], 'rb_fwd', sc), (g['down'][0], 'rb_down', sc), (o1 - 3, 'rb_grip', sc)]
    # the rifle leaves and re-enters the aim DOWN first (drop + muzzle dip only: its outline stays inside the settled
    # aim's own), and goes forward / cants only once it is under the centre box - run ra4 read 3-5 % for four frames
    # each way with all five numbers eased together (the support hand's fingers crossed the box rim)
    dn = (hold['drop'], 0.0, hold['pitch'], 0.0, 0.0)
    m1 = h0 + 0.45 * (h1 - h0); m2 = h2 + 0.5 * (h3 - h2)
    r = gunphys.simulate(n, ft, RIFLE, support=[(0, 1), (a0, 1), (a1, 0), (o0, 0), (o1, 1)], events=ev,
                         pose=[(0, z), (h0, z), (m1, dn), (h1, hv), (h2, hv), (m2, dn), (h3, z)], fade=5)
    return r, ev


def bake(name, root, hold=HOLD, sc=1.0, show=False, suffix=''):
    g = dict(GUNS[name])
    g['out'] = g['out'][:-4] + suffix + '.skc'
    hold = dict(hold, **{k: v for k, v in g.get('hold_set', {}).items() if hold.get(k) is None or k not in ('drop', 'pitch')})
    ease = hold.pop('ease', g.get('ease', EASE))
    if hold['drop'] is None:
        hold['drop'] = round(ease * FS_LEN / (FS_LEN - RCV_LEN), 3)
    if hold['pitch'] is None:
        hold['pitch'] = round(-float(np.degrees(np.arctan(ease / (FS_LEN - RCV_LEN)))), 3)
    rc = copy.deepcopy(K.RECIPES[g['recipe']])
    hip = R.load(R.ANIM + rc['hip'])
    n, ft = hip.numFrames, hip.frameTime
    r, ev = phys(g, n, ft, hold, sc)
    keep = float(hold.pop('fskeep', g.get('fs_keep', FS_KEEP)))
    X = r['X'].copy()
    zf = -X[:, 0] - g.get('fs_len', FS_LEN) * np.sin(np.radians(X[:, 2]))
    X[:, 0] += (1.0 - keep) * zf
    print('    front sight (clip alone, before -> after the pivot): %.2f..%.2f u -> %.2f..%.2f u' % (
        zf.min(), zf.max(), (keep * zf).min(), (keep * zf).max()))
    # gunphys (drop, roll, pitch, side, back) -> key_bolt (dip, cant, yaw, fwd, left, up); cant + = top to the LEFT
    rc['keys'] = {f: (float(X[f, 2]), float(-X[f, 1]), 0.0, float(-X[f, 4]), float(X[f, 3]), float(-X[f, 0])) for f in range(n)}
    # the cant turns about the SIGHT LINE (camera axis through the eye), not the bore 3 u under it: a roll about the
    # bore carried the front sight 0.2 deg sideways off the target
    rc['pivot_cant'] = (0.0, 0.0, 0.0)
    for k, v in g.get('rc', {}).items():
        rc[k] = v
    K.RECIPES['_phys_' + name] = rc
    # knob_off (gun frame u: x fwd, +y RIGHT, +z DOWN): the knob grip moved off the knob centre - the retail grip has
    # the knob deep in the palm, so the palm and the fingers lie over the receiver LEFT of the knob (at the cheek that
    # is the right half of the centre box); moved right / down the knob is held by the fingers and the hand's bulk is
    # beside the box. Weighted like the knob-grip fingers (in over the reach, out over the return).
    # grip_rot (deg about the gun's x fwd / y right / z down axes, through the KNOB, in that order) turns the whole hand
    # about the knob it holds; finger_s {finger digit: (base, middle, tip)} scales each joint's curl between the aim
    # grip's (0) and the knob grip's fist (1; > 1 tighter, < 0 opens it) - so the knob can be held by the thumb and the
    # first two fingers with the hand's bulk off to the lower right, instead of a fist beside it (2026-10-12, 1c).
    off = rc.get('knob_off')
    grot, fsc, pin = rc.get('grip_rot'), rc.get('finger_s'), rc.get('grip_pin')
    orig, cnt = K.solve_arms, [0]
    if off is not None or grot or fsc or pin:
        (k0, k1), (r0, r1), (t0, t1) = rc['knob'], rc['reach'], rc['ret']
        Kt, kft2 = anahip.knob_traj(K.V.GUNTIK[rc['gun']], g.get('anim', 'rechamber'))
        chg = R.load(R.ANIM + rc['charge']); pc_ = R.pose_dict(chg, chg.numFrames - 1)
        gs_ = rc.get('grip_src')
        fist = R.pose_dict(R.load(R.ANIM + gs_['hip']), gs_['frame']) if gs_ else R.pose_dict(hip, rc.get('grip_ref', k0))
        I3 = np.eye(3)
        if pin:
            pf = dict(pc_)
            for ch in fist:
                if ' Finger' in ch and ch.startswith('Bip01 R') and ch.endswith(' rot'):
                    dg, sfx = ch.split('Finger')[1].split(' ')[0][0], ch.split('Finger')[1].split(' ')[0][1:]
                    s_ = (fsc or {}).get(dg, (1.0, 1.0, 1.0))[('', '1', '2').index(sfx)] if sfx in ('', '1', '2') else 1.0
                    pf[ch] = slerp_x(pc_.get(ch, fist[ch]), fist[ch], s_)
                elif ch not in pf:
                    pf[ch] = fist[ch]
            Wf = R.evaluate(pf)
            Hi = R.inv(Wf['Bip01 R Hand'])
            loc = lambda b: (Wf['Bip01 R ' + b] @ Hi)[3, 0:3]
            unit = lambda v: np.asarray(v, float) / np.linalg.norm(v)
            ax_l = unit(loc('Finger2'))                              # wrist -> middle knuckle
            ac_l = loc('Finger4') - loc('Finger1'); ac_l = unit(ac_l - (ac_l @ ax_l) * ax_l)    # index -> little finger
            nl = np.cross(ax_l, ac_l)
            if nl @ (loc('Finger22') - loc('Finger2')) < 0:          # the curled fingertips lie on the PALM side
                nl = -nl
            # the pinch point: between two joints of the posed hand, `lift` u out of the palm side (the knob's radius)
            g_l = loc(pin.get('a', 'Finger11')) * (1 - pin.get('t', 0.5)) + loc(pin.get('b', 'Finger21')) * pin.get('t', 0.5) + \
                nl * pin.get('lift', 0.0) / R.S + ax_l * pin.get('along', 0.0) / R.S
            # target attitude in the gun frame (x fwd, y RIGHT, z DOWN): fingers along `dir`, palm facing `palm`
            ag = unit(pin['dir']); ng = np.asarray(pin['palm'], float); ng = unit(ng - (ng @ ag) * ag)
            Bl = np.array([ax_l, nl, np.cross(ax_l, nl)]); Bg = np.array([ag, ng, np.cross(ag, ng)])
            Rl2g = Bl.T @ Bg                                         # row vectors: v_local @ Rl2g = v_gun

        def sa(pd, Wc, HR, HL, Gads, pole_bias=None):
            f = cnt[0]; cnt[0] += 1
            w = 0.0 if (f <= r0 or f >= t1) else K.ease((f - r0) / float(k0 - r0)) if f < k0 else 1.0 if f <= k1 else \
                1.0 - K.ease((f - t0) / float(t1 - t0))
            if w > 0:
                HR = HR.copy()
                if pin:
                    # ABSOLUTE GRIP: the hand's attitude is given in the GUN frame (where the fingers point, where the
                    # palm faces) and the pinch point of the posed hand is put on the knob; the hand follows the knob's
                    # point through lift / back / forward / down without turning with the bolt (a ball knob turns in
                    # the fingers). Blended in over the reach and out over the return.
                    kk = Kt[min(len(Kt) - 1, int(round(f * ft / kft2)))] / R.S
                    HT = np.eye(4)
                    HT[0:3, 0:3] = Rl2g @ Gads[0:3, 0:3]
                    kw = (np.append(kk, 1.0) @ Gads)[0:3] + (np.array(pin.get('off', (0, 0, 0)), float) / R.S) @ Gads[0:3, 0:3]
                    HT[3, 0:3] = kw - g_l @ HT[0:3, 0:3]
                    HR = K.B.blend_H(HR, HT, w)
                if grot:
                    kk = Kt[min(len(Kt) - 1, int(round(f * ft / kft2)))] / R.S
                    Rr = R.axis_angle_rows([1.0, 0, 0], grot[0] * w) @ R.axis_angle_rows([0, 1.0, 0], grot[1] * w) @ \
                        R.axis_angle_rows([0, 0, 1.0], grot[2] * w)
                    HR = HR @ R.inv(Gads) @ K.B.H(I3, -kk) @ K.B.H(Rr, np.zeros(3)) @ K.B.H(I3, kk) @ Gads
                if off is not None:
                    # a dict {frame: (x, y, z)} = the grip SLIDES on the knob through the cycle (monotone cubic): the
                    # knob deep in the fingers while it is hauled back (clear of the box), out at the fingertips for
                    # the lift and the turn-down, where the knob stands at the box's rim
                    o_ = off if not isinstance(off, dict) else \
                        [K.pchip(sorted(off), [off[k_][i_] for k_ in sorted(off)], f) for i_ in range(3)]
                    HR[3, 0:3] += (np.array(o_, float) / R.S * w) @ Gads[0:3, 0:3]
                if fsc:
                    for dg, ss in fsc.items():
                        for j, sfx in enumerate(('', '1', '2')):
                            ch = 'Bip01 R Finger%s%s rot' % (dg, sfx)
                            if ch in pd and ch in fist:
                                pd[ch] = slerp_x(pc_.get(ch, fist[ch]), fist[ch], w * ss[j])
            return orig(pd, Wc, HR, HL, Gads)
        K.solve_arms = sa
    # THE HAND RIDES THE BOLT AS IT IS SHOWN WHILE AIMING: key_bolt asks for the gun's `rechamber` trajectories; the
    # aimed view shows `rechamber_ads` (boltcap.py: the stroke stops short of the eye), so the target gun's knob point
    # and bolt bone come from that clip. A borrowed grip's SOURCE (another gun's hip clip) keeps its hip `rechamber`.
    ganim, tgt = g.get('anim', 'rechamber'), K.V.GUNTIK[rc['gun']]
    ok_, oc_ = anahip.knob_traj, boltgrip.chamber_traj
    src_tik = rc.get('grip_src', {}).get('tik')
    calls = [0]

    def kt(tik, anim):
        # the borrowed-grip source call comes with the SOURCE tik; for the Kar98 (its own grip_ref) both are the target
        return ok_(tik, ganim if (tik == tgt and anim == 'rechamber') else anim)

    def ct(tik, anim='rechamber', bone=None):
        return oc_(tik, ganim if (tik == tgt and anim == 'rechamber') else anim, bone)
    anahip.knob_traj, boltgrip.chamber_traj = kt, ct
    try:
        sk, rep = K.key('_phys_' + name, CTL)
    finally:
        K.solve_arms = orig
        anahip.knob_traj, boltgrip.chamber_traj = ok_, oc_
    bts = R.skc_io.write(sk)
    dst = os.path.join(root, 'models', 'human', 'animation', g['out'].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bts)
    print(name, '->', g['out'], n, 'frames x %.4f s' % ft, hashlib.md5(bts).hexdigest()[:8])
    print('   ', r['report'])
    # the reaction alone (hold pose removed): what each stroke does to the rifle
    r0 = gunphys.simulate(n, ft, RIFLE, support=[(0, 1), (n - 1, 1)], events=ev, fade=5)['X']
    print('    strokes alone: pitch %.2f..%.2f deg, roll %.2f..%.2f deg, back %.2f..%.2f u, drop %.2f..%.2f u' % (
        r0[:, 2].min(), r0[:, 2].max(), r0[:, 1].min(), r0[:, 1].max(), r0[:, 4].min(), r0[:, 4].max(), r0[:, 0].min(), r0[:, 0].max()))
    if show:
        for f in range(0, n, 2):
            print('    %2d ' % f + ' '.join('%6.2f' % v for v in X[f]))
    json.dump(dict(gun=name, hold=hold, scale=sc, fs_keep=keep, events=[list(e) for e in ev], cls=RIFLE, report=r['report'],
                   md5=hashlib.md5(bts).hexdigest()), open(dst[:-4] + '_phys.json', 'w'), indent=1)
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--root', default='.'); ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--scale', type=float, default=2.5); ap.add_argument('--suffix', default=''); ap.add_argument('--print', action='store_true')
    ap.add_argument('--rc', action='append', default=[], help='recipe override k=python literal (knob_roll=60, pivot_cant=(0,0,0))')
    a = ap.parse_args()
    import ast
    for kv in a.rc:
        k, v = kv.split('=', 1)
        for nm in a.gun.split(','):
            GUNS[nm].setdefault('rc', {})[k] = ast.literal_eval(v)
    hold = dict(HOLD)
    for kv in a.set:
        k, v = kv.split('=')
        if k == 'hold':
            for nm in a.gun.split(','):
                GUNS[nm]['hold'] = tuple(int(x) for x in v.split(','))
        else:
            hold[k] = float(v)      # drop / roll / pitch / side / back, or ease
    for nm in a.gun.split(','):
        bake(nm, a.root, hold, a.scale, a.print, a.suffix)

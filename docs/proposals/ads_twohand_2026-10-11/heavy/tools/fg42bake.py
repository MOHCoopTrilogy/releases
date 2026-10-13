"""FG 42 (the scoped gun and the FG 42 Irons): the reloads to the acceptance rules - HIP (both guns, rows fg42_reload /
fg42_reload_empty) and AIMED on the iron sights (rows coopr_fg_42_irons_reload[_empty]_ads + _adsb).

The gun: a 20-round box magazine in from the LEFT side (surface fg42clip: x -4.0..0.6, y -7.6..-0.8, z -4.1..-3.0;
gun frame x forward, y right, z DOWN, u) and a cocking handle on the RIGHT of the receiver (fg42handle.py: surface
coop_handle on the bone coop_chg, 5.0 u back along the painted slot). Technique:
  * the LEFT hand leaves the handguard, cups the magazine from below - palm under it, fingers hooked up over its front
    edge (the StG 44 magazine grip of the retail art, turned 90 deg about the gun's long axis onto a sideways
    magazine) - draws it out to the left, takes it down to the pouch, brings the fresh one up and pushes it home;
  * rounds left = the bolt is cocked: nothing more, the hand goes back to the handguard;
  * EMPTY: the left hand is back on the handguard and holds the gun, the RIGHT hand leaves the pistol grip, hooks the
    handle (it is on the firing side - the hand that suits it), hauls it back and lets it fly forward; back to the grip.
  * weight: gunphys class `fg42` (5.3 kg with a loaded magazine hanging on the left side) - the support hand leaving,
    the magazine's weight going and coming, the tug / push on the magazine, the handle against its spring.

SERVER WINDOW (run hj26, both guns the same): the gun's own magazine is hidden 0.66-1.32 s (FG42.tik `reload` row
frames 20-40), the prop models/ammo/fg42clip.tik rides the off-hand tag 0.67-1.34 s (torso row coop_reload_fg42),
ammunition arrives at 1.35 s, the torso leaves the reload at 2.33 s, the weapon's `reload` row (WEAPON_RELOADING)
ends at 3.0 s. So: magazine out AT frame 20, home AT frame 40; rounds left = 71 frames (2.34 s, as retail); empty =
91 frames (3.0 s, the weapon row's length).

    cd heavy/assets; python ../tools/fg42bake.py [hip|ads|adsb|gun] [--only loaded|empty] [--set k=v ...] [--root dir]
"""
import sys, os, json, hashlib, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
import heavybake as HB          # the lane's physics tables, ease(), POUCH; its bake of other guns is not touched
import heavylib as HL
import gunphys
import gunskc
H, R, V, CTL = HB.H, HB.R, HB.V, HB.CTL
K = H.K
HJ = json.load(open(os.path.join(hv.LANE, 'fg42handle.json')))
KNOB = np.array(HJ['knob'], float)
TRAVEL = float(HJ['travel'])
ROWS = H.fps_rows()
SIGHT = 'fg42_irons'
AIMPOSE = 'viewmodel/fg42/coop_fg42_irons_aim.skc'
HIPPOSE = 'viewmodel/fg42/fg42_stand_idle.skc'
SRC = 'viewmodel/fg42/fg42_stand_reload.skc'          # the retail hip hands clip: channel set and frame time
MPCLIP = 'viewmodel/mp44/mp44_reload.skc'             # donor of the magazine grip (frame 12)
MPF = 12
VDIR = 'viewmodel/fg42'
GUNPATH = 'models/weapons/fg42'
GUNSRC = 'fg42.skc'

gunphys.CLASSES['fg42'] = dict(m=5.3, f2=2.6, f1=1.75, z=0.56, sag=(0.10, -1.0, 3.3, 0.0, 0.0), magw=0.12,
                               tr=(0.030, 0.14, 0.17, 0.022, 0.010), tr2=0.25)
gunphys.ACTIONS.update({
    # (drop, roll, pitch, side, back) for mass 1; + roll = top to the right, + side = to the left, + back = to the shoulder
    'fg_mag_tug':     ((4.0, 50.0, 12.0, 26.0, 0.0), 3.0),      # hauled out to the LEFT against its catch: the gun goes with it
    'fg_mag_free':    ((-10.0, 40.0, -45.0, -30.0, 0.0), 3.0),  # it lets go: 0.65 kg lighter on the left, the gun springs back
    'fg_mag_in':      ((0.0, -30.0, 10.0, -34.0, 2.0), 4.0),    # pushed in from the left: the gun is shoved to the right
    'fg_mag_home':    ((2.0, -45.0, 14.0, -50.0, 3.0), 1.5),    # ... and driven home onto its catch
    'fg_hand_on':     ((-20.0, 0.0, -75.0, -4.0, 4.0), 4.0),    # the support hand comes up under the handguard and lifts
    'fg_grip_off':    ((6.0, -18.0, 24.0, 4.0, -4.0), 3.0),     # the firing hand lets go of the grip: the left hand has it alone
    'fg_handle_grab': ((4.0, 36.0, 10.0, -3.0, 0.0), 2.0),      # fingers close on the right-side handle
    'fg_handle_back': ((8.0, 95.0, 28.0, -12.0, 150.0), 3.5),   # hauled back against the spring: into the shoulder, rolls to the hand
    'fg_handle_stop': ((0.0, 36.0, -50.0, 0.0, 70.0), 1.5),     # the carrier hits the rear stop
    'fg_handle_fwd':  ((5.0, -60.0, 90.0, 7.0, -180.0), 2.0),   # let go: the mass runs forward and stops, the muzzle dips
    'fg_grip_on':     ((-8.0, 10.0, -30.0, 0.0, 8.0), 3.0),     # the firing hand takes the grip again
})

# the magazine grip: StG 44 retail frame 12 (wrist behind, palm on the magazine's left face, fingers round its front)
# turned -90 deg about the gun's x axis (palm UNDER a magazine that lies to the left, thumb outboard, fingers hooked up
# over the front edge) and moved so that the palm face / the front edge / the hand's middle land on the FG 42 magazine's
# bottom face (z -3.03) / front edge (x 0.63) / y -4.3
GRIP_MOVE = (-8.4, -6.7, -4.13)
RX = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])            # rows: x -> x, y -> -z, z -> y
# the prop models/ammo/fg42clip.tik in the gun's frame (Kabsch fit of its 48 vertices on the gun's fg42clip surface,
# residual 1e-4 u): p_gun = p_prop @ PROP_R + PROP_T
PROP_R = np.array([[0.377, 0.418, -0.826], [0.360, 0.756, 0.547], [0.854, -0.503, 0.135]])
PROP_T = np.array([-0.751, -8.905, -4.849])

# AIMED: the gun leaves its aim STRAIGHT DOWN first (`down`, with the sag), turns to the work pose only under the box
# (`cant_in`), and comes back the same way (cant off, then `up`) - canted while still high the rear sight ring and the
# receiver left the aim's own silhouette sideways through the box (run hj29: 3.8 % standing, 2.7 % lean left at clip
# frame 14; run hj30: 3.0 % at frame 10). An emptied gun STAYS down between the magazine and the handle.
T_LOADED = dict(off=(5, 10), grab=18, out=(20, 23), show_out=(25, 26), pouch=(29, 31), show_in=(34, 35), well=38, seat=40,
                hold=44, leave=48, on=(52, 60), down=(5, 11), cant_in=(11, 18), cant_out=(46, 54), up=(54, 64))
T_EMPTY = dict(T_LOADED, on=(50, 57), cant_out=(46, 53),
               hcant_in=(55, 62), reach=(58, 64), pull=(66, 70), fwd=(71, 73), rleave=76, grip=(79, 85), hcant_out=(75, 82), up=(80, 88))

KINDS = {
    # HIP: the eye is the hip pose's eyes bone. For the magazine the gun is turned a little toward the left hand and
    # lifted; for the handle the left hand rolls it top-to-left so that the right side faces the eye.
    'hip': dict(hip=True, pose=HIPPOSE, pivot_pt=(-6.0, -0.9, 0.6), dip_pivot=-2.0,
                cant=dict(roll=6.0, pitch=-3.0, yaw=2.0, move=(0.0, 0.6, 0.8)),
                hcant=dict(roll=-26.0, pitch=-3.0, yaw=5.0, move=(-0.5, 1.4, 1.2)),
                show=(13.0, 8.5, -8.5), pouch=(4.0, 10.0, -17.0), off_add=(-0.6, 1.2, -1.2), leave_add=(-1.0, 1.5, -2.0),
                hk_off=(-2.4, -1.4, -2.0), out='coop_fg42_reload_hip%s.skc'),
    # AIMED: at the cheek the magazine lies 8 deg under the sight line, 4-17 deg left; the handle 8 deg under, 4 deg
    # right. The gun sags when the support hand leaves (class fg42) and the firing hand lets it down a little and
    # cants it top-to-right (the magazine side swings DOWN, away from the box); for the handle it is rolled the other
    # way, held by the left hand.
    'ads': dict(hip=False, pose=AIMPOSE, pivot_pt=(-19.0, -0.9, -0.6), dip_pivot=None,
                down=dict(roll=0.0, pitch=0.0, yaw=0.0, move=(0.6, 0.0, -1.0)),
                cant=dict(roll=14.0, pitch=0.0, yaw=-2.0, move=(1.5, 0.3, -1.0)),
                hcant=dict(roll=-16.0, pitch=0.0, yaw=1.0, move=(1.5, 0.2, -1.5)),
                show=(12.0, 7.5, -6.6), pouch=(4.0, 10.0, -16.0), off_add=(-0.6, 1.0, -1.4), leave_add=(-1.2, 1.5, -2.6),
                hk_off=(-2.4, -1.6, -1.8), out='fg42_irons_reload_%sads.skc'),
}
KINDS['adsb'] = dict(KINDS['ads'], sup=0.3, strength=0.8, out='fg42_irons_reload_%sadsb.skc',
                     down=dict(roll=0.0, pitch=0.0, yaw=0.0, move=(0.6, 0.0, -1.6)),
                     cant=dict(roll=14.0, pitch=0.0, yaw=-2.0, move=(1.5, 0.3, -1.6)),
                     hcant=dict(roll=-16.0, pitch=0.0, yaw=1.0, move=(1.5, 0.2, -2.0)))


def cam(pose, hip):
    """-> (Gs gun tag in the model, scaled rows; Mcam model -> camera) of the pose clip's last frame"""
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


def grip_rel(o):
    """the left hand's relation to the gun while it holds the SEATED magazine (rows, skc units)"""
    mp = R.load(R.ANIM + MPCLIP)
    W = R.evaluate(R.pose_dict(mp, MPF))
    rel = W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right'])
    X = np.eye(4); X[0:3, 0:3] = RX
    X[3, 0:3] = np.asarray(o.get('grip_move', GRIP_MOVE), float) / R.S
    rel = rel @ X
    yaw = float(o.get('grip_yaw', 0.0))
    if yaw:                                       # about the gun's z axis through the middle of the gripped section
        c = np.array([-1.7, -4.3, -3.0]) / R.S
        P = np.eye(4); P[3, 0:3] = -c
        Q = np.eye(4); Q[0:3, 0:3] = R.axis_angle_rows((0, 0, 1), yaw)
        Pi = np.eye(4); Pi[3, 0:3] = c
        rel = rel @ P @ Q @ Pi
    return rel


def bolt_u(t, f):
    """handle travel 0..1 at clip frame f: hauled back, held a frame, let go (the spring runs it home)"""
    if f <= t['pull'][0]:
        return 0.0
    if f <= t['pull'][1]:
        return HB.ease((f - t['pull'][0]) / float(t['pull'][1] - t['pull'][0]))
    if f <= t['fwd'][0]:
        return 1.0
    if f <= t['fwd'][1]:
        u = (f - t['fwd'][0]) / float(t['fwd'][1] - t['fwd'][0])
        return 1.0 - u * u
    return 0.0


def source(n):
    """the retail hip clip's channel set with n frames (its own frames, the last one held)"""
    c = R.load(R.ANIM + SRC)
    if n <= c.numFrames:
        return None
    return n


_load0 = R.load
_PAD = {'n': 0}


def _load(p):
    c = _load0(p)
    n = _PAD['n']
    if n and p.replace('\\', '/').endswith(SRC) and c.numFrames < n:
        # skc_io.write() packs into the clip's own byte layout: lay the longer clip out afresh (v13: header 48, frame
        # headers 48 each, values 16 per channel, names 32 per channel) - appended frame dicts alone overwrite frame 0
        assert c.version == 13, c.version
        old, nch = c.numFrames, c.numChannels
        k = n - old
        ofs_vals = 48 + 48 * n
        ofs_ch = ofs_vals + n * nch * 16
        c.V = np.concatenate([c.V, np.repeat(c.V[-1:], k, axis=0)], axis=0)
        c.frames = [dict(c.frames[min(f, old - 1)], ofsValues=ofs_vals + f * nch * 16) for f in range(n)]
        c.values = list(c.values) + [c.values[-1] for _ in range(k)]
        c.ofsChannels = ofs_ch
        c.ofsEnd = ofs_ch + 32 * nch
        c.raw = bytes(c.ofsEnd)
        c.numFrames = n
    return c


R.load = _load


def spec(kind, empty, o):
    g = dict(KINDS[kind])
    t = dict(T_EMPTY if empty else T_LOADED); t.update({k[2:]: v for k, v in o.items() if k.startswith('t.')})
    n = (91 if empty else 71) - 1
    hip = g['hip']
    Gs, Mcam = cam(g['pose'], hip)

    def gpt(p):
        return (np.r_[np.asarray(p, float), 1.0] @ Gs @ Mcam)[0:3]
    pivot = gpt(g['pivot_pt'])
    AIM = dict(aim=1, fing='pose')
    on = t['on']
    sup = float(o.get('sup', g.get('sup', 0.0)))
    ev = [(t['out'][0] - 1, 'fg_mag_tug'), (t['out'][0] + 2, 'fg_mag_free'), (t['well'], 'fg_mag_in'), (t['seat'] - 1, 'fg_mag_home'),
          (on[1] - 4, 'fg_hand_on')]
    support = [(0, 1), (t['off'][0], 1), (t['off'][1], sup), (on[0], sup), (on[1], 1)]
    if empty:
        # the firing hand off the grip: the left hand and the shoulder have the gun - a softer hold, not a one-handed one
        rs = float(o.get('rsup', 0.6 + 0.4 * sup))
        support += [(t['reach'][0], 1), (t['reach'][0] + 3, rs), (t['grip'][0], rs), (t['grip'][1], 1)]
        ev += [(t['reach'][0] + 1, 'fg_grip_off'), (t['pull'][0] - 2, 'fg_handle_grab'), (t['pull'][0], 'fg_handle_back'),
               (t['pull'][1] - 1, 'fg_handle_stop'), (t['fwd'][1] - 1, 'fg_handle_fwd'), (t['grip'][1] - 3, 'fg_grip_on')]
    ph = gunphys.simulate(n + 1, 1 / 30.0, 'fg42', support=support,
                          mag=[(0, 1), (t['out'][0], 1), (t['out'][1], 0), (t['well'], 0), (t['seat'], 1)],
                          events=sorted(ev), strength=float(o.get('strength', g.get('strength', 1.0))), fade=12)
    X = ph['X'].copy()
    if not hip:                      # at the cheek the gun does not ride ABOVE its aim (the lane's rule, heavybake)
        for j in (0, 2):
            X[:, j] = np.where(X[:, j] < 0.0, X[:, j] * 0.15, X[:, j])
    ph['X'] = X
    dip = {f: tuple(float(v) for v in X[f]) for f in range(n + 1)}

    def pose_T(key):
        d = dict(g[key]); d.update({k[len(key) + 1:]: (tuple(v) if isinstance(v, list) else float(v)) for k, v in o.items() if k.startswith(key + '.')})
        return Gs @ Mcam @ HL.xform(d, pivot)
    ci, co = t['cant_in'], t['cant_out']
    gun_abs = []
    if g.get('down'):
        dn, up = t['down'], t['up']
        gun_abs.append(dict(T=pose_T('down'), keys={0: 0.0, dn[0]: 0.0, dn[1]: 1.0, up[0]: 1.0, up[1]: 0.0, n: 0.0}))
    gun_abs.append(dict(T=pose_T('cant'), keys={0: 0.0, ci[0]: 0.0, ci[1]: 1.0, co[0]: 1.0, co[1]: 0.0, n: 0.0}))
    if empty:
        hi, ho = t['hcant_in'], t['hcant_out']
        gun_abs.append(dict(T=pose_T('hcant'), keys={0: 0.0, hi[0]: 0.0, hi[1]: 1.0, ho[0]: 1.0, ho[1]: 0.0, n: 0.0}))
    RELK = grip_rel(o)
    FING = ('clip', MPCLIP, MPF)
    HALF = ('clip', MPCLIP, max(0, MPF - 5))       # the donor's hand closing on its magazine: half open
    out = float(o.get('mag_out', 1.6))

    def Kq(dy, **kw):                              # ON the magazine, `dy` u out of the well (to the left)
        return dict(dict(relT=RELK, gun_add=(0.0, -dy, 0.0), fing=FING), **kw)

    def Cq(p, **kw):                               # carrying it: the grip's rotation, the wrist at a camera point
        return dict(dict(relT=RELK, cam=tuple(p), fing=FING), **kw)
    SHOW = np.array(o.get('show', g['show']), float)
    SHOW2 = SHOW + np.array([-0.5, 1.0, -0.8])
    POUCH = tuple(o.get('pouch', g['pouch']))
    lp = {0: AIM, t['off'][0]: AIM,
          t['off'][0] + 3: dict(aim=1, cam_add=tuple(g['off_add']), fing='pose'),
          # comes up under it from behind-below with the hand already closed to the grip (run hj28: the donor's half-open
          # frame was an open hand with the fingers up at the corner of the centre box)
          t['grab'] - 3: Kq(0.0, gun_add=tuple(g.get('under', (-0.8, -0.6, 2.2)))),
          t['grab']: Kq(0.0), t['out'][0]: Kq(0.0),
          t['out'][1]: Kq(out),
          t['show_out'][0]: Cq(SHOW), t['show_out'][1]: Cq(SHOW2),
          t['pouch'][0]: Cq(POUCH), t['pouch'][1]: Cq(POUCH),
          t['show_in'][0]: Cq(SHOW2), t['show_in'][1]: Cq(SHOW),
          t['well']: Kq(out), t['seat']: Kq(0.0), t['hold']: Kq(0.0),
          t['leave']: dict(aim=1, cam_add=tuple(g['leave_add']), fing='pose'),
          on[1] - 3: dict(aim=1, cam_add=(-0.5, 0.5, -1.2), fing='pose')}
    for f in range(on[1], n + 1):
        lp[f] = AIM
    rp = {0: AIM, n: AIM}
    fa = {}
    # the left hand's fingers CLOSE over the magazine's front edge while it has it (the donor grip is a loose one)
    lc = float(o.get('mag_curl', 1.0))
    for fg in (1, 2, 3, 4):
        for seg, dg in (('', 8.0), ('1', 55.0), ('2', 35.0)):
            fa['Bip01 L Finger%d%s rot' % (fg, seg)] = [(t['grab'] - 5, 0.0), (t['grab'] - 2, 0.6 * dg * lc), (t['grab'], dg * lc), (t['hold'], dg * lc), (t['hold'] + 3, 0.0)]
    if empty:
        # the firing hand hooks the handle with the grip it has on the PISTOL GRIP (an upright bar too): its relation to
        # the gun, moved so that the crook of its fingers (HOOK0, gun frame: behind the first phalanges, centre plane,
        # middle / ring finger height) lands on the handle's bar, pitched `hk_pitch` deg about the bar's cross axis
        # (wrist DOWN: the forearm comes up from below the receiver instead of along the comb) and `hk_out` u outboard
        # (the fingertips hook the bar, they do not go through the receiver wall)
        ap_ = R.load(R.ANIM + g['pose']); Wp_ = R.evaluate(R.pose_dict(ap_, ap_.numFrames - 1))
        relR = Wp_['Bip01 R Hand'] @ R.inv(Wp_['tag_weapon_right'])
        HOOK0 = np.array(o.get('hk_hook', (-1.5, -0.1, 1.3)), float)
        tgt = KNOB + np.array([0.0, float(o.get('hk_out', g.get('hk_out', 0.7))), 0.0])
        P_ = np.eye(4); P_[3, 0:3] = -HOOK0 / R.S
        Q_ = np.eye(4); Q_[0:3, 0:3] = R.axis_angle_rows((0, 1, 0), float(o.get('hk_pitch', g.get('hk_pitch', 35.0))))
        Pi_ = np.eye(4); Pi_[3, 0:3] = tgt / R.S
        RELH = relR @ P_ @ Q_ @ Pi_

        def Hd(back, extra=(0, 0, 0), **kw):
            return dict(dict(relT=RELH, gun_add=tuple(np.array([-back, 0.0, 0.0]) + np.array(extra, float)), fing='pose'), **kw)
        rp[t['reach'][0]] = AIM
        rp[t['reach'][0] + 2] = dict(aim=1, gun_add=(0.3, 0.8, -0.3), fing='pose')            # off the grip, out to the right
        rp[t['reach'][1]] = Hd(0.0, (-0.4, 0.5, 0.2))
        for f in range(t['pull'][0], t['fwd'][0] + 1):
            rp[f] = Hd(TRAVEL * bolt_u(t, f))
        # let go: the handle is gone, the hand - still closed - drops away under the receiver (run hj30: uncurling there
        # put the pose's straight trigger finger up into the box, 5-6 % for three capture frames)
        rp[t['fwd'][1] + 1] = Hd(TRAVEL, (-0.4, 0.8, 1.2))
        rp[t['rleave']] = Hd(TRAVEL, (-1.5, 1.2, 2.6))
        for f in range(t['grip'][1], n + 1):
            rp[f] = AIM
        rp[t['grip'][1] - 3] = dict(aim=1, gun_add=(0.2, 0.6, 0.3), fing='pose')
        # the firing hand's own grip curl is what hooks the handle; a little more curl while it is on it
        c0, c1, c2, c3 = t['reach'][1] - 2, t['pull'][0] - 1, t['rleave'], t['grip'][0] + 3
        # (run hj28, hip: the pistol-grip pose has the trigger finger straight and the others loose - on the handle
        # it read as an open hand) the index closes with the rest, all four a little tighter
        cs = float(o.get('hk_curl', 1.0))
        for fg in (1, 2, 3, 4):
            for seg, dg in ((('', 28.0), ('1', 62.0), ('2', 40.0)) if fg == 1 else (('', 8.0), ('1', 16.0), ('2', 12.0))):
                fa['Bip01 R Finger%d%s rot' % (fg, seg)] = [(c0, 0.0), (c1, dg * cs), (c2, dg * cs), (c3, 0.0)]
    # the magazine prop rides the left wrist, turned like the GUN: it coincides with the gun's own magazine while the
    # hand holds the seated one (the server shows the prop and hides the gun's in the same frames)
    hvec = PROP_T - RELK[3, 0:3] * R.S
    kw = dict(gun=SIGHT, charge=g['pose'], hip=SRC, fixed_right=True, weight=dict(on=False), handover=False,
              dip=dip, dip_after=True, gun_abs=gun_abs, left_path=lp, right_path=rp,
              ltag=dict(pinch=(0.0, 0.0, 0.0), hold_vec=tuple(hvec), axes=PROP_R),
              elbow_vec={'L': (0.0, 0.4, -1.0), 'R': (0.0, -0.5, -1.0)},
              elbow_down={'L': [(0, 0.0), (t['grab'], 2.5), (on[0], 2.5), (n, 0.0)]})
    kw['dip_pivot'] = g['dip_pivot'] if g['dip_pivot'] is not None else float(pivot[0])
    if hip:
        kw['hip_cam'] = True
    if empty:
        kw['elbow_down']['R'] = [(0, 0.0), (t['reach'][1], 1.5), (t['rleave'], 1.5), (n, 0.0)]
    if fa:
        kw['finger_add'] = fa
    return kw, ph, n + 1, t, g


def gun_clip(root):
    """the gun's own clip for an EMPTY reload: the handle bone hauled back and let go in the right hand's frames"""
    raw = R.vfs.read(GUNPATH + '/' + GUNSRC)
    per = np.array(HJ['per_u'], float)
    n = 91
    vals = [list(per * TRAVEL * bolt_u(T_EMPTY, f)) + [0.0] for f in range(n)]
    dst = os.path.join(root, (GUNPATH + '/coop_reload_empty.skc').replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    gunskc.write(dst, raw, n, {HJ['chan']: vals}, frame_time=0.033)
    print('gun clip ->', GUNPATH + '/coop_reload_empty.skc', n, 'frames', hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8],
          '(handle back f%d-%d, home f%d)' % (T_EMPTY['pull'][0], T_EMPTY['pull'][1], T_EMPTY['fwd'][1]))


def bake(kind, root, only=None, o=None):
    rep = {}
    for empty in (False, True):
        key = 'empty' if empty else 'loaded'
        if only and only != key:
            continue
        kw, ph, n, t, g = spec(kind, empty, dict(o or {}))
        _PAD['n'] = n
        rc = H.auto_recipe('fg42_reload', **kw)
        H.RECIPES['fg42_reload'] = rc
        sk, _ = H.bake('fg42_reload', CTL)
        _PAD['n'] = 0
        assert sk.numFrames == n, (sk.numFrames, n)
        bts = R.skc_io.write(sk)
        out = VDIR + '/' + (g['out'] % (('_empty' if kind == 'hip' else 'empty_') if empty else ''))
        dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        X = ph['X']
        print('fg42', kind, key, '->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])
        print('   ', ph['report'])
        print('    sag at the swap: pitch %.1f deg, drop %.2f u; roll swing %.1f deg; side %.2f u; back %.2f u' % (
            float(np.median(X[26:36, 2])), float(np.median(X[26:36, 0])), float(np.abs(X[:, 1]).max()), float(np.abs(X[:, 3]).max()), float(np.abs(X[:, 4]).max())))
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
    for kind in (['hip', 'ads', 'adsb'] if a.kind == 'all' else [a.kind]):
        if kind == 'gun':
            continue
        rep.update(bake(kind, a.root, a.only, o))
    if a.kind in ('all', 'gun'):
        gun_clip(a.root)
    if a.root == '.' and not o:
        p = os.path.join(hv.LANE, 'heavyphys.json')
        d = json.load(open(p)) if os.path.isfile(p) else {}
        d.setdefault('fg42', {}).update(rep)
        json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)

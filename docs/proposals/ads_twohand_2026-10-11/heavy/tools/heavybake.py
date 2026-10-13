"""Aimed reloads of the heavy guns to the user's three rules (2026-10-12) - BAR first, the reference heavy gun.

  1. ON TARGET: the centre box stays clear. The mechanism of a BAR cannot be seen at a cheek weld (the stock hides the
     left-side handle, the magazine well is 18-36 deg below the sight line), so for the work the gun SAGS under the
     box about the butt in the shoulder (what 9 kg does when the support hand leaves - physics, not a key) and the
     firing hand CANTS it (top to the right) to present the well and the handle side; back to the exact aim.
  2. THE WEAPON REACTS: gunphys.py, class and actions scaled for a 9 kg gun in the shoulder (below). No gun key
     except the cant, which is where the shooter holds it; the spring motion goes on top (hold_bake dip_after).
  3. THE ACTION WORKS: the left hand strips the magazine down out of the well, brings the fresh one up from the
     pouch and seats it, slaps it home; on an EMPTY gun it then hooks the left-side operating handle, hauls it back
     and runs it forward - the gun's own `bolt` bone keyed in the same frames (gun clip reload_ads_empty). A gun with
     rounds left is an open-bolt gun still cocked: no handle work (hands clip <row>_ads, gun clip = retail reload).

Frames follow the retail sound (BARReload1.wav: magazine out f12-16, in f40-44, click f52, handle back f67-69,
forward f71-73) and the server's prop window (bar_clip on tag_weapon_left f15-50, the gun's own Clip hidden f18-46).

    cd heavy/assets; python ../tools/heavybake.py bar|mp44 [--only loaded|empty] [--braced] [--set k=v ...]
"""
import sys, os, json, hashlib, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
import heavylib as HL
import gunphys
import gunskc

# ---------------------------------------------------------------------------------------------- physics, heavy guns
# pitch / drop act about the butt in the shoulder (hold_bake dip_pivot = the butt's place down the sight line)
gunphys.CLASSES.update({
    #  BAR M1918A2 8.8 kg empty, 20-round magazine 0.72 kg: a slow hold, a deep one-handed sag, a long settle
    'bar': dict(m=9.0, f2=2.0, f1=1.25, z=0.62, sag=(0.15, 0.0, 4.6, 0.0, 0.0), magw=0.08,
                tr=(0.030, 0.10, 0.14, 0.020, 0.010), tr2=0.25),
    #  StG 44 4.6 kg empty, 30-round magazine 0.9 kg: between the rifles and the light machine guns
    'stg': dict(m=5.4, f2=2.5, f1=1.7, z=0.56, sag=(0.10, 0.0, 3.4, 0.0, 0.0), magw=0.16,
                tr=(0.030, 0.14, 0.17, 0.022, 0.010), tr2=0.25),
    #  DP-28 9.1 kg empty, a loaded 47-round pan 2.8 kg ON TOP: heavier than the BAR, and a quarter of it is the pan
    'dp': dict(m=11.5, f2=1.9, f1=1.2, z=0.64, sag=(0.17, 0.0, 4.2, 0.0, 0.0), magw=0.22,
               tr=(0.030, 0.10, 0.14, 0.020, 0.010), tr2=0.25),
})
gunphys.ACTIONS.update({
    # velocity change for mass 1 in (drop, roll, pitch, side, back) and the pulse length in frames; + roll = top right,
    # + pitch = muzzle down, + side = left, + back = toward the shoulder
    'lg_mag_tug':     ((26.0, 0.0, 70.0, 0.0, 0.0), 3.0),     # the magazine hauled DOWN against its catch: the gun goes with it
    'lg_mag_free':    ((-30.0, 0.0, -110.0, 0.0, 0.0), 3.0),  # it lets go: 0.7 kg lighter, the front springs up
    'lg_mag_in':      ((-14.0, 0.0, -60.0, 0.0, 3.0), 4.0),   # pushed up the well, ahead of the firing hand: the front lifts
    'lg_mag_slap':    ((-34.0, -25.0, -150.0, 0.0, 8.0), 1.5),  # the palm strikes the floor plate
    # ... of a gun half the BAR's weight: the same blow threw the StG 44 1.7 x as far and its front sight touched the
    # box in the left lean (run he2, 2.02 % for two frames) - a lighter magazine is seated with a lighter palm
    'lg_mag_slap_light': ((-22.0, -16.0, -95.0, 0.0, 5.0), 1.5),
    'lg_handle_grab': ((4.0, -40.0, 10.0, 3.0, 0.0), 2.0),    # the hand closes on the left-side handle
    'lg_handle_back': ((8.0, -110.0, 30.0, 14.0, 150.0), 3.5),  # hauled back against the recoil spring: into the shoulder, rolls to the hand
    'lg_handle_stop': ((0.0, -40.0, -55.0, 0.0, 70.0), 1.5),   # the slide hits the rear stop
    'lg_handle_fwd':  ((6.0, 70.0, 95.0, -8.0, -190.0), 2.0),  # run forward: the mass stops in the front, muzzle dips
    'lg_hand_on':     ((-22.0, 0.0, -80.0, -4.0, 4.0), 4.0),   # the support hand comes up under the forearm and lifts
    # a PAN on top (DP-28): thumbed off its catch and lifted - the gun comes up with it a little, then is let go
    'lg_pan_lift':    ((-14.0, 0.0, -45.0, 0.0, 0.0), 3.0),
    'lg_pan_free':    ((10.0, 0.0, 30.0, 0.0, 0.0), 3.0),
    'lg_pan_on':      ((24.0, 0.0, 75.0, 0.0, 2.0), 4.0),      # 2.8 kg set down on the receiver, ahead of the firing hand
    'lg_pan_press':   ((30.0, 8.0, 115.0, 0.0, 4.0), 1.5),     # the palm drives it down onto its catch
})

POUCH = (4.0, 10.0, -16.0)             # camera frame (fwd, left, up): the belt, well under the frame
AIM = dict(aim=1, fing='pose')


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# ------------------------------------------------------------------------------------------------------------- BAR
BAR = dict(
    row='bar_reload', sight='bar', cls='bar', aim='viewmodel/mg/coop_bar_ads_hand.skc', vdir='viewmodel/mg',
    gun_path='models/weapons/bar_lmg', gun_reload='reload_bar.skc', gun_out='coop_reload_ads_empty.skc',
    butt=(-10.8, -0.3, -4.0),          # camera frame: the butt plate in the shoulder (heavylib.gun_pt)
    # the WORK pose the firing hand holds the gun in (on top of the sag): canted, top to the right, and let down out
    # of the cheek weld - 5 u forward, 1.5 u lower. At the cheek the left-side handle ends its travel 5 u from the eye
    # (run hb2: the pulling hand filled the lower left of the view) and the well is under the frame's edge.
    # 0.7 u lower since run hc1: the firing wrist showed pink under the canted gun along the bottom edge (hb7-hb9)
    cant=dict(roll=32.0, pitch=0.0, yaw=-3.0, move=(3.0, 0.4, -0.7)),
    # BRACED (<row>_adsb): the rest carries part of the front - the muzzle dips 2.6 deg where the free gun dips 4.1
    # and every reaction is 0.8 of the free gun's; the firer lowers the BUTT end a little more instead to get the work
    # under the box. A shallower sag does not clear it: with 1.3 deg the front sight ears stood in the bottom of the
    # box for the whole work (run hc2, 3-4 %), and the firing forearm showed in the lower left of the view.
    braced={'sup': 0.3, 'strength': 0.8, 'cant.move': [3.0, 0.4, -1.4]},
    mag_rel=15,                        # retail frame: the left hand holds the SEATED magazine (wrist behind it, fingers round the front)
    mag_out=5.8,                       # u down the well's own axis until the magazine is clear
    handle=(4.63, -2.75, -1.67),       # weapon-tag frame (fwd, right, DOWN): the operating handle's knob, forward
    travel=5.75,                       # u; bolt bone 'bolt pos' y 0 -> 11.06 skd units
    # camera frame (fwd, left, up): the wrist from the knob. Until run hg3 it was straight out to the LEFT (0.3, 3.9,
    # -0.6): from the eye the back of a flat pale hand a quarter to a third of the screen wide, no finger to be seen.
    # Now the wrist comes up from BELOW the handle: the eye looks down on the knuckles and four fingers closed round
    # the knob, the forearm runs down out of the frame (hktry.py sheets hk_a / hk_b / hk_c; box unchanged offline)
    hk_off=(0.2, 1.0, -3.8),
    hk_roll=180.0,                       # deg about the hand's long axis (which points at the knob)
    t=dict(off=(3, 9), cant_in=(4, 15), grab=13, out=(18, 21), show_out=(24, 27), pouch=(31, 33), show_in=(36, 39),
           well=43, seat=46, hold=50,
           slap=(51, 53),
           # empty: the handle (sound: back 67-69, forward 71-73)
           # the support hand is back by f82: the sag is out by f87 and the last frames ARE the aim pose (with on = 78-84
           # the gun was still rising at f87 and reached the aim two frames before the clip ended - coordinator 2026-10-12)
           reach=(57, 64), pull=(66, 69), fwd=(71, 73), leave=74, on=(77, 82), cant_out=(70, 77),
           # loaded: straight back to the forearm
           l_leave=55, l_on=(58, 66), l_cant_out=(56, 68)),
)


def bolt_u(g, f):
    """handle travel 0..1 at clip frame f (empty gun)"""
    t = g['t']
    if f <= t['pull'][0]:
        return 0.0
    if f <= t['pull'][1]:
        return ease((f - t['pull'][0]) / float(t['pull'][1] - t['pull'][0]))
    if f <= t['fwd'][0]:
        return 1.0
    if f <= t['fwd'][1]:
        u = (f - t['fwd'][0]) / float(t['fwd'][1] - t['fwd'][0])
        return 1.0 - u * u * (3 - 2 * u)
    return 0.0


def spec(g, empty, o):
    t = dict(g['t']); t.update({k[2:]: v for k, v in o.items() if k.startswith('t.')})
    n = R.load(R.ANIM + H.fps_rows()[g['row']]).numFrames - 1
    if empty:
        leave, on, co = t['leave'], t['on'], t['cant_out']
    else:
        leave, on, co = t['l_leave'], t['l_on'], t['l_cant_out']
    top = g.get('feed') == 'top'           # a pan lifted UP off the receiver (DP-28): the well keys with the axis turned round
    sgn = -1.0 if top else 1.0
    ev = [(t['out'][0] - 2, 'lg_pan_lift' if top else 'lg_mag_tug'), (t['out'][0] + 1, 'lg_pan_free' if top else 'lg_mag_free'),
          (t['well'] + 1, 'lg_pan_on' if top else 'lg_mag_in'),
          (t['slap'][1] - 1, g.get('slap_action', 'lg_pan_press' if top else 'lg_mag_slap')), (on[1] - 4, 'lg_hand_on')]
    if empty:
        ev += [(t['pull'][0] - 2, 'lg_handle_grab'), (t['pull'][0], 'lg_handle_back'), (t['pull'][1] - 1, 'lg_handle_stop'),
               (t['fwd'][1] - 1, 'lg_handle_fwd')]
    # BRACED (clip <row>_adsb, picked by cgame when the brace envelope is up): the rest carries most of the gun, so
    # the support hand leaving takes only `sup` of the hold away (sup 0 = free-standing) and every reaction is smaller
    sup = float(o.get('sup', 0.0))
    ph = gunphys.simulate(n + 1, 1 / 30.0, o.get('cls', g['cls']), support=[(0, 1), (t['off'][0], 1), (t['off'][1], sup), (on[0], sup), (on[1], 1)],
                          mag=[(0, 1), (t['out'][0], 1), (t['out'][1], 0), (t['well'], 0), (t['seat'], 1)],
                          events=sorted(ev), strength=float(o.get("strength", 1.0)), fade=12)
    # one-sided near the aim: the cheek and the support hand are a stop, gravity is not - the gun does not ride ABOVE its
    # aim (run hb1: the return overshot upward and put 5.5 % more gun into the centre box)
    X = ph['X'].copy()
    for j in (0, 2):
        X[:, j] = np.where(X[:, j] < 0.0, X[:, j] * 0.15, X[:, j])
    ph['X'] = X
    ph['dip'] = {f: tuple(float(v) for v in X[f]) for f in range(n + 1)}
    cant = dict(g['cant']); cant.update({k[5:]: (tuple(v) if isinstance(v, list) else float(v)) for k, v in o.items() if k.startswith('cant.')})
    Tc = HL.work_T(g['aim'], g['sight'], cant, g['butt'])
    ci = t['cant_in']
    gun_abs = [dict(T=Tc, keys={0: 0.0, ci[0]: 0.0, ci[1]: 1.0, co[0]: 1.0, co[1]: 0.0, n: 0.0})]
    if empty and (g.get('hcant') or any(k.startswith('hcant.') for k in o)):
        # the HANDLE pose: while the left hand hauls the handle back the firing hand shoves the gun forward against it
        # (and turns the handle side to the eye) - at the cheek the pull ends 7 u from the eye and the hand on the
        # knob is a quarter of the screen (runs hb4-hb9)
        hc = dict(cant); hc.update(g.get('hcant') or {})
        hc.update({k[6:]: (tuple(v) if isinstance(v, list) else float(v)) for k, v in o.items() if k.startswith('hcant.')})
        Th = HL.work_T(g['aim'], g['sight'], hc, g['butt'])
        gun_abs.append(dict(T=Th, keys={0: 0.0, t['reach'][0] - 2: 0.0, t['reach'][1] - 1: 1.0, t['fwd'][1]: 1.0, co[1] - 2: 0.0, n: 0.0}))
    MR = g['mag_rel']

    def M(dz, **kw):
        return dict(dict(rel=MR, gun_add=(0.0, 0.0, dz), fing=MR), **kw)
    out = float(o.get('mag_out', g['mag_out']))
    SHOW = tuple(o.get('show', g.get('show', (12.0, 7.5, -7.6))))      # camera frame (fwd, left, up): bottom-left of the view
    SHOW2 = (SHOW[0] - 0.5, SHOW[1] + 1.0, SHOW[2] - 0.8)              # ... a little further out and down (the way to the pouch)
    lp = {0: AIM, t['off'][0]: AIM,
          t['off'][0] + 3: dict(aim=1, cam_add=tuple(g.get('off_add', (-0.8, 0.8, -1.6))), fing=('mix', MR, 0.6)),   # comes off the forearm, down
          t['grab']: M(0.0), t['out'][0]: M(0.0),
          t['out'][1]: M(out),                                                               # stripped down the well's axis
          # the well of a shouldered BAR is below the frame (18-36 deg under the sight line): the magazine is SEEN in
          # the hand, swung out to the left through the bottom-left of the view on its way down and on its way back
          t['show_out'][0]: dict(rot=MR, cam=SHOW, fing=MR), t['show_out'][1]: dict(rot=MR, cam=SHOW2, fing=MR),
          t['pouch'][0]: dict(rot=MR, cam=POUCH, fing=MR), t['pouch'][1]: dict(rot=MR, cam=POUCH, fing=MR),
          t['show_in'][0]: dict(rot=MR, cam=SHOW2, fing=MR), t['show_in'][1]: dict(rot=MR, cam=SHOW, fing=MR),
          t['well']: M(out - 0.4 * sgn), t['seat']: M(0.0), t['hold']: M(0.0),
          t['slap'][0]: M(1.3 * sgn, fing=('mix', MR, 0.4)),                                 # lets go, the palm drops (a pan: lifts) ...
          t['slap'][1]: M(-0.15 * sgn, fing=('mix', MR, 0.4)),                               # ... and strikes the floor plate (the pan's top)
          t['slap'][1] + 2: M(0.3 * sgn, fing=('mix', MR, 0.4))}
    fa = {}
    if empty:
        hoff = np.array(o.get('hk_off', g['hk_off']), float); hroll = float(o.get('hk_roll', g['hk_roll']))
        knob = np.array(g['handle'], float)

        def Hd(back, extra=(0, 0, 0), **kw):
            # the hand works the KNOB (a point of the gun): wrist `off` from it in the camera frame, long axis at it,
            # the magazine grip's half-closed fingers hooked round it
            return dict(dict(gunpt=tuple(knob + np.array([-back, 0.0, 0.0])), off=tuple(hoff + np.array(extra, float)),
                             roll=hroll, fing=MR), **kw)
        lp[t['reach'][0]] = Hd(0.0, (-1.0, 2.5, -3.5), fing=('mix', MR, 0.5))                 # round from below-left
        lp[t['reach'][1]] = Hd(0.0, (-0.3, 0.5, -0.4))
        rel = bool(g.get('release'))
        # ON the knob: the hand and the bolt bone share bolt_u. A handle that is RELEASED (StG 44: no hold-open, the
        # spring runs it home) leaves the hand at the rear - the hand does not ride it forward.
        for f in range(t['pull'][0], (t['fwd'][0] if rel else t['fwd'][1]) + 1):
            lp[f] = Hd(g['travel'] * bolt_u(g, f))
        if rel:
            lp[t['fwd'][1] + 1] = Hd(g['travel'], (0.2, 0.9, -0.5), fing=('mix', MR, 0.5))     # opens, the handle is gone
        lp[leave] = Hd(g['travel'] * (0.6 if rel else 0.0), (0.5, 1.5, -1.5), fing=('mix', MR, 0.5))
        # the fingers close round the knob while the hand is on it (run hb4: a flat hand lay against the receiver)
        c0, c1, c2, c3 = t['reach'][1] - 3, t['pull'][0] - 1, (t['fwd'][0] if rel else t['fwd'][1]), leave
        cs = float(o.get('hk_curl', 1.0))
        for fg in (1, 2, 3, 4):
            for seg, dg in (('', 26.0), ('1', 48.0), ('2', 30.0)):
                fa['Bip01 L Finger%d%s rot' % (fg, seg)] = [(c0, 0.0), (c1, dg * cs), (c2, dg * cs), (c3, 0.0)]
    else:
        lp[leave] = dict(aim=1, cam_add=tuple(g.get('leave_add', (-1.5, 1.5, -3.0))), fing=('mix', MR, 0.5))
    for f in range(on[1], n + 1):
        lp[f] = AIM
    lp[on[1] - 3] = dict(aim=1, cam_add=(-0.5, 0.5, -1.2), fing=('mix', MR, 0.3))            # comes up under the forearm
    # handover / prop_hold (hold_bake): a prop the server attaches BEFORE the hand has it (StG 44: mp44_clip on the
    # off-hand tag from frame 0) stays in the gun's own magazine until the hand is on it - run-less offline find: the
    # magazine rode the hand off the forend through the centre box (5.6 % at f5-8)
    kw = dict(gun=g['sight'], charge=g['aim'], fixed_right=True, weight=dict(on=False), handover=bool(g.get('handover', False)),
              **({'prop_hold': g['prop_hold']} if g.get('prop_hold') else {}))
    kw.update(
              dip=ph['dip'], dip_pivot=g['butt'][0], dip_after=True, gun_abs=gun_abs, left_path=lp,
              tag_map={0: MR, n: MR}, elbow_vec={'L': (0.0, 0.4, -1.0)}, elbow_down={'L': [(0, 0.0), (t['grab'], 2.5), (on[0], 2.5), (n, 0.0)]})
    if fa:
        kw['finger_add'] = fa
    return kw, ph


def gun_clip(g, root):
    """the gun's own reload with the bolt bone hauled back and run forward in the hand's frames (EMPTY), and - where
    the retail gun clip works the handle in EVERY reload (StG 44) - a second one with the handle left alone (rounds left)"""
    raw = R.vfs.read(g['gun_path'] + '/' + g['gun_reload'])
    a = R.skc_io.read(raw)
    n = a.numFrames
    b = g.get('bolt') or dict(chan='bolt pos', rest=(0.0, 0.0, 0.0, 0.0), axis=1, units=11.06)

    def key(u):
        v = list(b['rest']); v[b['axis']] += b['units'] * u
        return v
    for out, fn in ((g['gun_out'], lambda f: bolt_u(g, f)), (g.get('gun_out_loaded'), lambda f: 0.0)):
        if not out:
            continue
        dst = os.path.join(root, (g['gun_path'] + '/' + out).replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        gunskc.write(dst, raw, n, {b['chan']: [key(fn(f)) for f in range(n)]})
        print('gun clip ->', g['gun_path'] + '/' + out, n, 'frames', hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8])


def bake(name, root, only=None, o=None, braced=False):
    g = GUNS[name]
    rep = {}
    o = dict(o or {})
    if braced:
        for k, v in g.get('braced', {}).items():
            o.setdefault(k, v)
    for empty in (False, True):
        key = 'empty' if empty else 'loaded'
        if only and only != key:
            continue
        kw, ph = spec(g, empty, o)
        rc = H.auto_recipe(g['row'], **kw)
        H.RECIPES[g['row']] = rc
        sk, _ = H.bake(g['row'], CTL)
        bts = R.skc_io.write(sk)
        out = '%s/%s_reload_%sads%s.skc' % (g['vdir'], name, 'empty_' if empty else '', 'b' if braced else '')
        dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        print(name, key, '->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])
        print('   ', ph['report'])
        X = ph['X']
        print('    sag at the work: pitch %.1f deg, drop %.2f u; roll swing %.1f deg; back %.2f u' % (
            float(np.median(X[30:40, 2])), float(np.median(X[30:40, 0])), float(np.abs(X[:, 1]).max()), float(np.abs(X[:, 4]).max())))
        rep[key + ('_braced' if braced else '')] = dict(peak_deg=round(ph['peak_deg'], 2), settle_s=round(ph['settle_s'], 2))
    if (not only or only == 'empty') and not braced:
        gun_clip(g, root)
    return rep


def bake_hip(name, root):
    """HIP, rounds left, of a gun whose retail hip clip cocks in EVERY reload (StG 44): the retail clip to the seat
    frame, the palm stays under the magazine `hold` frames, then the whole pose eases to the clip's own end pose - no
    mimed cock (the SMG lane's recipe for the MP40, smgbake.bake_hip). The EMPTY gun keeps the retail clip
    (row <row>_empty)."""
    g = GUNS[name]
    K = H.K
    src = H.fps_rows()[g['row']]
    hip = R.load(R.ANIM + src)
    out = R.load(R.ANIM + src)
    n = hip.numFrames
    cm = R.chanmap(hip)
    b0, b1 = g['hip_blend']
    hold = g.get('hip_hold', 3)
    pe, pa = R.pose_dict(hip, n - 1), R.pose_dict(hip, b0)
    for f in range(b0, n):
        w = ease((f - b0 - hold) / float(b1 - b0 - hold))
        pd = {}
        for ch in hip.names:
            if ch.endswith(' rot'):
                pd[ch] = R.qslerp(np.asarray(pa[ch], float), np.asarray(pe[ch], float), w)
            else:
                pd[ch] = (1 - w) * np.asarray(pa[ch], float) + w * np.asarray(pe[ch], float)
        K.write_frame(out, hip, cm, f, pd)
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(n)]
    bts = R.skc_io.write(out)
    o1 = '%s/coop_%s_reload_hip.skc' % (g['vdir'], name)
    dst = os.path.join(root, 'models', 'human', 'animation', o1.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bts)
    print(name, 'hip loaded ->', o1, n, 'frames', hashlib.md5(bts).hexdigest()[:8], '(retail to f%d, its end pose by f%d: no cock)' % (b0, b1))


# ---------------------------------------------------------------------------------------------------------- StG 44
# heavylib.py mp44: at the cheek weld the magazine hangs 33-50 deg below the sight line (frame edge 26) and the
# left-side cocking handle, 15 deg below at rest, ends its 6.2 u pull 37 deg below, 4 u from the eye. The same answer
# as the BAR: sag about the butt + the canted WORK pose, the magazine shown bottom-left, the handle worked by the left
# hand. Retail technique (clipinfo.py): left hand strips the magazine (gun's own hidden f13-42, prop on the off-hand
# tag f0-42), pouch, seats, then the same hand cocks (retail gun clip: handle back in ONE frame f66-67, home f71).
# A closed-bolt gun with rounds left has one in the chamber: NO cocking (gun clip coop_reload_ads_loaded, handle still).
MP44 = dict(
    row='mp44_reload', sight='stg44', cls='stg', aim='viewmodel/mp44_idle_stand.skc', vdir='viewmodel/mp44',
    gun_path='models/weapons/mp44', gun_reload='mp44_reload.skc', gun_out='coop_reload_ads_empty.skc',
    gun_out_loaded='coop_reload_ads_loaded.skc', gun_anim_loaded='reload_ads_loaded',
    bolt=dict(chan='Box02 pos', rest=(7.6, -7.4, -0.1, 0.0), axis=1, units=12.0),
    butt=(-11.8, -0.9, -5.1),
    # 1.2 u down (the BAR: 0.7): after a 30-round burst the gun rides a little higher through the reload than a
    # settled one - the same clip read 0.4 % loaded and 2.0-2.5 % emptied at the cant-in and at the slap (run he5)
    cant=dict(roll=32.0, pitch=0.0, yaw=-3.0, move=(3.0, 0.4, -1.2)),
    braced={'sup': 0.3, 'strength': 0.8, 'cant.move': [3.0, 0.4, -1.9]},
    mag_rel=12, mag_out=5.0,
    handle=(4.0, -2.2, -4.8), travel=6.24, release=True, slap_action='lg_mag_slap_light',
    hk_off=(0.2, 1.0, -3.8), hk_roll=180.0,     # wrist from below, as the BAR
    prop='models/ammo/mp44_clip.tik:0:42', handover=True, prop_hold={'tag_weapon_left': 12},
    # the gun sags first and cants after (cant 7-15): canted while still high it left the aim's own silhouette
    # through the box (5.6 % at f5-8 offline with cant 3-12)
    t=dict(off=(2, 6), cant_in=(7, 15), grab=11, out=(13, 16), show_out=(19, 22), pouch=(25, 28), show_in=(31, 34),
           well=38, seat=41, hold=44, slap=(46, 48),
           # empty: the handle (retail gun clip / sound: back f66-67, home f71)
           reach=(52, 60), pull=(63, 67), fwd=(69, 71), leave=73, on=(74, 78), cant_out=(68, 75),
           # the return mirrors the entry: the cant comes off while the gun is still low (52-60), THEN it rises
           # (support back 56-64) - risen while canted it read 1.7-2.0 % in every stance (run he1), 0.7 % this way
           l_leave=50, l_on=(56, 64), l_cant_out=(52, 60)),
    show=(12.0, 7.0, -6.4),            # the long magazine a little higher than the BAR's: in run he1 only its top showed
    # hip, rounds left: the retail hand holds the seated magazine f42-45 and leaves for its cock at f46 (clipinfo.py)
    hip_blend=(45, 68),
)

# ----------------------------------------------------------------------------------------------------------- DP-28
# heavylib.py dp28: at the aim the pan (8.4 u across, top z -5.0) lies 8-17 u from the eye, 1-3 deg under the sight line
# and 18 deg to either side - it IS the lower half of the settled aim's picture. Nothing of it may leave that
# silhouette upward, so for the swap the gun comes DOWN under the box (sag by class `dp`, then the work pose lower and
# a little canted) and the pan is lifted off there, swung out bottom-left, the new one brought in the same way and
# pressed home. The pack's hip technique (clipinfo.py): the LEFT hand does all of it - thumb-turn at f10-20 (gun clip
# `drum1 rot`), on the pan f24-28, away f32-40, seated f44-48, pressed f52-60, then the SAME hand hauls the handle
# (on this mesh a knob on the LEFT, surface Cylinder2 / bone `rechamb`, 2.7 u, gun clip f74-81).
# The server shows the pan prop on the off-hand tag f29-45 and hides the gun's own (`surface drum`) for exactly those
# frames: the lift starts AT f29 and the new pan is down AT f45 - 0.5 s for the whole swap, the server's window.
# OPEN BOLT: with rounds left the bolt is held back by the sear - no handle work; an emptied gun's bolt is forward.
# The gun's reload sound is the BAR's (handle at f67-73): the hand's pull is keyed to it (the pack's own was 0.25 s late).
DP28 = dict(
    row='dp28_reload', sight='dp_28', cls='dp', aim='viewmodel/coop_dp28/coop_dp28_ads_hand.skc', vdir='viewmodel/coop_dp28',
    gun_path='models/weapons/coop_dp28', gun_reload='dp28_reload.skc', gun_out='coop_reload_ads_empty.skc',
    gun_out_loaded='coop_reload_ads_loaded.skc', gun_anim_loaded='reload_ads_loaded',
    bolt=dict(chan='rechamb pos', rest=(15.0, -4.5, -1.5, 0.0), axis=0, units=-5.2),
    butt=(-10.4, 0.0, -6.5),
    feed='top',
    # 2.6 u down: with 3.6 the pan sat on the frame's bottom edge in the engine (run hh7 - the engine's gun rides lower
    # than the offline eye view shows) and the work was half out of view
    cant=dict(roll=14.0, pitch=0.0, yaw=-2.0, move=(1.5, 0.3, -2.6)),
    # the HANDLE pose: with the pan 3.6 u down the knob's side is under the frame's bottom edge (offline sheet dp_b: no
    # hand to be seen at all). For the pull the gun is most of the way back up - the pan inside the part of the
    # picture the settled aim covers anyway - and the forearm is seen going in under the pan's left rim
    hcant=dict(roll=8.0, pitch=0.0, yaw=-2.0, move=(1.0, 0.0, -1.5)),
    braced={'sup': 0.3, 'strength': 0.8, 'cant.move': [1.5, 0.3, -3.2]},
    mag_rel=46,                        # retail frame: the left hand on the seated pan
    mag_out=-1.1,                      # u: UP off the spigot (weapon z is down)
    off_add=(-0.4, 2.2, -0.8), leave_add=(-1.0, 1.5, -2.0),
    handle=(7.6, -2.0, -2.05), travel=2.7, release=True,
    # the knob sits UNDER the pan, 2.6 u inboard of its rim (no cant short of 56 deg shows it from the eye): the hand
    # goes in under the rim from the LEFT, by feel, as on the real gun - a wrist from below put the fingers up
    # through the pan (offline sheet dp_a)
    hk_off=(0.0, 3.6, -1.0), hk_roll=180.0,
    prop='models/ammo/coop_dp28_clip.tik:29:45',
    show=(13.5, 5.5, -3.0),            # the WRIST: the pan hangs 2.5 u under the hand and is 8.4 u across (centre 27 deg left, 25 deg down)
    t=dict(off=(3, 9), cant_in=(5, 16), grab=22, out=(29, 31), show_out=(32, 34), pouch=(36, 38), show_in=(39, 41),
           well=43, seat=45, hold=49, slap=(50, 52),
           reach=(56, 63), pull=(66, 69), fwd=(71, 73), leave=75, on=(80, 88), cant_out=(74, 86),
           # rounds left: 11 kg does not jump back - the cant comes off over 0.47 s, the support hand is under it by f72
           l_leave=54, l_on=(60, 72), l_cant_out=(56, 70)),
)

GUNS = {'bar': BAR, 'mp44': MP44, 'dp28': DP28}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--only'); ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--braced', action='store_true', help='bake ONLY the braced <row>_adsb clips')
    ap.add_argument('--hip', action='store_true', help='bake ONLY the hip rounds-left clip (no cock)')
    a = ap.parse_args()
    if a.hip:
        bake_hip(a.gun, '.')
        sys.exit(0)
    o = {}
    for kv in a.set:
        k, v = kv.split('=', 1)
        try:
            o[k] = json.loads(v)
        except ValueError:
            o[k] = v
    rep = bake(a.gun, '.', a.only, o, a.braced)
    p = os.path.join(hv.LANE, 'heavyphys.json')
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.setdefault(a.gun, {}).update(rep)
    json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)

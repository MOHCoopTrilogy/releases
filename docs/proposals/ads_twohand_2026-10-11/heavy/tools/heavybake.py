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

    cd heavy/assets; python ../tools/heavybake.py bar [--only loaded|empty] [--set k=v ...]
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
})
gunphys.ACTIONS.update({
    # velocity change for mass 1 in (drop, roll, pitch, side, back) and the pulse length in frames; + roll = top right,
    # + pitch = muzzle down, + side = left, + back = toward the shoulder
    'lg_mag_tug':     ((26.0, 0.0, 70.0, 0.0, 0.0), 3.0),     # the magazine hauled DOWN against its catch: the gun goes with it
    'lg_mag_free':    ((-30.0, 0.0, -110.0, 0.0, 0.0), 3.0),  # it lets go: 0.7 kg lighter, the front springs up
    'lg_mag_in':      ((-14.0, 0.0, -60.0, 0.0, 3.0), 4.0),   # pushed up the well, ahead of the firing hand: the front lifts
    'lg_mag_slap':    ((-34.0, -25.0, -150.0, 0.0, 8.0), 1.5),  # the palm strikes the floor plate
    'lg_handle_grab': ((4.0, -40.0, 10.0, 3.0, 0.0), 2.0),    # the hand closes on the left-side handle
    'lg_handle_back': ((8.0, -110.0, 30.0, 14.0, 150.0), 3.5),  # hauled back against the recoil spring: into the shoulder, rolls to the hand
    'lg_handle_stop': ((0.0, -40.0, -55.0, 0.0, 70.0), 1.5),   # the slide hits the rear stop
    'lg_handle_fwd':  ((6.0, 70.0, 95.0, -8.0, -190.0), 2.0),  # run forward: the mass stops in the front, muzzle dips
    'lg_hand_on':     ((-22.0, 0.0, -80.0, -4.0, 4.0), 4.0),   # the support hand comes up under the forearm and lifts
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
    cant=dict(roll=32.0, pitch=0.0, yaw=-3.0, move=(3.0, 0.4, 0.0)),
    mag_rel=15,                        # retail frame: the left hand holds the SEATED magazine (wrist behind it, fingers round the front)
    mag_out=5.8,                       # u down the well's own axis until the magazine is clear
    handle=(4.63, -2.75, -1.67),       # weapon-tag frame (fwd, right, DOWN): the operating handle's knob, forward
    travel=5.75,                       # u; bolt bone 'bolt pos' y 0 -> 11.06 skd units
    hk_off=(0.3, 3.9, -0.6),           # camera frame (fwd, left, up): the wrist from the knob - straight out to the LEFT (a hand behind the knob ends 4 u from the eye)
    hk_roll=180.0,                       # deg about the hand's long axis (which points at the knob)
    t=dict(off=(3, 9), cant_in=(4, 15), grab=13, out=(18, 21), show_out=(24, 27), pouch=(31, 33), show_in=(36, 39),
           well=43, seat=46, hold=50,
           slap=(51, 53),
           # empty: the handle (sound: back 67-69, forward 71-73)
           reach=(57, 64), pull=(66, 69), fwd=(71, 73), leave=75, on=(78, 84), cant_out=(70, 78),
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
    ev = [(t['out'][0] - 2, 'lg_mag_tug'), (t['out'][0] + 1, 'lg_mag_free'), (t['well'] + 1, 'lg_mag_in'),
          (t['slap'][1] - 1, 'lg_mag_slap'), (on[1] - 4, 'lg_hand_on')]
    if empty:
        ev += [(t['pull'][0] - 2, 'lg_handle_grab'), (t['pull'][0], 'lg_handle_back'), (t['pull'][1] - 1, 'lg_handle_stop'),
               (t['fwd'][1] - 1, 'lg_handle_fwd')]
    ph = gunphys.simulate(n + 1, 1 / 30.0, o.get('cls', g['cls']), support=[(0, 1), (t['off'][0], 1), (t['off'][1], 0), (on[0], 0), (on[1], 1)],
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
    MR = g['mag_rel']

    def M(dz, **kw):
        return dict(dict(rel=MR, gun_add=(0.0, 0.0, dz), fing=MR), **kw)
    out = float(o.get('mag_out', g['mag_out']))
    SHOW = tuple(o.get('show', g.get('show', (12.0, 7.5, -7.6))))      # camera frame (fwd, left, up): bottom-left of the view
    SHOW2 = (SHOW[0] - 0.5, SHOW[1] + 1.0, SHOW[2] - 0.8)              # ... a little further out and down (the way to the pouch)
    lp = {0: AIM, t['off'][0]: AIM,
          t['off'][0] + 3: dict(aim=1, cam_add=(-0.8, 0.8, -1.6), fing=('mix', MR, 0.6)),   # comes off the forearm, down
          t['grab']: M(0.0), t['out'][0]: M(0.0),
          t['out'][1]: M(out),                                                               # stripped down the well's axis
          # the well of a shouldered BAR is below the frame (18-36 deg under the sight line): the magazine is SEEN in
          # the hand, swung out to the left through the bottom-left of the view on its way down and on its way back
          t['show_out'][0]: dict(rot=MR, cam=SHOW, fing=MR), t['show_out'][1]: dict(rot=MR, cam=SHOW2, fing=MR),
          t['pouch'][0]: dict(rot=MR, cam=POUCH, fing=MR), t['pouch'][1]: dict(rot=MR, cam=POUCH, fing=MR),
          t['show_in'][0]: dict(rot=MR, cam=SHOW2, fing=MR), t['show_in'][1]: dict(rot=MR, cam=SHOW, fing=MR),
          t['well']: M(out - 0.4), t['seat']: M(0.0), t['hold']: M(0.0),
          t['slap'][0]: M(1.3, fing=('mix', MR, 0.4)),                                       # lets go, the palm drops ...
          t['slap'][1]: M(-0.15, fing=('mix', MR, 0.4)),                                     # ... and strikes the floor plate
          t['slap'][1] + 2: M(0.3, fing=('mix', MR, 0.4))}
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
        for f in range(t['pull'][0], t['fwd'][1] + 1):                # ON the knob: the hand and the bolt bone share bolt_u
            lp[f] = Hd(g['travel'] * bolt_u(g, f))
        lp[leave] = Hd(0.0, (0.5, 1.5, -1.5), fing=('mix', MR, 0.5))
        # the fingers close round the knob while the hand is on it (run hb4: a flat hand lay against the receiver)
        c0, c1, c2, c3 = t['reach'][1] - 3, t['pull'][0] - 1, t['fwd'][1], leave
        cs = float(o.get('hk_curl', 1.0))
        for fg in (1, 2, 3, 4):
            for seg, dg in (('', 26.0), ('1', 48.0), ('2', 30.0)):
                fa['Bip01 L Finger%d%s rot' % (fg, seg)] = [(c0, 0.0), (c1, dg * cs), (c2, dg * cs), (c3, 0.0)]
    else:
        lp[leave] = dict(aim=1, cam_add=(-1.5, 1.5, -3.0), fing=('mix', MR, 0.5))
    for f in range(on[1], n + 1):
        lp[f] = AIM
    lp[on[1] - 3] = dict(aim=1, cam_add=(-0.5, 0.5, -1.2), fing=('mix', MR, 0.3))            # comes up under the forearm
    kw = dict(gun=g['sight'], charge=g['aim'], fixed_right=True, weight=dict(on=False), handover=False,
              dip=ph['dip'], dip_pivot=g['butt'][0], dip_after=True, gun_abs=gun_abs, left_path=lp,
              tag_map={0: MR, n: MR}, elbow_vec={'L': (0.0, 0.4, -1.0)}, elbow_down={'L': [(0, 0.0), (t['grab'], 2.5), (on[0], 2.5), (n, 0.0)]})
    if fa:
        kw['finger_add'] = fa
    return kw, ph


def gun_clip(g, root):
    """the gun's own reload with the bolt bone hauled back and run forward in the hand's frames"""
    raw = R.vfs.read(g['gun_path'] + '/' + g['gun_reload'])
    a = R.skc_io.read(raw)
    n = a.numFrames
    keyed = {'bolt pos': [[0.0, 11.06 * bolt_u(g, f), 0.0, 0.0] for f in range(n)]}
    dst = os.path.join(root, (g['gun_path'] + '/' + g['gun_out']).replace('/', os.sep))
    gunskc.write(dst, raw, n, keyed)
    print('gun clip ->', g['gun_path'] + '/' + g['gun_out'], n, 'frames', hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8])


def bake(name, root, only=None, o=None):
    g = GUNS[name]
    rep = {}
    for empty in (False, True):
        key = 'empty' if empty else 'loaded'
        if only and only != key:
            continue
        kw, ph = spec(g, empty, o or {})
        rc = H.auto_recipe(g['row'], **kw)
        H.RECIPES[g['row']] = rc
        sk, _ = H.bake(g['row'], CTL)
        bts = R.skc_io.write(sk)
        out = '%s/%s_reload_%sads.skc' % (g['vdir'], name, 'empty_' if empty else '')
        dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        print(name, key, '->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])
        print('   ', ph['report'])
        X = ph['X']
        print('    sag at the work: pitch %.1f deg, drop %.2f u; roll swing %.1f deg; back %.2f u' % (
            float(np.median(X[30:40, 2])), float(np.median(X[30:40, 0])), float(np.abs(X[:, 1]).max()), float(np.abs(X[:, 4]).max())))
        rep[key] = dict(peak_deg=round(ph['peak_deg'], 2), settle_s=round(ph['settle_s'], 2))
    if not only or only == 'empty':
        gun_clip(g, root)
    return rep


GUNS = {'bar': BAR}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--only'); ap.add_argument('--set', action='append', default=[])
    a = ap.parse_args()
    o = {}
    for kv in a.set:
        k, v = kv.split('=', 1)
        try:
            o[k] = json.loads(v)
        except ValueError:
            o[k] = v
    rep = bake(a.gun, '.', a.only, o)
    p = os.path.join(hv.LANE, 'heavyphys.json')
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.setdefault(a.gun, {}).update(rep)
    json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)

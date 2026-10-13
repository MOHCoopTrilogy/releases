"""SMG reloads to the user's standard (2026-10-12), AIMED and HIP from one choreography:

  1. ON TARGET - the gun stays in the aim; the magazine leaves and arrives LOW (down the well, out of the bottom of
     the frame to the pouch, back up from the lower left); the cock is worked from BELOW the handle, under the centre box.
  2. THE WEAPON REACTS - no gun key is set by hand: gunphys.py's damped spring (class `smg`) driven by the clip's own
     events: the thumb on the catch, the magazine dragged out (the gun follows it down, then lifts as its weight goes),
     the support hand gone (the muzzle sags), the new magazine driven home (the gun is pushed up), the handle pulled
     (the gun comes back into the shoulder and cants), the bolt caught by the sear, the hand landing on its grip.
  3. THE ACTION WORKS - open bolt (smggun.py): an EMPTY gun's bolt is forward, so after the magazine the LEFT hand
     goes up to the handle, hooks it and pulls it back until the sear holds it (`<row>_empty_ads` + the gun's
     `reload_ads_empty`); a gun with rounds left is still cocked, so its reload has no pull (`<row>_ads`).

The firing hand keeps its aim grip. The support hand is keyed: aim grip -> down onto the magazine (the retail clip's
own hand-on-magazine relation, so the server's prop sits in the hand and meets the gun's own magazine at the seat
frame) -> out / pouch / in -> [handle] -> aim grip. First and last frame = the aim pose exactly.

HIP (the same story at the hip, coordinator 2026-10-12): `<row>` = the retail clip with its mimed cock REMOVED (a gun
with rounds left is cocked already); `<row>_empty` = the retail clip with the left hand re-keyed ONTO the handle for
the pull (the retail art mimes it 3-4 u below the slot).

    cd smg/assets; python ../tools/smgbake.py <gun> . [--look out.jpg --frames a:b:s --which ads_empty] [--box]
        env SB_STRENGTH (default 1.0), IRONSIGHT_EXTRA_PAKS=<overlay with the staged gun> for --look / --box
"""
import sys, os, json, hashlib, math, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.normpath(os.path.join(HERE, '..', '..', 'tools'))
sys.path.insert(0, SHARED)
import revbake as RB
import gunphys
H = RB.H; R = RB.R; V = RB.V; K = H.K; B = H.B

STRENGTH = float(os.environ.get('SB_STRENGTH', '1.0'))
SHOULDER = float(os.environ.get('SB_SHOULDER', '0.3'))   # run sb2: with 0 the muzzle hung 1.9 deg low for 1.2 s
POUCH = (4.0, 10.0, -17.0)             # camera frame (fwd, left, up): the belt, well under the frame


def _envf(name, default):
    v = os.environ.get(name)
    return tuple(float(x) for x in v.split(',')) if v else default


# SMG actions for gunphys (velocity change for mass 1 in (drop, roll, pitch, side, back), length in frames). The well is
# AHEAD of the firing hand and the shoulder, so a push up on the magazine lifts the gun and its muzzle; the handle is on
# the LEFT at bore height, pulled straight back against the return spring.
gunphys.ACTIONS.update({
    'smg_catch':     ((1.0, -10.0, 4.0, 0.8, 0.0), 2.0),        # the thumb on the magazine catch
    'smg_mag_drag':  ((27.0, -5.0, 48.0, 1.2, 0.0), 3.0),       # the magazine dragged down out of the well: the gun follows
                                                                # (0.8 of run sb4's: it was the fastest step of the sight line, 0.18 deg / frame)
    'smg_mag_free':  ((-22.0, 0.0, -46.0, 0.0, 0.0), 2.0),      # ...and springs up as it comes free
    'smg_mag_enter': ((-9.0, 5.0, -16.0, -1.0, 2.0), 2.0),      # the lips find the well
    'smg_mag_tug':   ((16.0, 2.0, 30.0, 0.0, 0.0), 2.5),        # a tug down on the seated magazine: is the catch holding?
    'smg_mag_seat':  ((-26.0, 0.0, -66.0, 0.0, 3.0), _envf('SB_SEATLEN', (5.5,))[0]),      # driven home with the palm: up, muzzle up, back (twice this
                                                                # lifts the sights 3-4 % into the centre box, offline)
    'smg_handle_on': ((-5.0, -10.0, -10.0, 2.0, 2.0), 2.0),     # the fingers hook the handle from below-left
    'smg_bolt_pull': ((6.0, -46.0, -70.0, 9.0, 120.0), 5.0),    # pulled back against the spring: into the shoulder, canted to the hand
    'smg_bolt_stop': ((0.0, -10.0, -34.0, 0.0, 60.0), 1.5),     # the bolt hits the end of its travel
    'smg_bolt_sear': ((2.0, 14.0, 52.0, -3.0, -66.0), 1.5),     # let go: the spring runs it forward onto the sear
    'smg_hand_on':   ((-12.0, 12.0, -30.0, -3.0, 5.0), 3.0),    # the support hand lands on the magazine housing
    'smg_grip_on':   ((-3.0, 5.0, -8.0, -1.0, 6.0), 3.0),       # the firing hand takes the grip again: a little into the shoulder
})
# a handle on the RIGHT, worked by the firing hand: the same actions with roll and side reversed (the simulation's one
# `hand` sign is the left hand's, for the magazine)
for _k in ('smg_handle_on', 'smg_bolt_pull', 'smg_bolt_stop', 'smg_bolt_sear'):
    _v, _d = gunphys.ACTIONS[_k]
    gunphys.ACTIONS[_k + '_r'] = ((_v[0], -_v[1], _v[2], -_v[3], _v[4]), _d)

GUNS = {
    'mp40': dict(row='mp40_reload', sight='mp40', aim='viewmodel/mp40/coop_mp40_ads_mag.skc', cls='smg', vdir='viewmodel/mp40',
                 tik='models/weapons/mp40.tik', prop='models/ammo/mp40_clip.tik', propwin=(10, 48),
                 out_rel=10, in_rel=48,           # retail frames: hand on the magazine as it leaves / as it is seated
                 well=(0.0, 0.0, 1.0),            # the way the magazine leaves the well (gun frame; z = down)
                 t=dict(down=(3, 8), catch=7, out=(10, 14), outshow=17, outgo=21, gone=25, back=28, show=33, hold=36, under=40, seat=(44, 48),
                        tug=51.5, on=(55, 62),    # loaded: a tug on the seated magazine, then back up to the housing
                        reach=(50, 55), pull=(55, 61), let=63, on_e=(65, 71)),
                 # gun frame: x forward, y right, z down. add = from the handle's centre to its front face (+ a little low)
                 # fingers up and IN toward the gun from a wrist at the lower left; the palm on the receiver's wall, turned down with them
                 # 2b: palm DOWN and toward the gun, fingers forward-right and a little up: the eye sees the row of
                 # knuckles lead up to the handle and the handle against the index (sb4's hand, fingers up the wall
                 # with the palm on it, showed the eye only its back = "a fist"). Tried and dropped: palm to the shooter
                 # (thumb stands up into the centre box, 6 %), palm flat down at handle height (2.3 %, a large hand)
                 hook=dict(ref=61, fdir=_envf('SB_FDIR', (0.55, 0.7, -0.45)), pdir=_envf('SB_PDIR', (0.0, 0.5, 0.85)),
                           add=_envf('SB_HADD', (0.18, -0.3, 0.05)), fdir_hip=_envf('SB_FDIRH', (0.8, 0.3, -0.5)), pdir_hip=_envf('SB_PDIRH', (0.0, 1.0, 0.0)), curl=_envf('SB_HCURL', (0.0,))[0], mix=_envf('SB_HMIX', (0.5,))[0]),
                 # hip, rounds left: from the seat frame (the retail hand opens for its cock right after) the gun is
                 # brought back to the hip over 0.63 s (2b: by f60 left 0.5 s of still pose at the end of the row)
                 hip_blend=(48, 70), hip_reach=(52, 58)),
}


def _variant(base, key, **kw):
    """a gun that shares `base`'s hands rows but has its OWN handle / mesh (step 3): the same choreography baked on its
    own sight line and handle (smggun_<key>.json), staged as the per-weapon rows coopr_<key>_reload[_empty][_ads]
    (cgame CoopPerWeaponReloadAnim: they win over the prefix rows for exactly this weapon)"""
    g = dict(GUNS[base]); g['hook'] = dict(g['hook'])
    g.update(sight=key, out='coopr_%s_reload' % key)
    hk = kw.pop('hook', {})
    g.update(kw); g['hook'].update(hk)
    return g


GUNS['silenced_mp40'] = _variant('mp40', 'silenced_mp40', tik='models/weapons/mp40silenced.tik')
GUNS['mp40_reactivated'] = _variant('mp40', 'mp40_reactivated', tik='models/weapons/mp40_mp40r2.tik')
# handle on the RIGHT, worked by the firing hand (hook = the mirror image of the left-hand one). The pull sits on the
# reload sound's two clacks (f59, f64.5) in both clips; the left hand is back on its grip before the right one leaves.
_RIGHT = dict(cock='R', hook=dict(fdir=(0.55, -0.7, -0.45), pdir=(0.0, -0.5, 0.85), add=(0.18, 0.3, 0.05),
                                  fdir_hip=(0.8, -0.3, -0.5), pdir_hip=(0.0, -1.0, 0.0)))
# For a gun the firing hand cannot reach the handle of from the aim (reachcheck.py: PPS-43, handle forward at x 10.4 =
# 117 % of the arm from the shoulder; a clamped arm drags the gun with it) the LEFT hand goes UNDER the receiver, between
# trigger guard and magazine, and its fingers come up the right side in front of the handle, palm to the shooter (the
# under-reach used on right-handed rifles) - the firing hand never leaves its grip, the hand works low. At the hip the
# same hand goes OVER the receiver (the retail technique for right-side handles, e.g. the Type 100's own clip).
_UNDER = dict(handle='R', hook=dict(fdir=_envf('SB_UF', (0.5, -0.1, -0.85)), pdir=_envf('SB_UP', (-1.0, 0.0, -0.5)), add=_envf('SB_UA', (0.45, 0.0, 0.1)),
                                    approach=_envf('SB_UAP', (-0.6, 0.6, -2.2)), leave=(0.0, 0.3, -1.2), home=(-1.0, 1.0, -2.5),
                                    hip_built=1, fdir_hip=_envf('SB_UFH', (0.2, 0.7, 0.7)), pdir_hip=_envf('SB_UPH', (-0.9, 0.0, 0.4)), add_hip=(0.45, 0.0, -0.1)))
GUNS['silenced_pps_43'] = _variant('mp40', 'silenced_pps_43', tik='models/weapons/ppsh43silenced.tik', **_UNDER)


def knob(name):
    j = json.load(open(os.path.join(HERE, 'smggun_%s.json' % name)))
    return np.array(j['forward'], float), float(j['travel']), j


def ease_(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def pull_u(f, a, b):
    """how far back the handle is (0..1) at frame f - smggun.pull_curve's shape"""
    if f <= a:
        return 0.0
    if f >= b:
        return 1.0
    u = (f - a) / float(b - a)
    return 1 - (1 - u) ** 2


def hook_rel(g, hipclip, fwd, hip=False, hand='L'):
    """hand-to-gun relation (rows, pre-scale) of the support hand HOOKED on the handle at its FORWARD place, built from
    the hand's own geometry in the aim grip's finger pose (no borrowed art): the first joints of the index and middle
    finger stand in front of the handle's front face, pointing `fdir` (gun frame; up the receiver's side), the palm
    looking `pdir` (rearward: the pull is toward the shooter), the wrist below and left of the handle."""
    hk = g['hook']
    aimp = os.path.join('models', 'human', 'animation', g['aim'].replace('/', os.sep))
    ac = R.load(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'])
    pa = dict(R.pose_dict(ac, ac.numFrames - 1))
    pr = R.pose_dict(hipclip, hk['ref'])
    for ch in list(pa):                    # the finger pose the keys use: ('mix', ref, mix) = the aim grip opened toward the
        if ch.startswith('Bip01 %s Finger' % hand) and ch in pr:           # retail cocking hand's open fingers
            pa[ch] = R.qslerp(np.asarray(pa[ch], float), np.asarray(pr[ch], float), hk['mix'])
    Wa = R.evaluate(pa)
    Hh = Wa['Bip01 %s Hand' % hand]

    def loc(b):
        return (Wa[b][3, 0:3] - Hh[3, 0:3]) @ Hh[0:3, 0:3].T
    mcp = (loc('Bip01 %s Finger1' % hand) + loc('Bip01 %s Finger2' % hand)) / 2
    pip = (loc('Bip01 %s Finger11' % hand) + loc('Bip01 %s Finger21' % hand)) / 2
    tip = (loc('Bip01 %s Finger12' % hand) + loc('Bip01 %s Finger22' % hand)) / 2           # the last joints: the pads are just beyond
    df = tip - mcp; df /= np.linalg.norm(df)                               # the fingers' overall direction
    side = loc('Bip01 %s Finger4' % hand) - loc('Bip01 %s Finger1' % hand)
    nrm = np.cross(df, side); nrm /= np.linalg.norm(nrm)
    if (pip - (mcp + tip) / 2) @ nrm > 0:  # a curled finger's middle joint stands out on the BACK of the hand
        nrm = -nrm
    A = np.array([df, nrm, np.cross(df, nrm)])
    # at the HIP the gun is at arm's length: the same hook with the fingers reaching FORWARD to the handle (the aimed
    # direction, wrist under the handle, is out of the arm's reach there: 11 clamped frames)
    F = np.asarray(hk['fdir_hip' if hip else 'fdir'], float); F /= np.linalg.norm(F)
    P = np.asarray(hk['pdir_hip' if hip else 'pdir'], float); P = P - (P @ F) * F; P /= np.linalg.norm(P)
    Bt = np.array([F, P, np.cross(F, P)])
    Rr = A.T @ Bt
    # contact: the INDEX finger's last joint, its thumb-side edge against the handle's front face. cross(F, P) is the
    # index -> little finger direction: with the palm on the receiver's wall (P = +y) it points FORWARD, so the other
    # fingers stand in front of the index along the wall. (Run sb3 had the palm facing the shooter: index -> little
    # finger then pointed INTO the gun and the fingertips came out on its right side.)
    c = loc('Bip01 %s Finger12' % hand) - (1.0 if hand == 'L' else -1.0) * np.cross(df, nrm) * (hk.get('thick', 0.3) / R.S)
    tgt = (np.asarray(fwd, float) + np.asarray(hk['add'], float)) / R.S
    rel = np.eye(4); rel[0:3, 0:3] = Rr; rel[3, 0:3] = tgt - c @ Rr
    return rel


def curl_add(keys, deg=(26.0, 38.0, 26.0), hand='L'):
    out = {}
    for fi in (1, 2, 3, 4):
        for j, sfx in enumerate(('', '1', '2')):
            out['Bip01 %s Finger%d%s rot' % (hand, fi, sfx)] = [(k, w * deg[j]) for k, w in keys]
    return out


# ------------------------------------------------------------------------------------------------------- AIMED
def ads_spec(name, empty):
    g = GUNS[name]
    t = g['t']
    rows = H.fps_rows()
    hipclip = R.load(R.ANIM + rows[g['row']])
    n = hipclip.numFrames - 1
    fwd, travel, _ = knob(name)
    o, i = g['out_rel'], g['in_rel']
    wl = np.asarray(g['well'], float)
    d0, d1 = t['down']; o0, o1 = t['out']; s0, s1 = t['seat']
    AIM = dict(aim=1, fing='aim')
    ONMAG = dict(rel=o, fing=o)
    lp = {0: AIM, d0: AIM, d1: ONMAG, o0: ONMAG,
          # OUT: straight down the well until the lips are clear (the housing holds about 3 u of it), then down-left -
          # the eye sees the top of the magazine leave at the lower left before the hand goes under the frame
          o0 + 2: dict(rel=o, gun_add=tuple(wl * 2.4), fing=o),
          o1: dict(rel=o, gun_add=tuple(wl * 3.5), cam_add=_envf('SB_OUT1', (-0.2, 1.0, 0.0)), fing=o),
          # ...and is SEEN: swung out to the left of the gun, under the centre box, before it goes down to the pouch
          # (2b: the swap was on screen for 0.2 s - "too quiet")
          t['outshow']: dict(rel=o, gun_add=tuple(wl * 3.0), cam_add=_envf('SB_OUT2', (-0.6, 5.2, 0.6)), fing=o),
          t['outgo']: dict(rel=o, gun_add=tuple(wl * 3.6), cam_add=_envf('SB_OUT3', (-1.0, 7.2, -0.6)), fing=o),
          t['gone']: dict(cam=POUCH, rot='aim', fing=o), t['back']: dict(cam=POUCH, rot='aim', fing=i),
          # IN: the new magazine comes up BESIDE the gun on the left, in view under the centre box (the shooter indexes
          # the well), drops under the housing, slides in under the well and is driven up
          t['show']: dict(rel=i, gun_add=tuple(wl * 1.2), cam_add=_envf('SB_IN1', (-0.5, 5.0, 0.8)), fing=i),
          t['hold']: dict(rel=i, gun_add=tuple(wl * 1.5), cam_add=_envf('SB_IN1B', (-0.4, 4.5, 0.9)), fing=i),
          t['under']: dict(rel=i, gun_add=tuple(wl * 3.6), cam_add=_envf('SB_IN2', (-0.2, 2.4, 0.0)), fing=i),
          s0 - 1: dict(rel=i, gun_add=tuple(wl * 3.5), fing=i),
          s0 + 1: dict(rel=i, gun_add=tuple(wl * 2.4), fing=i),
          s1 - 1: dict(rel=i, gun_add=tuple(wl * 0.5), fing=i),
          s1: dict(rel=i, fing=i), s1 + 2: dict(rel=i, fing=i)}
    # support weight: never 0 - the gun is still in the shoulder and the firing hand while the left hand is away
    # 2b: the weight comes back onto the left hand from the moment the magazine meets the well until after the seat
    # (it was SHOULDER until s0 and 0.75 at s1: the sag came back in 4 frames, with the seat's push = a hop)
    sup = [(0, 1), (d0, 1), (d1, 0.7), (o0 + 1, 0.55), (o1, SHOULDER), (s0 - 4, SHOULDER), (s1 + 3, 0.75)]
    ev = [(t['catch'], 'smg_catch'), (o0 - 0.5, 'smg_mag_drag'), (o0 + 2.0, 'smg_mag_free'), (s0 - 0.5, 'smg_mag_enter'), (s1 - _envf('SB_SEATAT', (3.0,))[0], 'smg_mag_seat', _envf('SB_SEAT', (0.8,))[0])]
    kw = {}
    if empty and g.get('cock') == 'R':
        # A handle on the RIGHT (step 3): the left hand seats the magazine and goes straight back to its grip (it and
        # the shoulder hold the gun), then the FIRING hand leaves the grip, hooks the handle from below-right, pulls it
        # back to the sear and returns - the mirror image of the left-hand pull, same physics with the roll reversed.
        a0, a1 = t['on_r']
        lp[a0] = dict(rel=i, fing=i)
        lp[a0 + 3] = dict(aim=1, cam_add=(0.0, 0.6, -1.2), fing=('mix', i, 0.5))
        for f in range(a1, n + 1):
            lp[f] = AIM
        r0, r1 = t['reach_r']; p0, p1 = t['pull']; e0, e1 = t['on_er']
        T = hook_rel(g, hipclip, fwd, hand='R')
        ck = g['hook'].get('curl_r', -0.8)
        rp = {0: AIM, r0: AIM, r1 - 2: dict(relT=T, cam_add=(-0.3, -1.3, -1.3), fing='aim'), r1: dict(relT=T, fing='aim')}
        for f in range(p0, p1 + 1):
            rp[f] = dict(relT=T, gun_add=(-travel * pull_u(f, p0, p1), 0.0, 0.0), fing='aim')
        rp[t['let']] = dict(relT=T, gun_add=(-travel, 0.0, 0.0), cam_add=(0.0, -0.5, -0.5), fing='aim')
        rp[e0] = dict(aim=1, cam_add=(1.0, -1.0, -1.5), fing='aim')
        for f in range(e1, n + 1):
            rp[f] = AIM
        kw['right_path'] = rp
        kw['finger_add'] = curl_add([(r0, 0.0), (r1, ck), (p1, ck), (t['let'] + 2, 0.0), (n, 0.0)], hand='R')
        sup += [(a0, 0.75), (a1, 0.95), (r0, 0.95), (r1, 0.7), (p1, 0.7), (e0, 0.7), (e1, 1.0), (n, 1.0)]
        ev += [(a1 - 3.0, 'smg_hand_on', 0.7), (r1 - 1.0, 'smg_handle_on_r'), (p0, 'smg_bolt_pull_r'), (p1 - 0.5, 'smg_bolt_stop_r'),
               (t['let'] - 1.0, 'smg_bolt_sear_r'), (e1 - 3.0, 'smg_grip_on')]
    elif empty:
        r0, r1 = t['reach']; p0, p1 = t['pull']; e0, e1 = t['on_e']
        T = hook_rel(g, hipclip, fwd)
        ck = g['hook']['curl']
        lp[r1] = dict(relT=T, fing=('mix', g['hook']['ref'], g['hook']['mix']))
        hk = g['hook']
        sfx = '_r' if g.get('handle') == 'R' else ''        # the handle's side: which way the pull rolls the gun
        lp[r1 - 2] = dict(relT=T, cam_add=hk.get('approach', (-0.3, 1.3, -1.3)), fing=('mix', g['hook']['ref'], g['hook']['mix']))   # up to the handle from below-left
        for f in range(p0, p1 + 1):
            lp[f] = dict(relT=T, gun_add=(-travel * pull_u(f, p0, p1), 0.0, 0.0), fing=('mix', g['hook']['ref'], g['hook']['mix']))
        back = (-travel, 0.0, 0.0)
        lp[t['let']] = dict(relT=T, gun_add=back, cam_add=hk.get('leave', (0.0, 0.5, -0.5)), fing=('mix', g['hook']['ref'], 0.9))
        lp[e0] = dict(aim=1, cam_add=hk.get('home', (-1.5, 2.0, -2.5)), fing=('mix', g['hook']['ref'], 0.6))
        for f in range(e1, n + 1):
            lp[f] = AIM
        kw['finger_add'] = curl_add([(r0, 0.0), (r1, ck), (p1, ck), (t['let'], 0.0), (n, 0.0)])
        sup += [(r0, 0.6), (r1, 0.4), (p1, 0.4), (e0, 0.4), (e1, 1.0), (n, 1.0)]
        ev += [(r1 - 1.0, 'smg_handle_on' + sfx), (p0, 'smg_bolt_pull' + sfx), (p1 - 0.5, 'smg_bolt_stop' + sfx), (t['let'] - 1.0, 'smg_bolt_sear' + sfx), (e1 - 3.5, 'smg_hand_on', 0.6)]
    else:
        a0, a1 = t['on']
        lp[a0] = dict(rel=i, fing=i)
        lp[a0 + 3] = dict(aim=1, cam_add=(0.0, 0.6, -1.2), fing=('mix', i, 0.5))
        for f in range(a1, n + 1):
            lp[f] = AIM
        sup += [(a0, 0.75), (a1, 1.0), (n, 1.0)]
        ev += [(t['tug'], 'smg_mag_tug'), (a1 - 3.0, 'smg_hand_on')]
    # fade 14: the last frames ease onto the exact aim (run sb3 with the default 6: 0.08 deg left when the row ends)
    ph = gunphys.simulate(n + 1, hipclip.frameTime, g['cls'], support=sup, fade=14,
                          mag=[(0, 1), (o0, 1), (o0 + 3, 0), (s0, 0), (s1, 1)], events=ev, strength=STRENGTH, hand=-1.0)
    if os.environ.get('SB_TRACE'):
        X = ph['X']; a_, b_ = [int(v) for v in os.environ['SB_TRACE'].split(':')]
        print('    f   drop   roll  pitch   side   back   | per-frame step: drop u, pitch deg')
        for f in range(a_, min(b_, n) + 1):
            print('   %3d %6.2f %6.2f %6.2f %6.2f %6.2f   | %+.3f %+.3f' % ((f,) + tuple(X[f]) + (X[f][0] - X[f - 1][0], X[f][2] - X[f - 1][2])))
    kw.update(gun=g['sight'], charge=g['aim'], fixed_right=True, dip=ph['dip'], left_path=lp, weight=dict(on=False), handover=False,
              tag_map={0: o, t['gone']: o, t['back']: i, n: i},
              elbow_vec={'R': (0.0, -1.0, -0.2), 'L': _envf('SB_ELB', (0.0, 0.35, -1.0))},
              elbow_down={'L': [(0, 4.0), (n, 4.0)]})
    return kw, ph


def bake_ads(name, root):
    g = GUNS[name]
    rep = {}
    for empty in (False, True):
        kw, ph = ads_spec(name, empty)
        rc = H.auto_recipe(g['row'], **kw)
        H.RECIPES[g['row']] = rc
        sk, _ = H.bake(g['row'], RB.CTL)
        bts = R.skc_io.write(sk)
        out = '%s/%s_reload_%sads.skc' % (g['vdir'], name, 'empty_' if empty else '')
        dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        print(name, 'aimed', 'empty ' if empty else 'loaded', '->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8])
        print('   ', ph['report'])
        rep['ads_empty' if empty else 'ads_loaded'] = dict(clip=out, peak_deg=round(ph['peak_deg'], 2), settle_s=round(ph['settle_s'], 2),
                                                          drop=round(float(np.abs(ph['X'][:, 0]).max()), 2), back=round(float(np.abs(ph['X'][:, 4]).max()), 2),
                                                          roll=round(float(np.abs(ph['X'][:, 1]).max()), 2))
    return rep


# --------------------------------------------------------------------------------------------------------- HIP
def bake_hip(name, root):
    """<row> (rounds left): the retail clip to the seat, then straight to its own end pose - no cock.
    <row>_empty: the retail clip with the left hand re-keyed onto the handle for the pull (gun and firing arm = retail)."""
    g = GUNS[name]
    rows = H.fps_rows()
    src = rows[g['row']]
    hip = R.load(R.ANIM + src)
    n = hip.numFrames
    cm = R.chanmap(hip)
    fwd, travel, kj = knob(name)
    rep = {}
    # ---- rounds left: no cock
    out = R.load(R.ANIM + src)
    b0, b1 = g['hip_blend']
    pe = R.pose_dict(hip, n - 1)
    pa = R.pose_dict(hip, b0)
    hold = g.get('hip_hold', 3)             # the palm stays under the seated magazine for a moment before the gun comes back
    for f in range(b0, n):
        w = max(0.0, min(1.0, (f - b0 - hold) / float(b1 - b0 - hold)))
        w = w * w * (3 - 2 * w)
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
    print(name, 'hip   loaded ->', o1, n, 'frames', hashlib.md5(bts).hexdigest()[:8], '(retail to f%d, then its end pose by f%d: no cock)' % (b0, b1))
    rep['hip_loaded'] = dict(clip=o1)
    if g.get('cock') == 'R':
        rep['hip_empty'] = bake_hip_right(name, root, g, hip, cm, dst, fwd, travel, kj)
        return rep
    # ---- empty: the hand on the handle
    # The retail cocking hand is at the handle's height and place ALONG the gun, but 3 u out to the left of the
    # receiver (index tip at y -5.3; the wall is at -1.8), and at arm's length (reach 25.9 of 26.8 u): a built hook
    # cannot be reached there. So the RETAIL hand is kept, wrist and all, and turned about its wrist by the smallest
    # rotation that puts its index fingertip on the handle's front face (the wrist backs off along that line so the
    # tip neither falls short nor passes through). The handle itself follows the retail fingertip's place along the
    # gun, frame by frame (smggun.py `hip_curve`) - so hand and handle cannot drift apart.
    out = R.load(R.ANIM + src)
    curve = kj['hip_curve']                      # forward fraction per frame of the gun's reload clock
    r0, r1 = g['hip_reach']
    moving = [f for f in range(n) if 0.0 < curve[min(f, len(curve) - 1)] < 1.0]
    p0, p1 = (min(moving) - 1, max(moving) + 1) if moving else (r1, r1 + 3)
    let = p1 + 2
    e1 = min(n - 3, let + 8)
    add = np.asarray(g['hook'].get('add_hip', (0.3, -0.25, 0.1)), float)
    used = []
    Th = hook_rel(g, hip, fwd, hip=True) if g['hook'].get('hip_built') else None
    # 2b: the RELEASE - the retail hand springs open (fingers splayed) as it lets go. The fingers now go from their
    # hooked pose at the end of the pull straight to the clip's last pose (the hip grip), eased over 0.33 s
    # Run sc1: with that, the PULL itself still showed the retail's flat open hand. From the reach on the fingers close
    # half way to the hip grip (`hip_mix`): a hooked hand; the fingertip the hand is turned onto the handle by is taken
    # from THAT finger pose.
    pf, pl = dict(R.pose_dict(hip, p1)), R.pose_dict(hip, n - 1)
    fch = [ch for ch in hip.names if ch.startswith('Bip01 L Finger') and ch.endswith(' rot')]
    # Runs sc4 / sc6 (coordinator): with the closing spread over the reach (f52-58, half way) the hand still FLOATED to
    # the knob open. It now closes as it leaves the magazine: three quarters to the hip grip by the frame the reach
    # starts (`hip_close` frames before r0), and stays so through the pull.
    hmix = g['hook'].get('hip_mix', 0.75)
    hclose = g['hook'].get('hip_close', 4)

    def hooked(pd, f):
        u = hmix * ease_((f - (r0 - hclose)) / float(hclose))
        for ch in fch:
            pd[ch] = R.qslerp(np.asarray(pd[ch], float), np.asarray(pl[ch], float), u)
    hooked(pf, p1)
    for f in range(r0 - hclose, r0):         # the frames before the reach: only the fingers change
        pd = dict(R.pose_dict(hip, f))
        hooked(pd, f)
        K.write_frame(out, hip, cm, f, pd)

    def relax(pd, f):
        u = ease_((f - p1) / 10.0)
        for ch in fch:
            pd[ch] = R.qslerp(np.asarray(pf[ch], float), np.asarray(pl[ch], float), u)
    for f in range(e1 + 1, n):
        pd = dict(R.pose_dict(hip, f))
        relax(pd, f)
        K.write_frame(out, hip, cm, f, pd)
    for f in range(r0, e1 + 1):
        ph = dict(R.pose_dict(hip, f))
        if f <= p1:
            hooked(ph, f)
        else:
            relax(ph, f)
        Wh = R.evaluate(ph)
        G = Wh['tag_weapon_right']
        HLr = Wh['Bip01 L Hand']
        wr = HLr[3, 0:3]
        tipw = Wh['Bip01 L Finger12'][3, 0:3]
        kx = fwd[0] - travel * (1.0 - curve[min(f, len(curve) - 1)])
        tgt = (np.r_[(np.array([kx, fwd[1], fwd[2]]) + add) / R.S, 1.0] @ G)[0:3]
        a_ = tipw - wr; la_ = np.linalg.norm(a_); a_ /= la_
        b_ = tgt - wr; b_ /= np.linalg.norm(b_)
        ax = np.cross(a_, b_); sn = np.linalg.norm(ax)
        Rm = R.axis_angle_rows(ax / sn, math.degrees(math.atan2(sn, a_ @ b_))) if sn > 1e-6 else np.eye(3)
        HLn = HLr.copy()
        HLn[0:3, 0:3] = HLr[0:3, 0:3] @ Rm
        HLn[3, 0:3] = tgt - la_ * b_
        if g['hook'].get('hip_built'):
            Tn = Th.copy()
            Tn[3, 0] -= travel * (1.0 - curve[min(f, len(curve) - 1)]) / R.S
            HLn = Tn @ G
            tgt = HLn[3, 0:3] + (Wh['Bip01 L Finger12'][3, 0:3] - HLr[3, 0:3]) @ HLr[0:3, 0:3].T @ HLn[0:3, 0:3]
        w = min(ease_((f - r0) / float(max(1, r1 - r0))), ease_((e1 - f) / float(max(1, e1 - let))))
        HL = B.blend_H(HLr, HLn, w)
        pd = dict(ph)
        K.solve_arms(pd, Wh, Wh['Bip01 R Hand'], HL, G, None)
        # the left weapon tag (no prop after the seat) keeps its retail value; solve_arms re-keys it onto the gun
        for ch in ('tag_weapon_left rot', 'tag_weapon_left pos'):
            if ch in ph:
                pd[ch] = ph[ch]
        if f > p1:
            relax(pd, f)
        K.write_frame(out, hip, cm, f, pd)
        if w > 0.99:
            Wn = R.evaluate(R.pose_dict(out, f))
            used.append(float(np.linalg.norm(Wn['Bip01 L Finger12'][3, 0:3] - tgt) * R.S))
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(n)]
    bts = R.skc_io.write(out)
    o2 = '%s/coop_%s_reload_empty_hip.skc' % (g['vdir'], name)
    dst = os.path.join(root, 'models', 'human', 'animation', o2.replace('/', os.sep))
    open(dst, 'wb').write(bts)
    print(name, 'hip   empty  ->', o2, n, 'frames', hashlib.md5(bts).hexdigest()[:8], '(retail hand turned in onto the handle f%d-%d, handle moves f%d-%d; index tip to its front face %.2f u at worst)' % (r1, let, p0, p1, max(used) if used else -1))
    rep['hip_empty'] = dict(clip=o2)
    return rep


def bake_hip_right(name, root, g, hip, cm, loaded_path, fwd, travel, kj):
    """HIP, empty, a handle on the RIGHT: the rounds-left clip (magazine only; the retail left-hand mime on the gun's
    left is gone with it) + the FIRING hand: it leaves the grip, hooks the handle (hook_rel, built from the hand's own
    geometry, fingers opened from the grip), rides it back along the gun clip's own curve and goes home. The left hand
    holds the gun meanwhile, as in the aimed clip."""
    base = R.load(loaded_path)
    out = R.load(loaded_path)
    n = hip.numFrames
    curve = kj['hip_curve']
    r0, r1 = g.get('hip_reach_r', (50, 57))
    moving = [f for f in range(n) if 0.0 < curve[min(f, len(curve) - 1)] < 1.0]
    p0, p1 = min(moving) - 1, max(moving) + 1
    let = p1 + 2
    e1 = min(n - 2, let + 8)
    T = hook_rel(g, hip, fwd, hip=True, hand='R')
    fch = [ch for ch in hip.names if ch.startswith('Bip01 R Finger') and ch.endswith(' rot')]
    opn = g['hook'].get('curl_r_hip', -22.0)        # deg per joint: the grip's fist opened into a hook
    clamp = 0
    for f in range(r0, e1 + 1):
        ph = dict(R.pose_dict(base, f))
        w = min(ease_((f - r0) / float(max(1, r1 - r0))), ease_((e1 - f) / float(max(1, e1 - let))))
        for ch in fch:
            ph[ch] = R.rows_to_quat(R.axis_angle_rows((0, 0, 1), opn * w) @ R.quat_to_rows(ph[ch]))
        Wh = R.evaluate(ph)
        G = Wh['tag_weapon_right']
        HRr = Wh['Bip01 R Hand']
        Tn = T.copy()
        Tn[3, 0] -= travel * (1.0 - curve[min(f, len(curve) - 1)]) / R.S
        HRn = Tn @ G
        HR = B.blend_H(HRr, HRn, w)
        # between the grip and the handle the hand swings out to the right, clear of the receiver
        HR[3, 0:3] += (np.array([0.0, 1.6, 0.0]) / R.S) @ G[0:3, 0:3] * math.sin(math.pi * w) * (1.0 if f < p0 or f > let else 0.0)
        pd = dict(ph)
        K.solve_arms(pd, Wh, HR, Wh['Bip01 L Hand'], G, None)
        for ch in ('tag_weapon_left rot', 'tag_weapon_left pos'):
            if ch in ph:
                pd[ch] = ph[ch]
        K.write_frame(out, hip, cm, f, pd)
        if w > 0.99:
            Wn = R.evaluate(R.pose_dict(out, f))
            clamp = max(clamp, float(np.linalg.norm(Wn['Bip01 R Hand'][3, 0:3] - HRn[3, 0:3]) * R.S))
    out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(n)]
    bts = R.skc_io.write(out)
    o2 = '%s/coop_%s_reload_empty_hip.skc' % (g['vdir'], name)
    open(os.path.join(root, 'models', 'human', 'animation', o2.replace('/', os.sep)), 'wb').write(bts)
    print(name, 'hip   empty  ->', o2, n, 'frames', hashlib.md5(bts).hexdigest()[:8],
          '(RIGHT hand: off the grip f%d, on the handle f%d, pull f%d-%d, home f%d; wrist short of its place by %.2f u at worst)' % (r0, r1, p0, p1, e1, clamp))
    return dict(clip=o2)


def rows_extra(name, rep):
    """the lane's rows for stage_rows.py (rows_extra.json): hip rounds-left = no cock; <row>_empty hip + both aimed rows"""
    g = GUNS[name]
    p = os.path.join(HERE, 'rows_extra.json')
    e = json.load(open(p)) if os.path.isfile(p) else {'repoint': [], 'add': []}
    row = g['row']
    if g.get('out'):                         # per-weapon rows: all four are new rows, after the prefix's own block
        o_ = g['out']
        names = (o_, o_ + '_empty', o_ + '_ads', o_ + '_empty_ads')
        e['add'] = [x for x in e['add'] if x[0] not in names]
        e['add'] += [[o_, rep['hip_loaded']['clip'], '0.1', row + '_empty_ads'], [o_ + '_empty', rep['hip_empty']['clip'], '0.1', o_],
                     [o_ + '_ads', rep['ads_loaded']['clip'], '0.1', o_ + '_empty'], [o_ + '_empty_ads', rep['ads_empty']['clip'], '0.1', o_ + '_ads']]
        json.dump(e, open(p, 'w'), indent=1)
        return
    e['repoint'] = [x for x in e['repoint'] if x[0] != row] + [[row, rep['hip_loaded']['clip']]]
    names = (row + '_empty', row + '_ads', row + '_empty_ads')
    e['add'] = [x for x in e['add'] if x[0] not in names]
    e['add'] += [[row + '_empty', rep['hip_empty']['clip'], '0.1', row],
                 [row + '_ads', rep['ads_loaded']['clip'], '0.1', row + '_empty'],
                 [row + '_empty_ads', rep['ads_empty']['clip'], '0.1', row + '_ads']]
    json.dump(e, open(p, 'w'), indent=1)


# --------------------------------------------------------------------------------------------------- offline looks
def clip_of(name, root, which):
    g = GUNS[name]
    m = dict(ads_loaded=('%s/%s_reload_ads.skc' % (g['vdir'], name), 'reload'), ads_empty=('%s/%s_reload_empty_ads.skc' % (g['vdir'], name), 'reload_ads_empty'),
             hip_loaded=('%s/coop_%s_reload_hip.skc' % (g['vdir'], name), 'reload'), hip_empty=('%s/coop_%s_reload_empty_hip.skc' % (g['vdir'], name), 'reload_empty'),
             retail=(H.fps_rows()[g['row']], 'reload'))[which]
    p = os.path.join(root, 'models', 'human', 'animation', m[0].replace('/', os.sep))
    return (p if os.path.isfile(p) else R.ANIM + m[0]), m[1]


def box_check(name, root, which, W=320, sheet=None, every=2, cols=10):
    """offbox.py's measure (extra centre-box cover beyond the settled aim, every frame) WITH the magazine prop drawn"""
    from PIL import Image, ImageDraw
    g = GUNS[name]
    path, anim = clip_of(name, root, which)
    c = R.load(path)
    aimp = os.path.join(root, 'models', 'human', 'animation', g['aim'].replace('/', os.sep))
    aim = R.load(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'])
    sight = V.SIGHTS[g['sight']]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), RB.CTL), sight)
    Hh = W * 9 // 16
    fov = V.weapon_fov()
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(Hh * 0.4), int(Hh * 0.6)

    def frame(cl, f, an, tex):
        surfs, E, Wb = V.scene2(R.pose_dict(cl, f), g['sight'], sight['tik'], an, f * cl.frameTime, RB.CTL, corr, None)
        return V.shade_render(surfs, E, fov, W, Hh, bg=(206, 212, 218), tex=tex)
    V.PROP.clear()
    _, ids, _ = frame(aim, aim.numFrames - 1, 'idle', False)
    m0 = (ids >= 0)[y0:y1, x0:x1]
    r = max(1, int(round(6 * W / 1280.0)))
    aimmask = m0.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            aimmask |= np.roll(np.roll(m0, dy, axis=0), dx, axis=1)
    V.PROP.update(tik=g['prop'], t0=g['propwin'][0] * c.frameTime, t1=g['propwin'][1] * c.frameTime, tag='tag_weapon_left')
    ex, ims = [], []
    for f in range(c.numFrames):
        want = bool(sheet) and f % every == 0
        rgb, ids, _ = frame(c, f, anim, want)
        e = float(((ids >= 0)[y0:y1, x0:x1] & ~aimmask).mean())
        ex.append(e)
        if want:
            im = Image.fromarray(rgb)
            d = ImageDraw.Draw(im)
            d.rectangle((x0, y0, x1, y1), outline=(255, 230, 0) if e <= 0.02 else (255, 0, 0))
            d.text((3, 2), 'f%d %.1f%%' % (f, 100 * e), fill=(0, 0, 0))
            ims.append(im)
    V.PROP.clear()
    over = ' '.join('%d:%.0f' % (k, 100 * e) for k, e in enumerate(ex) if e > 0.02) or '-'
    print('%s %-10s box extra max %.1f %%  frames over 2 %%: %s' % (name, which, 100 * max(ex), over))
    if sheet and ims:
        cols = min(cols, len(ims))
        S = Image.new('RGB', (W * cols, Hh * ((len(ims) + cols - 1) // cols)), 'white')
        for k, im in enumerate(ims):
            S.paste(im, ((k % cols) * W, (k // cols) * Hh))
        S.save(sheet, quality=86)
        print('   ', sheet)
    return max(ex), ex


def closeup(name, root, which, frames, out, W=420, cam=(-7.0, 9.0, 4.5), cols=4):
    """the handle and the hand on it, close, from the left-rear-above (the handle = the last 24 vertices of its surface)"""
    from PIL import Image, ImageDraw
    import raster
    g = GUNS[name]
    path, anim = clip_of(name, root, which)
    c = R.load(path)
    aimp = os.path.join(root, 'models', 'human', 'animation', g['aim'].replace('/', os.sep))
    aim = R.load(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'])
    sight = V.SIGHTS[g['sight']]
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), RB.CTL), sight)
    surf = json.load(open(os.path.join(HERE, 'smggun_%s.json' % name))).get('surface', 'gun1')
    V.PROP.clear()
    ims = []
    for f in frames:
        if f >= c.numFrames:
            continue
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), g['sight'], sight['tik'], anim, f * c.frameTime, RB.CTL, corr, None)
        kn = [s for s in surfs if s['name'] == surf][0]['P'][-24:].mean(0)
        lh = [s for s in surfs if s['name'] == 'lefthand'][0]['P']
        dmin = float(np.linalg.norm(lh - kn, axis=1).min())
        rgb, _, _ = raster.render({'surfs': surfs}, kn + np.asarray(cam, float), kn, np.array([0, 0, 1.0]), fov=40, W=W, H=W * 3 // 4,
                                  bg=(206, 212, 218), znear=1.0, tex=True)
        im = Image.fromarray(rgb.astype(np.uint8))
        ImageDraw.Draw(im).text((4, 4), '%s f%d  hand to handle %.2f u' % (which, f, dmin), fill=(0, 0, 0))
        print('f%d nearest left-hand vertex to the handle centre %.2f u' % (f, dmin))
        ims.append(im)
    cols = min(cols, len(ims))
    S = Image.new('RGB', (W * cols, (W * 3 // 4) * ((len(ims) + cols - 1) // cols)), 'white')
    for k, im in enumerate(ims):
        S.paste(im, ((k % cols) * W, (k // cols) * (W * 3 // 4)))
    S.save(out, quality=88)
    print(out)


def look(name, root, which, frames, out, W=400, hip=False):
    """eye + left side + below-left panels per frame, gun action and magazine prop drawn"""
    sys.path.insert(0, HERE)
    import sideview as SV
    from PIL import Image, ImageDraw
    g = GUNS[name]
    path, anim = clip_of(name, root, which)
    c = R.load(path)
    aimp = os.path.join(root, 'models', 'human', 'animation', g['aim'].replace('/', os.sep))
    corr = SV.corr_of(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'], g['sight'])
    SV.V.PROP.clear()
    SV.V.PROP.update(tik=g['prop'], t0=g['propwin'][0] * c.frameTime, t1=g['propwin'][1] * c.frameTime, tag='tag_weapon_left')
    rows_ = []
    for f in frames:
        if f >= c.numFrames:
            continue
        ps = SV.panels(c, f, g['sight'], corr, anim, W)
        ImageDraw.Draw(ps[0]).text((4, 4), '%s %s f%d' % (name, which, f), fill=(0, 0, 0))
        rows_.append(ps[1:] if hip == True else (ps[:1] if hip == 'eye' else ps))
    k = len(rows_[0])
    per = 2 if k == 3 else (4 if k == 1 else 3)
    Wp, Hp = rows_[0][0].size
    S = Image.new('RGB', (Wp * k * per, Hp * ((len(rows_) + per - 1) // per)), 'white')
    for i, ps in enumerate(rows_):
        for j, im in enumerate(ps):
            S.paste(im, (((i % per) * k + j) * Wp, (i // per) * Hp))
    S.save(out, quality=86)
    SV.V.PROP.clear()
    print(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('root'); ap.add_argument('--look'); ap.add_argument('--frames', default='0:76:4')
    ap.add_argument('--which', default='ads_empty'); ap.add_argument('--box', action='store_true'); ap.add_argument('--sheet')
    ap.add_argument('--eye', action='store_true'); ap.add_argument('--cu'); ap.add_argument('--only', default='ads,hip'); ap.add_argument('--nobake', action='store_true'); ap.add_argument('--w', type=int, default=400)
    a = ap.parse_args()
    rep = {}
    if not a.nobake:
        if 'ads' in a.only:
            rep.update(bake_ads(a.gun, a.root))
        if 'hip' in a.only:
            rep.update(bake_hip(a.gun, a.root))
        if len(rep) == 4 and os.path.abspath(a.root) == os.path.abspath(os.path.join(HERE, '..', 'assets')):
            rows_extra(a.gun, rep)
            p = os.path.join(HERE, 'smgphys.json')
            d = json.load(open(p)) if os.path.isfile(p) else {}
            d[a.gun] = rep
            json.dump(d, open(p, 'w'), indent=1, sort_keys=True)
    if a.box:
        for w_ in a.which.split(','):
            box_check(a.gun, a.root, w_, sheet=(a.sheet.replace('.jpg', '_%s.jpg' % w_) if a.sheet else None))
    p = [int(x) for x in a.frames.split(':')] if ':' in a.frames else None
    fr = list(range(*p)) if p else [int(x) for x in a.frames.split(',')]
    if a.cu:
        closeup(a.gun, a.root, a.which, fr, a.cu)
    if a.look:
        look(a.gun, a.root, a.which, fr, a.look, W=a.w, hip=('eye' if a.eye else (a.which.startswith('hip') or a.which == 'retail')))

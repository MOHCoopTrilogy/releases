"""Aimed full reload of a rifle to the 2026-10-12 standard, from the gun's own HIP technique.

Hands: hold_bake - both hands keep the retail hip clip's hand-to-gun relation frame by frame (its own contact with the
bolt, the clip, the magazine), blended from / to the aim grip at the two ends; arms by IK; the camera never moves.
Gun: NOT keyed frame by frame. The shooter's intent is a short list of HOLDS (5 numbers each, camera frame: drop u,
roll deg + = top to the right, pitch deg + = muzzle down, side u + = left, back u + = toward the eye; rotation about
the butt in the shoulder):
    'bolt'  off the cheek along the sight line, canted to the working hand - the bolt is worked on the sights
    'low'   the rifle brought DOWN under the centre box, action turned up to the eye - a clip / magazine is worked there
and gunphys (tools/gunphys.py, a rifle class) is the mass on a damped spring that FOLLOWS those holds (it lags, and
settles after each move) and answers every stroke of the action with an impulse at the frame the gun's own clip makes
it. The result goes in as hold_bake's `dip` (pivot = the butt).

    cd rifles/assets; python ../tools/riflereload.py kar98 [--set low.drop=6 ...] [--scale 4]
"""
import sys, os, json, argparse, hashlib, copy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boltphys as BP           # RIFLE class + rb_* actions (and the shared gunphys)
gunphys = BP.gunphys
T = BP.T
_c = os.getcwd(); os.chdir(T)
import hold_bake as H
os.chdir(_c)
R = H.R
CTL = BP.CTL

gunphys.ACTIONS.update({
    'clip_set':  ((2.0, -6.0, 3.0, 0.0, 0.0), 2.0),      # the charger set into its guide from above
    'clip_push': ((9.0, -5.0, 9.0, 0.0, -1.0), 3.0),     # five rounds thumbed down against the magazine spring: the rifle is pushed down
    'mag_out_r': ((-3.0, 0.0, -8.0, 0.0, 0.0), 3.0),     # a box magazine pulled out below: the rifle lifts as the weight leaves
    'mag_in_r':  ((-10.0, 0.0, 14.0, 0.0, 0.6), 2.5),    # ...and rocked / pushed home from below
})

PIVOT = -22.0       # hold_bake dip pivot: 22 u BEHIND the eye along the sight line = the butt in the shoulder
GUNS = {
    'kar98': dict(
        gun='kar98', hip='viewmodel/rifle/kar98_reload.skc', charge='viewmodel/kar_stand00.skc', offhand=(1, 100),
        out='viewmodel/rifle/kar98_reload_ads.skc', enter=6, exit=8,
        # retail timeline (30 fps): knob lifted 8-9, bolt back 14-15, hand to the pouch 21-33, clip on the gun 43,
        # pushed 53-54 (charger) and 62-63 (rounds), bolt forward 78-79 (the charger is thrown out), down 82-84,
        # hand back on the grip 93-99
        holds=dict(bolt=dict(drop=1.5, roll=3.0, pitch=2.5, side=0.0, back=-3.0),
                   # LOW: the muzzle swung down about the butt (which stays in the shoulder, so the left arm still
                   # reaches the fore-end): the open action comes under the centre box, its top turned to the eye
                   # LOW: the butt dropped from the shoulder toward the armpit, the rifle a little forward and turned to
                   # the working hand: the open action sits under the centre box with its top to the eye (a muzzle-down
                   # swing about the butt put it below the frame: v2), the charger is thumbed in there
                   low=dict(drop=4.3, roll=12.0, pitch=3.0, side=0.8, back=-2.5),
                   # the bolt is shoved home while the rifle is still on its way up
                   close=dict(drop=2.3, roll=4.0, pitch=3.0, side=0.0, back=-3.0),
                   down=dict(drop=1.5, roll=0.0, pitch=2.5, side=0.0, back=0.0)),
        # 'down' = the bolt hold's drop and muzzle dip alone: the rifle leaves and re-enters the aim downward first
        pose=[(0, None), (2, 'down'), (5, 'bolt'), (17, 'bolt'), (30, 'low'), (63, 'low'), (73, 'close'), (85, 'close'),
              (91, 'down'), (98, None), (101, None)],
        # the bolt strokes are worked with key_bolt's grip (one wrapped grip from retail frame 12, rolled under and
        # swung right of the knob so the hand body stays under the sight line), carried by the gun's own bolt bone
        bolt=dict(anim='reload', gref=12, roll=35.0, yaw=-40.0, spans=[(7, 18), (71, 85)]),
        # 55-60 the retail hand lifts the empty charger off and flicks it away - high enough to cross the centre
        # with the gun this near the eye (and the lens at the hip, bug-3451): the lift is kept low (gun frame: +y right, +z down)
        # prop_from 8: the hand-over to the off hand at frame 1 is FADED by the cgame from the main-hand tag; with the
        # prop's value on that tag from frame 1 the rifle started the reload with a 0.1 s jump to the left (run ra6)
        prop_until=51, prop_from=8,
        rhand=dict(aim=[(0, 3), (97, 101)], rel=(21, 68), way={5: (-0.8, 2.2, 2.6)},      # the reach to the knob dips under the sight line (run ra5: 3-5 % for two frames)
                   add={55: (0, 0.5, 1.2), 56: (0, 1.0, 2.6), 57: (0, 1.5, 3.6), 58: (0, 1.5, 3.4), 59: (0, 1.0, 2.2), 60: (0, 0.4, 0.9)}),
        support=[(0, 1), (3, 1), (6, 0), (92, 0), (98, 1)],
        events=[(8, 'rb_up'), (14, 'rb_back'), (15, 'rb_stop'), (43, 'clip_set'), (53, 'clip_push'), (61, 'clip_push', 0.7),
                (78, 'rb_fwd'), (82, 'rb_down'), (95, 'rb_grip')]),
}


def phys(g, n, ft, sc):
    z = (0.0,) * 5
    hv = lambda k: z if k is None else tuple(g['holds'][k][d] for d in gunphys.DOF)
    ev = [(e[0], e[1], (e[2] if len(e) > 2 else 1.0) * sc) for e in g['events']]
    r = gunphys.simulate(n, ft, BP.RIFLE, support=g['support'], events=ev, pose=[(f, hv(k)) for f, k in g['pose']], fade=5)
    return r, ev


def right_path(g, hip):
    """hold_bake right_path: the aim grip at the ends, the retail hand-to-gun relation frame by frame in between, and
    on the bolt strokes one wrapped knob grip riding the gun's bolt bone (key_bolt's technique)"""
    import anahip, boltgrip
    V = H.V; B = H.B
    rp = {}
    for a, b in g['rhand']['aim']:
        for f in range(a, b + 1):
            rp[f] = dict(aim=1)
    for f, add in g['rhand'].get('way', {}).items():      # reach waypoints: the aim grip moved in the gun frame (u: fwd, right, down)
        rp[f] = dict(aim=1, gun_add=add)
    a, b = g['rhand']['rel']
    for f in range(a, b + 1):
        rp[f] = dict(rel=f)
        if f in g['rhand'].get('add', {}):
            rp[f]['gun_add'] = g['rhand']['add'][f]
    bo = g.get('bolt')
    if bo:
        lo, hi = g['offhand']
        tik = V.GUNTIK[g['gun']]
        Kn, kft = anahip.knob_traj(tik, bo['anim']); Ch, cft = boltgrip.chamber_traj(tik, bo['anim'])
        gi = lambda f, ft_, L: min(L - 1, int(round(f * hip.frameTime / ft_)))
        gr = bo['gref']
        Wg = R.evaluate(R.pose_dict(hip, gr))
        rel = Wg['Bip01 R Hand'] @ R.inv(Wg['tag_weapon_left' if lo <= gr <= hi else 'tag_weapon_right'])
        k = Kn[gi(gr, kft, len(Kn))] / R.S
        X = B.H(np.eye(3), -k) @ B.H(R.axis_angle_rows([1.0, 0, 0], bo['roll']) @ R.axis_angle_rows([0, 0, 1.0], bo['yaw']), np.zeros(3)) @ B.H(np.eye(3), k)
        rel_bolt = rel @ X @ R.inv(Ch[gi(gr, cft, len(Ch))])
        for a, b in bo['spans']:
            for f in range(a, b + 1):
                rp[f] = dict(relT=rel_bolt @ Ch[gi(f, cft, len(Ch))], fing=gr)
    return rp


def bake(name, root, sc=4.0, sets=()):
    g = copy.deepcopy(GUNS[name])
    for kv in sets:
        k, v = kv.split('=')
        h, d = k.split('.')
        g['holds'][h][d] = float(v)
    hip = R.load(R.ANIM + g['hip'])
    n, ft = hip.numFrames, hip.frameTime
    r, ev = phys(g, n, ft, sc)
    rc = dict(gun=g['gun'], hip=g['hip'], charge=g['charge'], offhand=g['offhand'], enter=g['enter'], exit=g['exit'],
              slide={}, weight=dict(on=False), handover=False, dip=r['dip'], dip_pivot=PIVOT,
              free_tag=False)      # no ammo prop on a hand tag (the charger is part of the gun mesh): both tags stay on the gun
    if g.get('rhand'):
        rc['right_path'] = right_path(g, hip)
    rc.update(g.get('rc', {}))
    H.RECIPES['_r_' + name] = rc
    sk, _ = H.bake('_r_' + name, CTL)
    pu = g.get('prop_until')
    if pu:
        # the server attaches an ammo prop to the hand tag the gun is NOT on (kar98_clip_reload.tik on tag_weapon_right,
        # torso frames 0-50): up to there that tag keeps the hip art's value (the prop rides the hand); afterwards BOTH
        # tags are on the gun, so the hand-over back to the main hand at the end of the reload lands on the gun
        # whichever frame it arrives (run ra2: the gun swung out for 0.2 s after the clip)
        H.RECIPES['_r2_' + name] = dict(rc, free_tag=True)
        sk2, _ = H.bake('_r2_' + name, CTL)
        cm = R.chanmap(sk)
        other = 'tag_weapon_right' if g['offhand'][0] >= 0 else 'tag_weapon_left'
        for ch in (other + ' rot', other + ' pos'):
            for f in range(g.get('prop_from', 1), pu + 1):
                sk.V[f, cm[ch]] = sk2.V[f, cm[ch]]
        sk.values = [[[float(np.float32(x)) for x in sk.V[f, c]] for c in range(sk.numChannels)] for f in range(n)]
    bts = R.skc_io.write(sk)
    dst = os.path.join(root, 'models', 'human', 'animation', g['out'].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bts)
    print(name, '->', g['out'], n, 'frames x %.4f s' % ft, hashlib.md5(bts).hexdigest()[:8])
    print('   ', r['report'])
    json.dump(dict(gun=name, holds=g['holds'], pose=g['pose'], scale=sc, events=[list(e) for e in ev], cls=BP.RIFLE,
                   report=r['report'], md5=hashlib.md5(bts).hexdigest()), open(dst[:-4] + '_phys.json', 'w'), indent=1)
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--root', default='.'); ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--scale', type=float, default=4.0)
    a = ap.parse_args()
    for nm in a.gun.split(','):
        bake(nm, a.root, a.scale, a.set)

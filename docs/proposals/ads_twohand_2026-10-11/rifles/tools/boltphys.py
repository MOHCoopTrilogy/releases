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
sys.path.insert(0, T); sys.path.insert(0, SHARED)
_c = os.getcwd(); os.chdir(T)
import key_bolt as K
os.chdir(_c)
import gunphys
R = K.R
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))

# a bolt rifle in the shoulder: heavier and slower-settling than the pistols (4.6 Hz) and the shared 'rifle' class's
# two-handed hold; "support" here is the FIRING hand (1 = on the grip, 0 = off it: butt in the shoulder + the left
# hand on the fore-end alone - the rifle rolls a little toward the missing hand and the butt settles)
RIFLE = dict(m=4.1, f2=2.6, f1=2.0, z=0.62, sag=(0.10, 1.1, 0.35, -0.05, -0.06), magw=0.0,
             tr=(0.012, 0.10, 0.07, 0.010, 0.004), tr2=0.5)
# impulses for mass 1 (drop u/s, roll deg/s, pitch deg/s, side u/s, back u/s), length in frames.
# roll + = top to the RIGHT (toward the working hand), pitch + = muzzle down, back + = into the shoulder
gunphys.ACTIONS.update({
    'rb_up':    ((-1.5, -26.0, -5.0, -0.8, 0.0), 2.5),    # knob lifted on the right: that side is pushed up
    'rb_back':  ((0.6, 30.0, -16.0, -1.5, 9.0), 2.5),     # dragged rearward, high and right of the bore: into the shoulder, muzzle up and round to the hand
    'rb_stop':  ((0.0, 6.0, -7.0, 0.0, 5.0), 1.5),        # the bolt hits its stop
    'rb_fwd':   ((0.5, -12.0, 15.0, 0.8, -11.0), 2.5),    # shoved forward: the rifle goes forward, muzzle dips
    'rb_down':  ((3.0, 14.0, 9.0, 1.0, -2.0), 2.0),       # knob slapped down: the right side is pushed down, into battery
    'rb_grip':  ((0.6, 5.0, 2.0, 0.4, 1.0), 3.0),         # the firing hand lands on the grip again
})

GUNS = {
    # frames are the view clip's; up / back / fwd / down = (first, last) frame of that stroke in the gun's own clip
    'kar98': dict(recipe='kar98_rechamber', out='viewmodel/rifle/kar98_rechamber_ads.skc',
                  sight='kar98', aim='viewmodel/kar_stand00.skc', anim='rechamber',
                  off=(2, 7), up=(8, 10), back=(13, 15), fwd=(23, 24), down=(27, 29), on=(36, 42),
                  hold=(0, 7, 26, 40)),       # the hold pose eases in over 0-7 (the spring reaches it about frame 10), out over 26-40
    # Springfield M1903 (56 x 1/30 s): lift 8-10, back 15-17, forward 27-28, down 30-32, hand on the knob 8-31
    'springfield': dict(recipe='springfield_rechamber', out='viewmodel/rifle/springfield_rechamber_ads.skc',
                        sight='springfield_unscoped', aim='viewmodel/sprng_stand00.skc', anim='rechamber',
                        off=(2, 7), up=(8, 10), back=(15, 17), fwd=(27, 28), down=(30, 32), on=(38, 44), hold=(0, 6, 30, 43)),
    # Mosin-Nagant (45 x 1/30 s): lift 7-12, back 12-15, forward + down 26-27
    'mosin': dict(recipe='mosin_rechamber', out='viewmodel/mosin_nagant/mosin_rechamber_ads.skc',
                  sight='mosin_nagant_rifle', aim='viewmodel/kar_stand00.skc', anim='rechamber',
                  off=(1, 6), up=(7, 12), back=(12, 15), fwd=(26, 26), down=(27, 27), on=(34, 40), hold=(0, 5, 27, 39)),
    # Lee-Enfield (45 x 1/30 s): lift 7-12, back 12-15, forward + down 24-27; the rear sight sits on the receiver
    # bridge just ahead of the eye, so the rifle is eased further forward than the Kar98
    'enfield': dict(recipe='enfield_rechamber', out='viewmodel/enfield/enfield_rechamber_ads.skc',
                    sight='lee_enfield', aim='viewmodel/kar_stand00.skc', anim='rechamber',
                    off=(1, 6), up=(7, 12), back=(12, 15), fwd=(24, 25), down=(26, 27), on=(34, 40), hold=(0, 5, 27, 39),
                    hold_set=dict(back=-3.3)),
}
# the hold while the bolt is worked: (drop u, roll deg, pitch deg, side u, back u) - off the cheek along the sight line
HOLD = dict(drop=1.2, roll=3.0, pitch=2.3, side=0.0, back=-3.0)
SC = dict(k=1.0)


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


def bake(name, root, hold=HOLD, sc=1.0, show=False):
    g = GUNS[name]
    hold = dict(hold, **g.get('hold_set', {}))
    rc = copy.deepcopy(K.RECIPES[g['recipe']])
    hip = R.load(R.ANIM + rc['hip'])
    n, ft = hip.numFrames, hip.frameTime
    r, ev = phys(g, n, ft, hold, sc)
    X = r['X']
    # gunphys (drop, roll, pitch, side, back) -> key_bolt (dip, cant, yaw, fwd, left, up); cant + = top to the LEFT
    rc['keys'] = {f: (float(X[f, 2]), float(-X[f, 1]), 0.0, float(-X[f, 4]), float(X[f, 3]), float(-X[f, 0])) for f in range(n)}
    for k, v in g.get('rc', {}).items():
        rc[k] = v
    K.RECIPES['_phys_' + name] = rc
    sk, rep = K.key('_phys_' + name, CTL)
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
    json.dump(dict(gun=name, hold=hold, scale=sc, events=[list(e) for e in ev], cls=RIFLE, report=r['report'],
                   md5=hashlib.md5(bts).hexdigest()), open(dst[:-4] + '_phys.json', 'w'), indent=1)
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--root', default='.'); ap.add_argument('--set', action='append', default=[])
    ap.add_argument('--scale', type=float, default=4.0); ap.add_argument('--print', action='store_true')
    a = ap.parse_args()
    hold = dict(HOLD)
    for kv in a.set:
        k, v = kv.split('=')
        if k == 'hold':
            for nm in a.gun.split(','):
                GUNS[nm]['hold'] = tuple(int(x) for x in v.split(','))
        else:
            hold[k] = float(v)
    for nm in a.gun.split(','):
        bake(nm, a.root, hold, a.scale, a.print)

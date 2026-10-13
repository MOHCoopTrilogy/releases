r"""Pump shotgun: the PUMP STROKE after every AIMED shot (user 2026-10-13, deployed build: "noticed the shotgun doesnt
have the pumping action when in ads"). A FOLLOW-UP to the frozen shotgun files - new files only (SHOTGUN_PUMP_FIX.md).

Cause: while the aim is held the server keeps the hands at `charge` (the aim pose) through every shot, so the hands row
`shotgun_fire` - the retail clip with the pump stroke in it - never plays; the gun's own `fire` row (shotgun_fire.skc,
32 frames) still runs the forend back (frames 10-11, 5.38 u) and forward (frames 20-21) under a hand that stays put.
Fix: the cgame's client-only aimed cycle (apply_cyclewpn.py: row `coopr_shotgun_cycle_ads`, started when the clip
ammo drops while the aim pose is up) plays this clip:

    viewmodel/shotgun/coop_shotgun_cycle_ads.skc   32 frames at 30 / s = the gun's `fire` row, frame for frame
        the firing hand and the sights stay where the aim has them; the support hand keeps ITS AIM GRIP on the forend
        and works it: BACK over clip frames 3-5 (0.10-0.17 s: at the rear as the hull leaves - see main()), held, and
        FORWARD with the forend's own travel in shotgun_fire.skc at frames 20-21 (measured on the mesh); weight by
        gunphys class `shotgun` (the lane's `sg_pump_back` at frame 4, `sg_pump_fwd` at frame 20; at the cheek the gun
        does not ride above its aim)

    cd heavy/assets; python ../tools/sgpump.py [--root dir] [--strength 0.6]
"""
import sys, os, argparse, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
import sgbake as SB                      # library only: the lane's class `shotgun`, its pump actions, AIM, BUTT
H, R, V, CTL = SB.H, SB.R, SB.V, SB.CTL
gunphys = SB.gunphys
TIK = 'models/weapons/shotgun.tik'
SRC = 'viewmodel/shotgun/reload_end.skc'           # channel set / frame count / frame time (32 frames, as the gun's fire row)
OUT = 'viewmodel/shotgun/coop_shotgun_cycle_ads.skc'
N = 32


def forend():
    """the forend's travel along the bore (u, gun frame) at every frame of the gun's `fire` row, measured on the mesh"""
    RT = os.path.normpath(os.path.join(hv.LANE, '..', 'rifles', 'tools'))
    sys.path.insert(0, RT)
    import g43irons as G
    P0 = np.vstack([s['P'] for s in G.gungeo.load_gun(TIK, 'fire', 0)['surfs']])
    P1 = np.vstack([s['P'] for s in G.gungeo.load_gun(TIK, 'fire', 14)['surfs']])
    mv = np.linalg.norm(P1 - P0, axis=1) > 0.2
    assert mv.sum() > 8, mv.sum()
    return [(np.vstack([s['P'] for s in G.gungeo.load_gun(TIK, 'fire', f)['surfs']])[mv] - P0[mv]).mean(0) for f in range(N)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.'); ap.add_argument('--strength', type=float, default=0.6)
    ap.add_argument('--pull', default='3,5', help='clip frames of the back stroke: the hand leaves the front after the first, is at the rear from the second')
    a = ap.parse_args()
    a.pull = [int(x) for x in a.pull.split(',')]
    d = forend()
    back = [f for f in range(N) if d[f][0] < -0.1]
    print('forend: back %.2f u, frames %d-%d' % (-min(v[0] for v in d), back[0], back[-1]))
    # THE BACK STROKE IS EARLIER THAN THE FOREND'S (user 2026-10-13: "do you see the shell eject when you pump?"): the
    # gun's `fire` row throws the hull 0.2 s after the shot (tik: `entry commanddelay 0.2 tagspawn tag_eject`; in the
    # engine it is first in the picture 0.13-0.14 s after the client sees the shot, run hj49) but moves the forend
    # back only at 0.33-0.37 s - at the hip too the retail hull is out before the hand has started. The gun's row is
    # frozen and server-read, so the HAND is re-timed: back over clip frames PULL[0]..PULL[1] (at the rear as the hull
    # leaves), held there, forward WITH the forend at its own frames. From the eye the forend is hidden in this aim.
    full = min(v[0] for v in d)
    for f in range(N):
        if f < back[-1]:
            u = 0.0 if f <= a.pull[0] else 1.0 if f >= a.pull[1] else (f - a.pull[0]) / float(a.pull[1] - a.pull[0])
            d[f] = np.array([min(d[f][0], full * u), d[f][1], d[f][2]])
    ph = gunphys.simulate(N, 1 / 30.0, 'shotgun', [(0, 1.0), (N - 1, 1.0)], [(a.pull[0] + 1, 'sg_pump_back'), (back[-1], 'sg_pump_fwd')],
                          strength=a.strength, fade=6)
    X = ph['X'].copy()
    for j in (0, 2):                              # at the cheek the gun does not ride ABOVE its aim (the lane's rule)
        X[:, j] = np.where(X[:, j] < 0.0, X[:, j] * 0.15, X[:, j])
    dip = {f: tuple(float(v) for v in X[f]) for f in range(N)}
    lp = {f: dict(aim=1, gun_add=tuple(float(v) for v in d[f]), fing='pose') for f in range(N)}
    rc = H.auto_recipe('shotgun_reload_end', gun='shotgun', charge=SB.AIM, hip=SRC, fixed_right=True, enter=0, exit=0, wfade=(0, 0),
                       weight=dict(on=False), handover=False, left_path=lp, dip=dip, dip_after=True, dip_pivot=SB.BUTT,
                       elbow_vec={'L': SB.F3('SG_ELBV', '0,0.5,-1.0')})
    H.RECIPES['shotgun_reload_end'] = rc
    sk, _ = H.bake('shotgun_reload_end', CTL)
    assert sk.numFrames == N
    b = R.skc_io.write(sk)
    dst = os.path.join(a.root, 'models', 'human', 'animation', OUT.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(b)
    c = R.load(dst)
    xs = []
    for f in range(N):
        W = R.evaluate(R.pose_dict(c, f))
        xs.append(float(((W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']))[3, 0]) * R.S))
    print('%s %d frames %s | %s' % (OUT, N, hashlib.md5(b).hexdigest()[:8], ph['report']))
    print('support hand along the gun (u) per frame:', ' '.join('%.1f' % x for x in xs))
    print('gun off its aim, worst frame: drop %.2f u, pitch %.2f deg, roll %.2f deg, back %.2f u' % (
        np.abs(X[:, 0]).max(), np.abs(X[:, 2]).max(), np.abs(X[:, 1]).max(), np.abs(X[:, 4]).max()))


if __name__ == '__main__':
    main()

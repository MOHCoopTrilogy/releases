"""Weighty gun motion for aimed reloads (user 2026-10-12: "Should be weighty, weapon should move realistically based
on physics"): the gun in the hands is a mass on a damped spring (the wrists / the shoulder), driven by what is done to
it on the clip's timeline. Nothing is keyed by hand: the motion is the response to

  * IMPULSES  - a push on the magazine, the slide slamming forward, a bolt pulled back ... each a short force pulse
                (half-sine over `dur` frames, never instantaneous) in a direction that follows from where the force
                acts on the gun
  * LOADS     - the support hand leaving (the muzzle sags under the gun's weight, the hold gets softer), the magazine's
                weight leaving and coming back
  * TREMOR    - a held gun is never still: a slow three-sine wander, larger one-handed

Five degrees of freedom, the ones hold_bake's `dip` track takes, in the CAMERA frame about a pivot down the sight line:
    drop (u, + = down)   roll (deg, + = top to the right)   pitch (deg, + = muzzle down)
    side (u, + = left)   back (u, + = toward the eye)
Each is x'' = -2 z w x' - w^2 (x - x_eq) + a(t), w and x_eq following the support weight s(t) (1 = both hands / in
the shoulder, 0 = the firing hand alone).

Per weapon CLASS: mass (divides every impulse), hold frequency two-handed / one-handed (Hz), damping ratio, the
one-handed sag, the magazine's share of the weight, tremor size. Per ACTION: the impulse direction for mass 1.

    import gunphys
    r = gunphys.simulate(n_frames, frame_time, 'pistol', support=[(0, 1), (4, 1), (10, 0), ...],
                         mag=[(0, 1), (13, 1), (17, 0), (35, 0), (37, 1)], events=[(36, 'mag_seat'), (56, 'slide_fwd')])
    r['dip']        {frame: (drop, roll, pitch, side, back)}  -> recipe['dip']
    r['peak_deg']   largest sight-line deviation, r['settle_s'] time from the last impulse to rest, r['report'] text
"""
import math
import numpy as np

DOF = ('drop', 'roll', 'pitch', 'side', 'back')
CLASSES = {
    #           mass  f2 Hz  f1 Hz  damping  one-handed sag (drop, roll, pitch, side, back)   magazine share  tremor (one-handed amplitude)
    'pistol': dict(m=1.0, f2=4.6, f1=3.1, z=0.42, sag=(0.16, -1.4, 0.9, 0.05, 0.0), magw=0.22, tr=(0.020, 0.22, 0.16, 0.020, 0.008), tr2=0.30),
    'smg':    dict(m=3.6, f2=3.0, f1=2.1, z=0.50, sag=(0.38, -1.0, 1.9, 0.08, 0.0), magw=0.16, tr=(0.030, 0.20, 0.20, 0.025, 0.010), tr2=0.25),
    'rifle':  dict(m=4.2, f2=2.8, f1=1.9, z=0.52, sag=(0.45, -0.8, 2.2, 0.08, 0.0), magw=0.06, tr=(0.030, 0.18, 0.20, 0.025, 0.010), tr2=0.25),
    'lmg':    dict(m=8.5, f2=1.9, f1=1.3, z=0.58, sag=(0.70, -0.6, 3.0, 0.10, 0.0), magw=0.12, tr=(0.035, 0.14, 0.18, 0.025, 0.010), tr2=0.25),
}
# impulse per action for mass 1: velocity change (u/s, deg/s) in (drop, roll, pitch, side, back), and its length in frames
ACTIONS = {
    'mag_release': ((0.0, -7.0, 2.0, 0.5, 0.0), 2.0),      # the thumb on the button: a small twist
    'mag_out':     ((-2.5, 0.0, -7.0, 0.0, 0.0), 3.0),     # the magazine slides out: the gun lifts as its weight leaves
    'mag_seat':    ((-12.0, 0.0, 40.0, 0.0, 0.5), 2.0),    # a push up on the butt, behind the centre of mass: up, muzzle tips down
    'slide_fwd':   ((2.0, 0.0, 62.0, 0.0, -12.0), 1.5),    # the slide's mass stops forward: the gun is thrown forward, muzzle dips
    'slide_back':  ((-1.0, 0.0, -30.0, 0.0, 10.0), 2.0),
    'thumb_press': ((1.2, 6.0, 5.0, -0.5, 0.0), 2.0),      # a lever pushed down on the left side
    'hand_on':     ((-3.0, 4.0, -9.0, -1.0, 1.2), 3.0),    # the support hand lands from the left and below
    'bolt_up':     ((-2.0, 14.0, -6.0, -0.6, 0.0), 2.0),   # right-hand bolt lifted: the rifle rolls toward the hand
    'bolt_back':   ((0.0, 6.0, -12.0, -0.5, 14.0), 2.0),   # pulled rearward into the shoulder
    'bolt_fwd':    ((0.0, -4.0, 10.0, 0.4, -14.0), 2.0),
    'bolt_down':   ((2.0, -14.0, 6.0, 0.5, 0.0), 2.0),
}


def _smooth(keys, f):
    keys = sorted(keys)
    if f <= keys[0][0]:
        return keys[0][1]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if f <= b:
            u = (f - a) / float(b - a) if b > a else 1.0
            u = u * u * (3 - 2 * u)
            return va + (vb - va) * u
    return keys[-1][1]


def _pose(pose, t):
    """keyed gun pose (frame, 5-vector), smooth between keys"""
    if not pose:
        return 0.0
    return np.array([_smooth([(k, v[j]) for k, v in pose], t) for j in range(5)])


def _run(n, ft, c, support, mag, events, strength, tremor, hand=1.0, sub=10, pose=None):
    m = c['m']
    sag = np.array(c['sag'], float) * strength
    tr = np.array(c['tr'], float) * (1.0 if tremor else 0.0)
    x = np.zeros(5); v = np.zeros(5)
    out = np.zeros((n, 5))
    dt = ft / sub
    ph = np.array([0.0, 1.7, 3.1, 4.4, 5.2])
    for f in range(n):
        out[f] = x
        for k in range(sub):
            t = (f + k / float(sub))
            s = _smooth(support, t)
            w = 2 * math.pi * (c['f1'] + (c['f2'] - c['f1']) * s)
            load = 1.0 - c['magw'] * (1.0 - (_smooth(mag, t) if mag else 1.0))
            ts = t * ft
            wob = (np.sin(2 * math.pi * 0.83 * ts + ph) +0.6 * np.sin(2 * math.pi * 1.71 * ts + 2.3 * ph) + 0.35 * np.sin(2 * math.pi * 2.63 * ts + 0.7 * ph)) / 1.95 \
                if tremor else 0.0
            ramp = min(1.0, t / 4.0)                                  # nothing moves before the reload starts
            xeq = sag * (1.0 - s) * load + tr * wob * (c['tr2'] + (1.0 - c['tr2']) * (1.0 - s)) * ramp + _pose(pose, t)
            a = -2 * c['z'] * w * v - w * w * (x - xeq)
            for ev in events:
                f0, kind = ev[0], ev[1]
                sc = (ev[2] if len(ev) > 2 else 1.0) * strength
                vec, dur = ACTIONS[kind]
                if f0 <= t < f0 + dur:
                    u = (t - f0) / dur
                    pulse = math.pi / 2 * math.sin(math.pi * u) / (dur * ft)          # integrates to 1 over the pulse
                    vv = np.array(vec, float); vv[1] *= hand; vv[3] *= hand
                    a = a + vv * sc / m * pulse
            v = v + a * dt
            x = x + v * dt
    return out


def simulate(n, ft, cls, support, events, mag=None, strength=1.0, fade=6, hand=1.0, pose=None):
    """n frames of frame time ft; returns dict(dip, peak_deg, settle_s, residual, report)"""
    c = CLASSES[cls] if isinstance(cls, str) else cls
    # pose: where the shooter HOLDS the gun over time (e.g. brought down for a rack) - the spring follows it
    X = _run(n, ft, c, support, mag, events, strength, True, hand, pose=pose)
    X0 = _run(n, ft, c, support, mag, events, strength, False, hand, pose=pose)
    res = X[n - 1].copy()
    for f in range(n):                                                # the exact aim on the first and the last frame
        u = min(1.0, (n - 1 - f) / float(fade))
        X[f] *= u * u * (3 - 2 * u)
    X[0] = 0.0
    last = max(e[0] for e in events) if events else 0
    settle = 0.0
    for f in range(n - 1, int(last), -1):
        if abs(X0[f][1]) > 0.15 or abs(X0[f][2]) > 0.15 or max(abs(X0[f][0]), abs(X0[f][3]), abs(X0[f][4])) > 0.03:
            settle = (f + 1 - last) * ft
            break
    peak = float(np.abs(X[:, 2]).max())
    fp = int(np.abs(X[:, 2]).argmax())
    rep = ('class %s x%.2f: peak pitch %.2f deg at f%d, roll %.2f deg, drop %.2f u, back %.2f u; settles %.2f s after the last action; '
           'left at the last frame before the fade: pitch %.2f deg' % (cls if isinstance(cls, str) else 'custom', strength, peak, fp,
                                                                      float(np.abs(X[:, 1]).max()), float(np.abs(X[:, 0]).max()),
                                                                      float(np.abs(X[:, 4]).max()), settle, res[2]))
    return dict(dip={f: tuple(float(v) for v in X[f]) for f in range(n)}, peak_deg=peak, settle_s=settle, residual=res, report=rep, X=X)


if __name__ == '__main__':
    r = simulate(73, 1 / 30.0, 'pistol', support=[(0, 1), (3, 1), (9, 0), (40, 0), (50, 1)], mag=[(0, 1), (12, 1), (17, 0), (34, 0), (37, 1)],
                 events=[(9, 'mag_release'), (13, 'mag_out'), (35, 'mag_seat'), (47, 'hand_on'), (50, 'thumb_press'), (55, 'slide_fwd')])
    print(r['report'])
    for f in range(0, 73, 3):
        print(f, ' '.join('%6.2f' % v for v in r['dip'][f]))

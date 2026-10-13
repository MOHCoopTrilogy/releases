"""Iron-sight G43: its reloads - the gun's own clips (the bolt carrier really runs) and the AIMED hands clips.

The retail first-person clip (viewmodel/g43/g43_reload.skc, 88 frames = 2.93 s; the torso clip of the same length ends
the reload, run rb30): the right hand never leaves the grip; the LEFT hand takes the magazine out below (frame 10-18,
the tik hides the magazine surface 16-50), brings the new one (50-56), swings down and strikes the magazine's foot
with the palm (64-66: the rifle jumps), then goes back to the fore-end (74-82). Nobody touches the cocking handle, the
retail gun has no bolt bone and its own `reload` clip is only 56 frames.

GUN (mesh coop_g43_irons.skd: g43irons.py puts the carrier + handle on the bone `coop_bolt`), 88-frame clips:
    coop_g43_irons_reload.skc             tik row `reload` (hip, and aimed with rounds left): the retail clip held to 88 frames
    coop_g43_irons_reload_ads_empty.skc   `reload_ads_empty` (shown by the cgame: aimed, emptied): the carrier is racked
HANDS (riflereload.py: hold_bake + gunphys holds), rows in rows_rifle.py:
    coopr_g_43_irons_reload_ads        rounds left: the retail technique (magazine out, in, struck home), back to the aim
    coopr_g_43_irons_reload_empty_ads  emptied: magazine out and in, then the left hand racks the handle; back to the aim
The rifle is worked just under the centre box (holds `down` / `low` / `reach`), canted so the handle's side turns to
the eye, and returns to the exact aim. The magazine itself is under the rifle and below the picture, as at the SMGs.
NOT made: a hip clip with the rack (the hip rows coopr_g_43_irons_reload / _reload_empty are the retail clip).

    cd rifles/assets; python ../tools/g43reload.py [gun] [hands] [--set low.drop=3 ...]
"""
import sys, os, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged
SHARED = os.path.normpath(os.path.join(HERE, '..', '..', 'tools'))
sys.path.insert(0, SHARED)

N = 88
TRAVEL = 4.2                     # u the carrier runs back (it is 4.8 u long; the receiver cover behind it is 8 u)
RACK = {62: 0.0, 63: 0.12, 64: 0.55, 65: 0.92, 66: 1.0, 67: 1.0, 68: 0.30, 69: 0.0}     # carrier travel 0..1 by frame
GDIR = 'models/weapons/g43'
VDIR = 'viewmodel/g43'
HANDLE = (7.65, -2.05, -4.75)    # the cocking handle's knob in the gun frame (g43parts.py: x 7.4..7.9, y -2.4..-1.5, z -5.2..-4.3)


def rack(f, on=True):
    if not on:
        return 0.0
    ks = sorted(RACK)
    if f <= ks[0] or f >= ks[-1]:
        return 0.0
    return float(np.interp(f, ks, [RACK[k] for k in ks]))


def gun_clips(root):
    import bonefit as BF
    import gunskc
    staged.off()
    A, o = BF.fit('models/weapons/g43.tik', 'G43')
    raw = staged.vfs.read(GDIR + '/g43_reload.skc')
    staged.on()
    import struct
    if struct.unpack_from('<i', raw, 4)[0] == 14:
        raw = gunskc.skc14to13.convert(raw)
    a = gunskc.R.skc_io.read(raw)
    n0 = len(a.values)
    out = {}
    for fn, on in (('coop_g43_irons_reload.skc', False), ('coop_g43_irons_reload_ads_empty.skc', True)):
        keyed = {nm: [list(a.values[min(f, n0 - 1)][c]) for f in range(N)] for c, nm in enumerate(a.names)}
        bp, bq = [], []
        for f in range(N):
            p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (-TRAVEL * rack(f, on), 0.0, 0.0))
            bp.append(p); bq.append(q)
        keyed['coop_bolt pos'] = bp; keyed['coop_bolt rot'] = bq
        dst = os.path.join(root, (GDIR + '/' + fn).replace('/', os.sep))
        gunskc.write(dst, raw, N, keyed, frame_time=a.frameTime)
        out[fn] = hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8]
        print('gun clip %s: %d frames x %.4f s (retail %d), carrier %s  %s' % (fn, N, a.frameTime, n0, 'racked %d-%d, %.1f u' % (min(RACK), max(RACK), TRAVEL) if on else 'still', out[fn]))
    return out


HOLDS = dict(
    # straight down / straight up, aligned: the way out of and back into the aim (the Kar98's lesson, run rb21)
    down=dict(drop=1.9, roll=0.0, pitch=0.6, side=0.0, back=-0.6),
    # the work pose: under the centre box, top turned to the right - the magazine well swings to the left hand and the
    # handle's side of the receiver turns up to the eye
    low=dict(drop=2.7, roll=12.0, pitch=1.0, side=0.5, back=-1.2),
    # the left hand is away with the magazine: the rifle hangs on the firing hand and the shoulder, muzzle heavy
    reach=dict(drop=3.1, roll=9.0, pitch=2.6, side=0.2, back=-1.0))


def rack_grip(f):
    """the left hand WRAPPED on the cocking handle: the rifle's own hip grip of the fore-end (viewmodel/g43/g43_idle.skc:
    the palm under the wood, fingers wrapped up its far side) turned ROLL deg about the rifle's long axis - the palm
    comes round to the rifle's left side, the fingers hook over the handle from above - and moved from the fore-end's
    axis (FORE) onto the knob, which it then follows back and home."""
    import g43pose
    R = g43pose.R
    hc = R.load(R.ANIM + VDIR + '/g43_idle.skc')
    Wi = R.evaluate(R.pose_dict(hc, 0))
    rel = Wi['Bip01 L Hand'] @ R.inv(Wi['tag_weapon_right'])
    Tm = np.eye(4); Tm[3, 0:3] = -np.asarray(FORE, float) / R.S
    Rm = np.eye(4); Rm[0:3, 0:3] = R.axis_angle_rows((0, 0, 1), YAW) @ R.axis_angle_rows((1, 0, 0), ROLL)
    knob = np.array([HANDLE[0] - TRAVEL * rack(f) + KOFF[0], HANDLE[1] + KOFF[1], HANDLE[2] + KOFF[2]])
    Tp = np.eye(4); Tp[3, 0:3] = knob / R.S
    return rel @ Tm @ Rm @ Tp


def _lp(empty):
    """the LEFT hand, keyed: the aim grip, then the retail hand-to-gun relation frame by frame (its own contact with the
    magazine). Rounds left: the whole retail clip (seat 50-56, the palm struck up under the magazine 64-66, back to the
    fore-end 74-82). Emptied: after the seat the hand comes up the rifle's LEFT side (a waypoint clear of the wood),
    wraps the cocking handle (rack_grip), hauls it back with the carrier and lets it fly; then the retail way back
    to the fore-end."""
    lp = {0: dict(aim=1), 2: dict(aim=1)}
    for f in range(8, (56 if empty else 82) + 1, 2):
        lp[f] = dict(rel=f)
    if empty:
        lp[59] = dict(relT=rack_grip(59), gun_add=(1.0, -2.6, 3.2), fing='pose')        # left of the wood, on the way up
        for f in range(62, 68):
            lp[f] = dict(relT=rack_grip(f), fing='pose')
        lp[70] = dict(relT=rack_grip(70), gun_add=(1.5, -2.2, 2.0), fing='pose')        # let go: off to the left and down
        for f in range(74, 83, 2):
            lp[f] = dict(rel=f)
    lp[85] = dict(aim=1); lp[87] = dict(aim=1)
    return lp


CURL = 1.4
THUMB = (0.0, 30.0, 30.0)


def _curl(keys):
    import g43pose
    d = g43pose.RB.curl(keys)
    for ch, deg in (('Bip01 L Finger0 rot', THUMB[0]), ('Bip01 L Finger01 rot', THUMB[1]), ('Bip01 L Finger02 rot', THUMB[2])):     # the thumb laid down on the receiver, not standing up into the picture
        d[ch] = [(k, w * deg / max(CURL, 1e-6)) for k, w in keys]
    return d


YAW = 0.0
FORE = (17.0, -0.9, -1.2)       # gun frame u: the fore-end's axis where the hip grip holds it
KOFF = (-1.0, -0.2, 1.6)          # where in the wrapped hand the knob sits (gun frame u, added to the knob)
ROLL = 62.0


def entries():
    base = dict(gun='g43_irons', hip=VDIR + '/g43_reload.skc', charge=VDIR + '/coop_g43_irons_aim.skc', offhand=(-1, -1),
                enter=6, exit=8, holds=HOLDS,
                # the server hangs the magazine prop on tag_weapon_left for the reload: that tag keeps the hip art's place in
                # the LEFT HAND (run rb31: with both tags on the gun the spare magazine stuck out of the receiver's right side)
                prop_from=0, prop_until=N - 1)
    loaded = dict(base, out=VDIR + '/coop_g43_irons_reload_ads.skc',
                  pose=[(0, None), (5, 'down'), (10, 'low'), (18, 'low'), (24, 'reach'), (44, 'reach'), (49, 'low'), (70, 'low'),
                        (76, 'down'), (83, None), (87, None)],
                  support=[(0, 1), (3, 1), (8, 0), (76, 0), (81, 1)],
                  events=[(11, 'rb_grip', 0.5), (17, 'mag_out_r', 1.5), (20, 'hand_off'), (50, 'mag_in_r', 1.2), (57, 'hand_off', 0.6),
                          (64, 'mag_in_r', 1.6), (67, 'hand_off', 0.6), (80, 'rb_grip')],
                  rc=dict(fixed_right=True, left_path=_lp(False)))
    empty = dict(base, out=VDIR + '/coop_g43_irons_reload_empty_ads.skc',
                 pose=[(0, None), (5, 'down'), (10, 'low'), (18, 'low'), (24, 'reach'), (44, 'reach'), (49, 'low'), (72, 'low'),
                       (77, 'down'), (84, None), (87, None)],
                 support=[(0, 1), (3, 1), (8, 0), (78, 0), (83, 1)],
                 events=[(11, 'rb_grip', 0.5), (17, 'mag_out_r', 1.5), (20, 'hand_off'), (50, 'mag_in_r', 1.5), (57, 'hand_off', 0.6),
                         (64, 'rb_back', 1.3), (66, 'rb_stop'), (68, 'rb_fwd', 1.4), (70, 'hand_off', 0.6), (82, 'rb_grip')],
                 # the hand CLOSES on the thin handle (the fore-end's wide curl would leave the fingers standing open)
                 rc=dict(fixed_right=True, left_path=_lp(True), finger_add=_curl([(56, 0.0), (59, CURL), (69, CURL), (73, 0.0)])))
    return {'g43i': loaded, 'g43i_e': empty}


def hands(root, sets=(), which=('g43i', 'g43i_e'), scale=2.5):
    import g43pose
    g43pose.register()
    import riflereload as RR
    RR.GUNS.update(entries())
    return [RR.bake(k, root, scale, sets) for k in which]


if __name__ == '__main__':
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    sets = [sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == '--set']
    args = [x for x in args if x not in sets]
    if '--curl' in sys.argv:
        CURL = float(sys.argv[sys.argv.index('--curl') + 1])
        args = [x for x in args if x != sys.argv[sys.argv.index('--curl') + 1]]
    if '--thumb' in sys.argv:
        THUMB = tuple(float(x) for x in sys.argv[sys.argv.index('--thumb') + 1].split(','))
        args = [x for x in args if x != sys.argv[sys.argv.index('--thumb') + 1]]
    if '--yaw' in sys.argv:
        YAW = float(sys.argv[sys.argv.index('--yaw') + 1])
        args = [x for x in args if x != sys.argv[sys.argv.index('--yaw') + 1]]
    if '--koff' in sys.argv:
        KOFF = tuple(float(x) for x in sys.argv[sys.argv.index('--koff') + 1].split(','))
        args = [x for x in args if x != sys.argv[sys.argv.index('--koff') + 1]]
    if '--roll' in sys.argv:
        ROLL = float(sys.argv[sys.argv.index('--roll') + 1])
        args = [x for x in args if x != sys.argv[sys.argv.index('--roll') + 1]]
    do = args or ['gun', 'hands']
    if 'gun' in do:
        gun_clips('.')
    if 'hands' in do or 'loaded' in do or 'empty' in do:
        hands('.', sets, ('g43i', 'g43i_e') if 'hands' in do else tuple({'loaded': 'g43i', 'empty': 'g43i_e'}[x] for x in do if x in ('loaded', 'empty')))

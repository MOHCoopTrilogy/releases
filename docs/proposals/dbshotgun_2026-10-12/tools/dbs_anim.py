"""The gun's OWN animations (weapon tik clips): the action really works on the model.

    python tools/dbs_anim.py        -> assets/models/weapons/coop_dbshotgun/coop_dbs_<clip>.skc   (30 frames a second)

A hammerless side-by-side with a top lever and selective ejectors (as on a boxlock ejector gun): thumb the lever to
the right, the barrels drop on the hinge pin, the FIRED cases are thrown out as it opens (a live shell only rises with
its extractor and stays), one shell goes into each empty chamber by hand, the gun is swung shut and the lever snaps
back. Front trigger = right barrel, rear trigger = left barrel.

    idle                 closed, both chambers filled (a fired case looks the same from behind)
    fire                 front trigger (right barrel)          - the server plays `fire` while a round is left after it
    fire_empty           rear trigger (left barrel)            - and `fire_empty` for the last round (weapon.cpp:3631)
    reload               lever, barrels drop, RIGHT case ejected (one barrel fired; the left chamber keeps its shell)
    reload_empty         the same with BOTH cases ejected       - cgame swaps it in for `reload` when the clip is empty
    reload_single        a shell into the RIGHT chamber
    reload_single_first  a shell into the LEFT chamber          - cgame swaps it in for `reload_single` on an empty clip
    reload_end           swung shut, lever back
Lengths = the pump gun's first-person rows (reload_start 23, reload_fill 20, reload_end 32 frames): the server's
reload timing comes from the shared third-person shotgun states, so the clips must fit those.

Every part is keyed in GUN space (skd units, +x muzzle, +y right, +z down) and converted to the bone's parent-local
channels here. A shell that is "not there" is parked inside the stock's wood (PARK; a bone cannot be hidden).
"""
import os, sys, json, math
import numpy as np
import dbslib as L
import dbs_skx as X

FT = 1.0 / 30.0
OPEN = 34.0          # deg the barrels drop
LEVER = 24.0         # deg the top lever turns to the right
TRIG = 15.0          # deg a trigger turns
MDIR = os.path.join(L.ASSETS, 'models', 'weapons', 'coop_dbshotgun')
M = json.load(open(os.path.join(L.BUILD, 'model.json')))
BONES = [tuple(b) for b in M['bones']]
W0 = {k: np.array(v) for k, v in M['Wraw'].items()}
PAR = dict(BONES)
K = 13.25
# inside the receiver block, both at the same place (source frame, BU; the only enclosed place a shell fits - searched
# with park_check over the stock and receiver; the grip's wood did not pass)
PARK_BU = {'dbs_shell_r': (-1.3, 0.0, 0.05), 'dbs_shell_l': (-1.3, 0.0, 0.05)}


def to_raw(p):
    return np.asarray(p, float) * np.array([K, -K, -K]) + np.array([9.3, -1.05, -2.44]) / 0.52


def rot(axis, deg):
    """row-vector rotation matrix (p' = p @ R): right-handed turn of `deg` about `axis`"""
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    Kx = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return (np.eye(3) * c + s * Kx + (1 - c) * np.outer(a, a)).T


def quat(Rm):
    """the engine quaternion (x y z w) whose skdlib.quat_to_mat3 is Rm (checked both ways round)"""
    m = np.asarray(Rm, float)
    for mm in (m, m.T):
        t = np.trace(mm)
        if t > 0:
            s = math.sqrt(t + 1.0) * 2; q = [(mm[2, 1] - mm[1, 2]) / s, (mm[0, 2] - mm[2, 0]) / s, (mm[1, 0] - mm[0, 1]) / s, 0.25 * s]
        else:
            i = int(np.argmax(np.diag(mm))); j, k = (i + 1) % 3, (i + 2) % 3
            s = math.sqrt(1.0 + mm[i, i] - mm[j, j] - mm[k, k]) * 2
            q = [0, 0, 0, 0]
            q[i] = 0.25 * s; q[j] = (mm[j, i] + mm[i, j]) / s; q[k] = (mm[k, i] + mm[i, k]) / s; q[3] = (mm[k, j] - mm[j, k]) / s
        if np.allclose(np.array(L.skdlib.quat_to_mat3(q)), m, atol=1e-5):
            return tuple(q)
    raise AssertionError('quat')


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def key(keys, f):
    """piecewise: {frame: value}, smoothstep between keys"""
    ks = sorted(keys)
    if f <= ks[0]:
        return keys[ks[0]]
    for a, b in zip(ks[:-1], ks[1:]):
        if f <= b:
            return keys[a] + (keys[b] - keys[a]) * ease((f - a) / (b - a))
    return keys[ks[-1]]


PIN = W0['dbs_barrels']
# the action's timeline (frames at 30 a second) - dbs_hands.py keys the hands on the same numbers
# (run rl1: the rows play 0.75 s / 0.66 s / 1.17 s in the engine; with the barrels down by frame 13 the open gun
# stood still for 0.45 s - the lever and the drop are slower now and the eject is at frame 10)
EJECT_F = 10
THETA_OPEN = {0: 0.0, 5: 0.0, 11: OPEN * 1.04, 13: OPEN * 0.985, 15: OPEN}      # falls, checks on the stop
LEVER_OPEN = {0: 0.0, 2: 0.0, 5: LEVER, 23: LEVER}
SHUT_F = 12                                                                     # the frame the action latches
THETA_CLOSE = {0: OPEN, 7: OPEN, 10: OPEN * 0.5, 12: 0.0, 32: 0.0}
LEVER_CLOSE = {0: LEVER, 11: LEVER, 13: 0.0, 32: 0.0}
# the fired cases leave back, up and to the RIGHT of the gun (past the shooter's right side; never through the middle
# of the view): the emitter throws along the tag's x axis
EJECT_DIR = (-0.22, 0.86, -0.46)      # (run rm1: at -0.45 back the case passed 3 u from the eye and drew 100 px wide)


def frame_x(d):
    """rotation rows whose first row (the x axis) is the direction d"""
    x = np.asarray(d, float); x = x / np.linalg.norm(x)
    y = np.cross((0.0, 0.0, 1.0), x); y = y / np.linalg.norm(y)
    return np.array([x, y, np.cross(x, y)])


def barrels_R(theta):
    return rot((0, 1, 0), -theta)           # muzzle (+x) toward +z (down); sign checked in selftest


def chambered(bone, theta):
    Rb = barrels_R(theta)
    return Rb, (W0[bone] - PIN) @ Rb + PIN


def pose(theta=0.0, lever=0.0, tf=0.0, tr=0.0, shells=None):
    """-> {bone: (R world rows, t world)}; shells: {bone: 'in' | 'park' | (R, t)}"""
    shells = shells or {}
    P = {'origin': (np.eye(3), np.zeros(3))}
    Rb = barrels_R(theta)
    P['dbs_barrels'] = (Rb, PIN.copy())
    for b in ('tag_barrel', 'tag_dbs_r', 'tag_dbs_l'):
        P[b] = (Rb, (W0[b] - PIN) @ Rb + PIN)
    P['tag_eject'] = (frame_x(EJECT_DIR), W0['tag_eject'])
    P['dbs_lever'] = (rot((0, 0, 1), lever), W0['dbs_lever'])
    P['dbs_trig_f'] = (rot((0, 1, 0), tf), W0['dbs_trig_f'])
    P['dbs_trig_r'] = (rot((0, 1, 0), tr), W0['dbs_trig_r'])
    for b in ('dbs_shell_r', 'dbs_shell_l'):
        s = shells.get(b, 'in')
        if isinstance(s, str) and s == 'in':
            P[b] = chambered(b, theta)
        elif isinstance(s, str):
            P[b] = (np.eye(3), to_raw(PARK_BU[b]))
        else:
            P[b] = s
    return P


def channels(P):
    ch, vals = [], []
    for n, p in BONES:
        Rw, tw = P[n]
        if p in P:
            Rp, tp = P[p]
            Rl, tl = Rw @ Rp.T, (tw - tp) @ Rp.T
        else:
            Rl, tl = Rw, tw
        ch += [n + ' pos', n + ' rot']
        vals += [(*tl, 0.0), quat(Rl)]
    return ch, vals


def write(name, frames):
    ch = None; out = []
    for P in frames:
        ch, v = channels(P)
        out.append(v)
    # sign continuity of the quaternions
    for f in range(1, len(out)):
        for c in range(len(ch)):
            if ch[c].endswith(' rot') and np.dot(out[f][c], out[f - 1][c]) < 0:
                out[f][c] = tuple(-np.array(out[f][c]))
    # bounds: generous (open gun), radius likewise
    bmin = np.array(M['bmin']) - 12; bmax = np.array(M['bmax']) + 12
    data = X.build_skc(ch, out, FT, bmin, bmax, M['radius'] + 12)
    p = os.path.join(MDIR, 'coop_dbs_%s.skc' % name)
    open(p, 'wb').write(data)
    print('%-22s %2d frames %6d bytes' % (name, len(frames), len(data)))


def insert_path(bone, f, hand=None):
    """a shell on its way into its chamber (barrels open): -> (R, t) or 'park' / 'in'. The whole path is the loading
    hand's (build/hand_paths.json, written by dbs_hands.py: the shell rides the finger pinch, is let go of at the
    breech face and thumbed home); without that file: parked, then in from frame 15"""
    if hand is None:
        return 'park' if f < 15 else 'in'
    v = hand[f]
    return v if isinstance(v, str) else (np.array(v[0]), np.array(v[1]))


def clips():
    theta_open, lever_open = THETA_OPEN, LEVER_OPEN
    out = {}
    out['idle'] = [pose()]
    pull = [0.0, 0.7, 1.0, 1.0, 0.6, 0.3, 0.1, 0.0, 0.0, 0.0]
    out['fire'] = [pose(tf=TRIG * p) for p in pull]
    out['fire_empty'] = [pose(tr=TRIG * p) for p in pull]
    EJ = EJECT_F                                                                # the frame the ejectors trip
    for nm, gone in (('reload', ('dbs_shell_r',)), ('reload_empty', ('dbs_shell_r', 'dbs_shell_l'))):
        fr = []
        for f in range(23):
            sh = {b: ('park' if (b in gone and f >= EJ) else 'in') for b in ('dbs_shell_r', 'dbs_shell_l')}
            fr.append(pose(theta=key(theta_open, f), lever=key(lever_open, f), shells=sh))
        out[nm] = fr
    hp = os.path.join(L.BUILD, 'hand_paths.json')
    hand = json.load(open(hp)) if os.path.isfile(hp) else {}
    for nm, bone, other in (('reload_single', 'dbs_shell_r', 'in'), ('reload_single_first', 'dbs_shell_l', 'park')):
        fr = []
        h = hand.get(nm)
        h = {int(k): v for k, v in h.items()} if h else None
        ob = 'dbs_shell_l' if bone == 'dbs_shell_r' else 'dbs_shell_r'
        for f in range(20):
            fr.append(pose(theta=OPEN, lever=LEVER, shells={bone: insert_path(bone, f, hand=h), ob: other}))
        out[nm] = fr
    theta_close, lever_close = THETA_CLOSE, LEVER_CLOSE
    out['reload_end'] = [pose(theta=key(theta_close, f), lever=key(lever_close, f)) for f in range(32)]
    return out


def park_check():
    """the parked shells must be inside the stock's wood: every sample point of the shell has an odd number of body
    triangles above it (+z ray, source frame)"""
    P = json.load(open(os.path.join(L.BUILD, 'high_parts.json')))['parts']['body']
    T = np.array(P, float)[:, :, :3]
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    bad = 0
    for bone, o in PARK_BU.items():
        for dx in (0.0, 0.22, 0.445):
            for dy, dz in ((0, 0), (0.08, 0), (-0.08, 0), (0, 0.08), (0, -0.08)):
                p = np.array([o[0] + dx, o[1] + dy, o[2] + dz])
                v0, v1, v2 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2], p[:2] - a[:, :2]
                den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
                ok = np.abs(den) > 1e-12
                u = np.where(ok, (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / np.where(ok, den, 1), -1)
                v = np.where(ok, (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / np.where(ok, den, 1), -1)
                hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1)
                z = a[:, 2] + u * (b[:, 2] - a[:, 2]) + v * (c[:, 2] - a[:, 2])
                n = int((hit & (z > p[2])).sum())
                bad += (n % 2 == 0)
    return bad


def selftest():
    Rb, t = chambered('tag_barrel', 20.0)
    assert t[2] > W0['tag_barrel'][2] + 5, 'barrels must drop (muzzle toward +z)'
    Rl = rot((0, 0, 1), 10.0)
    assert quat(np.eye(3)) == (0.0, 0.0, 0.0, 1.0) or abs(quat(np.eye(3))[3]) == 1.0
    assert park_check() == 0, 'a parked shell pokes out of the stock: %d sample points' % park_check()


def main():
    selftest()
    os.makedirs(MDIR, exist_ok=True)
    for nm, fr in clips().items():
        write(nm, fr)


if __name__ == '__main__':
    main()

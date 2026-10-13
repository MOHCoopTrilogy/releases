"""A gun of a shared prefix HELD BY ITS SIDE MAGAZINE (user 2026-10-13: "was that gun not held by the mag?" / "it would
handle similarly to the sten") - the MP18: prefix mp40, whose hands hold a magazine housing UNDER the gun that this mesh
does not have (the support hand was under the fore-end, out of sight: the gun looked one-handed).

The hold is the STEN's own (retail hip idle sten_idle.skc: the left hand's place, rotation and fingers on the side
magazine), carried onto this gun's magazine neck: turned about the vertical by the neck's rake and moved from the
Sten's magazine axis to the neck. Nothing is invented but the place.

For every view row of the prefix that shows the support hand (idle, charge = the aim pose, fire, butt, raise, lower) a
per-weapon row coopr_<key>_<suffix> is staged (cgame ads-smg-next: the coopr_ rule for EVERY view animation, cvar
coop_vmPerWeaponRows) on a copy of that row's clip in which ONLY the left arm and its fingers are changed: the hand is
put in the hold's hand-to-gun relation in every frame (raise: blended in over its last part, lower: out over its
first), the arm re-solved. Trunk, eye, firing arm and weapon tag are the source clip's, so the sight picture and the
gun's motion cannot change (asserted).

    cd smg/assets;  python ../tools/sidehold.py mp40_mp18 . [--only idle,charge]      (IRONSIGHT_EXTRA_PAKS unset)
    env SH_OUT / SH_ROLL / SH_ADD / SH_YAW = trial values for `out` / `roll` / `add` / `yaw`
`hold_rel(key)` = the relation (rows, pre-scale) and the finger pose, for the reload bake (smgbake).
"""
import sys, os, json, math, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smgbake as SB
H = SB.H; R = SB.R; K = SB.K; B = SB.B


def _envf(name, default):
    v = os.environ.get(name)
    return tuple(float(x) for x in v.split(',')) if v else default


HOLDS = {
    # template: the Sten's hip idle. Its magazine: a straight box along y at x 12.4, z -3.6 (weapon-tag frame: x forward,
    # y right, z down). MP18 (root-frame mesh: its centre line is at y -2.5): housing stub to y -7.9, then the drum's
    # neck, raked back - centre line (11.2, -7.5, -3.45) -> (9.15, -10.5, -3.45) - and the drum body from y -11 on,
    # standing above the neck. The hand goes on the NECK between housing and drum, the drum against its heel.
    # se20 (user: the hand on the drum hid the drum - the back of the hand was toward the eye, the thumb on the far
    # side): the SAME template hand turned end for end along the neck (yaw 180) and rolled under it (roll 100) = an
    # underhand hold - palm up under the neck, the fingers up its far side and over its top toward the eye, the thumb
    # on the eye's side by the drum; the drum stands clear above and outboard of the hand (tools/holdtry.py shows it).
    'mp40_mp18': dict(prefix='mp40', vdir='viewmodel/mp40', template='viewmodel/sten/sten_idle.skc',
                      t_axis=((12.4, 0.0, -3.6), (0.0, -1.0, 0.0)),
                      neck=((11.2, -7.5, -3.45), (9.15, -10.5, -3.45)),
                      out=_envf('SH_OUT', (0.7,))[0],          # where along the neck the hand's centre sits (0 = housing end, 1 = drum)
                      roll=_envf('SH_ROLL', (100.0,))[0],       # deg about the neck's axis
                      yaw=_envf('SH_YAW', (180.0,))[0],         # deg about the vertical, on top of the rake
                      add=_envf('SH_ADD', (0.0, 0.0, 0.0)),     # gun frame, u
                      rows=dict(idle=('mp40_idle1', 1.0, 1.0), charge=('mp40_charge', 1.0, 1.0), fire=('mp40_fire', 1.0, 1.0),
                                fire_secondary=('mp40_fire_secondary', 1.0, 1.0),
                                pullout=('mp40_pullout', 0.0, 1.0), putaway=('mp40_putaway', 1.0, 0.0))),
}


def _T(v):
    m = np.eye(4); m[3, 0:3] = v
    return m


def _R(axis, deg):
    m = np.eye(4); m[0:3, 0:3] = R.axis_angle_rows(tuple(axis), deg)
    return m


def hold_rel(key):
    """(relation rows hand->tag pre-scale, {finger channel: quat}) of the support hand in the hold"""
    h = HOLDS[key]
    tc = R.load(R.ANIM + h['template'])
    pt = R.pose_dict(tc, 0)
    W = R.evaluate(pt)
    rel = W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right'])
    # the hand's centre on the template's magazine axis: the knuckles' mean, projected onto the axis
    kn = np.mean([(W['Bip01 L Finger%d' % i] @ R.inv(W['tag_weapon_right']))[3, 0:3] for i in (1, 2, 3, 4)], axis=0) * R.S
    a0, ad = np.asarray(h['t_axis'][0], float), np.asarray(h['t_axis'][1], float)
    a0[1] = 0.0
    cs = a0 + ad * ((kn - a0) @ ad)
    n0, n1 = np.asarray(h['neck'][0], float), np.asarray(h['neck'][1], float)
    nd = (n1 - n0) / np.linalg.norm(n1 - n0)
    cm = n0 + (n1 - n0) * h['out'] + np.asarray(h['add'], float)
    # the rotation that takes the template's magazine direction onto the neck's (both lie in the x-y plane)
    ang = math.degrees(math.atan2(np.cross(ad, nd)[2], ad @ nd))
    Rz = _R((0, 0, 1), ang + h['yaw'])
    if np.abs(np.r_[ad, 0.0] @ Rz - np.r_[nd, 0.0]).max() > 1e-3 and not h['yaw']:
        Rz = _R((0, 0, 1), -ang)
        assert np.abs(np.r_[ad, 0.0] @ Rz - np.r_[nd, 0.0]).max() < 1e-3
    A = _T(-cs / R.S) @ Rz @ _R(tuple(nd), h['roll']) @ _T(cm / R.S)
    fing = {ch: np.asarray(v, float) for ch, v in pt.items() if ch.startswith('Bip01 L Finger') and ch.endswith(' rot')}
    return rel @ A, fing, dict(template_centre=[round(float(x), 2) for x in cs], centre=[round(float(x), 2) for x in cm], rake_deg=round(ang, 1))


def bake(key, root, only=None):
    h = HOLDS[key]
    T, fing, info = hold_rel(key)
    print('%s: the template hand sits at %s on its magazine -> %s on the neck (rake %.1f deg, out %.2f, roll %.1f)' % (
        key, info['template_centre'], info['centre'], info['rake_deg'], h['out'], h['roll']))
    rows = H.fps_rows()
    staged = os.path.join(root, 'models', 'human', 'animation')
    rep = []
    for sfx, (row, w0, w1) in h['rows'].items():
        if only and sfx not in only:
            continue
        srcp = rows[row]
        sp = os.path.join(staged, srcp.replace('/', os.sep))
        try:
            src = R.load(sp if os.path.isfile(sp) else R.ANIM + srcp)
        except TypeError:                          # the released row names a clip that is not in the game (mp40_putaway)
            print('   coopr_%s_%-15s <- %s: NOT in the game files - no row (the prefix row plays, as today)' % (key, sfx, srcp))
            continue
        out = R.load(sp if os.path.isfile(sp) else R.ANIM + srcp)
        cm = R.chanmap(src)
        n = src.numFrames
        worst = 0.0
        for f in range(n):
            ph = dict(R.pose_dict(src, f))
            Wh = R.evaluate(ph)
            G = Wh['tag_weapon_right']
            HLr = Wh['Bip01 L Hand']
            u = f / float(max(1, n - 1))
            # raise: the hand comes onto the neck over the last 45 % of the clip; lower: leaves it over the first 45 %
            if w0 == w1:
                w = w0
            elif w1 > w0:
                w = SB.ease_((u - 0.55) / 0.45)
            else:
                w = 1.0 - SB.ease_(u / 0.45)
            HL = B.blend_H(HLr, T @ G, w) if w < 1.0 else T @ G
            pd = dict(ph)
            for ch, q in fing.items():
                if ch in pd:
                    pd[ch] = R.qslerp(np.asarray(pd[ch], float), q, w)
            K.solve_arms(pd, Wh, Wh['Bip01 R Hand'], HL, G, None)
            for ch in ph:                          # only the left arm may change
                if not ch.startswith('Bip01 L ') and not ch.startswith('tag_weapon_left'):
                    pd[ch] = ph[ch]
            K.write_frame(out, src, cm, f, pd)
            Wn = R.evaluate(R.pose_dict(out, f))
            worst = max(worst, float(np.linalg.norm(Wn['Bip01 L Hand'][3, 0:3] - HL[3, 0:3]) * R.S))
            assert np.abs(Wn['tag_weapon_right'] - G).max() < 1e-4 and np.abs(Wn['Bip01 R Hand'] - Wh['Bip01 R Hand']).max() < 1e-4, (row, f)
        out.values = [[[float(np.float32(x)) for x in out.V[f, c]] for c in range(out.numChannels)] for f in range(n)]
        bts = R.skc_io.write(out)
        o = '%s/coop_%s_%s.skc' % (h['vdir'], key, sfx)
        dst = os.path.join(staged, o.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(bts)
        print('   coopr_%s_%-15s <- %-48s %3d fr  hand off its place by %.2f u at worst (arm reach)  %s' % (key, sfx, srcp, n, worst, hashlib.md5(bts).hexdigest()[:8]))
        rep.append(['coopr_%s_%s' % (key, sfx), o, '0.25' if sfx in ('idle', 'charge') else ('0.05' if sfx == 'fire' else '0.3'), row])
    p = os.path.join(HERE, 'rows_extra.json')
    e = json.load(open(p)) if os.path.isfile(p) else {'repoint': [], 'add': []}
    names = [r[0] for r in rep]
    e['add'] = [x for x in e['add'] if x[0] not in names] + rep
    json.dump(e, open(p, 'w'), indent=1)


if __name__ == '__main__':
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    for k in sys.argv[1].split(','):
        bake(k, sys.argv[2], only)

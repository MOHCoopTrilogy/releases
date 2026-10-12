"""SMG aim poses with the support hand where the HIP pose has it (user 2026-10-12: "when holding the sten in ads, the
left hand should stay on the mag, it should be that way for any weapon where the mag is braced with the left/right
hand" / "Fix them all"). The SMG lane's version of ..\\tools\\magpose.py (same technique, same baker):

new pose = the released aim pose (`<prefix>_charge`) with the support hand in the hip idle's hand-to-gun relation
(place, rotation, fingers), the left arm solved to fit. Trunk, eye, the whole firing arm AND ITS FINGERS and the
weapon tag are the aim pose's, bit for bit, so the rig solve and the sight picture cannot change.

    cd smg/assets; python ../tools/smgpose.py <gun|all> .     -> <out>.skc (1 frame), prints hip / old aim / new aim
                                                                wrist places (gun frame, u) and the centre-box cover
"""
import sys, os, hashlib, subprocess, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.normpath(os.path.join(HERE, '..', '..', 'tools'))
sys.path.insert(0, SHARED)
import revbake as RB
H = RB.H; R = RB.R; V = RB.V

GUNS = {
    # prefix: sight gun (sights.json name), hip idle row, out clip; `lower` = camera-frame (fwd, left, up) nudge of the
    # hip relation where it would put the hand inside the centre box
    'mp40': dict(sight='mp40', idle='mp40_idle1', out='viewmodel/mp40/coop_mp40_ads_mag.skc'),
    # PPSh: at the exact hip place the thumb and the fingertips stand up on both sides of the rear sight (9.8 % of the
    # centre box). 1.2 u lower cleared the box but left the fingertips showing on the RIGHT of the receiver (run sa2;
    # coordinator: a left hand on the right of the gun reads wrong from the eye). The hip hand wraps a stock that is
    # narrower than the hand, so turning it about the gun's axis only moves the fingers round the right side; what
    # clears it is the same hand, same place ALONG the gun, 1.2 u to the left and 1.4 u lower: the fingertips end under
    # the stock, the palm and thumb lie on its left (0 px right of the centre line, 0.1 % of the box). 1.8 u off.
    'ppsh': dict(sight='ppsh_smg', idle='ppsh_idle', out='viewmodel/ppsh/coop_ppsh_ads_mag.skc', lower=(0.0, 1.2, -1.4)),
    'moschetto': dict(sight='moschetto', idle='moschetto_idle', out='viewmodel/moschetto/coop_moschetto_ads_mag.skc'),
    # Type 100 (side magazine): the exact hip place covers 11.8 % of the box with the hand; the pistol lane's first
    # pose took the magazine from underneath (0, 1.0, -1.7): 2.0 u off, 1.5 % hand in the box. (0, 1.05, -0.95) is
    # 1.4 u off (inside the matrix's 1.5 u) for 1.9 % (the released pose: 0.9 %). Same file, same row.
    'type100': dict(sight='type_100_smg', idle='type100_idle', out='viewmodel/sten/coop_type100_ads_mag.skc', lower=(0.0, 1.05, -0.95)),
    # the Sten's pose is the pistol lane's (magpose.py), taken over as a file: not rebuilt here
}
# the RELEASED aim clip of each prefix (the staged fps_anims_smg.txt already points sten / type100 at staged poses)
OLD_AIM = dict(mp40='viewmodel/mp40_stand_idle00.skc', ppsh='viewmodel/mp40_stand_idle00.skc',
               moschetto='viewmodel/mp40_stand_idle00.skc', type100='viewmodel/mp40_stand_idle00.skc',
               sten='viewmodel/mp40_stand_idle00.skc', thompson='viewmodel/idle_tommy_stand.skc')


def rel_hand(clip, f=0):
    a = R.load(clip if os.path.isfile(clip) else R.ANIM + clip)
    W = R.evaluate(R.pose_dict(a, min(f, a.numFrames - 1)))
    return (W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']))[3, :3] * R.S


def box_cover(gun, clip, W=640):
    """share of the centre box (middle 20 %) the first-person model covers in the settled aim, offline"""
    a = R.load(clip if os.path.isfile(clip) else R.ANIM + clip)
    sight = V.SIGHTS[gun]
    pd = R.pose_dict(a, a.numFrames - 1)
    corr = V.rig_target(V.evaluate_ctl(pd, RB.CTL), sight)
    Hh = W * 9 // 16
    surfs, E, Wb = V.scene2(pd, gun, sight['tik'], 'idle', 0.0, RB.CTL, corr, None)
    _, ids, _ = V.shade_render(surfs, E, V.weapon_fov(), W, Hh, tex=False)
    m = (ids >= 0)[int(Hh * 0.4):int(Hh * 0.6), int(W * 0.4):int(W * 0.6)]
    return float(m.mean())


def bake(name, root, lower=None, elb=None, elbw=None):
    g = GUNS[name]
    rows = H.fps_rows()
    hip, aim = rows[g['idle']], OLD_AIM[name]
    lower = lower if lower is not None else g.get('lower')
    rc = H.auto_recipe(g['idle'], gun=g['sight'], charge=aim, enter=0, exit=0, fixed_right=True, weight=dict(on=False),
                       handover=False, free_tag=False,
                       # the elbow hangs under the hand: the forearm comes up from the lower left, not straight at the eye
                       elbow_vec={'L': tuple(elb or g.get('elb', (0, 0.5, -1)))},
                       elbow_down={'L': [(0, float(elbw if elbw is not None else g.get('elbw', 4.0)))]})
    rc['hip'] = hip
    roll = float(os.environ['SP_ROLL']) if os.environ.get('SP_ROLL') else g.get('roll')
    if lower or roll:
        k = dict(rel=0, cam_add=tuple(lower or (0, 0, 0)), fing=0)
        if roll:
            # the hand turned about the gun's long axis through `pivot` (gun frame, u): the same place ALONG the gun,
            # the palm brought round to the gun's left / underside so no finger comes up on its right
            hc = R.load(R.ANIM + hip)
            Wh = R.evaluate(R.pose_dict(hc, 0))
            rel0 = Wh['Bip01 L Hand'] @ R.inv(Wh['tag_weapon_right'])
            pv = np.asarray(tuple(float(x) for x in os.environ['SP_PIVOT'].split(',')) if os.environ.get('SP_PIVOT') else g['pivot'], float) / R.S
            Tm = np.eye(4); Tm[3, 0:3] = -pv
            Rm = np.eye(4); Rm[0:3, 0:3] = R.axis_angle_rows((1, 0, 0), roll)
            Tp = np.eye(4); Tp[3, 0:3] = pv
            k['relT'] = rel0 @ Tm @ Rm @ Tp
        if g.get('fing_open') or os.environ.get('SP_OPEN'):
            pass
        rc['left_path'] = {0: k, R.load(R.ANIM + hip).numFrames - 1: k}
    H.RECIPES[g['idle']] = rc
    sk, _ = H.bake(g['idle'], RB.CTL)
    # the firing hand's fingers stay the AIM pose's (the baker takes both hands' fingers from the hip clip at w = 1)
    ac = R.load(R.ANIM + aim)
    pa = R.pose_dict(ac, ac.numFrames - 1)
    cm = R.chanmap(sk)
    nfix = 0
    for ch, i in cm.items():
        if ch.startswith('Bip01 R ') and ' Finger' in ch and ch in pa:
            sk.V[:, i] = pa[ch]; nfix += 1
    sk.values = [[[float(np.float32(x)) for x in sk.V[f, c]] for c in range(sk.numChannels)] for f in range(sk.numFrames)]
    tmp = os.path.join(HERE, '_smgpose_tmp.skc')
    open(tmp, 'wb').write(R.skc_io.write(sk))
    dst = os.path.join(root, 'models', 'human', 'animation', g['out'].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(SHARED, 'retime.py'), tmp, dst, 'slice', '0', '0'], check=True, capture_output=True)
    os.remove(tmp)
    # proof that nothing but the left arm changed: every channel outside 'Bip01 L ' / tag_weapon_left equals the aim pose
    n = R.load(dst); pn = R.pose_dict(n, 0)
    def _same(ch):                       # a rotation and its negated quaternion are the same; a position's 4th value is unused
        x, y = np.asarray(pn[ch], float), np.asarray(pa[ch], float)
        if ch.endswith(' rot'):
            return min(np.abs(x - y).max(), np.abs(x + y).max()) < 1e-5
        return np.abs(x[:3] - y[:3]).max() < 1e-5
    diff = [ch for ch in pn if ch in pa and not ch.startswith('Bip01 L ') and not ch.startswith('tag_weapon_left') and not _same(ch)]
    np.set_printoptions(precision=1, suppress=True)
    h, o, nw = rel_hand(hip), rel_hand(aim), rel_hand(dst)
    res = dict(hip=[round(float(x), 1) for x in h], old=[round(float(x), 1) for x in o], new=[round(float(x), 1) for x in nw],
               d_old=round(float(np.linalg.norm(h - o)), 1), d_new=round(float(np.linalg.norm(h - nw)), 1),
               box_old=round(100 * box_cover(g['sight'], aim), 1), box_new=round(100 * box_cover(g['sight'], dst), 1),
               clip=g['out'], md5=hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8], changed_outside_left_arm=diff)
    print('%-9s hip %s  old aim %s (%.1f u off)  new aim %s (%.1f u off) | centre box covered: old %.1f %%  new %.1f %% | %s %s%s'
          % (name, h, o, res['d_old'], nw, res['d_new'], res['box_old'], res['box_new'], g['out'], res['md5'],
             '' if not diff else '  !! CHANGED outside the left arm: %s' % diff))
    return res


if __name__ == '__main__':
    names = list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(',')
    kw = {}
    if os.environ.get('SP_LOWER'):
        kw['lower'] = tuple(float(x) for x in os.environ['SP_LOWER'].split(','))
    if os.environ.get('SP_ELB'):
        kw['elb'] = tuple(float(x) for x in os.environ['SP_ELB'].split(','))
    if os.environ.get('SP_ELBW'):
        kw['elbw'] = float(os.environ['SP_ELBW'])
    out = {nm: bake(nm, sys.argv[2], **kw) for nm in names}
    p = os.path.join(HERE, 'smgpose.json')
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.update(out)
    json.dump(d, open(p, 'w'), indent=1, sort_keys=True)
    if not kw and os.path.abspath(sys.argv[2]) == os.path.abspath(os.path.join(HERE, '..', 'assets')):
        # the lane's hand survey (the shape of ..\tools\handsurvey.json; coverage.py merges <lane>/handsurvey.json)
        rows = H.fps_rows()
        hs = {}
        for pfx, idle, clip in [(k, GUNS[k]['idle'], GUNS[k]['out']) for k in GUNS] + [('sten', 'sten_idle', 'viewmodel/sten/coop_sten_ads_mag.skc')]:
            h, a = rel_hand(rows[idle]), rel_hand(os.path.join(sys.argv[2], 'models', 'human', 'animation', clip.replace('/', os.sep)))
            dd = float(np.linalg.norm(h - a))
            hs[pfx] = dict(hip=[round(float(x), 1) for x in h], aim=[round(float(x), 1) for x in a], d=round(dd, 1), match=bool(dd <= 1.5),
                           aim_clip=clip, hip_clip=rows[idle], staged=True)
        json.dump(hs, open(os.path.join(HERE, '..', 'handsurvey.json'), 'w'), indent=1, sort_keys=True)
        print('wrote ../handsurvey.json', {k: v['d'] for k, v in hs.items()})

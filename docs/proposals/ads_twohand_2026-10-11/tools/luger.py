"""Luger P08 (+ silenced): its own aim pose and a WORKING TOGGLE in the reload (list item D).

Aim pose: pushpose.py - the approved two-handed Colt pose with the gun 2.2 u further from the eye (the Luger's rear
sight sits 1.6 u further back on its mesh than the Colt's; on the Colt pose its toggle block filled the lower half of
the centre box). Rows coopr_luger_p08_charge / coopr_silenced_luger_p08_charge (cgame ads-next 2627cb94).

Toggle: the mesh is one piece on bone Box01. bonefit.split puts the rear toggle link (rear sight + knurled knobs:
islands skin2/112 + skin1/240) on `coop_tog` and the breech block with the front link (skin2/206) on `coop_slide`.
Open = the rear link turned up TH deg about its axle, the breech back by what the linkage gives (two links L1, L2).
    idle_empty          toggle up (the hold-open after the last round)
    reload_ads_loaded   magazine out / in, toggle shut
    reload_ads_empty    toggle up from frame 0; the support hand takes the knobs from above, pulls and lets go: it snaps shut
    reload_empty        hip, emptied gun: up until the retail magazine is in
An open toggle stands 1.6 u ABOVE the sight line - it cannot be on the sights without covering the target. The emptied
gun is therefore held straight down under the centre box for the whole reload and comes back up when the toggle is shut.

    cd stage; python ../luger.py . [gun,pose,reload]      IRONSIGHT_EXTRA_PAKS = _ov_wip.pk3;_bases.pk3
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bonefit as BF
import p12, pistolgun, gunskc, gunphys
DIR = 'models/weapons/luger'
TIKS = {'lugerp08': 'luger.skd', 'lugerp08silenced': 'lugerSilenced.skd'}
PARTS = {'coop_tog': [('skin2', 112, -1.72), ('skin1', 240, -1.28)], 'coop_slide': [('skin2', 206, 0.76)]}
AIM = 'viewmodel/pistol/coop_luger_ads2h.skc'
VDIR = 'viewmodel/pistol'
AXLE = tuple(float(x) for x in os.environ.get('LUG_AXLE', '-1.05,-2.25').split(','))     # rear link's axle: gun x, z (u)
L1, L2 = 2.15, 1.9                              # axle -> knob joint, knob joint -> breech block pin (u)
TH = float(os.environ.get('LUG_TH', '50'))      # hold-open angle of the rear link
OVER = 6.0                                      # pulled this much further before it is let go
N = p12.N
T = pistolgun.GUNS['colt45']['t']
REL = dict(reach=48, pull=(49, 51), fwd=(52, 54), on=65)
LOW1 = tuple(float(x) for x in os.environ.get('LUG_LOW1', '2.4,0,0,0,0').split(','))      # the open toggle under the centre box
LOW2 = tuple(float(x) for x in os.environ.get('LUG_LOW2', '4.3,5,12,0,0.4').split(','))    # the hand over the knobs under it
GRASP_D = tuple(float(x) for x in os.environ.get('LUG_GRASP', '0.6,0.0,-1.0').split(','))  # the Hi-Standard overhand grasp moved onto the raised knobs
GRASP_F = ('clip', 'viewmodel/pistol/fire_hp.skc', 10)
DOWN_BY = int(os.environ.get('LUG_DOWN', '5'))


def back_of(th):
    t = math.radians(th)
    return (L1 + L2) - (L1 * math.cos(t) + math.sqrt(max(0.0, L2 * L2 - (L1 * math.sin(t)) ** 2)))


def angle(f, empty, hip=False):
    if not empty:
        return 0.0
    if hip:
        return TH if f <= N - 16 else TH * max(0.0, 1.0 - ((f - (N - 16)) / 2.0) ** 2)
    p0, p1 = REL['pull']; f0, f1 = REL['fwd']
    if f <= p0:
        return TH
    if f <= p1:
        u = (f - p0) / float(p1 - p0); return TH + OVER * u * u * (3 - 2 * u)
    if f <= f0:
        return TH + OVER
    return (TH + OVER) * max(0.0, 1.0 - ((f - f0) / float(f1 - f0)) ** 2)


def build_gun(root):
    for stem, skd in TIKS.items():
        BF.split('models/weapons/%s.tik' % stem, DIR + '/' + skd, PARTS, os.path.join(root, (DIR + '/' + skd).replace('/', os.sep)))
    A, o = BF.fit('models/weapons/lugerp08.tik', 'Box01')
    A2, o2 = BF.fit('models/weapons/lugerp08silenced.tik', 'Box01')
    assert np.abs(A - A2).max() < 1e-3 and np.abs(o - o2).max() < 1e-2      # one clip set serves both meshes
    raw = p12.rd(DIR + '/luger_reload.skc')
    a = gunskc.R.load(DIR + '/luger_reload.skc')
    cm = a.names.index('p38clip pos')
    seat_v = a.V[0, cm].copy()
    d = np.linalg.norm(a.V[:, cm, :3] - seat_v[:3], axis=1)
    far_v = a.V[int(np.argmax(d)), cm].copy()

    def clip(fn, n, empty, hip=False, magmove=True, const=None):
        tog_p, tog_q, br_p, br_q, mg = [], [], [], [], []
        for f in range(n):
            th = const if const is not None else angle(f, empty, hip)
            p, q = BF.chan(A, o, BF.rot_rows((0, 1, 0), th), (AXLE[0], 0.0, AXLE[1]))
            tog_p.append(p); tog_q.append(q)
            p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (-back_of(th), 0.0, 0.0))
            br_p.append(p); br_q.append(q)
            if hip:
                v = a.V[min(f, a.numFrames - 1), cm].copy()
            elif magmove:
                o0, o1 = T['out']; s0, s1 = T['seat']
                w = p12.smooth((f - o0) / float(o1 - o0)) if f < s0 - 6 else 1.0 - p12.smooth((f - (s0 - 6)) / float(s1 - (s0 - 6)))
                v = seat_v + (far_v - seat_v) * w
            else:
                v = seat_v.copy()
            mg.append([float(v[0]), float(v[1]), float(v[2]), 0.0])
        dst = os.path.join(root, (DIR + '/' + fn).replace('/', os.sep))
        gunskc.write(dst, raw, n, {'coop_tog pos': tog_p, 'coop_tog rot': tog_q, 'coop_slide pos': br_p, 'coop_slide rot': br_q, 'p38clip pos': mg},
                     frame_time=1 / 30.0)
        return fn
    clips = dict(reload_ads_loaded=clip('coop_luger_reload_ads_loaded.skc', N, False),
                 reload_ads_empty=clip('coop_luger_reload_ads_empty.skc', N, True),
                 reload_empty=clip('coop_luger_reload_empty.skc', N, True, hip=True),
                 idle_empty=clip('coop_luger_idle_empty.skc', 1, True, magmove=False, const=TH))
    nt = []
    for stem, tx in p12.tiks_for(dict(dir=DIR, clip='luger_reload.skc')):
        nl = '\r\n' if '\r\n' in tx else '\n'
        s = p12.patch_tik(stem, tx.replace('\r\n', '\n'), clips, 'shown by the cgame instead of `reload` (aimed; hip when empty): the toggle works')
        p12.depth_ok(s, stem)
        p12.write_tik(root, stem, s, nl)
        nt.append(stem)
    print('luger: toggle open %.0f deg = breech back %.2f u | clips %s | tiks %s' % (TH, back_of(TH), sorted(clips), nt))


def pose_keys(n):
    z = (0.0,) * 5
    # the gun starts down on the reload's first frame and is under the box by frame 5 (was 1 -> 7): the open toggle
    # stands in the centre box only while the gun travels
    return [(0, z), (DOWN_BY, LOW1), (REL['reach'] - 9, LOW1), (REL['reach'] - 3, LOW2), (REL['fwd'][1] + 2, LOW2), (REL['fwd'][1] + 12, z), (n, z)]


def toggle_hand(fing_open):
    import revbake as RB
    R = RB.R
    T0 = pistolgun.rack_rel('histandard').copy()
    T0[3, 0:3] += np.array(GRASP_D) / R.S
    up = (-0.15, 0.0, -0.30)
    return {REL['reach'] - 3: dict(relT=T0, cam_add=(0.0, 3.2, -3.4), fing=GRASP_F),      # round the left side, fingers already curled (open they stood up into the centre box: run pa8, 4.3 %)
            REL['reach']: dict(relT=T0, fing=GRASP_F), REL['pull'][0]: dict(relT=T0, fing=GRASP_F),
            REL['pull'][1]: dict(relT=T0, gun_add=up, fing=GRASP_F), REL['fwd'][0]: dict(relT=T0, gun_add=up, cam_add=(0.0, 0.9, -0.2), fing=GRASP_F),
            REL['fwd'][1] + 1: dict(relT=T0, gun_add=up, cam_add=(-0.3, 2.4, -1.2), fing=('clip', 'viewmodel/pistol/fire_hp.skc', 0))}


def bake_reload(root):
    import revbake as RB
    import pistolbake as PB
    import welrod as W
    H = RB.H
    base = dict(pistolgun.GUNS['colt45'])
    base.update(sight='luger_p08', aim=AIM, dir=DIR, clip='luger_reload.skc', empty=None, slide='coop_slide', mag=None, magup=(0.4, 0.0, -1.7))
    json.dump(dict(back=[-1.92, 0, 0], travel=1.0), open(os.path.join(HERE, 'slide_luger_l.json'), 'w'))
    json.dump(dict(back=[-1.92, 0, 0], travel=1.0), open(os.path.join(HERE, 'slide_luger.json'), 'w'))
    pistolgun.GUNS['luger_l'] = dict(base)
    eg = dict(base); eg['rack'] = dict(reach=REL['reach'], pull=REL['pull'], fwd=REL['fwd'], on=REL['on'])
    pistolgun.GUNS['luger'] = eg
    o_hand, o_pose, o_ev = pistolgun.rack_hand, pistolgun.rack_pose, PB.events
    pistolgun.rack_hand = lambda name, reach, pull, fwd, travel, fing, fing_open=None: toggle_hand(fing_open)
    pistolgun.rack_pose = lambda pull, fwd, n: pose_keys(n)
    PB.events = lambda g, empty: ([e for e in o_ev(g, empty) if e[1] not in ('slide_back', 'slide_fwd')]
                                  + [(REL['pull'][0], 'slide_back', 0.4), (REL['fwd'][1] - 1, 'slide_fwd', 0.8)]) if g.get('rack') else o_ev(g, empty)
    try:
        for key, empty in (('luger_l', False), ('luger', True)):
            kw, ph = PB.spec(key, empty)
            rc = H.auto_recipe('colt45_reload', **kw)
            H.RECIPES['colt45_reload'] = rc
            sk, _ = H.bake('colt45_reload', RB.CTL)
            W.save(root, sk, VDIR + '/coop_luger_reload_%sads.skc' % ('empty_' if empty else ''), ph)
    finally:
        pistolgun.rack_hand, pistolgun.rack_pose, PB.events = o_hand, o_pose, o_ev
        H.RECIPES.pop('colt45_reload', None)
        del pistolgun.GUNS['luger_l'], pistolgun.GUNS['luger']


def rows():
    L = ['\t//===================== HZM coop Luger P08: own aim pose (gun 2.2 u further out) and aimed reloads on it; the toggle works =====================']
    for key in ('luger_p08', 'silenced_luger_p08'):
        L += ['\tcoopr_%s_charge\t\t\t%s\t\tcrossblend 0.3' % (key, AIM),
              '\tcoopr_%s_reload\t\t\tviewmodel/pistol/reload_colt.skc\t\t\tcrossblend 0.3' % key,
              '\tcoopr_%s_reload_ads\t\t%s/coop_luger_reload_ads.skc\t\tcrossblend 0.1' % (key, VDIR),
              '\tcoopr_%s_reload_empty\t\tviewmodel/pistol/reload_colt.skc\t\t\tcrossblend 0.3' % key,
              '\tcoopr_%s_reload_empty_ads\t%s/coop_luger_reload_empty_ads.skc\t\tcrossblend 0.1' % (key, VDIR)]
    open(os.path.join(HERE, 'rows_p12_luger.txt'), 'w', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    root = sys.argv[1]
    what = sys.argv[2].split(',') if len(sys.argv) > 2 else ['gun', 'reload']
    if 'gun' in what:
        build_gun(root)
    if 'reload' in what:
        bake_reload(root)
    rows()

"""Welrod: a BOLT-ACTION pistol (list item D). Aimed, the bolt is worked by hand after every shot and at the end of
the reload of an emptied gun: the support hand leaves the grip, takes the knurled knob at the rear of the tube, turns
it, pulls the bolt back, runs it forward, turns it shut and returns to the grip. The knob sits ON the sight line, so
the gun is brought down under the centre box for it (pistolgun.rack_pose, as the Hi-Standard's rack) and comes back
onto the sights - the target stays in view above the gun. The gun's motion is gunphys (class pistol).

Gun: the mesh has no moving part (its clips are one frame). slidesplit.py puts the bolt surface (Cylinder3: knob +
bolt body) on a bone `coop_slide`; this module writes
    fire        the retail still pose, 26 frames (0.87 s, inside the 0.9 s fire delay) - the server's `fire` has to last
                as long as the cycle for the cgame to swap it
    fire_ads    the same length, the bolt turned / pulled / run forward / turned (shown while aiming with rounds left)
    reload      still, 73 frames (the hand clip's length; the retail clip is ONE frame)
    reload_ads_loaded   = reload (a round is chambered: no bolt work)
    reload_ads_empty    the bolt cycled at the end
Hands (per-weapon rows, cgame ads-next 2627cb94): coopr_welrod_cycle(_ads), coopr_welrod_reload(_ads),
coopr_welrod_reload_empty(_ads). At the hip nothing changes.

    cd stage; python ../welrod.py .          needs IRONSIGHT_EXTRA_PAKS=<pk3 with the 27-frame base clip> (see p12rows)
"""
import sys, os, re, json, math, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
import gunphys, gunskc, pistolgun, p12
import pistolbake as PB
H = RB.H; R = RB.R
NAME = 'welrod'
DIR = 'models/weapons/welrod'
AIM = 'viewmodel/pistol/coop_welrod_ads2h.skc'      # pushpose.py: the Colt pose with the gun 3.4 u further out (the knob stood 9.6 u from the eye)
VDIR = 'viewmodel/pistol'
BASE27 = 'viewmodel/pistol/coop_base_cycle27.skc'          # fire_hp.skc frames 0-26 (retime.py slice), in the overlay
SP = json.load(open(os.path.join(HERE, 'slide_welrod.json')))
TRAVEL = SP['travel']
PULL = 0.92
TURN = float(os.environ.get('WEL_TURN', '55'))              # degrees the knob (and the hand) turns to unlock
AXIS = (-0.62, -1.90)                                       # the bore in the gun frame: y (right), z (down), u
KNOB = float(os.environ.get('WEL_KX', '-2.6'))              # the Hi-Standard overhand grasp moved onto the knob (gun frame, u)
GRASP_D = (KNOB, 0.3, 0.2)
CYC = dict(off=(2, 5), reach=8, turn=(8, 10), pull=(10, 12), fwd=(13, 14), shut=(14, 16), on=(17, 22), n=26, down=(1, 6), up=(17, 24))
# the gun's pose while the bolt is worked (drop u, roll, pitch deg muzzle down, side, back u): lower than the Hi-Standard's
# rack (the hand sits BEHIND the gun and comes toward the eye on the pull), less pitch (a shorter way back up)
DOWN = tuple(float(x) for x in os.environ.get('WEL_DOWN', '2.8,6,13,0,0.4').split(','))
REL = dict(reach=48, turn=(49, 51), pull=(51, 53), fwd=(55, 56), shut=(56, 58), on=65, down=(41, 47), up=(59, 68))


def pose_keys(k, n):
    z = (0.0,) * 5
    return [(0, z), (k['down'][0], z), (k['down'][1], DOWN), (k['up'][0], DOWN), (k['up'][1], z), (n, z)]


def state(f, k):
    """(turn 0..1, back 0..1) of the bolt at frame f"""
    def ss(a, b):
        u = min(1.0, max(0.0, (f - a) / float(b - a))); return u * u * (3 - 2 * u)
    turn = ss(*k['turn']) * (1.0 - ss(*k['shut']))
    back = ss(*k['pull']) if f <= k['fwd'][0] else max(0.0, 1.0 - ((f - k['fwd'][0]) / float(k['fwd'][1] - k['fwd'][0])) ** 2)
    return turn, back * PULL


def twist4(deg):
    """4x4 (rows) in the gun frame: a turn about the bore, anticlockwise seen from behind (the top goes left)"""
    M = np.eye(4)
    r = R.axis_angle_rows(np.array([1.0, 0.0, 0.0]), deg)
    if (np.array([0.0, 0.0, -1.0]) @ r)[1] > 0:               # the top (-z) has to go to -y
        r = R.axis_angle_rows(np.array([1.0, 0.0, 0.0]), -deg)
    c = np.array([0.0, AXIS[0], AXIS[1]]) / R.S
    M[0:3, 0:3] = r
    M[3, 0:3] = c - c @ r
    return M


def grasp():
    T = pistolgun.rack_rel('histandard').copy()               # the retail overhand grasp (hip fire clip of the Hi-Standard)
    T[3, 0:3] += np.array(GRASP_D) / R.S
    return T


APPROACH = tuple(float(x) for x in os.environ.get('WEL_APP', '0,2.2,-1.4').split(','))


GRASP_F = ('clip', 'viewmodel/pistol/fire_hp.skc', 10)      # the overhand grasp's own fingers (the Hi-Standard hip rack)


def bolt_hand(k, fing, fing_open):
    T0 = grasp()
    Tt = T0 @ twist4(TURN)
    back = (-TRAVEL * PULL, 0.0, 0.0)
    # the hand comes to the knob round the LEFT side and from below (over the top it crossed the centre box, offline)
    return {k['reach'] - 2: dict(relT=T0, cam_add=APPROACH, fing=fing_open),
            k['reach']: dict(relT=T0, fing=fing), k['turn'][0]: dict(relT=T0, fing=fing), k['turn'][1]: dict(relT=Tt, fing=fing),
            k['pull'][1]: dict(relT=Tt, gun_add=back, fing=fing), k['fwd'][0]: dict(relT=Tt, gun_add=back, fing=fing),
            k['fwd'][1]: dict(relT=Tt, fing=fing), k['shut'][1]: dict(relT=T0, fing=fing),
            k['shut'][1] + 1: dict(relT=T0, cam_add=(0.0, 0.5, -0.3), fing=fing_open)}


def events(k, on):
    s = 0.30                                                   # the rifle bolt impulses on a 1 kg pistol
    return [(k['turn'][0], 'bolt_up', s), (k['pull'][0], 'bolt_back', s), (k['fwd'][1] - 1, 'bolt_fwd', s * 1.4), (k['shut'][0], 'bolt_down', s),
            (on - 4, 'hand_on')]


def quat_x(deg):
    """bone rotation (x, y, z, w) for a turn of `deg` about the bore; the sign convention is checked by gunview"""
    h = math.radians(deg) / 2.0
    return np.array([math.sin(h) * QSIGN, 0.0, 0.0, math.cos(h)])


QSIGN = float(os.environ.get('WEL_QSIGN', '1'))


def gun_clip(root, fn, n, k, tmpl):
    A = np.array(SP['A']); s = float(A[0, 0])                 # local = gun / s (identity orientation, measured by slidesplit)
    c = np.array([0.0, AXIS[0], AXIS[1]]) / s
    pos, rot = [], []
    for f in range(n):
        tn, bk = state(f, k) if k else (0.0, 0.0)
        q = quat_x(TURN * tn)
        # rotate about the bore (pivot c): p' = rot(p - c) + c; the engine applies rot then pos
        x, y, z, w = q
        Rm = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                       [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                       [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        p = c - (Rm @ c if QCOL else c @ Rm)
        p = p + np.array(SP['back']) * TRAVEL * bk
        pos.append([float(p[0]), float(p[1]), float(p[2]), 0.0]); rot.append([float(v) for v in q])
    dst = os.path.join(root, (DIR + '/' + fn).replace('/', os.sep))
    gunskc.write(dst, tmpl, n, {'coop_slide pos': pos, 'coop_slide rot': rot}, frame_time=1 / 30.0)
    return fn


QCOL = os.environ.get('WEL_QCOL', '0') == '1'      # the engine applies a bone quaternion as rows (measured: gunview, the knob stays on the bore)


def build_gun(root):
    tmpl = p12.rd(DIR + '/welrod_pistol_reload.skc')
    kc = dict(CYC)
    clips = dict(fire_ads=gun_clip(root, 'coop_welrod_fire_ads.skc', 26, kc, tmpl),
                 reload=gun_clip(root, 'coop_welrod_reload_hip.skc', p12.N, None, tmpl),
                 reload_ads_empty=gun_clip(root, 'coop_welrod_reload_ads_empty.skc', p12.N, REL, tmpl))
    clips['reload_ads_loaded'] = clips['reload']
    g = dict(dir=DIR, clip='welrod_pistol_reload.skc')
    nt = []
    for stem, tx in p12.tiks_for(g):
        nl = '\r\n' if '\r\n' in tx else '\n'
        s = tx.replace('\r\n', '\n')
        s = p12.patch_tik(stem, s, {k: clips[k] for k in ('reload_ads_loaded', 'reload_ads_empty')},      # `reload` = the server's row: as released (bug-3736)
                          'shown by the cgame instead of `reload` while aiming; the bolt is cycled when the gun was empty')
        mm = re.search(r'(?m)^(\s*)fire(\s+)welrod_pistol_fire\.skc[^\n]*\n', s)
        assert mm, stem
        i = s.index('{', mm.end()); d = 0; j = i
        while True:
            d += (s[j] == '{') - (s[j] == '}')
            j += 1
            if d == 0:
                break
        blk = '%sfire_ads%s%s\n%s%s\n' % (mm.group(1), mm.group(2), clips['fire_ads'], mm.group(1), s[i:j])
        blk = re.sub(r'commanddelay\s+0\.1(\s+tagspawn\s+tag_eject)', r'commanddelay %.2f\1' % ((CYC['pull'][0] + 1) / 30.0), blk)   # the case leaves when the bolt is pulled
        s = (s[:mm.start()] + '%s// HZM coop [aimed bolt cycle, pistol lane 2026-10-12] shown by the cgame instead of `fire` while aiming: the bolt is worked\n' % mm.group(1)
             + blk + s[mm.start():mm.end()] + s[mm.end():])                                  # `fire` = the server's row: as released (bug-3736)
        p12.depth_ok(s, stem)
        p12.write_tik(root, stem, s, nl)
        nt.append(stem)
    print('welrod gun clips', clips, '| tiks', len(nt))


def save(root, sk, out, ph):
    bts = R.skc_io.write(sk)
    dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bts)
    print('welrod hands ->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8]); print('   ', ph['report'])


def bake_cycle(root):
    k = CYC; n = k['n']
    a0, a1 = k['off']; o0, o1 = k['on']
    ph = gunphys.simulate(n + 1, 1 / 30.0, 'pistol', support=[(0, 1), (a0, 1), (a1, 0), (o0, 0), (o1, 1)], events=events(k, o1),
                          pose=pose_keys(k, n))
    AIMK = dict(aim=1, fing='aim')
    lp = {0: AIMK, k['reach'] - 4: AIMK}
    lp.update(bolt_hand(k, 10, ('mix', 0, 0.6)))
    for f in range(o1, n + 1):
        lp[f] = AIMK
    row = 'coopr_welrod_cycle'
    rc = dict(gun='welrod', hip=BASE27, charge=AIM, offhand=(-1, -1), enter=0, exit=0, slide={}, weight=dict(on=False), fixed_right=True,
              dip=ph['dip'], left_path=lp, handover=False, elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.0, -1.0)})
    H.RECIPES[row] = rc
    sk, _ = H.bake(row, RB.CTL)
    save(root, sk, VDIR + '/coop_welrod_cycle_ads.skc', ph)


def bake_reload(root):
    base = dict(pistolgun.GUNS['colt45'])
    base.update(sight='welrod', aim=AIM, dir=DIR, clip='welrod_pistol_reload.skc', empty=None, slide='coop_slide', mag=None, magup=(0.3, 0.0, -1.6))
    pistolgun.GUNS['welrod_l'] = dict(base)
    eg = dict(base); eg['rack'] = dict(reach=REL['reach'], pull=REL['pull'], fwd=REL['shut'], on=REL['on'])
    pistolgun.GUNS['welrod'] = eg
    json.dump(SP, open(os.path.join(HERE, 'slide_welrod_l.json'), 'w'))
    orig = pistolgun.rack_hand
    orig_pose = pistolgun.rack_pose
    pistolgun.rack_pose = lambda pull, fwd, n: pose_keys(REL, n)
    pistolgun.rack_hand = lambda name, reach, pull, fwd, travel, fing, fing_open=None: bolt_hand(REL, GRASP_F, GRASP_F)
    orig_ev = PB.events
    PB.events = lambda g, empty: ([e for e in orig_ev(g, empty) if e[1] not in ('slide_back', 'slide_fwd', 'hand_on')] + events(REL, REL['on'])) if g.get('rack') else orig_ev(g, empty)
    try:
        for key, empty in (('welrod_l', False), ('welrod', True)):
            kw, ph = PB.spec(key, empty)
            rc = H.auto_recipe('colt45_reload', **kw)
            H.RECIPES['colt45_reload'] = rc
            sk, _ = H.bake('colt45_reload', RB.CTL)
            save(root, sk, VDIR + '/coop_welrod_reload_%sads.skc' % ('empty_' if empty else ''), ph)
    finally:
        pistolgun.rack_hand = orig; PB.events = orig_ev; pistolgun.rack_pose = orig_pose
        H.RECIPES.pop('colt45_reload', None)
        del pistolgun.GUNS['welrod_l'], pistolgun.GUNS['welrod']


ROWS = ['\tcoopr_welrod_charge\t\t\t%s\t\tcrossblend 0.3' % AIM,
        '\tcoopr_welrod_reload\t\t\tviewmodel/pistol/reload_colt.skc\t\t\tcrossblend 0.3',
        '\tcoopr_welrod_reload_ads\t\t%s/coop_welrod_reload_ads.skc\t\tcrossblend 0.1' % VDIR,
        '\tcoopr_welrod_reload_empty\t\tviewmodel/pistol/reload_colt.skc\t\t\tcrossblend 0.3',
        '\tcoopr_welrod_reload_empty_ads\t%s/coop_welrod_reload_empty_ads.skc\t\tcrossblend 0.1' % VDIR,
        '\tcoopr_welrod_cycle\t\t\t%s/coop_welrod_cycle_ads.skc\t\tcrossblend 0.08' % VDIR,
        '\tcoopr_welrod_cycle_ads\t\t%s/coop_welrod_cycle_ads.skc\t\tcrossblend 0.08' % VDIR]


if __name__ == '__main__':
    root = sys.argv[1]
    what = sys.argv[2].split(',') if len(sys.argv) > 2 else ['gun', 'cycle', 'reload']
    if 'gun' in what:
        build_gun(root)
    if 'cycle' in what:
        bake_cycle(root)
    if 'reload' in what:
        bake_reload(root)
    open(os.path.join(HERE, 'rows_p12_welrod.txt'), 'w', newline='\n').write('\t//===================== HZM coop Welrod (bolt-action pistol): own aimed reload and per-shot bolt cycle =====================\n' + '\n'.join(ROWS) + '\n')

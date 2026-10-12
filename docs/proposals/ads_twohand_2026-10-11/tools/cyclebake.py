"""Aimed PER-SHOT CYCLE of a hand-cycled pistol (user 2026-10-12: "That hi standard needs a first person ads cock
animation between shots too"): the silenced Hi-Standard is racked by hand after every shot (fire delay 1.0 s; the hip
fire clip does it with the left hand, the aimed fire played the static aim pose).

Hands: `<prefix>_cycle_ads` - from the two-handed aim the support hand leaves the grip, takes the slide from the LEFT
with the retail hip clip's own hand-to-gun relation (so the centre stays as clear as the retail grasp allows), pulls it
back, lets it run forward and returns to the grip. Timed to the rack clicks inside the retail fire sound (frames 11-13
back, 16-18 forward). Gun motion from gunphys (pull back = the gun comes rearward, muzzle lifts; release = thrown
forward). Gun: `fire_ads` - the weapon's fire animation with the slide (coop_slide) following the hand.
cgame (ads-next): hands clip on a clip-ammo drop while aiming; gun shows fire_ads instead of fire while aiming.

    cd stage; python ../cyclebake.py histandard .
"""
import sys, os, re, hashlib, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
import gunphys, gunskc, pistolgun
H = RB.H; R = RB.R
MOD = pistolgun.MOD

GUNS = {
    # rel: hip fire clip frame with the hand on the slide; pull / fwd: frames the slide moves back / forward over
    'histandard': dict(row='histandard_fire', rel=10, off=(2, 5), reach=9, pull=(11, 13), fwd=(16, 17), on=(21, 27), cls='pistol',
                       fireclip='hs_pistol_fire.skc'),
}


def bake(name, root):
    g = GUNS[name]; pg = pistolgun.GUNS[name]
    hipc = H.fps_rows()[g['row']]
    n = R.load(R.ANIM + hipc).numFrames - 1
    sp = json.load(open(os.path.join(HERE, 'slide_%s.json' % name)))
    trav = sp['travel']
    p0, p1 = g['pull']; f0, f1 = g['fwd']; o0, o1 = g['on']; a0, a1 = g['off']
    ph = gunphys.simulate(n + 1, 1 / 30.0, g['cls'], support=[(0, 1), (a0, 1), (a1, 0), (o0, 0), (o1, 1)],
                          events=[(p0, 'slide_back'), (f1 - 1, 'slide_fwd'), (o1 - 4, 'hand_on')])
    AIM = dict(aim=1, fing='aim')
    # the retail grasp goes OVER the slide and a pinch from behind sits between the eye and the gun: both cover the
    # sights (offline previews). Aimed, the support hand slides UP from its grip along the left side of the gun to the
    # slide, takes it there and pulls - it stays left of the sight line
    UP = tuple(float(x) for x in os.environ.get('CY_UP', '0.3,0.5,1.7').split(','))      # camera frame: fwd, left, up
    FG = ('mix', g['rel'], float(os.environ.get('CY_FG', '0.35')))
    ON = dict(aim=1, cam_add=UP, fing=FG)
    BACK = dict(aim=1, cam_add=UP, gun_add=(-trav * 0.92, 0.0, 0.0), fing=FG)
    lp = {0: AIM, a0: AIM, g['reach']: ON, p0: ON, p1: BACK, f0: BACK,
          f1: dict(aim=1, cam_add=UP, gun_add=(-0.5, 0.0, 0.0), fing=FG),                 # the slide leaves the fingers
          f1 + 3: dict(aim=1, cam_add=tuple(0.5 * x for x in UP), fing='aim')}
    for f in range(o1, n + 1):
        lp[f] = AIM
    rc = H.auto_recipe(g['row'], gun=pg['sight'], charge=pg['aim'], hip=hipc, enter=0, exit=0, fixed_right=True, dip=ph['dip'],
                       left_path=lp, weight=dict(on=False), handover=False, offhand=(-1, -1),
                       elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.0, -1.0)})
    H.RECIPES[g['row']] = rc
    sk, _ = H.bake(g['row'], RB.CTL)
    bts = R.skc_io.write(sk)
    out = '%s/%s_cycle_ads.skc' % (pg['vdir'], name)
    dst = os.path.join(root, 'models', 'human', 'animation', out.replace('/', os.sep))
    open(dst, 'wb').write(bts)
    print(name, 'hands ->', out, sk.numFrames, 'frames', hashlib.md5(bts).hexdigest()[:8]); print('   ', ph['report'])
    # ---- the gun: fire_ads = the fire clip's length, the slide following the hand
    raw = pistolgun.read_game(pg['dir'] + '/' + g['fireclip'])
    a = R.load(pg['dir'] + '/' + g['fireclip'])
    secs = a.numFrames * a.frameTime
    m = int(round(secs * 30.0))
    back = np.array(sp['back']) * trav
    tr = np.zeros((m, 4))
    for f in range(m):
        if f <= p0:
            u = 0.0
        elif f <= p1:
            u = (f - p0) / float(p1 - p0); u = u * u * (3 - 2 * u)
        elif f <= f0:
            u = 1.0
        else:
            u = max(0.0, 1.0 - ((f - f0) / float(f1 - f0)) ** 2)
        tr[f, :3] = back * u * 0.92
    keyed = {nm: [list(a.V[0, c]) for _ in range(m)] for c, nm in enumerate(a.names)}
    for nm in keyed:
        if nm.endswith(' pos'):
            for v in keyed[nm]:
                v[3] = 0.0
    keyed['coop_slide pos'] = [list(v) for v in tr]
    keyed['coop_slide rot'] = [[0, 0, 0, 1.0]] * m
    fn = 'coop_%s_fire_ads.skc' % name
    gdst = os.path.join(root, (pg['dir'] + '/' + fn).replace('/', os.sep))
    gunskc.write(gdst, raw, m, keyed, frame_time=1 / 30.0)
    print(name, 'gun ->', pg['dir'] + '/' + fn, m, 'frames (retail fire clip %.2f s)' % secs)
    # ---- tiks (already staged by pistolgun.py): fire_ads = a copy of the fire animation's block on the new clip
    wd = os.path.join(root, 'models', 'weapons')
    nt = 0
    for tf in sorted(os.listdir(wd)):
        p = os.path.join(wd, tf)
        if not tf.lower().endswith('.tik'):
            continue
        t = open(p, 'rb').read().decode('latin-1')
        nl = '\r\n' if '\r\n' in t else '\n'
        s = t.replace('\r\n', '\n')
        mm = re.search(r'(?m)^(\s*)fire(\s+)%s[^\n]*\n' % re.escape(g['fireclip']), s)
        if not mm or 'fire_ads' in s:
            continue
        i = s.index('{', mm.end()); d = 0; j = i
        while True:
            d += (s[j] == '{') - (s[j] == '}')
            j += 1
            if d == 0:
                break
        blk = '%sfire_ads%s%s\n%s%s\n' % (mm.group(1), mm.group(2), fn, mm.group(1), s[i:j])
        s = s[:mm.start()] + '%s// HZM coop [aimed per-shot cycle 2026-10-12] shown by the cgame instead of `fire` while aiming: the slide is racked\n' % mm.group(1) + blk + s[mm.start():]
        dp = 0
        for ln in s.split('\n'):
            c = ln.split('//')[0]; dp += c.count('{') - c.count('}')
        assert dp == 0, tf
        open(p, 'wb').write(s.replace('\n', nl).encode('latin-1'))
        nt += 1
    print(name, 'tiks with fire_ads:', nt)
    open(os.path.join(HERE, 'rows_cycle.txt'), 'w', newline='\n').write(
        '\t//===================== HZM coop aimed per-shot cycle (cgame plays <prefix>_cycle_ads on a clip-ammo drop while aiming) =====================\n'
        + ''.join('\t%s_cycle_ads\t\t%s/%s_cycle_ads.skc\t\tcrossblend 0.08\n' % (k, pistolgun.GUNS[k]['vdir'], k) for k in GUNS))


if __name__ == '__main__':
    for nm in sys.argv[1].split(','):
        bake(nm, sys.argv[2])

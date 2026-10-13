"""Mauser C96 (+ Trench C96): the aimed reload on the mod's EXISTING stripper-clip prop (pistol lane, 2026-10-13 pm).

The C96 has no detachable magazine. The RELEASED game already loads it from the top at the hip: hands row
`coopr_mauser_c96_reload` = viewmodel/coop_reload/c96_reload.skc (anims_shared.txt) and the server's torso row
`coop_reload_c96`, which hangs the prop on the hands' tags (torso frames, 30 per second, = hands frames):
    28  models/ammo/coop_c96_stripper_full.tik on tag_weapon_left      (the clip in the support hand)
    41  the full clip on tag_weapon_right                              (= standing in the gun's guides)
    44  swapped for coop_c96_stripper_empty.tik, clip_fill             (the rounds are in)
    47  the empty clip on tag_weapon_left                              (taken by the hand)
    56  removed
This file builds the AIMED hands clips ON THAT TIMELINE (it is a server row: not changed) and the gun's clips.
The earlier version of this file (commit ddd502c) parked tag_weapon_left under the view and drew a clip of its own on
the gun's mesh; it also re-declared the hip row as the P38 magazine clip. Both are gone: the hip reload is the released
stripper reload, the clip that is seen is the server's prop.

Hands (both on the C96's two-handed aim pose): the gun comes straight down under the centre box and is turned so that
the eye looks at the SIDE of the standing clip (LOW: drop, roll, pitch, side, back; YAW); the support hand fetches the
clip below the frame (it appears in the hand at 28, out of view), brings it over the open action, stands it in the
guides (40), the thumb runs the rounds down (41-45, the server swaps the prop at 44), the hand takes the empty clip
(47), lifts it out (49-52: the bolt runs forward), drops it to the left (gone at 56) and returns to the grip while the
gun comes back up. tag_weapon_left is keyed RIGID to the support hand with the transform that makes it equal
tag_weapon_right at frame 41 (and at 47 for the way out), so the prop never jumps when the server moves it between the
tags.
Gun (mesh coop_c96: bonefit.split puts the bolt's rear end on `coop_slide`, the hammer on `coop_tog`; c96clip adds the
bolt bar and the open-port patch): bolt travel 2.0 u.
    idle_empty          bolt back, hammer cocked
    reload_ads_empty    bolt back from frame 0, forward as the clip leaves the guides
    reload_ads_loaded   rounds left: the support hand draws the bolt back first, then the same
    reload_empty        hip, emptied: back until the released hip hands lift the clip out (frame 48)
    reload              hip, rounds left (SERVER row: same 73 frames as the released P38_reload.skc): the bolt is drawn
                        back where the released hip hands pull its ears (12-18) and runs forward at 48

    cd stage; python ../c96.py . [reload,gun]       IRONSIGHT_EXTRA_PAKS = _ov_wip.pk3;_bases.pk3
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bonefit as BF
import p12, pistolgun, gunskc, gunphys
import c96clip as CC
GUNS = dict(mauser_c96=dict(dir='models/weapons/coop_c96', tik='models/weapons/mauser_c96.tik', skd='c96.skd', clip='P38_reload.skc', idle='c96.skc',
                            parts={'coop_slide': [('Cylinder1', 86, 0.72)], 'coop_tog': [('Tube3', 168, -0.04)]}))
AIM = os.environ.get('C96_AIM', 'viewmodel/pistol/coop_c96_ads2h.skc')
VDIR = 'viewmodel/pistol'
N = p12.N
BOLT = CC.BOLT
HAM = float(os.environ.get('C96_HAM', '78'))                                   # deg the hammer lies back when the bolt is over it
HPIV = (-0.30, -1.75)                        # hammer pivot, gun x / z
# the server's timeline (anims_shared.txt, torso row coop_reload_c96)
SRV = dict(hand=28, gun=41, fill=44, take=47, gone=56)
# frames: off = hand leaves the grip; draw = (loaded only) the bolt drawn back; pouch = hand below the frame;
# over = above the action with the clip; at = the clip stands in the guides; press = the rounds thumbed down;
# out = the empty clip lifted out (the bolt goes forward over its last two frames); toss = dropped; on = grip
K = dict(off=(3, 8), draw=(16, 20), pouch=(17, 29), pouch_l=(25, 29), over=36, at=40, press=(41, 45), out=(49, 52), toss=56, on=(59, 66), down=(2, 8), up=(55, 69))
DOWN_E = (19, 25, 32)    # emptied gun: it stays in the aim (one-handed) while the hand fetches the clip; straight down first (to LOW1, 19-25), turned only once it is under the box (25-32), as the hand comes up
DOWN2 = (21, 31)         # rounds left: the bolt is drawn LATE (16-20) so that the hand is away for the clip only 0.2 s (it appears in the hand at 28, below the frame); the gun turns to LOW meanwhile - it is not left standing alone (run pa30: with the draw at 10-13 it was alone for 0.5 s)
HIP = dict(draw=(12, 18), close=48)          # where the RELEASED hip hands pull the bolt's ears / lift the clip out (c96probe: left hand in gun space)


def envt(name, default):
    return tuple(float(x) for x in os.environ.get(name, default).split(','))


LOW = envt('C96_LOW', '4.6,-60,6,3,0.3')            # drop u, roll, pitch (muzzle down), side (+ = left), back
LOW1 = envt('C96_LOW1', '3.4,4,11,0,0.3')              # rounds left: the first, shallower lowering for the bolt draw
YAW = float(os.environ.get('C96_YAW', '-35'))          # deg the lowered gun is turned about the view's up axis (- = muzzle to the right: the eye sees the clip's side, the hand is behind it)
HOLD = envt('C96_HOLD', '-0.8,-1.5,-3.1')                # the hand on the clip, gun u from the grasp point (z up = negative)
HTRAV = float(os.environ.get('C96_HTRAV', '1.5'))      # u the hand goes down with the rounds
GRASP_D = envt('C96_GRASP', '3.6,0.0,-0.9')            # the Hi-Standard overhand grasp moved over the clip guides
HROT = envt('C96_HROT', '0,-90,0')                      # deg about the gun's x / y / z: the hand on the clip turned from the overhand rack grasp
GRASP_F = ('clip', 'viewmodel/pistol/fire_hp.skc', 10)
POUCH = (5.0, 9.0, -15.0)
TOSS = envt('C96_TOSS', '7.0,12.0,-13.0')              # where the empty clip is let go (camera: forward, left, up), below the frame


def bolt_state(f, empty, hip=False):
    """0..1: how far back the bolt is"""
    if hip:
        c = HIP['close']
        close = 1.0 if f <= c else max(0.0, 1.0 - ((f - c) / 2.0) ** 2)
        if empty:
            return close
        d0, d1 = HIP['draw']
        return min(p12.smooth((f - d0) / float(d1 - d0)), close)
    o0, o1 = K['out']
    close = 1.0 if f <= o1 - 2 else max(0.0, 1.0 - ((f - (o1 - 2)) / 2.0) ** 2)
    if empty:
        return close
    d0, d1 = K['draw']
    return min(p12.smooth((f - d0) / float(d1 - d0)), close)


def build_gun(root, key='mauser_c96'):
    g = GUNS[key]
    DIR = g['dir']
    skdf = os.path.join(root, (DIR + '/' + g['skd']).replace('/', os.sep))
    BF.split(g['tik'], DIR + '/' + g['skd'], g['parts'], skdf)
    CC.add_to_skd(skdf, g['tik'])
    CC.textures(root)
    A, o = BF.fit(g['tik'], 'origin')
    raw = p12.rd(DIR + '/' + g['clip'])

    def clip(fn, n, empty, hip=False, const=None):
        bp, bq, hp, hq = [], [], [], []
        st = (lambda f: const) if const is not None else (lambda f: bolt_state(f, empty, hip))
        extra = CC.port_only(A, o, n, st)
        for f in range(n):
            u = st(f)
            p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (-BOLT * u, 0.0, 0.0))
            bp.append(p); bq.append(q)
            p, q = BF.chan(A, o, BF.rot_rows((0, 1, 0), HAM * min(1.0, u * 1.6)), (HPIV[0], 0.0, HPIV[1]))
            hp.append(p); hq.append(q)
        ch = dict({'coop_slide pos': bp, 'coop_slide rot': bq, 'coop_tog pos': hp, 'coop_tog rot': hq}, **extra)
        seat = gunskc.R.load(DIR + '/' + g['idle'])
        if 'p38clip pos' in seat.names:
            ch['p38clip pos'] = [[float(x) for x in seat.V[0, seat.names.index('p38clip pos')][:3]] + [0.0]] * n     # no magazine leaves this gun
        dst = os.path.join(root, (DIR + '/' + fn).replace('/', os.sep))
        gunskc.write(dst, raw, n, ch, frame_time=1 / 30.0)
        return fn
    clips = dict(reload_ads_loaded=clip('coop_c96_reload_ads_loaded.skc', N, False), reload_ads_empty=clip('coop_c96_reload_ads_empty.skc', N, True),
                 reload_empty=clip('coop_c96_reload_empty.skc', N, True, hip=True), idle_empty=clip('coop_c96_idle_empty.skc', 1, True, const=1.0),
                 reload=clip('coop_c96_reload_hip.skc', N, False, hip=True))
    nt = []
    for stem, tx in p12.tiks_for(dict(dir=DIR, clip=g['clip'])) + p12.tiks_for(dict(dir=DIR, clip='coop_c96_reload_hip.skc')):
        nl = '\r\n' if '\r\n' in tx else '\n'
        s = p12.patch_tik(stem, tx.replace('\r\n', '\n'), clips, 'shown by the cgame instead of `reload` (aimed; hip when empty): the bolt works', sound_cut=False)
        s = CC.tik_lines(s)
        p12.depth_ok(s, stem)
        p12.write_tik(root, stem, s, nl)
        nt.append(stem)
    print('c96 clips', sorted(clips), '| tiks', len(nt), nt)


TR = dict(dir='models/weapons/coop_c96trench', tik='mauser_c96_c96trench', hip='c96_reload.skc', rack='c96fire.skc')        # the bolt's travel in the gun's OWN fire clip (4.93 raw = 2.56 u); its rack clip's 9.03 raw brought the bolt block 4.7 u toward the eye in the dry aim (run pa30)


def build_trench(root):
    """Trench C96 (model variant, its own mesh): the mesh HAS a bolt bone (`Bone2`, surface Cylinder1) that its own
    clips move - mauser_secondary.skc racks it 9.03 raw units. The same states as the base gun, written on that bone:
    hold-open, the aimed clips, the emptied hip clip, and the hip `reload` (SERVER row: the released c96_reload.skc is
    84 frames x 0.032 s and racks the bolt at 65-73, after the hands are done; same length, the bolt now moves where
    the released hip hands work it). White patch at the rear: textures/coop_c96trench/stuff2.jpg has a white surround
    (an alpha cut-out that never was one) around the hammer's ring - filled with the ring's own steel."""
    R = gunskc.R
    DIR = TR['dir']
    rack = R.load(DIR + '/' + TR['rack'])
    Vr = np.array(rack.values); ci = rack.names.index('Bone2 pos')
    p0 = Vr[0, ci].copy()
    pb = Vr[int(np.argmax(np.abs(Vr[:, ci, 0] - p0[0]))), ci].copy()        # the bolt at its rearmost in the gun's own rack
    raw = p12.rd(DIR + '/' + TR['hip'])
    hipc = R.load(DIR + '/' + TR['hip'])
    ft_hip, n_hip = float(hipc.frameTime), int(hipc.numFrames)
    print('trench bolt: Bone2 pos closed %s back %s | released hip row %d frames x %.4f s' % (np.round(p0[:3], 2), np.round(pb[:3], 2), n_hip, ft_hip))

    def clip(fn, n, empty, hip=False, const=None, ft=1 / 30.0):
        k = ft * 30.0                                    # clip frame -> 30 per second frame
        st = (lambda f: const) if const is not None else (lambda f: bolt_state(f * k, empty, hip))
        ch = {'Bone2 pos': [[float(x) for x in (p0 + (pb - p0) * st(f))] for f in range(n)]}
        gunskc.write(os.path.join(root, (DIR + '/' + fn).replace('/', os.sep)), raw, n, ch, frame_time=ft)
        return fn
    clips = dict(reload_ads_loaded=clip('coop_c96t_reload_ads_loaded.skc', N, False), reload_ads_empty=clip('coop_c96t_reload_ads_empty.skc', N, True),
                 reload_empty=clip('coop_c96t_reload_empty.skc', N, True, hip=True), idle_empty=clip('coop_c96t_idle_empty.skc', 1, True, const=1.0),
                 reload=clip('coop_c96t_reload_hip.skc', n_hip, False, hip=True, ft=ft_hip))
    tx = p12.rd('models/weapons/%s.tik' % TR['tik']).decode('latin-1')
    nl = '\r\n' if '\r\n' in tx else '\n'
    s = p12.patch_tik(TR['tik'], tx.replace('\r\n', '\n'), clips, 'shown by the cgame instead of `reload` (aimed; hip when empty): the bolt works', sound_cut=False)
    p12.depth_ok(s, TR['tik'])
    p12.write_tik(root, TR['tik'], s, nl)
    # the white patch
    from PIL import Image
    src = os.path.join(p12.MOD, 'textures', 'coop_c96trench', 'stuff2.jpg')
    im = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
    white = (im.min(2) > 150)
    grown = white.copy()
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            grown |= np.roll(np.roll(white, dy, axis=0), dx, axis=1)
    ys, xs = np.nonzero(white)
    box = im[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    inner = box[~grown[ys.min():ys.max() + 1, xs.min():xs.max() + 1]]          # the ring's own texels inside the white surround
    col = np.median(inner, axis=0)
    rng = np.random.RandomState(96)
    out = im.copy()
    out[grown] = np.clip(col + rng.normal(0, 2.0, (int(grown.sum()), 1)), 0, 255)
    d = os.path.join(root, 'textures', 'coop_c96trench'); os.makedirs(d, exist_ok=True)
    Image.fromarray(out.astype(np.uint8)).save(os.path.join(d, 'stuff2.jpg'), quality=93)
    print('trench clips', sorted(clips), '| tik', TR['tik'], '| stuff2.jpg: %d white texels (%.1f %%) filled with %s' % (int(white.sum()), 100.0 * white.mean(), np.round(col)))


def carry_clip(sk):
    """tag_weapon_left rigid to the support hand: = tag_weapon_right at the server's hand-over frames (41 in, 47 out)"""
    R = gunskc.R
    cm = {n: i for i, n in enumerate(sk.names)}
    V = np.array(sk.values, dtype=np.float64)

    def rel(f):
        W = R.evaluate(R.pose_dict(sk, f))
        return W['tag_weapon_right'] @ R.inv(W['Bip01 L Hand'])
    sk.V = V
    Cin, Cout = rel(SRV['gun']), rel(SRV['take'])
    for f in range(sk.numFrames):
        C = Cin if f < SRV['fill'] else Cout
        V[f, cm['tag_weapon_left rot']] = R.rows_to_quat(C[0:3, 0:3])
        V[f, cm['tag_weapon_left pos']] = np.array([C[3, 0], C[3, 1], C[3, 2], 0.0])
    sk.V = V
    sk.values = [[[float(np.float32(x)) for x in V[f, c]] for c in range(sk.numChannels)] for f in range(sk.numFrames)]
    err = []
    for f in (SRV['gun'], SRV['take']):
        W = R.evaluate(R.pose_dict(sk, f))
        err.append(float(np.abs(W['tag_weapon_left'] - W['tag_weapon_right']).max()))
    print('   clip tag: left = right at %d / %d, max matrix difference %.5f / %.5f' % (SRV['gun'], SRV['take'], err[0], err[1]))
    assert max(err) < 1e-3, err


def bake(root):
    import revbake as RB
    import welrod as W
    H = RB.H; R = RB.R
    T0 = pistolgun.rack_rel('histandard').copy()
    T0[3, 0:3] += np.array(GRASP_D) / R.S
    for ax, deg in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), HROT):       # the hand on the clip turned about the gun's axes (about its own origin)
        if deg:
            T0[0:3, 0:3] = T0[0:3, 0:3] @ BF.rot_rows(ax, deg)
    Tb =pistolgun.rack_rel('histandard').copy()
    Tb[3, 0:3] += np.array((0.3, 0.0, -0.3)) / R.S              # the same grasp over the bolt's rear end
    n = N - 1
    z = (0.0,) * 5
    AIMK = dict(aim=1, fing='aim')
    for empty in ((True,) if os.environ.get('C96_ONLY') == 'empty' else (False, True)):
        a0, a1 = K['off']; p0, p1 = K['pouch'] if empty else K['pouch_l']; s0, s1 = K['press']; o0, o1 = K['out']; g0, g1 = K['on']
        ev = [(s0, 'round_seat', 0.45), (s1 - 1, 'round_seat', 0.3), (o1 - 1, 'slide_fwd', 0.9), (g1 - 4, 'hand_on')]
        if not empty:
            ev.append((K['draw'][0], 'slide_back', 0.8))
        ph = gunphys.simulate(n + 1, 1 / 30.0, 'pistol', support=[(0, 1), (a0, 1), (a1, 0), (g0, 0), (g1, 1)], events=ev,
                              pose=([(0, z), (DOWN_E[0], z), (DOWN_E[1], LOW1), (DOWN_E[2], LOW)] if empty else [(0, z), (K['down'][0], z), (K['down'][1], LOW1), (DOWN2[0], LOW1), (DOWN2[1], LOW)]) + [(K['up'][0], LOW), (K['up'][1], z), (n, z)])
        dn = DOWN_E[1:] if empty else DOWN2
        yk = [(0, 0.0), (dn[0], 0.0), (dn[1], YAW), (K['up'][0], YAW), (K['up'][1] - 3, 0.0), (n, 0.0)]      # turned only while it is low

        def yaw_at(f):
            for (f0, v0), (f1, v1) in zip(yk, yk[1:]):
                if f0 <= f <= f1:
                    return v0 + (v1 - v0) * p12.smooth((f - f0) / float(max(1, f1 - f0)))
            return 0.0
        ph['dip'] = {f: tuple(v)[:5] + (yaw_at(f),) for f, v in ph['dip'].items()}
        lp = {0: AIMK, a0: AIMK}
        if empty:
            lp[a0 + 3] = dict(aim=1, cam_add=(-0.4, 1.3, -1.2), fing=('mix', 40, 0.5))
            lp[a1 + 3] = dict(aim=1, cam_add=(-1.5, 3.5, -6.5), fing=GRASP_F)
        else:                                    # rounds left: the bolt is drawn back first (the grasp over its rear end)
            d0, d1 = K['draw']
            lp[d0 - 2] = dict(relT=Tb, cam_add=(0.0, 2.2, -1.4), fing='aim')
            lp[d0] = dict(relT=Tb, fing=GRASP_F)
            lp[d1] = dict(relT=Tb, gun_add=(-BOLT, 0.0, 0.0), fing=GRASP_F)
            lp[d1 + 2] = dict(relT=Tb, gun_add=(-BOLT, 0.0, 0.0), cam_add=(0.0, 1.6, -1.0), fing=GRASP_F)
        lp[p0] = dict(cam=POUCH, rot='aim', fing=GRASP_F); lp[p1] = dict(cam=POUCH, rot='aim', fing=GRASP_F)
        hx, hy, hz = HOLD
        at = dict(relT=T0, gun_add=(hx, hy, hz), fing=GRASP_F)
        dn_ = dict(relT=T0, gun_add=(hx, hy, hz + HTRAV), fing=GRASP_F)
        lp[K['over']] = dict(relT=T0, gun_add=(hx - 0.4, hy, hz - 2.6), fing=GRASP_F)           # above the action with the clip in the hand
        lp[K['at']] = at; lp[s0] = at                                                           # the clip stands in the guides (the server moves it to the gun at 41)
        lp[s1] = dn_; lp[o0] = dn_                                                              # the thumb has run the rounds down; the hand takes the empty clip (47)
        lp[o1] = dict(relT=T0, gun_add=(hx - 0.3, hy, hz + HTRAV - 2.4), fing=GRASP_F)          # pulled out of the guides
        lp[K['toss']] = dict(cam=TOSS, rot='aim', fing=GRASP_F)                                 # dropped to the left, below the frame (the server removes it at 56)
        lp[K['toss'] + 2] = dict(cam=TOSS, rot='aim', fing=('clip', 'viewmodel/pistol/fire_hp.skc', 0))
        for f in range(g1, n + 1):
            lp[f] = AIMK
        kw = dict(gun='mauser_c96', charge=AIM, fixed_right=True, dip=ph['dip'], left_path=lp, weight=dict(on=False), handover=False,
                  tag_map={0: 40, n: 40}, elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.0, -1.0)})
        rc = H.auto_recipe('p38_reload', **kw)
        H.RECIPES['p38_reload'] = rc
        sk, _ = H.bake('p38_reload', RB.CTL)
        carry_clip(sk)
        W.save(root, sk, VDIR + '/coop_c96_reload_%sads.skc' % ('empty_' if empty else ''), ph)
    H.RECIPES.pop('p38_reload', None)


def rows():
    key = 'mauser_c96'
    L = ['\t//===================== HZM coop Mauser C96 (+ Trench C96): two-handed aim, aimed reload on the stripper-clip prop =====================',
         '\t// the HIP rows stay the released ones: coopr_%s_reload = viewmodel/coop_reload/c96_reload.skc is declared in anims_shared.txt.' % key,
         '\t// _reload_empty repeats that clip only so that the cgame finds _reload_empty_ads for a reload that starts on an empty gun.',
         '\tcoopr_%s_charge\t\t\t%s\t\tcrossblend 0.3' % (key, AIM),
         '\tcoopr_%s_reload_ads\t\t%s/coop_c96_reload_ads.skc\t\tcrossblend 0.1' % (key, VDIR),
         '\tcoopr_%s_reload_empty\t\tviewmodel/coop_reload/c96_reload.skc\t\tcrossblend 0.3' % key,
         '\tcoopr_%s_reload_empty_ads\t%s/coop_c96_reload_empty_ads.skc\t\tcrossblend 0.1' % (key, VDIR)]
    open(os.path.join(HERE, 'rows_p12_c96.txt'), 'w', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    root = sys.argv[1]
    what = sys.argv[2].split(',') if len(sys.argv) > 2 else ['reload', 'gun']
    if 'reload' in what:
        bake(root)
    if 'gun' in what:
        build_gun(root)
        build_trench(root)
    rows()

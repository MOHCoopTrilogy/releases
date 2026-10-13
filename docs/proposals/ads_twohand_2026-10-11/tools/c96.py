"""Mauser C96: its OWN aimed reload - charged from the TOP with a stripper clip, the gun kept up (list item D).

The C96 has no detachable magazine. On the P38 rows it borrowed, the aimed reload took the gun right out of the aim
(run pa6: 7.2 % of the centre box, 4.5 deg) to push a P38 magazine into a grip that has no well. New, both hands clips
on the P38 two-handed aim pose:
  the gun comes straight DOWN under the centre box, muzzle a little down (the eye looks onto the top of the action -
  the clip guides are on the sight line, they cannot be worked on the sights); the support hand leaves the grip, goes
  to the pouch (below the frame), comes back over the top of the action with the clip under the palm, the thumb
  strips the rounds down (the seat click of the sound), the hand lifts the empty clip out - the bolt runs forward -
  and returns to the grip; the gun comes straight back up. The server's P38 magazine prop is parked out of view.
Gun (mesh coop_c96: every vertex on bone `origin`): bonefit.split puts the bolt's rear end (Cylinder1) on `coop_slide` and the
hammer (Tube3) on `coop_tog`.
    idle_empty          bolt end back 0.42 u, hammer cocked (pressed down by the bolt)
    reload_ads_empty    bolt back from frame 0, forward as the clip leaves
    reload_ads_loaded   rounds left: the support hand's first move draws the bolt back, then the same
    reload_empty        hip, emptied: back until the retail clip's seat
WEAK (told to the user): no stripper-clip MESH exists - the clip is under the palm, never seen; the hammer rises again
with the closing bolt (the idle clip has it down; a cocked idle would need the fire clip redone).

    cd stage; python ../c96.py . [gun,reload]       IRONSIGHT_EXTRA_PAKS = _ov_wip.pk3;_bases.pk3
"""
import sys, os, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bonefit as BF
import p12, pistolgun, gunskc, gunphys
DIR = 'models/weapons/coop_c96'
PARTS = {'coop_slide': [('Cylinder1', 86, 0.72)], 'coop_tog': [('Tube3', 168, -0.04)]}
AIM = 'viewmodel/pistol/p38_ads2h.skc'
VDIR = 'viewmodel/pistol'
N = p12.N
BOLT = 0.42                                  # u the bolt's rear end comes back: the mesh has only that end as a separate part (0.6 u long) - further and it hangs in the air behind the gun
HAM = 60.0                                   # deg the hammer lies back when the bolt is over it
HPIV = (-0.30, -1.75)                        # hammer pivot, gun x / z
# frames: off = hand leaves the grip; draw = (loaded only) the bolt drawn back; in = hand over the action with the clip;
# press = the rounds stripped down; out = the clip lifted out (the bolt goes forward over its last two frames); on = grip
K = dict(off=(3, 8), draw=(10, 13), pouch=(17, 23), over=28, at=31, press=(33, 37), out=(49, 52), on=(56, 64), down=(2, 8), up=(57, 68))
DOWN_E = (17, 25)        # emptied gun: it stays in the aim (one-handed) while the hand fetches the clip, and comes down as the hand comes up
LOW = tuple(float(x) for x in os.environ.get('C96_LOW', '3.4,4,11,0,0.3').split(','))        # drop u, roll, pitch (muzzle down), side, back
GRASP_D = tuple(float(x) for x in os.environ.get('C96_GRASP', '3.6,0.0,-0.9').split(','))     # the Hi-Standard overhand grasp moved over the clip guides
GRASP_F = ('clip', 'viewmodel/pistol/fire_hp.skc', 10)
POUCH = (5.0, 9.0, -15.0)


def bolt_state(f, empty, hip=False):
    """0..1: how far back the bolt is"""
    if hip:
        return (1.0 if f <= N - 16 else max(0.0, 1.0 - ((f - (N - 16)) / 2.0) ** 2)) if empty else 0.0
    o0, o1 = K['out']
    close = 1.0 if f <= o1 - 2 else max(0.0, 1.0 - ((f - (o1 - 2)) / 2.0) ** 2)
    if empty:
        return close
    d0, d1 = K['draw']
    return min(p12.smooth((f - d0) / float(d1 - d0)), close)


def build_gun(root):
    BF.split('models/weapons/mauser_c96.tik', DIR + '/c96.skd', PARTS, os.path.join(root, (DIR + '/c96.skd').replace('/', os.sep)))
    A, o = BF.fit('models/weapons/mauser_c96.tik', 'origin')
    raw = p12.rd(DIR + '/P38_reload.skc')

    def clip(fn, n, empty, hip=False, const=None):
        bp, bq, hp, hq = [], [], [], []
        for f in range(n):
            u = const if const is not None else bolt_state(f, empty, hip)
            p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (-BOLT * u, 0.0, 0.0))
            bp.append(p); bq.append(q)
            p, q = BF.chan(A, o, BF.rot_rows((0, 1, 0), HAM * min(1.0, u * 1.6)), (HPIV[0], 0.0, HPIV[1]))
            hp.append(p); hq.append(q)
        seat = gunskc.R.load(DIR + '/c96.skc')
        mg = [[float(x) for x in seat.V[0, seat.names.index('p38clip pos')][:3]] + [0.0]] * n     # no magazine leaves this gun
        dst = os.path.join(root, (DIR + '/' + fn).replace('/', os.sep))
        gunskc.write(dst, raw, n, {'coop_slide pos': bp, 'coop_slide rot': bq, 'coop_tog pos': hp, 'coop_tog rot': hq, 'p38clip pos': mg}, frame_time=1 / 30.0)
        return fn
    clips = dict(reload_ads_loaded=clip('coop_c96_reload_ads_loaded.skc', N, False), reload_ads_empty=clip('coop_c96_reload_ads_empty.skc', N, True),
                 reload_empty=clip('coop_c96_reload_empty.skc', N, True, hip=True), idle_empty=clip('coop_c96_idle_empty.skc', 1, True, const=1.0))
    nt = []
    for stem, tx in p12.tiks_for(dict(dir=DIR, clip='P38_reload.skc')):
        nl = '\r\n' if '\r\n' in tx else '\n'
        s = p12.patch_tik(stem, tx.replace('\r\n', '\n'), clips, 'shown by the cgame instead of `reload` (aimed; hip when empty): the bolt works', sound_cut=False)
        p12.depth_ok(s, stem)
        p12.write_tik(root, stem, s, nl)
        nt.append(stem)
    print('c96 clips', sorted(clips), '| tiks', len(nt), nt[:3])


def bake(root):
    import revbake as RB
    import welrod as W
    H = RB.H; R = RB.R
    T0 = pistolgun.rack_rel('histandard').copy()
    T0[3, 0:3] += np.array(GRASP_D) / R.S
    Tb = pistolgun.rack_rel('histandard').copy()
    Tb[3, 0:3] += np.array((0.3, 0.0, -0.3)) / R.S              # the same grasp over the bolt's rear end
    n = N - 1
    z = (0.0,) * 5
    AIMK = dict(aim=1, fing='aim')
    for empty in (False, True):
        a0, a1 = K['off']; p0, p1 = K['pouch']; s0, s1 = K['press']; o0, o1 = K['out']; g0, g1 = K['on']
        ev = [(s0, 'round_seat', 0.45), (s1 - 1, 'round_seat', 0.3), (o1 - 1, 'slide_fwd', 0.9), (g1 - 4, 'hand_on')]
        if not empty:
            ev.append((K['draw'][0], 'slide_back', 0.8))
        ph = gunphys.simulate(n + 1, 1 / 30.0, 'pistol', support=[(0, 1), (a0, 1), (a1, 0), (g0, 0), (g1, 1)], events=ev,
                              pose=[(0, z), ((DOWN_E if empty else K['down'])[0], z), ((DOWN_E if empty else K['down'])[1], LOW), (K['up'][0], LOW), (K['up'][1], z), (n, z)])
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
        lp[K['over']] = dict(relT=T0, gun_add=(0.0, 0.0, -1.3), cam_add=(0.0, 1.0, 0.0), fing=GRASP_F)     # over the action, clip under the palm
        lp[K['at']] = dict(relT=T0, fing=GRASP_F)                                                         # clip in the guides
        lp[s0] = dict(relT=T0, fing=GRASP_F)
        lp[s1] = dict(relT=T0, gun_add=(0.0, 0.0, 0.7), fing=GRASP_F)                                     # the rounds stripped down
        lp[o0] = dict(relT=T0, gun_add=(0.0, 0.0, 0.7), fing=GRASP_F)
        lp[o1] = dict(relT=T0, gun_add=(-0.3, 0.0, -0.9), fing=GRASP_F)                                   # the empty clip lifted out
        lp[o1 + 2] = dict(relT=T0, gun_add=(-0.3, 0.0, -0.9), cam_add=(0.0, 2.4, -1.6), fing=('clip', 'viewmodel/pistol/fire_hp.skc', 0))
        for f in range(g1, n + 1):
            lp[f] = AIMK
        kw = dict(gun='mauser_c96', charge=AIM, fixed_right=True, dip=ph['dip'], left_path=lp, weight=dict(on=False), handover=False,
                  tag_park=dict(tag='tag_weapon_left', ranges=[(0, n)]), tag_map={0: 40, n: 40},
                  elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.0, -1.0)})
        rc = H.auto_recipe('p38_reload', **kw)
        H.RECIPES['p38_reload'] = rc
        sk, _ = H.bake('p38_reload', RB.CTL)
        W.save(root, sk, VDIR + '/coop_c96_reload_%sads.skc' % ('empty_' if empty else ''), ph)
    H.RECIPES.pop('p38_reload', None)


def rows():
    key = 'mauser_c96'
    L = ['\t//===================== HZM coop Mauser C96: its own aimed reload (stripper clip from the top, gun kept up under the centre box) =====================',
         '\tcoopr_%s_reload\t\t\tviewmodel/pistol/reload_p38.skc\t\t\tcrossblend 0.3' % key,
         '\tcoopr_%s_reload_ads\t\t%s/coop_c96_reload_ads.skc\t\tcrossblend 0.1' % (key, VDIR),
         '\tcoopr_%s_reload_empty\t\tviewmodel/pistol/reload_p38.skc\t\t\tcrossblend 0.3' % key,
         '\tcoopr_%s_reload_empty_ads\t%s/coop_c96_reload_empty_ads.skc\t\tcrossblend 0.1' % (key, VDIR)]
    open(os.path.join(HERE, 'rows_p12_c96.txt'), 'w', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    root = sys.argv[1]
    what = sys.argv[2].split(',') if len(sys.argv) > 2 else ['gun', 'reload']
    if 'gun' in what:
        build_gun(root)
    if 'reload' in what:
        bake(root)
    rows()

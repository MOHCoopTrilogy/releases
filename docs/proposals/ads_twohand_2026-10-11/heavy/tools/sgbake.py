r"""Shotgun (M1897) AIMED reload to the three rules - heavy lane. Tube magazine, loading gate under the receiver:
start -> one shell per loop -> end, and the pump is worked ONLY when the gun was empty (user 2026-10-12).

The retail hip technique, kept: the firing hand keeps the gun, the LEFT hand leaves the forend, goes down to the pouch,
comes up under the receiver and thumbs a shell into the gate and forward into the tube; at the end it goes back to the
forend (and racks it). Aimed, the gun comes DOWN out of the aim aligned (inside the aim's own silhouette), just under
the centre box, and rolls its top away from the feeding hand so the left flank and the gate edge turn to the eye; the
hand's place at the gate is the retail hand-to-gun relation (`rel`), riding the keyed gun. The pistol lane's revbake.py
is the library (work_T, curl) - the shared hold_bake does the solving.

    cd heavy/assets; python ../tools/sgbake.py [--only start|single|end|endl] [--hipend]
writes models/human/animation/viewmodel/shotgun/
    shotgun_reload_ads.skc            (shipped path - replaced)   start, 23 frames
    shotgun_reload_single_ads.skc     (shipped path - replaced)   one shell, 20 frames, seamless loop
    shotgun_reload_end_ads.skc        (shipped path - replaced)   end of a gun that WAS EMPTY: back up, pump (retail timing)
    shotgun_reload_end_loaded_ads.skc                             end with a round in the chamber: back up, no pump
    shotgun_reload_end_break_ads.skc                              break-off with a round chambered: 11 frames back into the aim
    coop_shotgun_reload_end_loaded.skc   (--hipend)               the retail hip end with the pump cut out (retime warp)
    coop_shotgun_reload_end_break.skc    (--hipend)               hip break-off, 11 frames; coop_tps_reload_break.skc = its third-person row
and the gun's still clip models/weapons/shotgun/coop_shotgun_still32.skc (tik rows reload_end_loaded / _ads).
"""
import sys, os, json, argparse, hashlib, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
sys.path.insert(0, hv.SHARED)
import revbake as RB
import gunphys

E = lambda k, d: os.environ.get(k, d)
F3 = lambda k, d: tuple(float(x) for x in E(k, d).split(','))
AIM = 'viewmodel/idle_shotgun00.skc'            # the shotgun_charge row = the aim pose
ANIM = 'viewmodel/shotgun/'
SHELL = 'models/ammo/shotgunshell.tik'
# work_T poses (drop u, roll deg + = top to the right, pitch deg + = muzzle down, left u, yaw) about a point 12 u down
# the view axis. LOW: the gun pitched down about the butt - the muzzle goes under the centre box, the receiver stays in
# the frame (a straight drop of the same size takes the receiver, 4-14 u from the eye, out of the bottom of the frame:
# first bake, nothing of the feed was in view). WORK: that, rolled over so the gate side turns to the eye.
LOWD = F3('SG_LOW', '2.0,0,4.6,0,0')
WORK = F3('SG_WORK', '1.6,20,4.6,-0.4,0')
FWD = float(E('SG_FWD', '3.0'))                 # the work pose pushed out along the view (u): the feed is further from the eye
BUTT = float(E('SG_BUTT', '-12.0'))             # the butt's place on the view axis (behind the eye): the physics pivot
POUCH = F3('SG_POUCH', '5.0,9.0,-10.0')        # camera frame (fwd, left, up): the belt, under the frame
ELB = float(E('SG_ELB', '3.0'))
ATTACH, SEATF, PUSHF = 0, 11, 13                # loop frames: the server attaches the shell (`first`) / it is at the gate / it is in
# [fifth agent 2026-10-13] the loop is RE-PHASED: it starts and ends with the hand at the pouch (was: under the gun), the
# shell is in the hand from the loop's first frame and is carried up into view at once - in view f3-f10 (0.25 s; was
# two GIF frames), and the start clip's hand is SEEN leaving the forend (f3-f18; was at the pouch by f13 = 0.6 s of
# nothing). The carrying hand is a closed pinch (PIN: thumb + two fingers on the shell, ring and little finger shut).
PIN = [F3('SG_PIN0', '24,26,20'), F3('SG_PIN12', '18,22,12'), F3('SG_PIN34', '52,64,40')]   # extra flexion (knuckle, middle, tip) deg: thumb / fore + middle / ring + little


def pinch(keys):
    """finger_add of the carrying hand: (frame, weight) keys x the PIN angles, on top of the forend grip's curl"""
    out = {}
    for fi in range(5):
        deg = PIN[0] if fi == 0 else PIN[1] if fi in (1, 2) else PIN[2]
        for j, sfx in enumerate(('', '1', '2')):
            out['Bip01 L Finger%d%s rot' % (fi, sfx)] = [(k, w * deg[j]) for k, w in keys]
    return out


HIPBRK = 'viewmodel/shotgun/coop_shotgun_reload_end_break.skc'   # --hipend writes it (11 frames); the aimed break row is baked on it
# M1897 3.6 kg; the support hand off: the muzzle sags, a slow one-handed hold
gunphys.CLASSES['shotgun'] = dict(m=3.6, f2=2.9, f1=1.9, z=0.54, sag=(0.30, 0.0, 2.2, 0.05, 0.0), magw=0.0,
                                  tr=(0.030, 0.16, 0.18, 0.022, 0.010), tr2=0.25)
gunphys.ACTIONS.update({
    # (drop, roll, pitch, side, back) velocity change for mass 1, pulse length in frames (heavybake's convention)
    'sg_shell_gate': ((-9.0, 16.0, 16.0, -3.0, 2.0), 2.0),     # the shell is pressed UP against the carrier, from the left below
    'sg_shell_home': ((-3.0, 6.0, 26.0, -2.0, -16.0), 2.0),    # and thumbed FORWARD up the tube past the stop: the gun goes with it
    'sg_pump_back':  ((3.0, -8.0, -34.0, 2.0, 60.0), 2.0),     # the forend hauled back hard: into the shoulder, muzzle up
    'sg_pump_fwd':   ((2.0, 6.0, 52.0, -1.0, -55.0), 1.5),     # and slammed forward: thrown forward, muzzle dips
})


def sets():
    Tlo = RB.work_T(AIM, 'shotgun', LOWD)
    Tw = RB.work_T(AIM, 'shotgun', WORK)
    Tw[3, 0] += FWD
    common = dict(gun='shotgun', fixed_right=True, charge=AIM,
                  elbow_vec={'L': F3('SG_ELBV', '0,0.5,-1.0')})
    PO = dict(cam=POUCH, rot='aim', fing='aim')
    LT = dict(pinch=F3('SG_PINCH', '8.6,2.4,-2.6'), hold_vec=F3('SG_HOLDV', '1.2,0.6,-1.4'))
    if E('SG_AXES', '1') == '1':                 # the shell lies along the bore, as it goes up the tube
        LT['axes'] = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]     # brass to the rear (the other way round the open mouth faces the eye)
    FG = E('SG_FING', 'aim')                     # fingers while carrying: the forend grip's curl (closed on the shell)
    FG = FG if FG == 'aim' else ('mix', 9, float(FG))
    # the SHOW beat: with the gun on the shoulder the gate cannot be seen (it is under the receiver), so the hand
    # brings the shell up beside the receiver's left flank first - in view, under the box - and then rolls it under
    low = F3('SG_APP', '-0.5,3.8,3.2')           # camera frame (fwd, left, up) from the hand's place at the gate
    # retail fill clip: at the gate f6-9, pushed forward f10-11, withdrawn under the gun f13-19
    REST = dict(rel=13, cam_add=F3('SG_REST', '0,1.0,-1.0'))
    loop = {0: PO, 1: PO, 5: dict(rel=9, cam_add=low, fing=FG), 8: dict(rel=9, cam_add=tuple(0.8 * x for x in low), fing=FG),
            10: dict(rel=8, cam_add=tuple(0.3 * x for x in low), fing=FG), SEATF: dict(rel=9, fing=FG), 12: dict(rel=9, fing=FG),
            PUSHF: dict(rel=10, fing=FG), 14: dict(rel=11, fing=FG), 19: PO}
    ga2 = lambda klo, kw: dict(gun_abs=[dict(T=Tlo, keys=klo), dict(T=Tw, keys=kw)])
    rows = {
        # START: the hand lets go, the gun comes down aligned (0-7) and turns (5-14); the hand is at the pouch by 14
        'start': ('shotgun_reload', 'shotgun_reload_ads.skc',
                  dict(left_path={0: dict(aim=1), 3: dict(aim=1), 19: PO, 22: PO}, elbow_down={'L': [(0, 0.0), (8, ELB), (22, ELB)]},
                       finger_add=pinch([(0, 0.0), (3, 0.0), (10, 0.8), (19, 1.0), (22, 1.0)]),
                       **ga2({0: 0.0, 7: 1.0, 22: 1.0}, {0: 0.0, 6: 0.0, 16: 1.0, 22: 1.0}))),
        # ONE SHELL: under the gun (0) -> pouch, out of frame (4-7, the prop appears there) -> up to the gate from the
        # left below (10-13) -> pressed in, thumbed forward (15-16) -> off
        'single': ('shotgun_reload_single', 'shotgun_reload_single_ads.skc',
                   dict(left_path=loop, ltag=LT, elbow_down={'L': [(0, ELB), (19, ELB)]}, finger_add=pinch([(0, 1.0), (PUSHF, 1.0), (16, 0.5), (19, 1.0)]),
                        **ga2({0: 1.0, 19: 1.0}, {0: 1.0, 19: 1.0}))),
        # END, the gun WAS EMPTY: the hand goes to the forend while the gun turns upright under the box (0-9), racks it
        # there with the gun's own slide (retail timing: back 10-11, forward 20-21), then the gun rises into the aim
        'end': ('shotgun_reload_end', 'shotgun_reload_end_ads.skc',
                dict(left_path={0: PO, 6: dict(rel=6), 9: dict(rel=9), 10: dict(rel=10), 11: dict(rel=11), 19: dict(rel=19),
                                20: dict(rel=20), 21: dict(rel=21), 23: dict(aim=1), 31: dict(aim=1)},
                     elbow_down={'L': [(0, ELB), (5, ELB), (9, 0.0), (31, 0.0)]}, finger_add=pinch([(0, 1.0), (4, 0.0), (31, 0.0)]),
                     **ga2({0: 1.0, 21: 1.0, 29: 0.0, 31: 0.0}, {0: 1.0, 2: 1.0, 9: 0.0, 31: 0.0}))),
        # END, a round in the chamber: no pump - the hand goes back to the forend, the gun turns upright and rises
        'endl': ('shotgun_reload_end', 'shotgun_reload_end_loaded_ads.skc',
                 dict(left_path={0: PO, 9: dict(rel=6), 12: dict(aim=1), 31: dict(aim=1)},
                      elbow_down={'L': [(0, ELB), (6, ELB), (11, 0.0), (31, 0.0)]}, finger_add=pinch([(0, 1.0), (5, 0.0), (31, 0.0)]),
                      **ga2({0: 1.0, 11: 1.0, 22: 0.0, 31: 0.0}, {0: 1.0, 3: 1.0, 12: 0.0, 31: 0.0}))),
        # BREAK-OFF with a round chambered (the trigger during the reload): 11 frames - the gun turns upright and comes
        # up at once, the hand goes straight to the forend; the server row shotgun_reload_break is as long, then the shot
        'brk': ('shotgun_reload_end', 'shotgun_reload_end_break_ads.skc',
                dict(hip=HIPBRK, left_path={0: dict(rel=0), 7: dict(aim=1), 10: dict(aim=1)},
                     elbow_down={'L': [(0, ELB), (3, ELB), (7, 0.0), (10, 0.0)]},
                     **ga2({0: 1.0, 3: 1.0, 9: 0.0, 10: 0.0}, {0: 1.0, 1: 1.0, 6: 0.0, 10: 0.0}))),
    }
    return common, rows


def physics(part, n):
    S = float(E('SG_SEAT', '3.0'))
    if part == 'start':                  # support leaves at 2: the muzzle sags while the firing hand brings the gun down
        return gunphys.simulate(n, 1 / 30.0, 'shotgun', [(0, 1), (3, 1), (7, 0.0), (n - 1, 0.0)], [], fade=0)
    if part == 'single':
        return gunphys.simulate(n, 1 / 30.0, 'shotgun', [(0, 0.0), (SEATF - 1, 0.0), (SEATF, 0.3), (PUSHF + 1, 0.3), (n - 1, 0.0)],
                                [(SEATF, 'sg_shell_gate', S), (PUSHF, 'sg_shell_home', S)], loop=True)
    if part == 'end':
        return gunphys.simulate(n, 1 / 30.0, 'shotgun', [(0, 0.0), (5, 0.0), (8, 1.0), (n - 1, 1.0)],
                                [(6, 'hand_on'), (10, 'sg_pump_back'), (20, 'sg_pump_fwd')])
    if part == 'brk':
        return gunphys.simulate(n, 1 / 30.0, 'shotgun', [(0, 0.0), (4, 0.0), (7, 1.0), (n - 1, 1.0)], [(6, 'hand_on')])
    return gunphys.simulate(n, 1 / 30.0, 'shotgun', [(0, 0.0), (8, 0.0), (11, 1.0), (n - 1, 1.0)], [(10, 'hand_on')])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only'); ap.add_argument('--hipend', action='store_true'); ap.add_argument('--root', default='.')
    a = ap.parse_args()
    common, rows = sets()
    if a.hipend:
        hipend()
    for part, (row, outn, rc0) in rows.items():
        if a.only and part not in a.only.split(','):
            continue
        kw = dict(common); kw.update(rc0)
        rc = H.auto_recipe(row, **kw)
        n_ = R.load(R.ANIM + rc['hip']).numFrames
        ph = physics(part, n_)
        rc['dip'] = ph['dip']; rc['dip_after'] = True; rc['dip_pivot'] = BUTT
        H.RECIPES[row] = rc
        sk, rep = H.bake(row, CTL)
        b = R.skc_io.write(sk)
        dst = os.path.join(a.root, 'models', 'human', 'animation', (ANIM + outn).replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(b)
        print('%-6s %s -> %s %d frames %s | %s' % (part, row, outn, sk.numFrames, hashlib.md5(b).hexdigest()[:8], ph['report'][:90]))


def hipend():
    """the clips that are cut from retail ones (run BEFORE the bakes: the aimed break row is baked on the hip break clip)"""
    rt = os.path.join(hv.SHARED, 'retime.py')

    def cut(src, dst, *args):
        r = subprocess.run([sys.executable, rt, src, hv.staged(dst)] + list(args), capture_output=True, text=True)
        print('%s: %s' % (dst.split('/')[-1], (r.stdout + r.stderr).strip()[-140:]))
    A = 'models/human/animation/' + ANIM
    # the retail hip end: hand to the forend 0-9, pump 10-21, idle 22-31 -> the pump cut out, the rest eased over it
    cut(A + 'reload_end.skc', A + 'coop_shotgun_reload_end_loaded.skc', 'warp', '0:0,9:9,14:22,31:31')
    cut('models/weapons/shotgun/shotgun_fire.skc', 'models/weapons/shotgun/coop_shotgun_still32.skc', 'warp', '0:0,31:0')
    # BREAK-OFF with a round chambered, 11 frames (0.37 s): hip hands = the retail end's hand to the forend and the
    # settle, no pump; third person (the server's row shotgun_reload_break - its length IS the time to the owed shot)
    cut(A + 'reload_end.skc', A + 'coop_shotgun_reload_end_break.skc', 'warp', '0:0,6:9,7:22,10:31', '--frames', '11')
    cut(A + 'tps_reload_end.skc', A + 'coop_tps_reload_break.skc', 'warp', '0:0,6:10,7:26,10:35', '--frames', '11')


if __name__ == '__main__':
    main()

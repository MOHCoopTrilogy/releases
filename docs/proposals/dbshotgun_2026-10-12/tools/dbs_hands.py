"""First-person HAND clips of the double-barrel shotgun (rows `coopr_shotgun_double_barrel_<row>`).

    python tools/dbs_hands.py bake                     -> assets/models/human/animation/viewmodel/coop_dbshotgun/*.skc
                                                          + build/hand_paths.json (the carried shell, for dbs_anim.py)
    python tools/dbs_hands.py sheet <clip> f,f,f out.jpg [--ov overlay.pk3]     offline look (arms + gun, eye camera)

Recipe = the pump gun's own first-person clips (viewmodel/shotgun/*.skc: body, eye, camera and finger channels are
taken from them frame by frame, same channel layout, same frame counts, so the server's timing is unchanged) with the
GUN and both HANDS re-keyed for this gun and the arms solved by the lanes' two-bone IK (ads_bolt key_bolt.solve_arms):
  * the right hand keeps the pump gun's grip relation to the gun (the pistol grip sits where the pump's wrist is);
  * the gun is held PUSH u further out than the pump gun (a 60 cm gun is held in front of the body, not shouldered:
    at the retail place its breech is 6.6 u from the eye and fills the screen);
  * the left hand holds the forend LH_BACK u nearer than the pump's forend grip (the forend ends at 21.9 u);
  * fire: no pump stroke - a short kick of the gun (muzzle flip about the grip, impulse response of a damped spring);
  * reload / reload_single / reload_end: the gun is turned up and in (RELOAD pose) so the open breech faces the eye,
    the left hand's finger pinch is keyed along a path in GUN space (fetch below the view -> behind the chamber ->
    push home along the chamber axis -> back), hand orientation = the retail shell-feeding hand turned onto the
    chamber axis; in reload_end the left hand takes the forend of the OPEN barrels and rides them shut.
All keyed places are in the gun frame (scaled game units: +x muzzle, +y right, +z down).
"""
import os, sys, json, math
import numpy as np
import dbslib as L
import dbs_skx as X
import dbs_rig as D
import dbs_anim as GA

R, V, K, B = D.R, D.V, D.K, D.B
S = R.S
ODIR = os.path.join(L.ASSETS, 'models', 'human', 'animation', 'viewmodel', 'coop_dbshotgun')
TIK = 'models/weapons/coop_dbshotgun.tik'

PUSH = 7.0            # u the gun is held further out along its own axis than the pump gun
LH_BACK = 4.5         # u the forend hand sits nearer than on the pump gun
LH_UP = 0.4           # u higher (this forend's underside is higher than the pump's)
# the gun during the reload, relative to the held (pushed) idle gun: degrees about the gun's own axes through the
# grip, then a move in the idle gun's frame
RELOAD = dict(roll=-18.0, pitch=-24.0, yaw=8.0, move=(0.0, -2.0, -2.0))      # sheets a2 / a4: (-3 -4.5 -3) put the grip hand in the eye, (4 -3 -3) is out of the arms' reach (39 IK clamps)
GRIP = (-4.0, -1.05, 0.5)
KICK = dict(pitch=-7.5, back=1.3, roll=2.0, tau=0.045)      # fire: peak muzzle flip (deg, - = muzzle up), push back (u)
PINCH_ROLL = 20.0     # deg the loading hand is rolled about the chamber axis (fingers a little downhill, wrist up)


def xg(roll=0.0, pitch=0.0, yaw=0.0, move=(0, 0, 0), pivot=GRIP):
    """gun-local rigid move, 4x4 row form in RIG units: rotations about the gun's x (roll), y (pitch, - = muzzle up),
    z (yaw) through `pivot`, then `move` (scaled units)"""
    Rm = GA.rot((1, 0, 0), roll) @ GA.rot((0, 1, 0), pitch) @ GA.rot((0, 0, 1), yaw)
    pv = np.asarray(pivot, float) / S
    Xm = np.eye(4); Xm[0:3, 0:3] = Rm
    Xm[3, 0:3] = -pv @ Rm + pv + np.asarray(move, float) / S
    return Xm


def tr(move):
    Xm = np.eye(4); Xm[3, 0:3] = np.asarray(move, float) / S
    return Xm


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lerpX(A, Bm, w):
    return B.blend_H(A, Bm, w)


class Rig:
    def __init__(self):
        self.idle = D.load('idle')
        self.pd0 = R.pose_dict(self.idle, 0)
        self.W0 = R.evaluate(self.pd0)
        self.G0 = self.W0['tag_weapon_right']
        gi = R.inv(self.G0)
        self.HRrel = self.W0['Bip01 R Hand'] @ gi                  # hand in gun frame (rig units)
        self.HLrel = self.W0['Bip01 L Hand'] @ gi
        self.HLfor = self.HLrel @ tr((-LH_BACK, 0, -LH_UP))        # on THIS gun's forend
        self.Gidle = tr((PUSH, 0, 0)) @ self.G0
        fill = D.load('reload_single')
        self.fill = fill
        # The loading hand. (First try, sheet a1: the retail shell-feeding hand turned onto the chamber axis - that
        # hand is OPEN and pushes from below with the palm up into a port under the receiver; turned onto a chamber
        # that faces the eye it stood palm-out in front of the camera, the shell 3 u beside the fingers.)
        # Now: the IDLE hand's own curl (it holds a round forend - the shape that holds a shell), the shell lying in
        # the upturned fingers along the thumb: thumb side -> chamber axis, fingers -> across to the gun's right,
        # palm -> up. The hand stays UNDER the shell, so the chamber is not hidden.
        self.fing8 = {k: v for k, v in self.pd0.items() if k.startswith('Bip01 L Finger')}
        Hl = self.W0['Bip01 L Hand']

        def loc(b):
            return (self.W0[b][3, 0:3] - Hl[3, 0:3]) @ Hl[0:3, 0:3].T
        f_loc = (loc('Bip01 L Finger1') + loc('Bip01 L Finger2') + loc('Bip01 L Finger3')) / 3
        f_loc /= np.linalg.norm(f_loc)
        s_loc = loc('Bip01 L Finger4') - loc('Bip01 L Finger1')      # sheet a3: the other way round the palm faced DOWN
        s_loc -= (s_loc @ f_loc) * f_loc; s_loc /= np.linalg.norm(s_loc)
        Mloc = np.array([f_loc, s_loc, np.cross(f_loc, s_loc)])
        # chamber axis / places of the OPEN gun, rig units in the gun frame
        Rb, c_r = GA.chambered('dbs_shell_r', GA.OPEN); _, c_l = GA.chambered('dbs_shell_l', GA.OPEN)
        self.ax = Rb[0]
        self.cham = {'r': c_r, 'l': c_l}                           # skd units == rig units (x S = game units)
        f_t = GA.rot(self.ax, PINCH_ROLL)[1]                       # the gun's right (+y), rolled about the chamber axis
        f_t = f_t - (f_t @ self.ax) * self.ax; f_t /= np.linalg.norm(f_t)
        Mgun = np.array([f_t, self.ax, np.cross(f_t, self.ax)])
        self.Rload = Mloc.T @ Mgun
        # where the held shell's axis crosses the hand: between the thumb's end joint and the first two fingers' middles
        self.pin_local = (loc('Bip01 L Finger02') + loc('Bip01 L Finger11') + loc('Bip01 L Finger21')) / 3

    def load_hand(self, pinch_gun):
        """left-hand matrix (gun frame, rig units) with its finger pinch at `pinch_gun`"""
        Hm = np.eye(4); Hm[0:3, 0:3] = self.Rload
        Hm[3, 0:3] = np.asarray(pinch_gun, float) - self.pin_local @ self.Rload
        return Hm

    def forend_hand(self, theta):
        """left hand on the forend of barrels dropped by theta deg (rides the hinge)"""
        Rb = GA.barrels_R(theta)
        Xm = np.eye(4); Xm[0:3, 0:3] = Rb; Xm[3, 0:3] = -GA.PIN @ Rb + GA.PIN
        return self.HLfor @ Xm

    def solve(self, pd, G, HLg, fingers=None, wf=1.0):
        """pd: base channels (a retail frame); G: gun (rig world); HLg: left hand in the gun frame"""
        pd = dict(pd)
        Wc = R.evaluate(pd)
        if fingers:
            for k, v in fingers.items():
                q = R.qslerp(np.asarray(pd[k]), np.asarray(v), wf)
                pd[k] = q
        K.solve_arms(pd, Wc, self.HRrel @ G, HLg @ G, G)
        return pd


def kick(t):
    """damped-spring impulse response, 1 at its peak t = tau"""
    x = t / KICK['tau']
    return x * math.exp(1 - x) if x > 0 else 0.0


def pinch_path(rig, side):
    """the carried shell's head (= the finger pinch) in the gun frame per frame of reload_single (20 frames)"""
    c = rig.cham[side]; ax = rig.ax
    behind = c - ax * 9.0
    fetch = behind + np.array([-9.0, -16.0, 30.0])              # below and left of the view, out of sight
    rise = behind + np.array([-3.0, -5.0, 7.0])
    rest = behind + np.array([-4.0, -6.0, 9.0])
    keys = {0: fetch, 5: rise, 10: behind, 11: behind, 15: c, 16: c, 19: rest}
    out = {}
    ks = sorted(keys)
    for f in range(20):
        for a, b in zip(ks[:-1], ks[1:]):
            if a <= f <= b:
                out[f] = keys[a] + (keys[b] - keys[a]) * ease((f - a) / max(1, b - a))
    return out, rest, fetch


def bake_all():
    rig = Rig()
    Gi = rig.Gidle
    Grel = xg(**RELOAD) @ Gi
    clips = {}
    # ---- idle (1 frame) / pullout / putaway: the retail clips with the gun held out and the forend hand moved
    for nm in ('idle', 'pullout', 'putaway'):
        a = D.load(nm); fr = []
        for f in range(a.numFrames):
            pd = R.pose_dict(a, f); W = R.evaluate(pd)
            # the gun comes out to the held place over the clip (pullout) / goes back over it (putaway): pushed all the way
            # from frame 0 the arms could not reach it (9 IK clamps, run act1: an arm across the view at raise f3)
            wp = 1.0 if nm == 'idle' else (ease(f / (a.numFrames - 1.0)) if nm == 'pullout' else 1.0 - ease(f / (a.numFrames - 1.0)))
            G = tr((PUSH * wp, 0, 0)) @ W['tag_weapon_right']
            HLg = W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']) @ tr((-LH_BACK, 0, -LH_UP))
            fr.append(rig.solve(pd, G, HLg))
        clips[nm] = (a, fr)
    # ---- fire: 16 frames, the gun kicks
    a = D.load('fire'); fr = []
    for f in range(16):
        k = kick(f / 30.0)
        G = xg(roll=KICK['roll'] * k, pitch=KICK['pitch'] * k, move=(-KICK['back'] * k, 0, 0)) @ Gi
        fr.append(rig.solve(R.pose_dict(a, 0), G, rig.HLfor))
    clips['fire'] = (a, fr)
    # ---- reload (23): thumb the lever, turn the gun up, the left hand lets go of the dropping barrels and goes for a shell
    pr, rest_r, fetch = pinch_path(rig, 'r')
    pl, rest_l, _ = pinch_path(rig, 'l')
    a = D.load('reload'); fr = []
    for f in range(23):
        w = ease(f / 12.0)
        G = lerpX(Gi, Grel, w)
        th = GA.key({0: 0.0, 3: 0.0, 9: GA.OPEN * 1.04, 11: GA.OPEN * 0.985, 13: GA.OPEN}, f)
        wl = ease((f - 8) / 12.0)                                       # rides the forend down, then lets go
        HLg = lerpX(rig.forend_hand(th), rig.load_hand(fetch), wl)
        fr.append(rig.solve(R.pose_dict(a, f), G, HLg, rig.fing8, wl))
    clips['reload'] = (a, fr)
    # ---- reload_single (20): one shell, right chamber; the `_first` copy goes to the left chamber
    # ONE hands clip for both chambers (the first-person rows cannot tell which chamber is next - only the gun's own
    # row is swapped, cgame): the hand works on the line between the chambers, each shell rides 0.7 u beside it
    paths = {}
    a = D.load('reload_single'); fr = []
    for f in range(20):
        fr.append(rig.solve(R.pose_dict(a, f), Grel, rig.load_hand((pr[f] + pl[f]) / 2), rig.fing8, 1.0))
    clips['reload_single'] = (a, fr)
    for nm, path in (('reload_single', pr), ('reload_single_first', pl)):
        paths[nm] = {str(f): [GA.barrels_R(GA.OPEN).tolist(), path[f].tolist()] for f in range(5, 11)}
    # ---- charge (the aim pose, 1 frame): the pump gun's aim pose with the gun held out the same way
    a = D.load('charge')
    pd = R.pose_dict(a, 0); W = R.evaluate(pd)
    G = tr((PUSH, 0, 0)) @ W['tag_weapon_right']
    HLg = W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']) @ tr((-LH_BACK, 0, -LH_UP))
    rc = Rig.__new__(Rig); rc.HRrel = W['Bip01 R Hand'] @ R.inv(W['tag_weapon_right'])
    clips['charge'] = (a, [rc.solve(pd, G, HLg)])
    print('charge pose: eye in the gun frame', np.round(D.in_gun(G, W['eyes bone'][3, 0:3]), 2))
    # ---- reload_end (32): the left hand takes the forend of the open barrels and swings them shut; gun back to the hold
    a = D.load('reload_end'); fr = []
    for f in range(32):
        th = GA.key({0: GA.OPEN, 6: GA.OPEN, 9: GA.OPEN * 0.6, 11: 0.0, 32: 0.0}, f)
        wl = ease(f / 5.0)
        HLg = lerpX(rig.load_hand(rest_r), rig.forend_hand(th), wl)
        wg = ease((f - 12) / 14.0)
        G = lerpX(Grel, Gi, wg)
        fr.append(rig.solve(R.pose_dict(a, min(f, 5) if f < 12 else 31), G, HLg, rig.fing8, 1.0 - wl))
    clips['reload_end'] = (a, fr)
    return clips, paths


def write(clips, paths):
    os.makedirs(ODIR, exist_ok=True)
    for nm, (a, fr) in clips.items():
        names = a.names
        vals = []
        for f, pd in enumerate(fr):
            row = []
            for c, n in enumerate(names):
                v = np.asarray(pd[n], float)
                if n.endswith(' pos'):
                    v = np.array([v[0], v[1], v[2], 0.0])
                elif vals and float(v @ np.asarray(vals[-1][c])) < 0:
                    v = -v
                row.append(tuple(v))
            vals.append(row)
        b = a.frames[0]['bounds']
        data = X.build_skc(names, vals, a.frameTime, b[0:3], b[3:6], a.frames[0]['radius'])
        p = os.path.join(ODIR, 'dbs_%s.skc' % nm)
        open(p, 'wb').write(data)
        print('%-22s %2d frames %6d bytes' % (nm, len(fr), len(data)))
    json.dump(paths, open(os.path.join(L.BUILD, 'hand_paths.json'), 'w'))


GUN_ANIM = {'idle': 'idle', 'pullout': 'idle', 'putaway': 'idle', 'fire': 'fire', 'reload': 'reload',
            'reload_single': 'reload_single', 'reload_single_first': 'reload_single_first', 'reload_end': 'reload_end'}


def sheet(clips, nm, frames, out, W=560, H=340, fov=80.0):
    from PIL import Image, ImageDraw
    a, fr = clips[nm]
    ims = []
    for f in frames:
        pd = fr[min(f, len(fr) - 1)]
        surfs, E, Wb = V.scene(pd, TIK, GUN_ANIM[nm], f / 30.0)
        img, ids, dep = V.shade_render(surfs, E, fov, W, H)
        im = Image.fromarray(img)
        ImageDraw.Draw(im).text((4, 2), '%s f%d' % (nm, f), fill=(255, 255, 0))
        ims.append(im)
    cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols
    sh = Image.new('RGB', (cols * W, rows * H))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * W, (i // cols) * H))
    sh.save(out, quality=85)
    print('wrote', out)


def main():
    cmd = sys.argv[1]
    clips, paths = bake_all()
    if cmd == 'bake':
        write(clips, paths)
    else:
        nm = sys.argv[2]
        sheet(clips, nm, [int(x) for x in sys.argv[3].split(',')], sys.argv[4])


if __name__ == '__main__':
    main()

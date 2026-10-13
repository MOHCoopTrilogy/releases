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

# THE HOLD (2026-10-12 b): the gun's own place in the VIEW, not the pump gun's place pushed out. The camera is the
# eyes bone, its axes are the rig's (forward +x, left +y, up +z; vmcam). The pump rig shoulders the gun: the eye sits
# beside the grip and the gun crosses the view 22 deg to the left and 12 deg up - with a 60 cm gun that put the grip
# hand and the stock wood in the lower right as a lump. A pistol-gripped sawn-off is held OUT IN FRONT and low:
#   breech   where the top of the breech end sits in the view (forward, left, up), game units
#   yaw / pitch / roll   the barrels' direction off the view axis (deg; + = left / up; roll - = the top leans to the eye)
HOLD = dict(breech=(13.8, -6.0, -3.2), yaw=5.0, pitch=2.5, roll=-8.0)      # run hold2: the engine draws the hip gun ~1.6 u lower than the offline camera (4.7 down put the breech on the screen's bottom edge)
# THE AIM (the `charge` row; the engine then lays the sight line on the view axis itself - cg_adssights.h row, the
# same two numbers): eye `relief` u behind the breech top, the breech top `delta` rad under the bead's top
AIM = dict(relief=11.0, delta=0.131)
SIGHT_R = (4.7932, -1.05, -5.0074)        # top of the breech end, centre line (build/model.json sight.R)
SIGHT_F = (21.5216, -1.05, -5.3041)       # top of the bead (sight.F centre - its radius 0.2067 u)
LH_BACK = 6.6         # u the forend hand sits nearer than on the pump gun: wrist at 9.1 u, palm under the rear half
                      # of the forend (it runs 10.4 .. 21.9 u), the muzzle third left free
LH_UP = float(os.environ.get('DBS_LH_UP', -0.7))          # u higher than on the pump gun (- = lower: the fingers stay under the barrels' top line in the aim picture; sheet _lh)
LH_ROLL = float(os.environ.get('DBS_LH_ROLL', 0.0))       # deg the forend hand is turned about the forend's own axis
LH_AXIS = (-1.05, -3.2)                                   # that axis: y, z in the gun frame
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


def hold_G(E, breech, yaw, pitch, roll, at=None):
    """gun matrix (rig world, row form) with the gun point `at` (default: the breech top) at view place `breech`"""
    y, p, r = (math.radians(v) for v in (yaw, pitch, roll))
    gx = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    gy0 = np.array([math.sin(y), -math.cos(y), 0.0])                # the gun's right
    gz0 = np.cross(gx, gy0)                                         # the gun's down
    gy = gy0 * math.cos(r) + gz0 * math.sin(r); gz = -gy0 * math.sin(r) + gz0 * math.cos(r)
    G = np.eye(4); G[0:3, 0:3] = np.array([gx, gy, gz])
    G[3, 0:3] = np.asarray(E, float) + np.asarray(breech, float) / S - (np.asarray(at or SIGHT_R, float) / S) @ G[0:3, 0:3]
    return G


def aim_G(E, relief=None, delta=None):
    """the aimed gun: bead top on the view axis, the breech top `relief` u from the eye and `delta` rad under it"""
    relief = AIM['relief'] if relief is None else relief; delta = AIM['delta'] if delta is None else delta
    fr = np.asarray(SIGHT_F) - np.asarray(SIGHT_R)
    Lfr = float(np.linalg.norm(fr))
    Rv = relief * np.array([math.cos(delta), 0.0, -math.sin(delta)])
    dF = Rv[0] + math.sqrt(Lfr * Lfr - Rv[2] * Rv[2])
    v = np.array([dF, 0.0, 0.0]) - Rv                              # breech top -> bead top in the view
    pitch = math.degrees(math.atan2(v[2], v[0]) - math.atan2(-fr[2], fr[0]))
    return hold_G(E, tuple(Rv), 0.0, pitch, 0.0)


def lh_fix():
    """the pump gun's forend hand (gun frame) -> this gun's forend: back, up, turned about the forend's axis"""
    return tr((-LH_BACK, 0, -LH_UP)) @ xg(roll=LH_ROLL, pivot=(0.0, LH_AXIS[0], LH_AXIS[1]))


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
        self.HLfor = self.HLrel @ lh_fix()                         # on THIS gun's forend
        self.E0 = self.W0['eyes bone'][3, 0:3].copy()
        self.Gidle = hold_G(self.E0, **HOLD)
        self.Dl = self.Gidle @ R.inv(self.G0)                       # the hold as a gun-local move of the pump gun's place
        self.Gaim = aim_G(self.E0)
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
            G = lerpX(np.eye(4), rig.Dl, wp) @ W['tag_weapon_right']
            HLg = W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']) @ lh_fix()
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
    G = aim_G(W['eyes bone'][3, 0:3])
    HLg = W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']) @ lh_fix()
    rc = Rig.__new__(Rig); rc.HRrel = W['Bip01 R Hand'] @ R.inv(W['tag_weapon_right'])
    clips['charge'] = (a, [rc.solve(pd, G, HLg)])
    print('charge pose: eye in the gun frame', np.round(D.in_gun(G, W['eyes bone'][3, 0:3]), 2))
    print('hold: eye in the gun frame', np.round(D.in_gun(rig.Gidle, rig.E0), 2))
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


GUN_ANIM = {'idle': 'idle', 'charge': 'idle', 'pullout': 'idle', 'putaway': 'idle', 'fire': 'fire', 'reload': 'reload',
            'reload_single': 'reload_single', 'reload_single_first': 'reload_single_first', 'reload_end': 'reload_end'}


def sheet(clips, nm, frames, out, W=int(os.environ.get('DBS_W', 560)), H=int(os.environ.get('DBS_H', 340)), fov=float(os.environ.get('DBS_FOV', 80.0))):
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

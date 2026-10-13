"""Iron-sight G43: its own aim pose (coordinator 2026-10-12: "tuck the two support-hand fingers that show right of the
receiver - own pose tweak rather than the raw Garand pose"). The SMG lane's smgpose.py technique with the hip relation
replaced by the aim pose's own: new pose = the released aim pose (g43_charge = viewmodel/grnd_stand00.skc) with the
SUPPORT hand moved in the camera frame (fwd, left, up u) and optionally rolled about the gun's long axis, the left arm
solved to fit. Trunk, eye, the whole firing arm and its fingers and the weapon tag are the aim pose's, bit for bit.

    cd rifles/assets; python ../tools/g43pose.py . [--lower f,l,u] [--roll deg --pivot x,y,z] [--pic out.jpg]
-> models/human/animation/viewmodel/g43/coop_g43_irons_aim.skc (1 frame); row coopr_g_43_irons_charge (rows_rifle.py)
"""
import sys, os, json, hashlib, subprocess, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged  # noqa: F401
SHARED = os.path.normpath(os.path.join(HERE, '..', '..', 'tools'))
sys.path.insert(0, SHARED)
import revbake as RB
H = RB.H; R = RB.R; V = RB.V
KEY = 'g43_irons'
TIK = 'models/weapons/coop_g43_irons.tik'
AIM = 'viewmodel/grnd_stand00.skc'
IDLE = 'viewmodel/g43/g43_idle.skc'
OUT = 'viewmodel/g43/coop_g43_irons_aim.skc'
LOWER = (0.0, 1.1, -1.6)        # the staged value: the hand 1.1 u to the left and 1.6 u lower (0.9 / 1.1 left one fingertip showing)


def register():
    ov = json.load(open(os.path.join(HERE, '..', 'sights_override.json')))[KEY]
    V.SIGHTS[KEY] = dict(tik=TIK, name='G 43 Irons', skd=ov['skd'], F=ov['F'], R=ov['R'], up=ov['up'], delta_mrad=1000.0 * ov.get('delta', 0.0),
                         ftype='tip', rtype='notch', relief=ov.get('relief', 0.0), verified=True, note='')
    V.GUNTIK[KEY] = TIK


def picture(clip, out, W=960):
    a = R.load(clip if os.path.isfile(clip) else R.ANIM + clip)
    sight = V.SIGHTS[KEY]
    pd = R.pose_dict(a, a.numFrames - 1)
    corr = V.rig_target(V.evaluate_ctl(pd, RB.CTL), sight)
    Hh = W * 9 // 16
    surfs, E, Wb = V.scene2(pd, KEY, sight['tik'], 'idle', 0.0, RB.CTL, corr, None)
    img, ids, _ = V.shade_render(surfs, E, V.weapon_fov(), W, Hh, tex=True)
    from PIL import Image
    im = Image.fromarray(np.asarray(img, np.uint8)[:, :, :3])
    im.save(out, quality=90)
    m = (ids >= 0)[int(Hh * 0.4):int(Hh * 0.6), int(W * 0.4):int(W * 0.6)]
    return float(m.mean())


def bake(root, lower, roll=None, pivot=None):
    rc = H.auto_recipe('g43_charge', gun=KEY, charge=AIM, enter=0, exit=0, fixed_right=True, weight=dict(on=False),
                       handover=False, free_tag=False, elbow_vec={'L': (0, 0.5, -1)}, elbow_down={'L': [(0, 4.0)]})
    # the baker needs a clip of several frames as its time line: the hip idle. The support hand's relation to the gun
    # is NOT the idle's - it is given outright (relT) as the aim pose's own, then moved / rolled
    rc['hip'] = IDLE
    ac = R.load(R.ANIM + AIM)
    hc = R.load(R.ANIM + IDLE)
    Wh = R.evaluate(R.pose_dict(ac, ac.numFrames - 1))
    rel = Wh['Bip01 L Hand'] @ R.inv(Wh['tag_weapon_right'])
    if roll:
        pv = np.asarray(pivot, float) / R.S
        Tm = np.eye(4); Tm[3, 0:3] = -pv
        Rm = np.eye(4); Rm[0:3, 0:3] = R.axis_angle_rows((1, 0, 0), roll)
        Tp = np.eye(4); Tp[3, 0:3] = pv
        rel = rel @ Tm @ Rm @ Tp
    k = dict(rel=0, relT=rel, cam_add=tuple(lower), fing=0)
    rc['left_path'] = {0: k, hc.numFrames - 1: k}
    H.RECIPES['g43_charge'] = rc
    sk, _ = H.bake('g43_charge', RB.CTL)
    pa = R.pose_dict(ac, ac.numFrames - 1)
    cm = R.chanmap(sk)
    for ch, i in cm.items():         # both hands' fingers stay the AIM pose's (the baker takes them from the hip clip)
        if ch.startswith('Bip01 ') and ' Finger' in ch and ch in pa:
            sk.V[:, i] = pa[ch]
    sk.values = [[[float(np.float32(x)) for x in sk.V[f, c]] for c in range(sk.numChannels)] for f in range(sk.numFrames)]
    tmp = os.path.join(HERE, '_g43pose_tmp.skc')
    open(tmp, 'wb').write(R.skc_io.write(sk))
    dst = os.path.join(root, 'models', 'human', 'animation', OUT.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(SHARED, 'retime.py'), tmp, dst, 'slice', '0', '0'], check=True, capture_output=True)
    os.remove(tmp)
    n = R.load(dst); pn = R.pose_dict(n, 0)

    def same(ch):
        x, y = np.asarray(pn[ch], float), np.asarray(pa[ch], float)
        if ch.endswith(' rot'):
            return min(np.abs(x - y).max(), np.abs(x + y).max()) < 1e-5
        return np.abs(x[:3] - y[:3]).max() < 1e-5
    diff = [ch for ch in pn if ch in pa and not ch.startswith('Bip01 L ') and not ch.startswith('tag_weapon_left') and not same(ch)]
    wn = R.evaluate(pn)
    print('support hand in the gun frame (u): aim pose %s -> new %s' % (np.round(rel[3, :3] * R.S, 2), np.round((wn['Bip01 L Hand'] @ R.inv(wn['tag_weapon_right']))[3, :3] * R.S, 2)))
    print('%s  %d frame(s)  md5 %s  lower %s roll %s%s' % (OUT, n.numFrames, hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8], lower, roll,
                                                         '' if not diff else '  !! CHANGED outside the left arm: %s' % diff))
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('root'); ap.add_argument('--lower'); ap.add_argument('--roll', type=float); ap.add_argument('--pivot', default='14,-1.15,-1.5')
    ap.add_argument('--pic')
    a = ap.parse_args()
    register()
    lower = tuple(float(x) for x in a.lower.split(',')) if a.lower else LOWER
    dst = bake(a.root, lower, a.roll, tuple(float(x) for x in a.pivot.split(',')))
    if a.pic:
        c0 = picture(AIM, a.pic[:-4] + '_old.jpg'); c1 = picture(dst, a.pic)
        print('centre box covered by the first-person model, offline: old pose %.1f %%  new pose %.1f %%' % (100 * c0, 100 * c1))

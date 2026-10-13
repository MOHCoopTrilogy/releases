"""Iron-sight FG 42: its own aim pose (row coopr_fg_42_irons_charge; the scoped FG 42 has no aim pose - it shows the
scope picture). The rifle lane's g43pose.py / the pistol lane's pushpose.py technique, through hold_bake:

  base   = the StG 44's aim pose (mp44_charge = viewmodel/mp44_idle_stand.skc: trunk, eye, both shoulders) with the GUN
           SEATED IN THE FIRING HAND AS THE FG 42'S OWN HIP IDLE HAS IT (the weapon tag's local channels and the firing
           hand's fingers of viewmodel/fg42/fg42_stand_idle.skc frame 0 - this mesh's raked grip is not the StG's)
  pose   = that, with both arms reaching D u further out along the sight line (the rear aperture stands D u further
           from the eye) and the SUPPORT hand in the hip idle's hand-to-gun relation (on the wooden handguard, fingers
           wrapped), optionally moved in the camera frame (--lower fwd,left,up)

    cd heavy/assets; IRONSIGHT_EXTRA_PAKS=<overlay with the staged mesh> python ../tools/fg42pose.py [--push 6] [--lower f,l,u] [--pic out.jpg] [--out clip]
-> models/human/animation/viewmodel/fg42/coop_fg42_irons_aim.skc (1 frame)
"""
import sys, os, hashlib, subprocess, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
KEY = 'fg42_irons'
AIM = 'viewmodel/mp44_idle_stand.skc'
IDLE = 'viewmodel/fg42/fg42_stand_idle.skc'
BASE = 'viewmodel/fg42/coop_fg42_irons_aimbase.skc'
IDLE3 = 'viewmodel/fg42/coop_fg42_idle3.skc'
OUT = 'viewmodel/fg42/coop_fg42_irons_aim.skc'
RT = os.path.join(hv.SHARED, 'retime.py')


def setvals(sk):
    sk.values = [[[float(np.float32(x)) for x in sk.V[f, c]] for c in range(sk.numChannels)] for f in range(sk.numFrames)]


def base():
    """the StG aim pose with the FG 42 seated in the firing hand as its hip idle has it"""
    a = R.load(R.ANIM + AIM); h = R.load(R.ANIM + IDLE)
    pa, ph = R.pose_dict(a, a.numFrames - 1), R.pose_dict(h, 0)
    cm = R.chanmap(a)
    moved = []
    for ch, i in cm.items():
        if (ch.startswith('tag_weapon_right') or (ch.startswith('Bip01 R ') and ' Finger' in ch)) and ch in ph:
            if np.abs(np.asarray(pa[ch], float) - np.asarray(ph[ch], float)).max() > 1e-4:
                moved.append(ch)
            a.V[:, i] = ph[ch]
    setvals(a)
    dst = hv.staged('models/human/animation/' + BASE)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + '.tmp'
    open(tmp, 'wb').write(R.skc_io.write(a))
    subprocess.run([sys.executable, RT, tmp, dst, 'slice', str(a.numFrames - 1), str(a.numFrames - 1)], check=True, capture_output=True)
    os.remove(tmp)
    w0, w1 = R.evaluate(pa), R.evaluate(R.pose_dict(R.load(dst), 0))
    d = (w1['tag_weapon_right'] @ R.inv(w0['tag_weapon_right']))[3, :3] * R.S
    print('base: %d channels taken from the FG 42 hip idle (tag + firing fingers); the gun moves %s u in the hand against the StG seat' % (len(moved), np.round(d, 2)))
    return dst


def picture(clip, out, W=960):
    a = R.load(clip)
    sight = V.SIGHTS[KEY]
    pd = R.pose_dict(a, a.numFrames - 1)
    ev = V.evaluate_ctl(pd, CTL)
    corr = V.rig_target(ev, sight)
    Hh = W * 9 // 16
    surfs, E, Wb = V.scene2(pd, KEY, sight['tik'], 'idle', 0.0, CTL, corr, None)
    img, ids, _ = V.shade_render(surfs, E, V.weapon_fov(), W, Hh, tex=True)
    from PIL import Image, ImageDraw
    im = Image.fromarray(np.asarray(img, np.uint8)[:, :, :3])
    ImageDraw.Draw(im).rectangle([int(W * 0.4), int(Hh * 0.4), int(W * 0.6), int(Hh * 0.6)], outline=(230, 220, 60))
    im.save(out, quality=90)
    m = (ids >= 0)[int(Hh * 0.4):int(Hh * 0.6), int(W * 0.4):int(W * 0.6)]
    return float(m.mean())


def bake(push, lower, out=None, roll=0.0, pivot=(7.0, -0.855, -2.6)):
    base()
    # the baker needs a time line of several frames; the FG 42's hip idle is ONE frame - a 3-frame copy of it
    i3 = hv.staged('models/human/animation/' + IDLE3)
    subprocess.run([sys.executable, RT, 'models/human/animation/' + IDLE, i3, '3'], check=True, capture_output=True)
    hc = R.load(R.ANIM + IDLE3)
    Wi = R.evaluate(R.pose_dict(hc, 0))
    rel = Wi['Bip01 L Hand'] @ R.inv(Wi['tag_weapon_right'])
    if roll:                                  # the support hand turned about the gun's long axis through the handguard (g43pose.py)
        pv = np.asarray(pivot, float) / R.S
        Tm = np.eye(4); Tm[3, 0:3] = -pv
        Rm = np.eye(4); Rm[0:3, 0:3] = R.axis_angle_rows((1, 0, 0), roll)
        Tp = np.eye(4); Tp[3, 0:3] = pv
        rel = rel @ Tm @ Rm @ Tp
    z = (0.0, 0.0, 0.0, 0.0, -float(push))
    k = dict(rel=0, relT=rel, cam_add=tuple(lower), fing=0)
    rc = dict(gun=KEY, hip=IDLE3, charge=BASE, offhand=(-1, -1), enter=0, exit=0, slide={}, weight=dict(on=False), fixed_right=True,
              handover=False, free_tag=False, dip={0: z, hc.numFrames - 1: z}, left_path={0: k, hc.numFrames - 1: k},
              elbow_vec={'R': (0.0, -1.0, -0.2), 'L': (0.0, 0.5, -1.0)}, elbow_down={'L': [(0, 3.0)]})
    H.RECIPES['fg42irons_charge'] = rc
    sk, _ = H.bake('fg42irons_charge', CTL)
    dst = out or hv.staged('models/human/animation/' + OUT)
    tmp = dst + '.tmp'
    open(tmp, 'wb').write(R.skc_io.write(sk))
    subprocess.run([sys.executable, RT, tmp, dst, 'slice', '0', '0'], check=True, capture_output=True)
    os.remove(tmp)
    n = R.load(dst); wn = R.evaluate(R.pose_dict(n, 0))
    print('%s 1 frame md5 %s push %.1f lower %s roll %s | support hand in the gun frame (u) %s' % (
        OUT, hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8], push, lower, roll, np.round((wn['Bip01 L Hand'] @ R.inv(wn['tag_weapon_right']))[3, :3] * R.S, 2)))
    return dst


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--push', type=float, default=5.0); ap.add_argument('--lower', default='0,0,-0.4'); ap.add_argument('--pic'); ap.add_argument('--out'); ap.add_argument('--roll', type=float, default=40.0)   # staged values (run hj23): the palm on the handguard's left flank, fingers under - nothing of the hand right of the receiver
    a = ap.parse_args()
    dst = bake(a.push, tuple(float(x) for x in a.lower.split(',')), a.out, a.roll)
    if a.pic:
        print('centre box covered by the first-person model, offline: %.1f %%' % (100 * picture(dst, a.pic)))

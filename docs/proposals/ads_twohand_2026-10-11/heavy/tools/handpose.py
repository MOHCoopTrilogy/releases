"""Aim pose with the support hand where the HIP pose has it - heavy lane (BAR, DP-28, Vickers-Berthier, Breda).

User 2026-10-12: "when holding the sten in ads, the left hand should stay on the mag, it should be that way for any
weapon where the mag is braced with the left/right hand" / "Fix them all". All four guns' `<prefix>_charge` row is the
BAR's aim clip (viewmodel/bar_stand00.skc): the support hand sits where a BAR forearm is, not where THIS gun has
something to hold. The method is the pistol lane's magpose.py: the aim pose is kept (trunk, eye, firing arm, weapon
tag - the sight picture cannot change) and only the support hand takes the hip idle's hand-to-gun relation (place,
rotation, fingers), the arm solved to fit.

    cd heavy/assets; python ../tools/handpose.py <prefix|all> [--lower f,l,u] [--elb x,y,z] [--elbw w]
writes models/human/animation/<vdir>/coop_<prefix>_ads_hand.skc (1 frame) and prints the hand's place in the gun frame
(x forward, y right, z down; u) at the hip, in the old aim pose and in the new one.
"""
import sys, os, hashlib, subprocess, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()

SET = {
    # prefix: per-gun options. lower = camera-frame move of the hand (fwd, left, up) where the hip relation would put
    # it inside the centre box; elb / elbw = elbow pole direction (camera frame) and weight
    'bar': dict(),
    'dp28': dict(),
    'vickers': dict(),
    'breda': dict(),
}


def out_clip(p):
    return '%s/coop_%s_ads_hand.skc' % (hv.GUNS[p]['vdir'], p)


def rel_hand(clip, f=0):
    a = R.load(clip if os.path.isfile(clip) else R.ANIM + clip)
    W = R.evaluate(R.pose_dict(a, min(f, a.numFrames - 1)))
    return (W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']))[3, :3] * R.S


def bake(p, a):
    g = hv.GUNS[p]
    o = dict(SET[p])
    rows = H.fps_rows()
    hip = rows[g['idle']]
    aim = a.aim or o.get('aim') or 'viewmodel/bar_stand00.skc'       # the released aim row (not a staged repoint)
    elb = tuple(float(x) for x in (a.elb or o.get('elb', '0,0.5,-1')).split(',')) if isinstance(a.elb or o.get('elb', ''), str) else o['elb']
    rc = H.auto_recipe(g['idle'], gun=g['sight'], charge=aim, enter=0, exit=0, fixed_right=True, weight=dict(on=False),
                       handover=False, free_tag=False, elbow_vec={'L': elb},
                       elbow_down={'L': [(0, float(a.elbw if a.elbw is not None else o.get('elbw', 4.0)))]})
    rc['hip'] = hip
    lower = tuple(float(x) for x in a.lower.split(',')) if a.lower else o.get('lower')
    hf = int(a.hipframe if a.hipframe is not None else o.get('hipframe', 0))
    k = dict(rel=hf, fing=hf)
    if lower:
        k['cam_add'] = lower
    if o.get('gun_add'):
        k['gun_add'] = o['gun_add']
    rc['left_path'] = {0: k, max(1, R.load(R.ANIM + hip).numFrames - 1): k}     # a one-frame idle still needs two keys
    H.RECIPES[g['idle']] = rc
    sk, _ = H.bake(g['idle'], CTL)
    os.makedirs(hv.SCR, exist_ok=True)
    tmp = os.path.join(hv.SCR, 'handpose_tmp.skc')
    open(tmp, 'wb').write(R.skc_io.write(sk))
    dst = hv.staged('models/human/animation/' + out_clip(p))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(hv.SHARED, 'retime.py'), tmp, dst, 'slice', '0', '0'], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    np.set_printoptions(precision=1, suppress=True)
    print('%-8s hand in the gun frame (fwd, right, down) u: hip %s  old aim %s  new aim %s' % (p, rel_hand(hip, hf), rel_hand(aim), rel_hand(dst)))
    print('%-8s -> %s %s | hip %s | old aim %s' % (p, out_clip(p), hashlib.md5(open(dst, 'rb').read()).hexdigest()[:8], hip, aim))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('--lower'); ap.add_argument('--elb'); ap.add_argument('--elbw', type=float)
    ap.add_argument('--aim'); ap.add_argument('--hipframe', type=int)
    a = ap.parse_args()
    for p in (list(SET) if a.gun == 'all' else a.gun.split(',')):
        bake(p, a)

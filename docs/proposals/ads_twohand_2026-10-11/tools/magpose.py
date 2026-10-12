"""Aim pose with the support hand where the HIP pose has it (user 2026-10-12: "when holding the sten in ads, the left
hand should stay on the mag, it should be that way for any weapon where the mag is braced with the left/right hand").

The aim pose row (`<prefix>_charge`) of several guns borrows another gun's clip (Sten: the MP40's, whose hand is under
the gun on an MP40 magazine). New pose = that aim pose with the support hand in the hip idle's hand-to-gun relation
(place, rotation, fingers), the arm solved to fit; trunk, eye, firing arm and the weapon tag stay the aim pose's, so
the sight picture cannot change. The same technique as the two-handed pistol pose.

    cd stage; python ../magpose.py <gun|all> .       -> <out>.skc (1 frame) + rows for mkov (ovargs_magpose.txt)
    also prints where the support hand sits relative to the gun at the hip and in the old / new aim pose
"""
import sys, os, hashlib, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revbake as RB
H = RB.H; R = RB.R

GUNS = {
    # prefix: sight gun, hip idle row, out clip
    'sten': dict(sight='sten_mark_ii', out='viewmodel/sten/coop_sten_ads_mag.skc'),
    # lower: the hip relation puts the hand's top inside the left edge of the centre box (offline preview); the hand
    # takes the magazine from underneath instead (camera frame: fwd, left, up)
    'type100': dict(sight='type_100_smg', out='viewmodel/sten/coop_type100_ads_mag.skc', lower=(0.0, 1.0, -1.7)),
}


def rel_hand(clip, f=0):
    a = R.load(R.ANIM + clip)
    W = R.evaluate(R.pose_dict(a, min(f, a.numFrames - 1)))
    return (W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right']))[3, :3] * R.S


def bake(name, root):
    g = GUNS[name]
    rows = H.fps_rows()
    hip, aim = rows[name + '_idle'], rows[name + '_charge']
    rc = H.auto_recipe(name + '_idle', gun=g['sight'], charge=aim, enter=0, exit=0, fixed_right=True, weight=dict(on=False),
                       handover=False, free_tag=False,
                       # the elbow hangs under the hand: the forearm comes up from the lower left, not straight at the eye
                       elbow_vec={'L': tuple(float(x) for x in os.environ.get('MP_ELB', '0,0.5,-1').split(','))},
                       elbow_down={'L': [(0, float(os.environ.get('MP_ELBW', '4.0')))]})
    if g.get('lower'):
        k = dict(rel=0, cam_add=g['lower'], fing=0)
        rc['left_path'] = {0: k, R.load(R.ANIM + hip).numFrames - 1: k}
    H.RECIPES[name + '_idle'] = rc
    sk, _ = H.bake(name + '_idle', RB.CTL)
    tmp = os.path.join(HERE, 'magpose_tmp.skc')
    open(tmp, 'wb').write(R.skc_io.write(sk))
    dst = os.path.join(root, 'models', 'human', 'animation', g['out'].replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(HERE, 'retime.py'), tmp, dst, 'slice', '0', '0'], check=True, capture_output=True)
    np.set_printoptions(precision=1, suppress=True)
    print(name, 'support hand in the gun frame (x fwd, y right, z down), u:  hip', rel_hand(hip), ' old aim', rel_hand(aim),
          ' new aim', rel_hand(dst) if False else '')
    b = open(dst, 'rb').read()
    print(name, '->', g['out'], hashlib.md5(b).hexdigest()[:8], '| hip clip', hip, '| old aim clip', aim)
    return '%s=%s' % (name, g['out'])


if __name__ == '__main__':
    args = [bake(nm, sys.argv[2]) for nm in (list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(','))]
    open(os.path.join(HERE, 'ovargs_magpose.txt'), 'w').write(' '.join(args) + '\n')

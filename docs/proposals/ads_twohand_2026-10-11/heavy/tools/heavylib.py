"""Heavy lane bake helpers on top of hold_bake (camera frame: x forward along the sight line, y LEFT, z UP, eye at 0).

    cam_of(aim, sight)            -> (Gs gun tag in the model, scaled rows; Mcam model -> camera)
    gun_pt(aim, sight, p)         a weapon-tag point (x fwd, y right, z DOWN; u) in the camera frame of the settled aim
    work_T(aim, sight, d, pivot)  gun-in-camera (rows, u) for hold_bake `gun_abs`: the AIMED gun rolled d['roll'] deg
                                  (+ = top to the right) about the forward axis, pitched d['pitch'] (+ = muzzle down)
                                  about the left axis, yawed d['yaw'] (+ = muzzle to the LEFT) about the up axis, all
                                  through `pivot` (camera frame, e.g. the butt in the shoulder), then moved
                                  d['move'] = (fwd, left, up) u
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()


def _load(clip):
    return R.load(clip if os.path.isfile(clip) else R.ANIM + clip)


def cam_of(aim, sight):
    a = _load(aim)
    pc = R.pose_dict(a, a.numFrames - 1)
    Wc = R.evaluate(pc)
    Wcc = V.evaluate_ctl(pc, CTL)
    corr = V.rig_target(Wcc, V.SIGHTS[sight])
    C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']; C[3, 0:3] *= R.S
    Mcam = C @ V.model_to_cam(corr)
    Gs = Wc['tag_weapon_right'].copy(); Gs[3, 0:3] *= R.S
    return Gs, Mcam


def gun_pt(aim, sight, p):
    Gs, Mcam = cam_of(aim, sight)
    return (np.r_[np.asarray(p, float), 1.0] @ Gs @ Mcam)[0:3]


def xform(d, pivot):
    """camera-frame rigid move (rows): rotations through `pivot`, then the move"""
    Rr = R.axis_angle_rows((1, 0, 0), d.get('roll', 0.0)) @ R.axis_angle_rows((0, 1, 0), d.get('pitch', 0.0)) \
        @ R.axis_angle_rows((0, 0, 1), d.get('yaw', 0.0))
    pv = np.asarray(pivot, float)
    P = np.eye(4); P[3, 0:3] = -pv
    Q = np.eye(4); Q[0:3, 0:3] = Rr
    Pi = np.eye(4); Pi[3, 0:3] = pv + np.asarray(d.get('move', (0, 0, 0)), float)
    return P @ Q @ Pi


def work_T(aim, sight, d, pivot):
    Gs, Mcam = cam_of(aim, sight)
    return Gs @ Mcam @ xform(d, pivot)


if __name__ == '__main__':
    np.set_printoptions(precision=1, suppress=True)
    p = sys.argv[1]
    g = hv.GUNS[p]
    import handpose
    aim = hv.staged('models/human/animation/' + handpose.out_clip(p))
    if not os.path.isfile(aim):
        aim = H.fps_rows().get(p + '_charge') or H.fps_rows()[g['idle']]
    print(p, 'gun tag in the camera frame (fwd, left, up):', gun_pt(aim, g['sight'], (0, 0, 0)))
    for a in sys.argv[2:]:
        pt = [float(x) for x in a.split(',')]
        c = gun_pt(aim, g['sight'], pt)
        print('  gun pt %s -> cam %s   %.1f deg below, %.1f deg left of the sight line' % (
            pt, c, -np.degrees(np.arctan2(c[2], c[0])), np.degrees(np.arctan2(c[1], c[0]))))

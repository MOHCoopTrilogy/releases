"""Where the off-hand tag (the ammo prop) is relative to the GUN tag in a baked clip, per frame, against a retail frame.

    cd heavy/assets; python ../tools/tagrel.py <baked clip.skc> <hip row> <retail frame> [step]
prints the tag's position in the gun's tag frame (u) and its distance / angle from the retail frame's relation
(0 u / 0 deg = the prop sits exactly where the retail art has it in the gun, i.e. inside the gun's own magazine).
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
np.set_printoptions(precision=1, suppress=True)
clip, row, rf = sys.argv[1], sys.argv[2], int(sys.argv[3])
step = int(sys.argv[4]) if len(sys.argv) > 4 else 2
hip = R.load(R.ANIM + H.fps_rows()[row])
Wq = R.evaluate(R.pose_dict(hip, rf))
ref = Wq['tag_weapon_left'] @ R.inv(Wq['tag_weapon_right'])
c = R.load(clip)
for f in range(0, c.numFrames, step):
    W = R.evaluate(R.pose_dict(c, f))
    rel = W['tag_weapon_left'] @ R.inv(W['tag_weapon_right'])
    d = np.linalg.norm((rel[3, 0:3] - ref[3, 0:3]) * R.S)
    ang = R.rot_angle_deg(rel[0:3, 0:3] @ ref[0:3, 0:3].T) if hasattr(R, 'rot_angle_deg') else 0.0
    print('f%-3d tag in gun frame %s   from retail f%d: %.1f u  %.0f deg' % (f, rel[3, 0:3] * R.S, rf, d, ang))

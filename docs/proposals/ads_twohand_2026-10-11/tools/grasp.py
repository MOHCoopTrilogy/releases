"""where the left hand sits in the GUN frame (u; x fwd, y right, z down) in a view clip's frame: wrist, knuckles, tips"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
np.set_printoptions(precision=2, suppress=True, linewidth=200)
clip, fr = sys.argv[1], int(sys.argv[2])
side = sys.argv[3] if len(sys.argv) > 3 else 'L'
a = R.load(R.ANIM + clip)
W = R.evaluate(R.pose_dict(a, fr))
G = W['tag_weapon_right']
for b in ['Bip01 %s Forearm' % side, 'Bip01 %s Hand' % side] + ['Bip01 %s Finger%s' % (side, k) for k in ('0', '01', '02', '1', '11', '12', '2', '21', '22', '3', '32', '4', '42')]:
    rel = W[b] @ R.inv(G)
    print('%-18s pos %s  x-axis %s' % (b, rel[3, 0:3] * R.S, rel[0, 0:3]))

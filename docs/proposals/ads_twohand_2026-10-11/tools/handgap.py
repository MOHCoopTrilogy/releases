"""per frame: distance of the left hand from the right hand (u) in a body / view clip - where the off hand leaves the
gun, where it is back. Used to line a prone torso reload up with the standing one.

    python handgap.py <clip under models/human/animation or a file> [...]
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
for c in sys.argv[1:]:
    a = R.load(c if os.path.isfile(c) else R.ANIM + c)
    d = []
    for f in range(a.numFrames):
        W = R.evaluate(R.pose_dict(a, f))
        d.append(float(np.linalg.norm((W['Bip01 L Hand'][3, 0:3] - W['Bip01 R Hand'][3, 0:3]) * R.S)))
    print(c, a.numFrames, 'f x %.4f' % a.frameTime)
    print('  ' + ' '.join('%d:%.0f' % (f, x) for f, x in enumerate(d)))

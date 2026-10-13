"""per frame: rotation angle (deg, from frame 0) and position shift of one channel pair of a gun clip - when a part moves.

    python chanang.py <clip (game path or file)> <bone> [...]
"""
import sys, os, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
a = R.load(sys.argv[1])
print(sys.argv[1], a.numFrames, 'f x %.4f' % a.frameTime)
for bone in sys.argv[2:]:
    out = []
    if bone + ' rot' in a.names:
        c = a.names.index(bone + ' rot')
        q0 = a.V[0, c]
        for f in range(a.numFrames):
            d = abs(float(np.dot(q0, a.V[f, c])))
            out.append('%d:%.0f' % (f, 2 * math.degrees(math.acos(min(1.0, d)))))
        print('  %s rot deg: %s' % (bone, ' '.join(out)))
    if bone + ' pos' in a.names:
        c = a.names.index(bone + ' pos')
        print('  %s pos u: %s' % (bone, ' '.join('%d:%.1f' % (f, float(np.linalg.norm(a.V[f, c, :3] - a.V[0, c, :3]))) for f in range(a.numFrames))))

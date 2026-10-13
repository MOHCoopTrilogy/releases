"""Which hand does what in a first-person reload clip: both wrists and both index fingertips in the GUN frame (weapon
tag: x forward, y right, z down; u) every few frames, and the frames in which each hand is away from where it starts.

    python handtrace.py <row or clip.skc> [...] [--step 4] [--full]
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'tools')))
import revbake as RB
R = RB.R; H = RB.H
step = int(sys.argv[sys.argv.index('--step') + 1]) if '--step' in sys.argv else 4
names = [a for a in sys.argv[1:] if not a.startswith('--') and not a.isdigit()]
rows = H.fps_rows()
np.set_printoptions(precision=1, suppress=True)
for nm in names:
    path = rows.get(nm, nm)
    c = R.load(R.ANIM + path)
    tr = []
    for f in range(c.numFrames):
        W = R.evaluate(R.pose_dict(c, f)); G = R.inv(W['tag_weapon_right'])
        tr.append([(W[b] @ G)[3, :3] * R.S for b in ('Bip01 L Hand', 'Bip01 R Hand', 'Bip01 L Finger12', 'Bip01 R Finger12')])
    tr = np.array(tr)
    print('== %s  (%s)  %d frames x %.4f s' % (nm, path, c.numFrames, c.frameTime))
    for k, hand in enumerate(('LEFT ', 'RIGHT')):
        d = np.linalg.norm(tr[:, k] - tr[0, k], axis=1)
        away = [f for f in range(c.numFrames) if d[f] > 1.5]
        runs, s = [], None
        for f in range(c.numFrames + 1):
            if f < c.numFrames and d[f] > 1.5:
                s = f if s is None else s
            elif s is not None:
                runs.append('%d-%d (max %.0f u at f%d, index tip there %s)' % (s, f - 1, d[s:f].max(), s + int(np.argmax(d[s:f])), tr[s + int(np.argmax(d[s:f])), 2 + k]))
                s = None
        print('   %s wrist starts %s; away from it: %s' % (hand, tr[0, k], '; '.join(runs) or 'never'))
    if '--full' in sys.argv:
        for f in range(0, c.numFrames, step):
            print('   f%-3d L %s tip %s | R %s tip %s' % (f, tr[f, 0], tr[f, 2], tr[f, 1], tr[f, 3]))

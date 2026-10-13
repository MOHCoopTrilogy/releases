"""What a retail reload does, in numbers, before it is rebuilt: the gun clip's moving bone channels (frame ranges and
values) and the hands clip's left hand in the gun's tag frame (x fwd, y right, z DOWN; u) every `step` frames.

    cd heavy/assets; python ../tools/clipinfo.py <hands row> <gun path/clip.skc> [step]
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
np.set_printoptions(precision=1, suppress=True)
row, gclip = sys.argv[1], sys.argv[2]
step = int(sys.argv[3]) if len(sys.argv) > 3 else 3
a = R.skc_io.read(R.vfs.read(gclip))
print('GUN clip', gclip, a.numFrames, 'frames', round(a.frameTime, 4))
names = list(a.names)
fr = np.asarray([[list(v) for v in f] for f in a.values], float)
print('  channels:', len(names), 'array', fr.shape)
for ci, n in enumerate(names):
    v = fr[:, ci, :] if fr.ndim == 3 else fr[:, ci]
    d = np.abs(v - v[0]).max(axis=-1) if v.ndim > 1 else np.abs(v - v[0])
    mv = np.nonzero(d > 1e-3)[0]
    if len(mv):
        k = int(np.argmax(d))
        print('  MOVES %-22s frames %d..%d  rest %s  peak f%d %s' % (n, mv[0], mv[-1], v[0], k, v[k]))
c = R.load(R.ANIM + H.fps_rows()[row])
print('HANDS', row, c.numFrames, 'frames')
for f in range(0, c.numFrames, step):
    W = R.evaluate(R.pose_dict(c, f))
    G = W['tag_weapon_right']
    L = W['Bip01 L Hand'] @ R.inv(G)
    p = L[3, 0:3] * R.S
    GL = W['tag_weapon_left'] @ R.inv(G)
    print('  f%-3d L hand in gun frame %s   off-hand tag from gun tag %s' % (f, p, GL[3, 0:3] * R.S))

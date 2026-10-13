"""third-person clips: where the left hand is relative to the gun over the clip (a pump stroke = it slides along x)
    python tools/tps_probe.py <clip under models/human/animation/> [...]"""
import sys
import numpy as np
import dbs_rig as D

R = D.R
for nm in sys.argv[1:]:
    try:
        a = R.load(R.ANIM + nm)
    except Exception as e:
        print(nm, 'load failed:', e); continue
    xs = []
    for f in range(a.numFrames):
        W = R.evaluate(R.pose_dict(a, f))
        G = W['tag_weapon_right']
        xs.append(D.in_gun(G, W['Bip01 L Hand'][3, 0:3]))
    xs = np.array(xs)
    print('%-52s %3d frames ft %.4f (%.2f s)  L hand in gun: x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f' % (
        nm, a.numFrames, a.frameTime, a.numFrames * a.frameTime, xs[:, 0].min(), xs[:, 0].max(), xs[:, 1].min(), xs[:, 1].max(), xs[:, 2].min(), xs[:, 2].max()))
    print('     x per 3 frames:', ' '.join('%.0f' % v for v in xs[::3, 0]))

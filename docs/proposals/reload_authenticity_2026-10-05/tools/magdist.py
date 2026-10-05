import sys, json, os
import numpy as np
sys.argv_save = sys.argv[:]; sys.argv = ['x', 'out', 'none']
import sheet as S
R, V = S.R, S.V
key, surfname = sys.argv_save[1], sys.argv_save[2]
tik, clips, ls, tn, side = S.G[key]
ctl = json.load(open(os.path.join(S.T, '..', 'assets', 'ctl_stand.json')))
c = R.load(S.resolve(clips[0]))
g = S.gungeo.load_gun(tik, anim='idle', frame=0)
sv = [s for s in g['surfs'] if s['name'].lower() == surfname.lower()][0]
cen = sv['P'].mean(0)
for f in range(0, c.numFrames, 3):
    W = V.evaluate_ctl(R.pose_dict(c, f), ctl)
    T = W['tag_weapon_right']; mag = cen @ T[0:3, 0:3] + T[3, 0:3] * R.S
    L = W['tag_weapon_left'][3, 0:3] * R.S
    print('f%3d t%.2f  hand-mag %.1f' % (f, f * c.frameTime, np.linalg.norm(L - mag)))

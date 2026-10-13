"""eye -> rear sight / front sight distance of a gun on an aim pose (the rig solve's own numbers), arm extension left

    python _eyedist.py <aim clip under ANIM> <sight key> [...]
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
V = gunskc.V; R = V.R
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
clip = sys.argv[1]
a = R.load(R.ANIM + clip)
pd = R.pose_dict(a, a.numFrames - 1)
W = V.evaluate_ctl(pd, CTL)
for side in 'RL':
    s = W['Bip01 %s UpperArm' % side][3, :3]; e = W['Bip01 %s Forearm' % side][3, :3]; h = W['Bip01 %s Hand' % side][3, :3]
    L = (np.linalg.norm(e - s) + np.linalg.norm(h - e)) * R.S
    d = np.linalg.norm(h - s) * R.S
    print('%s arm: length %.2f u, shoulder->wrist %.2f u, reach left %.2f u' % (side, L, d, L - d))
for key in sys.argv[2:]:
    sg = V.SIGHTS[key]
    c = V.rig_target(W, sg)
    G = W['tag_weapon_right']
    Rp = (np.r_[np.array(sg['R']) / R.S, 1.0] @ G)[:3] * R.S
    Fp = (np.r_[np.array(sg['F']) / R.S, 1.0] @ G)[:3] * R.S
    E = np.asarray(c['E'], float)
    print('%-22s eye->rear %.2f u  eye->front %.2f u  | rear x %.2f  relief %s' % (key, np.linalg.norm(Rp - E), np.linalg.norm(Fp - E), sg['R'][0], c.get('relief')))

"""Can a hand reach the handle from the AIM pose? Shoulder, grip wrist and the hooked wrist (hook_rel) in the gun frame,
the arm's length, and how far back the handle would have to be for the hand to get there.

    cd smg/assets; python ../tools/reachcheck.py <gun> [L|R]
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smgbake as SB
R = SB.R
name = sys.argv[1]
g = SB.GUNS[name]
hand = sys.argv[2] if len(sys.argv) > 2 else g.get('cock', 'L')
rows = SB.H.fps_rows()
hip = R.load(R.ANIM + rows[g['row']])
aimp = os.path.join('models', 'human', 'animation', g['aim'].replace('/', os.sep))
ac = R.load(aimp if os.path.isfile(aimp) else R.ANIM + g['aim'])
W = R.evaluate(R.pose_dict(ac, ac.numFrames - 1))
G = W['tag_weapon_right']; Gi = R.inv(G)
fwd, travel, kj = SB.knob(name)
np.set_printoptions(precision=1, suppress=True)


def gf(b):
    return (W[b] @ Gi)[3, :3] * R.S
sh, el, wr = gf('Bip01 %s UpperArm' % hand), gf('Bip01 %s Forearm' % hand), gf('Bip01 %s Hand' % hand)
arm = np.linalg.norm(el - sh) + np.linalg.norm(wr - el)
print('%s, %s hand, aim pose (gun frame, u): shoulder %s  wrist on its grip %s  arm length %.1f' % (name, hand, sh, wr, arm))
for hipdir in (False, True):
    T = SB.hook_rel(g, hip, fwd, hip=hipdir, hand=hand)
    wt = T[3, :3] * R.S
    d = np.linalg.norm(wt - sh)
    # slide the handle back along x until the wrist is within 97 % of the arm
    back = 0.0
    while np.linalg.norm(wt - np.array([back, 0, 0]) - sh) > 0.97 * arm and back < travel + 20:
        back += 0.1
    print('   hook (%s dirs): wrist at %s = %.1f u from the shoulder (%.0f %% of the arm); handle forward at %s, travel %.1f; in reach once the handle is %.1f u back'
          % ('hip' if hipdir else 'aim', wt, d, 100 * d / arm, np.round(fwd, 1), travel, back))

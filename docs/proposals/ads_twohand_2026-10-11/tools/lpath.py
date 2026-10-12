import sys, os, json
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V, hold_bake as H
os.chdir(_c)
R = V.R
np.set_printoptions(precision=1, suppress=True, linewidth=200)
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
hipn, aimn, gun = sys.argv[1], sys.argv[2], sys.argv[3]
hip = R.load(R.ANIM + hipn); aim = R.load(aimn if os.path.isfile(aimn) else R.ANIM + aimn)
pc = R.pose_dict(aim, aim.numFrames - 1); Wc = R.evaluate(pc); Gc = Wc['tag_weapon_right']
Wcc = V.evaluate_ctl(pc, CTL); corr = V.rig_target(Wcc, V.SIGHTS[gun])
C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']; C[3, 0:3] *= R.S
Mcam = C @ V.model_to_cam(corr)
print('aim: L hand cam', (np.r_[Wc['Bip01 L Hand'][3, 0:3] * R.S, 1] @ Mcam)[0:3], 'gun', ((Wc['Bip01 L Hand'] @ R.inv(Gc))[3, 0:3] * R.S))
sh = (np.r_[Wc['Bip01 L UpperArm'][3, 0:3] * R.S, 1] @ Mcam)[0:3]
print('L shoulder cam', sh, 'frames', hip.numFrames)
try:
    import prop_qa as Q
    print('props', Q.attach_windows(sys.argv[4], hip.numFrames, hip.frameTime))
except Exception as e:
    print('no prop windows', e)
for f in range(hip.numFrames):
    Wh = R.evaluate(R.pose_dict(hip, f)); Gh = Wh['tag_weapon_right']
    rel = Wh['Bip01 L Hand'] @ R.inv(Gh)
    HL = rel @ Gc
    p = (np.r_[HL[3, 0:3] * R.S, 1] @ Mcam)[0:3]
    tl = (Wh['tag_weapon_left'] @ R.inv(Gh))[3, 0:3] * R.S
    print('f%2d L hand: gun-frame %s cam %s reach %.1f | tag_left in gun frame %s' % (f, rel[3, 0:3] * R.S, p, np.linalg.norm(p - sh), tl))

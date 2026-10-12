"""inspect the pistol aim pose: channels, hand placement relative to the gun and the camera"""
import sys, os, json, math
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
os.chdir(T)
import vmcam as V
R = V.R
np.set_printoptions(precision=3, suppress=True, linewidth=200)

clip = sys.argv[1] if len(sys.argv) > 1 else 'viewmodel/coltpose00.skc'
gun = sys.argv[2] if len(sys.argv) > 2 else 'colt_45'
a = R.load(R.ANIM + clip)
print(clip, 'frames', a.numFrames, 'ft', a.frameTime, 'channels', a.numChannels)
print([n for n in a.names])
pd = R.pose_dict(a, a.numFrames - 1)
ctl = json.load(open('../assets/ctl_stand.json'))
print('ctl', ctl)
Wc = R.evaluate(pd)
Wcc = V.evaluate_ctl(pd, ctl)
corr = V.rig_target(Wcc, V.SIGHTS[gun])
print('corr', {k: (np.round(v, 4) if hasattr(v, '__len__') else round(v, 4)) for k, v in corr.items()})
C = R.inv(Wc['Bip01 Spine1']) @ Wcc['Bip01 Spine1']
C[3, 0:3] *= R.S
Mcam = C @ V.model_to_cam(corr)
def cam(H):
    return (np.r_[H[3, 0:3] * R.S, 1.0] @ Mcam)[0:3]
for b in ('eyes bone', 'tag_weapon_right', 'tag_weapon_left', 'Bip01 R Hand', 'Bip01 L Hand', 'Bip01 R Forearm', 'Bip01 L Forearm',
          'Bip01 R UpperArm', 'Bip01 L UpperArm', 'Bip01 R Clavicle', 'Bip01 L Clavicle'):
    print('%-20s cam(x fwd, y left, z up) %s' % (b, cam(Wc[b])))
G = Wc['tag_weapon_right']
print('gun axes in cam (rows = gun x,y,z):')
print(G[0:3, 0:3] @ Mcam[0:3, 0:3])
for side in 'RL':
    rel = Wc['Bip01 %s Hand' % side] @ R.inv(G)
    print(side, 'hand in gun frame: pos(scaled)', rel[3, 0:3] * R.S)
    print(rel[0:3, 0:3])
sk = R.skeleton()
print('bones:', [n for n in sk.order])
la = np.linalg.norm(Wc['Bip01 L Forearm'][3, 0:3] - Wc['Bip01 L UpperArm'][3, 0:3]) * R.S
lb = np.linalg.norm(Wc['Bip01 L Hand'][3, 0:3] - Wc['Bip01 L Forearm'][3, 0:3]) * R.S
print('L arm lengths', la, lb, 'shoulder->Rhand dist', np.linalg.norm(Wc['Bip01 R Hand'][3, 0:3] - Wc['Bip01 L UpperArm'][3, 0:3]) * R.S)

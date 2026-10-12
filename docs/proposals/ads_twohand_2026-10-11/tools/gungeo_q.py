"""gun mesh in its own (tag) frame: per-surface bbox and the grip's cross-sections; right-hand finger joints in the gun frame"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
R = V.R; PR = V.PR
np.set_printoptions(precision=2, suppress=True, linewidth=200)
tik = sys.argv[1] if len(sys.argv) > 1 else 'models/weapons/colt45.tik'
clip = sys.argv[2] if len(sys.argv) > 2 else 'viewmodel/coltpose00.skc'
g = PR.gungeo.load_gun(tik)
P = np.vstack([s['P'] for s in g['surfs']])
for s in g['surfs']:
    print('%-14s n=%4d min %s max %s' % (s['name'], len(s['P']), s['P'].min(0), s['P'].max(0)))
print('ALL min', P.min(0), 'max', P.max(0), '(x fwd, y right, z down)')
for z0 in (-3, -2, -1, 0, 1, 2, 3, 4, 5, 6):
    m = (P[:, 2] > z0 - 0.5) & (P[:, 2] <= z0 + 0.5)
    if m.any():
        print('z %+d: x %.2f..%.2f  y %.2f..%.2f  n=%d' % (z0, P[m, 0].min(), P[m, 0].max(), P[m, 1].min(), P[m, 1].max(), m.sum()))
a = R.load(R.ANIM + clip)
W = R.evaluate(R.pose_dict(a, a.numFrames - 1))
G = W['tag_weapon_right']
for b in ['Bip01 R Hand'] + ['Bip01 R Finger%s' % k for k in ('0', '01', '02', '1', '11', '12', '2', '21', '22', '3', '31', '32', '4', '41', '42')]:
    rel = W[b] @ R.inv(G)
    print('%-18s gun-frame pos %s  x-axis %s' % (b, rel[3, 0:3] * R.S, rel[0, 0:3]))

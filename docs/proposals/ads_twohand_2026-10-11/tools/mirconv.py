"""find the left/right bone-frame mirror convention of the fps rig from the hand meshes' bone-local vertex offsets"""
import sys, os, itertools
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); os.chdir(T)
import vmcam as V
R = V.R; PR = V.PR
np.set_printoptions(precision=3, suppress=True, linewidth=200)
m = PR.arms_skd()
names = [b.name for b in m.bones]
print('surfaces', [(s.name, s.numVerts) for s in m.surfaces])


def cloud(surf, bone):
    s = [x for x in m.surfaces if x.name == surf][0]
    out = []
    for normal, texc, wl, ml in s.verts:
        for bi, bw, off in wl:
            if names[bi] == bone and bw > 0.5:
                out.append(off)
    return np.array(out)


for bl, br in (('Bip01 L Hand', 'Bip01 R Hand'), ('Bip01 L Finger1', 'Bip01 R Finger1'), ('Bip01 L Finger0', 'Bip01 R Finger0'),
               ('Bip01 L Finger21', 'Bip01 R Finger21'), ('Bip01 L Forearm', 'Bip01 R Forearm')):
    for sl in ('lefthand', 'viewsleeves'):
        L = cloud(sl, bl)
        if len(L):
            break
    for sr in ('triggerhand', 'viewsleeves'):
        Rr = cloud(sr, br)
        if len(Rr):
            break
    print(bl, sl, len(L), '|', br, sr, len(Rr))
    if not len(L) or not len(Rr):
        continue
    print('  L mean', L.mean(0), 'min', L.min(0), 'max', L.max(0))
    print('  R mean', Rr.mean(0), 'min', Rr.min(0), 'max', Rr.max(0))
    best = []
    for sg in itertools.product((1, -1), repeat=3):
        F = np.array(sg, float)
        P = Rr * F
        d = np.sqrt(((L[:, None, :] - P[None, :, :]) ** 2).sum(-1)).min(1).mean()
        best.append((d, sg))
    best.sort()
    print('  fits', [(round(d, 3), sg) for d, sg in best[:4]])
# base pose bone offsets (skeleton)
sk = R.skeleton()
for n in ('Bip01 L Hand', 'Bip01 R Hand', 'Bip01 L Finger0', 'Bip01 R Finger0', 'Bip01 L Finger1', 'Bip01 R Finger1',
          'Bip01 L Finger11', 'Bip01 R Finger11', 'Bip01 L Forearm', 'Bip01 R Forearm'):
    b = sk.bones[n]
    print(n, {k: (v if not hasattr(v, '__len__') or len(v) < 12 else '...') for k, v in b.items() if k not in ('children',)})

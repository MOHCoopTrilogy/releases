"""Landmarks of the new C96 (BU, source frame: +y muzzle, +z up, +x right) vs the mod's current C96 (skd raw units, x0.52).
   python landmarks.py"""
import sys, os, json
import numpy as np
sys.path.insert(1, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import skdlib as S
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, '..', 'build')
d = np.load(os.path.join(B, 'tris.npz'))
A, part = d['corners'], d['part']
for nm in ('Root', 'Slide', 'Hammer', 'Trigger', 'Ring'):
    P = A[part == nm].reshape(-1, 8)[:, :3]
    print('NEW %-8s min %s max %s' % (nm, P.min(0).round(3), P.max(0).round(3)))
R = A[part == 'Root'].reshape(-1, 8)
P = R[:, :3]
g = P[P[:, 2] < -0.35]
print('NEW grip(z<-0.35): y %.3f..%.3f z %.3f..%.3f' % (g[:, 1].min(), g[:, 1].max(), g[:, 2].min(), g[:, 2].max()))
f = P[P[:, 1] > 2.2]
print('NEW front sight top z', f[:, 2].max(), 'at y', f[f[:, 2].argmax(), 1], ' muzzle y', P[:, 1].max(), 'bore z approx', P[P[:, 1] > 2.36][:, 2].min(), P[P[:, 1] > 2.36][:, 2].max())
rr = P[(P[:, 1] > 0.5) & (P[:, 1] < 0.7)]
print('NEW rear sight top z', rr[:, 2].max(), 'at y', rr[rr[:, 2].argmax(), 1])
# magazine / clip guide rails: shells 2,3 region
m = S.read_skd(open(r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod\models\weapons\coop_c96\c96.skd', 'rb').read())
for s in m.surfaces:
    Q = np.array([v[2][0][2] for v in s.verts]) * 0.52
    print('OLD %-10s scaled min %s max %s' % (s.name, Q.min(0).round(2), Q.max(0).round(2)))

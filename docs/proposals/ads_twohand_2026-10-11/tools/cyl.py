import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
PR = V.PR
np.set_printoptions(precision=2, suppress=True)
for tik in sys.argv[1:]:
    g = PR.gungeo.load_gun(tik)
    print(tik)
    for s in g['surfs']:
        print('  %-16s n=%4d min %s max %s' % (s['name'], len(s['P']), s['P'].min(0), s['P'].max(0)))
    P = np.vstack([s['P'] for s in g['surfs']])
    # left-side profile: for x slices, the leftmost y (most negative) in the band z -2.5..1.5 (thumb zone)
    for x0 in np.arange(-2, 7, 1.0):
        m = (P[:, 0] > x0 - 0.5) & (P[:, 0] <= x0 + 0.5) & (P[:, 2] > -2.5) & (P[:, 2] < 1.5)
        if m.any():
            print('  x %+.0f: y %.2f..%.2f  z %.2f..%.2f n=%d' % (x0, P[m, 1].min(), P[m, 1].max(), P[m, 2].min(), P[m, 2].max(), m.sum()))

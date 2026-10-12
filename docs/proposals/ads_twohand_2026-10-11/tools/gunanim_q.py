import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
PR = V.PR
np.set_printoptions(precision=2, suppress=True)
tik, anim = sys.argv[1], sys.argv[2]
g0 = PR.gungeo.load_gun(tik)
P0 = {s['name']: s['P'] for s in g0['surfs']}
for f in range(0, int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 2):
    g = PR.gungeo.load_gun(tik, anim=anim, frame=f)
    out = []
    for s in g['surfs']:
        d = s['P'] - P0[s['name']]
        mv = np.linalg.norm(d, axis=1)
        if mv.max() > 0.05:
            k = mv > 0.05
            out.append('%s: %d verts moved, mean %s' % (s['name'], k.sum(), d[k].mean(0)))
    print('f%d' % f, ' | '.join(out) if out else '-')

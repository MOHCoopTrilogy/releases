"""Which parts of a gun move in one of its own animations, and when: per surface the bbox at rest and the frames at
which its centre is displaced (tag frame: x fwd, y right, z DOWN; u). Also lists the gun clip's bone channels.

    cd heavy/assets; python ../tools/gunmove.py <weapon tik> <anim> [step]
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
H, R, V, CTL = hv.lib()
np.set_printoptions(precision=2, suppress=True)
tik, anim = sys.argv[1], sys.argv[2]
step = int(sys.argv[3]) if len(sys.argv) > 3 else 2
PR = V.PR
g0 = PR.gungeo.load_gun(tik)
rest = {s['name']: s['P'] for s in g0['surfs']}
for n, P in rest.items():
    print('rest %-14s min %s max %s' % (n, P.min(0), P.max(0)))
f = 0
moved = {}
while True:
    try:
        g = PR.gungeo.load_gun(tik, anim=anim, frame=f)
    except Exception as e:
        break
    any_ = False
    for s in g['surfs']:
        d = s['P'].mean(0) - rest[s['name']].mean(0)
        if np.abs(d).max() > 0.05:
            moved.setdefault(s['name'], []).append((f, d.round(2)))
    f += step
    if f > 400:
        break
print('frames scanned to', f - step)
for n, L in moved.items():
    print('MOVES %-12s frames %d..%d  ' % (n, L[0][0], L[-1][0]), ' '.join('%d:%s' % (a, list(b)) for a, b in L[::max(1, len(L) // 10)]))

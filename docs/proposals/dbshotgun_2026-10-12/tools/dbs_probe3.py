"""which channels the retail shotgun clips carry; speed of one FK pass (prints only)"""
import time
import numpy as np
import dbs_rig as D

R = D.R
for nm in ('idle', 'fire', 'reload', 'reload_single', 'reload_end', 'pullout', 'putaway', 'charge'):
    a = D.load(nm)
    n = a.names
    rf = [c for c in n if c.startswith('Bip01 R Finger')]
    lf = [c for c in n if c.startswith('Bip01 L Finger')]
    oth = [c for c in n if 'Finger' not in c]
    print('%-14s frames %2d ft %.4f channels %3d: R finger %2d, L finger %2d, other %s' % (nm, a.numFrames, a.frameTime, len(n), len(rf), len(lf), ' | '.join(oth) if nm in ('idle', 'charge') else len(oth)))
a = D.load('reload_single')
pd = R.pose_dict(a, 3)
print('pose_dict keys', len(pd), 'has R Finger0 rot', 'Bip01 R Finger0 rot' in pd, 'has pos keys', [k for k in pd if k.endswith(' pos')][:8])
t = time.time()
for _ in range(50):
    W = R.evaluate(pd)
print('evaluate: %.2f ms' % ((time.time() - t) / 50 * 1000))

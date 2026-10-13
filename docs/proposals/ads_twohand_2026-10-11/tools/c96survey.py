"""c96survey.py [tik]  surfaces + islands (bbox, gun space: +x muzzle, +y right, +z down) of a gun mesh"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bonefit as BF
np.set_printoptions(precision=2, suppress=True, linewidth=200)
tik = sys.argv[1] if len(sys.argv) > 1 else 'models/weapons/mauser_c96.tik'
g = BF.PR.gungeo.load_gun(tik)
print('keys', [k for k in g.keys()])
allp = np.concatenate([np.asarray(s['P']) for s in g['surfs']])
print('ALL  min', allp.min(0), 'max', allp.max(0))
for s in g['surfs']:
    P = np.asarray(s['P'])
    print('surface %-18s verts %5d  min %s max %s  keys %s' % (s.get('name'), len(P), P.min(0), P.max(0), [k for k in s.keys() if k not in ('P',)][:8]))
isl = BF.islands_of(g)
for name, L in isl.items():
    for it in L:
        try:
            print('  island', name, it if not hasattr(it, 'keys') else {k: (v if not hasattr(v, '__len__') or len(v) < 8 else len(v)) for k, v in it.items()})
        except Exception as e:
            print('  island', name, type(it), e)

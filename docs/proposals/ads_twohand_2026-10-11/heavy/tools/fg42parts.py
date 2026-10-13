"""FG 42: the vertices of chosen connected components of models/weapons/fg42/fg42.skd (gun frame as gungeo loads it:
x forward, y right, z down, tik-scaled u) - the front sight, the scope's mount, the receiver's top - and each one's bone.

    python fg42parts.py <surface> <tris> [<surface> <tris> ...]     e.g.  fg42barrel 46 fg42barrel 12
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.normpath(os.path.join(HERE, '..', '..', 'rifles', 'tools'))
sys.path.insert(0, RT)
import staged
staged.off()
import g43irons as G
g = G.gungeo.load_gun('models/weapons/FG42.tik', 'idle', 0)
args = sys.argv[1:]
for k in range(0, len(args), 2):
    name, nt = args[k], int(args[k + 1])
    for s in g['surfs']:
        if s['name'].lower() != name:
            continue
        for tl in G.comps(s['P'], s['tri']):
            if len(tl) != nt:
                continue
            P = np.unique(np.round(s['P'][np.unique(s['tri'][tl])], 3), axis=0)
            print('%s %d tris: %d positions, x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % ((name, nt, len(P)) + tuple(v for a in range(3) for v in (P[:, a].min(), P[:, a].max()))))
            for zc in sorted(set(np.round(P[:, 2], 1))):
                q = P[np.round(P[:, 2], 1) == zc]
                print('   z %5.1f: ' % zc + ' '.join('(%.2f,%.2f)' % (a, b) for a, b, c in q[np.argsort(q[:, 0])]))

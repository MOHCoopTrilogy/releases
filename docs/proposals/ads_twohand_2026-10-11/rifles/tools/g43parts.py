"""G43 irons request (user 2026-10-12: "I'd like an iron sight version of the g43 too"): what the shared mesh
models/weapons/g43/g43.skd is made of - per surface, its connected components (by shared vertex POSITION) with their
bounding boxes in the gun frame (model units x tik scale: x fwd, y right, z down as loaded by gungeo), so the scope,
its mount and the lens can be told from the rifle, and whether sights exist under the scope.

    python g43parts.py [tik]      (default models/weapons/g43.tik)
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged
import boltnear as BN
gungeo, vfs = BN.gungeo, BN.vfs
tik = sys.argv[1] if len(sys.argv) > 1 else 'models/weapons/g43.tik'
g = gungeo.load_gun(tik, 'idle', 0)
t = g['tik']
print(tik, 'skd', g['skd'], 'pak', os.path.basename(str(g['skdpak'])), 'scale', t['scale'], 'surface shaders', t['surf'])
allp = np.vstack([s['P'] for s in g['surfs']])
print('whole gun bbox min %s max %s' % (np.round(allp.min(0), 1), np.round(allp.max(0), 1)))
for s in g['surfs']:
    P, tri = s['P'], s['tri']
    key = {}
    vid = np.array([key.setdefault(tuple(np.round(p, 3)), len(key)) for p in P])
    par = list(range(len(key)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for a, b, c in vid[tri]:
        ra, rb, rc = find(a), find(b), find(c)
        par[rb] = ra; par[rc] = ra
    comp = {}
    for ti, (a, b, c) in enumerate(tri):
        comp.setdefault(find(vid[a]), []).append(ti)
    print('surface %-10s shader %-22s verts %4d tris %4d components %d' % (s['name'], s['shader'], len(P), len(tri), len(comp)))
    for r, tl in sorted(comp.items(), key=lambda kv: -len(kv[1])):
        pts = P[np.unique(tri[tl])]
        print('    %4d tris  x %6.1f..%6.1f  y %5.1f..%5.1f  z %5.1f..%5.1f' % (len(tl), pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max(), pts[:, 2].min(), pts[:, 2].max()))

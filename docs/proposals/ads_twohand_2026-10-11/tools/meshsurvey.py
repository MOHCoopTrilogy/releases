"""per surface / per bone / per island bounding boxes of a gun mesh in gun space (x fwd, y right, z down)

    python _meshsurvey.py <tik> [--islands SURFACE[,SURFACE]] [--min N]
"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
PR = V.PR
SK = PR.skdlib
np.set_printoptions(precision=2, suppress=True, linewidth=200)
tik = sys.argv[1]
isl = []
mn = 6
for i, a in enumerate(sys.argv):
    if a == '--islands':
        isl = sys.argv[i + 1].lower().split(',')
    if a == '--min':
        mn = int(sys.argv[i + 1])
g = PR.gungeo.load_gun(tik)
skd = SK.read_skd(PR.gungeo.vfs.read(g['skd']))
print(tik, g['skd'], '| bones:', ' '.join('%d:%s' % (i, b.name) for i, b in enumerate(skd.bones)), '| scale', g['tik']['scale'])
print('tags:', {k: np.round(v[0], 2).tolist() for k, v in g['tags'].items()})
for s, gs in zip(skd.surfaces, g['surfs']):
    P = gs['P']
    bone = np.array([max(v[2], key=lambda w: w[1])[0] for v in s.verts])
    print('%-12s shader %-22s n=%4d min %s max %s' % (s.name, gs['shader'], len(P), P.min(0), P.max(0)))
    for b in sorted(set(bone)):
        Q = P[bone == b]
        print('     bone %-10s n=%4d min %s max %s' % (skd.bones[b].name, len(Q), Q.min(0), Q.max(0)))
    if s.name.lower() in isl or 'all' in isl:
        tri = gs['tri']
        key = {}
        w = np.zeros(len(P), int)
        for i, p in enumerate(P):
            w[i] = key.setdefault(tuple(np.round(p, 2)), len(key))
        par = list(range(len(key)))

        def find(x):
            while par[x] != x:
                par[x] = par[par[x]]; x = par[x]
            return x
        for t in tri:
            a, b, c = find(w[t[0]]), find(w[t[1]]), find(w[t[2]])
            par[b] = a; par[c] = a
        comp = {}
        for i in range(len(P)):
            comp.setdefault(find(w[i]), []).append(i)
        for k, idx in sorted(comp.items(), key=lambda kv: -len(kv[1])):
            if len(idx) < mn:
                continue
            Q = P[idx]
            print('       island %4d verts  min %s  max %s' % (len(idx), np.round(Q.min(0), 2), np.round(Q.max(0), 2)))

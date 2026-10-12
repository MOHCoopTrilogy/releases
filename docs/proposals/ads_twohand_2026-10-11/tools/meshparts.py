"""Connected parts of a gun mesh surface (vertices welded by position): is the slide its own island?

    python meshparts.py <tik> <surface>
"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
g = V.PR.gungeo.load_gun(sys.argv[1])
for s in g['surfs']:
    if s['name'].lower() != sys.argv[2].lower():
        continue
    P = np.asarray(s['P']); tri = np.asarray(s['tri'])
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
    print(s['name'], len(P), 'verts', len(tri), 'tris', len(comp), 'parts (x fwd, y right, z down)')
    for k, idx in sorted(comp.items(), key=lambda kv: -len(kv[1])):
        Q = P[idx]
        print('  %4d verts  min %s  max %s' % (len(idx), np.round(Q.min(0), 2), np.round(Q.max(0), 2)))

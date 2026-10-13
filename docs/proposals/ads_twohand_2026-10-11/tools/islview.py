"""side (x, z) and top (x, y) vertex plots of a gun mesh's islands, one colour + label per island (>= --min verts)

    python _islview.py <tik> <out.png> [--min 10] [--xmax 8] [--surf a,b]
"""
import sys, os
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
os.chdir(_c)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
tik, out = sys.argv[1], sys.argv[2]
mn, xmax, only = 10, 8.0, None
for i, a in enumerate(sys.argv):
    if a == '--min':
        mn = int(sys.argv[i + 1])
    if a == '--xmax':
        xmax = float(sys.argv[i + 1])
    if a == '--surf':
        only = sys.argv[i + 1].lower().split(',')
g = V.PR.gungeo.load_gun(tik)
fig, ax = plt.subplots(2, 1, figsize=(15, 11))
k = 0
cm = plt.get_cmap('tab20')
for s in g['surfs']:
    if only and s['name'].lower() not in only:
        continue
    P = np.asarray(s['P']); tri = np.asarray(s['tri'])
    key = {}; w = np.zeros(len(P), int)
    for i, p in enumerate(P):
        w[i] = key.setdefault(tuple(np.round(p, 2)), len(key))
    par = list(range(len(key)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for t in tri:
        a = find(w[t[0]]); par[find(w[t[1]])] = a; par[find(w[t[2]])] = a
    comp = {}
    for i in range(len(P)):
        comp.setdefault(find(w[i]), []).append(i)
    for _, idx in sorted(comp.items(), key=lambda kv: -len(kv[1])):
        Q = P[idx]
        if len(idx) < mn or Q[:, 0].min() > xmax:
            continue
        lab = '%s/%d x%.2f' % (s['name'], len(idx), Q[:, 0].min())
        c = cm(k % 20); k += 1
        m = Q[:, 0] <= xmax + 2
        ax[0].scatter(Q[m, 0], Q[m, 2], s=14, color=c, label=lab)
        ax[1].scatter(Q[m, 0], Q[m, 1], s=14, color=c)
        ax[0].annotate(str(k), (Q[:, 0].mean(), Q[:, 2].min()), color=c, fontsize=13, weight='bold')
        ax[1].annotate(str(k), (Q[:, 0].mean(), Q[:, 1].min()), color=c, fontsize=13, weight='bold')
ax[0].invert_yaxis(); ax[0].set_aspect('equal'); ax[1].set_aspect('equal'); ax[1].invert_yaxis()
ax[0].set_title('side: x forward ->, z (down is down)'); ax[1].set_title('top: x forward, y right (left side of the gun at the top)')
ax[0].legend(fontsize=8, ncol=2, loc='lower right'); ax[0].grid(True, alpha=0.3); ax[1].grid(True, alpha=0.3)
fig.tight_layout(); fig.savefig(out, dpi=70)
print(out)

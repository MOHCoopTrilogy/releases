"""Path-node island sweep on the ENGINE's own graph (the .pth it writes at map load).
A node group the main graph cannot reach, or that cannot reach the main graph, with none of the original's AI places
(spawn / pose / squad objective / MMG / ICS / scene point: places an AI is put or sent, from the pak's data script) within 160u
(z within 64u: one floor level), is listed for ea_levels.json "path_nodes_drop". Groups WITH an AI place are reported for a fix.
usage: python -I islandsweep.py <pth> <pak> [street x,y,z]"""
import json, math, re, sys, zipfile
sys.path.insert(0, r"H:\hzm_work\eapolish\dbfix_2026-11-11\tools")
import pthread as P

pth, pak = sys.argv[1], sys.argv[2]
street = tuple(map(float, (sys.argv[3] if len(sys.argv) > 3 else "-2900,-600,-488").split(",")))
v, n = P.load(pth)
N = len(n)
adj = [set(c[0] for c in x[2]) for x in n]
radj = [set() for _ in range(N)]
for k in range(N):
    for y in adj[k]:
        radj[y].add(k)


def reach(s, a):
    seen = {s}; st = [s]
    while st:
        x = st.pop()
        for y in a[x]:
            if y not in seen:
                seen.add(y); st.append(y)
    return seen


s0 = min(range(N), key=lambda k: sum((n[k][0][i] - street[i]) ** 2 for i in range(3)))
main = reach(s0, adj) & reach(s0, radj)
z = zipfile.ZipFile(pak)
data = z.read("maps/coop_ea_1_11_data.scr").decode("latin-1")
anch = []
for m in re.finditer(r"level\.ea_(so|sp|ps|mg|sc|ic)_pos\[[^\]]+\] = \( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \)", data):
    anch.append(tuple(float(m.group(i)) for i in (2, 3, 4)))


def anchored(p):
    return any((a[0] - p[0]) ** 2 + (a[1] - p[1]) ** 2 < 160.0 ** 2 and abs(a[2] - p[2]) < 64.0 for a in anch)


und = [set(adj[k]) | radj[k] for k in range(N)]
left = set(range(N)) - main
drop, keep = [], []
while left:
    s = left.pop(); g = {s}; st = [s]
    while st:
        x = st.pop()
        for y in und[x]:
            if y in left:
                left.discard(y); g.add(y); st.append(y)
    pts = [n[k][0] for k in g]
    box = [[round(min(p[i] for p in pts)) for i in range(3)], [round(max(p[i] for p in pts)) for i in range(3)]]
    if any(anchored(p) for p in pts):
        keep.append((len(g), box))
    else:
        drop += [[round(p[0], 1), round(p[1], 1), round(p[2], 1)] for p in pts]
print("nodes", N, "main", len(main), "drop", len(drop), "anchored islands", len(keep))
for k in sorted(keep, reverse=True):
    print("  anchored island", k)
json.dump(drop, open(sys.argv[4] if len(sys.argv) > 4 else "islands_drop.json", "w"))

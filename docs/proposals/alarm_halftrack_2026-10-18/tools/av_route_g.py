"""av_route_g.py - m3l3 Nebelwerfer guard: two halftrack routes from the flood fill scout/m3l3g_scf.txt.
Stops: rotation-safe fill cells 900-1700 u from Nebelwerfer 1 on the church side, >= 350 u off the church->Nebelwerfer line, with room round them;
the two stops >= 600 u apart. Entries: >= 2500 u from the church and >= 1500 u from every Nebelwerfer, 1800-7000 u of drivable graph from the stop."""
import json, math, os, sys
import av_route as R
CH = (1551, -2370)
NEB = [(-1834, -5160), (-3454, -6531), (-4173, -6487), (-5676, -6055)]
cells, adj = R.load("m3l3g")
OVL = {}
if os.path.exists("scout/m3l3_ovl.txt"):
    for l in open("scout/m3l3_ovl.txt"):
        a = l.split()
        OVL[(round(float(a[0]), 1), round(float(a[1]), 1))] = int(a[3])
MINOV = int(os.environ.get("MINOV", "4"))
def ovl(c):
    return OVL.get((round(cells[c][0], 1), round(cells[c][1], 1)), -1)
comps = R.comps(cells, adj)
D = lambda c, p: math.hypot(cells[c][0] - p[0], cells[c][1] - p[1])
def lat(c):
    ax, ay = CH; bx, by = NEB[0]
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((cells[c][0] - ax) * dx + (cells[c][1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(cells[c][0] - (ax + dx * t), cells[c][1] - (ay + dy * t))
out = []
for comp in sorted(comps, key=len, reverse=True)[:14]:
    if len(comp) < 80:
        continue
    cand = [c for c in comp if ovl(c) >= MINOV and lat(c) >= 150 and R.fat(cells, c) and R.room(cells, adj, c) >= 2 and R.bypass(cells, c) >= 22]
    cand.sort(key=lambda c: (-ovl(c), abs(D(c, NEB[0]) - 1300)))
    print("component", len(comp), "stop candidates", len(cand))
    chosen = []
    for s in cand:
        if all(math.hypot(cells[s][0] - cells[t][0], cells[s][1] - cells[t][1]) >= 450 for t in chosen):
            dist, par = R.bfs(adj, s, lambda v: R.fat(cells, v))
            ents = [(dist[c], c) for c in comp if c in dist and 1800 <= dist[c] * 128 <= 7000 and D(c, CH) >= int(os.environ.get("ENTCH", "2500")) and min(D(c, n) for n in NEB) >= 1500]
            if not ents:
                continue
            ents.sort(reverse=True)
            top = ents[: max(1, len(ents) // 4)]
            top.sort(key=lambda e: (len(adj[e[1]]), -e[0]))
            ent = top[0][1]
            path = [ent]
            while path[-1] != s:
                path.append(par[path[-1]])
            thin = path[::3] + ([path[-1]] if (len(path) - 1) % 3 else [])
            nodes = [[round(cells[c][0], 1), round(cells[c][1], 1), round(cells[c][2] + 6, 1)] for c in thin]
            chosen.append(s)
            out.append(dict(name="guard%d" % len(out + [0]), nodes=nodes))
            print("route", len(out), "overlook", ovl(s), "nodes", len(nodes), "len", len(path) * 128, "entry", nodes[0], "stop", nodes[-1], "stop->neb1", round(D(s, NEB[0])), "lat", round(lat(s)))
        if len(chosen) >= 1:
            break
json.dump(out, open("scout/m3l3_guard_routes.json", "w"), indent=1)
print("routes", len(out))

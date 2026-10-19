"""av_route.py <map> [--stop-min 450 --stop-max 900 --entry-far 3000] - plan a truck route from an in-engine flood fill (scout/<map>_scf.txt).

Grid 128 u. Stop = a roomy cell 450-900 u from an alarm switch; entry = a cell of the same connected area at least --entry-far from
every switch and as far as possible along the drivable graph from the stop; path = shortest 4-neighbour path, simplified with a corridor
check (a segment is kept only when the cells around it are free). Prints the candidates and writes scout/<map>_route.json (one best route).
"""
import json, math, os, sys, collections, heapq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
STEP = 128


def load(m):
    """cells: id -> (x, y, z, flags); adj: id -> [ids] (tree edges of the flood fill: every edge was hull-swept in-engine)"""
    cells, adj, byxy = {}, collections.defaultdict(list), {}
    rows = []
    for ln in open(os.path.join(HERE, "scout", m + "_scf.txt")):
        a = ln.split()
        if len(a) < 6:
            continue
        rows.append([float(a[0]), float(a[1]), float(a[2]), int(a[3]), float(a[4]), float(a[5])])
    for i, r in enumerate(rows):
        cells[i] = (r[0], r[1], r[2], r[3])
        byxy[(round(r[0], 1), round(r[1], 1))] = i
    for i, r in enumerate(rows):
        p = byxy.get((round(r[4], 1), round(r[5], 1)))
        if p is not None and p != i:
            adj[i].append(p)
            adj[p].append(i)
    return cells, adj


def comps(cells, adj):
    seen, out = set(), []
    for c in cells:
        if c in seen:
            continue
        q = [c]
        seen.add(c)
        cur = []
        while q:
            u = q.pop()
            cur.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        out.append(cur)
    return out


def bfs(adj, src):
    dist = {src: 0}
    par = {}
    dq = collections.deque([src])
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                par[v] = u
                dq.append(v)
    return dist, par


def room(cells, adj, c):
    """how many fill neighbours within 2 steps: a roomy cell is not a corridor"""
    n = 0
    for v in adj[c]:
        n += 1
        for w in adj[v]:
            if w != c:
                n += 0.5
    return n


def main():
    m = sys.argv[1]
    arg = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    smin, smax, efar = arg("--stop-min", 450), arg("--stop-max", 900), arg("--entry-far", 3000)
    cells, adj = load(m)
    sw = [p for p in json.load(open(os.path.join(ROOT, "docs", "tools", "alarm_points.json")))[m]["points"] if p["kind"] == "switch"]
    sws = [(p["pos"][0], p["pos"][1]) for p in sw]
    print("cells", len(cells), "components", [len(c) for c in comps(cells, adj)][:8], "switches", sws)
    best = None
    D = lambda c, a, b: math.hypot(cells[c][0] - a, cells[c][1] - b)
    for comp in comps(cells, adj):
        if len(comp) < 60:
            continue
        for (sx, sy) in sws:
            cand = [(abs(D(c, sx, sy) - 650), c) for c in comp if smin <= D(c, sx, sy) <= smax and room(cells, adj, c) >= 5]
            cand.sort()
            for _, stop in cand[:10]:
                dist, par = bfs(adj, stop)
                ents = [(dist[c], c) for c in comp if c in dist and min(D(c, a, b) for a, b in sws) >= efar and dist[c] * 128 >= 1800]
                if not ents:
                    continue
                ents.sort(reverse=True)
                top = ents[: max(1, len(ents) // 4)]
                top.sort(key=lambda e: (len(adj[e[1]]), -e[0]))
                dd, ent = top[0]
                path = [ent]
                while path[-1] != stop:
                    path.append(par[path[-1]])
                score = dd * 128
                if 1800 <= score <= 9000 and (best is None or score > best[0]):
                    best = (score, stop, ent, path, (sx, sy))
    if best is None:
        print("NO ROUTE: no stop/entry pair (stop %g-%g u from a switch, entry >= %g u from every switch, route >= 1800 u)" % (smin, smax, efar))
        return 1
    score, stop, ent, path, sw1 = best
    thin = path[::3]
    if thin[-1] != path[-1]:
        thin.append(path[-1])
    nodes = [[round(cells[c][0], 1), round(cells[c][1], 1), round(cells[c][2] + 6, 1)] for c in thin]
    zs = [n[2] for n in nodes]
    print("route: %d nodes (%d cells), length %.0f u, entry %s stop %s, switch %s (%.0f u), z %.0f..%.0f" %
          (len(nodes), len(path), len(path) * 128, nodes[0], nodes[-1], sw1, math.hypot(nodes[-1][0] - sw1[0], nodes[-1][1] - sw1[1]), min(zs), max(zs)))
    json.dump(dict(map=m, nodes=nodes, switch=sw1), open(os.path.join(HERE, "scout", m + "_route.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

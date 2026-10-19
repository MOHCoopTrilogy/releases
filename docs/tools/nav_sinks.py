"""[bug-2901] Navmesh SINK finder: ground a bot can get INTO from a Push spawn but cannot get OUT of toward a home.

usage: python docs/tools/nav_sinks.py <navdump_home> [<baseline_navdump_home>] [map ...]
  navdump_home: a soak server home holding maintt/navdump/maps/<map>.bsp_mp.txt (soak or probe with +set nav_dump 1)
  baseline: a second home built with a change switched off (e.g. +set bot_navEntityBlocks 0 / bot_navLinkCheck 0);
            then only sinks that are NEW against it are listed.

Why: push_spawn_sweep.py proves every SPAWN reaches both homes; that missed round 13's t1l3 regression, where the prop
cut sealed the only exit of a pit bots FALL into from the spawn side (four axis bots stood in it for five minutes, no
route, one death in the round). A sink is reported by area (sq units) and centroid; tiny ones (< 4000 sq u, a crate
top, a sill) are noise and skipped.
"""
import os
import re
import sys
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEEDS = [os.path.join(ROOT, 'hzm-mohaa-coop-mod', 'coop_mod', f) for f in ('mp_push_bsp.scr', 'mp_push_maps.scr')]
RX = re.compile(r'spawn (info_player_\w+)\s+local\.e\.origin = \( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \)'
                r'(?:\s+local\.e\.angle = [\d.]+)?\s+local\.e\.targetname = "(\w+)"')


def seeds():
    out = {}
    for fn in SEEDS:
        for m in re.finditer(r'^seed_(\w+):(.*?)(?=^seed_|\Z)', open(fn, encoding='utf-8').read(), re.S | re.M):
            out[m.group(1)] = [(float(x), float(y), float(z), t) for c, x, y, z, t in RX.findall(m.group(2))]
    return out


def load(path):
    polys, fwd, back = {}, collections.defaultdict(set), collections.defaultdict(set)
    for line in open(path, encoding='latin-1'):
        p = line.split()
        if not p:
            continue
        if p[0] == 'P':
            n = int(p[5])
            vs = [(float(p[6 + 3 * i]), float(p[7 + 3 * i]), float(p[8 + 3 * i])) for i in range(n)]
            polys[p[1]] = (p[4] == '0' and p[2] != '54', vs)  # area 54: a live prop (excluded)
        elif p[0] == 'L':
            fwd[p[1]].add(p[2])
            back[p[2]].add(p[1])
    return polys, fwd, back


def area2(vs):
    s = 0.0
    for i in range(len(vs)):
        x1, y1 = vs[i][0], vs[i][1]
        x2, y2 = vs[(i + 1) % len(vs)][0], vs[(i + 1) % len(vs)][1]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def inside(x, y, vs):
    c = False
    j = len(vs) - 1
    for i in range(len(vs)):
        xi, yi, xj, yj = vs[i][0], vs[i][1], vs[j][0], vs[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi:
            c = not c
        j = i
    return c


class Mesh:
    def __init__(self, path):
        self.polys, self.fwd, self.back = load(path)
        self.grid = collections.defaultdict(list)
        for k, (g, vs) in self.polys.items():
            if not g or len(vs) < 3:
                continue
            for gx in range(int(min(v[0] for v in vs)) // 256, int(max(v[0] for v in vs)) // 256 + 1):
                for gy in range(int(min(v[1] for v in vs)) // 256, int(max(v[1] for v in vs)) // 256 + 1):
                    self.grid[(gx, gy)].append(k)

    def floor(self, pt, below=400.0, above=40.0):
        best = None
        for k in self.grid[(int(pt[0]) // 256, int(pt[1]) // 256)]:
            vs = self.polys[k][1]
            if inside(pt[0], pt[1], vs):
                dz = pt[2] - sum(v[2] for v in vs) / len(vs)
                if -above <= dz <= below and (best is None or abs(dz) < best[0]):
                    best = (abs(dz), k)
        return best[1] if best else None

    def bfs(self, starts, adj):
        seen = set(s for s in starts if s)
        q = collections.deque(seen)
        while q:
            u = q.popleft()
            for v in adj[u]:
                pv = self.polys.get(v)
                if pv and not pv[0] and len(pv[1]) >= 3:
                    continue  # a live prop's footprint (area 54): excluded by the bots' filter, so not a way through
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        return seen


def sinks(mesh, sp):
    homes = {}
    for x, y, z, t in sp:
        if t in ('alh', 'axh') and t not in homes:
            f = mesh.floor((x, y, z))
            if f:
                homes[t] = f
    if len(homes) < 2:
        return None
    reach_all = mesh.bfs([mesh.floor((x, y, z)) for x, y, z, t in sp], mesh.fwd)
    can_a = mesh.bfs([homes['alh']], mesh.back)
    can_x = mesh.bfs([homes['axh']], mesh.back)
    bad = {k for k in reach_all if mesh.polys.get(k, (False, []))[0] and len(mesh.polys[k][1]) >= 3
           and (k not in can_a or k not in can_x)}
    # cluster bad polys by adjacency (undirected)
    out, seen = [], set()
    for k in bad:
        if k in seen:
            continue
        comp, q = [], [k]
        seen.add(k)
        while q:
            u = q.pop()
            comp.append(u)
            for v in mesh.fwd[u] | mesh.back[u]:
                if v in bad and v not in seen:
                    seen.add(v)
                    q.append(v)
        a = sum(area2(mesh.polys[c][1]) for c in comp)
        if a < 4000:
            continue
        pts = [v for c in comp for v in mesh.polys[c][1]]
        cen = tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))
        which = ('allied' if any(c not in can_a for c in comp) else '') + ('/axis' if any(c not in can_x for c in comp) else '')
        out.append((a, cen, len(comp), which.strip('/')))
    return sorted(out, reverse=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    home, base = sys.argv[1], None
    rest = sys.argv[2:]
    if rest and os.path.isdir(rest[0]):
        base, rest = rest[0], rest[1:]
    sd = seeds()
    dumpdir = os.path.join(home, 'maintt', 'navdump', 'maps')
    maps = rest or sorted(f.split('.')[0] for f in os.listdir(dumpdir) if f.endswith('.bsp_mp.txt'))
    total = 0
    for m in maps:
        if m not in sd:
            continue
        path = os.path.join(dumpdir, m + '.bsp_mp.txt')
        if not os.path.exists(path):
            continue
        mesh = Mesh(path)
        s = sinks(mesh, sd[m])
        if s is None:
            print('%-6s homes without floor' % m)
            continue
        if base:
            bp = os.path.join(base, 'maintt', 'navdump', 'maps', m + '.bsp_mp.txt')
            if os.path.exists(bp):
                bmesh = Mesh(bp)
                bs = sinks(bmesh, sd[m]) or []
                # keep sinks whose centroid is not inside an existing baseline sink (by 256u proximity)
                s = [x for x in s if not any((x[1][0] - y[1][0]) ** 2 + (x[1][1] - y[1][1]) ** 2 < 256 ** 2 for y in bs)]
        total += len(s)
        print('%-6s %d sink(s)%s' % (m, len(s), ' NEW vs baseline' if base else ''))
        for a, c, n, which in s[:8]:
            print('         %7.0f sq u  %3d polys  at (%d %d %d)  cannot reach %s home' % (a, n, c[0], c[1], c[2], which))
    print('TOTAL', total)


if __name__ == '__main__':
    main()

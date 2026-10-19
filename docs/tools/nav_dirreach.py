"""[bug-2870] DIRECTED reachability on a nav_dump (L lines are Detour's directed poly links; fall links are one-way).
usage: dirreach.py <map> <x,y,z> [<x,y,z> ...] [--block x0,y0,z0,x1,y1,z1]
For each point: size of the region it can REACH, and whether it can reach / be reached from the biggest region."""
import sys, collections, os
m = sys.argv[1]; args = sys.argv[2:]
blocks = []
while '--block' in args:  # repeatable: every navlinks block of the map, to simulate them together
    i = args.index('--block'); blocks.append([float(v) for v in args[i + 1].split(',')]); args = args[:i] + args[i + 2:]
pts = [tuple(float(v) for v in a.split(',')) for a in args]
polys, out = {}, collections.defaultdict(set)
for line in open('server_home_soak/maintt/navdump/maps/%s.bsp_mp.txt' % m):
    p = line.split()
    if not p: continue
    if p[0] == 'P':
        nv = int(p[5]); polys[int(p[1])] = (int(p[4]), [tuple(float(a) for a in p[6 + 3 * k:9 + 3 * k]) for k in range(nv)])
    elif p[0] == 'L':
        out[int(p[1])].add(int(p[2]))
def cen(vs): return tuple(sum(v[i] for v in vs) / len(vs) for i in range(3))
dead = set()
for x0, y0, z0, x1, y1, z1 in blocks:
    ib = lambda c: x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and z0 <= c[2] <= z1
    dead |= {r for r, (t, vs) in polys.items() if (t == 0 and ib(cen(vs))) or (t != 0 and any(ib(v) for v in vs))}
if blocks:
    print('blocks remove', len(dead))
inn = collections.defaultdict(set)
for a, bs in out.items():
    for b in bs: inn[b].add(a)
def bfs(src, adj):
    seen = {src}; q = [src]
    while q:
        a = q.pop()
        for b in adj.get(a, ()):
            if b not in seen and b not in dead and b in polys: seen.add(b); q.append(b)
    return seen
def inside(x, y, vs):
    c = False; n = len(vs)
    for i in range(n):
        xa, ya = vs[i][0], vs[i][1]; xb, yb = vs[(i + 1) % n][0], vs[(i + 1) % n][1]
        if (ya > y) != (yb > y) and x < (xb - xa) * (y - ya) / (yb - ya) + xa: c = not c
    return c
SNAP = os.environ.get('SNAP') == '1'
def at(pt):
    if SNAP:  # like push_snapOne: the nearest floor 0..400u BELOW the point (40u above tolerated)
        hits = [(pt[2] - cen(vs)[2], r) for r, (t, vs) in polys.items() if t == 0 and r not in dead and inside(pt[0], pt[1], vs)]
        hits = [h for h in hits if -40 <= h[0] <= 400]
        return min(hits)[1] if hits else None
    hits = [(abs(cen(vs)[2] - pt[2]), r) for r, (t, vs) in polys.items() if t == 0 and r not in dead and inside(pt[0], pt[1], vs)]
    hits = [h for h in hits if h[0] < 120]
    return min(hits)[1] if hits else None
ground = [r for r, (t, vs) in polys.items() if t == 0 and r not in dead]
# the "main" region = what the largest-area reference point reaches: use the most-reached poly among a sample
import os
H = os.environ.get('HOMES')
homes = [tuple(float(v) for v in h.split(',')) for h in H.split(';')] if H else []
homeref = [at(h) for h in homes]
homefwd = [bfs(h, out) if h else set() for h in homeref]
ref = homeref[0] if homeref else max(ground, key=lambda r: len(out.get(r, ())))
mainfwd = bfs(ref, out)
for pt in pts:
    r = at(pt)
    if r is None: print(' ', pt, 'no poly'); continue
    fwd = bfs(r, out); bwd = bfs(r, inn)
    gf = sum(1 for q in fwd if polys[q][0] == 0)
    tags = []
    for i, (h, hf) in enumerate(zip(homeref, homefwd)):
        nm = 'AL' if i == 0 else 'AX'
        tags.append('%s: to %s from %s' % (nm, 'yes' if h in fwd else 'NO ', 'yes' if r in hf else 'NO '))
    print('  %-24s reaches %5d | %s' % (pt, gf, ' | '.join(tags)))

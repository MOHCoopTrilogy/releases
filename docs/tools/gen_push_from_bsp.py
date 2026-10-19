#!/usr/bin/env python3
# gen_push_from_bsp.py - AUTO-DERIVE MP Push spawn groups + battle-line zone chain for a campaign map
# straight from its compiled BSP, so campaign maps with no ViPER "King of the Map" conversion and no
# Base Assault layout can still be ported to Push without hand-capturing coordinates in-game.
#
# HOW: MOHAA BSPs (ident 'EALA', v21 / '2015' v19) carry an ASCII entity lump. We pull every info_pathnode
# origin (the AI navmesh blankets the walkable space) plus the SP info_player_start. The map's long axis is
# the farthest-apart node pair (2-pass diameter). We project all nodes onto that axis, split into N ordered
# bands (band 1 = the end nearest info_player_start = ALLIES home, band N = AXIS home), take each band's node
# AABB as its zone volume, and drop team spawn groups (alh/al2..al9, axh/ax2..ax9) into the bands so each
# team has spawns across the whole corridor keyed to the moving front - exactly the shape of the authored
# ViPER data in mp_push_maps.scr, just sourced from the map itself.
#
#   python docs/tools/gen_push_from_bsp.py t3l1 [t2l1 ...]        # print seed blocks + write mp_push_bsp.scr
#   python docs/tools/gen_push_from_bsp.py --all                  # regenerate every map already in the file
#
# Output: hzm-mohaa-coop-mod/coop_mod/mp_push_bsp.scr  (GENERATED - wired from mp_push.scr::push_seedAuthored
# as the fallback when the ViPER seed returns 0 zones). Coordinates are approximate/auto; a later hand pass
# can refine any map, but this makes it playable.
import os, sys, struct, zipfile, math, io

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
PAK_DIRS = ["main", "mainta", "maintt"]
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "hzm-mohaa-coop-mod", "coop_mod", "mp_push_bsp.scr")
N_ZONES = 10
N_GROUPS = 9          # alh + al2..al9  (home + 8 forward)
SPAWNS_PER_GROUP = 2  # ~2 per group per team -> ~18 each side, matches authored counts
HOME_SPAWNS = 3       # pinned home groups (alh/axh) get 3, like the ViPER authored layouts
# [bug-2870] per-map node EXCLUSIONS (x, y, z, radius): harvested nodes that make a broken spawn. A spawn picked
# here traps its bot for the whole round - soak evidence, not a guess (^~^~^ BOTSPAWN + a frozen BOTPROBE position).
EXCLUDE = {
    # m2l3 (Night Train): (-2713,-89,-464) freezes EVERY bot spawned there (3 of 3 across the heat rounds, moved 0u) -
    # a 341-spawn sweep found only this and the t3l1 one.
    "m2l3": [(-2713.0, -89.0, -464.0, 48.0)],
}


# [bug-2870] per-map node HEIGHT CAP: drop every node above zmax. t3l1 (Fall of Berlin): 1154 of its 1582 pathnodes are
# one flat layer at z~992 that is NOT a floor (the navmesh ground under it is z~-140, the SP start z-168). pick()'s
# median-height ground filter therefore put EVERY allied spawn ~1100u in the air - push_snapOne refuses a >384u drop, so
# bots fell out of the sky on each spawn, and the one under a roof (4136,7844) embedded its bot for the whole round.
EXCLUDE_ZMAX = {
    "t3l1": 700.0,
}


# [bug-2870] NAVMESH GROUND FILTER for maps whose pathnode cloud is unreliable: keep a node only if the bot navmesh
# (a nav_dump from a soak: server_home_soak/maintt/navdump/maps/<map>.bsp_mp.txt) has a MAIN-component floor under it
# within push_snapOne's reach (up to 384u below, 40u above). t3l1 after its height cap still put 12 of 36 spawns on
# navmesh islands or over nothing. Opt-in per map, so healthy maps keep their reviewed spawns byte-for-byte.
NAV_FILTER = {"t3l1"}
# [bug-2870 round 4] The PLAYABLE AREA filter: a node is kept only if its snapped floor is mutually reachable with the
# SP player start on the DIRECTED bot navmesh (the start can walk to it AND it can walk to the start). The all-maps
# spawn sweep found t2l3 (Ardennes Frost) with its axis home + spawns OUTSIDE the playable map, behind the boundary
# wall (0-1 deaths per run, the teams physically could not meet), plus floating spawns (e1l1/m1l3a/t1l1/t2l4 - dozens
# of in-game 'snap REFUSED'), island/sink spawns (t1l3 three groups, t1l1, m2l3). One rule covers all of them.
PLAYABLE_FILTER = {"t2l3", "t3l1", "e1l1", "t1l1", "t1l3", "t2l4", "m2l3", "t2l1", "e3l1"}
# m1l3a (Desert Road) is NOT in the set: its node cloud floats ~600u over floors outside every usable core (18 of 571
# nodes survive a re-seat) - it needs spawns from navmesh polys, not pathnodes. Its 7 floating spawns stay for now.
PLAYABLE_MIN_NODES = 60
# [bug-2870, user 2026-09-24 "fix desert roads"] maps whose pathnode cloud is unusable even after re-seating: spawn
# candidates are the playable core's FLOOR-POLY centres instead (bot navmesh), ends pinned to the current homes so the
# map keeps its orientation. m1l3a (Desert Road): 553 of 571 pathnodes sit ~600u over floors outside the core; its
# layout had 7 spawns floating beyond the 384u snap (players dropped from the sky, in-game 'snap REFUSED' x12).
NAVNODES = {"m1l3a"}
NAVDUMP = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "server_home_soak", "maintt", "navdump", "maps", "%s.bsp_mp.txt")
if os.environ.get("NAVDUMP_HOME"):  # e.g. NAVDUMP_HOME=server_home_test: read another soak server's dumps
    NAVDUMP = os.path.join(os.environ["NAVDUMP_HOME"], "maintt", "navdump", "maps", "%s.bsp_mp.txt")


def nav_grounded(mapname):
    path = NAVDUMP % mapname
    if not os.path.exists(path):
        raise SystemExit("NAV_FILTER map %s needs a nav dump: soak it with -Extra '+set,nav_dump,1' first" % mapname)
    polys, adj = {}, {}
    for line in open(path, encoding="latin-1"):
        p = line.split()
        if not p:
            continue
        if p[0] == "P" and (p[4] == "0" and p[2] != "54"):
            nv = int(p[5])
            polys[int(p[1])] = [tuple(float(v) for v in p[6 + 3 * k:9 + 3 * k]) for k in range(nv)]
        elif p[0] == "L":
            a, b = int(p[1]), int(p[2])
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    parent = {r: r for r in polys}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, bs in adj.items():
        for b in bs:
            if a in parent and b in parent:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb
    sizes = {}
    for r in polys:
        sizes[find(r)] = sizes.get(find(r), 0) + 1
    main = max(sizes, key=sizes.get)
    mainpolys = [(vs, min(v[0] for v in vs), max(v[0] for v in vs), min(v[1] for v in vs), max(v[1] for v in vs),
                  sum(v[2] for v in vs) / len(vs)) for r, vs in polys.items() if find(r) == main]

    def inside(x, y, vs):
        c = False
        n = len(vs)
        for i in range(n):
            x1, y1 = vs[i][0], vs[i][1]
            x2, y2 = vs[(i + 1) % n][0], vs[(i + 1) % n][1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    def ok(n):
        for vs, x0, x1, y0, y1, pz in mainpolys:
            if x0 <= n[0] <= x1 and y0 <= n[1] <= y1 and -40.0 <= n[2] - pz <= 384.0 and inside(n[0], n[1], vs):
                return True
        return False
    return ok


def nav_reach(mapname, homes):
    """[bug-2870] DIRECTED navmesh reachability filter: ok(node) is True only if the floor a spawn at `node` snaps onto
    (the nearest ground poly 0..400u below, 40u above tolerated - push_snapOne's reach) can REACH EVERY home on the bot
    navmesh, following Detour's directed links (fall links are one-way). e3l2 (Monte Cassino) had four band spawns in
    regions that reach neither home - one a 7-poly island, three in one-way sinks (a bot spawned at (416,3360) spent the
    round jump-climbing rubble in a pit with no route out). An undirected component check calls those connected."""
    path = NAVDUMP % mapname
    if not os.path.exists(path):
        raise SystemExit("nav_reach for %s needs a nav dump: soak it with -Extra '+set,nav_dump,1' first" % mapname)
    polys, inn = {}, {}
    for line in open(path, encoding="latin-1"):
        p = line.split()
        if not p:
            continue
        if p[0] == "P":
            nv = int(p[5])
            polys[int(p[1])] = ((p[4] == "0" and p[2] != "54"), [tuple(float(v) for v in p[6 + 3 * k:9 + 3 * k]) for k in range(nv)])
        elif p[0] == "L":
            inn.setdefault(int(p[2]), set()).add(int(p[1]))
    ground = [(r, vs, min(v[0] for v in vs), max(v[0] for v in vs), min(v[1] for v in vs), max(v[1] for v in vs),
               sum(v[2] for v in vs) / len(vs)) for r, (g, vs) in polys.items() if g]

    def inside(x, y, vs):
        c = False
        n = len(vs)
        for i in range(n):
            x1, y1 = vs[i][0], vs[i][1]
            x2, y2 = vs[(i + 1) % n][0], vs[(i + 1) % n][1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    def floor(n, loose=False):
        best = None
        for r, vs, x0, x1, y0, y1, pz in ground:
            if x0 <= n[0] <= x1 and y0 <= n[1] <= y1:
                dz = n[2] - pz
                if -40.0 <= dz <= 400.0 and inside(n[0], n[1], vs) and (best is None or dz < best[0]):
                    best = (dz, r)
        if best is None and loose:
            # a REFERENCE point (SP start / home) may stand on a vehicle or in an erosion gap: nearest floor within 160u
            for r, vs, x0, x1, y0, y1, pz in ground:
                cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                d = ((cx - n[0]) ** 2 + (cy - n[1]) ** 2) ** 0.5
                if d <= 160.0 and -40.0 <= n[2] - pz <= 400.0 and (best is None or d < best[0]):
                    best = (d, r)
        return best[1] if best else None

    can = None
    for h in homes:
        hr = floor(h, loose=True)
        if hr is None:
            raise SystemExit("nav_reach %s: home %s has no navmesh floor" % (mapname, h))
        seen, q = {hr}, [hr]  # backward BFS: every poly that can reach this home
        while q:
            a = q.pop()
            for b in inn.get(a, ()):
                if b in polys and not polys[b][0] and len(polys[b][1]) >= 3:
                    continue  # [bug-2901] a live prop's footprint (area 54) is no way through
                if b not in seen:
                    seen.add(b)
                    q.append(b)
        can = seen if can is None else (can & seen)

    def ok(n):
        f = floor(n)
        return f is not None and f in can
    return ok


def nav_from(mapname, src):
    """ok(node): the node's snapped floor is REACHABLE FROM `src` on the directed bot navmesh (companion of nav_reach)."""
    path = NAVDUMP % mapname
    polys, out = {}, {}
    for line in open(path, encoding="latin-1"):
        p = line.split()
        if not p:
            continue
        if p[0] == "P" and (p[4] == "0" and p[2] != "54"):
            nv = int(p[5])
            polys[int(p[1])] = [tuple(float(v) for v in p[6 + 3 * k:9 + 3 * k]) for k in range(nv)]
        elif p[0] == "L":
            out.setdefault(int(p[1]), set()).add(int(p[2]))
    ground = [(r, vs, min(v[0] for v in vs), max(v[0] for v in vs), min(v[1] for v in vs), max(v[1] for v in vs),
               sum(v[2] for v in vs) / len(vs)) for r, vs in polys.items()]

    def inside(x, y, vs):
        c = False
        n = len(vs)
        for i in range(n):
            x1, y1 = vs[i][0], vs[i][1]
            x2, y2 = vs[(i + 1) % n][0], vs[(i + 1) % n][1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    def floor(n, loose=False):
        best = None
        for r, vs, x0, x1, y0, y1, pz in ground:
            if x0 <= n[0] <= x1 and y0 <= n[1] <= y1:
                dz = n[2] - pz
                if -40.0 <= dz <= 400.0 and inside(n[0], n[1], vs) and (best is None or dz < best[0]):
                    best = (dz, r)
        if best is None and loose:
            # a REFERENCE point (SP start / home) may stand on a vehicle or in an erosion gap: nearest floor within 160u
            for r, vs, x0, x1, y0, y1, pz in ground:
                cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
                d = ((cx - n[0]) ** 2 + (cy - n[1]) ** 2) ** 0.5
                if d <= 160.0 and -40.0 <= n[2] - pz <= 400.0 and (best is None or d < best[0]):
                    best = (d, r)
        return best[1] if best else None
    s = floor(src, loose=True)
    if s is None:
        raise SystemExit("nav_from %s: source %s has no navmesh floor" % (mapname, src))
    seen, q = {s}, [s]
    while q:
        a = q.pop()
        for b in out.get(a, ()):
            if b not in seen:
                seen.add(b)
                q.append(b)

    def ok(n):
        f = floor(n)
        return f is not None and f in seen
    ok.floor = floor
    return ok


def nav_playable(mapname, src):
    """ok(node): the node's snapped floor lies in the PLAYABLE CORE = the largest strongly connected region (every poly
    can walk to every other, directed) among the polys reachable from the SP start. A start that is itself a one-way
    area (a truck bed, a barn loft you drop out of) is fine: the core is where it leads."""
    path = NAVDUMP % mapname
    polys, out, inn = {}, {}, {}
    for line in open(path, encoding="latin-1"):
        p = line.split()
        if not p:
            continue
        if p[0] == "P":
            nv = int(p[5])
            polys[int(p[1])] = ((p[4] == "0" and p[2] != "54"), [tuple(float(v) for v in p[6 + 3 * k:9 + 3 * k]) for k in range(nv)])
        elif p[0] == "L":
            a, b = int(p[1]), int(p[2])
            out.setdefault(a, set()).add(b)
            inn.setdefault(b, set()).add(a)
    if src is not None:
        reach_ok = nav_from(mapname, src)
        floor = reach_ok.floor
        s = floor(src, loose=True)
        fwd, q = {s}, [s]
        while q:
            a = q.pop()
            for b in out.get(a, ()):
                if b not in fwd:
                    fwd.add(b)
                    q.append(b)
    else:
        # no usable start (it rides a train / sits in a vehicle off the mesh): the whole mesh's largest SCC
        floor = nav_from(mapname, next(iter(polys[r][1][0] for r in polys if polys[r][0]))).floor
        fwd = set(polys)
    # Kosaraju restricted to fwd (iterative)
    order, seen = [], set()
    for v in fwd:
        if v in seen:
            continue
        stack = [(v, iter(out.get(v, ())))]
        seen.add(v)
        while stack:
            u, it = stack[-1]
            nxt = next((w for w in it if w in fwd and w not in seen), None)
            if nxt is None:
                order.append(u)
                stack.pop()
            else:
                seen.add(nxt)
                stack.append((nxt, iter(out.get(nxt, ()))))
    comp, best = {}, None
    for v in reversed(order):
        if v in comp:
            continue
        members, q = [v], [v]
        comp[v] = v
        while q:
            u = q.pop()
            for w in inn.get(u, ()):
                if w in fwd and w not in comp:
                    comp[w] = v
                    members.append(w)
                    q.append(w)
        size = sum(1 for m in members if polys[m][0])
        if best is None or size > best[0]:
            best = (size, v)
    core = {v for v, c in comp.items() if c == best[1]}

    def ok(n):
        f = floor(n)
        return f is not None and f in core

    gpolys = [(r, vs, min(v[0] for v in vs), max(v[0] for v in vs), min(v[1] for v in vs), max(v[1] for v in vs),
               sum(v[2] for v in vs) / len(vs)) for r, (g, vs) in polys.items() if g]

    def seat(n):
        """The node re-seated onto the FIRST floor below it (where a player spawned there lands, up to 2000u down),
        or None if that floor is not in the playable core (a roof, a pit, outside the map)."""
        best = None
        for r, vs, x0, x1, y0, y1, pz in gpolys:
            if x0 <= n[0] <= x1 and y0 <= n[1] <= y1 and -40.0 <= n[2] - pz <= 2000.0:
                c = False
                k = len(vs)
                for i in range(k):
                    xa, ya = vs[i][0], vs[i][1]
                    xb, yb = vs[(i + 1) % k][0], vs[(i + 1) % k][1]
                    if (ya > n[1]) != (yb > n[1]) and n[0] < (xb - xa) * (n[1] - ya) / (yb - ya) + xa:
                        c = not c
                if c and (best is None or pz > best[0]):
                    best = (pz, r)
        if best is None or best[1] not in core:
            return None
        return (n[0], n[1], best[0] + 16.0)
    ok.core_size = best[0]
    ok.seat = seat

    def area2(vs):
        return abs(sum(vs[i][0] * vs[(i + 1) % len(vs)][1] - vs[(i + 1) % len(vs)][0] * vs[i][1] for i in range(len(vs)))) / 2.0
    # floor-poly centres of the core (slivers < 40x40u dropped): a NAVNODES map's spawn candidates
    ok.core_centroids = [tuple(sum(v[i] for v in vs) / len(vs) for i in range(3))
                         for r, (g, vs) in polys.items() if g and r in core and area2(vs) >= 1600.0]
    return ok


def make_exclude(mapname, starts=None, nodes=None):
    spheres = EXCLUDE.get(mapname) or []
    zmax = EXCLUDE_ZMAX.get(mapname)
    grounded = nav_grounded(mapname) if mapname in NAV_FILTER else None
    if mapname in PLAYABLE_FILTER and starts and nodes is not None:
        pf = nav_playable(mapname, starts[0])
        kept = sum(1 for n in (nodes or []) if pf(n))
        if nodes is not None and kept < PLAYABLE_MIN_NODES:
            print("  .. %s: start-based core keeps only %d nodes (the SP start rides something off the mesh) - "
                  "using the whole mesh's largest strongly connected region" % (mapname, kept))
            pf = nav_playable(mapname, None)
            kept = sum(1 for n in (nodes or []) if pf(n))
        if nodes is not None and kept < PLAYABLE_MIN_NODES:
            print("  !! %s: playable filter keeps only %d nodes - NOT applied" % (mapname, kept))
        else:
            print("  .. %s: playable filter keeps %d of %d nodes (core %d polys)" % (mapname, kept, len(nodes or []),
                                                                             pf.core_size))
            g0 = grounded
            grounded = (lambda n: (g0 is None or g0(n)) and pf(n))
    if not spheres and zmax is None and grounded is None:
        return None
    return lambda n: ((zmax is not None and n[2] > zmax)
                      or any((n[0] - x) ** 2 + (n[1] - y) ** 2 + (n[2] - z) ** 2 <= r * r for x, y, z, r in spheres)
                      or (grounded is not None and not grounded(n)))

def find_bsp(mapname):
    """Return raw BSP bytes for maps/<mapname>.bsp from the GOG paks (later paks/dirs win, like the engine)."""
    hit = None
    for d in PAK_DIRS:
        pdir = os.path.join(GOG, d)
        if not os.path.isdir(pdir):
            continue
        for fn in sorted(os.listdir(pdir)):
            if not fn.lower().endswith(".pk3"):
                continue
            try:
                zf = zipfile.ZipFile(os.path.join(pdir, fn))
            except Exception:
                continue
            for nm in zf.namelist():
                if nm.lower() == f"maps/{mapname.lower()}.bsp":
                    hit = (os.path.join(pdir, fn), nm)
            zf.close()
    if not hit:
        return None
    zf = zipfile.ZipFile(hit[0]); data = zf.read(hit[1]); zf.close()
    return data

def entity_lump(bsp):
    """Locate + return the ASCII entity lump text of a MOHAA BSP by scanning the lump directory."""
    # header: ident[4] + version(int) [+ checksum(int) for EALA]; lump dir is (offset,length) int pairs.
    for base in (12, 8, 16):
        for i in range(0, 40):
            p = base + i * 8
            if p + 8 > len(bsp):
                break
            off, length = struct.unpack("<ii", bsp[p:p+8])
            if 0 < off < len(bsp) and 32 < length < 5_000_000 and off + length <= len(bsp):
                head = bsp[off:off+2000]
                if b"classname" in head or bsp[off:off+1] == b"{":
                    chunk = bsp[off:off+length]
                    if b"classname" in chunk:
                        return chunk.decode("latin-1", "replace")
    return None

def parse_entities(text):
    """Parse '{ "k" "v" ... }' blocks into list of dicts."""
    ents = []
    i = 0
    while True:
        a = text.find("{", i)
        if a < 0:
            break
        b = text.find("}", a)
        if b < 0:
            break
        body = text[a+1:b]
        d = {}
        # key/value pairs: "key" "value"
        j = 0
        while True:
            k1 = body.find('"', j)
            if k1 < 0:
                break
            k2 = body.find('"', k1+1)
            v1 = body.find('"', k2+1)
            v2 = body.find('"', v1+1)
            if min(k2, v1, v2) < 0:
                break
            d[body[k1+1:k2]] = body[v1+1:v2]
            j = v2 + 1
        ents.append(d)
        i = b + 1
    return ents

def vec(s):
    try:
        p = [float(x) for x in s.replace('"', '').split()]
        return (p[0], p[1], p[2]) if len(p) >= 3 else None
    except Exception:
        return None

def dist2(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2

def dist2_xy(a, b):
    # HORIZONTAL distance only. Maps are ground corridors; a full-3D farthest-pair on a vertically
    # stacked map (e.g. m3l1b Omaha bluffs/bunkers) cuts the axis diagonally THROUGH floors, scattering
    # spawns across disconnected heights so bots can't reach the front. XY keeps the axis along the ground.
    return (a[0]-b[0])**2 + (a[1]-b[1])**2

def harvest(mapname):
    bsp = find_bsp(mapname)
    if bsp is None:
        return None, f"BSP not found for {mapname}"
    text = entity_lump(bsp)
    if not text:
        return None, f"entity lump not located for {mapname}"
    ents = parse_entities(text)
    nodes = [vec(e["origin"]) for e in ents
             if e.get("classname") == "info_pathnode" and "origin" in e and vec(e["origin"])]
    starts = [vec(e["origin"]) for e in ents
              if e.get("classname") in ("info_player_start", "info_player_deathmatch") and "origin" in e and vec(e["origin"])]
    if len(nodes) < 20:
        # fall back to any positioned entity if the map is thin on pathnodes
        nodes = [vec(e["origin"]) for e in ents if "origin" in e and vec(e["origin"])]
    if len(nodes) < 8:
        return None, f"too few positioned entities in {mapname} ({len(nodes)})"
    return {"nodes": nodes, "starts": starts, "nent": len(ents)}, None

def component_filter(nodes, starts, radius=512.0):
    """Keep only ONE connected region of the node cloud - the component that contains the SP player start
    (else the largest). Some campaign maps (e3l1 Gothic Line) split into disconnected areas an intro/courtyard
    + the main map joined only by a scripted door pathnodes don't bridge; a farthest-pair axis across two such
    regions strands a team where it cannot path, and the front never moves (F5..5 stall). Restricting to one
    reachable region gives a coherent, playable corridor. A no-op on well-connected maps (~1 component)."""
    n = len(nodes)
    if n < 8:
        return nodes
    parent = list(range(n))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    from collections import defaultdict
    cell = radius; grid = defaultdict(list)
    for i, p in enumerate(nodes):
        grid[(int(p[0]//cell), int(p[1]//cell))].append(i)
    r2 = radius * radius
    for i, p in enumerate(nodes):
        cx, cy = int(p[0]//cell), int(p[1]//cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((cx+dx, cy+dy), []):
                    if j > i and (p[0]-nodes[j][0])**2 + (p[1]-nodes[j][1])**2 <= r2:
                        ra, rb = find(i), find(j)
                        if ra != rb: parent[ra] = rb
    comp = defaultdict(list)
    for i in range(n): comp[find(i)].append(i)
    chosen = None
    if starts:
        sp = starts[0]
        ni = min(range(n), key=lambda i: (nodes[i][0]-sp[0])**2 + (nodes[i][1]-sp[1])**2)
        chosen = find(ni)
    # fall back to the largest component if there is no start, or the start's region is tiny (<15% = a lobby)
    if chosen is None or len(comp[chosen]) < 0.15 * n:
        chosen = max(comp, key=lambda k: len(comp[k]))
    return [nodes[i] for i in comp[chosen]]

def derive(mapname, h, pins=None, exclude=None, skip_components=False):
    """pins = ((ax, ay), (xx, xy)): PIN the allies-home and axis-home ends instead of the auto farthest-pair
    [bug-2835, user 2026-09-23]. Used where the auto axis picks the wrong ends (m4l2: Viper's layout ignored the
    whole east half - the SP start/truck/tank depot; e3l3: allies + axis spawned on top of each other). With pins,
    the HOME groups (alh/axh) take the nodes nearest their pin (so allies really start at the SP truck, axis at the
    escape truck) and every other group is banded along the pin->pin axis as usual."""
    nodes, starts = h["nodes"], h["starts"]
    if not skip_components:
        # (a NAVNODES cloud is already one strongly connected navmesh region; its big-poly centres sit >512u apart and
        # this proximity clustering split it - it dropped Desert Road's whole west side, allied home included)
        nodes = component_filter(nodes, starts)
    if exclude:
        # [bug-2835] drop nodes OUTSIDE the push corridor (e.g. m5l1a: everything behind the map-end gate) so no
        # zone or spawn is placed there and bots are never directed into it.
        nodes = [n for n in nodes if not exclude(n)]
    if pins:
        A = min(nodes, key=lambda n: dist2_xy(n, pins[0]))
        B = min(nodes, key=lambda n: dist2_xy(n, pins[1]))
    else:
        # centroid, then 2-pass farthest-pair to get the long axis endpoints A,B
        cx = sum(n[0] for n in nodes)/len(nodes)
        cy = sum(n[1] for n in nodes)/len(nodes)
        cz = sum(n[2] for n in nodes)/len(nodes)
        c = (cx, cy, cz)
        A = max(nodes, key=lambda n: dist2_xy(n, c))
        B = max(nodes, key=lambda n: dist2_xy(n, A))
        # ALLIES home = endpoint nearest the SP player start (else A)
        if starts:
            sp = starts[0]
            if dist2_xy(B, sp) < dist2_xy(A, sp):
                A, B = B, A
    allied, axis = A, B
    # HORIZONTAL axis (XY): the front advances along the ground corridor, never diagonally through floors.
    ax = (axis[0]-allied[0], axis[1]-allied[1])
    axlen = math.sqrt(ax[0]**2 + ax[1]**2) or 1.0
    axu = (ax[0]/axlen, ax[1]/axlen)
    def proj(n):
        return ((n[0]-allied[0])*axu[0] + (n[1]-allied[1])*axu[1]) / axlen
    banded = [[] for _ in range(N_ZONES+1)]  # 1..N
    for n in nodes:
        t = proj(n)
        bi = int(t * N_ZONES) + 1
        bi = max(1, min(N_ZONES, bi))
        banded[bi].append(n)
    # zone AABB per physical band (pad a little; generous z so a crouched/elevated body still scores)
    PADXY, PADZ = 24.0, 80.0
    zones = {}
    for i in range(1, N_ZONES+1):
        b = banded[i] or banded[max(1, i-1)] or banded[min(N_ZONES, i+1)] or nodes
        xs = [p[0] for p in b]; ys = [p[1] for p in b]; zs = [p[2] for p in b]
        zones[i] = ((min(xs)-PADXY, min(ys)-PADXY, min(zs)-PADZ),
                    (max(xs)+PADXY, max(ys)+PADXY, max(zs)+PADZ))
    # yaw facing enemy
    allied_yaw = int(round(math.degrees(math.atan2(axu[1], axu[0]))) % 360)
    axis_yaw = (allied_yaw + 180) % 360
    # spawns: allied group g at band g; axis group g at band N+1-g. ~2 each, spread within the band.
    def pick(band_nodes, k):
        if not band_nodes:
            return []
        # GROUND FILTER: keep only nodes near the band's median height, so spawns land on the main floor
        # of that band, not on a roof or down a pit (m3l1b's bunker map had a ~2000u spawn z-spread).
        zs = sorted(p[2] for p in band_nodes)
        medz = zs[len(zs)//2]
        ground = [p for p in band_nodes if abs(p[2]-medz) <= 200.0]
        if len(ground) >= 1:
            band_nodes = ground
        if len(band_nodes) <= k:
            return band_nodes
        step = len(band_nodes) / float(k)
        return [band_nodes[int(i*step)] for i in range(k)]
    def pick_near(ref, k, min_sep=96.0):
        # [bug-2835] pinned HOME group: the k nodes nearest the pinned home node (3D, so they stay on its floor),
        # at least min_sep apart so the home spawns never stack into one clump.
        out = []
        for n in sorted(nodes, key=lambda n: dist2(n, ref)):
            if all(dist2_xy(n, o) >= min_sep * min_sep for o in out):
                out.append(n)
            if len(out) == k:
                break
        return out
    allied_spawns = []  # (origin, yaw, targetname)
    axis_spawns = []
    for g in range(1, N_GROUPS+1):
        if pins and g == 1:
            an = pick_near(allied, HOME_SPAWNS)
        else:
            an = pick(banded[min(g, N_ZONES)], SPAWNS_PER_GROUP)
        tn = "alh" if g == 1 else f"al{g}"
        for o in an:
            allied_spawns.append((o, allied_yaw, tn))
        xb = N_ZONES + 1 - g
        if pins and g == 1:
            xn = pick_near(axis, HOME_SPAWNS)
        else:
            xn = pick(banded[max(1, xb)], SPAWNS_PER_GROUP)
        tx = "axh" if g == 1 else f"ax{g}"
        for o in xn:
            axis_spawns.append((o, axis_yaw, tx))
    # [bug-2870 round 5] END ZONES = the HOME SPAWN clusters (as gen_push_pinned.py does). push_publishTargets sends each team
    # to the CENTRE of the enemy's end zone; a whole band's AABB centre can sit off the navmesh or on an island - t1l1's
    # allied end centre was on a region reaching neither home and its axis end centre had no floor, t3l1's were no-floor /
    # a 22-poly island - so bots chased goals they could never reach (partial paths: t1l1 allies hedge-jumped along
    # y~1900, t3l1 0-5 deaths a round). A home-spawn box's centre is on the floor those spawns stand on.
    def hbox(pts):
        xs = [q[0] for q in pts]; ys = [q[1] for q in pts]; zs = [q[2] for q in pts]
        return ((min(xs) - PADXY, min(ys) - PADXY, min(zs) - PADZ), (max(xs) + PADXY, max(ys) + PADXY, max(zs) + PADZ))
    def cluster(pts):
        # BSP home groups are picked ACROSS band 1 (t3l1's two axh sat 4000u apart - their box centre was off the mesh
        # again): use the MEDOID home spawn, so the goal centre IS a spawn standing on real ground
        if len(pts) <= 1:
            return pts
        # ...and only the medoid: even two spawns 400u apart put the box centre over a gap (t1l3, t2l4 end-zone check)
        med = min(pts, key=lambda a: sum(dist2_xy(a, b) for b in pts))
        return [med]
    home_a = cluster([o for (o, yaw, tn) in allied_spawns if tn == "alh"])
    home_x = cluster([o for (o, yaw, tn) in axis_spawns if tn == "axh"])
    if home_a:
        zones[1] = hbox(home_a)
    if home_x:
        zones[N_ZONES] = hbox(home_x)
    # home spawn origins for the score-return teleports
    retA = allied_spawns[0][0] if allied_spawns else allied
    retX = axis_spawns[0][0] if axis_spawns else axis
    return {"zones": zones, "allied": allied_spawns, "axis": axis_spawns,
            "retA": retA, "retX": retX, "spawnA": len(allied_spawns), "spawnX": len(axis_spawns)}

def fmt_v(v):
    return f"( {v[0]:.1f} {v[1]:.1f} {v[2]:.1f} )"

def emit_seed(mapname, d):
    L = []
    L.append(f"seed_{mapname}:")
    L.append("{")
    for (o, yaw, tn) in d["allied"]:
        L.append("\tlocal.e = spawn info_player_allied")
        L.append(f"\tlocal.e.origin = {fmt_v(o)}")
        L.append(f"\tlocal.e.angle = {yaw}")
        L.append(f'\tlocal.e.targetname = "{tn}"')
    for (o, yaw, tn) in d["axis"]:
        L.append("\tlocal.e = spawn info_player_axis")
        L.append(f"\tlocal.e.origin = {fmt_v(o)}")
        L.append(f"\tlocal.e.angle = {yaw}")
        L.append(f'\tlocal.e.targetname = "{tn}"')
    L.append(f"\tlevel.coop_mpPushZN = {N_ZONES}")
    z = d["zones"]
    for i in range(1, N_ZONES+1):
        L.append(f"\tlevel.coop_mpPushZAmin[{i}] = {fmt_v(z[i][0])}")
        L.append(f"\tlevel.coop_mpPushZAmax[{i}] = {fmt_v(z[i][1])}")
        xi = N_ZONES + 1 - i
        L.append(f"\tlevel.coop_mpPushZXmin[{i}] = {fmt_v(z[xi][0])}")
        L.append(f"\tlevel.coop_mpPushZXmax[{i}] = {fmt_v(z[xi][1])}")
    L.append(f"\tlevel.coop_mpPushZEndAmin = {fmt_v(z[N_ZONES][0])}")
    L.append(f"\tlevel.coop_mpPushZEndAmax = {fmt_v(z[N_ZONES][1])}")
    L.append(f"\tlevel.coop_mpPushZEndXmin = {fmt_v(z[1][0])}")
    L.append(f"\tlevel.coop_mpPushZEndXmax = {fmt_v(z[1][1])}")
    L.append(f"\tlevel.coop_mpPushRetA = {fmt_v(d['retA'])}")
    L.append(f"\tlevel.coop_mpPushRetX = {fmt_v(d['retX'])}")
    L.append(f"\tlevel.coop_mpPushAuthoredN = {N_ZONES}")
    L.append(f'\tprintln( "^~^~^ MPPUSHMAP seeded {mapname} (BSP-derived) spawns={d["spawnA"]+d["spawnX"]} zones={N_ZONES}" )')
    L.append("}end")
    return "\n".join(L)

def existing_maps():
    if not os.path.exists(OUT):
        return []
    maps = []
    for ln in open(OUT, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if ln.startswith("seed_") and ln.endswith(":"):
            maps.append(ln[5:-1])
    return maps

def prev_allied_homes(tag="alh"):
    """home-group origins per map from the CURRENT output file, read before it is rewritten (a fallback playable-core
    seed; NAVNODES pins). tag 'alh' = allies, 'axh' = axis."""
    out = {}
    if not os.path.exists(OUT):
        return out
    import re
    txt = open(OUT, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"^seed_(\w+):(.*?)(?=^seed_|\Z)", txt, re.S | re.M):
        out[m.group(1)] = [(float(a), float(b), float(c)) for a, b, c in re.findall(
            r'origin = \( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \)(?:\s+local\.e\.angle = [\d.]+)?\s+local\.e\.targetname = "%s"'
            % tag, m.group(2))]
    return out


def build(maps):
    blocks = {}
    prev_homes = prev_allied_homes()
    prev_axis = prev_allied_homes("axh")
    for m in maps:
        h, err = harvest(m)
        if err:
            print(f"  !! {m}: {err}")
            continue
        if m in NAVNODES:
            alh, axh = prev_homes.get(m, []), prev_axis.get(m, [])
            pf = None
            for ref in alh + ([h["starts"][0]] if h["starts"] else []):
                try:
                    pf = nav_playable(m, ref)
                    break
                except SystemExit:
                    continue
            if pf is None or not alh or not axh:
                print("  !! %s: NAVNODES needs a nav dump and the previous homes - left as authored" % m)
            else:
                nodes = [(c[0], c[1], c[2] + 16.0) for c in pf.core_centroids]
                print("  .. %s: spawn candidates = %d playable-core floor polys (core %d), ends pinned to the old homes"
                      % (m, len(nodes), pf.core_size))
                # pin each end to the first OLD home spawn that actually lands on the core (Desert Road's first alh floats)
                pa = next((p for p in alh if pf.seat(p) is not None), alh[0])
                px = next((p for p in axh if pf.seat(p) is not None), axh[0])
                d = derive(m, dict(h, nodes=nodes), pins=((pa[0], pa[1]), (px[0], px[1])), skip_components=True)
                blocks[m] = emit_seed(m, d)
                print(f"  ok {m}: navmesh nodes -> {d['spawnA']}A/{d['spawnX']}X spawns, {N_ZONES} zones")
                continue
        if m in PLAYABLE_FILTER:
            # [bug-2870] re-seat every node onto its landing floor and keep only playable-core ones (floating node clouds:
            # m1l3a ~z450 over a ~-190 floor, t1l1, t3l1 z992) - then no spawn floats and none sits off the core
            refs = ([h["starts"][0]] if h["starts"] else []) + prev_homes.get(m, []) + [None]
            for ref in refs:
                # the SP start's core; else the core round the CURRENT allied home (t1l1/e3l1: the start rides a plane /
                # sits off the mesh); else the whole mesh's largest strongly connected region
                try:
                    pf = nav_playable(m, ref)
                except SystemExit:
                    continue
                kept = [s for s in (pf.seat(n) for n in h["nodes"]) if s is not None]
                if len(kept) >= PLAYABLE_MIN_NODES:
                    break
            print("  .. %s: re-seated onto the playable core: %d of %d nodes (core %d polys)" %
                  (m, len(kept), len(h["nodes"]), pf.core_size))
            if len(kept) >= PLAYABLE_MIN_NODES:
                h = dict(h, nodes=kept)
                starts = h["starts"]
                if starts and pf.seat(starts[0]) is None:
                    # the start rides something off the core: seat the allies-home reference on the nearest core node
                    s0 = starts[0]
                    h["starts"] = [min(kept, key=lambda n: (n[0] - s0[0]) ** 2 + (n[1] - s0[1]) ** 2)]
        d = derive(m, h, exclude=make_exclude(m, h["starts"], None if m in PLAYABLE_FILTER else h["nodes"]))
        blocks[m] = emit_seed(m, d)
        print(f"  ok {m}: {h['nent']} entities, {len(h['nodes'])} nodes -> {d['spawnA']}A/{d['spawnX']}X spawns, {N_ZONES} zones")
    if not blocks:
        print("no maps generated"); return
    out = []
    out.append("//GENERATED by docs/tools/gen_push_from_bsp.py -- DO NOT HAND-EDIT (regenerate instead).")
    out.append("//Auto-derived MP Push spawn groups + battle-line zones for campaign maps with no ViPER/Base-Assault")
    out.append("//source data. Harvested from each map's BSP info_pathnode cloud (the AI navmesh). Approximate but")
    out.append("//playable; consumed by coop_mod/mp_push.scr exactly like the ViPER-authored mp_push_maps.scr data.")
    out.append("//Wired from mp_push.scr::push_seedAuthored as the fallback when the ViPER seed returns 0 zones.")
    out.append("//coop_mpRun-guarded; a compile canary on every MP boot.")
    out.append("alive:{")
    out.append("\tend 1")
    out.append("}end")
    out.append("")
    out.append("//Seed the BSP-derived frontline for the current map. Sets level.coop_mpPushAuthored[..] + N; returns N.")
    out.append("seed local.map:{")
    out.append("\tif( level.coop_mpRun != 1 ){ end 0 }")
    out.append("\tswitch( local.map ){")
    for m in sorted(blocks):
        out.append(f'\t\tcase "{m}":')
        out.append(f"\t\t\twaitthread seed_{m}")
        out.append("\t\t\tbreak")
    out.append("\t}")
    out.append("\tend level.coop_mpPushAuthoredN")
    out.append("}end level.coop_mpPushAuthoredN")
    out.append("")
    for m in sorted(blocks):
        out.append(blocks[m])
        out.append("")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"wrote {os.path.normpath(OUT)} ({len(blocks)} maps)")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)
    if args == ["--all"]:
        maps = existing_maps()
        if not maps:
            print("no existing maps in mp_push_bsp.scr to regenerate"); sys.exit(0)
    else:
        maps = args
    print(f"generating Push data for: {', '.join(maps)}")
    build(maps)

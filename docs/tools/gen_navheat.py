#!/usr/bin/env python3
"""Per-map bot HEAT MAPS for Push/MP bots (bug-2865) -> hzm-mohaa-coop-mod/navlinks/<map>_mp_heat.txt (GENERATED).

WHY: the bots already know every map's LAYOUT (the Recast navmesh, whole map), but not its EXPERIENCE - where bots
keep grinding on geometry the mesh thinks is walkable, where they spam jumps at a ledge they cannot clear, where
they die. Soak runs (docs/tools/bot_soak.ps1) record all of that; this turns it into navmesh COST volumes the engine
re-areas at build time (navigation_recast_load_ext.cpp ManualBlocks_Apply, tiers RECAST_AREA_COST1..4 = x2/x4/x8/x16).
A* then routes round bad ground whenever a sane alternative exists; a tier NEVER disconnects anything (the ground stays
walkable, only dearer), so the only route through a bad spot is still taken.

Signals per 128u x 128u x 96u cell, from ^~^~^ BOTPROBE samples of ALIVE bots:
  stuck  - wants to move (|fm| or |rm| > 20), speed < 12, not firing, NOT at its goal (gd >= 48)
           OR [bug-2867] makes no PROGRESS: pathing and wanting to move in >= 6 of its last 8 samples (4s), no enemy,
           not firing, yet < 64u net 2D displacement over them. Speed alone missed bots SLIDING on a slope the navmesh
           calls walkable (m4l2's MG42 hill: spd 30-150 all the time, z see-sawing 30-199, never getting anywhere)
  jumps  - jumping (um > 0 or jmp=1) while nearly still (speed < 60)
  deaths - the last alive position before a bot's al 1 -> 0 transition
  visits - every alive sample (the denominator)
Legit idling is excluded: bots that reached their goal (gd < 48), each bot's first SPAWN_SKIP samples after it spawns
(bots stand still a moment after spawning), and each navlinks "elevator" landing (waiting for the cab is correct).
[bug-2870] The spawn exclusion used to be SPATIAL (no cost within 320u of any respawn): it hid real multi-minute traps
that happen to sit near a spawn (m3l1b: 3 allies jump-stuck 2 min each on an obstacle beside their spawn; m2l1: an
axis bot wedged for the whole run) - with Push spawning across every held zone, "near a spawn" is much of the map.
Tiers: stuck ratio >= 0.8 -> 4 (x16), >= 0.6 -> 3 (x8), else 2 (x4) (needs >= STUCK_MIN samples, ratio >= 0.35);
jump-spam (>= JUMP_MIN, ratio >= 0.5) -> at least 3; deaths (>= 5, with an EXTRA requirement of >= 3x the map's median death
cell) -> 1 (x2, "danger": prefer a flank when one is about as short).

    python docs/tools/gen_navheat.py _soak_heatbase            # every map with a <map>.log in that dir
    python docs/tools/gen_navheat.py _soak_heatbase m4l2 e3l2  # just those
    python docs/tools/gen_navheat.py _soak_heatbase,_soak_heat1  # MERGE rounds (max tier per cell): a cell costed in
        # an earlier round stays costed even when the later round is clean there - the cost is WHY it is clean
    # A round from before a nav/geometry fix (props cut at build, bad links dropped - bugs 2893-2898) keeps costing the
    # traps that fix removed; that is only a detour, never a cut, so keep it in the merge (round 12 alone costed 0 cells
    # on m2l1, which the old rounds' costs took from 24% stuck to 2%) and add the fixed-build rounds on top.
"""
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(ROOT, "hzm-mohaa-coop-mod", "navlinks")
CELL, ZCELL = 128, 96
RX = re.compile(r'BOTPROBE e=(\d+) tm=(\w) al=(\d) hp=-?\d+ px=(-?[\d.]+) py=(-?[\d.]+) pz=(-?[\d.]+) spd=([\d.]+) '
                r'fm=(-?\d+) rm=(-?\d+) um=(-?\d+) fire=(\d+) blk=\d+ jmp=(\d+) pth=(\d+) gd=(-?[\d.]+)'
                r'(?: en=(-?\d+))?')
RXSPAWN = re.compile(r'BOTSPAWN e=\d+ tm=\w px=(-?[\d.]+) py=(-?[\d.]+)')  # [bug-2867] exact, when the dll logs it
SPAWN_SKIP = 6  # samples (3s at 500ms) ignored after each spawn
# thresholds are in SAMPLES at the bot_probe interval the heat soak uses (bot_soak.ps1 -ProbeMs 500): 12 = 6s stuck
STUCK_MIN, JUMP_MIN, DEATH_MIN = 12, 16, 5
PROG_N, PROG_WANT, PROG_R2 = 8, 6, 64 ** 2  # no-progress window: samples, of which wanting to move, max net move
LIFT_R2 = 224 ** 2
# [bug-2870] a TRAP = >= TRAP_MIN stuck samples (60s) at >= 80% of the cell's visits: bots that get IN and cannot get out.
# A cost cannot fix that (it only discourages entering; a bot already wedged, or one whose only route crosses the cell,
# stays stuck - round 1 kept costed traps on m3l1b/t3l1/t2l3/e1l1 at full strength). Reported, never auto-blocked: a
# block can disconnect a real route, so each trap gets a hand fix (navlinks block / fall link / spawn move).
TRAP_MIN = 120


def cell(x, y, z):
    return (int(x // CELL), int(y // CELL), int(z // ZCELL))


def elevator_landings(mapname):
    pts = []
    for fn in ("%s_mp.txt" % mapname, "%s.txt" % mapname):
        p = os.path.join(OUTDIR, fn)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="latin-1"):
            f = line.split("#")[0].split()
            # [bug-2912] >= 7: an elevator line may name its movers after the 7 numbers (cab= gate1= gate2=)
            if len(f) >= 7 and f[0].lower() == "elevator":
                v = [float(a) for a in f[1:7]]
                pts += [(v[0], v[1], v[2]), (v[3], v[4], v[5])]
    return pts


def analyse(logpath, mapname):
    visits, stuck, jumps, deaths = (collections.Counter() for _ in range(4))
    zs = collections.defaultdict(list)
    spawns = []
    exact = []
    last_alive = {}
    prev_al = {}
    lifts = elevator_landings(mapname)
    hist = collections.defaultdict(lambda: collections.deque(maxlen=PROG_N))  # e -> recent (x, y, wants&pathing)
    since = collections.Counter()  # e -> alive samples since its last (re)spawn
    for line in open(logpath, encoding="latin-1"):
        g = RX.search(line)
        if not g:
            s = RXSPAWN.search(line)
            if s:
                exact.append((float(s.group(1)), float(s.group(2))))
                se = re.search(r"BOTSPAWN e=(\d+)", line)
                if se:
                    since[se.group(1)] = 0
            continue
        e, al = g.group(1), g.group(3)
        x, y, z = float(g.group(4)), float(g.group(5)), float(g.group(6))
        spd, fm, rm, um = float(g.group(7)), int(g.group(8)), int(g.group(9)), int(g.group(10))
        fire, jmp, pth, gd = g.group(11) != "0", g.group(12) == "1", g.group(13) == "1", float(g.group(14))
        noenemy = g.group(15) in (None, "-1")
        if al == "0":
            hist.pop(e, None)
            since[e] = 0
            if prev_al.get(e) == "1" and e in last_alive:
                deaths[cell(*last_alive[e])] += 1
            prev_al[e] = "0"
            continue
        if prev_al.get(e) == "0":
            spawns.append((x, y))  # first alive sample after a death = a respawn position
        prev_al[e] = "1"
        last_alive[e] = (x, y, z)
        c = cell(x, y, z)
        visits[c] += 1
        zs[c].append(z)
        since[e] += 1
        if since[e] <= SPAWN_SKIP:
            continue
        if any((x - lx) ** 2 + (y - ly) ** 2 < LIFT_R2 and abs(z - lz) < 160 for lx, ly, lz in lifts):
            continue
        wants = abs(fm) > 20 or abs(rm) > 20
        h = hist[e]
        h.append((x, y, wants and pth and noenemy and not fire))
        slide = (len(h) == PROG_N and sum(1 for s in h if s[2]) >= PROG_WANT
                 and (h[0][0] - x) ** 2 + (h[0][1] - y) ** 2 < PROG_R2)
        if (wants and spd < 12 and not fire and gd >= 48) or slide:
            stuck[c] += 1
        if (um > 0 or jmp) and spd < 60:
            jumps[c] += 1

    if exact:
        spawns = exact  # the al 0->1 guess also fires on team switches and lands late at a 500ms probe interval

    tiers = {}
    for c, n in visits.items():
        t = 0
        s = stuck[c]
        if s >= STUCK_MIN and s / n >= 0.35:
            r = s / n
            t = 4 if r >= 0.8 else (3 if r >= 0.6 else 2)
        j = jumps[c]
        if j >= JUMP_MIN and j / n >= 0.5:
            t = max(t, 3)
        if t:
            tiers[c] = t
    dvals = sorted(v for v in deaths.values() if v > 0)
    med = dvals[len(dvals) // 2] if dvals else 0
    for c, d in deaths.items():
        if c not in tiers and d >= DEATH_MIN and d >= 3 * max(1, med):
            tiers[c] = 1
    traps = {c: (stuck[c], visits[c]) for c in visits if stuck[c] >= TRAP_MIN and stuck[c] >= 0.8 * visits[c]}
    return tiers, zs, len(spawns), sum(visits.values()), traps


def write(mapname, tiers, zs, nspawn, nsamples, src):
    out = os.path.join(OUTDIR, "%s_mp_heat.txt" % mapname)
    L = ["# GENERATED by docs/tools/gen_navheat.py from %s - DO NOT EDIT (regenerate instead). bug-2865" % src,
         "# %s: %d alive samples, %d respawns observed; %d costed cells (tier 1=x2 danger, 2=x4, 3=x8, 4=x16 stuck/jump)"
         % (mapname, nsamples, nspawn, len(tiers)),
         "# cost minx miny minz  maxx maxy maxz  tier   (read by game.dll with cm_variant mp: navlinks/<map>_mp_heat.txt)"]
    for c in sorted(tiers):
        z0 = min(zs[c]) - 32
        z1 = max(zs[c]) + 72
        L.append("cost %d %d %d  %d %d %d  %d" % (c[0] * CELL, c[1] * CELL, z0, (c[0] + 1) * CELL, (c[1] + 1) * CELL, z1,
                                                   tiers[c]))
    with open(out, "w", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    srcs = [s for s in sys.argv[1].split(",") if s]
    dirs = [os.path.join(ROOT, s) if not os.path.isabs(s) else s for s in srcs]
    maps = sys.argv[2:] or sorted({f[:-4] for d in dirs for f in os.listdir(d) if f.endswith(".log")})
    for m in maps:
        tiers, zs, ns, nv, used = {}, collections.defaultdict(list), 0, 0, []
        for s, d in zip(srcs, dirs):
            p = os.path.join(d, m + ".log")
            if not os.path.exists(p):
                continue
            t1, z1, n1, v1, tr = analyse(p, m)
            for c, (sn, vn) in tr.items():
                print("    TRAP %-6s %-16s cell (%d %d z%d..)  stuck %4d of %4d visits" % (m, s, c[0] * CELL, c[1] * CELL,
                                                                                         c[2] * ZCELL, sn, vn))
            for c, tier in t1.items():
                tiers[c] = max(tier, tiers.get(c, 0))
            for c, zl in z1.items():
                zs[c].extend(zl)
            ns += n1
            nv += v1
            used.append(s)
        if not used:
            print("  %-6s no log in %s" % (m, ",".join(srcs)))
            continue
        write(m, tiers, zs, ns, nv, "+".join(used))
        cnt = collections.Counter(tiers.values())
        print("  %-6s %6d samples  %3d cells costed  tiers %s  (%s)" % (m, nv, len(tiers), dict(sorted(cnt.items())),
                                                                        "+".join(used)))


if __name__ == "__main__":
    main()

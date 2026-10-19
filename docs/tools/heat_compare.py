#!/usr/bin/env python3
"""Before/after table for the Push bot HEAT MAP rounds (bug-2865/2867): one row per map, one column group per soak dir.

    python docs/tools/heat_compare.py _soak_heatbase _soak_heat1 [_soak_heat2 ...]

Per map and round:
  stuck%  - alive samples a bot spends stuck: gen_navheat's definition (wants to move + not moving + not firing + not at
            its goal) OR its no-progress window (sliding / see-sawing on terrain, < 64u net in 4s)
  jump%   - alive samples jumping while nearly still (the stuck-jump tell)
  A / X   - furthest each team's front got, 0% = own home .. 100% = enemy home (bot_soak_analyze.py, seeded homes)
  deaths  - completed bot deaths (the probe's al 1 -> 0 edge) - a proxy for how much the teams actually meet
Lower stuck%/jump% is better; fronts nearer 100% and more deaths mean the teams reach and fight each other.
Soaks are noisy (one 6-minute run per map); read a change of a few points as noise, not signal.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot_soak_analyze as bsa  # noqa: E402
import gen_navheat as gh  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def metrics(logpath, mapname):
    alive = stuck = jumps = deaths = 0
    hist = collections.defaultdict(lambda: collections.deque(maxlen=gh.PROG_N))
    prev_al = {}
    since = collections.Counter()
    lifts = gh.elevator_landings(mapname)
    for line in open(logpath, encoding="latin-1"):
        g = gh.RX.search(line)
        if not g:
            continue
        e, al = g.group(1), g.group(3)
        x, y, z = float(g.group(4)), float(g.group(5)), float(g.group(6))
        spd, fm, rm, um = float(g.group(7)), int(g.group(8)), int(g.group(9)), int(g.group(10))
        fire, jmp, pth, gd = g.group(11) != "0", g.group(12) == "1", g.group(13) == "1", float(g.group(14))
        noenemy = g.group(15) in (None, "-1")
        if al == "0":
            if prev_al.get(e) == "1":
                deaths += 1
            prev_al[e] = "0"
            hist.pop(e, None)
            continue
        if prev_al.get(e) != "1":
            since[e] = 0
        prev_al[e] = "1"
        alive += 1
        since[e] += 1
        if since[e] <= gh.SPAWN_SKIP:  # same post-spawn grace as gen_navheat
            continue
        if any((x - lx) ** 2 + (y - ly) ** 2 < gh.LIFT_R2 and abs(z - lz) < 160 for lx, ly, lz in lifts):
            continue
        wants = abs(fm) > 20 or abs(rm) > 20
        h = hist[e]
        h.append((x, y, wants and pth and noenemy and not fire))
        slide = (len(h) == gh.PROG_N and sum(1 for s in h if s[2]) >= gh.PROG_WANT
                 and (h[0][0] - x) ** 2 + (h[0][1] - y) ** 2 < gh.PROG_R2)
        if (wants and spd < 12 and not fire and gd >= 48) or slide:
            stuck += 1
        if (um > 0 or jmp) and spd < 60:
            jumps += 1
    r = bsa.analyse_map(logpath)
    fa = r.get("ta", {}) or {}
    fx = r.get("tx", {}) or {}
    return {"stuck": 100.0 * stuck / max(1, alive), "jump": 100.0 * jumps / max(1, alive), "deaths": deaths,
            "fa": fa.get("maxfront"), "fx": fx.get("maxfront"), "alive": alive}


def pct(v):
    return "  -" if v is None else "%3.0f" % (v * 100)


def main():
    dirs = sys.argv[1:]
    if len(dirs) < 1:
        raise SystemExit(__doc__)
    paths = [os.path.join(ROOT, d) if not os.path.isabs(d) else d for d in dirs]
    maps = sorted({f[:-4] for p in paths if os.path.isdir(p) for f in os.listdir(p) if f.endswith(".log")})
    head = "%-6s" % "MAP" + "".join(" | %-30s" % os.path.basename(d)[:30] for d in dirs)
    sub = "%-6s" % "" + "".join(" | %-30s" % "stuck jump   A%  X%  deaths" for _ in dirs)
    print(head)
    print(sub)
    print("-" * len(sub))
    tot = [collections.Counter() for _ in dirs]
    for m in maps:
        row = "%-6s" % m
        for i, p in enumerate(paths):
            lp = os.path.join(p, m + ".log")
            if not os.path.exists(lp):
                row += " | %-30s" % "(no run)"
                continue
            k = metrics(lp, m)
            row += " | %4.1f%% %4.1f%%  %s %s  %5d " % (k["stuck"], k["jump"], pct(k["fa"]), pct(k["fx"]), k["deaths"])
            tot[i]["maps"] += 1
            tot[i]["stuck"] += k["stuck"]
            tot[i]["jump"] += k["jump"]
            tot[i]["deaths"] += k["deaths"]
        print(row)
    print("-" * len(sub))
    row = "%-6s" % "MEAN"
    for t in tot:
        n = max(1, t["maps"])
        row += " | %4.1f%% %4.1f%%  (%2d maps) %5.0f " % (t["stuck"] / n, t["jump"] / n, t["maps"], t["deaths"] / n)
    print(row)


if __name__ == "__main__":
    main()

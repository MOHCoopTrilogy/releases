"""LIBERATION time limits, per map, from the placement sweep (sweep_place.json).

The bots-only clear test cannot time a clear: a 3-bot Allied squad is wiped by 16 Germans in about 75 s (mohdm6), so no
bot ever finishes a map. What the sweep does give is where the Germans stand and where the player starts, measured in the
running game. From those:

    methodical clear  =  walk + fights
    walk    = greedy nearest-neighbour tour from the player's start through the Germans' posts, at WALK u/s
              (a careful advance: run speed is ~250 u/s, a player checking corners averages well under half of it)
    fights  = FIGHT seconds per German (find, engage, confirm)
    limit   = MULT x methodical clear, clamped to the 6..12 minute guide, whole minutes

Two limits per map (at the lowest and the highest German count); the engine interpolates on the contract's count.
usage: python lib_limits.py <sweep_place.json>       prints the table and the LIB_POOL rows
"""
import json
import math
import sys

WALK = 110.0
FIGHT = 10.0
MULT = 2.0
LO, HI = 6, 12


def tour(eye, spots):
    left = [tuple(s) for s in spots]
    at = tuple(eye)
    d = 0.0
    while left:
        j = min(range(len(left)), key=lambda i: math.dist(at, left[i]))
        d += math.dist(at, left[j])
        at = left.pop(j)
    return d


def uniq(spots):
    out = []
    for s in spots:
        if all(math.dist(s, o) > 48 for o in out):
            out.append(s)
    return out


def limit(eye, spots, n):
    sub = spots[:n]
    clear = tour(eye, uniq(sub)) / WALK + FIGHT * n
    return clear, max(LO, min(HI, int(round(MULT * clear / 60.0))))


def main():
    rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8") if l.strip().startswith("{")]
    print("%-28s %5s %5s %4s %4s %5s %6s %6s  %s" % ("map", "want", "placed", "uniq", "vis", "float", "moved", "clear", "limits"))
    pool = []
    for r in rows:
        sp = r.get("spots") or []
        if not sp or not r.get("eye"):
            print("%-28s  NO PLACEMENT  %s" % (r["map"], r.get("fail")))
            continue
        want = r["germans"][0]
        u = uniq(sp)
        phi = r["germans"][1]                       # the pool's top count; fewer placed = the map could not seat them all
        hi = min(phi, len(u), r["placed"] - 1 if r["placed"] < phi else phi)
        hi = max(12, hi)
        lo = max(12, min(hi, int(round(hi * 0.68))))
        c0, l0 = limit(r["eye"], sp, lo)
        c1, l1 = limit(r["eye"], sp, hi)
        moved = max((t[2] for t in r.get("track", [])), default=0)
        print("%-28s %5d %5d %4d %4d %5d %6d %6.0f  %d..%d min for %d..%d  errs=%d" % (
            r["map"], want, r["placed"], len(u), r["visible"], r["floating"], moved, c1, l0, l1, lo, hi, r["script_errors"]))
        pool.append('    "%s": (%d, %d, %d, %d),' % (r["map"], lo, hi, l0, l1))
    print()
    print("\n".join(sorted(pool)))


if __name__ == "__main__":
    main()

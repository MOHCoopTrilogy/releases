#!/usr/bin/env python3
"""ops_botwatch.py - are the bots lost? Reads the OPSBOT lines (mp_ops.scr ops_botlog, coop_mpOpsBotLog 1) of an ops_sweep
--ops run and scores each map:

  stuck    a bot alive for 20 s that moved less than 96 units in that time
  loop     a bot alive for 40 s that walked over 1200 units but ended within 160 units of where it started
  idle%    share of alive 2-s samples with less than 16 units of movement
  reach    (objective maps) share of bots that came within 600 units of a charge at least once

    python ops_botwatch.py <qconsole.log> [...]        one line per log, and a JSON summary
"""
import json, math, re, sys

RX = re.compile(r"OPSBOT t=([\d.]+) e(\d+) team=(\w+) hp=([-\d.]+) o=\( ?([-\d.]+) ([-\d.]+) ([-\d.]+) ?\)")
RXC = re.compile(r"OPS charge \S+ node at \( ?([-\d.]+) ([-\d.]+) ([-\d.]+) ?\)")


def d(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def score(path):
    log = open(path, "rb").read().decode("latin-1")
    charges = [tuple(map(float, m)) for m in RXC.findall(log)]
    bots = {}
    for m in RX.finditer(log):
        t, e, team, hp, x, y, z = m.groups()
        bots.setdefault(e, []).append((float(t), team, float(hp), (float(x), float(y), float(z))))
    stuck = loop = idle = alive = 0
    stuck_team = {"allies": 0, "axis": 0}
    lastteam = {}
    flagged = set()
    reach = set()
    for e, s in bots.items():
        s.sort()
        seg = []
        for t, team, hp, o in s + [(1e9, "", -1, (0, 0, 0))]:
            if hp > 0 and team in ("allies", "axis"):
                seg.append((t, o))
                lastteam[e] = team
                if charges and min(d(o, c) for c in charges) < 600:
                    reach.add(e)
                continue
            # a life ended: score it
            for i in range(1, len(seg)):
                alive += 1
                if d(seg[i][1], seg[i - 1][1]) < 16:
                    idle += 1
            for i in range(len(seg)):
                j = next((k for k in range(i, len(seg)) if seg[k][0] - seg[i][0] >= 20), None)
                if j is not None and max(d(seg[k][1], seg[i][1]) for k in range(i, j + 1)) < 96:
                    stuck += 1
                    stuck_team[lastteam.get(e, "allies")] += 1
                    flagged.add(e)
                    break
            for i in range(len(seg)):
                j = next((k for k in range(i, len(seg)) if seg[k][0] - seg[i][0] >= 40), None)
                if j is None:
                    break
                walked = sum(d(seg[k][1], seg[k - 1][1]) for k in range(i + 1, j + 1))
                if walked > 1200 and d(seg[j][1], seg[i][1]) < 160:
                    loop += 1
                    flagged.add(e)
                    break
            seg = []
    r = {"log": path, "bots": len(bots), "stuck_lives": stuck, "stuck_by_team": stuck_team, "looping_lives": loop,
         "idle_pct": round(100.0 * idle / alive, 1) if alive else None, "bots_flagged": len(flagged),
         "charges": len(charges), "reach_pct": round(100.0 * len(reach) / len(bots), 1) if (bots and charges) else None,
         "kills": len(re.findall(r"\] \S+ (was |blew himself|took himself)", log))}
    return r


if __name__ == "__main__":
    out = [score(p) for p in sys.argv[1:]]
    for r in out:
        print(json.dumps(r))

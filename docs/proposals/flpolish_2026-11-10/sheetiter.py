#!/usr/bin/env python3
"""sheetiter - curate fl_levels.json "clip_keep" (the player-clip sheets that bound the level) with the walk audit.

Dev-time only, on the developer's own converted pak (LOCAL; nothing it reads is committed - the list it writes holds
only (disc chunk, triangle index) pairs, indexes into the player's disc like every other entry in fl_levels.json).

  python sheetiter.py <workdir> <baseline cells.npy> [--level 1_1] [--rounds 6]

Each round: convert (workdir/conv.py <pak>, which also writes <pak>.dropped.json: every dropped sheet's id and
centre), run geoaudit --cells, then find where the walker got OUT: reachable cells more than `escape` from every
cell the baseline (all sheets in place) reached, and every void fall. The dropped sheets nearest the ENTRY of each
escape (new cells next to the baseline region) and nearest each void fall go on the keep list. Stops when nothing
escapes. A sheet only bounds the level where the walker escapes past it, so everything else stays dropped.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LV = os.path.join(ROOT, "docs", "tools", "frontline", "fl_levels.json")
GEO = os.path.join(ROOT, "docs", "tools", "byoaudit", "geoaudit.py")


def grid_index(cells, cell=64.0):
    g = {}
    for i, c in enumerate(cells):
        g.setdefault((int(c[0] // cell), int(c[1] // cell)), []).append(i)
    return g


def near_any(g, cells, p, r, cell=64.0, dz=96.0):
    n = int(r // cell) + 1
    kx, ky = int(p[0] // cell), int(p[1] // cell)
    for dx in range(-n, n + 1):
        for dy in range(-n, n + 1):
            for i in g.get((kx + dx, ky + dy), ()):
                c = cells[i]
                if (c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 <= r * r and abs(c[2] - p[2]) < dz:
                    return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir")
    ap.add_argument("baseline")
    ap.add_argument("--level", default="1_1")
    ap.add_argument("--map", default="coop_fl_1_1")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--escape", type=float, default=160.0)
    a = ap.parse_args()
    base = np.load(a.baseline)
    gb = grid_index(base)
    for rnd in range(a.rounds):
        pak = "si%d_fl_%s.pk3" % (rnd, a.level)
        subprocess.run([sys.executable, "conv.py", pak], cwd=a.workdir, capture_output=True, check=True)
        out = os.path.join(a.workdir, "audit_si%d" % rnd)
        subprocess.run([sys.executable, GEO, pak, a.map, out, "--cells"], cwd=a.workdir, capture_output=True,
                       check=True)
        rep = json.load(open(os.path.join(out, "geoaudit.json")))
        cells = np.load(os.path.join(out, "cells.npy"))
        dropped = json.load(open(os.path.join(a.workdir, pak + ".dropped.json")))
        dc = np.array([d[1] for d in dropped], float) if dropped else np.zeros((0, 3))
        # escaped cells: far from everything the baseline reached
        esc = [c for c in cells if not near_any(gb, base, c, a.escape)]
        ge = grid_index(esc) if esc else {}
        # entry points: escaped-region cells... approximated by new cells (not within 32u of the baseline) that touch
        # an escaped cell's region and the baseline region both
        entry = [c for c in cells if not near_any(gb, base, c, 32.0) and near_any(gb, base, c, 96.0)
                 and esc and near_any(ge, esc, c, a.escape * 3)]
        voids = [v[0] for v in rep["void_clusters"]]
        s = rep["summary"]
        print(rnd, "escaped", len(esc), "entries", len(entry), "voids", s["void_falls"],
              {k: s[k] for k in ("walkable_cells", "invisible_on_route", "route_blocks", "pathnodes_unreachable")},
              flush=True)
        if not esc and s["void_falls"] == 0:
            break
        lv = json.load(open(LV, encoding="utf-8"))
        keep = {tuple(k) for k in lv[a.level].get("clip_keep", [])}
        n0 = len(keep)
        for p in entry + voids:
            if not len(dc):
                break
            d = np.hypot(dc[:, 0] - p[0], dc[:, 1] - p[1]) + 0.5 * np.abs(dc[:, 2] - p[2])
            for j in np.argsort(d)[:2]:
                if d[j] < 200 and dropped[j][0] is not None:
                    keep.add(tuple(dropped[j][0]))
        print("   keep", n0, "->", len(keep), flush=True)
        if len(keep) == n0:
            break
        lv[a.level]["clip_keep"] = sorted([list(k) for k in keep])
        json.dump(lv, open(LV, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()

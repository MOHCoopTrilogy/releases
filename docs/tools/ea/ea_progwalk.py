#!/usr/bin/env python3
"""ea_progwalk - PROGRESSION WALK of coop_ea_1_11 (our code; reads the local pak and a mission log, writes local).

Can a player who starts at the original's start physically reach, in order, every place the original's mission
sends him: each volume trigger the mission fired and each use point (demolition charges, plunger), in the order a
mission run fired them? Offline, on the pak's own collision with the engine's box-trace rules (byoaudit
mapgeo/geoaudit flood): the STAND hull first, the CROUCH hull where standing does not get through.

A point counts as reached when a flooded cell lies within 96u in plan and 80u in height of it (trigger volumes and
use radii are larger). Any point that is not reached is a PROGRESSION BLOCK: reported with the nearest reached cell
(where the walk stops) and the collision source that stops it. Dynamic blockers the mission removes itself (the
gates, the partisan leader's doorway blocker) are inline models and script entities - not in this static walk.

  python ea_progwalk.py <pk3> <mission server log> <outdir>
"""
import json
import math
import os
import re
import sys
import zipfile

BYO = os.environ.get("BYOAUDIT", r"C:\hzm-root-flpolish\docs\tools\byoaudit")
sys.path.insert(0, BYO)
import geoaudit  # noqa: E402
import mapgeo    # noqa: E402

PT = re.compile(r'level\.ea_trig_pos\[(\d+)\] = \( (-?\d+) (-?\d+) (-?\d+) \)')
NM = re.compile(r'level\.ea_lo_name\[(\d+)\] = "([^"]+)"')


def main():
    pk3, log, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    data = zipfile.ZipFile(pk3).read("maps/coop_ea_1_11_data.scr").decode("latin-1")
    pos = {int(i): (float(x), float(y), float(z)) for i, x, y, z in PT.findall(data)}
    names = {int(i): n for i, n in NM.findall(data)}
    name2i = {n: i for i, n in names.items()}
    shp = {int(i): int(v) for i, v in re.findall(r'level\.ea_lo_shape\[(\d+)\] = (\d+)', data)}
    rad = {int(i): float(v) for i, v in re.findall(r'level\.ea_lo_r\[(\d+)\] = (-?\d+)', data)}
    hx = {int(i): float(v) for i, v in re.findall(r'level\.ea_lo_hx\[(\d+)\] = (-?\d+)', data)}
    hy = {int(i): float(v) for i, v in re.findall(r'level\.ea_lo_hy\[(\d+)\] = (-?\d+)', data)}
    hz = {int(i): float(v) for i, v in re.findall(r'level\.ea_lo_hz\[(\d+)\] = (-?\d+)', data)}
    cls = dict((int(i), c) for i, c in re.findall(r'level\.ea_lo_cls\[(\d+)\] = "([^"]+)"', data))
    st = re.search(r"level\.ea_player = \( (-?\d+) (-?\d+) (-?\d+) \)", data)
    start = tuple(float(v) for v in st.groups())
    # the route: every trigger / use point in the order the mission run fired it
    route, seen_i = [], set()
    for m in re.finditer(r"\^~\^~\^ (?:EATRIG (\d+) \S+|EAUSE used (\S+))", open(log, encoding="latin-1").read()):
        i = int(m.group(1)) if m.group(1) else name2i.get(m.group(2))
        if i is None or i in seen_i or i not in pos:
            continue
        seen_i.add(i)
        route.append((i, names.get(i, "?"), pos[i]))
    M = mapgeo.MapGeo.load(pk3, "coop_ea_1_11")
    g, _n, _b = M.ground(start[0], start[1], start[2] + 8, start[2] - 512)
    seeds = [(start[0], start[1], g)]
    res = {}
    for hname, hh in (("stand", mapgeo.STAND_H), ("crouch", mapgeo.CROUCH_H)):
        seen, _bl, _v, _d, _w = geoaudit.flood(M, seeds, 16.0, hh)
        res[hname] = [(k[0] * 16.0, k[1] * 16.0, z) for k, z in seen.items()]
    import numpy as np
    S = np.array(res["stand"])
    C = np.array(res["crouch"])

    def near(A, p, i=None):
        # inside the trigger's own volume (the script's test: sphere radius / box half-extents + 32, height +-320 /
        # hz + 160); use points (charges, plunger): within 80u of the use box, the use reach
        d = np.hypot(A[:, 0] - p[0], A[:, 1] - p[1])
        r, vz = 96.0, 80.0
        if i is not None and cls.get(i) in ("DemoCharge", "CSATrigger"):
            r, vz = 120.0, 96.0
        elif i is not None and shp.get(i) == 1:
            r, vz = rad.get(i, 96.0), 320.0
        elif i is not None and shp.get(i) == 2:
            r, vz = max(hx.get(i, 48.0), hy.get(i, 48.0)) + 32, hz.get(i, 64.0) + 160
        ok = (d < r) & (np.abs(A[:, 2] - p[2]) < vz)
        j = int(np.argmin(d + 1000 * (np.abs(A[:, 2] - p[2]) >= 200)))
        return bool(ok.any()), A[j], float(d[j])
    walk, blocks = [], []
    for i, nm, p in route:
        ok_s, _c, _d = near(S, p, i)
        ok_c, cc, dc = near(C, p, i)
        how = "stand" if ok_s else ("crouch" if ok_c else "BLOCKED")
        walk.append({"i": i, "name": nm, "pos": p, "reach": how})
        if how == "BLOCKED":
            blocks.append({"i": i, "name": nm, "pos": p, "nearest_reached": [round(v) for v in cc], "gap": round(dc)})
    rep = {"start": start, "route_points": len(route), "reached_stand": sum(w["reach"] == "stand" for w in walk),
           "reached_crouch_only": sum(w["reach"] == "crouch" for w in walk), "progression_blocks": len(blocks),
           "blocks": blocks, "walk": walk, "stand_cells": len(S), "crouch_cells": len(C)}
    json.dump(rep, open(os.path.join(out, "progwalk.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("walk",)}, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""progwalk - the PROGRESSION WALK of a converted map: can a player who starts at the drop physically reach every
trigger and objective the original intended, in mission order, with nothing in the way?

  python progwalk.py <pk3> <map> <outdir> [--order x+y] [--step 16]

Physics as geoaudit (mapgeo = the engine's box traces over the BSP brushes, the map's own step height): a flood
from the player starts, first with the STAND hull; whatever the stand flood cannot reach is retried with the CROUCH
hull (allowed only where the drawn level is lower than a standing man - a crawl space the original made you crouch
through). Every target (the data script's level.fl_trig[] with its radius, and the objective spots in level.fl_pos[])
must have a reachable floor cell inside its radius, at most 160u above or below the point.
Writes <outdir>/progwalk.json: per target in order - reached standing / crouching / NOT, the path length from the
previous target, the cells where the walk had to crouch, and for every unreached target the nearest reached cell and
the brush that stops the walk toward it (its collision source: the original's own surface or ours).
"""
import argparse
import collections
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapgeo  # noqa: E402
import geoaudit  # noqa: E402

PT = re.compile(r'^\s*level\.(fl_trig|fl_pos)\[("?[\w ]+"?)\]\s*=\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)', re.M)
RR = re.compile(r'^\s*level\.fl_trig_r\[(\d+)\]\s*=\s*(-?[\d.]+)', re.M)


def flood_parents(M, seeds, step, hull_h, deadly):
    W = geoaudit.Walker(M, step)
    seen, par = {}, {}
    q = collections.deque()
    for s in seeds:
        k = (int(round(s[0] / step)), int(round(s[1] / step)), int(s[2] // 16))
        if k not in seen:
            seen[k] = s[2]
            par[k] = None
            q.append(k)
    while q:
        k = q.popleft()
        x, y, z = k[0] * step, k[1] * step, seen[k]
        for d in geoaudit.DIRS:
            nz, kind, _info = W.try_move((x, y), z, d, hull_h)
            if nz is None:
                continue
            nx, ny = x + d[0] * step, y + d[1] * step
            if any(lo[0] < nx < hi[0] and lo[1] < ny < hi[1] and nz < lo[2] - 40 for lo, hi in deadly):
                continue
            k2 = (int(round(nx / step)), int(round(ny / step)), int(nz // 16))
            if k2 in seen:
                continue
            seen[k2] = nz
            par[k2] = k
            q.append(k2)
    return seen, par


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pk3")
    ap.add_argument("map")
    ap.add_argument("outdir")
    ap.add_argument("--order", default="x+y")
    ap.add_argument("--step", type=float, default=16.0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    M = mapgeo.MapGeo.load(a.pk3, a.map)
    geoaudit.STEP = M.step
    t = M.read("maps/%s_data.scr" % a.map).decode("latin-1")
    rad = {int(m.group(1)): float(m.group(2)) for m in RR.finditer(t)}
    targets = []
    for m in PT.finditer(t):
        name, key = m.group(1), m.group(2).strip('"')
        p = tuple(float(v) for v in m.group(3, 4, 5))
        if name == "fl_trig":
            targets.append(("trigger %s" % key, p, max(192.0, rad.get(int(key), 192.0))))
        elif key.startswith(("M1_1_", "MObjective")):
            targets.append(("objective %s" % key, p, 96.0))
    key_ = lambda tp: eval(a.order, {}, {"x": tp[1][0], "y": tp[1][1]})   # noqa: E731 - our CLI expression
    targets.sort(key=key_, reverse=True)
    wl = {int(m.group(1)): tuple(map(float, m.group(2, 3, 4))) for m in re.finditer(
        r"level\.fl_water_lo\[(\d+)\] = \( (\S+) (\S+) (\S+) \)", t)}
    wh = {int(m.group(1)): tuple(map(float, m.group(2, 3, 4))) for m in re.finditer(
        r"level\.fl_water_hi\[(\d+)\] = \( (\S+) (\S+) (\S+) \)", t)}
    deadly = [(wl[k], wh[k]) for k in sorted(wl) if k in wh]
    spawns = [tuple(map(float, e["origin"].split())) for e in M.entities
              if e.get("classname") in ("info_player_start", "info_player_allied", "info_player_deathmatch")]
    seeds = []
    for s in spawns:
        z, _n, _b = M.ground(s[0], s[1], s[2] + 8, s[2] - 512)
        if z is not None:
            seeds.append((s[0], s[1], z))
    stand, par_s = flood_parents(M, seeds, a.step, mapgeo.STAND_H, deadly)
    crouch, par_c = flood_parents(M, seeds, a.step, mapgeo.CROUCH_H, deadly)
    st = np.array([(k[0] * a.step, k[1] * a.step, z) for k, z in stand.items()])
    cr_keys = list(crouch)
    cr = np.array([(k[0] * a.step, k[1] * a.step, crouch[k]) for k in cr_keys])

    def find(cells, p, r, ztol):
        d = np.hypot(cells[:, 0] - p[0], cells[:, 1] - p[1])
        ok = (d <= r) & (np.abs(cells[:, 2] - p[2]) < ztol)
        if not ok.any():
            return None, float(d.min()) if len(d) else None
        return int(np.argmin(np.where(ok, d, np.inf))), None

    def path(par, k):
        out = []
        while k is not None:
            out.append(k)
            k = par[k]
        return out[::-1]
    report = []
    blocks = []
    prev = None
    skipped = []
    for name, p, r in targets:
        # Frontline's triggers are tall volumes (their record point often sits 150-800u up, over the street): any floor
        # inside the radius counts. An objective spot with nothing drawn and no floor under it is a marker in empty
        # space (MObjective_1_1, 600u outside the playable area), not a place to walk to.
        ztol = 1e9 if name.startswith("trigger") else 160.0
        if name.startswith("objective"):
            f_, e_, b_, n_, ss_ = M.trace(p, (p[0], p[1], p[2] - 512), (0, 0, 0), (0, 0, 0))
            if f_ >= 1.0 and M.render_ray(p, (p[0], p[1], p[2] - 512)) >= 1.0:
                skipped.append({"target": name, "at": [round(v) for v in p], "why": "marker: nothing drawn or solid under it"})
                continue
        i, _ = find(st, p, r, ztol)
        how = "stand"
        if i is None:
            j, dmin = find(cr, p, r, ztol)
            if j is None:
                how = "NOT REACHED"
                # where the walk stops toward it: the nearest crouch-reached cell and the brush between
                d = np.hypot(cr[:, 0] - p[0], cr[:, 1] - p[1])
                n = int(np.argmin(d))
                c = cr[n]
                f, end, b, nn, ss = M.trace((c[0], c[1], c[2] + 19), (p[0], p[1], c[2] + 19), (-15, -15, 0), (15, 15, 35))
                src = M.shaders[int(M.bshader[b])][0].rsplit("/", 1)[-1] if f < 1 else "-"
                blocks.append({"target": name, "at": [round(v) for v in p], "nearest_reached": [round(v) for v in c],
                               "gap": round(float(d[n])), "stopped_by": src, "stop_at": [round(float(v)) for v in end]})
                report.append({"target": name, "at": [round(v) for v in p], "reached": how})
                continue
            how = "crouch"
            pk = cr_keys[j]
            route = path(par_c, pk)
        else:
            k = (int(round(st[i][0] / a.step)), int(round(st[i][1] / a.step)), int(st[i][2] // 16))
            route = path(par_s, k)
        # where the walk has to crouch: cells on the path where a STANDING box does not fit (a low ceiling) - past a
        # crawl hole the rest of the way is walked upright again
        def low(k):
            z_ = crouch.get(k, stand.get(k))
            return M.trace((k[0] * a.step, k[1] * a.step, z_ + 1), (k[0] * a.step, k[1] * a.step, z_ + 1.01),
                           *M.hull(mapgeo.STAND_H))[4]
        must = [r_ for r_ in route if low(r_)]

        def spot(k):
            # the low spot and what is over the head there (the collision's source: the original's surface or ours)
            x_, y_, z_ = k[0] * a.step, k[1] * a.step, crouch.get(k, stand.get(k))
            f_, e_, b_, n_, ss_ = M.trace((x_, y_, z_ + 1), (x_, y_, z_ + 200), (-15, -15, 0), (15, 15, 1))
            src_ = M.shaders[int(M.bshader[b_])][0].rsplit("/", 1)[-1] if f_ < 1 else "-"
            return [round(x_), round(y_), round(z_), round(f_ * 199) if f_ < 1 else None, src_]
        report.append({"target": name, "at": [round(v) for v in p], "reached": how,
                       "path_from_drop_u": round(len(route) * a.step),
                       "crouch_cells_on_path": len(must),
                       "crouch_at": [spot(r_) for r_ in must[:: max(1, len(must) // 6 or 1)]][:6]})
        prev = p
    out = {"pk3": os.path.basename(a.pk3), "step_height": M.step, "targets": len(targets),
           "reached_standing": sum(1 for r_ in report if r_["reached"] == "stand"),
           "reached_crouching": sum(1 for r_ in report if r_["reached"] == "crouch"),
           "progression_blocks": len(blocks), "blocks": blocks, "skipped": skipped, "walk": report}
    json.dump(out, open(os.path.join(a.outdir, "progwalk.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("targets", "reached_standing", "reached_crouching", "progression_blocks")}))
    for b in blocks:
        print("BLOCK", b)


if __name__ == "__main__":
    main()

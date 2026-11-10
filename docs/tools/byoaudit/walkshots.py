#!/usr/bin/env python3
"""walkshots - the MISSION WALK: dense stills along a converted map's route, for visual QA (holes, see-through
foliage, floating props, missing floors). Our code. The stills contain converted disc content: LOCAL ONLY, never
committed or published.

  python walkshots.py <pk3> <map> <outdir> [--order x+y|-x|...] [--every 1] [--limit N] [--sp]

Route = the map's own trigger points and objective positions from its data script (level.fl_trig[] / level.fl_pos[]
or the EA equivalents matched by --points), ordered along the mission by --order (an expression over x, y: points
are visited largest first). At each point: one still looking toward the next point and one looking back, from eye
height above the floor (noclip, god, notarget, no HUD, no viewmodel), plus one high oblique still every 4th point.
Writes <outdir>/<n>_<a|b|o>.tga and route.json (point, ground z, view angles).
"""
import argparse
import json
import math
import os
import re
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import byoclient  # noqa: E402
import mapgeo  # noqa: E402

PT = re.compile(r'level\.(\w+)(\[[^\]]*\])?\s*=\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)')


def route(pk3, mapname, points_rx, order):
    t = zipfile.ZipFile(pk3).read("maps/%s_data.scr" % mapname).decode("latin-1")
    pts = [(m.group(1) + (m.group(2) or ""), (float(m.group(3)), float(m.group(4)), float(m.group(5))))
           for m in PT.finditer(t) if re.match(points_rx, m.group(1))]
    key = lambda p: eval(order, {}, {"x": p[1][0], "y": p[1][1]})   # noqa: E731 - our own CLI expression
    pts.sort(key=key, reverse=True)
    M = mapgeo.MapGeo.load(pk3, mapname)
    out = []
    for name, p in pts:
        g = M.ground(p[0], p[1], p[2] + 400, p[2] - 900)[0]
        if g is None:
            g = M.ground(p[0], p[1], p[2] + 40, p[2] - 900)[0]
        out.append({"name": name, "pos": p, "ground": g if g is not None else p[2]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pk3")
    ap.add_argument("map")
    ap.add_argument("outdir")
    ap.add_argument("--points", default=r"^fl_(trig|pos|start)$")
    ap.add_argument("--order", default="x+y")
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    R = route(a.pk3, a.map, a.points, a.order)[::a.every]
    if a.limit:
        R = R[:a.limit]
    views = []
    for i, r in enumerate(R):
        nxt = R[min(i + 1, len(R) - 1)]["pos"] if i + 1 < len(R) else R[i - 1]["pos"]
        x, y = r["pos"][0], r["pos"][1]
        yaw = math.degrees(math.atan2(nxt[1] - y, nxt[0] - x)) if i + 1 < len(R) else \
            math.degrees(math.atan2(y - nxt[1], x - nxt[0]))
        z = r["ground"] + 8           # tele puts the FEET here; the eye is +82
        views.append(("%03d_a" % i, (x, y, z), (6, yaw)))
        views.append(("%03d_b" % i, (x, y, z), (6, yaw + 180)))
        if i % 4 == 0:
            views.append(("%03d_o" % i, (x - 300 * math.cos(math.radians(yaw)), y - 300 * math.sin(math.radians(yaw)),
                                         z + 420), (40, yaw)))
    json.dump({"route": R, "views": views}, open(os.path.join(a.outdir, "route.json"), "w"), indent=1)
    with byoclient.Client(a.map, sets=[("coop_fltest", "0"), ("coop_eatest", "0")], coop=False, w=960, h=540) as c:
        if not c.wait(r"Spawning Entities Done|FLAI |EAAI ", 300):
            raise RuntimeError("map never loaded")
        time.sleep(8)
        c.step(["noclip", "wait 5", "god", "wait 5", "notarget", "wait 5", "cg_drawviewmodel 0", "cg_hud 0",
                "ui_hud 0", "r_drawentities 1"])
        for name, (x, y, z), (p, yw) in views:
            c.step(["tele %.0f %.0f %.0f" % (x, y, z), "wait 3", "face %.1f %.1f 0" % (p, yw), "wait 40",
                    "screenshot wk_" + name, "wait 6"])
            c.grab("wk_" + name, a.outdir)
        c.keep_log(os.path.join(a.outdir, "qconsole.log"))
    print("stills:", len(views))


if __name__ == "__main__":
    main()

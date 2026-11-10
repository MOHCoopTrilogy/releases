#!/usr/bin/env python3
"""geoaudit - walkability / invisible-wall / floor-hole / crouch-opening / grounding audit of a converted
bring-your-own-disc map, run OFFLINE on the player's own local pak with the engine's collision rules
(mapgeo.MapGeo = CM_BoxTrace over the BSP brushes). Our code; nothing it reads is ever committed.

  python geoaudit.py <pk3> <mapname> <outdir> [--data maps/<map>_data.scr] [--step 16] [--png]

What it does
  1. FLOOD FILL from every player spawn (info_player_start / _allied / _deathmatch) with the STAND hull
     (x/y +-15, z 0..94, step 18 - bg_pmove.cpp PM_CheckDuck / STEPSIZE): 4-neighbour moves on a <step>u grid,
     Quake step-slide (straight, else step up 18 and over), drop to the floor, slopes steeper than 0.7 not standable.
  2. Every move the stand hull cannot make is retried CROUCHED (54) and PRONE (20). Each blocked move is classified
       visible   - drawn geometry is within 8u of the blocking contact (a real wall: fine)
       INVISIBLE - nothing drawn near the contact: an invisible wall
       opening   - drawn geometry blocks the upper body but the low rays (10/30/45u) pass: a visible crawl/crouch hole;
                   'opening_ok' when the crouch or prone hull gets through, 'opening_blocked' when collision fills it
  3. FLOOR HOLES: a free move whose drop finds no floor within 2048u (falls out of the world), and walkable cells whose
     floor has no drawn surface under the feet (you see the underside / the void through the floor).
  4. GROUNDING: every point in the data file (level.* = ( x y z ) placements) and every point entity in the BSP is
     dropped with a 30x30 box: floating (> 6u above the floor) or buried (starts in solid) is reported.
  5. ROUTE: every data-file point (objectives, AI, pickups) and every info_pathnode: reachable standing / only
     crouched / only prone / unreachable from the spawn region.
Results: <outdir>/geoaudit.json (+ geoaudit.png with --png). Counts are the numbers to track before/after a fix.
"""
import argparse
import collections
import json
import math
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mapgeo  # noqa: E402
from mapgeo import STAND_H, CROUCH_H, PRONE_H, STEP, HALF  # noqa: E402

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
PT_RX = re.compile(r'^\s*level\.(\w+)(\[[^\]]*\](?:\[[^\]]*\])?)?\s*=\s*\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)')


def data_points(text):
    out = []
    for line in text.splitlines():
        m = PT_RX.match(line)
        if m:
            out.append((m.group(1) + (m.group(2) or ""), (float(m.group(3)), float(m.group(4)), float(m.group(5)))))
    return out


class Walker:
    def __init__(self, M, step):
        self.M, self.g = M, step

    def try_move(self, p, z, d, h):
        """(new feet z, kind) or (None, 'blocked', contact) for a move of one grid step in direction d with hull h"""
        M, g = self.M, self.g
        mins, maxs = M.hull(h)
        x0, y0 = p
        x1, y1 = x0 + d[0] * g, y0 + d[1] * g
        # straight, feet lifted 1u (Quake keeps the box just off the floor)
        f, end, b, n, ss = M.trace((x0, y0, z + 1), (x1, y1, z + 1), mins, maxs)
        if f < 1.0:
            # step up: up STEP, across, back down
            fu, eu, _bu, _nu, _ = M.trace((x0, y0, z + 1), (x0, y0, z + 1 + STEP), mins, maxs)
            zu = eu[2]
            f2, e2, b2, n2, _ = M.trace((x0, y0, zu), (x1, y1, zu), mins, maxs)
            if f2 < 1.0:
                return None, "blocked", (end, b, n)
            start = (x1, y1, zu)
        else:
            start = (x1, y1, z + 1)
        fd, ed, bd, nd, ssd = M.trace(start, (x1, y1, start[2] - 2048), mins, maxs)
        if fd >= 1.0:
            return None, "void", (np.array(start), -1, nd)
        if nd[2] < 0.7:
            return None, "steep", (ed, bd, nd)
        nz = ed[2]
        if nz < z - 64:
            return nz, "drop", None
        return nz, "walk", None

    def classify(self, p, z, d, contact):
        """visible wall / INVISIBLE wall / visible low opening, from drawn geometry around the blocked contact"""
        M = self.M
        end = contact[0]
        # the contact face: the box front at the stop position
        cx, cy = end[0] + d[0] * (HALF + 2), end[1] + d[1] * (HALF + 2)
        near = 0
        tot = 0
        for dz in range(int(STEP + 6), int(STAND_H) + 1, 12):
            for lat in (-12, 0, 12):
                q = (cx + (lat if d[1] else 0), cy + (lat if d[0] else 0), z + dz)
                tot += 1
                if M.render_near(q, 8.0):
                    near += 1
        if near == 0:
            # past the contact there is no floor at all: a clip at the edge of the world (flcliff), not a wall in the way
            bx, by = end[0] + d[0] * (HALF + 24), end[1] + d[1] * (HALF + 24)
            f, e2, b2, n2, ss = M.trace((bx, by, z + 40), (bx, by, z - 2048), (0, 0, 0), (0, 0, 0))
            if f >= 1.0:
                return "edge"
            return "invisible"
        # low opening: rays at 10/30/45u pass 64u through, the 80u ray does not
        a = np.array((p[0], p[1], 0.0))
        dv = np.array((d[0], d[1], 0.0))
        low = all(M.render_ray(a + (0, 0, z + hz), a + dv * 64 + (0, 0, z + hz)) >= 1.0 for hz in (10, 30, 45))
        high = M.render_ray(a + (0, 0, z + 80), a + dv * 64 + (0, 0, z + 80)) < 1.0
        if low and high:
            return "opening"
        return "visible"


def flood(M, seeds, step, hull_h, limit=1500000):
    W = Walker(M, step)
    seen = {}
    q = collections.deque()
    for s in seeds:
        k = (int(round(s[0] / step)), int(round(s[1] / step)), int(s[2] // 16))
        if k not in seen:
            seen[k] = s[2]
            q.append((k[0] * step, k[1] * step, s[2]))
    blocked, voids, drops = [], [], 0
    while q and len(seen) < limit:
        x, y, z = q.popleft()
        for d in DIRS:
            nz, kind, info = W.try_move((x, y), z, d, hull_h)
            if nz is None:
                if kind == "blocked":
                    blocked.append(((x, y, z), d, info))
                elif kind == "void":
                    voids.append(((x, y, z), d))
                continue
            if kind == "drop":
                drops += 1
            k = (int(round((x + d[0] * step) / step)), int(round((y + d[1] * step) / step)), int(nz // 16))
            if k in seen:
                continue
            seen[k] = nz
            q.append((k[0] * step, k[1] * step, nz))
    return seen, blocked, voids, drops, W


def cluster(points, r=48.0):
    """greedy spatial clusters -> [(centre, n)]"""
    cl = []
    for p in points:
        for c in cl:
            if abs(c[0][0] - p[0]) < r and abs(c[0][1] - p[1]) < r and abs(c[0][2] - p[2]) < 96:
                c[1] += 1
                break
        else:
            cl.append([p, 1])
    return [(tuple(round(float(v)) for v in c[0]), c[1]) for c in cl]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pk3")
    ap.add_argument("mapname")
    ap.add_argument("outdir")
    ap.add_argument("--data", default=None, help="data script inside the pak (default maps/<map>_data.scr)")
    ap.add_argument("--step", type=float, default=16.0)
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(a.outdir, exist_ok=True)
    M = mapgeo.MapGeo.load(a.pk3, a.mapname)
    dtext = M.read(a.data or f"maps/{a.mapname}_data.scr")
    pts = data_points(dtext.decode("latin-1")) if dtext else []
    # placements only: trigger volumes, motion-path keys and audio are not things that stand on the floor
    pts = [(n, p) for n, p in pts if not re.match(r"^\w*_(trig|path|cue|music|jeepcrew)", n)]
    ents = M.entities
    spawns = [tuple(map(float, e["origin"].split())) for e in ents
              if e.get("classname") in ("info_player_start", "info_player_allied", "info_player_deathmatch")]
    seeds = []
    for s in spawns:
        z, _n, _b = M.ground(s[0], s[1], s[2] + 8, s[2] - 512)
        if z is not None:
            seeds.append((s[0], s[1], z))
    rep = {"pk3": os.path.basename(a.pk3), "map": a.mapname, "step": a.step, "seeds": len(seeds)}

    # ---- 1/2: reachability = a player who crouches where he must (CROUCH hull); blocked-move classification on it
    seen, blocked, voids, drops, W = flood(M, seeds, a.step, CROUCH_H)
    rep["walkable_cells"] = len(seen)
    seen_st, _b, _v, _d, _w = flood(M, seeds, a.step, STAND_H)
    rep["walkable_cells_stand"] = len(seen_st)
    # must-crouch cells: reachable, but a standing box does not fit there (doorway / beam head bumps, crawl holes)
    must = []
    for k, z in seen.items():
        x, y = k[0] * a.step, k[1] * a.step
        if M.trace((x, y, z + 1), (x, y, z + 1.01), *M.hull(STAND_H))[4]:
            must.append((x, y, z))
    rep["must_crouch_cells"] = len(must)
    rep["must_crouch_clusters"] = sorted(cluster(must, 64), key=lambda c: -c[1])
    cls = collections.Counter()
    inv_pts, open_blocked, open_ok = [], [], []
    inv_brushes = collections.Counter()
    for (x, y, z), d, info in blocked:
        c = W.classify((x, y), z, d, info)
        if c == "invisible":
            cls["invisible"] += 1
            inv_pts.append((x + d[0] * a.step / 2, y + d[1] * a.step / 2, z))
            inv_brushes[int(info[1])] += 1
        elif c == "opening":
            ok = None
            for hh, nm in ((PRONE_H, "prone"),):
                nz, kind, _ = W.try_move((x, y), z, d, hh)
                if nz is not None:
                    ok = nm
                    break
            (open_ok if ok else open_blocked).append(((x, y, z), d, ok))
            cls["opening_" + ("ok_" + ok if ok else "blocked")] += 1
        elif c == "edge":
            cls["edge_of_world"] += 1
        else:
            cls["visible"] += 1
    rep["blocked_moves"] = dict(cls)
    rep["invisible_brushes"] = len(inv_brushes)
    rep["invisible_clusters"] = sorted(cluster(inv_pts), key=lambda c: -c[1])
    rep["openings_blocked"] = sorted(cluster([p for p, _d, _o in open_blocked], 64), key=lambda c: -c[1])
    rep["openings_ok"] = sorted(cluster([p for p, _d, _o in open_ok], 64), key=lambda c: -c[1])
    # crouch-only area: flood again crouched from the stand region's cells to see what opens up
    # ---- 3: floor holes
    rep["void_falls"] = len(voids)
    rep["void_clusters"] = sorted(cluster([p for p, _d in voids], 64), key=lambda c: -c[1])
    undrawn = []
    for k, z in seen.items():
        x, y = k[0] * a.step, k[1] * a.step
        if not M.render_near((x, y, z - 2), 12.0):
            undrawn.append((x, y, z))
    rep["undrawn_floor_cells"] = len(undrawn)
    rep["undrawn_floor_clusters"] = sorted(cluster(undrawn, 64), key=lambda c: -c[1])[:200]
    # ---- 4: grounding of placements
    floating, buried = [], []
    for name, p in pts + [(e.get("classname"), tuple(map(float, e["origin"].split()))) for e in ents if "origin" in e]:
        if name and name.startswith("info_pathnode"):
            continue
        f, end, b, n, ss = M.trace(p, (p[0], p[1], p[2] - 512), (-15, -15, 0), (15, 15, 1))
        if ss:
            buried.append((name, p))
        elif f >= 1.0:
            floating.append((name, p, None))
        else:
            gap = p[2] - end[2]
            # data points carry +24 for actor drops (flpack); spawns +40: report the gap beyond that
            allow = 48 if name.startswith(("fl_", "ea_", "info_player")) else 8
            if gap > allow:
                floating.append((name, p, round(gap)))
    rep["placements_floating"] = floating
    rep["placements_buried"] = buried
    # ---- 5: reachability of placements and pathnodes
    sk = {}
    for k, z in seen.items():
        sk.setdefault((k[0], k[1]), []).append(z)

    def reach(p, r=48.0):
        n = int(math.ceil(r / a.step))
        kx, ky = int(round(p[0] / a.step)), int(round(p[1] / a.step))
        for dx in range(-n, n + 1):
            for dy in range(-n, n + 1):
                for z in sk.get((kx + dx, ky + dy), ()):
                    if abs(z - (p[2] - 24)) < 80:
                        return True
        return False
    unreach = [(nm, p) for nm, p in pts if not nm.startswith(("fl_cue", "fl_music")) and not reach(p, 64)]
    nodes = [tuple(map(float, e["origin"].split())) for e in ents if e.get("classname") == "info_pathnode"]
    un_nodes = [p for p in nodes if not reach(p, 48)]
    rep["data_points"] = len(pts)
    rep["data_unreachable"] = unreach
    rep["pathnodes"] = len(nodes)
    rep["pathnodes_unreachable"] = len(un_nodes)
    rep["pathnodes_unreachable_clusters"] = sorted(cluster(un_nodes, 200), key=lambda c: -c[1])
    # invisible walls on an intended route: within 96u of a Frontline/EA pathnode
    nk = collections.defaultdict(list)
    for p in nodes:
        nk[(int(p[0] // 128), int(p[1] // 128))].append(p)

    def near_node(p, r=96.0):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in nk.get((int(p[0] // 128) + dx, int(p[1] // 128) + dy), ()):
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < r * r and abs(q[2] - 16 - p[2]) < 96:
                        return True
        return False
    rep["invisible_on_route"] = sum(1 for p in inv_pts if near_node(p))
    # ROUTE BLOCKS: two of the level's own AI path points (info_pathnode, from the original's navpoints) <= 200u apart
    # with an open line between them as DRAWN (render rays at 30u and 60u reach) - a way the player can see - that a
    # crouching player cannot sweep along (step 18). Each one is an invisible wall or snag on an intended route.
    ng = collections.defaultdict(list)
    for i, p in enumerate(nodes):
        ng[(int(p[0] // 200), int(p[1] // 200))].append(i)
    rb = []
    npairs = 0
    for i, p in enumerate(nodes):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in ng.get((int(p[0] // 200) + dx, int(p[1] // 200) + dy), ()):
                    if j <= i:
                        continue
                    q = nodes[j]
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 > 200 * 200 or abs(q[2] - p[2]) > 40:
                        continue
                    za = M.ground(p[0], p[1], p[2] + 8, p[2] - 64, CROUCH_H)[0]
                    zb = M.ground(q[0], q[1], q[2] + 8, q[2] - 64, CROUCH_H)[0]
                    if za is None or zb is None:
                        continue
                    if any(M.render_ray((p[0], p[1], za + h), (q[0], q[1], zb + h)) < 1.0 for h in (30, 60)):
                        continue
                    npairs += 1
                    f, end, b, n, ss = M.trace((p[0], p[1], za + STEP + 1), (q[0], q[1], zb + STEP + 1), *M.hull(CROUCH_H - STEP))
                    if f < 1.0 and not ss:
                        rb.append(tuple(round(float(v)) for v in end))
    rep["route_pairs_open"] = npairs
    rep["route_blocks"] = len(rb)
    rep["route_block_clusters"] = sorted(cluster(rb, 64), key=lambda c: -c[1])
    rep["openings_blocked_on_route"] = sum(1 for p, _d, _o in open_blocked if near_node(p))
    rep["seconds"] = round(time.time() - t0, 1)
    summary = {k: rep[k] for k in ("walkable_cells", "walkable_cells_stand", "must_crouch_cells", "blocked_moves", "invisible_brushes", "invisible_on_route",
                                   "openings_blocked_on_route", "void_falls", "undrawn_floor_cells",
                                   "pathnodes", "pathnodes_unreachable", "data_points", "seconds")}
    summary["invisible_clusters"] = len(rep["invisible_clusters"])
    summary["route_pairs_open"] = rep["route_pairs_open"]
    summary["route_blocks"] = rep["route_blocks"]
    summary["route_block_clusters"] = len(rep["route_block_clusters"])
    summary["must_crouch_clusters"] = len(rep["must_crouch_clusters"])
    summary["openings_blocked_clusters"] = len(rep["openings_blocked"])
    summary["openings_ok_clusters"] = len(rep["openings_ok"])
    summary["void_clusters"] = len(rep["void_clusters"])
    summary["undrawn_floor_clusters"] = len(rep["undrawn_floor_clusters"])
    summary["placements_floating"] = len(floating)
    summary["placements_buried"] = len(buried)
    summary["data_unreachable"] = len(unreach)
    rep["summary"] = summary
    with open(os.path.join(a.outdir, "geoaudit.json"), "w") as f:
        json.dump(rep, f, indent=1, default=str)
    print(json.dumps(summary, indent=1))
    if a.png:
        png(M, seen, inv_pts, open_blocked, open_ok, voids, undrawn, nodes, os.path.join(a.outdir, "geoaudit.png"))


def png(M, seen, inv, ob, ok, voids, undrawn, nodes, path):
    """top-down map of the findings (LOCAL ONLY: the drawn footprint is converted disc geometry)"""
    from PIL import Image, ImageDraw
    lo, hi = M.lo, M.hi
    W = 2400
    s = W / max(hi[0] - lo[0], hi[1] - lo[1])
    Hh = int((hi[1] - lo[1]) * s) + 1

    def T(x, y):
        return ((x - lo[0]) * s, Hh - (y - lo[1]) * s)
    im = Image.new("RGB", (W, Hh), (0, 0, 0))
    dr = ImageDraw.Draw(im)
    for t in M.rtri[::2]:
        dr.polygon([T(p[0], p[1]) for p in t], fill=(38, 38, 38))
    st = 16
    for (kx, ky, _kz) in seen:
        x, y = T(kx * st, ky * st)
        dr.point((x, y), fill=(0, 90, 0))
    for p in nodes:
        x, y = T(p[0], p[1])
        dr.point((x, y), fill=(80, 80, 255))
    for p in undrawn:
        x, y = T(p[0], p[1])
        dr.rectangle((x - 1, y - 1, x + 1, y + 1), fill=(255, 140, 0))
    for p, _d in voids:
        x, y = T(p[0], p[1])
        dr.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255))
    for p in inv:
        x, y = T(p[0], p[1])
        dr.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(255, 0, 0))
    for p, _d, _o in ob:
        x, y = T(p[0], p[1])
        dr.rectangle((x - 3, y - 3, x + 3, y + 3), outline=(255, 0, 255))
    for p, _d, _o in ok:
        x, y = T(p[0], p[1])
        dr.rectangle((x - 3, y - 3, x + 3, y + 3), outline=(0, 255, 255))
    im.save(path)


if __name__ == "__main__":
    main()

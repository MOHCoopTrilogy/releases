#!/usr/bin/env python3
"""Re-derive a HAND-AUTHORED Push map's layout (docs/tools/push_spawns.json + docs/tools/push_zones.json ->
gen_push_maps.py) from the map's own BSP pathnodes, with the allies-home and axis-home ends PINNED (bug-2835).

WHY: the ViPER layouts are fixed coordinates. Where one uses the wrong part of the map (m4l2: only the WEST half;
m5l1a: the whole axis end sat BEHIND the map-end gate) re-authoring by hand in-game is slow. This reuses
gen_push_from_bsp.derive(pins=, exclude=) - the same banding the 18 BSP-derived maps use - and writes BOTH halves
of a map's Push data, because they are separate files and fixing only one was a real bug:
  * push_spawns.json  - the spawn groups (alh/al2..al9, axh/ax2..ax9)
  * push_zones.json   - the battle-line checkpoint boxes (a = allies order, x = axis order), the two END zones the
                        bots aim at, and the score-RETURN teleports. The first m5l1a pass rewrote only spawns: the old
                        zones still ran behind the gate and ret_x teleported axis INTO the dead end every time the
                        front scored (user screenshot: axis pressing into the closed gate).
Conventions match gen_push_from_bsp.emit_seed: a[i] = band i, x[i] = band N+1-i, end_a = band N (allies' goal,
the axis end), end_x = band 1 (axis' goal, the allies end), ret_a / ret_x = each side's first home spawn.

    python docs/tools/gen_push_pinned.py [map ...]
    python docs/tools/gen_push_maps.py build && python docs/tools/gen_arena_spawns.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_push_from_bsp as G  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPAWNS = os.path.join(ROOT, "docs", "tools", "push_spawns.json")
ZONES = os.path.join(ROOT, "docs", "tools", "push_zones.json")
Z_LIFT = 16.0  # pathnodes sit on the floor; lift a touch (push_groundSnapAll re-seats spawns at runtime anyway)
PAD_XY, PAD_Z = 48.0, 96.0

PINS = {
    "m4l2": {
        "allies": (5744.0, -560.0), "axis": (-6016.0, 1448.0), "alh": None,
        # [bug-2846/2847] REACHABILITY, not a hand box: with the track gates open, bots never entered the area south of
        # the tracks and spawns banded there stranded; with them closed it is the live southern route. So keep only
        # nodes a MOVING bot actually passed in the gates-closed soak, and never anything beyond the road gates north of
        # the escape truck (y>4860 west of x-4500 - out of the playable map).
        "exclude": (lambda n: n[1] > 4860.0 and n[0] < -4500.0),
        "reach": ["_soak_gates/m4l2.log"],
        "why": "user 2026-09-23: allies start at the SP start by the camp truck and push through the tank depot; "
               "axis home at the END where you board the escape truck (fakegetawaytruck). ViPER used only the west half. "
               "Dead south-of-tracks pocket excluded (bug-2846).",
    },
    "e3l2": {
        # [bug-2857] user 2026-09-23 (Monte Cassino): "spawn them [allies] by the tank that gets destroyed early on"
        # ($tank1, the TankPinDown tank) and axis were "spawning in the final room (like a prison cell) and have no way
        # out" - the BSP-derived farthest-pair picked a sealed upper room at (-2688,0,z-128) (soak: axis stuck/jumping
        # there 1000+ samples). Axis home = the SP END, the escape truck $Truck1.
        "allies": (1074.0, -4644.0), "axis": (-3316.0, 2605.0),
        # Explicit homes ON THE STREET (soak-walked cells at z-448; the nearest pathnodes sat ~120u up on terraces).
        # The escape truck's own yard was never reached by any soak bot (opened by the SP escape scene), so the axis
        # home is the reachable street just east of it (x-2336..-2176, the truck's exit route).
        "alh": [(1408.0, -4352.0, -432.0, 105.0), (1280.0, -4160.0, -432.0, 105.0), (1664.0, -4480.0, -448.0, 105.0)],
        "axh": [(-2336.0, 3088.0, -440.0, 285.0), (-2336.0, 3280.0, -440.0, 285.0), (-2176.0, 2816.0, -440.0, 285.0)],
        "exclude": (lambda n: (-2850.0 < n[0] < -2450.0 and -200.0 < n[1] < 300.0 and n[2] > -250.0)  # the sealed cell
                    or n[2] < -600.0                                                                  # the underground MC jail
                    # [bug-2863] a raised perch (z-40..-78) over a sunken dead-end pocket (z~-300) at x100..600
                    # y2400..3200: the ax2/al9 spawn sat on the perch and a soak axis bot dropped into the pocket and
                    # stayed there 80% of the run (pth=0). The street through there is at z-448 and unaffected.
                    or (100.0 < n[0] < 600.0 and 2400.0 < n[1] < 3200.0 and n[2] > -350.0)
                    # rooftops / nodes floating beyond the 384u snap cap: e3l2's streets are ~z-450 and its good
                    # band spawns sit at ~-150 (snapped down); a node at z>-100 is a roof or out of reach
                    or n[2] > -100.0),
        # [bug-2870] heat round 3: four band spawns sat in regions that reach NEITHER home on the directed navmesh
        # ((416,3360) pit, (784,-3648) + (3376,-80) sink, (1627,585) 7-poly island) - the round-to-round swing (8%..28%
        # stuck) was whichever bots spawned there. Every node must now reach both homes (nav_reach, nav_dump needed).
        "navreach": True,
        "why": "user 2026-09-23: allies home at the early-destroyed pin-down tank ($tank1), axis home at the SP end "
               "(escape truck $Truck1); the sealed cell and the underground jail excluded (bug-2857).",
    },
    "m5l1a": {
        "allies": (4968.0, -5056.0), "axis": (500.0, -1100.0), "exclude": (lambda n: n[0] < 260.0),
        # user 2026-09-23: "push the allies spawn back a bit (not out of the gate on their side or off the map) - more
        # fair". The derived home sat ~700u in front of the SP start (no pathnodes there), so use ViPER's original
        # hand-placed allies home at the SP start - it always spawned cleanly.
        "alh": [(5014.2, -5248.9, 67.1, 126.0), (5008.0, -5064.0, 31.8, 127.5), (5013.0, -4524.3, 46.6, 184.6)],
        # [bug-2870 round 4, user 2026-09-24 "yes fix the spawns"] two band spawns failed the directed-navmesh sweep: al9/ax2
        # sat just UNDER a floor (z24 vs 64), al6/ax5 on a ledge (z177) that reaches neither home. Each moves to the nearest
        # floor that reaches BOTH homes; the rest of the user-verified layout is untouched.
        "move": {(1008, -1480): (917.0, -1392.0, 30.0), (2608, -2448): (2562.0, -2492.0, 40.0)},
        "why": "user 2026-09-23: the map ENDS at the leftgate/rightgate pair (x~244); axis must spawn in FRONT of it. "
               "Moving only axh/ax2 (bug-2834) left ViPER's allied chain, zones and the axis return-teleport BEHIND the "
               "gate. Whole corridor now SP start -> gate; nothing west of the gate line is a zone, spawn or teleport.",
    },
}


def box(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
    return [min(xs) - PAD_XY, min(ys) - PAD_XY, min(zs) - PAD_Z, max(xs) + PAD_XY, max(ys) + PAD_XY, max(zs) + PAD_Z]


def union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2]), max(a[3], b[3]), max(a[4], b[4]), max(a[5], b[5])]


REACH_XY, REACH_Z, REACH_MINSPD = 192.0, 96.0, 40.0


def reach_filter(logs):
    """[bug-2846] Nodes the bots can ACTUALLY reach: within REACH_XY (and REACH_Z) of a soak sample of a MOVING bot
    (spd > REACH_MINSPD, so a bot stuck at a dead spawn does not vouch for its own pocket). Pathnodes are the SP AI's
    graph, not the bot navmesh - m4l2 had five spawn groups in a pocket with nodes but no mesh route out."""
    import re
    rx = re.compile(r'BOTPROBE e=\d+ tm=\w al=1 hp=-?\d+ px=(-?[\d.]+) py=(-?[\d.]+) pz=(-?[\d.]+) spd=([\d.]+)')
    cells = {}
    for f in logs:
        for line in open(os.path.join(ROOT, f), encoding="latin-1"):
            g = rx.search(line)
            if g and float(g.group(4)) > REACH_MINSPD:
                x, y, z = float(g.group(1)), float(g.group(2)), float(g.group(3))
                cells.setdefault((int(x // REACH_XY), int(y // REACH_XY)), []).append((x, y, z))
    def ok(n):
        cx, cy = int(n[0] // REACH_XY), int(n[1] // REACH_XY)
        for i in (cx - 1, cx, cx + 1):
            for j in (cy - 1, cy, cy + 1):
                for (x, y, z) in cells.get((i, j), ()):
                    if (x - n[0]) ** 2 + (y - n[1]) ** 2 <= REACH_XY ** 2 and abs(z - n[2]) <= REACH_Z:
                        return True
        return False
    return ok


def build(mapname):
    if mapname not in PINS:
        raise SystemExit("no pins for %s (add it to PINS with a reason)" % mapname)
    P = PINS[mapname]
    h, err = G.harvest(mapname)
    if err:
        raise SystemExit(err)
    excl = P["exclude"]
    if P.get("reach"):
        ok = reach_filter(P["reach"])
        base = excl
        excl = (lambda n: (base is not None and base(n)) or not ok(n))
    if P.get("navreach"):
        # [bug-2870] every node must reach BOTH explicit homes on the directed bot navmesh (see G.nav_reach)
        nr = G.nav_reach(mapname, [P["alh"][0][:3], P["axh"][0][:3]])
        base2 = excl
        excl = (lambda n: (base2 is not None and base2(n)) or not nr(n))
    d = G.derive(mapname, h, pins=(P["allies"], P["axis"]), exclude=excl)

    # ---- spawns ----
    spawns = []
    for side, key in (("a", "allied"), ("x", "axis")):
        for (o, yaw, tn) in d[key]:
            if side == "a" and tn == "alh" and P["alh"]:
                continue  # replaced by the explicit home below
            if side == "x" and tn == "axh" and P.get("axh"):
                continue  # [bug-2857] replaced by the explicit axis home below
            spawns.append({"x": round(o[0], 1), "y": round(o[1], 1), "z": round(o[2] + Z_LIFT, 1),
                           "ang": float(yaw), "grp": tn, "side": side})
    if P["alh"]:
        spawns = [{"x": x, "y": y, "z": z, "ang": a, "grp": "alh", "side": "a"} for (x, y, z, a) in P["alh"]] + spawns
    if P.get("axh"):
        spawns = spawns + [{"x": x, "y": y, "z": z, "ang": a, "grp": "axh", "side": "x"} for (x, y, z, a) in P["axh"]]
    for s in spawns:
        mv = P.get("move", {}).get((int(round(s["x"])), int(round(s["y"]))))
        if mv:
            s["x"], s["y"], s["z"] = mv
    groups = []
    for s in spawns:
        if s["grp"] not in groups:
            groups.append(s["grp"])
    sdata = json.load(open(SPAWNS))
    sdata[mapname] = {
        "spawns": spawns, "groups": groups,
        "a": sum(1 for s in spawns if s["side"] == "a"), "x": sum(1 for s in spawns if s["side"] == "x"),
        "note": "[bug-2835] PINNED re-derive by gen_push_pinned.py from BSP pathnodes: " + P["why"],
    }
    json.dump(sdata, open(SPAWNS, "w"), indent=1)

    # ---- zones / end zones / return teleports ----
    n = len(d["zones"])
    zb = {i: [d["zones"][i][0][0], d["zones"][i][0][1], d["zones"][i][0][2],
              d["zones"][i][1][0], d["zones"][i][1][1], d["zones"][i][1][2]] for i in range(1, n + 1)}
    home_a = [(s["x"], s["y"], s["z"]) for s in spawns if s["grp"] == "alh"]
    home_x = [(s["x"], s["y"], s["z"]) for s in spawns if s["grp"] == "axh"]
    # The END zones ARE the home spawn clusters. push_publishTargets sends allies bots to the CENTRE of ZA[N] and axis
    # bots to the centre of ZA[1]; a whole band's AABB centre can sit in a wall or off the nav (m4l2 band 1 spans
    # 5500u of y), a home-spawn box's centre is on the floor they spawn on. Only ZA[1]/ZA[N] are read at the ends;
    # the front itself comes from the alh->axh projection (push_countInBand), not zone containment.
    zb[1] = box(home_a)
    zb[n] = box(home_x)
    zdata = json.load(open(ZONES)) if os.path.exists(ZONES) else {}
    rec = {  # ViPER's "start" key is dropped: nothing reads it, and after a re-layout it points at the OLD allies start
        "a": {str(i): [round(v, 2) for v in zb[i]] for i in range(1, n + 1)},
        "x": {str(i): [round(v, 2) for v in zb[n + 1 - i]] for i in range(1, n + 1)},
        "end_a": [round(v, 2) for v in zb[n]],
        "end_x": [round(v, 2) for v in zb[1]],
        "ret_a": [home_a[0][0], home_a[0][1], home_a[0][2]],
        "ret_x": [home_x[0][0], home_x[0][1], home_x[0][2]],
        "note": "[bug-2835] PINNED re-derive by gen_push_pinned.py (zones + end zones + return teleports)",
    }
    zdata[mapname] = rec
    json.dump(zdata, open(ZONES, "w"), indent=1)

    print("%s: %dA/%dX spawns, %d zones -> push_spawns.json + push_zones.json" %
          (mapname, sdata[mapname]["a"], sdata[mapname]["x"], n))
    for tn in ("alh", "al9", "axh", "ax9"):
        print("   %-3s %s" % (tn, [(int(s["x"]), int(s["y"])) for s in spawns if s["grp"] == tn]))
    print("   end_a centre (%d,%d)  end_x centre (%d,%d)  ret_a %s  ret_x %s" % (
        (zb[n][0] + zb[n][3]) / 2, (zb[n][1] + zb[n][4]) / 2, (zb[1][0] + zb[1][3]) / 2, (zb[1][1] + zb[1][4]) / 2,
        tuple(int(v) for v in rec["ret_a"]), tuple(int(v) for v in rec["ret_x"])))


if __name__ == "__main__":
    for m in (sys.argv[1:] or sorted(PINS)):
        build(m)

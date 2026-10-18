#!/usr/bin/env python3
"""gen_counter_zones.py - vetted DEFEND ZONES for the final counter-attack, derived from each map's BSP (bsptrace.py).

WHY (bug-4006): the counter-attack held the squad "where the mission ended" with no idea of a place. The zone has to be somewhere
all players can reach and stand, never a vent, a ladder top or a closet. This derives candidate zones offline and writes
coop_mod/coop_counter_zones.scr; coop_counter.scr picks the vetted zone nearest the squad when the objective completes (and falls
back to a runtime-traced zone at the squad when a map has none near).

    python docs/tools/gen_counter_zones.py build [map ...]     # write coop_mod/coop_counter_zones.scr (+ docs/tools/counter_zones.json)
    python docs/tools/gen_counter_zones.py check                # regenerate in memory + byte-compare
    COUNTER_MOD=<mod checkout> overrides the checkout written to (default hzm-mohaa-coop-mod).

A candidate is a PATHNODE (so a pathnode lies inside the zone by construction) that passes:
  walkable floor     floor under it (nodes float 0-110 u above the floor) (the pathnode clouds of some maps float - those nodes are dropped)
  reachable on foot  in a SIZEABLE pathnode component (>=30 nodes and >=15% of the largest) or the start's own; edges are hull-clear
                     (<=300 u, dz<=64). Ladders are not traversable by a hull trace, so ladder tops / vents form small islands that are dropped
  room for 4         4 hull spots at 56 u around it are clear on the same floor, 16 rays at chest height: median free run >=160 u,
                     >=12 of 16 rays >=96 u
  not a vent/closet  open sky above, or a ceiling >=112 u; >=96 u from any func_ladder
Radius = 0.9 x the 60th-percentile free run, clamped 260..520 (a room or courtyard, not a tiny circle). Zones are >=800 u apart.
Name: open sky "the courtyard"; enclosed with a big run "the hall"; else "the room".
"""
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bsptrace as T  # noqa: E402
import alarm_place as AP  # noqa: E402  (EXTRA_STARTS: runtime spawns)

ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.environ.get("COUNTER_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
OUT = os.path.join(MOD, "coop_mod", "coop_counter_zones.scr")
JSON = os.path.join(HERE, "counter_zones.json")
# the maps coop_counter.scr lets run (counter_denied is the complement; BUILD.md step 3)
MAPS = "m1l1 m4l1 m1l2a m2l1 m3l2 m5l1a m6l3b t1l2 t2l1 t3l1 e3l1 e3l2".split()
GHULL = ((-14, -14, -28), (14, 14, 28))   # graph edges: node-to-node swept body (nodes float 0-110 u over the floor)
HULL = ((-14, -14, -10), (14, 14, 28))   # centred floor+30: spans floor+20..floor+58, so a stair step <=18 is crossed
MAXZ = 10


def floor_of(B, x, y, z):
    """ground under (x, y) near z: highest of the brush floor below z+6 and the terrain surface (<= z+30), or None."""
    best = None
    r = B.trace((x, y, z + 6), (x, y, z - 160))
    if r and r[1][2] > 0.7:
        best = z + 6 - r[0] * 166
    tz = B.terrain_z(x, y)
    if tz is not None and z - 160 <= tz <= z + 30 and (best is None or tz > best):
        best = tz
    return best


def slope_ok(B, a, b, step=32.0, per=24.0):
    """terrain/brush ground along a->b never rises or drops more than `per` u per `step` u (walkable, ~37 degrees)."""
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) // step))
    prev = a[2]
    for k in range(1, n + 1):
        x = a[0] + (b[0] - a[0]) * k / n
        y = a[1] + (b[1] - a[1]) * k / n
        g = floor_of(B, x, y, prev)
        if g is None or abs(g - prev) > per:
            return False
        prev = g
    return True


def ray_free(B, x, y, f, ang, length=700.0, h=48.0):
    """free run at chest height: brush hit or a terrain rise above chest height ends it."""
    p0 = (x, y, f + h)
    dx, dy = math.cos(ang), math.sin(ang)
    r = B.trace(p0, (x + dx * length, y + dy * length, f + h))
    run = length if not r else r[0] * length
    d = 24.0
    while d < run:
        tz = B.terrain_z(x + dx * d, y + dy * d)
        if tz is not None and tz > f + h:
            return d
        d += 24.0
    return run


def build_graph(B, nodes):
    cell = 300.0
    grid = {}
    for i, q in enumerate(nodes):
        grid.setdefault((int(q[0] // cell), int(q[1] // cell)), []).append(i)
    adj = [[] for _ in nodes]
    for i, a in enumerate(nodes):
        cx, cy = int(a[0] // cell), int(a[1] // cell)
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for j in grid.get((gx, gy), ()):
                    if j <= i:
                        continue
                    b = nodes[j]
                    if math.hypot(a[0] - b[0], a[1] - b[1]) > 300 or abs(a[2] - b[2]) > 64:
                        continue
                    r = B.trace_box(a, b, GHULL[0], GHULL[1])
                    if r is None:
                        adj[i].append(j)
                        adj[j].append(i)
    return adj


def components(adj):
    comp = [-1] * len(adj)
    n = 0
    for s in range(len(adj)):
        if comp[s] >= 0:
            continue
        st = [s]
        comp[s] = n
        while st:
            u = st.pop()
            for v in adj[u]:
                if comp[v] < 0:
                    comp[v] = n
                    st.append(v)
        n += 1
    return comp


def metrics(B, q, ladders):
    x, y, f = q
    d = []
    for k in range(16):
        a = math.radians(k * 22.5)
        d.append(ray_free(B, x, y, f, a))
    ds = sorted(d)
    med = ds[8]
    if med < 160 or sum(1 for v in d if v >= 96) < 12:
        return None
    up = B.trace((x, y, f + 8), (x, y, f + 600))
    sky = False
    if up:
        h = up[0] * 592 + 8
        nm = B.shaders[up[2]][0].lower() if 0 <= up[2] < len(B.shaders) else ""
        sky = "sky" in nm
        if h < 112 and not sky:
            return None
    else:
        sky = True
    for k in range(4):
        a = math.radians(k * 90 + 45)
        sx, sy = x + math.cos(a) * 56, y + math.sin(a) * 56
        if B.trace_box((x, y, f + 30), (sx, sy, f + 30), HULL[0], HULL[1]) is not None:
            return None
        sf = floor_of(B, sx, sy, f + 2)
        if sf is None or abs(sf - f) > 20:
            return None
    for lm, lx in ladders:
        if lm[0] - 96 <= x <= lx[0] + 96 and lm[1] - 96 <= y <= lx[1] + 96 and lm[2] - 128 <= f <= lx[2] + 128:
            return None
    p60 = ds[int(0.6 * 15)]
    rad = max(260.0, min(520.0, 0.9 * p60))
    return {"med": med, "sky": sky, "rad": rad}


def zones_for(m):
    B = T.BSP.load(m)
    es = B.entities()
    raw = [T.vec(e["origin"]) for e in es if e.get("classname") == "info_pathnode" and T.vec(e.get("origin", ""))]
    starts = [T.vec(e["origin"]) for e in es if e.get("classname", "").startswith("info_player") and T.vec(e.get("origin", ""))]
    starts += AP.EXTRA_STARTS.get(m, [])
    adj = build_graph(B, raw)
    comp = components(adj)
    cnt = {}
    for c in comp:
        cnt[c] = cnt.get(c, 0) + 1
    big = max(cnt.values())
    # the walkable main body: every sizeable component (doors/gaps split one map into several) plus the start's own; islands
    # (ladder tops, vents, roofs - a handful of nodes) are left out
    seed = set(c for c, n in cnt.items() if n >= max(30, 0.15 * big))
    seed |= set(comp[i] for i, q in enumerate(raw) if any(math.dist(q, s) < 450 for s in starts))
    nodes = []
    for i, q in enumerate(raw):
        if comp[i] not in seed:
            continue
        f = floor_of(B, q[0], q[1], q[2])
        if f is None or not (-20 <= q[2] - f <= 110):
            continue
        nodes.append((q[0], q[1], f))
    ladders = []
    for e in es:
        if e.get("classname") == "func_ladder" and e.get("model", "").startswith("*"):
            try:
                ladders.append(B.model_bounds(int(e["model"][1:])))
            except Exception:
                pass
    cands = []
    for i, q in enumerate(nodes):
        mt = metrics(B, q, ladders)
        if not mt:
            continue
        near = sum(1 for p in nodes if math.hypot(p[0] - q[0], p[1] - q[1]) <= mt["rad"] and abs(p[2] - q[2]) <= 48)
        if near < 4:
            continue
        score = mt["med"] + (120 if mt["sky"] else 0) + 4 * min(near, 40)
        cands.append((score, q, mt))
    cands.sort(key=lambda c: -c[0])
    out = []
    for score, q, mt in cands:
        if any(math.hypot(q[0] - o["pos"][0], q[1] - o["pos"][1]) < 800 and abs(q[2] - o["pos"][2]) < 150 for o in out):
            continue
        name = "the courtyard" if mt["sky"] else ("the hall" if mt["med"] >= 350 else "the room")
        out.append({"pos": [round(q[0], 1), round(q[1], 1), round(q[2], 1)], "rad": round(mt["rad"]), "name": name})
        if len(out) >= MAXZ:
            break
    return out, len(nodes), len(raw)


def render(d):
    o = ["//=========================================================================",
         "// coop_counter_zones.scr - GENERATED by docs/tools/gen_counter_zones.py (BSP-traced defend zones). Do not edit by hand.",
         "// zones <map> fills level.coop_czPos[i] / coop_czRad[i] / coop_czName[i] and returns how many (0 = none known for the map).",
         "//========================================================================="]
    o.append("zones local.map:{")
    o.append("\tlevel.coop_czN = 0")
    for m in sorted(d):
        if d[m]:
            o.append("\tif( local.map == \"%s\" ){ waitthread cz_%s }" % (m, m))
    o.append("}end level.coop_czN")
    o.append("")
    for m in sorted(d):
        if not d[m]:
            continue
        o.append("// %s: %d zone(s)" % (m, len(d[m])))
        o.append("cz_%s:{" % m)
        for i, z in enumerate(d[m], 1):
            o.append("\tlevel.coop_czPos[%d] = ( %s %s %s )" % (i, "%.1f" % z["pos"][0], "%.1f" % z["pos"][1], "%.1f" % z["pos"][2]))
            o.append("\tlevel.coop_czRad[%d] = %d" % (i, z["rad"]))
            o.append("\tlevel.coop_czName[%d] = \"%s\"" % (i, z["name"]))
        o.append("\tlevel.coop_czN = %d" % len(d[m]))
        o.append("}end")
        o.append("")
    return "\n".join(o) + "\n"


def main(argv):
    if len(argv) < 2 or argv[1] not in ("build", "check"):
        print(__doc__)
        return 2
    d = {}
    if os.path.exists(JSON):
        d = json.load(io.open(JSON, "r", encoding="utf-8"))
    if argv[1] == "build":
        for m in (argv[2:] or MAPS):
            z, nn, nr = zones_for(m)
            d[m] = z
            print(m, "zones", len(z), "nodes valid", nn, "of", nr)
            for q in z:
                print("   ", q)
        with io.open(JSON, "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, indent=1, sort_keys=True)
            f.write("\n")
        with io.open(OUT, "w", encoding="ascii", newline="\n") as f:
            f.write(render(d))
        print("wrote", OUT)
        return 0
    cur = io.open(OUT, "r", encoding="ascii", newline="").read() if os.path.exists(OUT) else ""
    if cur != render(d):
        print("DRIFT")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

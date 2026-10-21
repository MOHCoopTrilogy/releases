"""placement_audit.py <map> [--png out.png] - audit every placed objective item of one map and draw a top-down placement sheet.

Reads docs/tools/objx_points.json[map] and the map's BSP entity lump (docs/tools/bsptrace.py) and the coop spawn labels of
coop_mod/spawnlocations.scr (hzm-mod-objectives2 tree). For each placed thing (kit, targets, actor, work prop, radios, intel, zone
centres, near triggers) it reports:
  - distance to vehicle routes (info_vehiclepoint / info_waypoint chains t<N> -> t<N+1>, vanilla vehicle entities) - minus the
    vehicle half width: a prop closer than FOOT + VEH_HALF + 60 u to a route segment is flagged
  - distance to player spawns (info_player_start + the coop spawn tables) and to objective markers (script_origin obj*)
  - distance to doors, ladders, use triggers, vanilla AI spawn entities and breakable crates
  - free clearance around it (8 rays at chest height): a prop wants >= FOOT + 110 in at least 6 of 8 directions
  - walkable approach: a pathnode within 220 u whose floor is within 20 u of the item floor, and a player-hull walk from that
    node to the stand spot (no jump needed)
  - floor under the item vs the item z (floating / buried)
Footprint radii (FOOT) per model come from FOOT below (measured in game with ox_drv 'props'); the default is 60.
Exit 1 when any FAIL line is printed. The PNG is the placement sheet: pathnodes grey, vehicle routes blue, spawns green,
objective markers orange, doors purple, items red (circle = footprint), zones red dashed."""
import sys, os, re, json, math
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import bsptrace as T

MODROOT = "C:/mohaa-coop-dev/hzm-mod-objectives2"
FOOT = {   # model -> footprint radius at the item's own scale factor 1; multiplied by item scale when scale > 0
    "models/static/fuel_tanks.tik": 330,
    "models/static/fuel_tanks_d.tik": 330,
    "models/static/generator.tik": 140,
    "models/static/exp_crate1.tik": 40,
    "models/human/1st-ranger_engineer.tik": 30,
}
VEH_HALF = 110        # an Opel truck is ~220 wide, ~420 long; the half width plus swing
VEH_NAMES = ("vehicle_", "info_vehiclepoint")


def vec(s):
    return [float(x) for x in s.replace("(", " ").replace(")", " ").split()]


def seg_dist(p, a, b):
    ax, ay = a[0], a[1]
    bx, by = b[0], b[1]
    px, py = p[0], p[1]
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def spawn_points(mapname):
    out = []
    p = os.path.join(MODROOT, "coop_mod", "spawnlocations.scr")
    txt = open(p, encoding="latin-1").read().replace("\r", "")
    for m in re.finditer(r"^%s_update\d*:\{(.*?)^\}end" % re.escape(mapname), txt, re.S | re.M):
        body = m.group(1)
        for v in re.finditer(r"\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)", body):
            x, y, z = float(v.group(1)), float(v.group(2)), float(v.group(3))
            if abs(x) + abs(y) < 5:
                continue
            out.append((x, y, z))
        # loop-built rows: local.vec = (...) then vec[0|1] += step, count from "<=N"
        lv = re.search(r"local\.vec\s*=\s*\(\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*\)", body)
        cn = re.search(r"local\.i\s*<=\s*(\d+)", body)
        stp = re.search(r"local\.vec\[(\d)\]\s*(?:\+=\s*|=\s*\(\s*local\.vec\[\d\]\s*\+\s*)(-?\d+)", body)
        if lv and cn and stp:
            x, y, z = float(lv.group(1)), float(lv.group(2)), float(lv.group(3))
            ax = int(stp.group(1))
            d = float(stp.group(2))
            for i in range(1, int(cn.group(1))):
                x += d if ax == 0 else 0
                y += d if ax == 1 else 0
                out.append((x, y, z))
    return out


def floor_z(B, x, y, zhint):
    t = B.trace((x, y, zhint + 70), (x, y, zhint - 90))
    return None if not t else zhint + 70 - 160 * t[0]


def walk_ok(B, a, b):
    """player-hull walk a -> b at floor level: no step above 18 u, hull never blocked (so no jump is needed)"""
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 24))
    fz0 = floor_z(B, a[0], a[1], a[2])
    if fz0 is None:
        return False
    prev = fz0
    for i in range(1, n + 1):
        x = a[0] + (b[0] - a[0]) * i / n
        y = a[1] + (b[1] - a[1]) * i / n
        fz = floor_z(B, x, y, prev)
        if fz is None or abs(fz - prev) > 18:
            return False
        t = B.trace_box((x, y, fz + 20), (x, y, fz + 20.01), (-15, -15, 0), (15, 15, 56))
        if t and t[0] < 1:
            return False
        prev = fz
    return True


def reach_ok(B, nodes, p, r):
    """some stand point 50 u outside the footprint is reachable on foot from a pathnode within 450 u"""
    for ang in range(0, 360, 45):
        sx = p[0] + math.cos(math.radians(ang)) * (r + 50)
        sy = p[1] + math.sin(math.radians(ang)) * (r + 50)
        fz = floor_z(B, sx, sy, p[2])
        if fz is None:
            continue
        for n in sorted(nodes, key=lambda q: math.hypot(q[0] - sx, q[1] - sy))[:6]:
            if math.hypot(n[0] - sx, n[1] - sy) > 450 or abs(n[2] - fz) > 90:
                continue
            nz = floor_z(B, n[0], n[1], n[2])
            if nz is None:
                continue
            if walk_ok(B, (n[0], n[1], nz), (sx, sy, fz)):
                return (round(sx), round(sy))
    return None


def main():
    mp = sys.argv[1]
    png = sys.argv[sys.argv.index("--png") + 1] if "--png" in sys.argv else None
    data = json.load(open("C:/mohaa-coop-dev/docs/tools/objx_points.json", encoding="utf-8"))[mp]
    B = T.BSP.load(mp)
    ents = B.entities()
    nodes = [vec(e["origin"]) for e in ents if e["classname"] == "info_pathnode"]
    spawns = [vec(e["origin"]) for e in ents if e["classname"] == "info_player_start"] + spawn_points(mp)
    markers = [(e.get("targetname"), vec(e["origin"])) for e in ents if e["classname"] == "script_origin" and re.match(r"(obj|end|spot)", e.get("targetname", "") or "")]
    wps = {}
    for e in ents:
        if e["classname"] in ("info_waypoint", "info_vehiclepoint") and re.match(r"t\d+$", e.get("targetname", "") or ""):
            wps[int(e["targetname"][1:])] = vec(e["origin"])
        if e["classname"] == "info_vehiclepoint":
            wps.setdefault(-id(e), vec(e["origin"]))
    segs = []
    keys = sorted(k for k in wps if k >= 0)
    for a, b in zip(keys, keys[1:]):
        if b == a + 1 and math.dist(wps[a][:2], wps[b][:2]) < 2500:
            segs.append((wps[a], wps[b], "t%d-t%d" % (a, b)))
    vehs = [(e.get("targetname", e["classname"]), vec(e["origin"])) for e in ents if e["classname"].startswith("vehicle_") and "airplane" not in e["classname"]]
    doors = [(e["classname"], vec(e["origin"])) for e in ents if e["classname"] in ("func_rotatingdoor", "func_door", "func_ladder") or (e["classname"] == "trigger_use")]
    aisp = [vec(e["origin"]) for e in ents if e["classname"].startswith("ai_")]
    crates = [vec(e["origin"]) for e in ents if e["classname"] in ("func_crate", "func_barrel")]

    items = []
    for o in data["objectives"]:
        for it in o.get("items", []):
            r = FOOT.get(it["model"], 60) * (it.get("scale", 0) or 1)
            items.append((o["id"] + ":" + it["kind"], it["pos"], r, it))
            if it.get("prop_pos") and it["kind"] == "actor":
                rp = FOOT.get(it.get("aux", ""), 60) * (it.get("scale", 0) or 1)
                items.append((o["id"] + ":workprop", it["prop_pos"], rp, it))
        z = o.get("zone")
        if z:
            items.append((o["id"] + ":zone", z["pos"], 0, None))
    fails = 0
    warns = 0
    print("map", mp, "| nodes", len(nodes), "| spawns", len(spawns), "| route segments", len(segs), "| vehicles", len(vehs))
    for name, pos, r, it in items:
        pr = []
        kind = name.split(":")[1]
        p = pos
        if kind != "zone":
            # vehicle routes
            for a, b, nm in segs:
                d = seg_dist(p, a, b)
                if d < r + VEH_HALF + 60:
                    pr.append(("FAIL", "vehicle route %s %.0f u (needs %.0f)" % (nm, d, r + VEH_HALF + 60)))
            for a, b, nm in segs:   # a route END is where the truck parks: its whole body (about 230 u of swing) must stay clear
                for ep, en in ((a, nm.split("-")[0]), (b, nm.split("-")[1])):
                    if en in [x[2].split("-")[0] for x in segs] and ep is a:
                        continue
                    if ep is b and any(x[2].split("-")[0] == en for x in segs):
                        continue
                    d = math.hypot(p[0] - ep[0], p[1] - ep[1])
                    if d < r + 230:
                        pr.append(("FAIL", "vehicle STOP point %s %.0f u (needs %.0f)" % (en, d, r + 230)))
            for nm, v in vehs:
                d = math.hypot(p[0] - v[0], p[1] - v[1])
                if d < r + 260:
                    pr.append(("FAIL", "vanilla vehicle %s %.0f u" % (nm, d)))
            for s in spawns:
                d = math.hypot(p[0] - s[0], p[1] - s[1])
                if d < r + 90 and abs(p[2] - s[2]) < 120:
                    pr.append(("FAIL", "player spawn %.0f u (%s)" % (d, [round(x) for x in s])))
            for nm, m in markers:
                d = math.dist(p, m)
                if d < r + 80:
                    pr.append(("WARN", "objective marker %s %.0f u" % (nm, d)))
            for cn, dpos in doors:
                d = math.hypot(p[0] - dpos[0], p[1] - dpos[1])
                if d < r + 90 and abs(p[2] - dpos[2]) < 140:
                    pr.append(("WARN", "%s %.0f u" % (cn, d)))
            for q in aisp:
                d = math.hypot(p[0] - q[0], p[1] - q[1])
                if d < r + 40 and abs(p[2] - q[2]) < 100:
                    pr.append(("WARN", "vanilla AI spawn %.0f u" % d))
            nc = sum(1 for c in crates if math.hypot(p[0] - c[0], p[1] - c[1]) < r + 20 and abs(c[2] - p[2]) < 120)
            if nc:
                pr.append(("WARN", "%d vanilla crates/barrels inside the footprint" % nc))
            # floor + clearance
            f = B.trace((p[0], p[1], p[2] + 60), (p[0], p[1], p[2] - 100))
            if f:
                fz = p[2] + 60 - 160 * f[0]
                if abs(fz - p[2]) > 14:
                    pr.append(("FAIL" if abs(fz - p[2]) > 30 else "WARN", "floor at %.0f, item z %.0f (floating/buried)" % (fz, p[2])))
            else:
                pr.append(("WARN", "no BSP floor below (terrain / bmodel?)"))
            free = 0
            for ang in range(0, 360, 45):
                dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                L = r + 110
                t = B.trace((p[0] + dx * r * 0.5, p[1] + dy * r * 0.5, p[2] + 40), (p[0] + dx * L, p[1] + dy * L, p[2] + 40))
                if not t or t[0] > 0.97:
                    free += 1
            if free < 6:
                pr.append(("WARN", "tight: only %d/8 directions have %d u clear" % (free, r + 110)))
            # walkable approach from the nearest pathnode with a similar floor
            if kind in ("target", "kit", "actor", "workprop", "pickup", "radio"):
                rr = reach_ok(B, nodes, p, r)
                if rr is None:
                    pr.append(("FAIL", "no stand point reachable on foot without a jump (pathnode walk test)"))
        for lvl, msg in pr:
            if lvl == "FAIL":
                fails += 1
            else:
                warns += 1
            print("  %-5s %-22s %s" % (lvl, name, msg))
        if not pr:
            print("  ok    %-22s r=%.0f" % (name, r))
    print("RESULT fails=%d warns=%d" % (fails, warns))
    if png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        pts = [i[1] for i in items]
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        pad = 900
        x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
        fig, ax = plt.subplots(figsize=(12, 12 * (y1 - y0) / max(1, (x1 - x0))))
        ax.set_facecolor("#14161a")
        ax.scatter([n[0] for n in nodes], [n[1] for n in nodes], s=3, c="#6b7280", label="pathnodes (walkable)")
        for a, b, nm in segs:
            ax.plot([a[0], b[0]], [a[1], b[1]], c="#3b82f6", lw=6, alpha=0.35)
        ax.plot([], [], c="#3b82f6", lw=6, alpha=0.35, label="vehicle route")
        for nm, v in vehs:
            ax.scatter([v[0]], [v[1]], marker="s", c="#60a5fa", s=60)
        ax.scatter([s[0] for s in spawns], [s[1] for s in spawns], marker="*", c="#22c55e", s=90, label="player spawns")
        ax.scatter([m[1][0] for m in markers], [m[1][1] for m in markers], marker="D", c="#f59e0b", s=40, label="objective markers")
        ax.scatter([d[1][0] for d in doors], [d[1][1] for d in doors], marker="^", c="#a855f7", s=20, label="doors / use / ladders")
        for name, pos, r, it in items:
            kind = name.split(":")[1]
            if kind == "zone":
                oo = [o for o in data["objectives"] if o["id"] == name.split(":")[0]][0]["zone"]
                ax.add_patch(plt.Circle((pos[0], pos[1]), oo["r"], fill=False, ec="#ef4444", ls="--", lw=1.5))
                ax.text(pos[0], pos[1], name.split(":")[0] + " zone", color="#fca5a5", fontsize=8, ha="center")
            else:
                ax.add_patch(plt.Circle((pos[0], pos[1]), max(r, 20), fill=True, fc="#ef4444", ec="#fecaca", alpha=0.45))
                ax.text(pos[0] + 25, pos[1] + 25, name, color="#fecaca", fontsize=7)
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.legend(loc="upper left", fontsize=7, facecolor="#1f2937", labelcolor="white")
        ax.set_title("%s placement sheet (top-down, world units)" % mp, color="white")
        fig.patch.set_facecolor("#0b0d10")
        ax.tick_params(colors="#9ca3af")
        fig.savefig(png, dpi=110, facecolor=fig.get_facecolor())
        print("wrote", png)
    return 1 if fails else 0


sys.exit(main())

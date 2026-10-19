"""extract_alarm_vehicle_routes.py - ONE-OFF: read the vanilla vehicle waypoint chains out of the stock BSPs (GOG root, read only)
and write docs/tools/alarm_vehicle_routes.json (the committed source of truth; gen_alarm_vehicle_routes.py turns it into
coop_mod/alarmveh_routes.scr). Re-run only to re-derive a vanilla chain; hand-authored routes (ROUTES_HOWTO.md) are added to the
JSON directly and are never touched by this script.

    python docs/tools/extract_alarm_vehicle_routes.py            # writes the json
"""
import glob, json, math, os, re, sys, zipfile

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm_vehicle_routes.json")


def load(mp):
    for f in sorted(glob.glob(os.path.join(GOG, "main*", "*.pk3"))):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower() == mp:
                d = z.read(n)
                i = d.find(b'"classname"')
                i = d.rfind(b"{", 0, i)
                txt = d[i:i + 3000000].split(b"\x00")[0].decode("latin1")
                return [dict(re.findall(r'"([^"]+)"\s+"([^"]*)"', e)) for e in re.findall(r"\{([^{}]*)\}", txt)]
    raise SystemExit("bsp not found: " + mp)


def vec(s):
    return [round(float(v), 1) for v in s.split()]


def chain(ents, head):
    by = {}
    for e in ents:
        tn = e.get("targetname") or e.get("$targetname")
        if tn:
            by.setdefault(tn, e)
    out, cur, seen = [], by.get(head), set()
    while cur is not None:
        tn = cur.get("targetname") or cur.get("$targetname")
        if tn in seen:
            break
        seen.add(tn)
        out.append(vec(cur["origin"]))
        cur = by.get(cur.get("target", ""))
    return out


def crate_for(nodes, ref):
    """perpendicular of the last leg, 380u off the stop, on the side nearer ref (a point the players come from)."""
    a, b = nodes[-2], nodes[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    px, py = -dy / L, dx / L
    best = None
    for s in (1, -1):
        c = [b[0] + s * px * 380, b[1] + s * py * 380, b[2]]
        d = math.hypot(c[0] - ref[0], c[1] - ref[1])
        if best is None or d < best[0]:
            best = (d, c)
    c = best[1]
    yaw = math.degrees(math.atan2(b[1] - c[1], b[0] - c[0])) % 360
    return [round(c[0], 1), round(c[1], 1), round(c[2], 1)], round(yaw, 1)


def main():
    routes = {}
    # m3l3 (AA): the vanilla halftrack ambush hull + its 6-node road (maps/M3L3.scr::halftrack_drive)
    e = load("maps/m3l3.bsp")
    n = [[-729.9, 5373.4, -136.0]] + chain(e, "halftrack_path")
    c, y = crate_for(n, [-3300, 3900])          # the coop player spawn (spawnlocations.scr::m3l3_update1)
    routes["m3l3"] = [dict(name="halftrack", kind="halftrack", model="models/vehicles/sdkfz.tik", nodes=n, crate=c, crateyaw=y,
                           src="BSP halftrack (vehicles//sdkfz.tik) + halftrack_path 6n")]
    # t2l3 (BT): the vanilla snow halftrack + halftrack1_path
    e = load("maps/t2l3.bsp")
    n = [[2543.7, 3288.4, 60.0]] + chain(e, "halftrack1_path")
    c, y = crate_for(n, [2544, 3288])
    routes["t2l3"] = [dict(name="halftrack", kind="halftrack", model="models/vehicles/halftrack_winter.tik", nodes=n, crate=c, crateyaw=y,
                           src="BSP halftrack1 (halftrack_winter.tik) + halftrack1_path 10n")]
    # t3l1 (BT): s10_truck3 road, ends 440u from alarm switch 2 (1581,3091,236)
    e = load("maps/t3l1.bsp")
    n = [[1390.0, 6992.0, 192.0]] + chain(e, "s10_truck3_path")
    routes["t3l1"] = [dict(name="s10_truck3", kind="truck", model="models/vehicles/opeltruck.tik", nodes=n,
                           crate=[1524.4, 3098.1, 234.1], crateyaw=90.0, src="BSP s10_truck3 + s10_truck3_path 11n; crate = alarm switch 2 seed")]
    # m4l1 (AA): truck01 road (vanilla pose (1823,225,-120) then truck01_path)
    e = load("maps/m4l1.bsp")
    n = [[1823.0, 225.0, -120.0]] + chain(e, "truck01_path")
    c, y = crate_for(n, [3788, 4935])
    routes["m4l1"] = [dict(name="truck01", kind="truck", model="models/vehicles/opeltruckgreen.tik", nodes=n, crate=c, crateyaw=y,
                           src="maps/m4l1.scr::truck01_drive pose + truck01_path 12n")]
    # m4l2 (AA): camp truck gate -> camp
    e = load("maps/m4l2.bsp")
    n = chain(e, "camptruck_pathgate") + chain(e, "camptruck_pathpark")
    c, y = crate_for(n, [4424, 4456])
    routes["m4l2"] = [dict(name="camptruck", kind="truck", model="models/vehicles/opeltruckgreen_canopy.tik", nodes=n, crate=c, crateyaw=y,
                           src="camptruck_pathgate 8n + camptruck_pathpark 10n")]
    json.dump(routes, open(OUT, "w"), indent=1)
    for m, rs in routes.items():
        for r in rs:
            print(m, r["name"], r["kind"], len(r["nodes"]), "nodes, stop", r["nodes"][-1], "crate", r["crate"])


if __name__ == "__main__":
    main()

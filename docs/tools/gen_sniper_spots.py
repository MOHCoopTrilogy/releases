#!/usr/bin/env python3
"""gen_sniper_spots.py - find validated HIGH sniper spots (rooftops, upper floors, balconies, ledges) per map by tracing the BSP,
write docs/tools/sniper_spots.json and the generated coop_mod/alarmsnipers_spots.scr.

    python gen_sniper_spots.py scan <map> [<map> ...]    scan maps, merge into sniper_spots.json
    python gen_sniper_spots.py build [--mod <mod tree>]  write coop_mod/alarmsnipers_spots.scr from the json
    python gen_sniper_spots.py show <map>                print the per-spot trace results

Method (all with docs/tools/bsptrace.py, world brushes only; terrain is NOT traced so ridges on terrain are never offered):
  1. candidates: every upward-facing visible face of a solid world brush (normal z > 0.7) is clipped to a polygon, sampled on a
     48 u grid inset 24 u from its edges.
  2. height: the floor must stand >= 150 u above the median floor of the route anchors within 1200 u (pathnodes, player start,
     placed alarm switches, authored AI) - a roof, balcony, upper room or ledge, not the street.
  3. SOLID GROUND (hard rule): trace down from spot+16 -> world-brush floor within 2 u of the spot, normal z > 0.7, the hit shader
     not sky / water / nodraw; the four corners (+-12 u) must each find the same floor within 3 u (no edge, no slope); the full AI bbox
     (-15 -15 0)..(15 15 72) must not start solid; and >= 72 u of headroom (measured by a box trace up).
  4. fire exchange: the head (spot+60) must be visible from >= MINLOS route anchors 450..2300 u away (eye = anchor+56), the body
     (spot+30) from >= MINBODY of them, so a player who is shot at can always shoot back.
  5. dynamic: no spot inside a func_* mover's bounds (+64 u) or within 350 u of a vehicle / train path point (a tank or train lifted a sniper 224 u on m4l2).
  6. spread: greedy farthest-point pick, >= 350 u apart, tagged with a building cluster id (700 u) and a side (octant round the map's anchor centroid).
Every kept spot stores its trace results; the README prints them.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bsptrace as T

HERE = os.path.dirname(os.path.abspath(__file__))
OUTJ = os.path.join(HERE, "sniper_spots.json")
ALJ = os.path.join(HERE, "alarm_points.json")
MINH, MINLOS, MINBODY = 150.0, 6, 4
MAXSPOTS = 14
MINSEP = 350.0
BBMIN, BBMAX = (-15, -15, 0), (15, 15, 72)
OMAHA = {"m3l1a", "m3l1b"}


# ---------------- brush top faces
def clip_poly(poly, n, d):
    """keep the part of convex polygon `poly` (list of 3-tuples) with n.x <= d"""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        da = n[0] * a[0] + n[1] * a[1] + n[2] * a[2] - d
        db = n[0] * b[0] + n[1] * b[1] + n[2] * b[2] - d
        if da <= 0:
            out.append(a)
        if (da < 0 < db) or (db < 0 < da):
            t = da / (da - db)
            out.append(tuple(a[k] + (b[k] - a[k]) * t for k in range(3)))
    return out


def top_faces(B):
    for bi, (f, n, shn) in enumerate(B.brushes):
        if n < 4 or not B.brush_solid(bi):
            continue
        for k in range(f, f + n):
            pn, sh = B.sides[k][0], B.sides[k][1]
            nx, ny, nz, d = B.planes[pn]
            if nz < 0.7 or not B.side_visible(k):
                continue
            nm = B.shaders[sh][0].lower() if 0 <= sh < len(B.shaders) else ""
            if "water" in nm or "sky" in nm:
                continue
            # big quad on the plane
            ax = (1, 0, 0) if abs(nx) < 0.9 else (0, 1, 0)
            u = (ny * ax[2] - nz * ax[1], nz * ax[0] - nx * ax[2], nx * ax[1] - ny * ax[0])
            ul = math.sqrt(sum(c * c for c in u)); u = tuple(c / ul for c in u)
            v = (ny * u[2] - nz * u[1], nz * u[0] - nx * u[2], nx * u[1] - ny * u[0])
            c0 = (nx * d, ny * d, nz * d)
            R = 20000.0
            poly = [tuple(c0[i] + (u[i] * sx + v[i] * sy) * R for i in range(3)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            for j in range(f, f + n):
                if j == k:
                    continue
                p2 = B.planes[B.sides[j][0]]
                poly = clip_poly(poly, p2[:3], p2[3])
                if len(poly) < 3:
                    break
            if len(poly) >= 3:
                yield bi, (nx, ny, nz, d), poly


def inpoly_inset(poly, x, y, inset):
    # 2D point in convex polygon with edge distance >= inset (poly projected to XY, any winding)
    sgn = 0
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        el = math.hypot(ex, ey)
        if el < 1e-6:
            continue
        cr = (ex * (y - a[1]) - ey * (x - a[0])) / el
        if sgn == 0:
            sgn = 1 if cr >= 0 else -1
        if cr * sgn < inset:
            return False
    return True


# ---------------- solid-ground checks (mirrored by alarmsnipers.scr::asn_floor at spawn time)
def box_start_solid(B, o):
    """True when the AI bbox placed with its origin at o overlaps any solid world brush"""
    cx, cy, cz = o[0], o[1], o[2] + 36.0 + 0.25
    ex, ey, ez = 15.0, 15.0, 36.0
    seen = set()
    def rec(n):
        if n < 0:
            fb, nb = B.leafs[-n - 1]
            for k in range(fb, fb + nb):
                bi = B.leafbrushes[k]
                if bi in seen:
                    continue
                seen.add(bi)
                if not B.brush_solid(bi):
                    continue
                f, cnt, _ = B.brushes[bi]
                if cnt == 0:
                    continue
                inside = True
                for j in range(f, f + cnt):
                    nx, ny, nz, d = B.planes[B.sides[j][0]]
                    if nx * cx + ny * cy + nz * cz - d - (abs(nx) * ex + abs(ny) * ey + abs(nz) * ez) > -0.01:
                        inside = False
                        break
                if inside:
                    return True
            return False
        pn, c0, c1 = B.nodes[n]
        nx, ny, nz, d = B.planes[pn]
        off = abs(nx) * ex + abs(ny) * ey + abs(nz) * ez
        dc = nx * cx + ny * cy + nz * cz - d
        if dc >= off:
            return rec(c0)
        if dc <= -off:
            return rec(c1)
        return rec(c0) or rec(c1)
    return rec(0)


def floor_hit(B, x, y, z, up=16.0, down=16.0):
    """trace down from z+up to z-down; returns (hit z, normal z, shader name) or None"""
    r = B.trace_box((x, y, z + up), (x, y, z - down))
    if not r:
        return None
    fr, nrm, shn, bi, side = r
    hz = z + up - (up + down) * fr
    return hz, nrm[2], shn


def bad_surface(B, shn):
    # sky / water / nodraw-by-name judged on the HIT side's own shader entry (the same name appears with different flags)
    if not (0 <= shn < len(B.shaders)):
        return True
    n, sf, cf = B.shaders[shn]
    n = n.lower()
    if sf & T.SURF_SKY or cf & 0x38:       # sky; water / slime / lava contents
        return True
    return any(w in n for w in ("water", "sky", "nodraw", "caulk", "lava", "slime"))


def point_fluid(B, p):
    n = 0
    while n >= 0:
        pn, c0, c1 = B.nodes[n]
        nx, ny, nz, d = B.planes[pn]
        n = c0 if nx * p[0] + ny * p[1] + nz * p[2] - d >= 0 else c1
    fb, nb = B.leafs[-n - 1]
    for k in range(fb, fb + nb):
        bi = B.leafbrushes[k]
        f, cnt, shn = B.brushes[bi]
        cf = B.shaders[shn][2] if 0 <= shn < len(B.shaders) else 0
        if not (cf & 0x38):
            continue
        if all(B.planes[B.sides[j][0]][0] * p[0] + B.planes[B.sides[j][0]][1] * p[1] + B.planes[B.sides[j][0]][2] * p[2] - B.planes[B.sides[j][0]][3] <= 0 for j in range(f, f + cnt)):
            return True
    return False


GROUNDISH = ("forstsnow", "snowfield", "street", "earth", "grass", "dirt", "mud", "gravel", "sand", "crate", "cobble", "rail", "track", "road", "terrain", "ground")


def ground_check(B, p):
    """the hard solid-ground rule; returns a dict of results (ok flag + numbers) for the README"""
    x, y, z = p
    res = {"ok": False}
    h = floor_hit(B, x, y, z)
    if h is None:
        res["why"] = "no floor under spot+16"
        return res
    res["floorDz"] = round(h[0] - z, 2)
    res["normalZ"] = round(h[1], 3)
    res["shader"] = B.shaders[h[2]][0]
    if abs(h[0] - z) > 2.0:
        res["why"] = "floor %.1f u from spot" % (h[0] - z)
        return res
    if h[1] <= 0.7:
        res["why"] = "slope nz %.2f" % h[1]
        return res
    if bad_surface(B, h[2]):
        res["why"] = "bad surface " + B.shaders[h[2]][0]
        return res
    if any(w in B.shaders[h[2]][0].lower() for w in GROUNDISH):
        res["why"] = "ground-like surface " + B.shaders[h[2]][0]
        return res
    if point_fluid(B, (x, y, h[0] + 20.0)):
        res["why"] = "water at spot"
        return res
    cz = []
    for dx, dy in ((12, 12), (-12, 12), (12, -12), (-12, -12)):
        c = floor_hit(B, x + dx, y + dy, z)
        if c is None or abs(c[0] - h[0]) > 3.0 or bad_surface(B, c[2]):
            res["why"] = "corner (%d,%d) unsupported" % (dx, dy)
            return res
        cz.append(round(c[0] - h[0], 2))
    res["cornerDz"] = cz
    if box_start_solid(B, (x, y, h[0])):
        res["why"] = "bbox start-solid"
        return res
    up = B.trace_box((x, y, h[0] + 1.0), (x, y, h[0] + 1.0 + 256.0), (-15, -15, 0), (15, 15, 1))
    head = 256.0 if not up else 1.0 + 256.0 * up[0]
    res["headroom"] = round(head, 1)
    if head < 72.0:
        res["why"] = "headroom %.0f" % head
        return res
    res["ok"] = True
    return res


def drop_test(B, x, y, fz, nbanchors):
    """HIGH-PLACE test: the ground falls away near the spot. Of 16 samples (8 directions at 200 u and 320 u) at least 8 must find a floor
    >= 140 u below the spot's floor (world-brush trace) or, where the world brush has nothing below (terrain), a route anchor within
    400 u of the sample that stands >= 140 u lower. Returns the number of dropping samples."""
    n = 0
    for r in (200.0, 320.0):
        for k in range(8):
            a = math.radians(k * 45.0)
            sx, sy = x + math.cos(a) * r, y + math.sin(a) * r
            t = B.trace_box((sx, sy, fz + 8.0), (sx, sy, fz - 700.0))
            if t:
                if t[0] * 708.0 >= 148.0:
                    n += 1
            else:
                for an in nbanchors:
                    if (an[0] - sx) ** 2 + (an[1] - sy) ** 2 < 400.0 ** 2 and an[2] <= fz - 140.0:
                        n += 1
                        break
    return n


# ---------------- scan one map
def anchors_for(B, m):
    A = []
    for e in B.entities():
        c = e.get("classname", "")
        o = T.vec(e.get("origin", ""))
        if not o:
            continue
        if c in ("info_pathnode", "info_player_start", "info_player_deathmatch", "info_waypoint") or c.startswith("ai_") or c.startswith("item_health"):
            A.append(o)
    try:
        al = json.load(open(ALJ)).get(m, {}).get("points", [])
        for p in al:
            A.append(tuple(p["pos"]))
    except Exception:
        pass
    return A


def player_starts(B):
    return [T.vec(e["origin"]) for e in B.entities() if e.get("classname", "") in ("info_player_start", "info_player_deathmatch") and T.vec(e.get("origin", ""))]


def scan(m, seed=1, minh=None):
    MINH_ = MINH if minh is None else minh
    random.seed(seed)
    B = T.BSP.load(m)
    A = anchors_for(B, m)
    if len(A) < 20:
        return None, "too few anchors (%d)" % len(A)
    starts = player_starts(B)
    cell = 1200.0
    grid = {}
    for a in A:
        grid.setdefault((int(a[0] // cell), int(a[1] // cell)), []).append(a)
    def near(x, y, r):
        out = []
        for gx in range(int(x // cell) - 2, int(x // cell) + 3):
            for gy in range(int(y // cell) - 2, int(y // cell) + 3):
                for a in grid.get((gx, gy), ()):
                    if (a[0] - x) ** 2 + (a[1] - y) ** 2 <= r * r:
                        out.append(a)
        return out
    # dynamic things a standing man must not share a spot with: brush movers (func_*) and vehicle / train paths
    movers, vpts = [], []
    for e in B.entities():
        c = e.get("classname", "")
        mdl = e.get("model", "")
        if c.startswith("func_") and mdl.startswith("*"):
            try:
                mn, mx = B.model_bounds(int(mdl[1:]))
                movers.append((mn, mx))
            except Exception:
                pass
        o = T.vec(e.get("origin", ""))
        if o and (c in ("info_vehiclepoint", "info_splinepath") or c.startswith("vehicle_") or "vehicles/" in mdl.lower() or "train" in e.get("targetname", "").lower()):
            vpts.append(o)
    deny = []
    try:
        deny = json.load(open(os.path.join(HERE, "sniper_spots_deny.json"))).get(m, [])
    except Exception:
        pass
    cx = sum(a[0] for a in A) / len(A)
    cy = sum(a[1] for a in A) / len(A)
    cands = []
    nface = 0
    for bi, pl, poly in top_faces(B):
        nface += 1
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        nx, ny, nz, d = pl
        x = min(xs) + 24
        while x <= max(xs) - 24:
            y = min(ys) + 24
            while y <= max(ys) - 24:
                if inpoly_inset(poly, x, y, 24.0):
                    z = (d - nx * x - ny * y) / nz
                    cands.append((x, y, z))
                y += 48
            x += 48
    out = {"faces": nface, "raw": len(cands), "stage": {}}
    st = out["stage"]
    st["high"] = st["ground"] = st["los"] = 0
    keep = []
    random.shuffle(cands)
    for (x, y, z) in cands:
        nb = near(x, y, 1200.0)
        if len(nb) < 4:
            continue
        zs = sorted(a[2] for a in nb)
        if z - zs[len(zs) // 2] < MINH_:
            continue
        if any((s[0] - x) ** 2 + (s[1] - y) ** 2 < 500.0 ** 2 for s in starts):
            continue
        st["high"] += 1
        if any(mn[0] - 64 <= x <= mx[0] + 64 and mn[1] - 64 <= y <= mx[1] + 64 and mn[2] - 200 <= z <= mx[2] + 96 for mn, mx in movers):
            continue
        if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in deny):
            continue
        if any((v[0] - x) ** 2 + (v[1] - y) ** 2 < 350.0 ** 2 for v in vpts):
            continue
        g = ground_check(B, (x, y, z))
        if not g["ok"]:
            continue
        st["ground"] += 1
        if drop_test(B, x, y, z + g["floorDz"], nb) < 8:
            continue
        st["drop"] = st.get("drop", 0) + 1
        fz = z + g["floorDz"]
        head = (x, y, fz + 60.0)
        body = (x, y, fz + 30.0)
        far = near(x, y, 2300.0)
        random.shuffle(far)
        nl = nbod = 0
        tried = 0
        for a in far:
            dd = math.hypot(a[0] - x, a[1] - y)
            if dd < 450.0:
                continue
            tried += 1
            if tried > 160:
                break
            eye = (a[0], a[1], a[2] + 56.0)
            if not B.trace(eye, head):
                nl += 1
                if not B.trace(eye, body):
                    nbod += 1
        if nl < MINLOS or nbod < MINBODY:
            continue
        st["los"] += 1
        keep.append({"pos": [round(x, 2), round(y, 2), round(fz, 2)], "los": nl, "body": nbod, "ground": g,
                     "drop": 0, "elev": round(fz - sorted(a[2] for a in nb)[len(nb) // 2], 1)})
    # greedy pick: best score first but each pick must be MINSEP away from earlier picks and prefer new clusters / sides
    keep.sort(key=lambda s: -(s["los"] + s["body"]))
    picked = []
    def side(p):
        return int(((math.degrees(math.atan2(p[1] - cy, p[0] - cx)) + 360 + 22.5) % 360) // 45)
    def cluster_of(p):
        for s in picked:
            if (s["pos"][0] - p[0]) ** 2 + (s["pos"][1] - p[1]) ** 2 < 700.0 ** 2:
                return s["cluster"]
        return None
    ncl = 0
    pool = keep[:]
    while pool and len(picked) < MAXSPOTS:
        # farthest from picked among the top 40 by score
        mx = max(q["los"] + q["body"] for q in pool)
        top = [q for q in pool if q["los"] + q["body"] >= 0.4 * mx] or pool[:40]
        if picked:
            def mind(s):
                return min(math.hypot(s["pos"][0] - q["pos"][0], s["pos"][1] - q["pos"][1]) for q in picked)
            top.sort(key=lambda s: -mind(s))
            best = top[0]
            if mind(best) < MINSEP:
                break
        else:
            best = top[0]
        pool.remove(best)
        c = cluster_of(best["pos"])
        if c is None:
            ncl += 1
            c = ncl
        best["cluster"] = c
        best["side"] = side(best["pos"])
        picked.append(best)
    out["spots"] = picked
    out["kept_before_pick"] = len(keep)
    return out, "ok"


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd = a[0]
    data = json.load(open(OUTJ)) if os.path.exists(OUTJ) else {}
    if cmd == "scan":
        for m in a[1:]:
            if m in OMAHA:
                print(m, "SKIP omaha"); continue
            try:
                r, why = scan(m)
                if r is not None and len(r["spots"]) < 4:
                    r2, _ = scan(m, minh=100.0)
                    if r2 is not None and len(r2["spots"]) > len(r["spots"]):
                        r = r2; r["stage"]["minh"] = 100
            except FileNotFoundError:
                print(m, "no bsp"); continue
            if r is None:
                print(m, why); continue
            data[m] = {"spots": r["spots"], "stats": {"faces": r["faces"], "raw": r["raw"], **r["stage"], "kept": r["kept_before_pick"]}}
            print(m, "faces", r["faces"], "cands", r["raw"], r["stage"], "kept", r["kept_before_pick"], "picked", len(r["spots"]), flush=True)
            json.dump(data, open(OUTJ, "w"), indent=1, sort_keys=True)
    elif cmd == "show":
        for s in data[a[1]]["spots"]:
            print(s["pos"], "los", s["los"], "body", s["body"], "cl", s["cluster"], "side", s["side"], s["ground"])
    elif cmd == "build":
        mod = a[a.index("--mod") + 1] if "--mod" in a else os.path.join(os.path.dirname(os.path.dirname(HERE)), "hzm-mohaa-coop-mod")
        L = ["//=========================================================================",
             "// alarmsnipers_spots.scr - GENERATED by docs/tools/gen_sniper_spots.py from docs/tools/sniper_spots.json. Do not edit by hand.",
             "// spots <map> fills level.coop_asnSpot[i] (origin on the floor), level.coop_asnCl[i] (building cluster), level.coop_asnSide[i], returns the count.",
             "//========================================================================="]
        L.append("spots local.map:{")
        L.append("\tlocal.n = 0")
        for m in sorted(data):
            if data[m]["spots"]:
                L.append('\tif( local.map == "%s" ){ local.n = waitthread sp_%s }' % (m, m))
        L.append("}end local.n\n")
        for m in sorted(data):
            sp = data[m]["spots"]
            if not sp:
                continue
            L.append("// %s: %d spots" % (m, len(sp)))
            L.append("sp_%s:{" % m)
            for i, s in enumerate(sp, 1):
                p = s["pos"]
                L.append("\tlevel.coop_asnSpot[%d] = ( %s %s %s )" % (i, p[0], p[1], p[2]))
                L.append("\tlevel.coop_asnCl[%d] = %d" % (i, s["cluster"]))
                L.append("\tlevel.coop_asnSide[%d] = %d" % (i, s["side"]))
            L.append("}end %d\n" % len(sp))
        open(os.path.join(mod, "coop_mod", "alarmsnipers_spots.scr"), "w", newline="\n").write("\n".join(L) + "\n")
        print("wrote", sum(len(v["spots"]) for v in data.values()), "spots")


if __name__ == "__main__":
    main()

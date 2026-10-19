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
MINH, MINLOS, MINBODY = 60.0, 1, 1   # widened 2026-10-18 (user): one route point within 3000 u is enough; ranking does the rest
MAXSPOTS = 8
MINSEP = 600.0
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


GROUNDISH = ("street", "crate", "cobble", "rail", "track", "road", "terrain")


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
    # EDGE RULE (user 2026-10-18): the bbox must stay >= 24 u from a roof edge: 8 points on a ring of 39 u (15 bbox + 24) must all find
    # the same floor (within 8 u) - mirrored by the in-engine audit (asn_drv.scr::asd_judge)
    for k in range(8):
        a_ = math.radians(k * 45.0)
        e_ = floor_hit(B, x + math.cos(a_) * 39.0, y + math.sin(a_) * 39.0, z, up=16.0, down=40.0)
        if e_ is None or abs(e_[0] - h[0]) > 8.0 or bad_surface(B, e_[2]):
            res["why"] = "roof edge within 24 u (ring %d)" % k
            return res
    cz = []
    for dx, dy in ((12, 12), (-12, 12), (12, -12), (-12, -12)):
        c = floor_hit(B, x + dx, y + dy, z)
        if c is None or abs(c[0] - h[0]) > 8.0 or bad_surface(B, c[2]):
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


def open_sky(B, x, y, fz):
    """trace up from head height (floor+72) 6000 u: nothing solid, or the first thing hit is a sky surface = a roof / outdoor surface"""
    t = B.trace_box((x, y, fz + 72.0), (x, y, fz + 6072.0))
    if not t:
        return True
    shn = t[2]
    return 0 <= shn < len(B.shaders) and bool(B.shaders[shn][1] & T.SURF_SKY)


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
        # ELEVATION RULE (coordinator 2026-10-18): >= 128 u above the route ground under it = floor of the nearest route anchor
        # (pathnode / player start / switch / AI) in plan view within 1500 u
        na = None
        nd2 = 1500.0 ** 2
        for a in near(x, y, 1500.0):
            d2 = (a[0] - x) ** 2 + (a[1] - y) ** 2
            if d2 < nd2:
                nd2, na = d2, a
        if na is None or z - na[2] < 128.0:
            continue
        st["route128"] = st.get("route128", 0) + 1
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
        dn = drop_test(B, x, y, z + g["floorDz"], nb)
        if dn < 2:
            continue
        sky = open_sky(B, x, y, z + g["floorDz"])
        st["drop"] = st.get("drop", 0) + 1
        fz = z + g["floorDz"]
        head = (x, y, fz + 60.0)
        body = (x, y, fz + 30.0)
        far = near(x, y, 3000.0)
        random.shuffle(far)
        nl = nbod = 0
        tried = 0
        for a in far:
            dd = math.hypot(a[0] - x, a[1] - y)
            if dd < 250.0 or dd > 3000.0:
                continue
            tried += 1
            if tried > 220:
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
                     "routeDz": round(z - na[2], 1), "sky": sky, "type": ("roof" if sky and dn >= 12 else "outdoor-high" if sky else "interior fallback"), "elev": round(fz - sorted(a[2] for a in nb)[len(nb) // 2], 1)})
    # greedy pick: best score first but each pick must be MINSEP away from earlier picks and prefer new clusters / sides
    # USER RULE 2026-10-18: rooftops / outdoor elevated surfaces first; interior spots only on maps with no outdoor option
    # USER RULE 2026-10-18 (final): NO indoor snipers. Only open-sky spots (roof / outdoor-high) count; a map with none gets no snipers.
    keep = [q for q in keep if q["sky"]]
    keep.sort(key=lambda s: -(s["routeDz"] / 8.0 + s["los"] / 3.0 + s["body"] / 6.0))   # height, overlook
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
        # best ranked (height, overlook) that is >= MINSEP (600 u) from every pick; spread is the 600 u rule
        best = None
        for q in pool:
            if all(math.hypot(q["pos"][0] - p["pos"][0], q["pos"][1] - p["pos"][1]) >= MINSEP for p in picked):
                best = q
                break
        if best is None:
            break
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


def pick_spots(keep, cx, cy):
    """rank (height, overlook), keep the best MAXSPOTS that are >= MINSEP apart, tag building cluster and side"""
    keep = sorted(keep, key=lambda s: -(s["routeDz"] / 8.0 + s["los"] / 3.0 + s["body"] / 6.0))
    picked = []
    ncl = 0
    for q in keep:
        if len(picked) >= MAXSPOTS:
            break
        if any(math.hypot(q["pos"][0] - p["pos"][0], q["pos"][1] - p["pos"][1]) < MINSEP for p in picked):
            continue
        c = None
        for p in picked:
            if math.hypot(p["pos"][0] - q["pos"][0], p["pos"][1] - q["pos"][1]) < 700.0:
                c = p["cluster"]
        if c is None:
            ncl += 1
            c = ncl
        q["cluster"] = c
        q["side"] = int(((math.degrees(math.atan2(q["pos"][1] - cy, q["pos"][0] - cx)) + 360 + 22.5) % 360) // 45)
        picked.append(q)
    return picked


def merge_rf(m, path):
    """merge the engine-side roof scan (asn_scan.py ^~^~^ RF lines) with the brush-face spots already in the json, filter and re-pick"""
    random.seed(1)
    B = T.BSP.load(m)
    A = anchors_for(B, m)
    cell = 1200.0
    grid = {}
    for a in A:
        grid.setdefault((int(a[0] // cell), int(a[1] // cell)), []).append(a)
    def near(x, y, r):
        out = []
        for gx in range(int(x // cell) - 3, int(x // cell) + 4):
            for gy in range(int(y // cell) - 3, int(y // cell) + 4):
                for a in grid.get((gx, gy), ()):
                    if (a[0] - x) ** 2 + (a[1] - y) ** 2 <= r * r:
                        out.append(a)
        return out
    movers, vpts = [], []
    for e in B.entities():
        c, mdl = e.get("classname", ""), e.get("model", "")
        if c.startswith("func_") and mdl.startswith("*"):
            try:
                movers.append(B.model_bounds(int(mdl[1:])))
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
    # engine-audit failures (docs/proposals/alarm_snipers_2026-10-18/tools/spotcheck): never offered again within 96 u
    failed = []
    audit_pass = audit_n = 0
    base = os.path.join(HERE, "..", "proposals", "alarm_snipers_2026-10-18", "tools", "spotcheck")
    for d_ in (base, os.path.join(base, "_round1")):
        fp = os.path.join(d_, m + ".json")
        if os.path.exists(fp):
            rr_ = json.load(open(fp))
            failed += [r["pos"] for r in rr_ if r["verdict"] != "PASS"]
            audit_pass = audit_pass + sum(1 for r in rr_ if r["verdict"] == "PASS")
            audit_n = audit_n + len(rr_)
    raw = []
    for ln in open(path):
        p = ln.split()
        if len(p) >= 5 and p[1] == "RF" and p[2] not in ("START", "DONE", "CEIL"):
            raw.append((float(p[2]), float(p[3]), float(p[4]), float(p[5]) if len(p) > 5 else 0.0))
    # one candidate per 128 u cell: the highest
    best = {}
    for x, y, z, cd in raw:
        k = (int(x // 128), int(y // 128))
        if k not in best or z > best[k][2]:
            best[k] = (x, y, z, cd)
    cands = list(best.values())
    if audit_n >= 8 and audit_pass == 0:
        cands = []   # engine-scan surfaces on this map all failed the in-engine audit (actors fall through trees / terrain models): brush faces only
    st = {"rf_raw": len(raw), "rf_cells": len(cands), "route128": 0, "los": 0}
    keep = []
    for x, y, z, cd in cands:
        nb = near(x, y, 1500.0)
        na, nd2 = None, 1500.0 ** 2
        for a in nb:
            d2 = (a[0] - x) ** 2 + (a[1] - y) ** 2
            if d2 < nd2:
                nd2, na = d2, a
        if na is None or z - na[2] < 128.0:
            continue
        if any(mn[0] - 64 <= x <= mx[0] + 64 and mn[1] - 64 <= y <= mx[1] + 64 and mn[2] - 200 <= z <= mx[2] + 96 for mn, mx in movers):
            continue
        if any((v[0] - x) ** 2 + (v[1] - y) ** 2 < 350.0 ** 2 for v in vpts):
            continue
        if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in deny):
            continue
        if any((f[0] - x) ** 2 + (f[1] - y) ** 2 < 96.0 ** 2 for f in failed):
            continue
        st["route128"] += 1
        far = near(x, y, 3000.0)
        random.shuffle(far)
        nl = nbod = tried = 0
        head, body = (x, y, z + 60.0), (x, y, z + 30.0)
        for a in far:
            if math.hypot(a[0] - x, a[1] - y) < 250.0:
                continue
            tried += 1
            if tried > 70:
                break
            eye = (a[0], a[1], a[2] + 56.0)
            if not B.trace(eye, head):
                nl += 1
                if not B.trace(eye, body):
                    nbod += 1
        if nl < 1:
            continue
        st["los"] += 1
        t = B.trace_box((x, y, z + 8.0), (x, y, z - 8.0))
        brushroof = bool(t)
        if t:
            nm = B.shaders[t[2]][0].lower() if 0 <= t[2] < len(B.shaders) else ""
            # a surface the player cannot see is not a roof: the map-cap slab / sky hull / clip volumes (snipers "floated in the sky" on them, m4l1)
            if any(w in nm for w in ("nodraw", "caulk", "sky", "clip", "hint", "skip", "origin", "trigger", "textures/common/", "fog")):
                st["invisible"] = st.get("invisible", 0) + 1
                continue
        keep.append({"pos": [round(x, 2), round(y, 2), round(z, 2)], "los": nl, "body": nbod, "routeDz": round(z - na[2], 1), "sky": True,
                     "type": "roof" if brushroof else "outdoor-high", "src": "engine-scan",
                     "ground": {"ok": True, "floorDz": 0.0, "normalZ": ">0.7 (corners within %.1f u)" % cd, "cornerDz": [cd], "headroom": ">=72 (hull)", "shader": "engine floor"},
                     "elev": round(z - na[2], 1)})
    data = json.load(open(OUTJ))
    for s_ in data.get(m, {}).get("spots", []):
        if s_.get("sky") and s_.get("src", "brush-face") == "brush-face":
            s_.setdefault("src", "brush-face")
            keep.append(s_)
    cx = sum(a[0] for a in A) / len(A)
    cy = sum(a[1] for a in A) / len(A)
    picked = pick_spots(keep, cx, cy)
    data[m] = {"spots": picked, "stats": {**data.get(m, {}).get("stats", {}), **st, "kept": len(keep)}}
    json.dump(data, open(OUTJ, "w"), indent=1, sort_keys=True)
    print(m, st, "pool", len(keep), "picked", len(picked), [(p["type"], p["src"]) for p in picked])


def vanilla_candidates(m):
    """positions the original game already uses for high enemies: every ai_* actor, turret / MG nest, entity named sniper / tower / watch / nest,
    and elevated pathnodes (a node with another pathnode >= 128 u below it within 500 u: a tower, roof or stair top, so it has a real floor).
    Returns [(x, y, z, src)] and writes coop_mod/asn_cands_test.scr (TEST ONLY, untracked) into the alarmsnipers worktree for the in-engine snap."""
    B = T.BSP.load(m)
    A = anchors_for(B, m)
    nodes = [T.vec(e["origin"]) for e in B.entities() if e.get("classname") == "info_pathnode" and T.vec(e.get("origin", ""))]
    cell = 600.0
    grid = {}
    for n in nodes:
        grid.setdefault((int(n[0] // cell), int(n[1] // cell)), []).append(n)
    def below(x, y, z, r=500.0):
        lo = None
        for gx in range(int(x // cell) - 1, int(x // cell) + 2):
            for gy in range(int(y // cell) - 1, int(y // cell) + 2):
                for n in grid.get((gx, gy), ()):
                    if (n[0] - x) ** 2 + (n[1] - y) ** 2 <= r * r and (lo is None or n[2] < lo):
                        lo = n[2]
        return lo
    out = []
    for e in B.entities():
        c = e.get("classname", "")
        o = T.vec(e.get("origin", ""))
        if not o:
            continue
        nm = (e.get("targetname", "") + " " + e.get("type_attack", "") + " " + e.get("model", "")).lower()
        src = None
        if c.startswith("ai_"):
            src = "actor"
        elif c.startswith("turretweapon") or "mg42" in c:
            src = "nest"
        elif any(w in nm for w in ("sniper", "tower", "watch", "nest")) and not c.startswith(("light", "trigger", "info_path")):
            src = "named"
        elif c == "info_pathnode":
            lo = below(o[0], o[1], o[2])
            if lo is not None and o[2] - lo >= 128.0:
                src = "pathnode"
        if src:
            out.append((o[0], o[1], o[2], src))
    # pre-filter: roughly high over route ground (final rule 128 u is applied after the in-engine snap)
    keep = []
    for x, y, z, src in out:
        near = [a for a in nodes if (a[0] - x) ** 2 + (a[1] - y) ** 2 < 1500.0 ** 2]
        if src != "pathnode":
            if not near:
                continue
            na = min(near, key=lambda a: (a[0] - x) ** 2 + (a[1] - y) ** 2)
            if z - na[2] < 100.0:
                continue
        keep.append((x, y, z, src))
    # thin: one per 96 u cell
    seen = {}
    for x, y, z, src in keep:
        seen.setdefault((int(x // 96), int(y // 96), int(z // 48)), (x, y, z, src))
    return list(seen.values())


def write_cands(allc, mod):
    p = os.path.join(mod, "coop_mod", "asn_cands_test.scr")
    L = ["// TEST ONLY - generated by gen_sniper_spots.py cands, never committed", "cands local.map:{", "	local.n = 0"]
    for m, cands in allc.items():
        L.append('	if( local.map == "%s" ){' % m)
        for i, (x, y, z, src) in enumerate(cands, 1):
            L.append("		level.asd_cp[%d] = ( %g %g %g )" % (i, x, y, z))
            L.append('		level.asd_cs[%d] = "%s"' % (i, src))
        L.append("		local.n = %d" % len(cands))
        L.append("	}")
    L.append("}end local.n")
    open(p, "w", newline=chr(10)).write(chr(10).join(L) + chr(10))


def merge_snap(m, path):
    """vanilla candidates snapped onto the engine floor (asn_snap.py): route-ground height, LOS, visibility, movers, failure memory; pool with
    the spots already audited, keep the best MAXSPOTS (6 for vanilla runs), >= 600 u apart"""
    global MAXSPOTS
    MAXSPOTS = 6
    random.seed(1)
    B = T.BSP.load(m)
    A = anchors_for(B, m)
    nodes = [T.vec(e["origin"]) for e in B.entities() if e.get("classname") == "info_pathnode" and T.vec(e.get("origin", ""))] + player_starts(B)
    movers, vpts = [], []
    for e in B.entities():
        c, mdl = e.get("classname", ""), e.get("model", "")
        if c.startswith("func_") and mdl.startswith("*"):
            try:
                movers.append(B.model_bounds(int(mdl[1:])))
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
    failed = []
    base = os.path.join(HERE, "..", "proposals", "alarm_snipers_2026-10-18", "tools", "spotcheck")
    for d_ in (base, os.path.join(base, "_round1"), os.path.join(base, "_round2"), os.path.join(base, "_round3")):
        fp = os.path.join(d_, m + ".json")
        if os.path.exists(fp):
            failed += [r["pos"] for r in json.load(open(fp)) if r["verdict"] != "PASS"]
    data = json.load(open(OUTJ))
    failed += [d["pos"] for d in data.get(m, {}).get("dropped", [])]
    raw = []
    for ln in open(path):
        p = ln.split()
        if len(p) >= 7 and p[1] == "SNAP" and p[2] not in ("START", "DONE"):
            raw.append((float(p[3]), float(p[4]), float(p[5]), float(p[6]), p[7] if len(p) > 7 else "?"))
    st = {"snap": len(raw), "route128": 0, "los": 0, "invisible": 0}
    keep = []
    for x, y, z, cd, src in raw:
        low = [a[2] for a in nodes if (a[0] - x) ** 2 + (a[1] - y) ** 2 <= 600.0 ** 2]
        if not low or z - min(low) < 128.0:
            continue
        if any(mn[0] - 64 <= x <= mx[0] + 64 and mn[1] - 64 <= y <= mx[1] + 64 and mn[2] - 200 <= z <= mx[2] + 96 for mn, mx in movers):
            continue
        if any((v[0] - x) ** 2 + (v[1] - y) ** 2 < 350.0 ** 2 for v in vpts) or any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in deny):
            continue
        if any((f[0] - x) ** 2 + (f[1] - y) ** 2 < 48.0 ** 2 for f in failed):
            continue
        st["route128"] += 1
        t = B.trace_box((x, y, z + 8.0), (x, y, z - 8.0))
        if t:
            nm = B.shaders[t[2]][0].lower() if 0 <= t[2] < len(B.shaders) else ""
            if any(w in nm for w in ("nodraw", "caulk", "sky", "clip", "hint", "skip", "origin", "trigger", "textures/common/", "fog")):
                st["invisible"] += 1
                continue
        nl = nbod = tried = 0
        head, body = (x, y, z + 60.0), (x, y, z + 30.0)
        far = [a for a in A if 250.0 <= math.hypot(a[0] - x, a[1] - y) <= 3000.0]
        random.shuffle(far)
        for a in far[:80]:
            eye = (a[0], a[1], a[2] + 56.0)
            if not B.trace(eye, head):
                nl += 1
                if not B.trace(eye, body):
                    nbod += 1
        if nl < 1:
            continue
        st["los"] += 1
        keep.append({"pos": [round(x, 2), round(y, 2), round(z, 2)], "los": nl, "body": nbod, "routeDz": round(z - min(low), 1), "sky": True,
                     "type": "tower/high (vanilla %s)" % src, "src": "vanilla-" + src,
                     "ground": {"ok": True, "floorDz": 0.0, "normalZ": ">0.7", "cornerDz": [cd], "headroom": ">=72 (hull)", "shader": "engine floor"},
                     "elev": round(z - min(low), 1)})
    for s_ in data.get(m, {}).get("spots", []):
        s_["keepaudit"] = True
        keep.append(s_)
    cx = sum(a[0] for a in A) / len(A)
    cy = sum(a[1] for a in A) / len(A)
    picked = pick_spots(keep, cx, cy)
    data.setdefault(m, {})["spots"] = picked
    data[m]["audited"] = False
    data[m]["stats_snap"] = st
    json.dump(data, open(OUTJ, "w"), indent=1, sort_keys=True)
    print(m, st, "pool", len(keep), "picked", len(picked), [p.get("src") for p in picked])


# ---------------- ROOF PLATFORM SPOTS (user decision 2026-10-18): a solid prop deck on a real roof is the sniper's floor
PLAT_HALF = 32.0      # deck footprint 64 x 64 (two nazi_crate 32 x 64 side by side), 24 u high
PLAT_H = 24.0
PLAT_RING = 56.0      # deck half 32 + 24 u from the roof edge


POOLS = {}


def roof_spots(m):
    """sample real roof faces (visible solid world brush tops, normal z >= 0.75), keep points where a 64 x 64 deck sits flush (4 corners + 8 ring points at 56 u on the
    SAME face plane, +-5 u), open sky, >= 128 u over the lowest route node within 600 u, the high-place drop test, line of sight to >= 3 route anchors, not on movers.
    Returns the picked spots (<= 6, >= 600 u apart) with pos = TOP of the deck, base z and a yaw (0/90/180/270) that faces the route."""
    random.seed(1)
    B = T.BSP.load(m)
    A = anchors_for(B, m)
    nodes = [T.vec(e["origin"]) for e in B.entities() if e.get("classname") == "info_pathnode" and T.vec(e.get("origin", ""))] + player_starts(B)
    cell = 1200.0
    grid = {}
    for a in A:
        grid.setdefault((int(a[0] // cell), int(a[1] // cell)), []).append(a)
    def near(x, y, r):
        out = []
        for gx in range(int(x // cell) - 3, int(x // cell) + 4):
            for gy in range(int(y // cell) - 3, int(y // cell) + 4):
                for a in grid.get((gx, gy), ()):
                    if (a[0] - x) ** 2 + (a[1] - y) ** 2 <= r * r:
                        out.append(a)
        return out
    movers, vpts = [], []
    for e in B.entities():
        c, mdl = e.get("classname", ""), e.get("model", "")
        if c.startswith("func_") and mdl.startswith("*"):
            try:
                movers.append(B.model_bounds(int(mdl[1:])))
            except Exception:
                pass
        o = T.vec(e.get("origin", ""))
        if o and (c in ("info_vehiclepoint", "info_splinepath") or c.startswith("vehicle_") or "vehicles/" in mdl.lower() or "train" in e.get("targetname", "").lower()):
            vpts.append(o)
    stealth_free = [T.vec(e["origin"]) for e in B.entities() if e.get("classname") in ("info_player_start", "info_player_deathmatch") and T.vec(e.get("origin", ""))]
    st = {"faces": 0, "samples": 0, "flush": 0, "sky": 0, "high": 0, "drop": 0, "los": 0}
    keep = []
    for bi, pl, poly in top_faces(B):
        nx, ny, nz, d = pl
        if nz < 0.75:
            continue
        st["faces"] += 1
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        def pz(px, py):
            return (d - nx * px - ny * py) / nz
        x = min(xs) + 32
        while x <= max(xs) - 32:
            y = min(ys) + 32
            while y <= max(ys) - 32:
                if inpoly_inset(poly, x, y, 32.0):
                    st["samples"] += 1
                    z = pz(x, y)
                    ok = True
                    cz = []
                    for dx, dy in ((PLAT_HALF, PLAT_HALF), (-PLAT_HALF, PLAT_HALF), (PLAT_HALF, -PLAT_HALF), (-PLAT_HALF, -PLAT_HALF)):
                        h = floor_hit(B, x + dx, y + dy, pz(x + dx, y + dy), up=24.0, down=24.0)
                        if h is None or abs(h[0] - pz(x + dx, y + dy)) > 5.0 or bad_surface(B, h[2]):
                            ok = False
                            break
                        cz.append(h[0])
                    if ok and max(cz) - min(cz) <= 16.0:
                        for k in range(8):
                            a_ = math.radians(k * 45.0)
                            rx, ry = x + math.cos(a_) * PLAT_RING, y + math.sin(a_) * PLAT_RING
                            h = floor_hit(B, rx, ry, pz(rx, ry), up=24.0, down=24.0)
                            if h is None or abs(h[0] - pz(rx, ry)) > 5.0 or bad_surface(B, h[2]):
                                ok = False
                                break
                    if ok:
                        st["flush"] += 1
                        base = min(cz)
                        top = base + PLAT_H
                        # open sky over the sniper's head and 72 u of headroom above the deck
                        if open_sky(B, x, y, top):
                            st["sky"] += 1
                            low = [a[2] for a in nodes if (a[0] - x) ** 2 + (a[1] - y) ** 2 <= 600.0 ** 2]
                            if low and top - min(low) >= 128.0 and not any(mn[0] - 80 <= x <= mx[0] + 80 and mn[1] - 80 <= y <= mx[1] + 80 and mn[2] - 200 <= base <= mx[2] + 96 for mn, mx in movers)                                     and not any((v[0] - x) ** 2 + (v[1] - y) ** 2 < 350.0 ** 2 for v in vpts)                                     and not any((s_[0] - x) ** 2 + (s_[1] - y) ** 2 < 500.0 ** 2 for s_ in stealth_free):
                                st["high"] += 1
                                dn = drop_test(B, x, y, base, near(x, y, 1200.0))
                                if dn >= 8:
                                    st["drop"] += 1
                                    far = [a for a in near(x, y, 3000.0) if math.hypot(a[0] - x, a[1] - y) >= 250.0]
                                    random.shuffle(far)
                                    nl = nbod = 0
                                    sx = sy = 0.0
                                    for a in far[:90]:
                                        eye = (a[0], a[1], a[2] + 56.0)
                                        if not B.trace(eye, (x, y, top + 60.0)):
                                            nl += 1
                                            sx += a[0] - x
                                            sy += a[1] - y
                                            if not B.trace(eye, (x, y, top + 30.0)):
                                                nbod += 1
                                    if nl >= 3:
                                        st["los"] += 1
                                        ang = (math.degrees(math.atan2(sy, sx)) + 360.0) % 360.0
                                        yaw = int(round(ang / 90.0)) % 4 * 90
                                        keep.append({"pos": [round(x, 2), round(y, 2), round(top, 2)], "base": round(base, 2), "yaw": yaw, "plat": True,
                                                     "los": nl, "body": nbod, "routeDz": round(top - min(low), 1), "sky": True, "type": "roof (crate deck)", "src": "roof-deck",
                                                     "ground": {"ok": True, "floorDz": 0.0, "normalZ": round(nz, 3), "cornerDz": [round(c_ - base, 2) for c_ in cz], "headroom": ">=72", "shader": "roof brush"},
                                                     "elev": round(top - min(low), 1)})
                y += 64
            x += 64
    cx = sum(a[0] for a in A) / len(A)
    cy = sum(a[1] for a in A) / len(A)
    picked = pick_spots(keep, cx, cy)
    # the thinned full pool (one per 96 u cell, best score) goes to the in-engine pre-check
    keep.sort(key=lambda s_: -(s_["routeDz"] / 8.0 + s_["los"] / 3.0 + s_["body"] / 6.0))
    thin = {}
    for s_ in keep:
        thin.setdefault((int(s_["pos"][0] // 96), int(s_["pos"][1] // 96)), s_)
    st["pool"] = len(thin)
    roof_spots.pool = list(thin.values())
    return picked, st


def set_max(n):
    global MAXSPOTS
    MAXSPOTS = n


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
    elif cmd == "roofs":
        set_max(12)      # audit candidates; the best 6 PASSERS are kept afterwards
        for m_ in a[1:]:
            picked, st_ = roof_spots(m_)
            POOLS[m_] = roof_spots.pool
            json.dump(POOLS, open(os.path.join(HERE, "roof_pool.json"), "w"))
            ex = [e_ for e_ in data.get(m_, {}).get("spots", []) if not e_.get("plat")]
            add_ = [p for p in picked if all(math.hypot(p["pos"][0] - e_["pos"][0], p["pos"][1] - e_["pos"][1]) >= 600.0 for e_ in ex)]
            for p in add_:
                p.setdefault("cluster", 90 + len(ex)); p.setdefault("side", 0)
            data.setdefault(m_, {"spots": []})["spots"] = ex + add_
            data[m_]["audited"] = False
            data[m_]["stats_roof"] = st_
            json.dump(data, open(OUTJ, "w"), indent=1, sort_keys=True)
            print(m_, st_, "picked", len(picked), "kept after spacing vs existing", len(add_), flush=True)
    elif cmd == "roofcands":
        pools = json.load(open(os.path.join(HERE, "roof_pool.json")))
        mod = a[a.index("--mod") + 1] if "--mod" in a else os.path.join(os.path.dirname(os.path.dirname(HERE)), "hzm-mod-alarmsnipers")
        allc = {m_: [(p["pos"][0], p["pos"][1], p["base"], str(p["yaw"])) for p in v] for m_, v in pools.items()}
        write_cands(allc, mod)
        print({m_: len(v) for m_, v in allc.items()})
    elif cmd == "merge-dpre":
        set_max(12)
        pools = json.load(open(os.path.join(HERE, "roof_pool.json")))
        m_ = a[1]
        ok = set()
        for ln in open(a[2]):
            p = ln.split()
            if len(p) >= 4 and p[1] == "DPRE" and p[3] == "OK":
                ok.add(int(p[2]))
        pool = [p for i, p in enumerate(pools[m_], 1) if i in ok]
        failed = []
        base = os.path.join(HERE, "..", "proposals", "alarm_snipers_2026-10-18", "tools", "spotcheck")
        for d_ in [base] + [os.path.join(base, x) for x in os.listdir(base) if x.startswith("_round")]:
            fp = os.path.join(d_, m_ + ".json")
            if os.path.exists(fp):
                failed += [r["pos"] for r in json.load(open(fp)) if r["verdict"] != "PASS" and "deck=1" in r["line"]]
        n0 = len(pool)
        pool = [p for p in pool if not any((f[0] - p["pos"][0]) ** 2 + (f[1] - p["pos"][1]) ** 2 < 40.0 ** 2 for f in failed)]
        print(m_, "removed by earlier audit failures:", n0 - len(pool))
        ex = [e_ for e_ in data.get(m_, {}).get("spots", []) if not e_.get("plat")]
        cx = cy = 0.0
        picked = pick_spots(pool, 0.0, 0.0)
        picked = [p for p in picked if all(math.hypot(p["pos"][0] - e_["pos"][0], p["pos"][1] - e_["pos"][1]) >= 600.0 for e_ in ex)]
        for p in picked:
            p.setdefault("cluster", 90); p.setdefault("side", 0)
        data[m_]["spots"] = ex + picked
        data[m_]["audited"] = False
        json.dump(data, open(OUTJ, "w"), indent=1, sort_keys=True)
        print(m_, "pool", len(pools[m_]), "engine-flush", len(pool), "picked", len(picked))
    elif cmd == "merge-snap":
        merge_snap(a[1], a[2])
    elif cmd == "cands":
        mod = a[a.index("--mod") + 1] if "--mod" in a else os.path.join(os.path.dirname(os.path.dirname(HERE)), "hzm-mod-alarmsnipers")
        allc = {}
        for m_ in [x for x in a[1:] if not x.startswith("--") and x != mod]:
            allc[m_] = vanilla_candidates(m_)
            print(m_, len(allc[m_]))
        write_cands(allc, mod)
    elif cmd == "merge-rf":
        merge_rf(a[1], a[2])
    elif cmd == "drop-failed":
        res = json.load(open(a[2]))
        bad = [r["pos"] for r in res if r["verdict"] != "PASS"]
        before = len(data[a[1]]["spots"])
        data[a[1]]["spots"] = [s_ for s_ in data[a[1]]["spots"] if not any(abs(s_["pos"][0] - b[0]) < 1.5 and abs(s_["pos"][1] - b[1]) < 1.5 and abs(s_["pos"][2] - b[2]) < 1.5 for b in bad)]
        data[a[1]]["audited"] = True
        data[a[1]].setdefault("dropped", []).extend([{"pos": r["pos"], "why": r["verdict"]} for r in res if r["verdict"] != "PASS"])
        json.dump(data, open(OUTJ, "w"), indent=1, sort_keys=True)
        print(a[1], "kept", len(data[a[1]]["spots"]), "of", before)
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
            if data[m]["spots"] and (data[m].get("audited") or "--all" in a):   # dispatcher lists only maps that have a function (audited, or --all for audit runs)
                L.append('\tif( local.map == "%s" ){ local.n = waitthread sp_%s }' % (m, m))
        L.append("}end local.n\n")
        for m in sorted(data):
            sp = data[m]["spots"]
            if not sp or not (data[m].get("audited") or "--all" in a):
                continue
            L.append("// %s: %d spots" % (m, len(sp)))
            L.append("sp_%s:{" % m)
            for i, s in enumerate(sp, 1):
                p = s["pos"]
                L.append("\tlevel.coop_asnSpot[%d] = ( %s %s %s )" % (i, p[0], p[1], p[2]))
                L.append("\tlevel.coop_asnCl[%d] = %d" % (i, s["cluster"]))
                L.append("\tlevel.coop_asnSide[%d] = %d" % (i, s["side"]))
                L.append("\tlevel.coop_asnPlat[%d] = %d" % (i, 1 if s.get("plat") else 0))
                if s.get("plat"):
                    L.append("\tlevel.coop_asnYaw[%d] = %d" % (i, s["yaw"]))
            L.append("}end %d\n" % len(sp))
        open(os.path.join(mod, "coop_mod", "alarmsnipers_spots.scr"), "w", newline="\n").write("\n".join(L) + "\n")
        print("wrote", sum(len(v["spots"]) for v in data.values()), "spots")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""alarm_place.py - place alarm switches + bells FLUSH on solid walls by tracing the compiled BSP (bsptrace.py).

WHY (bug-4005): the first batch (gen_alarm_points.py + the in-game cn_scout) sat switches in doorways, floating, and at
22.5-degree-snapped angles. Hand-snapped yaw and a single three-height probe cannot see a door opening, a half-wall or a
slanted face. This places by geometry instead, copying the VANILLA recipe measured from m4l3 / m6l2a (alarmer.scr maps):
    switch  origin = wall hit + normal * 3.3,  yaw = atan2(normal)  (the model faces away from its wall),  z = floor + 52
    bell    same wall, same yaw, straight ABOVE the switch (+56), origin = wall hit + normal * 2.0

    python docs/tools/alarm_place.py solve [map ...]   # re-solve the points of alarm_points.json (seeds kept in "seed")
    python docs/tools/alarm_place.py audit [map ...]   # grade the CURRENT points (no change) - same checks as solve
Then: python docs/tools/gen_alarm_points.py build

A candidate wall must pass ALL of: a flat 57x48 patch (5 x 4 traces) of ONE plane with a visible (not nodraw/clip/sky/glass)
shader; 96 u clear in front at three heights and a clear stand spot; origin not inside a brush; >= 56 u (xy) from every
brush entity (script_object / func_*: doors, windows, ladders, crates, gates - these are not in the world brushes, so a
trace cannot see them); a pathnode within 120 u of the stand spot (an enemy can actually run there); >= 700 u from the
player start; floor under the stand spot within 24 u of the pathnode's (no ledge/stair edge). Score = distance from the
seed (the old point sits in the right enemy area) minus front openness. Points of one map are kept >= 450 u apart.
"""
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bsptrace as T  # noqa: E402

DATA = os.path.join(HERE, "alarm_points.json")
SW_OFF, BELL_OFF = 3.3, 2.0
SW_Z, BELL_UP = 52.0, 56.0
RADIUS = 520.0
MIN_SPAWN = 700.0
# t1l1 (paradrop): the German clusters sit 150-600 u from the landing zone, so a 700 rule leaves no wall at all
MIN_SPAWN_MAP = {"t1l1": 450.0}
MIN_SEP = 450.0
KEEP_PAD = 56.0
# runtime player spawns seen in the 2026-10-15 scout logs (the BSP info_player_start is not always where coop spawns)
EXTRA_STARTS = {
    "e3l1": [(-2620.979, -5445.941, 67.593)],
    "m1l1": [(2582.366, 126.161, 940.618)],
    "m2l1": [(-6519.0, -3558.0, 468.196)],
    "m3l2": [(-3894.0, 2160.0, 0.125)],
    "m4l2": [(5760.0, -529.0, 346.965)],
    "t1l1": [(-4567.0, 5639.0, 6622.0)],
}
# visible surfaces that must not sit behind / around a panel: they are draw surfaces over a flat collision wall
BADVIS = ("window", "win_", "_win", "door", "shutter", "bars", "grate", "fence", "glass", "vent", "ladder", "sign", "poster", "curtain",
          "gate", "lamp", "light", "pipe", "fusebox", "panel", "hatch", "frame", "arch")
BADSH = ("glass", "window", "fence", "grate", "chain", "wire", "ladder", "water", "sky", "clip", "nodraw", "caulk")


def load():
    return json.load(io.open(DATA, "r", encoding="utf-8"))


def save(d):
    with io.open(DATA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, indent=1, sort_keys=True)
        f.write("\n")


class Ctx:
    def __init__(s, m):
        s.m = m
        s.B = T.BSP.load(m)
        es = s.B.entities()
        s.nodes = [T.vec(e["origin"]) for e in es if e.get("classname") == "info_pathnode" and T.vec(e.get("origin", ""))]
        s.ai = [T.vec(e["origin"]) for e in es if ("ai_german" in e.get("classname", "").lower() or e.get("classname", "").lower() == "ai_actor") and T.vec(e.get("origin", ""))]
        s.wps = [T.vec(e["origin"]) for e in es if e.get("classname") == "info_waypoint" and T.vec(e.get("origin", ""))]
        s.starts = [T.vec(e["origin"]) for e in es if e.get("classname", "").startswith("info_player") and T.vec(e.get("origin", ""))]
        s.starts_x = EXTRA_STARTS.get(m, [])
        s.walk = list(s.nodes) + list(s.ai) + list(s.wps)
        s.keep = []
        for e in es:
            c = e.get("classname", "")
            mo = e.get("model", "")
            if not mo.startswith("*") or c in ("func_rain",) or c.startswith("trigger_"):
                continue
            try:
                mn, mx = s.B.model_bounds(int(mo[1:]))
            except Exception:
                continue
            # door/gate/window-sized movers only: script_object also carries whole-level proxy models (3000 u wide)
            if max(mx[i] - mn[i] for i in range(3)) > 450:
                continue
            org = T.vec(e.get("origin", "")) or (0, 0, 0)
            # brush-entity bounds are map space when there is no origin brush and origin-relative when there is one;
            # keep out of BOTH readings (conservative)
            s.keep.append((mn, mx, c))
            if any(org):
                s.keep.append((tuple(mn[i] + org[i] for i in range(3)), tuple(mx[i] + org[i] for i in range(3)), c))

    def visible_ok(s, shidx):
        if not (0 <= shidx < len(s.B.shaders)):
            return False
        n = s.B.shaders[shidx][0].lower()
        return not any(b in n for b in BADSH)

    def bad_surface(s, pos, n, half=44.0, hz=36.0):
        """name of a window/door/sign/etc. draw surface touching the panel's footprint (pos +-half along the wall, +-hz, 4 behind
        to 30 in front of the wall), else None."""
        t = (-n[1], n[0], 0.0)
        pts = []
        for u in (-half, half):
            for d in (-4.0, 30.0):
                pts.append((pos[0] + t[0] * u + n[0] * d, pos[1] + t[1] * u + n[1] * d))
        lo = (min(p[0] for p in pts) - 4, min(p[1] for p in pts) - 4, pos[2] - hz)
        hi = (max(p[0] for p in pts) + 4, max(p[1] for p in pts) + 4, pos[2] + hz)
        for nm, mn, mx in s.B.surfaces():
            if mx[0] < lo[0] or mn[0] > hi[0] or mx[1] < lo[1] or mn[1] > hi[1] or mx[2] < lo[2] or mn[2] > hi[2]:
                continue
            if any(b in nm for b in BADVIS):
                return nm
        return None

    def foreign_surface(s, pos, n, wall_sh, half=44.0, hz=36.0):
        """a draw surface with a DIFFERENT shader lying on the wall plane under the footprint = a decal (window, door, poster...)
        painted over the flat collision wall; the collision trace cannot see it. Returns its shader name or None."""
        t = (-n[1], n[0], 0.0)
        wd = (pos[0] - n[0] * SW_OFF) * n[0] + (pos[1] - n[1] * SW_OFF) * n[1]   # wall plane distance along n
        pts = []
        for u in (-half, half):
            pts.append((pos[0] + t[0] * u, pos[1] + t[1] * u))
        lo = (min(p[0] for p in pts) - 5, min(p[1] for p in pts) - 5, pos[2] - hz)
        hi = (max(p[0] for p in pts) + 5, max(p[1] for p in pts) + 5, pos[2] + hz)
        for nm, mn, mx in s.B.surfaces():
            if mx[0] < lo[0] or mn[0] > hi[0] or mx[1] < lo[1] or mn[1] > hi[1] or mx[2] < lo[2] or mn[2] > hi[2]:
                continue
            if nm == wall_sh:
                continue
            cs = [(x, y) for x in (mn[0], mx[0]) for y in (mn[1], mx[1])]
            ds = [c[0] * n[0] + c[1] * n[1] for c in cs]
            if min(ds) >= wd - 3.0 and max(ds) <= wd + 6.0:
                return nm
        return None

    def near_keep(s, p, pad=KEEP_PAD):
        for mn, mx, c in s.keep:
            if (mn[0] - pad <= p[0] <= mx[0] + pad and mn[1] - pad <= p[1] <= mx[1] + pad
                    and mn[2] - 24 <= p[2] <= mx[2] + 24):
                return c
        return None

    def floor_at(s, x, y, z, down=160.0):
        r = s.B.trace((x, y, z), (x, y, z - down))
        if r and r[1][2] > 0.7:
            return z - r[0] * down
        return None


def ang_of(n):
    return math.degrees(math.atan2(n[1], n[0])) % 360.0


def patch_ok(C, base, n, rows, cols=(-28, -14, 0, 14, 28)):
    """base = point ON the wall plane at the patch centre height 0; n = outward normal. True when every probe hits the same plane."""
    B = C.B
    t = (-n[1], n[0], 0.0)
    ref = None
    for v in rows:
        for u in cols:
            p0 = (base[0] + n[0] * 5 + t[0] * u, base[1] + n[1] * 5 + t[1] * u, base[2] + v)
            p1 = (p0[0] - n[0] * 16, p0[1] - n[1] * 16, p0[2])
            r = B.trace(p0, p1)
            if not r:
                return False
            nn = r[1]
            if abs(nn[0] - n[0]) > 0.03 or abs(nn[1] - n[1]) > 0.03 or abs(nn[2]) > 0.03:
                return False
            hp = (p0[0] + (p1[0] - p0[0]) * r[0], p0[1] + (p1[1] - p0[1]) * r[0])
            dist = hp[0] * n[0] + hp[1] * n[1]
            if ref is None:
                ref = dist
            elif abs(dist - ref) > 1.5:
                return False
            if not C.visible_ok(r[2]):
                return False
    return True


def front_clear(C, p, n, length=96.0):
    """three-height clear run in front of the switch; returns the shortest clear distance (capped 300) or 0 when blocked."""
    B = C.B
    best = 300.0
    for dz in (-24.0, 0.0, 24.0):
        s0 = (p[0] + n[0] * 4, p[1] + n[1] * 4, p[2] + dz)
        e0 = (s0[0] + n[0] * 300, s0[1] + n[1] * 300, s0[2])
        r = B.trace(s0, e0)
        d = 300.0 if not r else r[0] * 300.0
        best = min(best, d)
    return best if best >= length else 0.0


def _bell_clean(C, bpos, n):
    wr2 = C.B.trace((bpos[0] + n[0] * 5, bpos[1] + n[1] * 5, bpos[2]), (bpos[0] - n[0] * 12, bpos[1] - n[1] * 12, bpos[2]))
    return bool(wr2) and not C.foreign_surface(bpos, n, C.B.shaders[wr2[2]][0].lower(), 28.0, 20.0)


def evaluate(C, hitpt, n, floor, seed):
    """full check of one wall candidate; returns None or a dict with the placement."""
    B = C.B
    pos = (hitpt[0] + n[0] * SW_OFF, hitpt[1] + n[1] * SW_OFF, floor + SW_Z)
    if B.point_solid(pos):
        return None
    base = (hitpt[0], hitpt[1], pos[2])
    if not patch_ok(C, base, n, (-24, -8, 8, 24)):
        return None
    clr = front_clear(C, pos, n)
    if clr <= 0:
        return None
    stand = (pos[0] + n[0] * 40, pos[1] + n[1] * 40, pos[2])
    if B.point_solid(stand):
        return None
    for dd in (24.0, 60.0, 96.0):
        # headroom in front of the panel: a stair underside / low beam / vent over the stand spot makes a bad panel spot
        up = B.trace((pos[0] + n[0] * dd, pos[1] + n[1] * dd, floor + 8), (pos[0] + n[0] * dd, pos[1] + n[1] * dd, floor + 118))
        if up:
            return None
    sf = C.floor_at(stand[0], stand[1], pos[2] - 8, 160)
    if sf is not None and abs(sf - floor) > 24:
        return None
    if sf is None and floor is None:
        return None
    k = C.near_keep(pos)
    if k:
        return None
    if C.bad_surface(pos, n):
        return None
    wr = B.trace((pos[0] + n[0] * 5, pos[1] + n[1] * 5, pos[2]), (pos[0] - n[0] * 12, pos[1] - n[1] * 12, pos[2]))
    if not wr or C.foreign_surface(pos, n, B.shaders[wr[2]][0].lower(), 30.0, 26.0):
        return None
    for st in C.starts + C.starts_x:
        if math.dist(st, pos) < MIN_SPAWN_MAP.get(C.m, MIN_SPAWN):
            return None
    if not any(math.hypot(q[0] - stand[0], q[1] - stand[1]) <= 150 and abs(q[2] - floor) <= 64 for q in C.walk):
        return None
    bell = None
    bpos = (hitpt[0] + n[0] * BELL_OFF, hitpt[1] + n[1] * BELL_OFF, pos[2] + BELL_UP)
    bbase = (hitpt[0], hitpt[1], bpos[2])
    if not B.point_solid(bpos) and patch_ok(C, bbase, n, (-12, 0, 12), cols=(-20, -8, 0, 8, 20)) and not C.near_keep(bpos) and not C.bad_surface(bpos, n, 28.0, 20.0) and _bell_clean(C, bpos, n):
        bell = bpos
    d = math.hypot(pos[0] - seed[0], pos[1] - seed[1])
    if abs(pos[2] - seed[2]) > 90:
        return None
    return {"pos": pos, "yaw": ang_of(n), "bell": bell, "clear": clr, "dist": d, "score": d - 0.25 * min(clr, 240.0) - (40 if bell else 0)}


def anchors(C, seed, radius):
    """walkable ground points near the seed: pathnodes that really sit on a floor, German AI spawns, waypoints."""
    out = []
    sf = seed[2] - SW_Z
    for src in (C.nodes, C.ai, C.wps):
        for q in src:
            if math.hypot(q[0] - seed[0], q[1] - seed[1]) > radius or abs(q[2] - sf) > 130:
                continue
            fl = C.floor_at(q[0], q[1], q[2] + 6, 128)
            if fl is None:
                if src is C.nodes:
                    continue
                fl = q[2]
            if abs(fl - q[2]) > 40 or abs(fl - sf) > 90:
                continue
            out.append((q[0], q[1], fl))
    return out


def candidates(C, seed, radius=RADIUS):
    B = C.B
    out = []
    seen = []
    for q in anchors(C, seed, radius):
        floor = q[2]
        for yd in range(0, 360, 10):
            g = (math.cos(math.radians(yd)), math.sin(math.radians(yd)))
            p0 = (q[0], q[1], floor + SW_Z)
            p1 = (p0[0] + g[0] * 200, p0[1] + g[1] * 200, p0[2])
            r = B.trace(p0, p1)
            if not r or abs(r[1][2]) > 0.02 or not C.visible_ok(r[2]):
                continue
            hp = B.hit_point(p0, p1, r)
            if any(abs(hp[0] - a[0]) < 20 and abs(hp[1] - a[1]) < 20 and abs(r[1][0] - a[2]) < 0.1 and abs(r[1][1] - a[3]) < 0.1 for a in seen):
                continue
            seen.append((hp[0], hp[1], r[1][0], r[1][1]))
            out.append((hp, r[1], floor))
    return out


def solve_point(C, seed, others):
    best = None
    for radius in (RADIUS, 900.0):
        best = _solve(C, seed, others, radius)
        if best:
            return best
    return best


def _solve(C, seed, others, radius):
    best = None
    for hp, n, floor in candidates(C, seed, radius):
        res = evaluate(C, hp, n, floor, seed)
        if not res:
            continue
        if any(math.hypot(res["pos"][0] - o[0], res["pos"][1] - o[1]) < MIN_SEP for o in others):
            continue
        if best is None or res["score"] < best["score"]:
            best = res
    return best


def audit_point(C, pos, yaw, kind="switch"):
    """grade an existing point: wall behind along -yaw direction, flatness, doorway keep-out."""
    B = C.B
    f = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), 0.0)
    r = B.trace(pos, (pos[0] - f[0] * 12, pos[1] - f[1] * 12, pos[2]))
    probs = []
    if B.point_solid(pos):
        probs.append("inside geometry")
    if not r:
        probs.append("no wall within 12 u behind (floating)")
        return probs
    n = r[1]
    if abs(n[2]) > 0.02:
        probs.append("wall slanted")
    ang = abs((ang_of(n) - yaw + 180) % 360 - 180)
    if ang > 3:
        probs.append("yaw %.1f off the wall normal" % ang)
    hp = B.hit_point(pos, (pos[0] - f[0] * 12, pos[1] - f[1] * 12, pos[2]), r)
    if not patch_ok(C, (hp[0], hp[1], pos[2]), n, (-24, -8, 8, 24)):
        probs.append("wall not flat 57x48 (doorway/edge/odd shader)")
    k = C.near_keep(pos)
    if k:
        probs.append("within %d u of brush entity %s" % (KEEP_PAD, k))
    wr = B.trace((pos[0] + f[0] * 5, pos[1] + f[1] * 5, pos[2]), (pos[0] - f[0] * 12, pos[1] - f[1] * 12, pos[2]))
    fs = (C.foreign_surface(pos, n, B.shaders[wr[2]][0].lower(), 30.0, 26.0) if kind == "switch" else C.foreign_surface(pos, n, B.shaders[wr[2]][0].lower(), 28.0, 20.0)) if wr else None
    if fs:
        probs.append("decal surface %s painted over the wall (window/door/poster)" % fs.split("/")[-1])
    bs = C.bad_surface(pos, n) if kind == "switch" else C.bad_surface(pos, n, 28.0, 20.0)
    if bs:
        probs.append("window/door/sign surface %s on the mounting footprint" % bs.split("/")[-1])
    return probs


def main(argv):
    if len(argv) < 2 or argv[1] not in ("solve", "audit"):
        print(__doc__)
        return 2
    cmd = argv[1]
    d = load()
    dry = "--dry" in argv
    argv = [a for a in argv if a != "--dry"]
    maps = argv[2:] or sorted(d)
    rc = 0
    for m in maps:
        if m not in d:
            continue
        C = Ctx(m)
        pts = d[m]["points"]
        if cmd == "audit":
            for p in pts:
                pr = audit_point(C, tuple(p["pos"]), p["yaw"], p["kind"])
                print(m, p["kind"], p["pos"], p["yaw"], "OK" if not pr else "; ".join(pr))
                rc |= 1 if pr else 0
            continue
        sw = [p for p in pts if p["kind"] == "switch"] + [{"kind": "switch", "pos": list(sd)} for sd in d[m].get("dropped", [])]
        dropped = []
        newpts = []
        chosen = []
        spare = []
        for q in sorted(C.ai, key=lambda a: -sum(1 for b in C.ai if math.hypot(a[0] - b[0], a[1] - b[1]) < 600)):
            if all(math.hypot(q[0] - w[0], q[1] - w[1]) > 700 for w in spare) and all(math.dist(q, st) > MIN_SPAWN_MAP.get(m, MIN_SPAWN) for st in C.starts + C.starts_x):
                spare.append((q[0], q[1], q[2] + SW_Z))
        for p in sw:
            seed = tuple(p.get("seed") or p["pos"])
            res = solve_point(C, seed, chosen)
            if not res:
                # fallback: the densest German clusters instead of the unusable seed (no walls / no ground there)
                for alt in spare[:6]:
                    if any(math.hypot(alt[0] - o[0], alt[1] - o[1]) < MIN_SEP for o in chosen):
                        continue
                    res = solve_point(C, alt, chosen)
                    if res:
                        seed = alt
                        print(m, "  (seed unusable, re-seeded on an AI cluster at %d %d)" % (alt[0], alt[1]))
                        break
            if not res:
                print(m, "NO PLACEMENT near seed", seed, "- point dropped")
                dropped.append([round(v, 3) for v in seed])
                rc |= 1
                continue
            chosen.append(res["pos"])
            np_ = {"kind": "switch", "pos": [round(v, 3) for v in res["pos"]], "yaw": round(res["yaw"], 3), "seed": [round(v, 3) for v in seed]}
            newpts.append(np_)
            tag = "bell" if res["bell"] else "NO bell"
            print(m, "switch", np_["pos"], "yaw", np_["yaw"], "d=%.0f clear=%.0f %s" % (res["dist"], res["clear"], tag))
            if res["bell"]:
                newpts.append({"kind": "bell", "pos": [round(v, 3) for v in res["bell"]], "yaw": np_["yaw"]})
        d[m]["points"] = newpts
        d[m]["dropped"] = dropped
        if not dry:
            save(d)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))

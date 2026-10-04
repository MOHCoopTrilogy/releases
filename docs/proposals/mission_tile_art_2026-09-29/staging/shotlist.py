"""shotlist.py - build the per-level camera plan for the full tile set from each level's OWN entity lump (read-only).

    python staging/shotlist.py            # writes staging/shotlist.json and prints a per-map summary

For every level: up to 3 SUBJECTS the level itself places (tanks, guns, vehicles, set pieces - never spawned props), each
filmed by a ring of cameras (2 radii x 6 yaws, eye a little above the subject, looking at it), plus the player-start view
(4 yaws at eye height, 4 yaws elevated). JPEG scouting shots (screenshotJPEG); the pick is re-framed offline.
Hand overrides for levels whose signature subject is geometry, not an entity, live in OVERRIDES (authored, per level).
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\bt_loadscreens_2026-09-28\tools")
from ents import ents  # noqa: E402

LEVELS = ["training", "m4l0", "m1l1", "m1l2a", "m1l2b", "m1l3a", "m1l3b", "m1l3c", "m2l1", "m2l2a", "m2l2b", "m2l2c", "m2l3",
          "m3l1a", "m3l1b", "m3l2", "m3l3", "m4l1", "m4l2", "m4l3", "m5l1a", "m5l1b", "m5l2a", "m5l2b", "m5l3",
          "m6l1a", "m6l1b", "m6l1c", "m6l2a", "m6l2b", "m6l3a", "m6l3b", "m6l3c", "m6l3d", "m6l3e",
          "e1l1", "e1l2", "e1l3", "e1l4", "e2l1", "e2l2", "e2l3", "e3l1", "e3l2", "e3l3", "e3l4",
          "t1l1", "t1l2", "t1l3", "t2l1", "t2l2", "t2l3", "t2l4", "t3l1", "t3l2"]

# subject score by model/classname keyword (higher first); anything matching SKIP is ignored
KEYS = [(r"king|tiger", 10), (r"uboat|u-boat|submarine|sub_", 10), (r"lighthouse|beacon", 10), (r"nebelwerfer|nebel", 9),
        (r"flak|88|aagun|aa_gun", 9), (r"panzer|tank|sherman|t34|stug|jagd", 8), (r"halftrack|ab41|armored", 7),
        (r"glider|plane|bomber|stuka|bf109|p47|c47", 7), (r"train|locomotive|flatcar|railcar", 7),
        (r"artillery|cannon|howitzer|k5|gun_", 6), (r"truck|opel|gmc|kubel|jeep|schwimm", 4), (r"boat|ship|rowboat", 4),
        (r"radar|naxos|radio|antenna", 5)]
SKIP = r"info_vehiclepoint|(?<!stat)weapons/|emitter|fx_|_d\.tik|debris|gib|shell|ammo|player|human/|ai_|trigger|light|sound|decal"
OVERRIDES = {
    # the canal the level is named for: the level's own rowboats on the water (y -4644..-4756, water z ~16)
    "e1l3": [("canal", (200, -4500, 16), (500, 900), 110)],
    # the level's own Panzer IV (addon_vehicle_german_snowy-panzeriv, 1738 4867 1744) - round-2 fix of the floating tank
    "t2l1": [("pz4", (1738, 4867, 1744), (420, 650), 80)],
}


def subjects(mp):
    out = []
    for e in ents(mp):
        c = e.get("classname", "").lower()
        m = e.get("model", "").lower()
        if "origin" not in e or m.startswith("*") or re.search(SKIP, c + " " + m):
            continue
        if not (c.startswith(("vehicle", "addon_vehicle", "turret", "script_model", "func_vehicle")) or "vehicles/" in m
                or "statweapons" in m or "turret" in c):
            continue
        sc = max((s for k, s in KEYS if re.search(k, c + " " + m)), default=0)
        if sc == 0:
            continue
        try:
            o = tuple(float(v) for v in e["origin"].split())
        except ValueError:
            continue
        out.append((sc, m or c, o))
    out.sort(key=lambda t: -t[0])
    picked = []
    for sc, name, o in out:
        if all(math.dist(o[:2], p[2][:2]) > 900 for p in picked):
            picked.append((sc, name, o))
        if len(picked) >= 3:
            break
    return picked


OBJ_RE = re.compile(r'add_objectives\s+\S+\s+\S+\s+"([^"]+)"\s*\(?\s*\$(\w+)')
MODMAPS = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps"


def objective_points(mp):
    """The level's objective markers: add_objectives ... "text" $target(.origin) -> that target's origin (BSP)."""
    src = ""
    for p in (os.path.join(MODMAPS, mp + ".scr"),):
        if os.path.exists(p):
            src += open(p, encoding="latin-1").read()
    d = os.path.join(MODMAPS, mp)
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(".scr"):
                src += open(os.path.join(d, fn), encoding="latin-1").read()
    byname = {}
    for e in ents(mp):
        if "targetname" in e and "origin" in e:
            byname.setdefault(e["targetname"].lower(), e["origin"])
    out = []
    for text, tgt in OBJ_RE.findall(src):
        o = byname.get(tgt.lower())
        if not o:
            continue
        o = tuple(float(v) for v in o.split())
        if all(math.dist(o[:2], q[1][:2]) > 700 for q in out):
            out.append((text, o))
    return out[:3]


def scouts(mp, n=4):
    """Outdoor-by-construction scout points (the loadart cands.py recipe): vehicles then designer actor placements,
    farthest-point spread, snapped to the nearest pathnode (walkable height)."""
    E = ents(mp)
    P = [tuple(float(v) for v in e["origin"].split()) for e in E if e.get("classname") == "info_pathnode"]
    C = []
    for e in E:
        if "origin" not in e:
            continue
        mo = e.get("model", "").lower()
        if ("vehicles" in mo and not re.search("plane|stuka|c47|glider", mo)) or e.get("classname", "").startswith("ai_") \
                or "human/" in mo:
            try:
                C.append(tuple(float(v) for v in e["origin"].split()))
            except ValueError:
                pass
    if not C or not P:
        return []
    sel = [C[0]]
    while len(sel) < min(n, len(C)):
        sel.append(max(C, key=lambda c: min(math.dist(c[:2], s[:2]) for s in sel)))
    return [list(min(P, key=lambda q: math.dist(q[:2], c[:2]) + abs(q[2] - c[2]) * 2)) for c in sel]


def starts(mp):
    for cls in ("info_player_start", "info_player_allied", "info_player_deathmatch"):
        for e in ents(mp):
            if e.get("classname", "").lower() == cls and "origin" in e:
                return tuple(float(v) for v in e["origin"].split())
    return None


def plan(mp):
    shots = []
    subs = []
    for name, o, radii, dz in OVERRIDES.get(mp, []):
        subs.append({"name": name, "at": list(o), "radii": list(radii), "n": 6, "eye_dz": dz, "tgt_dz": 40})
    for sc, name, o in subjects(mp):
        if len(subs) >= 2 + len(OVERRIDES.get(mp, [])):
            break
        subs.append({"name": re.sub(r"[^a-z0-9]", "", os.path.basename(name).split(".")[0])[:10] or "subj",
                     "at": list(o), "radii": [450, 800], "n": 6, "eye_dz": 110, "tgt_dz": 50})
    for text, o in objective_points(mp):
        if len(subs) >= 5:
            break
        subs.append({"name": "obj", "why": text, "at": list(o), "radii": [300, 600], "n": 6, "eye_dz": 90, "tgt_dz": 30})
    st = starts(mp)
    return {"subjects": subs, "start": list(st) if st else None, "scouts": scouts(mp)}


def main():
    allp = {}
    for mp in LEVELS:
        p = plan(mp)
        allp[mp] = p
        print("%-8s start=%s scouts=%d subjects=%s" % (mp, "yes" if p["start"] else "NO", len(p["scouts"]),
                                              ", ".join("%s@%d,%d" % (s["name"], s["at"][0], s["at"][1]) for s in p["subjects"]) or "-"))
    json.dump(allp, open(os.path.join(HERE, "shotlist.json"), "w"), indent=1)
    n = sum(len(p["subjects"]) * 12 + (8 if p["start"] else 0) + 4 * len(p["scouts"]) for p in allp.values())
    print("levels", len(allp), "shots", n)


if __name__ == "__main__":
    main()

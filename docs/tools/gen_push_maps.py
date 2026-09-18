#!/usr/bin/env python
"""Generate coop_mod/mp_push_maps.scr - the authored MP Push frontlines for the seven converted
single-player campaign maps (m1l2b, m2l1, m3l3, m4l1, m4l2, m5l1a, m5l1b).

WHY THIS EXISTS
    Those SP bsps carry ZERO multiplayer team spawns (one info_player_start each), so MP Push cannot
    place players on them. The OwN-3m-All "Push to Gain Ground" mod (map conversions by Viper) solved this
    by SCRIPT-SPAWNING ordered team spawn groups; the coordinates were harvested from that mod (UberMod V5,
    docs/tools/push_spawns.json) - the exact frontlines Viper hand-placed. Credit: OwN-3m-All / Viper.

    This emits, per map, a seed thread that spawns all the info_player_allied/axis entities (so the stock
    MP spawn-selection has team spawns to pick from, and its enemy-distance heuristic gives the frontline
    feel for free) and records the ordered ALLIED group centroids (alh -> al9) as the capture chain that
    coop_mod/mp_push.scr drives. No bsp is touched; nothing here runs on a coop map (coop_mpRun-guarded).

    python docs/tools/gen_push_maps.py check   # regenerate in memory + byte-compare (exit 1 = drift)
    python docs/tools/gen_push_maps.py build   # write the file

ISOLATION
    Output is coop_mod/mp_push_maps.scr - an MP file (coop_mod/mp*.scr is in MP_MANIFEST), coop_mpRun-
    guarded, naming only coop_mpPush* level vars (MP-owned) and stock spawn builtins. Angles are normalised
    to [0,360) so no bare-negative scalar assignment appears (only vector literals carry negatives, which
    are valid). ASCII, LF, no BOM.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_spawns.json")
DATAZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "push_zones.json")
OUT = os.path.join(MOD, "coop_mod", "mp_push_maps.scr")

GROUP_ORDER = ["h"] + [str(i) for i in range(2, 10)]  # alh/axh then al2..al9 / ax2..ax9


def norm_ang(a):
    a = int(round(a)) % 360
    if a < 0:
        a += 360
    return a


def fnum(v):
    """A coordinate as a compact int-or-1dp string (no scientific, no trailing noise)."""
    r = round(v, 1)
    if r == int(r):
        return str(int(r))
    return ("%.1f" % r)


def load():
    return json.load(io.open(DATA, encoding="utf-8"))


def group_key(side, n):
    return "a%s%s" % ("l" if side == "a" else "x", n)


def centroid(spawns):
    n = len(spawns)
    cx = sum(s["x"] for s in spawns) / n
    cy = sum(s["y"] for s in spawns) / n
    cz = sum(s["z"] for s in spawns) / n
    return (cx, cy, cz)


def vec(box, lo):
    """min ([:3]) or max ([3:]) corner of an AABB list as a GSC vector literal."""
    a = box[0:3] if lo else box[3:6]
    return "( %s %s %s )" % (fnum(a[0]), fnum(a[1]), fnum(a[2]))


def seed_thread(mapname, rec, zrec):
    spawns = rec["spawns"]
    L = ["seed_%s:" % mapname, "{"]
    # spawn every authored point (stock team spawn entities for MP spawn-selection)
    for s in spawns:
        cls = "info_player_allied" if s["side"] == "a" else "info_player_axis"
        grp = group_key(s["side"], s["grp"][2:] if s["grp"][2:] else "h")
        L.append('\tlocal.e = spawn %s' % cls)
        L.append('\tlocal.e.origin = ( %s %s %s )' % (fnum(s["x"]), fnum(s["y"]), fnum(s["z"])))
        L.append('\tlocal.e.angle = %d' % norm_ang(s["ang"]))
        L.append('\tlocal.e.targetname = "%s"' % grp)
    # ---- battle-line ZONE data (the real OwN-3m-All checkpoint volumes; sptrgN allies, sptrgNx axis) ----
    za = zrec.get("a", {}) if zrec else {}
    zx = zrec.get("x", {}) if zrec else {}
    idxs = sorted(set(int(k) for k in za) | set(int(k) for k in zx))
    n = max(idxs) if idxs else 0
    L.append('\tlevel.coop_mpPushZN = %d' % n)
    for i in range(1, n + 1):
        ba = za.get(str(i)) or za.get(i)
        bx = zx.get(str(i)) or zx.get(i)
        if ba:
            L.append('\tlevel.coop_mpPushZAmin[%d] = %s' % (i, vec(ba, True)))
            L.append('\tlevel.coop_mpPushZAmax[%d] = %s' % (i, vec(ba, False)))
        if bx:
            L.append('\tlevel.coop_mpPushZXmin[%d] = %s' % (i, vec(bx, True)))
            L.append('\tlevel.coop_mpPushZXmax[%d] = %s' % (i, vec(bx, False)))
    if zrec and "end_a" in zrec:
        L.append('\tlevel.coop_mpPushZEndAmin = %s' % vec(zrec["end_a"], True))
        L.append('\tlevel.coop_mpPushZEndAmax = %s' % vec(zrec["end_a"], False))
    if zrec and "end_x" in zrec:
        L.append('\tlevel.coop_mpPushZEndXmin = %s' % vec(zrec["end_x"], True))
        L.append('\tlevel.coop_mpPushZEndXmax = %s' % vec(zrec["end_x"], False))
    if zrec and "ret_a" in zrec:
        r = zrec["ret_a"]
        L.append('\tlevel.coop_mpPushRetA = ( %s %s %s )' % (fnum(r[0]), fnum(r[1]), fnum(r[2])))
    if zrec and "ret_x" in zrec:
        r = zrec["ret_x"]
        L.append('\tlevel.coop_mpPushRetX = ( %s %s %s )' % (fnum(r[0]), fnum(r[1]), fnum(r[2])))
    # AuthoredN signals "this is an authored SP push map" (mp_push.scr re-arms sv_mpForceArena on restart).
    L.append('\tlevel.coop_mpPushAuthoredN = %d' % n)
    L.append('\tprintln( "^~^~^ MPPUSHMAP seeded %s spawns=%d zones=%d" )' % (mapname, len(spawns), n))
    L.append("}end")
    return "\n".join(L)


def render(data, zdata):
    order = ["m1l2b", "m2l1", "m3l3", "m4l1", "m4l2", "m5l1a", "m5l1b"]
    L = [
        "//GENERATED by docs/tools/gen_push_maps.py -- DO NOT HAND-EDIT (regenerate instead).",
        "//Authored MP Push data for the 7 converted SP campaign maps. Coordinates harvested from the",
        "//OwN-3m-All 'King of the Map / Push to Gain Ground' mod (map conversions by Viper); MP-isolated rebuild.",
        "//The bsps carry no MP team spawns, so we script-spawn the ordered team spawn groups (alh/al2..al9,",
        "//axh/ax2..ax9) here, plus the real per-checkpoint battle-line ZONE volumes (sptrgN allies / sptrgNx",
        "//axis), the two end zones and the score-return teleports. coop_mod/mp_push.scr's battle-line mechanic",
        "//consumes these. coop_mpRun-guarded; a compile canary on every MP boot.",
        "alive:{",
        "\tend 1",
        "}end",
        "",
        "//Spawn the authored frontline for the current map (lowercased mapname). Sets level.coop_mpPushAuthored",
        "//[1..N] (ordered capture chain) + coop_mpPushAuthoredN, and returns N (0 = not an authored map).",
        "seed local.map:{",
        "\tif( level.coop_mpRun != 1 ){ end 0 }",
        "\tlevel.coop_mpPushAuthoredN = 0",
        "\tswitch( local.map ){",
    ]
    present = [m for m in order if m in data]
    for m in present:
        L.append('\t\tcase "%s":' % m)
        L.append("\t\t\twaitthread seed_%s" % m)
        L.append("\t\t\tbreak")
    L += [
        "\t}",
        "\tend level.coop_mpPushAuthoredN",
        "}end level.coop_mpPushAuthoredN",
        "",
    ]
    for m in present:
        L.append(seed_thread(m, data[m], zdata.get(m, {})))
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    data = load()
    zdata = json.load(io.open(DATAZ, encoding="utf-8")) if os.path.exists(DATAZ) else {}
    text = render(data, zdata)
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        raise SystemExit("gen_push_maps: output is not ASCII")
    if mode == "build":
        io.open(OUT, "wb").write(text.encode("ascii"))
        print("wrote %s (%d bytes)" % (os.path.relpath(OUT, ROOT), len(text)))
        return 0
    if not os.path.exists(OUT):
        print("MISSING %s - run: python docs/tools/gen_push_maps.py build" % os.path.relpath(OUT, ROOT))
        return 1
    cur = io.open(OUT, "r", encoding="latin-1", newline="").read()
    if cur == text:
        print("EXACT REPRODUCTION (%s)" % os.path.relpath(OUT, ROOT))
        return 0
    print("DRIFT - run: python docs/tools/gen_push_maps.py build")
    return 1


if __name__ == "__main__":
    sys.exit(main())

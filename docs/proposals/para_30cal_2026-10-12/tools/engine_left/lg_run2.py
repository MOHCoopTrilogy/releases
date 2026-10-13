"""lg_run2.py <label> new|old [phases] - round 2 on the engine side of the left .30 cal, one session on m3l2:
  new   the game1 worktree's game.dll + the mod's edited player_legs.st / anims_shared.txt (in the overlay)
  old   the previous build (92944d37, <scratchpad>/built_leftgun/game_92944d37.dll) + the deployed state file: the BEFORE
phases (comma list, default all): mg42,low,rm,kill
  mg42   a retail MG42 (models/statweapons/mg42_gun.tik) on its bipod 60 u up, 300-round belt: the seat line, the heat
         numbers with rounds in the belt, the trigger held on an empty belt (bug-3639), the text; first person + side stills
  low    the paratroopers' .30 cal on a 40 u rest: the seat line, the hull, first person + side stills (idle, firing),
         then off it: the hull he gets back
  rm     the gun is removed while he is on it
  kill   he is killed on it
The side view: a script camera whose angles point across the gun; in third person on a turret the client chases the
player along the camera's angles. One screenshot per step."""
import json, math, os, re, sys, time
import lg_lib as G
R = G.R
LABEL, WHICH = sys.argv[1], sys.argv[2]
PH = sys.argv[3].split(",") if len(sys.argv) > 3 else "mg42,nest,low,rm,kill".split(",")
MAP = "m3l2"
X, Y, Z, YAW = -3608.0, 2303.0, 80.0, 225.0
GX = X + math.cos(math.radians(YAW)) * 130
GY = Y + math.sin(math.radians(YAW)) * 130
OLD = os.path.join(G.SCRATCH, "built_leftgun", "game_92944d37.dll")
RES = {"label": LABEL, "which": WHICH, "phases": PH}
rundir = notes = None


def hold(ms, shot=None, at=None):
    seq = ["+attackprimary"]
    if shot:
        seq += ["wait %d" % at, "screenshotJPEG %s" % shot, "wait %d" % max(1, ms - at)]
    else:
        seq += ["wait %d" % ms]
    seq += ["-attackprimary", "wait 100"]
    R.step(seq, timeout=60 + ms // 1000)


def pst():
    return G.since(G.cmd("pst"), r"LG PST[^\r\n]*")[-1]


def hull():
    return G.since(G.cmd("hull"), r"LG HULL[^\r\n]*")[-1]


def use():
    p = len(R.read_log())
    R.step(["+use", "wait 120", "-use", "wait 900"], timeout=30)
    return G.since(p, r"TURRETSEAT[^\r\n]*") + G.since(p, r"TURRETSTATE[^\r\n]*")


def mount(key):
    G.cmd("behind")
    time.sleep(0.8)
    RES[key + "_hull_before"] = hull()
    s = use()
    time.sleep(0.6)
    RES[key + "_mount"] = s
    RES[key + "_pst"] = pst()
    RES[key + "_hull_on"] = hull()
    G.log(LABEL, key, "mount:", s, "|", RES[key + "_pst"][-110:], "|", RES[key + "_hull_on"])
    if "turret=none" in RES[key + "_pst"]:
        raise RuntimeError("did not mount")


def stills(key, fire=True):
    """first person, then the side view idle (and firing)"""
    R.step(["wait 300", "screenshotJPEG %s_%s_first" % (LABEL, key), "wait 200"], timeout=30)
    G.cmd("arc", n=0)               # the gun follows the camera's angles: hold it on its own line for the side view
    G.cmd("sidecam", yaw=90, pitch=0)
    # pulled back and level with the waist so that the whole man is in the frame; no HUD (session-only settings)
    R.step(["set cg_cameradist 165", "set cg_cameraheight -14", "set cg_camerasideoffset 0", "ui_hud 0",
            "set cg_3rd_person 1", "wait 1800", "screenshotJPEG %s_%s_side" % (LABEL, key), "wait 200"], timeout=30)
    if fire:
        hold(1200, "%s_%s_side_fire" % (LABEL, key), 700)
    G.cmd("sidecam", yaw=-90, pitch=0)
    R.step(["wait 900", "screenshotJPEG %s_%s_side_left" % (LABEL, key), "wait 600", "set cg_3rd_person 0",
            "wait 400"], timeout=30)
    G.cmd("arc", n=45)
    R.step(["ui_hud 1", "wait 200"], timeout=20)


def summarise(rows):
    out = {}
    t0 = next((r["t"] for r in rows if r["heat"] > 0.5), None)
    tc = next((r["t"] for r in rows if r["oh"] == 1), None)
    if t0 is not None and tc is not None:
        a0 = next(r["ammo"] for r in rows if r["t"] >= t0)
        a1 = next(r["ammo"] for r in rows if r["t"] >= tc)
        aft = [r for r in rows if r["t"] >= tc]
        res = next((r["t"] for r in aft if r["ammo"] < a1), None)
        cold = next((r["t"] for r in aft if r["oh"] == 0), None)
        out = {"sec_to_cook": round(tc - t0, 2), "rounds_to_cook": a0 - a1, "rounds_per_sec": round((a0 - a1) / max(0.01, tc - t0), 2),
               "fire_resumed_after": round(res - tc, 2) if res else None, "cold_after": round(cold - tc, 2) if cold else None}
    out["ammo_first"], out["ammo_last"] = rows[0]["ammo"], rows[-1]["ammo"]
    return out


try:
    rundir, notes = G.boot("lg_" + LABEL, MAP, extra=["set coop_feedDebug 1", "set coop_hardcore 0"],
                           game=OLD if WHICH == "old" else None, lowgun=(WHICH == "new"))
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)
    G.log(LABEL, G.since(G.cmd("purge", timeout=60, tag="all"), r"LG purge[^\r\n]*"))
    RES["map_turrets"] = G.since(G.cmd("turrets", timeout=60), r"LG turret [^\r\n]*")
    G.log(LABEL, "the map's own guns:", RES["map_turrets"])
    G.cmd("poll", n=1)
    G.cmd("god", n=1)               # TEST SET-UP: nothing the map does may kill him during the stills
    R.step(["ui_hud 1", "wait 100"], timeout=20)

    if "mg42" in PH:
        p = G.cmd("mg42", x=GX, y=GY, z=Z, yaw=YAW, n=60, tag="belt")
        G.log(LABEL, G.since(p, r"LG gun at[^\r\n]*")[-1])
        time.sleep(1.5)
        mount("mg42")
        p = len(R.read_log())
        hold(7000)
        time.sleep(6.0)
        rows = G.poll(p)
        RES["mg42_heat"] = summarise(rows)
        RES["mg42_heat_trace"] = [(r["t"], r["ammo"], round(r["heat"], 1), r["oh"]) for r in rows][::3]
        G.log(LABEL, "mg42 heat", json.dumps(RES["mg42_heat"]))
        G.cmd("belt", n=3)
        p = len(R.read_log())
        hold(3000, "%s_mg42_empty" % LABEL, 2400)
        rows = G.poll(p)
        t = R.read_log()[p:]
        RES["mg42_empty"] = {"heat_max_trigger_held_on_empty": max(r["heat"] for r in rows), "ammo": rows[-1]["ammo"],
                             "heat_trace": [round(r["heat"], 1) for r in rows][::3],
                             "feed_lines": len(re.findall(r"FEED cat=\d key=mgbelt", t)),
                             "resupply_text_in_log": len(re.findall(r"BELT EMPTY - resupply", t)),
                             "cooked": max(r["oh"] for r in rows)}
        G.log(LABEL, "mg42 empty", json.dumps(RES["mg42_empty"]))
        time.sleep(5.0)
        G.cmd("belt", n=300)
        stills("mg42")
        RES["mg42_off"] = use()
        time.sleep(0.6)
        RES["mg42_hull_after"] = hull()
        G.log(LABEL, "mg42 off:", RES["mg42_off"], "|", RES["mg42_hull_after"])

    if "nest" in PH:
        # one of the MAP'S OWN guns: m3l2 scene7_mg1 (entity 17), 61.9 u over the ground behind it
        G.cmd("purge", timeout=60, tag="all")
        p = G.cmd("take", n=17, tag="none")
        G.log(LABEL, G.since(p, r"LG take[^\r\n]*")[-1])
        mount("nest")
        stills("nest", fire=False)
        RES["nest_off"] = use()
        time.sleep(0.6)
        RES["nest_hull_after"] = hull()
        G.log(LABEL, "nest off:", RES["nest_off"], "|", RES["nest_hull_after"])
        G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
        time.sleep(1.0)

    if any(k in PH for k in ("low", "rm", "kill")):
        p = G.cmd("gun", x=GX, y=GY, z=Z, yaw=YAW, tag="new")
        G.log(LABEL, G.since(p, r"LG gun at[^\r\n]*")[-1])
        G.cmd("left", n=250)
        time.sleep(1.0)
    if "low" in PH:
        mount("low")
        stills("low")
        RES["low_off"] = use()
        time.sleep(0.6)
        RES["low_hull_after"] = hull()
        RES["low_pst_after"] = pst()
        G.log(LABEL, "low off:", RES["low_off"], "|", RES["low_hull_after"])
        # and he can walk away: forward for a second
        a = RES["low_pst_after"]
        R.step(["+back", "wait 800", "-back", "wait 300"], timeout=20)
        RES["low_walk"] = [a[-150:], pst()[-150:]]
        G.log(LABEL, "walked:", RES["low_walk"])
    if "rm" in PH:
        mount("rm")
        p = G.cmd("rmgun")
        time.sleep(1.0)
        RES["rm_exit"] = G.since(p, r"TURRETSEAT[^\r\n]*")
        RES["rm_hull_after"] = hull()
        RES["rm_pst_after"] = pst()
        G.log(LABEL, "gun removed under him:", RES["rm_exit"], "|", RES["rm_hull_after"], "|", RES["rm_pst_after"][-60:])
    if "kill" in PH:
        p = G.cmd("gun", x=GX, y=GY, z=Z, yaw=YAW, tag="new")
        G.cmd("left", n=250)
        time.sleep(1.0)
        mount("kill")
        G.cmd("god", n=0)
        p = G.cmd("pkill")
        time.sleep(1.5)
        RES["kill_exit"] = G.since(p, r"TURRETSEAT[^\r\n]*")
        RES["kill_hull_after"] = hull()
        RES["kill_pst_after"] = pst()
        G.log(LABEL, "killed on it:", RES["kill_exit"], "|", RES["kill_hull_after"], "|", RES["kill_pst_after"][-60:])
    RES["errors"] = G.errors()
    G.log(LABEL, "script / alias errors:", RES["errors"])
except Exception as e:
    import traceback
    RES["exception"] = repr(e)
    G.log(LABEL, "EXCEPTION", traceback.format_exc())
finally:
    if notes is not None:
        notes["result"] = RES
    if rundir:
        json.dump(RES, open(os.path.join(rundir, "result.json"), "w"), indent=1)
    G.end(rundir, notes)
    G.log(LABEL, "ended", rundir)

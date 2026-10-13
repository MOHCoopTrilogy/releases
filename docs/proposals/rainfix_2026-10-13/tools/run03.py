"""run03.py <plan> <sess> <W> <H> [cgame: stats|final|base] - the rain-to-the-ground measurement and evidence runs.
plans:  matrix   suspects one at a time + the fix, yard level view (numbers + 5-still row profile each)
        fps      30 / 60 / 125 / 240 frames a second cap, before / after
        tiers    downpour -> normal rain (coop_wxNow 0), before / after
        views    every evidence view, before / after stills (3 each) + numbers when the cgame prints them
        gif      24 stills before, 24 after, yard level view
Several plans in one session: join with '+', e.g. matrix+fps+tiers."""
import sys, time, os, re, json
import rainlib as L
import rainpix as PX
R = L.R
BUILD = "C:/mohaa-coop-dev/openmohaa-hzm-rainfix/.cmake/code/client/cgame/Release/cgame.dll"
BD = "C:/mohaa-coop-dev/openmohaa-hzm-rainfix/.cmake/built_rainfix/"
DLL = {"stats": BD + "cgame_stats.dll", "final": BD + "cgame_final.dll", "base": BD + "cgame_base.dll"}
plans, sess, W, H = sys.argv[1].split("+"), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
which = sys.argv[5] if len(sys.argv) > 5 else "stats"
OPT = dict(a.split("=", 1) for a in sys.argv[6:])
MAP = OPT.get("map", "m3l2")
THEME = OPT.get("theme", "rain")
PIN = OPT.get("pin", "4")
TLEN = int(OPT.get("len", "260"))
SHADER = OPT.get("shader", "")
HAS_STATS = which == "stats"

BEFORE = ["set coop_rainToGround 0", "set coop_rainFloor 256"]
AFTER = ["set coop_rainToGround 1", "set coop_rainFloor 1024"]
if MAP == "m3l2":
    YARD = (-3608.0, 2303.0, 80.0)
    YAW = 135.0
    VIEWS = [  # name, pos, yaw, pitch, snap to ground
        ("yard_level", YARD, YAW, 0, 1),
        ("yard_down30", YARD, YAW, 30, 1),
        ("yard_up35", YARD, YAW, -35, 1),
        ("tunnel_looking_out", (-2648.0, 1903.0, -191.9), 180, 0, 1),
        ("canal_between_walls", (-4648.0, 1903.0, -191.9), 0, 0, 1),
        ("canal_between_walls_down20", (-4008.0, 1903.0, -191.9), 180, 20, 1),
        ("canal_edge_looking_down", (-4328.0, 2110.0, 60.0), 270, 35, 1),
        ("rooftop_height_300_up_down35", (YARD[0], YARD[1], 300.0), YAW, 35, 0),
    ]
elif MAP == "t1l3":
    # rooms with a way out, found by the rain-indoors work of 2026-10-12 (scratchpad gfx2art/sky.log "GQ indoor")
    YARD = (6189.0, 2713.0, 48.0)
    YAW = 330.0
    ROOMS = [("room1", (6189.0, 2713.0, 48.0), 330), ("room3", (-892.0, 1768.0, 48.0), 180),
             ("room4", (448.0, 2556.0, 48.0), 300), ("room5", (3656.0, 1260.0, 48.0), 90)]
    VIEWS = []
    for nm, pos, yw in ROOMS:
        VIEWS += [(nm + "_looking_out", pos, yw, 0, 0), (nm + "_ceiling", pos, yw, -65, 0),
                  (nm + "_floor", pos, yw, 50, 0)]
else:
    YARD = None
    YAW = float(OPT.get("yaw", "0"))
    VIEWS = None


def other_views():
    return [("spot_level", YARD, YAW, 0, 1), ("spot_down30", YARD, YAW, 30, 1), ("spot_up35", YARD, YAW, -35, 1),
            ("height_300_up_down35", (YARD[0], YARD[1], YARD[2] + 300.0), YAW, 35, 0)]


rundir = notes = None
OUT = {"plans": plans, "W": W, "H": H, "cgame": which, "rows": []}


def measure(tag, lines, nshots=5, secs=4.0, what=""):
    """apply cvars, read the numbers, take nshots stills, return the row"""
    if lines:
        L.sets(*lines)
    time.sleep(1.6)                 # streaks spawned under the old settings are gone (longest life < 1 s for rain)
    row = {"tag": tag, "what": what}
    if HAS_STATS:
        st, cov = L.stats(secs)
        row["stat"], row["cov"] = st, cov
        L.log("%-28s %s" % (tag, L.fmt(st, cov)))
    files = [f for f in L.burst(rundir, tag, nshots) if f]
    if len(files) >= 3:
        row["pix"] = PX.profile(files)
        L.log("%-28s streak pixels %.2f %% of the picture; by tenth of the height, top to bottom: %s"
              % (tag, row["pix"]["total_pct"], " ".join("%.1f" % v for v in row["pix"]["bands_pct"])))
    row["files"] = [os.path.basename(f) for f in files]
    OUT["rows"].append(row)
    L.save(rundir, "results.json", OUT)
    return row


try:
    ov = {"scripts/coop_rain.shader": SHADER} if SHADER else None
    rundir, notes = L.boot(sess, MAP, W, H, DLL[which] if os.path.exists(DLL[which]) else BUILD, "rain_" + which,
                           extra=["set coop_weatherPin %s" % PIN, "set coop_weatherForce %s" % THEME], overlay_files=ov)
    OUT["cgame_md5"] = notes.get("cgame_md5")
    if YARD is None:
        if "at" in OPT:
            YARD = tuple(float(v) for v in OPT["at"].split(","))
        else:
            m = re.findall(r"GQ ready origin=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \)", R.read_log())
            YARD = tuple(float(v) for v in m[-1])
        VIEWS = other_views()
        L.log("spot", YARD)
    if "only" in OPT:
        VIEWS = [v for v in VIEWS if v[0] in OPT["only"].split(",")]
    L.log(L.tp(YARD, YAW, 0, ground=0 if MAP == "t1l3" else 1))
    if HAS_STATS:
        L.log("tier streak length", L.wait_tier(TLEN, 110))
    else:
        time.sleep(50)
    for plan in plans:
        if plan == "matrix":
            L.sets(*BEFORE)
            measure("m_before", BEFORE, what="as deployed")
            measure("m_endgate0", ["set coop_rainEndGate 0"], what="coop_rainEndGate 0")
            measure("m_bytime0", ["set coop_rainEndGate 1", "set coop_rainByTime 0"], what="coop_rainByTime 0")
            measure("m_nearcull0", ["set coop_rainByTime 1", "set coop_rainNearCull 0"], what="coop_rainNearCull 0")
            measure("m_seed0", ["set coop_rainNearCull 36", "set coop_rainSeed 0"], what="coop_rainSeed 0")
            measure("m_seeout0", ["set coop_rainSeed 1", "set coop_rainSeeOut 0"], what="coop_rainSeeOut 0")
            measure("m_toground_only", ["set coop_rainSeeOut 1", "set coop_rainToGround 1"], what="coop_rainToGround 1, floor 256")
            measure("m_floor_only", ["set coop_rainToGround 0", "set coop_rainFloor 1024"], what="coop_rainFloor 1024, to-ground 0")
            measure("m_after", AFTER, what="the fix: both on")
        elif plan == "probe":
            import math
            for d in (0, 60, 100, 140, 180, 220, 260):
                q = (YARD[0] + math.cos(math.radians(YAW)) * d, YARD[1] + math.sin(math.radians(YAW)) * d, YARD[2])
                L.log("probe %d units out:" % d, L.tp(q, YAW, 0, ground=0))
        elif plan == "light":
            for wp, nm in ((1, "light"), (2, "medium")):
                L.cmd("wp", n=wp)
                time.sleep(28)
                for pitch, pn in ((0, "level"), (30, "down30")):
                    L.tp(YARD, YAW, pitch, ground=1)
                    measure("l_%s_%s_before" % (nm, pn), BEFORE, nshots=6, what="%s rain, before" % nm)
                    measure("l_%s_%s_after" % (nm, pn), AFTER, nshots=6, what="%s rain, after" % nm)
        elif plan == "quick":
            measure("q_before", BEFORE, what="as deployed")
            measure("q_after", AFTER, what="the fix")
        elif plan == "fps":
            for fps in (30, 60, 125, 240):
                cap = ["set com_maxfpsUnfocused %d" % fps, "set com_maxfps %d" % fps]
                measure("f%03d_before" % fps, cap + BEFORE, nshots=4, what="%d fps cap, before" % fps)
                measure("f%03d_after" % fps, cap + AFTER, nshots=4, what="%d fps cap, after" % fps)
            L.sets("set com_maxfpsUnfocused 60", "set com_maxfps 60")
        elif plan == "tiers":
            L.tp(YARD, YAW, 0, ground=1)
            L.sets("set coop_wxNow 0")
            time.sleep(55)
            if HAS_STATS:
                st, _ = L.stats(2)
                L.log("tier off: streak length now", st.get("len"), "density", st.get("den"))
            for pitch, pn, dz in ((0, "level", 0), (30, "down30", 0), (35, "height300_down35", 300)):
                L.tp((YARD[0], YARD[1], YARD[2] + dz), YAW, pitch, ground=0 if dz else 1)
                measure("t_normal_%s_before" % pn, BEFORE, what="normal rain (tier off), before")
                measure("t_normal_%s_after" % pn, AFTER, what="normal rain (tier off), after")
            L.sets("set coop_wxNow 1")
            time.sleep(40)
        elif plan == "views":
            for name, pos, yaw, pitch, gnd in VIEWS:
                L.log(name, L.tp(pos, yaw, pitch, ground=gnd))
                measure("v_%s_before" % name, BEFORE, nshots=3, secs=3.0, what=name + ", before")
                measure("v_%s_after" % name, AFTER, nshots=3, secs=3.0, what=name + ", after")
        elif plan == "gif":
            L.tp(YARD, YAW, 8, ground=1)
            L.sets(*BEFORE)
            time.sleep(1.6)
            L.burst(rundir, "g_before", 24)
            L.sets(*AFTER)
            time.sleep(1.6)
            L.burst(rundir, "g_after", 24)
    L.sets(*AFTER)
finally:
    if rundir:
        L.save(rundir, "results.json", OUT)
    L.finish(rundir, notes)
    print("RUNDIR", rundir)

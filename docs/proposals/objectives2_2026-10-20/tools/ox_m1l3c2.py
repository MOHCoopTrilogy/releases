"""ox_m1l3c2.py <label> [stages]  - m1l3c (The Sea Wall) objectives PHASE 2 walk-through on the private harness client (one player).
stages (comma list, default all): depot,repair,log,hold
Run inside a harness_turn.py turn (runbatch.sh). Writes logs/run_<label>.txt, frames into runs/ox_<label>/ and a timing table."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
STAGES = (sys.argv[2] if len(sys.argv) > 2 else "depot,repair,log,hold").split(",")
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
T0 = time.time()
HOLDSECS = os.environ.get("OXHOLD", "")


def log(*a):
    s = "%5.0fs " % (time.time() - T0) + " ".join(str(x) for x in a)
    G.log(LABEL, *a)
    OUT.write(s + "\n")
    OUT.flush()


def tp(x, y, z, yaw=0, pitch=0):
    G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)


def aim(x, y, z):
    G.cmd("aim", x=x, y=y, z=z)


def hold_use(ms):
    R.step(["+use", "wait %d" % ms, "-use", "wait 200"], timeout=40 + ms // 1000)


def wait_objx(pat, timeout):
    return R.wait_log(r"\^~\^~\^ OBJX2? " + pat, timeout, 0)


def panel(name):
    R.step(["pushmenu coop_objectives", "wait 700", "screenshotJPEG %s" % name, "wait 300", "popmenu 0", "wait 300"], timeout=30)


rundir = notes = None
try:
    extra = ["set coop_counterDebug 1", "set coop_objxFailsafe 900"]
    if os.environ.get("OXOBJX0"):
        extra.append("set coop_objx 0")
    if HOLDSECS:
        extra.append("set coop_objxHoldSecs " + HOLDSECS)
    rundir, notes = G.boot("ox_" + LABEL, "m1l3c", extra=extra)
    log("booted; players joined", notes.get("joined"))
    G.cmd("god")
    G.cmd("here")
    if "scoutdepot" in STAGES:
        tp(-5880, -5420, 2, 0, 0)
        wait_objx(r"ACTIVE depot", 25)
        time.sleep(2)
        for nm, (x, y, z, yw, pt) in {"w1": (-5800, -4804, 2, 0, 5), "w2": (-5800, -4532, 2, 0, 5), "w3": (-5800, -4244, 2, 0, 5),
                                      "n1": (-5500, -5100, 2, 90, 5), "s1": (-5500, -4000, 2, 270, 5),
                                      "hi": (-5600, -4900, 190, 90, 25), "hi2": (-5600, -4200, 190, 270, 25)}.items():
            tp(x, y, z, yw, pt)
            time.sleep(1.2)
            G.still("scout_" + nm)
    if "perfview" in STAGES:
        tp(-700, -1700, 314, 0, 0)
        wait_objx(r"ACTIVE repair", 30)
        time.sleep(4)
        for nm, (x, y, z) in {"c2": (-100, -150, 0), "c3": (-60, 150, 0), "c4": (-200, 120, 30), "c5": (-190, -130, 0)}.items():
            G.cmd("pfcam", x=x, y=y, z=z, k=2)
            time.sleep(0.8)
            G.frames("pc_" + nm, 4, 400)
        for nm, (x, y, yw) in {} .items() if False else {"S": (120, -2400, 90), "N": (120, -2180, 270), "W": (0, -2290, 0), "SW": (30, -2370, 45), "NW": (30, -2210, 315)}.items():
            tp(x, y, 326, yw, 8)
            time.sleep(0.8)
            G.frames("pv_" + nm, 5, 350)
    if "depot" in STAGES:
        log("-- the lift base: the depot objective starts when the squad comes within 520 of it")
        tp(-5880, -5420, 2, 0, 0)
        ok = wait_objx(r"ACTIVE depot", 25)
        log("ACTIVE depot seen:", bool(ok))
        time.sleep(2)
        G.frames("depot_start", 6, 300)
        panel("ox_panel_depot")
        log("-- the charges: stand beside the crate, hold USE")
        tp(-5600, -5320, 2, 180, 0)
        aim(-5672, -5320, -4)
        G.frames("kit_view", 4, 300)
        hold_use(1900)
        ok = wait_objx(r"KIT taken", 10)
        log("KIT taken seen:", bool(ok))
        G.frames("kit_taken", 3, 300)
        for n, (tx, ty) in enumerate(((-5564, -4804), (-5444, -4532), (-5572, -4244))):
            log("-- plant on target", n + 1)
            tp(tx + 170, ty, 2, 180, 0)
            aim(tx, ty, 50)
            G.frames("plant%d_view" % (n + 1), 3, 250)
            R.step(["+use", "wait 300"], timeout=20)
            for k in range(6):
                R.step(["screenshotJPEG plant%d_hold_%04d" % (n + 1, k), "wait 450"], timeout=20)
            R.step(["-use", "wait 300"], timeout=20)
            ok = wait_objx(r"PLANT %d/3" % (n + 1), 6)
            log("PLANT", n + 1, "seen:", bool(ok))
            G.frames("plant%d_done" % (n + 1), 2, 250)
        log("-- clear of the blast: the chain (12 s fuse), watched from the south end of the aisle")
        tp(-5436, -5004, 2, 90, 6)
        G.frames("chain", 40, 450)
        ok = wait_objx(r"DONE depot", 20)
        log("DONE depot seen:", bool(ok))
        G.frames("chain_after", 6, 350)
        panel("ox_panel_depot_done")
    if "repair" in STAGES:
        log("-- the generator yard: the engineer repair starts when the squad comes within 700")
        tp(-60, -2290, 326, 0, 0)
        ok = wait_objx(r"ACTIVE repair", 30)
        log("ACTIVE repair seen:", bool(ok))
        time.sleep(2)
        panel("ox_panel_repair")
        R.step(["set cg_drawviewmodel 0", "wait 100"], timeout=20)
        for nm, (x, y, z) in {"c2": (20, -100, 0), "c3": (20, 100, 0), "c5": (-90, -50, 20)}.items():
            G.cmd("pfcam", x=x, y=y, z=z, k=2)
            time.sleep(0.6)
            G.frames("pc_" + nm, 10, 220)
        R.step(["set cg_drawviewmodel 1", "wait 100"], timeout=20)
        tp(200, -2250, 326, 180, 0)
        for k in range(40):
            if R.wait_log(r"OBJX DONE repair", 0.1, 0):
                break
            G.frames("repair_%02d" % k, 2, 400)
            R.step(["+attackprimary", "wait 500", "-attackprimary", "wait 100"], timeout=20)
            time.sleep(4)
        ok = R.wait_log(r"\^~\^~\^ OBJX DONE repair", 30, 0)
        log("DONE repair seen:", bool(ok))
        R.step(["set cg_drawviewmodel 0", "wait 100"], timeout=20)
        G.cmd("pfcam", x=20, y=-100, z=0, k=2)
        G.frames("repair_done", 20, 250)
        R.step(["set cg_drawviewmodel 1", "wait 100"], timeout=20)
    if "pfdie" in STAGES:
        log("-- the engineer is killed mid-job: a replacement after 12 s, the clock waits")
        tp(-700, -1700, 314, 0, 0)
        wait_objx(r"ACTIVE repair", 30)
        time.sleep(15)
        G.cmd("pfkill", k=2)
        ok = R.wait_log(r"OBJX2? PERF performer died", 10, 0)
        log("performer death seen:", bool(ok))
        ok = R.wait_log(r"OBJX PERF repair performer #2", 30, 0)
        log("replacement performer seen:", bool(ok))
        G.cmd("pfcam", x=-140, y=0, z=0, k=2)
        G.frames("pfdie_after", 6, 400)
    if "truckcheck" in STAGES:
        tp(-731, -2400, 330, 90, 0)
        time.sleep(45)
        G.cmd("nearents")
    if "quickend" in STAGES:
        log("-- the exit gate: the end is touched with objectives open -> refused; then all done -> the mission ends")
        G.cmd("radios4")
        G.cmd("endnow")
        ok = R.wait_log(r"OBJX GATE closed", 15, 0)
        log("GATE closed with objectives open:", bool(ok))
        time.sleep(10)
        still_here = not R.wait_log(r"==-----briefing", 0.1, 0)
        log("mission still running behind the closed gate:", still_here)
        G.cmd("objxall")
        ok = R.wait_log(r"OBJX GATE open", 30, 0)
        log("GATE open once all are done:", bool(ok))
        reached = bool(R.wait_log(r"==-----briefing", 90, 0))
        log("mission-complete chain reached the next briefing:", reached)
    if "animtest" in STAGES:
        tp(-700, -1700, 314, 0, 0)
        wait_objx(r"ACTIVE repair", 30)
        time.sleep(8)
        R.step(["set cg_drawviewmodel 0", "wait 100"], timeout=20)
        for nm in ("unarmed_stand_alert", "unarmed_stand_bored_a01", "relax01", "watching01", "NOIDLE0", "ENABLE"):
            G.cmd("pfanim", s=nm, k=2)
            G.cmd("pfcam", x=-60, y=-140, z=0, k=2)
            time.sleep(3)
            G.still("anim_" + nm)
        R.step(["set cg_drawviewmodel 1", "wait 100"], timeout=20)
    if "truckwait" in STAGES:
        G.cmd("radios4")
        tp(300, -1800, 1118, 160, 0)
        aim(264, -1819, 1125)
        R.step(["+use", "wait 350", "-use", "wait 200"], timeout=30)
        tp(-731, -2400, 330, 90, 0)
        time.sleep(3)
        tp(-900, -2300, 330, 90, 0)
        for k in range(18):
            G.cmd("endinfo")
            time.sleep(9)
        log("DBG arrived:", bool(R.wait_log(r"DBG truck arrived", 0.1, 0)))
    if "arrival" in STAGES:
        log("-- Grillo's truck arrival with every objective prop standing (depot wrecks not needed: they are far away)")
        G.cmd("radios4")
        G.cmd("force", k=1)
        G.cmd("force", k=2)
        time.sleep(6)
        G.cmd("props")
        tp(300, -1800, 1118, 160, 0)
        aim(264, -1819, 1125)
        R.step(["+use", "wait 350", "-use", "wait 200"], timeout=30)
        tp(-731, -2400, 330, 90, 0)
        time.sleep(3)
        # vantage over the landing: the truck's last 100 u and its stop
        tp(-60, -1980, 322, 135, 4)
        caught = False
        for k in range(60):
            p0 = G.cmd("endinfo")
            v = G.since(p0, r"truckDist=(\S+)")
            if v and float(v[-1]) < 900 and not caught:
                caught = True
                G.frames("arrive", 40, 450)
            if caught:
                break
            time.sleep(3)
        time.sleep(4)
        G.frames("arrive_after", 4, 400)
        G.cmd("endinfo")
        log("DBG arrived:", bool(R.wait_log(r"DBG truck arrived", 20, 0)))
    if "radios" in STAGES:
        log("-- vanilla objective 1: the four comms sets")
        G.cmd("radios4")
        time.sleep(6)
    if "log" in STAGES:
        log("-- lighthouse base: obj2trig starts the signal-log objective (after the engineer)")
        tp(208, -1944, 330, 90, 0)
        ok = wait_objx(r"ACTIVE log", 30)
        log("ACTIVE log seen:", bool(ok))
        time.sleep(1.5)
        tp(300, -1800, 1118, 301, 20)
        aim(330, -1850, 1135)
        G.frames("log_view", 4, 300)
        tp(308, -1828, 1118, 315, 20)
        aim(330, -1850, 1146)
        R.step(["+use", "wait 350", "-use", "wait 200"], timeout=30)
        ok = wait_objx(r"DONE log", 12)
        log("DONE log seen:", bool(ok))
    if "lever" in STAGES:
        log("-- the lever: lights the beacon, starts the hold")
        tp(300, -1800, 1118, 160, 0)
        aim(264, -1819, 1125)
        R.step(["+use", "wait 350", "-use", "wait 200"], timeout=30)
        ok = wait_objx(r"ACTIVE hold", 20)
        log("ACTIVE hold seen:", bool(ok))
    if "hold" in STAGES:
        log("-- the truck trigger first (so the truck arrives during the hold), then the landing")
        tp(-731, -2400, 330, 90, 0)
        time.sleep(3)
        tp(-272, -1600, 330, 228, 0)
        for k in range(60):
            G.frames("hold_%02d" % k, 3, 350)
            R.step(["+attackprimary", "wait 700", "-attackprimary", "wait 100"], timeout=20)
            if k % 4 == 0:
                G.cmd("tp", x=-731, y=-2400, z=330, yaw=90, pitch=0)
                time.sleep(1.5)
                G.cmd("tp", x=-272, y=-1600, z=330, yaw=228, pitch=0)
            if R.wait_log(r"OBJX GATE open|OBJX HOLD clock 0:00", 0.1, 0):
                break
        ok = R.wait_log(r"OBJX HOLD clock 0:00", 40, 0)
        log("hold clock finished:", bool(ok))
        for z in (330, 370, 410, 330, 370, 410):
            if R.wait_log(r"OBJX GATE open|COUNTER skip m1l3c", 0.1, 0):
                break
            G.cmd("tp", x=-731, y=-2400, z=330, yaw=90, pitch=0)
            time.sleep(1.5)
            G.cmd("tp", x=-272, y=-1600, z=z, yaw=228, pitch=0)
            time.sleep(3)
        ok = R.wait_log(r"\^~\^~\^ OBJX ALL DONE", 40, 0)
        log("ALL DONE seen:", bool(ok))
    if "end" in STAGES:
        log("-- the way out: the truck, then the end trigger")
        reached = False
        G.cmd("killgerman")
        for k in range(70):
            if k % 5 == 4:
                G.cmd("killgerman")
            if R.wait_log(r"COUNTER skip m1l3c|COUNTER start|==-----briefing", 0.1, 0):
                reached = True
                break
            G.cmd("endinfo")
            G.cmd("tp", x=-731, y=-2400, z=330, yaw=90, pitch=0)
            time.sleep(2)
            G.cmd("tp", x=-272, y=-1600, z=(330, 370, 410)[k % 3], yaw=228, pitch=0)
            time.sleep(4)
        log("mission-complete chain reached the counter gate:", reached)
        G.frames("end", 6, 400)
    ox = G.objx_lines()
    log("---- OBJX log ----")
    for l in ox:
        if "tick" in l:
            continue
        log(l[:240])
    for l in re.findall(r"\^~\^~\^ (OBJX2 [^\r\n]*)", R.read_log()):
        log(l[:240])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

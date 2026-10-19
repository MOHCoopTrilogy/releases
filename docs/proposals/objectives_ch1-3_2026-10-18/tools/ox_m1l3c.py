"""ox_m1l3c.py <label> [stages]  - m1l3c (The Sea Wall) objectives playthrough on the private harness client (one player).
stages (comma list, default all): spawn,radios,intel,lever,hold,gate
Run inside a harness_turn.py turn. Writes logs/run_<label>.txt, frames into runs/<label>/ and a timing table."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
STAGES = (sys.argv[2] if len(sys.argv) > 2 else "spawn,radios,intel,lever,hold").split(",")
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
T0 = time.time()


def log(*a):
    s = "%5.0fs " % (time.time() - T0) + " ".join(str(x) for x in a)
    G.log(LABEL, *a)
    OUT.write(s + "\n")
    OUT.flush()


def tp(x, y, z, yaw=0, pitch=0):
    G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)


def aim(x, y, z):
    G.cmd("aim", x=x, y=y, z=z)


def use(ms=350):
    R.step(["+use", "wait %d" % ms, "-use", "wait 200"], timeout=30)


def wait_objx(pat, timeout):
    return R.wait_log(r"\^~\^~\^ OBJX " + pat, timeout, 0)


def panel(name):
    R.step(["pushmenu coop_objectives", "wait 700", "screenshotJPEG %s" % name, "wait 300", "popmenu 0", "wait 300"], timeout=30)


def state():
    p0 = G.cmd("state")
    for l in G.since(p0, r"\^~\^~\^ (OX STATE[^\r\n]*)"):
        log("  ", l)


rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + LABEL, "m1l3c", extra=["set coop_counterDebug 1", "set coop_objxFailsafe 600", "set coop_objxHoldSecs 140"])
    log("booted; players joined", notes.get("joined"))
    G.cmd("god")
    G.cmd("here")
    if "spawn" in STAGES:
        # a slow turn so the GIF shows the spawn area
        G.frames("spawn", 16, 250, pre=["+left"])
        R.step(["-left", "wait 100"], timeout=20)
        G.cmd("state")
    if "radios" in STAGES:
        log("-- vanilla objective 1: the four comms sets")
        G.cmd("radios4")
        time.sleep(8)
        G.frames("radios", 6, 400)
    if "intel" in STAGES:
        log("-- lighthouse base: obj2trig starts the signal-log objective")
        tp(208, -1944, 330, 90, 0)
        ok = wait_objx(r"ACTIVE log", 25)
        log("ACTIVE log seen:", bool(ok))
        time.sleep(1.5)
        G.frames("intel_active", 8, 250)
        panel("ox_panel_intel")
        log("-- up to the lever platform; look at the log from a few steps away")
        tp(300, -1800, 1118, 301, 20)
        aim(330, -1850, 1135)
        G.frames("intel_view", 6, 300)
        G.still("ox_intel_still")
        tp(308, -1828, 1118, 315, 20)
        aim(330, -1850, 1146)
        use()
        ok = wait_objx(r"DONE log", 12)
        log("DONE log seen:", bool(ok))
        G.frames("intel_done", 8, 250)
        panel("ox_panel_intel_done")
    if "lever" in STAGES:
        log("-- the lever: lights the beacon, starts the hold")
        tp(300, -1800, 1118, 160, 0)
        aim(264, -1819, 1125)
        G.frames("lever_view", 4, 300)
        use()
        ok = wait_objx(r"ACTIVE hold", 20)
        log("ACTIVE hold seen:", bool(ok))
        G.frames("lever_done", 8, 250)
        panel("ox_panel_hold")
    if "hold" in STAGES:
        log("-- the truck trigger first (so the truck arrives during the hold), then the landing")
        tp(-731, -2400, 330, 90, 0)
        time.sleep(3)
        tp(-272, -1600, 330, 228, 0)       # in the zone AND on the exit trigger, facing the south-west approach
        for k in range(60):
            G.frames("hold_%02d" % k, 5, 350)
            R.step(["+attackprimary", "wait 700", "-attackprimary", "wait 100"], timeout=20)
            if k % 4 == 0:
                G.cmd("enemies")
                G.cmd("endinfo")
                # step out of the exit box and back in, so a trigger that became triggerable meanwhile sees a fresh touch
                G.cmd("tp", x=-731, y=-2400, z=330, yaw=90, pitch=0)
                time.sleep(1.5)
                G.cmd("tp", x=-272, y=-1600, z=330, yaw=228, pitch=0)
            if R.wait_log(r"OBJX GATE closed", 0.1, 0) and k % 5 == 0:
                log("gate closed seen at loop", k)
            if k == 3:
                panel("ox_panel_hold_mid")
            if R.wait_log(r"OBJX GATE open|OBJX HOLD clock 0:00", 0.1, 0):
                break
        ok = R.wait_log(r"OBJX HOLD clock 0:00", 30, 0)
        log("hold clock finished:", bool(ok))
        # if the exit never fired during the hold, touch it now at a few heights so the chain to mission complete is still shown
        for z in (330, 370, 410, 330, 370, 410):
            if R.wait_log(r"OBJX GATE open|COUNTER skip m1l3c", 0.1, 0):
                break
            G.cmd("endinfo")
            G.cmd("tp", x=-731, y=-2400, z=330, yaw=90, pitch=0)
            time.sleep(1.5)
            G.cmd("tp", x=-272, y=-1600, z=z, yaw=228, pitch=0)
            time.sleep(3)
        ok = R.wait_log(r"\^~\^~\^ OBJX GATE open", 40, 0)
        log("GATE open seen:", bool(ok))
        G.frames("gate_end", 10, 300)
        ok = R.wait_log(r"COUNTER skip m1l3c", 40, 0)
        log("mission-complete chain reached the counter gate:", bool(ok))
        time.sleep(8)
    # timing table from the log
    ox = G.objx_lines()
    log("---- OBJX log ----")
    for l in ox:
        if "tick" in l:
            continue
        log(l[:230])
    for pat in ("COUNTER skip", "GATE", "DONE", "ACTIVE"):
        pass
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

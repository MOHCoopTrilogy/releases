"""ox_escort.py <label> - the shared ESCORT mechanic, on m1l3c's landing strip (north-south land band x -600..-100). A synthetic
objective is injected by the driver (mkescort); one player frees the prisoner (use) and walks him 650 units to the marker."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
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


rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + LABEL, "m1l3c", extra=["set coop_counterDebug 1"])
    log("booted; players joined", notes.get("joined"))
    G.cmd("god")
    tp(-420, -2000, 312, 90, 0)
    time.sleep(2)
    G.cmd("mkescort", yaw=90)
    ok = R.wait_log(r"\^~\^~\^ OBJX ACTIVE esc", 15, 0)
    log("ACTIVE esc:", bool(ok))
    time.sleep(2)
    G.frames("esc_view", 8, 250)
    # face him and free him
    tp(-420, -1895, 312, 90, 0)
    G.cmd("aim", x=-420, y=-1850, z=345)
    G.frames("esc_free", 4, 250)
    R.step(["+use", "wait 350", "-use", "wait 300"], timeout=20)
    ok = R.wait_log(r"\^~\^~\^ OBJX ESCORT freed", 10, 0)
    log("freed:", bool(ok))
    G.frames("esc_freed", 8, 250)
    for y in (-1840, -1770, -1700, -1630, -1560, -1490, -1420, -1380):
        tp(-420, y, 312, 90, 0)
        G.frames("esc_walk_%d" % (-y), 5, 500)
        G.cmd("escort")
    ok = R.wait_log(r"\^~\^~\^ OBJX DONE esc", 40, 0)
    log("DONE esc:", bool(ok))
    G.frames("esc_done", 8, 250)
    R.step(["pushmenu coop_objectives", "wait 700", "screenshotJPEG ox_panel_esc", "wait 300", "popmenu 0", "wait 300"], timeout=30)
    ox = G.objx_lines()
    log("---- OBJX log ----")
    for l in ox:
        if "tick" in l:
            continue
        log(l[:230])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

"""sl_run.py <label> <map> - searchlight proof: undetected pass (sweep), detected pass (hunt + MG), allied-AI pass, GIF frames."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
def lights(tag):
    p0 = G.cmd("lights")
    for l in G.since(p0, r"\^~\^~\^ SL light=[^\r\n]*"):
        log("  [%s] %s" % (tag, l[10:230]))
def extra_lines(p0):
    for l in G.since(p0, r"\^~\^~\^ SPOTLIGHT[^\r\n]*|::spotowner[^\r\n]*|\^~\^~\^ SL (?!light)[^\r\n]*"):
        log("   ", l[:200])
try:
    rundir, notes = G.boot("sl_" + LABEL, MAP, extra=["set coop_alarm 0"])
    G.cmd("lights")
    # ---- undetected pass: player in the light's sight, no alarm, notarget -> sweep keeps running
    p0 = G.cmd("tpl", n=int(os.environ.get("SLN", "1")))
    G.since(p0, r"SL tpl")
    log("== UNDETECTED PASS (alarm 0)")
    for k in range(4):
        time.sleep(3); lights("undet")
    extra_lines(p0)
    # ---- detected pass
    log("== DETECTED PASS (alarm live)")
    p1 = G.cmd("det1")
    G.cmd("tpl", n=int(os.environ.get("SLN", "1")))
    G.frames(LABEL + "_det", 60, ms=120)
    for k in range(3):
        lights("det"); time.sleep(2)
    extra_lines(p1)
    G.still(LABEL + "_det_end")
    # ---- calm: release
    log("== CALM (alarm off, expect return to sweep after ~12s)")
    p2 = G.cmd("det0")
    for k in range(6):
        time.sleep(4); lights("calm")
    extra_lines(p2)
    # ---- allied AI pass: player away, ally in sight, alarm live
    log("== ALLIED AI PASS")
    p3 = G.cmd("tpfar")
    G.cmd("det1")
    G.cmd("ally", n=int(os.environ.get("SLN", "1")))
    time.sleep(2)
    lights("ally")
    time.sleep(3); lights("ally")
    extra_lines(p3)
    # ---- scene actor protection
    log("== SCENE-ACTOR PASS (flagged ally must not be hunted)")
    p4 = G.cmd("scene")
    G.cmd("tpfar")
    time.sleep(8); lights("scene")
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

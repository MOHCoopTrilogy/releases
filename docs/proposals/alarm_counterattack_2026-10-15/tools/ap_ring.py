"""ap_ring.py <label> <map> - short proof of the ring rule: inside the zone (after 8 s) the ring is hidden; outside it is shown, clock paused."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aplib as A
G = A.G; R = A.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("ring_" + LABEL, MAP, extra=["set coop_counter 1", "set coop_counterDebug 1", "set coop_counterForce 1", "set ui_hud 1",
        "set coop_counterSecs 90", "set coop_counterWaveGap 30", "set coop_counterGrace 6", "set coop_counterLoseTime 60", "set coop_counterCap 4", "set coop_alarm 1", "set coop_dbno 0"])
    p0 = len(R.read_log())
    time.sleep(3)
    G.cmd("stay", timeout=60)
    time.sleep(1)
    G.cmd("mc", timeout=60, nl="m9x")
    t = time.time()
    while time.time() - t < 40 and "COUNTER zone src" not in R.read_log()[p0:]:
        time.sleep(1)
    time.sleep(11)
    G.frames(LABEL + "_ginside", 22, 250)
    log("--- LEAVE")
    G.cmd("leave", timeout=60)
    time.sleep(1)
    G.frames(LABEL + "_gout", 26, 250)
    G.cmd("enter", timeout=60)
    time.sleep(2)
    for l in re.findall(r"\^~\^~\^ (?:COUNTER|AP (?:LEAVE|ENTER))[^\r\n]*", R.read_log()[p0:]):
        log("   ", l[:230])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

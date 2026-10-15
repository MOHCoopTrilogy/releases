"""cn_run.py <label> <map> [key=val ...] - boot the map, force a mission completion, show the counter-attack waves + the mission ending.
cvars: pass as `set coop_x y` via CNSET env (semicolon separated)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
SECS = int(os.environ.get("CNSECS", "40"))
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
extra = ["set coop_counter 1", "set coop_counterDebug 1", "set coop_counterSecs %d" % SECS, "set coop_counterWaveGap 8",
         "set coop_xpSummaryTime 3", "set coop_aiScaleTest 1"] + [x for x in os.environ.get("CNSET", "").split(";") if x]
try:
    rundir, notes = G.boot("cn_" + LABEL, MAP, extra=extra)
    for g in range(1):
        G.cmd("gate"); G.cmd("state"); G.cmd("sizes")
    p0 = len(R.read_log())
    G.cmd("mc", timeout=30)
    t0 = time.time()
    while time.time() - t0 < SECS + 15 + 40:
        time.sleep(10)
        try:
            G.cmd("state")
        except RuntimeError:
            log("   (driver gone: the map transitioned)")
            break
        t = R.read_log()[p0:]
        if re.search(r"COUNTER end", t) or re.search(r"COUNTER skip", t):
            break
    time.sleep(8)
    G.still(LABEL + "_after")
    t = R.read_log()[p0:]
    for l in re.findall(r"\^~\^~\^ (?:COUNTER[^\r\n]*|CN [^\r\n]*)", t):
        log("   ", l[:230])
    for l in re.findall(r"[^\r\n]*(?:bsptransition|Loading map|loading maps)[^\r\n]*", t)[:4]:
        log("   TRANS", l[:200])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

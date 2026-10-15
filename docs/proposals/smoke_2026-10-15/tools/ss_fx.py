"""ss_fx.py <label> <map> - the effect alone: scout open ground, spawn a wall 700u ahead, shoot a frame sequence (1 per SSWAIT ms)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smokelib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
NFR = int(os.environ.get("SSFRAMES", "30"))
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
try:
    rundir, notes = G.boot("ss_" + LABEL, MAP, extra=["set g_ai 1", "set coop_aiScaleTest 1"])
    G.cmd("scout", timeout=60)
    G.cmd("purge", timeout=90)
    time.sleep(2)
    p0 = len(R.read_log())
    G.still(LABEL + "_00_before")
    G.cmd("wall", timeout=60)
    G.frames(LABEL + "_f", NFR, ms=int(os.environ.get("SSWAIT", "1000")))
    t = R.read_log()[p0:]
    for l in re.findall(r"\^~\^~\^ (?:SS [^\r\n]*|SMOKE [^\r\n]*)", t):
        log("   ", l[:200])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

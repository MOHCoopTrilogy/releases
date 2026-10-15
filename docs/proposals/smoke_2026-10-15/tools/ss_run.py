"""ss_run.py <label> <map> - elite squad at the far end of the longest clear run; the player watches the screen go up and the
squad advance through it. Stills + a frame sequence; the monitor lines show hold / AI cansee per second."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smokelib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
NFR = int(os.environ.get("SSFRAMES", "50"))
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
try:
    rundir, notes = G.boot("ss_" + LABEL, MAP, extra=["set g_ai 1", "set coop_aiScaleTest 1", "set coop_smokeDebug 1"] + [x for x in os.environ.get("SSSET", "").split(";") if x])
    if os.environ.get("SSSPOT", "") != "none":
        X, Y, Z, YAW = [float(v) for v in os.environ.get("SSSPOT", "-3608 2303 80 225").split()]
        G.cmd("tp", x=X, y=Y, z=Z, yaw=YAW)
        time.sleep(3)
    else:
        G.cmd("god")
        G.cmd("here")
    if os.environ.get("SSCAND"):
        G.cmd("pairs", timeout=90)
        G.cmd("usepair", n=int(os.environ["SSCAND"]), timeout=30)
        time.sleep(1)
        G.cmd("purge", timeout=90)
    elif os.environ.get("SSPAIR", "1") == "1":
        G.cmd("pair", timeout=90)
        G.cmd("purge", timeout=90)
    else:
        G.cmd("purge", timeout=90)
        G.cmd("probe", timeout=90)
    p0 = len(R.read_log())
    G.still(LABEL + "_00_before")
    G.cmd("squad", timeout=60)
    G.cmd("camon")
    G.frames(LABEL + "_f", NFR, ms=int(os.environ.get("SSWAIT", "45")))
    G.cmd("camoff"); G.cmd("monoff")
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

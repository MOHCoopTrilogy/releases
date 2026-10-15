"""ss_fxrun.py <label> <map> - controlled concealment proof: a held elite squad 1100u down level open ground, the AI visibility counted
per second, then a 3-canister wall 600u ahead; frames from the player's view. SSCAND picks the m3l2-style candidate spot."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smokelib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
NPRE = int(os.environ.get("SSPRE", "6"))
NFR = int(os.environ.get("SSFRAMES", "40"))
WAIT = int(os.environ.get("SSWAIT", "1000"))
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
try:
    rundir, notes = G.boot("ss_" + LABEL, MAP, extra=["set g_ai 1", "set coop_aiScaleTest 1"] + [x for x in os.environ.get("SSSET", "").split(";") if x])
    G.cmd("god")
    if os.environ.get("SSCAND"):
        G.cmd("pairs", timeout=90)
        G.cmd("usepair", n=int(os.environ["SSCAND"]), timeout=30)
    time.sleep(1)
    G.cmd("purge", timeout=90)
    G.cmd("fxspot", timeout=120)
    if os.environ.get("SSREAL"):
        p0 = len(R.read_log())
        G.still(LABEL + "_00_before")
        G.cmd("fxreal", timeout=60)
        G.frames(LABEL + "_f", NFR, ms=WAIT)
    else:
        G.cmd("fxsquad", timeout=60)
        p0 = len(R.read_log())
        time.sleep(3)
        G.still(LABEL + "_00_before")
        G.frames(LABEL + "_pre", NPRE, ms=WAIT)
        if os.environ.get("SSAB") == "A":
            G.cmd("fxen", timeout=30)          # no wall: control
        G.frames(LABEL + "_pre2", 3, ms=WAIT)
        if os.environ.get("SSLOB"):
            G.cmd("lob", timeout=60)
        else:
            G.cmd("wall", timeout=60)
        if os.environ.get("SSAB") == "B":
            G.frames(LABEL + "_wait", 10, ms=WAIT)    # let the bank close first
            G.cmd("fxen", timeout=30)
        G.frames(LABEL + "_f", NFR, ms=WAIT)
    G.cmd("monoff")
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

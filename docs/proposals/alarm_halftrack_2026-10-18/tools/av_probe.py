"""av_probe.py <label> <map> - PROBE-1/2/3 for the alarm vehicle (runtime halftrack spawn, runtime waypoint chain + drive, hull trace)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(A.HERE, "logs", "probe_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, MAP)
    p0 = len(R.read_log())
    G.cmd("here")
    G.cmd("probe1"); time.sleep(3)
    G.still(LABEL + "_p1")
    G.cmd("probe3")
    G.cmd("probe2")
    time.sleep(16)
    G.still(LABEL + "_p2")
    for l in re.findall(r"\^~\^~\^ AV P[0-9][^\r\n]*", R.read_log()[p0:]):
        log("   ", l[:220])
    log("script errors:", len(G.errors()), G.errors()[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

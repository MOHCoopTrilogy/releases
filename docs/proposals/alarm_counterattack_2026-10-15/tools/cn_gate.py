"""cn_gate.py <label> - boot m1l1, evaluate counter_gate for a list of map names (+ stealth flag)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
LABEL = sys.argv[1]
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
NAMES = "m1l1 m4l1 m1l2a m2l1 m3l2 m5l1a m6l3b t1l2 t2l1 t3l1 e3l1 e3l2 e1l1 e1l2 e1l4 e2l2 e3l3 m2l2a m2l3 m3l1a m3l1b m5l2b m6l1c m6l2a m6l3a t2l2 t3l2 co_lobby3 briefing2 training".split()
try:
    rundir, notes = G.boot("cn_" + LABEL, "m1l1", extra=["set coop_counter 1", "set coop_counterDebug 1"])
    p0 = len(R.read_log())
    for n in NAMES:
        R.step(["set cn_map %s" % n], timeout=20)
        G.cmd("gatemap")
    G.cmd("stealthon"); R.step(["set cn_map m1l1"], timeout=20); G.cmd("gatemap"); G.cmd("stealthoff")
    R.step(["set coop_counter 0"], timeout=20); R.step(["set cn_map m1l1"], timeout=20); G.cmd("gatemap")
    for l in re.findall(r"\^~\^~\^ CN GATEMAP ([^\r\n]*)", R.read_log()[p0:]):
        log("   ", l)
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

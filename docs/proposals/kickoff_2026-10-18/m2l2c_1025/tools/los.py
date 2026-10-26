import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
C = [(4004,-5352),(4228,-5112),(4228,-4888),(4020,-4376),(4244,-4136),(4020,-3912),(4228,-3912),(4020,-2680),(4244,-2680),(3796,-2936),(4244,-2936),(4244,-4376),(4020,-4888),(4020,-4136),(4244,-3400),(4020,-3400)]
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=["set coop_objx 0"])
    G.cmd("god"); time.sleep(2)
    for x, y in C:
        p0 = G.cmd("losgrid", x=x, y=y)
        for l in G.since(p0, r"\^~\^~\^ OX (losgrid[^\r\n]*)"): log(l)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

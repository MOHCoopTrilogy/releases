import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
import json
V = json.load(open(sys.argv[2]))
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=["set coop_counterDebug 1"])
    G.cmd("god")
    R.wait_log(r"M2L2C crane B ready", 40, 0)
    p0 = G.cmd("m2ents")
    for l in G.since(p0, r"\^~\^~\^ (OX M2ENT[^\r\n]*)"): log(l)
    for name, (x, y, z, yaw, pitch) in V.items():
        G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)
        R.step(["screenshotJPEG %s" % name, "wait 200"], timeout=20)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

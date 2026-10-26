import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=["set coop_m2NoWaves 1"])
    G.cmd("god"); time.sleep(6)
    for dz in (-150, -150):
        p0 = G.cmd("ubmove", z=dz)
        for l in G.since(p0, r"\^~\^~\^ OX (ubmove[^\r\n]*)"): log(l)
        G.cmd("tp", x=-240, y=-3900, z=-512, yaw=0, pitch=6); time.sleep(0.4)
        R.step(["screenshotJPEG ubm_%d" % abs(dz), "wait 200"], timeout=20)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

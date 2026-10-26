import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
def here():
    p0 = G.cmd("here")
    return G.since(p0, r"\^~\^~\^ OX here \( ([-\d.]+) ([-\d.]+) ([-\d.]+)")
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god"); time.sleep(2)
    for y in range(-3000, -2650, 50):
        for tag, x0, yaw in (("east-bound", 3400, 0),):
            G.cmd("tp", x=x0, y=y, z=-505, yaw=yaw, pitch=0); time.sleep(0.3)
            R.step(["+forward", "wait 3500", "-forward", "wait 200"], timeout=30)
            log(tag, "y=%d" % y, "ended", here())
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

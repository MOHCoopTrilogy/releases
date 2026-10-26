import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
def here(tag):
    p0 = G.cmd("here")
    for l in G.since(p0, r"\^~\^~\^ OX here ([^\r\n]*)"): log(tag, l)
def walk(key, ms):
    R.step(["+%s" % key, "wait %d" % ms, "-%s" % key, "wait 300"], timeout=30)
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god"); time.sleep(2)
    tests = [("pierE west from 950", 950, -3800, 180), ("pierE east from 950", 950, -3800, 0), ("pierW east from -330", -330, -3800, 0), ("pierW west from -330", -330, -3800, 180),
             ("pierE2 west from 2100 y-3400", 2100, -3400, 180), ("pierE2 east from 2100", 2100, -3400, 0),
             ("ledge: 720 west", 720, -3800, 180), ("ledge: 720 east", 720, -3800, 0)]
    for tag, x, y, yaw in tests:
        G.cmd("tp", x=x, y=y, z=-505, yaw=yaw, pitch=0); time.sleep(0.4)
        walk("forward", 2500); here(tag)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

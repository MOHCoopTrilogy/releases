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
    for l in G.since(p0, r"\^~\^~\^ OX here ([^\r\n]*)"):
        log(tag, l)
def walk(ms):
    R.step(["+forward", "wait %d" % ms, "-forward", "wait 300"], timeout=30)
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god")
    time.sleep(2)
    G.cmd("tp", x=-1300, y=-6340, z=-490, yaw=180, pitch=0); time.sleep(0.5); walk(3500); here("gate1 walk west from -1300")
    R.step(["screenshotJPEG w1", "wait 200"], timeout=20)
    G.cmd("tp", x=-2500, y=-6340, z=-490, yaw=180, pitch=0); time.sleep(0.5); walk(3500); here("gate2 walk west from -2500")
    R.step(["screenshotJPEG w2", "wait 200"], timeout=20)
    G.cmd("tp", x=-2500, y=-6340, z=-490, yaw=180, pitch=0)
    p0 = G.cmd("gmove", z=-60)
    for l in G.since(p0, r"\^~\^~\^ (OX gmove[^\r\n]*)"): log(l)
    walk(3500); here("gate2 raised, walk west")
    R.step(["screenshotJPEG w3", "wait 200"], timeout=20)
    G.cmd("tp", x=-2500, y=-6340, z=-490, yaw=180, pitch=0)
    G.cmd("gmove", z=-380)
    G.cmd("tp", x=-3100, y=-6300, z=-490, yaw=0, pitch=0); time.sleep(0.5); walk(3500); here("from west toward closed gate2")
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

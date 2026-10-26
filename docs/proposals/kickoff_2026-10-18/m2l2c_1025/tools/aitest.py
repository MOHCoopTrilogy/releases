import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
def ev(p0, pat, tag):
    for l in G.since(p0, pat): log(tag, l)
PAT_T = r"\^~\^~\^ (OX aitest[^\r\n]*)"
PAT_P = r"\^~\^~\^ (OX aipos[^\r\n]*)"
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god")
    time.sleep(2)
    G.cmd("tp", x=-1300, y=-6340, z=-490, yaw=180, pitch=0)
    p0 = G.cmd("aitest", x=-1300, y=-6340, z=-490, yaw=-900, pitch=-6340, k=-496)
    ev(p0, PAT_T, "control")
    for k in range(3):
        time.sleep(2.5)
        p0 = G.cmd("aipos"); ev(p0, PAT_P, "control")
    log("--- pocket test: west of gate1, goal east of it")
    p0 = G.cmd("aitest", x=-2300, y=-6340, z=-490, yaw=-1100, pitch=-6340, k=-496)
    ev(p0, PAT_T, "pocket")
    for k in range(6):
        time.sleep(2.5)
        p0 = G.cmd("aipos"); ev(p0, PAT_P, "pocket")
    R.step(["screenshotJPEG ai1", "wait 200"], timeout=20)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

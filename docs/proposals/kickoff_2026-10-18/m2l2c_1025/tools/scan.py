"""scan.py <label> <scans.json>: floor/ceiling line scans. scans.json = {name: [x,y,z,yaw,step,n]}"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
SC = json.load(open(sys.argv[2]))
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god")
    time.sleep(2)
    for name, (x, y, z, yaw, step, n) in SC.items():
        p0 = G.cmd("scan", x=x, y=y, z=z, yaw=yaw, pitch=step, k=n)
        log("## " + name)
        for l in G.since(p0, r"\^~\^~\^ OX scan ([^\r\n]*)"):
            log(l)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

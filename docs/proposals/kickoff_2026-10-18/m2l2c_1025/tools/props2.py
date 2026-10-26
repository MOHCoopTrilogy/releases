import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
def mk(model, x, y, z, pitch=0, yaw=0, roll=0, scale=0, cls="script_model"):
    return G.cmd("mk2", s=model, x=x, y=y, z=z, pitch=pitch, yaw=yaw, roll=roll, k=scale, cls=cls)
def shot(name, x, y, z, yaw, pitch=0):
    G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)
    R.step(["screenshotJPEG %s" % name, "wait 200"], timeout=20)
    log("shot", name)
SC = json.load(open(sys.argv[2]))
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c")
    G.cmd("god")
    time.sleep(2)
    for step in SC:
        kind = step[0]
        if kind == "mk":
            p0 = mk(*step[1:]); 
            for l in G.since(p0, r"\^~\^~\^ (OX mk2[^\r\n]*)"): log(l, step[1])
        elif kind == "shot":
            shot(*step[1:])
        elif kind == "clr":
            G.cmd("clr2")
        elif kind == "hray":
            name, (x, y, z, yaw, ln, n, stp) = step[1], step[2]
            p0 = G.cmd("hray", x=x, y=y, z=z, yaw=yaw, pitch=ln, k=n, step=stp)
            log("## hray " + name)
            for l in G.since(p0, r"\^~\^~\^ OX hray ([^\r\n]*)"): log(l)
        elif kind == "mv":
            G.cmd("mv2", k=step[1], x=step[2], y=step[3], z=step[4])
        elif kind == "light":
            G.cmd("light2", k=step[1], pitch=step[2])
        elif kind == "wait":
            time.sleep(step[1])
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

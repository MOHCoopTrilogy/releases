"""recon.py <label> : tour candidate viewpoints on m2l2c and screenshot each. Run inside a harness_turn turn."""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
VIEWS = json.load(open(sys.argv[2]))
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=(["set coop_objx 1"]))
    G.cmd("god")
    time.sleep(2)
    if os.environ.get("M2GL1") == "1":
        R.step(["set cl_renderer opengl1", "vid_restart", "wait 6000"], timeout=60)
        time.sleep(4)
        log("renderer now", R.read_log()[-600:].count("OpenGL"))
    for name, (x, y, z, yaw, pitch) in VIEWS.items():
        G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)
        R.step(["screenshotJPEG %s" % name, "wait 200"], timeout=20)
        log("shot", name, x, y, z, yaw, pitch)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

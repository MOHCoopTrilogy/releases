"""ox_shot.py <label> - does harness gunfire (+attackprimary) damage a shootable prop? Tries class animate and script_model_realdamage."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
T0 = time.time()
def log(*a):
    s = "%5.0fs " % (time.time() - T0) + " ".join(str(x) for x in a)
    G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + LABEL, "m1l3c")
    G.cmd("god")
    G.cmd("kit")
    time.sleep(3)
    R.step(["screenshotJPEG shot_kit", "wait 150"], timeout=20)
    for cls in ("animate", "script_model_realdamage"):
        G.cmd("mktarget", s=cls)
        G.cmd("aimtarget")
        G.cmd("targethp")
        R.step(["+attackprimary", "wait 700", "screenshotJPEG shot_%s" % cls, "wait 800", "-attackprimary", "wait 300"], timeout=20)
        G.cmd("targethp")
        log("class", cls, "done")
    for l in re.findall(r"\^~\^~\^ (OX (?:mktarget|targethp)[^\r\n]*)", R.read_log()):
        log(l[:200])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

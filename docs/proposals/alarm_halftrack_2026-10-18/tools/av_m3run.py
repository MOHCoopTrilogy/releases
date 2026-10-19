"""av_m3run.py <label> [minutes] - one full m3l3 sequence: officer reward check, church hold (45 s), paradrop, then the Nebelwerfer fight with the
new nests / defenders / waves / halftracks / rocket crate. Logs ^~^~^ NEB / PARADROP / OFFICER_DROP / PSQ lines, screenshots at the church (para squad)
and a frame burst around the guard halftracks."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL = sys.argv[1]
MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 9
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, "m3l3", extra=["set coop_reinfDebug 1", "set coop_mortarDebug 1", "set coop_alarmVehDebug 1", "set coop_alarmVehIgnoreMission 1"])
    p0 = len(R.read_log())
    G.cmd("here")
    G.cmd("offdrop")
    time.sleep(8)
    G.cmd("m3church")
    t0 = time.time()
    while time.time() - t0 < 240:
        G.cmd("m3status")
        txt = R.read_log()[p0:]
        if re.search(r"AVT m3 chDone=1", txt):
            break
        time.sleep(6)
    log("church hold finished after %d s" % (time.time() - t0))
    time.sleep(25)                      # the paradrop lands
    G.still(LABEL + "_church_para")
    G.frames(LABEL + "_para", 6, 400)
    G.cmd("m3nebel")
    t1 = time.time()
    shot = 0
    while time.time() - t1 < MIN * 60:
        time.sleep(15)
        G.cmd("m3status")
        txt = R.read_log()[p0:]
        if shot == 0 and re.search(r"NEB t=\S+ halftrack 1 stop", txt):
            shot = 1
    for l in re.findall(r"\^~\^~\^ (?:NEB|PARADROP|OFFICER_DROP|AVT officer|AVT m3|ALMVEH|MZ|CHDEFEND|PSQ)[^\r\n]*", R.read_log()[p0:]):
        if "AVT t=" in l:
            continue
        log("   ", l[:240])
    log("script errors:", len(G.errors()), G.errors()[:8])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-700:])
finally:
    G.end(rundir, notes)

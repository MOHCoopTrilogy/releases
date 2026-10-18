"""ap_shots.py <label> <map> - boot <map> (coop_alarm 1) on the private client, and for every placed switch teleport the player 125 u in
front of it facing the wall and take engine screenshots (lit + fullbright). Prints ^~^~^ AP lines. One game at a time (slot)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aplib as A
G = A.G; R = A.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("ap_" + LABEL, MAP, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set r_fullbright 0"])
    p0 = len(R.read_log())
    time.sleep(3)
    G.cmd("count", timeout=60)
    m = re.findall(r"AP COUNT sw=(\d+) bell=(\d+)", R.read_log()[p0:])
    n = int(m[-1][0]) if m else 0
    log("placed", m[-1] if m else None)
    for i in range(1, n + 1):
        for _t in range(14):
            G.cmd("view", timeout=60, i=i)
            time.sleep(1.0)
            G.cmd("view", timeout=60, i=i)
            _v = re.findall(r"AP VIEW i=\d+ .*? eye=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) now=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \)", R.read_log()[-4000:])
            if _v and abs(float(_v[-1][0]) - float(_v[-1][3])) < 30 and abs(float(_v[-1][1]) - float(_v[-1][4])) < 30:
                break
            log("view not held yet (ride/intro?), waiting", _t)
            time.sleep(10)
        R.step(["set r_fullbright 0", "wait 700"], timeout=30)
        G.still("%s_%s_%d_lit" % (LABEL, MAP, i))
        R.step(["set r_fullbright 1", "wait 700"], timeout=30)
        G.still("%s_%s_%d_fb" % (LABEL, MAP, i))
        R.step(["set r_fullbright 0"], timeout=30)
    for l in re.findall(r"\^~\^~\^ AP [^\r\n]*", R.read_log()[p0:]):
        log("   ", l[:200])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

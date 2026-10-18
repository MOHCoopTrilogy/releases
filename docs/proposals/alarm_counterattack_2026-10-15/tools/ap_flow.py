"""ap_flow.py <label> <map> - full defend-zone clock proof: counter starts, players hold (counts down), LEAVE (pauses, then winds back), ENTER
(resumes), enemies placed in an EMPTY zone (zone lost, restart), then the clock runs out to 0:00. Logs every ^~^~^ COUNTER line."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aplib as A
G = A.G; R = A.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
def lv():
    m = re.findall(r"COUNTER (?:tick|state)[^\r\n]* t=([\d.]+)", R.read_log()[-8000:])
    return float(m[-1]) if m else 0.0
def waitfor(pat, limit, since=None):
    t = time.time()
    since = len(R.read_log()) if since is None else since
    while time.time() - t < limit:
        if re.search(pat, R.read_log()[since:]):
            return True
        time.sleep(1)
    return False
rundir = notes = None
try:
    rundir, notes = G.boot("flow_" + LABEL, MAP, extra=["set coop_counter 1", "set coop_counterDebug 1", "set coop_counterForce 1", "set ui_hud 1",
        "set coop_counterSecs 70", "set coop_counterWaveGap 12", "set coop_counterGrace 6", "set coop_counterLoseTime 25", "set coop_counterCap 6", "set coop_alarm 1", "set coop_dbno 0"])
    p0 = len(R.read_log())
    time.sleep(3)
    G.cmd("stay", timeout=60)
    time.sleep(1)
    G.cmd("mc", timeout=60, nl="m9x")
    if not waitfor(r"COUNTER zone src", 40, p0): raise RuntimeError("no zone")
    time.sleep(1); G.frames(LABEL + "_gstart", 22, 230)
    waitfor(r"COUNTER tick[^\r\n]*state=hold[^\r\n]*remaining=([4-6][0-9])", 60)
    time.sleep(2)
    log("--- LEAVE")
    G.cmd("leave", timeout=60)
    G.frames(LABEL + "_gleave", 26, 230)
    time.sleep(2)
    log("--- ENTER")
    G.cmd("enter", timeout=60)
    G.frames(LABEL + "_gresume", 22, 230)
    log("--- LEAVE again + enemies in the empty zone")
    G.cmd("leave", timeout=60)
    G.cmd("foe", timeout=60)
    waitfor(r"COUNTER zone LOST", 60)
    G.cmd("enter", timeout=60)
    G.cmd("foe", timeout=60) if False else None
    waitfor(r"COUNTER clock 0:00", 200)
    time.sleep(3)
    for l in re.findall(r"\^~\^~\^ (?:COUNTER|AP (?:LEAVE|ENTER|FOE))[^\r\n]*", R.read_log()[p0:]):
        log("   ", l[:260])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

"""ap_carry.py <label> - lose a defend zone on e3l2, go to e3l3 through the REAL mission-complete path, show the heavier numbers + message + cleared
state; then prove a same-map reload clears a carried state. Logs every ^~^~^ CARRY / AP CARRY / COUNTER line."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aplib as A
G = A.G; R = A.R
LABEL, MAP, NL, FAKE = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
def waitfor(pat, limit, since):
    t = time.time()
    while time.time() - t < limit:
        if re.search(pat, R.read_log()[since:]):
            return True
        time.sleep(1)
    return False
def armed():
    return len(re.findall(r"\^~\^~\^ AI armed", R.read_log()))
rundir = notes = None
try:
    rundir, notes = G.boot("carry_" + LABEL, MAP, extra=["set coop_counter 1", "set coop_counterDebug 1", "set coop_counterForce 1", "set ui_hud 1",
        "set coop_counterSecs 20", "set coop_counterWaveGap 10", "set coop_counterGrace 3", "set coop_counterLoseTime 8", "set coop_counterCap 6", "set coop_dbno 0",
        "set coop_counterPenalty 1", "set coop_alarm 1", "set coop_alarmDebug 1"])
    p0 = len(R.read_log())
    time.sleep(3)
    G.cmd("carrystate", timeout=60)
    G.cmd("stay", timeout=60)
    time.sleep(1)
    G.cmd("mc", timeout=60, nl=NL)
    if not waitfor(r"COUNTER zone src", 40, p0): raise RuntimeError("no zone")
    time.sleep(6)
    G.cmd("leave", timeout=60)
    G.cmd("foe", timeout=60)
    if not waitfor(r"COUNTER zone LOST", 60, p0): raise RuntimeError("zone never lost")
    G.cmd("carrystate", timeout=60)
    G.cmd("enter", timeout=60)
    waitfor(r"COUNTER clock 0:00", 120, p0)
    a0 = armed()
    log("armed count before transition", a0)
    t = time.time()
    while armed() <= a0 and time.time() - t < 240:
        time.sleep(3)
    log("next map up:", armed() > a0)
    time.sleep(8)
    G.cmd("carrystate", timeout=90)
    waitfor(r"CARRY message sent", 90, 0)
    time.sleep(2)
    G.cmd("carrystate", timeout=60)
    if waitfor(r"CARRY ALARM ON START", 120, 0):
        time.sleep(4)
        G.cmd("carrystate", timeout=60)
        G.cmd("shoot1", timeout=60)
        time.sleep(4)
    if FAKE:
        a1 = armed()
        G.cmd("carryfake", timeout=60)
        t = time.time()
        while armed() <= a1 and time.time() - t < 200:
            time.sleep(3)
        time.sleep(8)
        G.cmd("carrystate", timeout=90)
    txt = R.read_log()
    for l in re.findall(r"\^~\^~\^ (?:CARRY|ALARM LIVE|ALARM OFF|ALARM wave|AP SHOOT1|AP CARRY|AP CARRYFAKE|COUNTER (?:start|zone|end|clock)|AI armed)[^\r\n]*", txt):
        log("   ", l[:260])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

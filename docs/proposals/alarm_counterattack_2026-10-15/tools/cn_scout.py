"""cn_scout.py <label> <map> [kill] - boot, auto-place alarm points at the densest guard clusters, QA still of switch 1, arm the
watcher, put the player next to a guard, watch the runner / LIVE / waves, shoot the switch -> OFF. Logs the ALMPT lines for alarm_points.json."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
KILL = "kill" in sys.argv[3:]
GEN = "gen" in sys.argv[3:]
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
def lvt():
    m = re.findall(r"CN ALM [^\r\n]* t=([\d.]+)", R.read_log()[-6000:])
    return float(m[-1]) if m else 0
try:
    rundir, notes = G.boot("cn_" + LABEL, MAP, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set coop_alarmWaveGap 10", "set coop_reinfDebug 1", "set coop_alarmMaxPulls 2"])
    p0 = len(R.read_log())
    if not GEN:
        G.cmd("scout", timeout=60)
        G.cmd("viewsw", timeout=60)
        R.step(["set r_fullbright 1", "wait 30"], timeout=20)
        time.sleep(1)
        G.still(LABEL + "_switch")
        R.step(["set r_fullbright 0"], timeout=20)
        G.cmd("arm")
    for k in range(30):
        G.cmd("almstate")
        t = lvt()
        if t >= 62:
            break
        time.sleep(max(1, min(10, 63 - t)))
    R.step(["notarget 0"], timeout=20)
    G.cmd("tpguard", timeout=60)
    killed = False
    for k in range(22):
        time.sleep(3)
        txt = R.read_log()[p0:]
        if KILL and not killed and re.search(r"ALARM runner start", txt):
            G.cmd("killrunner")
            killed = True
        G.cmd("almstate")
        txt = R.read_log()[p0:]
        if re.search(r"ALARM LIVE", txt) or re.search(r"ALARM pull cancelled", txt):
            break
    if re.search(r"ALARM LIVE", R.read_log()[p0:]):
        time.sleep(14)
        G.cmd("almstate")
        G.still(LABEL + "_live")
        G.cmd("shoot1", timeout=60)
        time.sleep(4)
        G.cmd("almstate")
    for l in re.findall(r"\^~\^~\^ (?:ALARM[^\r\n]*|ALMGATE[^\r\n]*|CN (?:ALM|PROBE|SCOUT|ALMPT|TPGUARD|KILLRUNNER|SHOOT1|VIEWSW|ARMED)[^\r\n]*)", R.read_log()[p0:]):
        log("   ", l[:230])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

"""cn_alm.py <label> <map> - m4l3 adopted-mode alarm test: pull the vanilla alarm, watch the waves, shoot the switch."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("cn_" + LABEL, MAP, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set coop_alarmWaveGap 10", "set coop_reinfDebug 1"])
    p0 = len(R.read_log())
    G.cmd("almstate")
    G.cmd("pull")
    for k in range(3):
        time.sleep(9)
        G.cmd("almstate")
    G.still(LABEL + "_live")
    G.cmd("shoot")
    time.sleep(4)
    G.cmd("almstate")
    time.sleep(3)
    G.cmd("almstate")
    for l in re.findall(r"\^~\^~\^ (?:ALARM[^\r\n]*|ALMGATE[^\r\n]*|CN ALM[^\r\n]*|CN SHOOT[^\r\n]*)", R.read_log()[p0:]):
        log("   ", l[:230])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

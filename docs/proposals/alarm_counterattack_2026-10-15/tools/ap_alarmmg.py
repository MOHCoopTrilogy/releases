"""ap_alarmmg.py <label> <map> - one alarm pull on <map>: prove it brings exactly ONE MG42 team (wave 1 or 2, hidden entry), with GIF frames
of the switch area while it sets up. coop_reinfMgChance 0 proves the alarm's team is guaranteed (the officer's roll is bypassed)."""
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
    rundir, notes = G.boot("mg_" + LABEL, MAP, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set coop_reinfDebug 1", "set coop_reinfMgChance 0",
        "set coop_alarmWaveGap 12", "set coop_alarmMg 1", "set ui_hud 1", "set coop_dbno 0"])
    p0 = len(R.read_log())
    time.sleep(3)
    G.cmd("count", timeout=60)
    G.cmd("view", timeout=60, i=1)
    time.sleep(1)
    G.cmd("view", timeout=60, i=1)
    G.cmd("pull", timeout=60)
    t0 = time.time()
    while time.time() - t0 < 60 and not re.search(r"ALARM MG team called", R.read_log()[p0:]):
        time.sleep(1)
    time.sleep(5)
    for _t in range(8):
        G.cmd("viewmg", timeout=60)
        if re.search(r"AP VIEWMG gunner", R.read_log()[-3000:]):
            break
        time.sleep(3)
    time.sleep(1)
    G.frames("%s_mgset" % LABEL, 28, 300)
    time.sleep(2)
    txt = R.read_log()[p0:]
    for l in re.findall(r"\^~\^~\^ (?:ALARM|RMG|AP PULL)[^\r\n]*", txt):
        log("   ", l[:230])
    log("MG team called lines:", len(re.findall(r"ALARM MG team called", txt)))
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

"""ap_cz.py <label> <map> - boot <map>; for every vetted defend zone (docs/tools/counter_zones.json) start its marker, stand 260 u away looking at it
and take an engine screenshot (HUD on, so the compass diamond shows). A map with no vetted zone gets one 'fallback' shot via a forced counter start."""
import json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aplib as A
G = A.G; R = A.R
LABEL, MAP = sys.argv[1], sys.argv[2]
Z = json.load(open("C:/mohaa-coop-dev/docs/tools/counter_zones.json")).get(MAP, [])
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("cz_" + LABEL, MAP, extra=["set coop_counter 1", "set coop_counterDebug 1", "set coop_counterForce 1", "set ui_hud 1", "set coop_alarm 1"])
    p0 = len(R.read_log())
    time.sleep(3)
    log("vetted zones", len(Z))
    for i in range(1, len(Z) + 1):
        for _t in range(14):
            G.cmd("czshow", timeout=90, i=i)
            time.sleep(1.0)
            G.cmd("czshow", timeout=90, i=i)
            _v = re.findall(r"AP CZ i=\d+ .*? eye=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) now=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \)", R.read_log()[-4000:])
            if _v and abs(float(_v[-1][0]) - float(_v[-1][3])) < 30 and abs(float(_v[-1][1]) - float(_v[-1][4])) < 30:
                break
            log("view not held yet (ride/intro?), waiting", _t)
            time.sleep(10)
        R.step(["set ui_hud 1", "wait 900"], timeout=30)
        G.still("%s_%s_z%d" % (LABEL, MAP, i))
    if not Z:
        G.cmd("mc", timeout=60, nl="m9x")
        time.sleep(6)
        G.still("%s_%s_zfb" % (LABEL, MAP))
    for l in re.findall(r"\^~\^~\^ (?:AP CZ|COUNTER (?:start|zone)|AP )[^\r\n]*", R.read_log()[p0:]):
        log("   ", l[:220])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)

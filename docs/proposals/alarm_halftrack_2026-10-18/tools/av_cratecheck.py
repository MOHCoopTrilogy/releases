"""av_cratecheck.py <label> <map> - alarm start: the crate scan runs, then the camera stands at the crate looking at the vehicle stop (screenshot proof)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL, MAP = sys.argv[1], sys.argv[2]
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, MAP, extra=["set coop_alarmVeh 1", "set coop_alarmVehDebug 1", "set coop_alarmVehDelay 400",
                           "set coop_alarmVehMinTime 0", "set coop_alarmVehIgnoreMission 1", "set g_ai 1"] + ([x for x in os.environ.get("AVEXTRA", "").split(";") if x]))
    p0 = len(R.read_log())
    G.cmd("here")
    G.cmd("arm")
    m = R.wait_log(r"\^~\^~\^ ALMVEH (CRATE route|crate FAILED)", 240, p0)
    time.sleep(1)
    G.cmd("cratecam")
    time.sleep(2.5)
    G.still(LABEL + "_crate_to_stop")
    G.cmd("here")
    for l in re.findall(r"\^~\^~\^ (?:ALMVEH (?:CRATE|crate)|ATSUPPLY|AVT cratecam)[^\r\n]*", R.read_log()[p0:]):
        G.log(LABEL, "   ", l[:260])
    G.log(LABEL, "script errors:", len(G.errors()), G.errors()[:3])
except Exception as e:
    import traceback
    G.log(LABEL, "FAILED", repr(e), traceback.format_exc()[-500:])
finally:
    G.end(rundir, notes)

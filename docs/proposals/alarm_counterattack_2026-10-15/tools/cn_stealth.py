"""cn_stealth.py <label> <map> - stealth regression: boot with coop_alarm 1 + coop_counter 1, expect no '^~^~^ ALARM' / 'COUNTER start' line.
The boot may fail to spawn a player on stealth maps (harness limit); the log is read either way."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
rundir = notes = None
try:
    try:
        rundir, notes = G.boot("cn_" + LABEL, MAP, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set coop_counter 1", "set coop_counterDebug 1"])
    except Exception as e:
        G.log(LABEL, "boot note:", repr(e)[:120])
    time.sleep(12)
    t = R.read_log()
    alarm = [l for l in re.findall(r"\^~\^~\^ ALARM [^\r\n]*", t) if not l.startswith("^~^~^ ALARM SYSTEM")]
    G.log(LABEL, "non-SYSTEM ALARM lines:", alarm[:3])
    gate = re.findall(r"\^~\^~\^ ALMGATE [^\r\n]*", t)
    cnt = re.findall(r"\^~\^~\^ COUNTER [^\r\n]*", t)
    armed = len(re.findall(r"coop_mainScriptLoaded|Detected Coop", t))
    G.log(LABEL, MAP, "coop-detected=%d ALARM lines=%d ALMGATE=%s COUNTER lines=%d" % (armed, len(alarm), gate[:2], len(cnt)))
    G.log(LABEL, "script errors", len(G.errors()), [x[-120:] for x in G.errors()[:3]])
finally:
    try:
        G.end(rundir, notes)
    except Exception as e:
        G.log("end", repr(e)[:80])

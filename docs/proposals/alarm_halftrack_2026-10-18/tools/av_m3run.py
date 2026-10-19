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
    G.cmd("find30")
    time.sleep(2)
    G.still(LABEL + "_church_para")
    G.frames(LABEL + "_para", 6, 400)
    G.cmd("m3nebel")
    t1 = time.time()
    # 1. the guard halftracks arrive: chase camera
    if R.wait_log(r"\^~\^~\^ ALMVEH ARRIVING halftrack", 150, p0):
        G.cmd("follow", x="450", y="250", z="160")
        G.frames(LABEL + "_ht_in", 26, 250)
    R.wait_log(r"\^~\^~\^ ALMVEH ARRIVED halftrack", 120, p0)
    G.frames(LABEL + "_ht_park", 10, 300)
    # 2. the squad moves up to Nebelwerfer 1: the nests see a player, the halftrack covers him
    G.cmd("nofollow")
    G.cmd("m3to", x="-1560", y="-4850", z="-120")
    G.cmd("pin", x="-1560", y="-4850", z="-120", lx="-2433", ly="-5096", lz="-40")
    time.sleep(40)
    G.frames(LABEL + "_fight", 18, 300)
    # 3. a charge goes on Nebelwerfer 1: defend wave, blast, counter-push
    G.cmd("m3plant", x="1")
    G.frames(LABEL + "_plant", 24, 300)
    time.sleep(45)
    G.frames(LABEL + "_counter", 18, 300)
    while time.time() - t1 < MIN * 60:
        time.sleep(15)
        G.cmd("m3status")
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

"""mg_sess4.py <label> <map> - relocation: once the gun has been up for 8 s the player steps to its flank (outside the arc, 280u, a line to it): it must
pack up and set up again somewhere else (relocate why=flanked), then a grenade is laid 150u from the gun: the crew runs and comes back."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mglib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
RMG = r"\^~\^~\^ (?:RMG[^\r\n]*|MG (?:camgun|GUN)[^\r\n]*|PSQ[^\r\n]*)"


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


def waitfor(pat, secs, p0):
    t = time.time()
    while time.time() - t < secs:
        m = re.search(pat, R.read_log()[p0:])
        if m:
            return m
        time.sleep(0.7)
    return None


try:
    rundir, notes = G.boot("mg_" + LABEL, MAP, extra=["set coop_paraDebug 1"])
    hh = G.since(G.cmd("here"), r"MG here \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) ang=\( [-\d.]+ ([-\d.]+)")
    X, Y, Z, YAW = [float(v) for v in hh[-1]]
    G.cmd("god")
    G.cmd("setup", yaw=YAW, timeout=90)
    G.cmd("purge", timeout=90)
    G.cmd("tpoff", n=700)
    time.sleep(2)
    p0 = len(R.read_log())
    G.cmd("wave", timeout=60)
    m = waitfor(r"RMG t=[\d.]+ gun up", 110, p0)
    log("gun up:", m.group(0) if m else None)
    if m:
        time.sleep(9)
        p1 = len(R.read_log())
        G.cmd("camgun", x=280, n=0)
        G.cmd("mute")
        m = waitfor(r"RMG t=[\d.]+ relocate", 30, p1)
        log("relocate:", m.group(0) if m else None)
        m = waitfor(r"RMG t=[\d.]+ pack up", 30, p1)
        log("pack up:", m.group(0) if m else None)
        m = waitfor(r"RMG t=[\d.]+ gun up", 90, p1)
        log("gun up again:", m.group(0) if m else None)
        time.sleep(4)
        G.cmd("state")
        for l in G.since(p0, RMG)[:60]:
            log("   ", l[:230])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

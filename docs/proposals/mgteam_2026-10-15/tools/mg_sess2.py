"""mg_sess2.py <label> <map> - close-up frame sequences of the officer's MG42 team: (1) the set-up (arrival, unpack, bipod, gun, mount),
(2) the gun firing at the player, (3) the gunner killed and the assistant taking the gun. Frames in runs/mg_<label>/, GIFs by mg_gif.py."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mglib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
RMG = r"\^~\^~\^ (?:RMG[^\r\n]*|MG (?:camgun|STATE|MAN|GUN)[^\r\n]*)"


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


def waitfor(pat, secs, p0):
    t = time.time()
    while time.time() - t < secs:
        m = re.search(pat, R.read_log()[p0:])
        if m:
            return m
        time.sleep(0.5)
    return None


def cam(dist, off, tries=40):
    for i in range(tries):
        p = len(R.read_log())
        G.cmd("camgun", x=dist, n=off)
        if re.search(r"MG camgun at=", R.read_log()[p:]):
            return True
        time.sleep(0.5)
    return False


try:
    rundir, notes = G.boot("mg_" + LABEL, MAP, extra=[])
    hh = G.since(G.cmd("here"), r"MG here \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) ang=\( [-\d.]+ ([-\d.]+)")
    X, Y, Z, YAW = [float(v) for v in hh[-1]]
    G.cmd("god")
    G.cmd("setup", yaw=YAW, timeout=90)
    G.cmd("purge", timeout=90)
    G.cmd("tpoff", n=700)
    time.sleep(2)
    G.cmd("calm")
    G.cmd("nt")
    p0 = len(R.read_log())
    G.cmd("wave", timeout=60)
    # (1) the set-up
    m = waitfor(r"RMG t=[\d.]+ staged", 80, p0)
    log("staged:", m.group(0) if m else None)
    ok = cam(280, 0)
    log("camera:", ok)
    if ok:
        G.frames(LABEL + "_s1", 60, ms=150)
        log("set-up frames taken")
    waitfor(r"RMG t=[\d.]+ gun up", 40, p0)
    # (2) firing: the camera inside the arc, 20 degrees off the line, 450u out
    ok = cam(380, 1)
    log("camera 2:", ok)
    time.sleep(3)
    G.frames(LABEL + "_s2", 30, ms=60)
    # (3) the gunner killed, the assistant takes over: the camera back out of the arc
    ok = cam(280, 0)
    log("camera 3:", ok)
    G.cmd("killgunner")
    G.frames(LABEL + "_s3", 44, ms=100)
    for l in G.since(p0, RMG)[:50]:
        log("   ", l[:240])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

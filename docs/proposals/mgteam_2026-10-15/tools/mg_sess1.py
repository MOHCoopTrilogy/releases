"""mg_sess1.py <label> <map> - the officer's MG42 team on the map's REAL officer: call, walk, set-up, engage, gunner killed -> the assistant takes over;
then the team is killed (its gun is left for the players), the officer dies, the radio's call brings the team again to cover the RADIO."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mglib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
RMG = r"\^~\^~\^ (?:RMG[^\r\n]*|RNF radio[^\r\n]*|MG (?:STATE|MAN|GUN)[^\r\n]*)"


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


def waitfor(pat, secs, p0):
    t = time.time()
    while time.time() - t < secs:
        m = re.search(pat, R.read_log()[p0:])
        if m:
            return m
        time.sleep(1.0)
    return None


try:
    rundir, notes = G.boot("mg_" + LABEL, MAP, extra=[])
    hh = G.since(G.cmd("here"), r"MG here \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) ang=\( [-\d.]+ ([-\d.]+)")
    X, Y, Z, YAW = [float(v) for v in hh[-1]]
    log("player", X, Y, Z, "yaw", YAW)
    G.cmd("god")
    G.cmd("setup", yaw=YAW, timeout=90)
    G.cmd("purge", timeout=90)
    G.cmd("tpoff", n=700)
    time.sleep(2)
    G.cmd("lookoff")
    G.still(LABEL + "_a_officer")
    p0 = len(R.read_log())
    G.cmd("wave", timeout=60)
    t0 = time.time()
    up = None
    k = 0
    while time.time() - t0 < 110:
        time.sleep(5)
        G.cmd("state")
        k += 1
        if k % 2 == 0:
            G.cmd("lookgun"); G.still("%s_b_walk%02d" % (LABEL, k))
        if re.search(r"RMG t=[\d.]+ gun up", R.read_log()[p0:]):
            up = time.time(); break
    log("gun up:", bool(up), "after", int(time.time() - t0), "s")
    if up:
        G.cmd("lookgun")
        G.frames(LABEL + "_c_seq", 14, ms=250)
        time.sleep(8)
        G.cmd("lookgun"); G.still(LABEL + "_d_firing")
        G.cmd("state")
        p1 = len(R.read_log())
        G.cmd("killgunner")
        time.sleep(1)
        G.cmd("lookgun"); G.still(LABEL + "_e_gunnerdown")
        m = waitfor(r"takeover done|takeover failed", 60, p1)
        log("takeover:", m.group(0) if m else None)
        time.sleep(8)
        G.cmd("state"); G.cmd("lookgun"); G.still(LABEL + "_f_assistant")
        for l in G.since(p0, RMG)[:50]:
            log("   ", l[:240])
        # the radio phase
        G.cmd("killteam"); time.sleep(3)
        G.cmd("state"); G.cmd("lookgun"); G.still(LABEL + "_g_gunleft")
        p2 = len(R.read_log())
        G.cmd("officerdie")
        m = waitfor(r"RMG t=[\d.]+ team sid=\d+ n=\d+ anchor=radio", 120, p2)
        log("radio team called:", m.group(0) if m else None)
        if m:
            t1 = time.time()
            while time.time() - t1 < 100:
                time.sleep(5)
                G.cmd("state")
                if re.search(r"RMG t=[\d.]+ gun up", R.read_log()[p2:]):
                    break
            G.cmd("lookgun"); G.still(LABEL + "_h_radio_walk")
            time.sleep(6)
            G.cmd("lookgun"); G.still(LABEL + "_i_radio_gun")
            G.cmd("state")
        for l in G.since(p2, RMG)[:60]:
            log("   ", l[:240])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

"""mg_sess3.py <label> <map> <aim 1|0> - lethality A/B on the same geometry: the player (mortal, 100000 hp, standing still 700u from the officer, in the
gun's lane) is shot at for 45 s once the gun is up. aim=1 is the team's script fire control, aim=0 the stock engine track cycle (the standard nest)."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mglib as G
R = G.R
LABEL, MAP, AIM = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


try:
    rundir, notes = G.boot("mg_" + LABEL, MAP, extra=["set coop_reinfMgAim " + AIM, "set coop_reinfMgSetup 1"])
    hh = G.since(G.cmd("here"), r"MG here \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) ang=\( [-\d.]+ ([-\d.]+)")
    X, Y, Z, YAW = [float(v) for v in hh[-1]]
    G.cmd("god")
    G.cmd("setup", yaw=YAW, timeout=90)
    G.cmd("purge", timeout=90)
    G.cmd("tpoff", n=700)
    time.sleep(2)
    p0 = len(R.read_log())
    G.cmd("wave", timeout=60)
    t0 = time.time()
    while time.time() - t0 < 120 and not re.search(r"RMG t=[\d.]+ gun up", R.read_log()[p0:]):
        time.sleep(2)
    log("gun up:", bool(re.search(r"RMG t=[\d.]+ gun up", R.read_log()[p0:])), "aim", AIM)
    G.cmd("mute")
    time.sleep(2)
    G.cmd("mortal")
    p1 = len(R.read_log())
    for i in range(26):
        time.sleep(2)
        G.cmd("mute")
        G.cmd("hp")
    hp = [(float(a), float(b), b2) for a, b, b2 in re.findall(r"MG HP t=([\d.]+) hp=([\d.]+) bursts=(\S+)", R.read_log()[p1:])]
    if hp:
        dmg = 100000 - hp[-1][1]
        secs = hp[-1][0] - hp[0][0]
        log("RESULT aim=%s gun-only damage=%.0f in %.0fs of game time (%.1f hp/s), bursts %s -> %s" % (AIM, dmg, secs, dmg / max(secs, 1), hp[0][2], hp[-1][2]))
        log("hp series:", [(round(t), int(100000 - h)) for t, h, _ in hp])
    for l in G.since(p0, r"\^~\^~\^ (?:RMG (?:burst|target|gun up)[^\r\n]*)")[:40]:
        log("   ", l[:200])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

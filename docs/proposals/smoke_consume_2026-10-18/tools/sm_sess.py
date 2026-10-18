"""sm_sess.py <label> <map> <flow>   flows: smoke | unused | binoc | drops
 smoke  : give the smoke, throw it (real input; sim fallback), state in flight / landed, die, respawn, state, refresh, state, throw again
 unused : give the smoke, die with it, respawn, walk over the drop (recovered), state, die again with it unused after a refresh
 binoc  : grant binoculars, fire (the one strike), state, die, respawn, state
 drops  : 10 officer drops on this (outdoor) map, 1 on an indoor map name, cache use by every player twice
"""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smlib
G = smlib.G
R = G.R
LABEL, MAP, FLOW = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
PAT = r"\^~\^~\^ (?:SM [^\r\n]*|SMOKE_[A-Z]+[^\r\n]*|REWARD_[A-Z]+[^\r\n]*|OFFICER_DROP[^\r\n]*|INDOOR_CACHE[^\r\n]*|PARADROP[^\r\n]*)"


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


def show(p0, n=60):
    for l in G.since(p0, PAT)[:n]:
        log("   ", l[:330])


def cmd(c, **kv):
    return G.cmd(c, timeout=80, **kv)


def die_and_respawn():
    p3 = len(R.read_log())
    R.step(["dog 0", "wait 40", "kill", "wait 60"], timeout=30)
    R.step(["set rw_cmd awaitrespawn"], timeout=10)
    t0 = time.time()
    while time.time() - t0 < 90 and not re.search(r"SM state respawned", R.read_log()[p3:]):
        time.sleep(4)
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 100"], timeout=30)
    R.step(["dog 1", "wait 100"], timeout=30)
    time.sleep(2)
    return p3


def throw_real():
    R.step(['use "Signal Smoke Grenade"', "wait 1500", "+attackprimary", "wait 1000", "-attackprimary", "wait 500"], timeout=40)


try:
    rundir, notes = G.boot("sm_" + LABEL, MAP, extra=[])
    hh = G.since(G.cmd("here"), r"RW here \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) ang=\( [-\d.]+ ([-\d.]+)")
    X, Y, Z, YAW = [float(v) for v in hh[-1]]
    cmd("purge")
    time.sleep(9)
    if FLOW in ("smoke", "unused", "binoc"):
        cmd("tpfwd", yaw=YAW, x=700, z=0)
        time.sleep(1)

    if FLOW == "smoke":
        p0 = len(R.read_log())
        log("=== 1. give the smoke")
        cmd("grantsmoke")
        log("=== 2. throw it (real input)")
        throw_real()
        time.sleep(1.2)
        cmd("state")
        log("   (in flight / just thrown)")
        time.sleep(7)
        cmd("state")
        sim = not re.search(r"PARADROP signal smoke", R.read_log()[p0:])
        if sim:
            log("   real throw never reached the landing hook -> simulated throw")
            cmd("grantsmoke")
            cmd("sim_throw")
            time.sleep(8)
            cmd("state")
        else:
            log("   real throw reached the landing hook (PARADROP signal smoke)")
        log("=== 3. die, respawn, inventory")
        p3 = die_and_respawn()
        cmd("state")
        log("=== 4. weapon / loadout refresh")
        cmd("refresh")
        log("=== 5. let the guardian run another 6 s")
        time.sleep(6)
        cmd("state")
        show(p0)

    if FLOW == "unused":
        p0 = len(R.read_log())
        log("=== 1. give the smoke, do NOT throw it")
        cmd("grantsmoke")
        log("=== 2. die with it, respawn")
        die_and_respawn()
        cmd("state")
        show(p0)
        log("=== 3. walk over the drop")
        cmd("walkoversmoke")
        time.sleep(1)
        cmd("state")
        log("=== 4. refresh, wait, state")
        cmd("refresh")
        time.sleep(4)
        cmd("state")
        show(p0)

    if FLOW == "binoc":
        p0 = len(R.read_log())
        log("=== 1. grant the binoculars")
        R.step(["set coop_binoc_skyCheck 0"], timeout=10)
        cmd("grantbinoc")
        log("=== 2. the one strike")
        cmd("firebinoc", yaw=YAW)
        time.sleep(4)
        cmd("state")
        log("=== 3. die, respawn")
        die_and_respawn()
        cmd("state")
        log("=== 4. refresh, wait")
        cmd("refresh")
        time.sleep(5)
        cmd("state")
        show(p0)

    if FLOW == "cache":
        p0 = len(R.read_log())
        cmd("purge")
        time.sleep(5)
        cmd("idrop")
        cmd("lookcache")
        time.sleep(1.5)
        G.frames("cacheshot", 24, ms=150)
        R.step(["set rw_cmd walkcache"], timeout=10)
        G.frames("cacheshot_b", 10, ms=150)
        cmd("retest")
        show(p0, 40)

    if FLOW == "drops":
        p0 = len(R.read_log())
        cmd("players")
        cmd("purge")
        log("=== 10 officer drops (outdoor map %s)" % MAP)
        R.step(["set rw_n 10"], timeout=10)
        cmd("odrops", n=10)
        time.sleep(3)
        log("=== 1 officer drop on an indoor map name (m2l2c)")
        cmd("idrop")
        time.sleep(3)
        cmd("lookcache")
        time.sleep(1.5)
        os.makedirs(os.path.join(G.HERE, "frames"), exist_ok=True)
        G.frames("cachegif", 26, ms=150)
        log("=== cache: every player uses it, then again")
        for slot in (0, 7):   # slot 0 = the real player, 7 = a stand-in second client slot (one real player in the harness)
            for rep in (1, 2):
                cmd("cacheuse", n=1, slot=slot)
                time.sleep(0.5)
        show(p0, 200)
    log("script errors:", len(G.errors()), G.errors()[:4])
finally:
    G.end(rundir, notes)

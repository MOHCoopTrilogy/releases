"""ox_m2l1.py <label> [stages] - m2l1 (Secret Documents of the Kriegsmarine) radio-set objective on the private harness client.
stages (comma list, default all): spawn,r1,r2,r3
r1 = gunfire on the first set, r2 = planted charge on the second, r3 = gunfire on the third (done).  One player."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
STAGES = (sys.argv[2] if len(sys.argv) > 2 else "spawn,r1,r2,r3").split(",")
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
T0 = time.time()


def log(*a):
    s = "%5.0fs " % (time.time() - T0) + " ".join(str(x) for x in a)
    G.log(LABEL, *a)
    OUT.write(s + "\n")
    OUT.flush()


def tp(x, y, z, yaw=0, pitch=0):
    G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)


def aim(x, y, z):
    G.cmd("aim", x=x, y=y, z=z)


def use(ms=350):
    R.step(["+use", "wait %d" % ms, "-use", "wait 200"], timeout=30)


def shoot(ms=1500):
    R.step(["+attackprimary", "wait %d" % ms, "-attackprimary", "wait 200"], timeout=30)


def wait_objx(pat, timeout):
    return R.wait_log(r"\^~\^~\^ OBJX " + pat, timeout, 0)


def panel(name):
    R.step(["pushmenu coop_objectives", "wait 700", "screenshotJPEG %s" % name, "wait 300", "popmenu 0", "wait 300"], timeout=30)


rundir = notes = None
try:
    rundir, notes = G.boot("ox_" + LABEL, "m2l1", extra=["set coop_counterDebug 1", "set coop_objxCallGap 25"])
    log("booted; players joined", notes.get("joined"))
    G.cmd("god")
    G.cmd("kit")
    G.cmd("here")
    if "spawn" in STAGES:
        ok = wait_objx(r"ACTIVE radios", 30)
        log("ACTIVE radios seen:", bool(ok))
        G.frames("spawn", 14, 250)
        panel("ox_panel_radios")
        p0 = G.cmd("state")
        for l in G.since(p0, r"\^~\^~\^ (OX STATE[^\r\n]*)"):
            log("  ", l)
    if "r1" in STAGES:
        log("-- set 1: gunfire")
        tp(-1682, -3448, 638, 180, 0)
        aim(-1762, -3447.8, 645)
        G.frames("r1_view", 4, 250)
        R.step(["screenshotJPEG ox_r1_before", "wait 150"], timeout=20)
        shoot(1800)
        G.cmd("radiohp")
        ok = wait_objx(r"RADIO down 1", 6)
        if not ok:
            log("gunfire did not bring set 1 down (see radiohp); using the driver damage call instead")
            G.cmd("dmgradio", k=1)
            ok = wait_objx(r"RADIO down 1", 10)
        log("set 1 down:", bool(ok))
        G.frames("r1_boom", 10, 200)
    if "r2" in STAGES:
        log("-- set 2: planted charge")
        tp(740, 3292, 538, 0, 0)
        aim(819.9, 3291.9, 545)
        G.frames("r2_view", 4, 250)
        use()
        G.frames("r2_plant", 14, 500)
        ok = wait_objx(r"RADIO down 2", 25)
        log("set 2 down:", bool(ok))
        G.frames("r2_boom", 8, 200)
        # the garrison call (a set stands, another has fallen)
        ok = wait_objx(r"RADIO call #1", 60)
        log("garrison call seen:", bool(ok))
        G.cmd("enemies")
    if "r3" in STAGES:
        log("-- set 3: gunfire")
        tp(3780.5, 6936, 26, 90, 0)
        aim(3780.5, 7016, 36)
        G.frames("r3_view", 4, 250)
        shoot(1800)
        G.cmd("radiohp")
        ok = wait_objx(r"DONE radios", 6)
        if not ok:
            log("gunfire did not bring set 3 down (see radiohp); using the driver damage call instead")
            G.cmd("dmgradio", k=3)
            ok = wait_objx(r"DONE radios", 12)
        log("DONE radios seen:", bool(ok))
        G.frames("r3_done", 10, 250)
        panel("ox_panel_radios_done")
    G.cmd("state")
    ox = G.objx_lines()
    log("---- OBJX log ----")
    for l in ox:
        if "tick" in l:
            continue
        log(l[:230])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

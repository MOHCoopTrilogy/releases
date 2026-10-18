"""sl_run2.py <label> <map> - calm proof WITHOUT the alarm + off-axis swing GIF.
A German spots the player (notarget off); the German is then removed and the player moved out of sight; detect/hunt logged every 2 s for 30 s."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
def lights(tag):
    p0 = G.cmd("lights")
    for l in G.since(p0, r"\^~\^~\^ SL light=[1-2][^\r\n]*"):
        log("  [%s] %s" % (tag, re.sub(r"pos=\([^)]*\) ", "", l[10:300])))
try:
    rundir, notes = G.boot("sl_" + LABEL, MAP, extra=["set coop_alarm 0"])
    G.cmd("purge", timeout=60); time.sleep(3)
    p0 = G.cmd("tpl", n=1)
    m = G.since(p0, r"SL tpl light=1 r=\d+ a=(\d+)")
    a = int(m[-1]) if m else 120
    face = (a + 180) % 360
    off = (face + 100) % 360
    G.R.step(["notarget 1"], timeout=20)
    log("== A: undetected sweep (off-axis camera yaw %d), then a German spots the player" % off)
    G.cmd("look", yaw=off, pitch=22)
    G.frames(LABEL + "_a", 30, ms=150)
    G.R.step(["notarget 0"], timeout=20)
    G.cmd("look", yaw=face, pitch=0)
    pg = G.cmd("german", yaw=face)
    G.cmd("look", yaw=off, pitch=22)
    G.frames(LABEL + "_b", 60, ms=150)
    lights("spotted")
    for l in G.since(pg, r"\^~\^~\^ SPOTLIGHT[^\r\n]*"):
        log("   ", l[:200])
    log("== B: German removed, player far out of sight, alarm untouched; detect/hunt every 2 s for 30 s")
    G.cmd("purge", timeout=60)
    G.cmd("tpfar")
    t0 = time.time()
    p2 = len(R.read_log())
    while time.time() - t0 < 32:
        lights("calm +%2ds" % int(time.time() - t0)); time.sleep(1.2)
    for l in G.since(p2, r"\^~\^~\^ SPOTLIGHT[^\r\n]*"):
        log("   ", l[:200])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

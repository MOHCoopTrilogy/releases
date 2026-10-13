"""p3_grease.py <label> <map> <x> <y> <z> <yaw> [chance=100] - the M3 grease gun on the squad's SMG man: call a stick
with coop_paraGreaseChance <chance>, then look at member 2 from close, several times over a minute (idle, moving,
firing at the map's own enemies), and print what weapon the engine says he holds."""
import os, re, sys, time
import p3lib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
X, Y, Z, YAW = [float(v) for v in sys.argv[3:7]]
OPT = dict(a.split("=", 1) for a in sys.argv[7:])
rundir = notes = None
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


try:
    rundir, notes = G.boot("p3_" + LABEL, MAP, extra=["set coop_paraGreaseChance %s" % OPT.get("chance", "100")],
                           files=["models/weapons/coop_greasegun_ai.tik"])
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)
    p0 = G.cmd("call", x=X, y=Y, z=Z, yaw=YAW, tag="pin")
    m = R.wait_log(r"PSQ t=[\d.]+ (grease k=2[^\r\n]*)", 90, p0)
    log(m.group(1) if m else "NO grease line (the roll did not give it, or the give thread did not run)")
    R.wait_log(r"PSQ t=[\d.]+ brain start", 60, p0)
    for k in range(int(OPT.get("looks", 7))):
        ang = (25, 335, 90, 25, 270, 40, 320)[k % 7]
        pc = G.cmd("camk", tag=2, n=(64, 64, 70, 58, 70, 90, 64)[k % 7], yaw=ang)
        time.sleep(0.5)
        R.step(["fov 55", "wait 300", "screenshotJPEG %s_look_%d" % (LABEL, k), "wait 150", "fov 80", "wait 100"], timeout=30)
        log("look", k, G.since(pc, r"P3 camk[^\r\n]*"))
        if k == 3:
            G.frames(LABEL + "_seq", 40, 150)
        time.sleep(float(OPT.get("gap", 6)))
    p1 = G.cmd("sq")
    for l in G.since(p1, r"P3 SQ[^\r\n]*"):
        log("   ", l[:200])
    log("script errors:", G.errors()[:6])
    for l in G.psq(p0):
        if "grease" in l or "lz plan" in l or "rescue" in l:
            log("   ", l[:200])
    t = R.read_log()[p0:]
    for l in sorted(set(re.findall(r"[^\r\n]*(?:greasegun|Thompson \(M3)[^\r\n]*", t)))[:8]:
        log("   LOG", l[-160:])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    G.end(rundir, notes)

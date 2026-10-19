"""av_m3para.py <label> - church hold + paradrop only; when the .30 cal team sets up, the camera stands behind the gun (PSQ line) for the screenshot."""
import math, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL = sys.argv[1]
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, "m3l3", extra=["set coop_paraDebug 1", "set g_ai 1"])
    p0 = len(R.read_log())
    G.cmd("m3church")
    mm = R.wait_log(r"\^~\^~\^ PSQ t=\S+ mg setup k=\d+ mode=\w+ gun=\( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \) yaw=(-?[\d.]+)", 420, p0)
    if mm:
        gx, gy, gz, gyaw = float(mm.group(1)), float(mm.group(2)), float(mm.group(3)), float(mm.group(4))
        bx, by = gx - 230 * math.cos(math.radians(gyaw)), gy - 230 * math.sin(math.radians(gyaw))
        G.cmd("pin", x="%.0f" % bx, y="%.0f" % by, z="%.0f" % (gz - 30), lx="%.0f" % gx, ly="%.0f" % gy, lz="%.0f" % (gz + 5))
        time.sleep(0.5)
        G.still(LABEL + "_30cal_team")
        G.cmd("gun30", x="%.0f" % gx, y="%.0f" % gy, z="%.0f" % gz)
        # side-on camera on the gun, then a German squad from 700 u ahead so the team has to fire
        sx, sy = gx + 90 * math.sin(math.radians(gyaw)), gy - 90 * math.cos(math.radians(gyaw))
        G.cmd("pin", x="%.0f" % (sx - 60 * math.cos(math.radians(gyaw))), y="%.0f" % (sy - 60 * math.sin(math.radians(gyaw))), z="%.0f" % (gz - 20), lx="%.0f" % gx, ly="%.0f" % gy, lz="%.0f" % (gz + 10))
        fx, fy = gx + 700 * math.cos(math.radians(gyaw)), gy + 700 * math.sin(math.radians(gyaw))
        G.cmd("m3foe", lx="%.0f" % fx, ly="%.0f" % fy, lz="%.0f" % gz)
        G.frames(LABEL + "_30cal_a", 8, 250)
        R.wait_log(r"\^~\^~\^ PSQ t=\S+ mg (suppress|track|fire)", 60, p0)
        G.frames(LABEL + "_30cal_fire", 14, 200)
        log("30cal team camera at", bx, by, "gun", gx, gy, gz, "yaw", gyaw)
    else:
        log("no .30 cal team formed this run")
    for l in re.findall(r"\^~\^~\^ PSQ t=\S+ (?:mg|lz plan|land)[^\r\n]*", R.read_log()[p0:]):
        log("   ", l[:230])
    log("script errors:", len(G.errors()), G.errors()[:4])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-600:])
finally:
    G.end(rundir, notes)

"""av_run.py <label> <map> <kind> <cx> <cy> <cz> <lx> <ly> <lz> - one alarm-vehicle proof run on <map>.
camera pinned at (cx,cy,cz) looking at (lx,ly,lz); kind = halftrack | truck.
Truck: ARRIVING -> drive frames -> ARRIVED/unloading frames -> WITHDRAW log.  Halftrack: ... FIRING frames -> rocket -> DESTROYED frames."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL, MAP, KIND = sys.argv[1], sys.argv[2], sys.argv[3]
cx, cy, cz, lx, ly, lz = sys.argv[4:10]
WD = os.environ.get("AVWD", "40")
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
def wl(pat, to, p0):
    m = R.wait_log(pat, to, p0)
    log("   wait", pat[:40], "->", "ok" if m else "TIMEOUT")
    return m
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, MAP, extra=["set coop_alarmVeh 1", "set coop_alarmVehDebug 1", "set coop_alarmVehDelay 3",
                           "set coop_alarmVehMinTime 0", "set coop_alarmVehWithdraw " + WD, "set coop_alarmVehLoop 0"] + (["set coop_alarmVehHp " + os.environ["AVHP"]] if os.environ.get("AVHP") else []) + [x for x in os.environ.get("AVEXTRA", "").split(";") if x])
    p0 = len(R.read_log())
    G.cmd("here")
    if cx != "none":
        G.cmd("pin", x=cx, y=cy, z=cz, lx=lx, ly=ly, lz=lz)
    time.sleep(1.5)
    G.cmd("pcount")
    G.still(LABEL + "_pre")
    G.cmd("trace")
    G.cmd("arm")
    if wl(r"\^~\^~\^ ALMVEH ARRIVING", 90, p0):
        if os.environ.get("AVFOLLOW"):
            a = os.environ["AVFOLLOW"].split(",")
            G.cmd("follow", x=a[0], y=a[1], z=a[2])
        if os.environ.get("AVCAM2"):
            a = os.environ["AVCAM2"].split(",")      # the squad walks to a vantage point AFTER the hidden spawn
            G.cmd("pin", x=a[0], y=a[1], z=a[2], lx=a[3], ly=a[4], lz=a[5])
        G.frames(LABEL + "_in", 26, 220)
    if wl(r"\^~\^~\^ ALMVEH ARRIVED", 120, p0):
        G.cmd("covercheck")
        G.frames(LABEL + "_arr", 14, 220)
    if KIND == "truck":
        time.sleep(4)
        G.frames(LABEL + "_dis", 16, 250)
        G.cmd("men")
        if wl(r"\^~\^~\^ ALMVEH WITHDRAW", 120, p0):
            G.frames(LABEL + "_wd", 14, 400)
        wl(r"\^~\^~\^ ALMVEH withdrawn", 120, p0)
    else:
        if wl(r"\^~\^~\^ ALMVEH FIRING", 40, p0):
            G.frames(LABEL + "_fire", 16, 220)
        G.cmd("hp", x="300")
        G.cmd("bullet")
        G.cmd("grenade")
        G.cmd("rocket")
        G.frames(LABEL + "_boom", 22, 250)
        wl(r"\^~\^~\^ ALMVEH DESTROYED", 30, p0)
    for l in re.findall(r"\^~\^~\^ (?:ALMVEH|AVT|ATSUPPLY|ATSUPPLY|ALARM)[^\r\n]*", R.read_log()[p0:]):
        if "AVT t=" in l:
            continue
        log("   ", l[:230])
    log("script errors:", len(G.errors()), G.errors()[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)

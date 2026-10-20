"""av_m3run.py <label> [minutes] - one full m3l3 sequence: officer reward check, church hold (45 s), paradrop, then the Nebelwerfer fight with the
new nests / defenders / waves / halftracks / rocket crate. Logs ^~^~^ NEB / PARADROP / OFFICER_DROP / PSQ lines, screenshots at the church (para squad)
and a frame burst around the guard halftracks."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import avlib as A
G = A.G; R = A.R
LABEL = sys.argv[1]
MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 9
OUT = open(os.path.join(A.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
rundir = notes = None
try:
    rundir, notes = G.boot("av_" + LABEL, "m3l3", extra=["set coop_reinfDebug 1", "set coop_mortarDebug 1", "set coop_alarmVehDebug 1", "set coop_alarmVehIgnoreMission 1", "set coop_paraDebug 1"] + ([x for x in os.environ.get("AVEXTRA", "").split(";") if x]))
    p0 = len(R.read_log())
    G.cmd("here")
    G.cmd("trace")
    G.cmd("offdrop")
    time.sleep(8)
    G.cmd("m3church")
    t0 = time.time()
    while time.time() - t0 < 240:
        G.cmd("m3status")
        txt = R.read_log()[p0:]
        if re.search(r"AVT m3 chDone=1", txt):
            break
        time.sleep(6)
    log("church hold finished after %d s" % (time.time() - t0))
    # the paratroopers' .30 cal team sets up: camera behind the gun (position + facing from the PSQ line)
    mm = R.wait_log(r"\^~\^~\^ PSQ t=\S+ mg setup k=\d+ mode=\w+ gun=\( (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) \) yaw=(-?[\d.]+)", 90, p0)
    if mm:
        gx, gy, gz, gyaw = float(mm.group(1)), float(mm.group(2)), float(mm.group(3)), float(mm.group(4))
        import math
        bx, by = gx - 260 * math.cos(math.radians(gyaw)), gy - 260 * math.sin(math.radians(gyaw))
        G.cmd("pin", x="%.0f" % bx, y="%.0f" % by, z="%.0f" % (gz + 40), lx="%.0f" % gx, ly="%.0f" % gy, lz="%.0f" % (gz + 20))
        G.still(LABEL + "_30cal_team")
        G.frames(LABEL + "_30cal", 8, 250)
        log("30cal team camera at", bx, by, "gun", gx, gy, gz, "yaw", gyaw)
    time.sleep(25)                      # the paradrop lands
    G.cmd("find30")
    time.sleep(2)
    G.still(LABEL + "_church_para")
    G.frames(LABEL + "_para", 6, 400)
    # screenshot from the rocket crate toward the halftrack stop (shows the cover between)
    G.cmd("pin", x="1601", y="-2420", z="-250", lx="-2837", ly="-3005", lz="-120")
    time.sleep(1.5)
    G.still(LABEL + "_crate_to_stop")
    G.cmd("m3nebel")
    t1 = time.time()
    # 1. the guard halftracks arrive: chase camera
    if R.wait_log(r"\^~\^~\^ ALMVEH ARRIVING halftrack", 150, p0):
        if os.environ.get("AVGUN"):
            a = os.environ["AVGUN"].split(",")
            G.cmd("gunfollow", x=a[0], y=a[1], z=a[2])
            for i in range(4):
                G.cmd("gunrel"); G.frames(LABEL + "_gdrive", 3, 300)
        else:
            G.cmd("follow", x="450", y="250", z="160")
        if os.environ.get("AVSWEEPD"):
            G.cmd("god")
            time.sleep(8)
            for k, cfg in enumerate(os.environ["AVSWEEPD"].split(";")):
                a = cfg.split(",")
                G.cmd("gunfollow", x=a[0], y=a[1], z=a[2], yaw=os.environ.get("AVLEVEL","0"))
                time.sleep(1.2)
                G.still("%s_dr%d_%s" % (LABEL, k, "_".join(a)))
        G.frames(LABEL + "_ht_in", 26 if not os.environ.get("AVGUN") else 6, 250)
    R.wait_log(r"\^~\^~\^ ALMVEH ARRIVED halftrack", 120, p0)
    if os.environ.get("AVGUN"):
        if os.environ.get("AVSWEEP"):
            G.cmd("god")
            for k, cfg in enumerate(os.environ["AVSWEEP"].split(";")):
                a = cfg.split(",")
                G.cmd("gunfollow", x=a[0], y=a[1], z=a[2], yaw=os.environ.get("AVLEVEL","0"))
                time.sleep(1.5)
                G.still("%s_sw%d_%s" % (LABEL, k, "_".join(a)))
        G.cmd("gunrel"); G.frames(LABEL + "_gpark", 6, 400); G.cmd("gunrel")
        raise SystemExit
    G.frames(LABEL + "_ht_park", 10, 300)
    # 2. the squad moves up to Nebelwerfer 1: the nests see a player, the halftrack covers him
    G.cmd("nofollow")
    G.cmd("m3to", x="-1560", y="-4850", z="-120")
    G.cmd("pin", x="-1560", y="-4850", z="-120", lx="-2433", ly="-5096", lz="-40")
    time.sleep(40)
    G.frames(LABEL + "_fight", 18, 300)
    # 3. a charge goes on Nebelwerfer 1: defend wave, blast, counter-push
    G.cmd("aiaudit")
    G.cmd("m3plant", x="1")
    time.sleep(3)
    G.cmd("aiaudit")
    G.frames(LABEL + "_plant", 24, 300)
    time.sleep(45)
    G.frames(LABEL + "_counter", 18, 300)
    while time.time() - t1 < MIN * 60:
        time.sleep(15)
        G.cmd("m3status")
    for l in re.findall(r"\^~\^~\^ (?:NEB|PARADROP|OFFICER_DROP|AVT officer|AVT m3|ALMVEH|MZ|CHDEFEND|PSQ)[^\r\n]*", R.read_log()[p0:]):
        if "AVT t=" in l:
            continue
        log("   ", l[:240])
    log("script errors:", len(G.errors()), G.errors()[:8])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-700:])
finally:
    G.end(rundir, notes)

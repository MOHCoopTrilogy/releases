"""mz_run.py <label> <map> [part...] - parts: ger (German crew + fire mission + frames), floor, para (Allied team).
One boot, one fair-queue turn. MZ_DIST = player distance from the officer (default 1500). Logs: logs/run_<label>.txt."""
import os, re, sys, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mzlib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
PARTS = sys.argv[3:] or ["ger", "floor", "para"]
DIST = os.environ.get("MZ_DIST", "1500")
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
rundir = notes = None
MZ = r"\^~\^~\^ MZ[^\r\n]*"
NUM = r"([-\d.]+) ([-\d.]+) ([-\d.]+)"


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


def here():
    hh = G.since(G.cmd("here"), r"MZ here \( " + NUM + r" \) ang=\( [-\d.]+ ([-\d.]+)")
    return [float(v) for v in hh[-1]]


def look_at(x, y, fx, fy, pitch=6):
    yaw = math.degrees(math.atan2(fy - y, fx - x))
    G.cmd("look", yaw=round(yaw, 1), pitch=pitch)


T0 = time.time()
try:
    rundir, notes = G.boot("mz_" + LABEL, MAP)
    log("booted in", int(time.time() - T0), "s")
    X, Y, Z, YAW = here()
    log("player", X, Y, Z, YAW)
    G.cmd("purge", timeout=90)
    if "ger" in PARTS:
        R.step(["notarget 0", "wait 100"], timeout=30)
        G.cmd("god")
        p0 = len(R.read_log())
        ok = False
        for attempt in range(5):
            G.cmd("toofficer", yaw=YAW + 90 * attempt, n=DIST, timeout=90)
            X, Y, Z, _ = here()
            log("player at", X, Y, Z, "attempt", attempt)
            G.cmd("ger", timeout=90)
            if "ger result=1" in R.read_log()[p0:]:
                ok = True
                break
            time.sleep(4)
        m = waitfor(r"MZ t=[\d.]+ site_g pick=\( " + NUM + r" \)", 5, p0)
        log("site:", m.group(0) if m else None)
        if ok and m:
            sx, sy = float(m.group(1)), float(m.group(2))
            look_at(X, Y, sx, sy)
            G.frames("ger_walk", 4, 500)
            m3 = waitfor(r"MZ t=[\d.]+ tube up at=\( " + NUM + r" \)", 120, p0)
            log("tube up:", m3.group(0) if m3 else None)
            if m3:
                tx, ty, tz = float(m3.group(1)), float(m3.group(2)), float(m3.group(3))
                # one German who SEES the player (rule A): halfway between the tube and the player
                pn = len(R.read_log())
                G.cmd("nearsite", x=tx, y=ty, z=tz)
                mm = waitfor(r"MZ nearsite done=\d player=\( " + NUM + r" \)", 10, pn)
                X, Y, Z = [float(v) for v in mm.groups()] if mm else here()[:3]
                log("player moved to", X, Y, Z, "(900-1200u from the tube, clear line)")
                look_at(X, Y, tx, ty)
                dd = math.hypot(tx - X, ty - Y) or 1.0
                G.cmd("observer", x=X + (tx - X) * 300 / dd, y=Y + (ty - Y) * 300 / dd, z=Z)
                G.frames("ger_tube", 8, 300)
            m4 = waitfor(r"MZ t=[\d.]+ round \d+ rule=\w+ at=", 70, p0)
            log("first round:", m4.group(0) if m4 else None)
            if m4:
                am = re.search(r"at=\( " + NUM + r" \)", m4.group(0) + R.read_log()[p0:][m4.end():m4.end() + 200])
                if am:
                    ax, ay, az = float(am.group(1)), float(am.group(2)), float(am.group(3))
                    dd = math.hypot(ax - X, ay - Y)
                    if dd < 80:
                        look_at(X, Y, tx, ty, -4)       # the shell is landing on him: look along the shell's line (toward the tube), a little up
                    else:
                        pitch = max(4.0, min(18.0, math.degrees(math.atan2(Z + 60 - az, max(dd, 1.0)))))
                        look_at(X, Y, ax, ay, pitch)    # the camera on the impact point
                G.frames("ger_fire", 36, 90)
            G.cmd("killobs")        # the observer's gunfire would otherwise kill the held player between shells
            time.sleep(3)
            G.cmd("tube")
            for l in G.since(p0, MZ)[:70]:
                log("   ", l[:230])
        G.cmd("state")
    if "floor" in PARTS and "ger" in PARTS:
        # FULL-HEALTH FLOOR PROOF: player at full health (750) is hit by big shells (700 amount) over and over; he must never go below
        # max_health / 4 = 187
        R.step(["set coop_mortarDmg 700", "set coop_mortarCap 700", "set coop_mortarGap 3", "dog 0", "wait 200"], timeout=30)
        G.cmd("hp", n=750)
        p1 = len(R.read_log())
        t0 = time.time()
        hits = 0
        while time.time() - t0 < 60 and hits < 3:
            time.sleep(2)
            hits = len(re.findall(r"MZ t=[\d.]+ (?:hit|floor hold) ", R.read_log()[p1:]))
        G.frames("ger_floor", 24, 130)
        G.cmd("here")
        low = []
        for l in G.since(p1, MZ):
            log("   ", l[:230])
        for mm in re.finditer(r"MZ t=[\d.]+ hit d=\d+ dmg=\d+ before=(\d+) hp=(\d+) floor=(\d+)", R.read_log()[p1:]):
            low.append((int(mm.group(1)), int(mm.group(2)), int(mm.group(3))))
        log("FLOOR RESULTS (before, after, floor):", low, "hits+holds:", hits, "min after:", min([x[1] for x in low]) if low else None)
        R.step(["set coop_mortarDmg 110", "set coop_mortarCap 140", "set coop_mortarGap 20"], timeout=30)
        G.cmd("god")
        G.cmd("killobs")
        G.cmd("unhold")
    if "para" in PARTS:
        G.cmd("purge", timeout=90)
        G.cmd("unhold")
        G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
        p0 = len(R.read_log())
        G.cmd("para", yaw=YAW, timeout=60)
        m = waitfor(r"MZ t=[\d.]+ allied site=", 150, p0)
        log("allied site:", m.group(0) if m else None)
        m = waitfor(r"MZ t=[\d.]+ allied tube up", 90, p0)
        log("allied tube up:", m.group(0) if m else None)
        # the Germans the spotter can use: 700-900u from the allied tube
        tm = re.search(r"allied site=\( " + NUM + r" \)", R.read_log()[p0:])
        if tm:
            G.cmd("targets2", n=4, x=tm.group(1), y=tm.group(2), z=tm.group(3), yaw=YAW)
            # the camera: the player 260u from the allied tube with a clear line, looking at it (the team and the launch)
            pn = len(R.read_log())
            # behind the tube as seen from the targets: tube and crew in front of the camera, the Germans beyond
            tg = re.search(r"MZ target2 1 at \( " + NUM + r" \)", R.read_log()[p0:])
            back = YAW
            if tg:
                back = math.degrees(math.atan2(float(tm.group(2)) - float(tg.group(2)), float(tm.group(1)) - float(tg.group(1))))
            G.cmd("god")
            G.cmd("nearsite", x=tm.group(1), y=tm.group(2), z=tm.group(3), n=300, yaw=round(back, 1))
            mm = waitfor(r"MZ nearsite done=\d player=\( " + NUM + r" \)", 10, pn)
            if mm:
                px, py, pz = [float(v) for v in mm.groups()]
                look_at(px, py, float(tm.group(1)), float(tm.group(2)), 6)
        G.frames("al_deploy", 12, 300)
        m = waitfor(r"MZ t=[\d.]+ allied round \d+", 60, p0)
        log("allied round:", m.group(0) if m else None)
        if m:
            G.frames("al_fire", 40, 110)
        time.sleep(4)
        G.cmd("state")
        G.cmd("tube")
        for l in G.since(p0, r"\^~\^~\^ (?:MZ|PSQ)[^\r\n]*")[:60]:
            log("   ", l[:230])
    errs = G.errors()
    log("script errors:", len(errs), errs[:8])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
    log("total", int(time.time() - T0), "s")

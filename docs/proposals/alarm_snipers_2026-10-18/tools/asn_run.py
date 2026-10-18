"""asn_run.py <label:map> [<label:map> ...] [shots] - ONE harness turn (harness_turn.py wait/release), up to 3 maps, ~4 min each.
Per map: boot in the private harness, let the alarm module arm, stand the player in front of switch 1, pull the alarm with 1 simulated
player (want 2), kill those, pull again with 3 (want 4); log ASNIPER lines + per-sniper floor facts; with `shots` also engine screenshots
(close view of the first sniper(s) at the spot, view from the player's place) and a frame dump for a GIF."""
import os, re, sys, time, shutil, glob, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asnlib as C
G = C.G; R = C.R
ARGS = [a for a in sys.argv[1:] if a != "shots"]
SHOTS = "shots" in sys.argv[1:]
NSHOT = 3
MEDIA = os.path.join(os.path.dirname(C.HERE), "media")
TURN = "C:/mohaa-coop-dev/docs/tools/harness_turn.py"
T_START = time.time()
OUT = None
LABEL = ""


def log(*a):
    G.log(LABEL, *a)
    if OUT:
        OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


def grab(tag):
    G.still("asn_%s_%s" % (LABEL, tag))
    time.sleep(0.6)
    fs = sorted(glob.glob(os.path.join(R.SHOTS, "asn_%s_%s*" % (LABEL, tag))), key=os.path.getmtime)
    if fs:
        shutil.copy(fs[-1], os.path.join(MEDIA, "%s_%s.jpg" % (LABEL, tag)))


def run_one(label, mp):
    global OUT, LABEL
    LABEL = label
    OUT = open(os.path.join(C.HERE, "logs", "run_%s.txt" % label), "w")
    rundir = notes = None
    try:
        for attempt in range(6):
            try:
                own = C.configure_slot()
                if own is None:
                    log("no free harness folder, waiting 30 s")
                    time.sleep(30)
                    raise RuntimeError("no free folder")
                log("using", own)
                rundir, notes = G.boot("asn_" + label, mp, extra=["set coop_alarm 1", "set coop_alarmDebug 1", "set coop_alarmSnipers 1",
                                       "set coop_alarmMaxPulls 2", "set coop_alarmSnipersSim 1", "set cg_fov 80"])
                break
            except Exception as e:
                log("boot attempt", attempt, "failed:", repr(e)[:160])
                try:
                    G.end(rundir, notes)
                except Exception:
                    pass
                rundir = notes = None
                if attempt == 5:
                    raise
        p0 = len(R.read_log())
        for k in range(20):
            G.cmd("status")
            m = re.findall(r"ASN STATUS [^\r\n]*? sw=(\d+)", R.read_log()[p0:])
            if m and int(m[-1]) > 0:
                break
            time.sleep(2)
        for k in range(4):
            G.cmd("autoplace")
            w = re.findall(r"ASN WHERE [^\r\n]*off=(\d+)", R.read_log()[p0:])
            log("teleport check off=", w[-1] if w else "?")
            if w and int(w[-1]) < 100:
                break
            time.sleep(8)
        shot_done = False
        G.cmd("load")
        for phase, sim in ((1, 1), (2, 3)):
            R.step(["set coop_alarmSnipersSim %d" % sim], timeout=20)
            log("PHASE", phase, "sim players", sim)
            G.cmd("pull")
            for k in range(14):
                time.sleep(5)
                G.cmd("status")
                if re.search(r"ASNIPER pull %d done" % phase, R.read_log()[p0:]):
                    break
            time.sleep(3)
            G.cmd("list")
            n = int(re.findall(r"ASN LIST alive=(\d+)", R.read_log()[p0:])[-1])
            if SHOTS and n >= 1 and not shot_done:
                shot_done = True
                for k in range(1, min(n, NSHOT) + 1):
                    G.cmd("cam", k=k, mode="close")
                    time.sleep(1.2)
                    R.step(["set cg_fov 80", "wait 60"], timeout=20)
                    grab("s%d_close" % k)
                    G.cmd("cam", k=k, mode="from")
                    R.step(["set cg_fov 28", "wait 60"], timeout=20)
                    time.sleep(1.2)
                    grab("s%d_player" % k)
                    if k == 1:
                        G.frames("asnf_%s" % label, 30, 200)
                    R.step(["set cg_fov 80"], timeout=20)
                G.cmd("autoplace")
            if phase == 1:
                G.cmd("killsn")
                time.sleep(4)
        for l in re.findall(r"\^~\^~\^ (?:ASNIPER[^\r\n]*|ASN [^\r\n]*|ALARM LIVE[^\r\n]*|ALARM armed[^\r\n]*|ALMGATE[^\r\n]*)", R.read_log()[p0:]):
            log("   ", l[:300])
        log("script errors:", len(G.errors()), G.errors()[:4])
    except Exception as e:
        import traceback
        log("FAILED", repr(e), traceback.format_exc()[-900:])
    finally:
        G.end(rundir, notes)
        # frame dump -> media
        for f in glob.glob(os.path.join(R.RUNS, "asn_" + label, "asnf_*")):
            shutil.copy(f, os.path.join(MEDIA, os.path.basename(f)))


subprocess.run([sys.executable, TURN, "wait", "alarmsnipers"], check=True)
T_START = time.time()
try:
    for a in ARGS:
        if time.time() - T_START > 0 and time.time() - T_START > 11 * 60 and a != ARGS[0]:
            print("turn budget used, skipping", a)
            continue
        lab, mp = a.split(":")
        run_one(lab, mp)
finally:
    subprocess.run([sys.executable, TURN, "release", "alarmsnipers"])

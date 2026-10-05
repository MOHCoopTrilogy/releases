"""planes_ingame.py - in-engine captures for the aircraft call-ins (queue slot "planes").

    python planes_ingame.py <label> <before|after> [--maps m2l1,m6l2b,m4l3] [--events para,binoc,stuka]
                            [--cgame cgame_live] [--game game_live] [--fps 60] [--secs 0] [--wait]

Private client G:\\mohaa-planes = byte copies of the LIVE exe/DLLs (G:\\mohaa-gl2, read only) + test DLLs in \\dlls.
Registered in docs/tools/harness_guard.py (owner "planes"). Basepath = the GOG tree read only (it carries the live
mod pk3s). Fresh home, no qkey/saves. The overlay pk3 goes in the home maintt:
  before = devprobe.scr hook + ac_probe.scr only (so the LIVE flight code runs)
  after  = the same + the working-tree aircraft files (FILES below)
Launch only via harness_window.launch_background (DISPLAY2, unfocused, muted), net_ip 127.0.0.1, com_maxfps 60
(the user allowed ONE capped 2-minute run at 125: --fps 125 --secs 120). Captures: engine screenshotJPEG via rcon.
"""
import argparse, json, os, re, shutil, socket, sys, time, zipfile

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LIVECODE = os.path.join(GOG, "maintt", "zzzzzz_co-op_hzm_mod_code.pk3")
CLIENT = r"G:\mohaa-planes"
EXE = os.path.join(CLIENT, "openmohaa_planes.exe")
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
RUNS = os.path.join(CLIENT, "runs")
SCRATCH = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad"
SLOTFILE = os.path.join(SCRATCH, "test_slot.txt")
OVERLAY = "zzzzzzzzzzzzz_planes_test.pk3"
OWNER = "planes"
PORT = 12733
RCONPW = "pl4nesPw"
MAGIC = b"\xff\xff\xff\xff"
FILES = ["coop_mod/aircraft.scr", "coop_mod/aircraft_envelope.scr", "coop_mod/paradrop.scr", "coop_mod/officer.scr",
         "coop_mod/precache.scr", "ubersound/coop_aircraft.scr"]
SITES = {  # from tools/sites.py: target T, camera C, camera yaw
    "m2l1": ((2960, 336, 496), (2392, 1288, 624), -59),
    "m6l2b": ((3200, -3656, 128), (2176, -3200, 320), -24),
    "m4l3": ((-3024, -848, 56), (-1704, -1060, 48), 170),
    "m5l1a": ((1040, -2088, 56), (-308, -1528, 112), -22),
    "e1l1": ((448, 480, 744), (688, -680, 744), 101),
    "m3l3": ((1792, -1408, -288), (2336, -2392, -192), 118),
    "e1l4": ((-3520, 4048, -432), (-3480, 2928, -288), 92),
}
CH = {"c": None, "proc": None}
SHOT_EVERY = 7
RX_CAM = re.compile(r"\^~\^~\^ ACCAM ev=(\w+) dur=(\d+)")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def read_log():
    try:
        return open(LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def rcon(cmd, timeout=1.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(MAGIC + b"\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
        try:
            d, _ = s.recvfrom(16384)
            return d[4:].decode("latin-1")
        except socket.timeout:
            return ""
    finally:
        s.close()


def guard():
    c, p = CH["c"], CH["proc"]
    if c is not None and c.watcher.violations:
        raise RuntimeError("window policy violation: %s" % (c.watcher.violations[:3],))
    if p is not None and p.poll() is not None:
        raise RuntimeError("client exited")


def wait_rx(rx, timeout, start=0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        guard()
        m = rx.search(read_log(), start)
        if m:
            return m
        time.sleep(0.5)
    return None


_N = {"n": 0}


def step(lines, timeout=120):
    _N["n"] += 1
    mk = "^~^~^ ACSTEP %d" % _N["n"]
    with open(os.path.join(MAINTT, "acstep.cfg"), "w", newline="\n") as f:
        f.write("\n".join(lines + ["echo %s" % mk]) + "\n")
    start = len(read_log())
    rcon("exec acstep.cfg")
    if not wait_rx(re.compile(re.escape(mk) + r"\b"), timeout, max(0, start - 10)):
        raise RuntimeError("step %d timed out" % _N["n"])


def build_overlay(mode):
    out = os.path.join(SCRATCH, "planes", OVERLAY)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    live = zipfile.ZipFile(LIVECODE)
    dp = live.read("coop_mod/devprobe.scr").decode("latin-1")
    k = dp.index("main:{")
    k = dp.index("\n", dp.index("//====", k)) + 1
    dp = dp[:k] + '\tif( getcvar( "coop_acTest" ) == "1" ){ thread coop_mod/ac_probe.scr::run }\t//TEST OVERLAY ONLY\n' + dp[k:]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/devprobe.scr", dp.encode("latin-1"))
        z.write(os.path.join(HERE, "over", "coop_mod", "ac_probe.scr"), "coop_mod/ac_probe.scr")
        if mode == "after":
            for f in FILES:
                p = os.path.join(MOD, f.replace("/", os.sep))
                if os.path.exists(p):
                    z.write(p, f)
    return out


def seed(overlay, cgame, game):
    os.makedirs(MAINTT, exist_ok=True)
    for d in ("maintt", "main", "mainta"):
        dd = os.path.join(HOME, d)
        if os.path.isdir(dd):
            for fn in os.listdir(dd):
                if fn.lower().endswith(".pid"):
                    os.remove(os.path.join(dd, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    shutil.copyfile(overlay, os.path.join(MAINTT, OVERLAY))
    shutil.copyfile(os.path.join(CLIENT, "dlls", cgame + ".dll"), os.path.join(CLIENT, "cgame.dll"))
    shutil.copyfile(os.path.join(CLIENT, "dlls", game + ".dll"), os.path.join(CLIENT, "game.dll"))
    os.makedirs(SHOTS, exist_ok=True)
    for fn in os.listdir(SHOTS):
        os.remove(os.path.join(SHOTS, fn))


def launch(mapname, fps, extra, w=960, h=540):
    t, c, yaw = SITES[mapname]
    on = ["set rconPassword %s" % RCONPW, "set sv_maxbots 0", "set sv_numbots 0", "set cg_drawviewmodel 0",
          "set coop_weatherPin 0", "set coop_dev 1", "set coop_acTest 1", "set cg_draw2d 0", "set ui_hud 0",
          "set ui_crosshair 0", "set coop_dbno 0", "set com_maxfps %d" % fps, "set coop_tinnitus 0",
          "set coop_dizzy 0", "set sv_fps 40", "set r_ppSuppression 0", "set r_ppMotionBlur 0",
          "set r_ppLowHealth 0", "set cg_dofStrength 0", "set r_ppDizzy 0",
          "set coop_acTx %d" % t[0], "set coop_acTy %d" % t[1], "set coop_acTz %d" % t[2],
          "set coop_acCx %d" % c[0], "set coop_acCy %d" % c[1], "set coop_acCz %d" % c[2],
          "set coop_acYaw %d" % yaw] + list(extra)
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(w)), ("r_customheight", str(h)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_port", str(PORT)), ("net_ip", "127.0.0.1")]
    args = [EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+set", "g_gametype", "2", "+exec", "ac_on.cfg", "+set", "ui_dmmap", mapname,
             "+exec", "coop_mod/start_server.cfg"]
    args, late = hw.apply_policy(args, width=w, height=h)
    on += late
    with open(os.path.join(MAINTT, "ac_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(on) + "\n")
    assert sum(1 for x in args if x.startswith("+")) <= 31
    cl = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    CH["c"], CH["proc"] = cl, cl.proc
    hg.set_slot_pid(OWNER, cl.proc.pid)


def join():
    start = len(read_log())
    for _ in range(4):
        step(["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "set g_teamswitchdelay 0",
              "join_team allies", "wait 20", "popmenu 0", "wait 40", "popmenu 0", "wait 20",
              "+attackprimary", "wait 10", "-attackprimary"])
        if wait_rx(re.compile(r"has joined the (Allies|Axis|Free)"), 20, start):
            return True
    return False


def session(label, mapname, mode, events, cgame, game, fps, secs, extra):
    rundir = os.path.join(RUNS, label, mapname)
    os.makedirs(rundir, exist_ok=True)
    notes = {"map": mapname, "mode": mode, "events": events, "cgame": cgame, "game": game, "fps": fps}
    seed(build_overlay(mode), cgame, game)
    t0 = time.time()
    try:
        launch(mapname, fps, ["set coop_acEvents %s" % events] + extra)
        if not wait_rx(re.compile(r"Detected Coop for"), 600):
            raise RuntimeError("map never became ready")
        if not wait_rx(re.compile(r"\^~\^~\^ ACP armed"), 120):
            raise RuntimeError("probe did not start")
        time.sleep(4)
        notes["joined"] = join()
        seen = 0
        tend = time.time() + (secs if secs else 400)
        while time.time() < tend:
            guard()
            L = read_log()
            if re.search(r"\^~\^~\^ ACP (done|abort)", L):
                break
            m = RX_CAM.search(L, seen)
            if m:
                seen = m.end()
                ev, dur = m.group(1), int(m.group(2))
                # frame-chained shots: one screenshotJPEG every SHOT_EVERY frames (~8/s at 60 fps), run by the
                # engine's own command buffer, so the cadence does not depend on rcon round trips
                n = int(dur * 60 / SHOT_EVERY)
                lines = []
                for i in range(n):
                    lines += ["screenshotJPEG ac_%s_%s_%03d" % (mapname, ev, i)] + ["wait 1"] * SHOT_EVERY
                    if ev == "down" and i == int(13 * 60 / SHOT_EVERY):
                        lines.append("+attackprimary")
                    if ev == "down" and i == int(33 * 60 / SHOT_EVERY):
                        lines.append("-attackprimary")
                with open(os.path.join(MAINTT, "acshots.cfg"), "w", newline=chr(10)) as f:
                    f.write(chr(10).join(lines + ["-attackprimary"]) + chr(10))
                rcon("exec acshots.cfg")
                te = time.time() + dur + 4
                while time.time() < te and time.time() < tend:
                    guard()
                    time.sleep(0.5)
            time.sleep(0.3)
        L = read_log()
        notes["air"] = re.findall(r"\^~\^~\^ AIR[^\r\n]*", L)[:400]
        notes["script_errors"] = re.findall(r"[^\r\n]*Script Error[^\r\n]*", L)[:40]
        notes["ours"] = re.findall(r"[^\r\n]*(?:aircraft|paradrop|officer|ac_probe)\.scr[^\r\n]*", L)[:40]
    finally:
        p = CH["proc"]
        if p is not None and p.poll() is None:
            try:
                rcon("quit")
                p.wait(40)
            except Exception:
                pass
        c = CH["c"]
        if c is not None:
            c.close()
            r = c.report()
            notes["window"] = {"clean": r["clean"], "violations": r["violations"]}
        CH["c"] = CH["proc"] = None
        k = 0
        if os.path.isdir(SHOTS):
            for fn in sorted(os.listdir(SHOTS)):
                shutil.move(os.path.join(SHOTS, fn), os.path.join(rundir, fn))
                k += 1
        notes["shots"] = k
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(rundir, "qconsole.log"))
        notes["minutes"] = round((time.time() - t0) / 60.0, 1)
        json.dump(notes, open(os.path.join(rundir, "notes.json"), "w"), indent=1, default=str)
        log("[%s/%s] done: %d shots, %.1f min" % (label, mapname, k, notes["minutes"]))
    return notes


def slot_value():
    try:
        return open(SLOTFILE).read().strip()
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label"); ap.add_argument("mode", choices=["before", "after"])
    ap.add_argument("--maps", default="m2l1,m6l2b,m4l3"); ap.add_argument("--events", default="para,binoc,stuka")
    ap.add_argument("--cgame", default="cgame_live"); ap.add_argument("--game", default="game_live")
    ap.add_argument("--fps", type=int, default=60); ap.add_argument("--secs", type=int, default=0)
    ap.add_argument("--extra", default=""); ap.add_argument("--wait", action="store_true")
    a = ap.parse_args()
    if a.fps > 60 and not (a.secs and a.secs <= 120):
        raise SystemExit("fps > 60 is only allowed for ONE capped run (--secs <= 120)")
    if a.wait:
        log("waiting for slot ==", OWNER)
        while slot_value() != OWNER:
            time.sleep(10)
        log("slot is ours")
    try:
        if hg.user_game_running():
            raise SystemExit("the user's game is running - not launching")
        hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=45)
        out = {}
        try:
            for m in a.maps.split(","):
                try:
                    out[m] = session(a.label, m, a.mode, a.events, a.cgame, a.game, a.fps, a.secs,
                                     [x for x in a.extra.split(";") if x])
                except Exception as e:
                    log("[%s] FAILED: %r" % (m, e))
                    out[m] = {"error": repr(e)}
            os.makedirs(os.path.join(RUNS, a.label), exist_ok=True)
            json.dump(out, open(os.path.join(RUNS, a.label, "summary.json"), "w"), indent=1, default=str)
            print("RUNDIR", os.path.join(RUNS, a.label))
        finally:
            hg.release_slot(OWNER)
    finally:
        if a.wait and slot_value() == OWNER:
            open(SLOTFILE, "w").write("free")
            log("test slot released: free")


if __name__ == "__main__":
    main()

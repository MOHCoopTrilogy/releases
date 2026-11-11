"""run_rof.py - real rates of fire in game, on the private client G:\\mohaa-recoil (recoil-eng dlls; never the live install).

    python run_rof.py player <tag> [--off]          coop m5l1a: each gun from the Armory, a 3 s aimed burst; the server's own
                                                     round trace (^~^~^ RECOILSHOT) gives the measured rpm
    python run_rof.py ai <tag> <map> [--off] [--min N]   coop <map> with the map tester's patrol (coop_maptest 2, the player
                                                     at 999999 hp is walked into the fights): every AI round (^~^~^ AISHOT,
                                                     coop_recoilDebug 2) -> rpm inside bursts and burst lengths per gun
--off = coop_realRof 0 (the before). Overlay = the recoil mod branch's recoil_pattern.txt + weapon_rof.txt, plus the
fg42fix anims_shared.txt (the FG 42 crashes v1.10.73 without it - bug-10899).
Launched only through docs/tools/harness_window (guard on, muted, no grab, no pad); the 1080p screen while the user plays.
"""
import os, re, shutil, socket, sys, time, zipfile
from collections import defaultdict
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-recoil"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
RUNS = r"H:\hzm_work\recoil\runs"
MODWT = r"C:\hzm-recoil\mod"
FIXTREE = r"C:\hzm-fg42fix\mod"
OVERLAY = "zzzzzzzzzzzzzzzzzzzzz_recoil_test.pk3"
PORT, RCONPW = 12417, "rcltest"
W, H = 1120, 630
# gun: (Armory cfg, pickup / use name)
GUNS = [("thompson", "24_s1", "Thompson"), ("mp40", "26_s1", "MP40"), ("ppsh", "29_s1", "PPSH SMG"), ("sten", "28_s1", "Sten Mark II"),
        ("greasegun", "31_s1", "M3 Grease Gun"), ("bar", "36_s1", "BAR"), ("stg44", "37_s1", "StG 44"), ("fg42", "39_s1", "FG 42"),
        ("bren", "82_s1", "Bren"), ("mg42", "43_s1", "MG42"), ("m1919", "42_s1", "M1919 30cal")]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def rcon(cmd):
    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    so.settimeout(1.5)
    try:
        so.sendto(b"\xff\xff\xff\xff\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
        try:
            so.recvfrom(16384)
        except socket.timeout:
            pass
    finally:
        so.close()


def size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def text(start=0):
    try:
        with open(LOG, "rb") as f:
            f.seek(start)
            return f.read().decode("latin-1")
    except OSError:
        return ""


def wait_for(rx, timeout, c, start=0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if c.watcher.violations or c.proc.poll() is not None:
            return False
        if re.search(rx, text(start)):
            return True
        time.sleep(0.5)
    return False


def overlay():
    with zipfile.ZipFile(os.path.join(MAINTT, OVERLAY), "w", zipfile.ZIP_STORED) as z:
        z.write(os.path.join(MODWT, "coop_mod", "recoil_pattern.txt"), "coop_mod/recoil_pattern.txt")
        z.write(os.path.join(MODWT, "coop_mod", "weapon_rof.txt"), "coop_mod/weapon_rof.txt")
        z.write(os.path.join(FIXTREE, "models", "player", "base", "anims_shared.txt"), "models/player/base/anims_shared.txt")


def player_steps():
    steps = []
    for g, cfg, name in GUNS:
        steps.append(["echo ^~^~^ ROFGUN %s" % g])
        steps.append((["exec ui/loadout/w%s.cfg" % cfg], r"Picked Up %s" % re.escape(name)))
        steps.append(['use "%s"' % name, "wait 2500", "centerview", "wait 300", "+button13", "wait 1000",
                      "echo ^~^~^ ROFBURST %s" % g, "+attack", "wait 3000", "-attack", "echo ^~^~^ ROFEND %s" % g, "wait 300",
                      "-button13", "wait 300", "reload", "wait 3500"])
    return steps


def analyse_player(t):
    res, cur, times = {}, None, []
    for l in t.splitlines():
        m = re.search(r"\^~\^~\^ ROFBURST (\S+)", l)
        if m:
            cur, times = m.group(1), []
            continue
        if cur and re.search(r"\^~\^~\^ ROFEND", l):
            if len(times) > 2:
                res[cur] = (len(times), 60.0 * (len(times) - 1) / (times[-1] - times[0]))
            cur = None
            continue
        m = re.search(r"RECOILSHOT t=([\d.]+)", l)
        if cur and m:
            ts = float(m.group(1))
            if not times or ts > times[-1] + 1e-4:     # pellets of one shot share a time
                times.append(ts)
    return res


def analyse_ai(t):
    per = defaultdict(list)        # (ent, weapon) -> times
    for m in re.finditer(r"AISHOT t=([\d.]+) ent=(\d+) weap=(.+?)\s*$", t, re.M):
        per[(m.group(2), m.group(3))].append(float(m.group(1)))
    byw = defaultdict(lambda: {"rpm": [], "burst": []})
    for (ent, w), ts in per.items():
        ts.sort()
        burst = [ts[0]]
        for a in ts[1:] + [1e9]:
            if a - burst[-1] > 0.4:
                if len(burst) >= 2:
                    byw[w]["rpm"].append(60.0 * (len(burst) - 1) / (burst[-1] - burst[0]))
                byw[w]["burst"].append(len(burst))
                burst = [a]
            else:
                burst.append(a)
    out = {}
    for w, d in byw.items():
        r = sorted(d["rpm"])
        b = sorted(d["burst"])
        out[w] = dict(bursts=len(b), rpm_med=(r[len(r) // 2] if r else None), burst_med=b[len(b) // 2],
                      burst_max=max(b), rounds=sum(b))
    return out


def main():
    mode, tag = sys.argv[1], sys.argv[2]
    off = "--off" in sys.argv
    if hg.user_game_running():
        raise SystemExit("user game running - not launching")
    if hg.user_game_running_raw() and hw.test_display()["rect"][2] - hw.test_display()["rect"][0] != 1920:
        raise SystemExit("the user is playing: the 1080p screen only (HZM_TEST_RES=1920x1080)")
    overlay()
    shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    mp = sys.argv[3] if mode == "ai" else "m5l1a"
    minutes = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 4.0
    boot = ["set developer 1", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0",
            "set s_musicvolume 0", "set s_ambientvolume 0", "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0",
            "seta coop_woundMuffleVol 0", "set rconpassword %s" % RCONPW, "set coop_lockLoadout 0", "set coop_dev 1",
            "set coop_recoilDebug %d" % (1 if mode == "player" else 2), "set coop_realRof %d" % (0 if off else 1)]
    if mode == "ai":
        boot += ["seta coop_maptest 2", "seta coop_maptest_dwell %d" % int(minutes * 60 + 60), "seta coop_maptest_waypoints 20",
                 "seta coop_maptest_dwell_wpt 6", "set coop_dbno 0", "seta g_scriptcheck 0"]
    boot += ["set g_gametype 2", "set ui_dmmap %s" % mp, "ui_startdmmap 2"]
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
            "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
            "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60",
            "+set", "net_enabled", "1", "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(PORT), "+exec", "rof_run.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H)
    open(os.path.join(MAINTT, "rof_run.cfg"), "w", newline="\n").write("\n".join(list(late) + boot) + "\n")
    join = ["+attack", "wait 300", "-attack", "wait 4000", "+attack", "wait 300", "-attack", "wait 5000",
            "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0", "seta coop_woundMuffleVol 0", "set s_volume 0"]
    steps = [join] + (player_steps() if mode == "player" else [])
    hg.acquire_slot("recoil", args[0], HOME, [PORT], minutes=40)
    out = os.path.join(RUNS, tag)
    try:
        c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
        hg.set_slot_pid("recoil", c.pid)
        try:
            if not wait_for(r"SELFTEST (OK|FAIL)|coop: loaded \d+ recoil pattern", 180, c):
                log("no map load")
            time.sleep(20)
            for i, st in enumerate(steps):
                rx = None
                if isinstance(st, tuple):
                    st, rx = st
                n0 = size()
                mk = "^~^~^ ROFSTEP %d" % i
                open(os.path.join(MAINTT, "rofstep.cfg"), "w", newline="\n").write("\n".join(st + ["echo " + mk]) + "\n")
                rcon("exec rofstep.cfg")
                if not wait_for(re.escape(mk) + r"(?![0-9])", 120, c, n0):
                    log("step", i, "timed out")
                    break
                if rx:
                    t0 = time.time()
                    while time.time() - t0 < 90 and not re.search(rx, text(n0)):
                        time.sleep(0.5)
                    time.sleep(2)
            if mode == "ai":
                t0 = time.time()
                while time.time() - t0 < minutes * 60 and c.proc.poll() is None and not c.watcher.violations:
                    time.sleep(5)
            rcon("quit")
            time.sleep(3)
        finally:
            if c.proc.poll() is None:
                c.proc.kill()
            c.close()
    finally:
        hg.release_slot("recoil")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    shutil.copy2(LOG, os.path.join(out, "qconsole.log"))
    t = text()
    if mode == "player":
        for g, (n, rpm) in sorted(analyse_player(t).items()):
            log("PLAYER %-10s rounds=%3d rpm=%.0f" % (g, n, rpm))
    else:
        for w, d in sorted(analyse_ai(t).items(), key=lambda x: -x[1]["rounds"]):
            log("AI %-24s rounds=%4d bursts=%3d rpm_med=%s burst_med=%d burst_max=%d" % (
                w, d["rounds"], d["bursts"], "%.0f" % d["rpm_med"] if d["rpm_med"] else "-", d["burst_med"], d["burst_max"]))
    log("crash lines:", len(re.findall(r"infinite state loop|Server crashed", t)))


if __name__ == "__main__":
    main()

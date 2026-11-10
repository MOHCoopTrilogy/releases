"""run_recoil.py - in-game recoil pattern runs on the private client G:\\mohaa-recoil (never the live install).

    python run_recoil.py scout <map>                       coord + 8 screenshots round the spawn (find a wall)
    python run_recoil.py fire <map> <tag> <yaw> <pitch> [--guns a,b] [--off]   per gun: 4 bursts (aimed / hip / crouched /
                                                           prone) at a fixed stand, decal screenshots, ^~^~^ RECOILSHOT /
                                                           RECOILPAT lines to the log. --off = coop_recoilPattern 0 (A/B)

Launched ONLY through docs/tools/harness_window.launch_background (guard on, never activated, below-normal priority,
muted, no mouse grab, in_gamepad 0 / in_joystick 0). Coop spawns un-mute (bug-10805): coop_tinnitusBaseVol 0,
coop_tinnitusMuffle 0, coop_woundMuffleVol 0 after autoexec. Overlay pk3 = the recoil mod branch's recoil_pattern.txt.
The client's cgame.dll / game.dll are this branch's build (copied beside the exe).
"""
import os, re, shutil, socket, sys, time, zipfile
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-recoil"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
RUNS = r"H:\hzm_work\recoil\runs"
MODWT = r"C:\hzm-recoil\mod"
OVERLAY = "zzzzzzzzzzzzzzzzzzzzz_recoil_test.pk3"
PORT, RCONPW = 12417, "rcltest"       # loopback only (net_ip 127.0.0.1); a test value for this private client
W, H = 1120, 630                      # one ultrawide slot (DISPLAY_QUEUE.md)

# gun: (tik stem, use name, burst ms, rounds note)
GUNS = {
    "thompson": ("thompsonsmg", "Thompson", 2600), "mp40": ("mp40", "MP40", 2500), "ppsh": ("ppsh_smg", "PPSH SMG", 2600),
    "sten": ("sten", "Sten Mark II", 2200), "bar": ("bar", "BAR", 2200), "fg42": ("fg42", "FG 42", 1750),
    "stg44": ("mp44", "StG 44", 3200), "bren": ("coop_bren", "Bren", 3300), "mg42": ("mg42portable", "MG42", 2800),
    "garand": ("m1_garand", "M1 Garand", 1500), "kar98": ("kar98", "Mauser KAR 98K", 5200),
    "carbine": ("carbine", "M1 Carbine", 1500), "colt": ("colt45", "Colt 45", 1000),
}
# the Armory route (cheats are forced off on a coop server, so `give` is refused): ui/loadout/w<id>_s<slot>.cfg
ARMORY = {"thompson": "24_s1", "mp40": "26_s1", "ppsh": "29_s1", "sten": "28_s1", "bar": "36_s1", "fg42": "39_s1",
          "stg44": "37_s1", "bren": "82_s1", "mg42": "43_s1", "garand": "01_s1", "kar98": "03_s1", "carbine": "02_s1",
          "colt": "48_s3"}
SEMI = {"garand": 5, "kar98": 5, "carbine": 5, "colt": 5}   # rounds in the string, one press each


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


def log_size():
    try:
        return os.path.getsize(LOG)
    except OSError:
        return 0


def log_text(start=0):
    """the log from byte <start> on (a MemoryError while other clients filled the RAM: never re-read the whole log)"""
    try:
        with open(LOG, "rb") as f:
            f.seek(max(0, start))
            return f.read().decode("latin-1")
    except OSError:
        return ""


def wait_for(rx, timeout, c, start=None):
    t0 = time.time()
    if start is None:
        start = max(0, log_size() - 65536)
    while time.time() - t0 < timeout:
        if c.watcher.violations or c.proc.poll() is not None:
            return False
        if re.search(rx, log_text(start)):
            return True
        time.sleep(0.5)
    return False


class Cfg:
    def __init__(self):
        self.lines = []

    def cmd(self, c, ms=0):
        self.lines.append(c)
        if ms:
            self.lines.append("wait %d" % ms)


def overlay():
    with zipfile.ZipFile(os.path.join(MAINTT, OVERLAY), "w", zipfile.ZIP_STORED) as z:
        z.write(os.path.join(MODWT, "coop_mod", "recoil_pattern.txt"), "coop_mod/recoil_pattern.txt")


def burst(s, gun, ms, semi, shot=None):
    if semi:
        for _ in range(semi):
            s.cmd("+attack", 60)
            s.cmd("-attack", 700 if gun != "kar98" else 1300)
    else:
        if shot:   # a frame mid-burst: the sights must still sit on the crosshair line while the aim climbs
            s.cmd("+attack", ms // 2)
            s.cmd("screenshotJPEG " + shot, ms - ms // 2)
        else:
            s.cmd("+attack", ms)
        s.cmd("-attack", 0)


def fire_steps(guns, yaw, pitch):
    steps = []
    for gi_, g in enumerate(guns):
        stem, name, ms = GUNS[g]
        semi = SEMI.get(g)
        s = Cfg()
        steps.append(["echo ^~^~^ RCLGUN %s" % g])
        s.cmd("coop_recoilPatOn")
        s.cmd("coop_recoilPattern")
        s.cmd("coop_gunHeft")
        steps.append((["exec ui/loadout/w%s.cfg" % ARMORY[g]], r"Picked Up %s" % re.escape(name)))
        s.cmd('use "%s"' % name, 2500)
        # four groups side by side on the wall, 7 deg apart; each burst starts at the same pitch from a fixed stand
        groups = [("aimed", 10.5), ("hip", 3.5), ("crouch", -3.5), ("prone", -10.5)]   # + = left
        prev = [-yaw]          # <yaw> = the stand's initial turn LEFT from the spawn view (deg), done once per gun
        for kind, dy in groups:
            if kind == "prone":
                s.cmd("set coop_prone 1")
                s.cmd("+movedown", 2200)
            elif kind == "crouch":
                s.cmd("set coop_prone 0")
                s.cmd("+movedown", 900)
            # `face` does not move a coop client's view (measured 2026-11-10): turn with the keys, 140 deg/s (cl_yawspeed)
            turn = int(round((dy - prev[0]) / 140.0 * 1000.0))
            prev[0] = dy
            if turn:
                s.cmd("+left" if turn > 0 else "+right", abs(turn))
                s.cmd("-left" if turn > 0 else "-right", 700)
            if kind != "hip":
                s.cmd("+button13", 1100)
            s.cmd("set coop_recoilProbe 1")
            s.cmd("echo ^~^~^ RCLBURST %s %s %.2f %.2f" % (g, kind, pitch, yaw + dy), 50)
            burst(s, g, ms, semi, ("rcl_%s_%s_mid" % (g, kind)) if kind == "aimed" else None)
            s.cmd("screenshotJPEG rcl_%s_%s_climb" % (g, kind), 200)
            s.cmd("wait 1", 1500)
            s.cmd("echo ^~^~^ RCLEND %s %s" % (g, kind))
            s.cmd("set coop_recoilProbe 0")
            s.cmd("-button13", 300)
            if kind in ("prone", "crouch"):
                s.cmd("-movedown", 1200 if kind == "prone" else 600)
                s.cmd("set coop_prone 1")
            if kind == "prone":
                s.cmd("+moveup", 300)
                s.cmd("-moveup", 1500)
            s.cmd("reload", 3500)
        mid = int(round((0.0 - prev[0]) / 140.0 * 1000.0))     # face the middle of the four groups for the wall still
        s.cmd("+left" if mid > 0 else "+right", abs(mid))
        s.cmd("-left" if mid > 0 else "-right", 1200)
        s.cmd("screenshotJPEG rcl_%s_wall" % g, 600)
        back = int(round(yaw / 140.0 * 1000.0))                 # back to the spawn view for the next gun
        if back:
            s.cmd("+right" if back > 0 else "+left", abs(back))
            s.cmd("-right" if back > 0 else "-left", 1200)
        steps.append(s.lines)
    return steps


def scout_steps():
    s = Cfg()
    s.cmd("coord", 300)
    for y in range(0, 360, 45):
        s.cmd("face 0 %d 0" % y, 900)
        s.cmd("screenshotJPEG scout_%03d" % y, 400)
    return [s.lines]


def main():
    mode, mp = sys.argv[1], sys.argv[2]
    tag = sys.argv[3] if mode == "fire" else "scout_" + mp
    off = "--off" in sys.argv
    if hg.user_game_running():
        raise SystemExit("user game running - not launching")
    if hg.user_game_running_raw() and hw.test_display()["rect"][2] - hw.test_display()["rect"][0] != 1920:
        raise SystemExit("the user is playing: the 1080p screen only (HZM_TEST_RES=1920x1080)")
    overlay()
    os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
    shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    shutil.rmtree(SHOTS, ignore_errors=True)
    os.makedirs(SHOTS, exist_ok=True)
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
            "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
            "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "cheats", "1",
            "+set", "net_enabled", "1", "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(PORT),
            "+exec", "rcl_run.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H)
    if "cheats" not in " ".join(args):
        args = args[:-2] + ["+set", "cheats", "1"] + args[-2:]
    lines = list(late) + [
        "set developer 1", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0", "set in_nograb 1",
        "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0",
        "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0", "seta coop_woundMuffleVol 0",
        "set g_gametype 2", "set coop_dev 1", "set coop_lockLoadout 0", "set coop_recoilDebug 1",
        "set coop_recoilProbe 0", "set coop_lookDebug 0", "set coop_recoilPattern %d" % (0 if off else 1),
        "set rconpassword %s" % RCONPW, "set ui_dmmap %s" % mp, "ui_startdmmap 2"]
    open(os.path.join(MAINTT, "rcl_run.cfg"), "w", newline="\n").write("\n".join(lines) + "\n")
    if mode == "scout":
        steps = scout_steps()
    else:
        yaw, pitch = float(sys.argv[4]), float(sys.argv[5])
        guns = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--guns=")), "thompson,mp40").split(",")
        steps = fire_steps(guns, yaw, pitch)
    hg.acquire_slot("recoil", args[0], HOME, [PORT], minutes=40)
    out = os.path.join(RUNS, tag)
    try:
        c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
        hg.set_slot_pid("recoil", c.pid)
        try:
            if not wait_for(r"SELFTEST (OK|FAIL)|coop: loaded \d+ recoil pattern", 180, c, 0):
                log("no map load")
            time.sleep(20)
            # the per-spawn un-mute (bug-10805) runs on spawn: set the volumes again now the player is in
            rcon("set s_volume 0; seta coop_tinnitusBaseVol 0; seta coop_tinnitusMuffle 0; seta coop_woundMuffleVol 0")
            time.sleep(1)
            # the mission card: "press FIRE to join the battle"
            steps = [["+attack", "wait 300", "-attack", "wait 4000", "+attack", "wait 300", "-attack", "wait 6000",
                      "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0", "seta coop_woundMuffleVol 0",
                      "set s_volume 0"]] + steps
            for i, st in enumerate(steps):
                rx = None
                if isinstance(st, tuple):
                    st, rx = st
                n0 = log_size()
                mk = "^~^~^ RCLSTEP %d" % i
                open(os.path.join(MAINTT, "rclstep.cfg"), "w", newline="\n").write("\n".join(st + ["echo " + mk]) + "\n")
                rcon("exec rclstep.cfg")
                if not wait_for(re.escape(mk) + r"(?![0-9])", 240, c, n0):
                    log("step", i, "timed out")
                    break
                if rx:
                    t0 = time.time()
                    while time.time() - t0 < 90 and not re.search(rx, log_text(n0)):
                        time.sleep(0.5)
                    log("step", i, "pickup", bool(re.search(rx, log_text(n0))))
                    time.sleep(2)
                if c.watcher.violations:
                    log("VIOLATION", c.watcher.violations[:3])
                    break
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
    if os.path.isdir(SHOTS):
        for f in os.listdir(SHOTS):
            shutil.copy2(os.path.join(SHOTS, f), out)
    shutil.copy2(LOG, os.path.join(out, "qconsole.log"))
    log("done", out, len(os.listdir(out)))


if __name__ == "__main__":
    main()

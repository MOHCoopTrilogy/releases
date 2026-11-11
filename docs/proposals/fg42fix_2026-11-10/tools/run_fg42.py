"""run_fg42.py - bug-10899 in game: every FG 42 variant equipped, fired and reloaded (several times, so the stress reload
variants _s / _m come up too) in SP, MP and co-op, on the private client G:\\mohaa-fg42fix (release v1.10.73 exe and
dlls copied from the live install; never the live install itself).

    python run_fg42.py <sp|mp|coop> <tag> [--nofix]

--nofix leaves the fix overlay out (the control: the crash should reproduce). Pass = no 'infinite state loop',
no "Can't find player animation" for an FG 42 reload, and every variant's reload logged.
Launched only through docs/tools/harness_window (guard on, muted, no grab, no pad); the 1080p screen while the user plays.
"""
import os, re, shutil, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-fg42fix"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
RUNS = r"H:\hzm_work\fg42fix\runs"
FIX = "zzzzzzzzzzzzzzzzzzzzzz_fg42fix_test.pk3"
PORT, RCONPW = 12419, "fgtest"
W, H = 1120, 630
VARIANTS = [("fg42", "FG 42"), ("fg42_gold", "FG 42 (Gold)"), ("fg42_camo_winter", "FG 42 (Winter)"),
            ("fg42_fs2_dak", "FG 42 (Afrika Korps)"), ("coop_fg42_irons", "FG 42 Irons"),
            ("coop_fg42_irons_bloody", "FG 42 Irons (Bloody)"), ("coop_fg42_irons_fs2_telo", "FG 42 Irons (Telo)")]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def rcon(cmd):
    import socket
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


def gun_steps(tik, name, give):
    s = ["echo ^~^~^ FGGUN %s" % tik]
    if give:
        s += ["give models/weapons/%s.tik" % tik, "wait 800", "give models/weapons/%s.tik" % tik, "wait 800"]
    s += ['use "%s"' % name, "wait 2500", "screenshotJPEG fg_%s_inhand" % tik, "wait 300", "coop_gunHeft"]
    for k in range(4):          # four reloads: the stress variants (COOP_RELOAD_VAR 1 / 2) come up at random
        s += ["+attack", "wait 700", "-attack", "wait 300", "reload", "wait 900", "screenshotJPEG fg_%s_reload%d" % (tik, k),
              "wait 3300", "echo ^~^~^ FGRELOAD %s %d" % (tik, k)]
    s += ["echo ^~^~^ FGDONE %s" % tik]
    return s


def main():
    mode, tag = sys.argv[1], sys.argv[2]
    nofix = "--nofix" in sys.argv
    if hg.user_game_running():
        raise SystemExit("user game running - not launching")
    if hg.user_game_running_raw() and hw.test_display()["rect"][2] - hw.test_display()["rect"][0] != 1920:
        raise SystemExit("the user is playing: the 1080p screen only (HZM_TEST_RES=1920x1080)")
    fixp = os.path.join(MAINTT, FIX)
    off = fixp + ".off"
    if nofix and os.path.exists(fixp):
        os.replace(fixp, off)
    if not nofix and os.path.exists(off):
        os.replace(off, fixp)
    shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    boot = ["set developer 1", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0",
            "set s_musicvolume 0", "set s_ambientvolume 0", "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0",
            "seta coop_woundMuffleVol 0", "set rconpassword %s" % RCONPW, "set coop_lockLoadout 0", "set coop_dev 1"]
    if mode == "sp":
        boot += ["set g_gametype 0", "devmap m1l1"]
    elif mode == "mp":
        boot += ["set g_gametype 1", "set sv_maxclients 8", "devmap dm/mohdm1"]
    else:
        boot += ["set g_gametype 2", "set ui_dmmap m5l1a", "ui_startdmmap 2"]
    open(os.path.join(MAINTT, "fg_run.cfg"), "w", newline="\n").write("\n".join(boot) + "\n")
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
            "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
            "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "cheats", "1",
            "+set", "net_enabled", "1", "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(PORT), "+exec", "fg_run.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H)
    if late:
        open(os.path.join(MAINTT, "fg_run.cfg"), "w", newline="\n").write("\n".join(list(late) + boot) + "\n")
    steps = [["+attack", "wait 300", "-attack", "wait 4000", "+attack", "wait 300", "-attack", "wait 5000",
              "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0", "seta coop_woundMuffleVol 0", "set s_volume 0"]]
    if mode == "coop":
        for wid, (tik, name) in (("39_s1", VARIANTS[0]), ("79_s1", VARIANTS[4])):
            steps.append((["exec ui/loadout/w%s.cfg" % wid], r"Picked Up %s" % re.escape(name)))
            steps.append(gun_steps(tik, name, give=False))
    else:
        for tik, name in VARIANTS:
            steps.append(gun_steps(tik, name, give=True))
    hg.acquire_slot("fg42fix", args[0], HOME, [PORT], minutes=40)
    out = os.path.join(RUNS, tag)
    try:
        c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
        hg.set_slot_pid("fg42fix", c.pid)
        try:
            if not wait_for(r"SELFTEST (OK|FAIL)|Server: |------- Game Initialization", 180, c):
                log("no map load")
            time.sleep(25)
            for i, st in enumerate(steps):
                rx = None
                if isinstance(st, tuple):
                    st, rx = st
                n0 = size()
                mk = "^~^~^ FGSTEP %d" % i
                open(os.path.join(MAINTT, "fgstep.cfg"), "w", newline="\n").write("\n".join(st + ["echo " + mk]) + "\n")
                rcon("exec fgstep.cfg")
                if not wait_for(re.escape(mk) + r"(?![0-9])", 120, c, n0):
                    log("step", i, "timed out (server down?)")
                    break
                if rx:
                    t0 = time.time()
                    while time.time() - t0 < 90 and not re.search(rx, text(n0)):
                        time.sleep(0.5)
                    log("step", i, "pickup", bool(re.search(rx, text(n0))))
                    time.sleep(2)
            rcon("quit")
            time.sleep(3)
        finally:
            if c.proc.poll() is None:
                c.proc.kill()
            c.close()
    finally:
        hg.release_slot("fg42fix")
        if os.path.exists(off):
            os.replace(off, fixp)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    shutil.copy2(LOG, os.path.join(out, "qconsole.log"))
    shots = os.path.join(MAINTT, "screenshots")
    if os.path.isdir(shots):
        for f in os.listdir(shots):
            if f.startswith("fg_"):
                shutil.move(os.path.join(shots, f), os.path.join(out, f))
    t = text()
    crash = len(re.findall(r"infinite state loop", t))
    miss = sorted(set(re.findall(r"Can't find player animation '([^']*fg42[^']*)'", t)))
    rel = re.findall(r"\^~\^~\^ FGRELOAD (\S+) (\d)", t)
    done = re.findall(r"\^~\^~\^ FGDONE (\S+)", t)
    log("RESULT", mode, "nofix" if nofix else "fix", "crash_lines=%d" % crash, "missing=%s" % miss,
        "reloads=%d" % len(rel), "guns_done=%s" % done)


if __name__ == "__main__":
    main()

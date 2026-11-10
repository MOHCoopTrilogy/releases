"""usefix_run.py - in-engine check of the v1.10.74 USE flip (tap = a dropped gun's ammo, hold = the gun) on a PRIVATE client
G:\\mohaa-usefix (copies of the live exe/renderers + the usefix game.dll/cgame.dll; basepath = the GOG tree read-only, own home).

    python usefix_run.py <tag> [map]        default map m2l1

Launch only through harness_window.launch_background (guard on, never activated, muted, mouse off). The test display is the
1920x1080 screen while the user's game runs, else the 3440x1440 ultrawide. One overlay pk3 in the home carries
coop_mod/usefix_test.scr (never shipped); the cfg starts a coop listen server with ui_startdmmap 2 and runs it with
`script *0 thread ...` once the map is up. Results: the ^~^~^ USEFIX / ^~^~^ LOOT lines of the run's qconsole.log."""
import os, re, shutil, sys, time, zipfile
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-usefix"
EXE = os.path.join(CLIENT, "openmohaa.exe")
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
RUNS = os.path.join(CLIENT, "runs")
W, H = 1280, 720
FIN = os.environ.get("UF_FIN") == "1"
MOD = r"H:\hzm_work\usefix-mod"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def rcon(cmd, port=12971, pw="usefixpw"):
    import socket
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sk.sendto(b"\xff\xff\xff\xff\x02rcon " + pw.encode() + b" " + cmd.encode(), ("127.0.0.1", port))
    sk.settimeout(1.0)
    try:
        print("RCON", cmd, "->", sk.recvfrom(4096)[0][4:].decode("latin-1", "replace").strip().replace("\n", " | "), flush=True)
    except OSError:
        print("RCON", cmd, "-> (no reply)", flush=True)
    sk.close()


def pick_display():
    want = (1920, 1080) if hg.user_game_running_raw() else (3440, 1440)
    mon = [m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == want]
    if not mon:
        raise SystemExit("no %dx%d display" % want)
    hw.test_display = lambda name=None, _m=mon[0]: _m
    log("test display", want)


def main(tag, mapname="m2l1"):
    pick_display()
    inuse = os.path.join(CLIENT, ".inuse")
    fd = os.open(inuse, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, ("usefix %s" % time.ctime()).encode())
    os.close(fd)
    try:
        with zipfile.ZipFile(os.path.join(MAINTT, "zzzzzzzzzzzzzzzzzzzz_usefix_test.pk3"), "w", zipfile.ZIP_DEFLATED) as z:
            z.write(os.path.join(HERE, "usefix_test.scr"), "coop_mod/usefix_test.scr")
            # the start hook: `script` needs cheats, which a coop listen host never has, so the TEST overlay replaces
            # an inert main.scr probe (coop_st_triggers 1 -> coop_selftest_triggers.scr::st_triggers_run) with a jump
            if FIN:
                # UF_FIN=1: the Norway finale's own loot harness (coop_finPathTest 4: placed MG42 + FG42 held, killed, the
                # death-drop held, a German's dropped gun held) with the usefix finale_m2l3.scr (its press is now a hold)
                z.write(os.path.join(MOD, "coop_mod", "finale_m2l3.scr"), "coop_mod/finale_m2l3.scr")
            z.writestr("coop_mod/coop_selftest_triggers.scr",
                       "st_triggers_run:{\r\n\tthread coop_mod/usefix_test.scr::main\r\n}end\r\n")
        shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
        for fn in os.listdir(MAINTT):
            if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
                os.remove(os.path.join(MAINTT, fn))
        if os.path.exists(LOG):
            os.remove(LOG)
        shutil.rmtree(SHOTS, ignore_errors=True)
        os.makedirs(SHOTS, exist_ok=True)
        lines = [
            "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
            "set in_mouse 0", "set in_nograb 1", "set in_gamepad 0", "set in_joystick 0",
            "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0",
            "set developer 1", "set coop_lootProbe 1", "set coop_dev 1", "set cl_memorial 0",
            "set rconPassword usefixpw", "set net_ip 127.0.0.1", "set coop_st_triggers %d" % (0 if FIN else 1), "set coop_finPathTest %d" % (4 if FIN else 0), "set uf_mode %s" % os.environ.get("UF_MODE", "1"), "set coop_joinCard 0", "set g_teamswitchdelay 0", "set sv_maxbots 0", "set sv_numbots 0",
            "wait 15000",
            "set g_gametype 2", "set thereisnomonkey 1", "set cheats 1",
            # LAST line: ui_startdmmap Cbuf_AddText's its `map` behind whatever is still in the buffer, so nothing may
            # follow it here (a wait after it would hold the map back). The rest is sent by rcon once the map is up.
            "set ui_dmmap %s" % mapname, "exec coop_mod/start_server.cfg",
        ]
        args = [EXE, "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", HOME,
                "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", str(W),
                "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0", "+set", "logfile", "2",
                "+set", "com_maxfps", "60", "+set", "in_gamepad", "0", "+set", "in_joystick", "0",
                "+set", "net_port", "12971", "+set", "thereisnomonkey", "1", "+set", "cheats", "1", "+set", "developer", "1", "+exec", "usefix_run.cfg"]
        args, late = hw.apply_policy(args, width=W, height=H)
        open(os.path.join(MAINTT, "usefix_run.cfg"), "w", newline="\n").write("\n".join(late + lines) + "\n")
        c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
        t0 = time.time()
        sent = False
        keyed = set()
        try:
            while time.time() - t0 < (900 if FIN else 480):
                if c.watcher.violations:
                    log("VIOLATION", c.watcher.violations[:3])
                    break
                if c.proc.poll() is not None:
                    break
                txt = open(LOG, encoding="latin-1", errors="replace").read() if os.path.exists(LOG) else ""
                if not sent and ("has entered the battle" in txt or time.time() - t0 > 200):
                    time.sleep(6)
                    for cmd in ["set com_maxfps 60", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0",
                                "set coop_woundMuffleVol 0", "set coop_lootProbe 1", "set s_volume 0",
                                "echo ^~^~^ USEFIX rcon cvars set",
                                "coop_st_triggers"]:
                        rcon(cmd)
                        time.sleep(0.3)
                    # join as the flharness does: rcon on a listen host runs in the host client's command buffer
                    open(os.path.join(MAINTT, "ufjoin.cfg"), "w", newline="\n").write("\n".join([
                        "popmenu 0", "wait 10", "primarydmweapon rifle", "wait 5", "join_team allies", "wait 20",
                        "popmenu 0", "wait 40", "popmenu 0", "wait 20", "+attackprimary", "wait 10", "-attackprimary",
                        "set s_volume 0", "set com_maxfps 60"]) + "\n")
                    for _ in range(4):
                        rcon("exec ufjoin.cfg")
                        time.sleep(4)
                        cur = open(LOG, encoding="latin-1", errors="replace").read()
                        if "joined the" in cur or "USEFIX start" in cur:
                            break
                    sent = True
                    log("rcon sent at", int(time.time() - t0))
                if sent:
                    for m in re.finditer(r"USEFIX KEY (\S+) ([0-9.]+)", txt):
                        if m.group(1) in keyed:
                            continue
                        keyed.add(m.group(1))
                        rcon("+use")
                        time.sleep(float(m.group(2)))
                        rcon("-use")
                        log("key", m.group(1), m.group(2))
                if "USEFIX done" in txt or "USEFIX no player" in txt or "NGTEST done" in txt:
                    time.sleep(2)
                    break
                time.sleep(0.2)
        finally:
            if c.proc.poll() is None:
                c.proc.kill()
            c.close()
        out = os.path.join(RUNS, tag)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        for fn in sorted(os.listdir(SHOTS)):
            shutil.move(os.path.join(SHOTS, fn), os.path.join(out, fn))
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(out, "qconsole.log"))
            for ln in open(LOG, encoding="latin-1", errors="replace"):
                if "USEFIX" in ln or "NGTEST" in ln or "^~^~^ LOOT" in ln or "Script Error" in ln or "Got " in ln:
                    print(ln.rstrip())
        log("out", out)
    finally:
        os.remove(inuse)


if __name__ == "__main__":
    main(sys.argv[1], *(sys.argv[2:3]))

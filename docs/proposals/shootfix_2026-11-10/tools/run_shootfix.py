r"""run_shootfix.py - bug-10935 ("anim/shoot.scr took over 10 seconds" server drop) co-op fight runs.

    python run_shootfix.py <tag> <map> [--control] [--min N] [--repro A|B] [--modfix]

Private client G:\\mohaa-shootfix: a copy of the live exe + dlls (never the live install itself), home inside it.
  default   game.dll = shootfix-eng build (C:\\hzm-shootfix\\eng\\.cmake)
  --control game.dll = the live release dll, unchanged
The map tester's patrol (coop_maptest 2) walks the player through the fights for ~2 minutes, watches, kills him
and respawns him at the start: actors left fighting out of sight sleep after 60 s (Actor::RequireThink) and wake
when the player comes back - the wake is where the release build drops the server.
--repro B  no patrol; a test thread (overlay pk3 in the private home, m3l3 only) stands bazooka men inside the
           player: the melee branch of anim/shoot.scr with no butt animation (the real script hang)
--repro A  no patrol; cover men fight a friendly, the player is moved away for 85 s and back (the sleep/wake case)
--modfix   the overlay also carries anim/shoot.scr + anim/attack.scr from the shootfix-mod worktree
Counted from the server log: "Server crashed", "COVERSHOOT wake" (developer print: the release build would have
dropped here), "COVERSHOOT stuck" (a shoot script that really did not end).
Launched only through docs/tools/harness_window (guard on, muted, no grab, no pad); 1080p screen while the user plays.
"""
import os, re, shutil, socket, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LIVE = r"G:\mohaa-gl2"
CLIENT = r"G:\mohaa-shootfix"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
RUNS = r"H:\hzm_work\shootfix\runs"
FIXDLL = r"C:\hzm-shootfix\eng\.cmake\code\server\fgame\Release\game.dll"
MODFIX = r"C:\hzm-shootfix\mod"
OVERLAY = os.path.join(MAINTT, "zzzzzzzz_sfxtest.pk3")
PRISTINE = r"G:\mohaa-recoil\pristine\omconfig.cfg"
PORT, RCONPW = 12431, "sfxtest"
W, H = 1120, 630
BIN = ["openmohaa.exe", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll", "SDL2.dll", "OpenAL64.dll",
       "libcurl.dll"]


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


def text():
    try:
        with open(LOG, "rb") as f:
            return f.read().decode("latin-1")
    except OSError:
        return ""


QUEUE = r"H:\hzm_work\display_queue.txt"


def wait_screen(limit=5400):
    r"""keep to H:\hzm_work\display_queue.txt: always write our line, launch only when no older "second" line is
    ahead of it and the 1080p screen is free (one client there, four clients in all); the line goes when we launch.
    Other agents leave their line standing while they still need the screen, so an older line holds us only
    until its owner has had a turn: one client seen on the screen and gone again per older line (or, with the
    screen empty the whole time, 5 minutes - nobody came)."""
    d = hw.test_display()["rect"]
    line = "shootfix %s waiting second" % time.strftime("%H:%M")
    open(QUEUE, "a").write(line + chr(10))
    log("queue line:", line)
    t0 = time.time()
    free = 0
    turns = 0
    was_busy = False
    idle0 = time.time()
    try:
        while True:
            try:
                rows_q = [l.strip() for l in open(QUEUE).read().splitlines() if l.strip()]
            except OSError:
                rows_q = [line]
            ahead = [l for l in (rows_q[:rows_q.index(line)] if line in rows_q else [])
                     if "second" in l and not l.startswith("shootfix ")]
            rows = [r for r in hg.classify() if r["cls"] == "HARNESS"]
            busy = [r["owner"] for r in rows for h in hw.windows_of(r["pid"], visible_only=True)
                    if hw._overlap(hw._wrect(h), d)]
            if busy:
                was_busy = True
                idle0 = time.time()
            elif was_busy:
                was_busy = False
                turns += 1
                log("screen freed: turn %d of %d ahead" % (turns, len(ahead)))
            held = ahead and turns < len(ahead) and time.time() - idle0 < 300
            if not held and not busy and len(rows) < 4:
                free += 1          # free on three looks 15 s apart: whoever just left the queue has had time to open
                if free >= 3:
                    break
            else:
                free = 0
            if time.time() - t0 > limit:
                raise SystemExit("test screen still busy: %s ahead=%s" % (busy, ahead))
            time.sleep(15)
    finally:
        try:
            rest = [l for l in open(QUEUE).read().splitlines(True) if l.strip() != line]
            open(QUEUE, "w").write("".join(rest))
        except OSError:
            pass


REPRO_HEAD = """
sfx_repro:
	local.p = NULL
	while (1)
	{
		if ($player != NULL)
		{
			local.p = $player[1]
			if (local.p != NULL && local.p.dmteam == "allies" && (isalive local.p)) { break }
		}
		wait 1
	}
	wait 8
	local.p = $player[1]
	thread sfx_heal
	local.home = local.p.origin
	println "^~^~^ SFXREPRO ready"
"""
REPRO_B = """
	for (local.i = 1; local.i <= 4; local.i++)
	{
		local.p = $player[1]
		local.a = spawn "models/human/german_waffenss_shutze.tik"
		local.a.origin = local.p.origin + (40 0 8)
		local.a gun "panzerschrek"
		local.a.health = 100000
		local.a type_attack "cover"
		local.a.enableEnemy = 1
		local.a forceactivate
		local.a attackplayer
		wait 1
		println ("^~^~^ SFXREPRO B spawned ent=" + local.a.entnum + " group=" + local.a.weapongroup)
		for (local.k = 0; local.k < 4; local.k++)
		{
			wait 6
			if (local.a != NULL) { println ("^~^~^ SFXREPRO B state ent=" + local.a.entnum + " think=" + local.a.thinkstate + " dist=" + (vector_length (local.a.origin - $player[1].origin))) }
		}
	}
	println "^~^~^ SFXREPRO done"
end
"""
REPRO_HEAL = """
sfx_heal:
	while (1)
	{
		if ($player != NULL) { $player[1] heal 1 }
		wait 0.25
	}
end
"""
REPRO_A = """
	local.f = spawn "models/human/allied_airborne_soldier.tik"
	local.f.origin = local.home + (0 90 8)
	local.f.health = 1000000
	for (local.i = 0; local.i < 6; local.i++)
	{
		local.a = spawn "models/human/german_waffenss_shutze.tik"
		local.a.origin = local.home + (160 0 8) + (60 0 0) * local.i + (0 60 0) * (local.i - 2)
		local.a.health = 100000
		local.a type_attack "cover"
		local.a.enableEnemy = 1
		local.a forceactivate
		println ("^~^~^ SFXREPRO A spawned ent=" + local.a.entnum)
	}
	wait 12
	local.p = $player[1]
	local.p origin ( -4758 2256 40 )
	println "^~^~^ SFXREPRO away"
	wait 85
	local.p = $player[1]
	local.p origin local.home
	println "^~^~^ SFXREPRO back"
	wait 25
	println "^~^~^ SFXREPRO done"
end
"""


def overlay(repro, modfix):
    """the test pk3: maps/m3l3.scr with one extra thread (and, with --modfix, the two fixed anim scripts)"""
    import zipfile
    if os.path.exists(OVERLAY):
        os.remove(OVERLAY)
    if not repro and not modfix:
        return
    z = zipfile.ZipFile(OVERLAY, "w", zipfile.ZIP_DEFLATED)
    if repro:
        t = open(os.path.join(MODFIX, "maps", "m3l3.scr"), "rb").read().decode("latin-1")
        hook = "waitthread coop_mod/main.scr::main"
        i = t.index(hook)
        j = t.index(chr(10), i)
        t = t[:j + 1] + "\tthread sfx_repro" + chr(13) + chr(10) + t[j + 1:]
        body = (REPRO_HEAD + (REPRO_B if repro == "B" else REPRO_A) + REPRO_HEAL).replace(chr(10), chr(13) + chr(10))
        z.writestr("maps/m3l3.scr", (t + body).encode("latin-1"))
    if modfix:
        for fn in ("anim/shoot.scr", "anim/attack.scr"):
            z.write(os.path.join(MODFIX, *fn.split("/")), fn)
    z.close()


def setup(control):
    os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
    os.makedirs(os.path.join(CLIENT, "stock"), exist_ok=True)
    for b in BIN:
        st = os.path.join(CLIENT, "stock", b)
        if not os.path.exists(st):
            shutil.copy2(os.path.join(LIVE, b), st)
        if b != "game.dll" and not os.path.exists(os.path.join(CLIENT, b)):
            shutil.copy2(st, os.path.join(CLIENT, b))
    shutil.copyfile(os.path.join(CLIENT, "stock", "game.dll") if control else FIXDLL, os.path.join(CLIENT, "game.dll"))
    shutil.copyfile(PRISTINE, os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)


def main():
    tag, mp = sys.argv[1], sys.argv[2]
    control = "--control" in sys.argv
    repro = sys.argv[sys.argv.index("--repro") + 1] if "--repro" in sys.argv else ""
    modfix = "--modfix" in sys.argv
    minutes = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 4.0
    if hg.user_game_running():
        raise SystemExit("user game running - not launching")
    if hg.user_game_running_raw() and hw.test_display()["rect"][2] - hw.test_display()["rect"][0] != 1920:
        raise SystemExit("the user is playing: the 1080p screen only (HZM_TEST_RES=1920x1080)")
    wait_screen()
    setup(control)
    overlay(repro, modfix)
    boot = ["set developer 1", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0",
            "set s_musicvolume 0", "set s_ambientvolume 0", "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0",
            "seta coop_woundMuffleVol 0", "set rconpassword %s" % RCONPW, "set coop_dev 1",
            "seta coop_maptest %d" % (0 if repro else 2), "seta coop_maptest_dwell %d" % int(minutes * 60 + 60), "seta coop_maptest_waypoints 20",
            "seta coop_maptest_dwell_wpt 6", "set coop_dbno 0", "seta g_scriptcheck 0",
            "set g_gametype 2", "set ui_dmmap %s" % mp, "ui_startdmmap 2"]
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
            "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
            "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60",
            "+set", "net_enabled", "1", "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(PORT), "+exec", "sfx_run.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H)
    open(os.path.join(MAINTT, "sfx_run.cfg"), "w", newline="\n").write("\n".join(list(late) + boot) + "\n")
    join = ["+attack", "wait 300", "-attack", "wait 4000", "+attack", "wait 300", "-attack", "wait 5000",
            "seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0", "seta coop_woundMuffleVol 0", "set s_volume 0"]
    hg.acquire_slot("shootfix", args[0], HOME, [PORT], minutes=30)
    out = os.path.join(RUNS, tag)
    try:
        c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
        hg.set_slot_pid("shootfix", c.pid)
        try:
            t0 = time.time()
            while time.time() - t0 < 180 and c.proc.poll() is None and not re.search(r"MAPTEST_LOADED|------ Server Initialization Complete", text()):
                time.sleep(1)
            time.sleep(15)
            open(os.path.join(MAINTT, "sfxstep.cfg"), "w", newline="\n").write("\n".join(join) + "\n")
            rcon("exec sfxstep.cfg")
            t0 = time.time()
            while time.time() - t0 < minutes * 60 and c.proc.poll() is None and not c.watcher.violations:
                if re.search(r"Server crashed|SFXREPRO done", text()):
                    time.sleep(3)
                    break
                time.sleep(5)
            rcon("quit")
            time.sleep(3)
        finally:
            if c.proc.poll() is None:
                c.proc.kill()
            c.close()
    finally:
        hg.release_slot("shootfix")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    shutil.copy2(LOG, os.path.join(out, "qconsole.log"))
    t = text()
    wp = len(re.findall(r"MAPTEST2_WAYPOINT", t))
    crash = re.findall(r"Server crashed: ([^\r\n]*?)\) -----", t)
    wake = re.findall(r"COVERSHOOT wake ent=(\d+) tn=(\S*) gap=(\d+) stale=(\d+)", t)
    stuck = re.findall(r"COVERSHOOT stuck[^\r\n]*", t)
    log("RESULT %s map=%s dll=%s scripts=%s repro=%s waypoints=%d respawn=%d crash=%d wake=%d stuck=%d nobutt=%d" % (
        tag, mp, "release" if control else "fix", "fix" if modfix else "release", repro or "-", wp,
        len(re.findall(r"KITSPAWN", t)), len(crash), len(wake), len(stuck), len(re.findall(r"unknown animation '\w+_butt'", t))))
    for x in re.findall(r"SFXREPRO [^\r\n]*", t)[:30]:
        log("  " + x)
    for x in crash:
        log("  CRASH", x)
    for x in wake[:12]:
        log("  WAKE ent=%s tn=%s gap=%.1fs stale=%.1fs" % (x[0], x[1], int(x[2]) / 1000.0, int(x[3]) / 1000.0))
    for x in stuck[:6]:
        log("  STUCK", x)


if __name__ == "__main__":
    main()

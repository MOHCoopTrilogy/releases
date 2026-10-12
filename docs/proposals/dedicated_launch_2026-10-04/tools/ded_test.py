"""Coop start screen DEDICATED option - in-game test (dedicated_launch 2026-10-04).

    python ded_test.py wait-and-run      waits for SCRATCHPAD\\test_slot.txt == "dedicated", runs, writes "free"

Private install G:\\mohaa-dedtest (registered in docs/tools/harness_guard.py): the exe built in openmohaa-hzm-dedicated,
byte copies of the LIVE DLLs + omohaaded.exe (G:\\mohaa-gl2 is only read), basepath = the GOG tree read-only, a fresh
home seeded from installer/omconfig_default.cfg (never the user's config, qkey or saves), the changed mod files as an
overlay pk3 in the home. Client on DISPLAY2 via harness_window.launch_background, net_ip 127.0.0.1, com_maxfps 60.

The client is a pure client here (it never hosts), so it has no rcon: it is driven by a step-file chain. The boot cfg
defines `dloop` = execq dstep_1.cfg; wait 500; dloop. Each step file first re-points dloop at the next file, so every
step runs exactly once; the next file is pre-created idle.

Session A (client log on, server log off - the shipped default):
  A1 menu screenshots, Dedicated off and on
  A2 APPLY (Dedicated) on m1l1 with 12204 held by this script -> server on the next free port (12205), command line
     carries the map / settings / maxclients; the client joins (detect.cfg, coop_active 1), joins a team, deploys
  A3 disconnect -> the server stops
  A4 BEGIN FULL CAMPAIGN (Dedicated) -> co_lobby1, 4 players, coop_campaign 1; joins; disconnect
  A5 omohaaded.exe missing -> clear message
  A6 server killed while starting -> clear message
  A7 every port 12204-12212 held (12203 is the client) -> clear message
  A8 Dedicated unticked -> today's listen host (no omohaaded, Detected Coop, 0 script errors)
  A9 Keep Running ticked -> quit leaves the server running (then this script ends it)
Session B (client logfile 0, coop_dedLog 1 -> the server writes qconsole.log with developer 1):
  B1 m1l1: server boots coop clean (Server/CM_LoadMap/loadout init, Detected Coop for the client, 0 Script Error)
  B2 campaign co_lobby1: same; then quit -> the server stops with the client
"""
import json, os, re, shutil, socket, subprocess, sys, time, zipfile

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.normpath(os.path.join(HERE, ".."))
EVID = os.path.join(PROP, "evidence")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
# DED_BINDIR = a folder holding a complete built set (exe + DLLs + omohaaded.exe) to test instead of the live copies
LIVE = os.environ.get("DED_BINDIR") or r"G:\mohaa-gl2"
CLIENT = r"G:\mohaa-dedtest"
EXE = os.path.join(CLIENT, "openmohaa.exe")
DED = os.path.join(CLIENT, "omohaaded.exe")
BUILT = os.path.join(os.environ["DED_BINDIR"], "openmohaa.exe") if os.environ.get("DED_BINDIR") else r"C:\mohaa-coop-dev\openmohaa-hzm-dedicated\.cmake\Release\openmohaa.exe"
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
OVERLAY_FILES = ["ui/coop_start.urc", "coop_mod/start_server.cfg", "coop_mod/cfg/server_rules.cfg",
                 "coop_mod/cfg/dedicated_server.cfg", "coop_mod/cfg/coop_dedcampaign.cfg"]
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SCRATCH = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad"
SLOTFILE = os.path.join(SCRATCH, "test_slot.txt")
OWNER = "dedicated"
PORTS = list(range(12203, 12213))
W, H = 1280, 720
RESULTS = []


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def check(tag, ok, detail=""):
    RESULTS.append((tag, bool(ok), detail))
    log("%s %s %s" % ("PASS" if ok else "FAIL", tag, detail))


def read_log():
    try:
        return open(LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def wait_log(pat, timeout, start=0):
    rx = re.compile(pat)
    t0 = time.time()
    while time.time() - t0 < timeout:
        m = rx.search(read_log(), start)
        if m:
            return m
        time.sleep(0.4)
    return None


def write_atomic(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


class Stepper:
    """Menu-time driver. dloop = dtick; wait 500; dgate. dtick execs the current step file; each step file re-points
    dtick at the next one, so a step runs exactly once. dgate is dloop while polling and empty when PAUSED: a `wait`
    chain blocks the WHOLE command buffer, so the loop must never run while the client is in a game (server stufftext
    such as the coop detect.cfg would be held behind it). In-game scripts go in activeAction and end by resuming."""

    def __init__(self, marker):
        self.n = 1
        self.marker = marker
        for fn in os.listdir(MAINTT):
            if fn.startswith("dstep_"):
                os.remove(os.path.join(MAINTT, fn))
        write_atomic(os.path.join(MAINTT, "dstep_1.cfg"), "// idle\n")

    @staticmethod
    def boot_lines():
        return ['alias dtick "execq dstep_1.cfg"', 'alias dloop "dtick; wait 500; dgate"', "alias dgate dloop", "dloop"]

    RESUME = "alias dgate dloop; dloop;"

    def step(self, lines, timeout=30, pause=False):
        n, nxt = self.n, self.n + 1
        write_atomic(os.path.join(MAINTT, "dstep_%d.cfg" % nxt), "// idle\n")
        mk = "^~^~^ DSTEP %d %d" % (n, int(time.time()) % 100000)
        body = ['alias dtick "execq dstep_%d.cfg"' % nxt]
        if pause:
            body.append('alias dgate ""')
        body += lines
        if self.marker:
            body.append("echo %s" % mk)
        start = len(read_log())
        write_atomic(os.path.join(MAINTT, "dstep_%d.cfg" % n), "\n".join(body) + "\n")
        self.n = nxt
        if self.marker:
            if not wait_log(re.escape(mk), timeout, max(0, start - 10)):
                raise RuntimeError("step %d timed out: %s" % (n, lines[:3]))
        else:
            time.sleep(2.0)
        return start


def ded_procs():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='omohaaded.exe'\" | "
          "Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip()
    if not out:
        return []
    j = json.loads(out)
    j = j if isinstance(j, list) else [j]
    return [p for p in j if (p.get("ExecutablePath") or "").lower().startswith(CLIENT.lower() + "\\")]


def masked(cmd):
    return re.sub(r'(rconPassword ")[^"]*"', r'\1<masked>"', cmd or "")


def wait_proc(pid, alive, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        have = any(p["ProcessId"] == pid for p in ded_procs())
        if have == alive:
            return True
        time.sleep(0.5)
    return False


def kill(pid):
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)


def hold_ports(ports):
    socks = []
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", p))
        socks.append(s)
    return socks


def release(socks):
    for s in socks:
        s.close()


def shot(st, name):
    d = os.path.join(MAINTT, "screenshots")
    before = set(os.listdir(d)) if os.path.isdir(d) else set()
    st.step(["screenshot"])
    t0 = time.time()
    while time.time() - t0 < 10:
        now = set(os.listdir(d)) if os.path.isdir(d) else set()
        new = sorted(now - before)
        if new:
            time.sleep(0.5)
            src = os.path.join(d, new[-1])
            shutil.copyfile(src, os.path.join(EVID, name + os.path.splitext(src)[1]))
            return True
        time.sleep(0.3)
    return False


def cvar(st, name):
    start = st.step([name])
    m = re.findall(r'"%s" is:"([^"]*)' % re.escape(name), read_log()[start:])
    return m[-1].replace("^7", "") if m else None


# ------------------------------------------------------------------ setup
def seed():
    os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
    for fn in ("cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll", "SDL2.dll", "OpenAL64.dll",
               "libcurl.dll", "omohaaded.exe"):
        src = os.path.join(LIVE, fn)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(CLIENT, fn))
    shutil.copyfile(BUILT, EXE)
    shutil.copyfile(r"C:\mohaa-coop-dev\installer\omconfig_default.cfg", os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn.lower().startswith("qconsole"):
            os.remove(os.path.join(MAINTT, fn))
    cfgd = os.path.join(MAINTT, "configs", "hzm_dedicated.cfg")
    if os.path.exists(cfgd):
        os.remove(cfgd)
    shutil.rmtree(os.path.join(MAINTT, "screenshots"), ignore_errors=True)
    with zipfile.ZipFile(os.path.join(MAINTT, "zzzzzzzzzzzzzz_dedicated_test.pk3"), "w", zipfile.ZIP_DEFLATED) as z:
        for rel in OVERLAY_FILES:
            z.write(os.path.join(MOD, rel.replace("/", os.sep)), rel)


def launch(session, client_log):
    st = Stepper(marker=client_log)
    boot = ["set ui_gamespy 0", "set sv_maxbots 0", "set com_maxfps 60", "set coop_dedTimeout 120",
            "set coop_dedKeep 0", "set coop_dedLog %d" % (0 if client_log else 1), "set ui_dedicated 0"]
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2" if client_log else "0"), ("net_port", "12203"),
            ("net_ip", "127.0.0.1"), ("com_maxfps", "60"), ("g_gametype", "2")]
    args = [EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "dboot.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H)
    write_atomic(os.path.join(MAINTT, "dboot.cfg"), "\n".join(boot + late + Stepper.boot_lines()) + "\n")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    hg.set_slot_pid(OWNER, c.proc.pid)
    log("session %s client pid %d" % (session, c.proc.pid))
    return c, st


def launch_plain(session, boot_lines):
    """client logfile 0, coop_dedLog 1, no step loop"""
    boot = ["set ui_gamespy 0", "set sv_maxbots 0", "set com_maxfps 60", "set coop_dedTimeout 120",
            "set coop_dedKeep 0", "set coop_dedLog 1", "set ui_dedicated 1"]
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "0"), ("net_port", "12203"), ("net_ip", "127.0.0.1"),
            ("com_maxfps", "60"), ("g_gametype", "2")]
    args = [EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "dboot.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H)
    write_atomic(os.path.join(MAINTT, "dboot.cfg"), "\n".join(boot + late + boot_lines) + "\n")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    hg.set_slot_pid(OWNER, c.proc.pid)
    log("session %s client pid %d" % (session, c.proc.pid))
    return c


def started_pid(start, timeout=20):
    m = wait_log(r"coop dedicated: started .*? pid (\d+) - map (\S+?)(?: \(campaign\))?, port (\d+)", timeout, start)
    return (int(m.group(1)), m.group(2), int(m.group(3))) if m else (None, None, None)


def close_window(c):
    for h in hw.windows_of(c.proc.pid):
        hw.u32.PostMessageW(h, 0x0010, 0, 0)  # WM_CLOSE -> SDL_QUIT -> "quit Closed window" (EXEC_NOW)


def cmd_of(pid):
    procs = [p for p in ded_procs() if p["ProcessId"] == pid]
    return procs[0]["CommandLine"] if procs else ""


def resumed(start, timeout):
    return bool(wait_log(r"\^~\^~\^ DSTEP", timeout, start))


# in-game scripts (activeAction): join + deploy, a still, then leave and resume the menu loop
INGAME = ("popmenu 0; primarydmweapon rifle; join_team allies; wait 2500; popmenu 0; join_team allies; +attack; "
          "wait 150; -attack; wait 9000; screenshot; wait 600; %s; wait 1500; " + Stepper.RESUME)


def session_a():
    c, st = launch("A", True)
    try:
        if not wait_log(r"\^~\^~\^ DSTEP|execing dboot\.cfg", 240):
            raise RuntimeError("client never reached the menu")
        time.sleep(4)
        # A1 - the screen
        st.step(["set ui_dmmap m1l1", "set ui_dedicated 0", "pushmenu coop_start", "wait 600"])
        check("A1 menu Dedicated off", shot(st, "A1_coop_start_dedicated_off"))
        st.step(["set ui_dedicated 1", "wait 400"])
        check("A1 menu Dedicated on", shot(st, "A1_coop_start_dedicated_on"))

        # A2 + A3 - APPLY with Dedicated on m1l1, 12204 held -> 12205; in game; the user's disconnect stops it
        held = hold_ports([12204])
        start = st.step(['set sv_hostname "Ded Test A"', 'set password "pw ok"', "set sv_maxclients 6",
                         "set coop_health 600", "set coop_lmsLives 2", "set coop_hardcore 0", "set ui_dmmap m1l1",
                         "set ui_dedicated 1", 'set activeAction "%s"' % (INGAME % "disconnect"), "wait 250",
                         "coop_dedStart"], pause=True)
        pid, mp, port = started_pid(start)
        release(held)
        check("A2 launched", pid is not None, "pid %s map %s port %s" % (pid, mp, port))
        check("A2 port busy -> next free", port == 12205, "port %s (12203 = the client, 12204 held)" % port)
        cmd = cmd_of(pid)
        json.dump({"A2": masked(cmd)}, open(os.path.join(EVID, "A2_cmdline.json"), "w"), indent=1)
        need = ['+map m1l1', '+set sv_maxclients 6', '+set sv_hostname "Ded Test A"', '+set password "pw ok"',
                '+set coop_health "600"', '+set coop_lmsLives "2"', '+set coop_campaign 0', '+set g_gametype 2',
                '+set net_port 12205', '+set net_ip "127.0.0.1"', '+set config "hzm_dedicated.cfg"', '+set logfile 0',
                '+set sv_gamespy 0', '+set fs_homepath "%s"' % HOME, '+set fs_basepath "%s"' % GOG,
                '+set com_target_game 2', '+exec coop_mod/cfg/dedicated_server.cfg', '+set dedicated 1']
        miss = [n for n in need if n not in cmd]
        check("A2 command line", cmd and not miss, "missing %s" % miss if miss else "all %d values" % len(need))
        check("A2 rcon is per-launch", 'rconPassword "' in cmd)
        check("A2 server up -> joining", bool(wait_log(r"server is up on port 12205 - joining", 150, start)))
        check("A2 connected and in the map", bool(wait_log(r"execing coop_mod/cfg/detect\.cfg", 180, start)))
        check("A2 joined a team", bool(wait_log(r"has joined the (Allies|Axis|Free)", 40, start)))
        check("A3 user disconnect stops the server", wait_proc(pid, False, 40), "pid %s" % pid)
        check("A3 message", bool(wait_log(r"you left, so your dedicated server is stopping", 5, start)))
        check("A2/A3 loop resumed", resumed(start, 20))
        shots = sorted(os.listdir(os.path.join(MAINTT, "screenshots")))
        if shots:
            shutil.copyfile(os.path.join(MAINTT, "screenshots", shots[-1]), os.path.join(EVID, "A2_ingame_m1l1" + os.path.splitext(shots[-1])[1]))

        # A4 - BEGIN FULL CAMPAIGN with Dedicated
        start = st.step(["set ui_dedicated 1", 'set activeAction "%s"' % (INGAME % "disconnect"), "wait 250",
                         "exec coop_mod/cfg/coop_dedcampaign.cfg"], pause=True)
        pid, mp, port = started_pid(start)
        cmd = cmd_of(pid)
        json.dump({"A4": masked(cmd)}, open(os.path.join(EVID, "A4_cmdline.json"), "w"), indent=1)
        need = ["+map co_lobby1", "+set sv_maxclients 4", "+set coop_campaign 1"]
        miss = [n for n in need if n not in cmd]
        check("A4 campaign launched", pid is not None and cmd and not miss, "pid %s map %s port %s missing %s" % (pid, mp, port, miss))
        check("A4 joined the campaign lobby", bool(wait_log(r"execing coop_mod/cfg/detect\.cfg", 180, start)))
        check("A4 disconnect stops it", wait_proc(pid, False, 45))
        check("A4 loop resumed", resumed(start, 20))
        shots = sorted(os.listdir(os.path.join(MAINTT, "screenshots")))
        if shots:
            shutil.copyfile(os.path.join(MAINTT, "screenshots", shots[-1]), os.path.join(EVID, "A4_ingame_co_lobby1" + os.path.splitext(shots[-1])[1]))

        # A5 - omohaaded.exe missing
        os.replace(DED, DED + ".hidden")
        try:
            start = st.step(["coop_dedStart"])
            check("A5 missing exe message", bool(wait_log(r"omohaaded\.exe is missing from the game folder", 5, start)))
        finally:
            os.replace(DED + ".hidden", DED)

        # A6 - the server dies while starting
        start = st.step(["set ui_dmmap m1l1", "coop_dedStart"])
        pid, mp, port = started_pid(start)
        if pid:
            kill(pid)
        check("A6 died-while-starting message",
              bool(wait_log(r"the server stopped while starting \(exit code \d+\)", 10, start)), "pid %s" % pid)
        st.step(["pushmenu coop_start", "wait 500"])
        check("A6 status on screen", shot(st, "A6_status_server_died"))

        # A7 - every port busy
        held = hold_ports(range(12204, 12213))
        try:
            start = st.step(["coop_dedStart"])
            check("A7 all ports busy message", bool(wait_log(r"no free port in 12203-12212", 5, start)))
            check("A7 nothing launched", not ded_procs())
            check("A7 status on screen", shot(st, "A7_status_no_port"))
        finally:
            release(held)

        # A8 - Dedicated unticked: today's listen host
        start = st.step(["set ui_dedicated 0", "set ui_dmmap m1l1", 'set activeAction "%s"' % (INGAME % "disconnect"),
                         "wait 250", "exec coop_mod/start_server.cfg"], pause=True)
        ok = wait_log(r"Detected Coop for", 240, start)
        check("A8 listen host coop", bool(ok))
        check("A8 no dedicated process", not ded_procs())
        check("A8 listen host left + loop resumed", resumed(start, 90))
        seg = read_log()[start:]
        check("A8 listen 0 script errors", seg.count("Script Error") == 0, "%d" % seg.count("Script Error"))
        check("A8 ui_dedicated still 0", cvar(st, "ui_dedicated") == "0")

        # A9 - Keep Running: quit leaves the server running
        start = st.step(["set coop_dedKeep 1", "set ui_dedicated 1", "set ui_dmmap m1l1",
                         'set activeAction "wait 8000; quit;"', "wait 250", "coop_dedStart"], pause=True)
        pid, mp, port = started_pid(start)
        check("A9 launched", pid is not None, "pid %s port %s" % (pid, port))
        try:
            c.proc.wait(240)
        except Exception:
            pass
        check("A9 client quit", c.proc.poll() is not None)
        check("A9 quit message", bool(wait_log(r"leaving the server running - omohaaded\.exe pid %d" % (pid or 0), 3, start)))
        time.sleep(5)
        alive = any(p["ProcessId"] == pid for p in ded_procs())
        check("A9 server still running after the client quit", alive)
        if alive:
            kill(pid)
    finally:
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(EVID, "A_client_qconsole.log"))
        if c.proc.poll() is None:
            try:
                c.proc.terminate()
                c.proc.wait(20)
            except Exception:
                pass
        c.close()
        for p in ded_procs():
            kill(p["ProcessId"])


def server_checks(tag, text, mp):
    check("%s server loaded %s" % (tag, mp), ("Server: %s" % mp) in text and "CM_LoadMap" in text)
    check("%s coop loadout init" % tag, ("initialising coop weapon loadout for maps/%s.scr" % mp) in text)
    check("%s Detected Coop for the client" % tag, "Detected Coop for" in text)
    check("%s 0 Script Error" % tag, text.count("Script Error") == 0, "%d" % text.count("Script Error"))
    check("%s 0 not properly loaded" % tag, text.count("not properly loaded") == 0)


def session_b(tag, boot_extra, mp, logname):
    """Client logfile 0 + coop_dedLog 1: qconsole.log is the SERVER's. No menu loop at all: the boot cfg starts the
    server; activeAction (no waits, so the coop detect.cfg is never held) joins + deploys; WM_CLOSE quits."""
    for fn in os.listdir(MAINTT):
        if fn.lower().startswith("qconsole"):
            os.remove(os.path.join(MAINTT, fn))
    c = launch_plain(tag, boot_extra + ['set activeAction "popmenu 0; primarydmweapon rifle; join_team allies; +attack;"',
                                        "wait 3000", "coop_dedStart" if mp == "m1l1" else "exec coop_mod/cfg/coop_dedcampaign.cfg"])
    try:
        if not wait_log(r"Detected Coop for", 300):
            check("%s server log" % tag, False, "no Detected Coop in the server log")
        else:
            time.sleep(20)
            text = read_log()
            shutil.copyfile(LOG, os.path.join(EVID, logname))
            server_checks(tag, text, mp)
            if mp == "m1l1":
                check("%s server saw the join" % tag, bool(re.search(r"has joined the (Allies|Axis|Free)", text)))
        pids = [p["ProcessId"] for p in ded_procs()]
        for p in pids:
            json.dump({tag: masked(cmd_of(p))}, open(os.path.join(EVID, "%s_cmdline.json" % tag), "w"), indent=1)
        close_window(c)
        try:
            c.proc.wait(30)
        except Exception:
            pass
        check("%s window close quits the client" % tag, c.proc.poll() is not None)
        check("%s quit stops the server (Keep Running off)" % tag, bool(pids) and all(wait_proc(p, False, 10) for p in pids),
              "pids %s" % pids)
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(EVID, logname))
    finally:
        if c.proc.poll() is None:
            try:
                c.proc.terminate()
                c.proc.wait(20)
            except Exception:
                pass
        c.close()
        for p in ded_procs():
            kill(p["ProcessId"])


def run():
    v = open(SLOTFILE).read().strip() if os.path.exists(SLOTFILE) else ""
    if v != OWNER:
        raise SystemExit("test slot is %r, not %r - not launching" % (v, OWNER))
    if hg.user_game_running():
        raise SystemExit("the user's game is running - not launching")
    os.makedirs(MAINTT, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, PORTS, minutes=60)
    try:
        seed()
        shutil.rmtree(EVID, ignore_errors=True)
        os.makedirs(EVID)
        try:
            session_a()
        except Exception as e:  # noqa: BLE001
            check("session A", False, repr(e))
        for tag, extra, mp, lg in (
                ("B1", ['set sv_hostname "Ded Test B"', 'set password ""', "set sv_maxclients 8", "set ui_dmmap m1l1"],
                 "m1l1", "B1_server_qconsole.log"),
                ("B2", ['set sv_hostname "Ded Test B"', 'set password ""'], "co_lobby1", "B2_server_qconsole.log")):
            try:
                session_b(tag, extra, mp, lg)
            except Exception as e:  # noqa: BLE001
                check("session " + tag, False, repr(e))
    finally:
        hg.release_slot(OWNER)
        n_ok = sum(1 for _, ok, _ in RESULTS if ok)
        log("RESULT %d/%d" % (n_ok, len(RESULTS)))
        os.makedirs(EVID, exist_ok=True)
        json.dump(RESULTS, open(os.path.join(EVID, "results.json"), "w"), indent=1)


def slot_is_ours():
    try:
        return open(SLOTFILE).read().strip() == OWNER
    except OSError:
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "wait-and-run":
        log("waiting for test_slot.txt == %s" % OWNER)
        while not slot_is_ours():
            time.sleep(15)
        log("slot is ours")
        try:
            try:
                run()
            except BaseException as e:  # noqa: BLE001
                log("run FAILED: %r" % (e,))
        finally:
            if slot_is_ours():  # the only write this harness ever makes to the slot file
                open(SLOTFILE, "w").write("free")
            log("slot released (free)")
            log("DEDICATED RUN DONE")
    else:
        print(__doc__)

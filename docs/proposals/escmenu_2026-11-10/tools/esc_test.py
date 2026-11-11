#!/usr/bin/env python3
"""esc_test.py - the in-game ESC board on PRIVATE clients. Nothing is deployed anywhere.

Clients:  H:\\hzm_work\\escmenu\\client (+ client2): byte copies of the LIVE G:\\mohaa-gl2 DLLs; openmohaa.exe = the live
          v1.10.73 exe (--before) or the escmenu build (default). basepath = the GOG tree, read only. home on H:. The board
          rides in ONE test pak in the home (built from H:\\hzm_work\\escmenu\\mod unless --before). Started ONLY through
          harness_window.launch_background, ON THE 1920x1080 SCREEN (HZM_TEST_RES=1920x1080): never focused, guard
          enforced, job object, muted (s_volume 0 + the coop un-mute cvars zeroed after autoexec), in_mouse 0,
          in_nograb 1, in_gamepad 0, in_joystick 0. Input = keys / clicks posted to OUR window. Any guard trip ends the run.

    python esc_test.py pak
    python esc_test.py shots  --mode sp|coop|mp [--res 1600x900] [--before]     ESC board stills (+ confirm stills)
    python esc_test.py buttons --mode sp|coop|mp [--res ...]                     every row's command, then its effect
    python esc_test.py leave --mode coop|mp|sp                                    the LEAVE path end to end (real clicks)
    python esc_test.py coopjoin / dedjoin                                         a second client on a listen / dedicated server
Results: H:\\hzm_work\\escmenu\\runs\\<case>\\ (log, result.json, stills)."""
import json, os, re, shutil, subprocess, sys, time, zipfile

TOOLS = r"C:\mohaa-coop-dev\docs\tools"
sys.path.insert(0, TOOLS)
os.environ.setdefault("HZM_TEST_RES", "1920x1080")
import harness_guard as hg     # noqa: E402
import harness_window as hw    # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
ROOT = r"H:\hzm_work\escmenu"
MOD = os.path.join(ROOT, "mod")
RUNS = os.path.join(ROOT, "runs")
PAK = "zzzzzzzzzzzzzzzzzzzzzz_escmenu.pk3"
PAK_FILES = ["ui/dm_main.urc", "ui/hzm_escconfirm.urc"]
VK = {"F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "ESC": 0x1B}
TRIPPED = []
MUTE = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set coop_joinCard 0", "set coop_whatsNewSeen 99999",
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
        "set developer 1", "set logfile 2", "seta ui_atticMain 1"]
BINDS = ['bind F5 "exec es_a.cfg"', 'bind F6 "exec es_b.cfg"', 'bind F7 "exec es_c.cfg"', 'bind F8 "exec es_d.cfg"',
         'bind F9 "exec es_e.cfg"', 'bind F10 "exec es_k.cfg"', 'bind F11 "screenshotJPEG"']
SPAWN = ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "set s_volume 0"]


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def read(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


class C:
    """one private client folder"""
    def __init__(self, folder="client", port=12971):
        self.dir = os.path.join(ROOT, folder)
        self.home = os.path.join(self.dir, "home")
        self.mt = os.path.join(self.home, "maintt")
        self.port = port
        os.makedirs(self.mt, exist_ok=True)

    def log(self):
        return os.path.join(self.mt, "qconsole.log")

    def cmd(self, name, lines):
        open(os.path.join(self.mt, name), "w", newline="\n").write("\n".join(lines) + "\n")


def build_pak(c, before=False):
    out = os.path.join(c.mt, PAK)
    if os.path.exists(out):
        os.remove(out)
    if before:
        return None
    with zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for rel in PAK_FILES:
            z.write(os.path.join(MOD, rel), rel)
    os.replace(out + ".tmp", out)
    return out


def use_exe(c, before):
    """the exe must be NAMED openmohaa.exe (the NVIDIA driver keys on it, bug-3062): copy the wanted build over it"""
    src = os.path.join(c.dir, "openmohaa_v1073.exe" if before else
                       ("openmohaa_esctest.exe" if os.path.exists(os.path.join(c.dir, "openmohaa_esctest.exe")) else "openmohaa_escmenu.exe"))
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(c.dir, "openmohaa.exe"))
    return "openmohaa.exe"


def guard(cl):
    v = getattr(getattr(cl, "watcher", None), "violations", None)
    if v:
        TRIPPED.append(repr(v))
    return bool(TRIPPED)


def user_playing():
    try:
        return [p for p in hg.classify() if p.get("cls") == "USER"]
    except Exception:  # noqa: BLE001
        return []


def launch(c, exe, extra=(), w=1600, h=900, tail=()):
    for fn in os.listdir(c.mt):
        if fn.lower().endswith(".pid") or fn == "qconsole.log":
            os.remove(os.path.join(c.mt, fn))
    base = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", c.home), ("cl_renderer", "opengl2"),
            ("r_fullscreen", "0"), ("developer", "1"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"),
            ("in_mouse", "0"), ("in_nograb", "1"), ("s_volume", "0"), ("name", "EscTester"), ("net_port", str(c.port))]
    args = [os.path.join(c.dir, exe)]
    for k, v in list(base) + list(extra):
        args += ["+set", k, v]
    args += ["+exec", "es_on.cfg"] + list(tail)
    d = hw.test_display()
    args, late = hw.apply_policy(args, width=w, height=h, display=d)
    c.cmd("es_on.cfg", MUTE + BINDS + late)
    env = {"SDL_MOUSE_AUTO_CAPTURE": "0", "SDL_HINT_MOUSE_AUTO_CAPTURE": "0"}
    return hw.launch_background(args[0], args[1:], c.dir, env=env, policy=False, display=d, below_normal=True,
                                watch_audio=True, log=lambda *a: None)


def wait_for(c, pat, timeout, start=0, cl=None):
    t = time.time()
    while time.time() - t < timeout:
        if re.search(pat, read(c.log())[start:]):
            return True
        if cl is not None and guard(cl):
            return False
        time.sleep(1)
    return False


def press_until(c, cl, key, cfg, tries=8):
    """press a bound key until the log shows its cfg ran (a menu veil can swallow a key)"""
    for _ in range(tries):
        n0 = len(read(c.log()))
        cl.post_key(VK[key])
        if wait_for(c, re.escape("execing " + cfg), 6, n0, cl):
            return True
    return False


def press(cl, key, settle=1.5):
    cl.post_key(VK[key])
    time.sleep(settle)


def shot(c, cl, out, name):
    sd = os.path.join(c.mt, "screenshots")
    before = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    press(cl, "F11", 2.5)
    after = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    new = sorted(after - before)
    if new:
        dst = os.path.join(out, name + ".jpg")
        shutil.copyfile(os.path.join(sd, new[-1]), dst)
        return dst
    dst = os.path.join(out, name + ".png")
    try:
        cl.capture_png(dst)
        return dst
    except Exception as e:  # noqa: BLE001
        return "shot failed %r" % e


def vclick(c, cl, vx, vy, w=None, h=None):
    """a click at a 640x480 menu point through the UI's own click path (private test exe: hzm_testclick puts the cursor
    there and runs the UI's hover/press/release frames). ui_clickdebug 1 logs where it landed (UICLICK)."""
    c.cmd("es_k.cfg", ["set ui_clickdebug 1", "hzm_testclick %g %g" % (vx, vy)])
    n0 = len(read(c.log()))
    cl.post_key(VK["F10"])
    wait_for(c, r"UICLICK UP", 5, n0, cl)
    m = re.findall(r"UICLICK (?:DOWN|UP) pos (\d+),(\d+) view '([^']*)'", read(c.log())[n0:])
    return m[-1] if m else None


START = {
    # the real start paths: SP = the attic's NEW GAME command form (difficulty + spmap); coop / MP = the Apply path
    "sp": ["difficultymedium", "spmap m1l1"],
    "coop": ["set ui_dmmap m1l1", "exec coop_mod/start_server.cfg"],
    "mp": ["set g_gametype 2", "set ui_gametype 2", "set ui_dmmap dm/mohdm1", "set sv_hostname EscMP", "ui_startdmmap 2"],
}
READY = {"sp": r"Starting game|CL_InitCGame|\^~\^~\^", "coop": r"EscTester has joined|coop_isCoopSession|entered the game",
         "mp": r"EscTester has joined|entered the game"}


def boot_mode(c, cl, mode, res):
    wait_for(c, r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, cl=cl)
    time.sleep(12)
    c.cmd("es_a.cfg", START[mode])
    n0 = len(read(c.log()))
    res["started"] = press_until(c, cl, "F5", "es_a.cfg")
    res["loaded"] = wait_for(c, r"Sound End Registration Complete", 240, n0, cl)
    time.sleep(15)
    # into the game: close any join/briefing menu, pick a weapon (MP), fire once to spawn
    c.cmd("es_b.cfg", SPAWN + ["popmenu 0", "wait 20", "popmenu 0", "wait 20", "join_team allies", "wait 300", "primarydmweapon rifle", "wait 20",
                               "popmenu 0", "wait 20", "+attackprimary", "wait 10", "-attackprimary", "wait 30"] + SPAWN)
    press(cl, "F6", 6)
    press(cl, "F6", 6)
    c.cmd("es_c.cfg", ["echo ESCSTATE gt=$cg_gametype", "cg_gametype", "coop_isCoopSession", "sv_running", "mapname",
                       "ui_hzmEscTitle"] + SPAWN)
    press(cl, "F7", 2)
    c.cmd("es_e.cfg", ["popmenu 0", "wait 20", "popmenu 0", "wait 20", "popmenu 0"])
    press(cl, "F9", 3)


def case_shots(mode, out, res):
    before = "--before" in sys.argv
    w, h = [int(x) for x in opt("--res", "1600x900").split("x")]
    c = C()
    build_pak(c, before)
    exe = use_exe(c, before)
    with launch(c, exe, w=w, h=h, extra=[("cheats", "1")]) as cl:
        boot_mode(c, cl, mode, res)
        if guard(cl):
            return
        res["ingame"] = shot(c, cl, out, "%s_%dx%d_game" % (mode, w, h))
        press(cl, "ESC", 2)
        res["esc"] = shot(c, cl, out, "%s_%dx%d_esc" % (mode, w, h))
        if not before:
            for ask, nm in (("1", "leave"), ("2", "quit")):
                c.cmd("es_d.cfg", ["set ui_hzmEscAsk " + ask, "pushmenu hzm_escconfirm"])
                press(cl, "F8", 2)
                res["confirm_" + nm] = shot(c, cl, out, "%s_%dx%d_confirm_%s" % (mode, w, h, nm))
                press(cl, "ESC", 1.5)      # STAY = back to the board
            res["after_confirm"] = shot(c, cl, out, "%s_%dx%d_back" % (mode, w, h))
            press(cl, "ESC", 2)
            res["resumed"] = shot(c, cl, out, "%s_%dx%d_resumed" % (mode, w, h))
        guard(cl)
        res["report"] = repr(cl.report())[:300]
    shutil.copyfile(c.log(), os.path.join(out, "qconsole.log"))


def rows(mode, path=None):
    """[(key, title, cx, cy)] for the mode's rows, in order, from the generated board"""
    txt = read(path or os.path.join(MOD, "ui", "dm_main.urc"))
    out = []
    for blk in txt.split("resource")[1:]:
        m = re.search(r'name "hzm_esc_%s_([a-z]+)"' % mode, blk)
        if not m or "Button" not in blk.split("{")[0]:
            continue
        r = [int(v) for v in re.search(r"rect (\d+) (\d+) (\d+) (\d+)", blk).groups()]
        t = re.search(r'name "hzm_esc_%s_%s_txt"\s*title "([^"]*)"' % (mode, m.group(1)), txt)
        out.append((m.group(1), t.group(1) if t else m.group(1), r[0] + r[2] / 2.0, r[1] + r[3] / 2.0))
    return out


RESET = ["popmenu 0", "wait 30", "popmenu 0", "wait 30", "popmenu 0", "wait 30", "popmenu 0"] + SPAWN


def case_buttons(mode, out, res):
    """every row by a REAL click (WM_MOUSEMOVE + WM_LBUTTONDOWN/UP posted to our window): open the board, click the
    row, still + the log lines it caused, reset. The leave row is clicked last and LEAVE is clicked for real."""
    w, h = [int(x) for x in opt("--res", "1600x900").split("x")]
    c = C()
    build_pak(c)
    skip = opt("--skip", "").split(",")
    with launch(c, use_exe(c, False), w=w, h=h, extra=[("cheats", "1")]) as cl:
        boot_mode(c, cl, mode, res)
        c.cmd("es_e.cfg", RESET)
        res["rows"] = {}
        for key, title, vx, vy in rows(mode):
            if guard(cl) or key in skip or key in ("quit",):
                continue
            press(cl, "ESC", 2.5)
            n0 = len(read(c.log()))
            res["rows"][key] = {"at": vclick(c, cl, vx, vy, w, h)}
            time.sleep(4 if key not in ("main", "report", "armory") else 8)
            res["rows"][key]["shot"] = shot(c, cl, out, "%s_row_%s" % (mode, key))
            new = read(c.log())[n0:]
            res["rows"][key]["log"] = [l[31:] for l in new.splitlines()
                                       if re.search(r"exec|menu|MENUDBG|Unknown|ERROR|COOPSAVE|disconnect|spectat|team",
                                                    l, re.I)][:12]
            if key == "leave":
                # the confirm card is up: LEAVE for real
                n1 = len(read(c.log()))
                vclick(c, cl, 320 - 150 + 16 + 60, 240 - 59 + 118 - 34 + 11, w, h)
                time.sleep(12)
                res["leave_done"] = shot(c, cl, out, "%s_after_leave" % mode)
                L = read(c.log())[n1:]
                res["leave_log"] = [l[31:] for l in L.splitlines() if re.search(r"COOPSAVE|Shutdown|disconnect|has left", l)][:10]
                break
            press_until(c, cl, "F9", "es_e.cfg", 3)
            time.sleep(2)
        guard(cl)
        res["report"] = repr(cl.report())[:300]
    shutil.copyfile(c.log(), os.path.join(out, "qconsole.log"))


SRV_HOME = os.path.join(ROOT, "server_home")
SRV_PORT = 12975


def start_dedicated(mode):
    """a muted dedicated server (omohaaded, our copy of the live one), the real coop start cvars for coop
    (coop_mod/start_server.cfg minus ui_startdmmap, then `map`, as launch_dedicated_2player.ps1 does)"""
    mt = os.path.join(SRV_HOME, "maintt")
    os.makedirs(mt, exist_ok=True)
    lg = os.path.join(mt, "qconsole.log")
    if os.path.exists(lg):
        os.remove(lg)
    lines = ["set s_volume 0", "set s_musicvolume 0", "set sv_hostname EscDed", "set logfile 2", "set developer 1"]
    if mode == "coop":
        src = read(os.path.join(MOD, "coop_mod", "start_server.cfg")).splitlines()
        lines += [l for l in src if not re.match(r"\s*ui_startdmmap", l)]
        # [guard trip 2026-11-10] player.scr / tinnitus.scr stuff `s_volume <SERVER's coop_tinnitusBaseVol>` (and fixed
        # muffle volumes) into every client on spawn: a muted client becomes audible unless the SERVER's cvars are 0
        lines += ["seta coop_tinnitusBaseVol 0", "seta coop_tinnitusMuffle 0", "seta coop_woundMuffleVol 0", "map m1l1"]
    else:
        lines += ["set g_gametype 2", "map dm/mohdm1"]
    open(os.path.join(mt, "es_ded.cfg"), "w", newline="\n").write("\n".join(lines) + "\n")
    args = [os.path.join(ROOT, "client", "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", SRV_HOME, "+set", "dedicated", "1", "+set", "net_port", str(SRV_PORT),
            "+set", "net_ip", "127.0.0.1", "+set", "sv_maxclients", "8", "+set", "g_gametype", "2",
            "+set", "s_volume", "0", "+exec", "es_ded.cfg"]
    p = subprocess.Popen(args, cwd=os.path.join(ROOT, "client"), **hw.popen_kwargs())
    return p, lg


def case_dedjoin(mode, out, res):
    """a client joins a DEDICATED server (mode coop|mp): the board's JOINED variant, the confirm's joined text,
    and DISCONNECT -> LEAVE for real; the server log must show this player's save flush on the way out"""
    w, h = [int(x) for x in opt("--res", "1600x900").split("x")]
    srv, slog = start_dedicated(mode)
    res["server_pid"] = srv.pid
    try:
        t = time.time()
        while time.time() - t < 240 and not re.search(r"Sound End Registration|------ Server Initialization Complete|"
                                                       r"Level ready|Fixme|ERROR", read(slog)):
            time.sleep(2)
        time.sleep(20)
        c = C()
        build_pak(c)
        START[mode + "_join"] = ["connect 127.0.0.1:%d" % SRV_PORT]
        with launch(c, use_exe(c, False), w=w, h=h) as cl:
            boot_mode(c, cl, mode + "_join", res)
            press(cl, "ESC", 2.5)
            res["esc"] = shot(c, cl, out, "%s_ded_esc" % mode)
            lv = [r for r in rows(mode) if r[0] == "leave"][0]
            vclick(c, cl, lv[2], lv[3], w, h)
            time.sleep(3)
            res["confirm"] = shot(c, cl, out, "%s_ded_confirm" % mode)
            n1 = len(read(slog))
            vclick(c, cl, 246, 276, w, h)
            time.sleep(12)
            res["after_leave"] = shot(c, cl, out, "%s_ded_after_leave" % mode)
            res["server_leave_log"] = [l for l in read(slog)[n1:].splitlines()
                                       if re.search(r"COOPSAVE|has left|disconnect", l, re.I)][:8]
            guard(cl)
            res["report"] = repr(cl.report())[:300]
        shutil.copyfile(c.log(), os.path.join(out, "qconsole.log"))
    finally:
        srv.kill()
        shutil.copyfile(slog, os.path.join(out, "server_qconsole.log")) if os.path.exists(slog) else None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    case = sys.argv[1]
    if case == "pak":
        print(build_pak(C()))
        return
    if user_playing():
        print("NOTE user game running: tests stay on the 1080p screen (HZM_TEST_RES=%s)" % os.environ["HZM_TEST_RES"])
    mode = opt("--mode", "coop")
    tag = "%s_%s_%s%s" % (case, mode, opt("--res", "1600x900"), "_before" if "--before" in sys.argv else "")
    out = os.path.join(RUNS, tag)
    os.makedirs(out, exist_ok=True)
    res = {"case": case, "mode": mode}
    try:
        {"shots": case_shots, "buttons": case_buttons, "dedjoin": case_dedjoin}[case](mode, out, res)
    finally:
        res["tripped"] = TRIPPED
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
        print(json.dumps(res, indent=1))
        if TRIPPED:
            print("GUARD TRIPPED - stop all launches")


if __name__ == "__main__":
    main()

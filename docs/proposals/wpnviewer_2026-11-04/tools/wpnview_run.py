"""wpnview_run.py - harness for the attic weapon viewer on the private client G:\\mohaa-wpnview (never the live install).

    python wpnview_run.py setup [exe]                  overlay pk3 from the wpnviewer mod worktree (+ the exe to test)
    python wpnview_run.py sheet <res> <first> <last>    every entry first..last: page, settle, screenshotJPEG (contact-sheet input)
    python wpnview_run.py views <res> [tag]             attic -> rack hotspot fly -> viewer; spin / tilt / zoom / reset; mouse drag;
                                                       variant / gun / tab stepping; ESC home
Runs on DISPLAY2 through docs/tools/harness_window (background window policy); RES: 43 = 1440x1080, 720 = 1280x720, 219 = 1920x804.
"""
import os, re, shutil, sys, time, zipfile
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\e5")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402
import e5_run as E  # noqa: E402

CLIENT = r"G:\mohaa-wpnview"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
RUNS = r"H:\hzm_work\wpnviewer\runs"
MOD = os.environ.get("WV_MOD", r"H:\hzm_work\wpnviewer-mod")
MENUS3D = os.environ.get("WV_MENUS3D", r"C:/mohaa-coop-dev/hzm-mohaa-coop-mod/zzzzzzzzzzzzzz_hzm_menus3d.pk3")
OVERLAY = "zzzzzzzzzzzzzzzzzzz_wpnview_ui.pk3"
RES = {"720": (1280, 720, 0), "1080": (1920, 1080, 0), "43": (1440, 1080, 1), "219": (1920, 804, 0)}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def setup(exe=None):
    if exe:
        shutil.copyfile(exe, os.path.join(CLIENT, "openmohaa.exe"))
    shutil.copyfile(MENUS3D, os.path.join(MAINTT, "zzzzzzzzzzzzzz_hzm_menus3d.pk3"))
    ui = os.path.join(MOD, "ui")
    with zipfile.ZipFile(os.path.join(MAINTT, OVERLAY), "w", zipfile.ZIP_DEFLATED) as z:
        for f in ("main.urc", "hzm_wpnview.urc", "hzm_attic_go_rack.cfg"):
            z.write(os.path.join(ui, f), "ui/" + f)
        for f in ("springfield_m1903.tik", "KAR98sniper_g98scope.tik"):        # the two variant tiks fixed on this branch
            z.write(os.path.join(MOD, "models", "weapons", f), "models/weapons/" + f)
        z.write(os.path.join(MOD, "global", "localization_coop.txt"), "global/localization_coop.txt")
        for f in sorted(os.listdir(os.path.join(ui, "wpnview"))):
            z.write(os.path.join(ui, "wpnview", f), "ui/wpnview/" + f)
    log("setup ok", os.path.getsize(os.path.join(CLIENT, "openmohaa.exe")))


class Script:
    def __init__(self):
        self.S, self.t = ["@hold", "@attach 0"], 1500

    def cmd(self, c, dt=60):
        assert len(c) < 63, c
        self.S.append("@cmd %d %s" % (self.t, c))
        self.t += dt

    def at(self, xy, dt=300):
        self.S.append("@cursor %d %d %d" % (self.t, xy[0], xy[1]))
        self.t += dt

    def mbtn(self, down, dt=100):
        self.S.append("@mbtn %d 1 %d" % (self.t, 1 if down else 0))
        self.t += dt

    def mouse(self, dx, dy, dt=30):
        self.S.append("@mouse %d %d %d" % (self.t, dx, dy))
        self.t += dt

    def pad(self, btn=0, rx=0, ry=0, dt=150):
        self.S.append("%d 0 0 %d %d 0 0 %d" % (self.t, rx, ry, btn))
        self.t += dt

    def write(self, name):
        os.makedirs(RUNS, exist_ok=True)
        p = os.path.join(RUNS, name)
        open(p, "w", newline="\n").write("\n".join(self.S) + "\n")
        assert len(self.S) < 2040
        return p


def launch(tag, res, script, lines=(), budget=600):
    w, h, center = RES[res]
    sp = script.write(tag + ".txt")
    shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    shutil.rmtree(SHOTS, ignore_errors=True)
    os.makedirs(SHOTS, exist_ok=True)
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", E.GOG, "+set", "fs_homepath", HOME,
            "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", str(w), "+set", "r_customheight", str(h),
            "+set", "r_fullscreen", "0", "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "r_picmip", "0", "+set", "com_maxfps", "60",
            "+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "in_padTestScript", sp.replace("\\", "/"), "+exec", "wv_run.cfg"]
    args, late = hw.apply_policy(args, width=w, height=h)
    boot = ["set developer 1", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set coop_hardcore 0",
            "wait 9000", "echo ^~^~^ WV start", "set in_padTestGo 1"]
    open(os.path.join(MAINTT, "wv_run.cfg"), "w", newline="\n").write("\n".join(late + list(lines) + boot) + "\n")
    if hg.user_game_running():
        raise SystemExit("user game running")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    t0 = time.time()
    try:
        while time.time() - t0 < budget:
            if c.watcher.violations:
                log("VIOLATION", c.watcher.violations[:3])
                break
            if c.proc.poll() is not None:
                break
            time.sleep(1)
    finally:
        if c.proc.poll() is None:
            c.proc.kill()
        c.close()
    out = os.path.join(RUNS, tag)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for fn in sorted(os.listdir(SHOTS)):
        shutil.move(os.path.join(SHOTS, fn), os.path.join(out, fn))
    shutil.copyfile(LOG, os.path.join(out, "qconsole.log"))
    lg = open(LOG, errors="ignore").read()
    errs = [l for l in lg.splitlines() if re.search(r"Script Error|ERROR|couldn't load|Couldn't find|Unknown command|WARNING", l, re.I)]
    log("run", tag, "shots", len(os.listdir(out)) - 1, "GL2" if "renderer_opengl2" in lg else "NOT GL2", "log hits", len(errs))
    for l in errs[:40]:
        print("   ", l)
    return out


def open_viewer(s):
    s.cmd("echo ^~^~^ WV boot", 3000)
    s.cmd("screenshotJPEG v_00_attic", 400)
    s.cmd("exec ui/hzm_attic_go_rack.cfg", 2200)


def sheet(res, a, b):
    s = Script()
    open_viewer(s)
    for n in range(int(a), int(b) + 1):
        s.cmd("exec ui/wpnview/e%03d.cfg" % n, 450)
        s.cmd("screenshotJPEG w_%03d" % n, 250)
    s.cmd("quit", 0)
    return launch("sheet_%s_%s_%s" % (res, a, b), res, s, budget=120 + (int(b) - int(a)) * 2)


def views(res, tag="v"):
    w, h, center = RES[res]
    s = Script()
    shot = lambda nm, dt=450: s.cmd("screenshotJPEG v_%s" % nm, dt)  # noqa: E731
    s.cmd("echo ^~^~^ WV boot", 3000)
    shot("00attic")
    s.cmd("set ui_scene_hot 17", 600)
    shot("01rack_hover")
    s.cmd("set ui_scene_hot 0", 100)
    s.cmd("exec ui/hzm_attic_go_rack.cfg", 300)
    shot("02flying", 1700)
    shot("03viewer")
    for nm, c in (("04spin60", "set ui_wvSpin 60"), ("05tilt35", "set ui_wvTilt 35"), ("06spin200", "set ui_wvSpin 200"),
                  ("07tiltm80", "set ui_wvTilt -80"), ("08zoom", "vstr ui_wvZoomNext"), ("09zoom2", "vstr ui_wvZoomNext"),
                  ("10reset", "set ui_wvSpin 0;set ui_wvTilt 0;exec ui/wpnview/z0.cfg"),
                  ("11nextvar", "vstr ui_wvNextV"), ("12nextvar", "vstr ui_wvNextV"), ("13nextgun", "vstr ui_wvNextG"),
                  ("14tab2", "exec ui/wpnview/t2.cfg"), ("15tab3", "exec ui/wpnview/t3.cfg"), ("16tab5", "exec ui/wpnview/t5.cfg"),
                  ("17tab4", "exec ui/wpnview/t4.cfg"), ("18tab0", "exec ui/wpnview/t0.cfg")):
        s.cmd(c, 500)
        shot(nm)
    # a real mouse drag across the viewer (cursor in the viewer's middle, button held, motion), then the wheel
    cx, cy = int(w / 2 + (317 - 320) * h / 480.0), int((206) * h / 480.0)
    s.at((cx, cy), 400)
    s.mbtn(True, 150)
    for _ in range(20):
        s.mouse(9, 4, 40)
    s.mbtn(False, 400)
    shot("19dragged")
    s.cmd("echo ^~^~^ WV spin $ui_wvSpin", 50)
    s.cmd("cvarlist ui_wv", 300)
    # pad: right stick held right then down (turns the model), D-pad focus moves, B = back
    s.pad(0, 28000, 0, 900)
    s.pad(0, 0, 0, 200)
    shot("20padstick")
    s.pad(0, 0, 22000, 700)
    s.pad(0, 0, 0, 200)
    shot("21padstick2")
    s.cmd("cvarlist ui_wv", 300)
    s.pad(1 << 12, 0, 0, 120)
    s.pad(0, 0, 0, 400)
    shot("22pad_down")
    s.cmd("ui_escape", 50) if False else None
    s.pad(1 << 1, 0, 0, 120)
    s.pad(0, 0, 0, 1600)
    shot("23back_home")
    s.cmd("quit", 0)
    return launch("views_%s_%s" % (res, tag), res, s, budget=200)


def shots(res, tag, *cmds):
    """open the viewer, then each argument = console commands separated by '|' (each < 63 chars) followed by one still"""
    s = Script()
    open_viewer(s)
    for i, c in enumerate(cmds):
        for part in c.split("|"):
            s.cmd(part, 120)
        s.cmd("wait 1", 450)
        s.cmd("screenshotJPEG x_%02d" % i, 250)
    s.cmd("quit", 0)
    return launch("shots_%s_%s" % (res, tag), res, s, budget=200)


def ingame(res="720"):
    """the in-game path: a map running, ESC -> Main Menu (the attic), the rack, the viewer, back"""
    s = Script()
    s.cmd("echo ^~^~^ WV boot", 26000)
    s.cmd("screenshotJPEG g_00_game", 400)
    s.cmd("pushmenu main", 2500)
    s.cmd("screenshotJPEG g_01_mainmenu", 400)
    s.cmd("exec ui/hzm_attic_go_rack.cfg", 2300)
    s.cmd("screenshotJPEG g_02_viewer", 400)
    s.cmd("exec ui/wpnview/e237.cfg", 600)
    s.cmd("set ui_wvSpin 40;set ui_wvTilt 20", 600)
    s.cmd("screenshotJPEG g_03_stg", 400)
    s.pad(1 << 1, 0, 0, 120)
    s.pad(0, 0, 0, 1800)
    s.cmd("screenshotJPEG g_04_back", 400)
    s.cmd("quit", 0)
    return launch("ingame_%s" % res, res, s, lines=["set g_gametype 2", "set sv_maxclients 4", "map dm/mohdm1"], budget=150)


if __name__ == "__main__":
    a = sys.argv[1:]
    {"setup": setup, "sheet": sheet, "views": views, "shots": shots, "ingame": ingame}[a[0]](*a[1:])

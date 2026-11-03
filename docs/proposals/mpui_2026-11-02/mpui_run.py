"""mpui_run.py - harness for the modernised multiplayer front-end on the private client G:\\mohaa-mpui (a copy of the mphub
client: never the live install). Reuses e5_run.launch (DISPLAY2, background window policy) like mphub_run.py.

    python mpui_run.py setup                 exe from the mpui engine build + the ship pk3 + an overlay pk3 of the mpui worktree's ui
    python mpui_run.py walk <43|720|219|1080|2160> [slow]   mouse: attic -> hub; JOIN (internet, LAN, select, favourite,
                                             favourites tab, filters), ARMORY, SERVICE RECORD, HOST (board -> coop -> desk,
                                             campaign, tile); stills at every stop
    python mpui_run.py host <res>            HOST GAME -> HZM coop -> Tunisia -> first tile -> LAUNCH MISSION: a real listen server
                                             (ui_gamespy 0: never listed on the master; net_port 12290: clear of the public servers)
    python mpui_run.py pad <res>             pad only: hub D-pad to the red door, A, D-pad into the roster, A on a row, B back
    python mpui_run.py film [res]            dense frames for the MP4 (the whole tour), assembled by make_mp4 in this file
Before every launch: no openmohaa*.exe three times 10 s apart, and the release flag present (the coordinator's rule)."""
import math, os, re, shutil, subprocess, sys, time, zipfile
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\e5")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import e5_run as E  # noqa: E402
import scene_params as SP  # noqa: E402

CLIENT = r"G:\mohaa-mpui"
E.CLIENT = CLIENT
E.EXE = os.path.join(CLIENT, "openmohaa.exe")
E.HOME = os.path.join(CLIENT, "home")
E.MAINTT = os.path.join(E.HOME, "maintt")
E.LOG = os.path.join(E.MAINTT, "qconsole.log")
E.SHOTS = os.path.join(E.MAINTT, "screenshots")
E.RUNS = r"H:\hzm_work\mpui\runs"
E.RES["1080"] = (1920, 1080, 0, "s")
E.RES["2160"] = (3840, 2160, 0, "s")
MOD = r"C:\mohaa-coop-dev\hzm-mod-mpui"
SHIP = r"H:\hzm_work\mpui\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3"
NEWEXE = r"H:\hzm_work\mpui\build\Release\openmohaa.exe"
OVERLAY = "zzzzzzzzzzzzzzzzzz_mpui_ui.pk3"
FLAG = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\release_done.flag"
_launch0 = E.launch


def quiet_wait():
    n = 0
    while n < 3:
        busy = "openmohaa" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower() or not os.path.exists(FLAG)
        n = 0 if busy else n + 1
        if busy:
            E.log("waiting: a game client is up or a release build runs")
        time.sleep(10)


def launch(tag, w, h, lines, extra=()):
    quiet_wait()
    out = _launch0(tag, w, h, lines, extra)
    lg = open(os.path.join(out, "qconsole.log"), errors="ignore").read()
    ok = 'Trying to load "renderer_opengl2.dll"' in lg
    print("^^ RENDERER %s: %s" % (tag, "renderer_opengl2.dll CONFIRMED" if ok else "NOT GL2"), flush=True)
    errs = [l for l in lg.splitlines() if re.search(r"Script Error|ERROR|couldn't load|Couldn't find|WARNING: .*(urc|menu)|Unknown event|unknown command", l, re.I)]
    print("^^ log errors: %d" % len(errs), *errs[:20], sep="\n   ")
    return out


UIFILES = ["multiplayer.urc", "joingame.urc", "coop_start.urc", "coop_maps.inc", "multiplayerstart.urc", "coop_mp_options.urc", "coop_sr.urc",
           "hzm_mapnames.txt"]


def setup():
    shutil.copy2(NEWEXE, E.EXE)
    B = os.path.dirname(os.path.dirname(NEWEXE))     # the whole set from the same tree (REF_API / cgame / game must match the exe)
    for rel in ("code/client/cgame/Release/cgame.dll", "code/server/fgame/Release/game.dll",
                "code/renderercommon/renderergl1/Release/renderer_opengl1.dll", "code/renderercommon/renderergl2/Release/renderer_opengl2.dll"):
        shutil.copy2(os.path.join(B, rel), CLIENT)
    shutil.copyfile(SHIP, os.path.join(E.MAINTT, os.path.basename(SHIP)))
    with zipfile.ZipFile(os.path.join(E.MAINTT, OVERLAY), "w", zipfile.ZIP_DEFLATED) as z:
        for f in UIFILES + [x for x in os.listdir(os.path.join(MOD, "ui")) if x.startswith("hzm_mpui_scene_")]:
            z.write(os.path.join(MOD, "ui", f), "ui/" + f)
        z.write(os.path.join(MOD, "global", "localization_coop.txt"), "global/localization_coop.txt")
    print("setup:", os.listdir(E.MAINTT), os.path.getsize(E.EXE))


def urc(name):
    return open(os.path.join(MOD, "ui", name), "rb").read().decode("latin-1").replace("\r\n", "\n")


def scene_info(text, scene):
    blk = text[text.index('name "%s"' % scene):]
    blk = blk[:blk.index("\n}\n")]
    cam = [float(v) for v in re.search(r"(?m)^scenecam (.*)$", blk).group(1).split()]
    hots = {m.group(1): np.array([float(m.group(2)), float(m.group(3)), float(m.group(4))]) for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+)', blk)}
    boxes = {m.group(1): [float(v) for v in m.groups()[1:]] for m in re.finditer(r'(?m)^scenehotbox "(\w+)" (\S+) (\S+) (\S+) (\S+)', blk)}
    return cam, hots, boxes


def hot_px(cam, pt, box, w, h):
    org, ang, fovy = np.array(cam[:3]), cam[3:6], cam[6]
    f, left, up = SP.axes_from_angles(*ang)
    c = np.asarray(pt) - org
    x, y, z = c @ f, c @ left, c @ up
    F = (h / 2) / math.tan(math.radians(fovy) / 2)
    sx, sy = w / 2 - y / x * F, h / 2 - z / x * F
    if box:
        sx += box[0] * h / 1080.0
        sy += box[1] * h / 1080.0
    return int(sx), int(sy)


def vpx(rect, w, h, center):
    x, y, rw, rh = rect
    if center:
        s = h / 480.0
        return int((w - 640 * s) / 2 + (x + rw / 2) * s), int((y + rh / 2) * s)
    return int((x + rw / 2) * w / 640.0), int((y + rh / 2) * h / 480.0)


def rect_of(name, urcfile):
    t = urc(urcfile)
    m = re.search(r'(?:title[^\n]*\n)?name\s+"%s"\s*\n(?:\s*title[^\n]*\n)?\s*rect\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)' % re.escape(name), t)
    return tuple(int(v) for v in m.groups())


class Script:
    def __init__(self, w, h, slow):
        self.S, self.t, self.w, self.h, self.slow = ["@hold", "@attach 0"], 1500, w, h, slow
        self.fr = 0
        self.film = None

    def cmd(self, c, dt=60):
        self.S.append("@cmd %d %s" % (self.t, c))
        self.t += dt

    def state(self, b):
        self.S.append("%d 0 0 0 0 0 0 %d" % (self.t, b))

    def press(self, b, wait=700):
        self.state(b)
        self.t += 150
        self.state(0)
        self.t += wait

    def at(self, xy, wait=700):
        self.S.append("@cursor %d %d %d" % (self.t, xy[0], xy[1]))
        self.t += wait

    def mark(self, s):
        self.cmd("echo ^~^~^ MPUI %s" % s)

    def write(self, name):
        p = os.path.join(E.RUNS, name)
        os.makedirs(E.RUNS, exist_ok=True)
        open(p, "w", newline="\n").write("\n".join(self.S) + "\n")
        return p


def boot_lines(center, slow, extra=()):
    return ["set developer 1", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow,
            "set in_padDebug 1", "set ui_clickdebug 1", "set ui_gamespy 0", "set ui_sbFavs \"\"", "set ui_sbCoopOnly 0", "set ui_sbHideFull 0",
            "set ui_sbHideEmpty 0", "set ui_sbSearch \"\""] + list(extra) + ["wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]


def boot_args(center, sp):
    return ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "net_port", "12290",
            "+set", "in_padTestScript", sp.replace("\\", "/")]


def tour(s, res, w, h, center, k, shot, deep=True, host=False):
    """the shared route: attic -> hub -> every place and back. shot(name, wait) takes a still (or nothing in film mode)."""
    acam, ahot, abox = scene_info(urc("main.urc") if os.path.exists(os.path.join(MOD, "ui", "main.urc")) else "", "atticscene")
    hcam, hhot, hbox = scene_info(urc("multiplayer.urc"), "hubscene")
    J = "joingame.urc"

    def btn(name, f, wait=700):
        s.at(vpx(rect_of(name, f), w, h, center), wait)

    s.at(hot_px(acam, ahot["mp"], abox.get("mp"), w, h))
    s.mark("attic MP door")
    s.press(0x1, 0)
    s.t += int(2000 * k)
    shot("01hub", 400)

    def hub(n, wait=900):
        s.at(hot_px(hcam, hhot[n], hbox.get(n), w, h), wait)

    # ---- JOIN GAME: the red door -> the roster
    hub("join")
    shot("10join_hover")
    s.mark("click JOIN")
    s.press(0x1, 0)
    s.t += int(300 * k)
    shot("11join_flying", 0)
    s.t += int(500 * k)
    shot("12browser_open", 200)
    s.t += 6000                                             # the master list + queries (real time)
    btn("hzmsrvlist", J, 300)
    s.at((vpx(rect_of("hzmsrvlist", J), w, h, center)[0], int(vpx((34, 98, 572, 222), w, h, center)[1] - 0.20 * 222 * h / 480)), 300)
    shot("13internet", 300)
    if deep:
        s.press(0x1, 500)                                   # select the first rows' server
        shot("14selected", 300)
        btn("favAdd", J, 300)
        s.press(0x1, 600)
        shot("15favourite", 300)
        btn("tab1", J, 200)
        s.press(0x1, 0)
        s.t += 4000
        shot("16lan", 300)
        s.at((vpx(rect_of("hzmsrvlist", J), w, h, center)[0], int(vpx((34, 98, 572, 222), w, h, center)[1] - 0.36 * 222 * h / 480)), 200)
        s.press(0x1, 400)
        shot("17lan_selected", 300)
        btn("tab2", J, 200)
        s.press(0x1, 0)
        s.t += 3500
        shot("18favourites", 300)
        btn("tab0", J, 200)
        s.press(0x1, 0)
        s.t += 6000
        btn("fltCoopOff", J, 200)
        s.press(0x1, 800)
        shot("19coop_only", 300)
        btn("fltCoopOn", J, 200)
        s.press(0x1, 500)
    s.mark("JOIN back")
    btn("back", J, 300)
    s.press(0x1, 0)
    s.t += int(250 * k)
    shot("1Ajoin_return_flying", 0)
    s.t += int(700 * k)
    shot("1Bhub_again", 300)

    # ---- ARMORY: the lockers
    hub("loadout")
    shot("20armory_hover")
    s.press(0x1, 0)
    s.t += int(1000 * k)
    shot("21armory", 400)
    btn("back", "coop_mp_options.urc", 300)
    s.press(0x1, 0)
    s.t += int(1000 * k)
    shot("22hub_again", 300)

    # ---- SERVICE RECORD: the board
    hub("record")
    shot("30record_hover")
    s.press(0x1, 0)
    s.t += int(1200 * k)
    shot("31record", 400)
    s.at(vpx((382, 452, 124, 18), w, h, center), 300)       # coop_sr backBtn (fullscreen 0, centred: same 640x480 frame)
    s.press(0x1, 0)
    s.t += int(1000 * k)
    shot("32hub_again", 300)

    # ---- HOST GAME: the board -> HZM coop -> the field desk
    hub("start")
    shot("40host_hover")
    s.press(0x1, 0)
    s.t += int(1000 * k)
    shot("41host_board", 400)
    btn("coopmodstart", "multiplayerstart.urc", 300)
    s.press(0x1, 0)
    s.t += int(300 * k)
    shot("42desk_flying", 0)
    s.t += int(700 * k)
    shot("43operation_orders", 300)
    btn("camp_e1" if host else "camp_m1", "coop_start.urc", 300)
    s.press(0x1, 600)
    shot("44campaign", 300)
    btn("coop_startMap2", "coop_maps.inc", 300)
    shot("45tile_hover", 200)
    s.press(0x1, 500)
    shot("46tile_picked", 300)
    if host:
        btn("apply", "coop_start.urc", 300)
        shot("47launch_hover", 200)
        s.mark("LAUNCH MISSION")
        s.press(0x1, 0)
        s.t += 2500
        shot("48loading", 0)
        s.t += 26000
        shot("49in_game", 500)
        s.t += 4000
        shot("4Ain_game2", 500)
        return
    btn("back", "coop_start.urc", 300)
    s.press(0x1, 0)
    s.t += int(250 * k)
    shot("47desk_return_flying", 0)
    s.t += int(800 * k)
    shot("48board_again", 300)
    s.at(vpx((8, 456, 96, 24), w, h, center), 300)
    s.press(0x1, 0)
    s.t += int(1000 * k)
    shot("49hub_again", 300)
    # ---- wooden door -> attic
    hub("main")
    s.press(0x1, 0)
    s.t += int(2200 * k)
    shot("50attic", 300)


def walk(res="43", slow=1.0, host=False):
    w, h, center, lay = E.RES[res]
    k = slow
    s = Script(w, h, slow)
    tag = "%s_%s" % ("host" if host else "walk", res)
    shot = lambda n, wait=500: s.cmd("screenshot mp_%s_%s" % (tag, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ MPUI start", 3500)
    shot("00attic")
    tour(s, res, w, h, center, k, shot, deep=not host, host=host)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mpui_%s.txt" % tag)
    extra = ["set sv_hostname \"HZM mpui harness (private)\"", "set password hzmharness%d" % (int(time.time()) % 9973)] if host else []
    return launch("mpui_" + tag, w, h, boot_lines(center, slow, extra), boot_args(center, sp))


def pad(res="43", slow=1.0):
    w, h, center, lay = E.RES[res]
    s = Script(w, h, slow)
    s.cmd("echo ^~^~^ MPUI pad start", 3500)
    s.cmd("set ui_keyNavActive 1", 100)
    s.cmd("exec ui/hzm_attic_go_mp.cfg", int(2500 * slow))
    s.cmd("screenshot mp_pad_%s_00hub" % res, 400)
    n = 1
    for name, m in (("right", 0x4000),) * 3:   # no focus at first: right x1 = the wooden door, x2 = the lockers, x3 = the red door
        s.press(m, 500)
    s.cmd("screenshot mp_pad_%s_%02d_door_focus" % (res, n), 300)
    n += 1
    s.mark("pad A door")
    s.press(0x1, 0)
    s.t += int(1500 * slow) + 6000
    s.cmd("screenshot mp_pad_%s_%02d_browser" % (res, n), 300)
    n += 1
    for name, m in (("down", 0x1000), ("up", 0x800), ("down", 0x1000)):      # D-pad: bottom bar, filter row, the roster
        s.press(m, 500)
        s.cmd("screenshot mp_pad_%s_%02d_%s" % (res, n, name), 300)
        n += 1
    s.mark("pad A row")
    s.press(0x1, 600)
    s.cmd("screenshot mp_pad_%s_%02d_A" % (res, n), 300)
    n += 1
    for name, m in (("down", 0x1000), ("down", 0x1000), ("up", 0x800)):
        s.press(m, 500)
        s.cmd("screenshot mp_pad_%s_%02d_%s" % (res, n, name), 300)
        n += 1
    s.mark("pad B")
    s.press(0x2, 0)
    s.t += int(1500 * slow)
    s.cmd("screenshot mp_pad_%s_%02d_back" % (res, n), 400)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mpui_pad_%s.txt" % res)
    return launch("mpui_pad_%s" % res, w, h, boot_lines(center, slow), boot_args(center, sp))


def film(res="720", slow=2.0, fps=20, host=True):
    """dense frames over the whole tour: screenshotJPEG on a fixed beat inserted between every scripted step"""
    w, h, center, lay = E.RES[res]
    s = Script(w, h, slow)
    beat = int(round(1000.0 / fps * slow))
    frames = [0]
    orig_cmd = s.cmd

    # wrap: every elapsed beat of script time gets a frame, so waits film at the game's pace
    def fill(t_to):
        while s._ft + beat <= t_to:
            s._ft += beat
            s.S.append("@cmd %d screenshotJPEG f%05d" % (s._ft, frames[0]))
            frames[0] += 1
    s._ft = s.t

    def cmd(c, dt=60):
        orig_cmd(c, dt)
        fill(s.t)
    s.cmd = cmd
    orig_at, orig_press = s.at, s.press

    def at(xy, wait=700):
        orig_at(xy, wait)
        fill(s.t)

    def press(b, wait=700):
        orig_press(b, wait)
        fill(s.t)
    s.at, s.press = at, press
    s.cmd("echo ^~^~^ MPUI film start", 3500)

    def shot(n, wait=500):
        s.t += wait
        fill(s.t)
    tour(s, res, w, h, center, slow, shot, deep=True, host=host)
    s.t += 1000
    fill(s.t)
    s.S.append("@cmd %d echo ^~^~^ MR done" % (s.t + 200))
    s.S.append("@cmd %d quit" % (s.t + 1000))
    sp = s.write("mpui_film_%s.txt" % res)
    extra = ["set sv_hostname \"HZM mpui harness (private)\"", "set password hzmharness%d" % (int(time.time()) % 9973), "set cl_maxfps 60"]
    print("frames", frames[0])
    return launch("mpui_film_%s" % res, w, h, boot_lines(center, slow, extra), boot_args(center, sp))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "setup":
        setup()
    elif a[0] == "walk":
        walk(a[1] if len(a) > 1 else "43", float(a[2]) if len(a) > 2 else 1.0)
    elif a[0] == "host":
        walk(a[1] if len(a) > 1 else "720", 1.0, host=True)
    elif a[0] == "pad":
        pad(a[1] if len(a) > 1 else "43")
    elif a[0] == "film":
        film(a[1] if len(a) > 1 else "720", float(a[2]) if len(a) > 2 else 2.0)

"""mphub_run.py - harness for the live 3D multiplayer room, on the private client G:\\mohaa-mphub (a copy of the live exe + DLLs; never the
live install).  Reuses e5_run.launch (DISPLAY2, background window policy, GL2 renderer DLL check as m3d_run does).

    python mphub_run.py setup                         ship pk3 + an overlay pk3 of the mphub3d worktree's ui files into the client's homepath
    python mphub_run.py walk <43|720|219> [slow]      cursor + A (the mouse path): attic MP door -> hub; every hub hotspot -> its menu -> BACK -> hub;
                                                      lockers -> LOADOUTS: Allied / Axis / Coop armories open and return; ESC -> attic.  Stills at every stop.
    python mphub_run.py pad <43|720|219> [slow]       pad only: D-pad focus walks the hub hotspots (PADNAV log), A opens, B returns; B in the hub -> attic
    python mphub_run.py gif [res]                     dense frames: attic -> MP door -> hub -> red door -> server browser -> back -> hub (frames -> gif)
Before every launch: no openmohaa*.exe three times 10 s apart, and the release flag present (the coordinator's rule)."""
import json, math, os, re, shutil, subprocess, sys, time, zipfile
import numpy as np

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\e5")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d")
import e5_run as E  # noqa: E402
import scene_params as SP  # noqa: E402

CLIENT = r"G:\mohaa-mphub"
E.CLIENT = CLIENT
E.EXE = os.path.join(CLIENT, "openmohaa.exe")
E.HOME = os.path.join(CLIENT, "home")
E.MAINTT = os.path.join(E.HOME, "maintt")
E.LOG = os.path.join(E.MAINTT, "qconsole.log")
E.SHOTS = os.path.join(E.MAINTT, "screenshots")
E.RUNS = r"H:\hzm_work\mphub3d\runs"
E.RES["1080"] = (1920, 1080, 0, "s")
MOD = r"C:\mohaa-coop-dev\hzm-mod-mphub"
SHIP = r"H:\hzm_work\mphub3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3"
OVERLAY = "zzzzzzzzzzzzzzzzzz_mphub_ui.pk3"
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
    errs = [l for l in lg.splitlines() if re.search(r"Script Error|ERROR|couldn't load|Couldn't find|WARNING: .*(urc|menu)", l)]
    print("^^ log errors: %d" % len(errs), *errs[:12], sep="\n   ")
    return out


def setup():
    shutil.copyfile(SHIP, os.path.join(E.MAINTT, os.path.basename(SHIP)))
    with zipfile.ZipFile(os.path.join(E.MAINTT, OVERLAY), "w", zipfile.ZIP_DEFLATED) as z:
        for f in ["multiplayer.urc", "coop_mp_options.urc", "main.urc", "hzm_newgame3d.urc", "hzm_attic_go_newgame.cfg"] + [x for x in os.listdir(os.path.join(MOD, "ui")) if x.startswith(("hzm_hub_go_", "hzm_ng3d_"))]:
            z.write(os.path.join(MOD, "ui", f), "ui/" + f)
    print("setup:", os.listdir(E.MAINTT))


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
    """640x480 virtual rect centre -> screen px (ui_menuCenter 1: a 4:3 column; 0: stretched)"""
    x, y, rw, rh = rect
    if center:
        s = h / 480.0
        return int((w - 640 * s) / 2 + (x + rw / 2) * s), int((y + rh / 2) * s)
    return int((x + rw / 2) * w / 640.0), int((y + rh / 2) * h / 480.0)


def rect_of(name, urcfile):
    t = urc(urcfile)
    m = re.search(r'name\s+"%s"\s*\n(?:\s*title[^\n]*\n)?\s*rect\s+(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)' % re.escape(name), t)
    return tuple(int(v) for v in m.groups())


class Script:
    def __init__(self, w, h, slow):
        self.S, self.t, self.w, self.h, self.slow = ["@hold", "@attach 0"], 1500, w, h, slow

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
        self.cmd("echo ^~^~^ MPHUB %s" % s)

    def write(self, name):
        p = os.path.join(E.RUNS, name)
        os.makedirs(E.RUNS, exist_ok=True)
        open(p, "w", newline="\n").write("\n".join(self.S) + "\n")
        return p


def boot_lines(center, slow):
    return ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set in_padDebug 1",
            "set ui_clickdebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]


def boot_args(center, sp):
    return ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace("\\", "/")]


def walk(res="43", slow=2.0):
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = scene_info(urc("main.urc"), "atticscene")
    hcam, hhot, hbox = scene_info(urc("multiplayer.urc"), "hubscene")
    k = slow / 1.0
    s = Script(w, h, slow)
    shot = lambda n, wait=500: s.cmd("screenshot mh_%s_%s" % (res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ MPHUB walk start", 3500)
    shot("00attic")
    s.at(hot_px(acam, ahot["mp"], abox.get("mp"), w, h))
    shot("01attic_mp_hover")
    s.mark("click attic MP door")
    s.press(0x1, 0)
    s.t += int(1900 * k)
    shot("02hub")
    s.cmd("ui_scene_hotdump 1", 100)
    s.cmd("ui_scene_hotdump 0", 100)

    def hub_at(n):
        s.at(hot_px(hcam, hhot[n], hbox.get(n), w, h))

    def back_btn(rect_name, urcfile):
        s.at(vpx(rect_name if isinstance(rect_name, tuple) else rect_of(rect_name, urcfile), w, h, center))
        s.press(0x1, 0)

    # every hub hotspot: hover (glow + caption) -> click -> the menu -> its own BACK button -> the hub flies home
    for n, menu_back in (("join", ("cancel", None)), ("start", ((8, 456, 96, 24), "multiplayerstart.urc")), ("record", ("backBtn", "coop_sr.urc"))):
        hub_at(n)
        shot("1%s_hover" % n)
        s.mark("click hub %s" % n)
        s.press(0x1, 0)
        s.t += int(1800 * k)
        shot("1%s_menu" % n, 600)
        s.mark("back from %s" % n)
        if menu_back[1]:
            back_btn(*menu_back)
        else:
            s.press(0x2, 0)                 # joingame is the stock maintt menu: its cancel = pad B (same popmenu 0)
        s.t += int(1800 * k)
        shot("1%s_hub_again" % n)
    # lockers -> LOADOUTS (mpoptions): Allied, Axis, Coop, each open + DONE back
    hub_at("loadout")
    shot("20loadout_hover")
    s.mark("click hub loadout")
    s.press(0x1, 0)
    s.t += int(1800 * k)
    shot("21loadouts")
    for side, done, df in (("allied", "doneBtn", "coop_mpa_defaults.urc"), ("axis", "doneBtn", "coop_mpx_defaults.urc"), ("coop", "closeBtn", "coop_loadout.urc")):
        s.at(vpx(rect_of(side, "coop_mp_options.urc"), w, h, center))
        s.mark("click %s" % side)
        s.press(0x1, 2500)
        shot("22%s_armory" % side, 600)
        s.mark("done %s" % side)
        back_btn(done, df)
        s.t += 1500
        if side == "coop":
            # the coop armory's DONE gate (ui/loadout/done.cfg) refuses while a locked item is equipped (this profile: a locked helmet)
            # and shows its own note: OK closes the note, B leaves the armory as a player would
            shot("22coop_done_gate", 300)
            back_btn((402, 255, 66, 14), None)
            s.press(0x2, 1500)
        shot("23%s_back_to_loadouts" % side)
    s.mark("back from loadouts")
    back_btn("back", "coop_mp_options.urc")
    s.t += int(1800 * k)
    shot("24hub_again")
    # wooden door -> the attic
    hub_at("main")
    shot("30main_hover")
    s.mark("click hub main")
    s.press(0x1, 0)
    s.t += int(2200 * k)
    shot("31attic_again")
    # into the hub again, ESC -> the attic
    s.at(hot_px(acam, ahot["mp"], abox.get("mp"), w, h))
    s.press(0x1, 0)
    s.t += int(1900 * k)
    shot("40hub_reentry")
    s.mark("ESC in hub")
    s.press(0x2, 0)
    s.t += int(2200 * k)
    shot("41attic_after_esc")
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mh_walk_%s.txt" % res)
    return launch("mh_walk_%s" % res, w, h, boot_lines(center, slow), boot_args(center, sp))


def pad(res="43", slow=2.0):
    """pad only: D-pad walks the focus over the hub hotspots, A opens the focused one, B returns, B in the hub -> attic"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = scene_info(urc("main.urc"), "atticscene")
    s = Script(w, h, slow)
    k = slow / 1.0
    s.cmd("echo ^~^~^ MPHUB pad start", 3500)
    s.cmd("set ui_keyNavActive 1", 100)
    s.cmd("exec ui/hzm_attic_go_mp.cfg", int(2500 * k))       # into the hub without a cursor (the attic door's own command)
    s.cmd("screenshot mp_%s_00hub" % res, 400)
    n = 1
    for name, m in (("right", 0x4000),) * 5 + (("left", 0x2000),) * 5:
        s.press(m, 600)
        s.cmd("screenshot mp_%s_%02d_%s" % (res, n, name), 300)
        n += 1
    # focus is now on the leftmost hotspot; step right twice (red door) and open it with A
    s.press(0x4000, 500)
    s.press(0x4000, 500)
    s.mark("pad A")
    s.press(0x1, 0)
    s.t += int(1900 * k)
    s.cmd("screenshot mp_%s_%02d_opened" % (res, n), 400)
    n += 1
    s.mark("pad B")
    s.press(0x2, 0)
    s.t += int(1900 * k)
    s.cmd("screenshot mp_%s_%02d_back" % (res, n), 400)
    n += 1
    s.mark("pad B in hub")
    s.press(0x2, 0)
    s.t += int(2200 * k)
    s.cmd("screenshot mp_%s_%02d_attic" % (res, n), 400)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mh_pad_%s.txt" % res)
    return launch("mh_pad_%s" % res, w, h, boot_lines(center, slow), boot_args(center, sp))


def gif(res="720", slow=4.0):
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = scene_info(urc("main.urc"), "atticscene")
    hcam, hhot, hbox = scene_info(urc("multiplayer.urc"), "hubscene")
    s = Script(w, h, slow)
    beat = int(round(1000.0 / 20.0 * slow))
    fr = [0]

    def rec(sec):
        for _ in range(int(round(sec * 20))):
            s.t += beat
            s.cmd("screenshotJPEG g%05d" % fr[0], 0)
            fr[0] += 1
    s.cmd("echo ^~^~^ MPHUB gif start", 3500)
    rec(0.8)
    s.at(hot_px(acam, ahot["mp"], abox.get("mp"), w, h), 80)
    rec(0.6)
    s.press(0x1, 0)
    rec(2.0)
    s.at(hot_px(hcam, hhot["join"], hbox.get("join"), w, h), 80)
    rec(0.8)
    s.press(0x1, 0)
    rec(2.0)
    s.press(0x2, 0)
    rec(1.8)
    s.at((int(w * 0.5), int(h * 0.92)), 80)
    rec(0.4)
    s.press(0x2, 0)                           # ESC in the hub: back to the attic
    rec(1.8)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mh_gif_%s.txt" % res)
    L = boot_lines(center, slow) + ["set cl_maxfps 60"]
    return launch("mh_gif_%s" % res, w, h, L, boot_args(center, sp))


def ng(res="43", unlocked="0", slow=2.0):
    """NEW GAME: attic -> the full wall map (no radio shelf) -> hover every campaign marker -> each unlocked one opens its difficulty
    screen, CANCEL returns to the map; a locked one only shows its caption; ESC -> the attic (radios back).  unlocked: g_t2l1 g_t3l1 value"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = scene_info(urc("main.urc"), "atticscene")
    ncam, nhot, nbox = scene_info(urc("hzm_newgame3d.urc"), "ngscene")
    k = slow
    s = Script(w, h, slow)
    shot = lambda n, wait=500: s.cmd("screenshot ng_%s_u%s_%s" % (res, unlocked, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ NG start", 3500)
    s.at(hot_px(acam, ahot["newgame"], abox.get("newgame"), w, h))
    shot("00attic_hover")
    s.mark("click attic NEW GAME")
    s.press(0x1, 0)
    s.t += int(1900 * k)
    shot("01map")
    lk = unlocked != "1"
    marks = [("tunisia", "mission1difficulty")] + [(m + ("_lk" if lk else ""), d) for m, d in (("sicily", "mission2difficulty"), ("italy", "mission3difficulty"))]
    for n, menu in marks:
        s.at(hot_px(ncam, nhot[n], nbox.get(n), w, h))
        shot("1%s_hover" % n)
        s.mark("click marker %s" % n)
        s.press(0x1, 1500)
        shot("1%s_clicked" % n, 600)
        if not n.endswith("_lk"):
            s.mark("cancel %s" % menu)
            s.at(vpx((272, 304, 96, 16), w, h, center))       # the stock CANCEL button
            s.press(0x1, 1200)
            shot("1%s_back_on_map" % n)
    s.mark("ESC on the map")
    s.press(0x2, 0)
    s.t += int(2200 * k)
    shot("20attic_after_esc")
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mh_ng_%s_u%s.txt" % (res, unlocked))
    L = boot_lines(center, slow)
    L.insert(0, "set g_t2l1 %s; set g_t3l1 %s" % (unlocked, unlocked))
    return launch("mh_ng_%s_u%s" % (res, unlocked), w, h, L, boot_args(center, sp) + ["+set", "g_t2l1", unlocked, "+set", "g_t3l1", unlocked])


def ngpad(res="43", slow=2.0):
    """pad only on the map: NEW GAME by its cfg, D-pad over the markers (PADNAV), A on the focused one, B back, B -> attic"""
    w, h, center, lay = E.RES[res]
    s = Script(w, h, slow)
    s.cmd("echo ^~^~^ NGPAD start", 3500)
    s.cmd("exec ui/hzm_attic_go_newgame.cfg", int(2500 * slow))
    s.cmd("screenshot ngp_%s_00map" % res, 400)
    n = 1
    for name, m in (("right", 0x4000), ("right", 0x4000), ("up", 0x800), ("left", 0x2000), ("down", 0x1000)):
        s.press(m, 600)
        s.cmd("screenshot ngp_%s_%02d_%s" % (res, n, name), 300)
        n += 1
    s.mark("pad A")
    s.press(0x1, 1500)
    s.cmd("screenshot ngp_%s_%02d_opened" % (res, n), 400)
    n += 1
    s.mark("pad B")
    s.press(0x2, 1200)
    s.cmd("screenshot ngp_%s_%02d_back" % (res, n), 400)
    n += 1
    s.press(0x2, 0)
    s.t += int(2200 * slow)
    s.cmd("screenshot ngp_%s_%02d_attic" % (res, n), 400)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mh_ngpad_%s.txt" % res)
    return launch("mh_ngpad_%s" % res, w, h, boot_lines(center, slow), boot_args(center, sp) + ["+set", "g_t2l1", "1", "+set", "g_t3l1", "0"])


def nggif(res="720", slow=4.0):
    """dense frames: attic -> NEW GAME -> the full map (radios gone) -> hover the markers -> TUNISIA -> difficulty -> CANCEL -> ESC -> attic"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = scene_info(urc("main.urc"), "atticscene")
    ncam, nhot, nbox = scene_info(urc("hzm_newgame3d.urc"), "ngscene")
    s = Script(w, h, slow)
    beat = int(round(1000.0 / 20.0 * slow))
    fr = [0]

    def rec(sec):
        for _ in range(int(round(sec * 20))):
            s.t += beat
            s.cmd("screenshotJPEG n%05d" % fr[0], 0)
            fr[0] += 1
    s.cmd("echo ^~^~^ NG gif start", 3500)
    rec(0.6)
    s.at(hot_px(acam, ahot["newgame"], abox.get("newgame"), w, h), 80)
    rec(0.6)
    s.press(0x1, 0)
    rec(2.0)
    for n in ("italy_lk", "sicily_lk", "tunisia"):
        s.at(hot_px(ncam, nhot[n], nbox.get(n), w, h), 80)
        rec(0.8)
    s.press(0x1, 0)
    rec(1.2)
    s.at(vpx((272, 304, 96, 16), w, h, center), 80)
    rec(0.4)
    s.press(0x1, 0)
    rec(0.8)
    s.press(0x2, 0)
    rec(2.0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mh_nggif_%s.txt" % res)
    return launch("mh_nggif_%s" % res, w, h, boot_lines(center, slow) + ["set cl_maxfps 60"], boot_args(center, sp) + ["+set", "g_t2l1", "0", "+set", "g_t3l1", "0"])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "setup":
        setup()
    elif a[0] == "walk":
        walk(a[1] if len(a) > 1 else "43", float(a[2]) if len(a) > 2 else 2.0)
    elif a[0] == "pad":
        pad(a[1] if len(a) > 1 else "43", float(a[2]) if len(a) > 2 else 2.0)
    elif a[0] == "ng":
        ng(a[1] if len(a) > 1 else "43", a[2] if len(a) > 2 else "0")
    elif a[0] == "ngpad":
        ngpad(a[1] if len(a) > 1 else "43")
    elif a[0] == "nggif":
        nggif(a[1] if len(a) > 1 else "720")
    elif a[0] == "gif":
        gif(a[1] if len(a) > 1 else "720", float(a[2]) if len(a) > 2 else 4.0)

"""m3d_run.py - menus3d spike harness (reuses e5_run.launch on the private client G:\\mohaa-hudfeed3\\e5pn).

    python m3d_run.py setup
    python m3d_run.py still <720|43|219>          pushmenu hzm_scene3d, one screenshot (+ the log's model-load lines)
    python m3d_run.py fly <720|43|219> [slow]     pad-driven: cursor on the radio hot sphere, A -> camera fly (sampled on a fixed beat) -> radio room -> B back -> fly home
Hold C:\\Users\\curry\\AppData\\Local\\Temp\\claude\\heavy.lock."""
import json, os, shutil, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\e5")
import e5_run as E  # noqa: E402

PK3 = r"G:\mohaa-hudfeed3\menus3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3"
STAGE = os.environ.get("M3D_STAGE", r"G:\mohaa-hudfeed3\menus3d\stage_w6")
E.RUNS = r"G:\mohaa-hudfeed3\menus3d\runs"


E.RES["1080"] = (1920, 1080, 0, "s")
_launch0 = E.launch


def _launch_gl2(tag, w, h, lines, extra=()):
    """every launch must be the GL2 renderer DLL (a static-GL1 exe silently tests the wrong renderer): check the log and say so"""
    out = _launch0(tag, w, h, lines, extra)
    lg = open(os.path.join(out, "qconsole.log"), errors="ignore").read()
    ok = 'Trying to load "renderer_opengl2.dll"' in lg
    print("^^ RENDERER %s: %s" % (tag, "renderer_opengl2.dll CONFIRMED" if ok else "NOT GL2 - results are GL1, do not use"), flush=True)
    if not ok:
        raise SystemExit("not the GL2 renderer DLL")
    return out


E.launch = _launch_gl2



def setup():
    E.setup()
    old = os.path.join(E.MAINTT, "zzzzzzzzzzzzz_menus3d.pk3")
    if os.path.exists(old):
        os.remove(old)                  # the old harness pk3 name would double-load stale files
    shutil.copyfile(PK3, os.path.join(E.MAINTT, os.path.basename(PK3)))
    print("pk3 in place")


def hot_px(res):
    """where the radio hot sphere projects (same maths as the widget) -> screen pixel"""
    import math
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_params as SP
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    w, h = E.RES[res][:2]
    org = np.array(P["home"][0]); ang = P["home"][1]; fovy = P["home"][2]
    f, left, up = SP.axes_from_angles(*ang)
    c = np.array(P["radio_ctr"]) - org
    x, y, z = c @ f, c @ left, c @ up
    t = math.tan(math.radians(fovy) / 2)
    fovx_t = t * w / h
    return int(w / 2 - (y / x) * (w / 2) / fovx_t), int(h / 2 - (z / x) * (h / 2) / t)


def still(res):
    w, h, center, lay = E.RES[res]
    L = ["set developer 0", "set ui_scene_debug 1", "set r_shadows 0", "set r_pshadows 0", "set r_dlightMode 0", "set ui_menuRoom 1", "set ui_menuCenter %d" % center, "wait 9000", "echo ^~^~^ M3D start", "pushmenu hzm_scene3d",
         "wait 3000", "screenshot m3d_%s_home" % res, "echo ^~^~^ MR done", "wait 300", "quit"]
    return E.launch("m3d_still_%s" % res, w, h, L)


def perf(res):
    """uncapped frame time of the scene menu (r_swapinterval 0, com_maxfps 1000): 6 s of the home view, log line SCENE3D frame"""
    w, h, center, lay = E.RES[res]
    L = ["set developer 0", "set ui_scene_debug 1", "set ui_menuRoom 1", "set ui_menuCenter %d" % center, "set com_maxfps 1000", "set r_swapinterval 0", "wait 9000", "com_maxfps", "r_swapinterval",
         "pushmenu hzm_scene3d", "wait 7000", "echo ^~^~^ MR done", "wait 300", "quit"]
    return E.launch("m3d_perf_%s" % res, w, h, L)


def padnav(res="720"):
    """D-pad focus test: the cursor starts away from the hotspot; each pad mask is pressed once; PADNAV lines in the log say where the cursor went"""
    w, h, center, lay = E.RES[res]
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))
    cmd("pushmenu hzm_scene3d", 3000)
    S.append("@cursor %d %d %d" % (t[0], int(w * 0.80), int(h * 0.80))); t[0] += 800
    cmd("screenshot m3d_pad_start", 500)
    for mask in (0x0100, 0x0200, 0x0400, 0x0800, 0x1000, 0x2000, 0x4000, 0x8000):
        cmd("echo ^~^~^ PADMASK %x" % mask, 0)
        state(mask); t[0] += 200; state(0); t[0] += 900
        cmd("echo ^~^~^ HOT $ui_scene_hot", 200)
        cmd("screenshot m3d_pad_%x" % mask, 400)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_padnav.txt")
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_menuCenter %d" % center, "set in_padDebug 1", "set ui_clickdebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_padnav", w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "in_padTestScript", sp.replace("\\", "/")])


def fly(res, slow=10.0):
    w, h, center, lay = E.RES[res]
    beat = int(round(33 * slow))
    nfr = int(0.6 * slow * 1000 / beat) + 3
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c))
        t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))
    cmd("pushmenu hzm_scene3d", 3000)
    cmd("screenshot m3d_%s_00home" % res, 400)
    px, py = hot_px(res)
    S.append("@cursor %d %d %d" % (t[0], px, py))
    t[0] += 900
    cmd("screenshot m3d_%s_01hover" % res, 400)
    cmd("echo ^~^~^ M3D click", 0)
    state(0x1)
    t[0] += 120
    state(0)
    for i in range(nfr):
        t[0] += beat
        cmd("screenshot m3d_%s_f%02d" % (res, i), 0)
    t[0] += 2500
    cmd("screenshot m3d_%s_20radios" % res, 600)
    cmd("echo ^~^~^ M3D back", 0)
    state(0x2)
    t[0] += 120
    state(0)
    for i in range(nfr):
        t[0] += beat
        cmd("screenshot m3d_%s_b%02d" % (res, i), 0)
    t[0] += 2000
    cmd("screenshot m3d_%s_30home" % res, 600)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_fly_%s.txt" % res)
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set in_padDebug 1", "wait 9000",
         "echo ^~^~^ MR start m3d", "set in_padTestGo 1"]
    return E.launch("m3d_fly_%s_x%g" % (res, slow), w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "in_padTestScript", sp.replace("\\", "/")])


def proj(pose, pt, w, h):
    import math
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_params as SP
    org, ang, fovy = np.array(pose[0]), pose[1], pose[2]
    f, left, up = SP.axes_from_angles(*ang)
    c = np.array(pt) - org
    x, y, z = c @ f, c @ left, c @ up
    t = math.tan(math.radians(fovy) / 2)
    return int(w / 2 - (y / x) * (w / 2) / (t * w / h)), int(h / 2 - (z / x) * (h / 2) / t)


def world(res="43", radios="video,audio", slow=5.0):
    """full tour with the pad/mouse path: attic -> (click OPTIONS) -> shelf -> (click a radio) -> close-up radio menu -> B -> shelf -> B -> attic.
    Flights are sampled on a fixed beat (ui_camslow=slow), stills at every stop."""
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_params as SP
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    R = json.load(open(r"G:/mohaa-hudfeed3/menus3d/bake_rj/radios.json"))
    shelf = (P["fly"][0], P["fly"][1], P["fly"][2])
    beat = int(round(33 * slow))
    nfr = int(0.6 * slow * 1000 / beat) + 3
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def press(b):
        state(b); t[0] += 120; state(0)

    def sample(tag):
        for i in range(nfr):
            t[0] += beat
            if not os.environ.get("M3D_NOSAMPLE"):
                cmd("screenshot m3d_%s_%s%02d" % (res, tag, i), 0)
        t[0] += 1800

    cmd("set ui_atcStop 0", 100)
    cmd("pushmenu hzm_scene3d", 3000)
    cmd("screenshot m3d_%s_00home" % res, 400)
    px, py = hot_px(res)
    S.append("@cursor %d %d %d" % (t[0], px, py)); t[0] += 900
    cmd("screenshot m3d_%s_01hover_options" % res, 400)
    press(0x1)
    sample("a")
    cmd("screenshot m3d_%s_10shelf" % res, 500)
    n = 20
    for r in radios.split(","):
        lo, hi = np.array(R[r]["min"]), np.array(R[r]["max"])
        c = SP.conv([(lo[0] + hi[0]) / 2, lo[1] - 0.02, (lo[2] + hi[2]) / 2], 52.5)
        rx, ry = proj(shelf, c, w, h)
        S.append("@cursor %d %d %d" % (t[0], rx, ry)); t[0] += 900
        cmd("screenshot m3d_%s_%d_%s_hover" % (res, n, r), 400)
        press(0x1)
        sample("%s_in" % r)
        cmd("screenshot m3d_%s_%d_%s_closeup" % (res, n + 1, r), 500)
        press(0x2)                       # B = ESC: the radio menu pops, the scene flies back to the shelf
        sample("%s_out" % r)
        cmd("screenshot m3d_%s_%d_%s_shelf" % (res, n + 2, r), 500)
        n += 3
    press(0x2)                           # B at the shelf: fly home
    sample("h")
    cmd("screenshot m3d_%s_90home" % res, 500)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_world_%s.txt" % res)
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_labeldebug 1", "set ui_menuRoom 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set in_padDebug 1", "wait 9000",
         "echo ^~^~^ MR start m3d", "set in_padTestGo 1"]
    return E.launch("m3d_world_%s%s" % (res, os.environ.get("M3D_TAG", "")), w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "in_padTestScript", sp.replace("\\", "/")])


def padshelf(res="43"):
    """D-pad only after the first click: attic -> A on OPTIONS -> shelf, then pad moves (right,right,down,left,left,up,...) with the focused hotspot logged and shot,
    then A on the focused radio = its close-up flies in; B back.  PADNAV lines show which proxy the cursor landed on."""
    w, h, center, lay = E.RES[res]
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def press(b, wait=700):
        state(b); t[0] += 150; state(0); t[0] += wait
    cmd("set ui_atcStop 0", 100)
    cmd("pushmenu hzm_scene3d", 3000)
    S.append("@cursor %d %d %d" % (t[0], int(w * 0.80), int(h * 0.80))); t[0] += 800
    press(0x100, 400); press(0x100, 400)           # wake the pad (the first presses after the menu opens are swallowed)
    press(0x800)                                   # up (D-pad masks: 0x800 up, 0x1000 down, 0x2000 left, 0x4000 right): focus OPTIONS (cursor jumps onto the only live proxy)
    cmd("echo ^~^~^ FOCUS attic $ui_scene_hot", 100)
    press(0x1, 3500)                               # A: fly to the shelf
    cmd("screenshot m3d_pad_shelf0", 400)
    n = 1
    for name, m in (("right", 0x4000), ("right", 0x4000), ("down", 0x1000), ("left", 0x2000), ("left", 0x2000), ("up", 0x800), ("down", 0x1000), ("right", 0x4000)):
        press(m, 600)
        cmd("echo ^~^~^ FOCUS %s %s hot=$ui_scene_hot" % (n, name), 100)
        cmd("screenshot m3d_pad_shelf%d_%s" % (n, name), 300)
        n += 1
    press(0x1, 4500)                               # A on whatever has focus: its close-up
    cmd("echo ^~^~^ FOCUS entered $ui_atcStop", 100)
    cmd("screenshot m3d_pad_closeup", 400)
    press(0x2, 3500)                               # B: back to the shelf
    cmd("echo ^~^~^ FOCUS back $ui_atcStop", 100)
    cmd("screenshot m3d_pad_back", 400)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_padshelf.txt")
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_menuCenter %d" % center, "set in_padDebug 1", "set ui_clickdebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_padshelf_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "in_padTestScript", sp.replace("\\", "/")])


def entry(res="43", mode="3d", slow=3.0):
    """the flat main menu is the root: OPTIONS door -> (3d: attic -> shelf -> radio -> back -> out | flat: radio room | classic: options_main), then the other flat doors
    (MULTIPLAYER, NEW GAME, RECORDS) still open their menus.  mode: 3d (ui_menuRoom 1, ui_menu3d 1), flat (ui_menu3d 0), classic (ui_menuRoom 0)."""
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_params as SP
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    R = json.load(open(r"G:/mohaa-hudfeed3/menus3d/bake_rj/radios.json"))
    shelf = (P["fly"][0], P["fly"][1], P["fly"][2])
    S = ["@hold", "@attach 0"]
    t = [1500]
    sc = (w / 640.0, h / 480.0) if not center else (min(w / 640.0, h / 480.0),) * 2
    ox = (w - 640 * sc[0]) / 2.0 if center else 0.0

    def vpt(x, y, ww, hh):
        return int(ox + (x + ww / 2.0) * sc[0]), int((y + hh / 2.0) * sc[1])

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def press(b, wait=700):
        state(b); t[0] += 150; state(0); t[0] += wait

    def at(x, y):
        S.append("@cursor %d %d %d" % (t[0], x, y)); t[0] += 700

    def shot(n, wait=500):
        cmd("screenshot ent_%s_%s_%s" % (mode, res, n), wait)
    cmd("echo ^~^~^ ENTRY start", 3000)      # the main menu is already up (it is the root)
    shot("00main")
    at(*vpt(34, 187, 114, 79))
    shot("01options_hover")
    press(0x1, 0)
    t[0] += int(5000 * slow / 3.0)
    shot("02after_options")
    if mode == "3d":
        lo, hi = np.array(R["video"]["min"]), np.array(R["video"]["max"])
        c = SP.conv([(lo[0] + hi[0]) / 2, lo[1] - 0.02, (lo[2] + hi[2]) / 2], 52.5)
        rx, ry = proj(shelf, c, w, h)
        at(rx, ry)
        shot("03radio_hover")
        press(0x1, 0)
        t[0] += int(5500 * slow / 3.0)
        shot("04closeup")
        press(0x2, 0)
        t[0] += int(4500 * slow / 3.0)
        shot("05back_at_shelf")
        press(0x2, 0)                        # ESC at the shelf: out of the attic, back to the flat main menu
        t[0] += int(5500 * slow / 3.0)
        shot("06main_again")
    else:
        press(0x2, 2500)
        shot("04back_on_main")
    at(*vpt(480, 128, 64, 160))
    press(0x1, 2500)
    shot("10multiplayer")
    press(0x2, 2000)
    at(*vpt(166, 129, 116, 92))
    press(0x1, 2500)
    shot("11newgame")
    press(0x2, 2000)
    shot("12main_final")
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_entry_%s_%s.txt" % (mode, res))
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom %d" % (0 if mode == "classic" else 1), "set ui_menu3d %d" % (0 if mode == "flat" else 1), "set ui_menuCenter %d" % center,
         "set ui_camslow %g" % slow, "set in_padDebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_entry_%s_%s" % (mode, res), w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", str(0 if mode == "classic" else 1), "+set", "ui_menu3d", str(0 if mode == "flat" else 1), "+set", "in_padTestScript", sp.replace("\\", "/")])


def atticmain(res="43", only="", slow=3.0):
    """ui_atticMain 1: the game opens on the 3D attic (main menu).  Mouse path: every home hotspot -> camera move -> its flat menu -> BACK (pad B) -> the camera flies home;
    then OPTIONS -> shelf -> VIDEO radio close-up -> back -> shelf -> ESC -> home.  Stills at every stop; frames of the first fly of each move."""
    import re
    import numpy as np
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    home = (P["home"][0], P["home"][1], P["home"][2])
    shelf = (P["fly"][0], P["fly"][1], P["fly"][2])
    mu = open(os.environ.get("ATTIC_MAIN_URC", r"C:\mohaa-coop-dev\hzm-mod-e5zoom\ui\main.urc"), encoding="utf-8").read()
    hot = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "', mu)}
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def press(b, wait=700):
        state(b); t[0] += 150; state(0); t[0] += wait

    def at(x, y):
        S.append("@cursor %d %d %d" % (t[0], x, y)); t[0] += 700

    def shot(n, wait=500):
        cmd("screenshot am_%s_%s" % (res, n), wait)
    mult = slow / 3.0
    cmd("echo ^~^~^ ATTICMAIN start", 3500)
    shot("00home")
    order = [k for k in ("mp", "newgame", "brief", "records") if not only or k in only.split(",")]
    for k in order:
        at(*proj(home, hot[k], w, h))
        shot("%s_hover" % k)
        press(0x1, 0)
        t[0] += int(1600 * mult)
        shot("%s_arrived" % k)
        t[0] += int(1800 * mult)           # the flat menu opens after the move
        shot("%s_menu" % k)
        press(0x2, 0)                      # BACK: pop the flat menu, the scene flies home
        t[0] += int(3500 * mult)
        shot("%s_home_again" % k)
    if not only or "options" in only.split(","):
        at(*proj(home, hot["options"], w, h))
        shot("options_hover")
        press(0x1, 0)
        t[0] += int(3000 * mult)
        shot("shelf")
        lo = np.array(json.load(open(r"G:/mohaa-hudfeed3/menus3d/bake_rj/radios.json"))["video"]["min"]); hi = np.array(json.load(open(r"G:/mohaa-hudfeed3/menus3d/bake_rj/radios.json"))["video"]["max"])
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import scene_params as SP
        c = SP.conv([(lo[0] + hi[0]) / 2, lo[1] - 0.02, (lo[2] + hi[2]) / 2], 52.5)
        at(*proj(shelf, c, w, h))
        press(0x1, 0)
        t[0] += int(5000 * mult)
        shot("closeup")
        press(0x2, 0)
        t[0] += int(4000 * mult)
        shot("back_at_shelf")
        press(0x2, 0)                      # ESC at the shelf: home
        t[0] += int(3500 * mult)
        shot("esc_home")
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_atticmain_%s.txt" % res)
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set in_padDebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_atticmain_%s%s" % (res, os.environ.get("M3D_TAG", "")), w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1"] + (["+set", "ui_scene_debug", "1"] if os.environ.get("AM_DEBUG") else []) + ["+set", "in_padTestScript", sp.replace("\\", "/")])


def tour(res="1080", slow=6.0, hold=1.0):
    """video tour of the attic main menu: dense 30 fps-of-scene-time capture (screenshotJPEG every 33 ms * ui_camslow), every hotspot, the shelf, a radio close-up, ESC home.
    frames land in runs/m3d_tour_<res>/t00000.jpg ... ; make_mp4.py turns them into the MP4."""
    import numpy as np
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    home = (P["home"][0], P["home"][1], P["home"][2])
    shelf = (P["fly"][0], P["fly"][1], P["fly"][2])
    import re
    mu = open(os.environ.get("ATTIC_MAIN_URC", r"C:\mohaa-coop-dev\hzm-mod-e5zoom\ui\main.urc"), encoding="utf-8").read()
    hot = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "', mu)}
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_params as SP
    R = json.load(open(r"G:/mohaa-hudfeed3/menus3d/bake_rj/radios.json"))
    S = ["@hold", "@attach 0"]
    t = [1500]
    beat = int(round(1000.0 / 30.0 * slow))
    n = [0]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def press(b):
        state(b); t[0] += 120; state(0)

    def at(x, y):
        S.append("@cursor %d %d %d" % (t[0], x, y)); t[0] += 80

    def rec(sec):
        for _ in range(int(round(sec * 30))):
            t[0] += beat
            cmd("screenshotJPEG t%05d" % n[0], 0)
            n[0] += 1
    cmd("echo ^~^~^ TOUR start", 3500)
    rec(hold + 0.6)
    for k in ("mp", "newgame", "brief", "records"):
        at(*proj(home, hot[k], w, h))
        rec(0.5)
        press(0x1)
        rec(0.6 + 1.1)                     # the camera move, then the flat menu is open
        rec(1.0)
        press(0x2)                         # BACK
        rec(0.9 + 0.5)                     # the camera flies home
    at(*proj(home, hot["options"], w, h))
    rec(0.5)
    press(0x1)
    rec(0.7 + 0.8)
    lo = np.array(R["video"]["min"]); hi = np.array(R["video"]["max"])
    c = SP.conv([(lo[0] + hi[0]) / 2, lo[1] - 0.02, (lo[2] + hi[2]) / 2], 52.5)
    at(*proj(shelf, c, w, h))
    rec(0.5)
    press(0x1)
    rec(0.7 + 1.4)                         # fly in, the crisp art fades up
    rec(1.0)
    press(0x2)
    rec(1.5)                               # fade out, fly back to the shelf
    rec(0.5)
    press(0x2)                             # ESC at the shelf: home
    rec(1.0 + 0.8)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_tour_%s.txt" % res)
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set cl_maxfps 60", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    out = E.launch("m3d_tour_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace("\\", "/")])
    print("frames", n[0], out)
    return out


def atticpad(res="43", slow=3.0):
    """pad only on the attic main menu: D-pad moves through the home hotspots (PADNAV log names the proxy), A opens the focused one, B returns, then the shelf by pad."""
    w, h, center, lay = E.RES[res]
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def press(b, wait=700):
        state(b); t[0] += 150; state(0); t[0] += wait
    cmd("echo ^~^~^ ATTICPAD start", 3500)
    S.append("@cursor %d %d %d" % (t[0], int(w * 0.5), int(h * 0.5))); t[0] += 600
    press(0x100, 400); press(0x100, 400)
    n = 0
    for name, m in (("up", 0x800), ("right", 0x4000), ("right", 0x4000), ("down", 0x1000), ("left", 0x2000), ("left", 0x2000), ("up", 0x800)):
        press(m, 600)
        cmd("screenshot ap_%s_%02d_%s" % (res, n, name), 300); n += 1
    press(0x1, 0)                          # A on the focused hotspot
    t[0] += int(5000 * slow / 3.0)
    cmd("screenshot ap_%s_%02d_opened" % (res, n), 400); n += 1
    press(0x2, 0)                          # B
    t[0] += int(4500 * slow / 3.0)
    cmd("screenshot ap_%s_%02d_back" % (res, n), 400)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_atticpad_%s.txt" % res)
    open(sp, "w", newline="\n").write("\n".join(S) + "\n")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set in_padDebug 1", "set ui_clickdebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_atticpad_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace("\\", "/")])


def life(res="1080", secs=45.0, slow=3.0):
    """home-view capture of the actor life loop: dense 30 fps-of-scene-time frames, no input.  frames in runs/m3d_life_<res>/"""
    w, h, center, lay = E.RES[res]
    S = ["@hold", "@attach 0"]
    t = [1500]
    beat = int(round(1000.0 / 30.0 * slow))
    n = 0
    S.append("@cmd %d echo ^~^~^ LIFE start" % t[0]); t[0] += 3500
    for n in range(int(round(secs * 30))):
        t[0] += beat
        S.append("@cmd %d screenshotJPEG t%05d" % (t[0], n))
    S.append("@cmd %d echo ^~^~^ MR done" % (t[0] + 800))
    S.append("@cmd %d quit" % (t[0] + 900))
    sp = os.path.join(E.RUNS, "m3d_life_%s.txt" % res)
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline=chr(10)).write(chr(10).join(S) + chr(10))
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set cl_maxfps 60", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_life_%s%s" % (res, os.environ.get("M3D_TAG", "")), w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace(chr(92), "/")])


def lifefly(res="1080", slow=3.0):
    """pause/resume check: record the life loop, fly to the MP hotspot and open its flat menu, BACK, record on.  frames in runs/m3d_lifefly_<res>/"""
    import re
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    home = (P["home"][0], P["home"][1], P["home"][2])
    mu = open(r"C:\mohaa-coop-dev\hzm-mod-e5zoom\ui\main.urc", encoding="utf-8").read()
    hot = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "', mu)}
    S = ["@hold", "@attach 0"]
    t = [1500]
    beat = int(round(1000.0 / 30.0 * slow))
    n = [0]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def rec(sec):
        for _ in range(int(round(sec * 30))):
            t[0] += beat
            cmd("screenshotJPEG t%05d" % n[0], 0)
            n[0] += 1
    cmd("echo ^~^~^ LIFEFLY start", 3500)
    rec(14.0)
    S.append("@cursor %d %d %d" % ((t[0],) + tuple(proj(home, hot["mp"], w, h)))); t[0] += 80
    rec(0.5)
    state(0x1); t[0] += 120; state(0)
    rec(5.0)
    state(0x2); t[0] += 120; state(0)
    rec(8.0)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_lifefly_%s.txt" % res)
    open(sp, "w", newline=chr(10)).write(chr(10).join(S) + chr(10))
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set cl_maxfps 60", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_lifefly_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace(chr(92), "/")])


def doors(res="43", slow=3.0):
    """click test: five points over each door (centre + four inner corners of its hit box), pad A at the cursor, screenshot, BACK.  frames dc_<res>_<door>_<n>.jpg"""
    import re
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    home = (P["home"][0], P["home"][1], P["home"][2])
    mu = open(r"C:\mohaa-coop-dev\hzm-mod-e5zoom\ui\main.urc", encoding="utf-8").read()
    hot = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "', mu)}
    box = {m.group(1): tuple(float(m.group(i)) for i in (2, 3, 4, 5)) for m in re.finditer(r'(?m)^scenehotbox "(\w+)" (\S+) (\S+) (\S+) (\S+)', mu)}
    k = h / 1080.0
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))
    cmd("echo ^~^~^ DOORS start", 3500)
    mult = slow / 3.0
    for door in ("mp", "brief"):
        sx, sy = proj(home, hot[door], w, h)
        ox, oy, hw, hh = box[door]
        cx, cy = sx + ox * k, sy + oy * k
        pts = [(0, 0), (-0.85, -0.9), (0.85, -0.9), (-0.85, 0.9), (0.85, 0.9)]
        for n, (fx, fy) in enumerate(pts):
            S.append("@cursor %d %d %d" % (t[0], int(cx + fx * hw * k), int(cy + fy * hh * k))); t[0] += 700
            state(0x1); t[0] += 150; state(0)
            t[0] += int(2600 * mult)
            cmd("screenshot dc_%s_%s_%d" % (res, door, n), 500)
            state(0x2); t[0] += 150; state(0)
            t[0] += int(3800 * mult)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_doors_%s.txt" % res)
    os.makedirs(E.RUNS, exist_ok=True)
    open(sp, "w", newline=chr(10)).write(chr(10).join(S) + chr(10))
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow, "set in_padDebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_doors_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace(chr(92), "/")])


def startmap(res="43", mapname="m1l1"):
    """console `set ui_dmmap <map>; ui_startdmmap 2` typed (script @cmd = the console path) while the attic main menu is up.  Log + screenshots tell whether the map loads."""
    w, h, center, lay = E.RES[res]
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt
    cmd("echo ^~^~^ STARTMAP start", 3000)
    cmd("screenshot sm_%s_00home" % res, 800)
    cmd("set ui_dmmap %s" % mapname, 200)
    cmd("ui_startdmmap 2", 1500)
    cmd("screenshot sm_%s_01after" % res, 1000)
    for i in range(6):
        t[0] += 5000
        cmd("screenshot sm_%s_%02d_t%d" % (res, 2 + i, 5 * (i + 1)), 100)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_startmap_%s.txt" % res)
    open(sp, "w", newline=chr(10)).write(chr(10).join(S) + chr(10))
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_startmap_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace(chr(92), "/")])


def mpflow(res="43", steps="940,125;1180,316"):
    """normal user path: Multiplayer door, then pad-A clicks at the given flat-menu pixels (x,y;x,y;...), a screenshot after each.  mf_<res>_<n>.tga"""
    import re
    w, h, center, lay = E.RES[res]
    P = json.load(open(os.path.join(STAGE, "poses.json")))
    home = (P["home"][0], P["home"][1], P["home"][2])
    mu = open(r"C:\mohaa-coop-dev\hzm-mod-e5zoom\ui\main.urc", encoding="utf-8").read()
    hot = {m.group(1): (float(m.group(2)), float(m.group(3)), float(m.group(4))) for m in re.finditer(r'(?m)^scenehot "(\w+)" (\S+) (\S+) (\S+) (\S+) "', mu)}
    box = {m.group(1): tuple(float(m.group(i)) for i in (2, 3, 4, 5)) for m in re.finditer(r'(?m)^scenehotbox "(\w+)" (\S+) (\S+) (\S+) (\S+)', mu)}
    k = h / 1080.0
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt

    def state(b):
        S.append("%d 0 0 0 0 0 0 %d" % (t[0], b))

    def click(x, y, wait):
        S.append("@cursor %d %d %d" % (t[0], int(x), int(y))); t[0] += 700
        state(0x1); t[0] += 150; state(0)
        t[0] += wait
    cmd("echo ^~^~^ MPFLOW start", 3500)
    sx, sy = proj(home, hot["mp"], w, h)
    ox, oy, hw, hh = box["mp"]
    click(sx + ox * k, sy + oy * k, 3500)
    cmd("screenshot mf_%s_00door" % res, 500)
    for n, st in enumerate(steps.split(";")):
        x, y = st.split(",")
        click(float(x), float(y), 3500)
        cmd("screenshot mf_%s_%02d" % (res, n + 1), 500)
    for i in range(4):
        t[0] += 6000
        cmd("screenshot mf_%s_z%d" % (res, i), 100)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_mpflow_%s.txt" % res)
    open(sp, "w", newline=chr(10)).write(chr(10).join(S) + chr(10))
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set in_padDebug 1", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_mpflow_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace(chr(92), "/")])


def cmdtest(res="43", cmds="vid_restart"):
    """type console commands (';'-separated) at the attic home view, screenshot before and 4 / 10 / 16 s after.  ct_<res>_<n>.tga"""
    w, h, center, lay = E.RES[res]
    S = ["@hold", "@attach 0"]
    t = [1500]

    def cmd(c, dt=60):
        S.append("@cmd %d %s" % (t[0], c)); t[0] += dt
    cmd("echo ^~^~^ CMDTEST start", 3000)
    cmd("screenshot ct_%s_00" % res, 800)
    for c in cmds.split(";"):
        cmd(c.strip(), 500)
    for i in range(3):
        t[0] += (4000 if i == 0 else 6000)
        cmd("screenshot ct_%s_%02d" % (res, i + 1), 100)
    cmd("echo ^~^~^ MR done", 800)
    cmd("quit", 0)
    sp = os.path.join(E.RUNS, "m3d_cmdtest_%s.txt" % res)
    open(sp, "w", newline=chr(10)).write(chr(10).join(S) + chr(10))
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]
    return E.launch("m3d_cmdtest_%s" % res, w, h, L, ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace(chr(92), "/")])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "setup":
        setup()
    elif a[0] == "still":
        still(a[1])
    elif a[0] == "padnav":
        padnav(a[1] if len(a) > 1 else "720")
    elif a[0] == "perf":
        perf(a[1])
    elif a[0] == "atticpad":
        atticpad(a[1] if len(a) > 1 else "43")
    elif a[0] == "lifefly":
        lifefly(a[1] if len(a) > 1 else "1080", float(a[2]) if len(a) > 2 else 3.0)
    elif a[0] == "doors":
        doors(a[1] if len(a) > 1 else "43")
    elif a[0] == "startmap":
        startmap(a[1] if len(a) > 1 else "43", a[2] if len(a) > 2 else "m1l1")
    elif a[0] == "mpflow":
        mpflow(a[1] if len(a) > 1 else "43", a[2] if len(a) > 2 else "940,125;1180,316")
    elif a[0] == "cmdtest":
        cmdtest(a[1] if len(a) > 1 else "43", a[2] if len(a) > 2 else "vid_restart")
    elif a[0] == "life":
        life(a[1] if len(a) > 1 else "1080", float(a[2]) if len(a) > 2 else 45.0, float(a[3]) if len(a) > 3 else 3.0)
    elif a[0] == "tour":
        tour(a[1] if len(a) > 1 else "1080", float(a[2]) if len(a) > 2 else 6.0)
    elif a[0] == "atticmain":
        atticmain(a[1] if len(a) > 1 else "43", a[2] if len(a) > 2 else "")
    elif a[0] == "entry":
        entry(a[1] if len(a) > 1 else "43", a[2] if len(a) > 2 else "3d")
    elif a[0] == "padshelf":
        padshelf(a[1] if len(a) > 1 else "43")
    elif a[0] == "world":
        world(a[1], a[2] if len(a) > 2 else "video,audio", float(a[3]) if len(a) > 3 else 5.0)
    elif a[0] == "fly":
        fly(a[1], float(a[2]) if len(a) > 2 else 10.0)

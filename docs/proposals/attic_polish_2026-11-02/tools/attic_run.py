"""attic_run.py - art/QA harness for the 3D attic main menu + the 3D New Game wall map, on the private client G:\\mohaa-attic
(a copy of the G:\\mohaa-mphub exe + DLLs; never the live install).  Reuses e5_run.launch (DISPLAY2, background window policy).

    python attic_run.py setup [shipdir]            ship pk3 (ATTIC_SHIP or the mphub ship) + overlay of the attic-polish worktree's ui files
    python attic_run.py survey <720|1080|219|43> [tag]   idle + every home hover, the radio shelf + every radio hover, the New Game map + markers
    python attic_run.py video <720|1080> [tag]     dense JPEG frames (20 fps of menu time): idle, hover tour, NEW GAME map, back (frames -> mp4)

2560x1440 / 3440x1440 do not fit DISPLAY2 (1920x1080; harness_window clamps the window), so 1080 stands in for 1440p (same
16:9 layout, the menu is resolution independent: 640x480 virtual + the scene's own fov) and 219 = 1920x804 for 3440x1440.
Before every launch: the release flag present and no openmohaa*.exe three times 10 s apart (the coordinator's rule)."""
import json, math, os, re, shutil, subprocess, sys, time, zipfile

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\e5")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\mphub3d_2026-11-02")
import e5_run as E  # noqa: E402
import mphub_run as M  # noqa: E402  (scene_info / hot_px / vpx / Script)

CLIENT = r"G:\mohaa-attic"
for mod in (E,):
    mod.CLIENT = CLIENT
    mod.EXE = os.path.join(CLIENT, "openmohaa.exe")
    mod.HOME = os.path.join(CLIENT, "home")
    mod.MAINTT = os.path.join(mod.HOME, "maintt")
    mod.LOG = os.path.join(mod.MAINTT, "qconsole.log")
    mod.SHOTS = os.path.join(mod.MAINTT, "screenshots")
E.RUNS = r"H:\hzm_work\attic_polish\runs"
E.RES.update({"720": (1280, 720, 0, "s"), "1080": (1920, 1080, 0, "s"), "219": (1920, 804, 0, "s"), "43": (1440, 1080, 0, "s"),
              "43c": (1440, 1080, 1, "c"), "219c": (1920, 804, 1, "c"), "1440": (2560, 1440, 0, "s"), "3440": (3440, 1440, 0, "s")})
MOD = os.environ.get("ATTIC_MOD", r"C:\mohaa-coop-dev\hzm-mod-attic")
M.MOD = MOD
SHIP = os.environ.get("ATTIC_SHIP", r"H:\hzm_work\mphub3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
OVERLAY = "zzzzzzzzzzzzzzzzzz_attic_ui.pk3"
FLAG = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\release_done.flag"
_launch0 = E.launch


def quiet_wait():
    n = 0
    while n < 3:
        # 2026-11-03 (coordinator): parallel tests are allowed now - wait only for this harness's own client copy
        ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process openmohaa* -ErrorAction SilentlyContinue | ForEach-Object { $_.Path }"],
                            capture_output=True, text=True).stdout.lower()
        busy = CLIENT.lower() + "\\" in ps or not os.path.exists(FLAG)
        n = 0 if busy else n + 1
        if busy:
            E.log("waiting: a game client is up or the release flag is missing")
        time.sleep(10)


def launch(tag, w, h, lines, extra=()):
    quiet_wait()
    out = _launch0(tag, w, h, lines, extra)
    lg = open(os.path.join(out, "qconsole.log"), errors="ignore").read()
    print("^^ RENDERER %s: %s" % (tag, "GL2 CONFIRMED" if 'Trying to load "renderer_opengl2.dll"' in lg else "NOT GL2"), flush=True)
    errs = [l for l in lg.splitlines() if re.search(r"Script Error|ERROR|couldn't load|Couldn't find|WARNING: .*(urc|menu|shader|model)", l)]
    print("^^ log errors: %d" % len(errs), *errs[:20], sep="\n   ")
    return out


UI_FILES = ["main.urc", "hzm_newgame3d.urc", "multiplayer.urc", "hzm_records3d.urc", "hzm_medals3d.urc", "hzm_wpnview.urc", "hzm_frplay.cfg"]      # multiplayer.urc: the MP room (its exit door pane)


def setup():
    shutil.copyfile(SHIP, os.path.join(E.MAINTT, "zzzzzzzzzzzzzz_hzm_menus3d.pk3"))
    with zipfile.ZipFile(os.path.join(E.MAINTT, OVERLAY), "w", zipfile.ZIP_DEFLATED) as z:
        ui = os.path.join(MOD, "ui")
        for f in UI_FILES + [x for x in os.listdir(ui) if x.startswith(("hzm_attic_go_", "hzm_ng3d_", "hzm_mpui_scene_"))]:
            z.write(os.path.join(ui, f), "ui/" + f)
        mm = os.path.join(ui, "coop_menumusic")
        if os.path.isdir(mm):
            for f in os.listdir(mm):
                z.write(os.path.join(mm, f), "ui/coop_menumusic/" + f)
        if os.path.exists(os.path.join(MOD, "coop_defaults.cfg")):
            z.write(os.path.join(MOD, "coop_defaults.cfg"), "coop_defaults.cfg")
        extra = os.environ.get("ATTIC_EXTRA")          # a dir whose tree is overlaid as-is (polish textures / shaders under test)
        if extra:
            for r, _, fs in os.walk(extra):
                for f in fs:
                    p = os.path.join(r, f)
                    z.write(p, os.path.relpath(p, extra).replace("\\", "/"))
    print("setup:", sorted(os.listdir(E.MAINTT)))


def boot_lines(center, slow):
    return ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow %g" % slow,
            "set coop_hardcore 0", "wait 9000", "echo ^~^~^ MR start", "set in_padTestGo 1"]


def boot_args(center, sp):
    return ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "in_padTestScript", sp.replace("\\", "/"),
            "+set", "g_t2l1", "1", "+set", "g_t3l1", "0",
            # user 2026-11-08: "keep all test runs muted" (harness_window's policy zeroes s_volume / s_musicvolume too)
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0",
            # the pad-script needs the pad system on (an archived in_gamepad 0 from earlier forced runs stalls it); the exe must
            # carry engine de222de5 (a pad-script client opens only its virtual pad, never the user's controller)
            "+set", "in_gamepad", "1"] + sum((["+set", kv.split("=")[0], kv.split("=")[1]] for kv in os.environ.get("ATTIC_SETS", "").split() if "=" in kv), [])


HOME_HOTS = ["options", "mp", "newgame", "brief", "records", "film", "music", "fieldreport", "bugbox", "needle", "rack"]


def gramclip(res="720", tag="arm"):
    """v1.10.62 tone arm: frames at 20 fps through two needle clicks (mouse on the needle + A) and one pad A on the cabinet hotspot:
    lift, track change while the arm is up, drop with the crackle, play"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    s = M.Script(w, h, 1.0)
    fr = [0]

    def rec(sec):
        for _ in range(int(round(sec * 20))):
            s.t += 50
            s.cmd("screenshotJPEG g%05d" % fr[0], 0)
            fr[0] += 1
    s.cmd("echo ^~^~^ GRAM start", 3500)
    s.at((4, 4), 1200)
    close = os.environ.get("GRAM_CLOSE")           # a QA close-up camera on the gramophone: the clicks go through the console
    if close:
        seq = re.search(r'scenehot "needle" (?:\S+ ){4}"([^"]*)"', M.urc("main.urc")).group(1)
        s.cmd("globalwidgetcommand atticscene scenecam %s" % close, 800)
        rec(0.8)
        for _ in range(3):
            s.cmd("echo ^~^~^ GRAM click", 0)
            s.cmd(seq, 0)
            rec(2.0)
        s.cmd("echo ^~^~^ MR done", 800)
        s.cmd("quit", 0)
        sp = s.write("gc_%s_%s.txt" % (tag, res))
        return launch("gc_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))
    rec(0.5)
    s.at(M.hot_px(acam, ahot["needle"], abox.get("needle"), w, h), 300)
    rec(0.8)
    for _ in range(2):
        s.cmd("echo ^~^~^ GRAM click", 0)
        s.press(0x1, 0)
        rec(2.0)
    s.at(M.hot_px(acam, ahot["music"], abox.get("music"), w, h), 300)
    rec(0.5)
    s.press(0x1, 0)
    rec(2.0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("gc_%s_%s.txt" % (tag, res))
    return launch("gc_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def camclip(res="720", tag="fan", pose="212.5 -47.4 115.8 0.00 -49.90 0.00 30.00", sec="3"):
    """a fixed QA camera (scenecam) and frames for `sec` seconds - the fan's blades, the record"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ CAM start", 3500)
    s.at((w // 2, h // 2), 600)          # centred: the attic camera leans towards the cursor
    s.cmd("globalwidgetcommand atticscene scenecam %s" % pose, 1000)
    for i in range(int(float(sec) * 20)):
        s.t += 50
        s.cmd("screenshotJPEG c%05d" % i, 0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("cc_%s_%s.txt" % (tag, res))
    return launch("cc_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def doorpair(res="720", tag="door"):
    """the MULTIPLAYER door straight on from both sides: the attic (fly to a pose 115 u in front of it, looking at it) and the MP
    room (its exit, the hub's own MAIN MENU fly-in pose); scenecam ignores yaw in a live scene, a fly does not"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ DOOR start", 3500)
    s.at((4, 4), 600)
    s.cmd('set ui_scene_pose "336.0 -42.2 73.5 1.30 -90.00 0.00 50.00"', 1200)       # the engine's test pose (cl_uiscene ui_scene_pose)
    s.cmd("screenshot dp_%s_%s_attic" % (tag, res), 800)
    s.cmd('set ui_scene_pose ""', 1200)
    s.cmd("exec ui/hzm_attic_go_mp.cfg", 4000)
    s.cmd("screenshot dp_%s_%s_room" % (tag, res), 800)
    s.cmd('set ui_scene_pose "212.6 59.3 73.5 1.30 90.00 0.00 50.00"', 1200)
    s.cmd("screenshot dp_%s_%s_exit" % (tag, res), 800)
    s.cmd('set ui_scene_pose ""', 300)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("dp_%s_%s.txt" % (tag, res))
    return launch("dp_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def mproom(res="1080", tag="mp"):
    """the MP room's home view: a clean frame, then the mouse on JOIN GAME (its glow + caption)"""
    w, h, center, lay = E.RES[res]
    hcam, hhot, hbox = M.scene_info(M.urc("multiplayer.urc"), "hubscene")
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ MPROOM start", 3500)
    s.at((4, 4), 600)
    s.cmd("exec ui/hzm_attic_go_mp.cfg", 4500)
    s.at((w - 4, 4), 1500)
    s.cmd("screenshot mr_%s_%s_clean" % (tag, res), 800)
    s.at(M.hot_px(hcam, hhot["join"], hbox.get("join"), w, h), 1500)
    s.cmd("screenshot mr_%s_%s_join" % (tag, res), 800)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mr_%s_%s.txt" % (tag, res))
    return launch("mr_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def flows63(res="1080", tag="63"):
    """v1.10.63: projector hover (reels / lit body / clatter), the rack, the flies of FIELD REPORT / REPORT A BUG, BRIEFING -> the 3D
    map, RECORDS -> the 3D desk -> the medal box -> back -> back (all six medals earned for the shot)"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    rcam, rhot, rbox = M.scene_info(M.urc("hzm_records3d.urc"), "records3dscene")
    s = M.Script(w, h, 1.0)
    shot = lambda n, wait=600: s.cmd("screenshot f63_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ F63 start", 3500)
    for k in range(6):
        s.cmd("seta g_medalbt%d 1" % k, 0)
    s.at((4, 4), 1200)
    shot("00idle")
    s.at(M.hot_px(acam, ahot["film"], abox.get("film"), w, h), 1200)
    for k in range(6):
        s.cmd("screenshotJPEG f63_%s_%s_film%d" % (tag, res, k), 160)
    s.at((int(w * 610 / 640), int(h * 233 / 480)), 400)      # the RACK > cue on the right edge: the camera turns right (scenepeek)
    shot("10rack_cue")
    shot("10rack_peek", 900)
    pk = re.search(r'(?m)^scenepeek "rack" \S+ (.*)$', M.urc("main.urc")).group(1).split()
    s.at(M.hot_px([float(v) for v in pk], ahot["rack"], abox.get("rack"), w, h), 700)
    shot("10rack_hover")
    s.press(0x1, 900)
    shot("11rack_fly", 2900)
    shot("12rack_back")
    s.at((int(w * 610 / 640), int(h * 233 / 480)), 1400)
    shot("13rack_peek_again")
    s.at((int(w * 0.2), int(h * 0.5)), 1000)
    shot("14rack_peek_home")
    for k, n in enumerate(("fieldreport", "bugbox", "brief")):
        s.at(M.hot_px(acam, ahot[n], abox.get(n), w, h), 900)
        shot("%d0_%s_hover" % (k + 2, n))
        s.press(0x1, 350)
        shot("%d1_%s_mid" % (k + 2, n), 1600)
        shot("%d2_%s_open" % (k + 2, n))
        s.at((4, 4), 200)
        s.press(0x2, 2600)
        shot("%d3_%s_back" % (k + 2, n))
    s.at(M.hot_px(acam, ahot["records"], abox.get("records"), w, h), 900)
    shot("50records_hover")
    s.press(0x1, 350)
    shot("51records_mid", 1700)
    shot("52desk")
    s.at(M.hot_px(rcam, rhot["medals"], rbox.get("medals"), w, h), 900)
    shot("53desk_box_hover")
    s.at(M.hot_px(rcam, rhot["loadsave"], rbox.get("loadsave"), w, h), 900)
    shot("54desk_trays_hover")
    s.at(M.hot_px(rcam, rhot["medals"], rbox.get("medals"), w, h), 600)
    s.press(0x1, 300)
    shot("55box_opening", 1700)
    shot("56medals")
    s.cmd("set ui_medalsign silverstar_sign; set ui_medaldesc silverstar_desc", 400)
    shot("57medals_desc")
    s.at((4, 4), 200)
    s.press(0x2, 1600)
    shot("58desk_again")
    s.press(0x2, 2600)
    shot("59home")
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("f63_%s_%s.txt" % (tag, res))
    return launch("f63_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def ingame63(res="1080", tag="63"):
    """v1.10.63 in-game path: a DM map loaded, ESC (togglemenu main) -> the attic -> BRIEFING -> 3D map -> back, RECORDS -> desk ->
    medal box -> back -> back -> BACK TO GAME"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    rcam, rhot, rbox = M.scene_info(M.urc("hzm_records3d.urc"), "records3dscene")
    s = M.Script(w, h, 1.0)
    shot = lambda n, wait=600: s.cmd("screenshot ig63_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ IG63 start", 3500)
    s.cmd("set g_gametype 1; map dm/mohdm1", 30000)
    shot("00ingame", 800)
    s.cmd("togglemenu main", 2500)
    s.at((4, 4), 800)
    shot("01esc_attic")
    for k, (n, wo) in enumerate((("brief", 2400), ("records", 2000))):
        s.at(M.hot_px(acam, ahot[n], abox.get(n), w, h), 900)
        shot("%d0_%s_hover" % (k + 1, n))
        s.press(0x1, wo)
        shot("%d1_%s_open" % (k + 1, n))
        if n == "records":
            s.at(M.hot_px(rcam, rhot["medals"], rbox.get("medals"), w, h), 700)
            s.press(0x1, 2000)
            shot("%d2_medals" % (k + 1))
            s.at((4, 4), 200)
            s.press(0x2, 1700)
            shot("%d3_desk_again" % (k + 1))
        s.at((4, 4), 200)
        s.press(0x2, 2600)
        shot("%d4_%s_back" % (k + 1, n))
    s.cmd("togglemenu main", 1500)
    shot("90back_to_game")
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("ig63_%s_%s.txt" % (tag, res))
    return launch("ig63_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def gram63(res="1080", tag="63"):
    """v1.10.63 the gramophone's 8 records: the launch-roll cfgs t6 / t7 (what the engine's roll execs), then NEXT RECORD clicked
    through shuffle -> 1 .. 8 -> shuffle, a shot of the hovered gramophone (sleeve, label, hover box) after each, the track logged"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    s = M.Script(w, h, 1.0)
    shot = lambda n, wait=600: s.cmd("screenshot g63_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ G63 start", 3500)
    for t in (6, 7):
        s.cmd("exec ui/coop_menumusic/t%d.cfg" % t, 1500)
        s.cmd("echo ^~^~^ G63 roll t%d", 0)
        s.cmd("ui_menuMusic", 100)
        s.cmd("ui_menuMusicTitle", 200)
    s.cmd("exec ui/coop_menumusic/ur.cfg", 1500)
    hp = M.hot_px(acam, ahot["music"], abox.get("music"), w, h)
    s.at(hp, 1200)
    shot("00shuffle")
    for k in range(9):
        s.press(0x1, 2600)
        s.cmd("echo ^~^~^ G63 click %d" % (k + 1), 0)
        for c in ("ui_menuMusic", "ui_menuMusicTitle", "ui_mmShuffle"):
            s.cmd(c, 80)
        s.at((4, 4), 150)
        s.at(hp, 900)
        shot("%02d" % (k + 1))
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("g63_%s_%s.txt" % (tag, res))
    return launch("g63_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def snd63(res="720", tag="63"):
    """v1.10.63 sounds, UNMUTED into a .wav (OpenAL Soft wave backend, alsoft.ini next to the exe - nothing reaches a speaker):
    the projector hover loop with the music off, then records 7 / 8 and record 1 (a reference level) at the user's volumes.
    Markers: '^~^~^ SND <name> on/off' in the log (wall-clock stamps); audio_snd63.py measures the windows."""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ SND start", 3500)
    for c in ("set s_volume 0.9", "set s_sfxvolume 1", "set s_musicvolume 0"):
        s.cmd(c, 100)
    s.at((4, 4), 4000)
    s.cmd("echo ^~^~^ SND quiet on", 3000)
    s.cmd("echo ^~^~^ SND quiet off", 0)
    s.at(M.hot_px(acam, ahot["film"], abox.get("film"), w, h), 0)
    s.cmd("echo ^~^~^ SND projector on", 6000)
    s.at((4, 4), 0)
    s.cmd("echo ^~^~^ SND projector off", 3000)
    s.cmd("set s_musicvolume 0.8", 100)
    for name, cfg in (("record7", "u6"), ("record8", "u7"), ("record1", "u0")):
        s.cmd("exec ui/coop_menumusic/%s.cfg" % cfg, 1500)
        s.cmd("echo ^~^~^ SND %s on" % name, 12000)
        s.cmd("echo ^~^~^ SND %s off" % name, 0)
    s.cmd("exec ui/coop_menumusic/ur.cfg", 300)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("snd63_%s_%s.txt" % (tag, res))
    wav = os.path.join(E.RUNS, "snd63_%s_%s.wav" % (tag, res))
    ini = os.path.join(CLIENT, "alsoft.ini")
    open(ini, "w", newline="\n").write("[general]\ndrivers=wave\n\n[wave]\nfile=%s\n" % wav)
    try:
        return launch("snd63_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))
    finally:
        os.remove(ini)


def medals64(res="1080", tag="64"):
    """v1.10.64 the medal box plates: RECORDS -> the desk -> the box -> hover each of the six medals (all earned), a shot each -
    the description plate above and the name plate below must show that medal's vanilla art (ui_medaldesc / ui_medalsign)"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    rcam, rhot, rbox = M.scene_info(M.urc("hzm_records3d.urc"), "records3dscene")
    mt = M.urc("hzm_medals3d.urc")
    mcam = [float(v) for v in re.search(r"(?m)^scenecam (.*)$", mt).group(1).split()]
    labs = {m.group(1): [float(m.group(k)) for k in (2, 3, 4)] for m in re.finditer(r'(?m)^scenelabel "(medal\d)" (\S+) (\S+) (\S+)', mt)}
    s = M.Script(w, h, 1.0)
    shot = lambda n, wait=500: s.cmd("screenshot m64_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ M64 start", 3500)
    for k in range(6):
        s.cmd("seta g_medalbt%d 1" % k, 0)
    s.at(M.hot_px(acam, ahot["records"], abox.get("records"), w, h), 900)
    s.press(0x1, 2400)
    s.at(M.hot_px(rcam, rhot["medals"], rbox.get("medals"), w, h), 700)
    s.press(0x1, 2400)
    s.at((4, 4), 600)
    shot("00none")
    for k in range(6):
        s.at(M.hot_px(mcam, labs["medal%d" % k], None, w, h), 700)
        s.cmd("ui_medaldesc", 50)
        s.cmd("ui_medalsign", 50)
        shot("%02d_medal%d" % (k + 1, k))
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("m64_%s_%s.txt" % (tag, res))
    return launch("m64_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def mpclock66(res="1080", tag="66"):
    """v1.10.66 the MP room's live wall clock: the room, a close-up of the clock twice 6 s apart (the log stamps the PC time of each
    shot), then JOIN GAME (the mpui copy of the room behind the server list, hzm_mpui_scene_join.inc) and its clock"""
    w, h, center, lay = E.RES[res]
    hcam, hhot, hbox = M.scene_info(M.urc("multiplayer.urc"), "hubscene")
    s = M.Script(w, h, 1.0)
    shot = lambda n, wait=600: s.cmd("screenshot mc_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ MPCLOCK start", 3500)
    s.at((4, 4), 600)
    s.cmd("exec ui/hzm_attic_go_mp.cfg", 4500)
    s.at((w - 4, 4), 1500)
    shot("00room")
    s.at(M.hot_px(hcam, hhot["join"], hbox.get("join"), w, h), 1200)
    s.press(0x1, 3500)
    s.at((w - 4, 4), 600)
    shot("01join")
    s.cmd("set ui_scene_pose 230.0 -49.9 128.0 -6.75 0.00 0.00 24.00", 800)
    s.cmd("echo ^~^~^ MPCLOCK shot1", 0)
    shot("02clock", 6000)
    s.cmd("echo ^~^~^ MPCLOCK shot2", 0)
    shot("03clock", 800)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mc_%s_%s.txt" % (tag, res))
    return launch("mc_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def mpclockgif(res="1080", tag="66"):
    """v1.10.66 a short clip of the MP room's live clock: the close-up pose, 24 JPEG frames 0.5 s apart (12 s of real time)"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ MPCLOCKGIF start", 3500)
    s.at((4, 4), 600)
    s.cmd("exec ui/hzm_attic_go_mp.cfg", 4500)
    s.at((w - 4, 4), 1200)
    s.cmd("set ui_scene_pose 230.0 -49.9 128.0 -6.75 0.00 0.00 34.00", 1500)
    for k in range(24):
        s.cmd("screenshotJPEG mg_%s_%s_%02d" % (tag, res, k), 500)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("mg_%s_%s.txt" % (tag, res))
    return launch("mg_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def padnav(res="720", tag="pad", moves="DDRRRLLLLUUU", press_at=None):
    """D-pad walk from the idle home view (the hotspots' proxies use spatial navigation), a shot after every move; optional A after
    move `press_at` (1-based) and a shot of what opened"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    bits = {"R": 0x4000, "L": 0x2000, "U": 0x800, "D": 0x1000}
    s.cmd("echo ^~^~^ PAD start", 3500)
    s.at((4, 4), 1200)
    s.cmd("screenshot pn_%s_%s_00" % (tag, res), 500)
    for i, m in enumerate(moves):
        s.press(bits[m], 500)
        s.cmd("screenshot pn_%s_%s_%02d%s" % (tag, res, i + 1, m), 400)
        if press_at and i + 1 == int(press_at):
            s.press(0x1, 1800)
            s.cmd("screenshot pn_%s_%s_%02dA" % (tag, res, i + 1), 500)
            s.press(0x2, 1800)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("pn_%s_%s.txt" % (tag, res))
    return launch("pn_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def flows(res="720", tag="flow", slow=1.0):
    """v1.10.62 click paths: FIELD REPORT board -> What's New, toolbox -> Report a Bug, the moved briefing door -> briefing room,
    the MP door -> MP room -> its exit; then the pad path (D-pad right through every home hotspot, A on the FIELD REPORT board)"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    s = M.Script(w, h, slow)
    shot = lambda n, wait=600: s.cmd("screenshot fl_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ FLOWS start", 3500)
    s.at((4, 4), 1200)
    shot("00idle")
    for k, (n, open_wait, back_wait) in enumerate((("fieldreport", 1500, 1800), ("bugbox", 1500, 1800), ("brief", 2200, 2600), ("mp", 3000, 3200))):
        s.at(M.hot_px(acam, ahot[n], abox.get(n), w, h), 900)
        shot("%d0_%s_hover" % (k + 1, n))
        s.cmd("echo ^~^~^ FLOW click %s" % n, 0)
        s.press(0x1, 400)
        shot("%d1_%s_mid" % (k + 1, n), open_wait)
        shot("%d2_%s_open" % (k + 1, n))
        s.at((4, 4), 200)
        s.press(0x2, back_wait)
        shot("%d3_%s_back" % (k + 1, n))
    s.at((4, 4), 600)
    for i in range(16):
        s.press(0x4000, 500)
        shot("6%02d_pad" % i, 300)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("fl_%s_%s.txt" % (tag, res))
    return launch("fl_%s_%s" % (tag, res), w, h, boot_lines(center, slow), boot_args(center, sp))
RADIOS = ["video", "graphics", "effects", "audio", "controls", "gameplay"]


def survey(res="1080", tag="before", slow=1.0):
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    ncam, nhot, nbox = M.scene_info(M.urc("hzm_newgame3d.urc"), "ngscene")
    s = M.Script(w, h, slow)
    shot = lambda n, wait=600: s.cmd("screenshot sv_%s_%s_%s" % (tag, res, n), wait)  # noqa: E731
    s.cmd("echo ^~^~^ SURVEY start", 3500)
    s.at((4, 4), 1500)
    shot("00idle")
    for i, n in enumerate(h_ for h_ in HOME_HOTS if h_ in ahot):
        s.at(M.hot_px(acam, ahot[n], abox.get(n), w, h), 900)
        shot("1%d_%s" % (i, n))
    s.at((4, 4), 300)
    # the radio shelf stop (OPTIONS) and its six radios
    s.cmd("exec ui/hzm_attic_go_options.cfg", 1800)
    shot("20shelf")
    import numpy as np  # noqa
    shelf = re.search(r"scenereturn ((?:\S+ ){6}\S+);", M.urc("main.urc")).group(1).split()
    scam = [float(v) for v in shelf]
    for i, n in enumerate(RADIOS):
        s.at(M.hot_px(scam, ahot[n], abox.get(n), w, h), 900)
        shot("2%d_%s" % (i + 1, n))
    s.at((4, 4), 300)
    s.press(0x2, 2200)                  # B: shelf -> home
    shot("29home_again")
    # NEW GAME: the wall map and its markers (g_t2l1 1, g_t3l1 0: Sicily open, Italy locked)
    s.cmd("exec ui/hzm_attic_go_newgame.cfg", 2600)
    shot("30map")
    for i, n in enumerate(k for k in nhot):
        s.at(M.hot_px(ncam, nhot[n], nbox.get(n), w, h), 900)
        shot("3%d_%s" % (i + 1, n))
    s.at((4, 4), 300)
    s.press(0x2, 2600)
    shot("39home_after_map")
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("sv_%s_%s.txt" % (tag, res))
    return launch("sv_%s_%s" % (tag, res), w, h, boot_lines(center, slow), boot_args(center, sp))


def still(res="1080", tag="scout", cmds=()):
    """idle home view (+ optional console commands, one shot after each)"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ STILL start", 3500)
    s.at((4, 4), 1200)
    s.cmd("screenshot st_%s_%s_00" % (tag, res), 600)
    for i, c in enumerate(cmds):
        s.cmd(c, 900)
        s.cmd("screenshot st_%s_%s_%02d" % (tag, res, i + 1), 600)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("st_%s_%s.txt" % (tag, res))
    return launch("st_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))



WX_HOME = "-36.7 21.0 102.4 7.01 0.00 0.00 55.11"
WX_CLOSE = os.environ.get("WX_CLOSE", "315.0 210.0 84.0 0.00 0.00 0.00 62.00")      # = the window hotspot's pose
WX_STATES = [("day", 12.5, 1), ("golden", 18.6, 1), ("dusk", 19.9, 1), ("night", 23.0, 1), ("dawn", 6.6, 1),
             ("overcast", 13.0, 2), ("rain", 14.0, 3), ("storm", 15.0, 4), ("nightrain", 23.5, 3)]


def wx67(res="1080", tag="67", only="", burst="0"):
    """v1.10.67 the window's outside: every time/weather state from the home camera and a close camera on the pane
    (ui_wxHour / ui_wxWeather force the state; a forced weather change cuts). burst=1: after each storm state a lightning strike
    (ui_wxFlash 1) and 16 frames at 50 ms to catch the flash and the room lighting up."""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ WX start", 3500)
    s.at((4, 4), 600)          # (the corner: with the cursor mid-screen a ui_scene_pose hold did not take)
    s.cmd("set ui_wxDebug 1", 300)
    for name, hr, wx in WX_STATES:
        if only and name not in only.split(","):
            continue
        s.cmd("set ui_wxHour %g; set ui_wxWeather %d" % (hr, wx), 2200)
        s.cmd("screenshot wx_%s_%s_%s_home" % (tag, res, name), 700)
        s.cmd("set ui_scene_pose \"%s\"; set ui_scene_hot 0; wait 5; set ui_atcStop 3" % WX_CLOSE, 1800)     # = the hotspot
        s.cmd("screenshot wx_%s_%s_%s_close" % (tag, res, name), 700)
        if burst == "1" and wx == 4:
            for hv in ("1", "0.5"):                      # the strike frozen at its peak and half way (ui_wxFlashHold): close, then home
                s.cmd("set ui_wxFlashHold %s" % hv, 500)
                s.cmd("screenshot wx_%s_%s_%s_flash%s_close" % (tag, res, name, hv.replace(".", "")), 500)
            s.cmd("set ui_wxFlashHold -1", 300)
        s.cmd("set ui_scene_pose \"%s\"; set ui_atcStop 0" % WX_HOME, 1200)   # the home camera held the same way (clearing the hold left the close pose)   # (ui_scene_pose: the QA hold - a console scenefly did not move the camera)
    if not only or "hot" in only.split(","):
        # the window hotspot: hover (glow + LOOK OUTSIDE), pad A = fly to the close view (BACK tab), pad B = home
        acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
        s.cmd("set ui_scene_pose 0; set ui_wxHour 12.5; set ui_wxWeather 1", 600)      # release the hold (the camera stays home)
        s.at(M.hot_px(acam, ahot["window"], abox.get("window"), w, h), 900)
        s.cmd("screenshot wx_%s_%s_hot_hover" % (tag, res), 500)
        s.press(0x1, 1600)
        s.cmd("screenshot wx_%s_%s_hot_open" % (tag, res), 500)
        s.press(0x2, 1600)
        s.cmd("screenshot wx_%s_%s_hot_back" % (tag, res), 500)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wx_%s_%s.txt" % (tag, res))
    return launch("wx_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def wxgif(res="1080", tag="67", weather="4", hour="15", sec="7", strike_at="2.5"):
    """v1.10.67 frames for the rain + lightning GIF: the close window view, `sec` s at 20 fps, a strike at `strike_at` s"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ WXGIF start", 3500)
    s.at((4, 4), 600)          # (the corner: with the cursor mid-screen a ui_scene_pose hold did not take)
    s.cmd("set ui_wxHour %s; set ui_wxWeather %s" % (hour, weather), 300)
    s.cmd("set ui_scene_pose \"%s\"; set ui_scene_hot 0; wait 5; set ui_atcStop 3" % WX_CLOSE, 2500)     # = the hotspot
    n = int(float(sec) * 20)
    k_strike = int(float(strike_at) * 20)
    for i in range(n):
        if i == k_strike:
            s.cmd("set ui_wxFlash 1", 0)
        s.t += 50
        s.cmd("screenshotJPEG wg%05d" % i, 0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wg_%s_%s.txt" % (tag, res))
    return launch("wg_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def wxflashab(res="1080", tag="ab"):
    """v1.10.67 QA: three strikes in the close window view - (A) as shipped, (B) the room glow off (ui_wxRoomFlash 0), (C) the window
    layers' share off (ui_wxFlashGain 0) - 20 fps JPEG frames, to see which part of the strike blows the frame out"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ WXAB start", 3500)
    s.at((4, 4), 600)          # (the corner: with the cursor mid-screen a ui_scene_pose hold did not take)
    s.cmd("set ui_wxHour 15; set ui_wxWeather 3; set ui_wxDebug 1", 300)
    s.cmd("set ui_scene_pose \"%s\"; set ui_scene_hot 0; wait 5; set ui_atcStop 3" % WX_CLOSE, 2500)     # = the hotspot
    plan = {30: "echo ^~^~^ STRIKE A; set ui_wxFlash 1", 80: "echo ^~^~^ STRIKE B; set ui_wxRoomFlash 0; set ui_wxFlash 1",
            130: "echo ^~^~^ STRIKE C; set ui_wxRoomFlash 1; set ui_wxFlashGain 0; set ui_wxFlash 1"}
    for i in range(170):
        if i in plan:
            s.cmd(plan[i], 0)
        s.t += 50
        s.cmd("screenshotJPEG wab%05d" % i, 0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wab_%s_%s.txt" % (tag, res))
    return launch("wab_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def wxqa2(res="1080", tag="q2"):
    """v1.10.67 QA in one short run: (1) the strike frozen (ui_wxFlashHold) at 1.0 / 0.5 in the window view - as shipped, the room
    glow off, the window layers off; (2) the ambience: every one-shot played once by name (ui_wxAmbTest) and the loop levels per
    weather / view, all logged (^~^~^ WXAMB) - the run is muted, the log is the check"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ WXQA2 start", 3500)
    s.at((4, 4), 600)          # (the corner: with the cursor mid-screen a ui_scene_pose hold did not take)
    s.cmd("set ui_wxDebug 1; set ui_wxHour 15; set ui_wxWeather 4", 300)
    s.cmd("set ui_scene_pose \"%s\"; set ui_scene_hot 0; wait 5; set ui_atcStop 3" % WX_CLOSE, 2600)     # = the hotspot
    for tagf, cmd in (("h10", "set ui_wxFlashHold 1"), ("h10room0", "set ui_wxRoomFlash 0"),
                      ("h10gain0", "set ui_wxRoomFlash 1; set ui_wxFlashGain 0"), ("h05", "set ui_wxFlashGain 1; set ui_wxFlashHold 0.5"),
                      ("h00", "set ui_wxFlashHold 0")):
        s.cmd(cmd, 700)
        s.cmd("screenshot wq_%s_%s_%s" % (tag, res, tagf), 600)
    s.cmd("set ui_wxFlashHold -1", 300)
    for n in ("wx_bell", "wx_owl", "wx_dog1", "wx_train", "wx_whistle", "wx_pa1", "wx_gust1", "wx_birds1", "wx_cricket", "wx_tank1", "wx_chat1", "wx_chat6"):
        s.cmd("set ui_wxAmbTest %s" % n, 500)
    for wx, hr in ((3, 13), (1, 12), (1, 23), (2, 13)):
        s.cmd("set ui_wxWeather %d; set ui_wxHour %d" % (wx, hr), 2300)
    s.cmd("set ui_scene_pose 0; set ui_atcStop 0; globalwidgetcommand atticscene scenecam -36.7 21.0 102.4 7.01 0.00 0.00 55.11", 2300)
    s.cmd("set ui_wxHour 8.995", 1500)
    s.cmd("set ui_wxHour 9.002", 3500)
    s.cmd("set ui_wxAmbience 0", 2300)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wq_%s_%s.txt" % (tag, res))
    return launch("wq_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


WX_LOOKUP = "202.7 112.4 70.5 -65.50 90.00 0.00 70.00"


def wxplane(res="1080", tag="pl", which="sky", ptype="5", sec="9", start="0.5"):
    """v1.10.67 an aircraft pass, 20 fps frames: which = sky (the LOOK UP pose, ui_wxPlane 5-7) or gable (the window pose, 1-4)"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    s.cmd("echo ^~^~^ WXPLANE start", 3500)
    s.at((4, 4), 600)
    pose = WX_LOOKUP if which == "sky" else WX_CLOSE
    s.cmd("set ui_wxDebug 2; set ui_wxHour 13; set ui_wxWeather 1; set ui_wxPlaneTest 1", 300)
    s.cmd("set ui_scene_pose \"%s\"; set ui_scene_hot 0; wait 5; set ui_atcStop %d" % (pose, 4 if which == "sky" else 3), 2500)
    n = int(float(sec) * 20)
    for i in range(n):
        if i == int(float(start) * 20):
            s.cmd("set ui_wxPlane %s" % ptype, 0)
        s.t += 50
        s.cmd("screenshotJPEG wp%05d" % i, 0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wp_%s_%s.txt" % (tag, res))
    return launch("wp_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def wxback(res="1080", tag="bk"):
    """v1.10.67 REAL clicks only (user: BACK did not fly home from either window view): home -> LOOK OUTSIDE (cursor on the hotspot,
    pad A) -> BACK tab (cursor on it, pad A); again with pad B; LOOK UP the same two ways. A still after every step; the log has
    the engine's fly / sceneback / tryescape lines (ui_scene_debug 1)"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    s.cmd("echo ^~^~^ WXBACK start; set ui_scene_debug 1", 3500)
    s.at((w // 2, h // 2), 1200)
    # the BACK tab: rect 8 446 64 24 in the 640x480 virtual screen, laid out like the other edge cues
    sc = h / 480.0
    ox = (w - 640 * sc) / 2 if center else 0
    tab = (int(ox + (8 + 32) * sc), int((446 + 12) * sc))
    n = [0]

    def shot(name):
        s.cmd("screenshot wb_%s_%s_%02d_%s" % (tag, res, n[0], name), 400)
        n[0] += 1
    shot("home")
    for hot in ("window", "lookup"):
        for how in ("tab", "padB"):
            s.at(M.hot_px(acam, ahot[hot], abox.get(hot), w, h), 900)
            s.press(0x1, 1600)
            shot("%s_open" % hot)
            if how == "tab":
                s.at(tab, 700)
                s.press(0x1, 1600)
            else:
                s.at((w // 2, h // 2), 500)
                s.press(0x2, 1600)
            shot("%s_back_%s" % (hot, how))
            s.at((w // 2, h // 2), 600)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wb_%s_%s.txt" % (tag, res))
    return launch("wb_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))


def wxamb(res="1080", tag="am"):
    """v1.10.67 ambience levels, REAL clicks for the view changes, logged (muted run): home rain -> LOOK OUTSIDE -> the SOUND tab
    cycled LOW -> MED -> OFF -> LOW -> BACK; one-shots by name at home and at the window (which file plays: _h at home)"""
    w, h, center, lay = E.RES[res]
    s = M.Script(w, h, 1.0)
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    sc = h / 480.0
    ox = (w - 640 * sc) / 2 if center else 0
    snd = (int(ox + (78 + 42) * sc), int((446 + 12) * sc))
    s.cmd("echo ^~^~^ WXAMB start; set ui_wxDebug 1; set ui_wxHour 14; set ui_wxWeather 3; seta ui_wxAmbLevel 1", 3500)
    s.at((w // 2, h // 2), 3000)
    s.cmd("set ui_wxAmbTest wx_bell", 2500)
    s.at(M.hot_px(acam, ahot["window"], abox.get("window"), w, h), 900)
    s.press(0x1, 3000)
    s.cmd("set ui_wxAmbTest wx_bell", 2500)
    for k in range(3):
        s.at(snd, 600)
        s.press(0x1, 2600)
        s.cmd("echo ^~^~^ WXAMB level now", 0)
        s.cmd("cvarlist ui_wxAmbLevel", 300)
    s.at(snd, 600)
    s.press(0x1, 1500)
    s.press(0x2, 3000)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("wa_%s_%s.txt" % (tag, res))
    return launch("wa_%s_%s" % (tag, res), w, h, boot_lines(center, 1.0), boot_args(center, sp))

def video(res="1080", tag="after", slow=4.0):
    """frames on a fixed beat (20 fps of menu time, ui_camslow stretches the moves so every frame is captured)"""
    w, h, center, lay = E.RES[res]
    acam, ahot, abox = M.scene_info(M.urc("main.urc"), "atticscene")
    ncam, nhot, nbox = M.scene_info(M.urc("hzm_newgame3d.urc"), "ngscene")
    s = M.Script(w, h, slow)
    beat = int(round(1000.0 / 20.0 * slow))
    fr = [0]

    def rec(sec):
        for _ in range(int(round(sec * 20))):
            s.t += beat
            s.cmd("screenshotJPEG v%05d" % fr[0], 0)
            fr[0] += 1
    s.cmd("echo ^~^~^ VIDEO start", 3500)
    s.at((int(w * 0.5), int(h * 0.04)), 80)
    rec(1.5)
    for n in ("options", "newgame", "records", "film", "mp", "brief"):
        s.at(M.hot_px(acam, ahot[n], abox.get(n), w, h), 80)
        rec(1.2)
    if "music" in ahot:          # the gramophone: hover, two records forward, one back (the card follows)
        s.at(M.hot_px(acam, ahot["music"], abox.get("music"), w, h), 80)
        rec(1.0)
        for _ in range(2):
            s.press(0x1, 0)
            rec(1.3)
        s.cmd("vstr ui_mmSelPrev", 0)
        rec(1.3)
    s.at(M.hot_px(acam, ahot["newgame"], abox.get("newgame"), w, h), 80)
    rec(0.4)
    s.press(0x1, 0)
    rec(2.2)
    for n in nhot:
        s.at(M.hot_px(ncam, nhot[n], nbox.get(n), w, h), 80)
        rec(1.0)
    s.at((int(w * 0.5), int(h * 0.04)), 80)
    s.press(0x2, 0)
    rec(2.4)
    s.at(M.hot_px(acam, ahot["options"], abox.get("options"), w, h), 80)
    rec(0.4)
    s.press(0x1, 0)
    rec(1.6)
    shelf = [float(v) for v in re.search(r"scenereturn ((?:\S+ ){6}\S+);", M.urc("main.urc")).group(1).split()]
    for n in RADIOS:
        s.at(M.hot_px(shelf, ahot[n], abox.get(n), w, h), 80)
        rec(0.7)
    s.at((int(w * 0.5), int(h * 0.04)), 80)
    s.press(0x2, 0)
    rec(2.0)
    s.cmd("echo ^~^~^ MR done", 800)
    s.cmd("quit", 0)
    sp = s.write("vid_%s_%s.txt" % (tag, res))
    return launch("vid_%s_%s" % (tag, res), w, h, boot_lines(center, slow) + ["set cl_maxfps 60"], boot_args(center, sp))


def _pose_to(cam, pt, fov):
    """a ui_scene_pose from camera `cam` (game units) looking at `pt` (pitch positive = down)"""
    d = [pt[i] - cam[i] for i in range(3)]
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = -math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return "%.1f %.1f %.1f %.2f %.2f 0.00 %.2f" % (cam[0], cam[1], cam[2], pitch, yaw, fov)


def wxstill(res="1080", tag="t68", states="day,golden,night", zoom="1"):
    """NO pad script, no input (user 2026-11-09 evening: they play on the TV with a controller - no virtual-pad runs): a boot cfg of
    cvars, waits (MILLISECONDS in this engine: Cbuf_Execute retires `wait N` by frame msec) and screenshots. Per state: the home camera, the LOOK OUTSIDE pose, and with zoom=1
    narrow-fov close-ups from the look-out camera (a grid over the town + every banner, WX_TOWN marks.json) for the mistake hunt."""
    w, h, center, lay = E.RES[res]
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow 1",
         "set coop_hardcore 0", "set ui_wxDebug 1", "wait 12000", "echo ^~^~^ WXS start"]
    cam = [float(v) for v in WX_CLOSE.split()[:3]]
    zooms = []
    if zoom == "1":
        for yw in (2, 10, 18, 26, 34):
            for pt in (2.5, 5.5):
                zooms.append(("g%02d_%02d" % (yw, int(pt * 10)), "%.1f %.1f %.1f %.2f %.2f 0.00 16.00" % (cam[0], cam[1], cam[2], pt, yw)))
        mk = os.path.join(os.environ.get("WX_TOWN", r"H:\hzm_work\wx\town68"), "marks.json")
        if os.path.exists(mk):
            for i, m in enumerate(x for x in json.load(open(mk)) if x["kind"].startswith("banner")):
                p_ = [v * 52.5 for v in m["p"]]
                p_[2] -= float(m["kind"].split(":")[2]) * 52.5 * m["size"] * 0.5
                zooms.append(("ban%d" % i, _pose_to(cam, p_, 12.0)))
    zooms.insert(0, ("home", "-36.7 21.0 102.4 1.60 27.40 0.00 8.00"))          # the main menu's pane, magnified (its own eye)
    for kv in [x for x in os.environ.get("WX_EXTRA_ZOOMS", "").split(";") if "=" in x]:     # name=pose;name=pose (extra close-ups)
        zooms.append(tuple(kv.split("=", 1)))
    if os.environ.get("WX_ONLY_EXTRA"):
        zooms = [z for z in zooms if z[0] in [kv.split("=")[0] for kv in os.environ["WX_EXTRA_ZOOMS"].split(";")]]
    for name, hr, wx in WX_STATES:
        if name not in states.split(","):
            continue
        L += ["set ui_wxHour %g; set ui_wxWeather %d" % (hr, wx), "wait 3000",
              'set ui_scene_pose "%s"; set ui_atcStop 0' % WX_HOME, "wait 2000", "screenshot wxs_%s_%s_%s_home" % (tag, res, name), "wait 700",
              'set ui_scene_pose "%s"; set ui_atcStop 3' % WX_CLOSE, "wait 2000", "screenshot wxs_%s_%s_%s_close" % (tag, res, name), "wait 700"]
        for zn, zp in zooms:
            L += ['set ui_scene_pose "%s"' % zp, "wait 1000", "screenshot wxs_%s_%s_%s_z%s" % (tag, res, name, zn), "wait 600"]
    L += ["echo ^~^~^ MR done", "wait 1500", "quit"]
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30"] +         sum((["+set", kv.split("=")[0], kv.split("=")[1]] for kv in os.environ.get("ATTIC_SETS", "").split() if "=" in kv), [])
    return launch("wxs_%s_%s" % (tag, res), w, h, L, args)



def st68(res="1080", tag="s68", states="day,golden,night", parts="wx,attic,play,mp"):
    """v1.10.68 stills, NO input (the user plays on the TV): a boot cfg of cvars, waits (ms) and screenshots.
    wx: the window views + the horizon grid (trees). attic: the right-hand wall (pull-down screen, the turned projector), idle and
    running (ui_scene_fxon film). play: the film room's framed PLAY simulated (pushmenu filmroom, then hzm_frplay.cfg's steps inline
    with screenshots between; ui_frPlayCmd is an echo - never a demo, no map loads). mp: the MP room with the rack, its caption, the
    weapon viewer opened from it (hzm_attic_go_rack.cfg)."""
    w, h, center, lay = E.RES[res]
    P = parts.split(",")
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow 1",
         "set coop_hardcore 0", "set ui_wxDebug 1", "wait 12000", "echo ^~^~^ ST68 start"]
    cam = [float(v) for v in WX_CLOSE.split()[:3]]
    grid = [("g%02d_%02d" % (yw, int(pt * 10)), "%.1f %.1f %.1f %.2f %.2f 0.00 16.00" % (cam[0], cam[1], cam[2], pt, yw))
            for yw in (-6, 2, 10, 18, 26, 34) for pt in (2.5, 5.5)] + [("home", "-36.7 21.0 102.4 1.60 27.40 0.00 8.00")]
    A68 = [("peek", "-36.7 21.0 102.4 7.01 -35.00 0.00 55.11"),
           ("wall", "150.0 -40.0 95.0 8.00 -125.00 0.00 60.00"),
           ("screen", "81.0 -60.0 86.0 0.00 -90.00 0.00 62.00"),
           ("proj", _pose_to((140.0, -20.0, 85.0), (105.0, -54.0, 62.0), 34.0)),
           ("projside", _pose_to((60.0, -35.0, 80.0), (104.0, -56.0, 62.0), 30.0)),
           ("scrzoom", _pose_to((81.0, -100.0, 86.0), (81.0, -150.0, 86.0), 40.0)),
           ("scrcase", _pose_to((70.0, -120.0, 118.0), (75.0, -153.0, 124.0), 30.0))]
    for name, hr, wx in WX_STATES:
        if name not in states.split(","):
            continue
        L += ["set ui_wxHour %g; set ui_wxWeather %d" % (hr, wx), "wait 3000",
              'set ui_scene_pose "%s"; set ui_atcStop 0' % WX_HOME, "wait 2000", "screenshot st_%s_%s_%s_home" % (tag, res, name), "wait 700"]
        if "wx" in P:
            L += ['set ui_scene_pose "%s"; set ui_atcStop 3' % WX_CLOSE, "wait 2000", "screenshot st_%s_%s_%s_close" % (tag, res, name), "wait 700"]
            for zn, zp in (grid if name != "night" else grid[-3:]):
                L += ['set ui_scene_pose "%s"' % zp, "wait 1000", "screenshot st_%s_%s_%s_z%s" % (tag, res, name, zn), "wait 600"]
        if "attic" in P and name == "day":
            L += ["set ui_atcStop 0"]
            for zn, zp in A68:
                L += ['set ui_scene_pose "%s"' % zp, "wait 1000", "screenshot st_%s_%s_%s_a%s" % (tag, res, name, zn), "wait 600"]
            L += ["set ui_scene_fxon film", "wait 800"]
            for zn, zp in A68:
                L += ['set ui_scene_pose "%s"' % zp, "wait 1000", "screenshot st_%s_%s_%s_a%s_run" % (tag, res, name, zn), "wait 600"]
            L += ['set ui_scene_fxon ""']
    L += ['set ui_scene_pose ""; set ui_atcStop 0; set ui_wxHour 12.5; set ui_wxWeather 1', "wait 2500"]
    if "play" in P:
        pic = json.load(open(r"H:\hzm_work\attic62\attic68.json"))["screen"]["pic"]
        scr = "%.1f %.1f %.1f 0.00 -90.00 0.00 50.00" % (pic[0], pic[1] + 72.0, pic[2])
        L += ["set ui_frTransition exec ui/hzm_frplay.cfg", "pushmenu filmroom", "wait 2500", "screenshot st_%s_%s_play0_filmroom" % (tag, res),
              'set ui_frPlayCmd "echo ^~^~^ FILMSTART"', "set ui_scene_hot 0", "set ui_scene_fxon film", "popmenu 0", "wait 50",
              "globalwidgetcommand atticscene scenefly 1.8 %s" % scr, "wait 500", "screenshot st_%s_%s_play1" % (tag, res),
              "wait 600", "screenshot st_%s_%s_play2" % (tag, res), "wait 1000", "screenshot st_%s_%s_play3" % (tag, res),
              "uiveil 1 0.35", "wait 200", "screenshot st_%s_%s_play4_veil" % (tag, res), "wait 200", 'set ui_scene_fxon ""', "vstr ui_frPlayCmd",
              "wait 300", "uiveil 0 0.2", "wait 1500",
              "globalwidgetcommand atticscene scenecam -36.7 21.0 102.4 7.01 0.00 0.00 55.11", "wait 1500"]
    if "mp" in P:
        L += ["exec ui/hzm_attic_go_mp.cfg", "wait 3500", "screenshot st_%s_%s_mp_home" % (tag, res), "wait 600",
              "set ui_scene_hot 6", "wait 1500", "screenshot st_%s_%s_mp_rackcap" % (tag, res), "set ui_scene_hot 0", "wait 400",
              "globalwidgetcommand hubscene scenecam 30.0 60.0 95.0 4.00 50.00 0.00 55.00", "wait 900", "screenshot st_%s_%s_mp_rackwide" % (tag, res),
              "globalwidgetcommand hubscene scenecam 112.0 95.0 100.0 0.00 90.00 0.00 55.00", "wait 900", "screenshot st_%s_%s_mp_rackfront" % (tag, res),
              "globalwidgetcommand hubscene scenecam 70.0 120.0 110.0 10.00 40.00 0.00 45.00", "wait 900", "screenshot st_%s_%s_mp_rackside" % (tag, res),
              "globalwidgetcommand hubscene scenecam -70.9 15.8 86.6 4.00 -3.00 0.00 58.00", "wait 900",
              "exec ui/hzm_attic_go_rack.cfg", "wait 3000", "screenshot st_%s_%s_mp_viewer" % (tag, res), "wait 600"]
    L += ["echo ^~^~^ MR done", "wait 1500", "quit"]
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30"]
    return launch("st_%s_%s" % (tag, res), w, h, L, args)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "setup":
        setup()
    elif a[0] == "survey":
        survey(a[1] if len(a) > 1 else "1080", a[2] if len(a) > 2 else "before")
    elif a[0] == "still":
        still(a[1], a[2], a[3:])
    elif a[0] == "camclip":
        camclip(*a[1:])
    elif a[0] == "st68":
        st68(*a[1:])
    elif a[0] == "wxstill":
        wxstill(*a[1:])
    elif a[0] == "wx67":
        wx67(*a[1:])
    elif a[0] == "wxgif":
        wxgif(*a[1:])
    elif a[0] == "wxflashab":
        wxflashab(*a[1:])
    elif a[0] == "wxqa2":
        wxqa2(*a[1:])
    elif a[0] == "wxplane":
        wxplane(*a[1:])
    elif a[0] == "wxback":
        wxback(*a[1:])
    elif a[0] == "wxamb":
        wxamb(*a[1:])
    elif a[0] == "doorpair":
        doorpair(*a[1:])
    elif a[0] == "mproom":
        mproom(*a[1:])
    elif a[0] == "mpclockgif":
        mpclockgif(*a[1:])
    elif a[0] == "mpclock66":
        mpclock66(*a[1:])
    elif a[0] == "medals64":
        medals64(*a[1:])
    elif a[0] == "snd63":
        snd63(*a[1:])
    elif a[0] == "gram63":
        gram63(*a[1:])
    elif a[0] == "ingame63":
        ingame63(*a[1:])
    elif a[0] == "flows63":
        flows63(*a[1:])
    elif a[0] == "padnav":
        padnav(a[1] if len(a) > 1 else "720", a[2] if len(a) > 2 else "pad", a[3] if len(a) > 3 else "DDRRRLLLLUUU", a[4] if len(a) > 4 else None)
    elif a[0] == "gramclip":
        gramclip(a[1] if len(a) > 1 else "720", a[2] if len(a) > 2 else "arm")
    elif a[0] == "flows":
        flows(a[1] if len(a) > 1 else "720", a[2] if len(a) > 2 else "flow")
    elif a[0] == "video":
        video(a[1] if len(a) > 1 else "1080", a[2] if len(a) > 2 else "after")

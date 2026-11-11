#!/usr/bin/env python3
"""liveops_test.py - Live Operations on a PRIVATE client (v1.10.71). Nothing is deployed anywhere.

Client:  G:\\mohaa-liveops (byte copies of the liveops-eng build + the shipped v1.10.70 dlls), basepath = the GOG tree
         read-only, home G:\\mohaa-liveops\\home (harness_guard classifies it HARNESS). The lane's mod changes ride in ONE
         test pak in that home (zzzz..._liveops.pk3, built by `pak`). Started ONLY by harness_window.launch_background:
         the test display is picked by resolution (HZM_TEST_RES, default 3440x1440), never focused, cursor/capture/audio
         guard ENFORCED, job object, muted, in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0; the coop un-mute cvars
         (TRAPS T14) are zeroed after autoexec. Input = console binds posted to OUR window. No pad scripts.
On ANY guard violation every launch stops and the run reports it.

    python liveops_test.py pak                build the test pak from H:/hzm_work/liveops-mod
    python liveops_test.py board              the NEW GAME wall with contracts (+ dump parity vs gen_ops.py), a hover
                                              slip and an open card (stills)
    python liveops_test.py tdm [--map M]      deploy a TEAM MATCH contract, play it out (short limit), return (stills)
    python liveops_test.py obj [--map M]      deploy an OBJECTIVE contract, the round is called, return
    python liveops_test.py flat               the flat chooser (ui_atticMain 0) strip + card
    python liveops_test.py lib [--map M] [--end win|lose|time|none]
                                              a LIBERATION contract: card, DEPLOY, curtain / placement / co-op kit /
                                              objective / radio / clock, the hunt, the result, the return (stills)
    --lane lib                                the Liberation lane's own client and trees (G:\\mohaa-lib, H:/hzm_work/lib-mod)
Results: H:\\hzm_work\\liveops-test\\runs\\<case>\\ (logs, result.json, png - local only)."""
import json, os, re, shutil, subprocess, sys, time, zipfile

TOOLS = r"C:\mohaa-coop-dev\docs\tools"   # the LIVE harness guard / window policy (read only)
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import harness_guard as hg     # noqa: E402
import harness_window as hw    # noqa: E402
import gen_ops                 # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
A = r"G:\mohaa-liveops"
HOME = os.path.join(A, "home")
MOD = r"H:\hzm_work\liveops-mod"
RUNS = r"H:\hzm_work\liveops-test\runs"
PAK = "zzzzzzzzzzzzzzzzzzzzzz_liveops.pk3"
PORT = 12293
SLOT = "liveops"
if "--lane" in sys.argv and sys.argv[sys.argv.index("--lane") + 1] == "lib":
    A = r"G:\mohaa-lib"
    HOME = os.path.join(A, "home")
    MOD = r"H:\hzm_work\lib-mod"
    RUNS = r"H:\hzm_work\liberacion\runs"
    PORT = 12953
    SLOT = "liberacion"
MOD = os.environ.get("LIVEOPS_MOD", MOD)   # test a merged tree with a lane's client
VK = {"F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}
TRIPPED = []
MUTE = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set con_notifytime -1", "set coop_joinCard 0",
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "set coop_whatsNewSeen 99999",
        "set developer 1", "set logfile 2"]
PAK_FILES = ["ui/hzm_newgame3d.urc", "ui/hzm_ngflat.urc", "scripts/hzm_ng3campaigns.shader", "coop_mod/mp.scr", "coop_mod/mp_armory.scr",
             "coop_mod/mp_bots.scr", "coop_mod/mp_hardcore.scr", "coop_mod/mp_weather.scr", "coop_mod/mp_ops.scr",
             "coop_mod/mp_ops_table.scr", "coop_mod/mp_armory.scr", "coop_mod/mp_dbno.scr", "coop_mod/mp_ops_text.scr", "coop_mod/libbridge.scr",
             "ubersound/coop_audio.scr", "sound/coop_vo/den_coop_lib_briefing.wav",
             "coop_mod/mp_medkits.scr", "coop_mod/mp_spawnprotect.scr", "global/localization_coop.txt",
             "coop_mod/challenges.scr"]


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def read(p):
    try:
        return open(p, "rb").read().decode("latin-1")
    except OSError:
        return ""


def build_pak():
    out = os.path.join(HOME, "maintt", PAK)
    if "--nopak" in sys.argv:                      # the shipped paks only (reproduce a released bug)
        if os.path.exists(out):
            os.remove(out)
        print("no test pak")
        return out
    files = PAK_FILES if "--urconly" not in sys.argv else ["ui/hzm_newgame3d.urc"]
    if "--armoryonly" in sys.argv:                 # the mod-only DEPLOY hotfix (b0627b2e) and nothing else
        files = ["coop_mod/mp_armory.scr"]
    if "--hotfix" in sys.argv:                     # the spawn hotfix: the armory class fix + the un-stalled MP poll
        files = ["coop_mod/mp_armory.scr", "coop_mod/mp.scr"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = 0
    # the temp file lives OUTSIDE maintt: the engine mounts any "*.pk3*" it finds there, so a failed rename once left a
    # 72-file "...pk3.tmp" loaded beside a stale 2-file pak and a test ran against both (2026-11-10)
    tmp = os.path.join(HOME, "liveops_pak.tmp")
    for fn in os.listdir(os.path.dirname(out)):
        if fn.startswith(PAK) and fn != PAK:
            os.remove(os.path.join(os.path.dirname(out), fn))
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(os.path.join(MOD, rel), rel)
            n += 1
        td = os.path.join(MOD, "textures", "menu")
        for fn in (sorted(os.listdir(td)) if ("--urconly" not in sys.argv and "--armoryonly" not in sys.argv and "--hotfix" not in sys.argv) else []):
            if fn.startswith(("hzm_ng3c_", "hzm_ops_")):
                z.write(os.path.join(td, fn), "textures/menu/" + fn)
                n += 1
    os.replace(tmp, out)
    print("pak", out, n, "files", os.path.getsize(out))
    return out


def lp():
    return os.path.join(HOME, "maintt", "qconsole.log")


def wait_for(pat, timeout, start=0, c=None):
    t = time.time()
    while time.time() - t < timeout:
        if re.search(pat, read(lp())[start:]):
            return True
        if c is not None and guard(c):
            return False
        time.sleep(1)
    return False


def guard(c):
    v = getattr(getattr(c, "watcher", None), "violations", None)
    if v:
        TRIPPED.append(repr(v))
    return bool(TRIPPED)


def client(binds, extra_sets=(), tail=(), w=1600, h=900, env=None):
    mt = os.path.join(HOME, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.lower().endswith(".pid") or fn == "qconsole.log":
            os.remove(os.path.join(mt, fn))
    base = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", "opengl2"),
            ("r_fullscreen", "0"), ("developer", "1"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"),
            ("in_mouse", "0"), ("in_nograb", "1"), ("s_volume", "0"), ("name", "OpsTester"), ("net_port", str(PORT))] + list(extra_sets)
    args = [os.path.join(A, "openmohaa.exe")]
    for k, v in base:
        args += ["+set", k, v]
    args += ["+exec", "lo_on.cfg"] + list(tail)
    d = hw.test_display()
    args, late = hw.apply_policy(args, width=w, height=h, display=d)
    open(os.path.join(mt, "lo_on.cfg"), "w", newline="\n").write("\n".join(MUTE + binds + late) + "\n")
    return hw.launch_background(args[0], args[1:], A, env=env, policy=False, display=d, below_normal=True, watch_audio=True, log=lambda *a: None)


def cmdfile(name, lines):
    open(os.path.join(HOME, "maintt", name), "w", newline="\n").write("\n".join(lines) + "\n")


A2 = r"G:\mohaa-liveops2"
HOME2 = os.path.join(A2, "home")


def client2(binds, w, h, env, connect):
    """a SECOND human (co-op squadmate): its own private install + home, the same test pak, connects to the host"""
    mt = os.path.join(HOME2, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.lower().endswith(".pid") or fn == "qconsole.log" or fn.startswith("zzzzzzzzzzzzzzzzzzzzzz_liveops"):
            os.remove(os.path.join(mt, fn))
    pk = os.path.join(HOME, "maintt", PAK)
    if os.path.exists(pk):
        shutil.copyfile(pk, os.path.join(mt, PAK))
    base = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME2), ("cl_renderer", "opengl2"),
            ("r_fullscreen", "0"), ("developer", "1"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"),
            ("in_mouse", "0"), ("in_nograb", "1"), ("s_volume", "0"), ("name", "OpsMate"), ("net_port", str(PORT + 1))]
    args = [os.path.join(A2, "openmohaa.exe")]
    for k, v in base:
        args += ["+set", k, v]
    args += ["+exec", "lo_on.cfg", "+connect", connect]
    d = hw.test_display()
    args, late = hw.apply_policy(args, width=w, height=h, display=d)
    open(os.path.join(mt, "lo_on.cfg"), "w", newline="\n").write("\n".join(MUTE + binds + late) + "\n")
    return hw.launch_background(args[0], args[1:], A2, env=env, policy=False, display=d, below_normal=True, watch_audio=True,
                                log=lambda *a: None)


def cmdfile2(name, lines):
    open(os.path.join(HOME2, "maintt", name), "w", newline="\n").write("\n".join(lines) + "\n")


def case_mpplain(out, res, gt):
    """a NORMAL MP host (no operation): the stock MP launch cfgs, join the Allies, armory DEPLOY by real click -> alive on
    the first press; TDM also respawns. gt 2 = Team Match on Remagen, 4 = Objective on Bologna."""
    w, h = (1600, 900) if "--wide" not in sys.argv else (1904, 816)
    res["window"] = "%dx%d" % (w, h)
    mp = "dm/mohdm3" if gt == 2 else "obj/mp_bologna_obj"
    cmdfile("lo_a.cfg", ["set ui_opsLive 0", "set ui_dmmap " + mp, "exec ui/coop_mpmenu/mode_none.cfg", "exec ui/coop_mpmenu/bots_8.cfg",
                         "exec ui/coop_mpmenu/launch_gt%d.cfg" % gt])
    cmdfile("lo_b.cfg", ["popmenu 0", "join_team allies"])
    cmdfile("lo_d.cfg", ["set coop_mpDeployDebug 1", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"])
    env = {"SDL_MOUSE_AUTO_CAPTURE": "0", "SDL_HINT_MOUSE_AUTO_CAPTURE": "0"}
    c = client(BINDS, extra_sets=[("cheats", "1"), ("thereisnomonkey", "1")], w=w, h=h, env=env)
    x, y = int(596 * w / 640.0), int(16 * h / 480.0)
    with c:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=c)
        time.sleep(20)
        for _k in range(6):
            press(c, "F5", 5)
            if "MP init" in read(lp()) or "CM_LoadMap" in read(lp()):
                break
        res["loaded"] = wait_for(r"\^~\^~\^ MP init", 240, 0, c)
        wait_for(r"CS_ACTIVE for OpsTester|OpsTester has entered", 120, 0, c)
        time.sleep(4)
        press(c, "F6", 2)
        res["joined"] = wait_for(r"OpsTester has joined the Allies", 30, 0, c)
        press(c, "F8", 1)
        time.sleep(1.5 if "--fast" in sys.argv else 5)
        cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (x, y)])
        press(c, "F7", 0.6)
        n0 = len(read(lp()))
        c.post_click(x, y)
        res["first_press_spawned"] = wait_for(r"MPKIT e0 ", 12, n0, c)
        res["deploy_seen"] = "MPDEPLOY e0" in read(lp())[n0:]
        res["inmatch"] = shot(c, out, "in_match")
        if gt == 2:
            time.sleep(8)                      # past spawn protection (it also stops the kill command)
            cmdfile("lo_c.cfg", ["kill"])
            press(c, "F7", 6)
            res["died"] = bool(re.search(r"OpsTester (took himself|blew himself)|You killed yourself", read(lp())))
            cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (x, y)])
            press(c, "F7", 0.6)
            n1 = len(read(lp()))
            c.post_click(x, y)
            res["respawned"] = wait_for(r"MPKIT e0 ", 25, n1, c)
        guard(c)
    res["mp_lines"] = re.findall(r"\^~\^~\^ (MPDEPLOY[^\n]*|MP init[^\n]*|OPS[^\n]*)", read(lp()))[-12:]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return read(lp())


DMAP, DGT = ("dm/mohdm3", "2") if "--gt2" in sys.argv else ("obj/mp_bologna_obj", "4")


def case_dedjoin(out, res):
    """join a DEDICATED objective server (bots) as a remote client and DEPLOY from the armory by real click"""
    w, h = 1600, 900
    srv_home = r"H:\hzm_work\liveops-test\srvhome2"     # not the sweep's home: the bot watch may be running
    mt = os.path.join(srv_home, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.startswith("zzzzzzzzzzzzzzzzzzzzzz_liveops") or fn == "qconsole.log":
            os.remove(os.path.join(mt, fn))
    pk = os.path.join(HOME, "maintt", PAK)
    if os.path.exists(pk) and "--nopak" not in sys.argv:
        shutil.copyfile(pk, os.path.join(mt, PAK))
    open(os.path.join(mt, "ded.cfg"), "w", newline="\n").write("\n".join([
        # TRAPS T14: the SERVER stuffs s_volume <coop_tinnitusBaseVol> to every player at spawn - on a dedicated server the
        # client's own mutes are overwritten, so they must be zeroed HERE (2026-11-10: a guard trip, peak 0.56, without them)
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
        "set developer 1", "set sv_maxbots 12", "set coop_mpBotFill 8", "set coop_mpMode none", "set coop_mpDeployDebug 1",
        "set ui_opsLive 0", "set sv_maplist " + DMAP, "map " + DMAP]) + "\n")
    sargs = [os.path.join(A, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", srv_home,
             "+set", "dedicated", "1", "+set", "net_port", "12295", "+set", "sv_maxclients", "4", "+set", "g_gametype", DGT,
             "+set", "logfile", "2", "+set", "sv_maxbots", "12", "+set", "developer", "1", "+exec", "ded.cfg"]
    srv = subprocess.Popen(sargs, cwd=A, **hw.popen_kwargs())
    res["server_pid"] = srv.pid
    SL = os.path.join(mt, "qconsole.log")
    try:
        t = time.time()
        while time.time() - t < 120 and "MP init" not in read(SL):
            time.sleep(2)
        res["server_up"] = "MP init" in read(SL)
        cmdfile("lo_b.cfg", ["popmenu 0", "join_team allies"])
        cmdfile("lo_d.cfg", ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"])
        env = {"SDL_MOUSE_AUTO_CAPTURE": "0", "SDL_HINT_MOUSE_AUTO_CAPTURE": "0"}
        c = client(BINDS, w=w, h=h, env=env, tail=["+connect", "127.0.0.1:12295"])
        x, y = int(596 * w / 640.0), int(16 * h / 480.0)
        with c:
            t = time.time()
            while time.time() - t < 240 and "OpsTester has entered" not in read(SL):
                if guard(c):
                    break
                time.sleep(3)
            time.sleep(5)
            press(c, "F6", 2)
            t = time.time()
            while time.time() - t < 30 and "OpsTester has joined the Allies" not in read(SL):
                time.sleep(2)
            res["joined"] = "OpsTester has joined the Allies" in read(SL)
            press(c, "F8", 1)
            # the server arms the armory hold when its MP poll reaches this player (measured, not assumed)
            t = time.time()
            while time.time() - t < 90 and not re.search(r"MPHOLD e\d+ side=a hold=1", read(SL)):
                time.sleep(1)
            res["hold_armed_after_s"] = round(time.time() - t, 1)
            time.sleep(1)
            cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (x, y)])
            press(c, "F7", 0.6)
            n0 = len(read(SL))
            c.post_click(x, y)
            t = time.time()
            while time.time() - t < 25 and not re.search(r"MPKIT e\d+ side=a [^\n]*cause=done", read(SL)[n0:]):
                time.sleep(1)
            res["first_press_spawned"] = bool(re.search(r"MPKIT e\d+ side=a [^\n]*cause=done", read(SL)[n0:]))
            res["deploy_seen"] = "MPDEPLOY" in read(SL)[n0:]
            res["inmatch"] = shot(c, out, "ded_in_match")
            guard(c)
    finally:
        if srv.poll() is None:
            srv.kill()
            srv.wait(20)
    shutil.copyfile(SL, os.path.join(out, "server_qconsole.log"))
    shutil.copyfile(lp(), os.path.join(out, "client_qconsole.log"))
    return read(SL)


def case_coop2(out, res):
    """host + a second human on one TDM contract: the squadmate must land on the ALLIES with no team choice, a forced
    'join_team axis' must be undone, and his armory DEPLOY (real click) must spawn him on the first press"""
    w, h = 960, 540
    utc, live, groups = pick_utc(lambda L: any(gen_ops.ENTRIES[c["entry"]]["mode"] == "TDM" and c["left"] > 300 for c in L))
    c0 = [c for c in live if gen_ops.ENTRIES[c["entry"]]["mode"] == "TDM" and c["left"] > 300][0]
    res["contract"] = gen_ops.describe(c0)
    cmdfile("lo_a.cfg", ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 1", "pushmenu hzm_newgame3d", "wait 1500",
                         "hzm_ops card %d" % slot_no(c0), "wait 1500", "hzm_ops deploy"])
    cmdfile("lo_d.cfg", ["set coop_mpDeployDebug 1", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"])
    env = {"SDL_MOUSE_AUTO_CAPTURE": "0", "SDL_HINT_MOUSE_AUTO_CAPTURE": "0"}
    host = client(BINDS, extra_sets=[("cheats", "1"), ("thereisnomonkey", "1")], w=w, h=h, env=env)
    with host:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=host)
        time.sleep(25)
        for _k in range(8):
            press(host, "F5", 5)
            if "OPS deploy" in read(lp()):
                break
        res["host_started"] = wait_for(r"\^~\^~\^ OPS start", 240, 0, host)
        wait_for(r"OpsTester has joined the Allies", 60, 0, host)
        press(host, "F8", 1)
        time.sleep(4)
        cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (int(596 * w / 640.0), int(16 * h / 480.0))])
        press(host, "F7", 0.6)
        host.post_click(int(596 * w / 640.0), int(16 * h / 480.0))
        res["host_spawned"] = wait_for(r"MPKIT e0 ", 20, 0, host)
        mate = client2(BINDS, w, h, env, "127.0.0.1:%d" % PORT)
        with mate:
            res["mate_joined_allies"] = wait_for(r"OpsMate has joined the Allies", 180, 0, host)
            res["mate_ever_axis_before_force"] = "OpsMate has joined the Axis" in read(lp())
            time.sleep(6)
            # his armory DEPLOY, by real click in HIS window
            cmdfile2("lo_c.cfg", ["hzm_ops testmouse %d %d" % (int(596 * w / 640.0), int(16 * h / 480.0))])
            press(mate, "F7", 0.6)
            n0 = len(read(lp()))
            mate.post_click(int(596 * w / 640.0), int(16 * h / 480.0))
            res["mate_spawned"] = wait_for(r"MPKIT e1 ", 20, n0, host)
            res["mate_shot"] = shot(mate, out, "mate_in_match") if False else None
            # try to defect: the operation must put him back on the Allies
            time.sleep(12)                    # the engine refuses a team change within 10 s of the last one
            cmdfile2("lo_c.cfg", ["join_team axis"])
            n1 = len(read(lp()))
            press(mate, "F7", 8)
            L = read(lp())[n1:]
            res["mate_forced_axis"] = bool(re.search(r"OpsMate[^\n]* has joined the Axis", L))
            res["mate_moved_back"] = bool(re.search(r"OPS allies e\d+ was on the axis - moved", L)) and bool(re.search(r"OpsMate[^\n]* has joined the Allies", L))
            guard(mate)
        guard(host)
    log = read(lp())
    res["teams"] = re.findall(r"(Ops\w+) has joined the (\w+)", log)
    shutil.copyfile(lp(), os.path.join(out, "host_qconsole.log"))
    try:
        shutil.copyfile(os.path.join(HOME2, "maintt", "qconsole.log"), os.path.join(out, "mate_qconsole.log"))
    except OSError:
        pass
    return log


def press(c, key, settle=2.0):
    c.post_key(VK[key])
    time.sleep(settle)


def shot(c, out, name):
    """the engine's own screenshot (jpg, exact frame) via F11, copied out; PrintWindow as a fallback"""
    sd = os.path.join(HOME, "maintt", "screenshots")
    before = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    press(c, "F11", 2.5)
    after = set(os.listdir(sd)) if os.path.isdir(sd) else set()
    new = sorted(after - before)
    if new:
        src = os.path.join(sd, new[-1])
        dst = os.path.join(out, name + os.path.splitext(src)[1])
        shutil.copyfile(src, dst)
        return dst
    try:
        dst = os.path.join(out, name + ".png")
        c.capture_png(dst)
        return dst
    except Exception as e:  # noqa: BLE001
        return "shot failed: %r" % e


BINDS = ['bind F5 "exec lo_a.cfg"', 'bind F6 "exec lo_b.cfg"', 'bind F7 "exec lo_c.cfg"', 'bind F8 "exec lo_d.cfg"',
         'bind F11 "screenshotJPEG"']


def pick_utc(pred, start=None, span=3 * 24 * 3600):
    """the first UTC second (on a :20 past the minute) whose roll satisfies pred(list)"""
    _p, groups, _pr = gen_ops.layout(gen_ops.load_sheet(r"H:\hzm_work\liveops-warmap"))
    t = (start or int(time.time())) // 60 * 60 + 20
    for k in range(span // 60):
        live = gen_ops.roll(t + k * 60, groups)
        if pred(live):
            return t + k * 60, live, groups
    raise SystemExit("no utc found")


def slot_no(c):
    return c["slot"] + 1


def case_board(out, res):
    utc, live, groups = pick_utc(lambda L: len(L) >= 5 and any(gen_ops.ENTRIES[c["entry"]]["mode"] == "OBJ" for c in L)
                                 and any(gen_ops.SLOTS[c["slot"]]["area"] for c in L))
    res["utc"] = utc
    res["ref"] = ["OPS " + gen_ops.describe(c) for c in live]
    hov = live[0]
    card = live[-1]
    res["hover"], res["card"] = gen_ops.SLOTS[hov["slot"]]["key"], gen_ops.SLOTS[card["slot"]]["key"]
    cmdfile("lo_a.cfg", ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 1", "pushmenu hzm_newgame3d"])
    cmdfile("lo_b.cfg", ["hzm_ops dump %d" % utc])
    c = client(BINDS)
    with c:
        if not wait_for(r"OPS dump|Started|------- Cvar|CL_InitCGame|Sound initialization|UI_Init|\^~\^~\^", 120, c=c):
            res["boot"] = False
        time.sleep(25)
        press(c, "F6", 2)
        press(c, "F5", 6)
        res["wall"] = shot(c, out, "wall")
        # the hover slip: the scene sets ui_scene_hot to a hotspot's list position; find this slot's from the urc
        hots = [l.split('"')[1] for l in read(os.path.join(MOD, "ui", "hzm_newgame3d.urc")).splitlines() if l.startswith("scenehot ")]
        hi = hots.index("ops%d" % slot_no(hov)) + 1
        cmdfile("lo_c.cfg", ["set ui_scene_hot %d" % hi])
        press(c, "F7", 2)
        res["slip"] = shot(c, out, "hover_slip")
        cmdfile("lo_d.cfg", ["set ui_scene_hot 0", "hzm_ops card %d" % slot_no(card)] + (["set ui_opsCharset 1"] if "--charset" in sys.argv else []))
        press(c, "F8", 3)
        res["card_shot"] = shot(c, out, "card")
        cmdfile("lo_a.cfg", ["set bot_manualmove 0", "set g_inactiveSpectate 60"])
        press(c, "F5", 1)
        guard(c)
        res["peak"] = repr(c.report())[:300]
    log = read(lp())
    eng = re.findall(r"^.*?(OPS t=[^\n]*)$", log, re.M)
    res["engine"] = [e.strip() for e in eng]
    res["parity"] = [l.split("OPS ", 1)[1] for l in res["ref"]] == [e.split("OPS ", 1)[1] for e in res["engine"]]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return log


def case_match(out, res, mode):
    want = opt("--map", "")

    def ok(L):
        for c in L:
            e = gen_ops.ENTRIES[c["entry"]]
            if e["mode"] == mode and (not want or e["map"] == want) and c["left"] > 150:
                return True
        return False
    utc, live, groups = pick_utc(ok)
    c0 = [c for c in live if gen_ops.ENTRIES[c["entry"]]["mode"] == mode and (not want or gen_ops.ENTRIES[c["entry"]]["map"] == want) and c["left"] > 150][0]
    res["utc"], res["contract"] = utc, gen_ops.describe(c0)
    cmdfile("lo_a.cfg", ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 1", "pushmenu hzm_newgame3d", "wait 1500",
                         "hzm_ops card %d" % slot_no(c0)])
    cmdfile("lo_b.cfg", ["hzm_ops deploy"])
    # in the match: a short limit so it ends inside the test (TDM: the time limit; OBJ: the round time)
    spawn = ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "popmenu 0", "wait 10",
             "primarydmweapon rifle", "wait 20", "popmenu 0", "wait 20", "popmenu 0", "+attackprimary", "wait 10", "-attackprimary"]
    cmdfile("lo_c.cfg", (["set timelimit 2", "set fraglimit 0"] if mode == "TDM" else ["set roundlimit 2"]) + spawn)
    cmdfile("lo_d.cfg", ["echo LOSCORE", "ui_opsResult", "ui_opsLive"])
    c = client(BINDS, extra_sets=[("cheats", "1"), ("thereisnomonkey", "1")])
    with c:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=c)
        time.sleep(25)
        press(c, "F5", 6)
        res["card_shot"] = shot(c, out, "card")
        n0 = len(read(lp()))
        press(c, "F6", 1)
        res["deployed"] = wait_for(r"OPS deploy", 20, n0, c)
        res["started"] = wait_for(r"\^~\^~\^ OPS start", 240, n0, c)
        res["joined"] = wait_for(r"OpsTester has joined the (Allies|Axis)", 60, n0, c)
        time.sleep(6)
        if not guard(c):
            press(c, "F7", 8)
            press(c, "F7", 6)
            res["inmatch"] = shot(c, out, "in_match")
            time.sleep(25)
            res["inmatch2"] = shot(c, out, "in_match2")
        res["ended"] = wait_for(r"\^~\^~\^ OPS end mode", 420, n0, c)
        res["paid"] = wait_for(r"\^~\^~\^ OPS paid", 60, n0, c)
        res["returned"] = wait_for(r"\^~\^~\^ OPS return", 90, n0, c)
        time.sleep(6)
        if res["returned"] and not guard(c):
            res["return_shot"] = shot(c, out, "returned_card")
        cmdfile("lo_a.cfg", ["set bot_manualmove 0", "set g_inactiveSpectate 60"])
        press(c, "F5", 1)
        guard(c)
        res["peak"] = repr(c.report())[:300]
    log = read(lp())
    res["ops_lines"] = re.findall(r"\^~\^~\^ (OPS[^\n]*|MPBOT fill[^\n]*|XP[^\n]*)", log)[-30:]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return log


def case_flat(out, res):
    utc, live, groups = pick_utc(lambda L: len(L) >= 4)
    res["utc"] = utc
    cmdfile("lo_a.cfg", ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 0", "pushmenu hzm_ngflat"])
    cmdfile("lo_b.cfg", ["hzm_ops cardd 2"])
    c = client(BINDS)
    with c:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=c)
        time.sleep(25)
        press(c, "F5", 5)
        res["flat"] = shot(c, out, "flat")
        press(c, "F6", 3)
        res["flat_card"] = shot(c, out, "flat_card")
        cmdfile("lo_c.cfg", ["seta ui_atticMain 1"])
        press(c, "F7", 1)
        guard(c)
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return read(lp())


def hotpos(name, start):
    """screen position of a scene hotspot, from the engine's own projection (ui_scene_hotdump)"""
    m = re.findall(r"SCENEHOT " + re.escape(name) + r" sx=(-?\d+) sy=(-?\d+) r=(\d+) depth=(-?\d+) W=(\d+) H=(\d+)", read(lp())[start:])
    return (int(m[-1][0]), int(m[-1][1]), int(m[-1][4]), int(m[-1][5])) if m else None


def case_click(out, res):
    """the REAL click path: the cursor is put on the button (private test exe: hzm_ops testmouse), then a left click is
    POSTED to our own window (WM_LBUTTONDOWN/UP -> SDL -> K_MOUSE1 -> UI hit-test -> the button's stuffcommand).
    FILE AWAY must close the card; a click on the contract's stamp must reopen it; DEPLOY must launch the match."""
    w, h = (1600, 900) if "--wide" not in sys.argv else (1904, 816)
    res["window"] = "%dx%d" % (w, h)
    utc, live, groups = pick_utc(lambda L: any(gen_ops.ENTRIES[c["entry"]]["mode"] == "TDM" and c["left"] > 200 for c in L))
    c0 = [c for c in live if gen_ops.ENTRIES[c["entry"]]["mode"] == "TDM" and c["left"] > 200][0]
    n = slot_no(c0)
    side = "1" if gen_ops.SLOTS[c0["slot"]]["pin"][1] < 20 else "2"
    res["contract"] = gen_ops.describe(c0)
    cmdfile("lo_a.cfg", ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 1", "pushmenu hzm_newgame3d"])
    cmdfile("lo_b.cfg", ["set ui_scene_hotdump 1", "wait 400", "set ui_scene_hotdump 0"])
    cmdfile("lo_d.cfg", ["echo LOCARD", "ui_opsCard"])
    env = {"SDL_MOUSE_AUTO_CAPTURE": "0", "SDL_HINT_MOUSE_AUTO_CAPTURE": "0"}
    c = client(BINDS, w=w, h=h, env=env)
    steps = []

    def click(hot):
        n0 = len(read(lp()))
        press(c, "F6", 2)
        p = hotpos(hot, n0)
        if not p:
            steps.append((hot, "no position"))
            return False
        x, y = p[0] * w // p[2], p[1] * h // p[3]
        cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (p[0], p[1])])
        press(c, "F7", 1)
        c.post_click(x, y)
        time.sleep(2)
        steps.append((hot, p, (x, y)))
        return True

    def card_state():
        n0 = len(read(lp()))
        press(c, "F8", 2)
        m = re.findall(r'"ui_opsCard" is:"(\d)', read(lp())[n0:])
        return m[-1] if m else "?"
    with c:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=c)
        time.sleep(25)
        press(c, "F5", 6)
        res["card_before_click"] = card_state()
        click("ops%d" % n)                                  # the contract's stamp: opens the card
        res["after_stamp_click"] = card_state()
        res["card_open_shot"] = shot(c, out, "card_open")
        click("opsfa%s" % side)                             # FILE AWAY
        res["after_fileaway_click"] = card_state()
        res["fileaway_shot"] = shot(c, out, "after_fileaway")
        click("ops%d" % n)
        res["reopened"] = card_state()
        n1 = len(read(lp()))
        click("opsdp%s" % side)                             # DEPLOY
        res["deployed"] = wait_for(r"\^~\^~\^ OPS deploy", 15, n1, c)
        res["match_started"] = wait_for(r"\^~\^~\^ OPS start", 240, n1, c)
        cmdfile("lo_a.cfg", ["set bot_manualmove 0", "set g_inactiveSpectate 60"])
        press(c, "F5", 1)
        guard(c)
        res["peak"] = repr(c.report())[:300]
    res["steps"] = [repr(s_) for s_ in steps]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return read(lp())


def case_spawn(out, res, mode):
    """the user's path, all by REAL click: war map -> contract card (cfg) -> DEPLOY on the card (click) -> the match -> the
    side armory opens -> DEPLOY in the armory (click, button rect 560 8 72 16 of 640x480, stretched) -> must be ALIVE after
    the FIRST press. TDM also dies (kill) and must respawn through the armory again."""
    w, h = (1600, 900) if "--wide" not in sys.argv else (1904, 816)
    res["window"] = "%dx%d" % (w, h)
    want = opt("--map", "")

    def ok(L):
        return [c for c in L if gen_ops.ENTRIES[c["entry"]]["mode"] == mode and c["left"] > 200
                and (not want or gen_ops.ENTRIES[c["entry"]]["map"] == want)]
    utc, live, groups = pick_utc(lambda L: bool(ok(L)))
    c0 = ok(live)[0]
    side = "1" if gen_ops.SLOTS[c0["slot"]]["pin"][1] < 20 else "2"
    res["contract"] = gen_ops.describe(c0)
    cmdfile("lo_a.cfg", ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 1", "pushmenu hzm_newgame3d", "wait 1500",
                         "hzm_ops card %d" % slot_no(c0)])
    cmdfile("lo_b.cfg", ["set ui_scene_hotdump 1", "wait 400", "set ui_scene_hotdump 0"])
    cmdfile("lo_d.cfg", ["set coop_mpDeployDebug 1", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"])
    env = {"SDL_MOUSE_AUTO_CAPTURE": "0", "SDL_HINT_MOUSE_AUTO_CAPTURE": "0"}
    c = client(BINDS, extra_sets=[("cheats", "1"), ("thereisnomonkey", "1")], w=w, h=h, env=env)

    def click_xy(vx, vy):                     # a point in the menu's 640x480 virtual space (stretched to the window)
        x, y = int(vx * w / 640.0), int(vy * h / 480.0)
        cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (x, y)])
        press(c, "F7", 0.6)
        c.post_click(x, y)

    def alive_after(n0, secs):
        t = time.time()
        while time.time() - t < secs:
            L = read(lp())[n0:]
            if re.search(r"MPDEPLOY e0 cause=done class=\S+", L) and not re.search(r"MPDEPLOYTRY e0 try=\d+ spec=1", L[-400:]):
                if re.search(r"\^~\^~\^ MP(SPAWN|ONSPAWN)|giveKit|MPKIT", L) or "spec=0" in L:
                    return True
            time.sleep(1)
        return False
    with c:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=c)
        time.sleep(25)
        for _k in range(8):                   # the attic can still be loading: press until the card is up
            press(c, "F5", 4)
            if "OPS card" in read(lp()):
                break
        m = None
        for _k in range(6):
            n0 = len(read(lp()))
            press(c, "F6", 2)
            m = re.findall(r"SCENEHOT opsdp" + side + r" sx=(-?\d+) sy=(-?\d+)", read(lp())[n0:])
            if m:
                break
        if not m:
            res["error"] = "no DEPLOY position"
            return read(lp())
        x, y = int(m[-1][0]), int(m[-1][1])
        cmdfile("lo_c.cfg", ["hzm_ops testmouse %d %d" % (x, y)])
        press(c, "F7", 0.6)
        n1 = len(read(lp()))
        c.post_click(x, y)
        res["deployed"] = wait_for(r"\^~\^~\^ OPS deploy", 15, n1, c)
        res["started"] = wait_for(r"\^~\^~\^ OPS start", 240, n1, c)
        res["joined"] = wait_for(r"OpsTester has joined the (Allies|Axis)", 60, n1, c)
        press(c, "F8", 1)
        time.sleep(1.5 if "--fast" in sys.argv else 6)   # --fast: press as soon as the armory is up (the user's race)
        res["armory_shot"] = shot(c, out, "armory")
        presses = []
        for k in range(5):                    # press DEPLOY until alive; the bar is ONE press
            n2 = len(read(lp()))
            click_xy(596, 16)
            time.sleep(5)
            L = read(lp())[n2:]
            if k == 0:
                res["first_press_spawned"] = "MPKIT e0 " in L
            presses.append({"k6seen": "MPDEPLOY k6seen" in L, "deploy": bool(re.search(r"MPDEPLOY e0 cause", L)),
                            "gaveup": "GAVEUP" in L, "tries": len(re.findall(r"MPDEPLOYTRY e0", L))})
            cmdfile("lo_c.cfg", ["echo LOSTATE", "ui_opsResult"])
            if re.search(r"MPDEPLOY e0 cause=\S+ class=", L) and not re.search(r"try=1[0-9] spec=1", L):
                break
        res["presses"] = presses
        n4 = len(read(lp()))
        time.sleep(3 if mode == "TDM" else 25)  # OBJ: the bots join and the round restarts - he must be alive in it
        L = read(lp())[n4:]
        res["after_release"] = {"restart": "OPS start" in L, "kit_again": len(re.findall(r"MPKIT e0 ", L)),
                                "allies_moves": len(re.findall(r"OPS allies e", L))}
        res["inmatch"] = shot(c, out, "in_match")
        if mode == "TDM":                     # respawn: die, then DEPLOY in the armory again
            cmdfile("lo_c.cfg", ["kill"])
            press(c, "F7", 8)
            n3 = len(read(lp()))
            click_xy(596, 16)
            time.sleep(6)
            L = read(lp())[n3:]
            res["respawn"] = {"deploy": bool(re.search(r"MPDEPLOY e0 cause", L)), "gaveup": "GAVEUP" in L}
            res["respawn_shot"] = shot(c, out, "respawned")
        guard(c)
        res["peak"] = repr(c.report())[:200]
    log = read(lp())
    res["mp_lines"] = re.findall(r"\^~\^~\^ (MPDEPLOY[^\n]*|MPHOLD[^\n]*|OPS[^\n]*)", log)[-40:]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return log


# [LIBERATION] a distinctive co-op kit (the user's check): Thompson with the GOLD finish, Colt, frags, the leather gloves and
# an engraving - archived exactly as the co-op Armory writes them (coop_lo<slot> = roster id, coop_loS<slot>F = finish id)
KIT = ['seta coop_lo1 24', 'seta coop_loS1F 1', 'seta coop_lo2 ""', 'seta coop_lo3 48', 'seta coop_lo4 64',
       'seta coop_loAGlove "append name ,gn2"', 'seta cl_engraveText LIBERTY', 'seta cl_engrave 1']
MP_LOADOUT = ["coop_mpa_K1", "coop_mpa_K2", "coop_mpa_K3", "coop_mpaFin1", "coop_mp_glove"]


def case_lib(out, res):
    want = opt("--map", "")
    end = opt("--end", "win")

    def pick(L):
        return [c for c in L if gen_ops.ENTRIES[c["entry"]]["mode"] == "LIB" and c["left"] > 150
                and (not want or gen_ops.ENTRIES[c["entry"]]["map"] == want)]
    utc, live, groups = pick_utc(lambda L: bool(pick(L)))
    c0 = pick(live)[0]
    e0 = gen_ops.ENTRIES[c0["entry"]]
    res["utc"], res["contract"] = utc, gen_ops.describe(c0)
    res["limit_min"] = gen_ops.lib_limit(e0, c0["bots"])
    res["xp_win"] = gen_ops.SKILLS[c0["skill"]][2] * gen_ops.LIB_XP_MULT
    cmdfile("lo_a.cfg", KIT + ["echo LOMPKIT"] + MP_LOADOUT + ["set ui_opsFakeUtc %d" % utc, "seta ui_atticMain 1", "pushmenu hzm_newgame3d", "wait 1500",
                               "hzm_ops card %d" % slot_no(c0)])
    cmdfile("lo_b.cfg", ["hzm_ops deploy"])
    mute = ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"]
    cmdfile("lo_c.cfg", mute)
    # the end: every German dies (script *<entnum> kill, cheats on), or the player does, or the clock runs out
    if end == "win":
        # "script *N kill" needs cheats, which a contract's own map start never has ("command not available"), so the
        # Germans are taken off the server instead: the hunt then counts 0 living Germans, the same test a last kill passes
        cmdfile("lo_d.cfg", ["set sv_numbots 0"])
    elif end == "lose":
        cmdfile("lo_d.cfg", ["kill"])
    elif end == "idle":
        # the stationary hunter: Germans frozen, the inactivity cvars LEFT ALONE (the contract itself must switch them off)
        cmdfile("lo_d.cfg", ["set bot_manualmove 1"])
    else:
        # the clock case needs the idle test client alive and on his side for the whole limit: the Germans are frozen
        # (bot_manualmove, a stock bot debug cvar) and the engine's inactivity move to the spectators is off
        cmdfile("lo_d.cfg", ["set bot_manualmove 1", "set g_inactiveSpectate 0"])
    c = client(BINDS, extra_sets=[("cheats", "1"), ("thereisnomonkey", "1")])
    with c:
        wait_for(r"UI_Init|CL_InitCGame|Sound|\^~\^~\^", 120, c=c)
        time.sleep(25)
        nb = len(read(lp()))
        press(c, "F5", 6)
        res["before_cvars"] = re.findall(r'"(coop_[A-Za-z0-9_]+)" is:"([^"]*)"', read(lp())[nb:])
        res["card_shot"] = shot(c, out, "card")
        n0 = len(read(lp()))
        press(c, "F6", 1)
        res["deployed"] = wait_for(r"OPS deploy", 20, n0, c)
        res["started"] = wait_for(r"\^~\^~\^ OPS start", 240, n0, c)
        press(c, "F7", 1)
        res["placed"] = wait_for(r"\^~\^~\^ LIB placed", 90, n0, c)
        time.sleep(2.5)
        if not guard(c):
            res["spawn_shot"] = shot(c, out, "spawn")
            time.sleep(2)
            res["spawn_shot2"] = shot(c, out, "spawn_radio")
            if end in ("time", "idle"):
                press(c, "F8", 1)
            if end == "idle":
                time.sleep(100)
                res["idle_ended_early"] = bool(re.search(r"OPS end mode=lib", read(lp())[n0:]))
                res["idle_shot"] = shot(c, out, "idle100")
                cmdfile("lo_d.cfg", ["set bot_manualmove 0", "set sv_numbots 0"])
                press(c, "F8", 2)
            # win: inside the opening grace (the player cannot be hurt for 6 s), so no German gets to him first
            time.sleep({"win": 0.5, "time": 5, "idle": 0.5}.get(end, 40))
            res["hunt_shot"] = shot(c, out, "hunt")
        if end in ("win", "lose") and not guard(c):
            press(c, "F8", 2)
        if end == "time":
            # stills of the two warnings (2 min and 30 s left)
            for tag, left in (("warn_2min", 118), ("warn_30s", 28)):
                if wait_for(r"\^~\^~\^ LIB warn left=%d" % (120 if left > 60 else 30), 60 * (res["limit_min"] + 1), n0, c):
                    time.sleep(1.0)
                    if not guard(c):
                        res[tag] = shot(c, out, tag)
        res["ended"] = wait_for(r"\^~\^~\^ OPS end mode=lib", 60 * (res["limit_min"] + 2), n0, c)
        time.sleep(1.5)
        if not guard(c):
            res["result_shot"] = shot(c, out, "result")
        res["paid"] = wait_for(r"\^~\^~\^ OPS paid", 30, n0, c)
        res["returned"] = wait_for(r"\^~\^~\^ OPS return", 60, n0, c)
        time.sleep(6)
        if res["returned"] and not guard(c):
            res["return_shot"] = shot(c, out, "returned_card")
            n1 = len(read(lp()))
            cmdfile("lo_a.cfg", ["echo LOMPKIT"] + MP_LOADOUT + ["coop_lo1", "coop_loS1F", "coop_lo3", "coop_lo4"])
            press(c, "F5", 3)
            res["after_cvars"] = re.findall(r'"(coop_[A-Za-z0-9_]+)" is:"([^"]*)"', read(lp())[n1:])
        cmdfile("lo_a.cfg", ["set bot_manualmove 0", "set g_inactiveSpectate 60"])
        press(c, "F5", 1)
        guard(c)
        res["peak"] = repr(c.report())[:300]
    log = read(lp())
    res["lines"] = re.findall(r"\^~\^~\^ ((?:OPS|LIB|MPBOT fill|XP)[^\n]*)", log)[-80:]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return log


def script_errors(log):
    return log.count("Script Error"), log.count("Couldn't compile")


def main(cases):
    if "pak" in cases:
        build_pak()
        cases = [c for c in cases if c != "pak"]
    os.makedirs(RUNS, exist_ok=True)
    vals = [i + 1 for i, a in enumerate(cases) if a in ("--map", "--lane", "--end")]   # an option's value is not a case
    cases = [a for i, a in enumerate(cases) if i not in vals and not a.startswith("--")]
    for case in cases:
        if TRIPPED:
            print("GUARD TRIPPED - stopping all launches:", TRIPPED, flush=True)
            break
        # the user may play on the ultrawide while we test (ALLOW_WHILE_PLAYING): then ONLY the 1080p second screen
        if SLOT == "liberacion":
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "liberacion_2026-11-10", "tools"))
            import lib_sweep
            why = lib_sweep.hold_reason()
            if why:
                print("HOLD - not launching:", why, flush=True)
                break
        if hg.user_game_running():
            print("a USER-class MOHAA client is running and testing beside it is not allowed - not launching", flush=True)
            break
        if hg.user_game_running_raw() and hw.test_display()["rect"][2] - hw.test_display()["rect"][0] != 1920:
            print("the user is playing: test on the 1080p screen only (HZM_TEST_RES=1920x1080) - not launching", flush=True)
            break
        out = os.path.join(RUNS, case + ("_" + opt("--map", "").replace("/", "_") if "--map" in sys.argv else ""))
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        res = {"case": case, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        hg.acquire_slot(SLOT, os.path.join(A, "openmohaa.exe"), HOME, [PORT], minutes=30)
        try:
            if case == "board":
                log = case_board(out, res)
            elif case == "tdm":
                log = case_match(out, res, "TDM")
            elif case == "obj":
                log = case_match(out, res, "OBJ")
            elif case in ("mp_tdm", "mp_obj"):
                log = case_mpplain(out, res, 2 if case == "mp_tdm" else 4)
            elif case == "dedjoin":
                log = case_dedjoin(out, res)
            elif case == "coop2":
                log = case_coop2(out, res)
            elif case in ("spawn_tdm", "spawn_obj"):
                log = case_spawn(out, res, case[-3:].upper())
            elif case == "click":
                log = case_click(out, res)
            elif case == "flat":
                log = case_flat(out, res)
            elif case == "lib":
                log = case_lib(out, res)
            else:
                raise SystemExit("unknown case " + case)
        finally:
            hg.release_slot(SLOT)
        res["script_errors"], res["compile_fail"] = script_errors(log)
        res["guard"] = TRIPPED[:]
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
        print(case, json.dumps(res, indent=1), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])

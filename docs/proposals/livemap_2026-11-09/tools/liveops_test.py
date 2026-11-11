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

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools")   # this worktree's docs/tools
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
VK = {"F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}
TRIPPED = []
MUTE = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set con_notifytime -1", "set coop_joinCard 0",
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "set coop_whatsNewSeen 99999",
        "set developer 1", "set logfile 2"]
PAK_FILES = ["ui/hzm_newgame3d.urc", "ui/hzm_ngflat.urc", "scripts/hzm_ng3campaigns.shader", "coop_mod/mp.scr",
             "coop_mod/mp_bots.scr", "coop_mod/mp_hardcore.scr", "coop_mod/mp_weather.scr", "coop_mod/mp_ops.scr",
             "coop_mod/mp_ops_table.scr", "coop_mod/mp_dbno.scr", "coop_mod/mp_ops_text.scr", "coop_mod/libbridge.scr",
             "ubersound/coop_audio.scr", "sound/coop_vo/den_coop_lib_briefing.wav"]


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
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = 0
    with zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(os.path.join(MOD, rel), rel)
            n += 1
        td = os.path.join(MOD, "textures", "menu")
        for fn in (sorted(os.listdir(td)) if "--urconly" not in sys.argv else []):
            if fn.startswith(("hzm_ng3c_", "hzm_ops_")):
                z.write(os.path.join(td, fn), "textures/menu/" + fn)
                n += 1
    os.replace(out + ".tmp", out)
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
    cmdfile("lo_b.cfg", ["set ui_scene_hotdump 1", "wait 60", "set ui_scene_hotdump 0"])
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
        guard(c)
        res["peak"] = repr(c.report())[:300]
    res["steps"] = [repr(s_) for s_ in steps]
    shutil.copyfile(lp(), os.path.join(out, "qconsole.log"))
    return read(lp())


# [LIBERATION] a distinctive co-op kit (the user's check): Thompson with the GOLD finish, Colt, frags, the leather gloves and
# an engraving - archived exactly as the co-op Armory writes them (coop_lo<slot> = roster id, coop_loS<slot>F = finish id)
KIT = ['seta coop_lo1 23', 'seta coop_loS1F 1', 'seta coop_lo2 ""', 'seta coop_lo3 46', 'seta coop_lo4 62',
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
    cmdfile("lo_c.cfg", ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"])
    # the end: every German dies (script *<entnum> kill, cheats on), or the player does, or the clock runs out
    if end == "win":
        cmdfile("lo_d.cfg", ["script *%d kill" % i for i in range(1, 27)])
    elif end == "lose":
        cmdfile("lo_d.cfg", ["kill"])
    else:
        cmdfile("lo_d.cfg", ["echo LONOP"])
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
            time.sleep(40 if end != "time" else 5)
            res["hunt_shot"] = shot(c, out, "hunt")
        if end in ("win", "lose") and not guard(c):
            press(c, "F8", 2)
        res["ended"] = wait_for(r"\^~\^~\^ OPS end mode=lib", 60 * (res["limit_min"] + 2), n0, c)
        time.sleep(1.0)
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
    for case in cases:
        if case.startswith("--") or case in (opt("--map", "\0"), opt("--lane", "\0"), opt("--end", "\0")):
            continue
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

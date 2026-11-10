#!/usr/bin/env python3
"""v1.10.69 own-disc missions in the menus and campaigns - test matrix on a PRIVATE client (H:/hzm_work/byo68-test/client, our
exe build). Muted, in_gamepad 0, in_joystick 0, in_mouse 0, in_nograb 1, on the ultrawide, never focused; the harness guard
(harness_window: foreground / cursor clip / capture / audio) kills the client on any violation - and this script then STOPS.
Input = console commands bound to F5..F12 in the boot cfg, posted to OUR window only (in_mouse 0: no clicks; a button is
exercised by running its own stuffcommand).  The test-only script maps/byotest.scr ends a level the way the level does.

  python byo69_test.py <case> [...]     cases: menu_absent menu_present sp_absent sp_present coop_absent coop_present
                                                 chrono_present continue_absent
Results: H:/hzm_work/byo68-test/runs69/<case>/ (qconsole.log, *.png, result.json)."""
import json
import os
import re
import shutil
import sys
import time

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
sys.path.insert(0, TOOLS)
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"H:\hzm_work\byo68-test\client"
EXE = os.path.join(CLIENT, "openmohaa.exe")
RUNS = r"H:\hzm_work\byo68-test\runs69"
OWNER = "byo68"
PORT = 12297
W, H = (int(v) for v in os.environ.get("BYO_RES", "1600x900").split("x"))   # 21:9 QA: BYO_RES=2400x1028
FK = {"F%d" % n: 0x6F + n for n in range(5, 13)}
TRIPPED = []


def home(present):
    return os.path.join(CLIENT, "home_present" if present else "home_absent")


def logp(present):
    return os.path.join(home(present), "maintt", "qconsole.log")


def read(present):
    try:
        return open(logp(present), encoding="latin-1").read()
    except OSError:
        return ""


def wait_for(present, pat, timeout, start=0):
    t = time.time()
    while time.time() - t < timeout:
        if re.search(pat, read(present)[start:]):
            return True
        time.sleep(0.5)
    return False


def launch(present, tail, steps):
    """steps: [(key, tag, commands)] -> byo_<tag>.cfg bound to the key"""
    mt = os.path.join(home(present), "maintt")
    for fn in os.listdir(mt):
        if fn.lower().endswith(".pid") or fn in ("qconsole.log", "byo_status.txt"):
            os.remove(os.path.join(mt, fn))
    on = ["set rconPassword byo69t", "set sv_maxbots 0", "set com_maxfps 60", "set coop_dev 1", "set coop_joinCard 0", "set thereisnomonkey 1", "set cheats 1",
          "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0", "set in_mouse 0",
          "set in_nograb 1", "set con_notifytime -1"]
    for key, tag, cmds in steps:
        open(os.path.join(mt, "byo_%s.cfg" % tag), "w", newline="\n").write("echo BYOT_%s\n%s\n" % (tag, "\n".join(cmds)))
        on.append('bind %s "exec byo_%s.cfg"' % (key, tag))
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", home(present)), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"), ("developer", "1"),
            ("logfile", "2"), ("net_port", str(PORT)), ("net_ip", "127.0.0.1"), ("s_volume", "0"), ("in_gamepad", "0"),
            ("in_joystick", "0"), ("in_mouse", "0"), ("in_nograb", "1"),
            ("cheats", "1")]     # testthread is a cheat, and cheats is latched: it has to be on the command line
    args = [EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "byo_on.cfg"] + list(tail)
    d = hw.test_display()
    args, late = hw.apply_policy(args, width=W, height=H, display=d)
    on += late
    open(os.path.join(mt, "byo_on.cfg"), "w", newline="\n").write("\n".join(on) + "\n")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, display=hw.test_display(), below_normal=True)
    hg.set_slot_pid(OWNER, c.proc.pid)
    return c


def press(c, present, key, tag, settle=3.0, tries=3):
    n = len(read(present))
    for _ in range(tries):
        c.post_key(FK[key])
        if wait_for(present, "BYOT_" + tag, 6, n):
            time.sleep(settle)
            return True
    return False


def shot(c, out, name):
    try:
        c.capture_png(os.path.join(out, name + ".png"))
    except Exception as e:
        print("capture failed", name, e)


def cv(present, name):
    return (re.findall(r'"%s" is:"([^"]*)' % re.escape(name), read(present)) or [None])[-1]


def guard_check(c):
    v = getattr(getattr(c, "watcher", None), "violations", None)
    if v:
        TRIPPED.append(repr(v))


def case_menu(present, out, res):
    st = [("F5", "start", ["pushmenu coop_start"]),
          ("F6", "fl", ["set ui_coopCamp 14", "exec ui/coop_start/fl.cfg"] +
           (["set ui_dmmap coop_fl_1_1", "seta coop_mapcmd map coop_fl_1_1"] if present else [])),
          ("F7", "ea", ["set ui_coopCamp 15", "exec ui/coop_start/ea.cfg"] +
           (["set ui_dmmap coop_ea_1_11", "seta coop_mapcmd map coop_ea_1_11"] if present else [])),
          # the tile's own command: with the pak the generic tile 1, without it the lock Button on top of it
          ("F8", "tile", (["set ui_coopCamp 14", "exec ui/coop_start/fl.cfg", "set ui_dmmap coop_fl_1_1;seta coop_mapcmd map coop_fl_1_1"]
                          if present else ["set ui_coopCamp 14", "exec ui/coop_start/fl.cfg", "set ui_byoLock 14"])),
          ("F9", "lockopen", ["set ui_byoLock 0", "pushmenu coop_byodisc"]),
          ("F10", "cvars", ["ui_dmmap", "coop_flHave_1_1", "coop_eaHave_1_11", "byo"]),
          ("F11", "newgame", ["pushmenu hzm_newgame3d"])]
    c = launch(present, [], st)
    with c:
        res["boot"] = wait_for(present, r"----- Client Initialization Complete|Sound initialization", 120)
        time.sleep(15)
        for key, tag, _ in st:
            res.setdefault("steps", {})[tag] = press(c, present, key, tag, settle=4)
            if tag in ("fl", "ea", "tile", "lockopen", "newgame"):
                shot(c, out, "%s_%s" % (tag, "present" if present else "absent"))
            guard_check(c)
            if TRIPPED:
                return
        res["cvars"] = {k: cv(present, k) for k in ("ui_dmmap", "coop_flHave_1_1", "coop_eaHave_1_11", "byo")}


def case_sp(present, out, res):
    """SP chronological: m4l3 ends -> (present) Frontline's briefing / (absent) AA 5's briefing; then coop_fl_1_1 ends -> AA 5"""
    st = [("F5", "endm4l3", ["testthread maps/byotest.scr end_m4l3"])]
    c = launch(present, ["+set", "g_gametype", "0", "+set", "coop_spChrono", "1", "+map", "m4l3"], st)
    with c:
        res["m4l3_loaded"] = wait_for(present, r"Spawning Entities Done", 240)
        time.sleep(15)
        n = len(read(present))
        res["m4l3_end"] = press(c, present, "F5", "endm4l3", settle=1)
        want = "briefing/briefingfl1" if present else "briefing/briefing5"
        res["sp_next_m4l3"] = (re.findall(r"BYOTEST sp next (\S*)", read(present)[n:]) or [None])[-1]
        res["sp_next_ok"] = res["sp_next_m4l3"] == want
        res["next_loaded"] = wait_for(present, r"Spawning Entities Done", 240, n + 10)
        time.sleep(8)
        shot(c, out, "sp_after_m4l3_" + ("present" if present else "absent"))
        guard_check(c)
    if not present or TRIPPED:
        return
    st = [("F5", "endbyo", ["testthread maps/byotest.scr end_byo"])]
    c = launch(present, ["+set", "g_gametype", "0", "+set", "coop_spChrono", "1", "+map", "coop_fl_1_1"], st)
    with c:
        res["fl_loaded"] = wait_for(present, r"Spawning Entities Done", 240)
        time.sleep(20)
        n = len(read(present))
        res["fl_end"] = press(c, present, "F5", "endbyo", settle=1)
        res["sp_next_fl"] = (re.findall(r"BYOTEST sp next (\S*)", read(present)[n:]) or [None])[-1]
        res["sp_next_fl_ok"] = res["sp_next_fl"] == "briefing/briefing5"
        res["fl_done_cvar"] = bool(re.search(r"SPCAMP done fl1 coop_spdoneC_fl1", read(present)[n:]))
        res["after_fl_loaded"] = wait_for(present, r"Spawning Entities Done", 240, n + 10)
        time.sleep(5)
        guard_check(c)


RCONPW = "byo69t"


def rcon(cmd):
    import socket
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sk.sendto(b"\xff\xff\xff\xff\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
    sk.close()


def walk(present, out, res, chrono, stop):
    """the campaign test walk (coop_mod/chrono.scr::chronoMapStart, coop_chronoTest 1): from m4l3, end each level the way the
    game does (rcon coop_chronoTestEnd 1) and record every map the campaign loads, until `stop`"""
    # the production recipe (coop_mod/cfg/chrono_start.cfg): the campaign cvars are set AFTER start_server.cfg inside one cfg - a
    # "+set" after "+exec start_server.cfg" on the command line lands after ui_startdmmap has already spawned the map
    open(os.path.join(home(present), "maintt", "byo_walk.cfg"), "w", newline="\n").write("\n".join(
        ["set ui_dmmap m4l3", "exec coop_mod/start_server.cfg", "set coop_campaign 1", "set coop_chronoTest 1",
         "set coop_campaignChrono %d" % (1 if chrono else 0), 'set coop_campaignNext ""']) + "\n")
    tail = ["+set", "g_gametype", "2", "+exec", "byo_walk.cfg"]
    seq = []
    c = launch(present, tail, [("F12", "rconpw", ["set rconPassword %s" % RCONPW])])
    with c:
        n = 0
        while True:
            t = time.time()
            got = None
            while time.time() - t < 300 and got is None:
                mm = re.findall(r"CHRONO_MAP (\S+)", read(present)[n:])
                if mm:
                    got = mm[0]
                    n = read(present).index("CHRONO_MAP " + got, n) + 5
                time.sleep(1)
                guard_check(c)
                if TRIPPED:
                    return seq
            if got is None:
                res["stalled_after"] = seq[-1] if seq else None
                break
            seq.append(got)
            if got == stop or len(seq) > 8:
                break
            time.sleep(8)
            for _ in range(4):                        # resend only when the level never took it (40 s): a second set lands on the NEXT map
                rcon("set coop_chronoTestEnd 1")
                if wait_for(present, "CHRONO_TESTEND " + re.escape(got), 40, n):
                    break
        log = read(present)
        res["handoffs"] = re.findall(r"(?:CHRONO_NEXT|BYO_NEXT) (\S+ -> \S+)", log)
        res["saves"] = re.findall(r"CHRONO_SAVE (\S*)", log)
        res["resolves"] = re.findall(r"BYO_RESOLVE (\S+ -> \S+)", log)
        shot(c, out, "walk_end")
    res["maps"] = seq
    return seq


def case_coop(present, out, res):
    """coop FULL campaign: m4l3 -> (present) briefingfl1 -> lobby -> coop_fl_1_1 -> briefing5 / (absent) m4l3 -> briefing5"""
    seq = walk(present, out, res, False, "briefing/briefing5")
    want = ["m4l3", "briefing/briefingfl1", "co_lobby1", "coop_fl_1_1", "briefing/briefing5"] if present else ["m4l3", "briefing/briefing5"]
    res["ok"] = seq == want


def case_chrono(present, out, res):
    """coop CHRONOLOGICAL: the same walk; chrono.dat is kept once the squad is in coop_fl_1_1 (for continue_absent)"""
    sv = os.path.join(home(present), "maintt", "coop_mod", "save", "chrono.dat")
    if os.path.exists(sv):
        os.remove(sv)
    seq = walk(present, out, res, True, "coop_fl_1_1" if present else "briefing/briefing5")
    want = ["m4l3", "briefing/briefingfl1", "co_lobby1", "coop_fl_1_1"] if present else ["m4l3", "briefing/briefing5"]
    res["ok"] = seq == want
    if os.path.exists(sv):
        res["chrono_dat"] = open(sv, encoding="latin-1").read().strip()
        shutil.copyfile(sv, os.path.join(out, "chrono.dat"))


def case_continue_absent(out, res):
    """the save made WITH the pak, CONTINUE'd without it: the lobby resolves it to the next mission"""
    src = os.path.join(RUNS, "chrono_present", "chrono.dat")
    dst = os.path.join(home(False), "maintt", "coop_mod", "save", "chrono.dat")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    res["saved"] = open(dst, encoding="latin-1").read().strip()
    c = launch(False, ["+set", "g_gametype", "2", "+exec", "coop_mod/cfg/chrono_continue.cfg"], [])
    with c:
        res["lobby"] = wait_for(False, r"CHRONO_LOBBY", 300)
        res["resolve"] = (re.findall(r"BYO_RESOLVE (\S+ -> \S+)", read(False)) or [None])[-1]
        res["resume"] = (re.findall(r"CHRONO_RESUME (\S+)", read(False)) or [None])[-1]
        res["ok"] = res["resolve"] is not None and res["resume"] == "briefing/briefing5"
        time.sleep(10)
        shot(c, out, "continue_absent_lobby")
        guard_check(c)


def main(cases):
    os.makedirs(RUNS, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, CLIENT, [PORT], minutes=90)
    try:
        for case in cases:
            if TRIPPED:
                print("GUARD TRIPPED - stopping:", TRIPPED)
                break
            present = case.endswith("present")
            out = os.path.join(RUNS, case + ("_" + os.environ["BYO_RES"] if os.environ.get("BYO_RES") else ""))
            shutil.rmtree(out, ignore_errors=True)
            os.makedirs(out)
            res = {"case": case}
            {"menu": lambda: case_menu(present, out, res), "sp": lambda: case_sp(present, out, res),
             "coop": lambda: case_coop(present, out, res), "chrono": lambda: case_chrono(present, out, res),
             "continue": lambda: case_continue_absent(out, res)}[case.split("_")[0]]()
            p = False if case == "continue_absent" else present
            log = read(p)
            res["script_errors"] = len(re.findall(r"Script Error", log))
            res["byo_userinfo"] = cv(p, "byo")
            res["guard"] = TRIPPED[:]
            shutil.copyfile(logp(p), os.path.join(out, "qconsole.log"))
            json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
            print(case, json.dumps(res), flush=True)
    finally:
        hg.release_slot(OWNER)


if __name__ == "__main__":
    main(sys.argv[1:])

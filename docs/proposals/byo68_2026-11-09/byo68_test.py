#!/usr/bin/env python3
"""v1.10.68 bring-your-own-disc test matrix on a PRIVATE client (H:/hzm_work/byo68-test/client, our exe build), muted,
in_gamepad 0 / in_joystick 0, on the ultrawide test display, never focused; only our own PID is ever stopped.

  python byo68_test.py <case> [<case> ...]
    menu_absent    boot without the paks: flags 0, map select / Settings / OWN DISCS sheet stills, coop_byoconvert
                   launches byo_convert.ps1 (a STUB in the test client: no window) and its status line comes back
    sp_absent      g_gametype 0 map coop_fl_1_1 without the pak: refused cleanly, client stays up
    coop_absent    stock coop m1l1 listen server boots as before (0 Script Errors); then coop_fl_1_1 refused
    menu_present   boot with the converted paks: flags 1, YOUR OWN DISCS board / sheet stills
    coop_present   coop listen server on coop_fl_1_1 (ui_startdmmap 2), join allies, still, 0 Script Errors
    sp_present     g_gametype 0 map coop_fl_1_1: loads, the mission script runs, still, 0 Script Errors
Results: H:/hzm_work/byo68-test/runs/<case>/ (qconsole.log, *.png, result.json)."""
import json
import os
import re
import shutil
import socket
import sys
import time

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
sys.path.insert(0, TOOLS)
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"H:\hzm_work\byo68-test\client"
EXE = os.path.join(CLIENT, "openmohaa.exe")
RUNS = r"H:\hzm_work\byo68-test\runs"
OWNER = "byo68"
PORT = 12297
RCONPW = "byo68t"
W, H = 1600, 900


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
        s = read(present)[start:]
        if re.search(pat, s):
            return True
        time.sleep(0.5)
    return False


def rcon(cmd):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b"\xff\xff\xff\xff\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
    s.close()


def launch(present, tail, boot_lines):
    mt = os.path.join(home(present), "maintt")
    for fn in os.listdir(mt):
        if fn.lower().endswith(".pid") or fn in ("qconsole.log", "byo_status.txt"):
            os.remove(os.path.join(mt, fn))
    on = ["set rconPassword %s" % RCONPW, "set sv_maxbots 0", "set com_maxfps 60", "set coop_dev 1", "set coop_joinCard 0",
          "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
          "set con_notifytime -1", "set thereisnomonkey 1", "set cheats 1"] + list(boot_lines)
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", home(present)), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_port", str(PORT)), ("net_ip", "127.0.0.1"), ("s_volume", "0"),
            ("in_gamepad", "0"), ("in_joystick", "0")]
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


def shot(c, out, name):
    p = os.path.join(out, name + ".png")
    try:
        c.capture_png(p)
    except Exception as e:
        print("capture failed", name, e)
    return p


def cvars(present, names, start=0):
    s = read(present)[start:]
    return {n: (re.findall(r'"%s" is:"([^"]*)' % re.escape(n), s) or [None])[-1] for n in names}


STEPS_ABSENT = [("s1", "pushmenu coop_start", "1_map_select"),
                ("s3", "pushmenu coop_settings", "3_settings"),
                ("s4", "pushmenu coop_byodisc", "4_own_discs_sheet"),
                ("s5", "coop_byoconvert frontline", None),
                ("s6", "coop_flHave_1_1;coop_flHave;coop_eaHave_1_11;coop_byoBusy;coop_byoStatus", "5_after_convert")]
STEPS_PRESENT = STEPS_ABSENT[:1] + [("s2", "set ui_coopCamp 14;exec ui/coop_start/byo.cfg;set ui_dmmap coop_fl_1_1;"
                                           "seta coop_mapcmd map coop_fl_1_1", "2_own_discs_board")] + STEPS_ABSENT[1:]
FKEYS = [0x74, 0x75, 0x76, 0x77, 0x78, 0x79]          # F5..F10, bound in the boot cfg to the step cfgs


def write_steps(present):
    """each menu step is a cfg bound to an F key; the harness posts the key to OUR window, waits, captures"""
    steps = STEPS_PRESENT if present else STEPS_ABSENT
    binds = []
    for (tag, cmd, _), vk in zip(steps, FKEYS):
        open(os.path.join(home(present), "maintt", "byo_%s.cfg" % tag), "w", newline="\n").write(
            "echo BYOT_%s\n%s\n" % (tag, cmd.replace(";", "\n")))
        binds.append('bind F%d "exec byo_%s.cfg"' % (vk - 0x6F, tag))
    return binds


def drive_menu(c, present, out, res):
    if not wait_for(present, r"----- Client Initialization Complete|Sound initialization", 120):
        res["boot"] = False
        return
    time.sleep(15)
    steps = STEPS_PRESENT if present else STEPS_ABSENT
    for (tag, cmd, name), vk in zip(steps, FKEYS):
        n = len(read(present))
        ok = False
        for _ in range(3):
            c.post_key(vk)
            if wait_for(present, "BYOT_" + tag, 6, n):
                ok = True
                break
        res.setdefault("steps", {})[tag] = ok
        time.sleep(4 if tag != "s5" else 6)
        if name:
            shot(c, out, name)
    res["cvars"] = cvars(present, ["coop_flHave_1_1", "coop_flHave", "coop_eaHave_1_11", "coop_byoBusy", "coop_byoStatus"])
    res["byoconvert_line"] = re.findall(r"coop_byoconvert: [^\n]*", read(present))


def main(cases):
    os.makedirs(RUNS, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, CLIENT, [PORT], minutes=60)
    summary = {}
    try:
        for case in cases:
            present = case.endswith("present")
            out = os.path.join(RUNS, case)
            shutil.rmtree(out, ignore_errors=True)
            os.makedirs(out)
            res = {"case": case}
            if case.startswith("menu"):
                c = launch(present, [], write_steps(present))
                with c:
                    drive_menu(c, present, out, res)
            elif case.startswith("sp"):
                c = launch(present, ["+set", "g_gametype", "0", "+map", "coop_fl_1_1"], [])
                with c:
                    if present:
                        res["loaded"] = wait_for(present, r"Spawning Entities Done|FLAI", 240)
                        time.sleep(25)
                        shot(c, out, "sp_coop_fl_1_1")
                    else:
                        res["refused"] = wait_for(present, r"[Cc]an't find map|Couldn't load maps/coop_fl_1_1|ERROR", 120)
                        time.sleep(5)
                        res["client_alive"] = c.proc.poll() is None
                        shot(c, out, "sp_absent_menu")
            elif case.startswith("coop"):
                mp = "coop_fl_1_1" if present else "m1l1"
                c = launch(present, ["+set", "g_gametype", "2", "+set", "ui_dmmap", mp, "+exec", "coop_mod/start_server.cfg"], [])
                with c:
                    res["loaded"] = wait_for(present, r"Spawning Entities Done", 300)
                    time.sleep(10)
                    for _ in range(4):
                        rcon("popmenu 0; wait 10; primarydmweapon rifle; wait 5; join_team allies; wait 20; popmenu 0")
                        if wait_for(present, r"has joined|joined the", 15):
                            break
                    res["joined"] = bool(re.search(r"has joined|joined the", read(present)))
                    time.sleep(25)
                    shot(c, out, "coop_" + mp)
                    if not present:
                        n = len(read(present))
                        rcon("map coop_fl_1_1")
                        res["fl_refused"] = wait_for(present, r"[Cc]an't find map|Couldn't load", 60, n)
                        time.sleep(5)
                        res["client_alive"] = c.proc.poll() is None
            log = read(present)
            res["script_errors"] = len(re.findall(r"Script Error", log))
            res["coop_main"] = bool(re.search(r"coop_mod|HZM", log))
            res["missing_fl_exec"] = bool(re.search(r"couldn't exec fl/have_1_1.cfg", log))
            res["pk3_fl_mounted"] = "zzzz_coop_fl_1_1.pk3" in log
            shutil.copyfile(logp(present), os.path.join(out, "qconsole.log"))
            json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
            summary[case] = res
            print(case, json.dumps(res))
    finally:
        hg.release_slot(OWNER)
    return summary


if __name__ == "__main__":
    main(sys.argv[1:])

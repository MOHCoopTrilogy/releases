#!/usr/bin/env python3
"""Private test-client harness for the Frontline pilot. Our own code.

Runs ONLY G:\\mohaa-frontline (registered in harness_guard as owner "frontline"):
byte copies of the GOG-root exe/DLLs, its own home (holding just the locally
converted pk3 + test cfgs), basepath = the GOG tree read-only. Launch is via
harness_window.launch_background (non-primary display, never focused, muted,
guard + job object). Only PIDs this script started are ever stopped.

usage:
  flharness.py shots <map> <views.json> <outdir> [--renderer opengl1|opengl2] [--coop]
      views.json: {"name": {"pos": [x,y,z], "ang": [pitch,yaw,0]}, ...}
  flharness.py cmd <map> <cfgfile> <seconds>       run arbitrary console lines after join
"""
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-frontline"
EXE = os.path.join(CLIENT, "openmohaa.exe")
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
OWNER = "frontline"
PORT = 12295
RCONPW = "flpilot"
MAGIC = b"\xff\xff\xff\xff"
H = {"c": None}


def test_display():
    """user 2026-11-08: test windows go on the 34" ULTRAWIDE, picked by its RESOLUTION (3440x1440), never by the
    primary flag or the device name (the primary is now a 3840x2160 TV and names renumber)"""
    for m in hw.monitors():
        r = m["rect"]
        if (r[2] - r[0], r[3] - r[1]) == (3440, 1440):
            return m
    raise RuntimeError("no 3440x1440 display connected - refusing to put a test window anywhere else")


def log(*a):
    print(*a, flush=True)


def rcon(cmd, timeout=1.5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(MAGIC + b"\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
        try:
            d, _ = s.recvfrom(16384)
            return d[4:].decode("latin-1")
        except socket.timeout:
            return ""
    finally:
        s.close()


def read_log():
    try:
        return open(LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def wait_log(pat, timeout, start=0):
    rx = re.compile(pat)
    t0 = time.time()
    while time.time() - t0 < timeout:
        c = H["c"]
        if c is not None and (c.proc.poll() is not None):
            raise RuntimeError("client exited")
        if c is not None and c.watcher.violations:
            raise RuntimeError("window policy violation %s" % c.watcher.violations[:2])
        m = rx.search(read_log(), start)
        if m:
            return m
        time.sleep(1.0)
    return None


_N = {"n": 0}


def step(lines, timeout=240):
    _N["n"] += 1
    mk = "FLSTEP_%d_done" % _N["n"]
    with open(os.path.join(MAINTT, "flstep.cfg"), "w", newline="\n") as f:
        # re-mute every step: the coop server stuffs s_volume 0.9 to the client after it joins
        f.write("\n".join(["set s_volume 0", "set s_musicvolume 0"] + lines + ["set s_volume 0", "echo %s" % mk]) + "\n")
    start = len(read_log())
    rcon("exec flstep.cfg")
    if not wait_log(re.escape(mk), timeout, max(0, start - 10)):
        raise RuntimeError("step timed out: %s" % lines[:3])


def launch(mapname, renderer="opengl1", coop=False, w=1280, h=720, extra_sets=(), gametype="2"):
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    on = ["set rconPassword %s" % RCONPW, "set sv_maxbots 0", "set sv_numbots 0", "set com_maxfps 60",
          "set thereisnomonkey 1", "set cheats 1", "set coop_dev 1", "set cg_drawviewmodel 0",
          "set con_notifytime -1", "set g_teamswitchdelay 0", "set coop_joinCard 0",
          "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0",
          "set in_gamepad 0", "set in_joystick 0"] + list(extra_sets)   # user: every test run muted
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", renderer),
            ("r_mode", "-1"), ("r_customwidth", str(w)), ("r_customheight", str(h)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_port", str(PORT)), ("net_ip", "127.0.0.1"),
            ("s_volume", "0"),
            # never read the user's controller: SDL delivers pad input to background windows, and pad Y in a menu
            # runs Sys_OpenOnScreenKeyboard -> osk.exe on the user's screen while they play (bug-10635)
            ("in_gamepad", "0"), ("in_joystick", "0")] + \
        ([("com_maxfpsUnfocused", "0"), ("r_swapInterval", "0")] if os.environ.get("FL_FULLSPEED") else [])
    # user: test runs are silent - the coop server stuffs s_volume 0.9 after join, so no sound device at all
    args = [EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+set", "g_gametype", gametype, "+exec", "fl_on.cfg"]
    if coop:
        args += ["+set", "ui_dmmap", mapname, "+exec", "coop_mod/start_server.cfg"]
    else:
        args += ["+map", mapname]
    d = test_display()
    if w > d["rect"][2] - d["rect"][0] or h > d["rect"][3] - d["rect"][1]:
        # big-resolution check (e.g. the user's 3440x1440) on the 1920x1080 test display: let the window overhang
        d = dict(d)
        d["rect"] = (d["rect"][0], d["rect"][1], d["rect"][0] + w, d["rect"][1] + h)
    args, late = hw.apply_policy(args, width=w, height=h, display=d)
    on += late
    with open(os.path.join(MAINTT, "fl_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(on) + "\n")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log, display=test_display(),
                             below_normal=not os.environ.get("FL_FULLSPEED"))
    H["c"] = c
    hg.set_slot_pid(OWNER, c.proc.pid)
    log("client pid", c.proc.pid)
    return c


def join():
    start = len(read_log())
    for _ in range(4):
        step(["popmenu 0", "wait 10", "primarydmweapon rifle", "wait 5", "join_team allies", "wait 20",
              "popmenu 0", "wait 40", "popmenu 0", "wait 20", "+attackprimary", "wait 10", "-attackprimary"])
        if wait_log(r"has joined the (Allies|Axis|Free)|joined the", 20, start):
            return True
    return False


def shots(mapname, views, outdir, renderer, coop, w=1280, h=720, fps=False):
    os.makedirs(outdir, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        c = launch(mapname, renderer, coop, w=w, h=h,
                   extra_sets=(["set fps 1", "set com_maxfps 250", "set r_swapInterval 0"] if fps else []) +
                   [x.strip() for x in os.environ.get("FL_SETS", "").split(";") if x.strip()])   # e.g. FL_SETS="set coop_fltest 4"
        with c:
            if not wait_log(r"Server: %s|Spawning Entities Done|COOP_MAPGRADE" % re.escape(mapname), 300):
                raise RuntimeError("map never loaded")
            time.sleep(8)
            join()
            time.sleep(14)          # the coop join card lingers up to 9 s after the last spectator send
            step(["noclip", "wait 5", "god", "wait 5", "notarget", "wait 20"] if not os.environ.get("FL_NOCLIP_OFF") else ["wait 20"])
            sd = os.path.join(MAINTT, "screenshots")
            for name, v in views.items():
                if "pos" not in v:          # stock-map check: shoot from wherever the player spawned
                    step(["popmenu 0", "wait 5", "popmenu 0", "wait 120", "screenshot fl_%s" % name, "wait 20"])
                    time.sleep(1.5)
                    for ext in (".tga", ".jpg"):
                        src = os.path.join(MAINTT, "screenshots", "fl_%s%s" % (name, ext))
                        if os.path.exists(src):
                            shutil.move(src, os.path.join(outdir, "%s%s" % (name, ext)))
                    continue
                x, y, z = v["pos"]
                p, yaw = v["ang"][0], v["ang"][1]
                step(["popmenu 0", "wait 5", "popmenu 0", "set thereisnomonkey 1", "set cheats 1", "tele %.1f %.1f %.1f" % (x, y, z), "wait 5", "face %.1f %.1f 0" % (p, yaw), "wait 120",
                      "screenshot fl_%s" % name, "wait 20"])
                time.sleep(1.5)
                for ext in (".tga", ".jpg"):
                    src = os.path.join(sd, "fl_%s%s" % (name, ext))
                    if os.path.exists(src):
                        shutil.move(src, os.path.join(outdir, "%s%s" % (name, ext)))
            step(["fps", "wait 5"])
            rep = c.report() if hasattr(c, "report") else None
            log("window report", rep)
            shutil.copyfile(LOG, os.path.join(outdir, "qconsole.log"))
    finally:
        hg.release_slot(OWNER)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "shots":
        r = "opengl1"
        if "--renderer" in a:
            r = a[a.index("--renderer") + 1]
        w, h = 1280, 720
        if "--size" in a:
            w, h = (int(v) for v in a[a.index("--size") + 1].split("x"))
        shots(a[1], json.load(open(a[2])), a[3], r, "--coop" in a, w, h, "--fps" in a)


def walk(outdir, pk3, renderer="opengl2"):
    """REAL-INPUT objective run: the client walks the last metres with +forward and presses +use (no teleport
    into the trigger, no self-test). AI is live (god only, no notarget) so guards/roamers/MG nests engage."""
    import zipfile as _zf
    os.makedirs(outdir, exist_ok=True)
    t = _zf.ZipFile(pk3).read("maps/coop_fl_1_1_data.scr").decode("latin-1")

    def vec(name):
        m = re.search(re.escape(name) + r" = \( (\S+) (\S+) (\S+) \)", t)
        return tuple(float(v) for v in m.groups())
    drop, roster = vec('level.fl_pos["M1_1_ResistanceDrop"]'), vec('level.fl_pos["M1_1_ClipBoard"]')
    wall, west = vec('level.fl_pos["M1_1_WallExplosion"]'), vec("level.fl_west")
    dock = tuple((a + b) / 2 for a, b in zip(wall, west))
    crate = (west[0] + 40, west[1], west[2])
    goals = [("drop", drop, True), ("roster", roster, True), ("wall", wall, True), ("dock", dock, False),
             ("crate", crate, True)]
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        c = launch("coop_fl_1_1", renderer, False, w=1280, h=720,
                   extra_sets=["set coop_fltest 0", "set coop_health 20000", "set coop_dbno 0"])
        with c:
            if not wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 300):
                raise RuntimeError("map never loaded")
            time.sleep(8)
            join()
            time.sleep(14)
            for name, g, use in goals:
                # approach from a Frontline navpoint 100-320u from the goal (a known-walkable spot), facing the goal
                import fl_gates
                nodes = fl_gates.pathnodes(pk3, "coop_fl_1_1")
                cand = [q for q in nodes if 48 < math.hypot(q[0] - g[0], q[1] - g[1]) < 320 and abs(q[2] - g[2]) < 80]
                q = min(cand, key=lambda q: (math.hypot(q[0] - g[0], q[1] - g[1]), q)) if cand else                     (g[0] - 200, g[1], g[2] + 16)
                ax, ay = q[0], q[1]
                dist = math.hypot(g[0] - ax, g[1] - ay)
                yaw = math.degrees(math.atan2(g[1] - ay, g[0] - ax))
                fwd_frames = int(dist / 220.0 * 60) + 10
                start = len(read_log())
                lines = ["popmenu 0", "+attackprimary", "wait 5", "-attackprimary", "wait 30", "popmenu 0",
                         "set thereisnomonkey 1", "set cheats 1",
                         "tele %.0f %.0f %.0f" % (ax, ay, q[2] - 8), "wait 20", "face 0 %.0f 0" % yaw, "wait 10",
                         "+forward", "wait %d" % fwd_frames, "-forward", "wait 10"]
                if use:
                    lines += ["+use", "wait 8", "-use", "wait 20", "+use", "wait 8", "-use", "wait 30"]
                lines += ["wait 60", "coord", "screenshot fl_walk_%s" % name, "wait 20"]
                step(lines)
                ok = wait_log(r"FLOBJ \d+ done", 25, start)
                log("objective", name, "->", ok.group(0) if ok else "NOT COMPLETED")
                time.sleep(2)
                for ext in (".tga", ".jpg"):
                    src = os.path.join(MAINTT, "screenshots", "fl_walk_%s%s" % (name, ext))
                    if os.path.exists(src):
                        shutil.move(src, os.path.join(outdir, "%s%s" % (name, ext)))
            time.sleep(10)
            shutil.copyfile(LOG, os.path.join(outdir, "qconsole.log"))
    finally:
        hg.release_slot(OWNER)


if __name__ == "__main__" and sys.argv[1] == "walk":
    walk(sys.argv[2], sys.argv[3])

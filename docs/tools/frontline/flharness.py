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
        f.write("\n".join(lines + ["echo %s" % mk]) + "\n")
    start = len(read_log())
    rcon("exec flstep.cfg")
    if not wait_log(re.escape(mk), timeout, max(0, start - 10)):
        raise RuntimeError("step timed out: %s" % lines[:3])


def launch(mapname, renderer="opengl1", coop=False, w=1280, h=720, extra_sets=()):
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    on = ["set rconPassword %s" % RCONPW, "set sv_maxbots 0", "set sv_numbots 0", "set com_maxfps 60",
          "set thereisnomonkey 1", "set cheats 1", "set coop_dev 1", "set cg_drawviewmodel 0",
          "set con_notifytime -1", "set g_teamswitchdelay 0", "set coop_joinCard 0"] + list(extra_sets)
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", renderer),
            ("r_mode", "-1"), ("r_customwidth", str(w)), ("r_customheight", str(h)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_port", str(PORT)), ("net_ip", "127.0.0.1")]
    args = [EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+set", "g_gametype", "2", "+exec", "fl_on.cfg"]
    if coop:
        args += ["+set", "ui_dmmap", mapname, "+exec", "coop_mod/start_server.cfg"]
    else:
        args += ["+map", mapname]
    args, late = hw.apply_policy(args, width=w, height=h)
    on += late
    with open(os.path.join(MAINTT, "fl_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(on) + "\n")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
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


def shots(mapname, views, outdir, renderer, coop):
    os.makedirs(outdir, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        c = launch(mapname, renderer, coop)
        with c:
            if not wait_log(r"Server: %s|Spawning Entities Done|COOP_MAPGRADE" % re.escape(mapname), 300):
                raise RuntimeError("map never loaded")
            time.sleep(8)
            join()
            time.sleep(14)          # the coop join card lingers up to 9 s after the last spectator send
            step(["noclip", "wait 5", "god", "wait 5", "notarget", "wait 20"])
            sd = os.path.join(MAINTT, "screenshots")
            for name, v in views.items():
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
        shots(a[1], json.load(open(a[2])), a[3], r, "--coop" in a)

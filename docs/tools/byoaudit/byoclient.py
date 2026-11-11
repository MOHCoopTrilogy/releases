#!/usr/bin/env python3
"""byoclient - one private background test client for the own-disc map audits (Frontline / European Assault).
Our code. Nothing from a disc is in here; screenshots and logs it writes are LOCAL ONLY (never committed).

Client folder (default G:\\mohaa-flpolish, override BYO_CLIENT): byte copies of the engine build, basepath = the GOG
tree read-only, home inside the folder (harness_guard classifies it HARNESS). Started ONLY through
harness_window.launch_background: test display picked by resolution (BYO_TEST_RES, default 1920x1080 = the second
screen, because the user plays on the ultrawide), never focused, cursor / capture / audio guard ENFORCED, job object,
muted, in_mouse 0 / in_nograb 1 / in_gamepad 0 / in_joystick 0. Cheats and every latched cvar go on the command line.
Input = rcon `exec` of a step cfg (no key injection, no pad). Only the PID this module started is ever stopped.

    with Client(map="coop_fl_1_1", sets=[("coop_fltest", "0")]) as c:
        c.wait(r"Spawning Entities Done", 300); c.join()
        c.step(["noclip", "tele 0 0 0", "screenshot x"]); c.grab("x", outdir)
"""
import os
import re
import shutil
import socket
import sys
import time

TOOLS = r"C:\mohaa-coop-dev\docs\tools"
sys.path.insert(0, TOOLS)
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
MAGIC = b"\xff\xff\xff\xff"
QUIET = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
         "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set con_notifytime -1", "set coop_joinCard 0",
         # player.scr stufftexts s_volume <coop_tinnitusBaseVol> on every spawn (bug-10805): keep all of these at 0
         "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"]


class GuardTrip(RuntimeError):
    pass


class Client:
    def __init__(self, map, sets=(), folder=None, port=12391, rconpw="byoaudit", coop=True, w=960, h=540,
                 renderer="opengl2", cfg=(), name="auditor", connect=None, home=None):
        self.folder = folder or os.environ.get("BYO_CLIENT", r"G:\mohaa-flpolish")
        self.home = home or os.path.join(self.folder, "home")
        self.connect = connect
        self.maintt = os.path.join(self.home, "maintt")
        self.log = os.path.join(self.maintt, "qconsole.log")
        self.map, self.sets, self.port, self.pw, self.coop = map, list(sets), port, rconpw, coop
        self.w, self.h, self.renderer, self.cfg, self.name = w, h, renderer, list(cfg), name
        self.c = None
        self.n = 0

    # ---------------------------------------------------------------- launch
    def __enter__(self):
        # the user's own game running -> only the 1080p second screen; otherwise the ultrawide (H:\hzm_work\DISPLAY_QUEUE.md)
        res = os.environ.get("BYO_TEST_RES") or ("1920x1080" if user_playing() else "3440x1440")
        os.environ["HZM_TEST_RES"] = res
        os.makedirs(self.maintt, exist_ok=True)
        for fn in os.listdir(self.maintt):
            if fn.lower().endswith(".pid") or fn == "qconsole.log":
                os.remove(os.path.join(self.maintt, fn))
        base = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", self.home),
                ("cl_renderer", self.renderer), ("r_mode", "-1"), ("r_customwidth", str(self.w)),
                ("r_customheight", str(self.h)), ("r_fullscreen", "0"), ("developer", "1"), ("logfile", "2"),
                ("net_port", str(self.port)), ("net_ip", "127.0.0.1"), ("in_gamepad", "0"), ("in_joystick", "0"),
                ("in_mouse", "0"), ("in_nograb", "1"), ("s_volume", "0"), ("name", self.name),
                ("cheats", "1"), ("thereisnomonkey", "1")] + self.sets
        args = [os.path.join(self.folder, "openmohaa.exe")]
        for k, v in base:
            args += ["+set", k, v]
        if self.connect:
            args += ["+exec", "byoaudit_on.cfg", "+connect", self.connect]
        elif self.coop:
            args += ["+set", "g_gametype", "2", "+exec", "byoaudit_on.cfg", "+set", "ui_dmmap", self.map,
                     "+exec", "coop_mod/start_server.cfg"]
        else:
            args += ["+set", "g_gametype", "0", "+exec", "byoaudit_on.cfg", "+map", self.map]
        d = hw.test_display()
        args, late = hw.apply_policy(args, width=self.w, height=self.h, display=d)
        on = QUIET + ([JOIN_BIND] if self.connect else []) + ["set rconPassword %s" % self.pw, "set sv_maxbots 0", "set sv_numbots 0", "set coop_dev 1",
                      "set g_teamswitchdelay 0"] + self.cfg + late
        open(os.path.join(self.maintt, "byoaudit_on.cfg"), "w", newline="\n").write("\n".join(on) + "\n")
        self.c = hw.launch_background(args[0], args[1:], self.folder, policy=False, display=d, below_normal=True,
                                      watch_audio=True, log=lambda *a: None)
        self.c.__enter__()
        return self

    def __exit__(self, *exc):
        try:
            if self.c is not None:
                self.c.__exit__(*exc)
        finally:
            self.c = None
        return False

    # ---------------------------------------------------------------- io
    def text(self):
        try:
            return open(self.log, "rb").read().decode("latin-1")
        except OSError:
            return ""

    def check(self):
        v = getattr(getattr(self.c, "watcher", None), "violations", None)
        if v:
            raise GuardTrip(repr(v[:3]))
        if self.c is not None and self.c.proc.poll() is not None:
            raise RuntimeError("client exited")

    def wait(self, pat, timeout, start=0):
        rx = re.compile(pat)
        t = time.time()
        while time.time() - t < timeout:
            self.check()
            m = rx.search(self.text(), start)
            if m:
                return m
            time.sleep(1.0)
        return None

    def rcon(self, cmd, timeout=1.5):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        try:
            s.sendto(MAGIC + b"\x02rcon " + self.pw.encode() + b" " + cmd.encode(), ("127.0.0.1", self.port))
            try:
                return s.recvfrom(16384)[0][4:].decode("latin-1")
            except socket.timeout:
                return ""
        finally:
            s.close()

    def step(self, lines, timeout=240):
        """exec a cfg of console lines on the server/client and wait for its end marker"""
        self.n += 1
        mk = "BYOSTEP_%d_done" % self.n
        open(os.path.join(self.maintt, "byostep.cfg"), "w", newline="\n").write(
            "\n".join(["set s_volume 0", "set s_musicvolume 0"] + list(lines) + ["set s_volume 0", "echo " + mk]) + "\n")
        start = len(self.text())
        self.rcon("exec byostep.cfg")
        if not self.wait(re.escape(mk), timeout, max(0, start - 10)):
            raise RuntimeError("step timed out: %s" % lines[:3])

    def join(self, team="allies"):
        start = len(self.text())
        for _ in range(5):
            self.step(["popmenu 0", "wait 10", "primarydmweapon rifle", "wait 5", "join_team " + team, "wait 20",
                       "popmenu 0", "wait 40", "popmenu 0", "wait 20"])
            if self.wait(r"has joined the|joined the (Allies|Axis)", 20, start):
                return True
        return False

    def grab(self, name, outdir):
        """move screenshots/<name>.(jpg|tga) to outdir (LOCAL ONLY)"""
        os.makedirs(outdir, exist_ok=True)
        time.sleep(1.0)
        for ext in (".jpg", ".tga"):
            src = os.path.join(self.maintt, "screenshots", name + ext)
            if os.path.exists(src):
                dst = os.path.join(outdir, name + ext)
                shutil.move(src, dst)
                return dst
        return None

    def keep_log(self, path):
        shutil.copyfile(self.log, path)


def user_playing():
    return hg.user_game_running_raw() if hasattr(hg, "user_game_running_raw") else hg.user_game_running()


class Server:
    """a private DEDICATED server (cheats really on - a listen host's ui_startdmmap runs 'set cheats 0'), no window
    (harness_window.popen_kwargs: CREATE_NO_WINDOW, below-normal priority). Home = <folder>/srvhome."""

    def __init__(self, map, sets=(), folder=None, port=12391, rconpw="byoaudit", cfg=()):
        import subprocess
        self.subprocess = subprocess
        self.folder = folder or os.environ.get("BYO_CLIENT", r"G:\mohaa-flpolish")
        self.home = os.path.join(self.folder, "srvhome")
        self.maintt = os.path.join(self.home, "maintt")
        self.log = os.path.join(self.maintt, "qconsole.log")
        self.map, self.sets, self.port, self.pw, self.cfg = map, list(sets), port, rconpw, list(cfg)
        self.p = None

    def __enter__(self):
        os.makedirs(self.maintt, exist_ok=True)
        for fn in os.listdir(self.maintt):
            if fn.lower().endswith(".pid") or fn == "qconsole.log":
                os.remove(os.path.join(self.maintt, fn))
        open(os.path.join(self.maintt, "byoaudit_srv.cfg"), "w", newline="\n").write("\n".join(
            ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "set developer 1",
             "set thereisnomonkey 1", "set cheats 1", "set g_inactivekick 0", "set g_inactivespectate 0"] + self.cfg) + "\n")
        args = [os.path.join(self.folder, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
                "+set", "fs_homepath", self.home, "+set", "dedicated", "1", "+set", "net_port", str(self.port),
                "+set", "net_ip", "127.0.0.1", "+set", "sv_maxclients", "4", "+set", "g_gametype", "2",
                "+set", "logfile", "2", "+set", "developer", "1", "+set", "cheats", "1", "+set", "thereisnomonkey", "1",
                "+set", "coop_joinCard", "0", "+set", "g_teamswitchdelay", "0", "+set", "rconpassword", self.pw,
                "+set", "g_inactivekick", "0", "+set", "g_inactivespectate", "0"]   # a parked audit player is not idle
        for k, v in self.sets:
            args += ["+set", k, v]
        args += ["+exec", "byoaudit_srv.cfg", "+map", self.map]
        self.p = self.subprocess.Popen(args, **hw.popen_kwargs())
        return self

    def __exit__(self, *exc):
        if self.p is not None and self.p.poll() is None:
            self.p.kill()        # only the PID this object started
        self.p = None
        return False

    def text(self):
        try:
            return open(self.log, "rb").read().decode("latin-1")
        except OSError:
            return ""

    def wait(self, pat, timeout, start=0, clients=()):
        rx = re.compile(pat)
        t = time.time()
        while time.time() - t < timeout:
            for c in clients:
                c.check()
            if self.p.poll() is not None:
                raise RuntimeError("server exited")
            m = rx.search(self.text(), start)
            if m:
                return m
            time.sleep(1.0)
        return None

    def rcon(self, cmd, timeout=1.5):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        try:
            s.sendto(MAGIC + b"\x02rcon " + self.pw.encode() + b" " + cmd.encode(), ("127.0.0.1", self.port))
            try:
                return s.recvfrom(16384)[0][4:].decode("latin-1")
            except socket.timeout:
                return ""
        finally:
            s.close()


JOIN_BIND = ('bind F9 "popmenu 0; wait 10; primarydmweapon rifle; wait 5; join_team allies; wait 30; popmenu 0; '
             'wait 30; popmenu 0"')
VK_F9 = 0x78


def join_client(srv, c, name, timeout=300):
    """press F9 in OUR client window (post_key to the test HWND only) until the server log shows the player joined"""
    t = time.time()
    while time.time() - t < timeout:
        s = srv.text()
        if re.search(re.escape(name) + r" has joined the (Allies|American)", s, re.I):
            return True
        if ("CS_ACTIVE for " + name) in s or "entered the battle" in s:
            c.c.post_key(VK_F9)
        c.check()
        time.sleep(5)
    return False

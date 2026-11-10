#!/usr/bin/env python3
"""Two-client coop run for the Frontline pilot: a private dedicated server (coop, coop_fltest 1 waiting for two
players) plus two private clients (G:\\mohaa-frontline, G:\\mohaa-frontline2) that connect and join. The server's
self-test then walks the team through all five objectives. Our own code; only our own PIDs are stopped.
usage: flcoop2.py <outdir>"""
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
# HZM_GAME=fl (default) / ea: the same two-client coop run for either BYO pilot
GAME = os.environ.get("HZM_GAME", "fl")
P = {"fl": dict(srvhome=r"G:\mohaa-frontline\srvhome", port=12291, ded=os.path.join(GOG, "omohaaded.exe"), mapname="coop_fl_1_1",
               clients=[(r"G:\mohaa-frontline", "frontline", "FL_Alpha"), (r"G:\mohaa-frontline2", "frontline2", "FL_Bravo")], tag="FL"),
     "ea": dict(srvhome=r"G:\mohaa-ea\srvhome", port=12396, ded=r"G:\mohaa-ea\omohaaded.exe", mapname="coop_ea_1_11",
               clients=[(r"G:\mohaa-ea", "ea", "EA_Alpha"), (r"G:\mohaa-ea2", "ea2", "EA_Bravo")], tag="EA")}[GAME]
SRVHOME = P["srvhome"]
SLOG = os.path.join(SRVHOME, "maintt", "qconsole.log")
PORT = P["port"]
CLIENTS = P["clients"]
T = P["tag"]
VK_F9 = 0x78


def slog():
    try:
        return open(SLOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def main(out):
    os.makedirs(out, exist_ok=True)
    if os.path.exists(SLOG):
        os.remove(SLOG)
    args = [P["ded"], "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", SRVHOME, "+set", "dedicated", "1", "+set", "net_port", str(PORT),
            "+set", "net_ip", "127.0.0.1", "+set", "sv_maxclients", "4", "+set", "g_gametype", "2",
            "+set", "logfile", "2", "+set", "developer", "1", "+set", "coop_%stest" % T.lower(), os.environ.get("FL_TESTMODE", "1"),
            "+set", "coop_%stestPlayers" % T.lower(), "2", "+set", "coop_joinCard", "0", "+set", "coop_dbno", "0",
            "+set", "g_teamswitchdelay", "0", "+set", "rconpassword", "hzmfilm", "+map", P["mapname"]]
    srv = subprocess.Popen(args, **hw.popen_kwargs())
    print("server pid", srv.pid, flush=True)
    clients = []
    try:
        t0 = time.time()
        while T + "AI" not in slog() and time.time() - t0 < 240:
            time.sleep(2)
        for folder, owner, name in CLIENTS:
            home = os.path.join(folder, "home")
            mt = os.path.join(home, "maintt")
            for fn in os.listdir(mt):
                if fn.lower().endswith(".pid"):
                    os.remove(os.path.join(mt, fn))
            with open(os.path.join(mt, "fl_c.cfg"), "w", newline="\n") as f:
                f.write('bind F9 "popmenu 0; wait 10; primarydmweapon rifle; wait 5; join_team allies; wait 30; '
                        'popmenu 0; wait 30; popmenu 0; +attackprimary; wait 10; -attackprimary"\n'
                        'bind F10 "rconpassword hzmfilm; rcon map %s"\n' % os.environ.get("FL_FILM", "none") +
                        'bind F11 "+attackprimary; wait 10; -attackprimary"\n'
                        'set cg_drawviewmodel 1\nset com_maxfps 60\n'
                        'set s_volume 0\nset s_musicvolume 0\nset s_ambientvolume 0\n'   # muted runs
                        'set in_gamepad 0\nset in_joystick 0\n')   # never read the user's pad (bug-10635: pad Y -> osk.exe)
            hg.acquire_slot(owner, os.path.join(folder, "openmohaa.exe"), home, [PORT], minutes=30)
            cargs = ["+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", home,
                     "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", "960",
                     "+set", "r_customheight", "540", "+set", "r_fullscreen", "0", "+set", "name", name,
                     "+set", "logfile", "2", "+set", "in_gamepad", "0", "+set", "in_joystick", "0",
                     "+exec", "fl_c.cfg", "+connect", "127.0.0.1:%d" % PORT]
            prim = next(m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == (3440, 1440))
            full, late = hw.apply_policy([os.path.join(folder, "openmohaa.exe")] + cargs, width=960, height=540,
                                         display=prim)
            c = hw.launch_background(full[0], full[1:], folder, policy=False, log=lambda *a: None, display=prim)
            hg.set_slot_pid(owner, c.proc.pid)
            clients.append((c, folder, owner, name))
            print("client", name, "pid", c.proc.pid, flush=True)
            time.sleep(20)
        # press F9 on each client until the server sees both in the battle
        t0 = time.time()
        # bigger converted paks (EA) load for minutes: keep pressing for up to 10 min, and only at a client the
        # server already shows ACTIVE (an F9 during the load runs join_team before cgame exists: "Unknown command")
        while time.time() - t0 < 600:
            log = slog()
            # "entered the battle" prints at CONNECT on v1.10.66+, before the team join: count a player only once
            # the server says he joined a team (still spectator -> keep pressing F9)
            def on_team(n):
                return re.search(re.escape(n) + r" has joined the (Allies|Axis|American|German)", log, re.I) is not None
            joined = [n for _, _, _, n in clients if on_team(n)]
            if len(joined) == len(clients) and ((T + "TEST players=2") in log or os.environ.get("FL_TESTMODE") == "3" or os.environ.get("FL_FILM")):
                break
            for c, _, _, n in clients:
                if n not in joined and ("to CS_ACTIVE for " + n) in log:
                    c.post_key(VK_F9)
            time.sleep(6)
        print("joined:", joined, flush=True)
        if os.environ.get("FL_FILM"):
            film_run(clients, out)
            return
        # watch the self-test, grab client frames for the record
        t0, k = time.time(), 0
        while time.time() - t0 < 600 and (T + "TEST end") not in slog() and "FLASSIST obj 5 done=1" not in slog():
            if os.environ.get("FL_TESTMODE") == "3":
                # real input: hold W (forward) ~0.7 s, then tap F (use) - the HZM default binds
                for c, _, _, n in clients:
                    c.post_key(0x57, down_ms=700)
                    c.post_key(0x46, down_ms=80)
            if k % 3 == 0:
                for c, _, _, n in clients:
                    try:
                        c.capture_png(os.path.join(out, "%s_%03d.png" % (n, k)))
                    except Exception:
                        pass
            k += 1
            time.sleep(5)
        time.sleep(5)
    finally:
        for c, folder, owner, n in clients:
            try:
                c.close()
            except Exception:
                try:
                    c.proc.kill()
                except Exception:
                    pass
            hg.release_slot(owner)
        srv.kill()
        shutil.copyfile(SLOG, os.path.join(out, "server_qconsole.log"))
    log = slog()
    for tag in [T + x for x in ("TEST", "ASSIST", "USE trigger", "OBJ", "CUE", "SET", "MISSION", "TANK", "CHARGE")] + ["Script Error"]:
        hits = re.findall(r"\^~\^~\^ " + tag + r"[^\n]*", log)
        print(tag, len(hits), hits[-7:])


def clog(folder):
    try:
        return open(os.path.join(folder, "home", "maintt", "qconsole.log"), "rb").read().decode("latin-1")
    except OSError:
        return ""


def film_run(clients, out):
    """FL_FILM=<briefing map>: both clients are in the battle on the mission map; client 1 rcons a map change to
    the briefing (the real route), both press fire to spawn, then the synced overlay must start on BOTH clients
    ('COOPBV start'); frames of both with the ready roster, then [Use] on both = READY gate -> next map."""
    brief = os.environ["FL_FILM"]
    n0 = len(slog())
    clients[0][0].post_key(0x79)                      # F10: rcon map <briefing>
    t0 = time.time()
    while ("Server: " + brief) not in slog()[n0:] and time.time() - t0 < 120:
        time.sleep(2)
    print("briefing loaded:", ("Server: " + brief) in slog()[n0:], flush=True)
    t0 = time.time()
    while "COOPBV publish" not in slog()[n0:] and time.time() - t0 < 180:
        for c, _, _, n in clients:
            c.post_key(VK_F9)                         # F9: close the team menu, join allies, fire (a client can come back from the map change at the team menu)
        time.sleep(6)
    print("publish:", "COOPBV publish" in slog()[n0:], flush=True)
    starts = {}
    t0, k = time.time(), 0
    while time.time() - t0 < 30:
        for c, folder, _, n in clients:
            m = re.findall(r"\^~\^~\^ COOPBV (?:start|stale|missing|cannot)[^\n]*", clog(folder))
            if m:
                starts[n] = m[-1]
            if k in (1, 3, 5):
                try:
                    c.capture_png(os.path.join(out, "film_%s_%d.png" % (n, k)))
                except Exception:
                    pass
        k += 1
        time.sleep(4)
    print("overlay:", starts, flush=True)
    t0 = time.time()
    while "EAKIT given" not in slog()[n0:] and time.time() - t0 < 240:
        for c, _, _, n in clients:
            c.post_key(0x46, down_ms=80)              # F = use = READY
        time.sleep(5)
    print("next map + kit:", "EAKIT given" in slog()[n0:], flush=True)
    time.sleep(3)


if __name__ == "__main__":
    main(sys.argv[1])

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
SRVHOME = r"G:\mohaa-frontline\srvhome"
SLOG = os.path.join(SRVHOME, "maintt", "qconsole.log")
PORT = 12291
CLIENTS = [(r"G:\mohaa-frontline", "frontline", "FL_Alpha"), (r"G:\mohaa-frontline2", "frontline2", "FL_Bravo")]
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
    args = [os.path.join(GOG, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", SRVHOME, "+set", "dedicated", "1", "+set", "net_port", str(PORT),
            "+set", "net_ip", "127.0.0.1", "+set", "sv_maxclients", "4", "+set", "g_gametype", "2",
            "+set", "logfile", "2", "+set", "developer", "1", "+set", "coop_fltest", os.environ.get("FL_TESTMODE", "1"),
            "+set", "coop_fltestPlayers", "2", "+set", "coop_joinCard", "0", "+set", "coop_dbno", "0",
            "+set", "g_teamswitchdelay", "0", "+map", "mfl_1_1"]
    srv = subprocess.Popen(args, **hw.popen_kwargs())
    print("server pid", srv.pid, flush=True)
    clients = []
    try:
        t0 = time.time()
        while "FLAI" not in slog() and time.time() - t0 < 240:
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
                        'set cg_drawviewmodel 1\nset com_maxfps 60\n'
                        'set s_volume 0\nset s_musicvolume 0\nset s_ambientvolume 0\n')   # muted runs
            hg.acquire_slot(owner, os.path.join(folder, "openmohaa.exe"), home, [PORT], minutes=30)
            cargs = ["+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", home,
                     "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", "960",
                     "+set", "r_customheight", "540", "+set", "r_fullscreen", "0", "+set", "name", name,
                     "+set", "logfile", "2", "+exec", "fl_c.cfg", "+connect", "127.0.0.1:%d" % PORT]
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
        while time.time() - t0 < 240:
            log = slog()
            joined = [n for _, _, _, n in clients if re.search(re.escape(n) + r" has (entered the battle|joined)", log)]
            if len(joined) == len(clients) and ("FLTEST players=2" in log or os.environ.get("FL_TESTMODE") == "3"):
                break
            for c, _, _, n in clients:
                if n not in joined:
                    c.post_key(VK_F9)
            time.sleep(6)
        print("joined:", joined, flush=True)
        # watch the self-test, grab client frames for the record
        t0, k = time.time(), 0
        while time.time() - t0 < 600 and "FLTEST end" not in slog() and "FLASSIST obj 5 done=1" not in slog():
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
    for tag in ("FLTEST", "FLASSIST", "FLUSE trigger", "FLOBJ", "FLCUE", "FLSET", "FLMISSION", "Script Error"):
        hits = re.findall(r"\^~\^~\^ " + tag + r"[^\n]*", log)
        print(tag, len(hits), hits[-7:])


if __name__ == "__main__":
    main(sys.argv[1])

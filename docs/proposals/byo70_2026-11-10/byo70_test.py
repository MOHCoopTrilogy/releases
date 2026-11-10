#!/usr/bin/env python3
"""v1.10.70 own-disc missions: exit + two-client coop matrix on PRIVATE clients (our code; nothing from a disc is in here).

Clients:  G:\\mohaa-byo70 (A) and G:\\mohaa-byo70b (B) - byte copies of the byo70-eng build (exe/cgame/game/renderers),
          basepath = the GOG tree read-only, homes inside their own folders (harness_guard classifies them HARNESS).
          Every client is started ONLY by harness_window.launch_background (test display picked by resolution, never
          focused, cursor/capture/audio guard ENFORCED, job object), muted, in_mouse 0, in_nograb 1, in_gamepad 0,
          in_joystick 0. Input = console binds posted to OUR window (post_key). No pad scripts.
Server:   G:\\mohaa-byo70\\omohaaded.exe with harness_window.popen_kwargs() (CREATE_NO_WINDOW: no console window at all,
          below-normal priority). Only PIDs this script started are ever stopped.
On ANY guard violation every launch stops and the run reports it.

  python byo70_test.py <case> [...]
    exit_fl_full exit_fl_chrono exit_ea_full exit_ea_chrono   listen server, 1 client: the mission's self-test walks the
                         objectives, then its REAL ending (coop_fltestExit/coop_eatestExit 1) hands over; the next map
                         the campaign loads is recorded (cheats + developer set on the command line)
    walk_fl              listen server: the Full Campaign from m4l3 into coop_fl_1_1 through the lobby (bug-10801 crash)
    coop2_fl coop2_fl_rescue coop2_ea   dedicated server + 2 clients: both join, the self-test walks the team through
                         every objective (rescue: the officer is shot in time -> Saving Private Castro)
    sp_absent_m4l3       SP on m4l3 without the paks (replace.scr:1975 Script Errors, bug-10804)
Results: H:\\hzm_work\\byo70-test\\runs\\<case>\\ (logs, result.json, png = LOCAL ONLY, never committed)."""
import json
import os
import re
import shutil
import subprocess
import sys
import time

TOOLS = r"C:\mohaa-coop-dev\docs\tools"
sys.path.insert(0, TOOLS)
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
A, B = r"G:\mohaa-byo70", r"G:\mohaa-byo70b"
SRVHOME = os.path.join(A, "srvhome")
RUNS = r"H:\hzm_work\byo70-test\runs"
PORT = 12271
RCONPW = "byo70t"
VK = {"F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}
TRIPPED = []
MUTE = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set con_notifytime -1", "set coop_joinCard 0",
        # the mod stufftexts "s_volume <coop_tinnitusBaseVol>" to every player on every spawn (player.scr spawn safety net) and
        # the tinnitus muffle sets fixed volumes: on a listen server these are this process's own cvars - keep them at 0
        # (the first run of this harness was killed by the audio guard at the first spawn, peak 0.012)
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0"]
JOIN = 'bind F9 "popmenu 0; wait 10; primarydmweapon rifle; wait 5; join_team allies; wait 30; popmenu 0; wait 30; popmenu 0"'


def home(folder, present=True):
    return os.path.join(folder, "home" if present else "home_absent")


def lp(h):
    return os.path.join(h, "maintt", "qconsole.log")


def read(path):
    try:
        return open(path, "rb").read().decode("latin-1")
    except OSError:
        return ""


def wait_for(path, pat, timeout, start=0, poll=None):
    t = time.time()
    while time.time() - t < timeout:
        if re.search(pat, read(path)[start:]):
            return True
        if poll:
            poll()
        if TRIPPED:
            return False
        time.sleep(1)
    return False


def guard(*clients):
    for c in clients:
        v = getattr(getattr(c, "watcher", None), "violations", None)
        if v:
            TRIPPED.append(repr(v))
        if c is not None and not c.alive() and not TRIPPED:
            pass
    return bool(TRIPPED)


def clean(h):
    mt = os.path.join(h, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.lower().endswith(".pid") or fn == "qconsole.log":
            os.remove(os.path.join(mt, fn))


def client(folder, h, sets, tail, cfg_lines, name):
    """one background client; sets = [(cvar, value)] that must be on the command line (latched: cheats, g_gametype ...)"""
    clean(h)
    mt = os.path.join(h, "maintt")
    base = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", h), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", "960"), ("r_customheight", "540"), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"), ("in_mouse", "0"),
            ("in_nograb", "1"), ("s_volume", "0"), ("name", name)] + list(sets)
    args = [os.path.join(folder, "openmohaa.exe")]
    for k, v in base:
        args += ["+set", k, v]
    args += ["+exec", "byo70_on.cfg"] + list(tail)
    d = hw.test_display()
    args, late = hw.apply_policy(args, width=960, height=540, display=d)
    open(os.path.join(mt, "byo70_on.cfg"), "w", newline="\n").write("\n".join(MUTE + [JOIN] + cfg_lines + late) + "\n")
    c = hw.launch_background(args[0], args[1:], folder, policy=False, display=d, below_normal=True, watch_audio=True,
                             log=lambda *a: None)
    return c


def join_until(c, logpath, name, timeout=300, start=0):
    """press F9 (team menu off, rifle, join allies) until the server log shows the player on a team"""
    t = time.time()
    while time.time() - t < timeout:
        s = read(logpath)[start:]
        if re.search(re.escape(name) + r" has joined the (Allies|Axis|American|German)", s, re.I):
            return True
        if "CS_ACTIVE for " + name in s or "entered the battle" in s or "Spawning Entities Done" in s:
            c.post_key(VK["F9"])
        if guard(c):
            return False
        time.sleep(6)
    return False


def script_errors(log):
    """Script Error count, and the files they come from (the line above each error names it)"""
    files = {}
    lines = log.splitlines()
    for i, l in enumerate(lines):
        if "Script Error" in l:
            f = "?"
            for j in range(i - 1, max(0, i - 6), -1):
                m = re.search(r"\(([^,()]+\.scr), (\d+)\)", lines[j])
                if m:
                    f = "%s:%s" % (m.group(1), m.group(2))
                    break
            files[f] = files.get(f, 0) + 1
    return sum(files.values()), files


def tags(log, pats):
    return {p: re.findall(r"\^~\^~\^ (" + p + r"[^\n]*)", log)[-8:] for p in pats}


# ----------------------------------------------------------------------------------------------------- exit (listen)
def case_exit(game, chrono, out, res):
    m = {"fl": "coop_fl_1_1", "ea": "coop_ea_1_11"}[game]
    want = "briefing/briefing5" if game == "fl" else "briefing/briefing2"
    h = home(A)
    t = game
    go = ["set coop_%stest 1" % t, "set coop_%stestPlayers 1" % t, "set coop_%stestExit 1" % t, "set coop_dbno 0",
          "set ui_dmmap %s" % m, "exec coop_mod/start_server.cfg", "set coop_campaign 1",
          "set coop_campaignChrono %d" % (1 if chrono else 0), 'set coop_campaignNext ""', "set coop_chronoTest 1",
          "set coop_%stest 1" % t, "set coop_%stestPlayers 1" % t, "set coop_%stestExit 1" % t]
    open(os.path.join(h, "maintt", "byo70_go.cfg"), "w", newline="\n").write("\n".join(go) + "\n")
    sets = [("g_gametype", "2"), ("cheats", "1"), ("thereisnomonkey", "1"), ("net_port", str(PORT)),
            ("rconpassword", RCONPW), ("coop_dev", "1")]
    c = client(A, h, sets, ["+exec", "byo70_go.cfg"], [], "BYO_Alpha")
    L = lp(h)
    with c:
        res["loaded"] = wait_for(L, r"Server: " + re.escape(m), 240) and wait_for(L, r"Spawning Entities Done", 400)
        res["joined"] = join_until(c, L, "BYO_Alpha", 400)
        tag = "FL" if game == "fl" else "EA"
        res["mission_complete"] = wait_for(L, tag + "MISSION complete", 1500, poll=lambda: guard(c))
        try:
            c.capture_png(os.path.join(out, "mission_complete.png"))
        except Exception:
            pass
        n = read(L).find(tag + "MISSION complete")
        res["next_loaded"] = wait_for(L, r"Server: (?!" + re.escape(m) + r")\S+", 240, n)
        nxt = re.findall(r"Server: (\S+)", read(L)[n:])
        res["next_maps"] = nxt[:3]
        wait_for(L, r"Spawning Entities Done", 240, n)
        time.sleep(8)
        try:
            c.capture_png(os.path.join(out, "next_map.png"))
        except Exception:
            pass
        guard(c)
    log = read(L)
    res["want_next"] = want
    # a campaign may pass through the loading lobby first (chrono); the mission that follows is what counts
    res["ok"] = bool(res["next_maps"]) and want in res["next_maps"][:2]
    res["tags"] = tags(log, [tag + "TEST", tag + "OBJ", tag + "MISSION", "BYO_NEXT", "CHRONO_MAP", "CHRONO_NEXT",
                             "CHRONO_SAVE", "COOP_CAMPAIGN", "FLCHAL", "CLPARSE"])
    res["crash"] = re.findall(r"Server crashed[^\n]*|tried to parse cg message[^\n]*", log)[:3]
    shutil.copyfile(L, os.path.join(out, "qconsole.log"))
    return log


# ----------------------------------------------------------------------------------------------- walk (listen, lobby)
def rcon(cmd):
    import socket
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sk.sendto(b"\xff\xff\xff\xff\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
    sk.close()


def case_walk(out, res):
    """Full Campaign m4l3 -> briefingfl1 -> co_lobby1 -> coop_fl_1_1; the lobby is launched AS SOON AS the client finished
    loading it (the byo69 crash timing), so the stale-cg-message fix is exercised; the run must reach coop_fl_1_1 alive"""
    h = home(A)
    open(os.path.join(h, "maintt", "byo70_go.cfg"), "w", newline="\n").write("\n".join(
        ["set ui_dmmap m4l3", "exec coop_mod/start_server.cfg", "set coop_campaign 1", "set coop_chronoTest 1",
         "set coop_campaignChrono 0", 'set coop_campaignNext ""']) + "\n")
    sets = [("g_gametype", "2"), ("cheats", "1"), ("net_port", str(PORT)), ("rconpassword", RCONPW), ("coop_dev", "1")]
    c = client(A, h, sets, ["+exec", "byo70_go.cfg"], [], "BYO_Alpha")
    L = lp(h)
    seq = []
    with c:
        n = 0
        while len(seq) < 6:
            t = time.time()
            got = None
            while time.time() - t < 400 and got is None:
                mm = re.findall(r"CHRONO_MAP (\S+)", read(L)[n:])
                if mm:
                    got = mm[0]
                    n = read(L).index("CHRONO_MAP " + got, n) + 5
                time.sleep(1)
                if guard(c) or not c.alive():
                    break
            if got is None:
                break
            seq.append(got)
            if got == "coop_fl_1_1":
                break
            # wait for the CLIENT to finish loading this map (CL_InitCGame), then end it at once
            wait_for(L, r"CL_InitCGame: [\d.]+ seconds", 300, n)
            for _ in range(4):
                rcon("set coop_chronoTestEnd 1")
                if wait_for(L, "CHRONO_TESTEND " + re.escape(got), 30, n):
                    break
        if seq and seq[-1] == "coop_fl_1_1":
            k = read(L).find("CHRONO_MAP coop_fl_1_1")
            res["fl_cgame"] = wait_for(L, r"CL_InitCGame: [\d.]+ seconds", 300, k)
            time.sleep(10)
            res["alive_after"] = c.alive()
            try:
                c.capture_png(os.path.join(out, "walk_fl.png"))
            except Exception:
                pass
        guard(c)
    log = read(L)
    res["maps"] = seq
    res["crash"] = re.findall(r"Server crashed[^\n]*|tried to parse cg message[^\n]*", log)[:3]
    res["clparse_dropped"] = len(re.findall(r"CLPARSE stale cg message dropped", log))
    res["ok"] = seq == ["m4l3", "briefing/briefingfl1", "co_lobby1", "coop_fl_1_1"] and not res["crash"]
    shutil.copyfile(L, os.path.join(out, "qconsole.log"))
    return log


# --------------------------------------------------------------------------------------------- two clients, dedicated
def case_coop2(game, rescue, out, res):
    m = {"fl": "coop_fl_1_1", "ea": "coop_ea_1_11"}[game]
    t = game
    T = t.upper()
    clean(SRVHOME)
    SL = lp(SRVHOME)
    args = [os.path.join(A, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", SRVHOME, "+set", "dedicated", "1", "+set", "net_port", str(PORT),
            "+set", "net_ip", "127.0.0.1", "+set", "sv_maxclients", "4", "+set", "g_gametype", "2",
            "+set", "logfile", "2", "+set", "developer", "1", "+set", "cheats", "1",
            "+set", "coop_%stest" % t, "1", "+set", "coop_%stestPlayers" % t, "2",
            "+set", "coop_fltestRescue", "1" if rescue else "0",
            "+set", "coop_joinCard", "0", "+set", "coop_dbno", "0", "+set", "g_teamswitchdelay", "0",
            "+set", "rconpassword", RCONPW, "+exec", "byo70_srv.cfg", "+map", m]
    # after autoexec (which seta's coop_tinnitusBaseVol 0.9): what the server stufftexts to the clients' s_volume
    open(os.path.join(SRVHOME, "maintt", "byo70_srv.cfg"), "w", newline="\n").write("set coop_tinnitusBaseVol 0\nset coop_tinnitusMuffle 0\n")
    srv = subprocess.Popen(args, **hw.popen_kwargs())
    res["server_pid"] = srv.pid
    cl = []
    try:
        wait_for(SL, T + "AI ", 400)
        for folder, name in ((A, T + "_Alpha"), (B, T + "_Bravo")):
            h = home(folder)
            c = client(folder, h, [("cheats", "1")], ["+connect", "127.0.0.1:%d" % PORT], [], name)
            cl.append((c, name))
            time.sleep(20)
            if guard(c):
                return read(SL)
        t0 = time.time()
        joined = []
        while time.time() - t0 < 900:
            s = read(SL)
            joined = [n for _, n in cl if re.search(re.escape(n) + r" has joined the (Allies|American)", s, re.I)]
            if len(joined) == 2 and (T + "TEST players=2") in s:
                break
            for c, n in cl:
                if n not in joined and ("to CS_ACTIVE for " + n) in s:
                    c.post_key(VK["F9"])
            if guard(*[c for c, _ in cl]):
                return read(SL)
            time.sleep(6)
        res["joined"] = joined
        k = 0
        t0 = time.time()
        while time.time() - t0 < 1500 and (T + "TEST end") not in read(SL):
            if k % 4 == 0:
                for c, n in cl:
                    try:
                        c.capture_png(os.path.join(out, "%s_%03d.png" % (n, k)))
                    except Exception:
                        pass
            k += 1
            if guard(*[c for c, _ in cl]):
                break
            if srv.poll() is not None:
                res["server_died"] = srv.returncode
                break
            time.sleep(5)
        wait_for(SL, T + "MISSION complete", 30)
        time.sleep(5)
        for c, n in cl:
            try:
                c.capture_png(os.path.join(out, "%s_end.png" % n))
            except Exception:
                pass
        res["clients_alive"] = [c.alive() for c, _ in cl]
    finally:
        for c, n in cl:
            try:
                c.close()
            except Exception:
                try:
                    c.proc.kill()
                except Exception:
                    pass
        if srv.poll() is None:
            srv.kill()
        if os.path.exists(SL):
            shutil.copyfile(SL, os.path.join(out, "server_qconsole.log"))
        for c, n in cl:
            p = lp(home(A if n.endswith("Alpha") else B))
            if os.path.exists(p):
                shutil.copyfile(p, os.path.join(out, "%s_qconsole.log" % n))
    log = read(SL)
    res["tags"] = tags(log, [T + "TEST", T + "OBJ", T + "MISSION", T + "SET", T + "CUE", T + "TANK", T + "CHARGE",
                             T + "KIT", "FLRESCUE", "FLCHAL", "FLSHOOT", "EAMUSIC", "EAPROPS", T + "AI"])
    res["objectives"] = re.findall(r"\^~\^~\^ " + T + r"OBJ (\d+) done", log)
    res["mission_complete"] = (T + "MISSION complete") in log
    res["chal_award"] = "FLCHAL saving_private_castro awarded" in log
    # the per-client challenge record (chal_apply -> chal_grant) prints the title on the client HUD; the server logs the grant
    res["chal_grant_lines"] = re.findall(r"[^\n]*Saving Private Castro[^\n]*", log)[:4]
    res["ok"] = res["mission_complete"] and len(res.get("joined", [])) == 2 and (not rescue or res["chal_award"])
    return log


# ------------------------------------------------------------------------------------------------- SP no-pak m4l3
def case_sp_absent(out, res):
    h = home(A, present=False)
    sets = [("g_gametype", "0"), ("cheats", "1"), ("net_port", str(PORT))]
    c = client(A, h, sets, ["+map", "m4l3"], [], "BYO_Alpha")
    L = lp(h)
    with c:
        res["loaded"] = wait_for(L, r"Spawning Entities Done", 300)
        time.sleep(30)
        guard(c)
    log = read(L)
    shutil.copyfile(L, os.path.join(out, "qconsole.log"))
    return log


def main(cases):
    os.makedirs(RUNS, exist_ok=True)
    for case in cases:
        if TRIPPED:
            print("GUARD TRIPPED - stopping all launches:", TRIPPED, flush=True)
            break
        if hg.user_game_running_raw():
            print("a USER-class MOHAA client is running - not launching", flush=True)
            break
        out = os.path.join(RUNS, case)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        res = {"case": case, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        hg.acquire_slot("byo70", os.path.join(A, "openmohaa.exe"), home(A), [PORT], minutes=60)
        hg.acquire_slot("byo70b", os.path.join(B, "openmohaa.exe"), home(B), [PORT], minutes=60)
        try:
            if case.startswith("exit_"):
                _, g, mode = case.split("_")
                log = case_exit(g, mode == "chrono", out, res)
            elif case == "walk_fl":
                log = case_walk(out, res)
            elif case.startswith("coop2_"):
                log = case_coop2(case.split("_")[1], case.endswith("rescue"), out, res)
            elif case == "sp_absent_m4l3":
                log = case_sp_absent(out, res)
            else:
                raise SystemExit("unknown case " + case)
        finally:
            hg.release_slot("byo70")
            hg.release_slot("byo70b")
        res["script_errors"], res["script_error_sites"] = script_errors(log)
        res["needs_alias"] = sorted(set(re.findall(r"(\S+) needs an alias", log)))[:30]
        res["guard"] = TRIPPED[:]
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
        print(case, json.dumps(res), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])

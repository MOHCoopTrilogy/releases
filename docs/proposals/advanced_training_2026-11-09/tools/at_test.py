#!/usr/bin/env python3
"""Advanced Training on m4l0 - boot, maptest and course matrix on PRIVATE clients.        [advtrain 2026-11-10]

Clients:  G:\\mohaa-advtrain (A) and G:\\mohaa-advtrainb (B): byte copies of the LIVE G:\\mohaa-gl2 exe/DLLs (read only),
          basepath = the GOG tree read-only, fresh homes inside their own folders (harness_guard: owner "advtrain").
          The branch code = ONE override pk3 (zzzzzzzzzzzzzzzzzzzzzzzz_advtrain.pk3) built from the mod worktree's diff
          against hotfix-1.10.53 into each home - nothing is deployed anywhere else.
          Every client is started ONLY by harness_window.launch_background (test display by resolution, never focused,
          cursor/capture/audio guard ENFORCED, job object), muted, in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0,
          and after autoexec coop_tinnitusBaseVol 0 / coop_tinnitusMuffle 0 / coop_woundMuffleVol 0 (TRAPS T14, bug-10805).
          Input = console binds posted to OUR window. No pad scripts.
Server:   omohaaded.exe with harness_window.popen_kwargs() (CREATE_NO_WINDOW, below normal). Only PIDs started here stop.
On ANY guard violation every launch stops and the run reports it.

  python at_test.py pak                    build the override pk3 into every home
  python at_test.py boot_at boot_raid      dedicated, no client: script parse + coop init + the branch (ATRAIN branch on)
  python at_test.py maptest_raid           listen, 1 client, coop_maptest 1 on m4l0 (the raid: the m4l0.scr edits regress nothing)
  python at_test.py solo                   listen, 1 client, coop_atSelftest 1: the whole course; a still after each warp
  python at_test.py coop2                  dedicated + 2 clients, coop_atSelftest 1: the whole course in coop
  python at_test.py views                  listen, 1 client, no self-test: a still of every station as a trainee sees it
Results: H:\\hzm_work\\advtrain-test\\runs\\<case>\\ (logs, result.json, png - LOCAL ONLY, never committed)."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools"))
sys.path.insert(0, TOOLS)
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
A, B = r"G:\mohaa-advtrain", r"G:\mohaa-advtrainb"
SRVHOME = os.path.join(A, "srvhome")
MOD = r"H:\hzm_work\advtrain-mod"
BASE_REF = "hotfix-1.10.53"
RUNS = r"H:\hzm_work\advtrain-test\runs"
PAK = "zzzzzzzzzzzzzzzzzzzzzzzz_advtrain.pk3"
PORT = 12281
RCONPW = "advt"
VK = {"F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A}
TRIPPED = []
MUTE = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set con_notifytime -1", "set coop_joinCard 0",
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0"]
HUDKEYS = ['bind F6 "cg_draw2d 0; cg_drawviewmodel 0"', 'bind F7 "cg_draw2d 1; cg_drawviewmodel 1"']
JOIN = ('bind F9 "popmenu 0; wait 10; primarydmweapon rifle; wait 5; join_team allies; wait 30; popmenu 0; wait 30; '
        'popmenu 0; +attackprimary; wait 10; -attackprimary"')
SRVCFG = ["set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0", "set developer 1",
          "set thereisnomonkey 1", "set cheats 1"]


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


import ctypes  # noqa: E402
_U32 = ctypes.WinDLL("user32", use_last_error=True)
USER_EXE = r"G:\mohaa-gl2\openmohaa.exe"
FOREIGN = []        # violations judged NOT ours (logged in result.json, never a stop)


def user_game_running():
    """the user own MOHAA (G:/mohaa-gl2) - checked before EVERY launch; while it runs, tests go to the 1080p screen"""
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_Process -Filter \"Name='openmohaa.exe'\").ExecutablePath"],
                         capture_output=True, text=True).stdout.lower()
    return USER_EXE.lower() in out


def pick_screen():
    if user_game_running():
        os.environ["HZM_TEST_RES"] = "1920x1080"
        return "1080p (user game running)"
    os.environ["HZM_TEST_RES"] = "1920x1080"     # the user games on the ultrawide: stay off it all session
    return "1080p"


def _fg_pid():
    h = _U32.GetForegroundWindow()
    pid = ctypes.c_ulong(0)
    _U32.GetWindowThreadProcessId(h, ctypes.byref(pid))
    return pid.value


def guard(*clients):
    """LOCAL judgement on top of harness_window's watcher (launched with enforce=False; the shared module is untouched):
    a cursor clip counts as OURS only when our window is foreground (the watcher already requires the clip rect to lie
    inside one of our windows - and a centred test window on the ultrawide contains the screen centre, where the user's
    own game clips, which is how coop2 attempt 2 was stopped). Every other kind - foreground theft, capture, audible,
    off-display, guard missing - is ours: the client is killed and every launch stops."""
    for c in clients:
        w = getattr(c, "watcher", None)
        vs = getattr(w, "violations", None) or []
        seen = getattr(c, "_at_seen", 0)
        for v in vs[seen:]:
            if v.get("kind") == "cursor_clip" and _fg_pid() != c.pid:
                FOREIGN.append(dict(v, judged="foreign: our window not foreground"))
                continue
            TRIPPED.append(repr(v))
        c._at_seen = len(vs)
    if TRIPPED:
        for c in clients:
            try:
                if c.alive():
                    k = ctypes.WinDLL("kernel32").OpenProcess(1, False, c.pid)
                    ctypes.WinDLL("kernel32").TerminateProcess(k, 1)
            except Exception:  # noqa: BLE001
                pass
    return bool(TRIPPED)


def clean(h):
    mt = os.path.join(h, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.lower().endswith(".pid") or fn == "qconsole.log":
            os.remove(os.path.join(mt, fn))


def build_pak():
    """the branch's changed + new files (vs hotfix-1.10.53) + the build-local Service Record pages, as one stored zip"""
    # against the MERGE-BASE, never the moving branch tip: hotfix-1.10.53 keeps receiving release commits, and a diff to
    # its tip would pack their files backwards into the override
    mb = subprocess.run(["git", "-C", MOD, "merge-base", "HEAD", BASE_REF], capture_output=True, text=True).stdout.strip()
    ch = subprocess.run(["git", "-C", MOD, "diff", "--name-only", mb], capture_output=True, text=True).stdout.split()
    un = subprocess.run(["git", "-C", MOD, "ls-files", "--others", "--exclude-standard"], capture_output=True,
                        text=True).stdout.split()
    files = sorted(set(f for f in ch + un if os.path.isfile(os.path.join(MOD, f))))
    sr = os.path.join(MOD, "textures", "mohmenu")
    files += sorted("textures/mohmenu/" + f for f in os.listdir(sr) if f.startswith("coop_sr_") and f.endswith(".tga"))
    for h in (os.path.join(A, "home"), os.path.join(B, "home"), SRVHOME):
        mt = os.path.join(h, "maintt")
        os.makedirs(mt, exist_ok=True)
        with zipfile.ZipFile(os.path.join(mt, PAK), "w", zipfile.ZIP_STORED) as z:
            for f in files:
                z.write(os.path.join(MOD, f), f)
    print("pak: %d files -> %s" % (len(files), PAK))
    return files


def client(folder, h, sets, tail, cfg_lines, name, size=(960, 540)):
    clean(h)
    mt = os.path.join(h, "maintt")
    base = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", h), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(size[0])), ("r_customheight", str(size[1])), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"), ("in_mouse", "0"),
            ("in_nograb", "1"), ("s_volume", "0"), ("name", name)] + list(sets)
    args = [os.path.join(folder, "openmohaa.exe")]
    for k, v in base:
        args += ["+set", k, v]
    args += ["+exec", "at_on.cfg"] + list(tail)
    print("screen:", pick_screen())
    d = hw.test_display()
    args, late = hw.apply_policy(args, width=size[0], height=size[1], display=d)
    open(os.path.join(mt, "at_on.cfg"), "w", newline="\n").write("\n".join(MUTE + [JOIN] + HUDKEYS + cfg_lines + late) + "\n")
    return hw.launch_background(args[0], args[1:], folder, policy=False, display=d, below_normal=True, watch_audio=True,
                                enforce=False, log=lambda *a: None)


def server(sets, mapname):
    clean(SRVHOME)
    open(os.path.join(SRVHOME, "maintt", "at_srv.cfg"), "w", newline="\n").write("\n".join(SRVCFG) + "\n")
    args = [os.path.join(A, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", SRVHOME, "+set", "dedicated", "1", "+set", "net_port", str(PORT),
            "+set", "net_ip", "127.0.0.1", "+set", "sv_maxclients", "4", "+set", "g_gametype", "2",
            "+set", "logfile", "2", "+set", "developer", "1", "+set", "cheats", "1", "+set", "coop_joinCard", "0",
            "+set", "rconpassword", RCONPW, "+set", "g_inactiveSpectate", "0", "+set", "g_inactivekick", "0"]
    # idle harness clients were moved to spectator after 60 s (coop2 run 1: every station from 5 on counted 0/0)
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "at_srv.cfg", "+map", mapname]
    return subprocess.Popen(args, **hw.popen_kwargs())


def join_until(c, logpath, name, timeout=300, start=0):
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


def errors(log):
    out = {"script_errors": 0, "files": {}, "compile": [], "notloaded": []}
    lines = log.splitlines()
    for i, l in enumerate(lines):
        if "Script Error" in l or "^~^~^ Script Error" in l:
            out["script_errors"] += 1
            ctx = " ".join(lines[max(0, i - 2):i + 3])
            m = re.search(r"\(([\w/]+\.scr), (\d+)\)", ctx)
            k = "%s:%s" % (m.group(1), m.group(2)) if m else "?"
            out["files"][k] = out["files"].get(k, 0) + 1
        if "Couldn't compile" in l or "parse error" in l.lower():
            out["compile"].append(l.strip()[:200])
        if "not properly loaded" in l:
            out["notloaded"].append(l.strip()[:200])
    out["compile"] = out["compile"][:10]
    out["notloaded"] = sorted(set(out["notloaded"]))[:10]
    return out


def atrain(log):
    return [l.strip()[:220] for l in log.splitlines() if "ATRAIN" in l and "^~^~^" in l]


# ---------------------------------------------------------------------------------------------------------- cases
def case_boot(at, out, res):
    srv = server([("coop_advTraining", "1" if at else "0")], "m4l0")
    try:
        res["loaded"] = wait_for(lp(SRVHOME), r"Spawning Entities Done", 300)
        time.sleep(25)
    finally:
        if srv.poll() is None:
            srv.kill()
    log = read(lp(SRVHOME))
    shutil.copyfile(lp(SRVHOME), os.path.join(out, "server_qconsole.log"))
    res.update(errors(log))
    res["atrain"] = atrain(log)
    res["branch_on"] = "ATRAIN branch on" in log
    res["ok"] = res["loaded"] and not res["compile"] and not res["notloaded"] and (res["branch_on"] == at)
    return log


def go_listen(h, extra, name="AT_Alpha", size=(960, 540), binds=None):
    go = extra + ["set ui_dmmap m4l0", "set coop_campaign 0", "exec coop_mod/start_server.cfg"]
    open(os.path.join(h, "maintt", "at_go.cfg"), "w", newline="\n").write("\n".join(go) + "\n")
    sets = [("g_gametype", "2"), ("cheats", "1"), ("thereisnomonkey", "1"), ("net_port", str(PORT)),
            ("rconpassword", RCONPW), ("coop_dev", "1"), ("g_inactiveSpectate", "0"), ("g_inactivekick", "0")]
    return client(A, h, sets, ["+exec", "at_go.cfg"], ['bind F5 "echo ATVOL; s_volume"'] + (binds or []), name, size)


def shoot(c, out, tag):
    try:
        c.capture_png(os.path.join(out, tag + ".png"))
    except Exception as e:  # noqa: BLE001
        print("capture failed", tag, e)


def case_maptest_raid(out, res):
    h = os.path.join(A, "home")
    clean(h)
    c = go_listen(h, ["set coop_advTraining 0", "set coop_maptest 1", "set coop_maptest_dwell 40"])
    L = lp(h)
    with c:
        res["loaded"] = wait_for(L, r"Spawning Entities Done", 400)
        res["joined"] = join_until(c, L, "AT_Alpha", 300)
        res["maptest_loaded"] = wait_for(L, r"MAPTEST_LOADED m4l0", 200, poll=lambda: guard(c))
        time.sleep(20)
        shoot(c, out, "raid")
        res["maptest_next"] = wait_for(L, r"Server: (?!m4l0)\S+", 120, poll=lambda: guard(c))
        guard(c)
    log = read(L)
    shutil.copyfile(L, os.path.join(out, "qconsole.log"))
    n = log.find("Server: m4l0")
    seg = log[n:log.find("Server:", n + 10)] if n >= 0 else log
    res.update(errors(seg))
    res["atrain_in_raid"] = len(atrain(seg))
    res["ok"] = bool(res["maptest_loaded"]) and not res["compile"] and res["atrain_in_raid"] == 0 and not TRIPPED
    return log


def watch_course(c, L, out, res, timeout, others=()):
    """stills after each station warp, until course_complete"""
    seen = set()
    t0 = time.time()
    while time.time() - t0 < timeout:
        log = read(L)
        for m in re.finditer(r"ATRAIN station st=(\d+) pos=(\d+)", log):
            k = m.group(1)
            if k not in seen:
                seen.add(k)
                time.sleep(4)
                c.post_key(VK["F6"])
                time.sleep(1.5)
                shoot(c, out, "st%02d_clean" % int(k))
                c.post_key(VK["F7"])
                time.sleep(2)
                shoot(c, out, "st%02d_a" % int(k))
                for i, o in enumerate(others):
                    shoot(o, out, "st%02d_%s" % (int(k), "b"))
                if k == "9":
                    time.sleep(14)
                    c.post_key(VK["F6"])
                    time.sleep(1)
                    shoot(c, out, "st09_strike")
                    c.post_key(VK["F7"])
        if "ATRAIN course_complete" in log:
            time.sleep(25)
            shoot(c, out, "end")
            return True
        if guard(c, *others):
            return False
        time.sleep(2)
    return False


def case_solo(out, res, selftest=True):
    h = os.path.join(A, "home")
    clean(h)
    extra = ["set coop_advTraining 1", "set coop_atDebug 1", "set coop_atTimeout 150"]
    if selftest:
        extra.append("set coop_atSelftest 1")
    c = go_listen(h, extra)
    L = lp(h)
    with c:
        res["loaded"] = wait_for(L, r"Spawning Entities Done", 400)
        res["joined"] = join_until(c, L, "AT_Alpha", 300)
        res["complete"] = watch_course(c, L, out, res, 2400 if selftest else 900)
        c.post_key(VK["F5"])
        time.sleep(2)
        guard(c)
    log = read(L)
    shutil.copyfile(L, os.path.join(out, "qconsole.log"))
    res.update(errors(log))
    res["atrain"] = atrain(log)
    res["vol"] = re.findall(r'"s_volume" is:"([^"]*)', log)[-3:]
    res["ok"] = bool(res["complete"]) and not res["compile"] and not TRIPPED
    return log


def case_coop2(out, res):
    srv = server([("coop_advTraining", "1"), ("coop_atSelftest", "1"), ("coop_atDebug", "1"), ("coop_atTimeout", "150")],
                 "m4l0")
    SL = lp(SRVHOME)
    ha, hb = os.path.join(A, "home"), os.path.join(B, "home")
    try:
        res["server_loaded"] = wait_for(SL, r"Spawning Entities Done", 400)
        ca = client(A, ha, [("cheats", "1")], ["+connect", "127.0.0.1:%d" % PORT], [], "AT_Alpha")
        with ca:
            res["a_joined"] = join_until(ca, SL, "AT_Alpha", 400)
            cb = client(B, hb, [("cheats", "1")], ["+connect", "127.0.0.1:%d" % PORT], [], "AT_Bravo")
            with cb:
                res["b_joined"] = join_until(cb, SL, "AT_Bravo", 400)
                res["complete"] = watch_course(ca, SL, out, res, 2700, others=(cb,))
                guard(ca, cb)
    finally:
        if srv.poll() is None:
            srv.kill()
        for src, dst in ((SL, "server_qconsole.log"), (lp(ha), "a_qconsole.log"), (lp(hb), "b_qconsole.log")):
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(out, dst))
    log = read(SL)
    res.update(errors(log))
    res["atrain"] = atrain(log)
    res["ok"] = bool(res.get("complete")) and not res["compile"] and not TRIPPED
    return log


def case_tilesrc(out, res):
    """a clean 1920x1080 frame of the range (HUD, gun and feed off) - the source for the Advanced Training tile art"""
    h = os.path.join(A, "home")
    clean(h)
    # Dig in (course position 6): no vote gate (its ready HUD draws even with cg_draw2d 0), the farm on the hill behind
    # the bag wall; the feed lines are left 35 s to fade before the frame
    pos = os.environ.get("AT_TILE_POS", "6")
    c = go_listen(h, ["set coop_advTraining 1", "set coop_atStation " + pos, "set coop_atTimeout 600"], size=(1920, 1080),
                  binds=['bind F6 "cg_draw2d 0; cg_drawviewmodel 0; ui_hud 0"'])
    L = lp(h)
    with c:
        res["loaded"] = wait_for(L, r"Spawning Entities Done", 400)
        res["joined"] = join_until(c, L, "AT_Alpha", 300)
        res["range"] = wait_for(L, r"ATRAIN prop st7 mg42" if pos == "6" else r"ATRAIN prop st3 models/static/haystack", 200,
                                poll=lambda: guard(c))
        time.sleep(35 if pos == "6" else 12)
        shoot(c, out, "range_hud")
        c.post_key(VK["F6"])
        time.sleep(3)
        shoot(c, out, "range_clean")
        guard(c)
    shutil.copyfile(L, os.path.join(out, "qconsole.log"))
    res["ok"] = bool(res["range"]) and not TRIPPED
    return read(L)


def main():
    cases = sys.argv[1:] or ["boot_at"]
    os.makedirs(RUNS, exist_ok=True)
    for case in cases:
        if TRIPPED:
            print("GUARD TRIPPED - no further launches:", TRIPPED)
            break
        if case == "pak":
            build_pak()
            continue
        out = os.path.join(RUNS, case)
        shutil.rmtree(out, ignore_errors=True)
        os.makedirs(out)
        res = {"case": case, "t": time.strftime("%Y-%m-%d %H:%M:%S")}
        t0 = time.time()
        try:
            if case == "boot_at":
                case_boot(True, out, res)
            elif case == "boot_raid":
                case_boot(False, out, res)
            elif case == "maptest_raid":
                case_maptest_raid(out, res)
            elif case == "solo":
                case_solo(out, res, True)
            elif case == "views":
                case_solo(out, res, False)
            elif case == "tilesrc":
                case_tilesrc(out, res)
            elif case == "coop2":
                case_coop2(out, res)
            else:
                print("unknown case", case)
                continue
        except hw.PolicyError as e:
            res["policy_error"] = str(e)
        res["secs"] = int(time.time() - t0)
        res["tripped"] = TRIPPED
        res["foreign"] = FOREIGN[:20]
        json.dump(res, open(os.path.join(out, "result.json"), "w"), indent=1)
        print(json.dumps({k: v for k, v in res.items() if k != "atrain"}, indent=1)[:3000])
    return 1 if TRIPPED else 0


if __name__ == "__main__":
    sys.exit(main())

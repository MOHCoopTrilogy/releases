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
# one harness for both BYO pilots: HZM_GAME=fl (default) or ea picks the private client, owner and port
GAME = os.environ.get("HZM_GAME", "fl")
CLIENT = {"fl": r"G:\mohaa-frontline", "ea": r"G:\mohaa-ea", "ea2": r"G:\mohaa-ea2"}[os.environ.get("HZM_CLIENT", GAME)]
EXE = os.path.join(CLIENT, "openmohaa.exe")
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
OWNER = {"fl": "frontline", "ea": "ea", "ea2": "ea2"}[os.environ.get("HZM_CLIENT", GAME)]
PORT = {"fl": 12295, "ea": 12395, "ea2": 12397}[os.environ.get("HZM_CLIENT", GAME)]
RCONPW = "flpilot"
MAGIC = b"\xff\xff\xff\xff"
H = {"c": None}


def test_display(slot=True):
    """user 2026-11-08: test windows go on the 34" ULTRAWIDE, picked by its RESOLUTION (3440x1440), never by the
    primary flag or the device name (the primary is now a 3840x2160 TV and names renumber)"""
    for m in hw.monitors():
        r = m["rect"]
        want = tuple(int(v) for v in os.environ.get("HZM_TEST_RES", "3440x1440").lower().split("x"))   # 1920x1080 = 2nd screen
        if (r[2] - r[0], r[3] - r[1]) == want:
            # shared display (H:\hzm_work\DISPLAY_QUEUE.md): FL_SLOT=A|B tiles our window into the left/right
            # 1720x1440 half so concurrent test clients never overlap
            slot = os.environ.get("FL_SLOT", "").upper() if slot else ""
            # DISPLAY_QUEUE.md 2026-11-09: three 1146-wide slots A|B|C (FL_SLOTS=2 keeps the old 1720 halves)
            nslots = int(os.environ.get("FL_SLOTS", "3"))
            if slot in ("A", "B", "C")[:nslots]:
                m = dict(m)
                sw = (r[2] - r[0]) // nslots
                x0 = r[0] + sw * "ABC".index(slot)
                m["rect"] = (x0, r[1], x0 + sw, r[3])
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
    # the guard needs the REAL monitor (a slot rect would make the ultrawide itself an 'other display')
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log, display=test_display(slot=False),
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


def patrol(mapname, outdir, renderer="opengl2", w=1100, h=620):
    """teleport patrol (EA: coop_eatest 2): the map script teleports player 1 over every placement and logs
    <TAG>PATROL i ok|fell|stuck; this only launches, joins (no noclip), waits for '<TAG>PATROL end' and keeps the log"""
    tag = {"fl": "FL", "ea": "EA"}[GAME]
    os.makedirs(outdir, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        c = launch(mapname, renderer, False, w=w, h=h,
                   extra_sets=["set coop_%stest 2" % tag.lower(), "set coop_health 20000", "set coop_dbno 0"])
        with c:
            if not wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 300):
                raise RuntimeError("map never loaded")
            time.sleep(8)
            join()
            step(["popmenu 0", "wait 5", "god", "wait 5", "notarget", "wait 5"])
            m = wait_log(tag + r"PATROL end[^\n]*", 900)
            log("patrol:", m.group(0) if m else "NO END LINE")
            shutil.copyfile(LOG, os.path.join(outdir, "qconsole.log"))
    finally:
        hg.release_slot(OWNER)


def cardfps(mapname, views, outdir, w, h, renderer="opengl2"):
    """join card + fps: launch at w x h with the join card on, screenshot while the card is up, then at each view
    run 'timerefresh' (128 frames over a full turn; the engine prints the fps) and screenshot. Run SOLO for fps."""
    os.makedirs(outdir, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        c = launch(mapname, renderer, False, w=w, h=h,
                   extra_sets=["set coop_joinCard 1", "set fps 1", "set com_maxfps 0", "set r_swapInterval 0", "set com_maxfpsUnfocused 0"])   # fps 1 = on-screen counter (Frontline recipe; this engine has no timerefresh)
        with c:
            if not wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 300):
                raise RuntimeError("map never loaded")
            start = len(read_log())
            # the card is up only while the client SPECTATES (before join, joincard.scr part 2) and types its lines in
            # over ~20 s. Frames on the wall clock at ~1, 6, 12 and 20 s after the first JC send: 'wait N' counts
            # frames, and at 400+ fps uncapped the old frame waits fired all four shots in 2 s, after the join.
            if not wait_log(r"\^~\^~\^ JC send", 120, start):
                log("cardfps: no JC send line (coop_joinCard off?)")
            t0 = time.time()
            for k, at in zip("abcd", (1, 6, 12, 20)):
                time.sleep(max(0, t0 + at - time.time()))
                step(["popmenu 0", "wait 2", "screenshot card_%dx%d_%s" % (w, h, k)], timeout=60)
            join()
            time.sleep(10)
            step(["popmenu 0", "wait 5", "god", "wait 5", "notarget", "wait 5"])
            for name, v in views.items():
                x, y, z = v["pos"]
                p, yaw = v["ang"][0], v["ang"][1]
                step(["popmenu 0", "set thereisnomonkey 1", "set cheats 1", "tele %.1f %.1f %.1f" % (x, y, z), "wait 5",
                      "face %.1f %.1f 0" % (p, yaw), "wait 120", "echo FPSVIEW " + name, "timerefresh", "wait 10",
                      "screenshot fps_%s" % name, "wait 20"], timeout=300)
            time.sleep(3)
            sd = os.path.join(MAINTT, "screenshots")
            for fn in os.listdir(sd):
                if fn.startswith(("card_", "fps_")):
                    shutil.move(os.path.join(sd, fn), os.path.join(outdir, fn))
            shutil.copyfile(LOG, os.path.join(outdir, "qconsole.log"))
            txt = read_log()[start:]
            for m in re.finditer(r"FPSVIEW (\S+)[\s\S]*?([\d.]+) seconds \(([\d.]+) fps\)", txt):
                log("fps", m.group(1), m.group(3))
    finally:
        hg.release_slot(OWNER)


if __name__ == "__main__" and sys.argv[1] == "cardfps":
    cardfps(sys.argv[2], json.load(open(sys.argv[3])), sys.argv[4], int(sys.argv[5]), int(sys.argv[6]))
if __name__ == "__main__" and sys.argv[1] == "patrol":
    patrol(sys.argv[2], sys.argv[3])
if __name__ == "__main__" and sys.argv[1] == "walk":
    walk(sys.argv[2], sys.argv[3])


def fire_until_spawned(start, tries=10):
    """press fire until the coop script reports a spawned player (join() returns on 'joined the', which can come
    before the spawn; a bare join then sits on 'Press Fire to join' as a spectator)"""
    for _ in range(tries):
        if wait_log(r"waitForPlayer DONE|EAKIT given", 1, start):
            return True
        step(["popmenu 0", "wait 10", "+attackprimary", "wait 10", "-attackprimary"], timeout=60)
        if wait_log(r"waitForPlayer DONE|EAKIT given", 8, start):
            return True
    return False


def entdump(top=1024, batch=16):
    """'whatis' every entity number. Small batches with a wait: ~128 replies in one frame overflow the client's
    reliable-command buffer and the rest are lost silently."""
    for b in range(0, top, batch):
        lines = []
        for i in range(b, b + batch):
            lines += ["whatis %d" % i, "wait 2"]
        step(lines, timeout=120)


def entmap(mapname, outdir, renderer="opengl2"):
    """join the map and dump every entity (QA: identify props by origin and model)"""
    os.makedirs(outdir, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        # the map script dumps (coop_eatest 4 -> ea_entdump); console 'whatis' in bulk loses most replies
        c = launch(mapname, renderer, False, w=1280, h=720, extra_sets=["set coop_eatest 4"])
        with c:
            if not wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 300):
                raise RuntimeError("map never loaded")
            time.sleep(8)
            start = len(read_log())
            join()
            fire_until_spawned(start)
            m = wait_log(r"EAENT done \d+", 120, start)
            log("entmap:", m.group(0) if m else "NO DUMP")
            shutil.copyfile(LOG, os.path.join(outdir, "qconsole.log"))
    finally:
        hg.release_slot(OWNER)


def film(briefmap, nextmap, outdir, renderer="opengl2"):
    """intro film check: start the briefing map as a coop server, join, screenshot the film while it plays, ready up
    with [Use] (the READY gate) and wait for the next map. On the next map, dump every entity with 'whatis' so script-
    spawned props can be identified by origin (QA: unknown floating objects)."""
    os.makedirs(outdir, exist_ok=True)
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=30)
    try:
        # the real route: players arrive on a briefing map from a map change, already on a team. A FRESH join on a
        # briefing map never spawns (coop bans every dm primary - dmflags 532676608 - so the team-menu spawn path
        # returns 'That weapon is currently banned'; the stock briefinge1 behaves the same), so start on the next
        # map, join there, then change map to the briefing.
        c = launch(nextmap, renderer, False, w=1280, h=720)
        with c:
            if not wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 300):
                raise RuntimeError("entry map never loaded")
            time.sleep(8)
            join()
            time.sleep(15)
            start = len(read_log())
            step(["map " + briefmap], timeout=120)
            if not wait_log(r"Server: %s" % re.escape(briefmap), 120, start):
                raise RuntimeError("briefing never loaded")
            wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 120, start)
            time.sleep(6)
            start = len(read_log())
            # after a map change the client waits on 'Press Fire to join': ONE press. join() retries fire until it
            # sees a 'joined the' line, which never comes after a map change, and fire skips a fullscreen film
            for _ in range(10):                     # fire until the coop script sees the player spawned, then stop
                step(["popmenu 0", "wait 10", "+attackprimary", "wait 10", "-attackprimary"], timeout=60)
                if wait_log(r"waitForPlayer DONE", 8, start):
                    break
            m = wait_log(r"COOPBV publish \S+", 60, start)
            log("film:", m.group(0) if m else "NO COOPBV PUBLISH")
            t0 = time.time()
            for k, at in zip("abcd", (3, 10, 25, 45)):
                time.sleep(max(0, t0 + at - time.time()))
                try:
                    step(["screenshot film_%s" % k], timeout=30)
                except RuntimeError as e:          # a fullscreen cinematic may hold the console: note it, go on
                    log("film shot %s:" % k, e)
            start = len(read_log())
            ok = None
            for _ in range(12):                     # READY gate: hold [Use] until the next map loads (cap 210 s anyway)
                step(["+use", "wait 30", "-use", "wait 30"], timeout=60)
                ok = wait_log(r"Server: %s|COOP_MAPGRADE[^\n]*%s|Loading map %s" % ((re.escape(nextmap),) * 3), 15, start)
                if ok:
                    break
            log("next map:", "loaded after %.0f s" % (time.time() - t0) if ok else "NOT LOADED")
            if ok:
                wait_log(r"Spawning Entities Done|COOP_MAPGRADE", 120, start)
                time.sleep(8)
                join()
                time.sleep(10)
                entdump()
            sd = os.path.join(MAINTT, "screenshots")
            for fn in os.listdir(sd):
                if fn.startswith("film_"):
                    shutil.move(os.path.join(sd, fn), os.path.join(outdir, fn))
            shutil.copyfile(LOG, os.path.join(outdir, "qconsole.log"))
    finally:
        hg.release_slot(OWNER)


if __name__ == "__main__" and sys.argv[1] == "film":
    film(sys.argv[2], sys.argv[3], sys.argv[4])

if __name__ == "__main__" and sys.argv[1] == "entmap":
    entmap(sys.argv[2], sys.argv[3])

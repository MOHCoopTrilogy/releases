#!/usr/bin/env python3
"""rkeep_p0.py - renderer_reinit P0 measurement run (docs/proposals/renderer_reinit_2026-09-26/plan.md, P0).

Drives a PRIVATE client (a copy of the live exe in G:\\mohaa-gfxtest, homepath G:\\mohaa-gl2\\home_keep) with the
probe renderer renderer_opengl2keep.dll, through a map cycle, and writes the log + a JSON summary of the
^~^~^ RKEEP* lines. Measurement only: the DLL changes nothing it draws.

Rules this obeys (harness lessons):
  - never a raw rcon map change while the log is the evidence (bug-3033/3034): every map change is written to a
    cfg and rcon only `exec`s it, so the load runs outside the rcon output redirect and is logged;
  - at most 31 '+' commands on the command line (bug-2996);
  - no cfg `wait` after map/vid_restart (bug-2995: wait is milliseconds) - waits are on log markers;
  - never touches G:\\mohaa-gl2\\home, the fixed-name DLLs, build.ps1 or any install; refuses to start while the
    user's openmohaa.exe or another private client (openmohaa_gfxtest.exe) runs; closes itself if the user's game
    starts. Client time on the shared G:\\mohaa-gfxtest copy is slotted by the coordinator.
  - background window (docs/tools/harness_window.py): on DISPLAY2, never activated, muted, mouse off; the size stays
    3440x1440 (the user's, for comparable timings) and hangs off DISPLAY2's far side, never onto DISPLAY1.

  python rkeep_p0.py run [--renderer opengl2keep] [--probe 1] [--tag NAME] [--maps m1l1,m1l2a,...]
  python rkeep_p0.py summarize <qconsole.log>
"""
import json, os, re, shutil, socket, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import harness_window as hw  # noqa: E402

GAME = r"G:\mohaa-gfxtest\openmohaa_gfxtest.exe"
GAMEDIR = r"G:\mohaa-gfxtest"
GOGROOT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
HOME = r"G:\mohaa-gl2\home_keep"
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
USER_CFG = r"G:\mohaa-gl2\home\maintt\configs\omconfig.cfg"   # read (copied), never written
PORT = 12460
RCONPW = "rkeeppw"
MAGIC = b"\xff\xff\xff\xff"
OUTROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")

# PLAY-GL2.bat's own settings (so the run matches the user's real launch), plus the harness's
BASE_SETS = [
    ("com_target_game", "2"), ("fs_basepath", GOGROOT), ("fs_homepath", HOME),
    ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"),
    ("r_uselod", "0"), ("r_lodscale", "28"), ("r_mode", "-1"),
    ("r_customwidth", "3440"), ("r_customheight", "1440"), ("r_fullscreen", "0"),
    ("developer", "1"), ("r_drawSunRays", "0"), ("r_specularMapping", "0"),
    ("r_cmdtrace", "0"), ("r_skeldiag", "0"), ("r_picmip", "0"),
    ("r_textureMode", "GL_LINEAR_MIPMAP_LINEAR"), ("r_ext_max_anisotropy", "16"),
    ("logfile", "2"),
    ("g_gametype", "2"), ("net_port", str(PORT)), ("rconPassword", RCONPW), ("in_mouse", "0"),
]

# Campaign order with the cases that matter: a new map, a revisit, a same-map reload, a lobby, a return to the menu.
DEFAULT_CYCLE = [
    ("map", "m1l2a"),     # mission -> next mission (a transition's load path)
    ("map", "m1l2b"),
    ("map", "m1l1"),      # revisit
    ("map", "m1l1"),      # same map again (SV_Map_f: differentmap stays qtrue, so it re-registers)
    ("map", "co_lobby1"), # a lobby, as full-campaign mode inserts
    ("map", "m2l1"),
    # disconnect -> menu registration, then the menu start path (ui_dmmap + start_server.cfg = ui_startdmmap 2).
    # One step: after `disconnect` the listen server is gone, so rcon could not reach a second step.
    ("menu_start", "m3l2"),
]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def procs(image):
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq %s" % image, "/NH", "/FO", "CSV"],
                         capture_output=True, text=True).stdout
    return [int(l.split('","')[1]) for l in out.splitlines() if l.lower().startswith('"%s"' % image.lower())]


def guard(our_pid=None):
    if procs("openmohaa.exe"):
        log("USER GAME RUNNING - closing our client and stopping")
        if our_pid:
            subprocess.run(["taskkill", "/PID", str(our_pid)], capture_output=True)
        raise SystemExit(3)


def rcon(command, timeout=1.5, settle=0.35):
    payload = MAGIC + b"\x02" + b"rcon " + RCONPW.encode() + b" " + command.encode()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(payload, ("127.0.0.1", PORT))
        chunks = []
        while True:
            try:
                data, _ = sock.recvfrom(16384)
            except socket.timeout:
                break
            chunks.append(data)
            sock.settimeout(settle)
        return b"".join(chunks).decode("latin-1")
    finally:
        sock.close()


def read_log():
    try:
        with open(LOG, "rb") as f:
            return f.read().decode("latin-1")
    except OSError:
        return ""


def wait_log(pattern, timeout, start=0, pid=None):
    rx = re.compile(pattern)
    t0 = time.time()
    while time.time() - t0 < timeout:
        guard(pid)
        txt = read_log()
        m = rx.search(txt, start)
        if m:
            return m
        if pid is not None and pid not in procs("openmohaa_gfxtest.exe"):
            return None
        time.sleep(1.0)
    return None


def step(lines, pid, tag, timeout=60, retries=3):
    """write the lines to rkstep.cfg and have rcon exec it: the commands then run from the command buffer, outside
    the rcon redirect, so everything they print reaches qconsole.log (bug-3034)."""
    mk = "^~^~^ RKSTEP %s" % tag
    with open(os.path.join(MAINTT, "rkstep.cfg"), "w", newline="\n") as f:
        f.write("\n".join(list(lines) + ["echo %s" % mk]) + "\n")
    start = len(read_log())
    for attempt in range(retries):
        rcon("exec rkstep.cfg")
        if wait_log(re.escape(mk), 12 if attempt < retries - 1 else timeout, start=max(0, start - 10), pid=pid):
            return True
        time.sleep(1.5)  # SVC_RemoteCommand rate-limits rcon per address
    raise RuntimeError("step %s never ran" % tag)


def run(renderer="opengl2keep", probe="1", tag=None, cycle=None):
    tag = tag or time.strftime("p0_%Y%m%d_%H%M")
    out = os.path.join(OUTROOT, tag)
    os.makedirs(out, exist_ok=True)
    guard()
    if procs("openmohaa_gfxtest.exe"):
        raise SystemExit("another private client is running (openmohaa_gfxtest.exe) - ask the coordinator for a slot")
    soaks = procs("omohaaded.exe")
    if not os.path.exists(os.path.join(GAMEDIR, "renderer_%s.dll" % renderer)):
        raise SystemExit("renderer_%s.dll missing in %s" % (renderer, GAMEDIR))
    os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
    shutil.copyfile(USER_CFG, os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)

    sets = dict(BASE_SETS)
    sets["cl_renderer"] = renderer
    sets["r_hzmKeepProbe"] = str(probe)
    args = [GAME]
    for k, v in sets.items():
        args += ["+set", k, v]
    first = "m1l1"
    args += ["+set", "ui_dmmap", first, "+exec", "coop_mod/start_server.cfg"]
    args, late = hw.apply_policy(args)   # windowed / muted / mouse off; keep the measured size below
    args[args.index("r_customwidth") + 1] = sets["r_customwidth"]
    args[args.index("r_customheight") + 1] = sets["r_customheight"]
    if late:
        log("policy cvars left at their config value (no '+' budget):", late)
    nplus = sum(1 for a in args if a.startswith("+"))
    if nplus > 31:
        raise SystemExit("command line has %d '+' commands; the engine keeps only 31 (bug-2996)" % nplus)
    notes = {"tag": tag, "renderer": renderer, "probe": probe, "cmdline": subprocess.list2cmdline(args),
             "soak_servers_running": soaks, "t0": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": []}
    log("launching", renderer, "probe", probe, "(%d '+' commands); soak servers running: %s" % (nplus, soaks))
    bg = hw.launch_background(GAME, args[1:], GAMEDIR, policy=False, log=log)
    pid = bg.pid
    try:
        if not wait_log(r"Detected Coop for", 400, start=0, pid=pid):
            raise RuntimeError("first map never became joinable")
        notes["steps"].append(("start", first, time.strftime("%H:%M:%S")))
        time.sleep(8)
        for i, (kind, mapname) in enumerate(cycle or DEFAULT_CYCLE):
            start = len(read_log())
            if kind == "map":
                step(["map %s" % mapname], pid, "s%d_map_%s" % (i, mapname), timeout=180, retries=1)  # a re-send would load twice
                ok = wait_log(r"Detected Coop for", 400, start=start, pid=pid)
            elif kind == "menu_start":
                # a bare `wait` is one frame (bug-2995: only `wait N` is milliseconds)
                step(["disconnect", "wait", "set ui_dmmap %s" % mapname, "exec coop_mod/start_server.cfg"], pid,
                     "s%d_menustart_%s" % (i, mapname), timeout=400, retries=1)  # never re-send a disconnect
                ok = wait_log(r"Detected Coop for", 400, start=start, pid=pid)
            else:
                raise ValueError(kind)
            notes["steps"].append((kind, mapname, time.strftime("%H:%M:%S"), bool(ok)))
            log("step", i, kind, mapname, "ok" if ok else "TIMEOUT")
            if not ok:
                break
            time.sleep(8)  # let late image loads land before the next registration closes the set
    finally:
        try:
            rcon("quit")
        except OSError:
            pass
        t0 = time.time()
        while pid in procs("openmohaa_gfxtest.exe") and time.time() - t0 < 40:
            time.sleep(1)
        if pid in procs("openmohaa_gfxtest.exe"):
            subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True)
            time.sleep(5)
            if pid in procs("openmohaa_gfxtest.exe"):
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        bg.close(grace=5)                # stops the watchdog, closes the job (bug-3147)
        wrep = bg.report()
        notes["window"] = {k: wrep[k] for k in ("test_display", "clean", "violations", "first_visible", "enforced",
                                                "guard")}
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(out, "qconsole.log"))
        json.dump(notes, open(os.path.join(out, "notes.json"), "w"), indent=1)
    s = summarize(os.path.join(out, "qconsole.log"))
    json.dump(s, open(os.path.join(out, "summary.json"), "w"), indent=1)
    log("done:", out)


KV = re.compile(r"(\w+)=([^\s|]+)")


def summarize(path):
    txt = open(path, "rb").read().decode("latin-1")
    res = {"RKEEPBUILD": [], "RKEEP": [], "RKEEPINIT": [], "RKEEPGLSL": [], "RKEEPIMG": [], "RKEEPVRAM": [],
           "glsl_engine_line": [], "cgame": [], "server": [], "errors": {}}
    for line in txt.splitlines():
        ts = line[1:20] if line.startswith("[") else ""
        m = re.search(r"\^~\^~\^ (RKEEP\w*) (.*)", line)
        if m:
            kv = dict(KV.findall(m.group(2)))
            if m.group(1) == "RKEEPIMG":
                parts = m.group(2).split("|")
                kv = dict(KV.findall(parts[0]))
                if len(parts) > 1:
                    kv.update({"prev_" + k: v for k, v in KV.findall(parts[1])})
                if len(parts) > 2:
                    kv.update({"world_" + k: v for k, v in KV.findall(parts[2])})
            kv["ts"] = ts
            res.setdefault(m.group(1), []).append(kv)
            continue
        if "GLSL shaders (" in line:
            res["glsl_engine_line"].append(line[33:].strip())
        m = re.search(r"CL_InitCGame: ([\d.]+) seconds", line)
        if m:
            res["cgame"].append((ts, float(m.group(1))))
        m = re.search(r"\] Server: (\S+)", line)
        if m:
            res["server"].append((ts, m.group(1)))
        for key in ("Script Error", "ERROR", "WARNING", "glGetError", "RKEEPGLSL binary unsupported"):
            if key in line:
                res["errors"][key] = res["errors"].get(key, 0) + 1
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "run":
        opts = dict(zip(a[1::2], a[2::2]))
        cyc = None
        if "--maps" in opts:
            cyc = [("map", m) for m in opts["--maps"].split(",")]
        run(opts.get("--renderer", "opengl2keep"), opts.get("--probe", "1"), opts.get("--tag"), cyc)
    elif a[0] == "summarize":
        print(json.dumps(summarize(a[1]), indent=1)[:20000])
    else:
        raise SystemExit(__doc__)

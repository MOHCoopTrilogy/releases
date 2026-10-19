#!/usr/bin/env python3
"""rkeep_client.py - keep-renderer gate harness (docs/proposals/renderer_reinit_2026-09-26/plan.md 9.4: G1-G5 + timing).

Drives a PRIVATE client in G:\\mohaa-keeptest (hash-verified copies of the live binaries in G:\\mohaa-gl2, the live data
as fs_basepath, homepath G:\\mohaa-gl2\\home_keep) with a keep test renderer (renderer_opengl2keep<suffix>.dll, installed
by build_keep.py) through scripted map sequences, and writes per-run folders with the log, JSON notes, GPU/RAM samples
and PNG frame captures. `report` turns runs into the gate tables; `diff` compares two runs' frames.

  python rkeep_client.py setup                      create/refresh G:\\mohaa-keeptest from the live install
  python rkeep_client.py verify                     is the private copy still identical to the live binaries?
  python rkeep_client.py run SCENARIO [options]
        SCENARIO  cycle | vidrestart | latch | fault | timing | live
        --renderer SUFFIX   renderer_opengl2keep<SUFFIX>.dll (default p2); "stock" = the live renderer_opengl2.dll
                            (was "live" before 2026-09-28; "live" is now the suffix of the live-settings DLL)
        --rname NAME        a raw cl_renderer name (renderer_<NAME>.dll), e.g. opengl1live for the gl1 smoke
        --set k=v,k=v       extra +set cvars (e.g. r_hzmLiveApply=7 for the live scenario)
        --keep 0|1          r_hzmKeepRenderer (default 1)
        --probe N           r_hzmKeepProbe (default 2: RKEEPWORLD + drift audit)
        --maps a,b,c        map list (default the 14-map cycle)     --loops N (cycle, default 2)
        --shots 0|1         frame captures per map (cycle, default 1)
        --exe keeptest|openmohaa   image name (default keeptest; openmohaa only for timing, bug-3062)
        --res WxH           default auto = the test display (1920x1080 on DISPLAY2); runs before 2026-09-27 used
                            3440x1440 - pass it explicitly to compare with those (it hangs off DISPLAY2's far side)
        --tag NAME
        --settle SEC        seconds after "Detected Coop" before sampling (default 20)
  python rkeep_client.py report RUN [RUN ...]        gate tables (G1 asserts, G2 world, G3 memory, timing)
  python rkeep_client.py diff RUN_A RUN_B [--floor RUN_C RUN_D]   frame compare, same step names

Rules (harness lessons, all enforced here):
  - one shared private-client slot (harness_guard.py); refuses while the user's game (classified by PATH, not image
    name) or another harness client runs; closes itself when the user's game appears;
  - map changes run from an exec'd cfg, never a raw rcon command, so the load is logged (bug-3033/3034); rcon only
    execs, and is rate-limited (SVC_RemoteCommand drops bursts);
  - <= 31 '+' commands on the command line (bug-2996); cfg `wait N` is milliseconds (bug-2995);
  - window-content captures only (bug-3053): the engine's own `screenshot`;
  - background window (harness_window.py, docs/proposals/test_window_policy_2026-09-27): launched on DISPLAY2, never
    activated, muted, mouse off; a watchdog records any focus/placement/capture violation into notes.json "window";
  - never writes G:\\mohaa-gl2 (except the harness homepath), a fixed-name DLL, build.ps1 or any install;
  - loopback only (net_ip 127.0.0.1).
"""
import hashlib, json, os, re, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

LIVE = r"G:\mohaa-gl2"
PRIV = r"G:\mohaa-keeptest"
HOME = r"G:\mohaa-gl2\home_keep"
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTDIR = os.path.join(MAINTT, "screenshots")
USER_CFG = os.path.join(LIVE, r"home\maintt\configs\omconfig.cfg")   # read (copied), never written
PORT = 12460
RCONPW = "rkeeppw"
MAGIC = b"\xff\xff\xff\xff"
OUTROOT = os.path.join(HERE, "runs")
OWNER = "rkeep"
COPY = ["openmohaa.exe", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll", "SDL2.dll",
        "OpenAL64.dll", "libcurl.dll"]
EXES = {"keeptest": "openmohaa_keeptest.exe", "openmohaa": "openmohaa.exe"}
CYCLE14 = ["m1l1", "m1l2a", "m2l1", "m2l2a", "m3l1a", "m3l2", "m4l0", "m5l1a", "m6l1a", "e1l1", "e1l4", "e2l2",
           "t1l1", "t2l1"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ setup / verify
def setup():
    if hg.user_game_running():
        raise SystemExit("the user's game is running - not touching anything")
    os.makedirs(PRIV, exist_ok=True)
    man = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {}}
    for fn in COPY:
        src = os.path.join(LIVE, fn)
        if not os.path.exists(src):
            raise SystemExit("missing in the live install: " + src)
        dsts = [os.path.join(PRIV, fn)]
        if fn == "openmohaa.exe":
            dsts.append(os.path.join(PRIV, EXES["keeptest"]))
        h = sha(src)
        for d in dsts:
            shutil.copyfile(src, d)
            if sha(d) != h:
                raise SystemExit("copy mismatch " + d)
            man["files"][os.path.basename(d)] = {"src": src, "sha256": h}
        pdb = src[:-4] + ".pdb"
        if os.path.exists(pdb):
            shutil.copyfile(pdb, os.path.join(PRIV, os.path.basename(pdb)))
    json.dump(man, open(os.path.join(PRIV, "manifest.json"), "w"), indent=1)
    log("private copy ready:", PRIV, len(man["files"]), "files")


def verify(quiet=False):
    try:
        man = json.load(open(os.path.join(PRIV, "manifest.json")))
    except (OSError, ValueError):
        raise SystemExit("no manifest - run setup")
    bad = []
    for fn, rec in man["files"].items():
        live = sha(rec["src"]) if os.path.exists(rec["src"]) else None
        mine = sha(os.path.join(PRIV, fn)) if os.path.exists(os.path.join(PRIV, fn)) else None
        if live != rec["sha256"] or mine != rec["sha256"]:
            bad.append((fn, "live changed" if live != rec["sha256"] else "private changed"))
    if not quiet:
        log("verify:", "IDENTICAL to the live binaries" if not bad else bad)
    return bad


# ------------------------------------------------------------------------------------------------ client plumbing
class Client:
    def __init__(self, exe_key, renderer, keep, probe, res, extra_sets=()):
        self.exe = os.path.join(PRIV, EXES[exe_key])
        self.image = EXES[exe_key]
        self.renderer = renderer
        self.keep, self.probe, self.res = keep, probe, res
        self.extra = list(extra_sets)
        self.pid = None
        self.bg = None
        self.window_report = None
        self.last_rcon = 0.0

    # --- guards
    def guard(self):
        if hg.user_game_running():
            log("USER GAME RUNNING - closing our client and stopping")
            self.kill()
            raise SystemExit(3)

    def alive(self):
        return self.pid is not None and any(r["pid"] == self.pid for r in hg.classify())

    # --- log
    @staticmethod
    def read_log():
        try:
            with open(LOG, "rb") as f:
                return f.read().decode("latin-1")
        except OSError:
            return ""

    def wait_log(self, pattern, timeout, start=0):
        rx = re.compile(pattern)
        t0 = time.time()
        last_guard = 0
        while time.time() - t0 < timeout:
            if time.time() - last_guard > 5:
                self.guard()
                last_guard = time.time()
            m = rx.search(self.read_log(), start)
            if m:
                return m
            if not self.alive():
                return None
            time.sleep(0.5)
        return None

    # --- rcon (exec only)
    def rcon(self, command, timeout=1.5, settle=0.35):
        gap = time.time() - self.last_rcon
        if gap < 1.2:
            time.sleep(1.2 - gap)  # SVC_RemoteCommand rate limit
        self.last_rcon = time.time()
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

    def step(self, lines, tag, timeout=60, retries=3):
        """lines go to rkstep.cfg and rcon execs it: they run from the command buffer, outside the rcon redirect,
        so everything they print reaches qconsole.log (bug-3034). Returns the log offset before the step."""
        mk = "^~^~^ RKSTEP %s" % tag
        with open(os.path.join(MAINTT, "rkstep.cfg"), "w", newline="\n") as f:
            f.write("\n".join(list(lines) + ["echo %s" % mk]) + "\n")
        start = len(self.read_log())
        for attempt in range(retries):
            self.rcon("exec rkstep.cfg")
            if self.wait_log(re.escape(mk), 12 if attempt < retries - 1 else timeout, start=max(0, start - 10)):
                return start
            time.sleep(1.5)
        raise RuntimeError("step %s never ran" % tag)

    def protect(self):
        """`dog 1` + `notarget 1`, REQUIRING the engine's "CHEAT: godmode ON" reply (bug-3182: the god cheat's console
        name here is "dog"; a bare `god` goes to the server, which ignores it, and nothing noticed). With an argument
        dog / notarget SET the flag; bare they TOGGLE, so never send them bare. Recipe:
        docs/proposals/fog_lod_pop_2026-09-27/tools/fogtest_run.py protect()."""
        for k in range(3):
            s = self.step(["dog 1", "notarget 1"], "god%d" % k)
            if self.wait_log(r"CHEAT: godmode ON", 10, start=max(0, s - 10)):
                return True
        raise RuntimeError("godmode never confirmed (no 'CHEAT: godmode ON' after dog 1)")

    def ready(self, ok):
        """after every map is up: godmode + notarget, confirmed (a death mid-run would pollute every gate)"""
        if ok:
            self.protect()
        return ok

    def query(self, cvar):
        """a cvar's value via rcon (a query, not a load: the redirect is harmless here)"""
        out = self.rcon(cvar)
        m = re.search(r'"%s" is:\s*"([^"]*)' % re.escape(cvar), out, re.I)
        latched = re.search(r'latched:\s*"([^"]*)', out)
        clean = lambda s: s.replace("^7", "").strip() if s is not None else None  # noqa: E731
        return clean(m.group(1) if m else None), clean(latched.group(1) if latched else None), out

    # --- lifecycle
    def launch(self, first_map, extra_boot=()):
        self.guard()
        others = [r for r in hg.classify() if r["cls"] == "HARNESS"]
        if others:
            raise SystemExit("another harness client is running: %s" % others)
        dll = os.path.join(PRIV, "renderer_%s.dll" % self.renderer)
        if not os.path.exists(dll):
            raise SystemExit("missing " + dll)
        os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
        os.makedirs(SHOTDIR, exist_ok=True)
        shutil.copyfile(USER_CFG, os.path.join(MAINTT, "configs", "omconfig.cfg"))
        for fn in os.listdir(MAINTT):
            if fn.lower().endswith(".pid"):
                os.remove(os.path.join(MAINTT, fn))
        if os.path.exists(LOG):
            os.remove(LOG)
        if self.res == "auto":
            dl, dt, dr, db = hw.test_display()["rect"]
            self.res = "%dx%d" % (dr - dl, db - dt)
        w, h = self.res.split("x")
        sets = [
            ("com_target_game", "2"), ("fs_basepath", LIVE), ("fs_homepath", HOME),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"),
            ("r_uselod", "0"), ("r_lodscale", "28"), ("r_mode", "-1"),
            ("r_customwidth", w), ("r_customheight", h), ("r_fullscreen", "0"),
            ("developer", "1"), ("r_drawSunRays", "0"), ("r_specularMapping", "0"),
            ("r_cmdtrace", "0"), ("r_skeldiag", "0"), ("r_picmip", "0"),
            ("r_textureMode", "GL_LINEAR_MIPMAP_LINEAR"), ("r_ext_max_anisotropy", "16"),
            ("logfile", "2"), ("net_ip", "127.0.0.1"), ("net_port", str(PORT)), ("rconPassword", RCONPW),
            ("cl_renderer", self.renderer), ("r_hzmKeepProbe", str(self.probe)),
            ("r_hzmKeepRenderer", str(self.keep)),
        ] + self.extra
        args = [self.exe]
        for k, v in sets:
            args += ["+set", k, v]
        args += ["+exec", "rkboot.cfg"]
        # background-window policy: forces windowed/muted/mouse-off +sets and hands back the cvars that did not fit
        # the 31 '+' budget for the boot cfg. An explicit --res larger than DISPLAY2 keeps its size (placed on DISPLAY2,
        # hanging off the side away from the primary).
        try:
            args, late = hw.apply_policy(args)
        except hw.PolicyError as e:
            raise SystemExit(str(e))
        args[args.index("r_customwidth") + 1], args[args.index("r_customheight") + 1] = w, h
        boot = ["set g_gametype 2", "set in_mouse 0", "set thereisnomonkey 1", "set cheats 1", "set g_ai 0",
                "set coop_dbno 0"] + late + \
            list(extra_boot) + ["set ui_dmmap %s" % first_map, "exec coop_mod/start_server.cfg"]
        with open(os.path.join(MAINTT, "rkboot.cfg"), "w", newline="\n") as f:
            f.write("\n".join(boot) + "\n")
        nplus = sum(1 for a in args if a.startswith("+"))
        if nplus > 31:
            raise SystemExit("command line has %d '+' commands; the engine keeps only 31 (bug-2996)" % nplus)
        hg.acquire_slot(OWNER, self.exe, HOME, [PORT], minutes=240)
        self.bg = hw.launch_background(self.exe, args[1:], PRIV, policy=False, log=log)
        self.pid = self.bg.pid
        hg.set_slot_pid(OWNER, self.pid)
        self.cmdline = subprocess.list2cmdline(args)
        log("launched", self.image, "renderer", self.renderer, "keep", self.keep, "probe", self.probe,
            "(%d '+')" % nplus)
        return self.ready(self.wait_log(r"Detected Coop for", 400, start=0))

    def kill(self):
        if self.pid is None:
            return
        try:
            self.rcon("quit")
        except OSError:
            pass
        t0 = time.time()
        while self.alive() and time.time() - t0 < 40:
            time.sleep(1)
        if self.alive():
            subprocess.run(["taskkill", "/PID", str(self.pid)], capture_output=True)
            time.sleep(5)
            if self.alive():
                subprocess.run(["taskkill", "/F", "/PID", str(self.pid)], capture_output=True)
        self.pid = None
        if self.bg is not None:
            self.bg.close(grace=5)       # stops the watchdog, closes the job (bug-3147)
            wrep = self.bg.report()
            self.window_report = {k: wrep[k] for k in ("test_display", "clean", "violations", "first_visible",
                                                       "enforced", "guard")}
            if not wrep["clean"]:
                log("WINDOW POLICY VIOLATIONS:", wrep["violations"])
            self.bg = None
        hg.release_slot(OWNER)

    # --- measurements
    def mem(self):
        """per-process dedicated GPU memory (the WDDM counter) + private bytes"""
        ps = ("$s=(Get-Counter '\\GPU Process Memory(pid_%d*)\\Dedicated Usage' -ErrorAction SilentlyContinue)"
              ".CounterSamples; $g=($s | Measure-Object CookedValue -Sum).Sum;"
              "$p=(Get-Process -Id %d -ErrorAction SilentlyContinue).PrivateMemorySize64;"
              "Write-Output \"$g $p\"") % (self.pid, self.pid)
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.split()
        try:
            return {"gpuMB": round(float(out[0]) / 2 ** 20, 1), "privMB": round(float(out[1]) / 2 ** 20, 1)}
        except (IndexError, ValueError):
            return {"gpuMB": None, "privMB": None}

    def shots(self, name, outdir):
        """world-only frames at the current view: entities/HUD off, shader time frozen; normal + r_lightmap 1"""
        res = {}
        for kind, extra in (("n", []), ("l", ["r_lightmap 1"])):
            fn = "rk_%s_%s" % (name, kind)
            tga = os.path.join(SHOTDIR, fn + ".tga")
            if os.path.exists(tga):
                os.remove(tga)
            self.step(["ui_hud 0", "r_drawentities 0", "r_hzmKeepFreezeTime 1"] + extra +
                      ["wait 700", "screenshot %s" % fn, "wait 300", "r_lightmap 0", "r_drawentities 1", "ui_hud 1",
                       "r_hzmKeepFreezeTime 0"], "shot_%s_%s" % (name, kind), timeout=60)
            t0 = time.time()
            while not os.path.exists(tga) and time.time() - t0 < 20:
                time.sleep(0.5)
            if not os.path.exists(tga):
                res[kind] = None
                continue
            time.sleep(1.0)
            try:
                from PIL import Image
                png = os.path.join(outdir, fn + ".png")
                Image.open(tga).save(png)
                os.remove(tga)
                res[kind] = os.path.basename(png)
            except Exception as e:  # keep the TGA if conversion fails
                res[kind] = "convert-failed: %s" % e
        return res


def load_map(c, mapname, tag):
    start = c.step(["map %s" % mapname], tag, timeout=180, retries=1)  # a re-send would load twice
    t0 = time.time()
    ok = c.wait_log(r"Detected Coop for", 400, start=start)
    wall = round(time.time() - t0, 1)          # measured before protect(): the timing gate is unaffected
    return bool(c.ready(ok)), wall


# ------------------------------------------------------------------------------------------------ scenarios
def scen_cycle(c, out, notes, maps, loops, shots, settle):
    i = 0
    for loop in range(loops):
        for m in maps:
            if i == 0:
                ok, wall = True, None     # the launch loaded maps[0]
            else:
                ok, wall = load_map(c, m, "s%02d_%s" % (i, m))
            rec = {"i": i, "loop": loop, "map": m, "ok": ok, "wall": wall}
            if ok:
                time.sleep(settle)
                rec["mem"] = c.mem()
                c.step(["meminfo"], "mem_%02d" % i)
                csv = os.path.join(MAINTT, "textureuse.csv")   # meminfo writes it; only the zone lines matter (E2-19)
                if os.path.exists(csv):
                    os.remove(csv)
                if shots:
                    rec["shots"] = c.shots("%02d_%s" % (i, m), out)
            notes["steps"].append(rec)
            log("step", i, m, "ok" if ok else "TIMEOUT", rec.get("mem"), wall)
            if not ok:
                return
            i += 1


def scen_vidrestart(c, out, notes, maps, settle, n=6):
    # two keep maps first, then restarts, then a map (plan G4)
    for j, m in enumerate(maps[1:3]):
        ok, wall = load_map(c, m, "pre%d_%s" % (j, m))
        notes["steps"].append({"kind": "map", "map": m, "ok": ok, "wall": wall})
    for k in range(n):
        start = c.step(["vid_restart"], "vr%d" % k, timeout=120, retries=1)
        ok = c.wait_log(r"\^~\^~\^ RKEEP path=", 120, start=start)
        time.sleep(settle / 2)
        notes["steps"].append({"kind": "vid_restart", "k": k, "ok": bool(ok), "mem": c.mem()})
        log("vid_restart", k, "ok" if ok else "TIMEOUT")
    shot = c.shots("vr_after", out)
    ok, wall = load_map(c, maps[3], "post_%s" % maps[3])
    time.sleep(settle)
    notes["steps"].append({"kind": "map", "map": maps[3], "ok": ok, "wall": wall, "mem": c.mem(), "shots": shot,
                           "shots_after": c.shots("vr_map", out)})


def star_set():
    """the generated star set: every post-FX row whose label ends in ' *' (gen_menu_graphics.py) - latched knobs
    that promise 'the next map load' - plus the non-latched init-read r_maxpolys (plan G5)"""
    sys.path.insert(0, os.path.dirname(HERE))
    import gen_menu_graphics as G
    cv = []
    for page in G.PFX_PAGES:
        for _col, _title, rows in page[5]:
            for row in rows:
                if row[2].rstrip().endswith("*") and row[3] not in cv:
                    cv.append(row[3])
    return cv + ["r_maxpolys"]


def scen_latch(c, out, notes, maps, settle):
    cvars = star_set()
    notes["star_set"] = cvars
    mi = 1
    for cv in cvars:
        val, latched, _ = c.query(cv)
        if val is None:
            notes["steps"].append({"cvar": cv, "error": "query failed"})
            continue
        new = "0" if val not in ("0", "0.0") else "1"
        if cv == "r_renderScale":
            new = "0.75" if val != "0.75" else "1"
        if cv == "r_maxpolys":
            new = str(int(float(val)) + 1024)
        c.step(["set %s %s" % (cv, new)], "set_%s" % cv)
        rec = {"cvar": cv, "orig": val, "new": new, "maps": []}
        for phase in ("apply", "keep", "restore", "keep2"):
            if phase == "restore":
                c.step(["set %s %s" % (cv, val)], "restore_%s" % cv)
            m = maps[mi % len(maps)]
            mi += 1
            ok, wall = load_map(c, m, "%s_%s_%s" % (cv, phase, m))
            after, lat, _ = c.query(cv)
            rec["maps"].append({"phase": phase, "map": m, "ok": ok, "wall": wall, "value": after, "latched": lat})
            if not ok:
                break
        notes["steps"].append(rec)
        log("latch", cv, [(x["phase"], x["ok"], x["value"], x["latched"]) for x in rec["maps"]])
    # a loose shader file changes the shader-file fingerprint
    loose = os.path.join(MAINTT, "scripts", "zz_rkeep_probe.shader")
    os.makedirs(os.path.dirname(loose), exist_ok=True)
    with open(loose, "w", newline="\n") as f:
        f.write("textures/rkeep/probe\n{\n\t{\n\t\tmap $whiteimage\n\t}\n}\n")
    rec = {"cvar": "loose-shader", "maps": []}
    for phase in ("apply", "keep", "restore", "keep2"):
        if phase == "restore":
            os.remove(loose)
        m = maps[mi % len(maps)]
        mi += 1
        ok, wall = load_map(c, m, "loose_%s_%s" % (phase, m))
        rec["maps"].append({"phase": phase, "map": m, "ok": ok, "wall": wall})
    notes["steps"].append(rec)
    if os.path.exists(loose):
        os.remove(loose)


def scen_fault(c, out, notes, maps, settle):
    # bit 1 lightmap swap (oracle validation), bit 8 skipped visClusters reset (assert), bit 4 GLSL ERR_DROP in a
    # legacy R_Init (E2-1 recovery). Each is one-shot and armed right before the map load it targets.
    seq = [(1, maps[1]), (8, maps[2]), (0, maps[3])]
    for bit, m in seq:
        if bit:
            c.step(["set r_hzmKeepFault %d" % bit], "arm%d" % bit)
        ok, wall = load_map(c, m, "fault%d_%s" % (bit, m))
        time.sleep(settle / 2)
        notes["steps"].append({"fault": bit, "map": m, "ok": ok, "wall": wall,
                               "shots": c.shots("fault%d_%s" % (bit, m), out) if ok else None})
        log("fault", bit, m, ok)
    # bit 4 needs a LEGACY R_Init (2nd+ in this DLL image): force one with a latch, then load. The ERR_DROP shuts the
    # listen server down (Com_Error: SV_Shutdown, then CL_FlushMemory -> CL_StartHunkUsers -> a nested registration,
    # which must take the legacy path and tear the half-built renderer down), so rcon cannot reach a later step: the
    # recovery rides in the same cfg behind a `wait` (ms, bug-2995; ERR_DROP does not clear the command buffer).
    ssao = (c.query("r_ppSSAO")[0] or "1")
    start = c.step(["set r_hzmKeepFault 4", "set r_ppSSAO %s" % ("0" if ssao != "0" else "1"),
                    "map %s" % maps[4], "wait 90000", "set ui_dmmap %s" % maps[5], "exec coop_mod/start_server.cfg"],
                   "fault4_%s" % maps[4], timeout=30, retries=1)
    dropped = c.wait_log(r"RKEEPFAULT: injected GLSL failure", 200, start=start)
    ok = bool(c.ready(c.wait_log(r"Detected Coop for", 500, start=start + 1))) if dropped else False
    notes["steps"].append({"fault": 4, "map": maps[4], "dropped": bool(dropped), "recovered_map": maps[5], "ok": ok,
                           "alive": c.alive()})
    log("fault 4 dropped", bool(dropped), "recovered", ok)
    if c.alive():
        c.step(["set r_ppSSAO %s" % ssao], "fault4_restore")


def scen_timing(c, out, notes, maps, settle):
    for i, m in enumerate(maps[1:]):
        ok, wall = load_map(c, m, "t%02d_%s" % (i, m))
        notes["steps"].append({"map": m, "ok": ok, "wall": wall})
        log("timing", m, ok, wall)
        if not ok:
            return
        time.sleep(settle)


# ------------------------------------------------------------------------------------------------ live settings (Track 2)
# docs/proposals/live_graphics_settings_2026-09-27/plan.md 4.2. Launch with --renderer live --set r_hzmLiveApply=<bits>
# on a sun map (m3l2). Every hook is flipped by an exec'd cfg (a set of a LATCH cvar latches it); the gate is read from
# LIVEAPPLY lines printed by a later frame plus rcon state queries (r_hzmRegCount unchanged = no re-init, pending 0).
LIVE_FLIPS = [("r_sunShadows", "0", "1", 1), ("r_ext_max_anisotropy", "2", "16", 1),
              ("r_ext_texture_filter_anisotropic", "0", "1", 1), ("r_swapInterval", "1", "0", 2),
              ("r_ppSSAO", "1", "0", 4), ("r_ppDoF", "1", "0", 4), ("r_softParticles", "0", "1", 4)]


def _live_flip(c, cv, val, tag, expect_apply, revert=False):
    reg0 = c.query("r_hzmRegCount")[0]
    start = c.step(["set %s %s" % (cv, val)], tag)
    hit = c.wait_log(r"\^~\^~\^ LIVEAPPLY cvar=%s value=%s" % (re.escape(cv), re.escape(val)),
                     8 if expect_apply else 4, start=start)
    time.sleep(0.5)
    reg1 = c.query("r_hzmRegCount")[0]
    now, latched, _ = c.query(cv)
    pend = c.query("r_hzmPendingRestart")[0]
    rec = {"cvar": cv, "set": val, "applied": bool(hit), "line": hit.group(0) if hit else None,
           "regBefore": reg0, "regAfter": reg1, "value": now, "latched": latched, "pending": pend}
    if expect_apply:
        rec["pass"] = bool(hit) and reg0 == reg1 and latched is None and now == val and pend == "0"
    else:   # G0: switch off - nothing applies, the latch stays, the pending count shows it
        # (a revert to the current value clears the latch instead - qcommon/cvar.c Cvar_Set2)
        rec["pass"] = (not hit) and reg0 == reg1 and (latched is None if revert else
                                                      (latched == val and pend not in (None, "0")))
    log("live", tag, cv, val, "PASS" if rec["pass"] else "FAIL", rec)
    return rec


def scen_live(c, out, notes, maps, settle):
    bits = int(c.query("r_hzmLiveApply")[0] or "0")
    notes["liveBits"] = bits
    g = notes.setdefault("gates", {})
    orig = {cv: c.query(cv)[0] for cv, _a, _b, _bit in LIVE_FLIPS}
    notes["orig"] = orig
    notes["shots"] = {}
    # G1 each hook live (G0 at bits 0: nothing applies); captures around the two visible hooks for G2's sensitivity
    g["G1"] = []
    for cv, a, b, bit in LIVE_FLIPS:
        on = bool(bits & bit)
        if orig.get(cv) is not None:       # flip away from the boot value and back (a set to the current value
            b = orig[cv]                   # latches nothing, so it would prove nothing)
            a = a if a != b else ("1" if b == "0" else "0")
        if cv in ("r_sunShadows", "r_ppSSAO"):
            notes["shots"]["%s_before" % cv] = c.shots("live_%s_before" % cv, out)
        g["G1"].append(_live_flip(c, cv, a, "g1_%s_a" % cv, on))
        if cv in ("r_sunShadows", "r_ppSSAO"):
            notes["shots"]["%s_live" % cv] = c.shots("live_%s_live" % cv, out)
        g["G1"].append(_live_flip(c, cv, b, "g1_%s_b" % cv, on, revert=(b == orig.get(cv))))
    if not bits:
        start = c.step(["vid_restart"], "g0_vidrestart", timeout=120, retries=1)
        c.wait_log(r"\^~\^~\^ RKEEP path=", 120, start=start)
        time.sleep(settle / 2)
        notes["G0_pendingAfterRestart"] = c.query("r_hzmPendingRestart")[0]
        return
    # G2 live == restart: the SSAO-on frame after a live apply vs after a real vid_restart at the same value
    c.step(["set r_ppSSAO 1"], "g2_ssao_on")
    c.wait_log(r"LIVEAPPLY cvar=r_ppSSAO value=1", 8)
    notes["shots"]["r_ppSSAO_live_on"] = c.shots("live_ssao_liveon", out)
    start = c.step(["vid_restart"], "g2_vidrestart", timeout=120, retries=1)
    c.wait_log(r"\^~\^~\^ RKEEP path=", 120, start=start)
    time.sleep(settle)
    notes["shots"]["r_ppSSAO_restart_on"] = c.shots("live_ssao_restarton", out)
    # G3 repeatable: SSAO and sun shadows toggled 20x, 1 s apart; memory before/after
    m0 = c.mem()
    n0 = len(re.findall(r"LIVEAPPLY cvar=", c.read_log()))
    for k in range(20):
        c.step(["set r_ppSSAO %d" % (k % 2), "set r_sunShadows %d" % ((k + 1) % 2)], "g3_%02d" % k)
        time.sleep(1.0)
    time.sleep(3)
    txt = c.read_log()
    fbos = [int(x) for x in re.findall(r"LIVEAPPLY cvar=\S+ value=\S+ ms=\S+ images=\d+ fbos=(\d+)", txt)]
    imgs = [int(x) for x in re.findall(r"LIVEAPPLY cvar=\S+ value=\S+ ms=\S+ images=(\d+)", txt)]
    g["G3"] = {"memBefore": m0, "memAfter": c.mem(), "applies": len(re.findall(r"LIVEAPPLY cvar=", txt)) - n0,
               "fbosMax": max(fbos) if fbos else None, "imagesLast10": imgs[-10:]}
    g["G3"]["pass"] = g["G3"]["applies"] >= 40 and (g["G3"]["fbosMax"] or 0) <= 56 and len(set(imgs[-10:])) <= 1
    log("live G3", g["G3"])
    # G5 APPLY semantics: only hooked rows changed -> no restart; plus an un-hooked latch -> exactly one
    r0 = len(re.findall(r"RKEEP path=full reason=first", c.read_log()))
    c.step(["pushmenu advanced_graphics"], "g5_push")
    time.sleep(1.5)
    c.step(["set r_ext_max_anisotropy 4"], "g5_hooked")
    time.sleep(1.5)
    c.step(["ui_checkrestart"], "g5_apply1")
    time.sleep(6)
    r1 = len(re.findall(r"RKEEP path=full reason=first", c.read_log()))
    c.step(["popmenu 0", "pushmenu advanced_graphics"], "g5_push2")
    time.sleep(1.5)
    sub = c.query("r_subdivisions")[0] or "4"
    c.step(["set r_ext_max_anisotropy 16", "set r_subdivisions %s" % ("8" if sub != "8" else "4")], "g5_mixed")
    time.sleep(1.5)
    start = c.step(["ui_checkrestart"], "g5_apply2", timeout=120, retries=1)
    c.wait_log(r"\^~\^~\^ RKEEP path=", 120, start=start)
    time.sleep(settle / 2)
    r2 = len(re.findall(r"RKEEP path=full reason=first", c.read_log()))
    c.step(["popmenu 0", "set r_subdivisions %s" % sub], "g5_restore")
    g["G5"] = {"hookedOnlyRestarts": r1 - r0, "mixedRestarts": r2 - r1, "pass": (r1 - r0) == 0 and (r2 - r1) == 1}
    log("live G5", g["G5"])
    # G4 edges: hooks at the main menu (no world), then a map load straight after a live apply
    start = c.step(["disconnect"], "g4_disconnect", timeout=60, retries=1)
    time.sleep(8)
    g["G4"] = {"menu": [_live_flip(c, "r_sunShadows", "0", "g4_menu_sun", True),
                        _live_flip(c, "r_ppDoF", "1", "g4_menu_dof", True)]}
    c.step(["set ui_dmmap %s" % maps[0], "exec coop_mod/start_server.cfg"], "g4_restart_map", timeout=60, retries=1)
    ok = c.ready(c.wait_log(r"Detected Coop for", 400, start=start))
    time.sleep(settle)
    g["G4"]["mapAfter"] = bool(ok)
    g["G4"]["sunLine"] = [ln for ln in c.read_log()[start:].splitlines() if "sun bridge:" in ln][-1:]
    g["G4"]["pass"] = bool(ok) and all(r["pass"] for r in g["G4"]["menu"])
    # restore the boot values
    c.step(["set %s %s" % (cv, v) for cv, v in orig.items() if v is not None], "restore")
    time.sleep(3)


def run(argv):
    scen = argv[0]
    opts = dict(zip(argv[1::2], argv[2::2]))
    if verify(quiet=True):
        raise SystemExit("the private copy differs from the live binaries - run setup (and tell the coordinator)")
    renderer = opts.get("--renderer", "p2")
    renderer = "opengl2" if renderer == "stock" else "opengl2keep" + renderer
    if "--rname" in opts:          # a raw renderer name, e.g. opengl1live (renderer_opengl1live.dll) for the gl1 smoke
        renderer = opts["--rname"]
    keep = int(opts.get("--keep", "1"))
    probe = int(opts.get("--probe", "2"))
    maps = opts["--maps"].split(",") if "--maps" in opts else list(CYCLE14)
    tag = opts.get("--tag") or time.strftime("%s_%s_k%d_%%Y%%m%%d_%%H%%M" % (scen, renderer, keep))
    out = os.path.join(OUTROOT, tag)
    os.makedirs(out, exist_ok=True)
    settle = float(opts.get("--settle", "20"))
    extra = [tuple(kv.split("=", 1)) for kv in opts.get("--set", "").split(",") if "=" in kv]
    c = Client(opts.get("--exe", "keeptest"), renderer, keep, probe, opts.get("--res", "auto"), extra)
    notes = {"tag": tag, "scenario": scen, "renderer": renderer, "keep": keep, "probe": probe, "maps": maps,
             "t0": time.strftime("%Y-%m-%d %H:%M:%S"), "servers": [r["pid"] for r in hg.classify()
                                                                   if r["cls"] == "SERVER"], "steps": []}
    try:
        if not c.launch(maps[0]):
            raise RuntimeError("first map never became joinable")
        notes["cmdline"] = c.cmdline
        time.sleep(settle)
        notes["first"] = {"map": maps[0], "mem": c.mem()}
        if scen == "cycle":
            if int(opts.get("--shots", "1")):
                notes["first"]["shots"] = None  # the cycle takes step 0's frames itself
            scen_cycle(c, out, notes, maps, int(opts.get("--loops", "2")), int(opts.get("--shots", "1")), settle)
        elif scen == "vidrestart":
            scen_vidrestart(c, out, notes, maps, settle)
        elif scen == "latch":
            scen_latch(c, out, notes, maps, settle)
        elif scen == "fault":
            scen_fault(c, out, notes, maps, settle)
        elif scen == "timing":
            scen_timing(c, out, notes, maps, settle)
        elif scen == "live":
            scen_live(c, out, notes, maps, settle)
        else:
            raise SystemExit("unknown scenario " + scen)
    finally:
        c.kill()
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(out, "qconsole.log"))
        notes["t1"] = time.strftime("%Y-%m-%d %H:%M:%S")
        notes["window"] = c.window_report
        json.dump(notes, open(os.path.join(out, "notes.json"), "w"), indent=1)
        log("run folder:", out)


# ------------------------------------------------------------------------------------------------ report / diff
KV = re.compile(r"(\w+)=([^\s|]+)")


def parse_log(path):
    txt = open(path, "rb").read().decode("latin-1")
    ev = []
    for line in txt.splitlines():
        m = re.search(r"\^~\^~\^ (RKEEP\w*|RKSTEP) (.*)", line)
        if m:
            kv = dict(KV.findall(m.group(2)))
            kv["_k"] = m.group(1)
            kv["_raw"] = m.group(2)
            ev.append(kv)
            continue
        m = re.search(r"CL_InitCGame: ([\d.]+) seconds", line)
        if m:
            ev.append({"_k": "cgame", "s": float(m.group(1))})
        if "GLSL shaders (" in line:
            ev.append({"_k": "glsl", "_raw": line.strip()})
        if "Detected Coop for" in line:
            ev.append({"_k": "coop"})
    return ev


def report(runs):
    for r in runs:
        notes = json.load(open(os.path.join(r, "notes.json")))
        ev = parse_log(os.path.join(r, "qconsole.log"))
        print("=" * 100)
        print(notes["tag"], "| scenario", notes["scenario"], "| renderer", notes["renderer"], "| keep", notes["keep"])
        keeps = [e for e in ev if e["_k"] == "RKEEP"]
        asserts = [e for e in ev if e["_k"] == "RKEEPASSERT"]
        fails = [e for e in asserts if e.get("failed", "0") != "0"]
        print("G1 registrations: %d | path counts: %s | asserts %d, failing %d %s" % (
            len(keeps), {p: sum(1 for e in keeps if e.get("path") == p) for p in ("keep", "full")}, len(asserts),
            len(fails), [(e.get("reg"), e.get("first")) for e in fails][:6]))
        print("   reasons:", [(e.get("reg"), e.get("path"), e.get("reason"), e.get("ms")) for e in keeps])
        chk = sorted({int(e.get("checked", 0)) for e in asserts if e.get("path") == "keep"})
        print("   keep-path checked counts:", chk[:5])
        fast = [e for e in ev if e["_k"] == "RKEEPFAST"]
        if fast:
            print("   RKEEPFAST:", [(e.get("reg"), e.get("swept"), e.get("held"), e.get("notPerm"), e.get("vaos"),
                                     e.get("ms")) for e in fast])
        held = [e["_raw"] for e in ev if e["_k"] == "RKEEPHELD"]
        if held:
            print("   HELD (lifecycle bugs):", held[:8])
        worlds = [e for e in ev if e["_k"] == "RKEEPWORLD"]
        print("G2 world:", [(e.get("reg"), e.get("map"), e.get("lightmaps"), e.get("lmcrc"), e.get("roleFailed"))
                            for e in worlds])
        drift = [e for e in ev if e["_k"] == "RKEEPDRIFTSUM"]
        dfields = sorted({(e.get("struct"), e.get("field")) for e in ev if e["_k"] == "RKEEPDRIFT"})
        if drift:
            print("   drift:", [(e.get("reg"), e.get("tr"), e.get("backEnd"), e.get("glState")) for e in drift],
                  "fields:", dfields)
        mem = [(s.get("map"), (s.get("mem") or {}).get("gpuMB"), (s.get("mem") or {}).get("privMB"))
               for s in notes["steps"] if isinstance(s, dict) and s.get("mem")]
        print("G3 memory (map, gpuMB, privMB):", mem)
        walls = [(s.get("map"), s.get("wall")) for s in notes["steps"] if isinstance(s, dict) and s.get("wall")]
        print("timing (map, wall s):", walls)
        print("   RKEEP ms:", [e.get("ms") for e in keeps], "| cgame s:", [e["s"] for e in ev if e["_k"] == "cgame"])
        faults = [e["_raw"] for e in ev if e["_k"] == "RKEEPFAULT"]
        if faults:
            print("faults fired:", faults)


def _load(path):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)


def frame_diff(a, b, thr=12):
    import numpy as np
    d = np.abs(a - b).max(axis=2) > thr
    n = int(d.sum())
    region = 0
    if n:
        try:
            from scipy import ndimage
            lab, k = ndimage.label(d)
            region = int(np.bincount(lab.ravel())[1:].max()) if k else 0
        except ImportError:
            region = -1
    return n, round(100.0 * n / d.size, 4), region


def diff(argv):
    a, b = argv[0], argv[1]
    names = sorted(f for f in os.listdir(a) if f.endswith(".png") and os.path.exists(os.path.join(b, f)))
    print("%-40s %10s %8s %8s" % ("frame", "pixels", "pct", "region"))
    for f in names:
        n, pct, reg = frame_diff(_load(os.path.join(a, f)), _load(os.path.join(b, f)))
        print("%-40s %10d %8.4f %8d" % (f, n, pct, reg))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    if a[0] == "setup":
        setup()
    elif a[0] == "verify":
        verify()
    elif a[0] == "run":
        run(a[1:])
    elif a[0] == "report":
        report(a[1:])
    elif a[0] == "diff":
        diff(a[1:])
    else:
        raise SystemExit(__doc__)

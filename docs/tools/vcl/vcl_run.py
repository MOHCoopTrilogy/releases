#!/usr/bin/env python3
"""vcl_run.py - volumetric clouds in-engine gates (docs/proposals/volumetric_clouds_2026-09-26/plan.md 2.8, V4-V9).

A PRIVATE client in G:\\mohaa-vcltest (hash-verified copies of the live binaries in G:\\mohaa-gl2 under a distinct exe
name, the live data as fs_basepath, homepath G:\\mohaa-vcltest\\home seeded with a COPY of the user's omconfig.cfg) runs
the test renderers renderer_opengl2vcl.dll (the vcl tree) and renderer_opengl2vclbase.dll (the same snapshot built
without the feature, for V9). Modelled on docs/tools/rkeep/rkeep_client.py; every harness rule is kept:
  - the shared client slot (harness_guard.py, owner "clouds"); refuses while the user's game or another harness runs,
    and closes itself if the user's game appears;
  - launched ONLY through harness_window.launch_background (DISPLAY2, never activated, muted, mouse off, guard DLL);
  - <= 31 '+' commands (bug-2996); every map change / command sequence from an rcon-exec'd cfg (bug-3033/3034);
    cfg `wait N` is milliseconds (bug-2995); waits on log markers, never on cfg waits;
  - captures are the engine's own `screenshot` only (bug-3053); loopback only; never writes G:\\mohaa-gl2 (read
    only), a fixed-name DLL, build.ps1 or any install.
  - the coordinator's launch gate: nothing starts unless <scratchpad>\\test_slot.txt says exactly "clouds".

  python vcl_run.py setup --dll P1.dll --base BASE.dll    private copy + the two test renderers
  python vcl_run.py verify                                  private binaries still identical to the live ones?
  python vcl_run.py p1  [--tag T]                           V5 map cycle + CLOUDS/CLOUDSFRAMES asserts, V9 byte
                                                            identity (vcl r_hzmClouds 0 vs vclbase), look captures,
                                                            dither frame stacks (P2 J1'/grain input)
  python vcl_run.py report RUN                              the gate tables of a run
  python vcl_run.py wait-and-run --slot-file F [--tag T]    poll F; run `p1` + `report` once it says "clouds"
"""
import argparse, hashlib, json, os, re, shutil, socket, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

LIVE = r"G:\mohaa-gl2"
PRIV = r"G:\mohaa-vcltest"
HOME = os.path.join(PRIV, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTDIR = os.path.join(MAINTT, "screenshots")
RUNS = os.path.join(PRIV, "runs")
USER_CFG = os.path.join(LIVE, r"home\maintt\configs\omconfig.cfg")   # read (copied), never written
PORT = 12470
RCONPW = "vclpw"
MAGIC = b"\xff\xff\xff\xff"
OWNER = "clouds"
EXE = "openmohaa_vcltest.exe"
COPY = ["openmohaa.exe", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll", "SDL2.dll",
        "OpenAL64.dll", "libcurl.dll"]
SCOPE = os.path.normpath(os.path.join(HERE, "..", "..", "proposals", "volumetric_clouds_2026-09-26", "p0_stills",
                                      "scope.json"))
# V5 (plan 2.8): the 8 IN maps; the Omaha family and the user's exclusions; a Spearhead night map; a day map
V5_MAPS = ["co_lobby2", "co_lobby3", "dm/mohdm7", "m1l1", "m1l2a", "m1l2b", "m6l3a", "m6l3b",
           "m3l1a", "m3l1b", "m3l2", "m3l3", "e3l1", "e3l2", "t1l1", "m2l1"]
# the P0 scenes (p0_stills/tools/vc_v2.py SCENES): eye, yaw, elevation. The dome is eye-centred, so only the view
# direction matters for the sky; the position only decides what geometry is in front. Standing view height 82.
SPOTS = {
    "01_zenith_camp": dict(map="co_lobby2", eye=(-6434.0, 2178.0, 594.0), yaw=178.0, el=89.0),
    "02_toward_moon_mohdm7": dict(map="dm/mohdm7", eye=(-3312.0, 3120.0, 368.0), yaw=68.0, el=22.0),
    "03_away_m1l1": dict(map="m1l1", eye=(-2682.0, -3235.0, 200.0), yaw=205.0, el=22.0),
    "04_day_m2l1": dict(map="m2l1", eye=None, yaw=None, el=30.0),          # OUT map: V9 on a non-profile sky
}
DITHER_SPOTS = ["01_zenith_camp", "02_toward_moon_mohdm7"]
DITHER_AMPS = ["0", "0.5", "0.75", "1.0"]
STACK = 12
SLOT_WORD = "clouds"

# ---- the fog harness recipe (docs/proposals/fog_lod_pop_2026-09-27/tools/fogtest_run.py, bug-3182), shared traps:
# - the god cheat's console name is "dog": `god` is only a forwarder (gamecmds.cpp gi.AddCommand("god", NULL)) with no
#   Event, so it silently does nothing. With an ARGUMENT dog / notarget SET the flag (bare they TOGGLE); the engine's
#   own "CHEAT: godmode ON" is REQUIRED in the log (Client.protect).
# - ui_startdmmap (start_server.cfg) forces cheats 0: latch `cheats 1` and restart the SAME map via SV_Map_f
#   (developer 1 keeps cheats), or tele / face / dog are refused.
# - the coop spawn comes up to ~15 s after "has joined the Allies"; a tele to a not-yet-spawned player is dropped:
#   retry tele + viewpos until the view lands (Client.goto).
# - g_ai 0 (Actor::Think returns at once: no fire, grenades or officer hunt), DBNO / tinnitus / ambience off, the
#   game-message box off, and coop_dynWeather 0 (weather would also change the sky between the two DLL runs).
# - the crosshair is ui_crosshair (cg_drawcrosshair does not exist); cg_draw2D is not used.
GOD = ["dog 1", "notarget 1"]
BOOT_BASE = ["set g_gametype 2", "set in_mouse 0", "set thereisnomonkey 1", "set cheats 1", "set coop_dynWeather 0"]
QUIET_BOOT = ["set g_ai 0", "set coop_dbno 0", "set coop_ambience 0", "set coop_tinnitus 0", "set coop_tinnitusBlast 0",
              "set ui_gmbox 0", "ui_checkrestart"]
VIEW = ["r_drawentities 0", "cg_drawviewmodel 0", "set ui_crosshair 0", "ui_hud 0", "set ui_gmbox 0", "ui_checkrestart",
        "set r_ppHitAmount 0", "set r_ppHitBlood 0", "set r_ppBloodFx 0", "set r_ppLowHealth 0", "set coop_dizzy 0",
        "cl_noprint 1"]
VIEW_OFF = ["r_drawentities 1", "cg_drawviewmodel 1", "ui_hud 1", "cl_noprint 0"]
JOIN = ["popmenu 0", "wait 10", "primarydmweapon rifle", "wait 5", "set g_teamswitchdelay 0", "join_team allies",
        "wait 20", "popmenu 0", "wait 40", "popmenu 0", "wait 20", "+attackprimary", "wait 10", "-attackprimary"]
CONTAM = re.compile(r"[^\r\n]*(DBNO down|SHELLSHOCK|You are DOWN|\bdied\b|Spawn protection|BAD FAILSAFE|godmode OFF)[^\r\n]*")
VIEW_HEIGHT = 82


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def slot_ok(slot_file):
    try:
        return open(slot_file, encoding="utf-8", errors="replace").read().strip() == SLOT_WORD
    except OSError:
        return False


# ------------------------------------------------------------------------------------------------ setup / verify
def real_user_game():
    """the user's own game by PATH (classify() also calls an unregistered harness copy USER, which is right for a
    launch - nothing may start next to it - but setup only copies files out of the live install)"""
    users = {hg._norm(p) for p in hg.USER_EXES}
    return [r["pid"] for r in hg.classify() if hg._norm(r.get("path")) in users]


def setup(dll, base):
    if real_user_game():
        raise SystemExit("the user's game is running - not touching anything")
    for p in (dll, base):
        if not os.path.exists(p):
            raise SystemExit("missing " + p)
    if b"HZM_VCL=test" not in open(dll, "rb").read():
        raise SystemExit("the vcl DLL has no HZM_VCL=test marker: " + dll)
    if b"HZM_VCL=test" in open(base, "rb").read():
        raise SystemExit("the base DLL carries the feature: " + base)
    os.makedirs(PRIV, exist_ok=True)
    man = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {}, "test": {}}
    for fn in COPY:
        src = os.path.join(LIVE, fn)
        if not os.path.exists(src):
            raise SystemExit("missing in the live install: " + src)
        dst = os.path.join(PRIV, EXE if fn == "openmohaa.exe" else fn)
        h = sha(src)
        shutil.copyfile(src, dst)
        if sha(dst) != h:
            raise SystemExit("copy mismatch " + dst)
        man["files"][os.path.basename(dst)] = {"src": src, "sha256": h}
    for name, src in (("renderer_opengl2vcl.dll", dll), ("renderer_opengl2vclbase.dll", base)):
        dst = os.path.join(PRIV, name)
        shutil.copyfile(src, dst)
        man["test"][name] = {"src": src, "sha256": sha(dst)}
    json.dump(man, open(os.path.join(PRIV, "manifest.json"), "w"), indent=1)
    log("private copy ready:", PRIV, man["test"])


def verify(quiet=False):
    try:
        man = json.load(open(os.path.join(PRIV, "manifest.json")))
    except (OSError, ValueError):
        raise SystemExit("no manifest - run setup")
    bad = []
    for fn, rec in list(man["files"].items()) + list(man["test"].items()):
        mine = sha(os.path.join(PRIV, fn)) if os.path.exists(os.path.join(PRIV, fn)) else None
        live = sha(rec["src"]) if os.path.exists(rec["src"]) else None
        if mine != rec["sha256"]:
            bad.append((fn, "private changed"))
        elif fn in man["files"] and live != rec["sha256"]:
            bad.append((fn, "live changed"))
    if not quiet:
        log("verify:", "OK" if not bad else bad)
    return bad, man


# ------------------------------------------------------------------------------------------------ the client
class Client:
    def __init__(self, renderer, slot_file=None):
        self.renderer = renderer
        self.exe = os.path.join(PRIV, EXE)
        self.slot_file = slot_file
        self.pid = None
        self.bg = None
        self.window_report = None
        self.last_rcon = 0.0

    def guard(self):
        if hg.user_game_running():
            log("USER GAME RUNNING - closing our client and stopping")
            self.kill()
            raise SystemExit(3)

    def alive(self):
        return self.pid is not None and any(r["pid"] == self.pid for r in hg.classify())

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
        last = 0
        while time.time() - t0 < timeout:
            if time.time() - last > 5:
                self.guard()
                last = time.time()
            m = rx.search(self.read_log(), start)
            if m:
                return m
            if not self.alive():
                return None
            time.sleep(0.5)
        return None

    def rcon(self, command, timeout=1.5, settle=0.35):
        gap = time.time() - self.last_rcon
        if gap < 1.2:
            time.sleep(1.2 - gap)
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
        """lines -> vclstep.cfg, rcon execs it (runs from the command buffer, so it all reaches qconsole.log)"""
        mk = "^~^~^ VCLSTEP %s" % tag
        with open(os.path.join(MAINTT, "vclstep.cfg"), "w", newline="\n") as f:
            f.write("\n".join(list(lines) + ["echo %s" % mk]) + "\n")
        start = len(self.read_log())
        for attempt in range(retries):
            self.rcon("exec vclstep.cfg")
            if self.wait_log(re.escape(mk), 12 if attempt < retries - 1 else timeout, start=max(0, start - 10)):
                return start
            time.sleep(1.5)
        raise RuntimeError("step %s never ran" % tag)

    def launch(self, first_map):
        self.guard()
        if self.slot_file and not slot_ok(self.slot_file):
            raise SystemExit("test_slot.txt does not say %r - not launching" % SLOT_WORD)
        others = [r for r in hg.classify() if r["cls"] in ("HARNESS", "USER")]
        if others:
            raise SystemExit("another client is running: %s" % others)
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
        dl, dt, dr, db = hw.test_display()["rect"]
        w, h = str(dr - dl), str(db - dt)
        sets = [
            ("com_target_game", "2"), ("fs_basepath", LIVE), ("fs_homepath", HOME),
            ("r_mode", "-1"), ("r_customwidth", w), ("r_customheight", h), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_ip", "127.0.0.1"), ("net_port", str(PORT)),
            ("rconPassword", RCONPW), ("cl_renderer", self.renderer),
            ("r_hzmClouds", "1"), ("r_hzmCloudsProbe", "1"), ("r_gfxLabel", "0"),
        ]
        args = [self.exe]
        for k, v in sets:
            args += ["+set", k, v]
        args += ["+exec", "vclboot.cfg"]
        try:
            args, late = hw.apply_policy(args)
        except hw.PolicyError as e:
            raise SystemExit(str(e))
        boot = BOOT_BASE + QUIET_BOOT + late + ["set ui_dmmap %s" % first_map, "exec coop_mod/start_server.cfg"]
        with open(os.path.join(MAINTT, "vclboot.cfg"), "w", newline="\n") as f:
            f.write("\n".join(boot) + "\n")
        nplus = sum(1 for a in args if a.startswith("+"))
        if nplus > 31:
            raise SystemExit("command line has %d '+' commands (bug-2996)" % nplus)
        hg.acquire_slot(OWNER, self.exe, HOME, [PORT], minutes=180)
        self.bg = hw.launch_background(self.exe, args[1:], PRIV, policy=False, log=log)
        self.pid = self.bg.pid
        hg.set_slot_pid(OWNER, self.pid)
        log("launched", EXE, "renderer", self.renderer, "(%d '+')" % nplus)
        # bug-3179: a renderer that cannot build a program dies with "Could not load <x> shader!" - abort, never retry
        m = self.wait_log(r"Could not load[^\r\n]*|Detected Coop for", 400, start=0)
        bad = re.search(r"Could not load[^\r\n]*", self.read_log())
        if bad:
            raise SystemExit("ABORT renderer start failed: %s" % bad.group(0))
        if not m:
            return None
        # ui_startdmmap forced cheats 0: latch cheats 1 and restart the same map through SV_Map_f
        time.sleep(2)
        start0 = len(self.read_log())
        if re.search(r'"cheats" is\s*:?\s*"\s*0', self.rcon("cheats")):
            self.rcon("set cheats 1")
            time.sleep(0.5)
            self.step(["map %s" % first_map], "cheats_restart", retries=1, timeout=30)
            if not self.wait_log(r"Detected Coop for", 400, start=start0):
                return None
        return True

    def join(self):
        """the mod's own team join, until the log says the player joined"""
        start = len(self.read_log()) - 4000
        time.sleep(5)
        for k in range(4):
            if re.search(r"has joined the (Allies|Axis)", self.read_log()[max(0, start):]):
                return True
            self.step(JOIN, "join%d" % k)
            self.wait_log(r"has joined the (Allies|Axis)", 20, start=max(0, start))
        return bool(re.search(r"has joined the (Allies|Axis)", self.read_log()[max(0, start):]))

    def where(self):
        s = self.step(["viewpos"], "viewpos")
        m = re.findall(r"\((-?\d+) (-?\d+) (-?\d+)\) : (-?\d+)", self.read_log()[s:])
        return [int(v) for v in m[-1]] if m else None

    def protect(self):
        """dog 1 + notarget 1, and REQUIRE the engine's own "CHEAT: godmode ON" (bug-3182)"""
        for k in range(3):
            s = self.step(GOD, "god%d" % k)
            if self.wait_log(r"CHEAT: godmode ON", 10, start=max(0, s - 10)):
                return True
        raise RuntimeError("godmode never confirmed (no 'CHEAT: godmode ON' after dog 1)")

    def goto(self, eye, pitch, yaw, timeout=90):
        """tele (feet = eye - view height) + face, retried until viewpos lands (a tele before the spawn is dropped).
        eye None = stay where the spawn put us, only face. Returns the landed viewpos."""
        t0 = time.time()
        vp = None
        while time.time() - t0 < timeout:
            lines = []
            if eye:
                lines.append("tele %d %d %d" % (eye[0], eye[1], eye[2] - VIEW_HEIGHT))
            lines += ["face %d %d 0" % (pitch, yaw), "wait 800"]
            self.step(lines, "goto")
            vp = self.where()
            if vp and (eye is None or (abs(vp[0] - eye[0]) < 24 and abs(vp[1] - eye[1]) < 24)):
                return vp
            time.sleep(2.0)
        raise RuntimeError("never landed at %s (viewpos %s)" % (eye, vp))

    def ready(self, eye=None, pitch=-60, yaw=0):
        """joined, spawned at the pose, godmode confirmed, view cvars set"""
        self.join()
        time.sleep(8)
        vp = self.goto(eye, pitch, yaw)
        self.protect()
        self.step(VIEW, "view")
        return vp

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
            self.bg.close(grace=5)
            wrep = self.bg.report()
            self.window_report = {k: wrep.get(k) for k in ("test_display", "clean", "violations", "enforced", "guard")}
            if not wrep.get("clean", True):
                log("WINDOW POLICY VIOLATIONS:", wrep.get("violations"))
            self.bg = None
        hg.release_slot(OWNER)

    def load_map(self, mapname, tag):
        """map change from a cfg; ready = the server finished AND (the coop marker, or 40 s for maps without one).
        Returns (this load's ^~^~^ CLOUDS line or None, the log offset before the change)."""
        start = self.step(["map %s" % mapname], tag, timeout=180, retries=1)
        base = mapname.split("/")[-1]
        if not self.wait_log(r"Server Initialization Complete", 400, start=start):
            return None, start
        self.wait_log(r"Detected Coop for", 40, start=start)
        m = self.wait_log(r"\^~\^~\^ CLOUDS map=%s [^\n]*" % re.escape(base),
                          5 if self.renderer.endswith("base") else 30, start=start)
        return (m.group(0) if m else None), start

    def shot(self, name, outdir, pre=(), post=()):
        tga = os.path.join(SHOTDIR, name + ".tga")
        if os.path.exists(tga):
            os.remove(tga)
        self.step(list(pre) + ["wait 700", "screenshot %s" % name, "wait 300"] + list(post), "shot_" + name)
        return self.collect(name, outdir)

    def collect(self, name, outdir, keep_tga=False):
        tga = os.path.join(SHOTDIR, name + ".tga")
        t0 = time.time()
        while not os.path.exists(tga) and time.time() - t0 < 20:
            time.sleep(0.4)
        if not os.path.exists(tga):
            return None
        time.sleep(0.8)
        from PIL import Image
        png = os.path.join(outdir, name + ".png")
        Image.open(tga).save(png)
        os.remove(tga)
        return os.path.basename(png)


# ------------------------------------------------------------------------------------------------ scenario
def oracle():
    d = json.load(open(SCOPE))
    return {r["map"][len("maps/"):-len(".bsp")]: r["klass"] for r in d["maps"]}


def parse_clouds(line):
    return dict(kv.split("=", 1) for kv in line.split()[2:] if "=" in kv) if line else {}


def expected_reason(mapname):
    base = mapname.split("/")[-1]
    if base in ("m3l1a", "m3l1b", "e3l1", "e3l2", "e3l1_sml", "e3l2_sml"):
        return "deny:omaha"
    if base == "m3l2":
        return "deny:user-m3l2"
    if base == "m3l3":
        return "deny:user-m3l3"
    return None


def spot_pose(sp):
    """MOHAA pitch is negative UP"""
    return sp["eye"], -int(round(sp["el"])), int(round(sp["yaw"] if sp["yaw"] is not None else 0))


def run_vcl(c, out, notes):
    orc = oracle()
    # ---- V5: the map cycle (r_hzmClouds 1 from the command line, so each load line states on/off and why)
    first = c.read_log()
    m = re.search(r"\^~\^~\^ VCLBUILD [^\n]*", first)
    notes["vclbuild"] = m.group(0) if m else None
    for i, mp in enumerate(V5_MAPS):
        if i == 0:
            m = re.search(r"\^~\^~\^ CLOUDS map=co_lobby2 [^\n]*", c.read_log())
            line, start = (m.group(0) if m else None), 0
        else:
            line, start = c.load_map(mp, "v5_%02d" % i)
        rec = {"map": mp, "clouds": line, "oracle": orc.get(mp), "fields": parse_clouds(line)}
        if line:
            if rec["oracle"] == "IN":
                # look 60 deg up from the spawn so the sky is in view (joined, spawned, godmode confirmed)
                try:
                    c.ready(eye=None, pitch=-60, yaw=0)
                except RuntimeError as e:
                    rec["ready_error"] = str(e)
                c.step(["wait 6000"], "v5look_%02d" % i, timeout=40)
            frames = re.findall(r"\^~\^~\^ CLOUDSFRAMES map=%s [^\n]*" % re.escape(mp.split("/")[-1]),
                                c.read_log()[start:])
            rec["frames"] = frames[-1] if frames else None
            rec["script_errors"] = len(re.findall(r"Script Error", c.read_log()[start:]))
        f = rec["fields"]
        want_on = rec["oracle"] == "IN"
        ok = bool(line) and (f.get("state") == "on") == want_on
        if ok and expected_reason(mp):
            ok = f.get("reason") == expected_reason(mp)
        if ok and not want_on and not expected_reason(mp):
            ok = f.get("reason") in ("no-profile-sky",)
        if ok and want_on:
            fr = parse_clouds(rec.get("frames")) if rec.get("frames") else {}
            rec["composited"] = int(fr.get("composited", 0) or 0)
        rec["ok"] = ok
        notes["v5"].append(rec)
        log("V5", mp, "OK" if ok else "FAIL", line, rec.get("frames"))
    # the live switch: one CLOUDS line per change (plan 2.2)
    line, start = c.load_map("co_lobby2", "v5_toggle_load")
    s1 = c.step(["r_hzmClouds 0", "wait 1500"], "tog0")
    off = c.wait_log(r"\^~\^~\^ CLOUDS map=co_lobby2 [^\n]*state=off reason=off-switch", 20, start=s1)
    s2 = c.step(["r_hzmClouds 1", "wait 1500"], "tog1")
    on = c.wait_log(r"\^~\^~\^ CLOUDS map=co_lobby2 [^\n]*state=on", 20, start=s2)
    notes["toggle"] = {"off_line": bool(off), "on_line": bool(on)}

    # ---- spots: V9 (off), the look (on, debug 1, debug 4), frozen time (r_gfxProbe 2 -> refdef.time 100000)
    for name, sp in SPOTS.items():
        c.load_map(sp["map"], "spot_" + name)
        rec = {"spot": name}
        rec["viewpos"] = c.ready(*spot_pose(sp))
        s0 = len(c.read_log())
        pre = ["r_gfxProbe 2"]
        rec["off_a"] = c.shot("v9_%s_vcl_off_a" % name, out, pre=pre + ["r_hzmClouds 0", "r_hzmCloudsDebug 0"])
        time.sleep(2)
        rec["off_b"] = c.shot("v9_%s_vcl_off_b" % name, out, pre=["r_hzmClouds 0"])
        rec["on"] = c.shot("look_%s_on" % name, out, pre=["r_hzmClouds 1"])
        rec["dbg1"] = c.shot("look_%s_dbg1" % name, out, pre=["r_hzmCloudsDebug 1"])
        rec["dbg4"] = c.shot("look_%s_dbg4" % name, out, pre=["r_hzmCloudsDebug 4"], post=["r_hzmCloudsDebug 0"])
        if name in DITHER_SPOTS:
            # consecutive frames of the frozen scene: the animated dither is the only thing that changes (P2 input
            # for in-engine J1' on the temporal mean and for the still-camera grain)
            rec["stacks"] = {}
            for amp in ["old"] + DITHER_AMPS:
                sw = ["r_hzmClouds 0"] if amp == "old" else ["r_hzmClouds 1", "r_hzmCloudsDither %s" % amp]
                names = ["st_%s_%s_%02d" % (name, amp.replace(".", "p"), k) for k in range(STACK)]
                lines = sw + ["wait 700"]
                for n in names:
                    lines += ["screenshot %s" % n, "wait 20"]
                c.step(lines, "stack_%s_%s" % (name, amp), timeout=90)
                rec["stacks"][amp] = [c.collect(n, out) for n in names]
            c.step(["r_hzmCloudsDither 0.5"], "dither_reset")
        c.step(["r_gfxProbe 0"] + VIEW_OFF, "unfreeze_" + name)
        rec["contamination"] = [m.group(0) for m in CONTAM.finditer(c.read_log()[s0:])]
        notes["spots"].append(rec)
        log("spot", name, {k: v for k, v in rec.items() if k != "stacks"})


def run_base(c, out, notes):
    for name, sp in SPOTS.items():
        c.load_map(sp["map"], "bspot_" + name)
        rec = {"spot": name, "viewpos": c.ready(*spot_pose(sp))}
        s0 = len(c.read_log())
        rec["base_a"] = c.shot("v9_%s_base_a" % name, out, pre=["r_gfxProbe 2"])
        time.sleep(2)
        rec["base_b"] = c.shot("v9_%s_base_b" % name, out)
        c.step(["r_gfxProbe 0"] + VIEW_OFF, "bunfreeze_" + name)
        rec["contamination"] = [m.group(0) for m in CONTAM.finditer(c.read_log()[s0:])]
        notes["base_spots"].append(rec)
        log("base spot", name, rec)


def p1(tag, slot_file=None):
    bad, man = verify(quiet=True)
    if bad:
        raise SystemExit("private copy differs: %s (run setup)" % bad)
    run = os.path.join(RUNS, time.strftime("%Y%m%d_%H%M%S") + ("_" + tag if tag else ""))
    os.makedirs(run, exist_ok=True)
    notes = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "manifest": man, "v5": [], "spots": [], "base_spots": []}
    try:
        for renderer, fn in (("opengl2vcl", run_vcl), ("opengl2vclbase", run_base)):
            c = Client(renderer, slot_file)
            try:
                ok = c.launch("co_lobby2")
                notes.setdefault("launch", {})[renderer] = bool(ok)
                if not ok:
                    log("launch of", renderer, "never reached 'Detected Coop for'")
                if ok:
                    time.sleep(10)
                    fn(c, run, notes)
            finally:
                logtxt = c.read_log()
                open(os.path.join(run, "qconsole_%s.log" % renderer), "w", encoding="latin-1").write(logtxt)
                c.kill()
                notes.setdefault("window", {})[renderer] = c.window_report
    finally:
        json.dump(notes, open(os.path.join(run, "notes.json"), "w"), indent=1, default=str)
        log("run folder", run)
    return run


# ------------------------------------------------------------------------------------------------ report
def tga_equal(a, b):
    from PIL import Image
    import numpy as np
    A = np.asarray(Image.open(a).convert("RGB"), np.int16)
    B = np.asarray(Image.open(b).convert("RGB"), np.int16)
    if A.shape != B.shape:
        return {"equal": False, "why": "shape"}
    d = np.abs(A - B).max(-1)
    return {"equal": bool((d == 0).all()), "px_diff": int((d > 0).sum()), "max": int(d.max())}


def report(run):
    notes = json.load(open(os.path.join(run, "notes.json")))
    res = {"run": run, "vclbuild": notes.get("vclbuild"), "launch": notes.get("launch"), "window": notes.get("window")}
    v5 = notes.get("v5", [])
    res["V5"] = {"maps": len(v5), "fail": [r["map"] for r in v5 if not r.get("ok")],
                 "in_not_composited": [r["map"] for r in v5 if r.get("oracle") == "IN" and not r.get("composited")],
                 "script_errors": sum(r.get("script_errors", 0) for r in v5), "toggle": notes.get("toggle")}
    v9 = {}
    base = {r["spot"]: r for r in notes.get("base_spots", [])}
    for r in notes.get("spots", []):
        b = base.get(r["spot"], {})
        pa = lambda k, d=r: os.path.join(run, d[k]) if d.get(k) else None  # noqa: E731
        ent = {}
        if r.get("off_a") and r.get("off_b"):
            ent["vcl_off_a_vs_b (floor)"] = tga_equal(pa("off_a"), pa("off_b"))
        if b.get("base_a") and b.get("base_b"):
            ent["base_a_vs_b (floor)"] = tga_equal(pa("base_a", b), pa("base_b", b))
        if r.get("off_a") and b.get("base_a"):
            ent["vcl_off_vs_base (V9)"] = tga_equal(pa("off_a"), pa("base_a", b))
        v9[r["spot"]] = ent
    res["V9"] = v9
    json.dump(res, open(os.path.join(run, "report.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
    return res


def wait_and_run(slot_file, tag, poll=30):
    if not lint():
        raise SystemExit("the harness command lint fails - not arming")
    log("waiting for %s to say %r (polling every %d s)" % (slot_file, SLOT_WORD, poll))
    while True:
        if slot_ok(slot_file) and not hg.user_game_running() and hg.slot_holder() in (None,) \
                and not [r for r in hg.classify() if r["cls"] == "HARNESS"]:
            log("slot is %r - starting" % SLOT_WORD)
            break
        time.sleep(poll)
    run = p1(tag, slot_file)
    report(run)


TREES = [r"C:\mohaa-coop-dev\openmohaa-hzm\code", r"C:\mohaa-coop-dev\openmohaa-hzm-vcl\code"]
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
BUILTIN = {"set", "seta", "exec", "wait", "echo", "map", "quit", "vstr"}


def lint():
    """fogtest_lint.py's method (bug-3182): a client command must be a real game Event the console may call
    (EV_CONSOLE / EV_CHEAT); a name that only gi.AddCommand(name, NULL) registers is a forwarder and does nothing"""
    import glob
    events, cmds, fwd, cvars = {}, set(), set(), set()
    for root in TREES:
        for ext in ("c", "cpp", "h"):
            for fp in glob.glob(os.path.join(root, "**", "*." + ext), recursive=True):
                t = open(fp, "rb").read().decode("latin-1")
                for m in re.finditer(r'\bEvent\s+\w+\s*\(\s*"([^"]+)"\s*,\s*([^,]+),', t):
                    events.setdefault(m.group(1).lower(), set()).add(m.group(2).strip())
                for m in re.finditer(r'\b(?:Cmd_AddCommand|gi\.AddCommand|cgi\.AddCommand|ri\.Cmd_AddCommand)\s*\(\s*"([^"]+)"\s*,\s*(\w+)', t):
                    (fwd if m.group(2) == "NULL" else cmds).add(m.group(1).lower())
                for m in re.finditer(r'\{\s*"(\w+)"\s*,\s*&?\w+_f\s*\}', t):
                    cmds.add(m.group(1).lower())
                for m in re.finditer(r'\b(?:Cvar_Get|gi\.Cvar_Get|cgi\.Cvar_Get|ri\.Cvar_Get|uii\.Cvar_Get|CvarGetForUI|'
                                     r'Cvar_VariableString|Cvar_VariableIntegerValue|Cvar_VariableValue)\s*\(\s*"([^"]+)"', t):
                    cvars.add(m.group(1).lower())
    for fp in glob.glob(os.path.join(MOD, "**", "*.scr"), recursive=True):
        for m in re.finditer(r'getcvar\s*\(?\s*"([^"]+)"', open(fp, "rb").read().decode("latin-1"), re.I):
            cvars.add(m.group(1).lower())
    lines = BOOT_BASE + QUIET_BOOT + GOD + VIEW + VIEW_OFF + JOIN + [
        "tele 0 0 0", "face 0 0 0", "viewpos", "screenshot x", "cheats", "set cheats 1", "r_gfxProbe 2",
        "r_hzmClouds 0", "r_hzmCloudsDebug 1", "r_hzmCloudsDither 0.5", "r_hzmCloudsProbe 1", "set ui_dmmap x",
        "exec coop_mod/start_server.cfg"]
    bad = []
    for ln in lines:
        w = ln.split()
        name = w[0].lower()
        if name in BUILTIN and name not in ("set", "seta"):
            continue
        if name in ("set", "seta"):
            if w[1].lower() not in cvars:
                bad.append((ln, "cvar '%s' is read nowhere" % w[1]))
            continue
        if name in cmds or name.lstrip("+-") in cmds or ("+" + name.lstrip("+-")) in cmds or name in cvars:
            continue
        if name in events:
            if not any(("EV_CONSOLE" in f or "EV_CHEAT" in f) for f in events[name]):
                bad.append((ln, "event flags %s - refused from the console" % events[name]))
            continue
        bad.append((ln, "forwarder only - no Event implements it" if name in fwd else "unknown"))
    for ln, why in bad:
        print("LINT FAIL  %-28s %s" % (ln, why))
    caught = "god" in fwd and "god" not in events
    print("lint: %d lines, %d bad; the old bare 'god' %s" % (len(lines), len(bad),
          "would be CAUGHT (forwarder only)" if caught else "would NOT be caught"))
    return not bad and caught


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["setup", "verify", "p1", "report", "wait-and-run", "lint"])
    ap.add_argument("run", nargs="?")
    ap.add_argument("--dll")
    ap.add_argument("--base")
    ap.add_argument("--tag", default="")
    ap.add_argument("--slot-file")
    a = ap.parse_args()
    if a.cmd == "setup":
        setup(a.dll, a.base)
    elif a.cmd == "verify":
        verify()
    elif a.cmd == "p1":
        if not a.slot_file or not slot_ok(a.slot_file):
            raise SystemExit("p1 needs --slot-file saying %r" % SLOT_WORD)
        report(p1(a.tag, a.slot_file))
    elif a.cmd == "report":
        report(a.run)
    elif a.cmd == "lint":
        sys.exit(0 if lint() else 1)
    elif a.cmd == "wait-and-run":
        if not a.slot_file:
            raise SystemExit("--slot-file is required")
        wait_and_run(a.slot_file, a.tag)


if __name__ == "__main__":
    main()

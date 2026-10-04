"""m3l2g_ingame.py - in-engine before/after for the m3l2 ground (docs/proposals/m3l2_ground_2026-09-29).

    python m3l2g_ingame.py setup                 seed the private home (no run)
    python m3l2g_ingame.py run [set ...]         sets: gl2_before gl2_after gl1_before gl1_after (default: all four)
    python m3l2g_ingame.py wait-and-run          wait for SCRATCHPAD\\test_slot.txt == "m3l2ground", run all, write "free"

Private client G:\\mohaa-m3l2ground = byte copies of the LIVE set read from G:\\mohaa-gl2 (exe 90e47187, cgame
0a0bb3b4, gl2 11df592f, gl1 4d25ba48; never written). Registered in docs/tools/harness_guard.py as owner "m3l2ground".
Basepath = the GOG tree, read only. Homepath G:\\mohaa-m3l2ground\\home (fresh: no qkey, no saves; the settings config
is the live omconfig.cfg - the user's graphics settings, r_ext_compressed_textures 1). Launch ONLY through
harness_window.launch_background (DISPLAY2, never focused, muted, guard + job), net_ip 127.0.0.1, net_port 12549,
com_maxfps 60. Captures: the engine `screenshot` only.

BEFORE = the player stack as installed. AFTER = the same + the staged ../staged/zzzzzzzzzz_coop_m3l2ground.pk3 in the
home maintt (a homepath pak mounts above every basepath pak). The camera is the gv_ingame.py overlay recipe (the
DEPLOYED coop_mod/weather.scr + a camera thread; no cheats, no map restart); weather pinned calm (coop_weatherPin 0)
so both runs light identically.
"""
import json, math, os, re, shutil, socket, subprocess, sys, time, zipfile

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-m3l2ground"
EXE = os.path.join(CLIENT, "openmohaa_m3l2ground.exe")
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
PRISTINE = os.path.join(CLIENT, "pristine")
USER_LOOSE = ["autoexec.cfg", "coop_defaults.cfg", "whatsnew_pending.cfg"]
OVERLAY = "zzzzzzzzzzzz_m3l2g_cam.pk3"
CANDIDATE = os.path.join(PROP, "staged", "zzzzzzzzzz_coop_m3l2ground.pk3")
RUNS = os.path.join(CLIENT, "runs")
SCRATCH = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad"
SLOTFILE = os.path.join(SCRATCH, "test_slot.txt")
OWNER = "m3l2ground"
PORT = 12549
RCONPW = "m3l2gpw"
MAGIC = b"\xff\xff\xff\xff"
DEPLOYED = os.path.join(GOG, "maintt", "zzzzzz_co-op_hzm_mod_code.pk3")
VIEWSFILE = os.path.join(PROP, "work", "views_ingame.json")
CLIENT_H = {"c": None, "proc": None}
SETS = {"gl2_before": ("opengl2", False, "m3l2"), "gl2_after": ("opengl2", True, "m3l2"),
        "gl1_before": ("opengl1", False, "m3l2"), "gl1_after": ("opengl1", True, "m3l2"),
        # a map that shares m3l3grass_bocroad: must render identically with and without the pak
        "m3l3_gl2_before": ("opengl2", False, "m3l3"), "m3l3_gl2_after": ("opengl2", True, "m3l3")}
MOTION = ("m3l2_court_barnfront", "m3l2_barnyard")      # short forward walk: shimmer / mip check


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


class Aborted(Exception):
    pass


HOOK_OLD = "\twaitthread coop_mod/duststorm.scr::coop_dust_boot\n"
HOOK_NEW = HOOK_OLD + "\tif( getcvar( \"coop_mgTestPoll\" ) == \"1\" ){ thread coop_mg_cam }\t//TEST OVERLAY ONLY\n"
FUNC = """
//TEST OVERLAY ONLY (docs/proposals/m3l2_ground_2026-09-29/tools/m3l2g_ingame.py): coop_mgCamSeq changing applies
//coop_mgCamX/Y/Z (feet) and coop_mgCamP/W (view) to player 1; frozen, ignored by the AI, unhurt; pose held every frame.
coop_mg_cam:{
	local.last = ""
	local.frozen = 0
	println( "^~^~^ MGCAM ready" )
	while( 1 ){
		local.s = getcvar( "coop_mgCamSeq" )
		if( local.s != "" && local.s != local.last && $player != NULL && $player.size >= 1 ){
			local.last = local.s
			local.p = $player[1]
			if( local.frozen == 0 ){
				local.p physics_off
				local.p nodamage
				local.p notarget 1
				local.frozen = 1
			}
			local.p unglue
			local.p unbind
			local.p.parent = NULL
			local.x = float( getcvar( "coop_mgCamX" ) )
			local.y = float( getcvar( "coop_mgCamY" ) )
			local.z = float( getcvar( "coop_mgCamZ" ) )
			local.a = float( getcvar( "coop_mgCamP" ) )
			local.b = float( getcvar( "coop_mgCamW" ) )
			local.p.origin = ( local.x local.y local.z )
			local.p.viewangles = ( local.a local.b 0 )
		}
		if( local.frozen == 1 && $player != NULL && $player.size >= 1 ){
			$player[1].origin = ( local.x local.y local.z )
			$player[1].viewangles = ( local.a local.b 0 )
			$player[1].velocity = ( 0 0 0 )
		}
		waitframe
	}
}end
"""


def build_overlay(out):
    with zipfile.ZipFile(DEPLOYED) as z:
        s = z.read("coop_mod/weather.scr").decode("latin-1")
    assert s.count(HOOK_OLD) == 1, "weather.scr anchor moved"
    s = s.replace(HOOK_OLD, HOOK_NEW) + FUNC
    assert all(ord(c) < 128 for c in s)
    depth = 0
    for ln in s.split("\n"):
        code = ln.split("//")[0]
        depth += code.count("{") - code.count("}")
        assert depth >= 0, ln
    assert depth == 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/weather.scr", s.encode("latin-1"))


def seed_home(with_candidate):
    os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
    shutil.copyfile(os.path.join(PRISTINE, "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    for f in USER_LOOSE:
        if os.path.exists(os.path.join(PRISTINE, f)):
            shutil.copyfile(os.path.join(PRISTINE, f), os.path.join(MAINTT, f))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    build_overlay(os.path.join(MAINTT, OVERLAY))
    dst = os.path.join(MAINTT, os.path.basename(CANDIDATE))
    if with_candidate:
        shutil.copyfile(CANDIDATE, dst)
    elif os.path.exists(dst):
        os.remove(dst)


def rcon(cmd, timeout=1.5, settle=0.35):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(MAGIC + b"\x02rcon " + RCONPW.encode() + b" " + cmd.encode(), ("127.0.0.1", PORT))
        out = []
        while True:
            try:
                d, _ = s.recvfrom(16384)
            except socket.timeout:
                break
            out.append(d[4:].decode("latin-1"))
            s.settimeout(settle)
        return "".join(out)
    finally:
        s.close()


def read_log():
    try:
        return open(LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def guard():
    c, proc = CLIENT_H["c"], CLIENT_H["proc"]
    if c is not None and c.watcher.violations:
        raise Aborted("window policy violation: %s" % (c.watcher.violations[:3],))
    if proc is not None and proc.poll() is not None:
        raise Aborted("client exited")


def wait_log(pat, timeout, start=0):
    rx = re.compile(pat)
    t0 = time.time()
    while time.time() - t0 < timeout:
        guard()
        m = rx.search(read_log(), start)
        if m:
            return m
        time.sleep(1.0)
    return None


_STEP = {"n": 0}


def step(lines, timeout=240):
    _STEP["n"] += 1
    mk = "^~^~^ MGSTEP %d" % _STEP["n"]
    with open(os.path.join(MAINTT, "mgstep.cfg"), "w", newline="\n") as f:
        f.write("\n".join(lines + ["echo %s" % mk]) + "\n")
    start = len(read_log())
    rcon("exec mgstep.cfg")
    if not wait_log(re.escape(mk) + r"\b", timeout, max(0, start - 10)):
        raise RuntimeError("step %d timed out: %s" % (_STEP["n"], lines[:3]))


_CAM = {"seq": 0}


def place(v, fwd=0.0):
    x, y = v["xy"]
    x += math.cos(math.radians(v["yaw"])) * fwd
    y += math.sin(math.radians(v["yaw"])) * fwd
    _CAM["seq"] += 1
    return ["set coop_mgCamX %.2f" % x, "set coop_mgCamY %.2f" % y, "set coop_mgCamZ %.2f" % (v["ground"] + 4.0),
            "set coop_mgCamP %.3f" % v["pitch"], "set coop_mgCamW %.3f" % v["yaw"], "set coop_mgCamSeq %d" % _CAM["seq"]]


def launch(renderer, mapname="m3l2", w=1280, h=720):
    on = ["set rconPassword %s" % RCONPW, "set sv_maxbots 0", "set sv_numbots 0", "set cg_drawviewmodel 0",
          "set coop_mgTestPoll 1", "set coop_weatherPin 0", "set sv_fps 100", "set coop_dev 1", "set g_ai 0",
          "set cg_draw2d 0", "set ui_hud 0", "set ui_gmbox 0", "set ui_crosshair 0", "set coop_dbno 0",
          "set coop_tinnitus 0", "set coop_tinnitusBlast 0", "set coop_dizzy 0", "set r_ppHitAmount 0",
          "set com_maxfps 60", "set con_notifytime -1"]
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", renderer),
            ("r_mode", "-1"), ("r_customwidth", str(w)), ("r_customheight", str(h)), ("r_fullscreen", "0"),
            ("developer", "1"), ("logfile", "2"), ("net_port", str(PORT)), ("net_ip", "127.0.0.1")]
    args = [EXE]
    for k, val in sets:
        args += ["+set", k, val]
    args += ["+set", "g_gametype", "2", "+exec", "mg_on.cfg", "+set", "ui_dmmap", mapname,
             "+exec", "coop_mod/start_server.cfg"]
    args, late = hw.apply_policy(args, width=w, height=h)
    on += late
    with open(os.path.join(MAINTT, "mg_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(on) + "\n")
    assert sum(1 for a in args if a.startswith("+")) <= 31
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    CLIENT_H["c"], CLIENT_H["proc"] = c, c.proc
    hg.set_slot_pid(OWNER, c.proc.pid)
    return c, subprocess.list2cmdline(args)


def join():
    start = len(read_log())
    for _ in range(4):
        step(["popmenu 0", "wait 10", "primarydmweapon rifle", "wait 5", "set g_teamswitchdelay 0",
              "join_team allies", "wait 20", "popmenu 0", "wait 40", "popmenu 0", "wait 20",
              "+attackprimary", "wait 10", "-attackprimary"])
        if wait_log(r"has joined the (Allies|Axis|Free)", 20, start):
            return True
    return False


def land(v):
    start = len(read_log())
    step(place(v) + ["wait 1500", "coord"])
    m = re.findall(r"location: (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", read_log()[start:])
    want = (v["xy"][0], v["xy"][1], v["ground"] + 4.0)
    if not m or max(abs(float(m[-1][i]) - want[i]) for i in range(3)) > 2.0:
        raise RuntimeError("camera did not land: %s vs %s" % (m[-1] if m else None, want))


def session(setname, rundir):
    renderer, cand, mapname = SETS[setname]
    views = {k: v for k, v in json.load(open(VIEWSFILE)).items() if v.get("map", "m3l2") == mapname}
    only = [t for t in os.environ.get("M3L2G_VIEWS", "").split(",") if t]
    if only:
        views = {k: v for k, v in views.items() if k in only}
    notes = {"set": setname, "renderer": renderer, "candidate": cand}
    os.makedirs(rundir, exist_ok=True)
    seed_home(cand)
    os.makedirs(SHOTS, exist_ok=True)
    for fn in os.listdir(SHOTS):
        os.remove(os.path.join(SHOTS, fn))
    t0 = time.time()
    try:
        c, notes["cmdline"] = launch(renderer, mapname)
        if not wait_log(r"Detected Coop for", 600):
            raise RuntimeError("map never became ready")
        if not wait_log(r"\^~\^~\^ MGCAM ready", 90):
            raise RuntimeError("camera overlay did not start")
        time.sleep(6)
        notes["joined"] = join()
        time.sleep(3)
        for tag, v in views.items():
            land(v)
            step(place(v) + ["wait 2500", "screenshot mg_%s_%s" % (setname, tag)])
            if tag in MOTION and renderer == "opengl2":
                L = []
                for k in range(12):
                    L += place(v, fwd=k * 6.0) + ["wait 1", "wait 1", "wait 1",
                                                  "screenshot mg_%s_%s_walk%02d" % (setname, tag, k)]
                step(L, timeout=300)
            log("[%s] %s" % (setname, tag))
        L = read_log()
        notes["script_errors"] = len(re.findall(r"Script Error", L))
        notes["shader_warnings"] = re.findall(r"[^\r\n]*(?:hzm_m3l2|m3l2ground)[^\r\n]*", L)[:20]
        notes["missing"] = re.findall(r"[^\r\n]*(?:Couldn't|could not|WARNING)[^\r\n]*(?:hzm_m3l2|farmyard|road)[^\r\n]*",
                                      L, re.I)[:10]
        notes["checksum"] = re.findall(r"[^\r\n]*checksum[^\r\n]*", L, re.I)[:5]
        # the retail maps/m3l2.pth must still load (navigate.cpp: map_time unchanged + FS_FileNewer is a stub)
        notes["pathnodes"] = re.findall(r"[^\r\n]*(?:Pathnodes|path nodes|path file)[^\r\n]*", L, re.I)[:5]
    finally:
        proc = CLIENT_H["proc"]
        if proc is not None and proc.poll() is None:
            try:
                rcon("quit")
                proc.wait(40)
            except Exception:
                pass
        c = CLIENT_H["c"]
        if c is not None:
            c.close()
            wrep = c.report()
            notes["window"] = {"clean": wrep["clean"], "violations": wrep["violations"]}
        CLIENT_H["c"] = CLIENT_H["proc"] = None
        n = 0
        if os.path.isdir(SHOTS):
            for fn in sorted(os.listdir(SHOTS)):
                shutil.move(os.path.join(SHOTS, fn), os.path.join(rundir, fn))
                n += 1
        notes["shots"] = n
        if os.path.exists(LOG):
            shutil.copyfile(LOG, os.path.join(rundir, "qconsole.log"))
        notes["minutes"] = round((time.time() - t0) / 60.0, 1)
        json.dump(notes, open(os.path.join(rundir, "notes.json"), "w"), indent=1, default=str)
        log("[%s] done: %d shots, %.1f min" % (setname, n, notes["minutes"]))
    return notes


def slot_value():
    try:
        return open(SLOTFILE).read().strip()
    except OSError:
        return ""


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(0)
    if a[0] == "setup":
        seed_home(False)
        sys.exit(0)
    if a[0] == "wait-and-run":
        while slot_value() != OWNER:
            time.sleep(15)
        log("slot is ours")
    if hg.user_game_running():
        raise SystemExit("the user's game is running - not launching")
    hg.acquire_slot(OWNER, EXE, HOME, [PORT], minutes=60)
    out = {}
    stamp = time.strftime("%H%M%S")
    try:
        sets = [s for s in a[1:] if s in SETS] or list(SETS)
        for s in sets:
            try:
                out[s] = session(s, os.path.join(RUNS, stamp, s))
            except Aborted:
                raise
            except Exception as e:
                log("[%s] FAILED: %r" % (s, e))
                out[s] = {"error": repr(e)}
        json.dump(out, open(os.path.join(RUNS, stamp, "summary.json"), "w"), indent=1, default=str)
        print(json.dumps(out, indent=1, default=str)[:4000])
    finally:
        hg.release_slot(OWNER)
        seed_home(False)
        ov = os.path.join(MAINTT, OVERLAY)
        if os.path.exists(ov):
            os.remove(ov)
        if a[0] == "wait-and-run" and slot_value() == OWNER:
            open(SLOTFILE, "w").write("free")
            log("test slot released: free")

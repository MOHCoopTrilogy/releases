"""sf_run.py - same-camera, same-timestamp stills (and GIF bursts) of smoke & fire effects on a PRIVATE client, for the
smoke & fire A/B (docs/proposals/smokefire_2026-11-24/PLAN.md). Derived from water_extras_2026-11-13/tools/water_fx_run.py.

    python sf_run.py <tag> <map> <scene.json> [<variant> ...]     (default variants: A B)

A variant is a pak set: A = the shipped mod as deployed in the GOG maintt (basepath), B = A + every pak listed in
scene["variants"]["B"] copied into the client's own home/maintt (homepath beats basepath). Cvar-only variants
(engine switches) are scene["variants"][name] = {"paks": [], "sets": ["set x 1", ...]}. Each variant is its own launch;
the scene is replayed identically, so frames with the same index are the same moment.

scene.json:
  {"loadwait": 45, "postload": 6,
   "variants": {"A": {"paks": [], "sets": []}, "B": {"paks": ["H:/hzm_work/smokefire/paks/zzzzzzzzzzzzz_coop_fx.pk3"]}},
   "pre": ["console line", ...],
   "shots": [{"name": "grenade", "at": [x, y, z], "cam": {"yaw": 270, "dist": 300, "h": 25, "look_h": 60},
              "fx": [{"model": "models/fx/f1grenadeexplosion.tik", "kind": "expl", "d": [0, 0, 0]}],
              "times": [100, 250, 600, 1500], "burst": {"every": 100, "n": 20}, "settle": 1500, "clear": 4000}]}
  kind: expl = `spawn <tik> origin` (a server Explosion / effectentity: the real cgame explosion path,
        CG_MakeExplosionEffect -> models/fx/grenexp_<surface>), sm = script_model + anim start (fx blasts),
        em = bare spawn + anim start (emitters), fire = +attackprimary for `ms` at the camera's aim (bullet impacts).
Camera = a script Camera (the mod's cutscene recipe) at centre - dist*dir(yaw) + h, looking at centre + look_h.

Client G:/mohaa-smokefire (own home; GOG tree = read-only basepath; binaries from SF_BIN, default the release engine
build). Launched only through harness_window.launch_background (the 1920x1080 test screen, never activated, muted,
in_mouse 0, in_nograb 1, in_gamepad 0). The CALLER holds the screen slot (H:/hzm_work/screen_slot.py). Never touches
G:/mohaa-gl2, %APPDATA% or the GOG folder (read only). Output: H:/hzm_work/smokefire/runs/<tag>/<variant>/.
"""
import json, math, os, shutil, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

tag, mapname, scenefile = sys.argv[1], sys.argv[2], sys.argv[3]
cfg = json.load(open(scenefile))
want = sys.argv[4:] or sorted(cfg.get("variants", {"A": {}, "B": {}}))
W, H = 1280, 720
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = os.environ.get("SF_CLIENT", r"G:\mohaa-smokefire")
SEED = r"G:\mohaa-engrave"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
OUTROOT = os.path.join(r"H:\hzm_work\smokefire\runs", tag)
BIN = os.environ.get("SF_BIN", r"H:\hzm_work\eng-hotfix13661\.cmake")
BINS = {"openmohaa.exe": r"Release\openmohaa.exe", "cgame.dll": r"code\client\cgame\Release\cgame.dll",
        "game.dll": r"code\server\fgame\Release\game.dll",
        "renderer_opengl1.dll": r"code\renderercommon\renderergl1\Release\renderer_opengl1.dll",
        "renderer_opengl2.dll": r"code\renderercommon\renderergl2\Release\renderer_opengl2.dll"}
mon = [hw.test_display()]

SF_SCR = r"""// sf_run.py test overlay (private client only) - camera + effect spawner driven by cvars
cam:
	level.sf_lk = spawn script_origin
	level.sf_cam = spawn Camera
	level.sf_cam fov 80
	waitthread place
	if(level.gametype != 0){ waitthread coop_mod/cutscene.scr::cut_cam level.sf_cam }else{ cuecamera level.sf_cam }
	println "^~^~^ SFCAM cam"
	local.last = ""
	while(1){
		local.k = getcvar "sf_cx" + getcvar "sf_cy" + getcvar "sf_cz" + getcvar "sf_lx" + getcvar "sf_ly" + getcvar "sf_lz"
		if(local.k != local.last){ waitthread place; local.last = local.k }
		wait 0.05
	}
end
place:
	local.x = int( getcvar "sf_cx" )
	local.y = int( getcvar "sf_cy" )
	local.z = int( getcvar "sf_cz" )
	local.o = ( local.x local.y local.z )
	local.lx = int( getcvar "sf_lx" )
	local.ly = int( getcvar "sf_ly" )
	local.lz = int( getcvar "sf_lz" )
	level.sf_lk.origin = ( local.lx local.ly local.lz )
	level.sf_cam movetopos local.o
	level.sf_cam watch level.sf_lk 0
	level.sf_cam cut
	println ("^~^~^ SFCAM at " + local.o + " look " + level.sf_lk.origin)
end
fx:
	local.m = getcvar "sf_model"
	local.k = getcvar "sf_kind"
	local.os = getcvar "sf_fx" + " " + getcvar "sf_fy" + " " + getcvar "sf_fz"
	if(local.k == "expl"){
		local.e = spawn local.m "origin" local.os
		local.cg = getcvar "sf_cgm"
		if(local.cg != "" && local.cg != "-"){ local.e explosioneffect local.cg }
	}
	if(local.k == "sm"){
		local.e = spawn script_model "model" local.m "origin" local.os
		local.e notsolid
		local.e anim start
	}
	if(local.k == "em"){
		local.e = spawn local.m "origin" local.os
		local.e notsolid
		local.e anim start
	}
	println ("^~^~^ SFFX " + local.k + " " + local.m + " at " + local.os)
	local.life = int( getcvar "sf_life" )
	if(local.life > 0){
		wait local.life
		if(local.e != NULL){ if(local.k != "expl"){ local.e anim stop } }
		wait 1
		if(local.e != NULL){ local.e remove }
	}
end
"""


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def script(variant):
    L = []
    c = L.append
    w = lambda ms: L.append("wait %d" % int(ms))   # noqa: E731  (cfg wait is milliseconds in this engine - TRAPS)
    w(15000)
    c("set thereisnomonkey 1"); c("set cheats 1")
    if cfg.get("coopcheat", True):
        # the coop start with cheats on (water_fx_run.py recipe): start_server.cfg's settings without its ui_startdmmap,
        # then the command text UI_StartDMMap_f queues, only with cheats 1. (spdevmap starts m5l2b in a vehicle and
        # the script Camera never took the view - run p0day #2.)
        src = open(r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\start_server.cfg", encoding="latin-1").read().splitlines()
        for ln in src:
            s = ln.split("//")[0].strip()
            if s and not s.lower().startswith("ui_startdmmap"):
                c(s)
        for s in ["set dedicated 0", "set sv_maxclients 4", "set g_gametype 2", 'set g_gametypestring "Team-Match"',
                  "set fraglimit 0", "set timelimit 0", "set g_teamdamage 0", "set sv_maplist " + mapname, "set cheats 1",
                  "set coop_dev 1", "wait", "map " + mapname]:
            c(s)
        w(cfg.get("loadwait", 90) * 1000)
        for s in ["popmenu 0", "wait 20", "popmenu 0", "wait 20", "join_team allies", "wait 3000", "primarydmweapon rifle",
                  "wait 20", "popmenu 0", "wait 20", "+attackprimary", "wait 10", "-attackprimary", "wait 30"]:
            c(s)
        w(cfg.get("postload", 8) * 1000)
    else:
        c("spdevmap " + mapname); w(cfg.get("loadwait", 45) * 1000); c("finishloadingscreen"); w(cfg.get("postload", 6) * 1000)
    c("god"); c("notarget"); c("dog 1"); c("noclip")
    c("set cg_draw2d 0"); c("set cg_drawviewmodel 0"); c("set ui_hud 0"); c("set cg_drawhud 0"); c("set cg_effectdetail 1")
    for s in ("hidemenu hud_compass", "hidemenu hud_health", "hidemenu hud_ammo", "set ui_crosshair 0", "set coop_compassBar 0"):
        c(s)
    for s in cfg.get("pre", []) + cfg["variants"].get(variant, {}).get("sets", []):
        c(s)
    k = 0
    first = True
    for sh in cfg["shots"]:
        x, y, z = sh["at"]
        cm = sh["cam"]
        yaw = math.radians(cm.get("yaw", 0))
        cx, cy = x - cm.get("dist", 300) * math.cos(yaw), y - cm.get("dist", 300) * math.sin(yaw)
        for nm, v in (("sf_cx", cx), ("sf_cy", cy), ("sf_cz", z + cm.get("h", 40)), ("sf_lx", x), ("sf_ly", y),
                      ("sf_lz", z + cm.get("look_h", 60))):
            c("set %s %.1f" % (nm, v))
        if first:
            c("testthread global/sf_run.scr cam"); first = False
        for s_ in sh.get("sets", []):
            c(s_)
        w(sh.get("settle", 1500))
        c("echo ^~^~^ SFRUN %s %s start" % (variant, sh["name"]))
        k += 1
        c("screenshotJPEG %s_%s_%02d_%s_0000" % (tag, variant, k, sh["name"]))
        w(300)
        for fx in sh["fx"]:
            d = fx.get("d", [0, 0, 0])
            if fx.get("kind") == "fire":
                c("+attackprimary"); w(fx.get("ms", 600)); c("-attackprimary")
                continue
            for nm, v in (("sf_fx", x + d[0]), ("sf_fy", y + d[1]), ("sf_fz", z + d[2])):
                c("set %s %.1f" % (nm, v))
            c("set sf_model %s" % fx["model"]); c("set sf_kind %s" % fx.get("kind", "sm")); c("set sf_life %s" % fx.get("life", 0))
            c("set sf_cgm %s" % fx.get("cgm", "-"))
            c("testthread global/sf_run.scr fx")
        t = 0
        bu = sh.get("burst")
        marks = sorted(set(sh.get("times", []) + ([bu["every"] * (i + 1) for i in range(bu["n"])] if bu else [])))
        for m in marks:
            w(m - t); t = m
            c("screenshotJPEG %s_%s_%02d_%s_%04d" % (tag, variant, k, sh["name"], m))
        w(sh.get("clear", 3000))
    c("echo ^~^~^ SFRUN %s done" % variant); c("quit")
    return L


def run(variant):
    V = cfg["variants"].get(variant, {})
    if [r for r in hg.classify() if r["cls"] == "USER" and os.path.normcase(r.get("path") or "").startswith(os.path.normcase(r"G:\mohaa-gl2"))]:
        raise SystemExit("the user's game is running: not launching a test client")
    os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
    os.makedirs(os.path.join(MAINTT, "global"), exist_ok=True)
    for fn in ("OpenAL64.dll", "SDL2.dll", "libcurl.dll"):
        if not os.path.exists(os.path.join(CLIENT, fn)):
            shutil.copy2(os.path.join(SEED, fn), os.path.join(CLIENT, fn))
    for dst, src in BINS.items():
        shutil.copy2(os.path.join(BIN, src), os.path.join(CLIENT, dst))
    for dst, src in V.get("bins", {}).items():     # a variant's own binary, e.g. the smokefire-eng gl2 renderer
        shutil.copy2(src, os.path.join(CLIENT, dst))
    for fn in os.listdir(MAINTT):     # variant paks: only what this variant lists
        if fn.lower().endswith(".pk3"):
            os.remove(os.path.join(MAINTT, fn))
    for p in V.get("paks", []):
        shutil.copy2(p, os.path.join(MAINTT, os.path.basename(p)))
    shutil.copyfile(os.path.join(SEED, "pristine", "omconfig_fresh.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    open(os.path.join(MAINTT, "global", "sf_run.scr"), "w", newline="\n").write(SF_SCR)
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    shutil.rmtree(SHOTS, ignore_errors=True)
    os.makedirs(SHOTS, exist_ok=True)
    L = script(variant)
    secs = sum(int(x.split()[1]) for x in L if x.startswith("wait ")) / 1000.0
    with open(r"H:\hzm_work\display_queue.txt", "a") as q:
        q.write("%s smokefire %s/%s/%s (1 client 1920x1080 screen, %dx%d, muted, ~%d min)\n" % (
            time.strftime("%Y-%m-%d %H:%M"), tag, mapname, variant, W, H, max(1, int(secs // 60) + 1)))
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "cl_renderer", os.environ.get("SF_RENDERER", "opengl2"), "+set", "r_mode", "-1",
            "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
            "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "in_gamepad", "0",
            "+set", "in_joystick", "0", "+set", "in_mouse", "0", "+set", "in_nograb", "1", "+set", "s_volume", "0",
            "+set", "s_musicvolume", "0", "+set", "coop_tinnitusBaseVol", "0", "+set", "net_port", os.environ.get("SF_PORT", "12987"),
            "+exec", "sf_run.cfg"]
    wd = hw.sdl_display_index(mon[0]) if hw.supports_window_cvars(CLIENT) else None
    args, late = hw.apply_policy(args, width=W, height=H, display=mon[0], window_display=wd)
    boot = ["set in_joystick 0", "set in_gamepad 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0", "set s_musicvolume 0",
            "set s_ambientvolume 0", "set coop_tinnitusBaseVol 0", "set developer 1"]
    open(os.path.join(MAINTT, "sf_run.cfg"), "w", newline="\n").write("\n".join(late + boot + L) + "\n")
    cl = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log, display=mon[0])
    t0 = time.time()
    try:
        while time.time() - t0 < secs + 120:
            if cl.watcher.violations:
                log("VIOLATION", cl.watcher.violations[:3])
                break
            if cl.proc.poll() is not None:
                break
            time.sleep(1)
    finally:
        if cl.proc.poll() is None:
            cl.proc.kill()
        cl.close()
    out = os.path.join(OUTROOT, variant)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    n = 0
    for fn in sorted(os.listdir(SHOTS)):
        shutil.move(os.path.join(SHOTS, fn), os.path.join(out, fn))
        n += 1
    if os.path.exists(LOG):
        shutil.copyfile(LOG, os.path.join(out, "qconsole.log"))
    log("variant", variant, "shots", n, "out", out, "seconds", int(time.time() - t0))


for v in want:
    run(v)

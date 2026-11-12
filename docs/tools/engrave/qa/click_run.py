"""click_run.py - cfg-only QA of the Customize bench's free placement (hzmcust clickf) on a private client.

    python click_run.py <tag> <scenario> <WxH window> <display WxH: 3440x1440 | 1920x1080> [scenario args]

Never the live install: the client is G:\\mohaa-engrave with its OWN home (home_click: only a config and one overlay pak),
the GOG tree is the read-only basepath. The exe / cgame / game / renderers come from the engine build tree (EG_BIN), the
overlay pak holds the mod files this work changed (EG_MOD's `git status` + EG_ADD). Launched through
harness_window.launch_background only (test display, never activated, muted, in_mouse 0, in_nograb 1, in_gamepad 0);
refuses to start while the user's own game runs (harness_guard). Stills + the console log land in H:\\hzm_work\\engrave\\click\\<tag>.

Scenarios (cfg lines; `wait` is MILLISECONDS in this engine):
    look      every test gun on the bench: opened (the default placement) and turned over - to pick click points from
    clicks    <points.json>: {gun: [[name, fx, fy, turned 0/1], ...]}: click each point (fractions of the preview box),
              still of the whole gun, still zoomed on the piece, the piece's string echoed (^~^~^ CLICK <gun> <name>)
    hand      <strings.json>: {gun: cl_cust string}: each gun in hand in first person with that string
"""
import json, os, shutil, subprocess, sys, time, zipfile
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

tag, scen, win, disp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W, H = (int(v) for v in win.split("x"))
DW, DH = (int(v) for v in disp.split("x"))
mon = [m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == (DW, DH)]
if not mon:
    raise SystemExit("no %s display" % disp)

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-engrave"
EXE = os.path.join(CLIENT, "openmohaa.exe")
HOME = os.path.join(CLIENT, "home_click")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
OUT = os.path.join(r"H:\hzm_work\engrave\click", tag)
BIN = os.environ.get("EG_BIN", r"H:\hzm_work\eng-hotfix13661\.cmake")
MOD = os.environ.get("EG_MOD", r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod")
OVERLAY_FILES = ["scripts/hzm_engrave_anchors.txt", "ui/coop_custom.urc"]
BINS = {"openmohaa.exe": r"Release\openmohaa.exe", "cgame.dll": r"code\client\cgame\Release\cgame.dll",
        "game.dll": r"code\server\fgame\Release\game.dll",
        "renderer_opengl1.dll": r"code\renderercommon\renderergl1\Release\renderer_opengl1.dll",
        "renderer_opengl2.dll": r"code\renderercommon\renderergl2\Release\renderer_opengl2.dll"}
# gun -> (loadout page that makes it the Armory's inspected gun, the tik, its `use` name in game)
GUNS = {"mp44scoped": ("p38", "models/weapons/mp44scoped.tik", "StG44 Scoped"),
        "m1_garand": ("mvp01_0_s1", "models/weapons/m1_garand.tik", "M1 Garand"),
        "thompsonsmg": ("mvp24_0_s1", "models/weapons/thompsonsmg.tik", "Thompson"),
        "colt45": ("mvp48_0_s1", "models/weapons/colt45.tik", "Colt 45"),
        "mg42portable": ("p43", "models/weapons/mg42portable.tik", "MG42"),
        "kar98sniper": ("mvp13_0_s1", "models/weapons/kar98sniper.tik", "KAR98 - Sniper")}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


L, n = [], [0]


def c(s):
    L.append(s)


def wait(sec):
    L.append("wait %d" % int(sec * 1000))


def shot(name, settle=1.0):
    wait(settle)
    n[0] += 1
    c("screenshotJPEG %s_%02d_%s" % (tag, n[0], name))
    wait(0.5)


def look():
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("pushmenu coop_custom")
    for g in sys.argv[5].split(",") if len(sys.argv) > 5 else GUNS:
        c("exec ui/loadout/%s.cfg" % GUNS[g][0]); c("hzmcust open;hzmcust reset"); shot(g + "_open", 1.5)
        c("echo ^~^~^ LOOK %s;cl_custEdit" % g)
        c("hzmcust turn"); shot(g + "_turned", 1.2)


def clicks():
    pts = json.load(open(sys.argv[5]))
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("pushmenu coop_custom")
    for g, plist in pts.items():
        c("exec ui/loadout/%s.cfg" % GUNS[g][0]); c("hzmcust open;hzmcust reset"); wait(1.5)
        turned = 0
        for name, fx, fy, tn in plist:
            if tn != turned:
                c("hzmcust turn"); wait(0.8); turned = tn
            item = 1 if name.startswith("emblem") else 0
            c("hzmcust item %d" % item)
            if item:
                [c("hzmcust emblem 1") for _ in range(12)]
            c("hzmcust clickf %.4f %.4f" % (fx, fy)); wait(0.3)
            c("echo ^~^~^ CLICK %s %s;cl_custEdit;cl_custPickNote" % (g, name))
            shot("%s_%s" % (g, name), 0.8)
            c("hzmcust zoom;hzmcust zoom"); shot("%s_%s_close" % (g, name), 0.8); c("hzmcust zoom"); wait(0.6)   # a frame of the whole-gun view before the next click is cast


def hand():
    strs = json.load(open(sys.argv[5]))
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("set thereisnomonkey 1"); c("set cheats 1")
    c("spdevmap m3l2"); wait(45); c("finishloadingscreen"); wait(6)
    for g, items in strs.items():
        key = os.path.basename(GUNS[g][1])[:-4]
        c("give " + GUNS[g][1]); wait(1); c('use "%s"' % GUNS[g][2]); wait(3)
        for name, s in items:
            c('set cl_cust_%s "%s"' % (key, s)); wait(0.6)
            c("echo ^~^~^ HAND %s %s" % (g, name))
            shot("%s_%s_hand" % (g, name), 0.6)
            c("set cg_engraveCheck 1"); wait(0.3)
            n[0] += 1; c("set cg_engraveQuadNow 1;screenshotJPEG %s_%02d_%s_%s_check" % (tag, n[0], g, name)); wait(0.6)
            c("set cg_engraveCheck 0")
        c('set cl_cust_%s ""' % key)


def ops():
    """MOVE / TILT / SIZE / MIRROR / CENTRE / TURN OVER / the SPOT stepper on top of a free placement (Garand receiver)"""
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("pushmenu coop_custom")
    c("exec ui/loadout/%s.cfg" % GUNS["m1_garand"][0]); c("hzmcust open;hzmcust reset"); wait(1.5)
    def step(name, cmd, still=True):
        c(cmd); wait(0.3); c("echo ^~^~^ OP %s;cl_custEdit;cl_custPickNote;cl_custSizeNote;cl_custSpotTxt" % name)
        if still:
            shot("ops_" + name, 0.5)
    step("click", "hzmcust clickf 0.581 0.30")
    step("move_right", "hzmcust move 0.25 0;hzmcust move 0.25 0;hzmcust move 0.25 0;hzmcust move 0.25 0")
    step("move_up", "hzmcust move 0 0.1")
    step("move_off_edge", ";".join(["hzmcust move 0 0.1"] * 12), False)
    step("tilt", "hzmcust rot 5;hzmcust rot 5")
    step("size_up", "hzmcust scale 0.25;hzmcust scale 0.25;hzmcust scale 0.25;hzmcust scale 0.25", False)
    step("size_down", "hzmcust scale -0.25;hzmcust scale -0.25;hzmcust scale -0.25;hzmcust scale -0.25;hzmcust scale -0.25")
    step("mirror", "hzmcust mirror")
    step("centre", "hzmcust mirror;hzmcust center")
    step("turn_over", "hzmcust turn")
    step("click_other_side", "hzmcust clickf 0.42 0.30")
    step("turn_back", "hzmcust turn")
    step("save", "hzmcust save;cl_cust_m1_garand", False)
    step("spot_stepper", "hzmcust spot 1")
    step("emblem_click", "hzmcust item 1;" + ";".join(["hzmcust emblem 1"] * 12) + ";hzmcust clickf 0.835 0.54")
    step("emblem_other", "hzmcust emblem 1")


{"look": look, "clicks": clicks, "hand": hand, "ops": ops}[scen]()
c("echo ^~^~^ CLICKRUN done"); c("quit")

# the RAW answer: harness_guard.user_game_running() says "nobody" while the allow-while-playing flag file exists (it
# did on 2026-11-11, and a client was launched under the user's game: the watchdog killed it at 1.2 s on the game's own
# cursor clip). This work's rule is: never while the user's own game runs.
if hg.user_game_running_raw():
    raise SystemExit("the user's game is running: not launching a test client")
with open(r"H:\hzm_work\display_queue.txt", "a") as q:
    q.write("%s engrave free placement %s/%s (1 client %dx%d, muted, ~%d min)\n" % (
        time.strftime("%Y-%m-%d %H:%M"), tag, scen, W, H, max(1, sum(int(x.split()[1]) for x in L if x.startswith("wait ")) // 60000 + 1)))

# the binaries under test, into the private client folder only
for dst, src in BINS.items():
    shutil.copy2(os.path.join(BIN, src), os.path.join(CLIENT, dst))
os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig_fresh.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
for fn in os.listdir(MAINTT):
    if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
        os.remove(os.path.join(MAINTT, fn))
with zipfile.ZipFile(os.path.join(MAINTT, "zzzzzzzzzzzzzzzzzzzz_click.pk3"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in OVERLAY_FILES:
        z.write(os.path.join(MOD, f), f)
    for pair in os.environ.get("EG_ADD", "").split(";"):
        if pair:
            src, arc = pair.split("=")
            z.write(src, arc)
if os.path.exists(LOG):
    os.remove(LOG)
shutil.rmtree(SHOTS, ignore_errors=True)
os.makedirs(SHOTS, exist_ok=True)
args = [EXE, "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", HOME,
        "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", str(W),
        "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0", "+set", "cl_memorial", "0",
        "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "in_gamepad", "0", "+set", "in_joystick", "0",
        "+set", "net_port", "12958", "+exec", "click_run.cfg"]
# r_windowDisplay: the engine itself opens the window on the test display (without it the window came up on the
# second screen once another full-screen app was running, and the watchdog killed the run)
wd = hw.sdl_display_index(mon[0]) if hw.supports_window_cvars(CLIENT) else None
args, late = hw.apply_policy(args, width=W, height=H, display=mon[0], window_display=wd)
boot = ["set in_joystick 0", "set in_gamepad 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0", "set s_musicvolume 0",
        "set s_ambientvolume 0", "set developer 1"]
open(os.path.join(MAINTT, "click_run.cfg"), "w", newline="\n").write("\n".join(late + boot + L) + "\n")
cl = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log, display=mon[0])
t0 = time.time()
budget = sum(int(x.split()[1]) for x in L if x.startswith("wait ")) / 1000.0 + 120
try:
    while time.time() - t0 < budget:
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
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
k = 0
for fn in sorted(os.listdir(SHOTS)):
    shutil.move(os.path.join(SHOTS, fn), os.path.join(OUT, fn))
    k += 1
shutil.copyfile(LOG, os.path.join(OUT, "qconsole.log"))
log("run", tag, "shots", k, "out", OUT, "seconds", int(time.time() - t0))

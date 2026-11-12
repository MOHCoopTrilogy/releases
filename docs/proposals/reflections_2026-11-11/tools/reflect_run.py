"""reflect_run.py - stills and frame-time numbers for r_hzmReflect on a private client (never the live install).

    python reflect_run.py <tag> <map> <spots.json> [perf]

spots.json: {"levels": [0, 1, 2], "spots": [[name, x, y, z, pitch, yaw], ...], "pre": ["console line", ...]}
For every spot: tele + face (noclip), then one still per level (r_hzmReflect is live between 0 / 1 / 2 once the map
was loaded with it on). With `perf`: the frame cap comes off and each level is held 5 s at each spot while the
renderer prints one `^~^~^ HZMREFLECT perf` line a second (r_hzmReflectDbg 2).

Client: G:\\mohaa-reflect with its own home; the GOG tree is the read-only basepath; exe / cgame / game / renderers come
from the engine build tree. Launched through harness_window.launch_background only (1920x1080 screen, never activated,
muted, in_mouse 0, in_nograb 1, in_gamepad 0); refuses to start while the user's game or another test client runs.
Stills + the console log land in H:\\hzm_work\\reflect\\<tag>.
"""
import json, os, shutil, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

tag, mapname, spotfile = sys.argv[1], sys.argv[2], sys.argv[3]
perf = len(sys.argv) > 4 and sys.argv[4] == "perf"
W, H, DW, DH = 1600, 900, 1920, 1080
mon = [m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == (DW, DH)]
if not mon:
    raise SystemExit("no 1920x1080 display")

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-reflect"
SEED = r"G:\mohaa-engrave"            # runtime DLLs + the pristine config only (read)
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
OUT = os.path.join(r"H:\hzm_work\reflect", tag)
BIN = os.environ.get("RF_BIN", r"H:\hzm_work\eng-hotfix13661\.cmake")
BINS = {"openmohaa.exe": r"Release\openmohaa.exe", "cgame.dll": r"code\client\cgame\Release\cgame.dll",
        "game.dll": r"code\server\fgame\Release\game.dll",
        "renderer_opengl1.dll": r"code\renderercommon\renderergl1\Release\renderer_opengl1.dll",
        "renderer_opengl2.dll": r"code\renderercommon\renderergl2\Release\renderer_opengl2.dll"}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


cfg = json.load(open(spotfile))
levels = cfg.get("levels", [0, 1, 2])
L, n = [], [0]


def c(s):
    L.append(s)


def wait(sec):
    L.append("wait %d" % int(sec * 1000))


wait(15)
c("set thereisnomonkey 1"); c("set cheats 1")
c("spdevmap " + mapname); wait(cfg.get("loadwait", 50)); c("finishloadingscreen"); wait(6)
c("dog 1"); c("notarget 1")
if cfg.get("noclip", True):
    c("noclip")
c("set cg_drawviewmodel 2"); c("set ui_hud 0"); c("set cg_drawhud 0")
for line in cfg.get("pre", []):
    c(line)
wait(1)
if perf:
    # the test window is never focused: the unfocused cap (60) is what limits it, so that comes off too
    c("set com_maxfps 0"); c("set com_maxfpsUnfocused 0"); c("set r_swapInterval 0"); c("set r_hzmReflectDbg 2")
for spot in cfg["spots"]:
    if spot[0] == "@":          # ["@", "console line"]: a command between spots
        c(spot[1])
        continue
    name, x, y, z, pitch, yaw = spot
    c("tele %d %d %d" % (x, y, z)); c("face %d %d 0" % (pitch, yaw)); wait(1.5)
    for lv in levels:
        c("set r_hzmReflect %d" % lv)
        c("echo ^~^~^ REFLECTRUN %s level %d" % (name, lv))
        if perf:
            wait(4.5)
        else:
            wait(0.8)
            n[0] += 1
            c("screenshotJPEG %s_%02d_%s_L%d" % (tag, n[0], name, lv)); wait(0.5)
if perf:
    c("set com_maxfpsUnfocused 60"); c("set com_maxfps 60")
c("echo ^~^~^ REFLECTRUN done"); c("quit")

if hg.user_game_running_raw():
    raise SystemExit("the user's game is running: not launching a test client")
if [p for p in hg.classify() if p["cls"] != "SERVER" and p["cls"] != "USER"]:
    raise SystemExit("another test client is up: one at a time on the 1920x1080 screen")
secs = sum(int(x.split()[1]) for x in L if x.startswith("wait ")) / 1000.0
with open(r"H:\hzm_work\display_queue.txt", "a") as q:
    q.write("%s reflections %s/%s%s (1 client 1920x1080 screen, %dx%d, muted, ~%d min)\n" % (
        time.strftime("%Y-%m-%d %H:%M"), tag, mapname, " perf" if perf else "", W, H, max(1, int(secs // 60) + 1)))

os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
for fn in ("OpenAL64.dll", "SDL2.dll", "libcurl.dll"):
    if not os.path.exists(os.path.join(CLIENT, fn)):
        shutil.copy2(os.path.join(SEED, fn), os.path.join(CLIENT, fn))
for dst, src in BINS.items():
    shutil.copy2(os.path.join(BIN, src), os.path.join(CLIENT, dst))
shutil.copyfile(os.path.join(SEED, "pristine", "omconfig_fresh.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
for fn in os.listdir(MAINTT):
    if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg":
        os.remove(os.path.join(MAINTT, fn))
if os.path.exists(LOG):
    os.remove(LOG)
shutil.rmtree(SHOTS, ignore_errors=True)
os.makedirs(SHOTS, exist_ok=True)
args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
        "+set", "fs_homepath", HOME, "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
        "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
        "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "in_gamepad", "0",
        "+set", "in_joystick", "0", "+set", "net_port", "12971",
        "+set", "r_hzmReflect", str(cfg.get("boot_level", 2)), "+exec", "reflect_run.cfg"]
for k, v in cfg.get("sets", {}).items():
    args[-2:-2] = ["+set", k, str(v)]
wd = hw.sdl_display_index(mon[0]) if hw.supports_window_cvars(CLIENT) else None
args, late = hw.apply_policy(args, width=W, height=H, display=mon[0], window_display=wd)
boot = ["set in_joystick 0", "set in_gamepad 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0", "set s_musicvolume 0",
        "set s_ambientvolume 0", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
        "set developer 1"]
open(os.path.join(MAINTT, "reflect_run.cfg"), "w", newline="\n").write("\n".join(late + boot + L) + "\n")
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
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
k = 0
for fn in sorted(os.listdir(SHOTS)):
    shutil.move(os.path.join(SHOTS, fn), os.path.join(OUT, fn))
    k += 1
if os.path.exists(LOG):
    shutil.copyfile(LOG, os.path.join(OUT, "qconsole.log"))
log("run", tag, "shots", k, "out", OUT, "seconds", int(time.time() - t0))

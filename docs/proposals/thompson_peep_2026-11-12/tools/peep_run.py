"""peep_run.py - ADS stills of Thompson variants on a private client (G:\\mohaa-thompson; never the live install).

    python peep_run.py <tag> <tik,tik,...> [overlay.pk3]

SP devmap m3l2 at the ironsights harness spot (open, lit). Per gun: takeall, give, select, aim (+button13), one still,
release. Client: G:\\mohaa-thompson, own home, GOG tree as the read-only basepath, exe/cgame/game/renderers byte-copied
from the live install (read only). Launched through harness_window.launch_background only (1920x1080 screen, never
activated, muted, in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0); refuses while the user's game or another test
client runs. Run it only inside a held screen slot (screen_slot.py acquire thompson ...). Stills -> H:\\hzm_work\\thompson\\<tag>.
"""
import os, shutil, sys, time
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg  # noqa: E402
import harness_window as hw  # noqa: E402

tag, guns = sys.argv[1], [g for g in sys.argv[2].split(",") if g]
overlay = sys.argv[3] if len(sys.argv) > 3 else None
W, H, DW, DH = 1600, 900, 1920, 1080
mon = [m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == (DW, DH)]
if not mon:
    raise SystemExit("no 1920x1080 display")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LIVE = r"G:\mohaa-gl2"                  # binaries are COPIED from here (read only); it is never launched
CLIENT = r"G:\mohaa-thompson"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
OUT = os.path.join(r"H:\hzm_work\thompson", tag)
OVNAME = "zzzzzzzzzzzzzzzzzzz_peeptest.pk3"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


L = []


def c(s):
    L.append(s)


def wait(sec):
    L.append("wait %d" % int(sec * 1000))


wait(15)
c("set thereisnomonkey 1"); c("set cheats 1")
c("spdevmap m3l2"); wait(50); c("finishloadingscreen"); wait(6)
c("dog 1"); c("notarget 1")
for s in ("cg_drawviewmodel 2", "ui_hud 0", "cg_drawhud 0", "ui_crosshair 0", "cg_adsSway 0", "cg_headbob 0",
          "cg_adsBreathVignette 0", "coop_ads_vignette 0", "r_ppMotionBlur 0", "r_ppDizzy 0", "r_ppLowHealth 0",
          "coop_idleInspect 0", "fov 80") + tuple(x for x in os.environ.get("PEEP_SETS", "").split(";") if x):
    c("set " + s)
c("tele -3608 2303 80"); c("face 0 225 0"); wait(2)
for i, tik in enumerate(guns):
    name = os.path.basename(tik).replace(".tik", "")
    c("-button13"); wait(0.4)
    c("give " + tik); wait(0.5)
    for _ in range(3):                  # (console `takeall` is not available; select by tik like build_overlay's hook)
        c("use " + tik); wait(0.8)
    wait(1.5)
    c("tele -3608 2303 80"); c("face 0 225 0"); wait(0.6)
    c("echo ^~^~^ PEEPRUN %s" % name)
    c("+button13"); wait(2.2)
    c("screenshotJPEG %s_%02d_%s" % (tag, i, name)); wait(0.6)
    c("-button13"); wait(0.6)
# HIP EMPTY RELOAD frames (the cocking hand is keyed onto the actuator knob): guns listed one per line in
# H:\hzm_work\thompson\reload_guns.txt - fire the gun dry from the hip, then one frame every ~0.12 s through the reload
RL = os.path.join(r"H:\hzm_work", "thompson", "reload_guns.txt")
for tik in ([l.strip() for l in open(RL) if l.strip()] if os.path.exists(RL) else []):
    if tik not in guns:
        continue
    name = os.path.basename(tik).replace(".tik", "")
    c("-button13"); c("give " + tik); wait(0.5)
    for _ in range(3):
        c("use " + tik); wait(0.8)
    wait(1.5)
    c("tele -3608 2303 80"); c("face 0 225 0"); wait(0.5)
    c("echo ^~^~^ PEEPRUN hipreload %s" % name)
    c("+attackprimary"); wait(7.0); c("-attackprimary"); wait(0.3)
    c("reload")
    for k in range(32):
        c("screenshotJPEG %s_rl_%s_%02d" % (tag, name, k)); wait(0.12)
c("echo ^~^~^ PEEPRUN done"); c("quit")

if hg.user_game_running_raw():
    raise SystemExit("the user's game is running: not launching a test client")
if [p for p in hg.classify() if p["cls"] != "SERVER" and p["cls"] != "USER"]:
    raise SystemExit("another test client is up: one at a time on the 1920x1080 screen")
secs = sum(int(x.split()[1]) for x in L if x.startswith("wait ")) / 1000.0
os.makedirs(os.path.join(MAINTT, "configs"), exist_ok=True)
for fn in ("openmohaa.exe", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll",
           "OpenAL64.dll", "SDL2.dll", "libcurl.dll"):
    shutil.copy2(os.path.join(LIVE, fn), os.path.join(CLIENT, fn))
CG_OVERRIDE = os.path.join(r"H:\hzm_work", "thompson", "cgame_override.dll")   # a test cgame (e.g. a sight-table change) when present
if os.path.exists(CG_OVERRIDE):
    shutil.copy2(CG_OVERRIDE, os.path.join(CLIENT, "cgame.dll"))
    log("cgame override", CG_OVERRIDE)
shutil.copyfile(r"G:\mohaa-engrave\pristine\omconfig_fresh.cfg", os.path.join(MAINTT, "configs", "omconfig.cfg"))
for fn in os.listdir(MAINTT):
    if fn.lower().endswith(".pid") or fn == "whatsnew_pending.cfg" or fn == OVNAME:
        os.remove(os.path.join(MAINTT, fn))
if overlay:
    shutil.copyfile(overlay, os.path.join(MAINTT, OVNAME))
if os.path.exists(LOG):
    os.remove(LOG)
shutil.rmtree(SHOTS, ignore_errors=True)
os.makedirs(SHOTS, exist_ok=True)
args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
        "+set", "fs_homepath", HOME, "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1",
        "+set", "r_customwidth", str(W), "+set", "r_customheight", str(H), "+set", "r_fullscreen", "0",
        "+set", "cl_memorial", "0", "+set", "logfile", "2", "+set", "com_maxfps", "60", "+set", "in_gamepad", "0",
        "+set", "in_joystick", "0", "+set", "net_port", "12983", "+exec", "peep_run.cfg"]
wd = hw.sdl_display_index(mon[0]) if hw.supports_window_cvars(CLIENT) else None
args, late = hw.apply_policy(args, width=W, height=H, display=mon[0], window_display=wd)
boot = ["set in_joystick 0", "set in_gamepad 0", "set in_mouse 0", "set in_nograb 1", "set s_volume 0", "set s_musicvolume 0",
        "set s_ambientvolume 0", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
        "set developer 1"]
open(os.path.join(MAINTT, "peep_run.cfg"), "w", newline="\n").write("\n".join(late + boot + L) + "\n")
log("launch", tag, len(guns), "guns, ~%d s" % secs, "overlay", overlay)
cl = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log, display=mon[0])
t0 = time.time()
try:
    while time.time() - t0 < secs + 90:
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

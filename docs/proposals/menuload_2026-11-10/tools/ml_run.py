r"""ml_run.py - in-game -> Main Menu load timing (v1.10.72 "the menu takes ages and the screen freezes") on the private client
G:\mohaa-menuload (a copy of the live G:\mohaa-gl2 binaries + a copy of the user's home cfgs; never the live install).

Launch policy: docs/tools/harness_window.py with the guard on, on the 1080p second screen (HZM_TEST_RES=1920x1080), below
normal priority, muted (s_volume 0 + the coop tinnitus / wound muffle volumes 0 after autoexec), in_mouse 0, in_nograb 1,
in_gamepad 0, in_joystick 0. A guard trip ends the run and writes STOP beside the runs; no later launch while it exists.

    python ml_run.py run <tag> [exe] [map]     boot -> attic (cold), start <map> (default m2l1) as a coop listen host,
                                               in game: pushmenu main (dm_main's "Main Menu" button), back, disconnect,
                                               then a second map + pushmenu main + disconnect (warm). Prints the MENULOAD lines.
The engine side is the MENULOAD probe (cl_uiscene.cpp / cl_main.cpp): "^~^~^ MENULOAD ready why=<boot|scene|disconnect> total=..".
"""
import os, re, shutil, sys, time
os.environ.setdefault("HZM_TEST_RES", "1920x1080")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
CLIENT = r"G:\mohaa-menuload"
HOME = os.path.join(CLIENT, "home")
MAINTT = os.path.join(HOME, "maintt")
LOG = os.path.join(MAINTT, "qconsole.log")
SHOTS = os.path.join(MAINTT, "screenshots")
RUNS = r"H:\hzm_work\menuload\runs"
STOP = os.path.join(RUNS, "STOP_GUARD_TRIPPED.flag")
QUIET = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0",
         "set coop_woundMuffleVol 0", "set in_mouse 0", "set in_nograb 1", "set in_gamepad 0", "set in_joystick 0"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def cycle(mp, n, shots, menu_only=False):
    """one in-game -> menu cycle on map mp (waits are milliseconds)"""
    L = ["echo ^~^~^ ML stage start%d %s" % (n, mp), "set ui_dmmap %s" % mp, "exec coop_mod/start_server.cfg",
         # ui_startdmmap Cbuf_AddText's its map command at the END of the buffer (after this whole cfg, i.e. after quit): issue
         # the same line it builds (cl_ui.cpp UI_StartDMMap_f) here, in order
         'set dedicated 0;set sv_maxclients 4;set sv_gamespy 0;set g_gametype 2;set g_gametypestring "Team-Match";set fraglimit 0;'
         'set timelimit 0;set g_teamdamage 0;set g_inactivespectate 600;set g_inactivekick 0;set cheats 0;wait;map "%s"' % mp, "wait 90000"]
    L += QUIET + ["echo ^~^~^ ML stage ingame%d" % n]
    if shots:
        L += ["screenshot ml_ingame%d" % n, "wait 500"]
    L += ["echo ^~^~^ ML stage pushmain%d" % n, "pushmenu main", "wait 25000"]
    if menu_only:
        return L
    if shots:
        L += ["screenshot ml_menuingame%d" % n, "wait 500"]
    L += ["echo ^~^~^ ML stage disconnect%d" % n, "disconnect", "wait 25000"]
    if shots:
        L += ["screenshot ml_menuafter%d" % n, "wait 500"]
    return L


def run(tag, exe=None, mp="m2l1", shots=True, cycles=2, sets=(), rooms=False, renderer=None):
    if os.path.exists(STOP):
        raise SystemExit("a guard tripped earlier (%s) - no more launches" % STOP)
    os.makedirs(RUNS, exist_ok=True)
    if exe:
        shutil.copy2(exe, os.path.join(CLIENT, "openmohaa.exe"))
    renderer = renderer or os.environ.get("ML_RENDERER")
    if renderer:
        shutil.copy2(renderer, os.path.join(CLIENT, "renderer_opengl2.dll"))
    exe = exe or os.environ.get("ML_EXE")
    if exe:
        shutil.copy2(exe, os.path.join(CLIENT, "openmohaa.exe"))
    # every run starts from the user's own config (a latched +set, e.g. r_ext_compressed_textures, is archived by the run)
    shutil.copyfile(os.path.join(CLIENT, "pristine", "omconfig.cfg"), os.path.join(MAINTT, "configs", "omconfig.cfg"))
    # and from the user's own shader-preload lists (polluted with the attic's shaders, as every player's are today)
    shutil.rmtree(os.path.join(MAINTT, "hzm_preload"), ignore_errors=True)
    shutil.copytree(os.path.join(CLIENT, "pristine", "hzm_preload"), os.path.join(MAINTT, "hzm_preload"))
    for fn in os.listdir(MAINTT):
        if fn.lower().endswith(".pid"):
            os.remove(os.path.join(MAINTT, fn))
    if os.path.exists(LOG):
        os.remove(LOG)
    shutil.rmtree(SHOTS, ignore_errors=True)
    os.makedirs(SHOTS, exist_ok=True)
    w, h = 1920, 1080
    args = [os.path.join(CLIENT, "openmohaa.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "fs_homepath", HOME,
            "+set", "cl_renderer", "opengl2", "+set", "r_mode", "-1", "+set", "r_customwidth", str(w), "+set", "r_customheight", str(h),
            "+set", "r_fullscreen", "0", "+set", "logfile", "2", "+set", "developer", "0", "+set", "s_volume", "0",
            "+set", "s_musicvolume", "0", "+set", "in_mouse", "0", "+set", "in_nograb", "1", "+set", "in_gamepad", "0",
            "+set", "in_joystick", "0"] + sum((["+set", k, v] for k, v in sets), []) + ["+exec", "ml_run.cfg"]
    args, late = hw.apply_policy(args, width=w, height=h)
    L = late + QUIET + ["set %s %s" % (k, v) for k, v in sets] + ["echo ^~^~^ ML stage boot", "wait 30000"]
    if shots:
        L += ["screenshot ml_menucold", "wait 500"]
    for n in range(1, cycles + 1):
        L += cycle(mp, n, shots and n == 1, menu_only=rooms)
    tail = [c for c in os.environ.get("ML_TAIL", "").split(";") if c.strip()]
    L += tail
    if not tail:
        L += ["echo ^~^~^ ML stage done", "wait 1000", "quit"]
    open(os.path.join(MAINTT, "ml_run.cfg"), "w", newline="\n").write("\n".join(L) + "\n")
    c = hw.launch_background(args[0], args[1:], CLIENT, policy=False, log=log)
    t0 = time.time()
    tripped = None
    try:
        while time.time() - t0 < 900:
            if c.watcher.violations:
                tripped = c.watcher.violations[:3]
                log("VIOLATION", tripped)
                break
            if c.proc.poll() is not None:
                break
            time.sleep(1)
    finally:
        if c.proc.poll() is None:
            c.proc.kill()
        c.close()
    out = os.path.join(RUNS, tag)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for fn in sorted(os.listdir(SHOTS)):
        shutil.move(os.path.join(SHOTS, fn), os.path.join(out, fn))
    shutil.copyfile(LOG, os.path.join(out, "qconsole.log"))
    if tripped:
        open(STOP, "w").write(repr(tripped))
        raise SystemExit("GUARD TRIPPED: %r" % (tripped,))
    summarize(os.path.join(out, "qconsole.log"))
    return out


def summarize(path):
    for l in open(path, errors="ignore"):
        if re.search(r"MENULOAD|ML stage|CL_InitCGame:|CL_EndRegistration|PRELOAD|KEEPIMG|VRAMACCT|Disconnected from|ERROR", l):
            print("  " + l.rstrip()[:220])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "run":
        print(run(a[1], a[2] if len(a) > 2 and a[2] != "-" else None, a[3] if len(a) > 3 else "m2l1"))
    elif a[0] == "boot":            # boot <tag> [cvar=value ...]: cold boot -> menu only
        print(run(a[1], None, cycles=0, sets=[kv.split("=", 1) for kv in a[2:]]))
    elif a[0] == "sum":
        summarize(a[1])

"""p2lib.py - harness glue for the .30 cal second pass (bug-3562). Private harness G:/mohaa-hudfeed5, DISPLAY2,
slot owner hudfeed5, port 12781. Binaries: the integration set from <scratchpad>/built_integ7 (never the *_ship files)."""
import os, re, sys, time, zipfile, shutil, hashlib
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
WORK = os.path.join(HERE, "work")
INTEG = os.path.join(os.path.dirname(HERE), "built_integ7")
R.OWNER = "hudfeed5"
R.CLIENT = "G:/mohaa-hudfeed5"
R.EXE = os.path.join(R.CLIENT, "openmohaa_integ7.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed5/runs"
R.PORT = 12781
LOGF = os.path.join(HERE, "p2.log")


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def _cp(src, dst):
    if not os.path.exists(dst) or hashlib.md5(open(src, "rb").read()).digest() != hashlib.md5(open(dst, "rb").read()).digest():
        shutil.copyfile(src, dst)


def install(game=None):
    """the integration set (exe, game, cgame, gl2); game = path of another game.dll to run instead"""
    _cp(os.path.join(INTEG, "openmohaa.exe"), R.EXE)
    _cp(os.path.join(INTEG, "game.dll"), os.path.join(R.CLIENT, "games", "game_integ7.dll"))
    _cp(os.path.join(INTEG, "cgame.dll"), os.path.join(R.CLIENT, "cgames", "cgame_integ7.dll"))
    _cp(os.path.join(INTEG, "renderer_opengl2.dll"), os.path.join(R.CLIENT, "renderers", "gl2_integ7.dll"))
    shutil.copyfile(game or os.path.join(R.CLIENT, "games", "game_integ7.dll"), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl2_integ7.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    return "cgame_integ7"


def restore_ship():
    for f, d in (("games/game_ship.dll", "game.dll"), ("renderers/gl2_ship.dll", "renderer_opengl2.dll"),
                 ("cgames/cgame_ship.dll", "cgame.dll")):
        shutil.copyfile(os.path.join(R.CLIENT, f), os.path.join(R.CLIENT, d))


def overlay(name="ov_p2.pk3", driver="p2_drv.scr", extra=()):
    """the driver as coop_mod/coop_selftest_xp.scr + every file under work/ (the edited mod files) + extra"""
    ov = os.path.join(HERE, name)
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, driver), "coop_mod/coop_selftest_xp.scr")
        for root, _, files in os.walk(WORK):
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, WORK).replace("\\", "/"))
        for rel in extra:
            if isinstance(rel, tuple):
                z.write(rel[0], rel[1])
            else:
                z.write(os.path.join(MOD, rel), rel)
    return ov


EXTRA = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
         "set g_ai 1", "set cg_drawviewmodel 0", "set coop_paraShootdownChance 0", "set s_volume 0",
         "set g_patherror 1"]


def boot(sess, mapname, W=1280, H=720, extra=(), ov=None):
    import subprocess
    subprocess.check_call([sys.executable, os.path.join(HERE, "build_scr.py")])      # never a stale work file
    cg = install()
    R.MAP = mapname
    rundir, notes = S.boot_session(sess, cg, W, H, EXTRA + list(extra), ov or overlay())
    log("booted", sess, mapname, notes.get("md5"), "dog", notes.get("dog"))
    t = R.read_log()
    if "P2 para armed" not in t:
        raise RuntimeError("driver did not start (overlay script did not compile?)")
    return rundir, notes


def end(rundir, notes):
    try:
        if rundir:
            S.end_session(rundir, notes or {})
    except Exception as e:
        log("end_session", repr(e))
    restore_ship()


def cmd(what, timeout=40, **kv):
    p0 = len(R.read_log())
    R.step(["set p2_%s %s" % (k, v) for k, v in kv.items()] + ["set p2_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ P2 did %s" % what, timeout, p0):
        raise RuntimeError("driver never did %s" % what)
    time.sleep(0.2)
    return p0


def since(p0, pat):
    return re.findall(pat, R.read_log()[p0:])


def errors():
    t = R.read_log()
    return sorted(set(l[-170:] for l in t.splitlines()
                      if "Script Error" in l or "not properly loaded" in l or "Couldn't compile" in l or "parse error" in l))


def frames(tag, n, ms=150, pre=()):
    seq = list(pre)
    for k in range(n):
        seq += ["screenshotJPEG %s_%04d" % (tag, k), "wait %d" % ms]
    R.step(seq, timeout=120 + n)


def cam(dist, ang, up=0):
    cmd("cam", n=dist, yaw=ang, z=up)
    time.sleep(0.6)


def still(name):
    R.step(["screenshotJPEG %s" % name, "wait 150"], timeout=30)

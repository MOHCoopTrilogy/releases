"""lg_lib.py - harness glue for the ENGINE side of the paratroopers' left .30 cal (engine branch game1-next).
Private harness G:/mohaa-hudfeed3, DISPLAY2, slot owner hudfeed3, port 12741. Binaries: exe + gl2 from the integration
set <scratchpad>/built_integ7, game.dll + cgame.dll from the game1 worktree's own build (never the *_ship files).
A copy of tools/pass2/p2lib.py with the owner / paths / port changed; the originals are not edited."""
import os, re, sys, time, zipfile, shutil, hashlib
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
SCRATCH = R.SCRATCH
INTEG = os.path.join(SCRATCH, "built_integ7")
WT = "C:/mohaa-coop-dev/openmohaa-hzm-game1/.cmake/code"
GAME = os.path.join(WT, "server", "fgame", "Release", "game.dll")
CGAME = os.path.join(WT, "client", "cgame", "Release", "cgame.dll")
R.OWNER = "hudfeed3"
R.CLIENT = "G:/mohaa-hudfeed3"
R.EXE = os.path.join(R.CLIENT, "openmohaa_integ7.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed3/runs"
R.PORT = 12741
LOGF = os.path.join(HERE, "lg.log")
KEEP = os.path.join(SCRATCH, "leftgun_keep")       # what stood in the harness root before this lane's first run
ROOTF = ("game.dll", "cgame.dll", "renderer_opengl2.dll")
# the gun, its rest and the bags are not in the deployed pak (the second pass is not deployed)
MODFILES = ["models/statweapons/coop_30cal_para.tik", "models/static/coop_mg_bags.tik",
            "models/static/coop_mg_bags/coop_mg_bags.skd", "models/static/coop_mg_bags/coop_mg_bags.skc",
            "scripts/coop_mgbags.shader"]


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def _cp(src, dst):
    if not os.path.exists(dst) or md5(src) != md5(dst):
        shutil.copyfile(src, dst)


def install(game=None):
    if not os.path.isdir(KEEP):
        os.makedirs(KEEP)
        for f in ROOTF:
            shutil.copyfile(os.path.join(R.CLIENT, f), os.path.join(KEEP, f))
    _cp(os.path.join(INTEG, "openmohaa.exe"), R.EXE)
    _cp(os.path.join(INTEG, "renderer_opengl2.dll"), os.path.join(R.CLIENT, "renderers", "gl2_integ7.dll"))
    _cp(game or GAME, os.path.join(R.CLIENT, "games", "game_leftgun.dll"))
    _cp(CGAME, os.path.join(R.CLIENT, "cgames", "cgame_leftgun.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "games", "game_leftgun.dll"), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl2_integ7.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    return "cgame_leftgun"


def restore():
    for f in ROOTF:
        if os.path.exists(os.path.join(KEEP, f)):
            shutil.copyfile(os.path.join(KEEP, f), os.path.join(R.CLIENT, f))


# the crouched manning pose on a low gun: the state file rows and the two aliases (mod coop-wip, not in the deployed pak)
LOWGUN = ["coop_mod/player_legs.st", "coop_mod/player_Torso.st", "models/player/base/anims_shared.txt"]


def overlay(name="ov_lg.pk3", driver="lg_drv.scr", lowgun=True):
    ov = os.path.join(HERE, name)
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, driver), "coop_mod/coop_selftest_xp.scr")
        for rel in MODFILES + (LOWGUN if lowgun else []):
            z.write(os.path.join(MOD, rel), rel)
    return ov


EXTRA = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
         "set g_ai 1", "set cg_drawviewmodel 1", "set coop_paraShootdownChance 0", "set s_volume 0"]


def boot(sess, mapname, W=1280, H=720, extra=(), game=None, lowgun=True):
    cg = install(game)
    R.MAP = mapname
    rundir, notes = S.boot_session(sess, cg, W, H, EXTRA + list(extra), overlay(lowgun=lowgun))
    notes["md5full"] = {f: md5(os.path.join(R.CLIENT, f)) for f in ROOTF}
    log("booted", sess, mapname, notes.get("md5"), "dog", notes.get("dog"))
    if "LG armed" not in R.read_log():
        end(rundir, notes)          # never leave the client up behind a failed boot
        raise RuntimeError("driver did not start (overlay script did not compile?)")
    return rundir, notes


def end(rundir, notes):
    try:
        if rundir:
            S.end_session(rundir, notes or {})
    except Exception as e:
        log("end_session", repr(e))
    restore()


def cmd(what, timeout=40, **kv):
    p0 = len(R.read_log())
    R.step(["set lg_%s %s" % (k, v) for k, v in kv.items()] + ["set lg_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ LG did %s" % what, timeout, p0):
        raise RuntimeError("driver never did %s" % what)
    time.sleep(0.2)
    return p0


def since(p0, pat):
    return re.findall(pat, R.read_log()[p0:])


def poll(p0):
    """the LGP lines since p0 as dicts"""
    out = []
    for m in re.finditer(r"LGP t=([\d.]+) ammo=(-?\d+) heat=([\d.]+) oh=(\d) pitch=(-?[\d.]+) yaw=(-?[\d.]+)", R.read_log()[p0:]):
        out.append({"t": float(m.group(1)), "ammo": int(m.group(2)), "heat": float(m.group(3)), "oh": int(m.group(4)),
                    "pitch": float(m.group(5)), "yaw": float(m.group(6))})
    return out


def errors():
    t = R.read_log()
    return sorted(set(l[-170:] for l in t.splitlines()
                      if "Script Error" in l or "not properly loaded" in l or "Couldn't compile" in l or "parse error" in l
                      or "needs an alias" in l))


def still(name):
    R.step(["screenshotJPEG %s" % name, "wait 150"], timeout=30)

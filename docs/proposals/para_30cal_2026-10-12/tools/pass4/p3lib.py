"""p3lib.py - harness glue for the paratrooper squad third pass. Private harness G:/mohaa-hudfeed5, DISPLAY2, slot owner
hudfeed5, port 12781. Binaries: the integration set built_integ7 (never the *_ship files).
The overlay pk3 = the driver (as coop_mod/coop_selftest_xp.scr) + the mod tree's WORKING copies of FILES (the GOG paks
the harness reads are older than the mod repo) + everything under stage/ (new assets not in the mod tree yet).
MODREF=<commit> takes FILES from that commit instead (the 'before' runs)."""
import os, re, sys, time, zipfile, shutil, hashlib, subprocess
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod"
STAGE = os.path.join(HERE, "stage")
INTEG = os.path.join(os.path.dirname(HERE), "built_integ7")
R.OWNER = "hudfeed5"
R.CLIENT = "G:/mohaa-hudfeed5"
R.EXE = os.path.join(R.CLIENT, "openmohaa_integ7.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")     # G: is full (2026-10-13): finished runs go to the scratchpad
R.PORT = 12781
LOGF = os.path.join(HERE, "p3.log")
FILES = ["coop_mod/parasquad.scr", "coop_mod/parasquad_gun.scr", "coop_mod/paradrop.scr", "anim/mg42_idle.scr",
         "models/static/coop_mg_bags.tik", "models/static/coop_mg_bags/coop_mg_bags.skd",
         "models/static/coop_mg_bags/coop_mg_bags.skc", "models/statweapons/coop_30cal_para.tik",
         "scripts/coop_mgbags.shader"]
MODREF = os.environ.get("MODREF", "")
GAME = os.environ.get("GAMEDLL", "game_p4")           # game_p4 = built_integ7/game.dll (6b515fbf); game_ship = the older one      # game_integ7 = the game.dll before the left-gun engine keys


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def _cp(src, dst):
    if not os.path.exists(dst) or hashlib.md5(open(src, "rb").read()).digest() != hashlib.md5(open(dst, "rb").read()).digest():
        shutil.copyfile(src, dst)


def install():
    _cp(os.path.join(INTEG, "openmohaa.exe"), R.EXE)
    _cp(os.path.join(os.path.dirname(HERE), "built_leftgun", "game.dll"), os.path.join(R.CLIENT, "games", "game_leftgun.dll"))
    _cp(os.path.join(INTEG, "game.dll"), os.path.join(R.CLIENT, "games", "game_p4.dll"))
    _cp(os.path.join(INTEG, "cgame.dll"), os.path.join(R.CLIENT, "cgames", "cgame_integ7.dll"))
    _cp(os.path.join(INTEG, "renderer_opengl2.dll"), os.path.join(R.CLIENT, "renderers", "gl2_integ7.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "games", GAME + ".dll"), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl2_integ7.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    return "cgame_integ7"


def restore_ship():
    for f, d in (("games/game_ship.dll", "game.dll"), ("renderers/gl2_ship.dll", "renderer_opengl2.dll"),
                 ("cgames/cgame_ship.dll", "cgame.dll")):
        shutil.copyfile(os.path.join(R.CLIENT, f), os.path.join(R.CLIENT, d))


def overlay(name="ov_p3.pk3", driver="p3_drv.scr", ref=None, extra=()):
    ref = MODREF if ref is None else ref
    ov = os.path.join(HERE, name)
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        drv = open(os.path.join(HERE, driver), "rb").read()
        if GAME in ("game_ship", "game_live"):
            drv = bytes([10]).join(l for l in drv.split(bytes([10])) if b"//NEWDLL" not in l)
        z.writestr("coop_mod/coop_selftest_xp.scr", drv)
        for rel in list(FILES) + list(extra):
            p = os.path.join(MOD, rel)
            if ref and rel.endswith((".scr", ".tik", ".shader", ".cfg", ".txt")):
                try:
                    z.writestr(rel, subprocess.check_output(["git", "-C", MOD, "show", ref + ":" + rel]))
                    continue
                except subprocess.CalledProcessError:
                    if rel.endswith(".scr"):
                        continue
            if os.path.exists(p):
                z.write(p, rel)
        if not ref:
            for root, _, files in os.walk(STAGE):
                for fn in files:
                    p = os.path.join(root, fn)
                    z.write(p, os.path.relpath(p, STAGE).replace("\\", "/"))
    return ov


EXTRA = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
         "set g_ai 1", "set cg_drawviewmodel 0", "set coop_paraShootdownChance 0", "set s_volume 0",
         "set g_patherror 1"]


def boot(sess, mapname, W=1280, H=720, extra=(), ov=None, ref=None, files=()):
    cg = install()
    R.MAP = mapname
    rundir, notes = S.boot_session(sess, cg, W, H, EXTRA + list(extra), ov or overlay(ref=ref, extra=files))
    log("booted", sess, mapname, "ref=" + (ref or MODREF or "work"), "dog", notes.get("dog"))
    t = R.read_log()
    if "P3 para armed" not in t:
        raise RuntimeError("driver did not start (overlay script did not compile?) " + str(errors()[:4]))
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
    R.step(["set p3_%s %s" % (k, v) for k, v in kv.items()] + ["set p3_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ P3 did %s" % what, timeout, p0):
        raise RuntimeError("driver never did %s" % what)
    time.sleep(0.15)
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


def still(name):
    R.step(["screenshotJPEG %s" % name, "wait 150"], timeout=30)


def psq(p0=0):
    return re.findall(r"\^~\^~\^ (PSQ t=[\d.]+ [^\r\n]*)", R.read_log()[p0:])


def vec(s):
    return [float(v) for v in s.replace("(", " ").replace(")", " ").split()]

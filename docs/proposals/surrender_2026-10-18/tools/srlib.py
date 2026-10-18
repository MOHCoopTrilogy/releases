"""ailib.py - harness glue for the ai_realism tests (adapted from para_30cal pass4/p3lib.py). Private client copy
G:/mohaa-hudfeed2 with the GOG-root release DLLs (hudfeed4/5 held by joinflood), slot owner hudfeed2, port 12721, DISPLAY2 via harness_window.
Overlay pk3 = the driver (as coop_mod/coop_selftest_xp.scr) + the airealism worktree's WORKING copies of FILES."""
import os, re, sys, time, zipfile, shutil, hashlib, subprocess
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mod-surrender"
R.OWNER = "hudfeed4"
R.CLIENT = "G:/mohaa-hudfeed4"
R.EXE = os.path.join(R.CLIENT, "openmohaa_sur.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
R.PORT = 12801
LOGF = os.path.join(HERE, "sr.log")
FILES = os.environ.get("AIFILES", "coop_mod/officer.scr,coop_mod/surrender.scr,coop_mod/aihandler.scr").split(",")
MODREF = os.environ.get("MODREF", "")


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def _cp(src, dst):
    if not os.path.exists(dst) or hashlib.md5(open(src, "rb").read()).digest() != hashlib.md5(open(dst, "rb").read()).digest():
        shutil.copyfile(src, dst)


def install():
    shutil.copyfile(os.path.join(R.CLIENT, "cgame.dll"), os.path.join(R.CLIENT, "cgames", "cgame_sr.dll"))
    return "cgame_sr"


def restore_ship():
    pass


def overlay(name="ov_sr.pk3", driver="sr_drv.scr", ref=None, extra=()):
    ref = MODREF if ref is None else ref
    ov = os.path.join(HERE, name)
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        drv = open(os.path.join(HERE, driver), "rb").read()
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
    return ov


EXTRA = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
         "set g_ai 1", "set cg_drawviewmodel 0", "set s_volume 0", "set g_patherror 1",
         "set s_show_sounds 1", "set coop_aggroDebug 0", "set coop_aiBehav 1", "set coop_aiSquad 1", "set coop_moraleEnable 1",
         "set coop_retreatEnable 1", "set coop_aiDynamic 1", "set coop_aiScaleTest 1", "set coop_retreatChance 100"]


def boot(sess, mapname, W=1280, H=720, extra=(), ov=None, ref=None, files=()):
    cg = install()
    R.MAP = mapname
    rundir, notes = S.boot_session(sess, cg, W, H, EXTRA + list(extra), ov or overlay(ref=ref, extra=files))
    log("booted", sess, mapname, "ref=" + (ref or MODREF or "work"), "dog", notes.get("dog"))
    t = R.read_log()
    if "SR armed" not in t:
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
    R.step(["set sr_%s %s" % (k, v) for k, v in kv.items()] + ["set sr_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ SR did %s" % what, timeout, p0):
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

"""oxlib.py - harness glue for the objectives-next tests (adapted from the surrender lane's srlib.py).
Private client copy G:/mohaa-<OXCL> (default hudfeed2) with the live release DLLs, slot owner = that copy, DISPLAY2 via harness_window.
Overlay pk3 = the driver (as coop_mod/coop_selftest_xp.scr) + the objectives worktree's WORKING copies of FILES.
Run ONLY inside a harness_turn.py turn:  python docs/tools/harness_turn.py wait objectives ... release objectives."""
import os, re, sys, time, zipfile, shutil, hashlib, subprocess
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mod-objectives2"
CLN = os.environ.get("OXCL", "obj2")
R.OWNER = CLN
R.CLIENT = "G:/mohaa-" + CLN
R.EXE = os.path.join(R.CLIENT, "openmohaa_objx.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
R.PORT = int(os.environ.get("OXPORT", "12861"))
LOGF = os.path.join(HERE, "ox.log")
# the files that differ from the shipped v1.10.31 pk3 (alarmplace merge + this lane)
FILES = os.environ.get("OXFILES", ",".join([
    "coop_mod/alarm.scr", "coop_mod/alarmpoints.scr", "coop_mod/carry.scr", "coop_mod/coop_counter.scr",
    "coop_mod/coop_counter_zones.scr", "coop_mod/main.scr", "coop_mod/officer.scr", "coop_mod/reinf_mg.scr",
    "coop_mod/missioncomplete.scr", "coop_mod/objx.scr", "coop_mod/objx2.scr", "coop_mod/objx_points.scr", "models/human/new_generic_human.tik", "maps/m1l3c.scr",
    "ui/coop_objectives.urc", "ui/coop_objectives/obj_setup.cfg"])).split(",")
MODREF = os.environ.get("MODREF", "")


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def install():
    # the LIVE exe + cgame + game + renderer (read-only copies from the user's install), into this harness copy
    exe = os.path.join(R.CLIENT, "openmohaa_objx.exe")
    for src, dst in (("openmohaa.exe", exe), ("game.dll", os.path.join(R.CLIENT, "game.dll")),
                     ("renderer_opengl2.dll", os.path.join(R.CLIENT, "renderer_opengl2.dll"))):
        a = os.path.join("G:/mohaa-gl2", src)
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(a):
            shutil.copyfile(a, dst)
    md5stub = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")   # run_sweep.boot_session hashes this name
    if not os.path.exists(md5stub):
        shutil.copyfile(exe, md5stub)
    os.makedirs(os.path.join(R.CLIENT, "cgames"), exist_ok=True)
    shutil.copyfile("G:/mohaa-gl2/cgame.dll", os.path.join(R.CLIENT, "cgames", "cgame_ox.dll"))
    return "cgame_ox"


def restore_ship():
    pass


def overlay(name="ov_ox.pk3", driver="ox_drv.scr", ref=None, extra=()):
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
            if rel == "coop_mod/objx_points.scr" and os.environ.get("OXPOINTS"):
                z.write(os.environ["OXPOINTS"], rel)
            elif os.path.exists(p):
                z.write(p, rel)
    return ov


EXTRA = ["set coop_st_xp 1", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
         "set g_ai 1", "set cg_drawviewmodel 1", "set s_volume 0", "set g_patherror 1",
         "set coop_aiBehav 1", "set coop_aiSquad 1", "set coop_objx 1", "set coop_objxDebug 1"]


def boot(sess, mapname, W=1280, H=720, extra=(), ov=None, ref=None, files=()):
    cg = install()
    R.MAP = mapname
    rundir, notes = S.boot_session(sess, cg, W, H, EXTRA + list(extra), ov or overlay(ref=ref, extra=files))
    log("booted", sess, mapname, "ref=" + (ref or MODREF or "work"), "dog", notes.get("dog"))
    t = R.read_log()
    if "OX armed" not in t:
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
    R.step(["set ox_%s %s" % (k, v) for k, v in kv.items()] + ["set ox_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ OX did %s" % what, timeout, p0):
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


def objx_lines(p0=0):
    return re.findall(r"\^~\^~\^ (OBJX [^\r\n]*)", R.read_log()[p0:])


def vec(s):
    return [float(v) for v in s.replace("(", " ").replace(")", " ").split()]


def wait_active(timeout=420):
    """map intros (m1l1 truck ride, jeep rides) keep the player inactive: wait until coop_isActive is 1"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        p0 = cmd("act")
        v = since(p0, r"OX act (\S+)")
        if v and v[-1] == "1":
            return True
        time.sleep(6)
    return False

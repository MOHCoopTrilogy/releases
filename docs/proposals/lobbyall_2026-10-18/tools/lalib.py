"""lalib.py - harness glue for the lobby-for-every-mission test. Private client copy G:/mohaa-hudfeed5 (env LACL),
openmohaa_surx.exe, GOG-root release DLLs. Overlay pk3 = driver + worktree files. Launch is patched to exec the
MENU cfg (mission_start.cfg = the Apply button's cfg) or campaign_start.cfg instead of start_server.cfg."""
import os, re, sys, time, zipfile, shutil, inspect
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = "C:/mohaa-coop-dev/hzm-mod-lobbyall"
CLN = os.environ.get("LACL", "hudfeed5")
R.OWNER = CLN
R.CLIENT = "G:/mohaa-" + CLN
R.EXE = os.path.join(R.CLIENT, os.environ.get("LAEXE", "openmohaa_surx.exe"))
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
R.PORT = 12811
LOGF = os.path.join(HERE, "la.log")
FILES = ["coop_mod/main.scr", "coop_mod/cfg/mission_start.cfg", "coop_mod/lobby.scr", "coop_mod/lobbybrief.scr", "global/missioncomplete.scr"]


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def patch_launch(startcfg):
    src = inspect.getsource(R.launch).replace("coop_mod/start_server.cfg", startcfg)
    exec(src, R.__dict__)


def overlay(name="ov_la.pk3"):
    ov = os.path.join(HERE, name)
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/coop_selftest_xp.scr", open(os.path.join(HERE, "lobbyall_drv.scr"), "rb").read())
        for rel in FILES:
            z.write(os.path.join(MOD, rel), rel)
    return ov


def install():
    shutil.copyfile(os.path.join(R.CLIENT, "cgame.dll"), os.path.join(R.CLIENT, "cgames", "cgame_la.dll"))
    return "cgame_la"


EXTRA = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
         "set g_ai 1", "set s_volume 0", "set sv_maxclients 4", "set ui_maxclients 4"]


def errors():
    t = R.read_log()
    return sorted(set(l[-170:] for l in t.splitlines()
                      if "Script Error" in l or "not properly loaded" in l or "Couldn't compile" in l or "parse error" in l))


def cmd(what, timeout=40):
    p0 = len(R.read_log())
    R.step(["set la_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ LA did %s" % what, timeout, p0):
        raise RuntimeError("driver never did " + what)
    time.sleep(0.2)
    return p0


def join_loop(tries=4):
    for k in range(tries):
        R.step(["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "set g_teamswitchdelay 0", "join_team allies",
                "wait 20", "popmenu 0", "wait 40", "popmenu 0", "wait 20"])
        time.sleep(3)

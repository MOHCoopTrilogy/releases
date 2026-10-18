"""smlib.py - harness glue for the smoke-consume / one-reward / indoor-cache proof (2026-10-18). Wraps rewards_2026-10-15/tools/rwlib.py
(private client G:/mohaa-hudfeed5, DISPLAY2 via harness_window) but overlays the hzm-mod-smokec WORKING files and this folder's driver."""
import os, sys
RW = "C:/mohaa-coop-dev/docs/proposals/rewards_2026-10-15/tools"
sys.path.insert(0, RW)
import rwlib as G
HERE = os.path.dirname(os.path.abspath(__file__))
G.HERE = HERE
G.MOD = "C:/mohaa-coop-dev/hzm-mod-smokec"
G.LOGF = os.path.join(HERE, "sm.log")
G.R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
G.FILES = ["coop_mod/officer.scr", "coop_mod/objective_drop.scr", "coop_mod/keyitems.scr", "coop_mod/paradrop.scr",
           "coop_mod/indoor_maps.scr"]
G.RWREF = os.environ.get("SMREF", "")
_ov = G.overlay
def overlay(name="ov_sm.pk3", driver="sm_drv.scr", ref=None, extra=()):
    ov = _ov(name, driver, ref, extra)
    if os.environ.get("SMBOTS"):
        # test-only: server_rules.cfg zeroes the latched bot cap on every coop start; let ONE engine bot join as a second coop Player
        import zipfile
        t = open(G.MOD + "/coop_mod/cfg/server_rules.cfg", "rb").read().decode("utf-8", "replace")
        t = t.replace("set sv_maxbots 0", "set sv_maxbots 2").replace("set sv_numbots 0", "set sv_numbots 1")
        with zipfile.ZipFile(ov, "a", zipfile.ZIP_DEFLATED) as z:
            z.writestr("coop_mod/cfg/server_rules.cfg", t)
    return ov
G.overlay = overlay
R = G.R

_c = os.environ.get("SMCLIENT")
if _c:
    _ports = {"hudfeed4": 12793, "hudfeed2": 12721, "hudfeed5": 12795}
    R.OWNER = _c
    R.CLIENT = "G:/mohaa-" + _c
    R.EXE = os.path.join(R.CLIENT, "openmohaa_rw.exe")
    R.HOME = os.path.join(R.CLIENT, "home")
    R.MAINTT = os.path.join(R.HOME, "maintt")
    R.LOG = os.path.join(R.MAINTT, "qconsole.log")
    R.SHOTS = os.path.join(R.MAINTT, "screenshots")
    R.PRISTINE = os.path.join(R.CLIENT, "pristine")
    R.PORT = _ports.get(_c, 12795)

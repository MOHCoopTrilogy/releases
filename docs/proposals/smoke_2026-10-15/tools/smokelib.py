"""smokelib.py - harness glue for the smoke-screen proof: reuses the ai_realism ailib but points at the smoke worktree, the
smoke driver and a free private client folder (G:/mohaa-hudfeed4, slot owner hudfeed4, DISPLAY2 via harness_window).
Overlay pk3 = the driver (as coop_mod/coop_selftest_xp.scr) + the smoke worktree's WORKING copies of FILES + the
fixes-pak tik (the real pak is built by docs/tools/gen_fixes_pak.py at integration)."""
import os, sys
AI = "C:/mohaa-coop-dev/docs/proposals/ai_realism_2026-10-15/tools"
sys.path.insert(0, AI)
import ailib as G
HERE = os.path.dirname(os.path.abspath(__file__))
G.HERE = HERE
G.MOD = "C:/mohaa-coop-dev/hzm-mod-smoke"
G.LOGF = os.path.join(HERE, "ss.log")
CL = os.environ.get("SSCLIENT", "hudfeed4")
G.R.OWNER = CL
G.R.CLIENT = "G:/mohaa-" + CL + "/smoke"
G.R.EXE = os.path.join(G.R.CLIENT, os.environ.get("SSEXE", "openmohaa_smoke.exe"))
G.R.HOME = "G:/mohaa-" + CL + "/home"
G.R.MAINTT = os.path.join(G.R.HOME, "maintt")
G.R.LOG = os.path.join(G.R.MAINTT, "qconsole.log")
G.R.SHOTS = os.path.join(G.R.MAINTT, "screenshots")
G.R.PRISTINE = os.path.join(G.R.CLIENT, "pristine")
G.R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
G.R.PORT = int(os.environ.get("SSPORT", "12761"))
G.FILES = os.environ.get("SSFILES", "coop_mod/smokescreen.scr,coop_mod/officer.scr,coop_mod/precache.scr").split(",")
FIX = "C:/mohaa-coop-dev/docs/tools/assets/fixes/"
_ov = G.overlay
def overlay(name="ov_ss.pk3", driver="ss_drv.scr", ref=None, extra=()):
    import zipfile
    ov = _ov(name, driver, ref, extra)
    with zipfile.ZipFile(ov, "a", zipfile.ZIP_DEFLATED) as z:
        for rel in ("models/fx/coop_screensmoke.tik",) + tuple(os.environ.get("SSFIX", "").split(",") if os.environ.get("SSFIX") else ()):
            z.write(FIX + rel, rel)
    return ov
G.overlay = overlay
R = G.R

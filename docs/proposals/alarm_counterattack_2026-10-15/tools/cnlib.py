"""cnlib.py - harness glue for alarm/counter tests: reuses the ai_realism ailib (private client G:/mohaa-hudfeed2, DISPLAY2) but
points at the alarm worktree, the cn driver and this folder's runs/logs."""
import os, sys
AI = "C:/mohaa-coop-dev/docs/proposals/ai_realism_2026-10-15/tools"
sys.path.insert(0, AI)
import ailib as G
HERE = os.path.dirname(os.path.abspath(__file__))
G.HERE = HERE
G.MOD = "C:/mohaa-coop-dev/hzm-mod-alarm"
G.LOGF = os.path.join(HERE, "cn.log")
G.R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
G.FILES = os.environ.get("CNFILES", "coop_mod/coop_counter.scr,coop_mod/missioncomplete.scr,autoexec.cfg").split(",")
_ov = G.overlay
def overlay(name="ov_cn.pk3", driver="cn_drv.scr", ref=None, extra=()):
    return _ov(name, driver, ref, extra)
G.overlay = overlay
R = G.R

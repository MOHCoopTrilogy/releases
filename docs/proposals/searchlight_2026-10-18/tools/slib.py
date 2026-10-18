"""slib.py - harness glue for the searchlight tests: ailib (private client G:/mohaa-hudfeed2) pointed at the searchlight worktree."""
import os, sys
AI = "C:/mohaa-coop-dev/docs/proposals/ai_realism_2026-10-15/tools"
sys.path.insert(0, AI)
import ailib as G
HERE = os.path.dirname(os.path.abspath(__file__))
G.HERE = HERE
G.MOD = "C:/mohaa-coop-dev/hzm-mod-searchlight"
G.LOGF = os.path.join(HERE, "sl.log")
G.R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
G.FILES = ["global/spotlight.scr"]
_ov = G.overlay
def overlay(name="ov_sl.pk3", driver="sl_drv.scr", ref=None, extra=()):
    return _ov(name, driver, ref, extra)
G.overlay = overlay
R = G.R

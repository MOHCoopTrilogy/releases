"""aplib.py - harness glue for the alarm placement v2 proofs: private client G:/mohaa-hudfeed2 via cnlib/ailib (harness_guard slot,
DISPLAY2), overlay = ap_drv.scr + the alarmplace worktree's alarm.scr + alarmpoints.scr (+ anything in APFILES)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
G.MOD = "C:/mohaa-coop-dev/hzm-mod-alarmplace"
G.FILES = os.environ.get("APFILES", "coop_mod/alarm.scr,coop_mod/alarmpoints.scr,coop_mod/coop_counter.scr,coop_mod/coop_counter_zones.scr").split(",")
HERE = C.HERE
_orig = C._ov


def overlay(name="ov_ap.pk3", driver="ap_drv.scr", ref=None, extra=()):
    return _orig(name, driver, ref, extra)


G.overlay = overlay

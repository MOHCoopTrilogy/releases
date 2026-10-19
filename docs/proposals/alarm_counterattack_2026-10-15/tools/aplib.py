"""aplib.py - harness glue for the alarm placement v2 proofs: private client G:/mohaa-hudfeed2 via cnlib/ailib (harness_guard slot,
DISPLAY2), overlay = ap_drv.scr + the alarmplace worktree's alarm.scr + alarmpoints.scr (+ anything in APFILES)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
G.MOD = "C:/mohaa-coop-dev/hzm-mod-alarmplace"

# harness copy: the first of hudfeed2 / 4 / 5 whose harness_guard slot is free (harness_turn allows 2 games, each needs its own copy)
import time
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import harness_guard as _hg
_SLOTS = [("hudfeed2", "G:/mohaa-hudfeed2", "openmohaa_air.exe", 12721), ("hudfeed4", "G:/mohaa-hudfeed4", "openmohaa_hdlive.exe", 12781),
          ("hudfeed5", "G:/mohaa-hudfeed5", "openmohaa_hdlive.exe", 12782)]


def _pick():
    for _t in range(120):
        for own, cl, exe, port in _SLOTS:
            if _hg.slot_holder(own) is None:
                return own, cl, exe, port
        time.sleep(5)
    raise RuntimeError("no harness slot free")


_own, _cl, _exe, _port = _pick()
R.OWNER = _own
R.CLIENT = _cl
R.EXE = os.path.join(_cl, _exe)
R.HOME = os.path.join(_cl, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(_cl, "pristine")
R.PORT = _port
print("harness copy:", _own, _exe, flush=True)
G.FILES = os.environ.get("APFILES", "coop_mod/alarm.scr,coop_mod/alarmpoints.scr,coop_mod/coop_counter.scr,coop_mod/coop_counter_zones.scr,coop_mod/reinf_mg.scr,coop_mod/carry.scr,coop_mod/main.scr,coop_mod/officer.scr").split(",")
HERE = C.HERE
_orig = C._ov


def overlay(name="ov_ap.pk3", driver="ap_drv.scr", ref=None, extra=()):
    return _orig(name, driver, ref, extra)


G.overlay = overlay

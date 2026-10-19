"""avlib.py - harness glue for the alarm-vehicle tests. Reuses the ai_realism ailib (protocol: ai_cmd cvar, '^~^~^ AI did <cmd>')
but points at the alarmveh worktree and the FREE private client copy G:/mohaa-hudfeed4 (exe openmohaa_c96.exe has the same md5 as
hudfeed2's openmohaa_air.exe; release DLLs identical to the GOG root). Slot owner hudfeed4, port 12741. Private copies only: nothing is
written to G:\\mohaa-gl2 or the GOG root (the GOG root is read-only basepath)."""
import os, sys
AI = "C:/mohaa-coop-dev/docs/proposals/ai_realism_2026-10-15/tools"
sys.path.insert(0, AI)
import ailib as G
HERE = os.path.dirname(os.path.abspath(__file__))
G.HERE = HERE
G.MOD = "C:/mohaa-coop-dev/hzm-mod-alarmveh"
G.LOGF = os.path.join(HERE, "av.log")
R = G.R
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import harness_guard as _hg
# first FREE private client copy (identical release DLLs; exe openmohaa_c96/_air have the same md5): hudfeed4, else hudfeed2
_slot = os.environ.get("AVSLOT") or ("hudfeed4" if _hg.slot_holder("hudfeed4") is None else "hudfeed2")
R.OWNER = _slot
R.CLIENT = "G:/mohaa-" + _slot
R.EXE = os.path.join(R.CLIENT, {"hudfeed4": "openmohaa_c96.exe", "hudfeed5": "openmohaa_c96.exe", "hudfeed3": "openmohaa_hdlive.exe"}.get(_slot, "openmohaa_air.exe"))
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
R.PORT = {"hudfeed4": 12741, "hudfeed3": 12731, "hudfeed5": 12751}.get(_slot, 12721)
G.FILES = os.environ.get("AVFILES", "coop_mod/alarmveh.scr,coop_mod/alarmveh_routes.scr,coop_mod/alarm.scr").split(",")
_ov = G.overlay


def overlay(name="ov_av.pk3", driver="av_drv.scr", ref=None, extra=()):
    return _ov(name, driver, ref, extra)


G.overlay = overlay

"""asnlib.py - harness glue for the alarm-sniper tests: reuses ai_realism ailib (private client G:/mohaa-hudfeed2, DISPLAY2 via harness_window)
but overlays the alarmsnipers worktree files and this folder's driver (asn_drv.scr). One game at a time (wait_idle)."""
import os, sys, time, subprocess
AI = "C:/mohaa-coop-dev/docs/proposals/ai_realism_2026-10-15/tools"
sys.path.insert(0, AI)
sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
import ailib as G
import harness_guard as hg
HERE = os.path.dirname(os.path.abspath(__file__))
G.HERE = HERE
G.MOD = "C:/mohaa-coop-dev/hzm-mod-alarmsnipers"
G.LOGF = os.path.join(HERE, "asn.log")
G.R.RUNS = os.path.join(HERE, "runs").replace("\\", "/")
G.FILES = ["coop_mod/alarmsnipers.scr", "coop_mod/alarmsnipers_spots.scr", "coop_mod/alarm.scr"]
_ov = G.overlay


def overlay(name="ov_asn.pk3", driver="asn_drv.scr", ref=None, extra=()):
    return _ov(name, driver, ref, extra)


G.overlay = overlay
R = G.R


def _busy():
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout.lower()
    return [l.split(",")[0].strip('"') for l in out.splitlines() if "openmohaa" in l or "omohaaded" in l]


def wait_idle(maxmin=240):
    """block until NO openmohaa*/omohaaded* process exists (one game at a time, never alongside another agent's client); tight poll so a
    gap between another agent's back-to-back runs is not missed"""
    t0 = time.time()
    last = 0
    while time.time() - t0 < maxmin * 60:
        b = _busy()
        if not b:
            return True
        if time.time() - last > 120:
            print("waiting, running:", b, flush=True)
            last = time.time()
        time.sleep(0.4)
    return False


SRC = "G:/mohaa-hudfeed2"
PORTS = {"hudfeed2": 12721, "hudfeed4": 12831, "hudfeed5": 12841}


def _in_use(folder):
    f = folder.lower().replace("/", "\\")
    return [p["pid"] for p in hg.classify() if (p.get("path") or "").lower().startswith(f)]


def configure_slot():
    """pick the first harness folder with no running game in it (hudfeed2, then hudfeed4, then hudfeed5) and point ailib's R at it.
    hudfeed4/5 get a private engine subfolder asn/ copied from hudfeed2 (the exact engine set the alarm tests were built against) so
    other agents' exe/dll swaps in the folder root do not change what I run; home stays the folder's registered home."""
    import shutil
    for owner in ("hudfeed2", "hudfeed4", "hudfeed5"):
        base = "G:/mohaa-" + owner
        if not os.path.isdir(base) or _in_use(base):
            continue
        if owner == "hudfeed2":
            client, exe = base, "openmohaa_air.exe"
        else:
            client, exe = base + "/asn", "openmohaa_asn.exe"
            if not os.path.isdir(client):
                os.makedirs(client)
                for fn in ("OpenAL64.dll", "SDL2.dll", "libcurl.dll", "cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll"):
                    shutil.copyfile(SRC + "/" + fn, client + "/" + fn)
                shutil.copyfile(SRC + "/openmohaa_air.exe", client + "/" + exe)
                shutil.copytree(SRC + "/pristine", client + "/pristine")
                for sub in ("cgames", "renderers", "games"):
                    if os.path.isdir(SRC + "/" + sub):
                        shutil.copytree(SRC + "/" + sub, client + "/" + sub)
                os.makedirs(base + "/home/maintt", exist_ok=True)
        R.OWNER = owner
        R.CLIENT = client
        R.EXE = client + "/" + exe
        R.HOME = base + "/home"
        R.MAINTT = R.HOME + "/maintt"
        R.LOG = R.MAINTT + "/qconsole.log"
        R.SHOTS = R.MAINTT + "/screenshots"
        R.PRISTINE = client + "/pristine"
        R.PORT = PORTS[owner]
        return owner
    return None

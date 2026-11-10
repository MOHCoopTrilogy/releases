r"""attic70_run.py - v1.10.70 cfg-only stills (the OWN DISCS film cans, the widened war map) on the private client G:\mohaa-attic
(attic_run's launcher: harness_window's foreground / cursor / capture guard, enforced). Same rules as mp69_run.py:

User rules (2026-11-09/10, they play on the TV): no pad script, no input, never a map; muted; in_mouse 0, in_nograb 1, in_gamepad 0,
in_joystick 0; the window on the 1080p second screen picked by RESOLUTION (HZM_TEST_RES=1920x1080); any guard trip stops every
later launch (STOP flag beside this run's output). Only this harness's own client (G:\mohaa-attic) is waited for - never another.

    python attic70_run.py shots <pak> <ui dir> <extra dir|-> <tag> <shots.json>
shots.json = [[name, [cfg lines run before the screenshot]], ...]; waits are MILLISECONDS (TRAPS: a cfg's wait is ms here).
The client boots into the 3D attic (ui_atticMain 1) and stays at its home view unless a shot's lines move it.
"""
import json, os, subprocess, sys, time
os.environ["HZM_TEST_RES"] = "1920x1080"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attic_run as A  # noqa: E402
import mp69_run as M  # noqa: E402   (its setup(): the menus pak + the ui overlay)
E = A.E
RUNS = os.environ.get("ATTIC70_RUNS", r"H:\hzm_work\attic62\ship70\runs")
STOP = os.path.join(RUNS, "GUARD_TRIPPED.flag")
os.makedirs(RUNS, exist_ok=True)
E.RUNS = RUNS
M.STOP = STOP
TRIPS = M.TRIPS


def quiet_wait():
    """wait only for THIS harness's client copy (another agent's run on it); the release-flag rule of attic_run is not ours"""
    n = 0
    while n < 3:
        ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-Process openmohaa* -ErrorAction SilentlyContinue | ForEach-Object { $_.Path }"],
                            capture_output=True, text=True).stdout.lower()
        busy = A.CLIENT.lower() + "\\" in ps
        n = 0 if busy else n + 1
        if busy:
            E.log("waiting: G:\\mohaa-attic is running")
        time.sleep(5)


A.quiet_wait = quiet_wait


def shots(pak, ui, extra, tag, spec):
    if os.path.exists(STOP):
        raise SystemExit("a guard tripped earlier (%s) - no more launches" % STOP)
    M.setup(pak, ui, extra)
    w, h, center, lay = E.RES[os.environ.get("ATTIC70_RES", "1080")]
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow 1",
         "set coop_hardcore 0", "set ui_wxHour 12.5", "set ui_wxWeather 1", "wait 12000", "echo ^~^~^ A70 start"]
    for name, cmds in json.load(open(spec)):
        L += cmds + ["echo ^~^~^ A70 shot %s" % name, "screenshot a70_%s_%s" % (tag, name), "wait 700"]
    L += ["echo ^~^~^ MR done", "wait 1500", "quit"]
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30",
            "+set", "in_mouse", "0", "+set", "in_nograb", "1", "+set", "in_gamepad", "0", "+set", "in_joystick", "0"]
    out = A.launch("a70_%s" % tag, w, h, L, args)
    if TRIPS:
        raise SystemExit("GUARD TRIPPED: %s - stopping" % (TRIPS[:2],))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "shots":
        print(shots(*a[1:6]))

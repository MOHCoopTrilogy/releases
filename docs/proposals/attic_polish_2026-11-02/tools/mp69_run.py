r"""mp69_run.py - v1.10.69 MP-room props: cfg-only stills on the private client G:\mohaa-attic (attic_run's launcher / guard).

User rules (2026-11-09, they play on the TV): no pad script, no input, never a map; muted; in_mouse 0, in_nograb 1, in_gamepad 0,
in_joystick 0; the window on the 1080p second screen picked by RESOLUTION (HZM_TEST_RES=1920x1080); any guard trip stops every
later launch (STOP flag beside this run's output).

    python mp69_run.py shots <pak> <ui dir> <extra dir|-> <tag> <shots.json>
shots.json = [[name, [cfg lines run before the screenshot]], ...]; waits are MILLISECONDS (TRAPS: a cfg's wait is ms here).
"""
import json, os, shutil, sys, zipfile
os.environ["HZM_TEST_RES"] = "1920x1080"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import attic_run as A  # noqa: E402
E = A.E
STOP = r"H:\hzm_work\mp69\runs\GUARD_TRIPPED.flag"
_log0 = E.log
TRIPS = []


def _log(*a):
    if a and a[0] == "VIOLATION":
        TRIPS.append(a)
        open(STOP, "w").write(repr(a))
    _log0(*a)


E.log = _log
E.RUNS = r"H:\hzm_work\mp69\runs"


def setup(pak, ui, extra):
    shutil.copyfile(pak, os.path.join(E.MAINTT, "zzzzzzzzzzzzzz_hzm_menus3d.pk3"))
    with zipfile.ZipFile(os.path.join(E.MAINTT, A.OVERLAY), "w", zipfile.ZIP_DEFLATED) as z:
        names = set()
        if extra and extra != "-":
            for r, _, fs in os.walk(extra):
                for f in fs:
                    p = os.path.join(r, f)
                    n = os.path.relpath(p, extra).replace("\\", "/")
                    z.write(p, n)
                    names.add(n.lower())
        for f in os.listdir(ui):
            p = os.path.join(ui, f)
            if os.path.isfile(p) and f.lower().endswith((".urc", ".inc", ".cfg")) and ("ui/" + f).lower() not in names:
                z.write(p, "ui/" + f)
        mm = os.path.join(ui, "coop_menumusic")
        for f in (os.listdir(mm) if os.path.isdir(mm) else []):
            z.write(os.path.join(mm, f), "ui/coop_menumusic/" + f)


def shots(pak, ui, extra, tag, spec):
    if os.path.exists(STOP):
        raise SystemExit("a guard tripped earlier (%s) - no more launches" % STOP)
    setup(pak, ui, extra)
    w, h, center, lay = E.RES["1080"]
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow 1",
         "set coop_hardcore 0", "set ui_wxHour 12.5", "set ui_wxWeather 1", "wait 12000", "echo ^~^~^ MP69 start",
         "exec ui/hzm_attic_go_mp.cfg", "wait 3500"]
    for name, cmds in json.load(open(spec)):
        L += cmds + ["screenshot mp69_%s_%s" % (tag, name), "wait 700"]
    L += ["echo ^~^~^ MR done", "wait 1500", "quit"]
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30",
            "+set", "in_mouse", "0", "+set", "in_nograb", "1", "+set", "in_gamepad", "0", "+set", "in_joystick", "0"]
    out = A.launch("mp69_%s" % tag, w, h, L, args)
    if TRIPS:
        raise SystemExit("GUARD TRIPPED: %s - stopping" % (TRIPS[:2],))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "shots":
        print(shots(*a[1:6]))

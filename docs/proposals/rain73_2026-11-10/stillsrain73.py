r"""stillsrain73.py <menus pak> <mod ui dir> <res 1080|219> <tag> <set: bands|fog> - rain73 QA stills on the PRIVATE client
G:\mohaa-rain73 (the rain73 exe + the live v1.10.73 DLLs). mp69_run's launcher and guard (muted, no input, 1080p screen).
bands: each intensity (ui_wxForce "I F") at home, LOOK OUTSIDE, LOOK UP; 3 frames 150 ms apart for the motion; glass given time to fill.
fog:   thin / thick morning fog at 07:00, noon and 23:00, and a storm peak with its haze.
"""
import os, sys
os.environ["HZM_TEST_RES"] = "1920x1080"
sys.path.insert(0, r"H:\hzm_work\rain73-root\docs\proposals\attic_polish_2026-11-02\tools")
import mp69_run as M  # noqa: E402

CL = r"G:\mohaa-rain73"
M.A.CLIENT = CL
E = M.E
E.CLIENT, E.EXE = CL, os.path.join(CL, "openmohaa.exe")
E.HOME = os.path.join(CL, "home")
E.MAINTT = os.path.join(E.HOME, "maintt")
E.LOG, E.SHOTS = os.path.join(E.MAINTT, "qconsole.log"), os.path.join(E.MAINTT, "screenshots")
E.RUNS = r"H:\hzm_work\rain73\runs"
os.makedirs(E.RUNS, exist_ok=True)
HOME = "-36.7 21.0 102.4 7.01 0.00 0.00 55.11"
OUT = "315.0 210.0 84.0 0.00 0.00 0.00 62.00"
UP = "202.7 128.7 106.4 -65.13 90.00 0.00 50.00"


def views(L, tag, fill):
    for vn, stop, pose in (("home", 0, HOME), ("out", 3, OUT), ("up", 4, UP)):
        L += ["set ui_atcStop %d; globalwidgetcommand atticscene scenefly 0.4 %s" % (stop, pose), "wait %d" % fill]
        for k in range(3):
            L += ["screenshot r73_%s_%s_%d" % (tag, vn, k), "wait 150"]


def script(which):
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_camslow 1", "set coop_hardcore 0", "set ui_wxHour 12.5",
         "set ui_wxWeather 3", "set ui_wxForce \"0.1 0\"", "wait 12000", "wait 6000"]
    if which == "perf":
        # frame time: the storm at its peak, each view 14 s (the WXRAIN / SCENE3D prints come every 240 / 120 frames), rain on then off
        L += ["set ui_wxDebug 1", "set ui_scene_debug 1", "set ui_wxWeather 4", "set ui_wxForce \"1.0 0.9\"", "wait 10000"]
        for parts in (1, 0):
            L += ["set ui_wxRainParts %d" % parts, "echo ^~^~^ PERF rainparts %d" % parts]
            for vn, stop, pose in (("home", 0, HOME), ("out", 3, OUT), ("up", 4, UP)):
                L += ["set ui_atcStop %d; globalwidgetcommand atticscene scenefly 0.4 %s" % (stop, pose), "echo ^~^~^ PERF view %s" % vn, "wait 14000"]
        L += ["set ui_wxDebug 0", "set ui_scene_debug 0"]
    elif which == "storm":
        for nm, I, F in (("4heavy", 0.78, 0.10), ("5storm", 1.0, 0.90)):
            L += ["set ui_wxWeather 4", "set ui_wxForce \"%.2f %.2f\"" % (I, F), "wait 12000"]
            views(L, nm, 2500)
        L += ["set ui_wxFlashHold 0.8", "set ui_atcStop 3; globalwidgetcommand atticscene scenefly 0.4 %s" % OUT, "wait 1500",
              "screenshot r73_5storm_flash_out", "wait 300", "set ui_wxFlashHold \"\""]
    elif which == "bands":
        for nm, I in (("1drizzle", 0.10), ("2light", 0.30), ("3steady", 0.50), ("4heavy", 0.78), ("5storm", 1.0)):
            F = 0.0 if I < 0.75 else (I - 0.75) / 0.25 * 0.9
            L += ["set ui_wxForce \"%.2f %.2f\"" % (I, F), "wait 9000"]
            views(L, nm, 2500)
    else:
        for nm, hour, F in (("fog_morn_thin", 7.0, 0.4), ("fog_morn_thick", 7.0, 0.9), ("fog_noon_thick", 12.5, 0.9), ("fog_night_thin", 23.0, 0.4),
                            ("fog_night_thick", 23.0, 0.9)):
            L += ["set ui_wxHour %.1f" % hour, "set ui_wxWeather 1", "set ui_wxForce \"0.0 %.2f\"" % F, "wait 4000"]
            for vn, stop, pose in (("home", 0, HOME), ("out", 3, OUT)):
                L += ["set ui_atcStop %d; globalwidgetcommand atticscene scenefly 0.4 %s" % (stop, pose), "wait 1500", "screenshot r73_%s_%s" % (nm, vn), "wait 300"]
        L += ["set ui_wxHour 16.0", "set ui_wxWeather 4", "set ui_wxForce \"1.0 0.9\"", "set ui_wxFlashHold 0.8", "wait 8000"]
        L += ["set ui_atcStop 3; globalwidgetcommand atticscene scenefly 0.4 %s" % OUT, "wait 1500", "screenshot r73_storm_peak_flash_out", "wait 300"]
        L += ["set ui_wxFlashHold \"\"", "wait 600", "screenshot r73_storm_peak_out", "wait 300"]
    L += ["wait 600", "quit"]
    return L


def run(pak, ui, res, tag, which):
    os.environ["MP69_RES"] = res
    if os.path.exists(M.STOP):
        raise SystemExit("guard tripped earlier")
    M.setup(pak, ui, "-")
    w, h, center, lay = E.RES[res]
    L = ["set ui_menuCenter %d" % center] + script(which)
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1", "+set", "s_volume", "0",
            "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30", "+set", "in_mouse", "0",
            "+set", "in_nograb", "1", "+set", "in_gamepad", "0", "+set", "in_joystick", "0", "+set", "coop_tinnitus", "0"]
    out = M.A.launch("r73_%s" % tag, w, h, L, args)
    if M.TRIPS:
        raise SystemExit("GUARD TRIPPED: %s" % (M.TRIPS[:2],))
    print(out)


if __name__ == "__main__":
    run(*sys.argv[1:6])

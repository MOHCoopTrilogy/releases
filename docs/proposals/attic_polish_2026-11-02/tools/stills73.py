r"""stills73.py <menus pak> <mod ui dir> <res 1080|219> <tag> - v1.10.73 polish QA stills on the PRIVATE client G:\mohaa-polish73
(the polish73 exe + the live v1.10.73 DLLs; never the user's install, never another agent's client). mp69_run's launcher and guard:
muted, in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0, the 1080p screen (HZM_TEST_RES=1920x1080), cfg-only (no input), a
guard trip stops every later launch. Waits are ms.
"""
import os, sys
os.environ["HZM_TEST_RES"] = "1920x1080"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mp69_run as M  # noqa: E402

CL = r"G:\mohaa-polish73"
M.A.CLIENT = CL
E = M.E
E.CLIENT = CL
E.EXE = os.path.join(CL, "openmohaa.exe")
E.HOME = os.path.join(CL, "home")
E.MAINTT = os.path.join(E.HOME, "maintt")
E.LOG = os.path.join(E.MAINTT, "qconsole.log")
E.SHOTS = os.path.join(E.MAINTT, "screenshots")
E.RUNS = r"H:\hzm_work\polish73\runs"
os.makedirs(E.RUNS, exist_ok=True)

HOME = "-36.7 21.0 102.4 7.01 0.00 0.00 55.11"
TURN = "-35.2 21.0 102.4 30.00 68.00 0.00 55.11"
DOWN = "12.0 126.0 70.0 55.00 90.00 0.00 55.00"
CLICK = ("set ui_scene_hot 0; set ui_atcHatch 0; globalwidgetcommand atticscene sceneleave; globalwidgetcommand atticscene scenefly 0.9 %s" % DOWN)


def shot(L, name, wait=900):
    L += ["wait %d" % wait, "screenshot p73_%s" % name, "wait 400"]


def script():
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_camslow 1", "set coop_hardcore 0", "set ui_wxHour 12.5",
         "set ui_wxWeather 3", "set ui_wxDebug 1", "wait 12000", "wait 14000", "echo ^~^~^ P73 start"]
    # ---- the attic, steady rain
    shot(L, "01_home_rain", 500)
    L += ["set ui_atcHatch 1", "globalwidgetcommand atticscene scenefly 0.5 %s" % TURN]
    shot(L, "02_hatch_idle", 1400)
    L += ["set ui_scene_hot 21"]
    shot(L, "03_hatch_hover", 900)
    L += [CLICK, "wait 430", "screenshot p73_04_hatch_midfly", "wait 900", "pushmenu hzm_quitconfirm"]
    shot(L, "05_hatch_confirm", 1500)
    L += ["popmenu 0"]
    shot(L, "06_after_stay_home", 2200)
    # ---- the skylight from home and LOOK UP, rain
    L += ["set ui_atcStop 4; set ui_scene_hot 0; globalwidgetcommand atticscene scenefly 0.7 202.7 128.7 106.4 -65.13 90.00 0.00 50.00"]
    shot(L, "07_lookup_rain_a", 1600)
    shot(L, "08_lookup_rain_b", 150)
    shot(L, "09_lookup_rain_c", 150)
    # ---- a storm: LOOK OUTSIDE, LOOK UP
    L += ["set ui_wxWeather 4", "wait 24000"]
    shot(L, "10_lookup_storm", 300)
    L += ["set ui_atcStop 3; set ui_scene_hot 0; globalwidgetcommand atticscene scenefly 0.7 315.0 210.0 84.0 0.00 0.00 0.00 62.00"]
    shot(L, "11_lookout_storm_a", 1500)
    shot(L, "12_lookout_storm_b", 150)
    L += ["set ui_atcStop 0; globalwidgetcommand atticscene scenefly 0.6 %s" % HOME]
    shot(L, "13_home_storm", 1500)
    # ---- the wing (the briefing door: no rain inside, no sliver) from the New Game view's side
    # the briefing-door wing in the storm (the v1.10.72 near rain sheet stood in here, x 442 y -105..-21): from inside the wing at
    # the door, back toward the gable side, and the film room's stop
    for nm_, pz in (("14_wing_door_storm", "380.0 -60.0 85.0 4.00 0.00 0.00 55.00"), ("14b_wing_back_storm", "490.0 -80.0 90.0 4.00 150.00 0.00 60.00"),
                    ("14c_wing_side_storm", "300.0 -100.0 90.0 2.00 20.00 0.00 60.00"), ("14d_film_storm", "56.4 -37.4 78.2 32.28 -32.10 0.00 42.00")):
        L += ["set ui_scene_pose \"%s\"" % pz]
        shot(L, nm_, 1200)
    L += ["set ui_scene_pose \"\""]
    # ---- records (its window now looks out)
    L += ["pushmenu hzm_records3d"]
    shot(L, "15_records", 2500)
    L += ["popmenu 0", "wait 1500"]
    # ---- the MP room: home, rack view, notices view (the closure)
    L += ["exec ui/hzm_attic_go_mp.cfg", "wait 3500"]
    shot(L, "16_mp_home", 600)
    L += ["set ui_hubRack 1", "globalwidgetcommand hubscene scenefly 0.5 -70.9 15.8 86.6 4.00 42.35 0.00 58.00"]
    shot(L, "17_mp_rack", 1400)
    L += ["globalwidgetcommand hubscene scenecam -70.9 15.8 86.6 4.00 21.18 0.00 58.00"]
    shot(L, "18_mp_rack_midturn", 600)
    L += ["set ui_hubRack 0", "exec ui/hzm_hub_board_on.cfg"]
    shot(L, "19_mp_board", 1600)
    L += ["echo ^~^~^ P73 done", "wait 1000", "quit"]
    return L


def run(pak, ui, res, tag):
    os.environ["MP69_RES"] = res
    if os.path.exists(M.STOP):
        raise SystemExit("guard tripped earlier")
    M.setup(pak, ui, "-")
    w, h, center, lay = E.RES[res]
    L = ["set ui_menuCenter %d" % center] + script()
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30",
            "+set", "in_mouse", "0", "+set", "in_nograb", "1", "+set", "in_gamepad", "0", "+set", "in_joystick", "0",
            "+set", "coop_tinnitus", "0"]
    out = M.A.launch("p73_%s" % tag, w, h, L, args)
    if M.TRIPS:
        raise SystemExit("GUARD TRIPPED: %s" % (M.TRIPS[:2],))
    print(out)
    return out


if __name__ == "__main__":
    run(*sys.argv[1:5])

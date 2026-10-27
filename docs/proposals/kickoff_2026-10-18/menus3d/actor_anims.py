"""actor_anims.py - stock MOHAA animation candidates for the attic actors (names -> .skc under models/human/animation).
The shipped lists were searched read-only (G:/mohaa-hudfeed3/menus3d/stock_skc.txt, 4027 .skc from main / mainta / maintt).  animtest.py renders every candidate on both menu models;
the validated subset + the station table live in the same file once chosen."""

CAND = {
    # locomotion
    "boredwalk": "walks_runs/boredwalk.skc", "alertwalk": "walks_runs/alert_walk.skc", "curiousfwd": "walks_runs/curiousw_forward.skc",
    "sciwalk": "scripted/scientist/scientist_walk.skc", "st1walk": "scripted/e1l1/A_11_streetcrosser1_walk.skc", "oberwalk": "scripted/T1L2/OBERwalk01.skc",
    # idle / look around
    "idleA01": "idle/generic_idle_a01(loop).skc", "idleA02": "idle/generic_idle_A02(weight_shift).skc", "idleB": "idle/generic_idle_B.skc",
    "sidle01": "idle/standidle01.skc", "sidle02": "idle/standidle02.skc", "sidle03": "idle/standidle03.skc", "sidle04": "idle/standidle04.skc", "sidle05": "idle/standidle05.skc",
    "atease": "idle/atease.skc", "lookat": "idle/shingle_idle_lookat.skc", "axislook": "misc/00G103_Axis_Lookaround.skc", "stretch": "misc/00A104_stretches.skc",
    "chatter01": "idle/chatter01.skc", "chatter02": "idle/chatter02.skc", "chatter03": "idle/chatter03.skc", "chatter04": "idle/chatter04.skc",
    # map / wall chart
    "mapA": "scripted/e1l1/A_11_maproomA.skc", "mapB": "scripted/e1l1/A_11_maproomB.skc", "mapC": "scripted/e1l1/A_11_maproomC.skc", "cleanmap": "scripted/e1l4/A_14_CleanMap.skc",
    "mapTalk": "scripted/e1l4/A_14_Germ_mapTalk.skc", "point": "misc/point.skc",
    "wcNod1": "scripted/scientist/scientist_wallchart_idle1(looknod)_sci1.skc", "wcNod2": "scripted/scientist/scientist_wallchart_idle1(looknod)_sci2.skc",
    "wcPoint1": "scripted/scientist/scientist_wallchart_idle2(pointout)_sci1.skc", "wcPoint2": "scripted/scientist/scientist_wallchart_idle2(pointout)_sci2.skc",
    "wcExcite1": "scripted/scientist/scientist_wallchart_idle3(excited)_sci1.skc", "wcExcite2": "scripted/scientist/scientist_wallchart_idle3(excited)_sci2.skc",
    # desk: papers / leaning / clipboard / coffee
    "lean01": "scripted/scientist/scientist_standtable_lean01(point).skc", "lean02": "scripted/scientist/scientist_standtable_lean02(dr_evil).skc",
    "lean03": "scripted/scientist/scientist_standtable_lean03(basic).skc", "toLean": "scripted/scientist/scientist_standtable_straighttolean.skc",
    "fromLean": "scripted/scientist/scientist_standtable_leantostraight.skc", "clip": "scripted/scientist/scientist_clipboard.skc",
    "clipStart": "scripted/scientist/scientist_clipboard_start.skc", "clipEnd": "scripted/scientist/scientist_clipboard_end.skc",
    "papers": "scripted/e1l4/A_14_Claus_show_papers.skc", "coffee": "scripted/T2L3/23A102_SipCoffee.skc", "coffee2": "scripted/T2L3/23A302_SipCoffee.skc",
    "chalk": "scripted/scientist/scientist_chalkboard.skc",
    # radio / listening
    "commIdle": "scripted/e3L4/A_34_Commtalk_idle.skc", "commRadio": "scripted/e3L4/A_34_Commtalk_radio_idle.skc", "commArm": "scripted/e3L4/A_34_Commtalk_armlift.skc",
    "commBreath": "scripted/e3L4/A_34_Commtalk_breathing.skc", "comm31": "scripted/e3l1/A_31_CommTalk.skc", "comm3101": "scripted/e3l1/A_31_CommTalk01.skc",
    "radioIdle": "scripted/T1L2/12C102_RadioIdle.skc",
    # smoking
    "smoke01": "idle/smoking01.skc", "smoke02": "idle/smoking02.skc", "smoke03": "idle/smoking03.skc", "smoke04": "idle/smoking04.skc", "smoke05": "idle/smoking05.skc",
    "lightup": "scripted/smoking/lightup.skc", "inhale": "scripted/smoking/inhale.skc", "firstinhale": "scripted/smoking/firstinhale.skc", "buttout": "scripted/smoking/buttout.skc",
    # rummage / bend
    "crPick1": "scripted/crate_carry/crate_pickup1.skc", "crPick2": "scripted/crate_carry/crate_pickup2.skc", "crPut1": "scripted/crate_carry/crate_putdown1.skc",
    "crPut2": "scripted/crate_carry/crate_putdown2.skc", "crIdle": "scripted/crate_carry/crate_stand_idle.skc",
    # talking gestures
    "talkBrit1": "scripted/e1L3/A_13_Brit_captalk01.skc", "talkBrit2": "scripted/e1L3/A_13_Brit_captalk02.skc", "talkBrit3": "scripted/e1L3/A_13_Brit_captalk03.skc",
    "talkBurt1": "scripted/e1L3/A_13_BurtonTalk01.skc", "talkBurt2": "scripted/e1L3/A_13_BurtonTalk02.skc", "talkBurt3": "scripted/e1L3/A_13_BurtonTalk03.skc",
}

# ---- the shipped round (BU = Blender metres; make_main3d converts to MOHAA units).  Papers / coffee are SEATED anims: not used.
SEATED = {"papers", "coffee"}
HUB = {"bu": (-2.7, 3.6), "idle": "idleA01|idle", "walk": "alertwalk|boredwalk", "speed": 70.0}
BREAK = {"anims": "idleA02|idleA01", "tmin": 2.0, "tmax": 4.0}
# name, yaw (MOHAA), stay min/max s, floor path BU (hub -> stand point), anim sequence ('~' loops, 'a|b' alternatives)
STATIONS = [
    ("map", 0, 9, 13, [(-2.0, 4.2), (-1.15, 4.9), (-1.1, 5.6), (-1.0, 6.15)], "wcPoint1,wcExcite2,wcPoint1~"),
    ("desk", -90, 8, 11, [(-1.8, 3.0), (-1.5, 2.6), (-0.65, 2.4)], "toLean,lean01~"),
    ("phone", -90, 7, 10, [(-1.8, 4.4), (-0.65, 4.4)], "talkBrit1,talkBrit2~"),
    ("radio", 90, 8, 11, [(-2.0, 4.6), (-1.35, 5.95)], "commRadio,commIdle~"),
    ("window", 0, 7, 10, [(-3.4, 4.5), (-3.95, 5.2), (-4.05, 5.9)], "axislook,lookat~"),
    ("cabinet", 0, 7, 10, [(-3.6, 4.5), (-4.3, 5.0), (-4.7, 5.6)], "crPick2,crPut2,crPick2~"),
]

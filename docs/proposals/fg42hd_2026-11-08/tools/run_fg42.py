"""in-game FG 42 stills on the private client (G:\mohaa-wpnview, DISPLAY2): commit Armory gun <gid> (optional finish page),
hip idle / hip fire / ADS (+button13 = MOUSE2) / ADS fire / reload / drop; frames to RUNS/fg_<tag>/
    python run_fg42.py <gid> <gun name> <tag> [page]
"""
import sys
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402
import os

# WV_RES: 720 (default) | 1080 | 43s | uw = the user's real 3440x1440 (armoryfix's unclamp: the window overhangs DISPLAY2,
# screenshots read the framebuffer); WV_TURN_MS: turn left that long before the hip stills (m2l1's spawn faces into the sun)
W.RES.update({"uw": (3440, 1440, 0), "43s": (1440, 1080, 0)})
RES = os.environ.get("WV_RES", "720")
if RES == "uw":
    _ap = W.hw.apply_policy

    def _uw(args, *a, **k):
        args2, late = _ap(args, *a, **k)
        for i, v in enumerate(args2[:-1]):
            if v == "r_customwidth":
                args2[i + 1] = "3440"
            if v == "r_customheight":
                args2[i + 1] = "1440"
        return args2, late
    W.hw.apply_policy = _uw

gid, gun, tag = sys.argv[1:4]
page = sys.argv[4] if len(sys.argv) > 4 else ""
s = W.Script()
s.cmd("echo ^~^~^ WV boot", int(__import__("os").environ.get("WV_BOOT", "40000")))
s.cmd("+attack", 300)
s.cmd("-attack", 7000)
s.cmd("exec ui/loadout/w%s_s1.cfg" % gid, 5000)
if page:
    s.cmd("exec ui/loadout/%s.cfg" % page, 300)
    s.cmd("vstr coop_loFA1", 6000)
s.cmd('use "%s"' % gun, 2500)
if int(os.environ.get("WV_TURN_MS", "0")):
    s.cmd("+left", int(os.environ["WV_TURN_MS"]))
    s.cmd("-left", 800)
s.cmd("screenshotJPEG f_01_hip", 400)
if os.environ.get("WV_RAISE") == "1":
    # [QA #2] the hip in good light (turn off the sun-facing spawn view) and a scope-raise sequence for a GIF: frames 70 ms apart
    s.cmd("+right", int(os.environ.get("WV_RAISE_TURN_MS", "650")))
    s.cmd("-right", 900)
    s.cmd("screenshotJPEG g_hip_lit", 600)
    s.cmd("+button13", 0)
    for i in range(14):
        s.cmd("screenshotJPEG r_%02d" % i, 70)
    s.cmd("screenshotJPEG r_14", 700)
    s.cmd("-button13", 0)
    for i in range(15, 24):
        s.cmd("screenshotJPEG r_%02d" % i, 70)
    s.cmd("+left", int(os.environ.get("WV_RAISE_TURN_MS", "650")))
    s.cmd("-left", 900)
s.cmd("+attack", 600)
s.cmd("screenshotJPEG f_02_hipfire", 100)
s.cmd("-attack", 1500)
s.cmd("+button13", 1500)
s.cmd("screenshotJPEG f_03_ads", 400)
s.cmd("+attack", 500)
s.cmd("screenshotJPEG f_04_adsfire", 100)
s.cmd("-attack", 800)
s.cmd("-button13", 1200)
s.cmd("reload", 1200)
s.cmd("screenshotJPEG f_05_reload_a", 600)
s.cmd("screenshotJPEG f_06_reload_b", 600)
s.cmd("screenshotJPEG f_07_reload_c", 2500)
s.cmd("+button13", 1500)
s.cmd("reload", 900)
s.cmd("screenshotJPEG f_08_adsreload", 2500)
s.cmd("-button13", 800)
s.cmd("weapdrop", 1200)
s.cmd("use \"%s\"" % gun, 1500)
s.cmd("cg_3rd_person 1", 1500)
s.cmd("screenshotJPEG f_10_third", 400)
s.cmd("cg_3rd_person 0", 600)
s.cmd("spawn " + __import__("os").environ.get("WV_SPAWN", "models/weapons/coop_fg42_irons.tik"), 1500)
s.cmd("+lookdown", 500)
s.cmd("-lookdown", 900)
s.cmd("screenshotJPEG f_09_drop", 400)
s.cmd("quit", 0)
W.launch("fg_%s" % tag, RES, s, lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA2 ""', "set g_gametype 2", "set cheats 1", "set coop_dev 1", "set coop_fireDebug 1",
                                          "set coop_lockLoadout 0", "set cg_scopeDebug 1", "set ui_dmmap m2l1", "ui_startdmmap 2"], budget=200)

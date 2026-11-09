"""in-game FG 42 stills on the private client (G:\mohaa-wpnview, DISPLAY2): commit Armory gun <gid> (optional finish page),
hip idle / hip fire / ADS (+button13 = MOUSE2) / ADS fire / reload / drop; frames to RUNS/fg_<tag>/
    python run_fg42.py <gid> <gun name> <tag> [page]
"""
import sys
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402

gid, gun, tag = sys.argv[1:4]
page = sys.argv[4] if len(sys.argv) > 4 else ""
s = W.Script()
s.cmd("echo ^~^~^ WV boot", 40000)
s.cmd("+attack", 300)
s.cmd("-attack", 7000)
s.cmd("exec ui/loadout/w%s_s1.cfg" % gid, 5000)
if page:
    s.cmd("exec ui/loadout/%s.cfg" % page, 300)
    s.cmd("vstr coop_loFA1", 6000)
s.cmd('use "%s"' % gun, 2500)
s.cmd("screenshotJPEG f_01_hip", 400)
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
s.cmd("spawn models/weapons/coop_fg42_irons.tik", 1500)
s.cmd("+lookdown", 500)
s.cmd("-lookdown", 900)
s.cmd("screenshotJPEG f_09_drop", 400)
s.cmd("quit", 0)
W.launch("fg_%s" % tag, "720", s, lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA2 ""', "set g_gametype 2", "set cheats 1", "set coop_dev 1", "set coop_fireDebug 1",
                                          "set coop_lockLoadout 0", "set ui_dmmap m2l1", "ui_startdmmap 2"], budget=200)

"""viewclip A/B on the private client (G:\\mohaa-wpnview, the 3440x1440 ultrawide by resolution, muted): one boot, one gun; the
same hip actions (fire, reload, switch) are captured with the view weapon on the WORLD near plane (r_weaponProjAlways 0, the
shipped behaviour) and then on the weapon near plane (1). Frames -> RUNS/vc_<tag>/{a,b}_NN.jpg.
    python run_ab.py <armory gid> "<gun name>" <tag> [shots before the reload]
Env: WV_RES (default 1080), WV_BOOT (ms, default 85000), WV_DISPLAY_RES (set by the caller; 3440x1440).
"""
import os, sys
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402

W.RES.update({"uw": (3440, 1440, 0)})
gid, gun, tag = sys.argv[1:4]
nshot = int(sys.argv[4]) if len(sys.argv) > 4 else 3
s = W.Script()
s.cmd("echo ^~^~^ VC boot", int(os.environ.get("WV_BOOT", "85000")))
s.cmd("+attack", 300)
s.cmd("-attack", 7000)
s.cmd("exec ui/loadout/w%s_s1.cfg" % gid, 6000)
s.cmd('use "%s"' % gun, 3000)
MOVES = os.environ.get("VC_MOVES") == "1"
SIDES = [x for x in (("a", "0", "1"), ("b", "1", "0.6")) if x[0] in os.environ.get("VC_SIDES", "ab")]
for side, val, zn in SIDES:     # a = v1.10.66 as shipped, b = the viewclip fixes; VC_SIDES=b: the after side only
    s.cmd("r_weaponProjAlways %s" % val, 300)
    s.cmd("r_weaponznear %s" % zn, 300)
    s.cmd("echo ^~^~^ VC side %s r_weaponProjAlways %s" % (side, val), 300)
    s.cmd("screenshotJPEG %s_00_idle" % side, 400)
    for k in range(nshot):
        s.cmd("+attack", 120)
        s.cmd("-attack", 650)
    s.cmd("screenshotJPEG %s_01_fired" % side, 300)
    s.cmd("reload", 150)
    for k in range(2, 16):
        s.cmd("screenshotJPEG %s_%02d_reload" % (side, k), 220)
    s.cmd("weapnext", 250)
    for k in range(16, 20):
        s.cmd("screenshotJPEG %s_%02d_switch" % (side, k), 180)
    s.cmd('use "%s"' % gun, 250)
    for k in range(20, 24):
        s.cmd("screenshotJPEG %s_%02d_pullout" % (side, k), 180)
    if MOVES:
        # the movement half of the matrix (PLAN.md rows 3-9): sprint, jump + land, crouch, lean both ways, a burst, ADS + ADS fire
        # gun vs world (PLAN row 12): turn to the rock face on the left of the m2l1 spawn and walk into it
        s.cmd("+left", 420)
        s.cmd("-left", 200)
        s.cmd("+forward", 1600)
        s.cmd("-forward", 400)
        s.cmd("screenshotJPEG %s_50_wall" % side, 300)
        s.cmd("+button13", 1200)
        s.cmd("screenshotJPEG %s_51_wallads" % side, 300)
        s.cmd("-button13", 600)
        s.cmd("+back", 1600)
        s.cmd("-back", 200)
        s.cmd("+right", 420)
        s.cmd("-right", 600)
        s.cmd("+speed", 0)
        s.cmd("+forward", 900)
        s.cmd("screenshotJPEG %s_30_sprint" % side, 450)
        s.cmd("screenshotJPEG %s_31_sprint" % side, 300)
        s.cmd("-forward", 0)
        s.cmd("-speed", 600)
        s.cmd("+moveup", 120)
        s.cmd("-moveup", 0)
        for k in range(32, 37):
            s.cmd("screenshotJPEG %s_%02d_jump" % (side, k), 140)
        s.cmd("+movedown", 900)
        s.cmd("screenshotJPEG %s_37_crouch" % side, 300)
        s.cmd("-movedown", 700)
        s.cmd("+leanleft", 800)
        s.cmd("screenshotJPEG %s_38_leanL" % side, 300)
        s.cmd("-leanleft", 500)
        s.cmd("+leanright", 800)
        s.cmd("screenshotJPEG %s_39_leanR" % side, 300)
        s.cmd("-leanright", 500)
        s.cmd("+attack", 90)
        s.cmd("screenshotJPEG %s_40_fire" % side, 250)
        s.cmd("-attack", 600)
        s.cmd("+button13", 1300)
        s.cmd("screenshotJPEG %s_41_ads" % side, 200)
        s.cmd("+attack", 90)
        s.cmd("screenshotJPEG %s_42_adsfire" % side, 250)
        s.cmd("-attack", 300)
        s.cmd("reload", 700)
        s.cmd("screenshotJPEG %s_43_adsreload" % side, 500)
        s.cmd("screenshotJPEG %s_44_adsreload" % side, 500)
        s.cmd("-button13", 1200)
    s.cmd("echo ^~^~^ VC side %s done" % side, 1500)
s.cmd("quit", 0)
W.launch("vc_%s" % tag, os.environ.get("WV_RES", "1080"), s,
         lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA2 ""', "set g_gametype 2", "set cheats 1", "set coop_dev 1",
                "set coop_lockLoadout 0"] + ["set ui_dmmap m2l1", "ui_startdmmap 2"], budget=340)

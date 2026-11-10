"""cfg-only engraving / bench stills on G:\\mohaa-engrave (no pad script, never activates: harness_window.launch_background).
python e_run.py <tag> <scenario> <WxH window> <display WxH: 3440x1440 | 1920x1080>
Scenarios are command lists (cfg lines, 'wait' frames at com_maxfps 60)."""
import os, sys, shutil, subprocess, zipfile, glob
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, r"C:\Users\curry\AppData\Local\Temp\claude\cf30267572f02900\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad")
import harness_window as hw
import e5_run_long as E

tag, scen, win, disp = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W, H = (int(v) for v in win.split("x"))
DW, DH = (int(v) for v in disp.split("x"))
mon = [m for m in hw.monitors() if (m["rect"][2] - m["rect"][0], m["rect"][3] - m["rect"][1]) == (DW, DH)]
if not mon:
    raise SystemExit("no %s display" % disp)
hw.test_display = lambda name=None, _m=mon[0]: _m
E.CLIENT = r"G:\mohaa-engrave"
E.EXE = os.path.join(E.CLIENT, "openmohaa.exe")
E.HOME = os.path.join(E.CLIENT, "home")
E.MAINTT = os.path.join(E.HOME, "maintt")
E.LOG = os.path.join(E.MAINTT, "qconsole.log")
E.SHOTS = os.path.join(E.MAINTT, "screenshots")
E.RUNS = os.path.join(E.CLIENT, "runs")
MOD = os.environ.get("EG_MOD", r"C:\mohaa-coop-dev\hzm-mod-engrave")
BASE = os.environ.get("EG_BASE", "4811fcef")

# the overlay: what the engrave branch changed (+ the ignored binaries it force-added) and any extra files
ov = os.path.join(E.MAINTT, "zzzzzzzzzzzzzzzzzz_spfix.pk3")
files = subprocess.check_output(["git", "-C", MOD, "diff", "--name-only", BASE], text=True).split()
files += subprocess.check_output(["git", "-C", MOD, "ls-files", "--others", "--exclude-standard"], text=True).split()
for pat in ("models/hzm/*", "textures/hzm/decal/*"):
    files += [os.path.relpath(x, MOD).replace(os.sep, "/") for x in glob.glob(os.path.join(MOD, pat))]
files = sorted(f for f in set(files) if os.path.isfile(os.path.join(MOD, f)) and not f.startswith(("docs/", "_research/")))
with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(os.path.join(MOD, f), f)
    for pair in os.environ.get("EG_ADD", "").split(";"):
        if pair:
            src, arc = pair.split("=")
            z.write(src, arc)

L = []
n = [0]
def c(s): L.append(s)
def wait(sec): L.append("wait %d" % int(sec * 1000))   # cmd_wait counts MILLISECONDS in this engine
def shot(name, settle=1.0):
    wait(settle); n[0] += 1; c("screenshotJPEG %s_%02d_%s" % (tag, n[0], name)); wait(0.5)

GUNS = [("colt45", "mvp48_0_s1"), ("m1_garand", "mvp01_0_s1"), ("mp40", "mvp26_0_s1"), ("thompsonsmg", "mvp24_0_s1"),
        ("bar", "mvp36_0_s1"), ("30calportable", "p42"), ("panzerschreck", "mvp46_0_s1"), ("kar98sniper", "mvp13_0_s1"),
        ("shotgun", "mvp44_0_s1")]

def bench_guns():
    wait(20); c('set cl_engraveText "Lucky Lady"')
    c("pushmenu coop_custom")
    for g, page in GUNS:
        c("echo ^~^~^ GUN " + g); c("exec ui/loadout/%s.cfg" % page)
        c("hzmcust open"); shot(g + "_open", 1.5)
        c("hzmcust zoom"); shot(g + "_zoom", 1)
        c("hzmcust zoom;hzmcust turn"); shot(g + "_turn", 1)
    c('set coop_loPrev ""'); c("hzmcust open"); shot("nogun", 1.5)

def bench_type():
    """the words field typed through the keyboard's own char path (hzmcust typetest), then emblems zoomed"""
    wait(20); c('set cl_engraveText "Lucky Lady"')
    c("exec ui/loadout/mvp01_0_s1.cfg"); c("pushmenu coop_custom"); c("hzmcust open"); shot("before", 2)
    c('hzmcust typetest "Pvt. J. Curry, Normandy 44" 1'); wait(0.5); c("echo ^~^~^ TYPED;cl_engraveText"); shot("typed", 1.5)
    c("hzmcust zoom"); shot("typed_zoom", 1.5)
    c("hzmcust zoom;hzmcust item 1"); [c("hzmcust emblem 1") for _ in range(12)]; c("hzmcust zoom"); shot("emb1_zoom", 1.5)
    c("hzmcust zoom;hzmcust item 2"); [c("hzmcust emblem -1") for _ in range(4)]; c("hzmcust zoom"); shot("emb2_zoom", 1.5)
    c("hzmcust zoom"); shot("both", 1.5)
    c("hzmcust save;echo ^~^~^ SAVED;cl_cust_m1_garand"); shot("saved", 1)

def ingame_emblems():
    """the real bench flow without the menu: pick two emblems (each lands on the first free emblem-sized spot), SAVE, look"""
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("set thereisnomonkey 1"); c("set cheats 1"); c("set developer 1")
    c("spdevmap m3l2"); wait(45); c("finishloadingscreen"); wait(6)
    for tik, name, page in (("m1_garand", "M1 Garand", "mvp01_0_s1"), ("mp40", "MP40", "mvp26_0_s1"), ("thompsonsmg", "Thompson", "mvp24_0_s1"),
                            ("bar", "BAR", "mvp36_0_s1"), ("colt45", "Colt 45", "mvp48_0_s1")):
        c("give models/weapons/%s.tik" % tik); wait(1); c('use "%s"' % name); wait(3)
        shot(tik + "_words", 1.0)
        c("exec ui/loadout/%s.cfg" % page); c("hzmcust open;hzmcust item 1")
        [c("hzmcust emblem 1") for _ in range(12)]          # bronze star
        c("hzmcust item 2;hzmcust emblem -1;hzmcust emblem -1")   # croix de guerre (MOH series, retail art)
        c("hzmcust save;hzmcust close;echo ^~^~^ EMB %s;cl_cust_%s" % (tik, tik)); shot(tik + "_emb", 1.5)

def check_spots():
    """hand check of every spot: one emblem per spot in flat magenta, ENGRAVEQUAD corners printed with the shot"""
    import json
    wait(20); c("set cg_engraveCheck 1"); c('set cl_engraveText "X"'); c("set thereisnomonkey 1"); c("set cheats 1"); c("set developer 1")
    c("spdevmap m3l2"); wait(45); c("finishloadingscreen"); wait(6)
    guns = json.load(open(r"C:\Users\curry\AppData\Local\Temp\claude\cf30267572f02900\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\eg_allguns.json"))
    rep = json.load(open(r"C:\Users\curry\AppData\Local\Temp\claude\cf30267572f02900\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\eg\r_merged.json"))
    only = os.environ.get("EG_ONLY", "")
    for tik, name, typ in guns:
        r = rep.get(tik)
        if not isinstance(r, dict) or (only and os.path.basename(tik)[:-4] not in only.split(",")):
            continue
        key = os.path.basename(tik)[:-4]
        c("give " + tik); wait(1); c('use "%s"' % name); wait(3)
        for sp in sorted(r["spots"]):
            c('set cl_cust_%s "notext;nofinish;d crest %s 0 0 0 1 0"' % (key, sp)); wait(1)
            c("echo ^~^~^ SPOTCHECK %s %s" % (key, sp))
            n[0] += 1; c("set cg_engraveQuadNow 1;screenshotJPEG %s_%02d_%s_%s" % (tag, n[0], key, sp)); wait(0.6)
        c('set cl_cust_%s ""' % key)

def face_check():
    """[benchfix] hand check of every spot's whole face: magenta tiles over its usable cells, ENGRAVETILE corners per tile"""
    import json
    wait(20); c("set thereisnomonkey 1"); c("set cheats 1"); c("set developer 1"); c('set cl_engraveText "X"')
    c("spdevmap m3l2"); wait(45); c("finishloadingscreen"); wait(6)
    guns = json.load(open(r"C:\Users\curry\AppData\Local\Temp\claude\cf30267572f02900\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\eg_allguns.json"))
    table = open(os.path.join(MOD, "scripts", "hzm_engrave_anchors.txt")).read().splitlines()
    faces = {}
    for ln in table:
        if ln.startswith("face "):
            k, sp = ln.split()[1:3]
            faces.setdefault(k, []).append(sp)
    only = os.environ.get("EG_ONLY", "")
    for tik, name, typ in guns:
        key = os.path.basename(tik)[:-4]
        if key not in faces or (only and key not in only.split(",")):
            continue
        c("echo ^~^~^ SPTEST gun " + tik)
        c("give " + tik); wait(1); c('use "%s"' % name); wait(3)
        for sp in faces[key]:
            c("set cg_engraveFaceCheck " + sp); wait(0.6)
            n[0] += 1; c("set cg_engraveQuadNow 1;screenshotJPEG %s_%02d_%s__%s" % (tag, n[0], key, sp)); wait(0.6)
        c('set cg_engraveFaceCheck ""')

def bench_tilt():
    """[benchfix] the preview tilted up / down (the drag's pitch, driven by hzmcust tilt), turned over, zoomed"""
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("pushmenu coop_custom")
    for g, page in (("m1_garand", "mvp01_0_s1"), ("thompsonsmg", "mvp24_0_s1"), ("colt45", "mvp48_0_s1"), ("kar98", "mvp03_0_s1")):
        c("exec ui/loadout/%s.cfg" % page); c("hzmcust open"); shot(g + "_flat", 1.5)
        c("hzmcust tilt 45"); shot(g + "_tiltup", 1)
        c("hzmcust tilt -90"); shot(g + "_tiltdown", 1)
        c("hzmcust tilt -90;echo ^~^~^ TILT;cl_custTilt"); shot(g + "_tiltclamp", 1)   # asks -105: stays at -60
        c("hzmcust turn"); shot(g + "_turn_tilted", 1)
        c("hzmcust zoom"); shot(g + "_zoom", 1)
        c("hzmcust zoom;hzmcust turn;hzmcust tilt 60")

def bench_move():
    """[benchfix] the carving slid along the whole face (ZOOM 1 = the face, ZOOM 2 = the piece): Garand receiver both ends,
    Kar98k stock side, an emblem slid along the receiver"""
    def look(name):
        c("hzmcust zoom"); shot(name + "_face", 1.2); c("hzmcust zoom"); shot(name + "_close", 1.2); c("hzmcust zoom")
    wait(20); c('set cl_engraveText "Lucky Lady"'); c("pushmenu coop_custom")
    c("exec ui/loadout/mvp01_0_s1.cfg"); c("hzmcust open;hzmcust scale -0.3"); look("garand_centre")
    for _ in range(8):
        c("hzmcust move -1.5 0")
    c("echo ^~^~^ MOVE garand far left;cl_custEdit"); look("garand_left")
    for _ in range(16):
        c("hzmcust move 1.5 0")
    c("echo ^~^~^ MOVE garand far right;cl_custEdit"); look("garand_right")
    c("hzmcust item 1"); [c("hzmcust emblem 1") for _ in range(12)]; c("hzmcust spot -1")
    for _ in range(10):
        c("hzmcust move -1.5 0")
    c("echo ^~^~^ MOVE garand emblem far;cl_custEdit"); look("garand_emblem_left")
    c("exec ui/loadout/mvp03_0_s1.cfg"); c("hzmcust open")
    c("hzmcust spot 1"); c("echo ^~^~^ MOVE kar98 spot;cl_custSpotTxt"); look("kar98_stock_centre")
    for _ in range(14):
        c("hzmcust move -1.5 0")
    c("echo ^~^~^ MOVE kar98 far;cl_custEdit"); look("kar98_stock_far")
    for _ in range(4):
        c("hzmcust move 0 0.1")
    c("echo ^~^~^ MOVE kar98 up;cl_custEdit"); look("kar98_stock_up")

def check_short():
    """hand check of the words on every gun (short words use the engrave_short spot): flat magenta quads"""
    import json
    wait(20); c("set cg_engraveCheck 1"); c("set thereisnomonkey 1"); c("set cheats 1"); c("set developer 1")
    c('set cl_engraveText "%s"' % os.environ.get("EG_TEXT", "LUCKY LADY"))
    c("spdevmap m3l2"); wait(45); c("finishloadingscreen"); wait(6)
    guns = json.load(open(r"C:\Users\curry\AppData\Local\Temp\claude\cf30267572f02900\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\eg_allguns.json"))
    only = os.environ.get("EG_ONLY", "")
    for tik, name, typ in guns:
        key = os.path.basename(tik)[:-4]
        if only and key not in only.split(","):
            continue
        c("echo ^~^~^ SPTEST gun " + tik); c('set cl_cust_%s "nofinish"' % key)
        c("give " + tik); wait(1); c('use "%s"' % name); wait(3.2)
        n[0] += 1; c("set cg_engraveQuadNow 1;screenshotJPEG %s_%02d_%s" % (tag, n[0], key)); wait(0.8)

{"face_check": face_check, "bench_tilt": bench_tilt, "bench_move": bench_move, "check_short": check_short, "bench_guns": bench_guns, "bench_type": bench_type, "ingame_emblems": ingame_emblems, "check_spots": check_spots}[scen]()
c("echo ^~^~^ ENGRAVE done"); c("quit")
E.CLIENT_CFG = "omconfig_fresh.cfg"
shutil.copyfile(os.path.join(E.CLIENT, "pristine", "omconfig_fresh.cfg"), os.path.join(E.CLIENT, "pristine", "omconfig.cfg.run"))
bk = os.path.join(E.CLIENT, "pristine", "omconfig.cfg")
keep = bk + ".keep"
shutil.copyfile(bk, keep)
shutil.copyfile(os.path.join(E.CLIENT, "pristine", "omconfig_fresh.cfg"), bk)
try:
    out = E.launch(tag, W, H, ["set in_joystick 0", "set in_gamepad 0", "set s_volume 0", "set s_musicvolume 0",
                               "set s_ambientvolume 0", "set developer 1"] + L,
                   ["+set", "in_gamepad", "0", "+set", "in_joystick", "0", "+set", "net_port", "12958"])
finally:
    shutil.copyfile(keep, bk); os.remove(keep)
print("OUT", out)

"""make_newgame3d.py - the attic wall map IS the new game screen (ui_atticMain 1).  Run AFTER make_mphub3d.py (it extends that ship pk3).

    python make_newgame3d.py --mod-ui C:/mohaa-coop-dev/hzm-mod-mphub/ui [--attic-bake G:/mohaa-hudfeed3/menus3d/bake_s5]
                             [--wm-bake H:/hzm_work/ng/bake_wm] [--map-json H:/hzm_work/ng/tex/wallmap_med_markers.json]
                             [--occ H:/hzm_work/ng/occ.json] [--stage H:/hzm_work/ng/stage] [--pk3 H:/hzm_work/mphub3d/ship/zzzzzzzzzzzzzz_hzm_menus3d.pk3]

User 2026-11-02: "The new game screen also needs revamped to match the new map and surroundings you built in the 3d view (it should
also be 3d)" / "The radio system is obviously covering it so maybe just omit all of that when you are looking at the full map".

  * attic NEW GAME (main.urc scenehot "newgame", made by make_main3d.py): the camera flies to a square-on full-map pose, the veil
    dips, and ui/hzm_newgame3d.urc opens: the same attic (same baked models) WITHOUT the radio shelf group (atc_nook*, atc_radio*)
    and with everything else between the camera and the map cut out of bg/chrome (atc_bgng*, atc_chromeng*: the records desk,
    chairs, desk lamps, the hanging chalk sign - boxes from occ.json, an object-bounds dump of the attic blend), no actors.
    BACK / ESC = popmenu: the attic resumes and flies home under its own dip, radios and all.  Re-run this after make_main3d.py.
  * the wall map (atc_wallmap1 + hzm_atc_wallmap.jpg) is re-baked from gen_theatremap.py (Tunisia, Sicily, Italy); the attic
    home view shows the same new map.
  * three campaign markers ON the map (paper tags framed onto the map by scenelabel, hover glow + caption, pad / keyboard focus
    through proxy buttons): TUNISIA -> mission1difficulty, SICILY (g_t2l1) -> mission2difficulty, ITALY (g_t3l1) ->
    mission3difficulty - the stock briefing room's commands and unlock cvars.  A locked campaign shows a dimmed LOCKED tag and
    its proxy only shows the caption.  The difficulty screens are the stock ones re-hosted over the same 3D view
    (ui/hzm_ng3d_mission<N>difficulty.urc: stock widgets verbatim, the painted backdrop include replaced by the scene)."""
import io, json, math, os, re, shutil, subprocess, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

H_ = os.path.dirname(os.path.abspath(__file__))
M3D = r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d"
sys.path.insert(0, M3D)
import scene_params as SP  # noqa: E402


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


MODUI = opt("--mod-ui", r"C:\mohaa-coop-dev\hzm-mod-mphub\ui")
ABAKE = opt("--attic-bake", r"G:\mohaa-hudfeed3\menus3d\bake_s5")
WBAKE = opt("--wm-bake", r"H:\hzm_work\ng\bake_wm")
MAPJ = opt("--map-json", r"H:\hzm_work\ng\tex\wallmap_med_markers.json")
OCC = opt("--occ", r"H:\hzm_work\ng\occ.json")
STAGE = opt("--stage", r"H:\hzm_work\ng\stage")
PK3 = opt("--pk3", r"H:\hzm_work\mphub3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
SCALE = 52.5
FONTS = r"C:\Windows\Fonts"
WM_LO, WM_HI = np.array([-2.8721, 6.745, 0.0707]), np.array([0.2762, 6.745, 2.7760])   # the attic wallmap plane (BU), u +x, v +z


def conv(p):
    return SP.conv(p, SCALE)


def pose_str(org, ang, fov):
    return "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (org[0], org[1], org[2], ang[0], ang[1], ang[2], fov)


# the full-map pose: square on, centred, 3.745 m back (BU y 3.0), vertical fov 46 (2.7 m map + margin at 4:3; wider screens see more wall)
MAPC = (WM_LO + WM_HI) / 2
CAM_BU = (MAPC[0], 3.0, MAPC[2])
MAP_POSE = pose_str(conv(CAM_BU), (0.0, 0.0, 0.0), 46.0)
DIST = WM_LO[1] - CAM_BU[1]
FPX = 540.0 / math.tan(math.radians(46.0) / 2)

# ---- 1. models: the re-baked wall map, and bg / chrome with the view to the map cut clear
shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE)
BM = open(os.path.join(M3D, "build_models2.py"), encoding="utf-8").read()


def build(bakedir, groups, out, rename=None, cut=None):
    code = BM
    a = 'GROUPS = ["bg", "wallmap", "nook", "radio", "chalk", "fan", "chrome", "projector", "floor"]'
    assert code.count(a) == 1
    code = code.replace(a, "GROUPS = %r" % groups)
    if rename:
        a = 'name = "atc_%s%d" % (g, m + 1)'
        assert code.count(a) == 1
        code = code.replace(a, 'name = "atc_%s' + rename + '%d" % (g, m + 1)')
    if cut is not None:
        a = 'CUT_BOXES = [((-3.90, 3.10, 2.10), (-3.30, 3.65, 2.65))]'
        assert code.count(a) == 1
        code = code.replace(a, "CUT_BOXES = [((-3.90, 3.10, 2.10), (-3.30, 3.65, 2.65))] + %r" % (cut,))
        a = '    if g == "bg":      # floating props'
        assert code.count(a) == 1
        code = code.replace(a, '    if g in ("bg", "chrome"):      # floating props')
    sv = sys.argv
    sys.argv = ["build_models2.py", bakedir, out, "--scale", str(SCALE)]
    try:
        exec(compile(code, "build_models2.py (newgame)", "exec"), {"__name__": "__bm__"})
    finally:
        sys.argv = sv


tmp = os.path.join(STAGE, "_tmp")
# (a) wall map
t1 = os.path.join(tmp, "wm")
os.makedirs(t1)
for f in ("wallmap.npz", "wallmap.png", "groups.json"):
    shutil.copy(os.path.join(WBAKE, f), t1)
build(t1, ["wallmap"], os.path.join(tmp, "out_wm"))
# (b) bg / chrome minus the objects between the full-map camera and the map
occ = json.load(open(OCC))
boxes = [(tuple(np.array(lo) - 0.01), tuple(np.array(hi) + 0.01)) for n, (lo, hi) in occ.items() if not n.startswith(("beam", "rafter", "wall", "roof"))]
t2 = os.path.join(tmp, "bg")
os.makedirs(t2)
for f in ("bg.npz", "bg.png", "chrome.npz", "chrome.png", "groups.json", "wallmap.npz"):
    shutil.copy(os.path.join(ABAKE, f), t2)
# the old Sicily map's pins and the wall socket sit ON the map plane: on the new map they are stray dots (and the socket baked a
# black square) - cut from every bg / chrome set, the attic's own included (inner map rectangle only, the red frame stays)
# (per-object boxes from an object-bounds dump - one big box also took the map's red frame, whose two triangles centre inside it)
PINS = [(tuple(np.array(lo) - 0.006), tuple(np.array(hi) + 0.006)) for lo, hi in json.load(open(opt("--pins", r"H:\hzm_work\ng\pins.json"))).values()]
# an arm lamp on the left post leans into the full-map frame (top left): cut from the map view only
LAMP = [((-2.95, 5.00, 1.85), (-2.10, 5.45, 2.65))]     # (the long records desk stays: a box cut through it left long sliver triangles)
build(t2, ["bg", "chrome"], os.path.join(tmp, "out_bg"), rename="ng", cut=boxes + PINS + LAMP)
# (c) the attic's own bg / chrome minus the pins, SAME model names and counts (main.urc lists them)
build(t2, ["bg", "chrome"], os.path.join(tmp, "out_at"), cut=PINS)
AT = json.load(open(os.path.join(tmp, "out_at", "build.json")))["groups"]
assert AT["bg"]["models"] == 8, AT          # main.urc lists atc_bg1..8; chrome drops from 2 models to 1 without the pins (patched below)
BJ = json.load(open(os.path.join(tmp, "out_bg", "build.json")))["groups"]
mdir = os.path.join(STAGE, "models", "menu")
tdir = os.path.join(STAGE, "textures", "menu")
sdir = os.path.join(STAGE, "scripts")
for d in (mdir, tdir, sdir):
    os.makedirs(d, exist_ok=True)
for fn in os.listdir(os.path.join(tmp, "out_bg", "models", "menu")):
    shutil.copy(os.path.join(tmp, "out_bg", "models", "menu", fn), mdir)
for fn in os.listdir(os.path.join(tmp, "out_at", "models", "menu")):
    shutil.copy(os.path.join(tmp, "out_at", "models", "menu", fn), mdir)
for fn in os.listdir(os.path.join(tmp, "out_wm", "models", "menu")):
    shutil.copy(os.path.join(tmp, "out_wm", "models", "menu", fn), mdir)
assert sorted(os.listdir(os.path.join(tmp, "out_wm", "models", "menu"))) == ["atc_wallmap1.skc", "atc_wallmap1.skd", "atc_wallmap1.tik"]
shutil.copy(os.path.join(tmp, "out_wm", "textures", "menu", "hzm_atc_wallmap.jpg"), tdir)
shutil.rmtree(tmp)

# ---- 2. campaign tags (RGBA tga): pinned paper tags, a dimmed LOCKED variant
MJ = json.load(open(MAPJ))["markers"]
CAMPAIGNS = [("tunisia", "TUNISIA", "MISSION 1", "mission1difficulty", None),
             ("sicily", "SICILY", "MISSION 2", "mission2difficulty", "g_t2l1"),
             ("italy", "ITALY", "MISSION 3", "mission3difficulty", "g_t3l1")]


def tag(name, sub, locked):
    w, h = 512, 196
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((22, 30, w - 14, h - 8), fill=(0, 0, 0, 120))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(im)
    paper = (150, 146, 136) if locked else (232, 214, 150)
    ink = (70, 68, 64) if locked else (40, 32, 24)
    d.rectangle((14, 22, w - 22, h - 16), fill=paper + (255,), outline=(90, 74, 50, 255), width=4)
    f1 = ImageFont.truetype(os.path.join(FONTS, "STENCIL.TTF"), 70)
    f2 = ImageFont.truetype(os.path.join(FONTS, "courbd.ttf"), 30)
    tw = d.textlength(name, font=f1)
    d.text(((w - 8 - tw) / 2, 50), name, font=f1, fill=ink + (255,))
    if locked:            # the subtitle line becomes a red LOCKED (never stamped across the name: it read as garbled text)
        sub = "LOCKED"
    tw = d.textlength(sub, font=f2)
    d.text(((w - 8 - tw) / 2, 128), sub, font=f2, fill=((160, 30, 25) if locked else ink) + (255,))
    pin = (110, 106, 100) if locked else (176, 28, 24)
    d.ellipse((w / 2 - 22, 4, w / 2 + 14, 40), fill=pin + (255,))
    d.ellipse((w / 2 - 12, 10, w / 2 - 2, 20), fill=tuple(min(255, c + 70) for c in pin) + (255,))
    return im


shader = ["// [newgame3d] campaign tags on the attic wall map (generated by make_newgame3d.py)"]
for key, name, sub, _m, cv in CAMPAIGNS:
    for lk in ((False, True) if cv else (False,)):
        nm = "hzm_ng_tag_%s%s" % (key, "_lk" if lk else "")
        tag(name, sub, lk).save(os.path.join(tdir, nm + ".tga"))
        shader.append("textures/menu/%s\n{\n\tnomipmaps\n\tnopicmip\n\tcull none\n\t{\n\t\tclampmap textures/menu/%s.tga\n\t\tblendFunc blend\n\t\trgbGen identity\n\t}\n}" % (nm, nm))
open(os.path.join(sdir, "hzm_newgame3d.shader"), "w", newline="\n").write("\n".join(shader) + "\n")

# ---- 3. the scene: the attic models (main.urc atticscene) minus the radio shelf, bg / chrome -> the cut sets, no actors / props
mainp = os.path.join(MODUI, "main.urc")
mraw = open(mainp, "rb").read()
assert mraw.count(b"\r\n") == mraw.count(b"\n")
mt = mraw.decode("latin-1")
blk = mt[mt.index('name "atticscene"'):]
blk = blk[:blk.index("\r\n}\r\n")]
models = []
for l in blk.split("\r\n"):
    m = re.match(r'scenemodel "models/menu/(atc_[a-z]+?)(\d+)\.tik" 0 0 0 0$', l)
    if not m:
        continue
    g, k = m.groups()
    if g in ("atc_nook", "atc_radio", "atc_chalk", "atc_fan", "atc_projector"):      # the shelf, the hanging chalk sign, the wall fan: not in the map view
        continue
    if g in ("atc_bg", "atc_chrome"):
        continue
    models.append('scenemodel "models/menu/%s%s.tik" 0 0 0 0' % (g, k))
for g in ("bg", "chrome"):
    models += ['scenemodel "models/menu/atc_%sng%d.tik" 0 0 0 0' % (g, k + 1) for k in range(BJ[g]["models"])]
assert any("atc_wallmap1" in m for m in models) and any("atc_floor" in m for m in models), models


def map_bu(uv, dz=0.0):
    return np.array([WM_LO[0] + uv[0] * (WM_HI[0] - WM_LO[0]), WM_LO[1] - 0.006, WM_LO[2] + uv[1] * (WM_HI[2] - WM_LO[2]) + dz])


TAG_W, TAG_H = 0.50, 0.19           # m on the wall (the 512x196 tag)
hots, boxes_, labels, caps, wid, btn = [], [], [], {}, [], []
idx = 0
for key, name, sub, menu, cv in CAMPAIGNS:
    pin = map_bu(MJ[key]["uv"])
    c = pin.copy()
    c[2] -= TAG_H / 2 - 0.012           # the tag hangs from its pin
    # QA gate: no tag may cover a printed name on the map (uv rect of the tag vs every label box from gen_theatremap.py)
    WW, HH = WM_HI[0] - WM_LO[0], WM_HI[2] - WM_LO[2]
    tu0, tu1 = (c[0] - TAG_W / 2 - WM_LO[0]) / WW, (c[0] + TAG_W / 2 - WM_LO[0]) / WW
    tv0, tv1 = (c[2] - TAG_H / 2 - WM_LO[2]) / HH, (c[2] + TAG_H / 2 + 0.02 - WM_LO[2]) / HH
    hit = [n for n, (u0, v0, u1, v1) in json.load(open(MAPJ))["labels"].items() if u0 < tu1 and u1 > tu0 and v0 < tv1 and v1 > tv0]
    assert not hit, (key, "tag covers", hit)
    assert 0 <= tu0 and tu1 <= 1 and 0 <= tv0 and tv1 <= 1, (key, "tag off the sheet")
    ce = conv(c)
    capc = conv(c - np.array([0, 0, TAG_H / 2 + 0.07]))
    hw, hh = TAG_W / 2 / DIST * FPX, TAG_H / 2 / DIST * FPX
    labels.append('scenelabel "ngtag_%s" %.1f %.1f %.1f %.2f %.2f' % (key, ce[0], ce[1], ce[2], TAG_W / 2 * SCALE, TAG_H / 2 * SCALE))
    wid.append(("ngtag_%s" % key, "hzm_ng_tag_%s" % key, cv))
    if cv:
        labels.append('scenelabel "ngtag_%s_lk" %.1f %.1f %.1f %.2f %.2f' % (key, ce[0], ce[1], ce[2], TAG_W / 2 * SCALE, TAG_H / 2 * SCALE))
        wid.append(("ngtag_%s_lk" % key, "hzm_ng_tag_%s_lk" % key, cv + "!=1"))
    for lk in ((False, True) if cv else (False,)):
        idx += 1
        hn = key + ("_lk" if lk else "")
        cap = name + (" - LOCKED" if lk else "")
        cmd = "set ui_scene_hot %d" % idx if lk else "set ui_scene_hot 0; pushmenu hzm_ng3d_%s" % menu
        hots.append('scenehot "%s" %.1f %.1f %.1f %.1f "%s" "%s" "ng_h%d"' % (hn, ce[0], ce[1], ce[2], TAG_W / 2 * SCALE, cmd, cap, idx))
        boxes_.append('scenehotbox "%s" 0.0 0.0 %.1f %.1f' % (hn, hw * 1.05, hh * 1.15))
        labels.append('scenelabel "ngcap%d" %.1f %.1f %.1f %.2f %.2f' % (idx, capc[0], capc[1], capc[2], 0.30 * SCALE, 0.05 * SCALE))
        caps[idx] = cap
        gate = (cv + ("!=1" if lk else "")) if cv else ""
        btn.append(("ng_h%d" % idx, idx, cmd, gate, lk))
NL = "\r\n"


def scene_block(name, with_hots):
    b = ["resource", "Scene3D", "{", 'name "%s"' % name, "rect 0 0 640 480"] + models + ["scenecam " + MAP_POSE]
    if with_hots:
        b += hots + boxes_
    b += [l.replace('scenelabel "ngtag', 'scenelabel "%s_ngtag' % name) if not with_hots else l for l in labels if with_hots or "ngtag" in l]
    b += ["}"]
    for wn, sh, cv in wid:
        b += ["resource", "Label", "{", 'name "%s"' % (wn if with_hots else name + "_" + wn), "rect 0 0 8 8", "fgcolor 1 1 1 1", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
              'shader "textures/menu/%s"' % sh] + (['enabledcvar "%s"' % cv] if cv else []) + ["}"]
    return b


U = ["// generated by docs/proposals/mphub3d_2026-11-02/newgame/make_newgame3d.py - do not hand-edit.  The attic wall map as the new game",
     "// screen (ui_atticMain 1; reached from the attic's NEW GAME hotspot).  BACK / ESC = popmenu: the attic flies home with its radios.",
     'menu "hzm_newgame3d" 640 480 NONE 0', "bgcolor 0 0 0 1", "borderstyle NONE", "bgfill 0 0 0 1", "fullscreen 1", "virtualres 1",
     'escapecommand "set ui_scene_hot 0; popmenu 1"', ""] + scene_block("ngscene", True)
for k in sorted(caps):
    U += ["resource", "Label", "{", 'name "ngcap%d"' % k, "rect 0 0 8 8", 'title "%s"' % caps[k], "fgcolor 0.93 0.88 0.72 1.00", "bgcolor 0.10 0.08 0.06 0.82",
          'borderstyle "NONE"', 'font "facfont-20"', "textalign center", 'enabledcvar "ui_scene_hot==%d"' % k, "}"]
for n, idx_, cmd, gate, lk in btn:
    U += ["resource", "Button", "{", 'name "%s"' % n, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
          'clicksound "sound/menu/%s.wav"' % ("back" if lk else "apply"), 'stuffcommand "%s"' % cmd, 'hovercommand "set ui_scene_hot %d"' % idx_,
          'mouseawaycommand "set ui_scene_hot 0"'] + (['enabledcvar "%s"' % gate] if gate else []) + ["}"]
U += ["resource", "Button", "{", 'name "back"', "rect 8 448 96 24", "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.50 0.50 0.50 0.00", 'borderstyle "3D_BORDER"',
      'shader "textures/mohmenu/back"', 'hovershader "textures/mohmenu/back_h"', 'clicksound "sound/menu/back.wav"', 'stuffcommand "set ui_scene_hot 0; popmenu 1"', "}", "end."]
open(os.path.join(MODUI, "hzm_newgame3d.urc"), "wb").write((NL.join(U) + NL).encode("latin-1"))

# ---- 4. the stock difficulty screens, re-hosted over the same 3D view (widgets verbatim; the painted backdrop include -> the scene)
pak = zipfile.ZipFile(os.path.join(GOG, "maintt", "pak1.pk3"))
for _k, _n, _s, menu, _cv in CAMPAIGNS:
    s = pak.read("ui/%s.urc" % menu).decode("latin-1").replace("\r\n", "\n")
    s, n1 = re.subn(r'menu "%s" ' % menu, 'menu "hzm_ng3d_%s" ' % menu, s, count=1)
    s, n2 = re.subn(r'(?m)^include "ui/briefing_room_nobuttons\.inc"\n', "", s)
    s = re.sub(r'(?m)^include "ui/common\.inc"\n', "", s)
    assert n1 == 1 and n2 == 1, (menu, n1, n2)
    head = "// generated by make_newgame3d.py from the stock maintt ui/%s.urc: the same widgets over the 3D wall map (ui_atticMain 1)\n" % menu
    i = s.index("\nresource\n")
    s = head + s[:i + 1] + "\n".join(scene_block("ngd_" + menu, False)) + "\n" + s[i + 1:]
    open(os.path.join(MODUI, "hzm_ng3d_%s.urc" % menu), "wb").write(s.replace("\n", NL).encode("latin-1"))

# ---- 5. the attic's NEW GAME hotspot: full-map pose, then this menu (main.urc + its cursor-less test cfg); idempotent
ln = [l for l in mt.split("\r\n") if l.startswith('scenehot "newgame" ')]
assert len(ln) == 1
new = re.sub(r"scenefly 0\.6 [-\d. ]+?;", "scenefly 0.6 %s;" % MAP_POSE, ln[0], count=1)
new = new.replace("pushmenu briefingroom", "pushmenu hzm_newgame3d")
assert "pushmenu hzm_newgame3d" in new and MAP_POSE in new
mt = mt.replace(ln[0], new)
new_cmd = re.match(r'scenehot "newgame" \S+ \S+ \S+ \S+ "([^"]*)" "[^"]*" "(\w+)"', new)
cmd_, proxy = new_cmd.group(1), new_cmd.group(2)
# the hotspot's proxy button runs the click (scenehot's own command only serves unbound hotspots): give it the same command
pat = re.compile(r'(name "%s"\r\n(?:(?!\r\n\}).)*?stuffcommand ")([^"]*)(")' % proxy, re.S)
mt, nb = pat.subn(lambda m: m.group(1) + cmd_ + m.group(3), mt)
assert nb == 1, (proxy, nb)
# the attic's chrome set without the pins: main.urc's atc_chrome lines follow the rebuilt model count
chl = re.findall(r'scenemodel "models/menu/atc_chrome\d+\.tik" 0 0 0 0\r\n', mt)
assert chl, "no atc_chrome lines"
mt = mt.replace("".join(chl), "".join('scenemodel "models/menu/atc_chrome%d.tik" 0 0 0 0\r\n' % (k + 1) for k in range(AT["chrome"]["models"])), 1)
assert len(re.findall(r'scenemodel "models/menu/atc_chrome\d+\.tik"', mt)) == AT["chrome"]["models"]
open(mainp, "wb").write(mt.encode("latin-1"))
cfgp = os.path.join(MODUI, "hzm_attic_go_newgame.cfg")
c = open(cfgp, encoding="latin-1").read()
c = re.sub(r"scenefly 0\.6 [-\d. ]+\n", "scenefly 0.6 %s\n" % MAP_POSE, c).replace("pushmenu briefingroom", "pushmenu hzm_newgame3d")
assert "pushmenu hzm_newgame3d" in c
open(cfgp, "w", newline="\n").write(c)

# ---- 6. the ship pk3: the hub pk3 + these files (only the wall map files may be replaced)
add = []
for root, _d, fs in os.walk(STAGE):
    for fn in fs:
        if fn.endswith(".json"):
            continue
        p = os.path.join(root, fn)
        add.append((p, os.path.relpath(p, STAGE).replace("\\", "/")))
names = {a for _p, a in add}
base = zipfile.ZipFile(PK3)
stale = re.compile(r"models/menu/atc_chrome(\d+)\.(tik|skd|skc)$")
keep = [i for i in base.infolist() if i.filename not in names and not (stale.match(i.filename) and int(stale.match(i.filename).group(1)) > AT["chrome"]["models"])]
repl = sorted(names & {i.filename for i in base.infolist()})
assert all(any(k in r for k in ("wallmap", "atc_bg", "atc_chrome", "hzm_ng_", "hzm_newgame3d")) for r in repl), repl      # the wall map, bg/chrome minus the pins, this script's own earlier output      # the wall map + this script's own earlier output
tmpk = PK3 + ".tmp"
with zipfile.ZipFile(tmpk, "w", zipfile.ZIP_DEFLATED) as z:
    for i in keep:
        z.writestr(i, base.read(i.filename))
    for p, a in sorted(add, key=lambda x: x[1]):
        z.write(p, a)
base.close()
os.replace(tmpk, PK3)
print("newgame3d: %d scene models, %d hotspots; replaced %s; pk3 %s %d bytes" % (len(models), len(hots), repl, PK3, os.path.getsize(PK3)))
print("map pose", MAP_POSE)

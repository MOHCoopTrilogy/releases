"""make_mphub3d.py <bake dir> <stage dir> <mod ui dir> [--base-pk3 P] [--ship-pk3 P] - the live 3D multiplayer room (ui_atticMain 1).

The sibling of menus3d/make_main3d.py for the multiplayer menu.  Pipeline (all idempotent):
  hub_prep.py (Blender)  -> hub_bake.py (Blender, the attic bake with hub groups) -> THIS:
    1. hub_build_models.py: bake -> <stage>/models/menu/hub_*.tik/skd/skc, textures/menu/hzm_hub_*.jpg, scripts/hzm_hubscene.shader
    2. splices the Scene3D "hubscene" + hotspot proxies + hover captions into the mod's ui/multiplayer.urc (between the
       [mphub3d] markers) and gates the flat room's widgets off while ui_atticActive is 1 (the flat menu stays the fallback:
       ui_atticMain 0, or ESC > Multiplayer during a game, where ui_atticActive is 0)
    3. writes ui/hzm_hub_go_<hotspot>.cfg (each hotspot's own command without a cursor, for smoke tests)
    4. the ship pk3 = the shipped menus3d pk3 (the attic) + the hub files, under the same name, so no build/publish list changes

Hotspots (functions 1:1 with the flat ui/multiplayer.urc; user 2026-11-02):
    wooden door -> back to the attic (popmenu)            lockers -> LOADOUTS (ui_getplayermodel; mpoptions: Allied / Axis / Coop)
    red door    -> the server browser (joingame)          SERVICE RECORD board -> coop_srsync; coop_sr
    game-type board -> START GAME (multiplayerstart)
A click = a 0.6 s camera move toward the object, a veil dip, the existing 2D menu; BACK from it = the hub flies home by itself
(sceneleave).  ESC in the hub = back to the attic.  ARMORY / SERVICE RECORD plates are hidden in the hub (they have 3D homes);
DISCONNECT is the in-game plate and never shows here (ui_atticActive is 0 in a game)."""
import json, math, os, re, shutil, subprocess, sys, zipfile
import numpy as np

H = os.path.dirname(os.path.abspath(__file__))
M3D = r"C:\mohaa-coop-dev\docs\proposals\kickoff_2026-10-18\menus3d"
sys.path.insert(0, M3D)
import scene_params as SP  # noqa: E402

bake, stage, modui = sys.argv[1], sys.argv[2], sys.argv[3]


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


BASE_PK3 = opt("--base-pk3", r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
SHIP_PK3 = opt("--ship-pk3", r"H:\hzm_work\mphub3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
SCALE = 52.5
SCENE = "hubscene"
GATE_ON = 'enabledcvar "ui_atticActive==1"'

# ---- 1. models
if "--no-models" not in sys.argv:
    shutil.rmtree(stage, ignore_errors=True)
    subprocess.check_call([sys.executable, os.path.join(H, "hub_build_models.py"), bake, stage, "--scale", str(SCALE)])
BJ = json.load(open(os.path.join(stage, "build.json")))
NB = json.load(open(os.path.join(bake, "groups.json")))["names"]


def conv(p):
    return SP.conv(p, SCALE)


# home camera (BU) - the same numbers as hub_prep.py's HUB_HOME camera
HOME_BU = (-0.30, -1.35, 1.65)
HOME_YAW_RIGHT, HOME_PITCH_DOWN, HOME_FOVY = 7.0, 4.0, 54.0
home_org = conv(HOME_BU)
HOME = (home_org, (HOME_PITCH_DOWN, -HOME_YAW_RIGHT, 0.0), HOME_FOVY)


def pose_str(org, ang, fov):
    return "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (org[0], org[1], org[2], ang[0], ang[1], ang[2], fov)


HOME_S = pose_str(*HOME)


def approach(target_bu, dist, fov, lift=0.0, dirbu=(0.0, 1.0, 0.0)):
    """the camera `dist` metres back from target_bu along dirbu (BU), lifted `lift` metres, looking at the target (= make_main3d.approach)"""
    t = conv(target_bu)
    u = SP.conv(np.array(dirbu, float), 1.0)
    u = u / np.linalg.norm(u)
    org = t - u * dist * SCALE
    org[2] += lift * SCALE
    f = t - org
    f /= np.linalg.norm(f)
    return pose_str(org, (math.degrees(-math.asin(max(-1, min(1, f[2])))), math.degrees(math.atan2(f[1], f[0])), 0.0), fov)


def bounds(key):
    b = NB[key]
    return np.array(b["min"]), np.array(b["max"])


# name, caption, bounds key, look point (BU; None = bounds centre), approach dist m, fov, lift m, direction (BU), caption plate (BU centre, half width, half height),
# command run at the click, command the camera move ends in (after the veil is up)
HOTS = [
    ("main", "MAIN MENU", "wd", None, 2.6, 50.0, 0.15, (0.0, 1.0, 0.0), ((-2.75, 5.30, 2.46), 0.40, 0.075), "", "back"),
    ("loadout", "LOADOUTS", "lk", None, 2.5, 50.0, 0.20, (0.15, 1.0, 0.0), ((-1.41, 5.10, 2.04), 0.40, 0.075), "ui_getplayermodel", "pushmenu mpoptions"),
    ("join", "SERVER BROWSER", "rd", None, 2.5, 50.0, 0.15, (0.0, 1.0, 0.0), ((0.25, 5.30, 2.36), 0.46, 0.075), "", "pushmenu joingame"),
    ("record", "SERVICE RECORD", "nb", (1.65, 5.37, 1.62), 1.45, 46.0, 0.05, (0.0, 1.0, 0.0), ((1.65, 5.30, 2.31), 0.46, 0.075), "coop_srsync", "pushmenu coop_sr"),
    ("start", "START GAME", "gb", (2.55, 3.05, 2.05), 2.35, 52.0, -0.25, (1.0, 0.35, 0.0), ((2.40, 3.05, 2.99), 0.36, 0.07), "", "pushmenu multiplayerstart"),
]
OVR = json.load(open(os.path.join(H, "hub_hots.json"))) if os.path.exists(os.path.join(H, "hub_hots.json")) else {}

# ---- home-view hit boxes: the object's bounds projected at the home camera (px at 1080 rows; the widget scales them, Hor+ keeps them aspect-free)
f_, l_, u_ = SP.axes_from_angles(*HOME[1])
FPX = 540.0 / math.tan(math.radians(HOME_FOVY) / 2)


def proj(p_eng):
    d = np.asarray(p_eng) - home_org
    x, y, z = d @ f_, d @ l_, d @ u_
    return -y / x * FPX, -z / x * FPX


hots, btns, boxes, labels, caps, gocfg = [], [], [], [], {}, {}
for i, (nm, cap, key, look, dist, fov, lift, dirbu, plate, pre, post) in enumerate(HOTS):
    o = OVR.get(nm, {})
    lo, hi = bounds(key)
    ctr_bu = (lo + hi) / 2
    look = tuple(o.get("look", look if look is not None else ctr_bu))
    pose = o.get("pose") or approach(look, o.get("dist", dist), o.get("fov", fov), o.get("lift", lift), o.get("dir", dirbu))
    c = conv(ctr_bu)
    rad = float(np.linalg.norm(hi - lo)) * 0.5 * SCALE
    xs, ys = [], []
    for k in range(8):
        cb = [(lo, hi)[(k >> a) & 1][a] for a in range(3)]
        px, py = proj(conv(cb))
        xs.append(px)
        ys.append(py)
    cx, cy = proj(c)
    bx = ((min(xs) + max(xs)) / 2 - cx, (min(ys) + max(ys)) / 2 - cy, (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2)
    idx = i + 1
    leave = "" if post == "back" else "globalwidgetcommand %s sceneleave; " % SCENE
    head = "set ui_scene_hot 0; %s%sglobalwidgetcommand %s scenefly 0.6 %s; uiafter 0.45 uiveil 1 0.15; " % ((pre + "; ") if pre else "", leave, SCENE, pose)
    if post == "back":
        # back to the attic: the veil is up at 0.6 s; the hub camera is put home (unseen) and the hub pops - the attic flies home under its own dip
        cmd = head + "uiafter 0.6 globalwidgetcommand %s scenecam %s; uiafter 0.6 popmenu 1" % (SCENE, HOME_S)
    else:
        cmd = head + "uiafter 0.6 %s; uiafter 0.62 uiveil 0 0.2" % post
    hots.append('scenehot "%s" %.1f %.1f %.1f %.1f "%s" "%s" "hub_h%d"' % (nm, c[0], c[1], c[2], rad, cmd, cap, idx))
    boxes.append('scenehotbox "%s" %.1f %.1f %.1f %.1f' % ((nm,) + tuple(o.get("box", bx))))
    pc, phw, phh = plate
    pce = conv(pc)
    labels.append('scenelabel "hubcap%d" %.1f %.1f %.1f %.2f %.2f' % (idx, pce[0], pce[1], pce[2], phw * SCALE, phh * SCALE))
    caps[idx] = cap
    btns.append(("hub_h%d" % idx, idx, cmd))
    gocfg[nm] = cmd

models = ['scenemodel "models/menu/hub_%s%d.tik" 0 0 0 0' % (g, k + 1) for g in ("bg", "floor", "chrome") if g in BJ["groups"]
          for k in range(BJ["groups"][g]["models"])]
models += ['scenemodel "models/menu/hub_%s.tik" 0 0 0 0' % g for g in sorted(BJ["groups"]) if g.startswith("q_")]      # the lettered boards
assert len([m for m in models if "hub_q_" in m]) == 3, models
CRLF = "\r\n"
blk = ["// ---- [mphub3d] begin: the live 3D multiplayer room (ui_atticMain 1; generated by docs/proposals/mphub3d_2026-11-02/make_mphub3d.py - do not hand-edit)",
       "resource", "Scene3D", "{", 'name "%s"' % SCENE, "rect 0 0 640 480", GATE_ON] + models + ["scenecam " + HOME_S] + hots + boxes + labels + ["}"]
for k in sorted(caps):
    blk += ["resource", "Label", "{", 'name "hubcap%d"' % k, "rect 0 0 8 8", 'title "%s"' % caps[k], "fgcolor 0.93 0.88 0.72 1.00", "bgcolor 0.10 0.08 0.06 0.82",
            'borderstyle "NONE"', 'font "facfont-20"', "textalign center", 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % k, "}"]
for n, idx, cmd in btns:
    blk += ["resource", "Button", "{", 'name "%s"' % n, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"',
            'stuffcommand "%s"' % cmd, 'hovercommand "set ui_scene_hot %d"' % idx, 'mouseawaycommand "set ui_scene_hot 0"', GATE_ON, "}"]
blk += ["// ---- [mphub3d] end"]
BLOCK = CRLF.join(blk) + CRLF

# ---- 2. splice into ui/multiplayer.urc (CRLF file, binary-safe, asserted)
mp = os.path.join(modui, "multiplayer.urc")
raw = open(mp, "rb").read()
assert raw.count(b"\r\n") == raw.count(b"\n"), "multiplayer.urc is not uniformly CRLF"
t = raw.decode("latin-1")
t = re.sub(r"// ---- \[mphub3d\] begin.*?// ---- \[mphub3d\] end\r\n", "", t, flags=re.S)
t = t.replace(" ui_atticActive!=1\"", "\"").replace('enabledcvar "ui_atticActive!=1"\r\n', "")
ESC = 'escapecommand "set ui_scene_hot 0; popmenu 1"\r\n'
t = t.replace(ESC, "")
ANCH = 'virtualres 1\r\ninclude "ui/multiplayerback.inc"\r\n'
assert t.count(ANCH) == 1
# ESC: the stock pop (popmenu 1 == the engine's PopMenu(qtrue)), plus a hover reset - a hub hotspot index must not light an attic hotspot
t = t.replace(ANCH, 'virtualres 1\r\n' + ESC + 'include "ui/multiplayerback.inc"\r\n' + BLOCK, 1)
KEEP = {"disconnect"}
ng = 0


def gate(m):
    global ng
    b = m.group(0)
    if "[mphub3d]" in b or "Scene3D" in b:
        return b
    name = (re.search(r'(?m)^name\s+"([^"]*)"', b) or [None, ""])[1]
    if name in KEEP or name.startswith(("hubcap", "hub_h")):
        return b
    ng += 1
    eg = re.search(r'(?m)^enabledcvar\s+"([^"]*)"\r$', b)
    if eg:
        return b.replace(eg.group(0), 'enabledcvar "%s ui_atticActive!=1"\r' % eg.group(1))
    assert b.endswith("}\r\n")
    return b[:-3] + 'enabledcvar "ui_atticActive!=1"\r\n}\r\n'


body_at = t.index("// ---- [mphub3d] end\r\n") + len("// ---- [mphub3d] end\r\n")
tail = re.sub(r"resource\r\n\w+\r\n\{\r\n.*?\r\n\}\r\n", gate, t[body_at:], flags=re.S)
t = t[:body_at] + tail
GATED = {"changemap", "sign", "radio_bg", "maproom", "Multiplayer Options", "joingame_bg", "joinlan", "startnew", "servicerecord", "armory"}
for g in GATED:
    assert re.search(r'name "%s"\r\n(?:(?!\r\n\}).)*?ui_atticActive!=1' % re.escape(g), t, re.S), "not gated: " + g
assert ng == 12, ng
open(mp, "wb").write(t.encode("latin-1"))

# ---- 3. smoke-test triggers: the hotspot's own command, uiafter steps as cfg waits
for nm, cmd in gocfg.items():
    out, tt = [], 0.0
    for l in [x.strip() for x in cmd.split(";") if x.strip()]:
        ma = re.match(r"uiafter (\S+) (.*)$", l)
        if ma:
            due = float(ma.group(1))
            if due > tt:
                out.append("wait %d" % int(round((due - tt) * 1000)))
                tt = due
            out.append(ma.group(2))
        else:
            out.append(l)
    open(os.path.join(modui, "hzm_hub_go_%s.cfg" % nm), "w", newline="\n").write(
        "// generated by make_mphub3d.py: the 3D multiplayer room hotspot '%s' without a cursor (ui_atticMain 1)\n" % nm + "\n".join(out) + "\n")

# ---- 4. ship pk3 = the shipped attic pk3 + the hub files (same name: no build.ps1 / publish_release.ps1 change)
os.makedirs(os.path.dirname(SHIP_PK3), exist_ok=True)
base = zipfile.ZipFile(BASE_PK3)
have = set(base.namelist())
add = []
for root, _d, fs in os.walk(stage):
    for fn in fs:
        if fn.endswith((".json", ".pk3")):
            continue
        p = os.path.join(root, fn)
        add.append((p, os.path.relpath(p, stage).replace("\\", "/")))
clash = [a for _p, a in add if a in have]
assert not clash, clash
tmp = SHIP_PK3 + ".tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
    for info in base.infolist():
        z.writestr(info, base.read(info.filename))
    for p, a in sorted(add, key=lambda x: x[1]):
        z.write(p, a)
base.close()
os.replace(tmp, SHIP_PK3)
print("multiplayer.urc: %d hotspots, %d flat widgets gated; ship pk3 %s (%d bytes, +%d hub files)" % (len(hots), ng, SHIP_PK3, os.path.getsize(SHIP_PK3), len(add)))
print("home", HOME_S)
for h, b in zip(hots, boxes):
    print("  ", h[:60], "...", b)

"""make_main3d.py <stage dir> <mod ui/main.urc> - the attic AS the main menu (ui_atticMain 1).

Reads the stage written by make_stage3.py (models / lights / home camera / shelf pose / radio hotspots), builds the root Scene3D + hotspot proxies, splices them into the
mod's generated ui/main.urc and gates the flat room off when ui_atticMain is 1.  Idempotent.  ui_atticMain 0 (default) leaves every existing behaviour untouched.

  stop 0 (attic overview): OPTIONS (radio shelf), MULTIPLAYER (door), NEW GAME (wall map), BRIEFING (door), RECORDS (long desk)
                           click = a short camera move toward the object, then the object's EXISTING flat menu; BACK = the scene flies home by itself (sceneleave)
  stop 1 (radio shelf):    the six radios -> hzm_radio3d_* (close-up, 2D controls over the 3D view);  ESC / B = home (UI_SceneEscape)
HUD plates (QUIT, BACK TO GAME, What's New, Report a Bug, version, Discord, music) stay 2D widgets over the 3D view."""
import json, math, os, re, sys
import numpy as np

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import scene_params as SP  # noqa: E402

stage, mainp = sys.argv[1], sys.argv[2]
SCALE = 52.5
RADIOS = json.load(open(os.environ.get("CAL_RADIOS", r"G:/mohaa-hudfeed3/menus3d/bake_rj/radios.json")))
CAL = json.load(open(os.path.join(H, "radio_cal.json")))
P = json.load(open(os.path.join(stage, "poses.json")))
urc = open(os.path.join(stage, "ui", "hzm_menus3d.urc"), encoding="utf-8").read()
scene_lines = [l for l in urc.splitlines() if l.startswith(("scenemodel", "scenelight", "scenecam"))]
home_org = np.array(P["home"][0])
shelf = "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (tuple(P["fly"][0]) + tuple(P["fly"][1]) + (P["fly"][2],))


def conv(p):
    return SP.conv(p, SCALE)


def approach(target_bu, dist_bu, fov, dz=0.0, dirbu=None):
    """camera pose `dist_bu` metres short of target_bu, looking at it: on the line from the home camera, or - with dirbu - looking along that BU direction (a door is
    framed square on, the camera flying over the desks)"""
    t = conv(target_bu)
    if dirbu is not None:
        u = SP.conv(np.array(dirbu, float), 1.0)
        u = u / np.linalg.norm(u)
    else:
        d = t - home_org
        u = d / np.linalg.norm(d)
    org = t - u * dist_bu * SCALE
    org[2] += dz * SCALE
    f = t - org
    f /= np.linalg.norm(f)
    yaw = math.degrees(math.atan2(f[1], f[0]))
    pitch = math.degrees(-math.asin(max(-1, min(1, f[2]))))
    return "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (org[0], org[1], org[2], pitch, yaw, 0.0, fov)


# name, caption, menu, hotspot centre (BU m), radius (BU m), approach distance (m), fov, camera lift (m)
# hotspot centres / approach poses are tuned in the world graph QA (docs: FEASIBILITY.md, attic main menu)
HOTS = [
    ("mp", "MULTIPLAYER", "multiplayer", (3.02, 6.40, 1.35), 0.75, 2.7, 46.0, 0.10),
    ("newgame", "NEW GAME", "briefingroom", (-0.55, 6.74, 2.05), 0.70, 3.4, 54.0, 0.0),
    ("brief", "BRIEFING", "briefingroom", (3.02, 8.30, 1.35), 0.75, 2.7, 46.0, 0.10),
    ("records", "RECORDS", "war_records", (0.17, 3.30, 0.95), 0.80, 1.7, 44.0, 0.30),
]
# camera targets / directions where the hotspot centre is not what the camera should look at (BU)
LOOK = {"newgame": (-1.15, 6.74, 1.45), "mp": (3.02, 6.40, 1.30), "brief": (3.02, 8.30, 1.30)}
DIRBU = {"mp": (0.9, 0.45, 0.0), "brief": (0.85, 0.55, 0.0), "newgame": (0.18, 1.0, 0.0)}      # doors: seen a little from the side, so the camera stays clear of the back wall
OVR = json.load(open(os.path.join(H, "attic_hots.json"))) if os.path.exists(os.path.join(H, "attic_hots.json")) else {}
rc = np.array(P["radio_ctr"])
hots, btns = [], []
opt_cmd = "set ui_atcStop 1; set ui_scene_hot 0; globalwidgetcommand atticscene scenereturn %s; globalwidgetcommand atticscene scenefly 0.6 %s" % (shelf, shelf)
hots.append('scenehot "options" %.1f %.1f %.1f %.1f "%s" "OPTIONS" "hot_a0" 0' % (rc[0], rc[1], rc[2], P["radio_size"] * 0.55, opt_cmd))
btns.append(("hot_a0", 1, opt_cmd))
for i, (nm, cap, menu, c, r, dist, fov, lift) in enumerate(HOTS):
    o = OVR.get(nm, {})
    c = tuple(o.get("centre", c)); r = o.get("radius", r); dist = o.get("dist", dist); fov = o.get("fov", fov); lift = o.get("lift", lift)
    pose = o.get("pose") or approach(tuple(o.get("look", LOOK.get(nm, c))), dist, fov, lift, o.get("dir", DIRBU.get(nm)))
    cu = conv(c)
    # the dip: the veil fades up over the last 0.15 s of the move, the flat menu opens under it, the veil fades out over 0.2 s (BACK does the reverse in the engine)
    cmd = "set ui_scene_hot 0; globalwidgetcommand atticscene sceneleave; globalwidgetcommand atticscene scenefly 0.6 %s; uiafter 0.45 uiveil 1 0.15; uiafter 0.6 pushmenu %s; uiafter 0.62 uiveil 0 0.2" % (pose, menu)
    hots.append('scenehot "%s" %.1f %.1f %.1f %.1f "%s" "%s" "hot_a%d" 0' % (nm, cu[0], cu[1], cu[2], r * SCALE, cmd, cap, i + 1))
    btns.append(("hot_a%d" % (i + 1), i + 2, cmd))
NAMES = [("video", "VIDEO"), ("graphics", "GRAPHICS"), ("effects", "EFFECTS"), ("audio", "AUDIO"), ("controls", "CONTROLS"), ("gameplay", "GAMEPLAY")]
for i, (r, cap) in enumerate(NAMES):
    lo, hi = np.array(RADIOS[r]["min"]), np.array(RADIOS[r]["max"])
    c = conv([(lo[0] + hi[0]) / 2, lo[1] - 0.02, (lo[2] + hi[2]) / 2])
    rad = max(hi[0] - lo[0], (hi[2] - lo[2]) * 1.4) * SCALE * 0.5 * 1.1
    co = conv(CAL[r]["cam_bu"])
    cp = "%.1f %.1f %.1f 0.00 0.00 0.00 %.2f" % (co[0], co[1], co[2], CAL[r]["fov_y"])
    cmd = "set ui_atcStop 2; set ui_scene_hot 0; set ui_hzmRad3d 1; set ui_hzmRadFade 0; set ui_hzmRadPage 0; globalwidgetcommand atticscene scenefly 0.6 %s; uiafter 0.6 pushmenu hzm_radio3d_%s; uiafter 0.65 set ui_hzmRadFade 1; uiafter 0.72 set ui_hzmRadFade 2; uiafter 0.79 set ui_hzmRadFade 3; uiafter 0.86 set ui_hzmRadFade 4" % (cp, r)
    hots.append('scenehot "%s" %.1f %.1f %.1f %.1f "%s" "%s" "hot_r%d" 1' % (r, c[0], c[1], c[2], rad, cmd, cap, i + 1))
    btns.append(("hot_r%d" % (i + 1), len(HOTS) + 2 + i, cmd))

GATE = 'enabledcvar "ui_atticMain==1"'
blk = ["// ---- [attic-main] the live 3D attic AS the main menu (ui_atticMain 1; generated by make_main3d.py - do not hand-edit)", "resource", "Scene3D", "{", 'name "atticscene"', "rect 0 0 640 480", GATE, "sceneroot"]
import actor_anims as AA  # noqa: E402
_h = conv((AA.HUB["bu"][0], AA.HUB["bu"][1], 0.0))
_dir = ['actorhub %.1f %.1f %.1f "%s" "%s" %.1f' % (_h[0], _h[1], -152.0, AA.HUB["idle"], AA.HUB["walk"], AA.HUB["speed"]),
        'actorbreak "%s" %.1f %.1f' % (AA.BREAK["anims"], AA.BREAK["tmin"], AA.BREAK["tmax"])]
for _n, _yaw, _a, _b, _pth, _seq in AA.STATIONS:
    _pp = ",".join("%.1f %.1f" % tuple(conv((x, y, 0.0))[:2]) for x, y in _pth)
    _dir.append('actorstation "%s" %d %.1f %.1f "%s" "%s"' % (_n, _yaw, _a, _b, _pp, _seq))
blk += scene_lines + _dir + hots + ["}"]
for n, idx, cmd in btns:
    blk += ["resource", "Button", "{", 'name "%s"' % n, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % cmd,
            'hovercommand "set ui_scene_hot %d"' % idx, 'mouseawaycommand "set ui_scene_hot 0"', GATE, "}"]
BLOCK = "\n".join(blk) + "\n"

# deterministic triggers for smoke tests / scripts (no cursor needed): `exec ui/hzm_attic_go_<hotspot>.cfg` runs the hotspot's own command.  Radios need the shelf stop first.
_cfgdir = os.path.dirname(mainp)
for _h in hots:
    _m = re.match(r'scenehot "(\w+)" \S+ \S+ \S+ \S+ "([^"]*)"', _h)
    _n, _lines = _m.group(1), [x.strip() for x in _m.group(2).split(";") if x.strip()]
    if _n in ("video", "graphics", "effects", "audio", "controls", "gameplay"):
        _lines = ["set ui_atcStop 1"] + _lines
    # test shortcut: no `uiafter` (timed steps run through the cfg's own `wait <ms>` instead; the mouse / pad paths keep uiafter in the button command)
    _out, _t = [], 0.0
    for _l in _lines:
        _ma = re.match(r"uiafter (\S+) (.*)$", _l)
        if _ma:
            _due = float(_ma.group(1))
            if _due > _t:
                _out.append("wait %d" % int(round((_due - _t) * 1000)))
                _t = _due
            _out.append(_ma.group(2))
        else:
            _out.append(_l)
    _lines = _out
    open(os.path.join(_cfgdir, "hzm_attic_go_%s.cfg" % _n), "w", newline="\n").write(
        "// generated by make_main3d.py: the attic hotspot '%s' without a cursor (ui_atticMain 1)\n" % _n + "\n".join(_lines) + "\n")

t = open(mainp, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
t = t.replace("\r\n", "\n")
# idempotent: drop a previous splice
t = re.sub(r"// ---- \[attic-main\].*?\n(?=resource\nLabel\n\{\nname \"sign\")", "", t, flags=re.S) if "[attic-main]" in t else t
t = re.sub(r'(?m)^(enabledcvar "[^"]*) ui_atticMain!=1"$', r'\1"', t)       # strip old gates before re-adding
KEEP = {"hzm_quit_plate", "hzm_quit", "hzm_backtogame_plate", "hzm_backtogame"}


def gate_block(m):
    b = m.group(0)
    name = (re.search(r'(?m)^name\s+"([^"]*)"', b) or [None, ""])[1]
    if name in KEEP:
        return b
    eg = re.search(r'(?m)^enabledcvar\s+"([^"]*)"$', b)
    btn = b.startswith("resource\nButton")
    if eg:
        cv = eg.group(1)
        if "ui_menuRoom" in cv or cv == "developer" or "ui_voodoo" in cv and False:
            return b.replace(eg.group(0), 'enabledcvar "%s ui_atticMain!=1"' % cv)
        return b
    # ungated hit areas of the flat room: new game, records, briefing, bigmap(developer has a gate), multiplayer, credits
    if btn and name in ("new game old", "records", "briefing", "Default", "credits"):
        sc = (re.search(r'(?m)^stuffcommand\s+"([^"]*)"', b) or [None, ""])[1]
        if sc.startswith(("pushmenu briefingroom", "pushmenu war_records", "pushmenu multiplayer", "spmap credits")):
            return b[:-2].rstrip("\n") + '\nenabledcvar "ui_atticMain!=1"\n}\n'
    return b


t = re.sub(r"resource\n\w+\n\{\n.*?\n\}\n", gate_block, t, flags=re.S)
anchor = 'resource\nLabel\n{\nname "sign"'
assert anchor in t, "sign label not found"
t = t.replace(anchor, BLOCK + anchor, 1)
open(mainp, "w", encoding="utf-8", newline="").write(t.replace("\n", nl))
print("main.urc patched:", len(HOTS) + 1, "home hotspots,", len(NAMES), "radios;", t.count("ui_atticMain!=1"), "gated flat widgets")
for h in hots:
    print("  ", h[:110])

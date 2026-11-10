"""make_attic_polish.py <mod ui dir> - the attic main menu's art/QA pass + the gramophone corner.  Idempotent.

BUILD ORDER of ui/main.urc's attic:  make_main3d.py -> make_mphub3d.py -> newgame/make_newgame3d.py -> THIS.
(make_main3d.py re-splices the whole [attic-main] block and drops this block with it, so run this again after it.)

The gramophone (user 2026-11-02): "Find a place in the 3d menu where it makes sense to switch through the main menu themes and still
shows the titles, should be interactive and not its own menu", then "Not a fan of your gramophone position it's awkward, make it
personal. I thought we'd have a way to interact with the gramophone itself not a menu."
  * the officer's own corner (corner_layout.py): a side table of his own in the gap between Weathers' work table and the long desk,
    the stock phonograph on it (re-posed, gen_gram_model.py) with its record spinning (hzm_gram_disc, 33 1/3 rpm).
  * the gramophone IS the control: one scenehot (appended LAST - ui_scene_hot is the 1-based list position) over the gramophone and
    its sleeve, with a proxy Button: hover = the standard warm glow + the chalk caption NEXT RECORD; click / Enter / pad A = the
    next record (vstr ui_mmSelNext) with the needle-drop sound.  No menu, no arrows, no frame.
  * the title is on the record itself: the sleeve leaning on the gramophone is the sleeve of what is playing (title + game type-set
    on its shop label, a Label linked to ui_mmSleeve), the record's own paper label on the turntable changes with it (ui_mmLabel),
    and while the pick is shuffle a pencilled "Shuffle ?" tag is tucked into the sleeve (ui_mmShuffle).
  * the flat menu's 2D theme box is hidden while the attic is up; its arrows step the same persisted pick in the flat menu.
Art / QA fixes are listed in ../README.md (defect table)."""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corner_layout as CL  # noqa: E402

ui = sys.argv[1]
mainp = os.path.join(ui, "main.urc")
t = open(mainp, encoding="latin-1", newline="").read()
nl = "\r\n" if "\r\n" in t else "\n"
t = t.replace("\r\n", "\n")
TAG = "// ---- [attic-polish]"

# idempotent: drop the previous run (scene lines carry no comments - a resource block takes none)
t = re.sub(r'(?m)^(?:scenemodel "models/(?:static/phonograph|menu/hzm_gram\w*|menu/hzm_corner\w*|menu/hzm_fan\w*|menu/hzm_door_pane\w*|menu/hzm_clock\w*|menu/hzm_medal\w*|menu/hzm_proj\w*|menu/hzm_dial\w*|menu/hzm_wx_\w*)\.tik"|scenewx "\w+"|scenehot "(?:music|fieldreport|bugbox|needle|rack|window|lookup)"|scenehotfx "\w+"|scenepeek "\w+"|scenehotbox "(?:film|rack)"|scenemodelhide "\w+"|scenemodelcvar "\w+"|scenelabel "(?:gram\w*|atticsignGram|atticsign_\w+|atticsignIdle)").*\n', "", t)
t = re.sub(r"// ---- \[attic-polish\] widgets\n.*?// ---- \[attic-polish\] widgets end\n", "", t, flags=re.S)
t = re.sub(r'(?m)^enabledcvar "ui_atticActive!=1" // \[attic-polish\]\n', "", t)

i0 = t.index('name "atticscene"')
blk_end = t.index("\n}\n", i0)
scene = t[i0:blk_end]
nhot = len(re.findall(r'(?m)^scenehot "', scene))
GATE = 'enabledcvar "ui_atticActive==1"'
idx = nhot + 1

# ---- the gramophone corner (every position: corner_layout.py)
sc = ['scenemodel "%s" %.1f %.1f %.1f %.1f "%s"' % m for m in CL.MODELS]
# v1.10.66 (user: "the records in the main menu come off as obviously being a 2d image"): the record's label, the sleeve and the
# SHUFFLE tag are 3D models now (gen_gram_model.py), one per record, drawn only while theirs is the playing one (engine
# scenemodelcvar, menu-attic66: ui_mmLabel / ui_mmSleeve are set by ui/coop_menumusic/p<n>.cfg). The plain disc stays for an empty ui_mmLabel.
import gen_menumusic as _GM  # noqa: E402
_dl = [l for l in sc if "hzm_gram_disc.tik" in l][0]
for _i in range(len(_GM.THEMES)):
    sc.append(_dl.replace("hzm_gram_disc.tik", "hzm_gram_disc%d.tik" % _i))
    sc.append('scenemodelcvar "hzm_gram_disc%d" "ui_mmLabel" "textures/menu/hzm_gram_label%d"' % (_i, _i))
    sc.append('scenemodel "models/menu/hzm_gram_sleeve3d%d.tik" %.1f %.1f %.1f %.1f' % ((_i,) + CL.SLEEVE3D))
    sc.append('scenemodelcvar "hzm_gram_sleeve3d%d" "ui_mmSleeve" "textures/menu/hzm_gram_sleeve%d"' % (_i, _i))
sc.append('scenemodelcvar "hzm_gram_disc" "ui_mmLabel" ""')
sc.append('scenemodel "models/menu/hzm_gram_tag3d.tik" %.1f %.1f %.1f %.1f' % CL.SLEEVE3D)
sc.append('scenemodelcvar "hzm_gram_tag3d" "ui_mmShuffle" "1"')
# v1.10.66 the telephones' rotary dials (gen_dials.py): a crisp face model on every dial (the baked atlas cannot hold one)
import json  # noqa: E402
for _dn in sorted(json.load(open(os.environ.get("DIALS_JSON", r"H:\hzm_work\attic62\dials.json")))):
    sc.append('scenemodel "models/menu/hzm_dial_%s.tik" 0 0 0 0' % _dn)
# v1.10.62 the wall fan's blades (gen_fan_rotor.py): origin on the hub, the idle anim turns them about the motor shaft
# v1.10.67 the gable window looks outside (gen_window_view.py): sky / town / oak / rain layers and their scenewx roles
_wxj = os.environ.get("WX_JSON", "H:/hzm_work/attic62/wxadd/wx_scene.json")
if os.path.exists(_wxj):
    sc.extend(json.load(open(_wxj))["lines"])
sc.append('scenemodel "models/menu/hzm_fan_rotor.tik" %.1f %.1f %.1f 0.0 "idle"' % CL.bu(CL.FAN_HUB_BU))
# v1.10.62 the MULTIPLAYER door's frosted pane, one texture for both sides of the door (gen_door_pane.py; the MP room's copy is
# put into multiplayer.urc's hubscene below)
sc.append('scenemodel "models/menu/hzm_door_pane_attic.tik" 0 0 0 0')
# v1.10.62 the wall clock tells the player's time (gen_clock.py): a new dial + three hands + cap on the arbor, yaw 180 (their +X
# looks out of the dial); the hands' anim field clock_h / clock_m / clock_s is the engine's local-time kind (menu-clock)
_ck = CL.bu(CL.CLOCK_BU)
sc.append('scenemodel "models/menu/hzm_clock_face.tik" %.2f %.2f %.2f 180.0' % _ck)
for _n, _an in (("hour", "clock_h"), ("minute", "clock_m"), ("second", "clock_s")):
    sc.append('scenemodel "models/menu/hzm_clock_%s.tik" %.2f %.2f %.2f 180.0 "%s"' % ((_n,) + _ck + (_an,)))
sc.append('scenemodel "models/menu/hzm_clock_cap.tik" %.2f %.2f %.2f 180.0' % _ck)
sc.append('scenehot "music" %.1f %.1f %.1f %.1f "%s" "NEXT RECORD" "hot_gram" 0' % (CL.HOT + (CL.GRAM_SEQ,)))
# v1.10.61 (user): "when the mouse is over the gramophone, show a small text box with the track that's playing (theme title, plus
# game line if it fits, same style as the room's hover captions)" - the dark caption plate of the New Game map's hover captions,
# above the gramophone; two lines linked to the PLAYING track's cvars (set by p<n>.cfg, so in shuffle it names the rolled track)
hx, hy, hz, hhw, hhh = CL.HOVERBOX
HOVER_ROWS = [  # name, cvar, placeholder = the longest value (the engine fits the placeholder, so every track keeps one size), font, band
    ("gramHoverTitle", "ui_menuMusicTitle", "Dogs of War: Main Title", "facfont-20", (0.10, 0.56)),
    ("gramHoverGame", "ui_menuMusicGame", "Medal of Honor: European Assault", "facfont-20", (0.58, 0.90)),
]
sc.append('scenelabel "gramHoverBox" %.2f %.2f %.2f %.2f %.2f' % CL.HOVERBOX)
for n, cv, ph, fnt, (b0, b1) in HOVER_ROWS:
    sc.append('scenelabel "%s" %.2f %.2f %.2f %.2f %.2f' % (n, hx - 0.1, hy, hz + hhh - (b0 + b1) * hhh, hhw * 0.92, (b1 - b0) * hhh))
# the chalk caption on the hanging board while the gramophone is hovered, framed like make_main3d's atticsign<N> labels
_sg = re.search(r'(?m)^scenelabel "atticsign\d+" (\S+ \S+ \S+ \S+ \S+)$', scene)
sc.append('scenelabel "atticsignGram" %s' % _sg.group(1))
# ---- v1.10.62: the two brown buttons get in-world homes, appended AFTER the gramophone (indices idx+1, idx+2: nothing shifts):
# the FIELD REPORT board on the post by the long desk (= WHAT'S NEW) and the field toolbox on the long desk (= REPORT A BUG);
# both baked into the room by attic62_edit.py, positions from corner_layout (BU -> game units)
import json  # noqa: E402
import math  # noqa: E402
import numpy as np  # noqa: E402
_M3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kickoff_2026-10-18", "menus3d")
sys.path.insert(0, _M3)
import scene_params as SP  # noqa: E402


def approach(look_bu, dist, fov, lift=0.0, dirbu=None):
    """make_main3d.approach: a camera `dist` m short of look_bu, looking at it - along dirbu (BU) or from the home camera"""
    t = SP.conv(np.array(look_bu, float), 52.5)
    if dirbu is not None:
        u = SP.conv(np.array(dirbu, float), 1.0)
    else:
        u = t - np.array([-36.7, 21.0, 102.4])
    u = u / np.linalg.norm(u)
    o = t - u * dist * 52.5
    o[2] += lift * 52.5
    f = (t - o) / np.linalg.norm(t - o)
    return "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (o[0], o[1], o[2], math.degrees(-math.asin(f[2])), math.degrees(math.atan2(f[1], f[0])), 0.0, fov)


def fly(pose, *then):
    """the attic's hotspot recipe (make_main3d): leave, fly 0.6 s, dip, the menu opens under the veil; BACK flies home"""
    return ("set ui_scene_hot 0; globalwidgetcommand atticscene sceneleave; globalwidgetcommand atticscene scenefly 0.6 %s; "
            "uiafter 0.45 uiveil 1 0.15; " % pose + "".join("uiafter 0.6 %s; " % c for c in then) + "uiafter 0.62 uiveil 0 0.2")


# v1.10.63 (user): "for report a bug, service record, and field report lets have the cameras move over to those too"
FR_POSE = approach(CL.FIELD_REPORT_BU, 1.25, 44.0, 0.0, (1.0, 0.0, 0.0))        # square on to the board on the wall
BUG_POSE = approach(CL.TOOLBOX_BU, 1.05, 44.0, 0.35)                              # over the desk from the home side
EXTRA_HOTS = [  # name, hotspot centre (game units), radius, the command (fly + open), chalk caption, proxy
    ("fieldreport", CL.bu(CL.FIELD_REPORT_BU), 16.0, fly(FR_POSE, "pushmenu coop_whatsnew"), "WHAT'S NEW", "hot_fieldreport"),
    ("bugbox", CL.bu(CL.TOOLBOX_BU), 15.0, 'seta coop_reportResult \\"\\"; ' + fly(BUG_POSE, "pushmenu coop_report", "coop_reportopen"), "REPORT A BUG", "hot_bugbox"),
]
for k, (n, c, r, cmd, cap, prox) in enumerate(EXTRA_HOTS):
    sc.append('scenehot "%s" %.1f %.1f %.1f %.1f "%s" "%s" "%s" 0' % (n, c[0], c[1], c[2], r, cmd, cap, prox))
    sc.append('scenelabel "atticsign_%s" %s' % (n, _sg.group(1)))
# v1.10.62 the tone arm's needle: its own hotspot, LAST (index idx + 3); click = the arm lifts, the record changes, the arm drops
NEEDLE_IDX = idx + 1 + len(EXTRA_HOTS)
sc.append('scenehot "needle" %.1f %.1f %.1f %.1f "%s" "NEXT RECORD" "hot_needle" 0' % (CL.NEEDLE_HOT + (CL.GRAM_SEQ,)))
sc.append('scenelabel "atticsign_needle" %s' % _sg.group(1))
# the hover box names the playing track for the needle too: a second set of its labels, gated on the needle's index
sc.append('scenelabel "gramHoverBoxN" %.2f %.2f %.2f %.2f %.2f' % CL.HOVERBOX)
for n, cv, ph, fnt, (b0, b1) in HOVER_ROWS:
    sc.append('scenelabel "%sN" %.2f %.2f %.2f %.2f %.2f' % (n, hx - 0.1, hy, hz + hhh - (b0 + b1) * hhh, hhw * 0.92, (b1 - b0) * hhh))
# v1.10.63 the RIFLE RACK (attic62_edit section 9, right-hand wall right of the post): hotspot "rack", LAST (NEEDLE_IDX + 1).
# The weapon viewer (branch wpnviewer) hooks its menu onto this hotspot; until then a click flies there and back.
RACK_IDX = NEEDLE_IDX + 1
RACK_C_BU = (2.90, 1.54, 1.56)           # attic62_edit RX 3.0, RY 1.03 .. 2.05 (centred between the post and the wall's end in the peek view)
RACK_POSE = approach(RACK_C_BU, 1.70, 50.0, 0.0, (1.0, 0.0, 0.0))
RACK_CMD = ("set ui_scene_hot 0; globalwidgetcommand atticscene scenefly 0.6 %s; uiafter 2.6 globalwidgetcommand atticscene scenefly 0.6 "
            "-36.7 21.0 102.4 7.01 0.00 0.00 55.11" % RACK_POSE)
_rc = CL.bu(RACK_C_BU)
sc.append('scenehot "rack" %.1f %.1f %.1f %.1f "%s" "WEAPONS RACK" "hot_rack" 0' % (_rc + (34.0, RACK_CMD)))
sc.append('scenehotbox "rack" 0.0 0.0 150.0 260.0')
# The rack wall is outside the 16:9 and 4:3 home view (coordinator 2026-11-04: "make the rack reachable at every aspect"). Option (a),
# moving it into view, has no room: the only right-wall strip in view at 16:9 is the FIELD REPORT board's, and none at 4:3. So (b):
# hovering / focusing the rack (its proxy, or the WEAPONS RACK cue at the right screen edge) turns the camera right from home
# (engine scenepeek, menu-attic63); moving the cursor back into the left 40 % of the screen, or onto another hotspot, turns it home.
# (A v1.10.64 move into the home view was cancelled by the user - "im good with the rack where its at" - mod branch attic-64.)
PEEK_POSE = "-36.7 21.0 102.4 7.01 -35.00 0.00 55.11"
sc.append('scenepeek "rack" 0.5 %s' % PEEK_POSE)
sc.append('scenelabel "atticsign_rack" %s' % _sg.group(1))
# v1.10.67 the WINDOW (coordinator: "the rafter hides most of the pane ... make the window an attic hotspot"): hotspot "window", LAST
# (RACK_IDX + 1). Hover = the usual warm glow + LOOK OUTSIDE on the chalkboard; click flies to a close view of the pane (ui_atcStop 3:
# the home hotspots sleep); BACK (the chalk tab, ESC, pad B - engine TryEscape takes stop 3 as well as the options shelf) flies home.
WINDOW_IDX = RACK_IDX + 1
WINDOW_POSE = "315.0 210.0 84.0 0.00 0.00 0.00 62.00"      # v1.10.67 the 1.5 x 0.9 m pane, between the rafter (x 294-305) and the glass
WINDOW_CMD = "set ui_atcStop 3; set ui_scene_hot 0; globalwidgetcommand atticscene scenefly 0.7 %s" % WINDOW_POSE
sc.append('scenehot "window" 358.0 210.0 84.0 30.0 "%s" "LOOK OUTSIDE" "hot_window" 0' % WINDOW_CMD)
sc.append('scenelabel "atticsign_window" %s' % _sg.group(1))
# v1.10.67 the SKYLIGHT (user: "when you go to look at the top window"): hotspot "lookup", LAST (WINDOW_IDX + 1). Hover = the glow +
# LOOK UP; click flies under the roof light (ui_atcStop 4) and sets ui_wxLookUp 1: the engine rolls a chance of an aircraft pass
# (40 %, never twice running). BACK / ESC / pad B fly home.
LOOKUP_IDX = WINDOW_IDX + 1
LOOKUP_POSE = "202.7 112.4 70.5 -65.50 90.00 0.00 70.00"
LOOKUP_CMD = "set ui_atcStop 4; set ui_scene_hot 0; set ui_wxLookUp 1; globalwidgetcommand atticscene scenefly 0.7 %s" % LOOKUP_POSE
sc.append('scenehot "lookup" 202.7 152.3 157.0 34.0 "%s" "LOOK UP" "hot_lookup" 0' % LOOKUP_CMD)
sc.append('scenelabel "atticsign_lookup" %s' % _sg.group(1))
# v1.10.63 RECORDS: the medal box's lid (gen_records3d.py; the box body and the LOAD / SAVE trays are baked)
HINGE = CL.bu((-0.13, 3.50, 0.86))          # = attic62_edit MB x centre, y1, zl
sc.append('scenemodel "models/menu/hzm_medal_lid.tik" %.2f %.2f %.2f 0.0 "closed"' % HINGE)
# v1.10.63 the Film Room projector on hover (gen_projector_fx.py; engine scenehotfx, menu-attic63): the reels turn, the clatter
# runs, the lamp-lit body replaces the dark baked one
_pr = json.load(open(os.environ.get("PROJ_REELS_JSON", r"H:\hzm_work\attic62\projector_reels.json")))["reels"]
_tops = sorted({round(r["c"][2], 3) for r in _pr}, reverse=True)
for _nm, _z in zip(("top", "bot"), _tops):
    _cs = [r["c"] for r in _pr if abs(r["c"][2] - _z) < 0.01]
    _c = CL.bu((float(np.mean([v[0] for v in _cs])), float(np.mean([v[1] for v in _cs])), _z))
    sc.append('scenemodel "models/menu/hzm_proj_reel_%s.tik" %.2f %.2f %.2f 0.0 "idle"' % ((_nm,) + _c))
sc.append('scenemodel "models/menu/hzm_projector_lit.tik" 0 0 0 0')
sc.append('scenemodelhide "hzm_projector_lit" 1')
# #16 the empty lower chalkboard: a standing chalk line when nothing is hovered, so it never reads as a blank plastic panel
sc.append('scenelabel "atticsignIdle" %s' % _sg.group(1))
# #1 the table props are baked into the room now (actor_anims.TABLE_PROPS is empty; this strips them from an older urc too)
t = re.sub(r'(?m)^scenemodel "models/(?:miscobj/clipboard|static/card_table|static/simplerectable)\.tik".*\n', "", t)
i0 = t.index('name "atticscene"')
blk_end = t.index("\n}\n", i0)
t = t[:blk_end] + "\n" + "\n".join(sc) + t[blk_end:]

W = [TAG + " widgets"]
_sgl = re.search(r'resource\nLabel\n\{\nname "atticsign\d+"\n(.*?)\n\}\n', t, re.S).group(1)       # copy the chalk caption style
_sgl = re.sub(r'(?m)^title ".*"$', 'title "NEXT RECORD"', _sgl)
_sgl = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % idx, _sgl)
W += ["resource", "Label", "{", 'name "atticsignGram"', _sgl, "}"]
for sfx, hidx in (("", idx), ("N", NEEDLE_IDX)):
    HGATE = 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % hidx
    W += ["resource", "Label", "{", 'name "gramHoverBox%s"' % sfx, "rect 0 0 8 8", "fgcolor 0.93 0.88 0.72 1.00", "bgcolor 0.10 0.08 0.06 0.82",
          'borderstyle "NONE"', HGATE, "}"]
    for n, cv, ph, fnt, band in HOVER_ROWS:
        col = "0.93 0.88 0.72 1.00" if n == "gramHoverTitle" else "0.78 0.72 0.58 1.00"
        W += ["resource", "Label", "{", 'name "%s%s"' % (n, sfx), "rect 0 0 8 8", 'title "%s"' % ph, "fgcolor %s" % col, "bgcolor 0 0 0 0",
              'borderstyle "NONE"', 'font "%s"' % fnt, "textalign center", 'linkcvar "%s"' % cv, "dontlocalize", HGATE, "}"]
# the click: the needle-drop crackle now plays when the arm comes down (in GRAM_SEQ), not on the click
for prox, hidx in (("hot_gram", idx), ("hot_needle", NEEDLE_IDX)):
    W += ["resource", "Button", "{", 'name "%s"' % prox, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
          'stuffcommand "%s"' % CL.GRAM_SEQ, 'hovercommand "set ui_scene_hot %d"' % hidx, 'mouseawaycommand "set ui_scene_hot 0"', GATE, "}"]
for k, (n, c, r, cmd, cap, prox) in enumerate(EXTRA_HOTS):
    hi = idx + 1 + k
    lab = re.sub(r'(?m)^title ".*"$', 'title "%s"' % cap, _sgl)
    lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % hi, lab)
    W += ["resource", "Label", "{", 'name "atticsign_%s"' % n, lab, "}"]
    W += ["resource", "Button", "{", 'name "%s"' % prox, "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
          'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % cmd, 'hovercommand "set ui_scene_hot %d"' % hi,
          'mouseawaycommand "set ui_scene_hot 0"', GATE, "}"]
lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % NEEDLE_IDX, _sgl)
W += ["resource", "Label", "{", 'name "atticsign_needle"', lab, "}"]
lab = re.sub(r'(?m)^title ".*"$', 'title "WEAPONS RACK"', _sgl)
lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % RACK_IDX, lab)
W += ["resource", "Label", "{", 'name "atticsign_rack"', lab, "}"]
# the cue: a chalk tab on the right screen edge (rect in the 640x480 virtual screen; x 588-636 stays on the right edge at every aspect)
# (the words on a Label: a Button's title goes through the localization table - 'RACK  >' has no entry, a dev-mode LOCALIZATION ERROR)
W += ["resource", "Label", "{", 'name "hzm_rackcue_text"', 'title "RACK  >"', "rect 584 222 52 22", "fgcolor 0.93 0.93 0.88 0.90",
      "bgcolor 0.10 0.08 0.06 0.60", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center",
      'enabledcvar "ui_atticActive==1 ui_scene_peek!=1"', "}"]
W += ["resource", "Button", "{", 'name "hzm_rackcue"', "rect 584 222 52 22", "fgcolor 0 0 0 0",
      "bgcolor 0 0 0 0", 'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"',
      'stuffcommand "%s"' % RACK_CMD, 'hovercommand "set ui_scene_hot %d"' % RACK_IDX,
      'enabledcvar "ui_atticActive==1 ui_scene_peek!=1"', "}"]
W += ["resource", "Button", "{", 'name "hot_rack"', "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
      'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % RACK_CMD, 'hovercommand "set ui_scene_hot %d"' % RACK_IDX,
      'mouseawaycommand "set ui_scene_hot 0"', GATE, "}"]
lab = re.sub(r'(?m)^title ".*"$', 'title "LOOK OUTSIDE"', _sgl)
lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % WINDOW_IDX, lab)
W += ["resource", "Label", "{", 'name "atticsign_window"', lab, "}"]
lab = re.sub(r'(?m)^title ".*"$', 'title "LOOK UP"', _sgl)
lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % LOOKUP_IDX, lab)
W += ["resource", "Label", "{", 'name "atticsign_lookup"', lab, "}"]
W += ["resource", "Button", "{", 'name "hot_lookup"', "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
      'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % LOOKUP_CMD, 'hovercommand "set ui_scene_hot %d"' % LOOKUP_IDX,
      'mouseawaycommand "set ui_scene_hot 0"', GATE, "}"]
W += ["resource", "Button", "{", 'name "hot_window"', "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
      'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % WINDOW_CMD, 'hovercommand "set ui_scene_hot %d"' % WINDOW_IDX,
      'mouseawaycommand "set ui_scene_hot 0"', GATE, "}"]
# at the window: a chalk BACK tab, bottom left (the words on a Label - a Button title goes through the localization table)
W += ["resource", "Label", "{", 'name "hzm_wxback_text"', 'title "<  BACK"', "rect 8 446 64 24", "fgcolor 0.93 0.93 0.88 0.90",
      "bgcolor 0.10 0.08 0.06 0.60", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center",
      'enabledcvar "ui_atticActive==1 ui_atcStop>2"', "}"]
W += ["resource", "Button", "{", 'name "hzm_wxback"', "rect 8 446 64 24", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
      'clicksound "sound/menu/apply.wav"', 'stuffcommand "globalwidgetcommand atticscene sceneback"',
      'enabledcvar "ui_atticActive==1 ui_atcStop>2"', "}"]
# the window's ambience level (user: "overbearing"): a chalk tab beside BACK cycling SOUND OFF / LOW / MED (ui_wxAmbLevel 0 / 1 / 2,
# archived, default LOW); one label and one button per state, each button steps to the next level
for _v, _t, _n in (("0", "SOUND  OFF", "1"), ("1", "SOUND  LOW", "2"), ("2", "SOUND  MED", "0")):
    W += ["resource", "Label", "{", 'name "hzm_wxsnd_text%s"' % _v, 'title "%s"' % _t, "rect 78 446 84 24", "fgcolor 0.93 0.93 0.88 0.90",
          "bgcolor 0.10 0.08 0.06 0.60", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center",
          'enabledcvar "ui_atticActive==1 ui_atcStop>2 ui_wxAmbLevel==%s"' % _v, "}"]
    W += ["resource", "Button", "{", 'name "hzm_wxsnd%s"' % _v, "rect 78 446 84 24", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
          'clicksound "sound/menu/apply.wav"', 'stuffcommand "seta ui_wxAmbLevel %s"' % _n,
          'enabledcvar "ui_atticActive==1 ui_atcStop>2 ui_wxAmbLevel==%s"' % _v, "}"]
idle = re.sub(r'(?m)^title ".*"$', 'title "AWAITING ORDERS"', _sgl)
idle = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==0"', idle)
idle = re.sub(r'(?m)^fgcolor (\S+ \S+ \S+) \S+$', r'fgcolor \1 0.70', idle)       # a little fainter than a live caption: old chalk
W += ["resource", "Label", "{", 'name "atticsignIdle"', idle, "}"]
W.append(TAG + " widgets end")
anchor = 'resource\nLabel\n{\nname "sign"'
assert anchor in t
t = t.replace(anchor, "\n".join(W) + "\n" + anchor, 1)


# the flat menu's theme box: hidden under the attic; its arrows step the same persisted pick
def flat(m):
    b = m.group(0)
    b = b.replace('stuffcommand "vstr ui_menuMusicPrev"', 'stuffcommand "vstr ui_mmSelPrev"').replace('stuffcommand "vstr ui_menuMusicNext"', 'stuffcommand "vstr ui_mmSelNext"')
    return b[:-2] + 'enabledcvar "ui_atticActive!=1" // [attic-polish]\n}\n'


t = re.sub(r'resource\n\w+\n\{\nname "menuMusic(?:Box|Title|Game|Prev|Next)"\n.*?\n\}\n', flat, t, flags=re.S)
# v1.10.62: WHAT'S NEW and REPORT A BUG are the FIELD REPORT board and the toolbox under the attic (the flat menu keeps them)
t = re.sub(r'resource\nButton\n\{\nname "(?:whatsnew|reportbug)"\n.*?\n\}\n', flat, t, flags=re.S)
assert t.count('enabledcvar "ui_atticActive!=1" // [attic-polish]') == 7, "flat theme / button widgets not found"
# v1.10.62: at 4:3 (ui_menuCenter 1) the FIELD REPORT board on the right wall is outside the frame, so WHAT'S NEW keeps its 2D button
# there - a twin of the flat button (enabledcvar ANDs its terms, so "flat OR 4:3" needs two widgets)
t = re.sub(r'resource\nButton\n\{\nname "whatsnew43"\n.*?\n\}\n\n?', "", t, flags=re.S)
_wn = re.search(r'resource\nButton\n\{\nname "whatsnew"\n.*?\n\}\n', t, re.S).group(0)
_wn43 = _wn.replace('name "whatsnew"', 'name "whatsnew43"').replace(
    'enabledcvar "ui_atticActive!=1" // [attic-polish]', 'enabledcvar "ui_atticActive==1 ui_menuCenter==1" // [attic-polish] 4:3 twin')
assert _wn43 != _wn and "whatsnew43" in _wn43
t = t.replace(_wn, _wn + "\n" + _wn43, 1)

# ---- v1.10.62 re-bake: the scene's model lists follow the new build, the briefing door hotspot follows the moved door
import json  # noqa: E402
import math  # noqa: E402
import numpy as np  # noqa: E402
_M3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "kickoff_2026-10-18", "menus3d")
sys.path.insert(0, _M3)
import scene_params as SP  # noqa: E402
_bj = os.environ.get("ATTIC62_BUILD")          # build_models2's build.json of the v1.10.62 bake (unset: model lists untouched)
if _bj:
    _G = json.load(open(_bj))["groups"]
    ORDER = ("floor", "fan", "projector", "props", "blueprint", "desk", "desk2")     # blueprint: v1.10.66 (attic62_edit section 11)
    for g in ORDER:
        n = _G[g]["models"] if g in _G else 0
        old = re.findall(r'(?m)^scenemodel "models/menu/atc_%s\d+\.tik" 0 0 0 0\n' % g, t)
        new = "".join('scenemodel "models/menu/atc_%s%d.tik" 0 0 0 0\n' % (g, k + 1) for k in range(n))
        if old:
            t = t.replace("".join(old), new, 1)
        elif n:         # a new group: right after the group before it (props after the projector, blueprint after props)
            prev = ORDER[ORDER.index(g) - 1]
            pj = re.findall(r'(?m)^scenemodel "models/menu/atc_%s\d+\.tik" 0 0 0 0\n' % prev, t)
            t = t.replace("".join(pj), "".join(pj) + new, 1)
        assert len(re.findall(r'(?m)^scenemodel "models/menu/atc_%s\d+\.tik"' % g, t)) == n, g
_OV = json.load(open(os.path.join(_M3, "attic_hots.json")))["brief"]
_c = SP.conv((1.50, 9.58, 1.35), 52.5)          # = make_main3d.py HOTS / LOOK / DIRBU / _BOX "brief" [v1.10.62]
_tg = SP.conv((1.50, 9.60, 1.30), 52.5)
_u = SP.conv(np.array(_OV["dir"], float), 1.0)
_u = _u / np.linalg.norm(_u)
_o = _tg - _u * _OV["dist"] * 52.5
_o[2] += _OV.get("lift", 0.0) * 52.5
_f = (_tg - _o) / np.linalg.norm(_tg - _o)
BRIEF_POSE = "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (_o[0], _o[1], _o[2], math.degrees(-math.asin(_f[2])), math.degrees(math.atan2(_f[1], _f[0])), 0.0, _OV["fov"])
_bl = re.search(r'(?m)^scenehot "brief" \S+ \S+ \S+ \S+ "([^"]*)"', t)
_oldcmd = _bl.group(1)
if "pushmenu briefingroom" in _oldcmd:          # (v1.10.63 below points the door at the 3D map; then this is already done)
    _newcmd = re.sub(r"scenefly 0\.6 [-\d. ]+?;", "scenefly 0.6 %s;" % BRIEF_POSE, _oldcmd, count=1)
    assert t.count(_oldcmd) == 2, "brief: hotspot + proxy button"
    t = t.replace(_oldcmd, _newcmd)
t = re.sub(r'(?m)^scenehot "brief" \S+ \S+ \S+ \S+ ', 'scenehot "brief" %.1f %.1f %.1f %.1f ' % (_c[0], _c[1], _c[2], _OV["radius"] * 52.5), t, count=1)
t = re.sub(r'(?m)^scenehotbox "brief" .*$', 'scenehotbox "brief" 0.8 3.0 50.0 131.0', t, count=1)
_gp = os.path.join(ui, "hzm_attic_go_brief.cfg")
_g = open(_gp, encoding="latin-1", newline="").read()     # keeps the file's own line ends
_g2 = re.sub(r"scenefly 0\.6 [-\d. ]+?(\r?\n)", lambda m: "scenefly 0.6 %s%s" % (BRIEF_POSE, m.group(1)), _g)
assert "scenefly 0.6 %s" % BRIEF_POSE in _g2
open(_gp, "w", encoding="latin-1", newline="").write(_g2)
print("brief pose", BRIEF_POSE)


def rehot(name, newcmd, centre=None, radius=None):
    """replace a make_main3d hotspot's command (its scenehot line and its proxy Button), optionally its centre / radius"""
    global t
    m = re.search(r'(?m)^scenehot "%s" (\S+ \S+ \S+ \S+) "([^"]*)"' % name, t)
    old = m.group(2)
    assert t.count(old) >= 2, (name, t.count(old))
    t = t.replace('"%s"' % old, '"%s"' % newcmd)
    if centre is not None:
        t = re.sub(r'(?m)^scenehot "%s" \S+ \S+ \S+ \S+ ' % name, 'scenehot "%s" %.1f %.1f %.1f %.1f ' % ((name,) + tuple(centre) + (radius,)), t, count=1)


def gocfg(name, pose, menu, comment):
    open(os.path.join(ui, "hzm_attic_go_%s.cfg" % name), "w", encoding="latin-1", newline="\r\n").write(
        "// generated by make_attic_polish.py: %s (ui_atticMain 1, no cursor)\nset ui_scene_hot 0\nglobalwidgetcommand atticscene sceneleave\n"
        "globalwidgetcommand atticscene scenefly 0.6 %s\nwait 450\nuiveil 1 0.15\nwait 150\npushmenu %s\nwait 20\nuiveil 0 0.2\n" % (comment, pose, menu))


# ---- v1.10.63 BRIEFING in 3D (user: "The 'Briefing' room also needs updated to the 3d Space (we can probably re-use the map ...)").
# Vanilla's briefing room (maintt pak1 ui/briefing_room.urc / .inc) is the campaign map: Tunisia / Sicily / Italy -> missionN
# difficulty, locked by g_t2l1 / g_t3l1, a sign on hover, BACK.  That is exactly the 3D New Game map (hzm_newgame3d + hzm_ng3d_*):
# the BRIEFING door now flies to the wall map and opens it.
_ng = re.search(r'(?m)^scenehot "newgame" \S+ \S+ \S+ \S+ "([^"]*)"', t).group(1)
rehot("brief", _ng)
_mp = re.search(r"scenefly 0\.6 ((?:\S+ ){6}\S+);", _ng).group(1)
gocfg("brief", _mp, "hzm_newgame3d", "the BRIEFING door -> the 3D briefing map (= the New Game wall map)")
# ---- v1.10.63 RECORDS in 3D: fly to the desk, the desk view opens as its own 3D menu (gen_records3d.py)
REC_POSE = "%.1f %.1f %.1f 24.00 0.00 0.00 50.00" % tuple(SP.conv(np.array((0.06, 2.08, 1.33)), 52.5))      # = gen_records3d.DESK_POSE
rehot("records", fly(REC_POSE, "pushmenu hzm_records3d"))
gocfg("records", REC_POSE, "hzm_records3d", "RECORDS -> the 3D records desk")
# ---- v1.10.63 the projector: the hotspot on the stock projector's body (its glow was centred on the old projector's lens) + a box
_pj = CL.bu((0.995, 2.00, 1.205))
rehot("film", re.search(r'(?m)^scenehot "film" \S+ \S+ \S+ \S+ "([^"]*)"', t).group(1), _pj, 15.0)
_i = t.index('name "atticscene"')
_e = t.index("\n}\n", _i)
t = t[:_e] + "\nscenehotbox \"film\" 0.0 -6.0 56.0 92.0\nscenehotfx \"film\" \"sound/menu/hzm_projector_loop.wav\" 0.48 \"hzm_proj_reel_top|hzm_proj_reel_bot\" \"spin\" \"hzm_projector_lit\" \"atc_projector1\"" + t[_e:]
print("v63: brief -> map, records -> desk %s, field report %s, bug box %s, rack %s" % (REC_POSE, FR_POSE, BUG_POSE, RACK_POSE))
open(mainp, "w", encoding="latin-1", newline="").write(t.replace("\n", nl))

# ---- the MP room (mphub3d / mpui generators own multiplayer.urc's hubscene block; make_mphub3d.py re-splices it, so this runs
# after it, like everything else here): the same frosted pane on the room side of the exit door.  Idempotent.
mpp = os.path.join(ui, "multiplayer.urc")
if os.path.exists(mpp):
    m = open(mpp, encoding="latin-1", newline="").read()
    mnl = "\r\n" if "\r\n" in m else "\n"
    m = m.replace("\r\n", "\n")
    m = re.sub(r'(?m)^scenemodel "models/menu/hzm_door_pane_hub\.tik".*\n', "", m)
    i0 = m.index('name "hubscene"')
    j = m.index("\nscenecam ", i0)
    m = m[:j] + '\nscenemodel "models/menu/hzm_door_pane_hub.tik" 0 0 0 0' + m[j:]
    assert m.count("hzm_door_pane_hub") == 1
    open(mpp, "w", encoding="latin-1", newline="").write(m.replace("\n", mnl))
    print("multiplayer.urc: hubscene + the exit door's pane")

# ---- v1.10.66 the MP room's wall clock goes live (user: "the clock in the join game menu needs to be live like the one in the main
# menu"): gen_clock.py CLOCK_PREFIX=hzm_hubclock - a dial 2 mm in front of the baked face (hub_mp.blend clk_face, centre (0.95, 5.327,
# 2.55) BU, radius 0.14 m; the new dial is 0.16 and a black bezel to 0.205 m covers the square baked face and its painted hands) and the three hands + cap on the engine's local-time anims. Into the
# hub's own scene AND every mpui copy of the room (ui/hzm_mpui_scene_*.inc - the room held at each spot). Idempotent.
HUBCLK = SP.conv(np.array((0.95, 5.325, 2.55)), 52.5)
HUBCLK_LINES = ['scenemodel "models/menu/hzm_hubclock_face.tik" %.2f %.2f %.2f 180.0' % tuple(HUBCLK)] + \
    ['scenemodel "models/menu/hzm_hubclock_%s.tik" %.2f %.2f %.2f 180.0 "%s"' % ((_n,) + tuple(HUBCLK) + (_an,))
     for _n, _an in (("hour", "clock_h"), ("minute", "clock_m"), ("second", "clock_s"))] + \
    ['scenemodel "models/menu/hzm_hubclock_cap.tik" %.2f %.2f %.2f 180.0' % tuple(HUBCLK),
     'scenemodel "models/menu/hzm_hubclock_bezel.tik" %.2f %.2f %.2f 180.0' % tuple(HUBCLK)]   # CLOCK_BEZEL 0.205: covers the baked square face
for _f, _scene in [(mpp, "hubscene")] + [(os.path.join(ui, _x), None) for _x in sorted(os.listdir(ui)) if re.match(r"hzm_mpui_scene_\w+\.inc$", _x)]:
    if not os.path.exists(_f):
        continue
    m = open(_f, encoding="latin-1", newline="").read()
    mnl = "\r\n" if "\r\n" in m else "\n"
    m = m.replace("\r\n", "\n")
    m = re.sub(r'(?m)^scenemodel "models/menu/hzm_hubclock_\w+\.tik".*\n', "", m)
    i0 = m.index('name "%s"' % _scene) if _scene else m.index("Scene3D")
    j = m.index("\nscenecam ", i0)
    m = m[:j] + "\n" + "\n".join(HUBCLK_LINES) + m[j:]
    assert m.count("hzm_hubclock_") == 6, _f
    open(_f, "w", encoding="latin-1", newline="").write(m.replace("\n", mnl))
    print("MP room clock ->", os.path.basename(_f))

# ---- D-N2: the New Game map's hover captions said the tag's own name again; now the action / the unlock rule.  The generator
# (newgame/make_newgame3d.py) makes the same captions; this patches the generated urc in place so the hub chain need not re-run.
ngp = os.path.join(ui, "hzm_newgame3d.urc")
if os.path.exists(ngp):
    g = open(ngp, encoding="latin-1", newline="").read()
    CAP = {"TUNISIA": "CHOOSE DIFFICULTY", "SICILY": "CHOOSE DIFFICULTY", "ITALY": "CHOOSE DIFFICULTY",
           "SICILY - LOCKED": "FINISH TUNISIA TO UNLOCK", "ITALY - LOCKED": "FINISH SICILY TO UNLOCK"}
    n = 0
    for old, new in CAP.items():
        pat = re.compile(r'(name "ngcap\d"\r?\nrect 0 0 8 8\r?\ntitle ")%s(")' % re.escape(old))
        g, k = pat.subn(r"\g<1>%s\g<2>" % new, g)
        n += k
    open(ngp, "w", encoding="latin-1", newline="").write(g)
    print("new game captions:", n, "changed")
# v1.10.67 the New Game attic (atc_bgng1) has the same gable window in view (far left at 21:9): the same outside, before its scenecam
if os.path.exists(_wxj):
    _wl = json.load(open(_wxj))["lines"]
    for _f in [os.path.join(ui, f) for f in sorted(os.listdir(ui)) if f == "hzm_newgame3d.urc" or (f.startswith("hzm_ng3d_") and f.endswith(".urc"))]:
        g = open(_f, encoding="latin-1", newline="").read()
        gnl = "\r\n" if "\r\n" in g else "\n"
        g = g.replace("\r\n", "\n")
        if "atc_bgng1" not in g:
            continue
        g = re.sub(r'(?m)^(?:scenemodel "models/menu/hzm_wx_\w*\.tik"|scenewx "\w+"|scenemodelcvar "hzm_wx_\w+").*\n', "", g)
        g = re.sub(r"(?m)^(scenecam .*)$", lambda mm: "\n".join(_wl) + "\n" + mm.group(1), g, count=1)
        open(_f, "w", encoding="latin-1", newline="").write(g.replace("\n", gnl))
        print("window outside ->", os.path.basename(_f))
print("attic polish: gramophone corner, hotspot #%d (ui_scene_hot %d); flat theme box gated" % (idx, idx))

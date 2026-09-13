#!/usr/bin/env python
"""Generate the COOP FIELD SETTINGS sheet, the HOST RULES sheet and their defaults from ONE table.

WHY THIS EXISTS
[user 2026-09-13] approved redesign of ui/coop_settings.urc: it no longer fit on screen (11 rows on a 30 pitch ran
to y472, under CLOSE at y454, so a click on Hit Markers closed the menu), two float cvars sat on integer-only
CheckBoxes (cg_weaponLag showed UNCHECKED while active; cg_tracerGlow became a dead control after one
uncheck/recheck), and 5 of its rows were host-only settings shown to every player. The fix is a two-column sheet
of player-owned settings plus a new HOST RULES sheet opened from Start Game.

The layout, the DEFAULTS button's cfg, the default tick marks under the sliders and the coop_defaults.cfg seeds all
derive from the same numbers, so they are generated together and cannot drift apart. The prototype and the approved
previews live in the 2026-09-13 session scratchpad (fieldsettings/final_layout.py).

    python docs/tools/gen_menu_fieldsettings.py check   # regenerate in memory, byte-compare, run every gate (exit 1 = problem)
    python docs/tools/gen_menu_fieldsettings.py build   # write the files, then run the gates

WHAT IT WRITES
    hzm-mohaa-coop-mod/ui/coop_settings.urc               menu "coop_settings"  (opened from options_main DOCUMENTS)
    hzm-mohaa-coop-mod/ui/coop_hostrules.urc              menu "coop_hostrules" (opened from coop_start HOST RULES)
    hzm-mohaa-coop-mod/coop_mod/cfg/coop_fielddefaults.cfg  exec'd by the DEFAULTS button
    hzm-mohaa-coop-mod/coop_defaults.cfg                  ONLY the block between the BEGIN/END seed markers

It does NOT write autoexec.cfg or coop_start.urc; `check` verifies both (no sheet cvar may be seta'd in autoexec,
which execs after the saved config - TRAPS T7 - and the HOST RULES opener must exist at its checked rect).

GATES (all fatal)
    byte drift . text fit (live RitualFont metrics) . canvas bounds . paper margins . interactive overlaps .
    a Label declared after a control it covers . unique names . brace/quote balance . ASCII only .
    CLOSE fall-through onto the menu underneath . opener rect vs every coop_start rect . every linked cvar is read
    in the reader file named in the table . every cvar seeded exactly once in coop_defaults.cfg with the table default .
    no sheet cvar seta'd in autoexec.cfg
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
ENG = os.path.join(ROOT, "openmohaa-hzm", "code")
SETTINGS_URC = os.path.join(MOD, "ui", "coop_settings.urc")
HOST_URC = os.path.join(MOD, "ui", "coop_hostrules.urc")
FIELD_CFG = os.path.join(MOD, "coop_mod", "cfg", "coop_fielddefaults.cfg")
DEFAULTS_CFG = os.path.join(MOD, "coop_defaults.cfg")
AUTOEXEC = os.path.join(MOD, "autoexec.cfg")
START_URC = os.path.join(MOD, "ui", "coop_start.urc")
OPTIONS_MAIN = os.path.join(MOD, "ui", "options_main.urc")

# ---------------------------------------------------------------- style tokens (house palette)
PAPER = (0.90, 0.86, 0.74, 1.0)
FOLDER = (0.58, 0.47, 0.29, 1.0)
TAB = (0.64, 0.53, 0.33, 1.0)
TABINK = (0.24, 0.15, 0.06, 1.0)
PLATE = (0.14, 0.10, 0.06, 0.94)       # main.urc reportbug / menuMusicBox house plate
BEIGE = (0.90, 0.84, 0.66, 1.0)
INK = (0.16, 0.09, 0.03, 1.0)
RUST = (0.42, 0.22, 0.06, 1.0)
RULE = (0.42, 0.22, 0.06, 0.70)
MUTED = (0.36, 0.26, 0.15, 1.0)
AMBER = (0.98, 0.78, 0.28, 1.0)
HOSTRED = (0.95, 0.55, 0.30, 1.0)
OFFPLATE = (0.22, 0.17, 0.11, 0.94)
OFFTEXT = (0.62, 0.57, 0.45, 1.0)
LAMP_ON = (0.98, 0.78, 0.28, 1.0)
LAMP_OFF = (0.34, 0.27, 0.17, 1.0)
STRIPE = (0.86, 0.82, 0.69, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
CLEAR = (0.0, 0.0, 0.0, 0.0)

ROW_SHADER = "textures/mohmenu/trans_click"   # ships in the mod; transparent, so the row CheckBox draws nothing
SLIDER_SHADER = "textures/menu/slider"          # retail; coop_postfx.urc slider recipe

# ---------------------------------------------------------------- geometry
PLATE_W, PLATE_H, COLW = 46, 18, 256
SLIDER_X, SLIDER_W, SLIDER_H = 110, 146, 16
ARROW_W, THUMB_W = 15, 10                       # uislider.cpp internals, for the default tick position
T_PITCH, S_PITCH, ROW_H = 24, 34, 20
CANVAS_W, CANVAS_H = 640, 480


def S(t, lo, hi, step, d, cl, cr):
    return dict(type=t, lo=lo, hi=hi, step=step, default=d, capL=cl, capR=cr)


def T(d):
    return dict(default=d)


# ---------------------------------------------------------------- THE TABLE
# (key, kind, label, cvar, spec, reader). reader = the file that reads the cvar; `check` asserts the read is there.
CG = "openmohaa-hzm/code/cgame/"
SETTINGS_SECTIONS = [
    (0, "VISUAL EFFECTS", [
        ("Smoke", "toggle", "Muzzle Smoke", "coop_smokeWhip", T(1), CG + "cg_parsemsg.cpp"),
        ("Tracer", "slider", "Tracer Width", "cg_tracerGlow", S("float", 1, 3, 0.1, 1.8, "STOCK", "THICK"), CG + "cg_parsemsg.cpp"),
        ("Heat", "toggle", "Heat Haze", "r_ppHeatHaze", T(1), "openmohaa-hzm/code/renderergl2/tr_postprocess.c"),
        ("Ragdoll", "toggle", "Ragdoll Bodies", "coop_ragdoll", T(1), CG + "cg_ragdoll.c"),
    ]),
    (0, "HUD & FEEDBACK", [
        ("HitMarker", "toggle", "Hit Markers", "coop_hitMarker", T(1), CG + "cg_drawtools.cpp"),
        ("DmgDir", "toggle", "Damage Direction", "coop_dmgIndicator", T(1), CG + "cg_drawtools.cpp"),
        ("Stamina", "toggle", "Stamina Gauge", "coop_staminaArc", T(1), CG + "cg_drawtools.cpp"),
        # [user 2026-09-13] "Modern Compass": on = the top compass bar (coop), off = the classic round ring
        ("Compass", "toggle", "Modern Compass", "coop_compassBar", T(1), CG + "cg_drawtools.cpp"),
        ("HudFade", "toggle", "Auto-Hide HUD", "coop_hudFade", T(1), CG + "cg_drawtools.cpp"),
        ("HudTime", "slider", "Hide HUD After", "coop_hudFadeTime", S("integer", 2, 15, 1, 5, "2 SEC", "15 SEC"), CG + "cg_drawtools.cpp"),
    ]),
    (1, "CAMERA & WEAPON", [
        ("CamMotion", "slider", "Camera Motion", "coop_camMotion", S("float", 0, 2, 0.1, 1, "STEADY", "STRONG"), CG + "cg_view.c"),
        ("HeadBob", "toggle", "Enhanced Head Bob", "cg_headbob", T(1), CG + "cg_view.c"),
        ("FreeAim", "toggle", "Free Aim", "cg_freeAim", T(1), CG + "cg_view.c"),
        ("Downed1P", "toggle", "Downed View: 1st Person", "cg_dbnoForceFirstPerson", T(0), CG + "cg_view.c"),
        ("Inertia", "slider", "Weapon Inertia", "cg_weaponLag", S("float", 0, 1.5, 0.1, 0.7, "OFF", "HEAVY"), CG + "cg_view.c"),
        ("Lower", "toggle", "Lower Gun: Sprint/Crawl", "cg_sprintLower", T(1), CG + "cg_view.c"),
        ("Feel", "toggle", "Weapon Motion", "coop_weaponFeel", T(1), CG + "cg_view.c"),
        ("Inspect", "toggle", "Idle Weapon Inspect", "coop_idleInspect", T(1), CG + "cg_view.c"),
    ]),
    (1, "SOUND", [
        ("Crack", "toggle", "Near-Miss Cracks", "coop_bulletCrack", T(1), CG + "cg_parsemsg.cpp"),
        ("Distant", "toggle", "Distant Gunfire", "coop_distantFire", T(1), CG + "cg_parsemsg.cpp"),
    ]),
]

# Host-decided settings: one value for the whole server, so they live on the host's own sheet. No DEFAULTS button
# here, so the table default is informational; the seeds already exist in coop_defaults.cfg.
HOST_SECTIONS = [
    (0, "SERVER-WIDE", [
        ("Blood", "toggle", "Blood Trails", "coop_bloodTrail", T(1), "openmohaa-hzm/code/fgame/sentient.cpp"),
        ("Cover", "toggle", "Auto Take-Cover", "coop_coverAuto", T(1), "openmohaa-hzm/code/fgame/player.cpp"),
        ("Tinnitus", "toggle", "Shell Shock Effects", "coop_tinnitus", T(1), "hzm-mohaa-coop-mod/coop_mod/tinnitus.scr"),
        ("XpPopup", "toggle", "XP Gain Popups", "coop_xpKillPopup", T(1), "hzm-mohaa-coop-mod/coop_mod/xp.scr"),
        ("ChalPopup", "toggle", "Pinned Challenge Progress", "coop_chalPopup", T(1), "hzm-mohaa-coop-mod/coop_mod/challenges.scr"),
    ]),
]

# The HOST RULES opener on coop_start.urc (hand-edited file; verified here, not written).
OPENER_NAME, OPENER_RECT, OPENER_CMD = "hostRulesBtn", (490, 96, 142, 22), "pushmenu coop_hostrules"


# ---------------------------------------------------------------- fonts (live metrics; mod @3x RitualFonts)
class Font(object):
    def __init__(self, name):
        t = io.open(os.path.join(MOD, "fonts", name + "@3x.RitualFont"), "rb").read().decode("latin-1")
        self.height = float(re.search(r"height\s+([\d.]+)", t).group(1))
        self.ind = [int(x) for x in re.search(r"indirections\s*\{([^}]*)\}", t).group(1).split()]
        self.locs = [tuple(map(float, m.groups())) for m in re.finditer(
            r"\{\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\}", t[t.find("locations"):])]

    def width(self, s):
        w = 0.0
        for c in s:
            i = self.ind[ord(c)] if ord(c) < len(self.ind) else -1
            if i < 0 or i >= len(self.locs):
                raise ValueError("glyph %r missing from font, in %r" % (c, s))
            w += self.locs[i][2]
        return w


# ---------------------------------------------------------------- widget model
def W(name, kind, rect, **kw):
    d = dict(name=name, kind=kind, rect=tuple(int(v) for v in rect))
    d.update(kw)
    return d


def label(name, rect, bg=CLEAR, border="NONE", **kw):
    return W(name, "Label", rect, bg=bg, border=border, **kw)


def text_label(name, rect, text, font, fg, align, dontlocalize=False, **kw):
    return label(name, rect, title=text, font=font, fg=fg, align=align, dontlocalize=dontlocalize, **kw)


def plate_button(name, rect, text, sound, cmd):
    return W(name, "Button", rect, title=text, fg=BEIGE, bg=PLATE, border="3D_BORDER", font="facfont-20",
             clicksound=sound, stuffcommand=cmd)


def lay_sheet(sections, colx, top, colw):
    """Row positions -> grouped non-interactive widgets + interactive widgets, in declaration groups."""
    rows, heads, bottoms = [], [], {}
    for col, title, items in sections:
        y = bottoms.get(col, top - 8) + 8
        heads.append((col, title, y))
        ry = y + 24
        for i, it in enumerate(items):
            rows.append((col, ry, i) + tuple(it))
            slider = it[1] == "slider"
            bottoms[col] = ry + (32 if slider else ROW_H)
            ry += S_PITCH if slider else T_PITCH
    g = dict(stripes=[], headers=[], labels=[], plates=[], lamps=[], notches=[], captions=[], sliders=[], checkboxes=[])
    for col, y, i, key, kind, text, cvar, spec, reader in rows:
        if i % 2 == 1:
            g["stripes"].append(label("stripe" + key, (colx[col], y - 2, colw, S_PITCH if kind == "slider" else T_PITCH), bg=STRIPE))
    for col, title, y in heads:
        tag = re.sub(r"[^A-Za-z]", "", title.title())
        g["headers"].append(text_label("hdr" + tag, (colx[col], y, colw, 18), title, "facfont-20", RUST, "left"))
        g["headers"].append(label("rule" + tag, (colx[col], y + 19, colw, 1), bg=RULE))
    for col, y, i, key, kind, text, cvar, spec, reader in rows:
        x = colx[col]
        if kind == "toggle":
            px = x + colw - PLATE_W
            g["labels"].append(text_label("lbl" + key, (x + 8, y, colw - PLATE_W - 14, ROW_H), text, "facfont-20", INK, "left"))
            g["plates"].append(text_label("on" + key, (px, y + 1, PLATE_W, PLATE_H), "ON", "facfont-20", AMBER, "center",
                                          dontlocalize=True, bg=PLATE, border="3D_BORDER", enabledcvar=cvar))
            g["plates"].append(text_label("off" + key, (px, y + 1, PLATE_W, PLATE_H), "OFF", "facfont-20", OFFTEXT, "center",
                                          dontlocalize=True, bg=OFFPLATE, border="INDENT_BORDER", enabledcvar="!" + cvar))
            g["lamps"].append(label("lampOn" + key, (px + 4, y + 6, 4, 8), bg=LAMP_ON, enabledcvar=cvar))
            g["lamps"].append(label("lampOff" + key, (px + 4, y + 6, 4, 8), bg=LAMP_OFF, enabledcvar="!" + cvar))
            g["checkboxes"].append(W("cb" + key, "CheckBox", (x, y, colw, ROW_H), fg=WHITE, bg=CLEAR, border="NONE", linkcvar=cvar))
        else:
            g["labels"].append(text_label("lbl" + key, (x + 8, y, SLIDER_X - 12, ROW_H), text, "facfont-20", INK, "left"))
            pos = (spec["default"] - spec["lo"]) / float(spec["hi"] - spec["lo"])
            cx = x + SLIDER_X + ARROW_W + THUMB_W / 2.0 + (SLIDER_W - 2 * ARROW_W - THUMB_W) * pos
            g["notches"].append(label("notch" + key, (round(cx - 1), y - 1, 2, 21), bg=RUST))
            g["captions"].append(text_label("capL" + key, (x + SLIDER_X, y + 20, 70, 12), spec["capL"], "verdana-12", MUTED, "left", dontlocalize=True))
            g["captions"].append(text_label("capR" + key, (x + SLIDER_X + SLIDER_W - 70, y + 20, 70, 12), spec["capR"], "verdana-12", MUTED, "right", dontlocalize=True))
            g["sliders"].append(W("sl" + key, "Slider", (x + SLIDER_X, y + 2, SLIDER_W, SLIDER_H), fg=WHITE, bg=CLEAR, border="NONE",
                                  linkcvar=cvar, slidertype=spec["type"], setrange=(spec["lo"], spec["hi"]), stepsize=spec["step"]))
    return rows, g


def ordered(chrome, g, footer, buttons):
    # Declaration order IS draw order and hit-test priority (later = on top): chrome, stripes, headers/rules, labels,
    # plates, lamps, notches, captions, footer labels, Sliders, CheckBoxes, Buttons.
    out = list(chrome)
    for k in ("stripes", "headers", "labels", "plates", "lamps", "notches", "captions"):
        out += g[k]
    out += footer + g["sliders"] + g["checkboxes"] + buttons
    return out


def sheet_settings():
    chrome = [
        label("folder", (20, 26, 600, 432), bg=FOLDER, border="3D_BORDER"),
        text_label("foldertab", (40, 6, 140, 24), "COOP OPTIONS", "facfont-20", TABINK, "center", bg=TAB, border="3D_BORDER"),
        label("paper", (32, 38, 576, 408), bg=PAPER, border="3D_BORDER"),
        label("titlePlate", (44, 46, 552, 26), bg=PLATE, border="3D_BORDER"),
        text_label("titleText", (56, 49, 240, 20), "FIELD SETTINGS", "facfont-20", BEIGE, "left"),
        text_label("scopeBadge", (344, 52, 240, 14), "YOUR GAME - ANY SERVER", "verdana-12", AMBER, "right", dontlocalize=True),
    ]
    rows, g = lay_sheet(SETTINGS_SECTIONS, {0: 52, 1: 332}, 80, COLW)
    foot = 406
    footer = [
        label("footRule", (44, foot - 8, 552, 1), bg=RULE),
        text_label("footHint", (164, foot + 5, 320, 14), "Applies instantly. Host rules: Start Game.", "verdana-12", MUTED, "center"),
    ]
    buttons = [
        plate_button("defaultsBtn", (44, foot, 112, 24), "DEFAULTS", "sound/menu/apply.wav", "exec coop_mod/cfg/coop_fielddefaults.cfg"),
        plate_button("closeBtn", (496, foot, 100, 24), "CLOSE", "sound/menu/back.wav", "popmenu 0"),
    ]
    return rows, ordered(chrome, g, footer, buttons), (32, 38, 608, 446)


def sheet_host():
    chrome = [
        label("folder", (104, 96, 528, 272), bg=FOLDER, border="3D_BORDER"),
        text_label("foldertab", (124, 76, 140, 24), "HOST RULES", "facfont-20", TABINK, "center", bg=TAB, border="3D_BORDER"),
        label("paper", (116, 108, 504, 250), bg=PAPER, border="3D_BORDER"),
        label("titlePlate", (128, 118, 480, 26), bg=PLATE, border="3D_BORDER"),
        text_label("titleText", (140, 121, 220, 20), "WHEN YOU HOST", "facfont-20", BEIGE, "left"),
        text_label("scopeBadge", (436, 124, 160, 14), "HOST ONLY", "verdana-12", HOSTRED, "right", dontlocalize=True),
        text_label("scopeNote", (136, 150, 464, 14), "Applies to everyone on your server. Ignored when you join someone else's.",
                   "verdana-12", MUTED, "left"),
    ]
    rows, g = lay_sheet(HOST_SECTIONS, {0: 128}, 172, 480)
    footer = [label("footRule", (128, 318, 480, 1), bg=RULE)]
    buttons = [plate_button("closeBtn", (530, 326, 78, 24), "CLOSE", "sound/menu/back.wav", "popmenu 0")]
    return rows, ordered(chrome, g, footer, buttons), (116, 108, 620, 358)


# ---------------------------------------------------------------- emit
def c4(c):
    return "%.2f %.2f %.2f %.2f" % c


def num(v):
    return "%g" % v


def emit_widget(w):
    L = ["resource", w["kind"], "{", '\tname "%s"' % w["name"]]
    if w.get("dontlocalize"):
        L.append("\tdontlocalize")
    if w.get("title"):
        L.append('\ttitle "%s"' % w["title"])
    L.append("\trect %d %d %d %d" % w["rect"])
    L.append("\tfgcolor " + c4(w.get("fg", WHITE)))
    L.append("\tbgcolor " + c4(w["bg"]))
    L.append('\tborderstyle "%s"' % w["border"])
    if w.get("font"):
        L.append('\tfont "%s"' % w["font"])
    if w["kind"] == "Label" and w.get("title"):
        L.append("\ttextalign " + w["align"])
    if w.get("enabledcvar"):
        L.append('\tenabledcvar "%s"' % w["enabledcvar"])
    if w["kind"] == "Slider":
        L += ['\tshader "%s"' % SLIDER_SHADER, '\tlinkcvar "%s"' % w["linkcvar"], "\tslidertype " + w["slidertype"],
              "\tsetrange %s %s" % (num(w["setrange"][0]), num(w["setrange"][1])), "\tstepsize " + num(w["stepsize"])]
    elif w["kind"] == "CheckBox":
        L += ['\tlinkcvar "%s"' % w["linkcvar"], '\tchecked_shader "%s"' % ROW_SHADER, '\tunchecked_shader "%s"' % ROW_SHADER]
    elif w["kind"] == "Button":
        L += ['\tclicksound "%s"' % w["clicksound"], '\tstuffcommand "%s"' % w["stuffcommand"]]
    L.append("}")
    return L


HEADER_COMMON = """\
// GENERATED by docs/tools/gen_menu_fieldsettings.py - DO NOT HAND-EDIT. Change the table there, run `build`,
// and `check` must pass (fit, overlap, fall-through, seeds, readers, byte drift).
//
// TOGGLE ROW, built only from proven parts: an ON plate + lit lamp gated `enabledcvar "<cvar>"`, an OFF plate +
// unlit lamp gated `enabledcvar "!<cvar>"` (the '!' form: uiwidget.cpp UIWidget::isEnabled), and a whole-row
// CheckBox declared after them with a transparent shader (textures/mohmenu/trans_click), so the row is the click
// target and draws nothing. Gated-off widgets are click-transparent (HZM FindResponder). Declaration order is draw
// order and hit priority: chrome, stripes, headers, labels, plates, lamps, ticks, captions, footer, Sliders,
// CheckBoxes, Buttons. Every control is linkcvar-bound (live; seta seeds in coop_defaults.cfg make it persist).
// FALLBACK if the row toggle ever misbehaves: set that CheckBox's shaders to textures/menu/checkbox_checked /
// checkbox_unchecked, shrink its rect to the plate, delete the on/off/lamp Labels.
// Canvas stays 640x480: a widget outside the declared canvas draws nothing (bug-1365). Each resource field is on its
// own line - the URC parser silently drops single-line blocks. Colour fills, never raw-image shaders, for panels
// (bug-menu-shader-label-invisible)."""


def emit_menu(name, intro, widgets):
    out = intro.splitlines() + HEADER_COMMON.splitlines() + [
        'menu "%s" 640 480 NONE 1' % name, "borderstyle NONE", "bgcolor 0 0 0 0", "align centerx centery",
        "virtualres 1", "fullscreen 0", "", "direction from_top 0", ""]
    for w in widgets:
        out += emit_widget(w)
    out.append("end.")
    return "\n".join(out) + "\n"


SETTINGS_INTRO = """\
// HZM coop - COOP OPTIONS / FIELD SETTINGS: an open manila folder holding a printed settings sheet. Opened from the
// Options workbench by clicking the desk DOCUMENTS (ui/options_main.urc). Only settings read on the player's OWN
// machine (cgame, client, renderer) live here - they apply on any server. Host-decided settings are on
// ui/coop_hostrules.urc, opened from Start Game. [user 2026-09-13] approved two-column redesign."""

HOST_INTRO = """\
// HZM coop - HOST RULES: settings one value of which applies to the whole server (game.dll and server scripts read
// them), so they are the HOST's choice and are ignored when you join someone else's game. Pushed from
// ui/coop_start.urc (hostRulesBtn). Offset right on purpose: its CLOSE sits over the one empty pocket of coop_start,
// so a double-click cannot fall through onto a map tile. [user 2026-09-13]"""


def sheet_cvars(sections):
    return [(it[3], it[1], it[4]) for _c, _t, items in sections for it in items]


def emit_fielddefaults():
    L = [
        "// HZM coop - FIELD SETTINGS SHIPPING DEFAULTS.",
        "// GENERATED by docs/tools/gen_menu_fieldsettings.py - DO NOT HAND-EDIT (the table there is the source).",
        "// The DEFAULTS button in ui/coop_settings.urc execs this, the way coop_postfx.urc execs coop_fxdefaults.cfg.",
        "// The same values are the coop_defaults.cfg seeds (a fresh profile starts here) and the rust tick marks under",
        "// the sliders, so the three cannot disagree. Host rules (ui/coop_hostrules.urc) are not reset here.",
    ]
    for cvar, kind, spec in sheet_cvars(SETTINGS_SECTIONS):
        L.append("seta %s %s" % (cvar, num(spec["default"])))
    L += ["", 'print "Field settings restored to defaults.\\n"']
    return "\n".join(L) + "\n"


SEED_BEGIN = "// >>> BEGIN gen_menu_fieldsettings.py seeds - generated, do not hand-edit (python docs/tools/gen_menu_fieldsettings.py build)"
SEED_END = "// <<< END gen_menu_fieldsettings.py seeds"
SEED_ANCHOR = "seta coop_xpKillPopup 1    // XP kill-popup toggle (Coop Settings) - archived so the menu choice persists\n"
SEED_NOTE = [
    "// FIELD SETTINGS sheet cvars that had no seed here. Exact values, so a cold-profile ESC cannot blank a cgame",
    "// cvar the menu opened before cgame registered it (uimenu.cpp RestoreCVars). coop_hudFade/coop_hudFadeTime,",
    "// cg_freeAim, coop_bulletCrack and coop_distantFire moved here from autoexec.cfg, which execs AFTER the saved",
    "// config and re-forced them every launch (TRAPS T7).",
]

SETA_RE = re.compile(r"^[ \t]*seta[ \t]+\"?([A-Za-z0-9_]+)\"?[ \t]+\"?([^\s\"]*)", re.M)


def strip_block(text):
    if SEED_BEGIN not in text:
        return text
    assert text.count(SEED_BEGIN) == 1 and text.count(SEED_END) == 1, "seed markers must appear exactly once"
    a = text.index(SEED_BEGIN)
    b = text.index(SEED_END) + len(SEED_END) + 1
    return text[:a] + text[b:]


def splice_defaults(text):
    base = strip_block(text)
    seeded = set(m.group(1) for m in SETA_RE.finditer(base))
    lines = [SEED_BEGIN] + SEED_NOTE
    for cvar, kind, spec in sheet_cvars(SETTINGS_SECTIONS):
        if cvar not in seeded:
            lines.append("seta %s %s" % (cvar, num(spec["default"])))
    lines.append(SEED_END)
    block = "\n".join(lines) + "\n"
    if SEED_BEGIN in text:
        a = text.index(SEED_BEGIN)
        b = text.index(SEED_END) + len(SEED_END) + 1
        return text[:a] + block + text[b:]
    assert text.count(SEED_ANCHOR) == 1, "coop_defaults.cfg seed anchor found %d times" % text.count(SEED_ANCHOR)
    i = text.index(SEED_ANCHOR) + len(SEED_ANCHOR)
    return text[:i] + block + text[i:]


# ---------------------------------------------------------------- read existing files (binary: TRAPS T2)
def rd(p):
    return io.open(p, "rb").read().decode("latin-1")


def strip_comment(ln):
    """Drop a // comment that is not inside a quoted string."""
    q = False
    for i, ch in enumerate(ln):
        if ch == '"':
            q = not q
        elif not q and ln.startswith("//", i):
            return ln[:i]
    return ln


def urc_resources(path):
    """[(kind, name, rect, stuffcommand)] of every live resource, following include lines."""
    out = []
    lines = [strip_comment(ln) for ln in rd(path).replace("\r\n", "\n").split("\n")]
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        m = re.match(r'include\s+"([^"]+)"', s)
        if m:
            out += urc_resources(os.path.join(MOD, m.group(1).replace("/", os.sep)))
        if s == "resource":
            j = i + 1
            while not lines[j].strip():
                j += 1
            kind = lines[j].strip()
            k = j + 1
            name, rect, cmd = "", None, ""
            while lines[k].strip() != "}":
                t = lines[k].strip()
                mm = re.match(r'name\s+"([^"]*)"', t)
                if mm:
                    name = mm.group(1)
                mm = re.match(r'rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)', t)
                if mm:
                    rect = tuple(int(v) for v in mm.groups())
                mm = re.match(r'stuffcommand\s+"(.*)"', t)
                if mm:
                    cmd = mm.group(1)
                k += 1
            out.append((kind, name, rect, cmd))
            i = k
        i += 1
    return out


INTERACTIVE = ("Button", "CheckBox", "Slider", "Field", "PulldownMenuContainer", "List", "ListBox", "ListCtrl")


def box(r):
    return (r[0], r[1], r[0] + r[2], r[1] + r[3])


def ov(a, b):
    a, b = box(a), box(b)
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


# ---------------------------------------------------------------- gates
def gate_sheet(tag, widgets, paper, fonts, problems):
    names = [w["name"] for w in widgets]
    dup = sorted(set(n for n in names if names.count(n) > 1))
    if dup:
        problems.append("%s duplicate widget names: %s" % (tag, dup))
    for w in widgets:
        x0, y0, x1, y1 = box(w["rect"])
        if x0 < 0 or y0 < 0 or x1 > CANVAS_W or y1 > CANVAS_H:
            problems.append("%s outside the 640x480 canvas: %s %s" % (tag, w["name"], w["rect"]))
        if w.get("title"):
            f = fonts[w["font"]]
            tw = f.width(w["title"])
            pad = 0 if w["bg"][3] == 0 else 6
            if tw + pad > w["rect"][2]:
                problems.append("%s text too wide: %s %.0f > %d" % (tag, w["name"], tw + pad, w["rect"][2]))
            if f.height > w["rect"][3] + 0.5:
                problems.append("%s text too tall: %s %.1f > %d" % (tag, w["name"], f.height, w["rect"][3]))
        if w["name"] not in ("folder", "foldertab", "paper"):
            if x0 < paper[0] + 6 or y0 < paper[1] + 6 or x1 > paper[2] - 6 or y1 > paper[3] - 6:
                problems.append("%s within 6 of the paper edge: %s %s" % (tag, w["name"], w["rect"]))
    inter = [w for w in widgets if w["kind"] in INTERACTIVE]
    for i, a in enumerate(inter):
        for b in inter[i + 1:]:
            if ov(a["rect"], b["rect"]):
                problems.append("%s interactive overlap: %s / %s" % (tag, a["name"], b["name"]))
    for i, a in enumerate(widgets):
        if a["kind"] in INTERACTIVE:
            for b in widgets[i + 1:]:
                if b["kind"] == "Label" and ov(a["rect"], b["rect"]):
                    problems.append("%s Label declared after a control it covers: %s over %s" % (tag, b["name"], a["name"]))
    return inter


def gate_text(tag, text, problems):
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        problems.append("%s: non-ASCII byte" % tag)
    if text.startswith("\ufeff") or "\r" in text:
        problems.append("%s: BOM or CR in generated text" % tag)
    depth = 0
    for n, ln in enumerate(text.split("\n"), 1):
        code = ln.split("//")[0] if not ln.lstrip().startswith("//") else ""
        if ln.lstrip().startswith("//"):
            continue
        if ln.count('"') % 2:
            problems.append("%s:%d odd quote count" % (tag, n))
        depth += code.count("{") - code.count("}")
        if depth < 0 or depth > 1:
            problems.append("%s:%d brace depth %d" % (tag, n, depth))
            depth = max(0, min(1, depth))
    if depth != 0:
        problems.append("%s: unbalanced braces at EOF (%d)" % (tag, depth))


def gate_readers(problems):
    for sections in (SETTINGS_SECTIONS, HOST_SECTIONS):
        for _c, _t, items in sections:
            for key, kind, text, cvar, spec, reader in items:
                p = os.path.join(ROOT, reader.replace("/", os.sep))
                if not os.path.exists(p):
                    problems.append("reader file missing for %s: %s" % (cvar, reader))
                    continue
                src = rd(p)
                if p.endswith(".scr"):
                    ok = re.search(r'getcvar\s*\(?\s*"%s"' % re.escape(cvar), src)
                else:
                    ok = re.search(r'Cvar_Get\s*\(\s*"%s"' % re.escape(cvar), src)
                if not ok:
                    problems.append("cvar %s is not read in %s (a setting is a promise)" % (cvar, reader))


def gate_cfgs(defaults_text, problems):
    seeds = {}
    for m in SETA_RE.finditer(defaults_text):
        seeds.setdefault(m.group(1), []).append(m.group(2))
    for cvar, kind, spec in sheet_cvars(SETTINGS_SECTIONS):
        got = seeds.get(cvar, [])
        if len(got) != 1:
            problems.append("coop_defaults.cfg seeds %s %d times (want exactly 1)" % (cvar, len(got)))
        elif abs(float(got[0]) - float(spec["default"])) > 1e-9:
            problems.append("coop_defaults.cfg seeds %s %s, table default is %s" % (cvar, got[0], num(spec["default"])))
    for cvar, kind, spec in sheet_cvars(HOST_SECTIONS):
        if len(seeds.get(cvar, [])) != 1:
            problems.append("coop_defaults.cfg seeds host cvar %s %d times (want exactly 1)" % (cvar, len(seeds.get(cvar, []))))
    auto = rd(AUTOEXEC)
    for cvar, kind, spec in sheet_cvars(SETTINGS_SECTIONS) + sheet_cvars(HOST_SECTIONS):
        if re.search(r"^[ \t]*seta?[ \t]+\"?%s\"?[ \t]" % re.escape(cvar), auto, re.M):
            problems.append("autoexec.cfg still sets %s - it execs after the saved config and clobbers the menu (TRAPS T7)" % cvar)


def gate_fallthrough(settings, host, problems, notes):
    # A CLOSE click pops the sheet; the second click of a double-click lands on the menu underneath.
    om = [r for r in urc_resources(OPTIONS_MAIN) if r[0] in INTERACTIVE and r[2]]
    close1 = [w for w in settings if w["name"] == "closeBtn"][0]
    for kind, name, rect, cmd in om:
        if ov(close1["rect"], rect):
            problems.append("coop_settings CLOSE falls through onto options_main %s %s" % (name, rect))
    st = urc_resources(START_URC)
    close2 = [w for w in host if w["name"] == "closeBtn"][0]
    for kind, name, rect, cmd in st:
        if kind in INTERACTIVE and rect and ov(close2["rect"], rect):
            problems.append("coop_hostrules CLOSE falls through onto coop_start %s %s %s" % (kind, name, rect))
    openers = [r for r in st if r[1] == OPENER_NAME]
    if len(openers) != 1:
        problems.append("coop_start.urc has %d %s buttons (want 1)" % (len(openers), OPENER_NAME))
    else:
        kind, name, rect, cmd = openers[0]
        if kind != "Button" or rect != OPENER_RECT or cmd != OPENER_CMD:
            problems.append("coop_start %s is %s %s %r, want Button %s %r" % (OPENER_NAME, kind, rect, cmd, OPENER_RECT, OPENER_CMD))
        for k2, n2, r2, c2 in st:
            if n2 != OPENER_NAME and r2 and ov(rect, r2):
                problems.append("coop_start %s overlaps %s %s %s" % (OPENER_NAME, k2, n2, r2))
        # advisory only: the opener's own second click landing on the sheet it opens
        for w in host:
            if w["kind"] in INTERACTIVE and ov(rect, w["rect"]):
                notes.append("opener double-click reaches coop_hostrules %s" % w["name"])
    docs = [r for r in om if "pushmenu coop_settings" in r[3]]
    for kind, name, rect, cmd in docs:
        for w in settings:
            if w["kind"] in INTERACTIVE and ov(rect, w["rect"]):
                a, b = box(rect), box(w["rect"])
                notes.append("options_main %s %s double-click can reach coop_settings %s %s (overlap %dx%d)" % (
                    name, rect, w["name"], w["rect"], min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])))


# ---------------------------------------------------------------- modes
def render_all():
    rows1, settings, paper1 = sheet_settings()
    rows2, host, paper2 = sheet_host()
    files = {
        SETTINGS_URC: emit_menu("coop_settings", SETTINGS_INTRO, settings),
        HOST_URC: emit_menu("coop_hostrules", HOST_INTRO, host),
        FIELD_CFG: emit_fielddefaults(),
        DEFAULTS_CFG: splice_defaults(rd(DEFAULTS_CFG)),
    }
    return files, (settings, paper1), (host, paper2)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode not in ("build", "check"):
        print(__doc__)
        return 2
    files, (settings, paper1), (host, paper2) = render_all()

    if mode == "build":
        for p, text in sorted(files.items()):
            data = text.encode("ascii")
            io.open(p, "wb").write(data)
            print("wrote %s (%d bytes, LF)" % (os.path.relpath(p, ROOT), len(data)))

    problems, notes = [], []
    drift = []
    for p, text in sorted(files.items()):
        rel = os.path.relpath(p, ROOT)
        if not os.path.exists(p):
            drift.append(rel + " (missing)")
        elif rd(p) != text:
            drift.append(rel)
    for rel in drift:
        problems.append("DRIFT: %s differs from the table - run build" % rel)

    fonts = {"facfont-20": Font("facfont-20"), "verdana-12": Font("verdana-12")}
    inter1 = gate_sheet("coop_settings", settings, paper1, fonts, problems)
    inter2 = gate_sheet("coop_hostrules", host, paper2, fonts, problems)
    for p in (SETTINGS_URC, HOST_URC, FIELD_CFG):
        gate_text(os.path.relpath(p, ROOT), files[p], problems)
    gate_readers(problems)
    gate_cfgs(files[DEFAULTS_CFG], problems)
    gate_fallthrough(settings, host, problems, notes)

    n1 = sum(len(i) for _c, _t, i in SETTINGS_SECTIONS)
    n2 = sum(len(i) for _c, _t, i in HOST_SECTIONS)
    print("coop_settings : %d widgets, %d interactive, %d rows" % (len(settings), len(inter1), n1))
    print("coop_hostrules: %d widgets, %d interactive, %d rows" % (len(host), len(inter2), n2))
    print("byte-identical: %d of %d files" % (len(files) - len(drift), len(files)))
    for n in notes:
        print("  advisory: " + n)
    if problems:
        print("PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  " + p)
        return 1
    print("  -> OK: no drift, fit/overlap/fall-through/seed/reader gates all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())

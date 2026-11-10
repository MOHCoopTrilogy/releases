"""Writes ui/coop_byodisc.urc (v1.10.68 YOUR OWN DISCS sheet). Run once; the .urc is the committed artifact."""
import sys
out = sys.argv[1]
PAPER = "0.90 0.86 0.74 1.00"; FOLDER = "0.58 0.47 0.29 1.00"; TAB = "0.64 0.53 0.33 1.00"; TABINK = "0.24 0.15 0.06 1.00"
PLATE = "0.14 0.10 0.06 0.94"; BEIGE = "0.90 0.84 0.66 1.00"; INK = "0.16 0.09 0.03 1.00"; RULE = "0.42 0.22 0.06 0.70"
MUTED = "0.36 0.26 0.15 1.00"; RUST = "0.55 0.22 0.06 1.00"; LAMP_ON = "0.98 0.78 0.28 1.00"; LAMP_OFF = "0.34 0.27 0.17 1.00"
CLEAR = "0.00 0.00 0.00 0.00"; WHITE = "1.00 1.00 1.00 1.00"
L = []


def W(kind, name, rect, **kw):
    L.extend(["resource", kind, "{", 'name "%s"' % name, "rect %d %d %d %d" % rect])
    for k in ("title", "fgcolor", "bgcolor", "borderstyle", "font", "textalign", "linkcvar", "enabledcvar", "clicksound",
              "stuffcommand", "hovershader"):
        if k in kw and kw[k] is not None:
            v = kw[k]
            L.append('%s "%s"' % (k, v) if k in ("title", "borderstyle", "font", "linkcvar", "enabledcvar", "clicksound",
                                                  "stuffcommand", "hovershader") else "%s %s" % (k, v))
    L.append("}")


def lab(name, rect, bg, border="NONE", **kw):
    W("Label", name, rect, fgcolor=WHITE, bgcolor=bg, borderstyle=border, **kw)


def txt(name, rect, t, font="verdana-12", fg=INK, align="left", **kw):
    W("Label", name, rect, title=t, fgcolor=fg, bgcolor=CLEAR, borderstyle="NONE", font=font, textalign=align, **kw)


def btn(name, rect, t, cmd, sound="sound/menu/apply.wav", **kw):
    W("Button", name, rect, title=t, fgcolor=BEIGE, bgcolor=PLATE, borderstyle="3D_BORDER", font="facfont-20", clicksound=sound,
      stuffcommand=cmd, **kw)


hdr = [
    "// HZM coop - YOUR OWN DISCS (v1.10.68). Opened from FIELD SETTINGS (ui/coop_settings.urc, OWN DISCS button).",
    "// Medal of Honor: Frontline / European Assault missions exist ONLY on a PC that converted its own disc: ADD runs the",
    "// engine command coop_byoconvert, which opens the converter window (byo_convert.ps1 + hzmconv beside openmohaa.exe).",
    "// The converter writes zzzz_coop_<game>_<level>.pk3 into maintt; the marker cfg inside it (fl/have_1_1.cfg) is exec'd by",
    "// autoexec.cfg and raises coop_flHave_1_1, which every gate here and in the co-op map select reads. Nothing of the",
    "// disc ships with the mod. coop_byoBusy / coop_byoStatus are engine cvars (cl_bugreport.cpp CL_ByoConvert_f).",
    "// CLOSE sits on FIELD SETTINGS' footer hint (348 406 140 24, a label): a double-click falls through onto nothing. The",
    "// OWN DISCS button that opened this sheet (196 406 140 24) lands on paper here. Each resource field on its own line.",
    "// Written by docs/proposals/byo68_2026-11-09/gen_byodisc.py.",
    'menu "coop_byodisc" 640 480 NONE 1', "borderstyle NONE", "bgcolor 0 0 0 0", "align centerx centery", "virtualres 1",
    "fullscreen 0", 'escapecommand "popmenu 0"', "", "direction from_top 0", ""]

lab("folder", (40, 46, 560, 398), FOLDER, "3D_BORDER")
W("Label", "foldertab", (60, 26, 220, 24), title="YOUR OWN DISCS", fgcolor=TABINK, bgcolor=TAB, borderstyle="3D_BORDER",
  font="facfont-20", textalign="center")
lab("paper", (52, 58, 536, 378), PAPER, "3D_BORDER")
lab("titlePlate", (64, 68, 512, 26), PLATE, "3D_BORDER")
txt("titleText", (76, 71, 480, 20), "MISSIONS FROM YOUR OWN DISC", "facfont-20", BEIGE)
txt("body1", (76, 104, 488, 15), "Own Medal of Honor: Frontline or European Assault? Point the converter at your")
txt("body2", (76, 119, 488, 15), "disc image (Xbox, USA: an .iso, or a .zip holding one) and its mission is converted")
txt("body3", (76, 134, 488, 15), "on this PC into a co-op mission. Nothing is downloaded; nothing leaves your PC.")

for i, (key, game, title, sub, cvar) in enumerate((
        ("Fl", "frontline", "FRONTLINE", "SEALED ORDERS - St. Mathieu, France, 1944", "coop_flHave_1_1"),
        ("Ea", "ea", "EUROPEAN ASSAULT", "THEIR DYING BREATH - Stalingrad, 1943", "coop_eaHave_1_11"))):
    y = 162 + i * 70
    lab("row%s" % key, (64, y, 512, 58), "0.84 0.78 0.62 1.00", "NONE")
    txt("title%s" % key, (76, y + 6, 300, 20), title, "facfont-20", RUST)
    txt("sub%s" % key, (76, y + 30, 300, 15), sub, "verdana-12", INK)
    lab("lampOn%s" % key, (304, y + 12, 8, 8), LAMP_ON, enabledcvar=cvar)
    txt("stOn%s" % key, (316, y + 8, 110, 15), "ADDED", "verdana-12", INK, enabledcvar=cvar)
    lab("lampOff%s" % key, (304, y + 12, 8, 8), LAMP_OFF, enabledcvar="!" + cvar)
    txt("stOff%s" % key, (316, y + 8, 110, 15), "NOT ADDED", "verdana-12", MUTED, enabledcvar="!" + cvar)
    btn("add%s" % key, (432, y + 15, 132, 28), "ADD", "coop_byoconvert " + game, enabledcvar="!%s !coop_byoBusy" % cvar)
    btn("redo%s" % key, (432, y + 15, 132, 28), "RE-CONVERT", "coop_byoconvert " + game, enabledcvar="%s !coop_byoBusy" % cvar)
    txt("busy%s" % key, (432, y + 22, 132, 15), "converting...", "verdana-12", RUST, "center", enabledcvar="coop_byoBusy")

lab("statusRule", (64, 306, 512, 1), RULE)
W("Label", "status", (64, 312, 512, 30), title="", fgcolor=RUST, bgcolor=CLEAR, borderstyle="NONE", font="verdana-12",
  textalign="left", linkcvar="coop_byoStatus")
txt("note1", (64, 350, 512, 15), "After adding a mission, restart the game: its tile unlocks (Co-op: FRONTLINE / EUROPEAN", "verdana-12", MUTED)
txt("note2", (64, 365, 512, 15), "ASSAULT) and the campaigns include it. To remove it, delete its zzzz_coop_ pak in maintt.", "verdana-12", MUTED)
lab("footRule", (64, 396, 512, 1), RULE)
btn("closeBtn", (348, 406, 140, 24), "CLOSE", "popmenu 0", sound="sound/menu/back.wav")
L.append("end.")
open(out, "w", encoding="ascii", newline="\r\n").write("\n".join(hdr + L) + "\n")
print("wrote", out, sum(1 for x in L if x == "resource"), "widgets")

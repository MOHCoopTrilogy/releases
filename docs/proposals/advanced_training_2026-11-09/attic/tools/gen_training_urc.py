"""gen_training_urc.py <mod ui dir> - writes ui/coop_training.urc, the TRAINING sheet the attic's practice target opens.  [advtrain 2026-11-10]

Two cards on the field-office paper (the OWN DISCS sheet's look, ui/coop_byodisc.urc - folder, tab, paper, title plate, the
dark ADD-style buttons, CLOSE on the footer): BASIC TRAINING (map training) and ADVANCED TRAINING (m4l0 with the course on).
Each card: its co-op tile art (textures/mohmenu/hzmtile/training_c, .../m4l0at_c - the co-op map select's own tiles), the
caption, the description, and BEGIN. The whole card is a button too (paper glow on hover).
Launch = what the co-op map select's tiles 1 / 2 set (ui/coop_start/m0.cfg) + coop_mod/cfg/mission_start.cfg (the Apply path: pre-mission lobby, then the map; listen host,
ui_startdmmap 2). coop_advTraining is `set`, never `seta` (TRAPS T7: an archived mode flag is a latch). ESC / BACK: popmenu 0
(the attic flies home as after every other prop). Every resource field on its own line; CRLF like the rest of ui/.
"""
import os, re, sys

ui = sys.argv[1]
BASIC = "set ui_dmmap training; set coop_advTraining 0; exec coop_mod/cfg/mission_start.cfg"
ADV = "set ui_dmmap m4l0; set coop_advTraining 1; exec coop_mod/cfg/mission_start.cfg"
DARK, PAPER, ROW, INKC, RUST, MUTED = "0.14 0.10 0.06 0.94", "0.90 0.86 0.74 1.00", "0.84 0.78 0.62 1.00", "0.16 0.09 0.03 1.00", \
    "0.55 0.22 0.06 1.00", "0.36 0.26 0.15 1.00"
CLEAR = "0.00 0.00 0.00 0.00"
R = []


def res(kind, **f):
    lines = ["resource", kind, "{"]
    for k, v in f.items():
        k = k.rstrip("_")
        if v is True:
            lines.append(k)
        else:
            lines.append('%s %s' % (k, v))
    lines.append("}")
    R.append("\n".join(lines))


def q(s):
    assert '"' not in s and ";" not in s or s.startswith("set "), s
    return '"%s"' % s


def label(name, rect, title=None, fg="1.00 1.00 1.00 1.00", bg=CLEAR, border="NONE", font=None, align=None, shader=None):
    f = dict(name=q(name), rect=rect)
    if title is not None:
        f["title"] = q(title)
    f["fgcolor"] = fg
    f["bgcolor"] = bg
    f["borderstyle"] = q(border)
    if shader:
        f["shader"] = q(shader)
    if font:
        f["font"] = q(font)
    if align:
        f["textalign"] = align
    res("Label", **f)


label("folder", "40 46 560 398", bg="0.58 0.47 0.29 1.00", border="3D_BORDER")
label("foldertab", "60 26 220 24", "TRAINING", fg="0.24 0.15 0.06 1.00", bg="0.64 0.53 0.33 1.00", border="3D_BORDER",
      font="facfont-20", align="center")
label("paper", "52 58 536 378", bg=PAPER, border="3D_BORDER")
label("titlePlate", "64 68 512 26", bg=DARK, border="3D_BORDER")
label("titleText", "76 71 480 20", "CHOOSE YOUR COURSE", fg="0.90 0.84 0.66 1.00", font="facfont-20", align="left")
label("body1", "76 100 488 15", "Both courses start a co-op game on this PC: your squad can join you on the range.", fg=INKC,
      font="verdana-12", align="left")

CARDS = (("Basic", 76, "Basic Training", ("The retail course: move, shoot,", "grenades, the MG42."), "textures/mohmenu/hzmtile/training_c", BASIC),
         ("Adv", 328, "Advanced Training", ("Every coop skill, one field:", "cover, medkits, DBNO, sandbags,", "supply drop, bombing run."),
          "textures/mohmenu/hzmtile/m4l0at_c", ADV))
for key, x, cap, desc, art, cmd in CARDS:
    # [trainfix 2026-11-10, v1.10.72 user report: the card pictures vanished on hover] the card's paper is a LABEL, and the
    # whole-card click target is a fully TRANSPARENT button with no hover shader. Declaring the button first does not keep
    # it underneath: UIWindowManager activates a hovered/clicked control with BringToFrontPropogated() (uilib/uiwinman.cpp
    # ~429), so the active button is drawn LAST - its opaque paper bgcolor + mpui_glow_paper covered the art, caption and
    # text. A transparent button can come to the front and hide nothing.
    label("cardBg" + key, "%d 122 236 258" % x, bg=ROW)
    res("Button", name=q("card" + key), rect="%d 122 236 258" % x, fgcolor=CLEAR, bgcolor=CLEAR, borderstyle=q("NONE"),
        clicksound=q("sound/menu/apply.wav"), stuffcommand=q(cmd))
    label("artFrame" + key, "%d 128 144 144" % (x + 46), bg=DARK, border="3D_BORDER")
    label("art" + key, "%d 132 136 136" % (x + 50), shader=art)
    label("cap" + key, "%d 276 212 20" % (x + 12), cap, fg=RUST, font="facfont-20", align="center")
    for i, ln in enumerate(desc):
        label("desc%s%d" % (key, i + 1), "%d %d 212 15" % (x + 12, 298 + i * 14), ln, fg=INKC, font="verdana-12", align="center")
    res("Button", name=q("begin" + key), rect="%d 348 132 26" % (x + 52), title=q("BEGIN"), fgcolor="0.90 0.84 0.66 1.00",
        bgcolor=DARK, borderstyle=q("3D_BORDER"), font=q("facfont-20"), clicksound=q("sound/menu/apply.wav"), stuffcommand=q(cmd))

label("footRule", "64 392 512 1", bg="0.42 0.22 0.06 0.70")
res("Button", name=q("backBtn"), rect="250 402 140 24", title=q("BACK"), fgcolor="0.90 0.84 0.66 1.00", bgcolor=DARK,
    borderstyle=q("3D_BORDER"), font=q("facfont-20"), clicksound=q("sound/menu/back.wav"), stuffcommand=q("popmenu 0"))

HEAD = """// HZM coop - TRAINING (advtrain 2026-11-10). Opened from the 3D attic's practice target (main.urc hotspot "training").
// The attic home of both training courses: BASIC TRAINING (the retail map "training") and ADVANCED TRAINING (m4l0 with
// coop_advTraining 1 - every coop skill on one field). Each card / BEGIN sets ui_dmmap + coop_advTraining exactly as the
// co-op map select's Training tiles do (ui/coop_start/m0.cfg) and runs coop_mod/start_server.cfg (listen host, ui_startdmmap 2).
// coop_advTraining is a plain set, never seta (TRAPS T7). Card art = the co-op tiles (zzzzzzzzzz_coop_tileart.pk3).
// Written by docs/proposals/advanced_training_2026-11-09/attic/tools/gen_training_urc.py - do not hand-edit.
menu "coop_training" 640 480 NONE 1
borderstyle NONE
bgcolor 0 0 0 0
align centerx centery
virtualres 1
fullscreen 0
escapecommand "popmenu 0"

direction from_top 0
"""
# [trainfix] GATE: an ACTIVE (hovered / clicked) button is brought to the front, so a button that is opaque or has a
# hover shader must not contain any other widget's rect - it would hide it while active.
import re as _re
_wid = []
for _r in R:
    _n = _re.search(r'name "([^"]+)"', _r)
    _rc = _re.search(r'rect (\d+) (\d+) (\d+) (\d+)', _r)
    if _n and _rc:
        _wid.append((_n.group(1), _r.lstrip().startswith("resource\nButton") or "\nButton\n" in _r[:40], tuple(map(int, _rc.groups())), _r))
for _nm, _isb, (_x, _y, _w, _h), _r in _wid:
    if not _isb:
        continue
    _bg = _re.search(r'bgcolor ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', _r)
    _opaque = ("hovershader" in _r) or (_bg is not None and float(_bg.group(4)) > 0)
    for _nm2, _isb2, (_x2, _y2, _w2, _h2), _r2 in _wid:
        if _nm2 == _nm or _isb2:
            continue
        _inside = _x <= _x2 and _y <= _y2 and _x2 + _w2 <= _x + _w and _y2 + _h2 <= _y + _h
        assert not (_opaque and _inside), "button %s hides %s while active (BringToFront): make it transparent" % (_nm, _nm2)
txt = HEAD + "\n" + "\n".join(R) + "\nend.\n"
# parse gates (the shapes that silently drop a urc): balanced braces per resource, every quote paired per line, ASCII only
assert txt.count("{") == txt.count("}") == len(R)
for n, ln in enumerate(txt.splitlines(), 1):
    assert ln.count('"') % 2 == 0, (n, ln)
    assert all(32 <= ord(c) < 127 or c == "\t" for c in ln), (n, ln)
names = re.findall(r'(?m)^name "([^"]+)"', txt)
assert len(names) == len(set(names)), "duplicate widget names"
for cmd in (BASIC, ADV):
    assert "seta" not in cmd and txt.count('stuffcommand "%s"' % cmd) == 2
out = os.path.join(ui, "coop_training.urc")
open(out, "wb").write(txt.replace("\n", "\r\n").encode("ascii"))
print("%s: %d widgets, %d lines" % (out, len(R), txt.count("\n")))

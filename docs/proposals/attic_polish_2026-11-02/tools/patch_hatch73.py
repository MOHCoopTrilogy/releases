"""patch_hatch73.py <mod ui dir> - v1.10.73: the attic's ladder hatch is the QUIT GAME exit (gen_hatch73.py models). Idempotent.

User: "add a ladder hatch to the left side of the main-menu room, so it's clear how the attic is reached" + "make that the Quit
Game room". The hatch is in the open floor LEFT of the home camera (not in the home frame, at any aspect), so - like the MP
room's rack and notice board (patch_mproom69.py) - a scripted turn shows it:
  * "< QUIT GAME" cue at the left edge (home only): hover turns the camera to the hatch (TURN: the home spot nudged 1.5 u, so
    the engine's ESC rule - away from home at stop 0 -> fly home - brings it back; yaw 68, 30 deg down). The cue is hidden while
    turned (ui_atcHatch 1); a strip at the RIGHT edge turns home (the opposite edge: no flip-flop, the v1.10.70 rack lesson).
  * the hatch hotspot (stop 0, appended LAST: ui_scene_hot = its list position): hover lights it (hzm_hatch_lit, the attic's
    lit-copy recipe) and the chalk sign reads QUIT GAME; its hit box is the hatch's projected box at the TURN view (it is
    off-screen at home, so it cannot catch a home hover).
  * click: the camera flies to the ladder's top and looks down the shaft (DOWN), then hzm_quitconfirm: the same room held at
    DOWN (its own scene copy: a pushed menu stops the attic's Draw) and a card - QUIT GAME / STAY. STAY (or ESC) pops it; the
    attic, left by sceneleave, flies home by itself.
  * the corner QUIT button opens the same confirmation (it used to quit at once - the user's rule: never quit unconfirmed).
"""
import json, math, os, re, sys

ui = sys.argv[1]
HOME = "-36.7 21.0 102.4 7.01 0.00 0.00 55.11"
TURN = "-35.2 21.0 102.4 30.00 68.00 0.00 55.11"
DOWN = "12.0 126.0 70.0 55.00 90.00 0.00 55.00"
HC = (12.0, 168.0, 0.0)
HBOX = [(x, y, z) for x in (-14.0, 42.0) for y in (144.0, 192.0) for z in (0.0, 60.0)]      # the hatch with its lid, rails, post


def project(p, cam, W=1920.0, H=1080.0):
    x, y, z, pitch, yaw, _r, fov = (float(v) for v in cam.split())
    pr, yr = math.radians(pitch), math.radians(yaw)
    f = (math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr))
    r = (math.sin(yr), -math.cos(yr), 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    d = (p[0] - x, p[1] - y, p[2] - z)
    zc, xc, yc = (sum(a * b for a, b in zip(d, v)) for v in (f, r, u))
    ty = math.tan(math.radians(fov / 2))
    return W / 2 + xc / zc / (ty * W / H) * W / 2, H / 2 - yc / zc / ty * H / 2


def rd(p):
    t = open(p, encoding="latin-1", newline="").read()
    return t.replace("\r\n", "\n"), ("\r\n" if "\r\n" in t else "\n")


def wr(p, t, nl):
    open(p, "w", encoding="latin-1", newline="").write(t.replace("\n", nl))


def drop_widget(t, name):
    return re.sub(r'resource\n\w+\n\{\nname "%s"\n.*?\n\}\n' % re.escape(name), "", t, flags=re.S)


mp = os.path.join(ui, "main.urc")
m, nl = rd(mp)
# ---- strip a previous run
m = re.sub(r'(?m)^scenemodel "models/menu/hzm_hatch_lit\.tik"[^\n]*\n', "", m)
m = re.sub(r'(?m)^scenemodelhide "hzm_hatch_lit"[^\n]*\n', "", m)
m = re.sub(r'(?m)^(?:scenehot|scenehotbox|scenehotfx) "quit" [^\n]*\n', "", m)
m = re.sub(r'(?m)^scenelabel "atticsign_quit" [^\n]*\n', "", m)
for w in ("atticsign_quit", "hot_quit", "hzm_hatchcue_text", "hzm_hatchcue", "hzm_hatchback"):
    m = drop_widget(m, w)
s0 = m.index('name "atticscene"')
s1 = m.index("\n}\n", s0)
sc = m[s0:s1]
assert '"models/menu/hzm_hatch.tik"' in sc, "run patch_close73.py first (the hatch models)"
# ---- the lit copy (hidden until hovered), right after the hatch
sc = sc.replace('scenemodel "models/menu/hzm_hatch.tik" 0 0 0 0\n',
                'scenemodel "models/menu/hzm_hatch.tik" 0 0 0 0\nscenemodel "models/menu/hzm_hatch_lit.tik" 0 0 0 0\n', 1)
k = sc.index("\nscenecam ")
sc = sc[:k] + '\nscenemodelhide "hzm_hatch_lit" 1' + sc[k:]
# ---- the hotspot, LAST
n0 = len(re.findall(r'(?m)^scenehot "', sc))
IDX = n0 + 1
CLICK = ("set ui_scene_hot 0; set ui_atcHatch 0; globalwidgetcommand atticscene sceneleave; globalwidgetcommand atticscene scenefly 0.9 %s; "
         "uiafter 0.9 pushmenu hzm_quitconfirm" % DOWN)
cx, cy = project((HC[0], HC[1], 20.0), TURN)
cs = [project(p, TURN) for p in HBOX]
xs, ys = [q[0] for q in cs], [q[1] for q in cs]
box = ((min(xs) + max(xs)) / 2 - cx, (min(ys) + max(ys)) / 2 - cy, (max(xs) - min(xs)) / 2 + 6, (max(ys) - min(ys)) / 2 + 6)
lines = ['scenehot "quit" %.1f %.1f %.1f 22.0 "%s" "QUIT GAME" "hot_quit" 0' % (HC[0], HC[1], 20.0, CLICK),
         'scenelabel "atticsign_quit" 225.8 65.9 116.7 19.74 4.93',
         'scenehotbox "quit" %.1f %.1f %.1f %.1f' % box,
         'scenehotfx "quit" "-" 0 "-" "-" "hzm_hatch_lit" "hzm_hatch"']
last = [mm for mm in re.finditer(r'(?m)^(?:scenehot|scenehotbox|scenehotfx|scenelabel) .*$', sc)][-1]
sc = sc[:last.end()] + "\n" + "\n".join(lines) + sc[last.end():]
m = m[:s0] + sc + m[s1:]
# ---- widgets: chalk sign + proxy (the training ones' style), the cue, the way back
lab = re.search(r'resource\nLabel\n\{\nname "atticsign_training"\n(.*?)\n\}\n', m, re.S).group(1)
btn = re.search(r'resource\nButton\n\{\nname "hot_training"\n(.*?)\n\}\n', m, re.S).group(1)
lab_q = re.sub(r'(?m)^title ".*"$', 'title "QUIT GAME"', lab)
lab_q = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % IDX, lab_q)
btn_q = re.sub(r'(?m)^stuffcommand ".*"$', lambda _m: 'stuffcommand "%s"' % CLICK, btn)
btn_q = re.sub(r'(?m)^hovercommand ".*"$', 'hovercommand "set ui_scene_hot %d"' % IDX, btn_q)
ON = "set ui_scene_hot 0; set ui_atcHatch 1; globalwidgetcommand atticscene scenefly 0.5 %s" % TURN
OFF = "set ui_scene_hot 0; set ui_atcHatch 0; globalwidgetcommand atticscene scenefly 0.5 %s" % HOME
W = ['resource', 'Label', '{', 'name "atticsign_quit"', lab_q, '}',
     'resource', 'Button', '{', 'name "hot_quit"', btn_q, '}',
     'resource', 'Label', '{', 'name "hzm_hatchcue_text"', 'title "<  QUIT GAME"', 'rect 4 222 104 22', 'fgcolor 0.93 0.93 0.88 0.90',
     'bgcolor 0.10 0.08 0.06 0.60', 'borderstyle "NONE"', 'font "facfont-20"', 'textalign center',
     'enabledcvar "ui_atticActive==1 ui_atcStop==0 ui_atcHatch!=1 ui_scene_hot==0"', '}',
     'resource', 'Button', '{', 'name "hzm_hatchcue"', 'rect 4 222 104 22', 'fgcolor 0 0 0 0', 'bgcolor 0 0 0 0', 'borderstyle "NONE"',
     'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % ON, 'hovercommand "%s"' % ON,
     'enabledcvar "ui_atticActive==1 ui_atcStop==0 ui_atcHatch!=1"', '}',
     # back home: a strip at the RIGHT edge while turned (the hatch and its sign sit left of centre there)
     'resource', 'Button', '{', 'name "hzm_hatchback"', 'rect 560 0 80 440', 'fgcolor 0 0 0 0', 'bgcolor 0 0 0 0', 'borderstyle "NONE"',
     'stuffcommand "%s"' % OFF, 'hovercommand "%s"' % OFF, 'enabledcvar "ui_atticActive==1 ui_atcHatch==1"', '}']
end = m.rindex("\nend.")
m = m[:end] + "\n" + "\n".join(W) + m[end:]
# ---- the corner QUIT button asks first
m = re.sub(r'(name "hzm_quit"\n(?:[^}]*?\n)*?)stuffcommand "quit"', lambda mm: mm.group(1) + 'stuffcommand "pushmenu hzm_quitconfirm"', m, count=1)
wr(mp, m, nl)
print("main.urc: hatch hotspot #%d, box %s, cue + back strip, corner QUIT confirms" % (IDX, tuple(round(v, 1) for v in box)))

# ---- hzm_quitconfirm.urc: the room held at DOWN + the card
blk = re.search(r'(?m)^resource\nScene3D\n\{\nname "atticscene"\n(.*?)\n\}\n', m, re.S).group(1)
keep = [l for l in blk.split("\n") if l.startswith(("scenemodel ", "scenemodelhide ", "scenewx ", "scenelight ", "actorstage ", "actorcycle ",
                                                     "actorprop ", "rect ", "enabledcvar ", "fgcolor ", "bgcolor ", "borderstyle "))]
keep = [l for l in keep if not l.startswith("enabledcvar")] + ['enabledcvar "ui_atticActive==1"', "scenecam %s" % DOWN]
card = []


def label(name, title, rect, font, fg, bg="0 0 0 0", align="center"):
    card.extend(["resource", "Label", "{", 'name "%s"' % name, 'title "%s"' % title, "rect %s" % rect, "fgcolor %s" % fg,
                 "bgcolor %s" % bg, 'borderstyle "NONE"', 'font "%s"' % font, "textalign %s" % align, "}"])


def button(name, title, rect, cmd):
    card.extend(["resource", "Button", "{", 'name "%s"' % name, 'title "%s"' % title, "rect %s" % rect, "fgcolor 0.93 0.89 0.78 1.00",
                 "bgcolor 0.18 0.15 0.11 0.95", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center",
                 'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % cmd, "}"])


label("qc_panel", "", "200 176 240 128", "facfont-20", "0 0 0 0", "0.07 0.06 0.05 0.82")
label("qc_title", "LEAVE THE ATTIC?", "200 190 240 28", "facfont-20", "0.93 0.88 0.72 1.00")
label("qc_sub", "Quit the game and return to the desktop.", "208 222 224 18", "verdana-12", "0.85 0.82 0.74 1.00")
button("qc_quit", "QUIT GAME", "216 258 96 26", "quit")
button("qc_stay", "STAY", "328 258 96 26", "popmenu 0")
q = ["// v1.10.73 GENERATED by docs/proposals/attic_polish_2026-11-02/tools/patch_hatch73.py - the QUIT GAME confirmation: the attic held",
     "// at the ladder's top looking down the hatch (its own scene copy: a pushed menu stops the attic's Draw) and a card. STAY / ESC pop it;",
     "// the attic, left by sceneleave, flies home by itself.",
     'menu "hzm_quitconfirm" 640 480 NONE 0', "bgcolor 0 0 0 0", "borderstyle NONE", "fullscreen 1", "virtualres 1", "bgfill 0 0 0 1", "",
     "resource", "Scene3D", "{", 'name "quitscene"'] + keep + ["}"] + card + ["end."]
wr(os.path.join(ui, "hzm_quitconfirm.urc"), "\n".join(q) + "\n", nl)
json.dump(dict(home=HOME, turn=TURN, down=DOWN, idx=IDX, box=box), open(os.path.join(ui, "..", "..", "hatch73_urc.json"), "w"), indent=1)
print("hzm_quitconfirm.urc: %d scene lines" % len(keep))

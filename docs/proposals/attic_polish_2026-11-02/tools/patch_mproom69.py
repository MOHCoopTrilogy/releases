"""patch_mproom69.py <mod ui dir> <mproom69 json> - v1.10.69 urc changes for gen_mproom69.py. Idempotent (every line it adds is
tagged or recognisable and is removed first). Runs AFTER patch_attic68.py (which writes the hub's rack and the weapon viewer's room).

multiplayer.urc (the hub, scene "hubscene")
  * the new models, their scene lights, the staged soldier (actorstage / actorcycle / actorprop - the attic's recipe), and the lit
    copies hidden until hovered (scenemodelhide ... 1; scenehotfx shows the lit copy and hides the plain one).
  * four hotspots after the six: 7 ORDERS OF THE DAY, 8 SERVICE RECORD, 9 PROMOTIONS (the three notices), 10 the RADIO. Each has a
    proxy Button (mouse / keyboard / pad focus, as the other six) and a caption.
  * the notice board is off the home view (right-hand wall, front half). The engine's scenepeek takes ONE hotspot per scene and
    the rack has it, so the board's turn is scripted: the right-edge cue "NOTICES >" flies the camera to the board when hovered
    (ui_hubBoard 1); the cursor in the left quarter of the screen (an invisible Button there) flies it home - the rack's peek, the
    other way round. ESC from either view leaves the room as before (the hub camera reset home first).
  * the radio: hover = its dial lights (lit copy); click = a short crackle (sound/menu/hzm_radio_tune.wav) and the next menu
    record (vstr ui_mmSelNext - the gramophone's shuffle).
every room copy (hzm_mpui_scene_*.inc, hzm_wpnview.urc): the same models, lights, soldier and hidden lit copies, no hotspots.
"""
import json, math, os, re, sys

ui, js = sys.argv[1:3]
A = json.load(open(js))
TAG = "// [mp69]"
HOME = "-70.9 15.8 86.6 4.00 -3.00 0.00 58.00"
WR = A["walls"]["right"]
FC = A["board"]["face"]
# (further back than the first cut; x +5 keeps the void past the room's missing front wall out of the 21:9 frame; at z 84 the bench
# under the peg rail stays wholly below the frame instead of poking into its corner)
BOARD_CAM = (FC[0] + 5.0, WR + 90.0, 84.0)
BOARD_POSE = "%.1f %.1f %.1f 2.00 -90.00 0.00 58.00" % BOARD_CAM
# the notices' hotspots carry a scenehot stop: live only while ui_atcStop == BOARD_STOP. ui_atcStop is the ATTIC's stop cvar (its
# own hotspots are stop 0 and its stops 1-4) - every way out of the board view sets it back to 0: the turn home, a notice's click,
# ESC. (The rack's engine peek also waits for ui_atcStop 0, so it cannot fire from the board view.)
BOARD_STOP = 69


def rd(p):
    t = open(p, encoding="latin-1", newline="").read()
    return t.replace("\r\n", "\n"), ("\r\n" if "\r\n" in t else "\n")


def wr(p, t, nl):
    open(p, "w", encoding="latin-1", newline="").write(t.replace("\n", nl))


def pose_to(cam, pt, fov):
    d = [pt[i] - cam[i] for i in range(3)]
    return "%.1f %.1f %.1f %.2f %.2f 0.00 %.2f" % (cam[0], cam[1], cam[2], -math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))),
                                                   math.degrees(math.atan2(d[1], d[0])), fov)


def project(p, cam, W=1920.0, H=1080.0):
    """a point -> 1080p screen pixels for a scene pose (fov = VERTICAL, the engine's; pitch positive = down)"""
    x, y, z, pitch, yaw, _r, fov = (float(v) for v in cam.split())
    pr, yr = math.radians(pitch), math.radians(yaw)
    f = (math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr))
    r = (math.sin(yr), -math.cos(yr), 0.0)
    u = (r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0])
    d = (p[0] - x, p[1] - y, p[2] - z)
    zc, xc, yc = (sum(a * b for a, b in zip(d, v)) for v in (f, r, u))
    ty = math.tan(math.radians(fov / 2))
    return W / 2 + xc / zc / (ty * W / H) * W / 2, H / 2 - yc / zc / ty * H / 2, zc


# ------------------------------------------------------------------ the room lines (every copy)
S = A["soldier"]
AL = S["tik"]
# No trailing comments on scene lines (no urc scene line in the mod carries one; an optional-argument command is no place to find
# out how the parser takes them). Our lines are recognised by content instead: hzm_hub69_ / hub_gi_menu models, the n_* / radio
# hotspots, and the lights by their radius, which ends in .69 (the engine reads it as a float).
LIGHTS = ["scenelight 140.0 -10.0 112.0 300.69 0.95 0.82 0.62", "scenelight 190.0 95.0 112.0 300.69 0.95 0.82 0.62",
          "scenelight %.1f %.1f %.1f 120.69 1.0 0.52 0.22" % tuple(A["stove"]["fire"]),
          "scenelight %.1f %.1f %.1f 80.69 1.0 0.78 0.45" % tuple(A["lantern"]),
          "scenelight %.1f %.1f 118.0 220.69 0.80 0.74 0.62" % (FC[0], FC[1] + 60.0)]
HIDES = ['scenemodelhide "hzm_hub69_n_daily_lit" 1', 'scenemodelhide "hzm_hub69_n_record_lit" 1', 'scenemodelhide "hzm_hub69_n_ranks_lit" 1',
         'scenemodelhide "hzm_hub69_radio_lit" 1']
STAGE = ['actorstage "%s" %.1f %.1f %.1f "cardA" 6.0 11.0' % (AL, S["pos"][0], S["pos"][1], S["yaw"]),
         'actorcycle "%s" 2.0 7.0 12.0 "cardB~"' % AL,
         'actorcycle "%s" 1.0 2.5 3.5 "cardDraw"' % AL,
         'actorprop "%s" "models/miscobj/cardhand01.tik" "tag_weapon_left" "card" 0 0 0 1 0 0 0' % AL]
MODELS = A["lines"]
ROOM = MODELS + HIDES + LIGHTS


def strip69(t):
    t = re.sub(r"(?m)^.*%s\n" % re.escape(TAG), "", t)          # (the first v1.10.69 drafts tagged their lines)
    t = re.sub(r'(?m)^(?:scenemodel|scenemodelhide|actorstage|actorcycle|actorprop) "(?:models/menu/)?hzm_hub69_[^\n]*\n', "", t)
    t = re.sub(r'(?m)^(?:scenemodel|actorstage|actorcycle|actorprop) "models/human/hzm_menu/hub_gi_menu\.tik"[^\n]*\n', "", t)
    t = re.sub(r'(?m)^scenelight (?:\S+ ){3}\d+\.69 [^\n]*\n', "", t)
    t = re.sub(r'(?m)^(?:scenehot|scenehotbox|scenehotfx) "(?:n_daily|n_record|n_ranks|radio)" [^\n]*\n', "", t)
    t = re.sub(r'(?m)^scenelabel "hubcap10" [^\n]*\n', "", t)
    return t


def add_room(t, i0, stage=True):
    """the room lines before the scene's scenecam; the soldier's stage lines after it (they need the model declared first)"""
    j = t.index("\nscenecam ", i0)
    t = t[:j] + "\n" + "\n".join(ROOM) + t[j:]
    if stage:
        k = t.index("\n", t.index("\nscenecam ", i0) + 1)
        t = t[:k] + "\n" + "\n".join(STAGE) + t[k:]
    return t


def drop_widget(t, name):
    return re.sub(r'resource\n\w+\n\{\nname "%s"\n.*?\n\}\n' % re.escape(name), "", t, flags=re.S)


# ------------------------------------------------------------------ multiplayer.urc
mpp = os.path.join(ui, "multiplayer.urc")
m, mnl = rd(mpp)
m = strip69(m)
for w in ("hubcap7", "hubcap8", "hubcap9", "hubcap10", "hot_n_daily", "hot_n_record", "hot_n_ranks", "hot_radio", "hzm_hubboardcue_text",
          "hzm_hubboardcue", "hzm_hubboardback", "hzm_hubboardcap7", "hzm_hubboardcap8", "hzm_hubboardcap9"):
    m = drop_widget(m, w)
sc0 = m.index('name "hubscene"')
m = add_room(m, sc0)
sc0 = m.index('name "hubscene"')
sc1 = m.index("\n}\n", sc0)
n0 = len(re.findall(r'(?m)^scenehot "', m[sc0:sc1]))
assert n0 == 6, ("expected the six hub hotspots (rack included) before these", n0)

HOTS = []
CAP = {"daily": "ORDERS OF THE DAY", "record": "SERVICE RECORD", "ranks": "PROMOTIONS"}
OPEN = {"daily": "coop_srsync; exec ui/coop_sr_pgd.cfg", "record": "coop_srsync; exec ui/coop_sr_pg0.cfg",
        "ranks": "set coop_mpSrP0 1; set coop_mpSrP1 0; set coop_mpSrP2 0; set coop_mpSrP3 0; set coop_mpSrP4 0; set coop_mpSrP5 0"}
MENU = {"daily": "coop_sr", "record": "coop_sr", "ranks": "coop_mp_record"}
add = []
for k, nt in enumerate(A["notices"]):
    key, c = nt["key"], nt["centre"]
    idx = n0 + 1 + k
    close = pose_to((c[0], c[1] + 40.0, c[2] + 1.0), c, 44.0)
    cmd = ("set ui_scene_hot 0; set ui_hubBoard 0; set ui_atcStop 0; %s; globalwidgetcommand hubscene sceneleave 1; globalwidgetcommand hubscene scenefly 0.6 %s; "
           "uiafter 0.6 pushmenu %s" % (OPEN[key], close, MENU[key]))
    sx, sy, _ = project(c, BOARD_POSE)
    # the hit box: the sheet's projected rectangle at the board view (pixels at 1080 p), offset from the projected centre
    cs = [project((c[0] + dx * nt["w"] / 2, c[1], c[2] + dz * nt["h"] / 2), BOARD_POSE) for dx in (-1, 1) for dz in (-1, 1)]
    xs, ys = [q[0] for q in cs], [q[1] for q in cs]
    box = ((min(xs) + max(xs)) / 2 - sx, (min(ys) + max(ys)) / 2 - sy, (max(xs) - min(xs)) / 2 + 4, (max(ys) - min(ys)) / 2 + 4)
    # live ONLY at the board view (stop BOARD_STOP): at home the three project to the right-hand screen edge, where their board-view
    # sized boxes would cover the NOTICES cue and the edge of the game-type board's box
    add += ['scenehot "n_%s" %.1f %.1f %.1f 11.0 "%s" "%s" "hot_n_%s" %d' % (key, c[0], c[1], c[2], cmd, CAP[key], key, BOARD_STOP),
            'scenehotbox "n_%s" %.1f %.1f %.1f %.1f' % (key, box[0], box[1], box[2], box[3]),
            'scenehotfx "n_%s" "-" 0 "-" "-" "hzm_hub69_n_%s_lit" "hzm_hub69_n_%s"' % (key, key, key)]
    HOTS.append((idx, "hot_n_%s" % key, CAP[key], cmd, "hzm_hubboardcap%d" % idx))
# the radio
rc, rlo, rhi = A["radio"]["centre"], A["radio"]["lo"], A["radio"]["hi"]
ridx = n0 + 4
rcmd = "play sound/menu/hzm_radio_tune.wav; uiafter 0.35 vstr ui_mmSelNext"
cs = [project((x, y, z), HOME) for x in (rlo[0], rhi[0]) for y in (rlo[1], rhi[1]) for z in (rlo[2], rhi[2])]
rsx, rsy, _ = project(rc, HOME)
xs, ys = [q[0] for q in cs], [q[1] for q in cs]
rbox = ((min(xs) + max(xs)) / 2 - rsx, (min(ys) + max(ys)) / 2 - rsy, (max(xs) - min(xs)) / 2 + 6, (max(ys) - min(ys)) / 2 + 6)
add += ['scenehot "radio" %.1f %.1f %.1f 12.0 "%s" "CHANGE STATION" "hot_radio"' % (rc[0], rc[1], rc[2], rcmd),
        'scenehotbox "radio" %.1f %.1f %.1f %.1f' % rbox,
        'scenehotfx "radio" "-" 0 "-" "-" "hzm_hub69_radio_lit" "hzm_hub69_radio"',
        'scenelabel "hubcap%d" %.1f %.1f %.1f 14.00 3.20' % (ridx, rc[0], rc[1], rhi[2] + 7.0)]
HOTS.append((ridx, "hot_radio", "CHANGE STATION", rcmd, "hubcap%d" % ridx))
last = [mm for mm in re.finditer(r'(?m)^(?:scenehot|scenehotbox|scenelabel|scenepeek) .*$', m[sc0:sc1])][-1]
k = sc0 + last.end()
m = m[:k] + "\n" + "\n".join(add) + m[k:]

# widgets: captions + proxies (the hub's own hubcap / hub_h styles), the board cue, the back zone
lab = re.search(r'resource\nLabel\n\{\nname "hubcap2"\n(.*?)\n\}\n', m, re.S).group(1)
btn = re.search(r'resource\nButton\n\{\nname "hub_h2"\n(.*?)\n\}\n', m, re.S).group(1)
blk = ""
for idx, wname, cap, cmd, capw in HOTS:
    if capw.startswith("hubcap"):          # the radio: a chalk caption framed to the radio (scenelabel), like the six
        l_ = re.sub(r'(?m)^title ".*"$', 'title "%s"' % cap, lab)
        l_ = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % idx, l_)
    else:                                  # a notice (board view, not home): a fixed caption at the foot of the screen
        l_ = re.sub(r'(?m)^rect .*$', "rect 220 430 200 26", lab)
        l_ = re.sub(r'(?m)^title ".*"$', 'title "%s"' % cap, l_)
        l_ = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_hubBoard==1 ui_scene_hot==%d"' % idx, l_)
    b_ = re.sub(r'(?m)^stuffcommand ".*"$', lambda _m: 'stuffcommand "%s"' % cmd, btn)
    b_ = re.sub(r'(?m)^hovercommand ".*"$', 'hovercommand "set ui_scene_hot %d"' % idx, b_)
    blk += "resource\nLabel\n{\nname \"%s\"\n%s\n}\nresource\nButton\n{\nname \"%s\"\n%s\n}\n" % (capw, l_, wname, b_)
ON = "set ui_scene_hot 0; set ui_hubBoard 1; set ui_atcStop %d; globalwidgetcommand hubscene scenefly 0.5 %s" % (BOARD_STOP, BOARD_POSE)
OFF = "set ui_scene_hot 0; set ui_hubBoard 0; set ui_atcStop 0; globalwidgetcommand hubscene scenefly 0.5 %s" % HOME
cue = ["resource", "Label", "{", 'name "hzm_hubboardcue_text"', 'title "NOTICES  >"', "rect 556 222 80 22", "fgcolor 0.93 0.93 0.88 0.90",
       "bgcolor 0.10 0.08 0.06 0.60", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center",
       'enabledcvar "ui_atticActive==1 ui_scene_peek!=1 ui_hubBoard!=1"', "}",
       "resource", "Button", "{", 'name "hzm_hubboardcue"', "rect 556 222 80 22", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0",
       'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % ON, 'hovercommand "%s"' % ON,
       'enabledcvar "ui_atticActive==1 ui_scene_peek!=1 ui_hubBoard!=1"', "}",
       # the way back: the cursor in the left quarter of the screen (the rack's peek turns home in the left 40 %)
       "resource", "Button", "{", 'name "hzm_hubboardback"', "rect 0 0 160 480", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0",
       'borderstyle "NONE"', 'stuffcommand "%s"' % OFF, 'hovercommand "%s"' % OFF, 'enabledcvar "ui_atticActive==1 ui_hubBoard==1"', "}"]
blk += "\n".join(cue) + "\n"
end = m.index("// ---- [mphub3d] end")
m = m[:end] + blk + m[end:]
# the rack's "< RACK" cue hides at the board view
m = re.sub(r'(name "hzm_hubrack(?:cue|cue_text)"\n(?:.*\n)*?)enabledcvar "ui_atticActive==1 ui_scene_peek!=1(?: ui_hubBoard!=1)?"',
           lambda mm: mm.group(1) + 'enabledcvar "ui_atticActive==1 ui_scene_peek!=1 ui_hubBoard!=1"', m)
# ESC leaves the room as before; the hub camera and the board flag reset first (it may be at the board view)
m = re.sub(r'(?m)^escapecommand ".*"$', 'escapecommand "set ui_scene_hot 0; set ui_hubBoard 0; set ui_atcStop 0; globalwidgetcommand hubscene scenecam %s; popmenu 1"' % HOME, m, count=1)
wr(mpp, m, mnl)
print("multiplayer.urc: hotspots %s, board pose %s" % ([h[0] for h in HOTS], BOARD_POSE))

# ------------------------------------------------------------------ the room copies
for f in sorted(os.listdir(ui)):
    if not (re.match(r"hzm_mpui_scene_\w+\.inc$", f) or f == "hzm_wpnview.urc"):
        continue
    p = os.path.join(ui, f)
    t, nl = rd(p)
    t = strip69(t)
    i0 = t.index('name "wvscene"') if f == "hzm_wpnview.urc" else t.index("Scene3D")
    t = add_room(t, i0)
    wr(p, t, nl)
    print("%s: the room's v1.10.69 props" % f)
open(os.path.join(ui, "hzm_hub_board_on.cfg"), "w", encoding="latin-1", newline="\r\n").write(
    "// generated by patch_mproom69.py: the MP room's notice board view (the multiplayer menu open, ui_atticMain 1)\n%s\n" % ON.replace("; ", "\n"))
json.dump(dict(board_pose=BOARD_POSE, home=HOME, hots=[(h[0], h[1], h[2]) for h in HOTS]),
          open(os.path.join(os.path.dirname(os.path.abspath(js)), "mproom69_urc.json"), "w"), indent=1)

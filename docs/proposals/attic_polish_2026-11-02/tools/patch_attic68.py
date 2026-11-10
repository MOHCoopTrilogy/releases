"""patch_attic68.py <mod ui dir> <attic68 json> - v1.10.68 urc changes for gen_attic68_props.py. Idempotent. Runs AFTER
make_attic_polish.py and gen_weapon_viewer.py (both keep the attic's rack hotspot - the viewer's generator re-adds its own if the
attic has none) and BEFORE gen_records3d.py (which copies main.urc's room into the records / medals scenes).

main.urc
  * the rack leaves: its scenehot / scenehotbox / scenepeek / chalk caption, the hot_rack proxy and the RACK > cue go; the hotspots
    after it (window 18, lookup 19) move up one (ui_scene_hot 17, 18).
  * the projector turns to the screen: atc_projector1, the lamp-lit copy and both reels placed with the turn (gen_attic68_props:
    origin O, yaw TH about the projector's centre); the screen model joins the room. The 2D beam / lamp labels (frBeam, frLamp:
    a beam drawn toward the old, left-hand side) are retired - the beam is 3D now, inside hzm_projector_lit.
multiplayer.urc + every mpui copy of the room (hzm_mpui_scene_*.inc)
  * the rack and its wall shadow on the left wall; in the hub's own scene a 6th hotspot "rack" (WEAPONS RACK, the caption and proxy
    like the other five) that opens the weapon viewer exactly as the attic's did.
hzm_wpnview.urc
  * the viewer's room is the MP room at its rack now (the hub's models + the rack; the camera in front of it).
"""
import json, math, os, re, sys

ui, js = sys.argv[1:3]
A = json.load(open(js))
cs, sn = A["turn_cs"]
PC = A["proj_pivot"]
YAW = A["proj_yaw"]
O = A["proj_origin"]


def rd(p):
    t = open(p, encoding="latin-1", newline="").read()
    return t.replace("\r\n", "\n"), ("\r\n" if "\r\n" in t else "\n")


def wr(p, t, nl):
    open(p, "w", encoding="latin-1", newline="").write(t.replace("\n", nl))


def drop_widget(t, name):
    return re.sub(r'resource\n\w+\n\{\nname "%s"\n.*?\n\}\n' % re.escape(name), "", t, flags=re.S)


def turned(x, y):
    dx, dy = x - PC[0], y - PC[1]
    return PC[0] + cs * dx - sn * dy, PC[1] + sn * dx + cs * dy


# ------------------------------------------------------------------ main.urc
mp_, nl = rd(os.path.join(ui, "main.urc"))
t = mp_
hots = re.findall(r'(?m)^scenehot "(\w+)"', t[t.index('name "atticscene"'):])
if "rack" in hots:
    ri = hots.index("rack") + 1
    t = re.sub(r'(?m)^(?:scenehot|scenehotbox|scenepeek) "rack" .*\n', "", t)
    t = re.sub(r'(?m)^scenelabel "atticsign_rack" .*\n', "", t)
    for w in ("atticsign_rack", "hzm_rackcue_text", "hzm_rackcue", "hot_rack"):
        t = drop_widget(t, w)
    for k in range(ri + 1, len(hots) + 1):
        t = t.replace("ui_scene_hot==%d\"" % k, "ui_scene_hot==%d\"" % (k - 1))
        t = t.replace("set ui_scene_hot %d\"" % k, "set ui_scene_hot %d\"" % (k - 1))
    assert "rack" not in re.findall(r'(?m)^scenehot "(\w+)"', t)
    print("main.urc: rack hotspot #%d removed, %d later hotspots renumbered" % (ri, len(hots) - ri))
# the projector, turned (every scene that holds it is fixed the same way: main, viewer copies before they regenerate)
PROJ = 'scenemodel "models/menu/atc_projector1.tik" %.3f %.3f 0 %.3f' % (O[0], O[1], YAW)
LIT = 'scenemodel "models/menu/hzm_projector_lit.tik" %.3f %.3f 0 %.3f' % (O[0], O[1], YAW)


def fix_proj(t):
    t = re.sub(r'(?m)^scenemodel "models/menu/atc_projector1\.tik" .*$', PROJ, t)
    t = re.sub(r'(?m)^scenemodel "models/menu/hzm_projector_lit\.tik" .*$', LIT, t)

    # (a reel line from make_attic_polish has yaw 0.0: turn it; one already carrying YAW stays)
    t = re.sub(r'(?m)^scenemodel "models/menu/hzm_proj_reel_(top|bot)\.tik" (\S+) (\S+) (\S+) (\S+) "idle"$',
               lambda m: m.group(0) if abs(float(m.group(5)) - YAW) < 0.01 else
               'scenemodel "models/menu/hzm_proj_reel_%s.tik" %.2f %.2f %s %.3f "idle"' % ((m.group(1),) + turned(float(m.group(2)), float(m.group(3))) + (m.group(4), YAW)), t)
    if "hzm_proj_screen.tik" not in t:
        t = t.replace(PROJ + "\n", PROJ + '\nscenemodel "models/menu/hzm_proj_screen.tik" 0 0 0 0\n', 1)
    return t


t = fix_proj(t)
t = re.sub(r'(name "fr(?:Beam|Lamp)"\n(?:.*\n)*?)enabledcvar "[^"]*"', lambda m: m.group(1) + 'enabledcvar "ui_frBeam2d==1"', t)
wr(os.path.join(ui, "main.urc"), t, nl)
print("main.urc: projector yaw %.2f at %s, screen in, 2D beam retired" % (YAW, O[:2]))

# ------------------------------------------------------------------ the MP room
RC = A["hub_rack_centre"]
POSE = "%.1f %.1f %.1f 0.00 90.00 0.00 50.00" % (RC[0], A["hub_rack_lo"][1] - 1.7 * 52.5 + 25.7, RC[2])
RLINES = ['scenemodel "models/menu/hzm_hub_rack.tik" 0 0 0 0', 'scenemodel "models/menu/hzm_hub_rackshadow.tik" 0 0 0 0']
if os.path.exists(os.path.join(os.path.dirname(js), "posters68.json")):       # v1.10.68: the WWII posters (gen_posters68.py)
    RLINES.append('scenemodel "models/menu/hzm_hub_posters.tik" 0 0 0 0')
HCMD = ("set ui_scene_hot 0; exec ui/wpnview/open.cfg; globalwidgetcommand hubscene sceneleave 1; "
        "globalwidgetcommand hubscene scenefly 0.6 %s; uiafter 0.6 pushmenu hzm_wpnview" % POSE)
mpp = os.path.join(ui, "multiplayer.urc")
for f in [mpp] + [os.path.join(ui, x) for x in sorted(os.listdir(ui)) if re.match(r"hzm_mpui_scene_\w+\.inc$", x)]:
    m, mnl = rd(f)
    m = re.sub(r'(?m)^scenemodel "models/menu/hzm_hub_(?:rack|posters)\w*\.tik".*\n', "", m)
    i0 = m.index('name "hubscene"') if f == mpp else m.index("Scene3D")
    j = m.index("\nscenecam ", i0)
    m = m[:j] + "\n" + "\n".join(RLINES) + m[j:]
    if f == mpp:
        m = re.sub(r'(?m)^(?:scenehot|scenehotbox|scenepeek) "rack" .*\n|^scenelabel "hubcap6" .*\n', "", m)
        for w in ("hubcap6", "hot_rack", "hzm_hubrackcue_text", "hzm_hubrackcue"):
            m = drop_widget(m, w)
        sc0 = m.index('name "hubscene"')
        sc1 = m.index("\n}\n", sc0)
        n = len(re.findall(r'(?m)^scenehot "', m[sc0:sc1])) + 1
        cap = re.search(r'(?m)^scenelabel "hubcap1" \S+ \S+ \S+ (\S+) (\S+)$', m)
        add = ['scenehot "rack" %.1f %.1f %.1f 30.0 "%s" "WEAPONS RACK" "hot_rack"' % (RC[0], RC[1], RC[2], HCMD),
               'scenehotbox "rack" 0.0 0.0 %.1f %.1f' % (A["hub_rack_hi"][0] - A["hub_rack_lo"][0] + 6, A["hub_rack_hi"][2] - A["hub_rack_lo"][2] + 6),
               'scenelabel "hubcap6" %.1f %.1f %.1f 24.15 3.94' % (RC[0], A["hub_rack_lo"][1] + 4, A["hub_rack_hi"][2] + 6)]
        _cam = re.search(r'(?m)^scenecam (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)$', m[sc0:sc1]).groups()
        _yaw = math.degrees(math.atan2(RC[1] - float(_cam[1]), RC[0] - float(_cam[0])))
        add.append('scenepeek "rack" 0.5 %s %s %s %s %.2f %s %s' % (_cam[0], _cam[1], _cam[2], _cam[3], _yaw - 4.0, _cam[5], _cam[6]))
        last = [mm for mm in re.finditer(r'(?m)^scenelabel "hubcap\d" .*$', m[sc0:sc1])][-1]
        k = sc0 + last.end()
        m = m[:k] + "\n" + "\n".join(add) + m[k:]
        lab = re.search(r'resource\nLabel\n\{\nname "hubcap2"\n(.*?)\n\}\n', m, re.S).group(1)
        lab = re.sub(r'(?m)^title ".*"$', 'title "WEAPONS RACK"', lab)
        lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % n, lab)
        btn = re.search(r'resource\nButton\n\{\nname "hub_h2"\n(.*?)\n\}\n', m, re.S).group(1)
        btn = re.sub(r'(?m)^stuffcommand ".*"$', lambda _m: 'stuffcommand "%s"' % HCMD, btn)
        btn = re.sub(r'(?m)^hovercommand ".*"$', 'hovercommand "set ui_scene_hot %d"' % n, btn)
        blk = "resource\nLabel\n{\nname \"hubcap6\"\n%s\n}\nresource\nButton\n{\nname \"hot_rack\"\n%s\n}\n" % (lab, btn)
        # the left wall is outside the room's home view (the camera looks along it): as in the attic (make_attic_polish PEEK_POSE),
        # hovering the rack - its proxy or the "< RACK" cue at the left screen edge - turns the camera left (engine scenepeek)
        cue = ["resource", "Label", "{", 'name "hzm_hubrackcue_text"', 'title "<  RACK"', "rect 4 222 52 22", "fgcolor 0.93 0.93 0.88 0.90",
               "bgcolor 0.10 0.08 0.06 0.60", 'borderstyle "NONE"', 'font "facfont-20"', "textalign center",
               'enabledcvar "ui_atticActive==1 ui_scene_peek!=1"', "}",
               "resource", "Button", "{", 'name "hzm_hubrackcue"', "rect 4 222 52 22", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0",
               'borderstyle "NONE"', 'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % HCMD,
               'hovercommand "set ui_scene_hot %d"' % n, 'enabledcvar "ui_atticActive==1 ui_scene_peek!=1"', "}"]
        blk += "\n".join(cue) + "\n"
        anc = m.index('resource\nButton\n{\nname "hub_h1"')
        m = m[:anc] + blk + m[anc:]
        print("multiplayer.urc: rack hotspot #%d at %s, pose %s" % (n, RC, POSE))
    wr(f, m, mnl)

# ------------------------------------------------------------------ the weapon viewer's room: the MP room at the rack
wv = os.path.join(ui, "hzm_wpnview.urc")
if os.path.exists(wv):
    w, wnl = rd(wv)
    m, _ = rd(mpp)
    hs = m[m.index('name "hubscene"'):]
    hs = hs[:hs.index("\n}\n")]
    room = [l for l in hs.splitlines() if l.startswith(("scenemodel ", "scenelight "))]
    s0 = w.index('name "wvscene"')
    s1 = w.index("\n}\n", s0)
    body = w[s0:s1].split("\n")
    head = [l for l in body if not l.startswith(("scenemodel ", "scenelight ", "scenemodelcvar ", "scenemodelhide ", "scenecam "))]
    w = w[:s0] + "\n".join(head + room + ["scenecam %s" % POSE]) + w[s1:]
    wr(wv, w, wnl)
    print("hzm_wpnview.urc: the MP room at the rack (%d room lines)" % len(room))
gr = os.path.join(ui, "hzm_attic_go_rack.cfg")
open(gr, "w", encoding="latin-1", newline="\r\n").write(
    "// generated by patch_attic68.py: the MP room's rack (the multiplayer menu open, ui_atticMain 1, no cursor)\nset ui_scene_hot 0\n"
    "exec ui/wpnview/open.cfg\nglobalwidgetcommand hubscene sceneleave 1\nglobalwidgetcommand hubscene scenefly 0.6 %s\nwait 600\n"
    "pushmenu hzm_wpnview\n" % POSE)

# ------------------------------------------------------------------ PLAY in the film room: a framed start (engine menu-attic68:
# HZMDemoList playdemo runs `vstr ui_frTransition` with the demo command waiting in ui_frPlayCmd). The film room closes, the camera
# flies to the pull-down screen while the projector runs (ui_scene_fxon film: the reels turn, the lamp, the beam and the picture's
# light show, the clatter plays - the same scenehotfx the hover uses), the picture fills the view, a short veil, the film starts.
# (A cfg's wait is MILLISECONDS in this engine.)
PIC = A["screen"]["pic"]
SCR_POSE = "%.1f %.1f %.1f 0.00 -90.00 0.00 50.00" % (PIC[0], PIC[1] + 72.0, PIC[2])
open(os.path.join(ui, "hzm_frplay.cfg"), "w", encoding="latin-1", newline="\r\n").write(
    "// generated by patch_attic68.py: the film room's PLAY - fly to the screen with the projector running, then the film\n"
    "set ui_scene_hot 0\nset ui_scene_fxon film\npopmenu 0\nwait 50\n"
    "globalwidgetcommand atticscene scenefly 1.8 %s\nwait 2100\nuiveil 1 0.35\nwait 400\nset ui_scene_fxon \"\"\nvstr ui_frPlayCmd\n"
    "wait 300\nuiveil 0 0.2\n" % SCR_POSE)
t, nl = rd(os.path.join(ui, "main.urc"))
fc = re.search(r'(?m)^scenehot "film" \S+ \S+ \S+ \S+ "([^"]*)"', t).group(1)
if not fc.startswith("set ui_frTransition "):
    n = t.count('"%s"' % fc)
    t = t.replace('"%s"' % fc, '"set ui_frTransition exec ui/hzm_frplay.cfg; %s"' % fc)
    wr(os.path.join(ui, "main.urc"), t, nl)
    print("main.urc: the film hotspot arms the framed PLAY (%d copies)" % n)
print("hzm_frplay.cfg: screen pose", SCR_POSE)

"""make_mpui.py [--mod DIR] [--ship-pk3 P] [--base-pk3 P] - the modernised multiplayer front-end (user 2026-11-02):
"modernize the server browser and the start game menus in the multiplayer lobbies. Use the same camera zoom to specific
places (armory, service record, join game, host game)".

Runs AFTER docs/proposals/mphub3d_2026-11-02/make_mphub3d.py (it reads the hub's Scene3D block out of ui/multiplayer.urc).
Idempotent; every splice sits between [mpui] markers and is removed before it is re-made.

What it writes (mod tree, CRLF like the rest of ui/):
  ui/hzm_mpui_scene_<dest>.inc   the SAME room (the hub's own models) at the pose the hub camera flies to, gated
                                 ui_atticActive==1, so the menu a hotspot opens draws "in" that place with no cut:
                                   join    -> the red door        (joingame: the new server browser)
                                   start   -> the game-type board (multiplayerstart: HOST GAME)
                                   host    -> the field desk (radio + phone) - coop_start flies board -> desk on show
                                   loadout -> the lockers         (mpoptions: ARMORY, Allied / Axis / Coop)
                                   record  -> the service record board (coop_sr)
  ui/joingame.urc                the server browser: one FAKKServerList in the engine's `hzmbrowser` mode (paper rows,
                                 map display names, INTERNET / LAN / FAVOURITES, live filters, search, favourites,
                                 a selection strip, direct connect, HZM coop server, instant action, network settings)
  ui/coop_start.urc + ui/coop_maps.inc   HOST A CO-OP GAME on the field-office sheet (every option of the old screen:
                                 13 campaigns as a pad-friendly list instead of the pull-down, the same mission tiles and
                                 cfgs, server name, password, max players, player health, LMS lives, dedicated + keep
                                 running, host rules, network settings, BEGIN FULL CAMPAIGN, APPLY -> mission_start.cfg)
  ui/multiplayerstart.urc        restyled in place (plates on a paper sheet; every button, rect and command unchanged)
  ui/coop_mp_options.urc         ARMORY - SELECT SIDE on paper (names / rects / commands unchanged)
  ui/coop_sr.urc                 one include line (the room behind the record); docs/tools/gen_service_record.py emits it too
  ui/multiplayer.urc             the four hub hotspots open their menus without the black dip (the menu shows the same
                                 frame) and come back with `sceneleave 1`; captions JOIN GAME / HOST GAME / ARMORY
  ui/hzm_mapnames.txt            map file -> display name for the browser (campaign names from ui/coop_start/*.cfg)
  global/localization_coop.txt   entries for every new multi-word string (no LOCALIZATION ERROR under developer 1)
Ship pk3: the menus3d pk3 (base) + scripts/hzm_mpui.shader + textures/mohmenu/hzm_theme/mpui_*.tga (hover glows)."""
import glob, io, math, os, re, sys, zipfile
import numpy as np
from PIL import Image, ImageFilter

H = os.path.dirname(os.path.abspath(__file__))


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


MOD = opt("--mod", r"C:\mohaa-coop-dev\hzm-mod-mpui")
BASE_PK3 = opt("--base-pk3", r"H:\hzm_work\mphub3d\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
SHIP_PK3 = opt("--ship-pk3", r"H:\hzm_work\mpui\ship\zzzzzzzzzzzzzz_hzm_menus3d.pk3")
STAGE = opt("--stage", r"H:\hzm_work\mpui\stage")
UI = os.path.join(MOD, "ui")
CRLF = "\r\n"

# ---------------------------------------------------------------- palette (the house paper kit: docs/tools/gen_menu_fieldsettings.py)
PAPER = (0.90, 0.86, 0.74, 1.0)
FOLDER = (0.58, 0.47, 0.29, 1.0)
TAB = (0.64, 0.53, 0.33, 1.0)
TABINK = (0.24, 0.15, 0.06, 1.0)
PLATE = (0.14, 0.10, 0.06, 0.94)
BEIGE = (0.90, 0.84, 0.66, 1.0)
INK = (0.16, 0.09, 0.03, 1.0)
RUST = (0.42, 0.22, 0.06, 1.0)
RULE = (0.42, 0.22, 0.06, 0.70)
MUTED = (0.36, 0.26, 0.15, 1.0)
STRIPE = (0.86, 0.82, 0.69, 1.0)
FIELD = (0.97, 0.95, 0.88, 1.0)
REDPLATE = (0.48, 0.10, 0.06, 0.97)
LAMP_ON = (0.98, 0.78, 0.28, 1.0)
LAMP_OFF = (0.34, 0.27, 0.17, 1.0)
CLEAR = (0.0, 0.0, 0.0, 0.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
GLOW = "textures/mohmenu/hzm_theme/mpui_glow"          # amber hover wash on plates
GLOW_P = "textures/mohmenu/hzm_theme/mpui_glow_paper"  # rust hover wash on paper rows
TILE_H = "textures/mohmenu/hzm_theme/mpui_tileframe"   # mission tile hover frame
LOC = set()                                            # strings that need a localization entry


def c4(c):
    return "%.2f %.2f %.2f %.2f" % c


def W(kind, name, rect, **kw):
    """one urc resource; kw order is kept (draw-relevant keys first)"""
    L = ["resource", kind, "{"]
    if "title" in kw and kw["title"] is not None:
        L.append('title "%s"' % kw["title"])
        t = kw["title"].replace("\\n", " ")
        if " " in t.strip() and not re.search(r"\d", t):
            LOC.add(t.strip())
    L.append('name "%s"' % name)
    L.append("rect %d %d %d %d" % tuple(rect))
    L.append("fgcolor " + c4(kw.get("fg", WHITE)))
    L.append("bgcolor " + c4(kw.get("bg", CLEAR)))
    L.append('borderstyle "%s"' % kw.get("border", "NONE"))
    for k in ("shader", "hovershader", "font", "textalign", "linkcvar", "clicksound", "stuffcommand", "hovercommand",
              "enabledcvar", "checked_shader", "unchecked_shader", "ordernumber", "extra"):
        if k in kw and kw[k] is not None:
            v = kw[k]
            if k in ("font", "textalign"):
                L.append("%s %s" % (k, v))
            elif k == "ordernumber":
                L.append("ordernumber %d" % v)
            elif k == "extra":
                L += v if isinstance(v, list) else [v]
            elif k in ("checked_shader", "unchecked_shader"):
                L.append('%s "%s"' % (k, v))
            else:
                L.append('%s "%s"' % (k, v))
    L.append("}")
    return L


def label(name, rect, bg=CLEAR, border="NONE", **kw):
    return W("Label", name, rect, bg=bg, border=border, **kw)


def text(name, rect, t, font, fg, align="left", **kw):
    return W("Label", name, rect, title=t, fg=fg, font=font, textalign=align, **kw)


def plate(name, rect, t, cmd, font="facfont-20", sound="sound/menu/apply.wav", bg=PLATE, fg=BEIGE, **kw):
    return W("Button", name, rect, title=t, fg=fg, bg=bg, border="3D_BORDER", font=font, hovershader=GLOW, clicksound=sound,
             stuffcommand=cmd, **kw)


def field(name, rect, cvar, font="verdana-14", extra=None, **kw):
    return W("Field", name, rect, fg=INK, bg=FIELD, border="INDENT_BORDER", font=font, textalign="left", clicksound="sound/menu/scroll.wav",
             linkcvar=cvar, extra=extra, **kw)


def toggle(name, rect, t, cvar):
    """a filter toggle row built from proven parts (the coop_hostrules recipe): ON and OFF plates gated by the cvar, a lamp,
    and the click sets the cvar to the other value. Gated-off widgets are click-transparent (HZM FindResponder)."""
    x, y, w, h = rect
    out = []
    out += W("Button", name + "On", rect, title=t, fg=BEIGE, bg=PLATE, border="3D_BORDER", font="verdana-12", textalign="center",
             hovershader=GLOW, clicksound="sound/menu/apply.wav", stuffcommand="set %s 0" % cvar, enabledcvar=cvar)
    out += W("Button", name + "Off", rect, title=t, fg=(0.62, 0.57, 0.45, 1.0), bg=(0.22, 0.17, 0.11, 0.94), border="3D_BORDER",
             font="verdana-12", textalign="center", hovershader=GLOW, clicksound="sound/menu/apply.wav", stuffcommand="set %s 1" % cvar,
             enabledcvar="!" + cvar)
    out += label(name + "LampOn", (x + 6, y + (h - 8) // 2, 8, 8), bg=LAMP_ON, enabledcvar=cvar)
    out += label(name + "LampOff", (x + 6, y + (h - 8) // 2, 8, 8), bg=LAMP_OFF, enabledcvar="!" + cvar)
    LOC.add(t)
    return out


def header(menu, extra=()):
    L = ['menu "%s" 640 480 NONE 0' % menu, "bgcolor 1 1 1 1", "borderstyle NONE", "bgfill 0 0 0 1", "fullscreen 1", "virtualres 1"]
    return L + list(extra)


def write(path, lines, note):
    body = CRLF.join(["// " + l for l in note] + lines) + CRLF
    open(path, "wb").write(body.encode("latin-1"))


def read(path):
    raw = open(path, "rb").read()
    assert raw.count(b"\r\n") == raw.count(b"\n"), path + " is not uniformly CRLF"
    return raw.decode("latin-1")


# ---------------------------------------------------------------- 1. the hub: models, poses, seamless hotspots
MP = os.path.join(UI, "multiplayer.urc")
mp = read(MP)
blk = mp[mp.index('name "hubscene"'):]
blk = blk[:blk.index("\r\n}\r\n")]
MODELS = re.findall(r'(?m)^scenemodel .*?(?=\r$)', blk)
assert len(MODELS) >= 5, MODELS
POSE = {}
for m in re.finditer(r'(?m)^scenehot "(\w+)" \S+ \S+ \S+ \S+ "([^"]*)"', blk):
    f = re.search(r"scenefly 0\.6 ((?:-?[\d.]+ ){6}-?[\d.]+)", m.group(2))
    POSE[m.group(1)] = f.group(1)
HOME = re.search(r"(?m)^scenecam (.*?)\r$", blk).group(1)
for k in ("join", "start", "loadout", "record"):
    assert k in POSE, k

# the field desk (chest of drawers with the radio + field telephone): an officer sets up the operation here.
# Engine units; desk top centre ~ (160, -114, 50) (hub bake "ch" bounds, x52.5). Looked down at from the room side.
DESK = "157.5 -42.0 91.9 29.06 -90.00 0.00 52.00"   # BU (0.80, 3.00, 1.75) looking +x BU (the desk front) down at its top (2.15, 3.00, 1.00)


def pose_vals(s):
    return [float(v) for v in s.split()]


SCENES = {"join": POSE["join"], "start": POSE["start"], "host": DESK, "loadout": POSE["loadout"], "record": POSE["record"]}


def scene_inc(dest):
    L = ["// [mpui] generated by docs/proposals/mpui_2026-11-02/make_mpui.py - do not hand-edit.",
         "// The 3D multiplayer room (the hub's own models) held at the pose the hub camera flies to for '%s', so this menu" % dest,
         "// opens IN that place (ui_atticActive 1 only; the flat background under it is the fallback).",
         "resource", "Scene3D", "{", 'name "mpui_scene_%s"' % dest, "rect 0 0 640 480", 'enabledcvar "ui_atticActive==1"'] + MODELS
    L += ["scenecam " + SCENES[dest], "}"]
    # a soft vignette of the room so the paper reads first (the scene stays visible around the sheet)
    L += label("mpui_scene_%s_dim" % dest, (-200, 0, 1040, 480), bg=(0.0, 0.0, 0.0, 0.28), enabledcvar="ui_atticActive==1",
                   extra="fadein 0.35")       # eased in, so the cut from the hub at the same pose stays invisible
    return L


for d in SCENES:
    write(os.path.join(UI, "hzm_mpui_scene_%s.inc" % d), scene_inc(d), [])

# hub hotspots: no black dip into the menu (it shows the same frame), `sceneleave 1` (no dip on the way back either)
SEAM = ("loadout", "join", "record", "start")
n_rep = 0
for k in SEAM:
    pat = re.compile(r'((?:scenehot "%s" \S+ \S+ \S+ \S+ ")|(?:stuffcommand "))([^"\r]*scenefly 0\.6 %s[^"\r]*)"' % (k, re.escape(POSE[k])))

    def fix(m):
        global n_rep
        c = m.group(2)
        c = c.replace("globalwidgetcommand hubscene sceneleave;", "globalwidgetcommand hubscene sceneleave 1;")
        c = c.replace("uiafter 0.45 uiveil 1 0.15; ", "").replace("; uiafter 0.62 uiveil 0 0.2", "")
        n_rep += 1
        return m.group(1) + c + '"'
    mp = pat.sub(fix, mp)
assert n_rep == 8, n_rep            # scenehot line + proxy button, per hotspot
for old, new in (("SERVER BROWSER", "JOIN GAME"), ("START GAME", "HOST GAME"), ("LOADOUTS", "ARMORY")):
    for q in ('"%s" "hub_h' % old, 'title "%s"' % old):
        mp = mp.replace(q, q.replace(old, new))
    assert mp.count(old) == 0 or old == "START GAME", (old, mp.count(old))
open(MP, "wb").write(mp.encode("latin-1"))
LOC.update(["JOIN GAME", "HOST GAME", "No server selected", "Pick a row, then JOIN - or double-click it."])  # + the engine-set ui_sbSel* idle text

# ---------------------------------------------------------------- 2. map display names
names = {}
for p in sorted(glob.glob(os.path.join(UI, "coop_start", "*.cfg"))):
    for m in re.finditer(r"(?m)^//([a-z0-9_/]+) - (.+?)\r?$", open(p, encoding="latin-1").read()):
        names[m.group(1)] = m.group(2).strip()
STOCK = {  # the retail multiplayer maps (names as the game's own map lists give them)
    "dm/mohdm1": "Southern France", "dm/mohdm2": "Destroyed Village", "dm/mohdm3": "Remagen", "dm/mohdm4": "The Crossroads",
    "dm/mohdm5": "Snowy Park", "dm/mohdm6": "Stalingrad", "dm/mohdm7": "Algiers",
    "obj/obj_team1": "The Hunt", "obj/obj_team2": "V2 Rocket Facility", "obj/obj_team3": "Omaha Beach", "obj/obj_team4": "The Bridge",
    "dm/mp_bahnhof_dm": "Bahnhof", "dm/mp_bazaar_dm": "Bazaar", "dm/mp_brest_dm": "Brest", "dm/mp_gewitter_dm": "Gewitter",
    "dm/mp_holland_dm": "Holland", "dm/mp_malta_dm": "Malta", "dm/mp_stadt_dm": "Stadt", "dm/mp_unterseite_dm": "Unterseite",
    "dm/mp_verschneit_dm": "Verschneit", "obj/mp_ardennes_tow": "Ardennes", "obj/mp_berlin_tow": "Berlin",
    "obj/mp_druckkammern_tow": "Druckkammern", "obj/mp_flughafen_tow": "Flughafen",
    "lib/mp_anzio_lib": "Anzio", "lib/mp_bizerteharbor_lib": "Bizerte Harbor", "lib/mp_ship_lib": "Bizerte Harbor (Ship)",
    "lib/mp_tunisia_lib": "Tunisian Desert", "obj/mp_bizertefort_obj": "Bizerte Fort", "obj/mp_bologna_obj": "Bologna",
    "obj/mp_castello_obj": "Castello", "obj/mp_kasserine_tow": "Kasserine Pass", "obj/mp_montebattaglia_tow": "Monte Battaglia",
    "obj/mp_montecassino_tow": "Monte Cassino", "obj/mp_palermo_obj": "Palermo",
    "co_lobby1": "Pre-mission Lobby",
}
names.update(STOCK)
# servers report the bare map name for briefing/ and dm/obj/lib maps ("mohdm7", "briefing1"): alias every unique base name
base_of = {}
for k in list(names):
    if "/" in k:
        base_of.setdefault(k.rsplit("/", 1)[1], []).append(k)
for b, ks in base_of.items():
    if len(ks) == 1 and b not in names:
        names[b] = names[ks[0]]
mn = ["// map file|display name - the server browser's MAP column (engine cl_uiserverlist.cpp HzmMapName). Generated by",
      "// docs/proposals/mpui_2026-11-02/make_mpui.py from ui/coop_start/*.cfg + the retail MP map list. Unknown maps fall back",
      "// to the file's base name, capitalised."] + ["%s|%s" % kv for kv in sorted(names.items())]
open(os.path.join(UI, "hzm_mapnames.txt"), "wb").write((CRLF.join(mn) + CRLF).encode("latin-1"))

# ---------------------------------------------------------------- 3. the server browser (joingame)
def sheet(tabtitle, title, folder=(14, 22, 612, 448), tabw=190):
    fx, fy, fw, fh = folder
    out = []
    out += label("folder", folder, bg=FOLDER, border="3D_BORDER")
    out += text("foldertab", (fx + 16, fy - 18, tabw, 22), tabtitle, "facfont-20", TABINK, "center", bg=TAB, border="3D_BORDER")
    out += label("paper", (fx + 10, fy + 10, fw - 20, fh - 20), bg=PAPER, border="3D_BORDER")
    out += label("titlePlate", (fx + 20, fy + 18, fw - 40, 26), bg=PLATE, border="3D_BORDER")
    out += text("titleText", (fx + 30, fy + 21, 300, 20), title, "facfont-20", BEIGE, "left")
    return out


J = header("joingame", ['escapecommand "popmenu 0"'])
J += ['include "ui/multiplayerback.inc"', 'include "ui/hzm_mpui_scene_join.inc"']
J += sheet("JOIN GAME", "SERVER ROSTER")
# tabs (title plate, right): the active one lit, the others dark
TABS = [("INTERNET", 0, 330, 84), ("LAN", 1, 418, 56), ("FAVOURITES", 2, 478, 118)]
for t, k, x, w in TABS:
    J += label("tabLit%d" % k, (x, 42, w, 22), bg=(0.42, 0.31, 0.14, 1.0), border="3D_BORDER", enabledcvar="ui_sbTab==%d" % k)
    J += W("Button", "tab%d" % k, (x, 42, w, 22), title=t, fg=BEIGE, bg=CLEAR, border="NONE", font="verdana-14", textalign="center",
           hovershader=GLOW, clicksound="sound/menu/apply.wav", stuffcommand="globalwidgetcommand hzmsrvlist hzmtab %d" % k)
    J += label("tabUnder%d" % k, (x + 6, 61, w - 12, 2), bg=LAMP_ON, enabledcvar="ui_sbTab==%d" % k)
# filters
J += toggle("fltCoop", (34, 72, 118, 20), "CO-OP ONLY", "ui_sbCoopOnly")
J += toggle("fltFull", (156, 72, 104, 20), "HIDE FULL", "ui_sbHideFull")
J += toggle("fltEmpty", (264, 72, 110, 20), "HIDE EMPTY", "ui_sbHideEmpty")
J += text("searchLbl", (384, 74, 56, 16), "SEARCH", "verdana-12", RUST, "right")
J += field("searchField", (444, 72, 162, 20), "ui_sbSearch", font="verdana-12", extra="SetMaxChars 24")
# the roster itself
J += W("FAKKServerList", "hzmsrvlist", (34, 98, 572, 222), fg=INK, bg=(0.88, 0.84, 0.71, 1.0), font="verdana-14",
       extra=["ordernumber 1", "hzmbrowser"])
J += label("listRule", (34, 320, 572, 1), bg=RULE)
J += W("Label", "statusLbl", (34, 322, 572, 14), fg=MUTED, font="verdana-12", textalign="left", linkcvar="ui_sbStatus")
# selection strip
J += label("selStrip", (34, 338, 572, 50), bg=STRIPE, border="INDENT_BORDER")
J += W("Label", "selName", (42, 341, 420, 18), fg=INK, font="facfont-20", textalign="left", linkcvar="ui_sbSelName")
J += W("Label", "selMap", (42, 359, 420, 14), fg=RUST, font="verdana-12", textalign="left", linkcvar="ui_sbSelMap")
J += W("Label", "selInfo", (42, 372, 440, 14), fg=MUTED, font="verdana-12", textalign="left", linkcvar="ui_sbSelInfo")
J += plate("favAdd", (478, 342, 122, 20), "FAVOURITE", "globalwidgetcommand hzmsrvlist hzmfav", font="verdana-12",
           enabledcvar="ui_sbHasSel !ui_sbSelFav")
J += plate("favDel", (478, 342, 122, 20), "UNPIN", "globalwidgetcommand hzmsrvlist hzmfav", font="verdana-12", enabledcvar="ui_sbHasSel ui_sbSelFav")
J += plate("joinSel", (478, 364, 122, 20), "JOIN", "globalwidgetcommand hzmsrvlist connect", font="facfont-20", bg=REDPLATE,
           enabledcvar="ui_sbHasSel")
# direct connect + quick links
J += text("addrLbl", (34, 396, 60, 18), "ADDRESS", "verdana-12", RUST, "left")
J += field("addrField", (96, 394, 156, 22), "ui_connectip", font="verdana-12", extra="SetIPField")
J += plate("addrGo", (256, 394, 78, 22), "CONNECT", "setreturnmenu;menuconnect ui_connectip", font="verdana-12")
J += plate("hzmCoop", (342, 394, 140, 22), "HZM CO-OP SERVER", "setreturnmenu;connect coop.hazardmodding.com", font="verdana-12")
J += plate("instant", (486, 394, 120, 22), "INSTANT ACTION", "pushmenu iamenu", font="verdana-12")
# bottom bar
J += plate("back", (34, 424, 96, 26), "BACK", "popmenu 0", sound="sound/menu/back.wav")
J += plate("netcfg", (136, 424, 170, 26), "NETWORK SETTINGS", "exec net_cl.cfg", font="verdana-12")
J += plate("refresh", (380, 424, 104, 26), "REFRESH", "globalwidgetcommand hzmsrvlist hzmrefresh")
J += plate("join", (490, 424, 116, 26), "JOIN", "globalwidgetcommand hzmsrvlist connect", bg=REDPLATE)
J += ["end."]
write(os.path.join(UI, "joingame.urc"), J,
      ["HZM coop - JOIN GAME: the server browser (user 2026-11-02 'modernize the server browser'). GENERATED by",
       "docs/proposals/mpui_2026-11-02/make_mpui.py - do not hand-edit. Replaces the retail three-button joingame menu;",
       "everything it had is here (LAN, internet, instant action) plus joininternetgame's direct connect / HZM server /",
       "network settings. The list is the engine's FAKKServerList in `hzmbrowser` mode (cl_uiserverlist.cpp [HZM mpui]):",
       "tabs hzmtab 0/1/2, live filters ui_sbCoopOnly / ui_sbHideFull / ui_sbHideEmpty / ui_sbSearch, favourites ui_sbFavs,",
       "selection -> ui_sbSel*. Opened in the 3D room at the red door (hzm_mpui_scene_join.inc)."])

# ---------------------------------------------------------------- 4. HOST A CO-OP GAME (coop_start + coop_maps.inc)
CAMPAIGNS = [("Training / Secret", "m0", None),
             ("1  Lighting the Torch", "m1", "ALLIED ASSAULT"), ("2  Scuttling the U-529", "m2", None), ("3  Operation Overlord", "m3", None),
             ("4  Behind Enemy Lines", "m4", None), ("5  The Day of the Tiger", "m5", None), ("6  Return to Schmerzen", "m6", None),
             ("1  Tunisia", "e1", "BREAKTHROUGH"), ("2  Sicily", "e2", None), ("3  Italy", "e3", None),
             ("1  Normandy", "t1", "SPEARHEAD"), ("2  Bastogne", "t2", None), ("3  Berlin", "t3", None)]
HOSTBACK = "globalwidgetcommand mpui_scene_host scenefly 0.45 %s; uiafter 0.45 popmenu 0" % POSE["start"]
C = header("coop_start", ['escapecommand "%s"' % HOSTBACK,
                          'showcommand "globalwidgetcommand mpui_scene_host scenecam %s; globalwidgetcommand mpui_scene_host scenereturn %s; '
                          'globalwidgetcommand mpui_scene_host scenefly 0.6 %s"' % (POSE["start"], DESK, DESK)])
C += ['include "ui/hzm_mpui_scene_host.inc"']
C += label("folder", (4, 22, 632, 450), bg=FOLDER, border="3D_BORDER")
C += text("foldertab", (20, 4, 236, 22), "HOST A CO-OP GAME", "facfont-20", TABINK, "center", bg=TAB, border="3D_BORDER")
C += label("paper", (10, 30, 620, 436), bg=PAPER, border="3D_BORDER")
C += label("titlePlate", (18, 36, 604, 24), bg=PLATE, border="3D_BORDER")
C += text("titleText", (26, 38, 200, 20), "OPERATION ORDERS", "facfont-20", BEIGE, "left")
C += W("Label", "coop_missionName", (232, 38, 382, 20), title="No Mission Selected", fg=BEIGE, font="facfont-20", textalign="right")
# column heads
for nm, x, w, t in (("Camp", 18, 156, "CAMPAIGN"), ("Miss", 182, 272, "MISSION"), ("Serv", 462, 160, "SERVER")):
    C += text("hdr" + nm, (x, 66, w, 18), t, "facfont-20", RUST, "left")
    C += label("rule" + nm, (x, 85, w, 1), bg=RULE)
# campaigns: a list, one button per campaign (pad-friendly; the pull-down's 13 commands), the picked one marked
y = 90
for i, (t, cfg, grp) in enumerate(CAMPAIGNS):
    if grp:
        y += 4
        C += text("grp" + cfg, (22, y, 150, 13), grp, "verdana-12", MUTED, "left")
        y += 14
    C += label("campLit%d" % (i + 1), (18, y, 156, 20), bg=(0.80, 0.70, 0.50, 1.0), enabledcvar="ui_coopCamp==%d" % (i + 1))
    C += label("campMark%d" % (i + 1), (18, y, 4, 20), bg=RUST, enabledcvar="ui_coopCamp==%d" % (i + 1))
    C += W("Button", "camp_" + cfg, (18, y, 156, 20), title=t, fg=INK, bg=CLEAR, border="NONE", font="verdana-12", textalign="left",
           hovershader=GLOW_P, clicksound="sound/menu/apply.wav", stuffcommand="set ui_coopCamp %d;exec ui/coop_start/%s.cfg" % (i + 1, cfg))
    y += 21
assert y <= 420, y
C += ['include "ui/coop_maps.inc"']
C += text("mapLbl", (182, 432, 66, 18), "MAP FILE", "verdana-12", RUST, "left")
C += field("mapField", (250, 430, 204, 20), "ui_dmmap", font="verdana-12")
# server column (hostRulesBtn keeps its rect: docs/tools/gen_menu_fieldsettings.py check pins it, and the HOST RULES sheet's
# CLOSE (530 422 78 24) must not land on anything clickable here)
C += W("Button", "hostRulesBtn", (490, 96, 142, 22), title="HOST RULES", fg=BEIGE, bg=PLATE, border="3D_BORDER", font="facfont-20",
       hovershader=GLOW, clicksound="sound/menu/apply.wav", stuffcommand="pushmenu coop_hostrules")
rows = [("Server name", "sv_hostname", 124, None), ("Password", "password", 160, None)]
for t, cv, yy, _ in rows:
    C += text("lbl_" + cv, (466, yy, 156, 13), t, "verdana-12", MUTED, "left")
    C += field("fld_" + cv, (466, yy + 13, 156, 20), cv, font="verdana-12")
for t, cv, yy in (("Max players", "sv_maxclients", 198), ("Player health", "coop_health", 222), ("LMS lives", "coop_lmsLives", 246)):
    C += text("lbl_" + cv, (466, yy + 3, 96, 14), t, "verdana-12", INK, "left")
    C += field("fld_" + cv, (566, yy, 56, 20), cv, font="verdana-12")
C += text("lbl_ded", (466, 273, 120, 14), "Dedicated server", "verdana-12", INK, "left")
C += W("CheckBox", "dedBox", (598, 270, 20, 20), fg=WHITE, bg=CLEAR, linkcvar="ui_dedicated",
       checked_shader="textures/menu/checkbox_checked", unchecked_shader="textures/menu/checkbox_unchecked")
C += text("coop_dedKeepLbl", (476, 295, 120, 14), "Keep it running", "verdana-12", INK, "left", enabledcvar="ui_dedicated")
C += W("CheckBox", "coop_dedKeepBox", (598, 292, 20, 20), fg=WHITE, bg=CLEAR, linkcvar="coop_dedKeep",
       checked_shader="textures/menu/checkbox_checked", unchecked_shader="textures/menu/checkbox_unchecked", enabledcvar="ui_dedicated")
C += plate("coop_serverNetConfigurationBtn", (466, 318, 156, 22), "NETWORK SETTINGS", "exec net_sv.cfg", font="verdana-12")
C += plate("coop_beginCampaignBtn", (466, 346, 156, 22), "BEGIN FULL CAMPAIGN", "wait 250;exec coop_mod/cfg/campaign_start.cfg",
           font="verdana-12", enabledcvar="!ui_dedicated")
C += plate("coop_beginCampaignDedBtn", (466, 346, 156, 22), "BEGIN FULL CAMPAIGN", "wait 250;exec coop_mod/cfg/coop_dedcampaign.cfg",
           font="verdana-12", enabledcvar="ui_dedicated")
C += plate("apply", (466, 374, 156, 34), "LAUNCH MISSION", "wait 250;exec coop_mod/cfg/mission_start.cfg", bg=REDPLATE,
           enabledcvar="!ui_dedicated")
C += plate("applyDedicated", (466, 374, 156, 34), "LAUNCH MISSION", "wait 250;coop_dedStart", bg=REDPLATE, enabledcvar="ui_dedicated")
C += W("Label", "coop_startPortInfo", (462, 412, 164, 44), title="To host, forward UDP ports\\n12203-12204 and\\n29253-29254", fg=MUTED,
       font="verdana-12", textalign="left", enabledcvar="!ui_dedicated")
C += W("Label", "coop_dedStatusLbl", (462, 412, 164, 44), title="", fg=MUTED, font="verdana-12", textalign="left", linkcvar="coop_dedStatus",
       enabledcvar="ui_dedicated")
C += plate("back", (18, 430, 96, 26), "BACK", HOSTBACK, sound="sound/menu/back.wav")
C += W("Label", "coop_startHzmInfo", (120, 452, 336, 12), title="MOH Trilogy Coop - based on the HaZardModding (HZM) Coop Mod", fg=MUTED,
       font="verdana-12", textalign="center")
C += ["end."]
write(os.path.join(UI, "coop_start.urc"), C,
      ["HZM coop - HOST A CO-OP GAME (coop_start). GENERATED by docs/proposals/mpui_2026-11-02/make_mpui.py - do not hand-edit.",
       "Every option of the earlier screen, on the field-office sheet: campaign list (was a pull-down; same 13 cfgs), mission",
       "tiles (ui/coop_maps.inc, driven by ui/coop_start/*.cfg exactly as before), server name, password, max players, player",
       "health, LMS lives, dedicated + keep running, HOST RULES (rect pinned by gen_menu_fieldsettings.py), network settings,",
       "BEGIN FULL CAMPAIGN and LAUNCH MISSION (apply -> coop_mod/cfg/mission_start.cfg -> start_server.cfg -> ui_startdmmap 2;",
       "dedicated twins -> coop_dedStart). 3D: the camera flies from the HOST GAME board to the field desk (radio + telephone)."])

# coop_maps.inc: the same 35 widgets (names / cvars / order), on a 3 x 4 grid of 82 px tiles
inc = read(os.path.join(UI, "coop_maps.inc"))
TX, TY, TS, TG = 186, 92, 82, 6


def tile_rect(i):
    r, c = divmod(i, 3)
    return TX + c * (TS + TG), TY + r * (TS + TG), TS, TS


M = []
M += W("Widget", "coop_startServerLogo", (238, 126, 168, 168), shader="textures/mohmenu/coop/hzm_coop_mod_logo")
M += W("Label", "coop_startMapSelect", (190, 300, 264, 60), title="1. Pick a campaign\\n2. Pick a mission\\n3. LAUNCH MISSION", fg=INK,
       font="verdana-14", textalign="left")
for i in range(11):
    r = tile_rect(i)
    M += W("Label", "coop_tileArtC%d" % (i + 1), r, linkcvar="coop_tileArt%d_c" % (i + 1), enabledcvar="ui_menuCenter",
           extra="linkcvartoshader")
    M += W("Label", "coop_tileArtS%d" % (i + 1), r, linkcvar="coop_tileArt%d_s" % (i + 1), enabledcvar="!ui_menuCenter",
           extra="linkcvartoshader")
    M += W("Button", "coop_startMap%d" % (i + 1), r, title="", fg=WHITE, bg=CLEAR, font="facfont-20", textalign="center", hovershader=TILE_H,
           clicksound="sound/menu/apply.wav")
assert sum(1 for l in M if l == "resource") == 35
write(os.path.join(UI, "coop_maps.inc"), M,
      ["HZM coop - mission tiles for ui/coop_start.urc. GENERATED by docs/proposals/mpui_2026-11-02/make_mpui.py.",
       "Each coop_startMapN Button is the click target; its art is drawn by the two Labels under it from the coop_tileArtN_c / _s",
       "cvars (ui_menuCenter 1 / 0) set by ui/coop_start/*.cfg (docs/proposals/mission_tile_art_2026-09-29/tools/gen_wiring.py)."])

# ---------------------------------------------------------------- 5. HOST GAME (multiplayerstart): restyled in place
MS = os.path.join(UI, "multiplayerstart.urc")
ms = read(MS)
ms = re.sub(r"// \[mpui\] begin.*?// \[mpui\] end\r\n", "", ms, flags=re.S)
ANCH = 'include "ui/serverback.inc"\r\n'
assert ms.count(ANCH) == 1
sheet_ms = ['// [mpui] begin: the room at the HOST GAME board + the paper sheet (generated by make_mpui.py)',
            'include "ui/hzm_mpui_scene_start.inc"']
sheet_ms += label("mpuiFolder", (40, 104, 560, 336), bg=FOLDER, border="3D_BORDER")
sheet_ms += label("mpuiPaper", (48, 112, 544, 320), bg=PAPER, border="3D_BORDER")
sheet_ms += label("mpuiTitlePlate", (40, 66, 560, 30), bg=PLATE, border="3D_BORDER", enabledcvar="ui_atticActive==1")
sheet_ms += text("mpuiTitle", (52, 70, 400, 22), "HOST GAME - SELECT THE GAME TYPE", "facfont-20", BEIGE, "left", enabledcvar="ui_atticActive==1")
sheet_ms += ["// [mpui] end"]
ms = ms.replace(ANCH, ANCH + CRLF.join(sheet_ms) + CRLF, 1)


def restyle(m):
    b = m.group(0)
    if "[mpui]" in b:
        return b
    nm = (re.search(r'(?m)^\s*name\s+"([^"]*)"', b) or [None, ""])[1]
    shader = re.search(r'(?m)^\s*shader\s+"([^"]*)"', b)
    if "\r\nLabel\r\n" in b[:20] and shader and ("selectgame" in shader.group(1)):
        # the wooden banner art: kept in the flat menu only
        if "ui_atticActive!=1" in b:
            return b
        if "enabledcvar" in b:
            return re.sub(r'(?m)^(\s*)enabledcvar\s+"([^"]*)"', lambda e: '%senabledcvar "%s ui_atticActive!=1"' % (e.group(1), e.group(2)), b)
        return b[:-3] + 'enabledcvar "ui_atticActive!=1"\r\n}\r\n'
    if "\r\nButton\r\n" in b[:20]:
        primary = nm == "coopmodstart"
        b = re.sub(r'(?m)^(\s*)shader\s+"textures/mohmenu/weapon_sign"\r\n', "", b)
        b = re.sub(r'(?m)^(\s*)hovershader\s+"[^"]*"', r'\1hovershader "%s"' % GLOW, b)
        b = re.sub(r'(?m)^(\s*)fgcolor\s+[\d. ]+', r"\1fgcolor " + c4(BEIGE), b)
        b = re.sub(r'(?m)^(\s*)bgcolor\s+[\d. ]+', r"\1bgcolor " + c4(REDPLATE if primary else PLATE), b)
        if "borderstyle" not in b:
            b = b.replace("\r\n{\r\n", '\r\n{\r\n\tborderstyle "3D_BORDER"\r\n', 1)
        if nm == "Default" and "textures/mohmenu/back" in b:       # BACK: a plate like every other screen's
            b = re.sub(r'(?m)^\s*shader\s+"textures/mohmenu/back"\r\n', "", b)
            b = re.sub(r'(?m)^(\s*)hovershader\s+"[^"]*"', r'\1hovershader "%s"' % GLOW, b)
            b = b.replace("\r\n{\r\n", '\r\n{\r\n\ttitle "BACK"\r\n\tfont facfont-20\r\n', 1)
        return b
    if "\r\nLabel\r\n" in b[:20] and nm in ("hdrHzmModes", "hdrStockModes"):
        return re.sub(r'(?m)^(\s*)fgcolor\s+[\d. ]+', r"\1fgcolor " + c4(RUST), b)
    return b


ms = re.sub(r"resource\r\n\w+\r\n\{\r\n.*?\r\n\}\r\n", restyle, ms, flags=re.S)
for tt in re.findall(r'(?m)^\s*title\s+"([^"]*)"', ms):     # the mode names never had entries (LOCALIZATION ERROR under developer 1)
    if " " in tt.strip() and not re.search(r"\d", tt):
        LOC.add(tt.strip())
assert ms.count(GLOW) >= 22, ms.count(GLOW)
open(MS, "wb").write(ms.encode("latin-1"))
LOC.update(["HOST GAME - SELECT THE GAME TYPE"])

# ---------------------------------------------------------------- 6. ARMORY - SELECT SIDE (mpoptions)
O = ['menu "mpoptions" 640 479 NONE 0', "bgcolor 1 1 1 1", "borderstyle NONE", "bgfill 0 0 0 1", "fullscreen 1", "virtualres 1",
     'include "ui/multiplayerback.inc"', 'include "ui/hzm_mpui_scene_loadout.inc"']
O += label("folder", (156, 120, 328, 248), bg=FOLDER, border="3D_BORDER")
O += text("foldertab", (172, 102, 150, 22), "ARMORY", "facfont-20", TABINK, "center", bg=TAB, border="3D_BORDER")
O += label("bg_panel", (164, 128, 312, 232), bg=PAPER, border="3D_BORDER")
O += label("titlePlate", (172, 136, 296, 26), bg=PLATE, border="3D_BORDER")
O += W("Label", "caption", (172, 139, 296, 20), title="SELECT SIDE", fg=BEIGE, font="facfont-20", textalign="xcenter")
for nm, t, x, cmd in (("allied", "ALLIED", 180, "exec ui/coop_mpa_armory/dopen.cfg"), ("axis", "AXIS", 276, "exec ui/coop_mpx_armory/dopen.cfg"),
                      ("coop", "COOP", 372, "exec ui/loadout/open.cfg")):
    O += plate(nm, (x, 200, 88, 28), t, cmd)
O += plate("mprecord", (208, 234, 224, 22), "MP SERVICE RECORD",
           "set coop_mpSrP0 1;set coop_mpSrP1 0;set coop_mpSrP2 0;set coop_mpSrP3 0;set coop_mpSrP4 0;set coop_mpSrP5 0;pushmenu coop_mp_record",
           font="verdana-12")
O += W("Label", "hint", (168, 268, 304, 16), title="In a match, F7 opens your side's armory", fg=MUTED, font="verdana-12", textalign="xcenter")
O += W("Label", "nameLabel", (176, 301, 44, 18), title="Name", fg=INK, font="verdana-12")
O += W("Field", "nameField", (220, 298, 248, 24), title="nameentry", fg=INK, bg=FIELD, border="INDENT_BORDER", clicksound="sound/menu/scroll.wav",
       linkcvar="ui_name", font="facfont-20", textalign="left", extra="SetMaxChars 20")
O += plate("back", (8, 448, 96, 24), "BACK", "Popmenu 1", sound="sound/menu/back.wav")
O += ["end."]
write(os.path.join(UI, "coop_mp_options.urc"), O,
      ["HZM coop - ARMORY / LOADOUTS - SELECT SIDE (mpoptions). GENERATED by docs/proposals/mpui_2026-11-02/make_mpui.py -",
       "do not hand-edit. Names, rects and commands are the earlier screen's; restyled onto the paper kit and opened in the 3D",
       "room at the lockers (hzm_mpui_scene_loadout.inc)."])

# ---------------------------------------------------------------- 7. SERVICE RECORD: the room behind the record
SR = os.path.join(UI, "coop_sr.urc")
sr = read(SR)
LINE = 'include "ui/hzm_mpui_scene_record.inc"\r\n'
if LINE not in sr:
    A2 = "direction from_top 0\r\n"
    assert sr.count(A2) == 1
    sr = sr.replace(A2, A2 + LINE, 1)
    open(SR, "wb").write(sr.encode("latin-1"))

# ---------------------------------------------------------------- 8. localization
LP = os.path.join(MOD, "global", "localization_coop.txt")
lt = open(LP, "rb").read().decode("latin-1")
nl = "\r\n" if "\r\n" in lt else "\n"
lt = re.sub(r"//\[mpui\] begin.*?//\[mpui\] end\r?\n", "", lt, flags=re.S)
have = set(re.findall(r'\{ "([^"]*)" "', lt))
add = sorted(s for s in LOC if s not in have)
if add:
    lt = lt.rstrip("\r\n") + nl + "//[mpui] begin: the server browser / host / armory screens (make_mpui.py)" + nl
    lt += nl.join('{ "%s" "%s" }' % (s, s) for s in add) + nl + "//[mpui] end" + nl
open(LP, "wb").write(lt.encode("latin-1"))

# ---------------------------------------------------------------- 9. art + ship pk3
os.makedirs(os.path.join(STAGE, "textures", "mohmenu", "hzm_theme"), exist_ok=True)
os.makedirs(os.path.join(STAGE, "scripts"), exist_ok=True)


def glow(path, rgb, a0, a1, w=128, h=32):
    """a soft hover wash: alpha a0 at the edges rising to a1 in the middle (no hard rectangle edge)"""
    y = np.linspace(-1, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    k = np.clip(1.0 - np.maximum(np.abs(x) ** 6, np.abs(y) ** 4), 0, 1)
    a = (a0 + (a1 - a0) * k) * 255
    img = np.zeros((h, w, 4), np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = rgb
    img[..., 3] = a.astype(np.uint8)
    Image.fromarray(img, "RGBA").save(path)


T = os.path.join(STAGE, "textures", "mohmenu", "hzm_theme")
glow(os.path.join(T, "mpui_glow.tga"), (255, 196, 92), 0.10, 0.32)
glow(os.path.join(T, "mpui_glow_paper.tga"), (150, 72, 20), 0.10, 0.26)
# the tile hover frame: a 3 px rust rule inside a 1 px amber line, transparent centre
fr = np.zeros((128, 128, 4), np.uint8)
fr[:, :, :3] = (122, 40, 14)
for d in range(5):
    fr[d, :, 3] = fr[-1 - d, :, 3] = fr[:, d, 3] = fr[:, -1 - d, 3] = 235
fr[5:7, 5:-5, :3] = fr[-7:-5, 5:-5, :3] = (250, 200, 72)
fr[5:-5, 5:7, :3] = fr[5:-5, -7:-5, :3] = (250, 200, 72)
fr[5:7, 5:-5, 3] = fr[-7:-5, 5:-5, 3] = fr[5:-5, 5:7, 3] = fr[5:-5, -7:-5, 3] = 220
Image.fromarray(fr, "RGBA").save(os.path.join(T, "mpui_tileframe.tga"))
sh = []
for n in ("mpui_glow", "mpui_glow_paper", "mpui_tileframe"):
    sh += ["textures/mohmenu/hzm_theme/%s" % n, "{", "\tnomipmaps", "\tnopicmip", "\t{", "\t\tmap textures/mohmenu/hzm_theme/%s.tga" % n,
           "\t\tblendFunc blend", "\t}", "}", ""]
open(os.path.join(STAGE, "scripts", "hzm_mpui.shader"), "w", newline="\n").write("// [mpui] hover art for the multiplayer front-end (make_mpui.py)\n" + "\n".join(sh))

os.makedirs(os.path.dirname(SHIP_PK3), exist_ok=True)
base = zipfile.ZipFile(BASE_PK3)
have = set(base.namelist())
add = []
for root, _d, fs in os.walk(STAGE):
    for fn in fs:
        p = os.path.join(root, fn)
        add.append((p, os.path.relpath(p, STAGE).replace("\\", "/")))
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
print("hub hotspots made seamless: %d; scenes: %s" % (n_rep, ", ".join(sorted(SCENES))))
print("map names: %d; localization strings: %d" % (len(names), len(LOC)))
print("ship pk3 %s (%d bytes, +%d mpui files)" % (SHIP_PK3, os.path.getsize(SHIP_PK3), len(add)))

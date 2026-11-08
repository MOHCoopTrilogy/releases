#!/usr/bin/env python3
"""gen_weapon_viewer.py - the attic WEAPON VIEWER (the rifle rack, v1.10.63), generated from the code and data.

    python docs/tools/gen_weapon_viewer.py build [--inventory <inventory.json>]   # write the files into HZM_MOD
    python docs/tools/gen_weapon_viewer.py check [...]                            # regenerate in memory, byte-compare (exit 1 = drift)
    python docs/tools/gen_weapon_viewer.py list                                   # print every entry (harness input)

WHY GENERATED. The viewer shows every gun the mod ships, every finish and every model variant, with its name, how to
unlock it and who made it. All of that already exists in the code; a hand-kept copy would rot the first time a gun, a
challenge target or a variant changes. Every fact below is read from the source that ENFORCES it:

  guns         coop_mod/loadoutroster.scr   level.coop_loRoster{Id,Give,Tab}[i] - the server's armory roster, in order
  name / pose  ui/loadout/p<id>.cfg         coop_loNm, coop_loCd, coop_loPrev (the model the Armory previews),
                                            coop_loXfmHero (the Armory hero pose: its angles are the viewer's base pose)
  variants     coop_mod/loadoutskins.scr    coop_skinGive[give][fid] (1-7 finishes, 8+ model variants), names
  unlocks      xp.scr rank grants, challenges.scr rewards, loadoutpick.scr free starters (armory_unlocks.py parsers),
               finchal_gen.scr (per-gun finish ladders), mvchal_gen.scr (per-variant challenges) + the mastery gate
  status       the client's archived cvars: coop_loLkA<id> (armory padlock), coop_uiD<i> / coop_uiN<i> (challenge done /
               progress, i = the Service Record index = chal_def order in challenges.scr + mvchal_gen.scr)
  credits      hzm_credits.txt + docs/SKIN_CREDITS.md, distilled in weapon_history.tsv "credit:" rows; the author in a
               variant's name "(AUTHOR)"; the first pak that ships a tik / the pak whose texture wins (weapon_hd inventory)
  history      docs/tools/weapon_history.tsv - the one AUTHORED input (prose). A roster gun without a row fails the build.

OUTPUT (HZM_MOD = a mod tree, default <repo>/hzm-mohaa-coop-mod):
  ui/wpnview/e<NNN>.cfg  one page per entry: sets the ui_wv* cvars the menu shows, prev / next pointers
  ui/wpnview/t<k>.cfg    a category tab: jump to its first gun;  ui/wpnview/open.cfg (menu open), z<k>.cfg (zoom steps)
  ui/hzm_wpnview.urc     the viewer menu: the attic at the rack (its own Scene3D), the paper sheet, the orbit model
  ui/main.urc            the attic's "rack" hotspot: added if absent, else its command is pointed at the viewer
  ui/hzm_attic_go_rack.cfg  test shortcut (the hotspot without a cursor)
"""
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
os.environ["HZM_MOD"] = MOD
sys.path.insert(0, HERE)
import armory_unlocks as au  # noqa: E402

WHD = os.path.join(ROOT, "docs", "proposals", "weapon_hd_2026-10-05", "tools")
M3D = os.path.join(ROOT, "docs", "proposals", "kickoff_2026-10-18", "menus3d")
FIXES = os.path.join(ROOT, "docs", "tools", "assets", "fixes")
WPNFIX = os.path.join(ROOT, "docs", "tools", "assets", "wpnfix")     # [v1.10.64 wpnfix2] new tiks ride the wpnfix pak
HIST = os.path.join(HERE, "weapon_history.tsv")
CRLF = "\r\n"


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


INVENTORY = arg("--inventory", os.path.join(ROOT, "docs", "proposals", "wpnviewer_2026-11-04", "inventory.json"))


def rd(rel):
    return io.open(os.path.join(MOD, rel), encoding="latin-1", newline="").read()


def scr(rel):
    return au.strip_comments(rd(rel))


def clean(s):
    """safe inside a quoted cfg / urc string: ASCII, no quotes / semicolons / braces / newlines (TRAPS T1, T2)"""
    s = au.sanitise(s).replace(";", ",").replace("{", "(").replace("}", ")")
    return s


# ---------------------------------------------------------------- font metrics (exact: the RitualFont the menu draws with)
def font_widths(name):
    sys.path.insert(0, WHD)
    import vfs  # noqa: E402
    t = vfs.read("fonts/%s.ritualfont" % name).decode("latin-1")
    ind = [int(x) for x in re.search(r"indirections\s*\{([^}]*)\}", t).group(1).split()]
    locs = re.findall(r"\{\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\}", t[t.index("locations"):])
    h = float(re.search(r"height\s+(\S+)", t).group(1))
    w = {}
    for c in range(32, 127):
        i = ind[c] if c < len(ind) else -1
        w[chr(c)] = float(locs[i][2]) if 0 <= i < len(locs) else h * 0.5
    return w


FW = {}


def width(text, font="verdana-12"):
    if font not in FW:
        FW[font] = font_widths(font)
    return sum(FW[font].get(ch, 6.0) for ch in text)


def wrap(text, px, font="verdana-12"):
    out, cur = [], ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if width(t, font) <= px:
            cur = t
        else:
            if cur:
                out.append(cur)
            cur = wd
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- 1. the roster and the Armory pages
roster = scr("coop_mod/loadoutroster.scr")
RID = {int(i): v for i, v in re.findall(r'level\.coop_loRosterId\[(\d+)\]\s*=\s*"([^"]+)"', roster)}
RGIVE = {int(i): v for i, v in re.findall(r'level\.coop_loRosterGive\[(\d+)\]\s*=\s*"([^"]+)"', roster)}
RTAB = {int(i): int(v) for i, v in re.findall(r'level\.coop_loRosterTab\[(\d+)\]\s*=\s*(\d+)', roster)}
assert RID and set(RID) == set(RGIVE) == set(RTAB), "loadoutroster.scr roster arrays disagree"
# v1.10.64: the Mills bomb's 2D-icon stand-in is gone - its shader is fixed (gen_wpnfix_pak.py: scripts/coop_wpnfix.shader maps
# an RGB copy of the sheet; the stock sheet's alpha is ~0 everywhere and the model drew black), so every gun shows its model
ICON2D = ()
TABS = ["RIFLES", "SNIPERS", "SMGS", "HEAVY", "PISTOLS", "GRENADES"]


def page(gid):
    p = os.path.join(MOD, "ui", "loadout", "p%s.cfg" % gid)
    assert os.path.exists(p), "no Armory page " + p
    return dict(re.findall(r'(?m)^set (\w+) "([^"]*)"', io.open(p, encoding="latin-1").read()))


# ---------------------------------------------------------------- 2. variants
skins = scr("coop_mod/loadoutskins.scr")
GIVE = {}
for b, f, v in re.findall(r'coop_skinGive\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', skins):
    GIVE.setdefault(b.lower(), {})[int(f)] = v
FINNAME = {int(f): n for f, n in re.findall(r'coop_skinFinName\[(\d+)\]\s*=\s*"([^"]+)"', skins)}
MVNAME = {(b.lower(), int(f)): n for b, f, n in re.findall(r'coop_skinMvName\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', skins)}

# ---------------------------------------------------------------- 3. challenges, ranks, finish and variant ladders
chal_src = scr("coop_mod/challenges.scr")
mv_src = scr("coop_mod/mvchal_gen.scr")
fin_src = scr("coop_mod/finchal_gen.scr")
CHAL_RX = re.compile(r'chal_def\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+"([^"]*)"\s+(\d+)\s+"([^"]*)"')
SR_ROWS = [m.groups() for m in CHAL_RX.finditer(chal_src + "\n" + mv_src)]      # the Service Record order (gen_service_record.py)
SR_IDX = {r[0]: i for i, r in enumerate(SR_ROWS)}
CHAL = {r[0]: r for r in SR_ROWS}
for m in CHAL_RX.finditer(fin_src):
    CHAL[m.group(1)] = m.groups()
MVCHAL = {(b.lower(), int(f)): c for b, f, c in re.findall(r'coop_skinMvChal\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', mv_src)}
MVTOK = {(b.lower(), int(f)): t.lower() for b, f, t in re.findall(r'coop_skinMvTok\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', mv_src)}
MVELITE = {b.lower(): c for b, c in re.findall(r'coop_skinMvElite\["([^"]+)"\]\s*=\s*"([^"]+)"', skins)}
FINCID = {(w, int(f)): c for w, f, c in re.findall(r'coop_finCid\["([^"]+)"\]\[(\d+)\]\s*=\s*"([^"]+)"', fin_src)}
xp = scr("coop_mod/xp.scr")
RANKNAME = au.rank_names(xp)
RANK = {}
for r, tok in au.rank_grants(xp):
    RANK[tok.lower()] = min(r, RANK.get(tok.lower(), r))
REWARDS = au.chal_rewards(chal_src + "\n" + mv_src)
FREE = {t.lower() for t in au.free_guns(scr("coop_mod/loadoutpick.scr"))}
_wf = re.search(r"(?ms)^chal_widFromModel\b.*?^\}end", chal_src).group(0)
WIDCHAIN = re.findall(r'containsText local\.m "([^"]+)" 0 \)\{ local\.wid = "([^"]+)" \}', _wf)
assert len(WIDCHAIN) > 40, "chal_widFromModel chain not parsed"


def wid_of(model):
    m = model.lower()
    for tok, w in WIDCHAIN:
        if tok.lower() in m:
            return w
    return ""


def cond(desc):
    d = clean(desc)
    d = re.sub(r"\s+to unlock\b.*$", "", d)
    return d


# ---------------------------------------------------------------- 4. authored text: histories, notes, credits
HISTORY, CREDIT = {}, {}
for ln in io.open(HIST, encoding="utf-8"):
    if ln.startswith("#") or not ln.strip():
        continue
    k, v = ln.rstrip("\r\n").split("\t", 1)
    assert v == clean(v), "weapon_history.tsv row %s has a character the cfg cannot carry" % k
    (CREDIT if k.startswith("credit:") else HISTORY)[k.replace("credit:", "")] = v

# the first pak that ships a file = where it came from; the pak whose texture wins = whose art is on screen
INV = {}
if os.path.exists(INVENTORY):
    for e in json.load(io.open(INVENTORY, encoding="utf-8")):
        INV[e["tik"].lower()] = e
ORIGIN = []           # (pak name test, credit line)
ORIGIN_PAK = [
    (re.compile(r"xw_weapons", re.I), "Model: Soares93 (Extra WW2 Weapons pack)"),
]
TEX_PAK = [(re.compile(r"HRRTM", re.I), "Textures: czwarty_ (Hi-Res Realism Texture mod)")]
STOCK = [(re.compile(r"^main/pak\d+\.pk3$", re.I), "Medal of Honor: Allied Assault"), (re.compile(r"^mainta/pak\d+\.pk3$", re.I), "MOHAA Spearhead"),
         (re.compile(r"^maintt/pak\d+\.pk3$", re.I), "MOHAA Breakthrough")]       # the retail paks only
_vfs = None


def vfs():
    global _vfs
    if _vfs is None:
        sys.path.insert(0, WHD)
        import vfs as v  # noqa: E402
        v.index()
        _vfs = v
    return _vfs


def first_pak(vpath):
    lst = vfs().index().get(vpath.lower())
    if not lst:
        return ""
    p = lst[0][0].replace("\\", "/")
    return "/".join(p.split("/")[-2:])


AUTHORS = {"ACME313": "acme313", "EAST": "East", "LEON": "Leon", "GUANSHIRE": "Guanshire", "HOBBS": "Hobbs", "DIRTYHARRY": "DirtyHarry",
           "STLKID": "stlkid", "DARKANGEL": "DaRKaNGeL", "DR.DELETO": "Dr.Deleto", "FLAKRIDER": "FlakRider", "STATIC": "Static",
           "SCHUTZE": "Schutze", "HOBBS & RECOIL": "Hobbs and Recoil"}
PACKS = {"MOH:PA": "a Medal of Honor: Pacific Assault port"}


def name_author(vname):
    """the author named in a variant label '... (AUTHOR)' - only names in AUTHORS / PACKS count: '(REACTIVATED)' is a
    description, not a person"""
    groups = re.findall(r"\(([^)]*)\)", vname)
    out = []
    for g in groups:
        if g in AUTHORS:
            out.append("Skin / model: " + AUTHORS[g])
        elif g in PACKS:
            out.append("Port: " + PACKS[g])
    return out


def credits_for(gid, model, vstem, fid):
    lines = []
    if vstem and vstem in CREDIT:
        lines += CREDIT[vstem].split(" | ")
    elif fid >= 8:
        lines += name_author(MVNAME.get((GIVE_OF[gid], fid), ""))
    if fid == 0 or (fid >= 8 and not lines):
        if gid in CREDIT:
            lines += CREDIT[gid].split(" | ")
    e = INV.get(model.lower())
    fp = first_pak(model)
    for rx, line in ORIGIN_PAK:
        if rx.search(fp) or (e and rx.search(e.get("tikpak", ""))):
            lines.append(line)
    if e:
        won = {t.get("info", {}).get("pak", "") for s in e.get("surfaces", []) for t in s.get("textures", [])}
        for rx, line in TEX_PAK:
            if any(rx.search(p) for p in won):
                lines.append(line)
    if not lines:
        bp = first_pak(BASEMODEL_OF[gid])           # a finish / skin of a stock gun is still the stock mesh
        for rx, nm in STOCK:
            if rx.search(fp) or rx.search(bp):
                lines.append("Stock %s model" % nm)
                break
    if 1 <= fid <= 7:
        lines.append("Finish: made for the HZM Coop Mod")
    seen, out = set(), []
    for l in lines:
        if l not in seen:
            seen.add(l)
            out.append(clean(l))
    return out


# ---------------------------------------------------------------- 5. the entries
GIVE_OF, BASEMODEL_OF = {}, {}
entries = []          # dicts, in viewer order: tab, roster order, base / finishes / variants
guns = []
for i in sorted(RID, key=lambda i: (RTAB[i], i)):
    gid, give, tab = RID[i], RGIVE[i], RTAB[i]
    pg = page(gid)
    GIVE_OF[gid] = give.lower()
    if gid not in HISTORY:
        raise SystemExit("weapon_history.tsv has no history for roster gun %s (%s)" % (gid, give))
    model = pg.get("coop_loPrev") or give
    BASEMODEL_OF[gid] = model
    xfm = pg.get("coop_loXfmHero") or pg.get("coop_loXfmW") or "0 0 0 1 0 270 180"
    g = {"gid": gid, "give": give, "tab": tab, "name": clean(pg.get("coop_loNm", gid)), "cd": clean(pg.get("coop_loCd", "")),
         "model": model, "xfm": xfm, "entries": []}
    guns.append(g)
    var = GIVE.get(give.lower(), {})
    for fid in [0] + sorted(var):
        tik = model if fid == 0 else var[fid]
        stem = os.path.splitext(os.path.basename(tik))[0].lower()
        if fid == 0:
            vname = "STANDARD ISSUE"
        elif fid <= 7:
            vname = "%s FINISH" % FINNAME.get(fid, str(fid))
        else:
            vname = MVNAME.get((give.lower(), fid), stem.upper())
        e = {"g": g, "fid": fid, "tik": tik, "stem": stem, "vname": clean(vname)}
        g["entries"].append(e)
        entries.append(e)
for n, e in enumerate(entries):
    e["n"] = n + 1

# every mv: / fin: / credit: key must name something that exists (a typo would silently drop a note)
_stems = {e["stem"] for e in entries}
for k in list(HISTORY) + list(CREDIT):
    if k.startswith("mv:"):
        assert k[3:] in _stems, "weapon_history.tsv: no variant " + k
    elif k.startswith("fin:"):
        assert int(k[4:]) in FINNAME, "weapon_history.tsv: no finish " + k
    elif re.match(r"^\d\d$", k):
        pass                              # a retired gun keeps its row (v1.10.64: 71, the gold Thompson) so an older roster still builds
    else:
        assert k in _stems, "weapon_history.tsv: unknown key " + k


def unlock(e):
    """(lines of 'how to unlock' text, status spec). status: ('free',) | ('gun', gid, sr_index or None) |
    ('mv', sr_index, mastery sr_index or None) | ('text', words)"""
    g, fid = e["g"], e["fid"]
    give = g["give"].lower()
    if fid == 0:
        if give in FREE:
            return ["Free: in every soldier's kit from the start."], ("free",)
        ways, chal_idx = [], None
        if give in RANK:
            r = RANK[give]
            ways.append("Reach rank %d, %s." % (r, clean(RANKNAME.get(r, ""))))
        for cid, title, desc, rw in REWARDS:
            if rw.lower() == give:
                ways.append("Challenge %s: %s." % (clean(title), cond(desc)))
                if chal_idx is None and cid in SR_IDX:
                    chal_idx = SR_IDX[cid]
        if not ways:
            ways = ["Not currently obtainable."]
        if len(ways) > 2:
            ways = ways[:2] + ["(or %d other way%s)" % (len(ways) - 2, "" if len(ways) == 3 else "s")]
        return ways, ("gun", g["gid"], chal_idx)
    wid = wid_of(give)
    if fid <= 7:
        cid = FINCID.get((wid, fid))
        if cid and cid in CHAL:
            c = CHAL[cid]
            return (["%s (challenge %s)." % (cond(c[3]), clean(c[2])), "Needs the gun unlocked first."],
                    ("text", "Progress: Armory finish chips, in a game."))
        return (["The old account-wide %s reward is retired, players who earned it keep it on mastered guns." % FINNAME[fid].lower()],
                ("text", "Not obtainable for new players."))
    tok = MVTOK.get((give, fid))
    if tok:
        # [v1.10.64 wpnfix2] a TOKEN-gated variant (coop_skinMvTok): open with that token, no mastery rule
        if tok in RANK:
            r = RANK[tok]
            return ["Reach rank %d, %s." % (r, clean(RANKNAME.get(r, "")))], ("text", "Progress: your rank, in the Service Record.")
        return ["Not currently obtainable."], ("text", "")
    cid = MVCHAL.get((give, fid)) or MVELITE.get(give)
    lines, sidx = [], None
    if cid and cid in CHAL:
        c = CHAL[cid]
        lines.append("%s." % cond(c[3]))          # the challenge title is a generic "<gun> Variant n": the condition says it all
        sidx = SR_IDX.get(cid)
    else:
        lines.append("Not currently obtainable.")
    mid = None
    if wid and ("wpn_" + wid) in CHAL:
        c = CHAL["wpn_" + wid]
        lines.append("Master the gun first: %s." % re.sub(r"^Get ", "", cond(c[3])))
        mid = SR_IDX.get("wpn_" + wid)
    return lines, ("mv", sidx, mid)


# ---------------------------------------------------------------- 6. layout (640 x 480 virtual, the mpui paper kit)
PAPER = (0.90, 0.86, 0.74, 1.0)
FOLDER = (0.58, 0.47, 0.29, 1.0)
TAB = (0.64, 0.53, 0.33, 1.0)
TABINK = (0.24, 0.15, 0.06, 1.0)
PLATE = (0.14, 0.10, 0.06, 0.94)
BEIGE = (0.90, 0.84, 0.66, 1.0)
INK = (0.16, 0.09, 0.03, 1.0)
RUST = (0.42, 0.22, 0.06, 1.0)
MUTED = (0.36, 0.26, 0.15, 1.0)
GREEN = (0.13, 0.36, 0.12, 1.0)
RED = (0.55, 0.10, 0.06, 1.0)
SEL = (0.42, 0.22, 0.06, 0.22)
FELT = (0.11, 0.10, 0.08, 1.0)
CLEAR = (0.0, 0.0, 0.0, 0.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
GLOW = "textures/mohmenu/hzm_theme/mpui_glow"
GLOW_P = "textures/mohmenu/hzm_theme/mpui_glow_paper"

LIST = (34, 98, 176, 14)          # x y w row-h of the gun list: wide enough for the longest roster name at every aspect (asserted)
VIEW = (216, 98, 246, 250)        # the orbit viewer
RIGHT = (470, 98, 136)            # the info column
HIST_Y, HIST_W, HIST_N = 398, 566, 4
# the @3x fonts the engine swaps in at high resolutions run up to ~10 % wider than the 1x metrics measured here (seen at 1440x1080):
# every wrap / fit keeps that margin
FIT = 0.88
RIGHT_W = (RIGHT[2] - 2) * FIT
N_CRED, N_UNL = 4, 7


def c4(c):
    return "%.2f %.2f %.2f %.2f" % c


def W(kind, name, rect, **kw):
    L = ["resource", kind, "{"]
    if kw.get("title") is not None:
        L.append('title "%s"' % kw["title"])
    L.append('name "%s"' % name)
    L.append("rect %s %s %s %s" % tuple(("%g" % v) for v in rect))
    L.append("fgcolor " + c4(kw.get("fg", WHITE)))
    L.append("bgcolor " + c4(kw.get("bg", CLEAR)))
    L.append('borderstyle "%s"' % kw.get("border", "NONE"))
    for k in ("shader", "hovershader", "font", "textalign", "linkcvar", "clicksound", "stuffcommand", "hovercommand", "enabledcvar"):
        if kw.get(k) is not None:
            L.append(("%s %s" % (k, kw[k])) if k in ("font", "textalign") else ('%s "%s"' % (k, kw[k])))
    L += kw.get("extra", [])
    L.append("}")
    return L


def text(name, rect, t, font="verdana-12", fg=INK, align="left", **kw):
    return W("Label", name, rect, title=t, fg=fg, font=font, textalign=align, **kw)


def cvl(name, rect, cvar, font="verdana-12", fg=INK, align="left", **kw):
    return W("Label", name, rect, fg=fg, font=font, textalign=align, linkcvar=cvar, **kw)


def plate(name, rect, t, cmd, font="verdana-12", **kw):
    return W("Button", name, rect, title=t, fg=BEIGE, bg=PLATE, border="3D_BORDER", font=font, textalign="center", hovershader=GLOW,
             clicksound="sound/menu/scroll.wav", stuffcommand=cmd, **kw)


# ---------------------------------------------------------------- 7. the attic rack hotspot + the room at the rack
sys.path.insert(0, M3D)
import numpy as np  # noqa: E402
import scene_params as SP  # noqa: E402

# the rack the attic session builds (attic_polish tools/make_attic_polish.py: RACK_C_BU / RACK_POSE, attic62_edit.py section 9):
# right-hand wall right of the post. The same numbers here, so this step and theirs agree on where the camera goes.
RACK_C_BU = (2.90, 1.54, 1.56)        # 2026-11-04 the attic session moved it 1.01 m along the wall (game 80.9 -152.2 81.9)
RACK_DIST, RACK_FOV, RACK_DIR = 1.70, 50.0, (1.0, 0.0, 0.0)


def approach(look_bu, dist, fov, lift=0.0, dirbu=None):
    t = SP.conv(np.array(look_bu, float), 52.5)
    u = SP.conv(np.array(dirbu, float), 1.0) if dirbu is not None else t - np.array([-36.7, 21.0, 102.4])
    u = u / np.linalg.norm(u)
    o = t - u * dist * 52.5
    o[2] += lift * 52.5
    f = (t - o) / np.linalg.norm(t - o)
    return "%.1f %.1f %.1f %.2f %.2f %.2f %.2f" % (o[0], o[1], o[2], math.degrees(-math.asin(f[2])), math.degrees(math.atan2(f[1], f[0])), 0.0, fov)


MAIN = arg("--main", os.path.join(MOD, "ui", "main.urc"))     # --main: a main.urc elsewhere (merge rehearsal), read and written there
main_raw = io.open(MAIN, "rb").read().decode("latin-1")
main_nl = "\r\n" if "\r\n" in main_raw else "\n"
main_t = main_raw.replace("\r\n", "\n")
_scene = re.search(r'name "atticscene"\n(.*?)\n\}\n', main_t, re.S).group(1)

# WHERE THE RACK IS belongs to the attic session. Precedence: --rack-pose "x y z pitch yaw roll fov" (and --rack-centre "x y z",
# game units) on the command line; else the pose their own `scenehot "rack"` already flies to (the first `scenefly 0.6 <pose>`
# in its command - their placeholder, or ours from an earlier run); else the RACK_C_BU defaults above. When they move the rack,
# the viewer (hotspot command, the viewer's own camera, the test cfg) follows on the next run with no edit here.
_POSE_RX = r"scenefly 0\.6 ((?:-?[\d.]+ ){6}-?[\d.]+)"
_rack_hot = re.search(r'(?m)^scenehot "rack" (\S+) (\S+) (\S+) (\S+) "([^"]*)"', _scene)
RACK_POSE = arg("--rack-pose")
# our own fallback rack (the [wpnviewer] block, on a tree without theirs) is NOT an authority: it is re-placed from RACK_C_BU
_OURS_ONLY = "[wpnviewer] the rifle rack hotspot" in main_t and main_t.count('name "hot_rack"') == 1
if not RACK_POSE and _rack_hot and not _OURS_ONLY and re.search(_POSE_RX, _rack_hot.group(5)):
    RACK_POSE = re.search(_POSE_RX, _rack_hot.group(5)).group(1)
if not RACK_POSE:
    RACK_POSE = approach(RACK_C_BU, RACK_DIST, RACK_FOV, 0.0, RACK_DIR)
assert len(RACK_POSE.split()) == 7, RACK_POSE
RACK_CENTRE = arg("--rack-centre")
if not RACK_CENTRE and _OURS_ONLY:
    RACK_CENTRE = "%.1f %.1f %.1f" % tuple(SP.conv(np.array(RACK_C_BU, float), 52.5))
RACK_CMD = ("set ui_scene_hot 0; exec ui/wpnview/open.cfg; globalwidgetcommand atticscene sceneleave 1; "
            "globalwidgetcommand atticscene scenefly 0.6 %s; uiafter 0.6 pushmenu hzm_wpnview" % RACK_POSE)
ROOM = [l for l in _scene.splitlines() if l.startswith("scenemodel ") and "models/human/" not in l] + \
       [l for l in _scene.splitlines() if l.startswith("scenelight ")]
assert len(ROOM) > 10, "atticscene models not found in main.urc"


def splice_main(t):
    """the rack hotspot: the attic session's (make_attic_polish.py) if present - only its command changes - else ours, LAST"""
    # a merge of this branch into the attic session's main.urc carries BOTH racks: drop ours (the [wpnviewer] widget block and a
    # second copy of the three rack scene lines - theirs come first, ours were appended last) and keep theirs
    ours = re.search(r"// ---- \[wpnviewer\] the rifle rack hotspot.*?// ---- \[wpnviewer\] end\n", t, re.S)
    dropped = bool(ours) and len(re.findall(r'(?m)^resource\nButton\n\{\nname "hot_rack"$', t)) > 1
    if dropped:
        t = t.replace(ours.group(0), "")
        for pfx in ('scenehot "rack" ', 'scenehotbox "rack" ', 'scenelabel "atticsign_rack" '):
            lines = [m.start() for m in re.finditer(r"(?m)^" + re.escape(pfx), t)]
            for s in reversed(lines[1:]):
                t = t[:s] + t[t.index("\n", s) + 1:]
    if re.search(r'(?m)^scenehot "rack" ', t):
        # replace ONLY the rack command (RACK_CMD in make_attic_polish.py): every exact copy of it - the hotspot, its hot_rack proxy
        # and their RACK > cue (hzm_rackcue). The peek (scenepeek "rack" / PEEK_POSE), hover and gating lines are theirs and untouched.
        old = re.search(r'(?m)^scenehot "rack" \S+ \S+ \S+ \S+ "([^"]*)"', t).group(1)
        n = t.count('"%s"' % old)
        assert n >= 2, "rack command found %d times (hotspot + hot_rack proxy at least)" % n
        t = t.replace('"%s"' % old, '"%s"' % RACK_CMD)
        if RACK_CENTRE:
            t = re.sub(r'(?m)^scenehot "rack" \S+ \S+ \S+ ', lambda m: 'scenehot "rack" %s ' % " ".join("%.1f" % float(v) for v in RACK_CENTRE.split()), t, count=1)
        assert re.search(r'resource\nButton\n\{\nname "hot_rack"\n', t), "scenehot rack without its hot_rack proxy"
        return t, "rewired (%d copies of the rack command%s)" % (n, ", our duplicate rack removed" if dropped else "")
    hots = re.findall(r'(?m)^scenehot "(\w+)"', _scene)
    idx = len(hots) + 1
    c = [float(v) for v in RACK_CENTRE.split()] if RACK_CENTRE else SP.conv(np.array(RACK_C_BU, float), 52.5)
    sg = re.search(r'(?m)^scenelabel "atticsign\d+" (\S+ \S+ \S+ \S+ \S+)$', _scene).group(1)
    add = ['scenehot "rack" %.1f %.1f %.1f %.1f "%s" "WEAPONS RACK" "hot_rack" 0' % (c[0], c[1], c[2], 34.0, RACK_CMD),
           'scenehotbox "rack" 0.0 0.0 150.0 260.0', 'scenelabel "atticsign_rack" %s' % sg]
    t = t.replace('name "atticscene"\n' + _scene + "\n}\n", 'name "atticscene"\n' + _scene + "\n" + "\n".join(add) + "\n}\n", 1)
    lab = re.search(r'resource\nLabel\n\{\nname "atticsign\d+"\n(.*?)\n\}\n', t, re.S).group(1)
    lab = re.sub(r'(?m)^title ".*"$', 'title "WEAPONS RACK"', lab)
    lab = re.sub(r'(?m)^enabledcvar ".*"$', 'enabledcvar "ui_atticActive==1 ui_scene_hot==%d"' % idx, lab)
    w = ["// ---- [wpnviewer] the rifle rack hotspot (gen_weapon_viewer.py; the attic session's make_attic_polish.py adds the same one)",
         "resource", "Label", "{", 'name "atticsign_rack"', lab, "}",
         "resource", "Button", "{", 'name "hot_rack"', "rect 0 0 8 8", "fgcolor 0 0 0 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
         'clicksound "sound/menu/apply.wav"', 'stuffcommand "%s"' % RACK_CMD, 'hovercommand "set ui_scene_hot %d"' % idx,
         'mouseawaycommand "set ui_scene_hot 0"', 'enabledcvar "ui_atticActive==1"', "}", "// ---- [wpnviewer] end"]
    anchor = 'resource\nLabel\n{\nname "sign"'
    assert anchor in t
    return t.replace(anchor, "\n".join(w) + "\n" + anchor, 1), "added (index %d)" % idx


# ---------------------------------------------------------------- 8. render
OUT = {}            # mod-relative path -> text (CRLF)


def put(rel, lines):
    OUT[rel] = CRLF.join(lines) + CRLF


def ecfg(e):
    return "exec ui/wpnview/e%03d.cfg" % e["n"]


clipped = []
for gi, g in enumerate(guns):
    ents = g["entries"]
    for k, e in enumerate(ents):
        fid = e["fid"]
        hist = HISTORY[g["gid"]]
        note = HISTORY.get("mv:" + e["stem"]) or (HISTORY.get("fin:%d" % fid) if 1 <= fid <= 7 else None)
        sent = re.split(r"(?<=\.)\s+", hist)
        while True:
            body = ((note + " ") if note else "") + " ".join(sent)
            lines = wrap(body, HIST_W * FIT)
            if len(lines) <= HIST_N or not sent or (not note and len(sent) <= 1):
                break
            sent = sent[:-1]
        if len(lines) > HIST_N:
            clipped.append(("history", e["n"], g["name"]))
            lines = lines[:HIST_N]
        unl, status = unlock(e)
        ul = []
        for u in unl:
            ul += wrap(u, RIGHT_W)
        if len(ul) > N_UNL:
            clipped.append(("unlock", e["n"], g["name"]))
            ul = ul[:N_UNL]
        cr = credits_for(g["gid"], e["tik"], e["stem"] if fid else "", fid)
        cl = []
        for c in cr:
            cl += wrap(c, RIGHT_W)
        if len(cl) > N_CRED:
            clipped.append(("credit", e["n"], g["name"]))
            cl = cl[:N_CRED]
        if not cl:
            cl = ["Not recorded."]
        e["status"] = status
        prev_e = entries[e["n"] - 2] if e["n"] > 1 else entries[-1]
        next_e = entries[e["n"] % len(entries)]
        prev_g = guns[gi - 1]["entries"][0]
        next_g = guns[(gi + 1) % len(guns)]["entries"][0]
        L = ["// GENERATED by docs/tools/gen_weapon_viewer.py - do not edit. %s / %s" % (g["name"], e["vname"]),
             "set ui_wvE %d" % e["n"], "set ui_wvG %d" % int(g["gid"]), "set ui_wvTab %d" % g["tab"],
             'set ui_wvModel "%s"' % ("" if g["gid"] in ICON2D else e["tik"]), 'set ui_wvXfm "%s"' % g["xfm"],
             'set ui_wvName "%s"' % g["name"], 'set ui_wvCd "%s"' % g["cd"],
             'set ui_wvVar "%s"' % e["vname"], 'set ui_wvVarN "%d / %d"' % (k + 1, len(ents)),
             'set ui_wvNum "%d of %d on the rack"' % (e["n"], len(entries))]
        L += ['set ui_wvH%d "%s"' % (j + 1, lines[j] if j < len(lines) else "") for j in range(HIST_N)]
        L += ['set ui_wvC%d "%s"' % (j + 1, cl[j] if j < len(cl) else "") for j in range(N_CRED)]
        L += ['set ui_wvU%d "%s"' % (j + 1, ul[j] if j < len(ul) else "") for j in range(N_UNL)]
        sl = wrap(status[1], RIGHT_W) if status[0] == "text" else []
        assert len(sl) <= 2, sl
        L += ['set ui_wvS "%s"' % (sl[0] if sl else ""), 'set ui_wvS2 "%s"' % (sl[1] if len(sl) > 1 else "")]
        if status[0] == "gun":
            # the Armory's own padlock state, archived by the server (loadoutpick.scr: seta coop_loLkA<id> "set coop_loLkV<id> 0|1");
            # fail-locked like the Armory's lktab pages when the profile has never joined a game
            L += ["set coop_loLkV%s 1" % g["gid"], "vstr coop_loLkA%s" % g["gid"]]
        L += ['set ui_wvPrevE "%s"' % ecfg(prev_e), 'set ui_wvNextE "%s"' % ecfg(next_e),
              'set ui_wvPrevV "%s"' % ecfg(ents[k - 1]), 'set ui_wvNextV "%s"' % ecfg(ents[(k + 1) % len(ents)]),
              'set ui_wvPrevG "%s"' % ecfg(prev_g), 'set ui_wvNextG "%s"' % ecfg(next_g),
              'set ui_wvLast "%s"' % ecfg(e)]
        put("ui/wpnview/e%03d.cfg" % e["n"], L)
for k in range(len(TABS)):
    first = [g for g in guns if g["tab"] == k][0]["entries"][0]
    put("ui/wpnview/t%d.cfg" % k, ["// GENERATED by docs/tools/gen_weapon_viewer.py - the %s tab" % TABS[k], ecfg(first)])
ZOOMS = (1.0, 1.5, 2.2)
for k, z in enumerate(ZOOMS):
    put("ui/wpnview/z%d.cfg" % k, ["// GENERATED by docs/tools/gen_weapon_viewer.py - zoom step", "set ui_wvZoom %.2f" % z,
                                   'set ui_wvZoomNext "exec ui/wpnview/z%d.cfg"' % ((k + 1) % len(ZOOMS))])
put("ui/wpnview/open.cfg", ["// GENERATED by docs/tools/gen_weapon_viewer.py - the viewer opens on the gun shown last (or the first)",
                            "set ui_wvSpin 0", "set ui_wvTilt 0", "exec ui/wpnview/z0.cfg", ecfg(entries[0]), "vstr ui_wvLast"])
put("ui/hzm_attic_go_rack.cfg", ["// generated by gen_weapon_viewer.py: the attic hotspot 'rack' without a cursor (ui_atticMain 1)",
                                 "set ui_scene_hot 0", "exec ui/wpnview/open.cfg", "globalwidgetcommand atticscene sceneleave 1",
                                 "globalwidgetcommand atticscene scenefly 0.6 %s" % RACK_POSE, "wait 600", "pushmenu hzm_wpnview"])

# ---- the menu
CLOSE = "set ui_scene_hot 0; popmenu 0"
U = ['menu "hzm_wpnview" 640 480 NONE 0', "bgcolor 0 0 0 0", "borderstyle NONE", "bgfill 0 0 0 0", "fullscreen 1", "virtualres 1",
     'escapecommand "%s"' % CLOSE, "",
     "// the attic held at the rack (the camera the hotspot flew to), so the menu opens IN the room; a soft vignette under the sheet",
     "resource", "Scene3D", "{", 'name "wvscene"', "rect 0 0 640 480", 'enabledcvar "ui_atticActive==1"'] + ROOM + \
    ["scenecam " + RACK_POSE, "}"]
U += W("Label", "wvDim", (-200, 0, 1040, 480), bg=(0.0, 0.0, 0.0, 0.30), extra=["fadein 0.35"])
U += W("Label", "wvBack", (-200, 0, 1040, 480), bg=(0.10, 0.09, 0.07, 1.0), enabledcvar="!ui_atticActive")   # flat menu: no room behind
# sheet
U += W("Label", "folder", (14, 22, 612, 452), bg=FOLDER, border="3D_BORDER")
U += text("foldertab", (30, 4, 190, 22), "WEAPONS RACK", "facfont-20", TABINK, "center", bg=TAB, border="3D_BORDER")
U += plate("wvClose", (520, 4, 96, 20), "BACK", CLOSE)
U += W("Label", "paper", (24, 32, 592, 434), bg=PAPER, border="3D_BORDER")
U += W("Label", "titlePlate", (34, 40, 572, 26), bg=PLATE, border="3D_BORDER")
U += cvl("wvName", (44, 43, 330, 20), "ui_wvName", "facfont-20", BEIGE)
U += cvl("wvCd", (330, 45, 268, 16), "ui_wvCd", "verdana-12", BEIGE, "right")
# category tabs (named tab<k>: LB / RB step them, uiwinman PadTab)
tw = 572.0 / len(TABS)
for k, nm in enumerate(TABS):
    r = (34 + k * tw, 72, tw - 2, 20)
    U += W("Label", "tabOn%d" % k, r, bg=TAB, border="3D_BORDER", enabledcvar="ui_wvTab==%d" % k)
    U += W("Button", "tab%d" % k, r, title=nm, fg=INK, bg=CLEAR, border="NONE", font="verdana-12", textalign="center",
           hovershader=GLOW_P, clicksound="sound/menu/scroll.wav", stuffcommand="exec ui/wpnview/t%d.cfg" % k)
# the gun list of the open tab
for k in range(len(TABS)):
    tg = [g for g in guns if g["tab"] == k]
    assert len(tg) * LIST[3] <= VIEW[3] + 150, "tab %d list too long" % k
    for j, g in enumerate(tg):
        nm = g["name"]
        assert width(nm) <= (LIST[2] - 4) * FIT, "gun name %r does not fit the list column" % nm
        r = (LIST[0], LIST[1] + j * LIST[3], LIST[2], LIST[3])
        U += W("Label", "gSel%s" % g["gid"], r, bg=SEL, enabledcvar="ui_wvTab==%d ui_wvG==%d" % (k, int(g["gid"])))
        U += W("Button", "g%s" % g["gid"], r, title=nm, fg=INK, bg=CLEAR, border="NONE", font="verdana-12", textalign="left",
               hovershader=GLOW_P, clicksound="sound/menu/scroll.wav", stuffcommand=ecfg(g["entries"][0]), enabledcvar="ui_wvTab==%d" % k)
# the viewer
vx, vy, vw, vh = VIEW
U += W("Label", "wvFelt", (vx, vy, vw, vh), bg=FELT, border="INDENT_BORDER")
U += W("Label", "wvGun", (vx + 2, vy + 2, vw - 4, vh - 4), fg=WHITE, linkcvar="ui_wvModel",
       extra=['modelxformcvar "ui_wvXfm"', "rendermodel 1", "rendermodelfit 1", 'modelspincvar "ui_wvSpin"',
              # an older engine does not know the next three lines and shows the Armory's hero view instead (yaw drag only)
              "modelorbit 1", 'modeltiltcvar "ui_wvTilt"', 'modelzoomcvar "ui_wvZoom"',
              'modeloffset "0 0 0"', 'modelrotateoffset "0 0 0"', 'modelangles "0 270 180"', "modelscale 1.00", "modelanim idle"])
for gid in ICON2D:
    U += W("Label", "wvIcon%s" % gid, (vx + vw / 2 - 60, vy + vh / 2 - 60, 120, 120), shader="textures/hud/weap_grenade",
           enabledcvar="ui_wvG==%d" % int(gid))
U += text("wvHint", (vx, vy + vh - 16, vw, 13), "DRAG TO TURN  -  WHEEL TO ZOOM", "verdana-12", (0.62, 0.57, 0.45, 0.8), "center")
by = vy + vh + 4
bx0, bw0 = LIST[0], vx + vw - LIST[0]          # the variant bar and the buttons span the list and the viewer
U += plate("vPrev", (bx0, by, 24, 20), "<", "vstr ui_wvPrevV", font="verdana-14")
U += W("Label", "vPlate", (bx0 + 26, by, bw0 - 52, 20), bg=PLATE, border="3D_BORDER")
VNAME_W = bw0 - 110
U += cvl("vName", (bx0 + 30, by + 3, VNAME_W, 14), "ui_wvVar", "verdana-12", BEIGE)
U += cvl("vNum", (bx0 + bw0 - 76, by + 3, 46, 14), "ui_wvVarN", "verdana-12", BEIGE, "right")
U += plate("vNext", (bx0 + bw0 - 24, by, 24, 20), ">", "vstr ui_wvNextV", font="verdana-14")
for e in entries:
    assert width(e["vname"]) <= VNAME_W * FIT, "variant name %r does not fit" % e["vname"]
cy = by + 24
bw = (bw0 - 6) / 4.0
for k, (nm, t, cmd) in enumerate((("gPrev", "PREV GUN", "vstr ui_wvPrevG"), ("gNext", "NEXT GUN", "vstr ui_wvNextG"),
                                  ("wvZoomB", "ZOOM", "vstr ui_wvZoomNext"), ("wvReset", "RESET VIEW", "set ui_wvSpin 0; set ui_wvTilt 0; exec ui/wpnview/z0.cfg"))):
    U += plate(nm, (bx0 + k * (bw + 2), cy, bw, 20), t, cmd)
U += cvl("wvNum", (RIGHT[0], cy + 4, RIGHT[2], 14), "ui_wvNum", "verdana-12", MUTED)
# the info column
rx, ry, rw = RIGHT
y = ry
U += text("hCred", (rx, y, rw, 14), "MADE BY", "verdana-14", RUST)
y += 16
for j in range(N_CRED):
    U += cvl("wvC%d" % (j + 1), (rx, y + j * 13, rw, 13), "ui_wvC%d" % (j + 1))
y += N_CRED * 13 + 8
U += text("hUnl", (rx, y, rw, 14), "HOW TO UNLOCK", "verdana-14", RUST)
y += 16
for j in range(N_UNL):
    U += cvl("wvU%d" % (j + 1), (rx, y + j * 13, rw, 13), "ui_wvU%d" % (j + 1))
y += N_UNL * 13 + 8
U += text("hSt", (rx, y, rw, 14), "YOUR STATUS", "verdana-14", RUST)
y += 16
SY = y
U += cvl("wvS", (rx, SY, rw, 13), "ui_wvS", "verdana-12", MUTED)
U += cvl("wvS2", (rx, SY + 13, rw, 13), "ui_wvS2", "verdana-12", MUTED)
# per-gun / per-variant status from the archived profile cvars (enabledcvar ANDs its tokens; a never-joined profile reads locked)
for g in guns:
    for e in g["entries"]:
        st = e["status"]
        gate = "ui_wvE==%d" % e["n"]
        if st[0] == "free":
            U += text("st%d" % e["n"], (rx, SY, rw, 13), "FREE - ALWAYS YOURS", fg=GREEN, enabledcvar=gate)
        elif st[0] == "gun":
            U += text("stU%d" % e["n"], (rx, SY, rw, 13), "UNLOCKED - IN YOUR ARMORY", fg=GREEN, enabledcvar=gate + " !coop_loLkV" + g["gid"])
            U += text("stL%d" % e["n"], (rx, SY, rw, 13), "LOCKED", fg=RED, enabledcvar=gate + " coop_loLkV" + g["gid"])
            if st[2] is not None:
                U += text("stPl%d" % e["n"], (rx, SY + 13, 54, 13), "Progress:", fg=MUTED, enabledcvar=gate + " coop_loLkV" + g["gid"])
                U += cvl("stP%d" % e["n"], (rx + 54, SY + 13, rw - 54, 13), "coop_uiN%d" % st[2], fg=MUTED, enabledcvar=gate + " coop_loLkV" + g["gid"])
        elif st[0] == "mv":
            si, mi = st[1], st[2]
            if si is None:
                continue
            ok = gate + " coop_uiD%d" % si + ((" coop_uiD%d" % mi) if mi is not None else "")
            U += text("stU%d" % e["n"], (rx, SY, rw, 13), "UNLOCKED", fg=GREEN, enabledcvar=ok)
            U += text("stL%d" % e["n"], (rx, SY, rw, 13), "LOCKED", fg=RED, enabledcvar=gate + " !coop_uiD%d" % si)
            if mi is not None:
                U += text("stM%d" % e["n"], (rx, SY, rw, 13), "LOCKED - MASTER THE GUN", fg=RED, enabledcvar=gate + " coop_uiD%d !coop_uiD%d" % (si, mi))
            U += text("stPl%d" % e["n"], (rx, SY + 13, 54, 13), "Progress:", fg=MUTED, enabledcvar=gate + " !coop_uiD%d" % si)
            U += cvl("stP%d" % e["n"], (rx + 54, SY + 13, rw - 54, 13), "coop_uiN%d" % si, fg=MUTED, enabledcvar=gate + " !coop_uiD%d" % si)
assert SY + 26 < HIST_Y - 4, "info column runs into the history band"
# history band
U += W("Label", "histRule", (34, HIST_Y - 4, 572, 1), bg=(0.42, 0.22, 0.06, 0.6))
U += text("hHist", (34, HIST_Y, 200, 14), "FIELD NOTES", "verdana-14", RUST)
for j in range(HIST_N):
    U += cvl("wvH%d" % (j + 1), (36, HIST_Y + 15 + j * 13, HIST_W + 4, 13), "ui_wvH%d" % (j + 1))
assert HIST_Y + 15 + HIST_N * 13 <= 466, "history band below the paper"
put("ui/hzm_wpnview.urc", ["// GENERATED by docs/tools/gen_weapon_viewer.py - DO NOT HAND-EDIT. The attic rifle rack's weapon viewer (v1.10.63):",
                           "// %d guns, %d entries (each finish and model variant is its own entry). Engine: modelorbit (wpnviewer-eng)." % (len(guns), len(entries))] + U)

# localization: every static title the menu draws (the engine logs a LOCALIZATION ERROR for a title without an entry);
# the block is replaced on every run, like make_mpui.py's [mpui] block
LOC = sorted({m for m in re.findall(r'(?m)^title "([^"]+)"$', "\n".join(U)) if re.search(r"[A-Za-z]", m)})
LP = os.path.join(MOD, "global", "localization_coop.txt")
if os.path.exists(LP):
    lt = io.open(LP, "rb").read().decode("latin-1")
    lnl = "\r\n" if "\r\n" in lt else "\n"
    lt = re.sub(r"//\[wpnviewer\] begin.*?//\[wpnviewer\] end\r?\n", "", lt, flags=re.S)
    have = set(re.findall(r'\{ "([^"]*)" "', lt))
    add = [s for s in LOC if s not in have]
    if add:
        lt = lt.rstrip("\r\n") + lnl + "//[wpnviewer] begin: the attic weapon viewer (gen_weapon_viewer.py)" + lnl
        lt += lnl.join('{ "%s" "%s" }' % (s, s) for s in add) + lnl + "//[wpnviewer] end" + lnl
    OUT["global/localization_coop.txt"] = lt
main_new, how = splice_main(main_t)
OUT["ui/main.urc"] = main_new.replace("\n", main_nl)


# ---------------------------------------------------------------- 9. build / check / list
def manifest():
    return [{"n": e["n"], "gid": e["g"]["gid"], "name": e["g"]["name"], "variant": e["vname"], "fid": e["fid"], "tik": e["tik"],
             "tab": e["g"]["tab"]} for e in entries]


cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
if cmd == "list":
    for m in manifest():
        print("%(n)03d  %(gid)s  %(name)-26s %(variant)-40s %(tik)s" % m)
    sys.exit(0)
stale = []
for rel, txt in sorted(OUT.items()):
    p = MAIN if rel == "ui/main.urc" else os.path.join(MOD, rel)
    data = txt.encode("latin-1") if rel.endswith("localization_coop.txt") else txt.encode("latin-1")
    if not os.path.exists(p) or open(p, "rb").read() != data:
        stale.append(rel)
        if cmd == "build":
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(data)
if cmd == "build":
    old = {f for f in os.listdir(os.path.join(MOD, "ui", "wpnview"))} - {os.path.basename(r) for r in OUT if r.startswith("ui/wpnview/")}
    for f in old:
        os.remove(os.path.join(MOD, "ui", "wpnview", f))
    json.dump(manifest(), open(os.path.join(ROOT, "docs", "proposals", "wpnviewer_2026-11-04", "entries.json"), "w"), indent=1)
print("weapon viewer: %d guns, %d entries (%d finishes, %d model variants); rack hotspot %s; %d files %s" % (
    len(guns), len(entries), sum(1 for e in entries if 1 <= e["fid"] <= 7), sum(1 for e in entries if e["fid"] >= 8), how,
    len(stale), "written" if cmd == "build" else "stale"))
for c in clipped:
    print("  clipped:", c)
missing = [e for e in entries if not (os.path.exists(os.path.join(MOD, e["tik"])) or os.path.exists(os.path.join(FIXES, e["tik"])) or os.path.exists(os.path.join(WPNFIX, e["tik"]))
                                       or vfs().winner(e["tik"]))]
for e in missing:
    print("  MISSING MODEL: %03d %s %s" % (e["n"], e["g"]["name"], e["tik"]))
sys.exit(1 if (cmd == "check" and stale) else 0)

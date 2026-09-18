#!/usr/bin/env python
"""Generate the two MP-only armory screens (Allied + Axis), their cfg trees and their side
rosters from docs/tools/mp_armory_roster.tsv.

WHY THIS EXISTS (and why it is NOT gen_loadout.py)
    The MP loadout gets its OWN Allied and Axis armories - "I don't want allies having access to
    any non-allied weapons" (user, 2026-09-13). The coop armory generator (gen_loadout.py) is a
    build gate that must stay 615/615 byte-identical, it hard-codes the ui/loadout path and the
    coop_lo* prefix, and its page shape leans on `vstr` gating that MP must never use (a server-
    stuffed vstr is filtered - TRAPS T8 - and the MP UI is a client-origin design). So this is a
    SEPARATE tool with copied idioms, never a shared file: a coop edit to gen_loadout.py can never
    move MP output, and MP output can never carry a coop_lo / ui/loadout / vstr token.

    It is trustworthy for the same reason gen_loadout.py is: `check` regenerates every file in
    memory and byte-compares it against disk (exit 1 on any drift), so build.ps1 can gate on it.

    python docs/tools/gen_mp_armory.py check   # regenerate in memory + byte-compare (exit 1 = drift)
    python docs/tools/gen_mp_armory.py build   # write the files

WHAT IT WRITES (nothing else - the coop armory is never an output)
    hzm-mohaa-coop-mod/ui/coop_mpa_armory.urc        menu "coop_mpa_armory"  (Allied in-match screen)
    hzm-mohaa-coop-mod/ui/coop_mpx_armory.urc        menu "coop_mpx_armory"  (Axis in-match screen)
    hzm-mohaa-coop-mod/ui/coop_mpa_armory/*.cfg       open / tab0..7 / c<mpid> / deploy
    hzm-mohaa-coop-mod/ui/coop_mpx_armory/*.cfg
    hzm-mohaa-coop-mod/coop_mod/mpa_roster.scr        server roster: mpid -> give/slot/class/tab/ammo/starter
    hzm-mohaa-coop-mod/coop_mod/mpx_roster.scr

    It READS, read-only, docs/tools/loadout_weapons.tsv (tik/name/cd/xfm by coop id) and
    coop_mod/loadoutroster.scr::roster_get (ammo/ammoN by coop id) so the tile ids are real.

DETERMINISM AND ISOLATION (emitter assertions - a violation aborts the run, writing nothing)
    * ASCII only, no BOM, no newline inside a string; explicit LF written in binary mode (TRAPS T2).
    * No coop_lo* / ui/loadout/ / vstr token in ANY output (isolation clauses 12, 18).
    * An Allied output never names a coop_mpx_* token and an Axis output never names coop_mpa_*
      (clause 13); every cvar an output names carries the coop_mpa_ / coop_mpx_ separator.
    * Exactly one free starter per (side, tab); no (side, tab) cell over 9 tiles; every `exec`
      target is itself an output; every ,q marker matches the grammar declared in mp_armory.scr.
    * No empty right-hand side in the roster .scr (the gen_loadout bug-1908 lesson).
"""
import io
import os
import re
import sys

import gen_mp_challenges  # the MP challenge table (same dir); the Service Record renders its list

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mp_armory_roster.tsv")
LW_TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loadout_weapons.tsv")
ROSTER_SCR = os.path.join(MOD, "coop_mod", "loadoutroster.scr")

# The eight populated tabs this slice, in screen order. SAPPER (index 8) is reserved: no tiles yet
# (its guns need the mine-detector tiks and the landmine-map runtime gate, a later slice).
TABS = ["RIFLE", "SNIPER", "SMG", "MG", "SHOTGUN", "ROCKET", "PISTOL", "NADES"]
TAB_INDEX = dict((t, i) for i, t in enumerate(TABS))
TAB_PCLASS = {"RIFLE": "rifle", "SNIPER": "sniper", "SMG": "smg", "MG": "mg", "SHOTGUN": "shotgun",
              "ROCKET": "rocket", "PISTOL": "pistol", "NADES": "nades"}
TAB_DMCLASS = {"RIFLE": "rifle", "SNIPER": "sniper", "SMG": "smg", "MG": "mg", "SHOTGUN": "shotgun",
               "ROCKET": "heavy", "PISTOL": "pistol", "NADES": "grenade"}
# slot letter and the name-bus FIELD digit (grammar ,q<side><field><mpid>)
TAB_SLOT = {"RIFLE": "p", "SNIPER": "p", "SMG": "p", "MG": "p", "SHOTGUN": "p", "ROCKET": "p",
            "PISTOL": "s", "NADES": "g"}
SLOT_FIELD = {"p": "1", "s": "2", "g": "3"}
SLOT_NAME = {"p": "PRIMARY", "s": "SIDEARM", "g": "GRENADE"}
# Readable class names for the Service Record (the progression ladder is by pclass, in TABS order,
# which matches mp_progression.scr::init's coop_mpProgClasses[0..7] exactly).
PCLASS_DISPLAY = {"rifle": "Rifle", "sniper": "Sniper", "smg": "SMG", "mg": "Machine Gun",
                  "shotgun": "Shotgun", "rocket": "Rocket", "pistol": "Pistol", "nades": "Grenade"}
DEFAULT_XFM = "0 0 0 1.00 0 90 180"
# The 3D viewer poses the character to HOLD the selected weapon, exactly as the coop loadout does. Only
# three hold anims exist in models/player/base/anims_shared.txt (rifle/smg/pistol, shared by EVERY player
# model incl. the MP DM bodies) and coop maps every long-gun tab onto coop_hold_rifle - mirror that. NB:
# the base idle coop_loadout_idle is deliberately NOT used - it trips the coop_lo* isolation ban; the hold
# anims are coop_hold_* (coop_ho, not coop_lo) so they are clean in MP output.
TAB_ANIM = {"pistol": "coop_hold_pistol", "smg": "coop_hold_smg", "rifle": "coop_hold_rifle",
            "sniper": "coop_hold_rifle", "mg": "coop_hold_rifle", "shotgun": "coop_hold_rifle",
            "rocket": "coop_hold_rifle", "nades": "coop_hold_rifle"}
# The viewer's char transform (extra transform on top of modeloffset), cloned from the coop charRender
# seed coop_loXfmC. Spin off by default; the same idle base the coop viewer opens on.
VIEW_XFMC = "57 1 4 0.80 0 200 0"
VIEW_ANIM_BASE = "coop_hold_rifle"

TSV_COLS = ["side", "mpid", "coop_id", "tab", "starter", "landmine",
            "give", "name", "cd", "ammo", "ammoN", "dmclass"]

REQ_LOCKED = "Unlocks with MP progression"


def rd(p):
    return io.open(p, "r", encoding="latin-1", newline="").read()


# ---------------------------------------------------------------- read the coop source data
def load_loadout_weapons():
    """id -> {tik, name, cd, xfm} from docs/tools/loadout_weapons.tsv (read-only)."""
    out = {}
    cols = None
    for line in io.open(LW_TSV, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        v = line.rstrip("\n").split("\t")
        if v[0] == "id":
            cols = v
            continue
        row = dict(zip(cols, v + [""] * (len(cols) - len(v))))
        out[row["id"]] = {"tik": row["tik"], "name": row["name"], "cd": row["cd"], "xfm": row["xfm"]}
    return out


def load_roster_ammo():
    """coop id -> {ammo, ammoN} from coop_mod/loadoutroster.scr::roster_get (read-only)."""
    txt = rd(ROSTER_SCR)
    out = {}
    for m in re.finditer(r'case\s+"(\d+)":(.*?)break', txt, re.S):
        wid, body = m.group(1), m.group(2)
        a = re.search(r'local\.r\["ammo"\]\s*=\s*"([^"]*)"', body)
        n = re.search(r'local\.r\["ammoN"\]\s*=\s*(\d+)', body)
        out[wid] = {"ammo": a.group(1) if a else "", "ammoN": n.group(1) if n else ""}
    return out


def load_rows():
    rows = []
    for line in io.open(TSV, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        v = line.rstrip("\n").split("\t")
        if v[0] == "side":
            continue
        row = dict(zip(TSV_COLS, v + [""] * (len(TSV_COLS) - len(v))))
        rows.append(row)
    return rows


def resolve(rows, lw, ammo):
    """Fill each row's derived fields. '-' means derive from the coop id; a value overrides."""
    out = []
    for r in rows:
        side, coop = r["side"], r["coop_id"]
        tab = r["tab"]
        if side not in ("a", "x"):
            raise SystemExit("gen_mp_armory: bad side %r for mpid %s" % (side, r["mpid"]))
        if tab not in TAB_INDEX:
            raise SystemExit("gen_mp_armory: bad tab %r for mpid %s (not one of %s)"
                             % (tab, r["mpid"], ",".join(TABS)))
        src = lw.get(coop) if coop != "-" else None
        am = ammo.get(coop) if coop != "-" else None

        def pick(col, fallback):
            v = r[col]
            return fallback if v == "-" or v == "" else v

        give = pick("give", src["tik"] if src else "")
        name = pick("name", src["name"] if src else "")
        cd = pick("cd", src["cd"] if src else "")
        ammo_t = pick("ammo", am["ammo"] if am else "")
        ammo_n = pick("ammoN", am["ammoN"] if am else "")
        dmclass = pick("dmclass", TAB_DMCLASS[tab])
        xfm = src["xfm"] if src else DEFAULT_XFM
        if not (give and name and cd and ammo_t and ammo_n):
            raise SystemExit("gen_mp_armory: mpid %s (side %s) is missing a derivable field - a coop_id "
                             "of '-' needs give/name/cd/ammo/ammoN in the TSV" % (r["mpid"], side))
        out.append({
            "side": side, "mpid": r["mpid"], "coop_id": coop, "tab": tab,
            "tabidx": TAB_INDEX[tab], "pclass": TAB_PCLASS[tab], "dmclass": dmclass,
            "slot": TAB_SLOT[tab], "field": SLOT_FIELD[TAB_SLOT[tab]],
            "anim": TAB_ANIM[TAB_PCLASS[tab]],
            "give": give, "name": name, "cd": cd, "xfm": xfm,
            "ammo": ammo_t, "ammoN": ammo_n, "starter": r["starter"] == "1",
            "landmine": r["landmine"] == "1",
        })
    return out


# ---------------------------------------------------------------- invariants
def check_invariants(rows):
    for side in ("a", "x"):
        srows = [w for w in rows if w["side"] == side]
        # exactly one starter per tab, and <= 9 tiles per tab
        by_tab = {}
        for w in srows:
            by_tab.setdefault(w["tab"], []).append(w)
        for tab, ws in by_tab.items():
            if len(ws) > 9:
                raise SystemExit("gen_mp_armory: side %s tab %s has %d tiles (>9)" % (side, tab, len(ws)))
            starters = [w for w in ws if w["starter"]]
            if len(starters) != 1:
                raise SystemExit("gen_mp_armory: side %s tab %s must have exactly one starter, has %d"
                                 % (side, tab, len(starters)))
        # unique mpid per side
        ids = [w["mpid"] for w in srows]
        if len(ids) != len(set(ids)):
            raise SystemExit("gen_mp_armory: side %s has duplicate mpids" % side)


# ---------------------------------------------------------------- emit: cfg tree
def cvar(side, suffix):
    return "coop_mp%s_%s" % (side, suffix)


# ---------------------------------------------------------------- MP cosmetics (appearance panel)
# DERIVED, not hand-written: the id/name lists AND the viewer model each option previews are parsed
# read-only from coop_mod/mp_cosmetics.scr (skinGet / helmGet), which is the server's own validation
# table. Parsing (not a second copy) means the UI can NEVER offer an id the server rejects or preview a
# model the server would not wear - the drift the old "KEEP IN SYNC" comment warned about is impossible.
# Skins are side-specific; helmets are shared (both sides get the full lists, per user 09-15). Each entry
# is (id, display-name, viewer-value): a skin's viewer-value is the body tik the charRender links; a
# helmet's is the head-attach tik, or "" for std/none (the body's own baked look - no attach, matching
# mp_cosmetics::apply, which only attaches for ids past std/none).
COS_MP_SCR = os.path.join(MOD, "coop_mod", "mp_cosmetics.scr")


def load_cosmetics():
    """Parse skinGet (per side) and helmGet from mp_cosmetics.scr into the UI option tables."""
    txt = rd(COS_MP_SCR)

    def body(fn):
        m = re.search(r"\n%s\b[^\{]*\{" % re.escape(fn), txt)
        if not m:
            raise SystemExit("gen_mp_armory: mp_cosmetics.scr has no %s block" % fn)
        i = m.end() - 1
        depth = 0
        for j in range(i, len(txt)):
            if txt[j] == "{":
                depth += 1
            elif txt[j] == "}":
                depth -= 1
                if depth == 0:
                    return txt[i + 1:j]
        raise SystemExit("gen_mp_armory: %s block never closes" % fn)

    skin_body = body("skinGet")
    parts = re.split(r"\}\s*else\s*\{", skin_body, maxsplit=1)
    if len(parts) != 2:
        raise SystemExit("gen_mp_armory: skinGet is not a two-side if/else")
    skin_rx = re.compile(r'case\s+"(\w+)":\s*local\.r\["stem"\]\s*=\s*"([^"]*)";\s*'
                         r'local\.r\["name"\]\s*=\s*"([^"]*)"')
    skins = {}
    for side, chunk in (("a", parts[0]), ("x", parts[1])):
        skins[side] = [(sid, name, "models/player/" + stem + ".tik")
                       for sid, stem, name in skin_rx.findall(chunk)]
        if not skins[side]:
            raise SystemExit("gen_mp_armory: no %s skins parsed from skinGet" % side)

    helm_rx = re.compile(r'case\s+"(\w+)":\s*local\.r\["tik"\]\s*=\s*"([^"]*)";\s*'
                         r'local\.r\["name"\]\s*=\s*"([^"]*)"')
    helms = []
    for hid, tik, name in helm_rx.findall(body("helmGet")):
        view = "" if tik in ("std", "none") else tik
        helms.append((hid, name, view))
    if not helms:
        raise SystemExit("gen_mp_armory: no helmets parsed from helmGet")
    return skins, helms


COS_SKINS, COS_HELMS = load_cosmetics()
# Gloves are 3P hand-surface skin bits (mp_cosmetics::writeGloveBits), not a model swap, so they cannot
# be shown in the charRender the way a skin/helmet can - the appearance panel offers them by name only.
COS_GLOVES = [("0", "BARE HANDS", ""), ("1", "GRAY GLOVES", ""), ("2", "BLACK GLOVES", ""),
              ("3", "BROWN GLOVES", ""), ("4", "TAN GLOVES", ""), ("5", "WINTER GLOVES", ""),
              ("6", "ALPINE GLOVES", "")]


# ---------------------------------------------------------------- progression constants (DERIVED)
# The Service Record must state the SAME thresholds the server gates on, so parse them from the scripts
# rather than restating them: the weapon-unlock kills and kills-per-rank from mp_progression.scr, and the
# per-piece cosmetic step from mp_cosmetics.scr::cosNeed. If a script retunes a number, the SR follows on
# the next build - it can never quietly disagree with what the game actually enforces.
MP_PROG_SCR = os.path.join(MOD, "coop_mod", "mp_progression.scr")


def load_prog_consts():
    txt = rd(MP_PROG_SCR)

    def gi(name, default):
        m = re.search(r"level\.%s\s*=\s*(\d+)" % re.escape(name), txt)
        return int(m.group(1)) if m else default

    ctxt = rd(COS_MP_SCR)

    def step(field):
        m = re.search(r'field\s*==\s*"%s".*?\*\s*(\d+)' % field, ctxt, re.S)
        return int(m.group(1)) if m else 0

    return {"unlock": gi("coop_mpProgUnlockKills", 15), "perrank": gi("coop_mpProgKillsPerRank", 25),
            "skin_step": step("k"), "helm_step": step("h"), "glove_step": step("v")}


PROG = load_prog_consts()


def cos_option_cfg(side, field, oid, name, view):
    """One appearance option cfg: update the 3D viewer live (skin -> body model, helmet -> head attach;
    gloves have no model form so `view` is ""), set the chip name for feedback, and seta the carried
    USERINFO cvar (field k=skin h=helmet v=glove). No vstr, and NO name-bus marker: cosmetics ride the
    userinfo carry alone (E1), which the server validates + applies at spawn (mp_cosmetics::apply, which
    now enforces cosUnlocked on the carried id). That is what lets the SAME cfg work both in a live match
    and disconnected from Multiplayer Options - a menu pick never pollutes the player name, and the server
    is still authoritative over the earned gate. The viewer cvars are the ones the charRender links, so
    the pick shows instantly on either screen."""
    persist = {"k": "cosSkin", "h": "cosHelm", "v": "cosGlove"}[field]
    L = []
    if field == "k":
        L.append('set %s "%s"' % (cvar(side, "Char"), view))
    elif field == "h":
        L.append('set %s "%s"' % (cvar(side, "Helm"), view))
    L += [
        'set %s "%s"' % (cvar(side, "CosNm"), name),
        'seta %s "%s"' % (cvar(side, persist), oid),
    ]
    return "\n".join(L) + "\n"


def cos_panel_urc(side):
    """coop_mp<side>_appearance.urc - a self-contained cosmetics panel (SKIN / HELMET / GLOVES columns of
    option buttons), opened by the APPEARANCE button on the armory. Every button execs a static option
    cfg (no vstr). Fonts limited to facfont-20 / verdana-12 (bug-519). Server validates + applies picks."""
    menu = "coop_mp%s_appearance" % side
    dir_ = "coop_mp%s_armory" % side
    title = ("ALLIED" if side == "a" else "AXIS") + " APPEARANCE"
    L = [
        "// HZM MP %s APPEARANCE - GENERATED by docs/tools/gen_mp_armory.py - DO NOT HAND-EDIT." % title,
        "// Skin/helmet/glove picks commit via the ,q name-bus (mp_armory.scr::applyMarker), applied at",
        "// spawn by mp_cosmetics.scr. No vstr; names only coop_mp* cvars (isolation clauses 12/13/18).",
        'menu "%s" 640 480 NONE 1' % menu,
        "borderstyle NONE",
        "bgcolor 0 0 0 0",
        "align centerx centery",
        "virtualres 1",
        "fullscreen 0",
        "",
    ]
    L += w_label("bg", (0, 0, 640, 480), order=50, bg="0.05 0.06 0.08 1.00")
    L += [""]
    L += w_label("title", (220, 12, 200, 16), text=title)
    L += [""]
    L += w_button("doneBtn", (560, 8, 72, 16), "DONE", "popmenu 0")
    L += [""]
    # the same 3D viewer as the armory, on the left - a skin/helmet pick updates its Char/Helm live so you
    # see the change while you browse (the weapon + hold anim carry over from the armory's Prev/CharAnim).
    L += w_label("charRender", (12, 60, 134, 356), order=20, model=True, fg="1.00 1.00 1.00 1.00",
                 link=cvar(side, "Char"), xfmcvar=cvar(side, "XfmC"),
                 attachcvar=cvar(side, "Helm"), attachtag="Bip01 Head",
                 attachcvar2=cvar(side, "Prev"), attachtag2="tag_weapon_right",
                 spincvar=cvar(side, "CharSpin"), animcvar=cvar(side, "CharAnim"),
                 modeloffset="78 0 -18", modelrotateoffset="0 0 0", modelangles="0 200 0",
                 modelscale="1.0", modelanim=VIEW_ANIM_BASE)
    L += [""]
    L += w_button("spinBtn", (12, 420, 134, 15), "SPIN", "toggle %s" % cvar(side, "CharSpin"))
    L += [""]
    L += w_label("selName", (156, 34, 300, 14), link=cvar(side, "CosNm"), fg="0.86 0.74 0.44 1.00")
    L += [""]
    # three columns to the right of the viewer: SKIN / HELMET / GLOVES
    cols = [("SKIN", "k", COS_SKINS[side], 156), ("HELMET", "h", COS_HELMS, 310), ("GLOVES", "v", COS_GLOVES, 464)]
    for capn, field, items, x in cols:
        L += w_label("cap_%s" % field, (x, 60, 150, 16), text=capn, fg="0.55 0.60 0.66 1.00")
        L += [""]
        for i, (oid, name, view) in enumerate(items):
            y = 82 + 20 * i
            L += w_button("opt_%s%s" % (field, oid), (x, y, 150, 17), name,
                          "exec ui/%s/%s%s.cfg" % (dir_, field, oid))
            L += [""]
    # WEAPON FINISH row (below the columns): OFF + 7 finish buttons, each gated on its earned-finish cvar
    # (coop_mpUfin_<finish>, pushed by the challenge derivation). The server re-validates the pick.
    L += w_label("cap_f", (156, 330, 300, 16), text="WEAPON FINISH  (earn via challenges)",
                 fg="0.55 0.60 0.66 1.00")
    L += [""]
    for i, (idx, fin, lbl) in enumerate(MP_FINISH_OPTS):
        col, r = i % 4, i // 4
        x = 156 + col * 115
        y = 350 + r * 22
        enabled = None if fin == "none" else "coop_mpUfin_%s" % fin
        L += w_button("optf_%d" % idx, (x, y, 110, 18), lbl,
                      "exec ui/%s/f%d.cfg" % (dir_, idx), enabled=enabled)
        L += [""]
    return "\n".join(L).rstrip("\n") + "\n"


def commit_cfg(w):
    """c<mpid>.cfg - click a tile: preview + archive the pick + append the ,q name-bus marker. EVERY
    tile now commits (slice 5); the SERVER (mp_armory.scr::applyMarker) validates the pick against the
    player's progression unlocks and denies a locked one, so a client cannot select past the gate. A
    non-starter still shows the "Unlocks with MP progression" hint + the padlock overlay until earned,
    and the server degrades a locked carried pick at deploy time."""
    side, f, mpid = w["side"], w["field"], w["mpid"]
    req = '""' if w["starter"] else '"%s"' % REQ_LOCKED
    L = [
        'set %s "%s"' % (cvar(side, "Prev"), w["give"]),
        'set %s "%s"' % (cvar(side, "XfmW"), w["xfm"]),
        'set %s "%s"' % (cvar(side, "CharAnim"), w["anim"]),
        'set %s "%s"' % (cvar(side, "Nm"), w["name"]),
        'set %s "%s"' % (cvar(side, "Cd"), w["cd"]),
        'set %s %s' % (cvar(side, "Req"), req),
        'seta %s "%s"' % (cvar(side, "K" + f), mpid),
        'seta %s "%s"' % (cvar(side, "N" + f), w["name"]),
        'seta %s "%s"' % (cvar(side, "S" + f), w["give"]),
        "append name ,q%s%s%s" % (side, f, mpid),
    ]
    return "\n".join(L) + "\n"


def defaults_commit_cfg(w):
    """d<mpid>.cfg - defaults click (disconnected): like commit but NO marker (seta the carried default
    only). Every tile archives its pick; the server validates the unlock when the player connects and
    deploys, so an offline default for a not-yet-earned weapon is degraded to the starter at spawn."""
    side, f, mpid = w["side"], w["field"], w["mpid"]
    req = '""' if w["starter"] else '"%s"' % REQ_LOCKED
    L = [
        'set %s "%s"' % (cvar(side, "Prev"), w["give"]),
        'set %s "%s"' % (cvar(side, "XfmW"), w["xfm"]),
        'set %s "%s"' % (cvar(side, "CharAnim"), w["anim"]),
        'set %s "%s"' % (cvar(side, "Nm"), w["name"]),
        'set %s "%s"' % (cvar(side, "Cd"), w["cd"]),
        'set %s %s' % (cvar(side, "Req"), req),
        'seta %s "%s"' % (cvar(side, "K" + f), mpid),
        'seta %s "%s"' % (cvar(side, "N" + f), w["name"]),
        'seta %s "%s"' % (cvar(side, "S" + f), w["give"]),
    ]
    return "\n".join(L) + "\n"


def tab_cfg(side, k):
    """tab<k>.cfg - show tab k, hide the rest (client-side visibility, no marker)."""
    L = ['set %s %d' % (cvar(side, "Tab%d" % i), 1 if i == k else 0) for i in range(len(TABS))]
    L.append('set %s ""' % cvar(side, "Req"))
    return "\n".join(L) + "\n"


def default_body(side):
    """The body tik the viewer opens on: skin id '01' (the starter skin), or the first parsed skin."""
    items = COS_SKINS[side]
    for oid, name, view in items:
        if oid == "01":
            return view
    return items[0][2]


def view_seed(side, prim):
    """The charRender seed lines shared by open.cfg / dopen.cfg: default body, no helmet (std baked look),
    the char transform, spin off, and the starter's hold anim. The weapon attach comes from Prev (seeded
    below); a skin/helmet pick or a weapon tile updates these live afterwards."""
    return [
        'set %s "%s"' % (cvar(side, "Char"), default_body(side)),
        'set %s ""' % cvar(side, "Helm"),
        'set %s "%s"' % (cvar(side, "XfmC"), VIEW_XFMC),
        'set %s 0' % cvar(side, "CharSpin"),
        'set %s "%s"' % (cvar(side, "CharAnim"), prim["anim"]),
    ]


def open_cfg(side, rows):
    """open.cfg - seed the view to tab 0 and the starter kit, then push the menu. No commit, no marker."""
    srows = [w for w in rows if w["side"] == side]
    prim = next(w for w in srows if w["tab"] == "RIFLE" and w["starter"])
    starters = {}
    for w in srows:
        if w["starter"]:
            starters[w["slot"]] = w
    L = ['set %s %d' % (cvar(side, "Tab%d" % i), 1 if i == 0 else 0) for i in range(len(TABS))]
    L += [
        'set %s ""' % cvar(side, "Req"),
        'set %s "%s"' % (cvar(side, "Nm"), prim["name"]),
        'set %s "%s"' % (cvar(side, "Cd"), prim["cd"]),
        'set %s "%s"' % (cvar(side, "Prev"), prim["give"]),
        'set %s "%s"' % (cvar(side, "XfmW"), prim["xfm"]),
        'set %s "%s"' % (cvar(side, "N1"), starters["p"]["name"]),
        'set %s "%s"' % (cvar(side, "N2"), starters["s"]["name"]),
        'set %s "%s"' % (cvar(side, "N3"), starters["g"]["name"]),
    ]
    L += view_seed(side, prim)
    L.append("pushmenu coop_mp%s_armory" % side)
    return "\n".join(L) + "\n"


def deploy_cfg(side):
    return "append name ,q%sd\n" % side


def defaults_open_cfg(side, rows):
    """dopen.cfg - seed the defaults view to tab 0 and the starter kit, then push the defaults menu."""
    srows = [w for w in rows if w["side"] == side]
    prim = next(w for w in srows if w["tab"] == "RIFLE" and w["starter"])
    starters = {}
    for w in srows:
        if w["starter"]:
            starters[w["slot"]] = w
    L = ['set %s %d' % (cvar(side, "Tab%d" % i), 1 if i == 0 else 0) for i in range(len(TABS))]
    L += [
        'set %s ""' % cvar(side, "Req"),
        'set %s "%s"' % (cvar(side, "Nm"), prim["name"]),
        'set %s "%s"' % (cvar(side, "Cd"), prim["cd"]),
        'set %s "%s"' % (cvar(side, "Prev"), prim["give"]),
        'set %s "%s"' % (cvar(side, "XfmW"), prim["xfm"]),
        'set %s "%s"' % (cvar(side, "N1"), starters["p"]["name"]),
        'set %s "%s"' % (cvar(side, "N2"), starters["s"]["name"]),
        'set %s "%s"' % (cvar(side, "N3"), starters["g"]["name"]),
    ]
    L += view_seed(side, prim)
    L.append("pushmenu coop_mp%s_defaults" % side)
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- emit: the .urc screen
def w_label(name, rect, text=None, link=None, order=None, model=False, xfmcvar=None, shader=None,
            enabled=None, fg="0.84 0.82 0.76 1.00", bg="0.00 0.00 0.00 0.00", border="NONE",
            font="verdana-12", attachcvar=None, attachtag=None, attachcvar2=None, attachtag2=None,
            spincvar=None, animcvar=None, modelanim=None, modeloffset=None, modelrotateoffset=None,
            modelangles=None, modelscale=None):
    L = ["resource", "Label", "{"]
    if order is not None:
        L.append("ordernumber %d" % order)
    L.append('name "%s"' % name)
    if text is not None:
        L.append('title "%s"' % text)
    L.append("rect %d %d %d %d" % rect)
    L.append("fgcolor %s" % fg)
    L.append("bgcolor %s" % bg)
    L.append('borderstyle "%s"' % border)
    if text is not None:
        L.append('font "%s"' % font)
    if link is not None:
        L.append('linkcvar "%s"' % link)
    if model:
        L.append("rendermodel 1")
        if xfmcvar:
            L.append('modelxformcvar "%s"' % xfmcvar)
        # char-viewer attachments/pose (cloned from coop_loadout.urc::charRender) - a helmet at the head
        # tag, the selected weapon at the right-hand tag, a spin toggle, and a hold anim so the body poses
        # around the weapon instead of standing in bind pose.
        if attachcvar:
            L.append('modelattachcvar "%s"' % attachcvar)
        if attachtag:
            L.append('modelattachtag "%s"' % attachtag)
        if attachcvar2:
            L.append('modelattachcvar2 "%s"' % attachcvar2)
        if attachtag2:
            L.append('modelattachtag2 "%s"' % attachtag2)
        if spincvar:
            L.append('modelspincvar "%s"' % spincvar)
        if animcvar:
            L.append('modelanimcvar "%s"' % animcvar)
        if modeloffset:
            L.append('modeloffset "%s"' % modeloffset)
        if modelrotateoffset:
            L.append('modelrotateoffset "%s"' % modelrotateoffset)
        if modelangles:
            L.append('modelangles "%s"' % modelangles)
        if modelscale is not None:
            L.append("modelscale %s" % modelscale)
        if modelanim:
            L.append("modelanim %s" % modelanim)
    if shader is not None:
        L.append('shader "%s"' % shader)
    if enabled is not None:
        L.append('enabledcvar "%s"' % enabled)
    L.append("}")
    return L


def w_button(name, rect, title, stuff, enabled=None, hover=None, away=None):
    L = ["resource", "Button", "{",
         'name "%s"' % name,
         'title "%s"' % title,
         "rect %d %d %d %d" % rect,
         "fgcolor 0.84 0.82 0.76 1.00",
         "bgcolor 0.09 0.10 0.13 0.90",
         'borderstyle "3D_BORDER"',
         'font "verdana-12"',
         'clicksound "sound/menu/apply.wav"']
    if enabled is not None:
        L.append('enabledcvar "%s"' % enabled)
    L.append('stuffcommand "%s"' % stuff)
    if hover is not None:
        L.append('hovercommand "%s"' % hover)
    if away is not None:
        L.append('mouseawaycommand "%s"' % away)
    L.append("}")
    return L


def urc(side, rows, defaults=False):
    srows = [w for w in rows if w["side"] == side]
    kind = "defaults" if defaults else "armory"
    menu = "coop_mp%s_%s" % (side, kind)
    title = ("ALLIED" if side == "a" else "AXIS") + (" DEFAULTS" if defaults else " ARMORY")
    dir_ = "coop_mp%s_armory" % side
    cfg_prefix = "d" if defaults else "c"
    side_label = "ALLIED" if side == "a" else "AXIS"
    L = [
        "// HZM MP %s %s - GENERATED by docs/tools/gen_mp_armory.py - DO NOT HAND-EDIT."
        % (side_label, "DEFAULTS" if defaults else "ARMORY"),
        "// Client-origin design: every pick execs a static cfg that archives the pick%s."
        % (" (no marker - disconnected defaults only)" if defaults
           else " and appends one\n// ,q name-bus marker"),
        "// No vstr; names no coop armory cvar or tree (isolation clauses 12/13/18).",
        'menu "%s" 640 480 NONE 1' % menu,
        "borderstyle NONE",
        "bgcolor 0 0 0 0",
        "align centerx centery",
        "virtualres 1",
        "fullscreen 0",
        "",
        "direction from_top 0",
        "",
    ]
    # background (solid; the coop_mp*_armory_bg.tga art is a later slice)
    L += w_label("bg", (0, 0, 640, 480), order=50, bg="0.05 0.06 0.08 1.00")
    L += [""]
    L += w_label("title", (306, 20, 200, 16), text=title)
    L += [""]
    if defaults:
        L += w_button("doneBtn", (560, 8, 72, 16), "DONE", "popmenu 0")
    else:
        L += w_button("deployBtn", (560, 8, 72, 16), "DEPLOY",
                      "popmenu 0 ; exec ui/%s/deploy.cfg" % dir_)
    L += [""]
    # APPEARANCE button - opens the skin/helmet/glove panel. Present on BOTH screens: the in-match armory
    # AND the disconnected defaults screen reached from Multiplayer Options. Cosmetics ride the userinfo
    # carry (no name-bus marker), so a pick made in either place persists and applies identically at spawn.
    L += w_button("appearBtn", (476, 8, 80, 16), "APPEARANCE", "pushmenu coop_mp%s_appearance" % side)
    L += [""]
    # 3D character viewer - a beat-for-beat clone of coop_loadout.urc::charRender: the player body
    # (linkcvar Char) wearing the picked helmet (attach at "Bip01 Head") and holding the selected weapon
    # (attach at "tag_weapon_right"), posed by a hold anim, with a spin toggle. Skin/helmet picks (the
    # appearance panel) drive Char/Helm; weapon tiles drive Prev + CharAnim. Everything is a client cvar -
    # no vstr, no server round-trip - so it updates live and works on the disconnected defaults screen too.
    L += w_label("charRender", (12, 82, 134, 312), order=20, model=True, fg="1.00 1.00 1.00 1.00",
                 link=cvar(side, "Char"), xfmcvar=cvar(side, "XfmC"),
                 attachcvar=cvar(side, "Helm"), attachtag="Bip01 Head",
                 attachcvar2=cvar(side, "Prev"), attachtag2="tag_weapon_right",
                 spincvar=cvar(side, "CharSpin"), animcvar=cvar(side, "CharAnim"),
                 modeloffset="78 0 -18", modelrotateoffset="0 0 0", modelangles="0 200 0",
                 modelscale="1.0", modelanim=VIEW_ANIM_BASE)
    L += [""]
    # spin toggle for the viewer (set the spin cvar 0/1 - a plain client cvar, no vstr).
    L += w_button("spinBtn", (12, 396, 134, 15), "SPIN", "toggle %s" % cvar(side, "CharSpin"))
    L += [""]
    # three slot cards
    for i in (1, 2, 3):
        y = 41 + 76 * (i - 1)
        L += w_label("slotcap%d" % i, (153, y, 140, 14), text=SLOT_NAME[{1: "p", 2: "s", 3: "g"}[i]],
                     font="verdana-12", fg="0.55 0.60 0.66 1.00")
        L += w_label("slotnm%d" % i, (153, y + 16, 140, 20), link=cvar(side, "N%d" % i))
        L += [""]
    # stats / inspect panel
    L += w_label("statNm", (478, 44, 156, 16), link=cvar(side, "Nm"))
    L += w_label("statCd", (478, 62, 156, 16), link=cvar(side, "Cd"), fg="0.62 0.66 0.70 1.00")
    L += w_label("statReq", (478, 404, 156, 44), link=cvar(side, "Req"), fg="0.86 0.55 0.30 1.00")
    L += [""]
    # tabs (3x3 grid; 8 populated)
    tx = [306, 361, 416]
    ty = [42, 59, 76]
    for k, tab in enumerate(TABS):
        rect = (tx[k % 3], ty[k // 3], 52, 15)
        L += w_button("tab%d" % k, rect, tab, "exec ui/%s/tab%d.cfg" % (dir_, k))
        L += [""]
    # tiles, grouped by tab, in TSV order; padlock overlay for locked tiles
    for k, tab in enumerate(TABS):
        ws = [w for w in srows if w["tab"] == tab]
        for pos, w in enumerate(ws):
            y = 97 + 19 * pos
            L += w_button("tile%s" % w["mpid"], (306, y, 162, 16), w["name"],
                          "exec ui/%s/%s%s.cfg" % (dir_, cfg_prefix, w["mpid"]),
                          enabled=cvar(side, "Tab%d" % k))
            if not w["starter"]:
                L += w_label("tilelk%s" % w["mpid"], (452, y + 1, 14, 14), order=8,
                             enabled=cvar(side, "Tab%d" % k),
                             shader="textures/mohmenu/coop_mp_lock.tga",
                             fg="1.00 1.00 1.00 1.00")
            L += [""]
    return "\n".join(L).rstrip("\n") + "\n"


# ---------------------------------------------------------------- emit: the MP Service Record
def record_urc():
    """ui/coop_mp_record.urc - the MP Service Record reached from Multiplayer Options. GENERATED so its
    numbers are the SAME the server enforces: it lays out the whole progression ladder - rank + total,
    then every weapon class with its live kill count / the unlock threshold and an UNLOCKED badge that
    lights when earned, then the cosmetic ladder in words. Values arrive as client cvars pushed by
    mp_progression.scr::applyUnlocks (coop_mpRank / coop_mpTotal / coop_mpCnt_<class> / coop_mpUnlockC_
    <class>); a Label with linkcvar + dontlocalize renders the cvar value as text (coop_sr.urc idiom).
    Fonts limited to facfont-20 / verdana-12 (bug-519). Shared coop_mp* cvars only (side-agnostic)."""
    unlock, perrank = PROG["unlock"], PROG["perrank"]

    def blk(kind, lines):
        return ["resource", kind, "{"] + lines + ["}", ""]

    def cap(name, rect, text, fg="0.86 0.74 0.44 1.00", font="verdana-12", align=None):
        L = ['name "%s"' % name, 'title "%s"' % text, "rect %d %d %d %d" % rect,
             "fgcolor %s" % fg, "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "%s"' % font]
        if align:
            L.append("textalign %s" % align)
        return blk("Label", L)

    def val(name, rect, link, fg="1.00 1.00 1.00 1.00"):
        return blk("Label", ['name "%s"' % name, "rect %d %d %d %d" % rect, "fgcolor %s" % fg,
                             "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "verdana-12"',
                             "dontlocalize", 'linkcvar "%s"' % link])

    L = [
        "// HZM SERVICE RECORD (MP view) - GENERATED by docs/tools/gen_mp_armory.py - DO NOT HAND-EDIT.",
        "// [user 2026-09-17] SHARED RANK: coop and MP now feed ONE rank ladder. The header shows the same",
        "// coop rank the player earns everywhere (emblem + name + prestige + total XP + XP-to-next), from the",
        "// coop_xp_* cvars pushed by coop_mod/xp.scr::xp_push_own_cvars - NOT the old kill-count coop_mpRank.",
        "// Below it, the MP challenge list shows each unlock's progress / %d-kill target / DONE badge, parsed" % unlock,
        "// from mp_progression.scr / mp_challenges.scr so the numbers match what the server enforces. No vstr.",
        'menu "coop_mp_record" 640 480 NONE 0',
        "bgcolor 1 1 1 1",
        "borderstyle NONE",
        "bgfill 0 0 0 1",
        "fullscreen 1",
        "virtualres 1",
        'include "ui/multiplayerback.inc"',
        "",
    ]
    # framed panel
    L += blk("Label", ['name "bg_panel"', "rect 96 44 448 404", "fgcolor 0.84 0.82 0.76 1.00",
                       "bgcolor 0.05 0.06 0.08 1.00", 'borderstyle "RAISED"'])
    L += cap("caption", (96, 56, 448, 24), "SERVICE RECORD", fg="0.84 0.82 0.76 1.00",
             font="facfont-20", align="xcenter")
    # [user 2026-09-17] SHARED RANK HEADER. Coop and MP now feed ONE rank ladder, so the record leads with
    # the same coop rank the player earns everywhere: emblem + rank name + prestige on the left, total XP
    # and XP-to-next-rank on the right. Values are pushed by coop_mod/xp.scr::xp_push_own_cvars (coop_xp_*),
    # NOT the old kill-count coop_mpRank/coop_mpTotal. The challenge list below shows what each unlock needs.
    L += blk("Label", ['name "rankEmblem"', "rect 110 82 44 44", "fgcolor 1.00 1.00 1.00 1.00",
                       "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', "dontlocalize",
                       'linkcvar "coop_xp_rankShader"', "linkcvartoshader"])
    L += blk("Label", ['name "rankName"', "rect 162 80 236 24", "fgcolor 0.98 0.86 0.30 1.00",
                       "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "facfont-20"',
                       "dontlocalize", 'linkcvar "coop_xp_rankName"'])
    L += cap("presCap", (162, 108, 64, 14), "PRESTIGE")
    L += val("presVal", (226, 108, 40, 14), "coop_xp_prestige")
    L += cap("xpCap", (300, 80, 80, 14), "TOTAL XP")
    L += val("xpVal", (382, 80, 60, 14), "coop_xp_totalOwn")
    L += cap("nextCap", (300, 100, 80, 14), "XP TO NEXT")
    L += val("nextVal", (382, 100, 60, 14), "coop_xp_next")
    L += cap("rankNote", (96, 130, 448, 12),
             "Rank shared with Co-op. Your rank AND these challenges both unlock weapons.",
             fg="0.55 0.60 0.66 1.00")

    # --- CHALLENGE BROWSER (79 challenges, paginated) ---
    CAT_DISP = {"rifles": "RIF", "marksman": "MRK", "smgs": "SMG", "sidearms": "PSL",
                "support": "SUP", "feats": "FEAT", "objectives": "OBJ", "modes": "MODE",
                "milestones": "MILE"}
    CLASS_STATS = set(gen_mp_challenges.CLASS_STATS)

    def prog_cvar(stat):
        if stat == "total":
            return "coop_mpTotal"
        if stat in CLASS_STATS:
            return "coop_mpCnt_%s" % stat
        return "coop_mpS_%s" % stat

    ch = gen_mp_challenges.all_challenges()
    PER = 14
    npages = (len(ch) + PER - 1) // PER

    # page selector: buttons "1".."N", each sets exactly one coop_mpSrP<p> flag on
    L += cap("pgCap", (410, 112, 40, 14), "PAGE", fg="0.55 0.60 0.66 1.00")
    for p in range(npages):
        sets = ";".join("set coop_mpSrP%d %d" % (q, 1 if q == p else 0) for q in range(npages))
        L += blk("Button", ['name "pg%d"' % p, 'title "%d"' % (p + 1),
                            "rect %d 108 22 20" % (446 + p * 24), "fgcolor 1.00 1.00 1.00 1.00",
                            "bgcolor 0.14 0.10 0.06 0.94", 'borderstyle "3D_BORDER"', 'font "verdana-12"',
                            "textalign center", 'clicksound "sound/menu/scroll.wav"',
                            'stuffcommand "%s"' % sets])

    # rows: all pages share the y band; each row is gated on its page flag. One row = tag + title +
    # live progress (linkcvar) + "/ target" + DONE badge (enabledcvar coop_mpChD<i>).
    for i, (cid, cat, title, desc, stat, tgt, rw) in enumerate(ch):
        page = i // PER
        row = i % PER
        y = 150 + row * 22
        pg = 'enabledcvar "coop_mpSrP%d"' % page
        L += blk("Label", ['name "t%d" ' % i, 'title "%s"' % CAT_DISP.get(cat, cat[:4].upper()),
                           "rect 104 %d 40 16" % y, "fgcolor 0.55 0.60 0.66 1.00",
                           "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "verdana-12"', pg])
        L += blk("Label", ['name "n%d"' % i, 'title "%s"' % title.replace('"', "'"),
                           "rect 146 %d 224 16" % y, "fgcolor 0.86 0.82 0.74 1.00",
                           "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "verdana-12"', pg])
        L += blk("Label", ['name "v%d"' % i, "rect 372 %d 34 16" % y, "fgcolor 1.00 1.00 1.00 1.00",
                           "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "verdana-12"',
                           "dontlocalize", 'linkcvar "%s"' % prog_cvar(stat), "textalign right", pg])
        L += blk("Label", ['name "s%d"' % i, 'title "/ %d"' % tgt, "rect 410 %d 44 16" % y,
                           "fgcolor 0.55 0.60 0.66 1.00", "bgcolor 0.00 0.00 0.00 0.00",
                           'borderstyle "NONE"', 'font "verdana-12"', pg])
        # DONE badge - lights only when the challenge's done cvar is set (and the page is active).
        L += blk("Label", ['name "d%d"' % i, 'title "DONE"', "rect 458 %d 70 16" % y,
                           "fgcolor 0.55 0.80 0.45 1.00", "bgcolor 0.00 0.00 0.00 0.00",
                           'borderstyle "NONE"', 'font "verdana-12"',
                           'enabledcvar "coop_mpChD%d"' % i])

    # back
    L += blk("Button", ['name "back"', "rect 8 448 96 24", "fgcolor 1.00 1.00 1.00 1.00",
                        "bgcolor 0.50 0.50 0.50 0.00", 'borderstyle "3D_BORDER"',
                        'shader "textures/mohmenu/back"', 'hovershader "textures/mohmenu/back_h"',
                        'clicksound "sound/menu/back.wav"', 'stuffcommand "Popmenu 1"'])
    L += ["end."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- emit: the roster .scr
MP_FINISHES = ["gold", "chrome", "blued", "bloody", "camo_woodland", "camo_winter", "camo_desert"]
# appearance-panel finish buttons: (index, finish token, short label). Index 0 = OFF (clears the pick,
# always available). The name-bus marker carries the numeric INDEX (grammar ,q<side>f<digits>); the server
# maps it back to the finish name in applyMarker.
MP_FINISH_OPTS = [(0, "none", "OFF"), (1, "gold", "GOLD"), (2, "chrome", "CHROME"), (3, "blued", "BLUED"),
                  (4, "bloody", "BLOODY"), (5, "camo_woodland", "WOODLND"), (6, "camo_winter", "WINTER"),
                  (7, "camo_desert", "DESERT")]


def finish_option_cfg(side, idx):
    """f<idx>.cfg - pick a weapon finish: append the ,q<side>f<idx> name-bus marker (numeric index) so the
    server (mp_armory.scr::applyMarker) records + validates it. No preview (a finish is not shown live)."""
    return "append name ,q%sf%d\n" % (side, idx)


def _coop_variants():
    """The set of variant tik paths coop shipped (models/weapons/<base>_<finish>.tik), from the generated
    reverse map. Read-only mirror of DATA - MP owns a copy, it never calls coop's loadoutskins (clause 10)."""
    p = os.path.join(MOD, "coop_mod", "loadoutskins_base.scr")
    txt = io.open(p, encoding="latin-1").read()
    return set(v for v, b in re.findall(r'coop_skinBase\["([^"]+)"\]\s*=\s*"([^"]+)"', txt))


def finish_map_scr(rows):
    """coop_mod/mp_finish_map.scr - the MP-owned weapon-FINISH map + spawn resolver. For each MP weapon
    that has coop variant tiks, records base|finish -> variant tik. mp_armory.scr::giveKit calls resolve()
    so a player who has EARNED a finish (fin:<finish> challenge) and PICKED it (userinfo coop_mpFinPick)
    deploys the variant model instead of the base. Isolation: MP file, coop_mpRun-guarded, mirrors coop's
    variant data (never calls loadoutskins), calls only mp_challenges.scr (MP->MP, clause 10)."""
    variants = _coop_variants()
    gives = sorted(set(w["give"] for w in rows if w.get("give")))
    L = [
        "//GENERATED by docs/tools/gen_mp_armory.py -- DO NOT HAND-EDIT (regenerate instead).",
        "//MP weapon-finish map: base|finish -> variant tik, for every MP weapon that has coop variants.",
        "//mp_armory.scr::giveKit calls resolve() to deploy an earned+picked finish's variant model.",
        "alive:{",
        "\tend 1",
        "}end",
        "",
        "mpfin_init:{",
        "\tif( level.coop_mpFinReady == 1 ){ end }",
        "\tlevel.coop_mpFinReady = 1",
    ]
    n = 0
    for base in gives:
        for fin in MP_FINISHES:
            var = base.replace(".tik", "_" + fin + ".tik")
            if var in variants:
                L.append('\tlevel.coop_mpFinVar["%s|%s"] = "%s"' % (base, fin, var))
                n += 1
    L.append('\tprintln( "^~^~^ MPFIN init combos=%d" )' % n)
    L.append("}end")
    L.append("")
    L += [
        "//Resolve a weapon give to its finish variant IF the player has earned + picked that finish. Returns",
        "//the variant tik, or the base unchanged. The pick is the server flag coop_mpFinSel (a finish name,",
        "//e.g. gold), set by mp_armory.scr::applyMarker only after the fin:<finish> challenge is complete -",
        "//so this is server-authoritative and needs no re-check, but we re-validate anyway (belt + braces).",
        "resolve local.p local.base:{",
        "\tlocal.out = local.base",
        "\tif( local.p == NULL || local.base == NIL || local.base == \"\" ){ end local.out }",
        "\tif( level.coop_mpRun != 1 ){ end local.out }",
        "\twaitthread mpfin_init",
        "\tlocal.fin = local.p.flags[\"coop_mpFinSel\"]",
        "\tif( local.fin == NIL || local.fin == \"\" ){ end local.out }",
        "\tif( waitthread coop_mod/mp_challenges.scr::isUnlocked local.p ( \"fin:\" + local.fin ) != 1 ){ end local.out }",
        "\tlocal.var = level.coop_mpFinVar[( local.base + \"|\" + local.fin )]",
        "\tif( local.var != NIL && local.var != \"\" ){ local.out = local.var }",
        "}end local.out",
    ]
    return "\n".join(L) + "\n"


def roster_scr(side, rows):
    srows = [w for w in rows if w["side"] == side]
    # tier = 1-based index within (progression class), file order (the starter is first per class).
    # Matches the wt:<class>:<tier> unlock tokens from gen_mp_challenges.py, so tier>=2 weapons gate on
    # coop_mpUw_<class>_<tier> / the "wt:<class>:<tier>" challenge unlock store entry.
    _tc = {}
    _tier = {}
    for w in srows:
        c = w["pclass"]
        _tc[c] = _tc.get(c, 0) + 1
        _tier[id(w)] = _tc[c]
    label = "ALLIED" if side == "a" else "AXIS"
    L = [
        "//GENERATED by docs/tools/gen_mp_armory.py -- DO NOT HAND-EDIT (regenerate instead)",
        "//MP %s armory roster. side %s. slot p=primary s=sidearm g=grenade. Read by the (future)"
        % (label, side),
        "//coop_mod/mp_armory.scr dispatcher; a compile canary on every dedicated MP boot (TRAPS T1).",
        "alive:{",
        "\tend 1",
        "}end",
        "",
        "roster_get local.id:{",
        '\tlocal.r["give"] = ""',
        "\tswitch(local.id){",
    ]
    for w in srows:
        L += [
            '\t\tcase "%s":' % w["mpid"],
            '\t\t\tlocal.r["give"] = "%s"' % w["give"],
            '\t\t\tlocal.r["name"] = "%s"' % w["name"],
            '\t\t\tlocal.r["slot"] = "%s"' % w["slot"],
            '\t\t\tlocal.r["class"] = "%s"' % w["pclass"],
            '\t\t\tlocal.r["tab"] = %d' % w["tabidx"],
            '\t\t\tlocal.r["dmclass"] = "%s"' % w["dmclass"],
            '\t\t\tlocal.r["ammo"] = "%s"' % w["ammo"],
            '\t\t\tlocal.r["ammoN"] = %s' % w["ammoN"],
            '\t\t\tlocal.r["starter"] = %d' % (1 if w["starter"] else 0),
            '\t\t\tlocal.r["tier"] = %d' % _tier[id(w)],
            "\t\t\tbreak",
        ]
    L += ["\t}", "}end local.r", ""]
    return "\n".join(L)


def prog_wpnmap_scr(rows):
    """Emit coop_mod/mp_prog_wpnmap.scr - the MP-owned exact-match weapon-model -> progression class
    map that coop_mod/mp_progression.scr reads on a scored kill. Side-agnostic (an Axis rifle kill
    advances the rifle ladder - progression classes are team-blind), so the two sides are merged and
    a model that resolves to two different classes is a generation error. This EXISTS because coop's
    chal_widFromModel misattributes and is forbidden to MP by isolation clause 10 - MP owns its own
    table, generated from the same mp_armory_roster.tsv the rosters come from so it can never drift."""
    by_model = {}
    for w in rows:
        m = w["give"].strip().lower()
        c = w["pclass"]
        if not m:
            continue
        if m in by_model and by_model[m] != c:
            raise SystemExit("gen_mp_armory: weapon %s maps to two progression classes %r and %r"
                             % (m, by_model[m], c))
        by_model[m] = c
    L = [
        "//GENERATED by docs/tools/gen_mp_armory.py -- DO NOT HAND-EDIT (regenerate instead)",
        "//MP progression weapon-model -> class map (isolation clause 10: MP owns its attribution, never",
        "//coop's chal_widFromModel). Side-agnostic: progression classes are team-blind. Read by",
        "//coop_mod/mp_progression.scr::onKill. A compile canary on every dedicated MP boot (TRAPS T1).",
        "alive:{",
        "\tend 1",
        "}end",
        "",
        "//model is matched lowercased (the caller lowercases getactiveweap's .model). Returns \"\" for an",
        "//unmapped model (projectiles, world models) - the caller logs those and credits nothing.",
        "classOf local.m:{",
        '\tlocal.c = ""',
        "\tswitch( local.m ){",
    ]
    for m in sorted(by_model):
        L.append('\t\tcase "%s":' % m)
        L.append('\t\t\tlocal.c = "%s"' % by_model[m])
        L.append("\t\t\tbreak")
    L += ["\t}", "\tend local.c", "}end local.c", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- assemble + validate the output set
def render_all(rows):
    files = {}
    for side in ("a", "x"):
        dir_ = os.path.join(MOD, "ui", "coop_mp%s_armory" % side)
        files[os.path.join(MOD, "ui", "coop_mp%s_armory.urc" % side)] = urc(side, rows)
        files[os.path.join(MOD, "ui", "coop_mp%s_defaults.urc" % side)] = urc(side, rows, defaults=True)
        files[os.path.join(dir_, "open.cfg")] = open_cfg(side, rows)
        files[os.path.join(dir_, "dopen.cfg")] = defaults_open_cfg(side, rows)
        files[os.path.join(dir_, "deploy.cfg")] = deploy_cfg(side)
        for k in range(len(TABS)):
            files[os.path.join(dir_, "tab%d.cfg" % k)] = tab_cfg(side, k)
        for w in [w for w in rows if w["side"] == side]:
            files[os.path.join(dir_, "c%s.cfg" % w["mpid"])] = commit_cfg(w)
            files[os.path.join(dir_, "d%s.cfg" % w["mpid"])] = defaults_commit_cfg(w)
        files[os.path.join(MOD, "coop_mod", "mp%s_roster.scr" % side)] = roster_scr(side, rows)
        # MP cosmetics: the appearance panel + one option cfg per skin/helmet/glove (commit via ,q bus).
        files[os.path.join(MOD, "ui", "coop_mp%s_appearance.urc" % side)] = cos_panel_urc(side)
        cdir = os.path.join(MOD, "ui", "coop_mp%s_armory" % side)
        for oid, name, view in COS_SKINS[side]:
            files[os.path.join(cdir, "k%s.cfg" % oid)] = cos_option_cfg(side, "k", oid, name, view)
        for oid, name, view in COS_HELMS:
            files[os.path.join(cdir, "h%s.cfg" % oid)] = cos_option_cfg(side, "h", oid, name, view)
        for oid, name, view in COS_GLOVES:
            files[os.path.join(cdir, "v%s.cfg" % oid)] = cos_option_cfg(side, "v", oid, name, view)
        # weapon-finish option cfgs (OFF + 7 finishes) - commit via the ,q<side>f<idx> name-bus.
        for idx, fin, lbl in MP_FINISH_OPTS:
            files[os.path.join(cdir, "f%d.cfg" % idx)] = finish_option_cfg(side, idx)
    files[os.path.join(MOD, "coop_mod", "mp_prog_wpnmap.scr")] = prog_wpnmap_scr(rows)
    files[os.path.join(MOD, "coop_mod", "mp_finish_map.scr")] = finish_map_scr(rows)
    # the MP Service Record (side-agnostic; reached from Multiplayer Options).
    files[os.path.join(MOD, "ui", "coop_mp_record.urc")] = record_urc()
    return files


def assert_clean(files):
    """Emitter assertions - abort the run before writing anything on any violation."""
    dirs = {os.path.join(MOD, "ui", "coop_mpa_armory").lower(),
            os.path.join(MOD, "ui", "coop_mpx_armory").lower()}
    exec_rx = re.compile(r'exec\s+(ui/[^\s";)]+\.cfg)', re.I)
    marker_rx = re.compile(r'append name (,q[a-z0-9]+)')
    # weapons: ,q<side><1|2|3><mpid> or ,q<side>d ; cosmetics: ,q<side><k|h|v><id>
    grammar_rx = re.compile(r'^,q[ax](?:[123]\d+|d|[khvf]\d+)\Z')
    outset = set()
    for p in files:
        if p.lower().endswith(".cfg"):
            outset.add(os.path.relpath(p, MOD).replace(os.sep, "/"))
    def strip_comments(t):
        t = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), t, flags=re.S)
        return re.sub(r"//[^\n]*", "", t)

    for p, text in files.items():
        rel = os.path.relpath(p, MOD).replace(os.sep, "/")
        try:
            text.encode("ascii")
        except UnicodeEncodeError:
            raise SystemExit("gen_mp_armory: %s is not ASCII" % rel)
        if text.startswith("﻿"):
            raise SystemExit("gen_mp_armory: %s has a BOM" % rel)
        # the token bans are judged on the comment-stripped view, exactly as check_mp_isolation.py
        # does (a token named only in a comment is documentation, not a wire).
        low = strip_comments(text).lower()
        if re.search(r"(?<![a-z0-9])coop_lo\w*", low):
            raise SystemExit("gen_mp_armory: %s names a coop armory (coop_lo*) token" % rel)
        if re.search(r"ui[/\\]+loadout[/\\]", low):
            raise SystemExit("gen_mp_armory: %s names the coop ui/loadout/ tree" % rel)
        if re.search(r"(?<![a-z0-9_])vstr\b", low):
            raise SystemExit("gen_mp_armory: %s uses vstr (banned in MP UI, clause 18)" % rel)
        # side-purity: Allied output must not name coop_mpx_, Axis must not name coop_mpa_
        side = "a" if "coop_mpa" in rel or "mpa_roster" in rel else ("x" if "coop_mpx" in rel or "mpx_roster" in rel else None)
        if side == "a" and re.search(r"(?<![a-z0-9])coop_mpx_\w*", low):
            raise SystemExit("gen_mp_armory: Allied output %s names an Axis coop_mpx_ token" % rel)
        if side == "x" and re.search(r"(?<![a-z0-9])coop_mpa_\w*", low):
            raise SystemExit("gen_mp_armory: Axis output %s names an Allied coop_mpa_ token" % rel)
        if "\n" in text and any('"' in ln and ln.count('"') % 2 for ln in text.split("\n")):
            raise SystemExit("gen_mp_armory: %s has an odd-quote line" % rel)
        for m in exec_rx.finditer(text):
            if m.group(1) not in outset:
                raise SystemExit("gen_mp_armory: %s execs %s which is not an output" % (rel, m.group(1)))
        for m in marker_rx.finditer(text):
            if not grammar_rx.match(m.group(1)):
                raise SystemExit("gen_mp_armory: %s appends a marker %r off-grammar" % (rel, m.group(1)))
    # roster .scr: no empty right-hand side (bug-1908)
    for p, text in files.items():
        if p.endswith(".scr"):
            srel = os.path.relpath(p, MOD).replace(os.sep, "/")
            for i, ln in enumerate(text.split("\n"), 1):
                if re.search(r"=\s*$", ln) and not ln.strip().startswith("//"):
                    raise SystemExit("gen_mp_armory: %s:%d has an empty right-hand side" % (srel, i))


# ---------------------------------------------------------------- modes
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode not in ("build", "check"):
        print(__doc__)
        return 2
    rows = resolve(load_rows(), load_loadout_weapons(), load_roster_ammo())
    check_invariants(rows)
    files = render_all(rows)
    assert_clean(files)

    if mode == "build":
        for p, text in sorted(files.items()):
            d = os.path.dirname(p)
            if not os.path.isdir(d):
                os.makedirs(d)
            io.open(p, "wb").write(text.encode("ascii"))
        print("wrote %d files for %d tiles (LF, ASCII)" % (len(files), len(rows)))
        return 0

    bad, missing = [], []
    for p, text in sorted(files.items()):
        rel = os.path.relpath(p, ROOT)
        if not os.path.exists(p):
            missing.append(rel)
        elif rd(p) != text:
            bad.append(rel)
    # orphan: a generated-looking file in either armory dir that we no longer emit
    keep = set(os.path.abspath(p) for p in files)
    orphan = []
    for side in ("a", "x"):
        d = os.path.join(MOD, "ui", "coop_mp%s_armory" % side)
        if os.path.isdir(d):
            for f in os.listdir(d):
                fp = os.path.abspath(os.path.join(d, f))
                if os.path.isfile(fp) and fp not in keep:
                    orphan.append(os.path.relpath(fp, ROOT))
    print("%d tiles -> %d generated files" % (len(rows), len(files)))
    print("  byte-identical : %d" % (len(files) - len(bad) - len(missing)))
    if bad:
        print("  DIFFERENT      : %d  %s" % (len(bad), bad[:8]))
    if missing:
        print("  MISSING        : %d  %s" % (len(missing), missing[:8]))
    if orphan:
        print("  on disk only   : %d  %s" % (len(orphan), orphan[:8]))
    ok = not bad and not missing and not orphan
    print("  -> %s" % ("EXACT REPRODUCTION" if ok else "MISMATCH - run: python docs/tools/gen_mp_armory.py build"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

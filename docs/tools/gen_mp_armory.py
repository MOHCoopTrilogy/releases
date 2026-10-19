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


def _read_skin_tsv(fname):
    """FULL skin roster from docs/tools/<fname>: rows (oid, stem, piece, name). ids are zero-padded 2-digit
    below 100 (compat with saved coop_mp<side>_cosSkin) and plain above."""
    rows, n = [], 0
    for l in io.open(os.path.join(ROOT, "docs", "tools", fname), encoding="utf-8"):
        if l.startswith("#") or not l.strip():
            continue
        p = (l.rstrip("\n").split("\t") + ["", ""])[:3]
        n += 1
        oid = "%02d" % n if n < 100 else "%d" % n
        rows.append((oid, p[0], p[1], p[2]))
    return rows


# [bug-2762] The FULL skin roster is the source of truth in these tsvs. It lives in its own generated data
# files (mp_skins_a/x.scr, emitted below) rather than one giant skinGet switch, which escapes the morpheus
# per-file switch-case ceiling (~150 cases/file, ~82/switch) that a 186-case skinGet blew.
SKIN_ROSTER = {"a": _read_skin_tsv("mp_allied_skins.tsv"), "x": _read_skin_tsv("mp_axis_skins.tsv")}


def load_cosmetics():
    """Skins from the tsv roster (SKIN_ROSTER); helmets parsed from helmGet in mp_cosmetics.scr."""
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

    skins = {}
    for side in ("a", "x"):
        skins[side] = [(oid, name, "models/player/" + stem + ".tik")
                       for oid, stem, piece, name in SKIN_ROSTER[side]]

    helm_rx = re.compile(r'case\s+"(\w+)":\s*local\.r\["tik"\]\s*=\s*"([^"]*)";\s*'
                         r'local\.r\["name"\]\s*=\s*"([^"]*)"')
    # [bug-2761] helmGet is now side-specific (allied US/UK vs axis German/Italian), same two-side if/else
    # shape as skinGet - parse each side into its own list so the armory offers side-correct headgear.
    helm_body = body("helmGet")
    hparts = re.split(r"\}\s*else\s*\{", helm_body, maxsplit=1)
    if len(hparts) != 2:
        raise SystemExit("gen_mp_armory: helmGet is not a two-side if/else")
    helms = {}
    for side, chunk in (("a", hparts[0]), ("x", hparts[1])):
        helms[side] = [(hid, name, "" if tik in ("std", "none") else tik)
                       for hid, tik, name in helm_rx.findall(chunk)]
        if not helms[side]:
            raise SystemExit("gen_mp_armory: no %s helmets parsed from helmGet" % side)
    return skins, helms


COS_SKINS, COS_HELMS = load_cosmetics()
# Gloves are 3P hand-surface skin bits (mp_cosmetics::writeGloveBits), not a model swap, so they cannot
# be shown in the charRender the way a skin/helmet can - the appearance panel offers them by name only.
COS_GLOVES = [("0", "BARE HANDS", ""), ("1", "GRAY GLOVES", ""), ("2", "BLACK GLOVES", ""),
              ("3", "BROWN GLOVES", ""), ("4", "TAN GLOVES", ""), ("5", "WINTER GLOVES", ""),
              ("6", "ALPINE GLOVES", "")]


# ---------------------------------------------------------------- [bug-2754] preview helmet-double fix data
def nohat_of(full_vpath):
    """The _nohat twin virtual path for a body tik if the twin exists on disk (all 24 armory skins now have
    one - Allied shipped, Axis via _research/nohat/gen_axis_nohat.py), else the full body (never a broken
    model). The MP appearance 3D PREVIEW uses the twin so an attached helmet does not double over a baked hat
    (the UI model widget cannot nodraw a surface, unlike the live spawn's mp_cosmetics::hideBakedHelmet)."""
    if not full_vpath.endswith(".tik"):
        return full_vpath
    twin = full_vpath[:-4] + "_nohat.tik"
    return twin if os.path.isfile(os.path.join(MOD, twin.replace("/", os.sep))) else full_vpath


def _allied_std_from_loadout():
    """Parse each coop loadout skin cfg (ui/loadout/skin/*.cfg) for its twin body (coop_loChar) -> its
    Standard-Issue head PIECE (coop_loStdH's `set coop_loHelm <piece>`), keyed by body stem. This reuses
    coop's already-fit-tested per-skin std hat for the MP preview. Read at generation time only - the MP
    OUTPUT carries just the models/coop_helmets/*.tik piece path (a shared asset), never a coop_lo/ui/loadout
    token (isolation clauses 12/17 are about MP output, not what the generator reads)."""
    out = {}
    d = os.path.join(MOD, "ui", "loadout", "skin")
    if not os.path.isdir(d):
        return out
    for fn in os.listdir(d):
        if not (fn.startswith("s") and fn.endswith(".cfg")):
            continue
        t = io.open(os.path.join(d, fn), encoding="latin-1").read()
        mc = re.search(r'set\s+coop_loChar\s+"[^"]*?/([^"/]+)_nohat\.tik"', t)
        ms = re.search(r'set\s+coop_loStdH\s+"set\s+coop_loHelm\s+([^"]+)"', t)
        if mc and ms:
            out[mc.group(1)] = ms.group(1).strip()
    return out


# Each MP AXIS/Italian skin -> the coop_helmets piece that matches its baked headgear (thematically AND
# head-bone-fit; coop_helmets pieces are head-local geometry). Coop's loadout is allied-only, so axis is
# mapped here by the headgear each body carries (see _research/nohat/gen_axis_nohat.py's AXIS_HEADGEAR).
AXIS_STD = {
    "german_wehrmacht_soldier":    "models/coop_helmets/coop_helmet_ger_helmet.tik",   # stahlhelm
    "german_waffenss_shutze":      "models/coop_helmets/coop_helmet_ger_covered.tik",  # coveredhelm_new
    "german_waffenss_officer":     "models/coop_helmets/coop_helmet_ss_officerhat.tik",# officerhat_new
    "german_Afrika_Private":       "models/coop_helmets/coop_helmet_ger_helmet.tik",   # germanhelmet
    "german_Afrika_Officer":       "models/coop_helmets/coop_helmet_ssncocap.tik",     # ssncocap
    "german_Panzer_Shutze":        "models/coop_helmets/coop_helmet_ger_helmet.tik",   # stahlhelm
    "german_Panzer_Tankcommander": "models/coop_helmets/coop_helmet_ger_officercap.tik",# officerhat_new
    "german_Elite_SS_officer":     "models/coop_helmets/coop_helmet_ss_officerhat.tik",# officerhat_new
    "german_Feldgendarmerie":      "models/coop_helmets/coop_helmet_ger_helmet.tik",   # stahlhelm
    "german_Kriegsmarine":         "models/coop_helmets/coop_helmet_ger_creasecap.tik",# creasecap
    "IT_AX_Ital_Vol":              "models/coop_helmets/coop_helmet_ital_volhat.tik",  # ax_it_volhat
    "Sc_AX_Ital_Inf":              "models/coop_helmets/coop_helmet_ital_infhat.tik",  # ax_ital_infhat
    # [bug-2757] axis depth batch
    "german_afrika_nco":           "models/coop_helmets/coop_helmet_ger_hat.tik",      # hat
    "german_elite_gestapo":        "models/coop_helmets/coop_helmet_ss_officerhat.tik",# officerhat_new
    "german_dday_colonel":         "models/coop_helmets/coop_helmet_ger_officercap.tik",# officercap
    "german_kradshutzen":          "models/coop_helmets/coop_helmet_ger_helmet.tik",   # stahlhelm
    "german_wehrmacht_officer":    "models/coop_helmets/coop_helmet_ger_offhat_sh.tik",# germangear/officer_hat
    "german_wehrmacht_nco":        "models/coop_helmets/coop_helmet_ger_hat.tik",      # hat
}
# [bug-2762] FULL axis roster: merge every stem->piece from docs/tools/mp_axis_skins.tsv (research-derived).
_AXTSV = os.path.join(ROOT, "docs", "tools", "mp_axis_skins.tsv")
if os.path.isfile(_AXTSV):
    for _l in io.open(_AXTSV, encoding="utf-8"):
        if _l.startswith("#") or not _l.strip():
            continue
        _v = _l.rstrip("\n").split("\t")
        if len(_v) >= 2 and _v[0] not in AXIS_STD:
            AXIS_STD[_v[0]] = _v[1]

# [bug-2762] SKIN_STD (skin -> Standard-Issue head piece for the preview) now comes straight from the tsv
# roster, which carries a piece per skin. (AXIS_STD / _allied_std_from_loadout above are retained only as the
# provenance of those tsv piece columns; the roster is authoritative.)
SKIN_STD = {}
for _side in ("a", "x"):
    for _oid, _stem, _piece, _name in SKIN_ROSTER[_side]:
        if _piece:
            SKIN_STD[_stem] = _piece


def _stem_of(view):
    """models/player/<stem>.tik -> <stem>."""
    b = os.path.basename(view)
    return b[:-4] if b.endswith(".tik") else b


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


def cos_need(field, oid):
    """The cumulative-kill threshold to unlock this cosmetic - MUST mirror mp_cosmetics.scr::cosNeed exactly
    (k skin: (n-1)*step; h helmet: n>=3 -> (n-2)*step else 0; v glove: n*step), using the steps parsed from
    that same script (PROG). 0 = free. The Service Record + server gate on the same numbers, so a retune of
    cosNeed flows through here on the next build and the menu can never quietly disagree with the game."""
    n = int(oid)
    if field == "k":
        return max(0, n - 1) * PROG["skin_step"]
    if field == "h":
        return (n - 2) * PROG["helm_step"] if n >= 3 else 0
    if field == "v":
        return n * PROG["glove_step"]
    return 0


def cos_option_cfg(side, field, oid, name, view):
    """One appearance option cfg: update the 3D viewer live (skin -> body model, helmet -> head attach;
    gloves have no model form so `view` is ""), set the chip name for feedback, and seta the carried
    USERINFO cvar (field k=skin h=helmet v=glove). No vstr (clause 18 - the MP UI is vstr-free by design),
    and NO name-bus marker: cosmetics ride the userinfo carry alone (E1), which the server validates +
    applies at spawn (mp_cosmetics::apply, which enforces cosUnlocked on the carried id). That is what lets
    the SAME cfg work both in a live match and disconnected from Multiplayer Options - a menu pick never
    pollutes the player name, and the server is still authoritative over the earned gate.

    [bug-2754] PREVIEW HELMET-DOUBLE FIX (no vstr - clause 18): the skin viewer body is the `_nohat` TWIN, and
    the skin's iconic baked hat is re-shown as an ATTACHED Standard-Issue piece (SKIN_STD, coop's fit-tested
    coop_helmets pieces). So a helmet pick attaches onto a HATLESS head - no doubling - and picking a skin
    resets the carried helmet to Standard Issue (seta cosHelm 01) so the preview matches what spawns. The
    live spawn was already correct via mp_cosmetics::hideBakedHelmet; this fixes only the menu model."""
    persist = {"k": "cosSkin", "h": "cosHelm", "v": "cosGlove"}[field]
    need = cos_need(field, oid)
    req = "" if need <= 0 else ("Unlocks at %d career kills" % need)
    L = []
    if field == "k":
        # body = the hatless twin; head = this skin's Standard-Issue piece (its baked hat, as an attach).
        # [bug-2777] seta (persist) so the preview shows this saved skin on RE-OPEN, not the default body.
        L.append('seta %s "%s"' % (cvar(side, "Char"), nohat_of(view)))
        L.append('seta %s "%s"' % (cvar(side, "Helm"), SKIN_STD.get(_stem_of(view), "")))
    elif field == "h":
        L.append('seta %s "%s"' % (cvar(side, "Helm"), view))   # [bug-2777] persist for re-open preview
    L += [
        # [bug-2777] seta (persist) the picked cosmetic NAME so the appearance panel's selName label shows
        # the last-chosen cosmetic on re-open instead of blank - the pick data itself already persists+applies
        # (vet-confirmed), this restores the visible confirmation. Display-only archive cvar.
        'seta %s "%s"' % (cvar(side, "CosNm"), name),
        # [bug-2755] show this option's unlock requirement (coop parity: coop_loCosReq). Empty for a free
        # option. The server (cosUnlocked) remains authoritative - this is display only.
        'set %s "%s"' % (cvar(side, "CosReq"), req),
        'seta %s "%s"' % (cvar(side, persist), oid),
    ]
    if field == "k":
        # [bug-2754] a skin pick resets the CARRIED helmet to Standard Issue (id 01, always free) so the live
        # spawn shows this skin's baked hat - matching the preview's twin + Standard-Issue piece. Pick a real
        # helmet afterwards to override. (coop's loadout does the same reset-to-std on a skin change.)
        L.append('seta %s "01"' % cvar(side, "cosHelm"))
    return "\n".join(L) + "\n"


def _challenge_by_token():
    """[bug-2779] reward-token -> (title, desc) from the MP challenge table, for coop-parity mouse-over text
    that names the SPECIFIC challenge that unlocks each tile (like coop_loadout's hovercommand req cfgs)."""
    out = {}
    for c in gen_mp_challenges.all_challenges():
        # KEEP FIRST occurrence: a reward can be granted by more than one challenge (e.g. a feat AND a
        # catch-all milestone). all_challenges() lists the weapon ladder, then feats/objectives/modes, then
        # milestones last, so the first hit is the intended/easier path - show that, not the 1000-kill milestone.
        if c[6] not in out:
            out[c[6]] = (c[2], c[3])   # reward token -> (title, desc)
    return out


def weapon_hover_text(w, pos):
    """[bug-2779] The specific unlock line for a weapon tile's mouse-over. Starter -> blank (no unlock). A
    gated weapon at tier pos+1 names its class-mastery challenge + the exact kill count. Built from the
    RESOLVED row (real names, bool starter) and TIER_KILLS - NOT the challenge desc, whose '(name)' suffix is
    '(-)' because gen_mp_challenges reads the raw roster where names are placeholders."""
    if w["starter"]:
        return ""
    cls = w["tab"].strip().lower()
    tier = pos + 1
    kills = gen_mp_challenges.TIER_KILLS.get(tier, 225 + (tier - 9) * 60)
    return "%s Mastery %d: %d %s kills or rank" % (w["tab"].title(), tier, kills, cls)


def cos_hover_text(field, oid, side, tok):
    """[bug-2779] The specific unlock line for a skin/helmet/glove tile. Free -> blank. If a dedicated
    challenge rewards it, name the challenge AND the career-kill fallback (either unlocks it, server two-tier);
    otherwise just the kill threshold."""
    need = cos_need(field, oid)
    if need <= 0:
        return ""
    key = {"k": "sk:%s:%s" % (side, oid), "h": "hl:%s" % oid, "v": "gl:%s" % oid}[field]
    if key in tok:
        title, desc = tok[key]
        return ("%s, or %d career kills" % (desc, need)).replace('"', "'")
    return "Unlocks at %d career kills" % need


def finish_hover_text(fin, tok):
    """[bug-2779] The specific unlock line for a weapon-finish tile. OFF -> blank; otherwise its challenge."""
    if fin == "none":
        return ""
    key = "fin:%s" % fin
    if key in tok:
        title, desc = tok[key]
        return (desc.split(" to unlock")[0]).replace('"', "'")   # strip the redundant "to unlock the X finish"
    return "Complete its Service Record challenge"


def _cos_challenge_cvars():
    """[bug-2778] Map each cosmetic that has a DEDICATED challenge to its earned client cvar, from the MP
    challenge table (`gen_mp_challenges`). Skins are per-side (`sk:<a|x>:<id>`), helmets/gloves shared
    (`hl:<id>`/`gl:<id>`). The server's `mp_cosmetics::cosUnlocked` is two-tier — a cosmetic unlocks by its
    challenge (`isUnlocked`) OR by the cumulative-kill fallback — so the padlock must hide when EITHER is met.
    Only ~37 cosmetics have a challenge; the rest unlock purely by the kill threshold and keep the plain gate."""
    out = {"k": {}, "h": {}, "v": {}}
    for c in gen_mp_challenges.all_challenges():
        parts = c[6].split(":")
        if parts[0] == "sk" and len(parts) == 3:
            out["k"][(parts[1], parts[2])] = gen_mp_challenges.reward_cvar(c[6])
        elif parts[0] == "hl" and len(parts) == 2:
            out["h"][parts[1]] = gen_mp_challenges.reward_cvar(c[6])
        elif parts[0] == "gl" and len(parts) == 2:
            out["v"][parts[1]] = gen_mp_challenges.reward_cvar(c[6])
    return out


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
                 attachcvar2=cvar(side, "S1"), attachtag2="tag_weapon_right",
                 spincvar=cvar(side, "CharSpin"), animcvar=cvar(side, "CharAnim"),
                 modeloffset="78 0 -18", modelrotateoffset="0 0 0", modelangles="0 200 0",
                 modelscale="1.0", modelanim=VIEW_ANIM_BASE)
    L += [""]
    L += w_button("spinBtn", (12, 420, 134, 15), "SPIN", "toggle %s" % cvar(side, "CharSpin"))
    L += [""]
    L += w_label("selName", (156, 34, 300, 14), link=cvar(side, "CosNm"), fg="0.86 0.74 0.44 1.00")
    L += [""]
    # [bug-2755] the selected option's unlock requirement (coop parity: coop_loCosReq). Empty for a free pick.
    L += w_label("selReq", (156, 48, 300, 12), link=cvar(side, "CosReq"), fg="0.86 0.55 0.30 1.00")
    L += [""]
    # three columns to the right of the viewer: SKIN / HELMET / GLOVES.
    # [bug-2754] the HELMET column drops id "01" (Standard Issue): a skin pick already sets the twin + this
    # skin's Standard-Issue piece, so "Standard Issue" as a shared button would need a per-skin vstr (banned)
    # and would otherwise show bareheaded. To return to standard, re-pick the skin. "No Helmet" (02) stays.
    helm_items = [h for h in COS_HELMS[side] if h[0] != "01"]
    TOP, BOT = 82, 452
    # [bug-2762] SKIN column is PAGINATED (the roster is large - up to ~80 axis skins). Page buttons above the
    # column each set exactly one coop_mp<side>_SkPg<p> flag; every skin row is gated on its page's flag (the
    # proven Service-Record page mechanism). Page 0 is seeded on menu open (view_seed). HELMET/GLOVES are small
    # so they stay single-page, auto-fit.
    chal = _cos_challenge_cvars()   # [bug-2778] per-item challenge unlock cvars, so the padlock tracks BOTH paths
    skins = COS_SKINS[side]
    SK_PER = 16
    sk_pages = max(1, (len(skins) + SK_PER - 1) // SK_PER)
    L += w_label("cap_k", (156, 60, 90, 14), text="SKIN", fg="0.55 0.60 0.66 1.00")
    L += [""]
    row0 = 78
    if sk_pages > 1:
        pw = min(24, 148 // sk_pages)   # fit all page buttons inside the 150-wide skin column (clear of helmet x310)
        for pg in range(sk_pages):
            sets = " ; ".join("set %s %d" % (cvar(side, "SkPg%d" % q), 1 if q == pg else 0)
                              for q in range(sk_pages))
            L += w_button("skpg%d" % pg, (156 + pg * pw, 74, pw - 3, 14), "%d" % (pg + 1), sets)
            L += [""]
        row0 = 92
    for i, (oid, name, view) in enumerate(skins):
        pg = i // SK_PER
        y = row0 + (i % SK_PER) * 20
        pgflag = cvar(side, "SkPg%d" % pg) if sk_pages > 1 else None
        L += w_button("opt_k%s" % oid, (156, y, 150, 17), name,
                      "exec ui/%s/k%s.cfg" % (dir_, oid), enabled=pgflag,
                      hover="exec ui/%s/hk%s.cfg" % (dir_, oid))   # [bug-2779] coop-parity unlock hint
        need = cos_need("k", oid)
        if need > 0:
            # [bug-2774/2778] the padlock CLEARS when earned by EITHER path the server honours: its dedicated
            # challenge (`!coop_mpUsk_<side><id>` — hides the instant that challenge completes) OR the
            # cumulative-kill fallback (`coop_mpTotal<need`). The multi-condition enabledcvar (uiwidget.cpp)
            # ANDs them, so the lock shows only while BOTH are unmet — matching mp_cosmetics::cosUnlocked.
            lockgate = "coop_mpTotal<%d" % need
            cv = chal["k"].get((side, oid))
            if cv:
                lockgate = "!%s %s" % (cv, lockgate)
            if pgflag:
                lockgate = "%s %s" % (pgflag, lockgate)
            L += w_label("lk_k%s" % oid, (290, y, 13, 13), order=8, enabled=lockgate,
                         shader="textures/mohmenu/coop_mp_lock.tga", fg="1.00 1.00 1.00 1.00")
        L += [""]
    # HELMET + GLOVES columns (single page, auto-fit row step to the item count).
    for capn, field, items, x in [("HELMET", "h", helm_items, 310), ("GLOVES", "v", COS_GLOVES, 464)]:
        L += w_label("cap_%s" % field, (x, 60, 150, 16), text=capn, fg="0.55 0.60 0.66 1.00")
        L += [""]
        n = len(items)
        step = 20 if n <= 1 else min(20, (BOT - TOP) // (n - 1))
        bh = max(11, min(17, step - 2))
        for i, (oid, name, view) in enumerate(items):
            y = TOP + step * i
            L += w_button("opt_%s%s" % (field, oid), (x, y, 150, bh), name,
                          "exec ui/%s/%s%s.cfg" % (dir_, field, oid),
                          hover="exec ui/%s/h%s%s.cfg" % (dir_, field, oid))   # [bug-2779] coop-parity hint
            need = cos_need(field, oid)
            if need > 0:
                # [bug-2774/2778] padlock clears when earned by EITHER path: the item's challenge
                # (`!coop_mpU{hl,gl}_<id>`) OR the cumulative-kill fallback (`coop_mpTotal<need`) - ANDed, so
                # the lock shows only while both are unmet, matching the server's two-tier cosUnlocked.
                lockgate = "coop_mpTotal<%d" % need
                cv = chal[field].get(oid)
                if cv:
                    lockgate = "!%s %s" % (cv, lockgate)
                L += w_label("lk_%s%s" % (field, oid), (x + 134, y, 13, min(13, bh)), order=8,
                             enabled=lockgate,
                             shader="textures/mohmenu/coop_mp_lock.tga", fg="1.00 1.00 1.00 1.00")
            L += [""]
    # [bug-2753] WEAPON FINISH moved OUT of here and INTO the armory (urc()) - a weapon finish is a weapon
    # property and belongs where weapons are chosen (user 2026-09-20). Appearance now carries body cosmetics only.
    return "\n".join(L).rstrip("\n") + "\n"


def locked_req(w):
    """[bug-2763] The unlock requirement on a locked weapon tile - shows the weapon is EARNABLE, not missing
    (user: 'we are missing guns' - they were padlocked with a vague message). A non-starter unlocks by kills of
    its class OR by rank; the exact kill count escalates per tier (15/30/50/75...) so we state the mechanism
    rather than a single wrong number (the old text always said 15, wrong for tier 3+; audit P2.4)."""
    return "Master the %s class (kills or rank) to unlock" % w["tab"].title()


def commit_cfg(w):
    """c<mpid>.cfg - click a tile: preview + archive the pick + append the ,q name-bus marker. EVERY
    tile now commits (slice 5); the SERVER (mp_armory.scr::applyMarker) validates the pick against the
    player's progression unlocks and denies a locked one, so a client cannot select past the gate. A
    non-starter still shows the "Unlocks with MP progression" hint + the padlock overlay until earned,
    and the server degrades a locked carried pick at deploy time."""
    side, f, mpid = w["side"], w["field"], w["mpid"]
    req = '""' if w["starter"] else '"%s"' % locked_req(w)   # [bug-2763] specific requirement, not a generic hint
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
    req = '""' if w["starter"] else '"%s"' % locked_req(w)   # [bug-2763] specific requirement, not a generic hint
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
    """The charRender seed lines shared by open.cfg / dopen.cfg: default body + its Standard-Issue hat, the
    char transform, spin off, and the starter's hold anim. The weapon attach comes from Prev (seeded below);
    a skin/helmet pick or a weapon tile updates these live afterwards. [bug-2754] the body is the `_nohat`
    TWIN with the default skin's Standard-Issue piece attached, so the opening preview shows the iconic look
    with no baked-hat doubling once a helmet is chosen."""
    # [bug-2777] Do NOT re-seed Char/Helm here. They are seta'd (persisted) by every cosmetic pick and given
    # a launch DEFAULT by the engine (cl_main.cpp mp_preview_defaults, Cvar_Get-only-if-absent), so a fresh
    # profile shows a default soldier while a saved skin/helmet is preserved and RE-DISPLAYED on re-open.
    # Re-setting them to the default on every armory open is exactly what made cosmetics "look reset" - the
    # same clobber class as the weapon-slot bug-2776. XfmC/CharSpin/CharAnim are viewer params (not saved
    # cosmetics), so they still seed here.
    return [
        'set %s 1' % cvar(side, "SkPg0"),   # [bug-2762] show skin page 1 by default (paginated skin column)
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
    # [bug-2808/user 2026-09-21] Do NOT clear the K6 deploy flag here. This cfg re-execs on EVERY engine armory
    # re-open while the player is still a spectator (UserSelectWeapon redirect), so an earlier "seta K6 0" wiped
    # a just-pressed DONE (K6=1) before the 0.5s poll could read it - that is what made DONE need 3-5 presses.
    # The authoritative per-life clear is mp_armory.scr::onTeamFlip (host: direct setcvar, lag-free; remote:
    # stufftext) guarded by holdSince>0.3s, and deploy consumes K6 on every deploy - so nothing here touches K6.
    L = []
    L += ['set %s %d' % (cvar(side, "Tab%d" % i), 1 if i == 0 else 0) for i in range(len(TABS))]
    L += [
        'set %s ""' % cvar(side, "Req"),
        'set %s "%s"' % (cvar(side, "Nm"), prim["name"]),
        'set %s "%s"' % (cvar(side, "Cd"), prim["cd"]),
        'set %s "%s"' % (cvar(side, "Prev"), prim["give"]),
        'set %s "%s"' % (cvar(side, "XfmW"), prim["xfm"]),
    ]
    # [bug-2776] Do NOT re-seed the slot labels N1/N2/N3 here. They are seta'd (persisted) by every pick
    # (c<id>.cfg / d<id>.cfg) and seeded to the starter in coop_defaults.cfg BEFORE the saved config, so the
    # loadout the player last chose survives. Re-setting them to the starter on every armory open is exactly
    # what made "the loadout resets after Done" - it clobbered (and archived over) the saved selection.
    L += view_seed(side, prim)
    L.append("pushmenu coop_mp%s_armory" % side)
    return "\n".join(L) + "\n"


def deploy_cfg(side):
    # [bug-2767] DEPLOY through a USERINFO flag (coop_mp<side>_K6), not only the name-bus. The ,q<side>d name
    # marker is silently TRUNCATED off whenever stale/appearance markers have filled the 32-char `name` cvar
    # (bug-2759), and the server cannot reliably clean a listen-host's name, so DONE was being lost and the
    # player could never leave the armory (can't-spawn, both teams, all maps). K6 is a registered CVAR_USERINFO
    # cvar (an otherwise-dead kit slot) the server reads with info_valueforkey - immune to name truncation. The
    # ,q<side>d name marker is kept as a secondary trigger for the (clean-name) case.
    return "seta %s 1\nappend name ,q%sd\n" % (cvar(side, "K6"), side)


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
    ]
    # [bug-2776] Do NOT re-seed N1/N2/N3 here - that was THE "loadout resets after Done" bug: opening the
    # defaults menu overwrote the persisted slot labels with the starter. They persist via the pick cfgs +
    # the coop_defaults.cfg starter seeds (before the saved config), so the last-chosen loadout shows on re-open.
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
                 attachcvar2=cvar(side, "S1"), attachtag2="tag_weapon_right",
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
    # [bug-2785] widened from 156w so the hover unlock text (the challenge requirement) no longer runs off
    # both edges. Sits in the free lower band (x300..634, right of the finish column at x153..298).
    L += w_label("statReq", (300, 402, 334, 28), link=cvar(side, "Req"), fg="0.86 0.55 0.30 1.00")
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
                          enabled=cvar(side, "Tab%d" % k),
                          hover="exec ui/%s/h%s.cfg" % (dir_, w["mpid"]))   # [bug-2779] coop-parity unlock hint
            if not w["starter"]:
                L += w_label("tilelk%s" % w["mpid"], (452, y + 1, 14, 14), order=8,
                             enabled=cvar(side, "Tab%d" % k),
                             shader="textures/mohmenu/coop_mp_lock.tga",
                             fg="1.00 1.00 1.00 1.00")
            L += [""]
    # [bug-2753] WEAPON FINISH - moved here from the Appearance panel (a finish is a weapon property, so it
    # lives where weapons are chosen). Single column in the free lower-centre band (below the slot cards,
    # left of the tiles). OFF + 7 finishes, each gated on its earned-finish cvar (coop_mpUfin_<finish>, pushed
    # by the challenge derivation); the server re-validates the pick. Present on BOTH the armory and the
    # disconnected defaults screen (urc builds both), so a finish set in either place persists like the kit.
    L += w_label("cap_f", (153, 250, 150, 14), text="WEAPON FINISH", font="verdana-12",
                 fg="0.55 0.60 0.66 1.00")
    L += [""]
    for i, (idx, fin, lbl) in enumerate(MP_FINISH_OPTS):
        y = 268 + 18 * i
        # [bug-2793] every finish is ALWAYS listed + clickable (the server re-validates via finUnlocked and
        # degrades a locked pick), with a PADLOCK overlay when it is not yet earned and the hover naming its
        # unlock condition - so you see the full locked/unlocked list + how to earn each, instead of the old
        # greyed-out buttons that read as "just OFF/ON".
        L += w_button("optf_%d" % idx, (153, y, 128, 16), lbl,
                      "exec ui/%s/f%d.cfg" % (dir_, idx),
                      hover="exec ui/%s/hf%d.cfg" % (dir_, idx))   # [bug-2779] coop-parity unlock hint
        if fin != "none":
            L += w_label("lkf_%d" % idx, (285, y + 1, 13, 13), order=8,
                         enabled="!coop_mpUfin_%s" % fin,
                         shader="textures/mohmenu/coop_mp_lock.tga", fg="1.00 1.00 1.00 1.00")
        L += [""]
    # [bug-2777] show the ACTIVE finish (linkcvar coop_mp<side>_FinNm) below the options, so re-opening the
    # armory reflects the saved pick instead of looking "reset". Additive labels only - nothing moves.
    yb = 268 + 18 * len(MP_FINISH_OPTS) + 4
    L += w_label("selFinCap", (153, yb, 52, 12), text="ACTIVE:", fg="0.55 0.60 0.66 1.00")
    L += w_label("selFin", (207, yb, 91, 12), link=cvar(side, "FinNm"), fg="0.86 0.74 0.44 1.00")
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
    PER = 12   # [bug-2758] was 14 - the 13th/14th rows + their progress bars ran off the bottom of the panel
    npages = (len(ch) + PER - 1) // PER

    # [user 2026-09-21] RANK PROGRESS BAR under the XP block (coop-parity with coop_sr): a dark track + a
    # linkcvartoshader fill driven by coop_xp_barMark (pushed by xp.scr), with the XP-TO-NEXT-rank callout
    # kept above it. Sits in the header's right column, clear of the pager row below.
    L += blk("Label", ['name "rankBarTrk"', "rect 300 120 224 6", "fgcolor 0.20 0.20 0.20 1.00",
                       "bgcolor 0.10 0.11 0.14 0.90", 'borderstyle "NONE"'])
    L += blk("Label", ['name "rankBarFill"', "rect 300 120 224 6", "fgcolor 1.00 1.00 1.00 1.00",
                       "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', "dontlocalize",
                       'linkcvar "coop_xp_barMark"', "linkcvartoshader"])

    # [bug-2785/2790] page selector on its OWN row, INSIDE the panel (x96..544). The previous placement ran
    # to x634 - PAST the panel's right edge (544) = off-screen - and sat at y108 over the XP block. Centered
    # with spacing that shrinks to fit any page count.
    L += cap("pgCap", (150, 150, 44, 14), "PAGE", fg="0.55 0.60 0.66 1.00")
    _psp = min(28, (516 - 200) // max(1, npages))
    _pbw = max(16, _psp - 3)
    for p in range(npages):
        sets = ";".join("set coop_mpSrP%d %d" % (q, 1 if q == p else 0) for q in range(npages))
        L += blk("Button", ['name "pg%d"' % p, 'title "%d"' % (p + 1),
                            "rect %d 148 %d 18" % (200 + p * _psp, _pbw), "fgcolor 1.00 1.00 1.00 1.00",
                            "bgcolor 0.14 0.10 0.06 0.94", 'borderstyle "3D_BORDER"', 'font "verdana-12"',
                            "textalign center", 'clicksound "sound/menu/scroll.wav"',
                            'stuffcommand "%s"' % sets])

    # rows: all pages share the y band; each row is gated on its page flag. One row = tag + title +
    # live progress (linkcvar) + "/ target" + DONE badge (enabledcvar coop_mpChD<i>).
    for i, (cid, cat, title, desc, stat, tgt, rw) in enumerate(ch):
        page = i // PER
        row = i % PER
        y = 172 + row * 22   # [bug-2790] start below the moved PAGE row (y148) + the rank bar
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
        # [bug-2756] graphical PROGRESS BAR (coop-parity with coop_sr): a dark track + a linkcvartoshader
        # fill whose shader (textures/hud/coop_bf<0..10>/coop_bfd) is pushed per challenge by
        # mp_challenges::derive. Under the title, in the row's lower gap. Reuses coop's existing bar art.
        L += blk("Label", ['name "bt%d"' % i, "rect 146 %d 224 3" % (y + 16),
                           "fgcolor 0.20 0.20 0.20 1.00", "bgcolor 0.10 0.11 0.14 0.90",
                           'borderstyle "NONE"', pg])
        L += blk("Label", ['name "bf%d"' % i, "rect 146 %d 224 3" % (y + 16),
                           "fgcolor 1.00 1.00 1.00 1.00", "bgcolor 0.00 0.00 0.00 0.00",
                           'borderstyle "NONE"', "dontlocalize",
                           'linkcvar "coop_mpB%d"' % i, "linkcvartoshader", pg])
        # [bug-2764] MOUSEOVER: a transparent hover button over the row runs a tiny cfg that sets
        # coop_mpSrHover to what this challenge unlocks; the hint label below shows it (coop-SR-style).
        # hovercommand is a Button event (uibutton.cpp); the exec cfg avoids fragile nested quotes in the URC.
        L += blk("Button", ['name "hov%d"' % i, "rect 100 %d 434 20" % y,
                            "fgcolor 1 1 1 0", "bgcolor 0 0 0 0", 'borderstyle "NONE"',
                            'hovercommand "exec ui/coop_mp_record/srhov%d.cfg"' % i, pg])

    # [bug-2764] hover hint: shows what the row under the cursor unlocks.
    L += blk("Label", ['name "srhint"', "rect 104 434 424 14", "fgcolor 0.86 0.74 0.44 1.00",
                       "bgcolor 0.00 0.00 0.00 0.00", 'borderstyle "NONE"', 'font "verdana-12"',
                       "dontlocalize", 'linkcvar "coop_mpSrHover"'])
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
    """f<idx>.cfg - pick a weapon finish. [bug-2775] seta the choice to a carried USERINFO cvar
    (coop_mp<side>_K5, a registered-but-unused kit slot) so the finish PERSISTS across sessions/servers like
    the kit + cosmetics, AND append the ,q<side>f<idx> name-bus marker so the server records+validates it this
    life. This also fixes the finish being a dead click on the disconnected DEFAULTS screen (it now setas).

    [bug-2777] Also seta the finish LABEL to a dedicated display cvar (coop_mp<side>_FinNm) so the armory
    shows the ACTIVE finish on re-open. K5 travels+persists but nothing re-displayed it, so the menu looked
    like it "reset" (it did not). FinNm is a display-only archive cvar nothing else writes - no clobber path
    (the view_seed default-reset that hides the 3D preview's saved cosmetic never touches it)."""
    lbl = next((l for (i, f, l) in MP_FINISH_OPTS if i == idx), "OFF")
    return "seta %s %d\nseta %s \"%s\"\nappend name ,q%sf%d\n" % (
        cvar(side, "K5"), idx, cvar(side, "FinNm"), lbl, side, idx)


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
    mastered_bases = []   # distinct base tiks that have >=1 variant, in a STABLE (sorted) order = bit index
    for base in gives:
        has_var = False
        for fin in MP_FINISHES:
            var = base.replace(".tik", "_" + fin + ".tik")
            if var in variants:
                L.append('\tlevel.coop_mpFinVar["%s|%s"] = "%s"' % (base, fin, var))
                n += 1
                has_var = True
        if has_var:
            mastered_bases.append(base)
    # [bug-2770] PER-WEAPON MASTERY index table. Each variant-having base gets a FIXED bit index; the
    # player's carried mastered-set bitstring (coop_mpMasterStr, persisted in the v3 progression blob) has a
    # '1' at that index once they master the weapon. mpfin_mastered() reads it to gate the variant per-gun.
    # Order is sorted+append-only: adding weapons appends higher indices, so existing persisted bits stay put.
    for i, base in enumerate(mastered_bases):
        L.append('\tlevel.coop_mpFinIdx["%s"] = %d' % (base, i))
    L.append('\tlevel.coop_mpFinIdxN = %d' % len(mastered_bases))
    L.append('\tprintln( "^~^~^ MPFIN init combos=%d masterable=%d" )' % (n, len(mastered_bases)))
    L.append("}end")
    L.append("")
    L += [
        "//[bug-2770] Has this player MASTERED local.base (its per-weapon bit set in the carried mastered set)?",
        "//A weapon with no variant / no index is UNGATED (returns 1) - nothing to gate. Mirrors coop's",
        "//loadout_finMastered: a finish variant only shows on a gun you have mastered. Mastery is earned by",
        "//per-weapon kills (mp_progression.scr::credit) and persists in the v3 blob (coop_mpMasterStr).",
        "mpfin_mastered local.p local.base:{",
        "\tif( local.p == NULL ){ end 0 }",
        "\twaitthread mpfin_init",
        "\tlocal.idx = level.coop_mpFinIdx[local.base]",
        "\tif( local.idx == NIL ){ end 1 }",
        "\tlocal.str = local.p.flags[\"coop_mpMasterStr\"]",
        "\tif( local.str == NIL || local.str == \"\" ){ end 0 }",
        "\tif( local.idx >= local.str.size ){ end 0 }",
        "\tif( local.str[local.idx] == \"1\" ){ end 1 }",
        "}end 0",
        "",
        "//Resolve a weapon give to its finish variant IF the player has earned + picked that finish AND has",
        "//MASTERED that specific weapon (bug-2770). Returns the variant tik, or the base unchanged. The pick is",
        "//the server flag coop_mpFinSel; finUnlocked re-checks the finish is earned; mpfin_mastered gates per-gun.",
        "resolve local.p local.base:{",
        "\tlocal.out = local.base",
        "\tif( local.p == NULL || local.base == NIL || local.base == \"\" ){ end local.out }",
        "\tif( level.coop_mpRun != 1 ){ end local.out }",
        "\twaitthread mpfin_init",
        "\tlocal.fin = local.p.flags[\"coop_mpFinSel\"]",
        "\tif( local.fin == NIL || local.fin == \"\" ){ end local.out }",
        "\tif( waitthread coop_mod/mp_challenges.scr::finUnlocked local.p local.fin != 1 ){ end local.out }",
        "\tif( waitthread mpfin_mastered local.p local.base != 1 ){ end local.out }",
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


def skins_data_scr(side):
    """[bug-2762] coop_mod/mp_skins_<side>.scr - the FULL skin roster in its OWN file, split into range
    sub-switches (<=48 cases) so neither the per-switch nor per-file morpheus case ceiling is hit. skinGet_<side>
    (id) dispatches by id range; each sub returns stem+name. MP file (MP_MANIFEST); returns data only, names no
    coop token; the caller (mp_cosmetics::skinGet) is coop_mpRun-guarded. Generated from mp_<side-name>_skins.tsv."""
    rows = SKIN_ROSTER[side]
    CH = 48
    nsub = max(1, (len(rows) + CH - 1) // CH)
    sname = "allied" if side == "a" else "axis"
    L = [
        "//GENERATED by docs/tools/gen_mp_armory.py -- DO NOT HAND-EDIT (regenerate instead).",
        "//[bug-2762] FULL MP %s skin roster, split into <=48-case sub-switches to stay under the morpheus" % sname,
        "//per-file/per-switch case ceiling. skinGet_%s(id) dispatches; mp_cosmetics.scr::skinGet calls it." % side,
        "//MP-isolated: returns stem/name data only, names no coop token; coop_mpRun-guarded via the caller.",
        "alive:{",
        "\tend 1",
        "}end",
        "",
        "skinGet_%s local.id:{" % side,
        '\tlocal.r["stem"] = ""',
        '\tlocal.r["name"] = ""',
        "\tlocal.n = int( local.id )",
    ]
    for s in range(nsub):
        if s < nsub - 1:
            L += ["\tif( local.n <= %d ){" % ((s + 1) * CH),
                  "\t\tlocal.r = waitthread skinGet_%s%d local.id" % (side, s + 1),
                  "\t\tend local.r",
                  "\t}"]
    L += ["\tlocal.r = waitthread skinGet_%s%d local.id" % (side, nsub),
          "\tend local.r",
          "}end local.r",
          ""]
    for s in range(nsub):
        sub = rows[s * CH:(s + 1) * CH]
        L += ["skinGet_%s%d local.id:{" % (side, s + 1),
              '\tlocal.r["stem"] = ""',
              '\tlocal.r["name"] = ""',
              "\tswitch( local.id ){"]
        for oid, stem, piece, name in sub:
            L += ['\t\tcase "%s": local.r["stem"] = "%s"; local.r["name"] = "%s"; break' % (oid, stem, name)]
        L += ["\t}", "\tend local.r", "}end local.r", ""]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- assemble + validate the output set
def render_all(rows):
    files = {}
    tok = _challenge_by_token()   # [bug-2779] reward-token -> (title, desc) for coop-parity hover hints
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
        # [bug-2762] FULL skin roster in its own data file (escapes the morpheus per-file case ceiling).
        files[os.path.join(MOD, "coop_mod", "mp_skins_%s.scr" % side)] = skins_data_scr(side)
        # MP cosmetics: the appearance panel + one option cfg per skin/helmet/glove (commit via ,q bus).
        files[os.path.join(MOD, "ui", "coop_mp%s_appearance.urc" % side)] = cos_panel_urc(side)
        cdir = os.path.join(MOD, "ui", "coop_mp%s_armory" % side)
        for oid, name, view in COS_SKINS[side]:
            files[os.path.join(cdir, "k%s.cfg" % oid)] = cos_option_cfg(side, "k", oid, name, view)
        for oid, name, view in COS_HELMS[side]:
            files[os.path.join(cdir, "h%s.cfg" % oid)] = cos_option_cfg(side, "h", oid, name, view)
        for oid, name, view in COS_GLOVES:
            files[os.path.join(cdir, "v%s.cfg" % oid)] = cos_option_cfg(side, "v", oid, name, view)
        # weapon-finish option cfgs (OFF + 7 finishes) - commit via the ,q<side>f<idx> name-bus.
        for idx, fin, lbl in MP_FINISH_OPTS:
            files[os.path.join(cdir, "f%d.cfg" % idx)] = finish_option_cfg(side, idx)
        # [bug-2779] coop-parity MOUSE-OVER unlock hints. Each tile's hovercommand execs a READ-ONLY cfg that
        # sets the requirement text (weapons/finishes -> coop_mp<side>_Req shown by statReq; cosmetics ->
        # coop_mp<side>_CosReq shown by selReq) to the SPECIFIC challenge that unlocks it, exactly like
        # coop_loadout's ui/loadout/req*.cfg hovers. No commit, no name-bus - hovering never changes the kit.
        srows_side = [w for w in rows if w["side"] == side]
        for tab in TABS:
            ws = [w for w in srows_side if w["tab"] == tab]
            for pos, w in enumerate(ws):
                files[os.path.join(cdir, "h%s.cfg" % w["mpid"])] = \
                    'set %s "%s"\n' % (cvar(side, "Req"), weapon_hover_text(w, pos))
        for idx, fin, lbl in MP_FINISH_OPTS:
            files[os.path.join(cdir, "hf%d.cfg" % idx)] = \
                'set %s "%s"\n' % (cvar(side, "Req"), finish_hover_text(fin, tok))
        for oid, name, view in COS_SKINS[side]:
            files[os.path.join(cdir, "hk%s.cfg" % oid)] = \
                'set %s "%s"\n' % (cvar(side, "CosReq"), cos_hover_text("k", oid, side, tok))
        for oid, name, view in COS_HELMS[side]:
            files[os.path.join(cdir, "hh%s.cfg" % oid)] = \
                'set %s "%s"\n' % (cvar(side, "CosReq"), cos_hover_text("h", oid, side, tok))
        for oid, name, view in COS_GLOVES:
            files[os.path.join(cdir, "hv%s.cfg" % oid)] = \
                'set %s "%s"\n' % (cvar(side, "CosReq"), cos_hover_text("v", oid, side, tok))
    files[os.path.join(MOD, "coop_mod", "mp_prog_wpnmap.scr")] = prog_wpnmap_scr(rows)
    files[os.path.join(MOD, "coop_mod", "mp_finish_map.scr")] = finish_map_scr(rows)
    # the MP Service Record (side-agnostic; reached from Multiplayer Options).
    files[os.path.join(MOD, "ui", "coop_mp_record.urc")] = record_urc()
    # [bug-2764] per-row hover cfgs for the Service Record mouseover (what each challenge unlocks).
    for i, (cid, cat, title, desc, stat, tgt, rw) in enumerate(gen_mp_challenges.all_challenges()):
        hov = ("%s  ->  unlocks %s" % (desc, gen_mp_challenges.reward_name(rw))).replace('"', "'")
        files[os.path.join(MOD, "ui", "coop_mp_record", "srhov%d.cfg" % i)] = 'set coop_mpSrHover "%s"\n' % hov
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

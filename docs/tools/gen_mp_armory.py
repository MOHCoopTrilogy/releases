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
DEFAULT_XFM = "0 0 0 1.00 0 90 180"

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


def commit_cfg(w):
    """c<mpid>.cfg - click a tile. Unlocked: preview + archive + name-bus marker. Locked: preview +
    lock text, no commit (a locked tile previews but cannot be selected until progression ships)."""
    side, f, mpid = w["side"], w["field"], w["mpid"]
    L = [
        'set %s "%s"' % (cvar(side, "Prev"), w["give"]),
        'set %s "%s"' % (cvar(side, "XfmW"), w["xfm"]),
        'set %s "%s"' % (cvar(side, "Nm"), w["name"]),
        'set %s "%s"' % (cvar(side, "Cd"), w["cd"]),
    ]
    if w["starter"]:
        L += [
            'set %s ""' % cvar(side, "Req"),
            'seta %s "%s"' % (cvar(side, "K" + f), mpid),
            'seta %s "%s"' % (cvar(side, "N" + f), w["name"]),
            'seta %s "%s"' % (cvar(side, "S" + f), w["give"]),
            "append name ,q%s%s%s" % (side, f, mpid),
        ]
    else:
        L += ['set %s "%s"' % (cvar(side, "Req"), REQ_LOCKED)]
    return "\n".join(L) + "\n"


def tab_cfg(side, k):
    """tab<k>.cfg - show tab k, hide the rest (client-side visibility, no marker)."""
    L = ['set %s %d' % (cvar(side, "Tab%d" % i), 1 if i == k else 0) for i in range(len(TABS))]
    L.append('set %s ""' % cvar(side, "Req"))
    return "\n".join(L) + "\n"


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
        "pushmenu coop_mp%s_armory" % side,
    ]
    return "\n".join(L) + "\n"


def deploy_cfg(side):
    return "append name ,q%sd\n" % side


# ---------------------------------------------------------------- emit: the .urc screen
def w_label(name, rect, text=None, link=None, order=None, model=False, xfmcvar=None, shader=None,
            enabled=None, fg="0.84 0.82 0.76 1.00", bg="0.00 0.00 0.00 0.00", border="NONE",
            font="verdana-12"):
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


def urc(side, rows):
    srows = [w for w in rows if w["side"] == side]
    menu = "coop_mp%s_armory" % side
    title = "ALLIED ARMORY" if side == "a" else "AXIS ARMORY"
    dir_ = "coop_mp%s_armory" % side
    L = [
        "// HZM MP %s ARMORY - GENERATED by docs/tools/gen_mp_armory.py - DO NOT HAND-EDIT."
        % ("ALLIED" if side == "a" else "AXIS"),
        "// Client-origin design: every pick execs a static cfg that archives the pick and appends one",
        "// ,q name-bus marker. No vstr; names no coop armory cvar or tree (isolation clauses 12/13/18).",
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
    # DEPLOY (commits nothing itself: appends the deploy marker the future dispatcher reads)
    L += w_button("deployBtn", (560, 8, 72, 16), "DEPLOY",
                  "popmenu 0 ; exec ui/%s/deploy.cfg" % dir_)
    L += [""]
    # weapon preview
    L += w_label("wprev", (12, 82, 134, 312), order=20, model=True,
                 link=cvar(side, "Prev"), xfmcvar=cvar(side, "XfmW"))
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
                          "exec ui/%s/c%s.cfg" % (dir_, w["mpid"]),
                          enabled=cvar(side, "Tab%d" % k))
            if not w["starter"]:
                L += w_label("tilelk%s" % w["mpid"], (452, y + 1, 14, 14), order=8,
                             enabled=cvar(side, "Tab%d" % k),
                             shader="textures/mohmenu/coop_mp_lock.tga",
                             fg="1.00 1.00 1.00 1.00")
            L += [""]
    return "\n".join(L).rstrip("\n") + "\n"


# ---------------------------------------------------------------- emit: the roster .scr
def roster_scr(side, rows):
    srows = [w for w in rows if w["side"] == side]
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
            "\t\t\tbreak",
        ]
    L += ["\t}", "}end local.r", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- assemble + validate the output set
def render_all(rows):
    files = {}
    for side in ("a", "x"):
        dir_ = os.path.join(MOD, "ui", "coop_mp%s_armory" % side)
        files[os.path.join(MOD, "ui", "coop_mp%s_armory.urc" % side)] = urc(side, rows)
        files[os.path.join(dir_, "open.cfg")] = open_cfg(side, rows)
        files[os.path.join(dir_, "deploy.cfg")] = deploy_cfg(side)
        for k in range(len(TABS)):
            files[os.path.join(dir_, "tab%d.cfg" % k)] = tab_cfg(side, k)
        for w in [w for w in rows if w["side"] == side]:
            files[os.path.join(dir_, "c%s.cfg" % w["mpid"])] = commit_cfg(w)
        files[os.path.join(MOD, "coop_mod", "mp%s_roster.scr" % side)] = roster_scr(side, rows)
    return files


def assert_clean(files):
    """Emitter assertions - abort the run before writing anything on any violation."""
    dirs = {os.path.join(MOD, "ui", "coop_mpa_armory").lower(),
            os.path.join(MOD, "ui", "coop_mpx_armory").lower()}
    exec_rx = re.compile(r'exec\s+(ui/[^\s";)]+\.cfg)', re.I)
    marker_rx = re.compile(r'append name (,q[a-z0-9]+)')
    grammar_rx = re.compile(r'^,q[ax](?:[123]\d+|d)\Z')
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

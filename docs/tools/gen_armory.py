#!/usr/bin/env python3
"""gen_armory.py - the "Showroom" Armory (direction B, docs/proposals/armory_redesign_2026-10-18): generated cfg families + the urc.

Imported by gen_loadout.py (render_all) so ONE `gen_loadout.py check` covers all of it. Everything here is derived: the gun table
(loadout_weapons.tsv), the stat table (armory_stats.tsv <- the weapon .tik files, gen_weapon_stats.py), the unlock text (req<id>.cfg,
derived from the scripts by gen_loadout.py) and the rank abbreviations (xp.scr).

THE ENGINE LIMITS THIS WORKS AROUND (all verified in the existing generated pages, and modelled in docs/tools/cfgsim.py):
  * widgets cannot move, and a cfg cannot branch, count, copy a cvar or concatenate a name. So "unlocked first" is a CHAIN:
    each gun's lock state is an archived command-valued cvar (coop_loSrt<id>, pushed by the server next to coop_loCmt<id>),
    the chain walks the tab's guns in order and every step executes the file for ITS (gun, card) pair.
  * a pointer cvar holds the NEXT step as a command ("exec ui/loadout/nu2_3.cfg"); executing it places the gun in the current card and
    rewrites the pointer. Pass A places the unlocked guns (the locked pointer is a no-op), pass B the locked ones, starting at the card
    after the last unlocked one (the unlocked pointer's last state published it). Card cvars are position-specific (coop_loK<c>*).
  * compare = a join of two unary-encoded levels: the slot's gun publishes, for each stat, 12 cvars coop_loJ<r>_<c> = "exec cm<r>_<e>_<c>";
    the inspected gun runs `vstr coop_loJ<r>_<its level>`. 720 tiny cm files; nothing per gun pair.
  * the server pushes ONLY what the client cannot know: the lock-aware sort command (coop_loSrt<id>) and unlock progress levels.

Second pass (2026-10-18): ONE continuous flow of 18 positions (3 rows x 6; no tab has more than 18 guns), the LOCKED label sits over the first locked card
(coop_loLbS<row>_<col>), the first four locked guns also fill the 'what unlocks next' ledger (nlw<t>_<u>_<j> -> wl_<g>_<j>), compare DELTAS are a
join of raw-value indexes (dpub / dm), finish chips carry a colour flag per finish (coop_loFp<p>C<f>), slot tiles read coop_loNs<n> (nsn<n>_<g>).

Card cvars (position c, 0..17):  coop_loK<c>V visible, L locked, T1/T2/T3 text lines, M model, X xfm, Go click, Ks selected, EqP equipped,
Kb<c>_<1..10> progress steps.  Candidate/compare cvars: coop_loCv<r> / coop_loEv<r> raw texts, coop_loCb<n|g|r><r>_<1..10> candidate bar,
coop_loEb<r>_<1..10> equipped bar, coop_loCpl/Cmi/Ceq<r> delta mark.
"""
import io
import os
import re

import gen_weapon_stats as gws

NC = 18                         # card positions: 3 rows of 6 - ONE continuous flow (unlocked first, the locked group follows; no tab has more than 18 guns)
COLS = 6
LV_NA = 11                      # level value of an n/a stat
STAT_KEYS = ["dmg", "rate", "acc", "mob", "rel"]        # r = 0..4
STAT_COLS = {"dmg": "dmgL", "rate": "rateL", "acc": "accL", "mob": "mobL", "rel": "relL"}
TABNAMES = ["RIFLE", "SNIPER", "SMG", "HEAVY", "PISTOL", "NADES"]
REQ_CARD_COLS = 15              # characters of the one-line requirement on a card


def tabs_of(rows):
    out = {t: [] for t in range(6)}
    seen = set()
    for w in rows:
        if w["id"] in seen or w["tab"] == "":
            continue
        seen.add(w["id"])
        out[int(w["tab"])].append(w)
    return out


def wrap2(s, maxc=14):
    """greedy wrap to at most two lines of maxc characters (a last line that still overflows is cut)"""
    words = s.split()
    lines, cur = [], ""
    for wd in words:
        if cur and len(cur) + 1 + len(wd) > maxc:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + " " + wd).strip()
    lines.append(cur)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    return [l[:maxc + 1] for l in lines[:2]]


def rank_abbr(mod):
    t = io.open(os.path.join(mod, "coop_mod", "xp.scr"), encoding="latin-1").read()
    names = {int(i): n for i, n in re.findall(r'coop_xp_rankName\[(\d+)\]\s*=\s*"([^"]+)"', t)}
    ab = {int(i): n for i, n in re.findall(r'coop_xp_rankAbbr\[(\d+)\]\s*=\s*"([^"]+)"', t)}
    return {names[i]: ab[i] for i in names if i in ab}


def tw(s):
    """width in menu units of verdana-12 text: the font's own glyph widths (fonts/verdana-12@3x.RitualFont) x 0.69 units per sheet unit
    (calibrated against the live menu, run ab6: "Finish the Ardennes with nobod" = 118 units, "M1 GARAND" = 48 units)"""
    import ritualfont
    return ritualfont.measure("verdana-12", s, 12.0, 1.0) * 0.69


def wrap_lines(text, maxc=11, maxl=2, maxw=54.0):
    """word wrap by ESTIMATED WIDTH (a hyphen is a break opportunity: MOSIN- / NAGANT) to at most maxl lines; a single word wider than maxw stays whole
    (the widget clips it) and the rest of the last line is cut at maxc characters"""
    words = []
    for wd in text.split():
        parts = re.findall(r"[^-]+-?|-", wd)
        words += parts if tw(wd) > maxw else [wd]
    lines, cur = [], ""
    for wd in words:
        glue = "" if cur.endswith("-") else " "
        if cur and tw(cur + glue + wd) > maxw:
            lines.append(cur)
            cur = wd
        else:
            cur = (cur + glue + wd).strip()
    if cur:
        lines.append(cur)
    if len(lines) > maxl:
        lines = lines[:maxl - 1] + [" ".join(lines[maxl - 1:])]
    out = []
    for l in lines[:maxl]:
        while tw(l) > maxw + 3 and len(l) > 3:
            l = l[:-1]
        out.append(l)
    return out


def req_lines(req, abbr):
    """the requirement printed on a locked card (<= 2 lines), from the derived hover line ('UNLOCK: Rank: Staff Sergeant')"""
    t = req.replace("UNLOCK:", "").strip()
    m = re.match(r"Rank: (.+)$", t)
    if m:
        return ["Rank " + abbr.get(m.group(1), m.group(1))]
    t = t.replace("Eliminate ", "Kill ").replace(" infantry", "").replace("long-range", "long range").replace(" w/ ", " ")
    return wrap_lines(t, 11, 2)


def split_cd(cd):
    """caliber / action / capacity line -> two short lines for the hero (first part, the rest)"""
    parts = [p.strip() for p in cd.split(" / ")]
    if len(parts) <= 1:
        return cd, ""
    return parts[0], " / ".join(parts[1:])


def raw_texts(st):
    """the five raw display strings of the compare panel (n/a never guessed)"""
    na = "n/a"
    return [
        st["dmg"] if st["dmg"] != "" else na,
        ("%s rpm" % st["rpm"]) if st["rpm"] != "" else na,
        st["acc"] if st["acc"] != "" else na,
        ("%s%%" % st["mob"]) if st["mob"] != "" else na,
        ("%.1f s" % float(st["reload_s"])) if st["reload_s"] != "" else na,
    ]


def levels(st):
    return [int(st[STAT_COLS[k]]) if st[STAT_COLS[k]] != "" else LV_NA for k in STAT_KEYS]


ABBREV = [("(IRON SIGHTS)", "IRON"), ("SILENCED", "SIL."), ("SNIPER", "SNPR"), ("SCOPED", "SCP."), ("SPRINGFIELD", "SPRNGFLD"),
          ("THOMPSON", "THOMP."), ("GEWEHR", "GEW."), ("VICKERS-BERTHIER", "VICKERS"), ("STIELHANDGRANATE", "STIELHAND"),
          ("NEBELHANDGRANATE", "NEBELHAND"), ("PANZERSCHRECK", "PZ.SCHRECK"), ("HI-STANDARD", "HI-STD"), ("LEE-ENFIELD", "ENFIELD")]


def fit_text(text, maxw):
    """one line that fits maxw menu units: apply the abbreviation ladder step by step, then cut characters and end with a full stop"""
    t = text
    for a, b in ABBREV:
        if tw(t) <= maxw:
            return t
        t = t.replace(a, b)
    t = " ".join(t.split())
    while tw(t) > maxw and len(t) > 3:
        t = t[:-2].rstrip() + "."
    return t


# One-line card names where the abbreviation ladder alone would give a meaningless cut ("WALTHER P."). A display style table (like ABBREV), checked
# against the font's own widths at build time: an entry that does not fit falls back to the ladder.
SHORT = {"02": "CARBINE", "05": "ENFIELD", "06": "SPRNGFLD", "07": "CARCANO", "09": "MOSIN", "10": "ARISAKA 99", "11": "M1 SIL.",
         "70": "JOHNSON", "78": "G43 IRON", "12": "M1903 SNP", "13": "KAR98K SN", "14": "L42A1", "15": "M1 SCOPE", "17": "ENFIELD SN",
         "18": "CARC. SNP", "19": "ARISAKA SN", "20": "MOSIN SN", "21": "MOSIN SIL.", "22": "KAR98K SIL.", "23": "DE LISLE",
         "24": "THOMPSON", "25": "T. DRUM", "27": "MP40 SIL.", "30": "PPS-43 SIL.", "31": "M3 GREASE", "32": "GREASE SIL", "33": "MOSCHET.",
         "34": "BERETTA 38", "35": "TYPE 100", "71": "T. GOLD", "38": "STG 44 SCP.", "40": "VICKERS", "42": "M1919 .30", "44": "TRENCH",
         "45": "BAZOOKA", "46": "SCHRECK", "80": "DBL BARREL", "48": "COLT 1911", "49": "COLT SIL.", "50": "P38", "51": "P38 SIL.",
         "52": "HI-STD", "53": "WEBLEY", "54": "NAGANT", "55": "BERETTA 34", "56": "BERET. SIL.", "58": "LUGER SIL.", "59": "PPK",
         "60": "TOKAREV", "61": "TT-33 SIL.", "62": "NAMBU", "63": "WELROD", "74": "MAUSER", "75": "S&W M10", "65": "STIELHAND",
         "67": "BREDA 35", "69": "NEBELHAND"}
LEDW_NAME = 70.0  # ledger row: name (left) and the percentage (right) share the 132-wide row
LEDW_REQ = 130.0  # ledger row: the one-line requirement
SLOTW = 76.0      # slot tile name line
TXTW = 50.5       # card text box in menu units: the 56-wide card minus ~3 padding each side (text starts x+3)


def card_name(g, name):
    s = SHORT.get(g)
    if s and tw(s) <= TXTW:
        return s
    return fit_text(name, TXTW)


def slot_name(g, name, maxw=None):
    """the name line of a slot tile (82-wide tile) or a ledger row: the full name when it fits, else the card short name"""
    maxw = maxw or SLOTW
    if tw(name) <= maxw:
        return name
    s = SHORT.get(g)
    if s and tw(s) <= maxw:
        return s
    return fit_text(name, maxw)


def req_line(req, abbr, maxw):
    """the ONE requirement line of a locked card: 'Rank SSgt', '175 kills', '25 headshot kills' ... (the hero panel has the full text)"""
    t = req.replace("UNLOCK:", "").strip()
    m = re.match(r"Rank: (.+)$", t)
    if m:
        return fit_text("Rank " + abbr.get(m.group(1), m.group(1)), maxw)
    t = re.sub(r" w/ .*$", "", t)
    t = t.replace("Eliminate ", "Kill ").replace(" infantry", "").replace("long-range", "long range")
    return fit_text(t, maxw)


def info_line(st, maxw):
    """the info line of an unlocked card: magazine and rate of fire, the longest form that fits"""
    clip, rpm = st["clip"], st["rpm"]
    for cand in (("%s rd/%s rpm" % (clip, rpm)) if clip and rpm else "", ("%srd/%srpm" % (clip, rpm)) if clip and rpm else "",
                 ("%s rpm" % rpm) if rpm else "", ("%s rd" % clip) if clip else ""):
        if cand and tw(cand) <= maxw:
            return cand
    return ""


def npos(n):
    return n                    # a gun sits at position 0..n-1 whatever its lock state (continuous flow)


NLEDGER = 4                     # "what unlocks next" rows: the first four locked guns of the tab
STAT_VALS = [("dmg", "dmg"), ("rpm", "rpm"), ("acc", "acc"), ("mob", "mob"), ("reload_s", "reload_s")]   # the raw numbers the compare deltas are built from
DELTA_UNIT = ["", "", "", "%", "s"]


# ------------------------------------------------------------------ cfg families -------------------------------------------------
def build(rows, files, mod):
    """-> {path relative to the mod root: text}.  `files` = gen_loadout's ui/loadout dict (for the derived req<id>.cfg texts)."""
    import gen_loadout as gl
    stats = gws.load()
    abbr = rank_abbr(mod)
    tabs = tabs_of(rows)
    out = {}
    U = "ui/loadout/"

    def put(name, lines):
        out[U + name] = "\n".join(lines) + "\n"

    def reqline(w):
        f = files.get("req%s.cfg" % w["id"])
        if not f:
            return ""
        m = re.search(r'coop_loReq "([^"]*)"', f)
        return m.group(1) if m else ""

    # ---- card clear
    # (cvar budget: the engine holds 8192 cvars in all - the per-gun "off" commands were replaced by one clear-all file, kselclr.cfg)
    put("kselclr.cfg", ["// GENERATED - clear the selected mark of every card position"] + ["set coop_loKs%d 0" % c for c in range(NC)])
    L = ["// GENERATED by gen_armory.py - clear every card position", "set coop_loLbU 0"]
    L += ["set coop_loLbS%d_%d 0" % (r, c) for r in range(NC // COLS) for c in range(COLS)]
    for j in range(NLEDGER):
        L += ["set coop_loWv%d 0" % j, "set coop_loWn%d \"\"" % j, "set coop_loWr%d \"\"" % j, "set coop_loWp%d \"\"" % j]
        L += ["set coop_loWb%d_%d 0" % (j, i) for i in range(1, 11)]
    L += ["set coop_loDl%d \"\"" % r for r in range(5)]
    for c in range(NC):
        L += ["set coop_loK%dV 0" % c, "set coop_loK%dL 0" % c, "set coop_loK%dT1 \"\"" % c, "set coop_loK%dT2 \"\"" % c,
              "set coop_loK%dGo \"set coop_loNop 0\"" % c, "set coop_loKs%d 0" % c, "set coop_loEqP%d 0" % c, "set coop_loK%dI 0" % c]
        L += ["set coop_loKb%d_%d 0" % (c, i) for i in range(1, 11)]
    put("kclr.cfg", L)

    # ---- progress join: pgpub<c> publishes the 11 level commands of card c; kbs<c>_<L> lights step L
    for c in range(NC):
        put("pgpub%d.cfg" % c, ["// GENERATED - progress join for card %d" % c]
            + ['set coop_loPgX%d "exec ui/loadout/kbs%d_%d.cfg"' % (lv, c, lv) for lv in range(11)])
        for lv in range(11):
            put("kbs%d_%d.cfg" % (c, lv), ["// GENERATED - card %d progress level %d" % (c, lv)]
                + ["set coop_loKb%d_%d %d" % (c, i, 1 if i == lv else 0) for i in range(1, 11)])
    # hero progress level files (the hero bar has its own 10 steps); hpub publishes them through the SAME per-gun command the cards use (coop_loPgA<id>)
    put("hpub.cfg", ["// GENERATED - progress join for the hero bar"] + ['set coop_loPgX%d "exec ui/loadout/hpg%d.cfg"' % (lv, lv) for lv in range(11)])
    for lv in range(11):
        put("hpg%d.cfg" % lv, ["// GENERATED - hero progress level %d" % lv] + ["set coop_loHPg%d %d" % (i, 1 if i == lv else 0) for i in range(1, 11)])

    # ledger rows: wpub<j> publishes the 11 level commands of ledger row j; wbs<j>_<L> lights step L and writes the percentage text
    for j in range(NLEDGER):
        put("wpub%d.cfg" % j, ["// GENERATED - progress join for ledger row %d" % j]
            + ['set coop_loPgX%d "exec ui/loadout/wbs%d_%d.cfg"' % (lv, j, lv) for lv in range(11)])
        for lv in range(11):
            put("wbs%d_%d.cfg" % (j, lv), ["// GENERATED - ledger row %d progress level %d" % (j, lv)]
                + ["set coop_loWb%d_%d %d" % (j, i, 1 if i == lv else 0) for i in range(1, 11)] + ['set coop_loWp%d "%d%%"' % (j, lv * 10)])

    # ---- per tab: pointer chains + fill
    for t in range(6):
        ids = [w["id"] for w in tabs[t]]
        n = len(ids)
        P = npos(n)
        for k in range(n + 1):
            nxt_u = "exec ui/loadout/nu%d_%d.cfg" % (t, k + 1) if k < n else "set coop_loNop 0"
            lu = ["// GENERATED - unlocked pointer, tab %d state %d (place card %d, then advance)" % (t, k, k)]
            if k < n:
                lu.append("vstr coop_loJU%d" % k)
                if k == 0:
                    lu.append("set coop_loLbU 1")
                c1 = k + 1                                  # unlocked placed so far: the locked group starts on the NEXT card (one continuous flow)
                lu += ["set coop_loNxU %s" % nxt_u,
                       "set coop_loUnTxt \"UNLOCKED %d\"" % c1,
                       "set coop_loLkTxt \"LOCKED %d\"" % (n - c1),
                       ("set coop_loLbLsel set coop_loLbS%d_%d 1" % (c1 // COLS, c1 % COLS)) if c1 < n else "set coop_loLbLsel set coop_loNop 0",
                       "set coop_loNxLSt set coop_loNxL exec ui/loadout/nlw%d_%d_0.cfg" % (t, c1)]
            else:
                lu.append("set coop_loNxU %s" % nxt_u)
            put("nu%d_%d.cfg" % (t, k), lu)
        for k in range(P + 1):
            nxt_l = "exec ui/loadout/nl%d_%d.cfg" % (t, k + 1) if k < P else "set coop_loNop 0"
            ll = ["// GENERATED - locked pointer, tab %d state %d (place card %d, then advance)" % (t, k, k)]
            if k < P:
                ll.append("vstr coop_loJL%d" % k)
            ll.append("set coop_loNxL %s" % nxt_l)
            put("nl%d_%d.cfg" % (t, k), ll)
        # the FIRST NLEDGER locked guns also fill the "what unlocks next" ledger (nlw<t>_<u>_<j>: u = unlocked count = first locked position)
        for u in range(n + 1):
            for j in range(NLEDGER):
                pos = u + j
                lw = ["// GENERATED - locked pointer, tab %d: %d unlocked, ledger row %d (card %d)" % (t, u, j, pos)]
                if pos < n:
                    lw += ["vstr coop_loJL%d" % pos, "vstr coop_loJW%d" % j]
                    nxt = "exec ui/loadout/nlw%d_%d_%d.cfg" % (t, u, j + 1) if j + 1 < NLEDGER else "exec ui/loadout/nl%d_%d.cfg" % (t, pos + 1)
                else:
                    nxt = "set coop_loNop 0"
                lw.append("set coop_loNxL %s" % nxt)
                put("nlw%d_%d_%d.cfg" % (t, u, j), lw)
        F = ["// GENERATED - fill the card grid of tab %d (%s): unlocked guns first, then locked on their own rows (pass A / pass B)" % (t, TABNAMES[t]),
             "exec ui/loadout/kclr.cfg",
             "set coop_loUnTxt \"UNLOCKED 0\"",
             "set coop_loLkTxt \"LOCKED %d\"" % n,
             ("set coop_loLbLsel \"set coop_loLbS0_0 1\"") if n else "set coop_loLbLsel \"set coop_loNop 0\"",
             "set coop_loNxU \"exec ui/loadout/nu%d_0.cfg\"" % t,
             "set coop_loNxL \"set coop_loNop 0\"",
             "set coop_loNxLSt \"set coop_loNxL exec ui/loadout/nlw%d_0_0.cfg\"" % t]
        F += ["vstr coop_loSrt%s" % i for i in ids]
        F += ["set coop_loNxU \"set coop_loNop 0\"", "vstr coop_loLbLsel", "vstr coop_loNxLSt"]
        F += ["vstr coop_loSrt%s" % i for i in ids]
        F += ["set coop_loRefill \"exec ui/loadout/fill%d.cfg\"" % t]
        put("fill%d.cfg" % t, F)

    # ---- compare DELTAS (+60, -278, +0.4s): a join of two raw-value indexes per stat (the cfg cannot subtract).  dpub<r>_<vi> publishes, for every candidate
    # value index c, the command that writes the delta text; dm<r>_<vi>_<c> writes it.  vi = position of the raw value among the distinct values of that stat
    # across all guns (the last index = n/a).  The colour of the text comes from the LEVEL join below (coop_loCpl/Cmi/Ceq), so "better" is always green.
    vals = []
    for r, (col, _) in enumerate(STAT_VALS):
        vals.append(sorted({float(stats[g][col]) for g in stats if stats[g][col] != ""}))

    def vidx(r, st_):
        v = st_[STAT_VALS[r][0]]
        return len(vals[r]) if v == "" else vals[r].index(float(v))

    def fmt_delta(r, d):
        if r == 4:
            d = round(d, 1)
            return "=" if d == 0 else ("%+.1fs" % d)
        d = round(d, 2)
        if d == 0:
            return "="
        return ("%+g" % d) + DELTA_UNIT[r]

    # The LEVEL (0..10 bar length, LV_NA = n/a) is a function of the raw value, so ONE join serves both: dm<r>_<vi>_<c> writes the delta text AND the level
    # comparison (bar colour, +/-/= flags); coop_loJ<r>_<c> holds the commands (the engine holds 8192 cvars in all - this saved 180 of them).
    lvl_of = []
    for r in range(5):
        m = {}
        for g in stats:
            m[vidx(r, stats[g])] = levels(stats[g])[r]
        lvl_of.append(m)
    for r in range(5):
        put("cmclr%d.cfg" % r, ["// GENERATED - clear the candidate bar + delta mark of stat row %d" % r]
            + ["set coop_loCb%s%d_%d 0" % (col, r, i) for col in "ngr" for i in range(1, 11)]
            + ["set coop_loCpl%d 0" % r, "set coop_loCmi%d 0" % r, "set coop_loCeq%d 0" % r])
        V = len(vals[r])
        for vi in range(V + 1):
            e = lvl_of[r].get(vi, LV_NA)
            P = ["// GENERATED - stat row %d: the slot's gun has raw value #%d%s (level %s)" % (r, vi, " (n/a)" if vi == V else "", "n/a" if e == LV_NA else e)]
            P += ["set coop_loEb%d_%d %d" % (r, i, 1 if (e != LV_NA and i <= e) else 0) for i in range(1, 11)]
            P += ['set coop_loJ%d_%d "exec ui/loadout/dm%d_%d_%d.cfg"' % (r, c, r, vi, c) for c in range(V + 1)]
            put("dpub%d_%d.cfg" % (r, vi), P)
            for c in range(V + 1):
                cl = lvl_of[r].get(c, LV_NA)
                txt = "" if (vi == V or c == V) else fmt_delta(r, vals[r][c] - vals[r][vi])
                C = ["// GENERATED - stat row %d: slot value #%d (level %s), candidate value #%d (level %s)" % (r, vi, "n/a" if e == LV_NA else e, c, "n/a" if cl == LV_NA else cl),
                     "exec ui/loadout/cmclr%d.cfg" % r, 'set coop_loDl%d "%s"' % (r, txt)]
                if cl != LV_NA:
                    if e == LV_NA:
                        col = "n"
                    elif cl > e:
                        col = "g"
                        C.append("set coop_loCpl%d 1" % r)
                    elif cl < e:
                        col = "r"
                        C.append("set coop_loCmi%d 1" % r)
                    else:
                        col = "n"
                        C.append("set coop_loCeq%d 1" % r)
                    if cl >= 1:
                        C.append("set coop_loCb%s%d_%d 1" % (col, r, cl))
                put("dm%d_%d_%d.cfg" % (r, vi, c), C)

    # ---- per gun: sort steps, publishers, placements, compare publish
    for t in range(6):
        ids = [w["id"] for w in tabs[t]]
        n = len(ids)
        for w in tabs[t]:
            g = w["id"]
            st = stats[g]
            put("sru%s.cfg" % g, ["// GENERATED - sort step, gun %s UNLOCKED" % g, "exec ui/loadout/uj%s.cfg" % g, "vstr coop_loNxU"])
            put("srl%s.cfg" % g, ["// GENERATED - sort step, gun %s LOCKED" % g, "exec ui/loadout/lj%s.cfg" % g, "vstr coop_loNxL"])
            put("uj%s.cfg" % g, ["// GENERATED - publish the unlocked placements of gun %s" % g]
                + ['set coop_loJU%d "exec ui/loadout/plu_%s_%d.cfg"' % (c, g, c) for c in range(n)])
            put("lj%s.cfg" % g, ["// GENERATED - publish the locked placements of gun %s" % g]
                + ['set coop_loJL%d "exec ui/loadout/pll_%s_%d.cfg"' % (c, g, c) for c in range(npos(n))]
                + ['set coop_loJW%d "exec ui/loadout/wl_%s_%d.cfg"' % (j, g, j) for j in range(NLEDGER)])
            for j in range(NLEDGER):
                put("wl_%s_%d.cfg" % (g, j), ["// GENERATED - ledger row %d shows gun %s (what unlocks next)" % (j, g),
                                              "set coop_loWv%d 1" % j,
                                              'set coop_loWn%d "%s"' % (j, slot_name(g, w["name"], LEDW_NAME)),
                                              'set coop_loWr%d "%s"' % (j, req_line(reqline(w), abbr, LEDW_REQ)),
                                              "exec ui/loadout/wpub%d.cfg" % j, "vstr coop_loPgA%s" % g])
            nm = card_name(g, w["name"])
            xf = w.get("xfmt") or w["xfm"]
            for c in range(npos(n)):
                common = ["set coop_loK%dV 1" % c,
                          "set coop_loK%dM \"%s\"" % (c, "" if g in gl.ICON2D else w["tik"]),
                          "set coop_loK%dI %d" % (c, 1 if g in gl.ICON2D else 0), "set coop_loK%dX \"%s\"" % (c, xf),
                          "set coop_loK%dGo \"exec ui/loadout/t%s.cfg\"" % (c, g),
                          "set coop_loEqOn%s \"set coop_loEqP%d 1\"" % (g, c),
                          "set coop_loSlOn%s \"set coop_loKs%d 1\"" % (g, c)]
                tl = lambda a, b_: ["set coop_loK%dT1 \"%s\"" % (c, a), "set coop_loK%dT2 \"%s\"" % (c, b_)]
                if c < n:
                    put("plu_%s_%d.cfg" % (g, c), ["// GENERATED - card %d shows gun %s (unlocked)" % (c, g), "set coop_loK%dL 0" % c]
                        + tl(nm, info_line(st, TXTW)) + common)
                if c < npos(n):
                    put("pll_%s_%d.cfg" % (g, c), ["// GENERATED - card %d shows gun %s (locked)" % (c, g), "set coop_loK%dL 1" % c]
                        + tl(nm, req_line(reqline(w), abbr, TXTW)) + common + ["exec ui/loadout/pgpub%d.cfg" % c, "vstr coop_loPgA%s" % g])
            # candidate (inspected) publish + equipped publish
            lv = levels(st)
            rt = raw_texts(st)
            cd1, cd2 = split_cd(w["cd"])
            put("cand%s.cfg" % g, ["// GENERATED - inspect gun %s: candidate stats (raw text) + the compare join against the active slot's gun" % g]
                + ["set coop_loCv%d \"%s\"" % (r, rt[r]) for r in range(5)]
                + ["set coop_loCdA \"%s\"" % cd1, "set coop_loCdB \"%s\"" % cd2]
                + ["set coop_loCandRe \"exec ui/loadout/cand%s.cfg\"" % g]
                + ["vstr coop_loJ%d_%d" % (r, vidx(r, st)) for r in range(5)])
            put("pubgun%s.cfg" % g, ["// GENERATED - publish gun %s as the EQUIPPED side of the compare" % g]
                + ["set coop_loEv%d \"%s\"" % (r, rt[r]) for r in range(5)]
                + ["exec ui/loadout/dpub%d_%d.cfg" % (r, vidx(r, st)) for r in range(5)])
            for sl in "1234":
                put("nsn%s_%s.cfg" % (sl, g), ["// GENERATED - slot %s tile name for gun %s" % (sl, g), 'set coop_loNs%s "%s"' % (sl, slot_name(g, w["name"]))])

    # ---- finish chips (f = 0 STD fixed first, f = 1..7 sorted unlocked first; VARIANT stays a fixed widget)
    FIN = ["STD", "GOLD", "CHROME", "BLUED", "BLOODY", "WOOD", "SNOW", "SAND"]
    NF = 8
    L = ["// GENERATED - clear the finish chip positions"]
    for p in range(NF):
        L += ["set coop_loFp%dC%d 0" % (p, f) for f in range(NF) if (p == 0) == (f == 0)]
        L += ["set coop_loFp%dV 0" % p, "set coop_loFp%dL 0" % p, "set coop_loFp%dT \"\"" % p, "set coop_loFp%dGo \"set coop_loNop 0\"" % p,
              "set coop_loFp%dHov \"set coop_loNop 0\"" % p]
    put("fclr.cfg", L)
    for k in range(NF + 1):
        nxt_u = "exec ui/loadout/fu_%d.cfg" % (k + 1) if k < NF else "set coop_loNop 0"
        nxt_l = "exec ui/loadout/fl_%d.cfg" % (k + 1) if k < NF else "set coop_loNop 0"
        put("fu_%d.cfg" % k, ["// GENERATED - finish chips, unlocked pointer state %d" % k]
            + (["vstr coop_loFJU%d" % k] if k < NF else [])
            + ["set coop_loFpNxU %s" % nxt_u, "set coop_loFpNxLSt set coop_loFpNxL exec ui/loadout/fl_%d.cfg" % (k + 1 if k < NF else k)])
        put("fl_%d.cfg" % k, ["// GENERATED - finish chips, locked pointer state %d" % k] + (["vstr coop_loFJL%d" % k] if k < NF else [])
            + ["set coop_loFpNxL %s" % nxt_l])
    for f in range(NF):
        for state, pre, jn in (("unlocked", "fpu", "FJU"), ("locked", "fpl", "FJL")):
            for p in range(NF):
                hov = "exec ui/loadout/reqf%d.cfg" % f if f >= 1 else "exec ui/loadout/reqclear.cfg"
                put("%s_%d_%d.cfg" % (pre, f, p), ["// GENERATED - finish chip %d shows finish %d (%s)" % (p, f, state),
                    "set coop_loFp%dV 1" % p, ("set coop_loFp%dC%d 1" % (p, f)) if (p == 0) == (f == 0) else "set coop_loNop 0", "set coop_loFp%dL %d" % (p, 0 if state == "unlocked" else 1),
                    "set coop_loFp%dT \"%s\"" % (p, FIN[f]), "set coop_loFp%dGo \"vstr coop_loFcmt%d\"" % (p, f),
                    "set coop_loFp%dHov \"%s\"" % (p, hov)])
        for pre, jn, pl in (("fuj", "FJU", "fpu"), ("flj", "FJL", "fpl")):
            put("%s%d.cfg" % (pre, f), ["// GENERATED - publish the %s chip placements of finish %d" % ("unlocked" if pre == "fuj" else "locked", f)]
                + ['set coop_lo%s%d "exec ui/loadout/%s_%d_%d.cfg"' % (jn, p, pl, f, p) for p in range(NF)])
        put("fsu%d.cfg" % f, ["// GENERATED - finish sort step, finish %d UNLOCKED" % f, "exec ui/loadout/fuj%d.cfg" % f, "vstr coop_loFpNxU"])
        put("fsl%d.cfg" % f, ["// GENERATED - finish sort step, finish %d LOCKED" % f, "exec ui/loadout/flj%d.cfg" % f, "vstr coop_loFpNxL"])
    for n in range(1, 5):
        F = ["// GENERATED - fill the finish chips for slot %d (STD first, then unlocked, then locked finishes)" % n,
             "exec ui/loadout/fclr.cfg",
             "set coop_loFpNxU \"exec ui/loadout/fu_0.cfg\"",
             "set coop_loFpNxL \"set coop_loNop 0\"",
             "set coop_loFpNxLSt \"set coop_loFpNxL exec ui/loadout/fl_0.cfg\"",
             "exec ui/loadout/fsu0.cfg"]
        F += ["vstr coop_loFsrt%d_%d" % (n, f) for f in range(1, NF)]
        F += ["set coop_loFpNxU \"set coop_loNop 0\"", "vstr coop_loFpNxLSt"]
        F += ["vstr coop_loFsrt%d_%d" % (n, f) for f in range(1, NF)]
        put("ffill%d.cfg" % n, F)

    # ---- defaults a never-connected client needs (exec'd from coop_defaults.cfg, BEFORE the saved config: they never override a push)
    D = ["// GENERATED - ARMORY defaults, exec'd by coop_defaults.cfg. The saved config loads after this and wins, so a server push (seta) is never overridden.",
         "// Fail-LOCKED, like the padlocks: every gun sorts as locked until the server says otherwise."]
    for t in range(6):
        for w in tabs[t]:
            D.append("seta coop_loSrt%s \"exec ui/loadout/srl%s.cfg\"" % (w["id"], w["id"]))
            D.append("seta coop_loPgA%s \"set coop_loNop 0\"" % w["id"])
            D.append("seta coop_loPgT%s set coop_loReqPg -" % w["id"])
    for s, g in (("1", "01"), ("2", "24"), ("3", "48"), ("4", "64")):
        D.append("seta coop_loPubS%s \"exec ui/loadout/pubgun%s.cfg\"" % (s, g))
    for s, g in (("1", "01"), ("2", "24"), ("3", "48"), ("4", "64")):
        D.append("seta coop_loNsA%s \"exec ui/loadout/nsn%s_%s.cfg\"" % (s, s, g))
        D.append("seta coop_loFNmS%s \"set coop_loFinNm STD\"" % s)
    D.append("set coop_loFinNm STD")
    D += ["seta coop_loTc%d \"0 / %d\"" % (t, len(tabs[t])) for t in range(6)]
    for n in range(1, 5):
        for f in range(1, 8):
            D.append("seta coop_loFsrt%d_%d \"exec ui/loadout/fsl%d.cfg\"" % (n, f, f))
    import gen_armory_cos as gac
    D += gac.defaults()
    D.append("seta coop_loRefill \"set coop_loNop 0\"")
    put("armory_defaults.cfg", D)
    import gen_armory_urc
    out["ui/coop_loadout.urc"] = gen_armory_urc.build_urc()
    out["coop_mod/unlockprog_gen.scr"] = progress_scr(rows, mod)
    out["coop_mod/cosring_gen.scr"] = gac.ring_scr()
    out["coop_mod/cosorder.scr"] = gac.COSORDER
    return out


def progress_scr(rows, mod):
    """coop_mod/unlockprog_gen.scr - per gated gun, the SAME primary source its hover text names (rank first, else the first challenge),
    for loadout_ui_exportProgress. Derived from xp.scr / challenges.scr / loadoutpick.scr through gen_loadout's own parsers."""
    import armory_unlocks as au
    import gen_loadout as gl
    xp, chal, lp = gl._script("xp.scr"), gl._script("challenges.scr"), gl._script("loadoutpick.scr")
    free = {t.lower() for t in au.free_guns(lp)}
    rank = {}
    for r, tok in au.rank_grants(xp):
        rank[tok.lower()] = min(r, rank.get(tok.lower(), r))
    tgt = {}
    for line in chal.splitlines():
        m = re.search(r'chal_def\s+"([^"]+)"\s+"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+(\d+)\s+"([^"]*)"', line)
        if m:
            tgt[m.group(1)] = int(m.group(2))
    rewards = au.chal_rewards(chal)
    L = ["//=========================================================================",
         "// GENERATED by docs/tools/gen_armory.py (progress_scr) - DO NOT EDIT BY HAND",
         "// The unlock source the armory's hover text names for each gated gun, as data for loadoutpick.scr::loadout_ui_exportProgress:",
         "//   Kind \"R\" = reach rank Key (XP threshold coop_xp_rankXP[Key]);  Kind \"C\" = challenge Key, Need = its target.",
         "//=========================================================================",
         "",
         "main:{",
         "\tif( level.coop_unlockProgBuilt == 1 ){ end }",
         "\tlevel.coop_unlockProgBuilt = 1"]
    tabs = tabs_of(rows)
    L.append("	//the category of every gun and the size of each category: the per-tab \"unlocked / total\" counts of loadout_ui_exportUnlocks")
    for t in range(6):
        L.append('	level.coop_loTabN[%d] = %d' % (t, len(tabs[t])))
        for w in tabs[t]:
            L.append('	level.coop_loTabOf["%s"] = %d' % (w["id"], t))
    seen = set()
    for w in rows:
        if w["id"] in seen:
            continue
        seen.add(w["id"])
        give = w["give"] or w["tik"]
        if give.lower() in free:
            continue
        if give.lower() in rank:
            L += ['\tlevel.coop_unlockProgKind["%s"] = "R"' % give, '\tlevel.coop_unlockProgKey["%s"] = %d' % (give, rank[give.lower()])]
            continue
        src = [(c, rw) for c, _t, _d, rw in rewards if rw.lower() == give.lower()]
        if src and src[0][0] in tgt:
            L += ['\tlevel.coop_unlockProgKind["%s"] = "C"' % give, '\tlevel.coop_unlockProgKey["%s"] = "%s"' % (give, src[0][0]),
                  '\tlevel.coop_unlockProgNeed["%s"] = %d' % (give, tgt[src[0][0]])]
    L += ["}end", ""]
    return "\n".join(L)

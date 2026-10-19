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

Card cvars (position c, 0..17):  coop_loK<c>V visible, L locked, T1/T2/T3 text lines, M model, X xfm, Go click, Ks selected, EqP equipped,
Kb<c>_<1..10> progress steps.  Candidate/compare cvars: coop_loCv<r> / coop_loEv<r> raw texts, coop_loCb<n|g|r><r>_<1..10> candidate bar,
coop_loEb<r>_<1..10> equipped bar, coop_loCpl/Cmi/Ceq<r> delta mark.
"""
import io
import os
import re

import gen_weapon_stats as gws

NC = 18                         # card positions (the biggest tab, PISTOL, has 18 guns)
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
    """width in menu units of verdana-12 text: the font's own glyph widths (fonts/verdana-12@3x.RitualFont) x 0.63 units per sheet unit
    (calibrated against the live menu: 'SPRINGFIELD M1903' = 76.7 units)"""
    import ritualfont
    return ritualfont.measure("verdana-12", s, 12.0, 1.0) * 0.63


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


def card_info(w, st):
    """the two info lines of an unlocked card: magazine, rate of fire"""
    return ["%s rd" % st["clip"] if st["clip"] else "", "%s rpm" % st["rpm"] if st["rpm"] else ""]


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
    L = ["// GENERATED by gen_armory.py - clear every card position", "set coop_loSelClr \"set coop_loNop 0\""]
    for c in range(NC):
        L += ["set coop_loK%dV 0" % c, "set coop_loK%dL 0" % c, "set coop_loK%dT1 \"\"" % c, "set coop_loK%dT2 \"\"" % c,
              "set coop_loK%dT3 \"\"" % c, "set coop_loK%dT4 \"\"" % c, "set coop_loK%dGo \"set coop_loNop 0\"" % c, "set coop_loKs%d 0" % c, "set coop_loEqP%d 0" % c, "set coop_loK%dI 0" % c]
        L += ["set coop_loKb%d_%d 0" % (c, i) for i in range(1, 11)]
    put("kclr.cfg", L)

    # ---- progress join: pgpub<c> publishes the 11 level commands of card c; kbs<c>_<L> lights step L
    for c in range(NC):
        put("pgpub%d.cfg" % c, ["// GENERATED - progress join for card %d" % c]
            + ['set coop_loPgX%d "exec ui/loadout/kbs%d_%d.cfg"' % (lv, c, lv) for lv in range(11)])
        for lv in range(11):
            put("kbs%d_%d.cfg" % (c, lv), ["// GENERATED - card %d progress level %d" % (c, lv)]
                + ["set coop_loKb%d_%d %d" % (c, i, 1 if i == lv else 0) for i in range(1, 11)])
    # hero progress level files (the hero bar has its own 10 steps)
    for lv in range(11):
        put("hpg%d.cfg" % lv, ["// GENERATED - hero progress level %d" % lv] + ["set coop_loHPg%d %d" % (i, 1 if i == lv else 0) for i in range(1, 11)])

    # ---- per tab: pointer chains + fill
    for t in range(6):
        ids = [w["id"] for w in tabs[t]]
        n = len(ids)
        for k in range(n + 1):
            nxt_u = "exec ui/loadout/nu%d_%d.cfg" % (t, k + 1) if k < n else "set coop_loNop 0"
            nxt_l = "exec ui/loadout/nl%d_%d.cfg" % (t, k + 1) if k < n else "set coop_loNop 0"
            lu = ["// GENERATED - unlocked pointer, tab %d state %d (place card %d, then advance)" % (t, k, k)]
            if k < n:
                lu.append("vstr coop_loJU%d" % k)
            lu += ["set coop_loNxU %s" % nxt_u,
                   "set coop_loUnTxt \"UNLOCKED %d\"" % (k + 1 if k < n else k),
                   "set coop_loLkTxt \"LOCKED %d\"" % (n - k - 1 if k < n else 0),
                   "set coop_loNxLSt set coop_loNxL exec ui/loadout/nl%d_%d.cfg" % (t, k + 1 if k < n else k)]
            put("nu%d_%d.cfg" % (t, k), lu)
            ll = ["// GENERATED - locked pointer, tab %d state %d (place card %d, then advance)" % (t, k, k)]
            if k < n:
                ll.append("vstr coop_loJL%d" % k)
            ll.append("set coop_loNxL %s" % nxt_l)
            put("nl%d_%d.cfg" % (t, k), ll)
        F = ["// GENERATED - fill the card grid of tab %d (%s): unlocked guns first, then locked (pass A / pass B)" % (t, TABNAMES[t]),
             "exec ui/loadout/kclr.cfg",
             "set coop_loUnTxt \"UNLOCKED 0\"",
             "set coop_loLkTxt \"LOCKED %d\"" % n,
             "set coop_loNxU \"exec ui/loadout/nu%d_0.cfg\"" % t,
             "set coop_loNxL \"set coop_loNop 0\"",
             "set coop_loNxLSt \"set coop_loNxL exec ui/loadout/nl%d_0.cfg\"" % t]
        F += ["vstr coop_loSrt%s" % i for i in ids]
        F += ["set coop_loNxU \"set coop_loNop 0\"", "vstr coop_loNxLSt"]
        F += ["vstr coop_loSrt%s" % i for i in ids]
        F += ["set coop_loRefill \"exec ui/loadout/fill%d.cfg\"" % t]
        put("fill%d.cfg" % t, F)

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
                + ['set coop_loJL%d "exec ui/loadout/pll_%s_%d.cfg"' % (c, g, c) for c in range(n)])
            nm = (wrap_lines(w["name"].replace("SILENCED", "SIL."), 11, 2) + [""])[:2]       # the name always owns T1/T2; info / requirement own T3/T4
            xf = w.get("xfmt") or w["xfm"]
            for c in range(n):
                common = ["set coop_loK%dV 1" % c,
                          "set coop_loK%dM \"%s\"" % (c, "" if g in gl.ICON2D else w["tik"]),
                          "set coop_loK%dI %d" % (c, 1 if g in gl.ICON2D else 0), "set coop_loK%dX \"%s\"" % (c, xf),
                          "set coop_loK%dGo \"exec ui/loadout/t%s.cfg\"" % (c, g),
                          "set coop_loEqOn%s \"set coop_loEqP%d 1\"" % (g, c), "set coop_loEqOff%s \"set coop_loEqP%d 0\"" % (g, c),
                          "set coop_loSlOn%s \"set coop_loKs%d 1\"" % (g, c), "set coop_loSlOff%s \"set coop_loKs%d 0\"" % (g, c)]
                lu = (nm + card_info(w, st) + ["", "", ""])[:4]
                ll = (nm + req_lines(reqline(w), abbr) + ["", "", ""])[:4]
                tl = lambda L4: ["set coop_loK%dT%d \"%s\"" % (c, i + 1, L4[i]) for i in range(4)]
                put("plu_%s_%d.cfg" % (g, c), ["// GENERATED - card %d shows gun %s (unlocked)" % (c, g), "set coop_loK%dL 0" % c] + tl(lu) + common)
                put("pll_%s_%d.cfg" % (g, c), ["// GENERATED - card %d shows gun %s (locked)" % (c, g), "set coop_loK%dL 1" % c] + tl(ll) + common
                    + ["exec ui/loadout/pgpub%d.cfg" % c, "vstr coop_loPgA%s" % g])
            # candidate (inspected) publish + equipped publish
            lv = levels(st)
            rt = raw_texts(st)
            cd1, cd2 = split_cd(w["cd"])
            put("cand%s.cfg" % g, ["// GENERATED - inspect gun %s: candidate stats (raw text) + the compare join against the active slot's gun" % g]
                + ["set coop_loCv%d \"%s\"" % (r, rt[r]) for r in range(5)]
                + ["set coop_loCdA \"%s\"" % cd1, "set coop_loCdB \"%s\"" % cd2]
                + ["set coop_loCandRe \"exec ui/loadout/cand%s.cfg\"" % g]
                + ["vstr coop_loJ%d_%d" % (r, lv[r]) for r in range(5)])
            put("pubgun%s.cfg" % g, ["// GENERATED - publish gun %s as the EQUIPPED side of the compare" % g]
                + ["set coop_loEv%d \"%s\"" % (r, rt[r]) for r in range(5)]
                + ["exec ui/loadout/pub%d_%d.cfg" % (r, lv[r]) for r in range(5)])

    # ---- compare tables
    for r in range(5):
        put("cmclr%d.cfg" % r, ["// GENERATED - clear the candidate bar + delta mark of stat row %d" % r]
            + ["set coop_loCb%s%d_%d 0" % (col, r, i) for col in "ngr" for i in range(1, 11)]
            + ["set coop_loCpl%d 0" % r, "set coop_loCmi%d 0" % r, "set coop_loCeq%d 0" % r])
        for e in range(12):
            P = ["// GENERATED - stat row %d: the slot's gun is at level %s" % (r, "n/a" if e == LV_NA else e)]
            P += ["set coop_loEb%d_%d %d" % (r, i, 1 if (e != LV_NA and i <= e) else 0) for i in range(1, 11)]
            P += ['set coop_loJ%d_%d "exec ui/loadout/cm%d_%d_%d.cfg"' % (r, c, r, e, c) for c in range(12)]
            put("pub%d_%d.cfg" % (r, e), P)
            for c in range(12):
                C = ["// GENERATED - stat row %d: slot %s, candidate %s" % (r, "n/a" if e == LV_NA else e, "n/a" if c == LV_NA else c),
                     "exec ui/loadout/cmclr%d.cfg" % r]
                if c != LV_NA:
                    if e == LV_NA:
                        col = "n"
                    elif c > e:
                        col = "g"
                        C.append("set coop_loCpl%d 1" % r)
                    elif c < e:
                        col = "r"
                        C.append("set coop_loCmi%d 1" % r)
                    else:
                        col = "n"
                        C.append("set coop_loCeq%d 1" % r)
                    if c >= 1:
                        C.append("set coop_loCb%s%d_%d 1" % (col, r, c))
                put("cm%d_%d_%d.cfg" % (r, e, c), C)

    # ---- finish chips (f = 0 STD fixed first, f = 1..7 sorted unlocked first; VARIANT stays a fixed widget)
    FIN = ["STD", "GOLD", "CHROM", "BLUED", "BLOOD", "WOOD", "SNOW", "SAND"]
    NF = 8
    L = ["// GENERATED - clear the finish chip positions"]
    for p in range(NF):
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
                    "set coop_loFp%dV 1" % p, "set coop_loFp%dL %d" % (p, 0 if state == "unlocked" else 1),
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
            D.append("seta coop_loPgH%s \"exec ui/loadout/hpg0.cfg\"" % w["id"])
            D.append("seta coop_loPgT%s set coop_loReqPg -" % w["id"])
    for s, g in (("1", "01"), ("2", "24"), ("3", "48"), ("4", "64")):
        D.append("seta coop_loPubS%s \"exec ui/loadout/pubgun%s.cfg\"" % (s, g))
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

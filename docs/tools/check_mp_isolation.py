#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_mp_isolation.py - PROVE the multiplayer loadout cannot touch coop.

WHY THIS EXISTS
    The user, on approving the MP loadout build (2026-09-09): "I cannot stress this enough we need
    to make sure this does not in any way impact the coop mod or experience itself."

    A promise is not a safeguard. This is the safeguard: a mechanical test of the isolation contract
    that fails loudly the moment any of it is violated, so the guarantee survives the sessions that
    come after the one that made it. build.ps1 runs it BEFORE packing, together with
    check_mp_isolation_selftest.py, which plants violations in a scratch copy to prove every rule
    here can actually fail (TRAPS T14: a check that cannot fail is worse than none).

WHAT COUNTS AS MULTIPLAYER
    Exactly the files matched by MP_MANIFEST. EVERY other file is coop. That fails closed: a new MP
    file that forgets to join the manifest is judged by the stricter coop rules, and clause 11 fails
    any MP-named file outside it.

THE CONTRACT (ISO track, 2026-09-13), and why each clause is here rather than merely sensible

  0. THE CHECKER ITSELF IS POINTED AT THE REAL TREES AND ITS TABLES ARE SANE.
     A wrong --mod/--engine would otherwise report PENDING everywhere and go green by checking nothing.
  1. NO COOP FILE MAY NAME AN MP SCRIPT OR CFG (coop_mod/mp*.scr, coop_mod/cfg/mp*.cfg).
     If a coop script ever execs MP code, the two frameworks are one framework. global/ambient.scr is
     the one sanctioned hook and belongs to clause 3. 1b: nor may it assemble one from strings
     ("coop_mod/cfg/" + "mp..."), which 1a cannot see.
  2. mp.scr's FIRST STATEMENT MUST REFUSE TO RUN WHEN COOP IS LOADED, and the guard must end.
  3. THE ambient.scr HOOK MUST BE THE ONLY ONE AND MUST BE GATED ON THE COOP TEST.
     ambient.scr is exec'd by BOTH coop maps and stock MP maps - that is why it was chosen.
  4. MP MUST NEVER WRITE A SAVED COOP CVAR, nor cvar_restart (which resets all of them).
     server.scr:238 re-seeds level.coop_health from its cvar on every map, so a cvar written in MP
     follows the player into the next coop map. Every cvar writer at qcommon/cvar.c:1781-1806 counts.
     4c: MP may not even NAME one outside a getcvar( "..." ) read - a name parked in a local and handed to
     setcvar later (local.c = "coop_prone"; setcvar local.c "0") is the same write.
  5. MP MUST NEVER WRITE coop_lockLoadout. server.scr:28 seeds it only when EMPTY: a one-way latch.
  6. ui/coop_loadout.urc IS LOCKED BY CHECKSUM (LOCKS): its generator exists in no commit, so it cannot
     be regenerated. Either committed line-ending form passes; any other byte fails. The MP-facing menus
     (multiplayer*.urc, coop_weaponselect_suppress.urc) are deliberately NOT locked - the user approved
     coop edits to them (Select Game Type cleanup, mod copies of the MP options screens, 2026-09-13).
  7. COOP FILES NEVER NAME A coop_mp* TOKEN (MP cvars, MP menus, ui/coop_mp*/ cfg trees).
  8. THE CHALLENGE AND XP SYSTEMS STAY COOP-ONLY IN MULTIPLAYER (the coop_mpRun guards).
  9. MP MUST NEVER SET flags["coop_isHost"] (spaced or not) - it unlocks dev godmode, noclip and give_all.
 10. MP CALLS ONLY THE ALLOWLISTED COOP HELPERS, never the coop armory, progression or cosmetics.
 11. EVERY MP-NAMED FILE IS IN THE MANIFEST: any file under ui/ or coop_mod/, and any script, cfg or menu
     anywhere else (.tik and assets are not judged there: stock mp40/mp44 weapons and mp_* map art are coop).
 12. MP FILES NEVER NAME A coop_lo* CVAR OR ui/loadout/, AND NEVER BUILD A coop_ NAME AT RUNTIME.
     12c: a string ending in a prefix of a saved coop cvar, coop_lo*, ui/loadout/ or a coop_mod/ path may not be
     concatenated ("coop_" + x) or parked alone ("coop_"); a join that steers into MP space ("coop_mp" + x,
     "coop_" + "mpammo", "coop_mod/mp_" + x) is legal.
 13. THE ALLIED (coop_mpa_) AND AXIS (coop_mpx_) ARMORY FILES NEVER NAME EACH OTHER'S TOKENS. The separator
     is part of the name, in the tokens and the globs, so a shared name like coop_mpammo belongs to neither.
 14. ENGINE MP CODE LIVES ONLY IN DECLARED HOOKS: // HZM-MP-BEGIN(name) ... // HZM-MP-END(name),
     each registered in ENGINE_MP_HOOKS, with no coop_lo* or ui/loadout/ inside and no coop_mp*
     token or MP script/cfg path (coop_mod/mp*.scr, coop_mod/cfg/mp*.cfg) outside.

MATCHING RULES
    Every name match is case-insensitive: the engine looks cvars up with Q_stricmp (cvar.c:109).
    Comments are stripped by TWO lexers and a hit in either counts: an escape-aware one (Morpheus
    strings, lex_source.txt:186; urc strings, script.cpp:907-925) and the escape-unaware one the cfg
    and stufftext tokenizer uses (cmd.c Cmd_TokenizeString2). Either alone can be fooled by an
    escaped quote into reading live code as a comment.

USAGE
    python docs/tools/check_mp_isolation.py              # exit 1 on any violation
    python docs/tools/check_mp_isolation.py -v           # also list what passed
    python docs/tools/check_mp_isolation.py --mod DIR --engine DIR
    python docs/tools/check_mp_isolation.py --list-clauses | --list-inputs | --print-lock REL

Output goes to stdout ONLY. Inside publish_release.ps1 ($ErrorActionPreference=Stop) a single stderr
line - even a Python SyntaxWarning from a non-raw regex - aborts the release, so every regex here
is a raw string. Clauses whose subject does not exist yet report PENDING rather than passing, so this
cannot quietly go green by testing nothing.
"""
import argparse
import hashlib
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
DEFAULT_MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
DEFAULT_ENGINE = os.path.join(ROOT, "openmohaa-hzm")

CLAUSES = [str(i) for i in range(15)]

# ---------------------------------------------------------------- tables
# The files that ARE multiplayer. Mod-relative, forward slashes, case-insensitive; * stays inside one
# path segment, ** spans segments. Everything not matched here is coop.
MP_MANIFEST = ["coop_mod/mp*.scr", "coop_mod/cfg/mp*.cfg", "ui/coop_mp*.urc", "ui/coop_mp*/**"]
# Clause 13. The separator is part of the name: coop_mpammo is shared, coop_mpa_ammo is Allied.
ALLIED_GLOBS = ["coop_mod/mpa_*.scr", "ui/coop_mpa_*.urc", "ui/coop_mpa_*/**"]
AXIS_GLOBS = ["coop_mod/mpx_*.scr", "ui/coop_mpx_*.urc", "ui/coop_mpx_*/**"]

# Clause 10. Coop scripts MP code may never call, and the only coop labels it may.
MP_COOP_DENY = {"loadoutpick", "loadout", "loadoutroster", "loadoutskins", "loadoutskins_base", "challenges",
                "xp", "medals", "helmet", "gloves", "itemhandler", "lobby", "lobbyui", "unlockreq_gen",
                "mvchal_gen"}
MP_COOP_ALLOW = {"main::containstext", "player::playercleanname", "player::coop_limpwarn",
                 "ads::coop_ads_monitor", "painbreath::wounded_monitor", "tinnitus::coop_tinnitus_monitor",
                 "tinnitus::coop_injured_muffle_monitor"}

# Clause 14. Declared engine MP hooks: name -> one-line reason. Keep this on ONE line (the self-test patches it).
ENGINE_MP_HOOKS = {}

# Clause 6. sha256 of the committed blob (LF) and of the same blob with CRLF line endings. Known writers:
# docs/tools/gen_glove_ui.py --write rewrites ui/coop_loadout.urc (:162-163), so a legitimate run of it needs a
# re-lock; gen_armory_bg.py:222 only reads it; gen_loadout.py:287 and gen_service_record.py:316 mention it in
# comments. build.ps1 runs none of them in write mode against these files (gen_loadout runs only `check`).
# ONLY this file: the MP-facing menus are left unlocked on purpose - the user approved coop edits to them
# (Select Game Type cleanup, mod copies of the MP options screens, 2026-09-13).
LOCKS = {
    "ui/coop_loadout.urc": {"sha256_lf": "0e74a2f09dd05730afcd795888bf15edc6dc2f4d3444e76b52476a36b9d14ebe", "sha256_crlf": "46e106da9dc1c5b68322fe80054d75b4da9e1e0134580410c0a119e8bbd62cd3", "lf_bytes": 75406, "blob": "1d608297", "eol": "crlf", "commit": "9a7a5e50", "locked": "2026-09-13 ISO track"},
}

# Clauses 4/5. Every saved coop cvar MP could plausibly touch [bug-2564]; each would follow the player into coop.
SAVED_COOP_CVARS = ["coop_prone", "coop_coverAuto", "coop_pickupOneMag", "coop_dmgFalloff", "coop_limp",
                    "coop_adsSpeedMult", "coop_tinnitusBaseVol", "coop_sprintStamina", "coop_breathShareStamina",
                    "coop_health"]
# Clause 12c. Names MP must not be able to assemble at runtime. A string ending in a prefix of one of these, joined
# with anything that does not provably steer away from it, is a coop name built where no static scan can see it.
BUILD_BAN = [c.lower() for c in SAVED_COOP_CVARS] + ["coop_lockloadout", "coop_lo"]
# A string held alone (no `+` after it) counts only when it is exactly one of these stubs; a longer string is a
# whole name, which 4c and 12a judge.
STUB_BAN = {"coop_", "coop_l", "coop_lo", "ui/", "ui/loadout", "coop_mod", "coop_mod/", "coop_mod/cfg/"}
# Clause 11 outside ui/ and coop_mod/. Only scripts, cfgs and menus are judged there: the stock mp40/mp44 .tik
# files and the mp_* BT map art are coop assets (369 such paths on 2026-09-13, 0 scripts). Exact lower-case paths
# of stock scripts whose names start with mp go in MP_NAME_ALLOW; there are none today.
MP_NAME_EXT = {".scr", ".cfg", ".urc", ".inc", ".st"}
MP_NAME_ALLOW = set()
RX_VERB = r"(?<![A-Za-z0-9_])(?:set[asu]?|setcvar|reset|unset|toggle|add|subtract|scale|append|bitset)\s*\(?\s*\"?"

# ---------------------------------------------------------------- patterns (all case-insensitive)
RX_COOP_LO = re.compile(r"(?<![A-Za-z0-9])coop_lo\w*", re.I)
RX_MP_TOKEN = re.compile(r"(?<![A-Za-z0-9])coop_mp\w*", re.I)
RX_MPX_TOKEN = re.compile(r"(?<![A-Za-z0-9])coop_mpx_\w*", re.I)
RX_MPA_TOKEN = re.compile(r"(?<![A-Za-z0-9])coop_mpa_\w*", re.I)
RX_UI_LOADOUT = re.compile(r"ui[/\\]+loadout[/\\]", re.I)
RX_SAVED_NAME = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(c) for c in SAVED_COOP_CVARS + ["coop_lockLoadout"])
                           + r")\b", re.I)
RX_GETCVAR_OPEN = re.compile(r"getcvar\s*\(\s*\"\Z", re.I)
# String literals as each lexer sees them (same order as both_texts), and what may follow one.
RX_LIT = (re.compile(r"\"((?:[^\"\\\r\n]|\\.)*)\""), re.compile(r"\"([^\"\r\n]*)\""))
RX_NAME_HEAD = re.compile(r"[A-Za-z0-9_/\\]*")
RX_PLUS_LIT = re.compile(r"\s*\+\s*\"")
RX_PLUS = re.compile(r"\s*\+")
RX_B_COOP_CONCAT = re.compile(br"(?i)coop[A-Za-z0-9_/\\]*\"\s*\+")
RX_MP_PATH = re.compile(r"(?<![A-Za-z0-9_])coop_mod[/\\]+(?:cfg[/\\]+)?mp\w*\.(?:scr|cfg)", re.I)
RX_MPRUN_READ = re.compile(r"level\.coop_mpRun\s*==\s*1", re.I)
RX_TIK_OK = re.compile(r"coop_mp(?:18|40r2|44strap)(?:_\w+)?", re.I)
RX_CVAR_RESTART = re.compile(r"(?<![A-Za-z0-9_])cvar_restart\b", re.I)
RX_ISHOST_SET = re.compile(r"coop_isHost\"\s*\]\s*=(?!=)", re.I)
RX_COOP_CALL = re.compile(r"(?<![A-Za-z0-9_])coop_mod[/\\]+((?:\w+[/\\]+)*\w+)\.scr(?:::(\w+))?", re.I)
RX_MP_GUARD = re.compile(r"^main\s*:\s*\{\s*if\s*\(\s*level\.coop_mainScriptLoaded\s*==\s*1\s*\)\s*\{[^{}]*\bend\s*\}",
                         re.I | re.M)
RX_AMB_HOOK = re.compile(r"if\s*\(([^()]*)\)\s*\{\s*exec\s+coop_mod/mp\.scr::main\s*\}", re.I)
RX_AMB_COND = re.compile(r"\s*(?:level\.gametype\s*!=\s*0\s*&&\s*level\.coop_mainScriptLoaded\s*!=\s*1"
                         r"|level\.coop_mainScriptLoaded\s*!=\s*1(?:\s*&&\s*level\.gametype\s*!=\s*0)?)\s*", re.I)
RX_MPRUN_GUARD = re.compile(r"if\(\s*level\.coop_mpRun\s*==\s*1\s*\)\s*\{\s*end\s*\}")
RX_HOOK_BEGIN = re.compile(r"//\s*HZM-MP-BEGIN\(\s*(\w+)\s*\)", re.I)
RX_HOOK_END = re.compile(r"//\s*HZM-MP-END\(\s*(\w+)\s*\)", re.I)

# Two lexers; both keep string literals and replace a comment with its own newlines, so line numbers hold.
LEX_ESC = re.compile(r"\"(?:[^\"\\\r\n]|\\.)*\"?|//[^\n]*|/\*.*?(?:\*/|\Z)", re.S)
LEX_NOESC = re.compile(r"\"[^\"\n]*\"?|//[^\n]*|/\*.*?(?:\*/|\Z)", re.S)

SCAN_EXT = {".scr", ".cfg", ".urc", ".inc", ".st", ".tik"}
EXCLUDE_TOP = {"_research", "_notes", "_terrain_pack"}   # never shipped (build.ps1 $excludeTop)
ENGINE_EXT = {".c", ".cpp", ".cc", ".h", ".hpp", ".inl"}


def glob_rx(glob):
    out = []
    i = 0
    while i < len(glob):
        if glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out), re.I)


def _strip_keep(m):
    s = m.group(0)
    if s[0] == "\"":
        return s
    return "\n" * s.count("\n")


def _strip_blank(m):
    s = m.group(0)
    if s[0] == "\"":
        # same length, so offsets stay equal to the kept text; an `end` inside a string cannot satisfy a guard
        return "\"" + re.sub(r"[^\n]", " ", s[1:])
    return "\n" * s.count("\n")


def both_texts(txt):
    return (LEX_ESC.sub(_strip_keep, txt), LEX_NOESC.sub(_strip_keep, txt))


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def hits(texts, rx):
    """Unique (line, lower-cased match) over every lexer's view of the file."""
    seen = set()
    for t in texts:
        for m in rx.finditer(t):
            seen.add((line_of(t, m.start()), m.group(0).lower()))
    return sorted(seen)


NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_/\\")


def norm_name(s):
    return re.sub(r"[/\\]+", "/", s).lower()


def literal_names(texts, lead):
    """Every string literal whose trailing name (letters, digits, _ and slashes) starts with `lead`, in each lexer
    view, as (text, offset, joined, mode). mode is 'lit' when `+ "..."` follows - joined then adds that string's
    leading name characters - 'var' when `+ <anything else>` follows, and 'alone' otherwise."""
    for t, rx in zip(texts, RX_LIT):
        for m in rx.finditer(t):
            s = m.group(1)
            i = len(s)
            while i and s[i - 1] in NAME_CHARS:
                i -= 1
            name = norm_name(s[i:])
            if not name.startswith(lead):
                continue
            pl = RX_PLUS_LIT.match(t, m.end())
            if pl:
                yield t, m.start(), name + norm_name(RX_NAME_HEAD.match(t, pl.end()).group(0)), "lit"
            elif RX_PLUS.match(t, m.end()):
                yield t, m.start(), name, "var"
            else:
                yield t, m.start(), name, "alone"


def builds_coop_name(joined, mode):
    """Clause 12c: does this string, with what follows it, assemble a coop cvar, ui/loadout/ or coop_mod/ path?"""
    if mode == "alone":
        return joined in STUB_BAN
    if joined == "coop_mod" or joined.startswith("coop_mod/"):
        return not joined.startswith(("coop_mod/mp", "coop_mod/cfg/mp"))
    if joined.startswith("coop_"):
        return (joined.startswith("coop_lo") or "coop_mod/".startswith(joined)
                or any(b.startswith(joined) for b in BUILD_BAN))
    if joined.startswith("ui/"):
        return joined.startswith("ui/loadout/") or "ui/loadout/".startswith(joined)
    return False


def where(rel, line=None):
    return rel if line is None else "%s:%d" % (rel, line)


class Result(object):
    def __init__(self):
        self.passed, self.pending, self.warns, self.fails = [], [], [], []
        self.inputs = set()
        self.n_mod = 0
        self.n_engine = 0

    def ok(self, clause, msg):
        self.passed.append("[%s] %s" % (clause, msg))

    def pend(self, clause, msg):
        self.pending.append("[%s] %s" % (clause, msg))

    def warn(self, sid, loc, msg):
        self.warns.append("[%s] %s %s" % (sid, loc, msg))

    def fail(self, sid, loc, msg, detail=()):
        self.fails.append(("[%s] %s %s" % (sid, loc, msg), list(detail)))


def run(mod_root, engine_root):
    r = Result()

    def read(kind, rel):
        base = mod_root if kind == "mod" else engine_root
        try:
            with open(os.path.join(base, *rel.split("/")), "rb") as f:
                data = f.read()
        except (IOError, OSError):
            return None
        r.inputs.add((kind, rel))
        return data

    # ------------------------------------------------------------ 0. roots and tables
    if not os.path.isfile(os.path.join(mod_root, "coop_mod", "main.scr")):
        r.fail("0a", "mod-root", "%s is not the coop mod tree (no coop_mod/main.scr) - a wrong root must never go green"
               % mod_root)
    if not os.path.isdir(os.path.join(engine_root, "code", "cgame")):
        r.fail("0b", "engine-root", "%s is not the engine tree (no code/cgame) - a wrong root must never go green"
               % engine_root)
    for g in MP_MANIFEST:
        if not re.match(r"[A-Za-z0-9_./*-]+\Z", g) or not g.lower().startswith(("coop_mod/", "ui/")):
            r.fail("0c", "MP_MANIFEST", "glob %r must use only [A-Za-z0-9_./*-] and sit under coop_mod/ or ui/" % g)
    clash = sorted(set(p.split("::")[0] for p in MP_COOP_ALLOW) & MP_COOP_DENY)
    if clash:
        r.fail("0d", "MP_COOP_DENY", "script(s) both allowlisted and denied for MP calls: " + ", ".join(clash))
    if r.fails:
        # a bad root or table makes every later verdict meaningless - stop before anything can pass
        return r
    r.ok("0", "roots exist and the manifest, allow and deny tables are well-formed")

    manifest_rx = [glob_rx(g) for g in MP_MANIFEST]
    allied_rx = [glob_rx(g) for g in ALLIED_GLOBS]
    axis_rx = [glob_rx(g) for g in AXIS_GLOBS]

    def is_mp(rel):
        return any(x.match(rel) and x.match(rel).end() == len(rel) for x in manifest_rx)

    def matches(rel, rxs):
        return any(x.match(rel) and x.match(rel).end() == len(rel) for x in rxs)

    mod_files = []
    for dirpath, dirs, files in os.walk(mod_root):
        reld = os.path.relpath(dirpath, mod_root).replace("\\", "/")
        if reld == ".":
            reld = ""
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_TOP and d.lower() != ".git"]
        else:
            dirs[:] = [d for d in dirs if d.lower() != ".git"]
        dirs.sort()
        for f in sorted(files):
            mod_files.append(reld + "/" + f if reld else f)
    manifest = [rel for rel in mod_files if is_mp(rel)]
    scan = [rel for rel in mod_files if os.path.splitext(rel)[1].lower() in SCAN_EXT]
    r.n_mod = len(scan)

    # ------------------------------------------------------------ 1 + 7. coop files never name MP code or tokens
    for rel in scan:
        if is_mp(rel):
            continue
        raw = read("mod", rel)
        # 1a and 7a need coop_mod or coop_mp; 1b needs a "coop..." string followed by +
        if raw is None or (b"coop_m" not in raw.lower() and not RX_B_COOP_CONCAT.search(raw)):
            continue
        texts = both_texts(raw.decode("latin-1"))
        lines1a = set()
        if rel.lower() != "global/ambient.scr":           # the one sanctioned hook - clause 3 owns it
            for ln, tok in hits(texts, RX_MP_PATH):
                lines1a.add(ln)
                r.fail("1a", where(rel, ln), "coop file names the MP script/cfg %s - coop must never reach MP code" % tok)
        lines1b = set()
        for t, pos, joined, _mode in literal_names(texts, "coop"):
            if joined.startswith(("coop_mod/mp", "coop_mod/cfg/mp")):
                ln = line_of(t, pos)
                if ln not in lines1a and ln not in lines1b:
                    lines1b.add(ln)
                    r.fail("1b", where(rel, ln), "coop file assembles the MP script/cfg path %s... from strings - coop "
                           "must never reach MP code" % joined)
        tik = rel.lower().endswith(".tik")
        texts7 = [RX_MPRUN_READ.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), t) for t in texts]
        for ln, tok in hits(texts7, RX_MP_TOKEN):
            if tok == "coop_mpmenu":
                continue
            if tik and RX_TIK_OK.match(tok) and RX_TIK_OK.match(tok).end() == len(tok):
                continue
            r.fail("7a", where(rel, ln), "coop file names the MP token %s - MP cvars, menus and cfg trees stay out of coop"
                   % tok)
    if not any(f[0].startswith(("[1a]", "[1b]")) for f in r.fails):
        r.ok("1", "no coop file names or assembles an MP script or cfg (global/ambient.scr is checked by clause 3)")
    if not any(f[0].startswith("[7a]") for f in r.fails):
        r.ok("7", "no coop file names a coop_mp* token")

    # ------------------------------------------------------------ 2. mp.scr refuses to run under coop
    mp = read("mod", "coop_mod/mp.scr")
    if mp is None:
        r.pend("2","coop_mod/mp.scr does not exist yet - the refusal guard cannot be checked")
    else:
        blank = LEX_ESC.sub(_strip_blank, mp.decode("latin-1"))
        if RX_MP_GUARD.search(blank):
            r.ok("2", "mp.scr's first statement refuses to run when coop is loaded, and ends")
        else:
            lm = re.search(r"^main\s*:", blank, re.I | re.M)
            r.fail("2a", where("coop_mod/mp.scr", line_of(blank, lm.start()) if lm else 1),
                   "main's FIRST statement must be `if( level.coop_mainScriptLoaded == 1 ){ ... end }`")

    # ------------------------------------------------------------ 3. the ambient.scr hook is the only one, and gated
    amb_rel = "global/ambient.scr"
    amb = read("mod", amb_rel)
    if amb is None:
        r.fail("3a", amb_rel, "global/ambient.scr is missing from the mod tree")
    else:
        atxt = amb.decode("latin-1")
        kept_esc, kept_noesc = both_texts(atxt)
        blank = LEX_ESC.sub(_strip_blank, atxt)
        m_esc = list(RX_MP_PATH.finditer(kept_esc))
        m_noesc = list(RX_MP_PATH.finditer(kept_noesc))
        count = max(len(m_esc), len(m_noesc))
        if count == 0 and mp is None:
            r.pend("3", "global/ambient.scr does not hook mp.scr yet")
        elif count != 1 or len(m_esc) != 1:
            last = (m_esc or m_noesc)
            ln = line_of(kept_esc if m_esc else kept_noesc, last[-1].start()) if last else 1
            r.fail("3b", where(amb_rel, ln), "ambient.scr must reference MP code exactly once (found %d)" % count)
        else:
            pos = m_esc[0].start()
            hook = None
            for hm in RX_AMB_HOOK.finditer(blank):
                if hm.start() <= pos < hm.end():
                    hook = hm
            ln = line_of(kept_esc, pos)
            if hook is None:
                r.fail("3b", where(amb_rel, ln), "the MP reference is not `if( <coop test> ){ exec coop_mod/mp.scr::main }`")
            elif not (RX_AMB_COND.match(hook.group(1)) and RX_AMB_COND.match(hook.group(1)).end() == len(hook.group(1))):
                r.fail("3c", where(amb_rel, ln), "the ambient.scr MP hook is not gated on exactly "
                       "`level.gametype != 0 && level.coop_mainScriptLoaded != 1` - every coop map would run MP init")
            else:
                r.ok("3", "the ambient.scr MP hook is the only one and is gated on coop_mainScriptLoaded != 1")

    # ------------------------------------------------------------ 4/5/9/10/12/13. rules over every MP file
    mp_texts = []
    for rel in manifest:
        raw = read("mod", rel)
        if raw is not None:
            mp_texts.append((rel, both_texts(raw.decode("latin-1"))))
    rx4 = [(cv, re.compile(RX_VERB + re.escape(cv) + r"\b", re.I)) for cv in SAVED_COOP_CVARS]
    rx5 = re.compile(RX_VERB + r"coop_lockLoadout\b", re.I)
    mark = len(r.fails)
    for rel, texts in mp_texts:
        direct = set()
        for cv, rx in rx4:
            for ln, _tok in hits(texts, rx):
                direct.add((ln, cv.lower()))
                r.fail("4a", where(rel, ln), "MP file writes the saved coop cvar %s - it would follow the player into coop"
                       % cv)
        for ln, _tok in hits(texts, RX_CVAR_RESTART):
            r.fail("4b", where(rel, ln), "MP file runs cvar_restart - that resets every saved coop cvar")
        for ln, _tok in hits(texts, rx5):
            direct.add((ln, "coop_lockloadout"))
            r.fail("5a", where(rel, ln), "MP file writes coop_lockLoadout - server.scr:28 latches it for every coop map")
        named = set()
        for t in texts:
            for m in RX_SAVED_NAME.finditer(t):
                if RX_GETCVAR_OPEN.search(t, max(0, m.start() - 40), m.start()):
                    continue                              # getcvar( "coop_x" ) is a read (mp.scr's tinnitus volume)
                named.add((line_of(t, m.start()), m.group(0).lower()))
        for ln, tok in sorted(named - direct):
            r.fail("4c", where(rel, ln), "MP file names the saved coop cvar %s outside a getcvar( \"...\" ) read - a name "
                   "parked in a variable is a write waiting to happen" % tok)
    if not mp_texts:
        r.pend("4", "no MP file exists yet - the saved-cvar rules have nothing to check")
        r.pend("5", "no MP file exists yet - the coop_lockLoadout rule has nothing to check")
    else:
        if not any(f[0].startswith(("[4a]", "[4b]", "[4c]")) for f in r.fails[mark:]):
            r.ok("4", "no MP file writes a saved coop cvar or runs cvar_restart (%d cvars, %d files)"
                 % (len(SAVED_COOP_CVARS), len(mp_texts)))
        if not any(f[0].startswith("[5a]") for f in r.fails[mark:]):
            r.ok("5", "no MP file writes coop_lockLoadout")

    mp_scr = [(rel, t) for rel, t in mp_texts if rel.lower().endswith(".scr")]
    mark = len(r.fails)
    for rel, texts in mp_scr:
        for ln, _tok in hits(texts, RX_ISHOST_SET):
            r.fail("9a", where(rel, ln), "MP assigns flags[\"coop_isHost\"] - that unlocks dev godmode, noclip and give_all")
    if not mp_scr:
        r.pend("9", "no MP script exists yet")
    elif len(r.fails) == mark:
        r.ok("9", "no MP script assigns flags[\"coop_isHost\"]")

    mark = len(r.fails)
    ncalls = 0
    for rel, texts in mp_scr:
        seen = set()
        for t in texts:
            for m in RX_COOP_CALL.finditer(t):
                path = re.sub(r"[/\\]+", "/", m.group(1)).lower()
                label = (m.group(2) or "").lower()
                ln = line_of(t, m.start())
                if (ln, path, label) in seen:
                    continue
                seen.add((ln, path, label))
                if is_mp("coop_mod/" + path + ".scr"):
                    continue
                ncalls += 1
                if path in MP_COOP_DENY:
                    r.fail("10a", where(rel, ln), "MP calls coop armory/progression code coop_mod/%s.scr" % path)
                elif not label:
                    r.fail("10b", where(rel, ln), "MP names coop_mod/%s.scr without a label - only allowlisted labels" % path)
                elif (path + "::" + label) not in MP_COOP_ALLOW:
                    r.fail("10c", where(rel, ln), "MP calls coop_mod/%s.scr::%s, which is not in MP_COOP_ALLOW"
                           % (path, label))
    if not mp_scr:
        r.pend("10", "no MP script exists yet")
    elif len(r.fails) == mark:
        r.ok("10", "MP scripts call only allowlisted coop helpers (%d calls)" % ncalls)

    mark = len(r.fails)
    for rel, texts in mp_texts:
        for ln, tok in hits(texts, RX_COOP_LO):
            r.fail("12a", where(rel, ln), "MP file names the coop armory cvar %s" % tok)
        for ln, _tok in hits(texts, RX_UI_LOADOUT):
            r.fail("12b", where(rel, ln), "MP file names the coop armory cfg tree ui/loadout/")
        built = set()
        for t, pos, joined, mode in literal_names(texts, ("coop", "ui")):
            if builds_coop_name(joined, mode):
                ln = line_of(t, pos)
                if ln not in built:
                    built.add(ln)
                    r.fail("12c", where(rel, ln), "MP file assembles the coop name %s at runtime (%s) - a static scan "
                           "cannot see what it becomes" % (joined, "held alone" if mode == "alone" else "concatenated"))
    if not mp_texts:
        r.pend("12", "no MP file exists yet")
    elif len(r.fails) == mark:
        r.ok("12", "no MP file names a coop_lo* cvar or ui/loadout/, or assembles a coop name from strings")

    mark = len(r.fails)
    n_allied = n_axis = 0
    for rel, texts in mp_texts:
        if matches(rel, allied_rx):
            n_allied += 1
            for ln, tok in hits(texts, RX_MPX_TOKEN):
                r.fail("13a", where(rel, ln), "Allied armory file names the Axis token %s" % tok)
        elif matches(rel, axis_rx):
            n_axis += 1
            for ln, tok in hits(texts, RX_MPA_TOKEN):
                r.fail("13b", where(rel, ln), "Axis armory file names the Allied token %s" % tok)
    if n_allied == 0 and n_axis == 0:
        r.pend("13", "no Allied or Axis armory file exists yet")
    elif len(r.fails) == mark:
        r.ok("13", "Allied (%d) and Axis (%d) armory files stay apart" % (n_allied, n_axis))

    # ------------------------------------------------------------ 6. shared menus are locked by checksum
    for rel in sorted(LOCKS):
        lock = LOCKS[rel]
        raw = read("mod", rel)
        if raw is None:
            r.fail("6a", rel, "locked file is MISSING", lock_detail(rel, lock))
            continue
        h = hashlib.sha256(raw).hexdigest()
        if h == lock["sha256_lf"] or h == lock["sha256_crlf"]:
            form = "lf" if h == lock["sha256_lf"] else "crlf"
            if form != lock["eol"]:
                r.warn("6w", rel, "line endings differ from the locked checkout (%s, locked %s) - content is identical"
                       % (form, lock["eol"]))
            r.ok("6", "%s matches its lock (%s)" % (rel, form))
        else:
            r.fail("6b", rel, "locked file CHANGED (sha256 %s) - this is a coop file, not an MP leak: a deliberate coop "
                   "edit needs --print-lock and a re-lock" % h[:12], lock_detail(rel, lock))

    # ------------------------------------------------------------ 8. challenge and xp systems stay coop-only
    def guard_before(body, anchor):
        idx = body.find(anchor)
        if idx < 0:
            return None, 0
        return bool(RX_MPRUN_GUARD.search(body[max(0, idx - 200):idx])), line_of(body, idx)

    crel = "coop_mod/challenges.scr"
    chal = read("mod", crel)
    if chal is None:
        r.fail("8d", crel, "coop_mod/challenges.scr is missing")
    else:
        body = both_texts(chal.decode("latin-1"))[0]
        st, ln = guard_before(body, "thread chal_autosave_loop")
        if st is None:
            r.fail("8d", crel, "anchor `thread chal_autosave_loop` not found - re-check the MP guard in chal_init")
        elif not st:
            r.fail("8a", where(crel, ln), "NO MP guard in chal_init before its background loops - PvP would write coop "
                   "progression")
        else:
            r.ok("8", "challenges.scr MP guard present in chal_init before its background loops")
        st, ln = guard_before(body, "waitthread chal_pin_load local.player")
        if st is None:
            r.fail("8d", crel, "anchor `waitthread chal_pin_load local.player` not found - re-check the MP guard in "
                   "chal_ensure")
        elif not st:
            r.fail("8b", where(crel, ln), "NO MP guard in chal_ensure before the pin/medal writers")
        else:
            r.ok("8", "challenges.scr MP guard present in chal_ensure before the pin/medal writers")
    xrel = "coop_mod/xp.scr"
    xpt = read("mod", xrel)
    if xpt is None:
        r.fail("8d", xrel, "coop_mod/xp.scr is missing")
    else:
        body = both_texts(xpt.decode("latin-1"))[0]
        st, ln = guard_before(body, "thread xp_autosave_loop")
        if st is None:
            r.fail("8d", xrel, "anchor `thread xp_autosave_loop` not found - re-check the MP guard in xp_init")
        elif not st:
            r.fail("8c", where(xrel, ln), "NO MP guard in xp_init before its loops - PvP would write coop XP")
        else:
            r.ok("8", "xp.scr MP guard present in xp_init before its loops")

    # ------------------------------------------------------------ 11. every MP-named file is in the manifest
    mark = len(r.fails)
    for rel in mod_files:
        segs = rel.split("/")
        if not any(re.match(r"(?:coop_)?mp", s, re.I) for s in (segs[1:] or segs)):
            continue
        if segs[0].lower() not in ("ui", "coop_mod") or len(segs) < 2:
            if os.path.splitext(rel)[1].lower() not in MP_NAME_EXT or rel.lower() in MP_NAME_ALLOW:
                continue
        if not is_mp(rel):
            r.fail("11a", rel, "MP-named file is not in MP_MANIFEST - it would be judged as coop and its MP rules skipped")
    if len(r.fails) == mark:
        r.ok("11", "every MP-named file (all of ui/ and coop_mod/, scripts elsewhere) is in the manifest (%d MP files)"
             % len(manifest))

    # ------------------------------------------------------------ 14. engine MP code lives only in declared hooks
    code_root = os.path.join(engine_root, "code")
    blocks = []          # (name, rel, begin_line)
    mark = len(r.fails)
    markers_seen = False
    stray = False
    for dirpath, dirs, files in os.walk(code_root):
        reld = os.path.relpath(dirpath, engine_root).replace("\\", "/")
        if reld.lower() == "code":
            dirs[:] = [d for d in dirs if d.lower() != "thirdparty" and d.lower() != ".git"]
        else:
            dirs[:] = [d for d in dirs if d.lower() != ".git"]
        dirs.sort()
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() not in ENGINE_EXT:
                continue
            rel = reld + "/" + f
            r.n_engine += 1
            raw = read("engine", rel)
            if raw is None:
                continue
            low = raw.lower()
            if b"coop_mp" not in low and b"hzm-mp" not in low and b"coop_mod" not in low:
                continue
            lines = raw.decode("latin-1").split("\n")
            inside = [False] * (len(lines) + 1)
            open_name, open_line = None, 0
            for i, line in enumerate(lines, 1):
                b = RX_HOOK_BEGIN.search(line)
                e = RX_HOOK_END.search(line)
                if b:
                    markers_seen = True
                    if open_name is not None:
                        r.fail("14b", where(rel, i), "HZM-MP-BEGIN(%s) inside the open block %s - hooks do not nest"
                               % (b.group(1), open_name))
                        open_name = None
                        break
                    open_name, open_line = b.group(1).lower(), i
                elif e:
                    markers_seen = True
                    name = e.group(1).lower()
                    if open_name is None:
                        r.fail("14a", where(rel, i), "HZM-MP-END(%s) with no open block" % name)
                    elif name != open_name:
                        r.fail("14a", where(rel, i), "HZM-MP-END(%s) closes HZM-MP-BEGIN(%s)" % (name, open_name))
                        open_name = None
                    else:
                        blocks.append((open_name, rel, open_line))
                        for k in range(open_line, i + 1):
                            inside[k] = True
                        open_name = None
            if open_name is not None:
                r.fail("14a", where(rel, open_line), "HZM-MP-BEGIN(%s) is never closed" % open_name)
            for i, line in enumerate(lines, 1):
                if inside[i]:
                    if RX_COOP_LO.search(line) or RX_UI_LOADOUT.search(line):
                        r.fail("14g", where(rel, i), "an engine MP hook names a coop armory cvar or ui/loadout/")
                    continue
                for m in RX_MP_TOKEN.finditer(line):
                    if m.group(0).lower() != "coop_mpmenu":
                        stray = True
                        r.fail("14f", where(rel, i), "engine names the MP token %s outside a declared HZM-MP hook"
                               % m.group(0).lower())
                for m in RX_MP_PATH.finditer(line):
                    stray = True
                    r.fail("14f", where(rel, i), "engine names the MP script/cfg %s outside a declared HZM-MP hook"
                           % m.group(0).lower())
    registry = dict((k.lower(), v) for k, v in ENGINE_MP_HOOKS.items())
    byname = {}
    for name, rel, ln in blocks:
        byname.setdefault(name, []).append((rel, ln))
    for name in sorted(byname):
        if len(byname[name]) > 1:
            rel, ln = byname[name][1]
            r.fail("14c", where(rel, ln), "engine MP hook name %s is used by %d blocks" % (name, len(byname[name])))
        for rel, ln in byname[name]:
            if name not in registry:
                r.fail("14d", where(rel, ln), "engine MP hook %s is not registered in ENGINE_MP_HOOKS" % name)
    for name in sorted(registry):
        if name not in byname:
            r.fail("14e", "ENGINE_MP_HOOKS[%s]" % name, "registered engine MP hook has no well-formed block")
    if not stray:
        r.ok("14", "no MP token or MP script path outside a hook in %d engine files" % r.n_engine)
    if not registry and not markers_seen:
        r.pend("14", "no MP engine hooks declared yet")
    elif not any(f[0].startswith(("[14a]", "[14b]", "[14c]", "[14d]", "[14e]", "[14g]")) for f in r.fails[mark:]):
        r.ok("14", "%d engine MP hook(s) well-formed, registered and free of coop armory names" % len(blocks))
    return r


def lock_detail(rel, lock):
    out = ["If this change is DELIBERATE: run `python docs/tools/check_mp_isolation.py --print-lock %s` and paste the "
           "entry into LOCKS with a dated reason and bug id." % rel,
           "To undo an uncommitted edit: `git -c core.autocrlf=true -C hzm-mohaa-coop-mod restore --source=HEAD "
           "--worktree -- %s`." % rel,
           "To return to the locked content: the same command with `--source=%s`." % lock["commit"],
           "Never recreate it with `git show ... >` from PowerShell: that writes UTF-16/BOM and LF."]
    if rel == "ui/coop_loadout.urc":
        out.append("Its layout generator exists in no commit - it cannot be regenerated.")
    return out


def print_lock(mod_root, rel):
    p = os.path.join(mod_root, *rel.split("/"))
    if not os.path.isfile(p):
        print("no such file: %s" % p)
        return 1
    raw = open(p, "rb").read()
    lf = raw.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    eol = "crlf" if b"\r\n" in raw else "lf"
    print("    \"%s\": {\"sha256_lf\": \"%s\", \"sha256_crlf\": \"%s\", \"lf_bytes\": %d, \"blob\": \"<git hash-object>\", "
          "\"eol\": \"%s\", \"commit\": \"<commit>\", \"locked\": \"<date> <reason, bug id>\"},"
          % (rel, hashlib.sha256(lf).hexdigest(), hashlib.sha256(crlf).hexdigest(), len(lf), eol))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="MP/coop isolation contract")
    ap.add_argument("--mod", default=DEFAULT_MOD)
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--list-clauses", action="store_true")
    ap.add_argument("--list-inputs", action="store_true")
    ap.add_argument("--print-lock", metavar="REL")
    a = ap.parse_args(argv)
    if a.list_clauses:
        for c in CLAUSES:
            print(c)
        return 0
    if a.print_lock:
        return print_lock(os.path.abspath(a.mod), a.print_lock.replace("\\", "/"))
    r = run(os.path.abspath(a.mod), os.path.abspath(a.engine))
    if a.list_inputs:
        for kind, rel in sorted(r.inputs):
            print("%s\t%s" % (kind, rel))
        return 1 if r.fails else 0
    print("MP/coop isolation contract")
    print("=" * 74)
    if a.verbose:
        for line in r.passed:
            print("  PASS    " + line)
    for line in r.pending:
        print("  PENDING " + line)
    for line in r.warns:
        print("  WARN    " + line)
    for line, detail in r.fails:
        print("  FAIL    " + line)
        for d in detail:
            print("            " + d)
    print("-" * 74)
    print("scanned: %d mod files, %d engine files" % (r.n_mod, r.n_engine))
    print("%d passed, %d pending, %d FAILED" % (len(r.passed), len(r.pending), len(r.fails)))
    if r.fails:
        print("\nThe MP loadout must not be able to change the coop experience. Fix the above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

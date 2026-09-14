#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_mp_isolation_selftest.py - prove check_mp_isolation.py can FAIL, rule by rule.

WHY THIS EXISTS
    TRAPS T14: a check that cannot fail is worse than none - it prints PASS and everyone stops looking.
    The isolation contract guards the user's standing rule ("I cannot stress this enough we need to make
    sure this does not in any way impact the coop mod or experience itself"), so every one of its
    sub-rules is proven here by planting the violation it exists to catch and asserting that exactly that
    sub-rule fires, at exactly the planted file and line.

HOW
    1. Run the checker on the real trees: it must pass, write nothing to stderr, and list its inputs.
    2. Copy exactly those inputs, byte for byte, into a temp directory. NEVER hardlinks: a write through a
       link would corrupt the real coop tree.
    3. Plant each mutation in the copy (or in a patched copy of the checker, for rules that depend on the
       checker's own tables), run the checker, assert exit 1, empty stderr, the exact FAIL sub-id set and
       the exact location, then restore the bytes.
    4. Near-misses must still pass. A final clean run proves every restore.
    5. Every fail("<id>") and warn("<id>") site in the checker's source must be exercised, and the real
       tree's input hashes must be unchanged at the end.

    ANCHORS are located in the checker's own comment-stripped view (its LEX_ESC lexer, imported from the
    checker under test), and a mutation acts on the FIRST occurrence there - the one the checker reads. So a
    comment that happens to quote an anchor changes nothing, and near-miss N14 proves it.

    PLANTED FILES all carry the reserved token "zzselftest" in their name, inside the glob their clause
    needs. A real MP file can therefore never collide with a plant and read as drift.

    --if-changed skips the ~2 minute run when the checker, this file and Python are unchanged since the last
    full pass (stamp), but still re-checks every mutation anchor against the real tree, so an edit that
    removes an anchor blocks the build that introduced it instead of rotting silently.

The last stdout line is exactly one of:
    selftest: ok (<n> mutations, <m> near-misses, <s>s)
    selftest: unchanged since <utc>
    selftest: FAILED - <reason>
Output goes to stdout only (build.ps1 runs this inside publish_release.ps1's Stop mode).
"""
import argparse
import datetime
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SELF = os.path.abspath(__file__)
DEF_CHECKER = os.path.join(ROOT, "docs", "tools", "check_mp_isolation.py")
DEF_STAMP = os.path.join(ROOT, "build_out", "mp_isolation_selftest.stamp")
DEF_MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
DEF_ENGINE = os.path.join(ROOT, "openmohaa-hzm")

MP = "coop_mod/mp.scr"
AMB = "global/ambient.scr"
FILTER = "code/cgame/cg_servercmds_filter.cpp"
# ENGINE_MP_HOOKS is no longer empty once real hooks (E4/E5) are registered, so the anchor is the dict
# OPENING and HOOKS_TEST inserts a "test" entry AHEAD of the real hooks, keeping them registered (R7:
# the first real entry retired the old `= {}` anchor - this is that rework). The opening appears once.
HOOKS_ANCHOR = "ENGINE_MP_HOOKS = {"
HOOKS_TEST = "ENGINE_MP_HOOKS = {\"test\": \"selftest\", "
MP_KIT = "static const char *k = \"coop_mpaW1\";"
RESERVED = "zzselftest"
RX_END = re.compile(r"\bend\b")

# N14: quote every clause-8 anchor in a comment ABOVE the real one, then prove the precheck, the checker and the
# mutations that depend on those anchors all still behave.
COMMENT_ANCHORS = [
    ("coop_mod/challenges.scr", "// selftest: thread chal_autosave_loop / waitthread chal_pin_load local.player\n"),
    ("coop_mod/xp.scr", "/* selftest: thread xp_autosave_loop */\n"),
]
COMMENT_NESTED = ("M18a", "M18b", "M19", "M19b")

CK = None   # the checker under test, imported so anchors are found in exactly the view it reads


class SelfTestError(Exception):
    pass


# ---------------------------------------------------------------- mutation table
# op: append (a line at EOF), appendraw (bytes at EOF, no newline), new (a file named with RESERVED), replace (first
#     anchor outside comments), delete, unguard (drop the coop_mpRun guard(s) in the 200 view characters before an
#     anchor), dropend (drop the first `end` after an anchor), eol (flip a file's line endings), none (checker/args
#     only), commentanchors (N14)
# loc: ("append", k) k-th planted line; ("new", k); ("find", needle) first line holding needle outside comments after
#      mutation; ("file",) rel only; ("where", text) literal location token
def mut(mid, op, rel=None, text=None, expect=(), loc=None, root="mod", anchor=None, frag=None, patch=None,
        args=None, warn=()):
    return dict(id=mid, op=op, rel=rel, text=text, expect=set(expect), loc=loc, root=root, anchor=anchor,
                frag=frag, patch=patch, args=args, warn=set(warn))


def A(mid, rel, text, expect, root="mod", k=0, **kw):
    return mut(mid, "append", rel, text, expect, ("append", k), root, **kw)


def N(mid, rel, text, expect, root="mod", loc=None, **kw):
    return mut(mid, "new", rel, text, expect, loc or ("new", 0), root, **kw)


MUTATIONS = [
    # [0] roots and tables
    mut("X1", "none", expect={"0a"}, loc=("where", "mod-root"), args="mod-nope"),
    mut("X2", "none", expect={"0b"}, loc=("where", "engine-root"), args="engine-nope"),
    mut("X3", "delete", "coop_mod/main.scr", expect={"0a"}, loc=("where", "mod-root")),
    mut("P1", "none", expect={"0c"}, loc=("where", "MP_MANIFEST"),
        patch=("MP_MANIFEST = [", "MP_MANIFEST = [\"ui/coop_mp[x].urc\", ")),
    mut("P2", "none", expect={"0d"}, loc=("where", "MP_COOP_DENY"),
        patch=("MP_COOP_DENY = {", "MP_COOP_DENY = {\"main\", ")),
    # [1] coop never names or assembles MP code
    A("M1", "coop_mod/main.scr", "waitthread coop_mod/mp.scr::main", {"1a"}),
    A("M2", "@coopmap", "exec coop_mod/mp_armory.scr", {"1a"}),
    A("M2b", "coop_mod/cfg/detect.cfg", "exec coop_mod/cfg/mp_start.cfg", {"1a"}),
    A("M2c", "coop_mod/main.scr", "exec COOP_MOD\\mp.scr::main", {"1a"}),
    A("M2d", "coop_mod/main.scr", "exec ( \"coop_mod/cfg/\" + \"mp_start.cfg\" )", {"1b"}),
    A("M2e", "coop_mod/player.scr", "local.s = \"coop_mod/mp_\" + local.side + \".scr\"", {"1b"}),
    # a file with no `coop_m` in it at all: proves the byte prefilter lets a split name through to 1b
    A("M2f", "global/autosave.scr", "exec ( \"coop\" + \"_mod\\\\mp.scr\" )", {"1b"}),
    # [2] mp.scr refusal guard
    mut("M4", "replace", MP, "main:{\n\tlevel.x = 1", {"2a"}, ("find", "main:{"), anchor="main:{"),
    mut("M4b", "dropend", MP, None, {"2a"}, ("find", "main:{"), anchor="if( level.coop_mainScriptLoaded == 1 ){"),
    # [3] ambient hook
    A("M3", AMB, "exec coop_mod/mp.scr::main", {"3b"}),
    mut("M3c", "delete", AMB, expect={"3a"}, loc=("file",)),
    mut("M5", "replace", AMB, "", {"3c"}, ("find", "exec coop_mod/mp.scr::main"),
        anchor=" && level.coop_mainScriptLoaded != 1"),
    mut("M5b", "replace", AMB, "0 || level.coop_main", {"3c"}, ("find", "exec coop_mod/mp.scr::main"),
        anchor="0 && level.coop_main"),
    # [4] saved coop cvars
    A("M6", MP, "setcvar \"coop_health\" \"100\"", {"4a"}),
    A("M6c", MP, "local.c = \"coop_prone\"\nsetcvar local.c \"0\"", {"4c"}),
    N("M7", "ui/coop_mpa_zzselftest/reset.cfg", "seta coop_prone 0", {"4a"}),
    N("M7b", "ui/coop_mpa_zzselftest/r.cfg", "sets coop_health 100", {"4a"}),
    A("M7c", MP, "stuffsrv \"toggle coop_prone\"", {"4a"}),
    N("M7d", "ui/coop_mpx_zzselftest/w.cfg", "cvar_restart", {"4b"}),
    N("M7e", "ui/coop_mpa_zzselftest.urc", "linkcvar \"COOP_LIMP\"", {"4c"}),
    # [5] coop_lockLoadout
    N("M8", "coop_mod/cfg/mp_zzselftest_start.cfg", "set coop_lockLoadout 0", {"5a", "12a"}),
    # [6] lock
    mut("M9", "appendraw", "ui/coop_loadout.urc", " ", {"6b"}, ("file",)),
    mut("M11", "delete", "ui/coop_loadout.urc", expect={"6a"}, loc=("file",)),
    # [7] coop never names coop_mp*
    A("M12", "coop_mod/player.scr", "level.coop_mpaA1 = 1", {"7a"}),
    A("M13", "coop_mod/xp.scr", "level.coop_mpRun = 1", {"7a"}),
    A("M14", "ui/loadout/t01.cfg", "exec ui/coop_mpx/w1.cfg", {"7a"}),
    A("M15", "ui/coop_jeepEnter.urc", "stuffcommand \"pushmenu coop_mpa_armory\"", {"7a"}),
    N("M16", "ui/zzselftest_axis_armory.urc", "stuffcommand \"seta coop_mpxW1 1\"", {"7a"}),
    A("M17", "coop_mod/loadoutpick.scr", "level.coop_mpFreeKit = 1", {"7a"}),
    A("M17b", "coop_mod/player.scr", "level.Coop_MpaA1 = 1", {"7a"}),
    A("M17c", "autoexec.cfg", "set coop_mpmenuX 1", {"7a"}),
    A("M17d", "coop_mod/player.scr", "level.coop_mp44strap_x = 1", {"7a"}),
    N("M17e", "ui/zzselftest_x.urc", "coop_mp18", {"7a"}),
    A("M17f", "coop_mod/player.scr",
      "local.p stufftext \"echo \\\"http://x\\\"\" ; local.p stufftext \"seta coop_mpaW1 1\"", {"7a"}),
    # [8] challenge / xp guards
    mut("M18a", "unguard", "coop_mod/challenges.scr", None, {"8a"}, ("find", "thread chal_autosave_loop"),
        anchor="thread chal_autosave_loop", frag="chal_init"),
    mut("M18b", "unguard", "coop_mod/challenges.scr", None, {"8b"},
        ("find", "waitthread chal_pin_load local.player"), anchor="waitthread chal_pin_load local.player",
        frag="chal_ensure"),
    mut("M19", "unguard", "coop_mod/xp.scr", None, {"8c"}, ("find", "thread xp_autosave_loop"),
        anchor="thread xp_autosave_loop", frag="xp_init"),
    mut("M19b", "replace", "coop_mod/xp.scr", "thread xpautosave_loop", {"8d"}, ("file",),
        anchor="thread xp_autosave_loop"),
    # [9] coop_isHost
    A("M20", MP, "local.p.flags[\"coop_isHost\"] = 1", {"9a"}),
    A("M20b", MP, "local.p.flags[ \"coop_isHost\" ] = 1", {"9a"}),
    # [10] coop helper calls
    N("M21", "coop_mod/mp_zzselftest_armory.scr", "waitthread coop_mod/loadoutpick.scr::loadout_set local.p", {"10a"}),
    A("M22", MP, "waitthread coop_mod/main.scr::changeGameType 0 0", {"10c"}),
    A("M23", MP, "exec coop_mod/xp.scr", {"10a"}),
    A("M23b", MP, "exec coop_mod/tinnitus.scr", {"10b"}),
    A("M23c", MP, "thread coop_mod/cache/common.scr::x", {"10c"}),
    A("M23d", MP, "waitthread COOP_MOD\\loadoutpick.scr::loadout_set", {"10a"}),
    # [10] MP modes slice 1 (Gun Game): a mode file is judged by the MP rules like any coop_mod/mp*.scr.
    # The standing rule is that a mode must NEVER changeGameType (it ends in setcvar g_gametype and would
    # force gt2, killing FFA). Prove that a Gun-Game-shaped mode file calling it is caught by clause 10c.
    N("MGG", "coop_mod/mp_zzselftest_gungame.scr", "waitthread coop_mod/main.scr::changeGameType 2 0", {"10c"}),
    # [11] manifest
    N("M24", "ui/mpzzselftest/a.cfg", "echo x", {"11a"}, loc=("file",)),
    N("M24b", "global/mp_zzselftest.scr", "end", {"11a"}, loc=("file",)),
    # [12] MP never names or assembles coop armory state
    N("M25", "ui/coop_mpa_zzselftest/a1.cfg", "seta coop_loW1 5", {"12a"}),
    N("M25b", "ui/coop_mpa_zzselftest/c.cfg", "seta COOP_LOW1 5", {"12a"}),
    N("M26", "ui/coop_mpx_zzselftest/a2.cfg", "exec ui/loadout/t01.cfg", {"12b"}),
    N("M26b", "ui/coop_mpx_zzselftest/a3.cfg", "exec ui\\loadout\\t01.cfg", {"12b"}),
    A("M27", MP, "local.cv = \"coop_\" + \"loW1\"", {"12c"}),
    A("M27b", MP, "local.p stufftext ( \"seta coop_\" + local.n + \" 0\" )", {"12c"}),
    A("M27c", MP, "local.cv = \"coop_l\" + local.x", {"12c"}),
    A("M27d", MP, "local.cv = \"COOP_LO\" + local.x", {"12a", "12c"}),
    A("M27e", MP, "exec ( \"ui/\" + local.f )", {"12c"}),
    A("M27f", MP, "exec ( \"ui\\\\loadout\\\\\" + local.f )", {"12b", "12c"}),
    A("M27g", MP, "waitthread ( \"coop_mod/\" + local.s + \".scr::x\" )", {"12c"}),
    A("M27h", MP, "local.cv = \"coop_h\" + \"ealth\"", {"12c"}),
    A("M27i", MP, "local.stub = \"coop_\"", {"12c"}),
    A("M28", MP, "local.p stufftext \"echo http://x\" ; local.p stufftext \"seta coop_loW1 1\"", {"12a"}),
    A("M28b", MP, "local.p stufftext \"echo \\\"http://x\\\"\" ; local.p stufftext \"seta coop_loW1 1\"", {"12a"}),
    # [13] Allied / Axis
    N("M29", "ui/coop_mpa_zzselftest/x.cfg", "seta coop_mpx_W1 1", {"13a"}),
    N("M29b", "coop_mod/mpx_zzselftest.scr", "level.coop_mpa_A1 = 1", {"13b"}),
    # [14] engine hooks
    A("M30", FILTER, MP_KIT, {"14f"}, root="engine"),
    N("M30b", "code/mpnew_zzselftest/x.cpp", "static const char *k = \"coop_mpxW1\";", {"14f"}, root="engine"),
    A("M30c", FILTER, "static const char *s = \"exec coop_mod/cfg/mp_start.cfg\";", {"14f"}, root="engine"),
    A("M31", FILTER, "// HZM-MP-BEGIN(test)", {"14a"}, root="engine"),
    A("M32", FILTER, "// HZM-MP-BEGIN(test)\n// HZM-MP-END(test)", {"14d"}, root="engine"),
    A("M33", FILTER, "// HZM-MP-BEGIN(test)\n// HZM-MP-BEGIN(test2)\n// HZM-MP-END(test2)\n// HZM-MP-END(test)",
      {"14b"}, root="engine", k=1),
    mut("P3", "none", expect={"14e"}, loc=("where", "ENGINE_MP_HOOKS[test]"), patch=(HOOKS_ANCHOR, HOOKS_TEST)),
    A("P3+M34", FILTER, "// HZM-MP-BEGIN(test)\n// HZM-MP-END(test)\n// HZM-MP-BEGIN(test)\n// HZM-MP-END(test)",
      {"14c"}, root="engine", k=2, patch=(HOOKS_ANCHOR, HOOKS_TEST)),
    A("P3+M35", FILTER, "// HZM-MP-BEGIN(test)\nseta coop_loW1 1\n// HZM-MP-END(test)", {"14g"}, root="engine", k=1,
      patch=(HOOKS_ANCHOR, HOOKS_TEST)),
    # [15] the coop compass-bar session flag and prefs; M36c proves BUILD_BAN carries the new names into 12c
    A("M36", MP, "local.p stufftext \"set coop_isCoopSession 1\"", {"15a"}),
    N("M36b", "ui/coop_mpa_zzselftest/cb.cfg", "seta COOP_COMPASSBARSCALE 0.8", {"15a"}),
    A("M36c", MP, "local.cv = \"coop_compass\" + \"Bar\"", {"12c"}),
    # [16] MP urc menu names
    N("M37", "ui/coop_mp_zzselftest16a.urc", "menu \"randomthing\" 640 480 NONE 1", {"16a"}),
    N("M37b", "ui/coop_mp_zzselftest16b.urc", "menu \"SelectPrimaryWeapon_german\" 640 480 NONE 1", {"16b"}),
    # [17] MP never names the coop character-gear cvars
    A("M38", MP, "local.p stufftext \"seta dm_playermodel x\"", {"17a"}),
    A("M38b", MP, "local.p stufftext \"seta coop_gloveIdx 3\"", {"17a"}),
    # [18] no vstr in the MP UI trees (coop_mpx_zz is not in cmd_srvguard.h)
    N("M39", "ui/coop_mpx_zzselftest/v.cfg", "vstr coop_mpx_zz", {"18a"}),
    N("M39b", "ui/coop_mpa_zzselftest/v.cfg", "vstr \"coop_mpa_zz\"", {"18a"}),
]

NEAR_MISSES = [
    A("N1", MP, "if( local.p.flags[ \"coop_isHost\" ] == 1 || local.p.flags[\"coop_isHost\"] == 1 ){ }", ()),
    A("N2", "coop_mod/player.scr", "// level.coop_mpaA1 = 1", ()),
    A("N3", "coop_mod/player.scr", "if( level.coop_mpRun == 1 ){ end }", ()),
    N("N4", "ui/coop_mpa_zzselftest/ok.cfg", "seta coop_mpa_W1 5", ()),
    N("N5", "models/weapons/zzselftest.tik", "coop_mp44strap_x", ()),
    mut("N6", "eol", "ui/coop_loadout.urc", warn={"6w"}),
    mut("N8", "replace", AMB, "if(level.gametype!=0&&level.coop_mainScriptLoaded!=1)\n\t{",
        anchor="if( level.gametype != 0 && level.coop_mainScriptLoaded != 1 ){"),
    A("N9", MP, "local.v = getcvar( \"coop_health\" )", ()),
    A("N10", FILTER, "// HZM-MP-BEGIN(test)\n" + MP_KIT + "\n// HZM-MP-END(test)", (), root="engine",
      patch=(HOOKS_ANCHOR, HOOKS_TEST)),
    # joins that steer into MP space stay legal for MP code
    A("N11", MP, "local.a = \"coop_mp\" + local.x\nlocal.b = \"coop_\" + \"mpammo\"\n"
      "local.c = \"coop_mod/mp_\" + local.side + \".scr\"\nlocal.d = \"ui/coop_mpa_\" + local.x\n"
      "local.e = getcvar(\"coop_prone\")", ()),
    # coop's own dynamic save paths are not MP paths
    A("N12", "coop_mod/main.scr", "local.f = \"coop_mod/save/xp_\" + local.id\nlocal.g = \"coop_mod/\" + local.sub", ()),
    # a shared coop_mp name (no a_/x_ separator) belongs to neither side
    N("N13", "coop_mod/mpx_zzselftest.scr", "level.coop_mpammo = 1\nlevel.coop_mpx_W1 = 1", ()),
    mut("N14", "commentanchors"),
    # a stock-named weapon skin outside ui/ and coop_mod/ is a coop asset, not an unlisted MP file
    N("N15", "models/weapons/mp40_zzselftest.tik", "// weapon skin", ()),
    # naming the compass-bar cvars in a comment is not a write
    A("N16", MP, "// only coop script sets coop_isCoopSession and the coop_compassBar prefs", ()),
    # a coop_mp* menu name in an MP urc is legal (16a exempts coop_mp*), as is MP_OWNED_MENUS "mpoptions"
    N("N17", "ui/coop_mp_zzselftest_ok.urc", "menu \"coop_mp_zzselftest_ok\" 640 480 NONE 1", ()),
    N("N18", "ui/coop_mp_zzselftest_mpo.urc", "menu \"mpoptions\" 640 480 NONE 1", ()),
    # a vstr named only in a comment is documentation, not a wire (clause 18 reads the stripped view)
    N("N19", "ui/coop_mpa_zzselftest/vc.cfg", "// vstr coop_mpa_zz is only a comment here", ()),
    # naming the gear cvars in a comment is not a write (clause 17 reads the stripped view)
    A("N20", MP, "// MP never writes dm_playermodel or coop_gloveIdx", ()),
]


# ---------------------------------------------------------------- helpers
def out(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def eol_of(data):
    return b"\r\n" if b"\r\n" in data else b"\n"


def load_checker(path):
    """Import the checker under test. Warnings are errors here, so a non-raw regex in it fails loudly instead of
    writing a SyntaxWarning to stderr inside publish_release.ps1's Stop mode."""
    global CK
    sys.dont_write_bytecode = True
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            spec = importlib.util.spec_from_file_location("mpiso_checker_under_test", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
    except Exception as e:
        raise SelfTestError("cannot import the checker %s: %s" % (path, e))
    for attr in ("LEX_ESC", "both_texts", "_strip_blank", "RX_MPRUN_GUARD"):
        if not hasattr(mod, attr):
            raise SelfTestError("the checker has no %s - update the self-test" % attr)
    CK = mod


def view(data):
    """The checker's escape-aware comment-stripped view of raw bytes (both_texts()[0]), the same view with strings
    blanked (what clauses 2 and 3 parse), and pos[i] = the raw offset of view offset i."""
    txt = data.decode("latin-1")
    kept, blank, pos = [], [], []
    last = 0
    for m in CK.LEX_ESC.finditer(txt):
        if m.start() > last:
            kept.append(txt[last:m.start()])
            blank.append(txt[last:m.start()])
            pos.extend(range(last, m.start()))
        s = m.group(0)
        if s[0] == "\"":
            kept.append(s)
            blank.append(CK._strip_blank(m))
            pos.extend(range(m.start(), m.end()))
        else:
            nl = [m.start() + k for k, c in enumerate(s) if c == "\n"]
            kept.append("\n" * len(nl))
            blank.append("\n" * len(nl))
            pos.extend(nl)
        last = m.end()
    kept.append(txt[last:])
    blank.append(txt[last:])
    pos.extend(range(last, len(txt)))
    k, b = "".join(kept), "".join(blank)
    if k != CK.both_texts(txt)[0] or len(b) != len(k) or len(pos) != len(k):
        raise SelfTestError("the self-test's view of a file disagrees with the checker's lexer - update the self-test")
    return k, b, pos


def cut(data, pos, start, end):
    """Remove view span [start, end) from the raw bytes."""
    return data[:pos[start]] + data[pos[end - 1] + 1:]


def run_checker(checker, mod, engine, extra=()):
    p = subprocess.run([sys.executable, checker, "--mod", mod, "--engine", engine] + list(extra),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode("latin-1").replace("\r\n", "\n"), p.stderr


def parse(text):
    res = {"pass": [], "pending": [], "warn": [], "fail": [], "scanned": None, "summary": None}
    for line in text.split("\n"):
        m = re.match(r"  (PASS|PENDING|WARN|FAIL) +\[(\w+)\] (.*)$", line)
        if m:
            kind = m.group(1).lower()
            if kind == "fail" or kind == "warn":
                loc, _, msg = m.group(3).partition(" ")
                res[kind].append((m.group(2), loc, msg))
            else:
                res[kind].append(line)
        elif line.startswith("scanned: "):
            res["scanned"] = line
        elif re.match(r"\d+ passed, \d+ pending, \d+ FAILED$", line):
            res["summary"] = line
    return res


def coop_map_candidates(mod):
    found = []
    mapdir = os.path.join(mod, "maps")
    for dirpath, dirs, files in os.walk(mapdir):
        dirs.sort()
        for f in sorted(files):
            if f.lower().endswith(".scr"):
                p = os.path.join(dirpath, f)
                with open(p, "rb") as fh:
                    if b"coop_mod/main.scr::main" in fh.read():
                        found.append(os.path.relpath(p, mod).replace("\\", "/"))
    return sorted(found)


def resolve_rel(m, mod):
    if m["rel"] == "@coopmap":
        c = coop_map_candidates(mod)
        if not c:
            raise SelfTestError("SELFTEST ANCHOR DRIFT in maps/: no coop-integrated map script found - update the "
                                "mutation table")
        return c[0]
    return m["rel"]


def anchor_precheck(mod, engine, checker, table):
    """Cheap: every anchor the table depends on is still there, in the checker's own comment-stripped view, in the
    given trees. One occurrence is enough - mutations act on the first, which is the one the checker reads - so a
    comment that quotes an anchor can never block a build."""
    csrc = open(checker, "rb").read().decode("latin-1")
    for m in table:
        if m["patch"]:
            n = csrc.count(m["patch"][0])
            if n != 1:
                raise SelfTestError("SELFTEST ANCHOR DRIFT in %s: %s found %d times - update the mutation table"
                                    % (os.path.basename(checker), m["patch"][0], n))
        if m["op"] in ("none", "commentanchors"):
            continue
        base = mod if m["root"] == "mod" else engine
        rel = resolve_rel(m, mod)
        path = os.path.join(base, *rel.split("/"))
        if m["op"] == "new":
            if RESERVED not in rel.lower():
                raise SelfTestError("%s plants %s, which does not carry the reserved name %s - a real file could "
                                    "collide with it" % (m["id"], rel, RESERVED))
            if os.path.exists(path):
                raise SelfTestError("SELFTEST ANCHOR DRIFT in %s: a file with the self-test's reserved name exists - "
                                    "delete it (names containing %s belong to the self-test)" % (rel, RESERVED))
            continue
        if not os.path.isfile(path):
            raise SelfTestError("SELFTEST ANCHOR DRIFT in %s: target file missing - update the mutation table" % rel)
        if m["anchor"]:
            kept, blank, _pos = view(open(path, "rb").read())
            idx = kept.find(m["anchor"])
            if idx < 0:
                raise SelfTestError("SELFTEST ANCHOR DRIFT in %s: %s not found outside comments - update the mutation "
                                    "table" % (rel, m["anchor"]))
            if m["op"] == "unguard" and CK.RX_MPRUN_GUARD.search(kept, max(0, idx - 200), idx) is None:
                raise SelfTestError("SELFTEST ANCHOR DRIFT in %s: no coop_mpRun guard before %s - update the mutation "
                                    "table" % (rel, m["anchor"]))
            if m["op"] == "dropend" and RX_END.search(blank, idx) is None:
                raise SelfTestError("SELFTEST ANCHOR DRIFT in %s: no `end` after %s - update the mutation table"
                                    % (rel, m["anchor"]))


# ---------------------------------------------------------------- one mutation
def apply(m, tmp_mod, tmp_engine):
    """Returns (undo list, rel, expected location or None)."""
    undo = []
    if m["op"] == "none":
        return undo, None, None
    base = tmp_mod if m["root"] == "mod" else tmp_engine
    rel = resolve_rel(m, tmp_mod)
    path = os.path.join(base, *rel.split("/"))
    orig = open(path, "rb").read() if os.path.isfile(path) else None
    line = None
    if m["op"] == "new":
        if orig is not None:
            raise SelfTestError("%s: %s already exists in the copy" % (m["id"], rel))
        created = []
        d = os.path.dirname(path)
        while not os.path.isdir(d):
            created.append(d)
            d = os.path.dirname(d)
        for d in reversed(created):
            os.mkdir(d)
        data = (m["text"] + "\n").encode()
        with open(path, "wb") as f:
            f.write(data)
        undo.append(("rm", path))
        for d in created:
            undo.append(("rmdir", d))
        line = 1 + m["loc"][1] if m["loc"] and m["loc"][0] == "new" else None
        return undo, rel, line
    if orig is None:
        raise SelfTestError("%s: target %s is missing in the copy" % (m["id"], rel))
    undo.append(("restore", path, orig))
    eol = eol_of(orig)
    if m["op"] == "append":
        pre = orig if orig.endswith(b"\n") or not orig else orig + eol
        planted = m["text"].replace("\n", "\r\n" if eol == b"\r\n" else "\n").encode() + eol
        data = pre + planted
        line = pre.count(b"\n") + 1 + m["loc"][1]
    elif m["op"] == "appendraw":
        data = orig + m["text"].encode()
    elif m["op"] == "delete":
        os.remove(path)
        return undo, rel, None
    elif m["op"] == "replace":
        kept, _blank, pos = view(orig)
        i = kept.find(m["anchor"])
        if i < 0:
            raise SelfTestError("%s: anchor %r not found outside comments in %s" % (m["id"], m["anchor"], rel))
        repl = m["text"].replace("\n", "\r\n" if eol == b"\r\n" else "\n").encode()
        data = orig[:pos[i]] + repl + orig[pos[i + len(m["anchor"]) - 1] + 1:]
    elif m["op"] == "unguard":
        data = orig
        removed = 0
        for _round in range(20):
            kept, _blank, pos = view(data)
            i = kept.find(m["anchor"])
            if i < 0:
                raise SelfTestError("%s: anchor %r not found outside comments in %s" % (m["id"], m["anchor"], rel))
            ms = list(CK.RX_MPRUN_GUARD.finditer(kept, max(0, i - 200), i))
            if not ms:
                break
            data = cut(data, pos, ms[-1].start(), ms[-1].end())
            removed += 1
        if not removed:
            raise SelfTestError("%s: no coop_mpRun guard in the 200 characters before %r" % (m["id"], m["anchor"]))
    elif m["op"] == "dropend":
        kept, blank, pos = view(orig)
        i = kept.find(m["anchor"])
        em = RX_END.search(blank, i) if i >= 0 else None
        if em is None:
            raise SelfTestError("%s: no anchor %r followed by `end` outside comments in %s" % (m["id"], m["anchor"], rel))
        data = cut(orig, pos, em.start(), em.end())
    elif m["op"] == "eol":
        lf = orig.replace(b"\r\n", b"\n")
        data = lf if eol == b"\r\n" else lf.replace(b"\n", b"\r\n")
    else:
        raise SelfTestError("unknown op %s" % m["op"])
    with open(path, "wb") as f:
        f.write(data)
    if m["loc"] and m["loc"][0] == "find":
        kept = view(data)[0]
        p = kept.find(m["loc"][1])
        if p < 0:
            raise SelfTestError("%s: location needle %r missing after mutation" % (m["id"], m["loc"][1]))
        line = kept.count("\n", 0, p) + 1
    return undo, rel, line


def undo_all(undo):
    for item in undo:
        if item[0] == "restore":
            with open(item[1], "wb") as f:
                f.write(item[2])
        elif item[0] == "rm":
            if os.path.exists(item[1]):
                os.remove(item[1])
    for item in undo:
        if item[0] == "rmdir" and os.path.isdir(item[1]):
            os.rmdir(item[1])


def patched_checker(checker, patch, tmp):
    src = open(checker, "rb").read()
    a = patch[0].encode()
    if src.count(a) != 1:
        raise SelfTestError("patch anchor %r found %d times in the checker" % (patch[0], src.count(a)))
    d = os.path.join(tmp, "checker_patched")
    if not os.path.isdir(d):
        os.mkdir(d)
    p = os.path.join(d, "check_mp_isolation.py")
    with open(p, "wb") as f:
        f.write(src.replace(a, patch[1].encode()))
    return p


def expected_where(m, rel, line):
    loc = m["loc"]
    if loc is None:
        return None
    if loc[0] == "where":
        return loc[1]
    if loc[0] == "file":
        return rel
    return "%s:%d" % (rel, line)


def run_comment_anchors(m, checker, tmp, tmp_mod, tmp_engine):
    """N14: a comment quoting every clause-8 anchor, above the real ones, must not block the precheck, must not
    fail the checker, and must not stop the mutations that depend on those anchors from firing."""
    undo = []
    problems = []
    try:
        for rel, text in COMMENT_ANCHORS:
            path = os.path.join(tmp_mod, *rel.split("/"))
            if not os.path.isfile(path):
                raise SelfTestError("%s: target %s is missing in the copy" % (m["id"], rel))
            orig = open(path, "rb").read()
            undo.append(("restore", path, orig))
            with open(path, "wb") as f:
                f.write(text.replace("\n", eol_of(orig).decode()).encode() + orig)
        try:
            anchor_precheck(tmp_mod, tmp_engine, checker, MUTATIONS + NEAR_MISSES)
        except SelfTestError as e:
            problems.append("anchor precheck rejected a comment-only coop edit: %s" % e)
        rc, text, err = run_checker(checker, tmp_mod, tmp_engine, ["-v"])
        res = parse(text)
        if rc != 0 or err or res["fail"] or res["summary"] is None:
            problems.append("checker did not pass with anchors quoted in comments: exit %d, FAIL %s"
                            % (rc, [f[0] + " " + f[1] for f in res["fail"]]))
        byid = dict((x["id"], x) for x in MUTATIONS)
        for mid in COMMENT_NESTED:
            sub, _got = run_one(byid[mid], checker, tmp, tmp_mod, tmp_engine, False)
            problems.extend("%s under the comments: %s" % (mid, p) for p in sub)
    finally:
        undo_all(undo)
    return problems, "precheck ok, checker clean, %s still fire" % "/".join(COMMENT_NESTED)


def run_one(m, checker, tmp, tmp_mod, tmp_engine, near):
    if m["op"] == "commentanchors":
        return run_comment_anchors(m, checker, tmp, tmp_mod, tmp_engine)
    ck = patched_checker(checker, m["patch"], tmp) if m["patch"] else checker
    mod, engine = tmp_mod, tmp_engine
    if m["args"] == "mod-nope":
        mod = os.path.join(tmp, "nope")
    elif m["args"] == "engine-nope":
        engine = os.path.join(tmp, "nope")
    undo = []
    try:
        undo, rel, line = apply(m, tmp_mod, tmp_engine)
        rc, text, err = run_checker(ck, mod, engine, ["-v"])
    finally:
        undo_all(undo)
        if m["patch"]:
            os.remove(ck)
    res = parse(text)
    problems = []
    if err:
        problems.append("stderr not empty: %r" % err[:200])
    if res["summary"] is None:
        problems.append("no summary line")
    warns = set(w[0] for w in res["warn"])
    if warns != m["warn"]:
        problems.append("WARN ids %s, expected %s" % (sorted(warns), sorted(m["warn"])))
    if near:
        if rc != 0 or res["fail"]:
            problems.append("near-miss failed: exit %d, FAIL %s" % (rc, [f[0] + " " + f[1] for f in res["fail"]]))
        return problems, "exit %d" % rc
    got = set(f[0] for f in res["fail"])
    if rc != 1:
        problems.append("exit %d, expected 1" % rc)
    if got != m["expect"]:
        problems.append("FAIL ids %s, expected %s" % (sorted(got), sorted(m["expect"])))
    want = expected_where(m, rel, line)
    if want is not None:
        wheres = sorted(set(f[1] for f in res["fail"]))
        if wheres != [want]:
            problems.append("FAIL locations %s, expected [%s]" % (wheres, want))
    if m["frag"] and not any(m["frag"] in f[2] for f in res["fail"]):
        problems.append("no FAIL message contains %r" % m["frag"])
    return problems, "%s @ %s" % (",".join(sorted(got)), want)


# ---------------------------------------------------------------- full run
def full_run(checker, mod, engine, keep):
    t0 = time.time()
    rc, text, err = run_checker(checker, mod, engine, ["-v"])
    base = parse(text)
    if rc != 0 or err or base["summary"] is None or not base["summary"].endswith(" 0 FAILED"):
        for line in text.split("\n"):
            if line.startswith("  FAIL"):
                out("  real tree: " + line.strip())
        if err:
            out("  real tree stderr: %r" % err[:300])
        raise SelfTestError("the checker does not pass the real tree (exit %d) - fix the real violation first" % rc)
    rc2, listing, err2 = run_checker(checker, mod, engine, ["--list-inputs"])
    if rc2 != 0 or err2:
        raise SelfTestError("--list-inputs failed (exit %d)" % rc2)
    inputs = [tuple(l.split("\t", 1)) for l in listing.split("\n") if "\t" in l]
    if not inputs:
        raise SelfTestError("--list-inputs listed nothing")
    real = dict((kr, sha_file(os.path.join(mod if kr[0] == "mod" else engine, *kr[1].split("/")))) for kr in inputs)
    out("  real tree: %s (%d inputs)" % (base["summary"], len(inputs)))

    tmp = tempfile.mkdtemp(prefix="mpiso_selftest_")
    tmp_mod = os.path.join(tmp, "mod")
    tmp_engine = os.path.join(tmp, "engine")
    failures = []
    try:
        for kind, rel in inputs:
            src = os.path.join(mod if kind == "mod" else engine, *rel.split("/"))
            dst = os.path.join(tmp_mod if kind == "mod" else tmp_engine, *rel.split("/"))
            d = os.path.dirname(dst)
            if not os.path.isdir(d):
                os.makedirs(d)
            shutil.copyfile(src, dst)

        def clean(label):
            rc, text, err = run_checker(checker, tmp_mod, tmp_engine, ["-v"])
            res = parse(text)
            same = (res["pass"], res["pending"], res["warn"], res["scanned"], res["summary"]) == \
                   (base["pass"], base["pending"], base["warn"], base["scanned"], base["summary"])
            if rc != 0 or err or not same:
                raise SelfTestError("%s clean run on the copy differs from the real tree (exit %d, stderr %d bytes)"
                                    % (label, rc, len(err)))
            out("  clean copy (%s): %s" % (label, res["summary"]))

        anchor_precheck(tmp_mod, tmp_engine, checker, MUTATIONS + NEAR_MISSES)
        clean("before")
        for near, table in ((False, MUTATIONS), (True, NEAR_MISSES)):
            for m in table:
                try:
                    problems, got = run_one(m, checker, tmp, tmp_mod, tmp_engine, near)
                except SelfTestError as e:
                    problems, got = [str(e)], "error"
                if problems:
                    failures.append(m["id"])
                    out("  BAD  %-7s %s" % (m["id"], "; ".join(problems)))
                else:
                    out("  ok   %-7s %s" % (m["id"], got))
        clean("after")

        # coverage: every sub-id the checker can emit is proven, and every clause has a proof
        src = open(checker, "rb").read().decode("latin-1")
        universe = set(re.findall(r"fail\(\s*\"(\w+)\"", src))
        wuniverse = set(re.findall(r"warn\(\s*\"(\w+)\"", src))
        covered = set()
        for m in MUTATIONS:
            covered |= m["expect"]
        wcovered = set()
        for m in NEAR_MISSES:
            wcovered |= m["warn"]
        missing = sorted(universe - covered) + sorted(wuniverse - wcovered)
        rc3, clauses, _e = run_checker(checker, mod, engine, ["--list-clauses"])
        clause_ids = [c.strip() for c in clauses.split("\n") if c.strip()]
        uncovered = [c for c in clause_ids if not any(re.match(c + r"[a-z]", s) for s in covered)]
        if missing:
            failures.append("coverage")
            out("  BAD  coverage: sub-ids never proven to fire: %s" % ", ".join(missing))
        if uncovered or not clause_ids:
            failures.append("clauses")
            out("  BAD  coverage: clauses with no mutation: %s" % ", ".join(uncovered))
    finally:
        if keep:
            out("  kept temp copy: %s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    changed = [kr[1] for kr in real if sha_file(os.path.join(mod if kr[0] == "mod" else engine,
                                                             *kr[1].split("/"))) != real[kr]]
    if changed:
        raise SelfTestError("the REAL tree changed during the self-test: %s" % ", ".join(changed[:5]))
    if failures:
        raise SelfTestError("%d case(s) did not behave: %s" % (len(failures), ", ".join(failures)))
    return len(MUTATIONS), len(NEAR_MISSES), time.time() - t0


def stamp_key(checker):
    h = hashlib.sha256()
    h.update(open(checker, "rb").read())
    h.update(b"\0")
    h.update(open(SELF, "rb").read())
    h.update(b"\0")
    h.update(sys.version.encode())
    return h.hexdigest()


def main(argv):
    ap = argparse.ArgumentParser(description="prove check_mp_isolation.py can fail")
    ap.add_argument("--if-changed", action="store_true")
    ap.add_argument("--stamp", default=DEF_STAMP)
    ap.add_argument("--checker", default=DEF_CHECKER)
    ap.add_argument("--mod", default=DEF_MOD)
    ap.add_argument("--engine", default=DEF_ENGINE)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)
    checker, mod, engine = os.path.abspath(a.checker), os.path.abspath(a.mod), os.path.abspath(a.engine)
    try:
        if not os.path.isfile(checker):
            raise SelfTestError("checker not found: %s" % checker)
        load_checker(checker)
        key = stamp_key(checker)
        if a.if_changed and os.path.isfile(a.stamp):
            parts = open(a.stamp, "rb").read().decode("latin-1").split()
            if len(parts) >= 2 and parts[0] == key:
                anchor_precheck(mod, engine, checker, MUTATIONS + NEAR_MISSES)
                out("selftest: unchanged since %s" % parts[1])
                return 0
        n, m, secs = full_run(checker, mod, engine, a.keep)
        d = os.path.dirname(os.path.abspath(a.stamp))
        if not os.path.isdir(d):
            os.makedirs(d)
        with open(a.stamp, "wb") as f:
            f.write(("%s %s\n" % (key, datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
                    .encode())
        out("selftest: ok (%d mutations, %d near-misses, %ds)" % (n, m, int(round(secs))))
        return 0
    except SelfTestError as e:
        msg = str(e)
        if msg.startswith("SELFTEST ANCHOR DRIFT"):
            out(msg)
        out("selftest: FAILED - %s" % msg)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

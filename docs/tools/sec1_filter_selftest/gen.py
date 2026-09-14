#!/usr/bin/env python3
# SEC1 self-test generator.
#
# Emits the .inc files the harness links so the pass/fail behaviour below is produced by the SAME
# engine parser and the SAME filter source that ship in cgame.dll - never a hand copy (docs/TRAPS.md
# T14: the guard must be able to fail against the shipped code).
#
#   real_qshared.inc      COM_ParseExt / SkipWhitespace / Q_strncpyz / Q_stricmp[n]  (q_shared.c)
#   real_cmd.inc          Cmd_TokenizeString2 / Cmd_Args / Cmd_ArgsFrom              (cmd.c)
#   real_filter_work.inc  the WORKING-TREE cg_servercmds_filter.cpp (the patched filter)
#   real_filter_head.inc  the committed HEAD cg_servercmds_filter.cpp (the pre-SEC1 filter)
#
# The two filter incs drive the delta arm: HEAD must ADMIT the attack list, WORK must DROP it, which
# proves the fix is load-bearing rather than blocking things that were never allowed.
import os, re, subprocess, sys

ENG = r"C:\mohaa-coop-dev\openmohaa-hzm\code"
FILTER_REL = "code/cgame/cg_servercmds_filter.cpp"
FILTER_ABS = os.path.join(ENG, "cgame", "cg_servercmds_filter.cpp")
OUT = os.path.dirname(os.path.abspath(__file__))


def src(p):
    return open(os.path.join(ENG, p), encoding="latin-1").read()


def extract(text, sig):
    """Return the whole function whose signature matches `sig` (brace-balanced, string/comment aware)."""
    m = re.search(sig, text, re.M)
    if not m:
        sys.exit("signature not found: " + sig)
    i = m.start()
    j = text.index("{", m.end() - 1) if text[m.end() - 1] != "{" else m.end() - 1
    d = 0
    k = j
    n = len(text)
    while k < n:
        c = text[k]
        if text.startswith("//", k):
            k = text.index("\n", k)
            continue
        if text.startswith("/*", k):
            k = text.index("*/", k) + 2
            continue
        if c == '"' or c == "'":
            q = c
            k += 1
            while text[k] != q:
                if text[k] == "\\":
                    k += 1
                k += 1
            k += 1
            continue
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if d == 0:
                return text[i:k + 1]
        k += 1
    sys.exit("unbalanced " + sig)


def strip_includes(txt):
    return re.sub(r'^#include.*$', '', txt, flags=re.M)


qs = src("qcommon/q_shared.c")
cmd = src("qcommon/cmd.c")

qshared = [
    extract(qs, r"^static char \*SkipWhitespace\( char \*data, qboolean \*hasNewLines \)"),
    extract(qs, r"^char \*COM_ParseExt\( char \*\*data_p, qboolean allowLineBreaks \)"),
    extract(qs, r"^void Q_strncpyz\( char \*dest, const char \*src, size_t destsize \)"),
    extract(qs, r"^void Q_strcat\( char \*dest, int size, const char \*src \)"),
    extract(qs, r"^int Q_stricmpn\( const char \*s1, const char \*s2, size_t n \)"),
    extract(qs, r"^int Q_stricmp \(const char \*s1, const char \*s2\)"),
]
cmdparts = [
    extract(cmd, r"^static void Cmd_TokenizeString2\( const char \*text_in, qboolean ignoreQuotes \)"),
    extract(cmd, r"^char\s*\*Cmd_Args\( void \)"),
    extract(cmd, r"^char \*Cmd_ArgsFrom\( int arg \)"),
]

open(os.path.join(OUT, "real_qshared.inc"), "w", newline="\n").write("\n\n".join(qshared))
open(os.path.join(OUT, "real_cmd.inc"), "w", newline="\n").write("\n\n".join(cmdparts))

# SEC2: the working-tree filter now calls the statement rules shared with the exe (qcommon/cmd_filter.c).
# Paste the header + implementation verbatim, with the generated guard list inlined where cmd_filter.c
# includes it, so the patched arm links the same rule code that ships in cgame.dll and openmohaa.exe.
flt_h = src("qcommon/cmd_filter.h")
flt_c = src("qcommon/cmd_filter.c")
guard = src("qcommon/cmd_srvguard.h")
if flt_c.count('#include "cmd_srvguard.h"') != 1:
    sys.exit("cmd_filter.c no longer includes cmd_srvguard.h exactly once")
flt_c = flt_c.replace('#include "cmd_srvguard.h"', guard)
srv = strip_includes(flt_h).replace("#pragma once", "") + "\n" + strip_includes(flt_c)
open(os.path.join(OUT, "real_srvfilter.inc"), "w", newline="\n").write(srv)

# working-tree filter (the patched one under test)
open(os.path.join(OUT, "real_filter_work.inc"), "w", newline="\n").write(strip_includes(FILTER_ABS and open(FILTER_ABS, encoding="latin-1").read()))

# pre-SEC1 filter - via git so the delta arm always compares against what was checked in. It must be the
# filter as it was BEFORE the first bug-2580 commit, not HEAD: once SEC1 itself was committed, HEAD drops the
# attack list too and the delta arm failed on a correct tree (found 2026-09-13 while landing SEC2).
first = subprocess.run(
    ["git", "-C", r"C:\mohaa-coop-dev\openmohaa-hzm", "log", "--reverse", "--format=%H", "--grep=bug-2580",
     "--", FILTER_REL],
    capture_output=True, text=True,
)
if first.returncode != 0 or not first.stdout.split():
    sys.exit("could not find the bug-2580 commit of " + FILTER_REL + ": " + first.stderr)
base_rev = first.stdout.split()[0] + "^"
head = subprocess.run(
    ["git", "-C", r"C:\mohaa-coop-dev\openmohaa-hzm", "show", base_rev + ":" + FILTER_REL],
    capture_output=True, text=True, encoding="latin-1",
)
if head.returncode != 0:
    sys.exit("git show HEAD failed: " + head.stderr)
open(os.path.join(OUT, "real_filter_head.inc"), "w", newline="\n").write(strip_includes(head.stdout))

print("ok  qshared", [len(p) for p in qshared], " cmd", [len(p) for p in cmdparts],
      " work", os.path.getsize(os.path.join(OUT, "real_filter_work.inc")),
      " head", os.path.getsize(os.path.join(OUT, "real_filter_head.inc")))

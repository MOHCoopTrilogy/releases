#!/usr/bin/env python3
# Generates inv.inc: every real archived value the mod's server-side vstr's actually expand to, swept
# live from the cfg/urc tree, PLUS the script-BUILT shapes reconstructed from the `stufftext (...)`
# producers in coop_mod/*.scr (no hard-coded literals - each is grepped from source and its string-
# concatenation expression reconstructed with representative tokens). The harness sets each cvar and
# runs "vstr <cvar>" through the REAL filter and asserts 0 drops - i.e. no legitimate server-origin
# resend regresses. build.bat regenerates inv.inc fresh on every run (and re-generates a second time
# and byte-compares, so the output is proven reproducible - a stale copy cannot survive).
import os, re

ROOT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
OUT = os.path.dirname(os.path.abspath(__file__))
Q = chr(34)

# cvars the SERVER vstr's directly (grep of `stufftext ( "vstr ...` in coop_mod/*.scr, helmet/player/
# loadoutpick/itemhandler): these are the names the filter's vstr value-gate actually fires on.
server_vstr = {
    "coop_loA1", "coop_loA2", "coop_loA3", "coop_loA4",
    "coop_loASkin", "coop_loAHelm",
    "coop_loFA1", "coop_loFA2", "coop_loFA3", "coop_loFA4",
    "coop_loOpenSkin", "coop_loOpenHelm", "coop_loOpenInspect",
    "coop_loDeny", "g_m2l1", "g_m1l3",
}
# recursion targets a value can vstr into (exercises depth>1); base name after trailing digits
recursion = {"coop_loCmt", "coop_loCcur", "coop_loC", "coop_loFcmt", "coop_loFgo",
             "coop_loCharP", "coop_loCharN", "coop_loHelmP", "coop_loHelmN"}


def is_target(cv):
    if cv in server_vstr:
        return True
    return re.sub(r"\d+$", "", cv) in recursion


pat = re.compile(r'\b(seta|set|sets|setu)\s+([A-Za-z_]\w*)\s+(.+)$')
vals = {}   # cvar -> set of raw archived values
synth = {}  # cvar -> set of synthetic (script-built) values

for dp, dn, fn in os.walk(ROOT):
    if "_research" in dp or ".git" in dp:
        continue
    for f in fn:
        if not f.lower().endswith((".cfg", ".urc")):
            continue
        for line in open(os.path.join(dp, f), encoding="latin-1"):
            s = line.strip()
            if s.startswith("//"):
                continue
            m = pat.match(s)
            if not m:
                continue
            cv = m.group(2)
            if not is_target(cv):
                continue
            rest = m.group(3)
            # strip a trailing // comment that is outside quotes
            out = ""
            q = False
            j = 0
            while j < len(rest):
                c = rest[j]
                if c == Q:
                    q = not q
                if not q and rest[j:j + 2] == "//":
                    break
                out += c
                j += 1
            rest = out.strip()
            # take the value up to the first unquoted semicolon (one statement) and unquote
            val = ""
            q = False
            for c in rest:
                if c == Q:
                    q = not q
                    continue
                if c == ';' and not q:
                    break
                val += c
            val = val.strip().strip(Q)
            vals.setdefault(cv, set()).add(val)

# --- script-BUILT shapes: reconstructed from the coop_mod/*.scr `stufftext (...)` producers ---
# The .scr files build these values at runtime by string concatenation (e.g.
# `stufftext ( "seta coop_loFA" + local.slot + " append name ,f" + local.slot + local.fid )`), so the
# literal never sits in a cfg. We grep every stufftext line and reconstruct the emitted command by
# substituting a representative token for each non-literal concatenation piece (local.*, level.*,
# game.*, parenthesised expr). Then, for any `set|seta|sets|setu <targetcvar> <value>` whose cvar is
# a vstr target, the reconstructed <value> is recorded exactly as a live archived value would be.
#
# SUBS maps a concat variable to a representative literal (chosen so the reconstruction lands on a
# real in-range marker). Anything unmatched falls back to "1" (a harmless numeric token).
SUBS = [
    ("authtoken", "aBcDeF"), ("uniform", "american_army"), ("skin", "american_army"),
    ("fov", "90"), ("slot", "1"), ("fid", "3"), ("done", "2"), ("have", "2"), ("tgt", "5"),
    ("name", "Rifleman"), ("class", "allied_manager"), ("prev", "0"), ("flk", "5"), ("lk", "5"),
    ("pg", "1"), ("sid", "1"), ("idx", "1"), ("id", "1"),
]


def sub_var(piece):
    p = piece.strip().lower()
    for key, rep in SUBS:
        if key in p:
            return rep
    return "1"


# reconstruct a `stufftext ( <expr> )` concatenation into the concrete command it emits
def reconstruct(expr):
    out = ""
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c == Q:  # quoted literal - copy verbatim (unescape \n as a newline terminator we drop)
            i += 1
            while i < n and expr[i] != Q:
                if expr[i] == "\\" and i + 1 < n:
                    out += {"n": "\n", "t": "\t"}.get(expr[i + 1], expr[i + 1])
                    i += 2
                    continue
                out += expr[i]
                i += 1
            i += 1
        elif c == "(":  # parenthesised sub-expression -> a representative token
            d = 1
            i += 1
            while i < n and d:
                if expr[i] == "(":
                    d += 1
                elif expr[i] == ")":
                    d -= 1
                i += 1
            out += "1"
        elif c == "+" or c == ")" or c.isspace():
            i += 1  # separators / stray close-paren: skip (always advances -> no infinite loop)
        else:  # a bareword operand (local.x / level.x / game.x / number) -> representative token
            j = i
            while j < n and expr[j] not in "+()" and expr[j] != Q:
                j += 1
            out += sub_var(expr[i:j])
            i = j if j > i else i + 1  # defensive: never stall
    return out.replace("\n", " ").strip()


STUFF = re.compile(r'stufftext\s*\(?\s*(.+?)\s*\)?\s*(?://.*)?$')
setpat = re.compile(r'^(seta|set|sets|setu)\s+([A-Za-z_]\w*)\s+(.+)$')

for dp, dn, fn in os.walk(ROOT):
    if "_research" in dp or ".git" in dp:
        continue
    for f in fn:
        if not f.lower().endswith(".scr"):
            continue
        for line in open(os.path.join(dp, f), encoding="latin-1"):
            s = line.strip()
            if s.startswith("//") or "stufftext" not in s:
                continue
            m = STUFF.search(s)
            if not m:
                continue
            cmd = reconstruct(m.group(1))
            # a stufftext can carry several ';'-separated statements (e.g. player.scr:827 sets both
            # g_m2l2 and g_m2l1); record the value of every set-family statement whose cvar is a
            # vstr target, so each is replayed independently just as the engine would run it.
            for stmt in cmd.split(";"):
                sm = setpat.match(stmt.strip())
                if not sm:
                    continue
                cv = sm.group(2)
                if is_target(cv):
                    synth.setdefault(cv, set()).add(sm.group(3).strip())

allpairs = {}
for cv in sorted(set(vals) | set(synth)):
    allpairs[cv] = set(vals.get(cv, set())) | set(synth.get(cv, set()))


def cesc(v):
    return v.replace("\\", "\\\\").replace(Q, "\\" + Q)


lines = ["/* generated by gen_inv.py - real archived (swept) + script-built (synthetic) values */"]
# inv_setup pre-populates the recursion-target cvars so a value that chains (vstr coop_loCcur ...)
# resolves during replay. Last-wins per cvar is fine here: these only need to EXIST and pass.
lines.append("static void inv_setup(void){")
for cv in sorted(allpairs):
    if cv not in server_vstr:
        for v in sorted(allpairs[cv]):
            lines.append('  setcv(%s%s%s,%s%s%s,CVAR_USER_CREATED);' % (Q, cv, Q, Q, cesc(v), Q))
lines.append("}")

# inv_run sets AND vstr-checks every (server-vstr'd cvar, value) pair individually, so EVERY archived
# value is replayed - not just the last one written to each name.
lines.append("static int inv_run(void){ int n=0;")
for cv in sorted(allpairs):
    if cv in server_vstr:
        for v in sorted(allpairs[cv]):
            lines.append(
                '  setcv(%s%s%s,%s%s%s,CVAR_USER_CREATED);'
                ' { char b[512]; Q_strncpyz(b,%s%s%s,sizeof(b));'
                ' if(!CG_IsStatementAllowed(b)){printf("  REPLAY-FAIL %%s = %%s\\n",%s%s%s,%s%s%s);fail++;}else{pass++;} n++; }'
                % (Q, cv, Q, Q, cesc(v), Q, Q, "vstr " + cv, Q, Q, cv, Q, Q, cesc(v), Q))
lines.append("  return n;\n}")

open(os.path.join(OUT, "inv.inc"), "w", newline="\n").write("\n".join(lines))

# SEC2: the same inventory as plain data, for the exe-side (layer 2) replay in ../sec2_filter_selftest,
# which runs each server `vstr` through the real command buffer as SERVER-origin text.
pairs = ["/* generated by sec1_filter_selftest/gen_inv.py - INV_SETUP(cvar,value) / INV_PAIR(cvar,value) */"]
for cv in sorted(allpairs):
    if cv not in server_vstr:
        for v in sorted(allpairs[cv]):
            pairs.append('INV_SETUP(%s%s%s,%s%s%s)' % (Q, cv, Q, Q, cesc(v), Q))
for cv in sorted(allpairs):
    if cv in server_vstr:
        for v in sorted(allpairs[cv]):
            pairs.append('INV_PAIR(%s%s%s,%s%s%s)' % (Q, cv, Q, Q, cesc(v), Q))
open(os.path.join(OUT, "inv_pairs.inc"), "w", newline="\n").write("\n".join(pairs) + "\n")

tot = sum(len(v) for v in allpairs.values())
print("distinct target cvars:", len(allpairs), " (cvar,value) pairs:", tot)
for cv in sorted(allpairs):
    tag = "[SERVER-VSTR]" if cv in server_vstr else "[recursion]"
    ns = len(synth.get(cv, set()))
    print("  %-18s %s  %d values (%d synthetic)" % (cv, tag, len(allpairs[cv]), ns))

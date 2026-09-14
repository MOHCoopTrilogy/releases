#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sec2_guardlist.py - derive the SEC2 server-write guard list from the tree, and prove it has not drifted.

WHY THIS EXISTS
    Security layer 2 (openmohaa.exe) filters every SERVER-origin command line at execution. That cannot
    see a laundering path where the server only WRITES a cvar and the CLIENT later runs it through `vstr`
    from its own origin: autoexec.cfg firing an archived self-vstr'd one-shot (coop_fxPoolStep) at the
    next launch, an armory tile click (exec ui/loadout/t01.cfg -> vstr coop_loCmt01), a key bind
    (vstr clip_toggle), or an engine site that executes a cvar's value (nextmap).

    The approved closure (user, 2026-09-13) is a REFUSE-LIST, not persisted taint: server-origin writes to
    the cvars the client itself vstr's are refused - or, when the server legitimately writes that cvar
    today (the armory resends), the written VALUE is validated instead. The list must be DERIVED, never
    hand-maintained, or a new generator output silently reopens the hole. This script is the derivation.

DERIVATION
    1. CLIENT-VSTR NAMES - every `vstr <name>` the client can run from its own origin:
         a. every .cfg and .urc in the mod tree (autoexec.cfg included), comments stripped;
         b. engine string literals that contain `vstr <name>`, and engine sites that feed
            Cvar_VariableString("<name>") straight back into the command buffer (nextmap);
         c. `vstr <name>` inside a VALUE the server writes (loadoutpick.scr: seta coop_loCmt<id>
            "vstr coop_loCcur") - that value later expands at client origin.
       A name ending in digits folds into a digit family (coop_loCmt01 -> coop_loCmt#).
    2. SERVER WRITES - every cvar the server can write at server origin today:
         the writes (set/seta/sets/setu/append/bare `<cvar> <value>`) in every coop script
         `stufftext`, plus every write reached by following those stufftexts through `exec`
         (runtime-built paths become globs) and `vstr` (every value the tree assigns) to any depth.
    3. CLASS - VALIDATE if any server write lands in the family, else REFUSE.

USAGE
    python docs/tools/sec2_guardlist.py            write openmohaa-hzm/code/qcommon/cmd_srvguard.h
    python docs/tools/sec2_guardlist.py --check    exit 1 if the committed header no longer matches the tree
    python docs/tools/sec2_guardlist.py -v         also print every entry with its evidence
"""
import argparse
import fnmatch
import os
import re
import sys

DEV = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MOD = os.path.join(DEV, "hzm-mohaa-coop-mod")
ENG = os.path.join(DEV, "openmohaa-hzm", "code")
HEADER = os.path.join(ENG, "qcommon", "cmd_srvguard.h")

Q = '"'
W = "\x7f"  # stands in for a runtime-built piece of a script string (a token character to the tokenizer)
EXEC_PREFIXES = ("ui/loadout/", "ui/coop_", "coop_mod/")
SET_VERBS = ("set", "seta", "sets", "setu")
MAX_WALK_DEPTH = 16


# ------------------------------------------------------------------ engine-faithful text handling
def cbuf_split(text):
    """Split `text` into lines exactly like qcommon/cmd.c Cbuf_Execute (quotes, ;, LF, CR, //, /* */)."""
    out = []
    star = slash = False
    n = len(text)
    start = 0
    while start < n:
        quotes = 0
        i = start
        while i < n:
            c = text[i]
            if c == Q:
                quotes += 1
            if not quotes & 1:
                if i < n - 1:
                    if not star and text[i:i + 2] == "//":
                        slash = True
                    elif not slash and text[i:i + 2] == "/*":
                        star = True
                    elif star and text[i:i + 2] == "*/":
                        star = False
                        i += 1
                        break
                if not slash and not star and c == ";":
                    break
            if not star and c in "\r\n":
                slash = False
                break
            i += 1
        out.append(text[start:i])
        start = i + 1
    return out


def tokenize(s):
    """qcommon/cmd.c Cmd_TokenizeString2(text, qfalse)."""
    out = []
    i = 0
    n = len(s)
    while True:
        while i < n and ord(s[i]) <= 32:
            i += 1
        if i >= n or s.startswith("//", i):
            return out
        if s.startswith("/*", i):
            j = s.find("*/", i)
            if j < 0:
                return out
            i = j + 2
            continue
        if s[i] == Q:
            j = s.find(Q, i + 1)
            if j < 0:
                out.append(s[i + 1:])
                return out
            out.append(s[i + 1:j])
            i = j + 1
            continue
        j = i
        while j < n and ord(s[j]) > 32 and s[j] != Q and not s.startswith("//", j) and not s.startswith("/*", j):
            j += 1
        out.append(s[i:j])
        i = j


def read(p):
    return open(p, encoding="latin-1").read()


# ------------------------------------------------------------------ tree
def mod_files(exts):
    for dp, dn, fn in os.walk(MOD):
        dn[:] = [d for d in dn if d not in (".git", "_research")]
        for f in fn:
            if f.lower().endswith(exts):
                p = os.path.join(dp, f)
                yield os.path.relpath(p, MOD).replace("\\", "/"), p


def engine_files():
    for dp, dn, fn in os.walk(ENG):
        dn[:] = [d for d in dn if d not in ("thirdparty", ".git")]
        for f in fn:
            if f.lower().endswith((".c", ".cpp", ".h")):
                p = os.path.join(dp, f)
                yield os.path.relpath(p, ENG).replace("\\", "/"), p


def strip_line_comment(line):
    q = False
    for i, c in enumerate(line):
        if c == Q:
            q = not q
        elif not q and line.startswith("//", i):
            return line[:i]
    return line


def strip_block_comments(text):
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


def strip_c_comments(text):
    """Remove // and /* */ comments from C/C++ source, leaving string and char literals intact."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            out.append(" ")
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def engine_commands():
    """Registered command names (Cmd_AddCommand / cgame console table), lower-case."""
    names = set()
    for rel, p in engine_files():
        t = read(p)
        names.update(m.lower() for m in re.findall(r'(?:Cmd_AddCommand|AddCommand)\s*\(\s*"([^"]+)"', t))
        if rel.endswith("cg_consolecmds.c"):
            names.update(m.lower() for m in re.findall(r'\{\s*"([^"]+)"\s*,\s*&', t))
    return names


def reconstruct(expr):
    """Rebuild the command a `stufftext ( "lit" + local.x + "lit" )` emits; runtime pieces become W."""
    out = ""
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c == Q:
            i += 1
            while i < n and expr[i] != Q:
                if expr[i] == "\\" and i + 1 < n:
                    out += {"n": "\n", "t": "\t"}.get(expr[i + 1], expr[i + 1])
                    i += 2
                    continue
                out += expr[i]
                i += 1
            i += 1
        elif c == "(":
            d = 1
            i += 1
            while i < n and d:
                d += {"(": 1, ")": -1}.get(expr[i], 0)
                i += 1
            out += W
        elif c in "+)" or c.isspace():
            i += 1
        else:
            j = i
            while j < n and expr[j] not in "+()" and expr[j] != Q:
                j += 1
            out += W
            i = max(j, i + 1)
    return out


def stufftext_expr(s):
    """The argument expression of the first `stufftext` on a script line, or None.

    `stufftext ( <expr> )` -> the balanced, quote-aware parenthesised expression (a trailing `}` or a
    second statement on the line is NOT part of it); `stufftext "lit"` -> that literal; anything else
    (`stufftext local.cmd`) -> a single runtime piece."""
    m = re.search(r'\bstufftext\b\s*', s)
    if not m:
        return None
    i = m.end()
    if i >= len(s):
        return None
    if s[i] == "(":
        d = 0
        j = i
        q = False
        while j < len(s):
            c = s[j]
            if c == Q:
                q = not q
            elif not q:
                if c == "(":
                    d += 1
                elif c == ")":
                    d -= 1
                    if d == 0:
                        return s[i + 1:j]
            j += 1
        return s[i + 1:]
    if s[i] == Q:
        j = s.find(Q, i + 1)
        return s[i:j + 1] if j > 0 else s[i:]
    return W


def script_stufftexts():
    """[(statement, 'file:line')] for every coop script stufftext, split into Cbuf statements."""
    out = []
    for rel, p in mod_files((".scr",)):
        for ln, line in enumerate(open(p, encoding="latin-1"), 1):
            s = strip_line_comment(line).strip()
            if "stufftext" not in s:
                continue
            expr = stufftext_expr(s)
            if expr is None:
                continue
            cmd = reconstruct(expr) if expr != W else W
            for st in cbuf_split(cmd):
                if st.strip():
                    out.append((st, "%s:%d" % (rel, ln)))
    return out


class Tree(object):
    def __init__(self):
        self.cfg = {}                 # lower rel path -> text
        self.assigns = {}             # lower cvar (may hold W) -> set(values)
        self.assign_src = {}          # lower cvar -> set(rel)
        self.commands = engine_commands()
        for rel, p in mod_files((".cfg", ".urc")):
            txt = read(p)
            if rel.lower().endswith(".cfg"):
                self.cfg[rel.lower()] = txt
            for st in cbuf_split(txt):
                t = tokenize(st)
                if len(t) >= 3 and t[0].lower() in SET_VERBS:
                    self._assign(t[1], " ".join(t[2:]), rel)
        self.stuff = script_stufftexts()
        for st, where in self.stuff:
            t = tokenize(st)
            if len(t) >= 3 and t[0].lower() in SET_VERBS:
                self._assign(t[1], " ".join(t[2:]), where.split(":")[0])

    def _assign(self, name, value, src):
        k = name.lower()
        self.assigns.setdefault(k, set()).add(value)
        self.assign_src.setdefault(k, set()).add(src)

    def vstr_values(self, name):
        name = name.lower()
        out = set()
        for k, vs in self.assigns.items():
            if name_match(name, k):
                out |= vs
        return out

    def exec_files(self, path):
        """cfgs a server-origin `exec <path>` can reach: the filter's path scope, runtime pieces never cross '/'."""
        p = path.lower()
        rx = "".join("[^/]*" if c == W else re.escape(c) for c in p)
        if not p.endswith(".cfg"):
            rx += r"(?:\.cfg)?"
        out = []
        for k in self.cfg:
            if k.startswith(EXEC_PREFIXES) and re.fullmatch(rx, k):
                out.append(k)
        return sorted(out)

    def writes(self, tokens):
        """[(name, value)] a tokenized statement writes (bare `<cvar> <value>` = a non-command verb)."""
        if not tokens:
            return []
        v = tokens[0].lower()
        if v in SET_VERBS:
            return [(tokens[1], " ".join(tokens[2:]))] if len(tokens) >= 3 else []
        if v == "append":
            return [(tokens[1], tokens[2])] if len(tokens) >= 3 else []
        if len(tokens) >= 2 and v not in self.commands and v not in ("exec", "execq", "vstr", "wait", "echo"):
            return [(tokens[0], " ".join(tokens[1:]))]
        return []

    def server_closure(self):
        """Walk every script stufftext through exec/vstr. Returns {statement: first chain}; self.expanded is the
        set of statements some chain reaches THROUGH an exec or vstr (they run inside a cfg or a cvar value,
        at server origin depth >= 1)."""
        reached = {}
        self.expanded = set()
        seen = set()
        stack = [(st, [where], 0) for st, where in self.stuff]
        while stack:
            st, chain, depth = stack.pop()
            key = st.strip()
            if not key or (key, depth > 0) in seen or depth > MAX_WALK_DEPTH:
                continue
            seen.add((key, depth > 0))
            reached.setdefault(key, chain)
            if depth > 0:
                self.expanded.add(key)
            t = tokenize(st)
            if not t:
                continue
            v = t[0].lower()
            if v in ("exec", "execq") and len(t) > 1:
                for f in self.exec_files(t[1]):
                    for sub in cbuf_split(self.cfg[f]):
                        if sub.strip():
                            stack.append((sub, chain + ["exec " + f], depth + 1))
            elif v == "vstr" and len(t) > 1:
                for val in self.vstr_values(t[1]):
                    for sub in cbuf_split(val):
                        if sub.strip():
                            stack.append((sub, chain + ["vstr " + t[1].replace(W, "*")], depth + 1))
        return reached


def name_regex(name):
    """A cvar name that may hold runtime pieces -> regex (a runtime piece is identifier characters)."""
    return "".join("[a-z0-9_]*" if c == W else re.escape(c) for c in name.lower())


def name_match(a, b):
    """Could names a and b (either may hold runtime pieces) be the same cvar?"""
    a = a.lower()
    b = b.lower()
    return bool(re.fullmatch(name_regex(a), b.replace(W, "1")) or re.fullmatch(name_regex(b), a.replace(W, "1")))


# ------------------------------------------------------------------ families
VSTR_RE = re.compile(r'\bvstr\s+"?([A-Za-z_][A-Za-z0-9_' + W + r']*)', re.I)


def family(name):
    """-> (key, prefix, kind): kind 'EXACT' or 'DIGITS' (prefix followed by one or more digits)."""
    n = name
    if n.endswith(W):
        n = n.rstrip(W)
        n = re.sub(r"\d+$", "", n)
        return (n.lower() + "#", n, "DIGITS")
    if W in n:
        return None  # a runtime piece mid-name: cannot be a literal client vstr target
    m = re.match(r"^(.*[A-Za-z_])(\d+)$", n)
    if m:
        return (m.group(1).lower() + "#", m.group(1), "DIGITS")
    return (n.lower(), n, "EXACT")


def family_hit(prefix, kind, pattern):
    """Does a server write `pattern` (lower, may hold W) land in the family?"""
    pat = pattern.lower()
    p = prefix.lower()
    if kind == "EXACT":
        return name_match(p, pat)
    if W not in pat:
        return bool(re.fullmatch(re.escape(p) + r"\d+", pat))
    return any(re.fullmatch(name_regex(pat), p + d) for d in ("1", "01", "001", "0"))


EXEC_WINDOW = 16  # lines after a Cvar_VariableString("x") searched for the Cbuf call that runs it
CBUF_CALL = r'Cbuf_(?:ExecuteText|AddText|InsertText)\s*\(\s*(?:EXEC_\w+\s*,\s*)?'


def engine_executes_value(line, m, window_lines):
    """Does the engine hand the value of Cvar_VariableString("x") (match `m` on `line`) to the command buffer?

    The value must be the WHOLE command text, not an argument inside one: `Cbuf_AddText( va( "map %s\\n",
    Cvar_VariableString( "mapname" ) ) )` (sv_main.c, server side) runs `map`, not the value.

    Three shapes: the value formatted straight into a Cbuf call (`Cbuf_...( va("%s\\n", Cvar_VariableString
    ("x")) )` or through a variable on the next lines, cl_cin.cpp nextmap); that call on the same line; and
    the value copied or assigned into a variable that a Cbuf call within the window then takes as its whole
    argument or inside a va() (`Q_strncpyz( v, Cvar_VariableString("nextdemo"), ... )` ... `Cbuf_AddText( v )`,
    cl_main.cpp CL_NextDemo)."""
    window = "\n".join(window_lines)
    if re.search(CBUF_CALL + r'[^;]*va\s*\(\s*"%s', "\n".join(window_lines[:8])):
        return True
    if re.search(CBUF_CALL + re.escape(m.group(0)) + r'\s*\)', line):
        return True
    head = line[:m.start()]
    d = (re.search(r'Q_strncpyz\s*\(\s*([A-Za-z_]\w*)\s*,\s*$', head)
         or re.search(r'\b([A-Za-z_]\w*)\s*=\s*$', head))
    if not d:
        return False
    v = re.escape(d.group(1))
    return bool(re.search(CBUF_CALL + r'(?:' + v + r'\s*\)|va\s*\([^;]*\b' + v + r'\b)', window))


def script_identifier_literals(rel):
    """String literals in a script that are whole cvar-shaped identifiers (candidates for a runtime name)."""
    p = os.path.join(MOD, rel)
    if not os.path.exists(p):
        return set()
    return set(m for m in re.findall(r'"([A-Za-z_][A-Za-z0-9_]*_[A-Za-z0-9_]*)"', read(p)))


def derive():
    tree = Tree()
    fams = {}  # key -> dict(prefix, kind, client=set(src))

    def add(name, src):
        f = family(name)
        if not f:
            return
        e = fams.setdefault(f[0], {"prefix": f[1], "kind": f[2], "client": set(), "server": set()})
        e["client"].add(src)

    # 1a. mod cfg/urc (client-executable text)
    for rel, p in mod_files((".cfg", ".urc")):
        txt = strip_block_comments(read(p))
        for line in txt.splitlines():
            for m in VSTR_RE.finditer(strip_line_comment(line)):
                add(m.group(1), rel)
    # 1b. engine literals and cvar-value executors
    for rel, p in engine_files():
        if rel.endswith("qcommon/cmd_srvguard.h"):
            continue  # the generated output itself
        t = strip_c_comments(read(p))
        for lit in re.findall(r'"((?:[^"\\\n]|\\.)*)"', t):
            for m in VSTR_RE.finditer(lit):
                add(m.group(1), "engine:" + rel)
        lines = t.splitlines()
        for i, line in enumerate(lines):
            for m in re.finditer(r'Cvar_VariableString\s*\(\s*"([A-Za-z_]\w*)"\s*\)', line):
                if engine_executes_value(line, m, lines[i:i + EXEC_WINDOW]):
                    add(m.group(1), "engine-exec:" + rel)
    # 1c. vstr inside a value the server writes
    for st, where in tree.stuff:
        for name, value in tree.writes(tokenize(st)):
            for m in VSTR_RE.finditer(value):
                add(m.group(1), "server-value:" + where.split(":")[0])

    # 2. server writes: script stufftexts + everything reached through exec/vstr
    closure = tree.server_closure()
    server_writes = {}  # lower pattern -> first chain
    unresolved = []     # (statement, chain) whose written NAME is built entirely at runtime
    for st, chain in closure.items():
        for name, value in tree.writes(tokenize(st)):
            if name.replace(W, "") == "":
                # e.g. readygate.scr coop_gateSet: `set <local.gc> <local.gx>`. A bare `*` would poison every
                # family, so resolve the name from the identifier literals of the script that sends it.
                src = chain[0].rsplit(":", 1)[0]
                cands = script_identifier_literals(src)
                unresolved.append((st, chain, len(cands)))
                for c in cands:
                    server_writes.setdefault(c.lower(), chain + ["(runtime name candidate %s)" % c])
                continue
            server_writes.setdefault(name.lower(), chain)
    derive.unresolved = unresolved

    # 3. classify
    for key, e in fams.items():
        for pat, chain in server_writes.items():
            if family_hit(e["prefix"], e["kind"], pat):
                e["server"].add(" <- ".join(chain[-3:]).replace(W, "<*>"))
        e["cls"] = "VALIDATE" if e["server"] else "REFUSE"
    return fams, closure, tree


def render(fams):
    out = []
    out.append("/*")
    out.append(" * GENERATED by docs/tools/sec2_guardlist.py - DO NOT EDIT BY HAND.")
    out.append(" *   regenerate: python docs/tools/sec2_guardlist.py")
    out.append(" *   drift test: python docs/tools/sec2_guardlist.py --check   (exit 1 == stale)")
    out.append(" *")
    out.append(" * HZM coop [SEC2] server-write guard list, included ONLY by qcommon/cmd_filter.c.")
    out.append(" * Every cvar the CLIENT runs through `vstr` from its own origin (mod cfg/urc, engine literals,")
    out.append(" * engine cvar-value executors, vstr inside server-written values). A server-origin write to a")
    out.append(" * REFUSE entry is dropped; a write to a VALIDATE entry (the server legitimately writes it today)")
    out.append(" * is admitted only when the written value validates. DIGITS = prefix followed by 1+ digits.")
    out.append(" */")
    for key in sorted(fams):
        e = fams[key]
        out.append('SRVG( "%s", SRVG_%s, SRVG_%s )' % (e["prefix"], e["kind"], e["cls"]))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()

    fams, closure, tree = derive()
    for key, e in fams.items():
        if e["prefix"].lower().startswith("coop_mp"):
            sys.exit("FAIL: guard entry %s is a coop_mp* token (check_mp_isolation clause 14)" % e["prefix"])
        if any(ord(c) > 127 for c in e["prefix"]):
            sys.exit("FAIL: non-ASCII guard entry %r" % e["prefix"])
    text = render(fams)

    if a.v:
        nref = sum(1 for e in fams.values() if e["cls"] == "REFUSE")
        print("closure: %d script stufftext statements -> %d reached statements" % (len(tree.stuff), len(closure)))
        print("guard entries: %d  (REFUSE %d, VALIDATE %d)" % (len(fams), nref, len(fams) - nref))
        opaque = [(st, w) for st, w in tree.stuff if tokenize(st) and tokenize(st)[0] == W]
        print("opaque stufftexts (whole command built at runtime - no static derivation can see them): %d"
              % len(opaque))
        for st, w in opaque:
            print("  %s" % w)
        for st, chain, n in getattr(derive, "unresolved", []):
            print("runtime-built write name at %s: resolved against %d identifier literals of that script"
                  % (chain[0], n))
        for key in sorted(fams):
            e = fams[key]
            print("  %-8s %-6s %-24s client: %s" % (e["cls"], e["kind"], e["prefix"] + ("#" if e["kind"] == "DIGITS" else ""),
                                                  ", ".join(sorted(e["client"])[:2])))
            for s in sorted(e["server"])[:1]:
                print("                                           server: %s" % s[:150])

    if a.check:
        cur = open(HEADER, "rb").read().decode("ascii") if os.path.exists(HEADER) else ""
        if cur != text:
            print("sec2_guardlist: STALE - %s no longer matches the tree; run python docs/tools/sec2_guardlist.py"
                  % os.path.relpath(HEADER, DEV))
            return 1
        print("sec2_guardlist: OK (%d entries)" % len(fams))
        return 0

    with open(HEADER, "wb") as f:
        f.write(text.encode("ascii"))
    print("wrote %s (%d entries)" % (os.path.relpath(HEADER, DEV), len(fams)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""Statemap (.st) syntax check.

Exists because a brace-depth scan CANNOT catch this class: on 2026-08-28 two comment
lines shipped without their '//' prefix, depthscan2 passed the file, and the engine
rejected it with "Expecting ':' on line 89" - which ERR_DROPs the server on map load.

The rule the engine enforces: inside a `states { }` block every statement is
`NEWSTATE : CONDITION...` and MUST contain a colon. Inside `entrycommands { }` /
`exitcommands { }` the lines are commands and must NOT be required to have one. So the
check has to track which kind of block it is in - a flat "every line needs a colon" scan
produces hundreds of false positives on a perfectly good file.
"""
import io, re, sys

def check(path):
    bad = []
    depth = 0
    stack = []          # what kind of block each open brace is
    pending = None      # keyword seen just before a '{'
    for i, raw in enumerate(io.open(path, encoding="utf-8", errors="replace").read().split("\n"), 1):
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        for tok in re.findall(r'\{|\}|[^{}]+', line):
            tok = tok.strip()
            if tok == "{":
                stack.append(pending); pending = None; depth += 1
            elif tok == "}":
                if stack: stack.pop()
                depth -= 1
                if depth < 0:
                    bad.append((i, "brace depth went negative", raw.strip()))
            elif tok:
                low = tok.lower()
                if low in ("states", "entrycommands", "exitcommands", "action"):
                    pending = low
                elif re.match(r'^state\b', low) or re.match(r'^statemap\b', low):
                    pending = "state"
                else:
                    ctx = stack[-1] if stack else None
                    if ctx in ("states", "action") and ":" not in tok:
                        bad.append((i, "statement in a '%s' block has no ':'" % ctx, tok[:70]))
                    pending = None
    if depth != 0:
        bad.append((0, "unbalanced braces: file ends at depth %d" % depth, ""))
    return bad

rc = 0
for p in sys.argv[1:]:
    b = check(p)
    if b:
        rc = 1
        print("FAIL %s" % p)
        for ln, why, txt in b:
            print("   line %-5s %s  |  %s" % (ln or "?", why, txt))
    else:
        print("OK   %s" % p)
sys.exit(rc)

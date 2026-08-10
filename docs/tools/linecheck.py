"""
MOHAA .scr continuation linter.

WHY: depthscan2.py only balances braces, so it cannot see the parse break shipped on 08-02 -
a println() whose continuation lines each STARTED with '+'. That took the whole file down
("Script 'coop_mod/itemhandler.scr' was not properly loaded"), which killed the loadout system.

Multi-line statements ARE legal in MOHAA script - itemhandler.scr:53-55 wraps an if() across
three lines and compiles fine. The distinction is WHERE the operator sits: every working
example ends the line with the operator (`... ||`). A survey of the whole shipped mod finds
ZERO lines that begin with a binary operator. That is the rule this checks.

Deliberately NOT checked (verified false positives on hundreds of working lines):
  - `if (waitthread foo)`            - nested waitthread as a condition is normal and fine
  - unbalanced parens per line        - legal when the statement is a genuine continuation

Usage: python linecheck.py <file.scr> [...]
"""
import re
import sys

# a continuation line may not START with one of these
LEADING_OP = re.compile(r'^\s*(\+\+|--)?\s*(\+|\|\||&&|==|!=|>=|<=)(?!=)')
# ...but `+=`, `++`, a negative literal, and a lone `-` unary are fine, so keep the set tight


def strip_comment(line):
    out, i, instr = [], 0, False
    while i < len(line):
        c = line[i]
        if c == '"':
            instr = not instr
        if not instr and c == '/' and i + 1 < len(line) and line[i + 1] == '/':
            break
        out.append(c)
        i += 1
    return "".join(out)


def check(path, quiet=False):
    bad = []
    try:
        src = open(path, encoding="latin-1").read().split("\n")
    except OSError as e:
        print("  !! %s" % e)
        return False

    for n, raw in enumerate(src, 1):
        code = strip_comment(raw)
        if not code.strip():
            continue
        if code.lstrip().startswith("+="):
            continue
        if LEADING_OP.match(code):
            bad.append((n, "line STARTS with a binary operator - move it to the end of the "
                           "previous line", raw.strip()))

    if bad:
        print("FAIL %s" % path)
        for n, why, txt in bad:
            print("   %5d  %s" % (n, txt[:78]))
            print("          %s" % why)
        return False
    if not quiet:
        print("OK   %s" % path)
    return True


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "-q"]
    quiet = "-q" in sys.argv
    ok = all([check(p, quiet) for p in args])
    sys.exit(0 if ok else 1)

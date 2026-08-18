"""Catch an assignment that has no value on the right-hand side.

This is a PARSE KILLER, and in MOHAA script a parse killer takes the WHOLE file with it: the map
then runs with no script at all. It is worth its own check because of how badly it misreports.

A bare trailing '=' is legal on its own. Retail global/MountGunOrPlantCharge.scr does this:

    local.throbber_forward_component =
            (vector_dot local.gun_forward local.orig_gun_to_throbber)

so the rule is NOT "the line ends with =". The rule is: the line ends with '=' AND the next code
line is itself an assignment. Then the value was never written, the parser swallows the following
statement as the value, and chokes on THAT statement's '=' - reporting

    syntax error, unexpected TOKEN_ASSIGNMENT

against the line AFTER the broken one. Reading the error at face value sends you to a line that is
perfectly correct.

bug-1908: gen_loadout.py rendered six "level.coop_loRosterTab[N] = " lines from a column that was
empty in the table behind it. loadoutroster.scr stopped compiling outright. In game the only
symptoms were a NIL loadout, default weapons and no unlock padlocks - the compile failure itself
was a single console line nobody was watching. scrlint's brace/BOM/non-ASCII checks all passed it,
which is exactly the TRAPS T1 lesson: the scanners pass files that cannot compile.
"""
import glob
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else "hzm-mohaa-coop-mod"

# an '=' that is a real assignment, not ==, <=, >=, !=, +=, -=, *=, /=
ASSIGN_END = re.compile(r"[=<>!+\-*/]=$")
ASSIGN_IN = re.compile(r"[^=<>!+\-*/]=[^=]")


def strip_code(text):
    """Return [(lineno, code)] with strings and comments removed."""
    out = []
    state = "code"
    for ln, line in enumerate(text.split("\n"), 1):
        code = ""
        i = 0
        while i < len(line):
            c = line[i]
            if state == "code":
                if c == '"':
                    # leave a placeholder: a stripped string still IS a value, and without this
                    # every `x = "text"` looks like an empty right-hand side (167 false hits)
                    state = "string"
                    code += "S"
                elif c == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    break
                elif c == "/" and i + 1 < len(line) and line[i + 1] == "*":
                    state = "blockcomment"
                    i += 1
                else:
                    code += c
            elif state == "string":
                if c == '"':
                    state = "code"
            elif state == "blockcomment":
                if c == "*" and i + 1 < len(line) and line[i + 1] == "/":
                    state = "code"
                    i += 1
            i += 1
        if state == "string":      # unterminated quote - scrlint reports that one
            state = "code"
        if code.strip():
            out.append((ln, code))
    return out


fails = []
n = 0
for path in glob.glob(os.path.join(root, "**", "*.scr"), recursive=True):
    n += 1
    lines = strip_code(open(path, "rb").read().decode("latin-1"))
    for i, (ln, code) in enumerate(lines[:-1]):
        c = code.rstrip()
        if c.endswith("=") and not ASSIGN_END.search(c):
            if ASSIGN_IN.search(lines[i + 1][1]):
                rel = os.path.relpath(path, root)
                fails.append("%s:%d: assignment with an empty right-hand side - "
                             "the next line is another assignment, so this is a parse killer "
                             "and it kills the whole file" % (rel, ln))
                break

for f in fails:
    print("FAIL", f)
if fails:
    print("empty-rhs: %d FAIL in %d files - BUILD BLOCKED" % (len(fails), n))
    sys.exit(1)
print("  empty-rhs: %d script(s) clean" % n)

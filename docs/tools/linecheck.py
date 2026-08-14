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


# First words a real statement can start with. Only used to spare the prose rule below;
# prose beginning with one of these is vanishingly unlikely, and a false FAIL blocks a good build.
NUMBER = re.compile(r"^-?(\d+\.?\d*|\.\d+)$")

STATEMENT_WORDS = {
    "if", "else", "while", "for", "switch", "case", "default", "break", "continue", "end",
    "goto", "return", "thread", "waitthread", "exec", "waitexec", "wait", "waitframe",
    "waittill", "spawn", "trigger", "remove", "delete", "hide", "show", "println", "print",
    "iprint", "iprintln", "iprintlnbold", "iprintlnbold_noloc", "setcvar", "getcvar",
    "radiusdamage", "playsound", "loopsound", "stoploopsound", "anim", "anim_scripted",
    "walkto", "runto", "moveto", "forceactivate", "takeall", "give", "ammo", "use", "damage",
}

def check(path, quiet=False):
    bad = []
    try:
        src = open(path, encoding="latin-1").read().split("\n")
    except OSError as e:
        print("  !! %s" % e)
        return False

    prev_was_comment = False
    in_block = False                      # inside /* ... */
    for n, raw in enumerate(src, 1):
        stripped = raw.strip()
        # block comments are prose by definition - track and skip them
        if in_block:
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block = True
            continue
        # [2026-08-12] A COMMENT LINE THAT LOST ITS SLASHES - bug-1715, twice in one night.
        # Raw prose in code position is 'syntax error, unexpected TOKEN_COMMA' and the engine
        # refuses to compile the WHOLE file, so the map runs with no script at all. Braces,
        # quotes and operators all balance happily in prose, so no other scanner sees it.
        # Deliberately narrow: only fires when the PREVIOUS line was a comment, and only when the
        # line carries no argument-shaped token. A broad 'looks like English' rule flagged real
        # commands such as `radiusdamage local.gnd 600 900`, and a scanner that cries wolf is worse
        # than no scanner. This costs a missed case where prose starts a block; it never blocks a
        # good build.
        if prev_was_comment and stripped and not stripped.startswith(("//", "/*", "*")):
            bare = strip_comment(raw).strip()      # a trailing // is not prose
            first = bare.split()[0].lower() if bare.split() else ""
            rest = bare.split()[1:]
            # `fadeout 0.1 0 0 0 1` is a command with numeric args, not prose. Any line whose
            # arguments are ALL numbers is a call, whatever the verb is.
            all_numeric = bool(rest) and all(NUMBER.match(t) for t in rest)
            if (len(bare.split()) >= 4
                    and not all_numeric
                    and first not in STATEMENT_WORDS
                    and "_" not in first          # huddraw_align etc - commands have underscores,
                                                  # English words in a comment do not
                    and not any(t in bare for t in
                                ("local.", "level.", "game.", "self", "parm.", "group.",
                                 "$", '"', "=", "{", "}"))):
                bad.append((n, "prose directly under a comment - did you drop the // ? "
                               "(this silently kills the whole file)", bare))
        if stripped:
            prev_was_comment = stripped.startswith("//")

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

# -*- coding: utf-8 -*-
"""prosecheck.py - find ENGLISH PROSE standing where a Morpheus statement should be.

WHY THIS EXISTS. depthscan2 / linecheck / quotecheck all check STRUCTURE - brace depth, leading
operators, string termination. None of them can tell a sentence from a command, because

    test skips the WHOLE LOOP, and the code after this one is `takedamage` for every player

is, syntactically, a command call with eight arguments. So when a fixer's replacement drops the `//`
off the second line of a wrapped comment, every existing scanner passes a file that is broken:

  2026-09-06  a comment in coop_rampHandoff lost its marker and became `them. A mid-beat kill...`
  2026-09-08  eight continuation lines of two comment blocks in coopified.scr lost theirs - in the
              very session that wrote the TRAPS entry about the 09-06 case (bug-2531)

Both were produced the same way: a Python fixer inserting a multi-line comment where only the FIRST
line carried `//`. That is the failure this tool is for, and it belongs in the build beside
depthscan2 - the two are blind to different halves of the same class.

HOW IT DECIDES. A line is prose if it is not blank, not a comment, not a brace, not a label, does
not START like a statement, and then trips one of these - each chosen because no real statement in
this codebase does it:

  * a BACKTICK, which is not a Morpheus token and only ever appears in prose;
  * ending in a COMMA, which no statement does;
  * >= 5 words with no '(' and no '=' - a sentence, not a call;
  * sentence punctuation ('. ' followed by a word) with no '(' on the line.

The load-bearing test is the FIRST TOKEN. A statement begins with a receiver (`local.x`, `self`,
`$ent`), a scope, a keyword, or a command name; prose begins with an ordinary English word.

  python docs/tools/prosecheck.py <file.scr> [more.scr ...]
  python docs/tools/prosecheck.py --all          every .scr in the mod tree

exit 1 if anything is flagged.
"""
import os
import re
import sys
import glob

MOD = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                   "hzm-mohaa-coop-mod")

# a bare statement may legitimately start with one of these and carry no other punctuation
KEYWORD = re.compile(r"^(end|break|continue|waitframe|wait|thread|waitthread|exec|goto|case|default|"
                     r"else|if|while|for|switch|return|try|catch)\b")

# `name:{`, `name local.a local.b:{`, or a bare goto target `name:`
LABEL = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\s+(local\.|level\.)[A-Za-z0-9_]+)*\s*:\s*\{?\s*$")

# A statement's first token: a scope/receiver, a targetname, or a brace.
CODE_START = re.compile(r"^(local|level|self|game|parm|group|owner|world|player)\b|^[\$\{\}]")

# ...or a call: `println(`, or one of the engine commands used bare at statement level.
CALL = re.compile(r"^[a-z][a-z0-9_]*\s*\(")
COMMANDISH = re.compile(r"^(ihuddraw_|println|print|iprint|spawn|stuffsrv|cache|remove|delete|"
                        r"setcvar|tmstart|tmstartloop|playsound|stopsound|fadein|fadeout|clearfade|"
                        r"missionfailed|teleport|centerprint|locprint|setthread|assert)\b")


STOPWORDS = set("""a an the and or but so because if then than that this these those it its
of to in on at by for with from into onto over under after before while when where which who whom
whose is are was were be been being has have had do does did not no nor as up down out off about
against between through during without within upon per via i you he she they we them his her their
our your my me him us anyone everyone something anything nothing every each both all any some most
more less least very much many few own same other another such only just even still yet already
here there now once again always never sometimes often rather instead however therefore thus hence
would could should must may might can will shall does""".split())


def is_prose(s):
    line = s.strip()
    if not line or line.startswith("//") or line.startswith("/*") or line.startswith("*"):
        return None
    if line.startswith("{") or line.startswith("}"):
        return None
    if LABEL.match(line):
        return None
    # strip string literals, then the trailing // comment, so neither can trip a rule
    bare = re.sub(r'"[^"]*"', '""', line)
    bare = bare.split("//")[0].strip()
    if not bare:
        return None
    if CODE_START.match(bare) or CALL.match(bare) or COMMANDISH.match(bare) or KEYWORD.match(bare):
        return None
    if "`" in bare:
        return "backtick - not a Morpheus token"
    if bare.endswith(","):
        return "ends in a comma"
    # THE DISCRIMINATOR. Enumerating every bare engine command (waitexec, radiusdamage, huddraw_*,
    # earthquake, aliascache, the whole UI colour vocabulary...) is a losing game. Argument lists do
    # not contain English function words; sentences are made of them. Two is already decisive.
    words = [w.strip(".,;:()[]").lower() for w in re.split(r"\s+", bare)[1:]]
    stop = sum(1 for w in words if w in STOPWORDS)
    if stop >= 2:
        return "%d English function words in argument positions" % stop
    if stop and re.search(r"[a-z]\.\s+[A-Za-z]", bare) and "(" not in bare:
        return "sentence punctuation"
    return None


def scan(path):
    """Walk the file tracking /* */ state - a line inside a block comment is not code, and the
    retail map scripts carry large prose blocks that would otherwise be flagged wholesale."""
    hits = []
    with open(path, "rb") as f:
        text = f.read().decode("latin-1")
    inblock = False
    for i, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if inblock:
            if "*/" in stripped:
                inblock = False
                # anything after the close on the same line is code again
                stripped = stripped.split("*/", 1)[1].strip()
                if not stripped:
                    continue
            else:
                continue
        elif "/*" in stripped.split("//")[0] and "*/" not in stripped:
            # a `/*` that appears AFTER a `//` is prose about block comments, not one opening
            inblock = True
            continue
        why = is_prose(stripped)
        if why:
            hits.append((i, why, line.rstrip()[:110]))
    return hits


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--all" in sys.argv or not args:
        # Morpheus map/coop scripts only. ui/*.SCR is the menu language and ubersound/uberdialog are
        # alias tables - both are .scr and neither is Morpheus, so they would be all false positives.
        args = []
        for sub in ("maps", "coop_mod", "global"):
            args += glob.glob(os.path.join(MOD, sub, "**", "*.scr"), recursive=True)
        args = sorted(p for p in args
                      if os.path.basename(p).lower() not in ("ubersound.scr", "uberdialog.scr"))
    bad = 0
    for p in args:
        hits = scan(p)
        if hits:
            bad += len(hits)
            print("PROSE-AS-CODE  %s" % p)
            for ln, why, txt in hits:
                print("  %6d  [%s]  %s" % (ln, why, txt))
    if bad:
        print("\nFAILED: %d prose line(s) across %d file(s) scanned" % (bad, len(args)))
        return 1
    print("OK   %d file(s) scanned, no prose standing where a statement should be" % len(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())

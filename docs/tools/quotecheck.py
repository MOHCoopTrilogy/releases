"""
Find UNTERMINATED / MULTI-LINE STRING LITERALS in the mod's .scr files.

Motivated by bug-1283: coop_mod/buildmode.scr contained a string literal written across four
lines. Morpheus cannot do that - it read the opening quote as a bare command ('unknown command: "')
and failed to compile the WHOLE file, so build mode silently ceased to exist. bug-1285 then found
two more, latent, in shipped retail gag scripts.

This class is invisible to the other two scanners:
  - depthscan2.py  - braces still balance
  - linecheck.py   - no line starts with a binary operator

Heuristic: for each line, walk the CODE portion (stopping at a // that is not inside a string) and
count double quotes. An odd count means the string never closed on that line.

Known-good exception: ubersound/uberdialog.scr carries retail subtitles with genuine embedded
newlines inside an 'alias' - a different construct the alias parser accepts. Skipped by default.

Exit 1 if anything is found, so it can gate a build.
"""
import glob
import io
import os
import sys

ROOT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"

# retail data files whose parser genuinely tolerates embedded newlines (see bug-1285)
SKIP = {"ubersound/uberdialog.scr", "ubersound/ubersound.scr"}


def code_part(line):
    """Return the line up to a comment marker, honouring quotes (a // inside a string is data)."""
    out, i, in_str = [], 0, False
    while i < len(line):
        c = line[i]
        if c == '"':
            in_str = not in_str
        if not in_str and c == "/" and i + 1 < len(line) and line[i + 1] == "/":
            break
        out.append(c)
        i += 1
    return "".join(out)


def main(argv):
    targets = argv[1:]
    if targets:
        files = [os.path.abspath(t) for t in targets]
    else:
        files = glob.glob(os.path.join(ROOT, "**", "*.scr"), recursive=True)

    bad = []
    for path in sorted(files):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        if rel in SKIP:
            continue
        try:
            src = io.open(path, encoding="latin-1").read().split("\n")
        except OSError:
            continue
        for n, line in enumerate(src, 1):
            if code_part(line).count('"') % 2:
                bad.append((rel, n, line.strip()[:90]))

    if not bad:
        print("OK   no unterminated string literals in %d file(s)" % len(files))
        return 0

    print("UNTERMINATED STRING LITERAL - this kills the WHOLE file at compile time\n")
    for rel, n, text in bad:
        print("  %s:%d" % (rel, n))
        print("      %s" % text)
    print("\n%d site(s). Note the game log names only the FIRST one per file - fix them all." % len(bad))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""scrlint - static parse-killer gate for Morpheus .scr files (detector catalog rank 1, static half).

Rewrite of the lost scratchpad scanners, now comment- and string-AWARE (the raw-brace-count trap):
  FAIL: UTF-8 BOM; non-ASCII outside string literals/comments; brace depth negative or nonzero at
        EOF; unterminated string at end of line (cross-line quote pair = parse killer);
        unterminated /* block at EOF.
  WARN: non-ASCII inside strings/comments (engine tolerates latin-1 there - player.scr name bus).

Usage: python docs/tools/scrlint.py [root]   (default: hzm-mohaa-coop-mod)
Exit 1 on any FAIL. Wired into build.ps1 as a hard gate.
"""
import sys, os, glob

root = sys.argv[1] if len(sys.argv) > 1 else r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
fails = []
warns = []

def lint(path):
    raw = open(path, "rb").read()
    rel = os.path.relpath(path, root)
    if raw[:3] == b"\xef\xbb\xbf":
        fails.append(f"{rel}: UTF-8 BOM")
        return
    text = raw.decode("latin-1")
    depth = 0
    state = "code"           # code | string | linecomment | blockcomment
    for ln, line in enumerate(text.split("\n"), 1):
        if state == "linecomment":
            state = "code"
        i = 0
        while i < len(line):
            c = line[i]
            if state == "code":
                if c == '"':
                    state = "string"
                elif c == "/" and i + 1 < len(line) and line[i+1] == "/":
                    state = "linecomment"; break
                elif c == "/" and i + 1 < len(line) and line[i+1] == "*":
                    state = "blockcomment"; i += 1
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth < 0:
                        fails.append(f"{rel}:{ln}: brace depth negative")
                        return
                elif ord(c) > 127:
                    fails.append(f"{rel}:{ln}: non-ASCII 0x{ord(c):02x} outside string/comment")
                    return
            elif state == "string":
                if c == '"':
                    state = "code"
                elif ord(c) > 127:
                    warns.append(f"{rel}:{ln}: non-ASCII inside string")
            elif state == "blockcomment":
                if c == "*" and i + 1 < len(line) and line[i+1] == "/":
                    state = "code"; i += 1
                elif ord(c) > 127:
                    warns.append(f"{rel}:{ln}: non-ASCII inside comment")
            i += 1
        if state == "string":
            fails.append(f"{rel}:{ln}: unterminated string at end of line (cross-line quote pair)")
            return
        if state == "linecomment":
            state = "code"
    if state == "blockcomment":
        fails.append(f"{rel}: unterminated /* block at EOF")
    elif depth != 0:
        fails.append(f"{rel}: brace depth {depth} at EOF")

n = 0
for f in glob.glob(os.path.join(root, "**", "*.scr"), recursive=True):
    lint(f); n += 1

for w in warns[:10]:
    print("WARN", w)
if fails:
    for x in fails:
        print("FAIL", x)
    print(f"scrlint: {len(fails)} FAIL in {n} files - BUILD BLOCKED")
    sys.exit(1)
print(f"scrlint: {n} files clean ({len(warns)} warns)")

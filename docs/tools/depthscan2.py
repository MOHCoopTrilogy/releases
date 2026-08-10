"""Running-depth brace scan for MOHAA .scr files.

Raw brace counting miscounts braces that appear inside // comments, /* */ blocks
and "quoted strings" -- and two opposite errors can cancel so the totals still
balance while the file is broken (bug-239). This walks the file tracking depth.

Rules enforced:
  * depth must never go negative
  * depth must be 0 at EOF
  * a column-0 label must sit at depth 0 (internal goto labels may sit at depth 1)
"""
import sys
import re

LABEL = re.compile(r'^[A-Za-z_]\w*(\s+local\.\w+)*\s*:')
BACKSLASH = chr(92)


def scan(path):
    src = open(path, encoding='utf-8', errors='replace').read().split('\n')
    depth = 0
    in_block = False
    problems = []

    for lineno, line in enumerate(src, 1):
        if LABEL.match(line) and depth not in (0, 1):
            problems.append(
                "  line %d: label at depth %d (expected 0, or 1 for goto labels): %s"
                % (lineno, depth, line.strip()[:60]))

        i = 0
        n = len(line)
        while i < n:
            two = line[i:i + 2]
            if in_block:
                if two == '*/':
                    in_block = False
                    i += 2
                    continue
                i += 1
                continue
            if two == '//':
                break
            if two == '/*':
                in_block = True
                i += 2
                continue
            if line[i] == '"':
                i += 1
                while i < n and line[i] != '"':
                    if line[i] == BACKSLASH:
                        i += 1
                    i += 1
                i += 1
                continue
            if line[i] == '{':
                depth += 1
            elif line[i] == '}':
                depth -= 1
                if depth < 0:
                    problems.append("  line %d: DEPTH WENT NEGATIVE: %s"
                                    % (lineno, line.strip()[:60]))
            i += 1

    if depth != 0:
        problems.append("  EOF depth = %d (must be 0)" % depth)

    print(("FAIL " if problems else "OK   ") + path)
    for p in problems[:25]:
        print(p)
    return not problems


if __name__ == '__main__':
    ok = all(scan(p) for p in sys.argv[1:])
    sys.exit(0 if ok else 1)

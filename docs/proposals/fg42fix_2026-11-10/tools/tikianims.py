"""The TIKI 'animations { ... }' grammar as the engine parses it (tiki/tiki_parse.cpp TIKI_ParseAnimations /
TIKI_ParseAnimationCommands): returns the aliases that load and the places the engine would log
'unknown anim command' (a token inside an alias's { } that is not client / server / })."""
import re


def tokens(text):
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        line = re.sub(r"//.*", "", line)
        for t in re.findall(r'"[^"]*"|\S+', line):
            out.append((ln, t))
    return out


def parse(text):
    toks = tokens(text)
    n = len(toks)
    aliases, bad, i = [], [], 0
    # top level: find the 'animations' section(s); everything else (includes, setup...) is skipped
    while i < n:
        if toks[i][1].lower() == "animations" and i + 1 < n and toks[i + 1][1] == "{":
            i += 2
            while i < n:
                ln, t = toks[i]
                if t == "}":
                    i += 1
                    break
                if t.startswith("$"):            # $path ...
                    j = i + 1
                    while j < n and toks[j][0] == ln:
                        j += 1
                    i = j
                    continue
                # alias <file> [args] on one line, then an optional { client/server blocks }
                aliases.append((ln, t))
                j = i + 1
                while j < n and toks[j][0] == ln:
                    j += 1
                if j < n and toks[j][1] == "{":
                    j += 1
                    while j < n:
                        l2, t2 = toks[j]
                        if t2 == "}":
                            j += 1
                            break
                        if t2.lower() in ("client", "server") and j + 1 < n and toks[j + 1][1] == "{":
                            depth, j = 1, j + 2
                            while j < n and depth:
                                depth += {"{": 1, "}": -1}.get(toks[j][1], 0)
                                j += 1
                            continue
                        bad.append((l2, t2, t))
                        cur = l2
                        while j < n and toks[j][0] == cur:   # 'skipping line'
                            j += 1
                i = j
        else:
            i += 1
    return aliases, bad

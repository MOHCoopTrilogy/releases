#!/usr/bin/env python3
"""exec_audit.py: every `<var> = [self ]exec <file>::<label>` in the mod's scripts, with whether the label can wait.

Engine rule (proven 2026-11-23 on the live v1.10.89 build, headless test H:/hzm_work/decodeaudit/ea/mk_exectest.py):
`x = exec f::l` runs the label at once and hands back its `end <value>` ONLY if the label reaches its end without
executing any wait, waitframe, waittill - OR ANY waitthread / waitexec, even one whose callee returns at once. Otherwise
exec hands back an unresolved value at once: not the value, not NULL, not NIL (a label returning NULL through a nested
waitthread compares != NULL). A nested `exec` inside the label is harmless. `waitthread` always blocks and hands back the
value. So a site is a BUG when the label can execute one of those and the caller uses the value.
Verdicts: BUG-nested (only waitthread/waitexec inside: switching the site to waitthread changes no timing),
BUG-timed (real waits inside: the caller would now block - check the site), ok-no-wait, no-return, unknown-label.

usage: python docs/tools/exec_audit.py [--tsv out.tsv]   (run from the repo root; reads hzm-mohaa-coop-mod + the
game's stock pk3s for files the mod does not carry)
"""
import glob
import os
import re
import sys
import zipfile

MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hzm-mohaa-coop-mod")
GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)((?:\s+(?:local|group)\.[A-Za-z0-9_]+)*)\s*:(?!:)")
WAIT = re.compile(r"(?i)(?<![.\w])(wait|waitframe|waittill|waittillany|pause)\b")
NEST = re.compile(r"(?i)(?<![.\w])(waitthread|waitexec)\b")
CALL = re.compile(r"(?i)\b(waitthread|waitexec)\s+([A-Za-z0-9_/.]+::)?([A-Za-z0-9_]+)")
SITE = re.compile(r"(?i)^(.*?)([A-Za-z0-9_.\[\]\"]+)\s*=\s*(self\s+)?exec\s+([A-Za-z0-9_/.]+)::([A-Za-z0-9_]+)(.*)$")


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), s, flags=re.S)
    return "\n".join(l.split("//")[0] for l in s.split("\n"))


def load_files():
    files = {}
    for p in glob.glob(os.path.join(GOG, "main*", "*.pk3")):
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            if n.lower().endswith(".scr"):
                files.setdefault(n.lower(), z.read(n).decode("latin-1"))
    for p in glob.glob(os.path.join(MOD, "**", "*.scr"), recursive=True):
        rel = os.path.relpath(p, MOD).replace("\\", "/").lower()
        files[rel] = open(p, encoding="latin-1").read()          # the mod wins
    return files


def labels(text):
    out, cur, body = {}, None, []
    for line in strip_comments(text).split("\n"):
        m = LABEL.match(line)
        if m and not line.startswith((" ", "\t")):
            if cur:
                out[cur] = "\n".join(body)
            cur, body = m.group(1).lower(), [line[m.end():]]
        elif cur:
            body.append(line)
    if cur:
        out[cur] = "\n".join(body)
    return out


def main(argv):
    files = load_files()
    L = {f: labels(t) for f, t in files.items()}
    memo = {}

    def may_wait(f, lab, depth=0):
        key = (f, lab)
        if key in memo:
            return memo[key]
        memo[key] = False
        body = L.get(f, {}).get(lab)
        if body is None:
            memo[key] = None          # unknown label
            return None
        # 'timed' = a real wait in the label or in a label it waitthreads into; 'nested' = only waitthread / waitexec
        res = "timed" if WAIT.search(NEST.sub("", body)) else False
        if not res and NEST.search(body):
            res = "nested"
            if depth < 12:
                for c in CALL.finditer(body):
                    cf = (c.group(2)[:-2].lower() if c.group(2) else f)
                    if may_wait(cf, c.group(3).lower(), depth + 1) == "timed":
                        res = "timed"
                        break
        memo[key] = res
        return res

    rows = []
    for p in glob.glob(os.path.join(MOD, "**", "*.scr"), recursive=True):
        rel = os.path.relpath(p, MOD).replace("\\", "/")
        for i, line in enumerate(open(p, encoding="latin-1"), 1):
            code = line.split("//")[0]
            m = SITE.match(code)
            hits = []
            if m:
                hits.append((m.group(2), m.group(4).lower(), m.group(5).lower()))
            # the value used inline: ( exec f::l ... ) / if(exec f::l ...)
            for mi in re.finditer(r"(?i)\(\s*(?:self\s+)?exec\s+([A-Za-z0-9_/.]+)::([A-Za-z0-9_]+)", code):
                hits.append(("(inline)", mi.group(1).lower(), mi.group(2).lower()))
            for var, f, lab in hits:
                body = L.get(f, {}).get(lab)
                returns = bool(body is not None and re.search(r"(?m)\bend\s+[^\s/]", body.replace("}end", "} end")))
                w = may_wait(f, lab)
                verdict = ("unknown-label" if body is None else ("BUG-" + w) if (returns and w) else "ok-no-wait"
                           if returns else "no-return")
                rows.append((verdict, rel, i, var, f + "::" + lab, w, code.strip()))
    rows.sort(key=lambda r: (not r[0].startswith("BUG"), r[1], r[2]))
    from collections import Counter
    c = Counter(r[0] for r in rows)
    print("sites", len(rows), dict(c))
    for r in rows:
        if r[0].startswith("BUG") or r[0] == "unknown-label":
            print("%s\t%s:%d\t%s\t%s" % (r[0], r[1], r[2], r[3], r[4]))
    if "--tsv" in argv:
        with open(argv[argv.index("--tsv") + 1], "w", encoding="utf-8") as o:
            o.write("verdict\tfile\tline\tvar\ttarget\tlabel_may_wait\tcode\n")
            for r in rows:
                o.write("\t".join(str(x) for x in r) + "\n")
    print("labels that may wait (targets):", sorted({(r[4], r[0]) for r in rows if r[0].startswith("BUG")}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

#!/usr/bin/env python
"""Find shader files the engine will throw away WHOLE, and the ones we have masked.

WHY THIS EXISTS
A shader file is all-or-nothing. One syntax error and the engine prints
"WARNING: Ignoring shader file <name>" and discards EVERY shader in it - so a single stray
token 200 lines away turns a dozen unrelated weapons invisible at once. That is what happened
to soviet_weapons.shader: an orphan name with no { } body took out the file, and the user saw
"nagant sniper is also invisible, ppsh43 silenced is invisible, tt33 is invisible all as well".

Brace balance is NOT enough to catch it - an orphan name leaves the braces perfectly balanced.
The test that works is structural: at top level, every token must be a shader name IMMEDIATELY
followed by a { } block.

    python docs/tools/audit_shaders.py
"""
import glob
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
GAME = r"G:/GOG/Medal of Honor - Allied Assault War Chest"


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def check(text, label):
    """Return a list of structural defects that make the engine discard the whole file."""
    bad = []
    t = strip_comments(text)
    i, n, depth = 0, len(t), 0
    pending = None          # a top-level name we have seen but not yet matched to a {
    while i < n:
        c = t[i]
        if c == "{":
            depth += 1
            pending = None
            i += 1
            continue
        if c == "}":
            depth -= 1
            if depth < 0:
                bad.append("%s: unmatched '}' at offset %d" % (label, i))
                return bad
            i += 1
            continue
        if depth > 0:
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        m = re.match(r"\S+", t[i:])
        tok = m.group(0)
        if pending is not None:
            # two names in a row at top level: the first has no body, so the parser aborts
            bad.append("%s: shader '%s' has no { } body (next token is '%s')"
                       % (label, pending, tok))
        pending = tok
        i += len(tok)
    if depth != 0:
        bad.append("%s: %d unclosed '{' at end of file" % (label, depth))
    if pending is not None:
        bad.append("%s: trailing name '%s' with no { } body at end of file" % (label, pending))
    return bad


def main():
    # every shader the game can see, pak + mod, so we can also report which ones we override
    sources = {}        # virtual name -> list of (origin, text)
    for f in sorted(glob.glob(GAME + "/main*/*.pk3")):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for nm in z.namelist():
            if nm.lower().endswith(".shader"):
                sources.setdefault(os.path.basename(nm).lower(), []).append(
                    (os.path.basename(f), z.read(nm).decode("latin-1")))
    for p in glob.glob(os.path.join(MOD, "scripts", "*.shader")):
        sources.setdefault(os.path.basename(p).lower(), []).append(
            ("OUR MOD", io.open(p, "rb").read().decode("latin-1")))

    broken, masked, ok = [], [], 0
    for name in sorted(sources):
        entries = sources[name]
        winner_origin, winner_text = entries[-1]       # last pak alphabetically wins the file
        defects = check(winner_text, name)
        if defects:
            broken.append((name, winner_origin, defects))
        else:
            ok += 1
        # A file we ship that also exists in a THIRD-PARTY pak: ours wins, so the override is
        # worth seeing. Our own build output (co-op_hzm_mod_code.pk3) is the same loose files
        # repacked, so comparing against it is self-referential - ignore it.
        if winner_origin == "OUR MOD":
            under = [e[0] for e in entries[:-1] if "co-op_hzm_mod" not in e[0]]
            if under:
                masked.append((name, under))

    print("checked %d distinct shader files\n" % len(sources))
    if broken:
        print("== FILES THE ENGINE WILL DISCARD ENTIRELY (%d)" % len(broken))
        for name, origin, defects in broken:
            print("   %s   [effective copy: %s]" % (name, origin))
            for d in defects:
                print("      " + d.split(": ", 1)[1])
        print()
    else:
        print("no structurally broken shader files\n")
    if masked:
        print("== WE OVERRIDE THESE (our copy wins; keep it in sync if the pack updates) (%d)"
              % len(masked))
        for name, under in masked:
            print("   %-34s over %s" % (name, ", ".join(under)))
        print()
    print("%d file(s) clean" % ok)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

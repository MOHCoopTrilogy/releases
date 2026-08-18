"""Verify every `surface X shader Y` in our weapon tiks names a surface the mesh actually has.

A tik that names a surface its skd does not carry produces, at load:

    TIKI_InitTiki: could not find surface 'shell' in 'models/weapons/panzerfaust.tik'

and then that surface is untextured and - far worse - every FRAME COMMAND targeting it is dead.
That is bug-1912: the Panzerfaust inherited its whole surface list from our panzerschreck.tik, but
East's mesh carries four completely different surfaces, so `surface shell +nodraw` in the raise,
reload and fire animations all referred to nothing. The engine printed the reason on every single
load and it went unread for the entire hunt, through several wrong theories.

Surface names live in the skd as "SKL <name>" records, which is what this reads.

Scoped to models/weapons/ in the MOD only. Retail player models genuinely ship this warning
(allied_infantry and friends all name 'ranger_top_c', which does not exist), so widening it would
bury our own defects under content we do not own - the same reason the wav-existence check was
deleted from audit_weapons.py.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")


def skd_surfaces(path):
    """Surface names in an skd - stored as 'SKL <name>' records."""
    try:
        data = io.open(path, "rb").read()
    except OSError:
        return None
    return {m.decode()[4:].strip()
            for m in re.findall(rb"SKL [ -~]{1,62}", data)}


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else MOD
    weapons = os.path.join(root, "models", "weapons")
    fails, checked, noskd = [], 0, 0

    for p in sorted(glob.glob(os.path.join(weapons, "*.tik"))):
        t = io.open(p, encoding="latin-1", errors="replace").read()
        surfs = re.findall(r"(?mi)^\s*surface\s+(\S+)\s+shader\s+\S+", t)
        if not surfs:
            continue
        mpath = re.search(r"(?mi)^\s*path\s+(\S+)", t)
        mskel = re.search(r"(?mi)^\s*skelmodel\s+(\S+)", t)
        if not mpath or not mskel:
            continue
        skd = os.path.join(root, mpath.group(1).replace("/", os.sep), mskel.group(1))
        have = skd_surfaces(skd)
        if have is None:
            noskd += 1          # retail mesh, not shipped by us - nothing to check against
            continue
        checked += 1
        for s in surfs:
            if s.lower() == "all":
                continue        # TIKI wildcard for every surface, not a name - bar.tik uses it
            if s not in have and s.lower() not in {h.lower() for h in have}:
                fails.append("%s: surface '%s' is not on %s (mesh has: %s)"
                             % (os.path.basename(p), s, mskel.group(1),
                                ", ".join(sorted(have)[:6]) or "none"))

    for f in fails:
        print("FAIL", f)
    if fails:
        print("tik-surfaces: %d bad surface reference(s) in %d checked mesh(es) - BUILD BLOCKED"
              % (len(fails), checked))
        return 1
    print("  tik-surfaces: %d weapon mesh(es) clean (%d use retail meshes, not checkable)"
          % (checked, noskd))
    return 0


if __name__ == "__main__":
    sys.exit(main())

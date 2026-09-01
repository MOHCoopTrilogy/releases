"""
gen_gore_tiks.py - give character TIKIs the gore skin ladder they are missing.

WHY
---
bug-2202. Commit 00a2f577 (2026-08-21) fixed "invisible enemies" by clamping the gore skin tier to
what each surface actually declares:

    surfTier = gi.TIKI_SurfaceNumSkins(edict->tiki, i) - 1;
    if (surfTier > tier) { surfTier = tier; }

That clamp is correct and must stay - without it a surface with one skin renders as nothing. But it
makes the bloodied look purely a matter of authoring, and `audit_gore_skins.py` measured the result:
of 1656 AI TIKIs only 40 can reach a gore tier at all, and 76 of the ones the campaign actually
spawns cannot bleed - including Omaha's own dday_29th_private and dday_ranger_* rangers.

WHAT THIS DOES
--------------
For each target TIKI it inserts the missing ladder rungs:

    surface wehrmact_tunic shader wehrmacht_soldat            <- already there
    surface wehrmact_tunic shader wehrmacht_soldat_blood1     <- added (light)
    surface wehrmact_tunic shader wehrmacht_soldat_blood2     <- added (heavy)
    surface wehrmact_tunic shader wehrmacht_soldat_blood3     <- added (gib)

and writes the result as a mod-side override (our pk3 sorts last and wins).

THE ONE RULE THAT MATTERS
-------------------------
NEVER emit a shader name that does not exist. Referencing a missing shader is precisely what caused
the invisible-enemy bug this whole thing came from. So every rung is added only after confirming the
shader is defined in hzm-mohaa-coop-mod/scripts/*.shader.

AND THE RUNGS MUST BE CONTIGUOUS FROM _blood1, because the skin INDEX is the tier. The first version
of this tool emitted whichever variants happened to exist, which gave `hand` surfaces a lone
handsnew_blood3: that lands the GIB texture at tier 1, so hands looked shredded from a graze. A
surface stops at its first missing rung instead - _blood1 only is a fine 2-skin ladder, _blood3
without _blood1 is a bug.

Gear surfaces (helmet, holster, ammobox, gear, pouches...) are skipped: they should not bleed, and
the audit's "worst surface" metric is misleading precisely because of them.

Usage:
  python docs/tools/gen_gore_tiks.py --list      # report only, write nothing
  python docs/tools/gen_gore_tiks.py --write     # generate the overrides
"""

import argparse
import glob
import os
import re
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
PAK_GLOB = r"G:\GOG\Medal of Honor - Allied Assault War Chest\*\*.pk3"

TIERS = ("_blood1", "_blood2", "_blood3")
TIER_NOTE = {
    "_blood1": "HZM coop - gore tier 1 (light)",
    "_blood2": "HZM coop - gore tier 1 (heavy)",
    "_blood3": "HZM coop - gore tier1e (gib)",
}

# surfaces that are equipment, not flesh or cloth - they must not bleed
SKIP_SURF = re.compile(
    r"helmet|inside|outside|holster|ammobox|shell|gear|loadout|strap|pack|canteen|bayonet|knife|"
    r"granade|grenade|goggle|binocular|pouch|beret|hat$|cap$|armband|vest|map$",
    re.I,
)
SURF_RE = re.compile(r"^(\s*)surface\s+(\S+)\s+shader\s+(\S+)\s*(//.*)?$", re.I)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return "\n".join(l.split("//")[0] for l in text.splitlines())


def shipped_shaders():
    have = set()
    for f in glob.glob(os.path.join(MOD, "scripts", "*.shader")):
        t = strip_comments(open(f, encoding="latin-1").read())
        for m in re.finditer(r"^\s*([A-Za-z0-9_\-/\.]+)\s*$", t, re.M):
            have.add(m.group(1).lower())
    return have


def retail_bodies():
    """lowercased path -> raw text, first pak wins (retail order)."""
    out = {}
    for p in sorted(glob.glob(PAK_GLOB)):
        if "co-op_hzm" in os.path.basename(p):
            continue
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            ln = n.lower()
            if ln.endswith(".tik") and ln.startswith("models/human/") and ln not in out:
                try:
                    out[ln] = z.read(n).decode("latin-1")
                except Exception:
                    pass
        z.close()
    return out


def existing_skins(text):
    """surface -> number of shader tokens, matching tiki_parse.cpp."""
    per = {}
    for line in strip_comments(text).splitlines():
        m = re.match(r"\s*surface\s+(\S+)\s+(.*)$", line, re.I)
        if not m:
            continue
        n = len(re.findall(r"\bshader\s+\S+", m.group(2), re.I))
        if n:
            per[m.group(1).lower()] = per.get(m.group(1).lower(), 0) + n
    return per


def build(text, have):
    """Insert the missing rungs. Returns (new_text, {surface: [tiers added]})."""
    counts = existing_skins(text)
    added = {}
    out = []
    done = set()
    for line in text.split("\n"):
        out.append(line)
        m = SURF_RE.match(line)
        if not m:
            continue
        indent, surf, shader = m.group(1), m.group(2), m.group(3)
        key = surf.lower()
        if key in done or SKIP_SURF.search(surf):
            continue
        # only extend a surface that is genuinely short
        if counts.get(key, 0) >= 4:
            continue
        # RUNGS MUST BE CONTIGUOUS FROM _blood1. The skin index IS the tier, so a surface that has
        # only _blood3 would put the GIB texture at tier 1 - hands looking shredded from a graze.
        # Stop at the first missing rung rather than emitting what happens to exist.
        # Rungs already declared on THIS surface must not be re-emitted - the tool has to be safe to
        # re-run as new blood shaders are generated, or a second pass duplicates every existing rung.
        already = set()
        for mm in re.finditer(r"^\s*surface\s+" + re.escape(surf) + r"\s+shader\s+(\S+)",
                              text, re.I | re.M):
            hit = re.search(r"(_blood[123])$", mm.group(1), re.I)
            if hit:
                already.add(hit.group(1).lower())
        rungs = []
        for t in TIERS:
            if (shader.lower() + t) not in have:
                break
            if t not in already:
                rungs.append(t)
        if not rungs:
            continue
        done.add(key)
        for t in rungs:
            out.append("%ssurface %s shader %s%s\t// %s" % (indent, surf, shader, t, TIER_NOTE[t]))
        added[surf] = rungs
    return "\n".join(out), added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the override TIKIs")
    ap.add_argument("--list", action="store_true", help="report only")
    ap.add_argument("--only", help="substring filter on the tiki path")
    args = ap.parse_args()
    if not args.write and not args.list:
        args.list = True

    have = shipped_shaders()
    print("  gore shaders shipped: %d" % len(have))
    retail = retail_bodies()

    fixlist = os.path.join(REPO, "docs", "generated", "gore_missing.txt")
    if not os.path.exists(fixlist):
        print("  missing %s - run audit_gore_skins.py first (see its --csv)" % fixlist)
        return 1
    targets = [l.strip() for l in open(fixlist, encoding="utf-8") if l.strip() and not l.startswith("#")]
    if args.only:
        targets = [t for t in targets if args.only in t]

    wrote = skipped = 0
    for path in targets:
        local = os.path.join(MOD, path.replace("/", os.sep))
        src = open(local, encoding="latin-1").read() if os.path.exists(local) else retail.get(path)
        if src is None:
            print("    UNRESOLVED %s" % path)
            continue
        new, added = build(src, have)
        if not added:
            skipped += 1
            continue
        total = sum(len(v) for v in added.values())
        print("    %-56s +%d rung(s) over %d surface(s)" % (path, total, len(added)))
        if args.write:
            os.makedirs(os.path.dirname(local), exist_ok=True)
            data = new.encode("latin-1")
            open(local, "wb").write(data)
            wrote += 1
    print()
    print("  %s: %d written, %d already covered / nothing to add"
          % ("WROTE" if args.write else "DRY RUN", wrote, skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())

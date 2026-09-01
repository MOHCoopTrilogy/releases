"""
audit_gore_skins.py - how many gore skins does each character TIKI actually author?

WHY THIS EXISTS
---------------
bug-2202 / commit 00a2f577 (2026-08-21) fixed "invisible enemies" by clamping the gore skin tier
to what each SURFACE really declares:

    surfTier = gi.TIKI_SurfaceNumSkins(edict->tiki, i) - 1;
    if (surfTier > tier) { surfTier = tier; }

Before that the engine applied the requested tier blindly, and a surface with no such skin rendered
as nothing. The clamp is correct and must stay. But it means the bloodied look is now bounded by
authoring: a surface with only 1 skin can never leave tier 0, however much damage it takes, so those
enemies read clean no matter how many rounds go into them.

This tool measures that, so the fix is an authoring list rather than a guess.

WHAT IT COUNTS
--------------
Exactly what the engine counts. tiki_parse.cpp:934-948 increments `numskins` once per `shader`
token parsed under a surface, and TIKI_Surface_NumSkins returns that. So numskins is the number of
`shader` tokens declared for a surface across the whole setup block - `surface X shader A shader B`
and two separate `surface X shader ...` lines both give 2.

`surface all shader X` applies to every surface, so it is tracked separately and folded in.

RESOLUTION ORDER
----------------
Our pk3s sort last and therefore WIN, so the effective TIKI for a path is the mod's copy if one
exists, else the retail one. This resolves the same way, and reports which source won.

Usage:  python docs/tools/audit_gore_skins.py [--tiers N] [--all] [--csv out.csv]
"""

import argparse
import glob
import os
import re
import sys
import zipfile
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
PAK_GLOB = r"G:\GOG\Medal of Honor - Allied Assault War Chest\*\*.pk3"

# Character TIKIs live under these prefixes. models/player is the armory/player set; models/human is
# the AI set - the AI set is what the user shoots, so it is reported first.
AI_PREFIX = "models/human/"
PLAYER_PREFIX = "models/player/"

SURF_RE = re.compile(r"^\s*surface\s+(\S+)\s+(.*)$", re.I)
SHADER_RE = re.compile(r"\bshader\s+(\S+)", re.I)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return "\n".join(l.split("//")[0] for l in text.splitlines())


def parse_skins(body):
    """Return {surface_name: numskins}, mirroring tiki_parse.cpp's counting."""
    body = strip_comments(body)
    per = defaultdict(int)
    allsurf = 0
    for line in body.splitlines():
        m = SURF_RE.match(line)
        if not m:
            continue
        name = m.group(1).lower()
        n = len(SHADER_RE.findall(m.group(2)))
        if n == 0:
            continue
        if name == "all":
            allsurf += n
        else:
            per[name] += n
    if allsurf:
        # `surface all` contributes to every named surface, and to nothing if none are named.
        for k in list(per):
            per[k] += allsurf
        if not per:
            per["all"] = allsurf
    return dict(per)


def collect():
    """path -> (source, body) with mod copies winning."""
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
            if ln.endswith(".tik") and (ln.startswith(AI_PREFIX) or ln.startswith(PLAYER_PREFIX)):
                if ln not in out:
                    try:
                        out[ln] = ("retail:" + os.path.basename(p), z.read(n).decode("latin-1"))
                    except Exception:
                        pass
        z.close()
    for pref in (AI_PREFIX, PLAYER_PREFIX):
        base = os.path.join(MOD, pref.replace("/", os.sep))
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.lower().endswith(".tik"):
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, MOD).replace(os.sep, "/").lower()
                try:
                    out[rel] = ("mod", open(full, "rb").read().decode("latin-1"))
                except Exception:
                    pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", type=int, default=4,
                    help="skins needed for the full gore ladder (default 4: base + 3 gore levels)")
    ap.add_argument("--all", action="store_true", help="list every TIKI, not just the shortfall")
    ap.add_argument("--csv", help="write the full table to a CSV")
    args = ap.parse_args()

    tiks = collect()
    if not tiks:
        print("no character TIKIs found - is the retail install mounted?")
        return 1

    rows = []
    for path, (src, body) in sorted(tiks.items()):
        skins = parse_skins(body)
        if not skins:
            continue  # no surface/shader lines at all (include-only or alias tik)
        worst = min(skins.values())
        best = max(skins.values())
        short = sorted([s for s, n in skins.items() if n < args.tiers])
        kind = "AI" if path.startswith(AI_PREFIX) else "player"
        rows.append((kind, path, src, worst, best, len(skins), short))

    for kind in ("AI", "player"):
        sub = [r for r in rows if r[0] == kind]
        if not sub:
            continue
        full = [r for r in sub if r[3] >= args.tiers]
        part = [r for r in sub if r[3] < args.tiers]
        print("=" * 100)
        print("%s TIKIs: %d total | %d author the full %d-skin ladder on EVERY surface | %d fall short"
              % (kind, len(sub), len(full), args.tiers, len(part)))
        print("=" * 100)
        dist = defaultdict(int)
        for r in sub:
            dist[r[3]] += 1
        print("  worst-surface skin count distribution:")
        for k in sorted(dist):
            print("    %d skin(s): %4d TIKI(s)%s" % (k, dist[k], "   <-- can never show gore" if k < 2 else ""))
        show = sub if args.all else part
        if show:
            print("  %-62s %-10s %5s %5s  %s" % ("tiki", "source", "min", "max", "surfaces short"))
            for _k, path, src, worst, best, nsurf, short in show[:60]:
                s = ",".join(short[:4]) + ("..." if len(short) > 4 else "")
                print("  %-62s %-10s %5d %5d  %s" % (path[:62], src[:10], worst, best, s))
            if len(show) > 60:
                print("  ... and %d more" % (len(show) - 60))
        print()

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["kind", "tiki", "source", "min_skins", "max_skins", "num_surfaces", "short_surfaces"])
            for kind, path, src, worst, best, nsurf, short in rows:
                w.writerow([kind, path, src, worst, best, nsurf, ";".join(short)])
        print("wrote %s (%d rows)" % (args.csv, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

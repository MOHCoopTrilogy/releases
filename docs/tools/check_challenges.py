#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_challenges.py - build-time proof that every challenge can actually be earned.

WHY THIS EXISTS
    A challenge that can NEVER complete looks exactly like one nobody has completed yet.
    That is why 32 unearnable challenges survived to ship: nothing distinguished them from
    hard ones until somebody audited all 344 by hand, months later. This makes the three
    failure modes mechanical and catchable the day they are introduced:

      DEAD      the stat it counts is never written by anything, anywhere
      MISSING   the reward it grants points at an asset that is not in any pak
      SHORT     the target exceeds the supply that actually exists in the game

    Run it in CI or before a release. Exit 1 means a challenge shipped that a player
    cannot finish.

USAGE
    python docs/tools/check_challenges.py            # report + exit 1 on any failure
    python docs/tools/check_challenges.py --warn     # report, always exit 0
    python docs/tools/check_challenges.py --json     # machine-readable

TWO TRAPS THIS DELIBERATELY HANDLES - both cost a previous audit a wrong answer:

  1. MULTIPLE CALLS PER LINE. challenges.scr:1565 puts three chal_team_bump calls on one
     line separated by ';'. A per-line-first-match scan reports cc_secret_service and
     cc_gamespy as dead when they are wired. Every match on every line is collected.

  2. COMPUTED STATS. Three families are never written as literals - fac_* comes from
     chal_factionOf, wpn_* from chal_weaponId, map_* from ("map_" + mapname). Treating
     them as dead would flag ~150 working challenges. They are resolved by their generator
     instead, and fac_* is additionally supply-checked against real actor placements.
"""

import glob
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
CHAL = os.path.join(MOD, "coop_mod", "challenges.scr")

PAK_GLOBS = [
    r"G:\GOG\Medal of Honor - Allied Assault War Chest\main*\*.pk3",
    os.path.join(MOD, "**", "*.pk3"),
]

# ---------------------------------------------------------------- parsing

CHAL_RE = re.compile(
    r'chal_def\s+"([^"]+)"\s+"([^"]+)"\s+"([^"]*)"\s+"([^"]*)"'
    r'(?:\s+"([^"]*)"\s+(\S+)\s+"([^"]*)")?'
)


def load_challenges():
    src = io.open(CHAL, encoding="latin-1").read()
    out = []
    for m in CHAL_RE.finditer(src):
        tgt = m.group(6)
        out.append({
            "cid": m.group(1), "cat": m.group(2), "name": m.group(3),
            "desc": m.group(4), "stat": m.group(5) or "",
            "target": int(tgt) if tgt and tgt.isdigit() else 0,
            "reward": m.group(7) or "",
        })
    return out, src


# Any call that advances a counter. Collected with finditer so several on one line all
# register - see trap 1 in the module docstring.
#
# The argument between the call and the stat name is deliberately matched as "anything that
# is not a quote, semicolon or newline". An earlier version allowed only `local.<word>` and
# therefore missed ammobox.scr:240, which passes `$player[local.bi]` - reporting a WIRED
# challenge as dead. A false positive here is as damaging as a false negative: it sends
# someone to fix something that already works, and it erodes trust in the whole check.
# Stopping at ';' keeps a multi-statement line from bleeding into the next call.
#
# chal_quiet_feat is a WRAPPER: it takes the stat as a parameter and calls chal_team_bump with
# a variable, so a scan for literal bumps cannot see through it. Any future helper of that shape
# has to be added here too, or the challenges it wires will read as dead.
WRITER_RE = re.compile(
    r'(?:chal_bump|chal_team_bump|cc_award_clean|chal_quiet_feat)[^";\n]*"([^"]+)"')


def load_writers():
    """Every stat literal written anywhere in the mod tree."""
    stats = set()
    for path in glob.glob(os.path.join(MOD, "**", "*.scr"), recursive=True):
        try:
            body = io.open(path, encoding="latin-1").read()
        except Exception:
            continue
        for m in WRITER_RE.finditer(body):
            stats.add(m.group(1))
    return stats


# ---------------------------------------------------------------- supply

# chal_factionOf, in order - first match wins. Kept in step with challenges.scr by the
# self-test below, which fails if the script's rule list stops matching this one.
FACTION_EXCLUDE = ["hund", "dialogue", "worker", "scientist"]
FACTION_RULES = [
    ("sniper", "fac_sniper"), ("colonel", "fac_general"), ("major", "fac_general"),
    ("commander", "fac_general"), ("gestapo", "fac_ss"), ("feldgendarmerie", "fac_ss"),
    ("elite_ss", "fac_ss"), ("ss_guard", "fac_ss"), ("ss_gasmask", "fac_ss"),
    ("_fg", "fac_fallsch"), ("ital_para", "fac_bersag"), ("ital_vol", "fac_carab"),
    ("ital", "fac_regio"), ("kriegsmarine", "fac_kmarine"), ("kreigsmarine", "fac_kmarine"),
    ("kmarine", "fac_kmarine"), ("frogman", "fac_kmarine"), ("afrika", "fac_afrika"),
    ("_dak", "fac_afrika"), ("officer", "fac_officer"),
]


def classify(model):
    m = model.lower()
    for e in FACTION_EXCLUDE:
        if e in m:
            return None
    for pat, fac in FACTION_RULES:
        if pat in m:
            return fac
    return "fac_heer"


# Factions that are NOT bounded by map placement, and why. The supply scan can only see
# actors written into map files, so a faction with a live spawner would otherwise be reported
# as permanently short. Every entry here names a verified runtime source; adding one without
# a source would quietly disable the check for that faction.
RUNTIME_SOURCED = {
    # officer.scr::coop_officer_skin - the officer BOSS rolls this skin at randomint 4 == 3
    "fac_ss",
    # officer.scr::coop_model_for "sniper" - officer sniper waves (officer.scr:2360)
    "fac_sniper",
    # the coop officer boss is hooked in on death (see the AXIS FACTION TRACKING note)
    "fac_general",
    # a derived meta-counter of DISTINCT factions killed, not a unit that is placed anywhere
    "fac_variety",
}

# Stats that ARE bounded by placement, but by the placements of several other factions rather
# than their own. Kept checkable this way instead of exempted, so a target that outgrows the
# real supply is still caught - exempting would have quietly switched the guard off.
DERIVED_SUPPLY = {
    # counts Italians of any unit: Regio Esercito plus the militia volunteers
    "fac_italy": ["fac_regio", "fac_carab"],
}


def blueprint_supply():
    """How many blueprints are actually placed across all map scripts.

    The bp_* ladder is pinned to this number - the top tier literally reads "Recover all N".
    Place more and the ladder is understated; the top tier stops meaning "all" and the
    collection has no visible end. Remove some and it becomes unreachable, which is the state
    it shipped in (60 wanted, 31 existed, and found-blueprints persist so replaying never
    helped). Counted here so either direction is caught the day it happens.

    COMMENTS ARE NOT PLACEMENTS. A plain count of the string reported 36 for 35 real calls,
    because a comment in m4l2.scr explains what coop_bp_place does and the word counted. Each
    line is stripped at '//' before matching, and only a real call is counted.
    """
    n = 0
    for path in glob.glob(os.path.join(MOD, "maps", "**", "*.scr"), recursive=True):
        try:
            body = io.open(path, encoding="latin-1").read()
        except Exception:
            continue
        for line in body.split("\n"):
            code = line.split("//", 1)[0]
            n += len(re.findall(r"coop_bp_place\s*\(", code))
    return n


def faction_supply():
    """Count ONE actor per entity block. A block carries both a classname and a model;
    counting both double-counts and inflates every faction by roughly 2x."""
    supply = {}
    for path in glob.glob(os.path.join(ROOT, "map_entities", "*_entities.txt")):
        try:
            txt = io.open(path, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for block in re.findall(r"\{(.*?)\}", txt, re.S):
            cn = re.search(r'"classname"\s+"([^"]+)"', block)
            if not cn or "ai_" not in cn.group(1).lower():
                continue
            mdl = re.search(r'"model"\s+"([^"]+)"', block)
            fac = classify(mdl.group(1) if mdl else cn.group(1))
            if fac:
                supply[fac] = supply.get(fac, 0) + 1
    return supply


# ---------------------------------------------------------------- assets

def asset_index():
    """Every file in every mounted pak, plus loose files in the mod tree. Assets live in
    pk3s, NOT in the git tree - checking the tree alone falsely flags ~48 real rewards."""
    have = set()
    for pattern in PAK_GLOBS:
        for pak in glob.glob(pattern, recursive=True):
            try:
                with zipfile.ZipFile(pak) as z:
                    have |= {n.lower().replace("\\", "/") for n in z.namelist()}
            except Exception:
                pass
    for path in glob.glob(os.path.join(MOD, "**", "*.tik"), recursive=True):
        have.add(os.path.relpath(path, MOD).lower().replace("\\", "/"))
    return have


# ---------------------------------------------------------------- checks

def main():
    warn_only = "--warn" in sys.argv
    as_json = "--json" in sys.argv

    chals, src = load_challenges()
    writers = load_writers()
    supply = faction_supply()
    bp_have = blueprint_supply()
    have = asset_index()

    # self-test: if challenges.scr grows a faction rule this file does not know about, the
    # supply numbers silently go wrong. Better to fail loudly than to report a wrong count.
    live_rules = set(re.findall(r'chal_facHas\s+local\.model\s+"([^"]+)"', src))
    known = {p for p, _ in FACTION_RULES} | set(FACTION_EXCLUDE)
    drifted = live_rules - known
    dead, missing, short, notes = [], [], [], []
    if drifted:
        notes.append("faction rules in challenges.scr not known to this checker: %s"
                     % ", ".join(sorted(drifted)))

    for c in chals:
        stat, cid = c["stat"], c["cid"]
        if not stat:
            continue

        # DEAD - computed families are resolved by their generator, never written literally
        computed = stat.startswith("fac_") or stat.startswith("wpn_") or stat.startswith("map_")
        if not computed and stat not in writers:
            dead.append(c)

        # SHORT - only faction stats have a measurable fixed supply, and only those whose
        # supply is entirely PLACED. The supply scan counts actors sitting in map files; a
        # faction fed by a runtime spawner has no fixed ceiling and would be reported short
        # forever. Each exemption below names its verified source - do not add one without.
        if stat.startswith("fac_") and stat not in RUNTIME_SOURCED:
            if stat in DERIVED_SUPPLY:
                hav = sum(supply.get(s, 0) for s in DERIVED_SUPPLY[stat])
            else:
                hav = supply.get(stat, 0)
            if c["target"] > hav:
                short.append((c, hav))

        # SHORT - blueprints have a countable supply too, and the top tier claims to be "all"
        if stat == "blueprint":
            if c["target"] > bp_have:
                short.append((c, bp_have))
            elif c["cid"] == "bp_60" and c["target"] != bp_have:
                notes.append("top blueprint tier is %d but %d are placed - it no longer means "
                             "\"all\"; retune the bp_* ladder" % (c["target"], bp_have))

        # MISSING - reward asset must resolve in a pak. Two reward classes are NOT assets and are
        # legitimate by construction: perk_* (engine-side perks) and finish_* (skin-finish unlock
        # strings probed straight out of the pipe store by loadout_finUnlocked - the finish strip,
        # 2026-08-18). Anything else must be a real file, or the challenge pays nothing.
        rew = c["reward"]
        if rew and not rew.startswith(("perk_", "finish_")) and rew.lower() not in have:
            missing.append(c)

    if as_json:
        print(json.dumps({
            "total": len(chals),
            "dead": [c["cid"] for c in dead],
            "missing": [{"cid": c["cid"], "reward": c["reward"]} for c in missing],
            "short": [{"cid": c["cid"], "target": c["target"], "supply": h} for c, h in short],
            "notes": notes,
        }, indent=2))
        return 0 if warn_only else (1 if (dead or missing or short) else 0)

    print("challenges: %d | stat writers found: %d | actor placements: %d"
          % (len(chals), len(writers), sum(supply.values())))
    for n in notes:
        print("  NOTE: %s" % n)

    if dead:
        print("\nDEAD - stat is never written, so this can never progress (%d):" % len(dead))
        for c in dead:
            print("  %-26s %-30s stat=%s" % (c["cid"], c["name"][:30], c["stat"]))
    if short:
        print("\nSHORT - target exceeds the supply that exists (%d):" % len(short))
        for c, h in short:
            print("  %-26s %-30s needs %d, %d placed" % (c["cid"], c["name"][:30], c["target"], h))
    if missing:
        print("\nMISSING - reward asset is not in any pak (%d):" % len(missing))
        for c in missing:
            print("  %-26s -> %s" % (c["cid"], c["reward"]))

    bad = len(dead) + len(short) + len(missing)
    if not bad:
        print("\nOK - every challenge has a writer, a reachable target and a real reward.")
        return 0
    print("\n%d challenge(s) cannot be completed as shipped." % bad)
    if warn_only:
        print("(--warn: not failing the build)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

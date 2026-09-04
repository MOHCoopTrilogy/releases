#!/usr/bin/env python
"""
check_anim_dwell.py - find `anim X` followed by a `wait` LONGER than X actually lasts.

WHY THIS EXISTS
    The user reported, repeatedly and across many sessions, allied actors "just standing" on Omaha -
    including men who were supposed to be lying injured. The cause is not a missing or misspelled
    animation (check_map_anims.py already gates that); it is a TIMING mismatch:

        self anim rifle_pain_flooridle      <- a ONE-SHOT lasting 2.70 s
        wait ( 2.8 + ( randomfloat 4 ) )    <- up to 6.8 s

    A one-shot fires ANIMDONE and the actor falls back to its idle, which for a standing human is
    STANDING. So the man lies down for 2.7 s and then stands in the open for up to another 4 s,
    wounded, under machine-gun fire. Every screenshot of "a guy just standing there" is one of these
    caught in its dead time. The animation was correct, reachable and playing; the DWELL was wrong.

    LOOPING anims are exempt - they hold the pose for as long as you wait, which is the whole point.

BLIND SPOT THIS ALSO CLOSES
    check_map_anims.py matches `anim <literal>` only, so it never saw the concatenated form this file
    uses for weapon-group variants:  anim ( local.wg + "_pain_crawl" ).  Those resolve to TWO real
    aliases (rifle_* and unarmed_*) which can differ in BOTH duration and loop flag - and on this map
    they do: unarmed_pain_flooridle loops, rifle_pain_flooridle does not. Checked here for every
    group the calling code can supply.

Exit 1 if any dwell overruns a one-shot.
"""
import io, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_map_anims as C

MODELS = ["models/human/dday_29th_private.tik", "models/human/dday_ranger_private.tik",
          "models/human/dday_engineer.tik", "models/human/dday_ranger_medic.tik",
          "models/human/dday_29th_private_patient.tik"]

# the groups `local.wg` can hold - see coop_beachBehave
WGROUPS = ["rifle", "unarmed"]


def num(tok):
    try:
        return float(tok)
    except ValueError:
        return None


def wait_upper_bound(expr):
    """Largest value this wait expression can take. `( 2.8 + ( randomfloat 4 ) )` -> 6.8"""
    e = expr.strip()
    tot, sawnum = 0.0, False
    for m in re.finditer(r"randomfloat\s+([0-9.]+)", e):
        tot += float(m.group(1)); sawnum = True
    for m in re.finditer(r"randomint\s+([0-9.]+)", e):
        tot += float(m.group(1)) - 1; sawnum = True
    stripped = re.sub(r"random(float|int)\s+[0-9.]+", "", e)
    for m in re.finditer(r"(?<![\w.])([0-9]+\.?[0-9]*)(?![\w.])", stripped):
        tot += float(m.group(1)); sawnum = True
    return tot if sawnum else None


def anim_names(bare):
    """Every alias an `anim ...` statement on this line can resolve to."""
    out = []
    m = re.search(r'\banim\s*\(\s*local\.\w+\s*\+\s*"([^"]+)"\s*\)', bare)
    if m:
        return [g + m.group(1) for g in WGROUPS]
    m = re.search(r'\banim\s+"?([A-Za-z_][A-Za-z0-9_]*)"?(?![\w."])', bare)
    if m and bare[m.end():m.end() + 1] != "." and m.group(1).lower() not in C.NOT_ANIMS:
        return [m.group(1).lower()]
    return out


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m3l1a"
    script = os.path.join(C.MOD, "maps", mapname, "coopified.scr")
    aliases = {}
    for m in MODELS:
        aliases.update(C.collect_aliases(m, mapname))

    src = io.open(script, encoding="latin-1").read().splitlines()
    bad, unknown, ok = [], [], 0

    for i, line in enumerate(src):
        names = anim_names(line.split("//")[0])
        if not names:
            continue
        # the next `wait` within 3 lines, provided nothing else intervenes that would consume the anim
        w, wline = None, None
        for j in range(i + 1, min(i + 4, len(src))):
            nxt = src[j].split("//")[0]
            if "waittill" in nxt:
                break                       # `waittill animdone` is the correct pattern, not a dwell
            mw = re.search(r"^\s*wait\s+(.+?)\s*$", nxt)
            if mw:
                w, wline = wait_upper_bound(mw.group(1)), j + 1
                break
            if re.search(r"\banim\b|\bend\b|\bthread\b", nxt):
                break
        if w is None:
            continue

        for nm in names:
            if nm not in aliases:
                unknown.append((i + 1, nm))
                continue
            infos = [x for x in (C.skc_info(p) for p in aliases[nm]) if x]
            if not infos:
                continue
            if any(x["loop"] for x in infos):
                ok += 1
                continue
            dur = max(x["dur"] for x in infos)
            if w > dur + 0.25:
                bad.append((i + 1, nm, dur, w, wline, round(w - dur, 2)))
            else:
                ok += 1

    print("  %d anim/wait pairs checked against real SKC durations" % (ok + len(bad)))
    if unknown:
        print("\n  NOT REACHABLE on %s (a weapon-group variant that does not exist):" % mapname)
        for ln, nm in unknown:
            print("    coopified.scr:%-6d %s" % (ln, nm))
    if bad:
        print("\n  ONE-SHOT ANIM LEFT STANDING - the actor reverts to idle for the excess:")
        for ln, nm, dur, w, wl, over in sorted(bad, key=lambda r: -r[5]):
            print("    coopified.scr:%-6d %-34s plays %5.2fs, waits up to %5.2fs (line %d)"
                  "  -> STANDING up to %.2fs" % (ln, nm, dur, w, wl, over))
    if not bad and not unknown:
        print("\n  OK - no animation is left standing by an over-long wait.")
    return 1 if (bad or unknown) else 0


if __name__ == "__main__":
    sys.exit(main())

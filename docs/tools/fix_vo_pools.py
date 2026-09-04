#!/usr/bin/env python
"""
fix_vo_pools.py - turn same-name alias "pools" into REAL numbered pools.

THE BUG
    [user 2026-09-02] "The allies STILL are constantly saying He's hit... its almost like thats the
    only line they have to say, there is zero variety its just Hes hit constantly. Its so obnoxious."

    coop_aivoice.scr and coop_chatter.scr build their voice pools by declaring many aliases that all
    share ONE name, and coop_aivoice.scr states the assumption in its own comment:

        // ONE NAME, MANY LINES = a random pool. Alias_ListFindRandomRange picks among same-name
        // entries, which is exactly the coop_av_us_mandown shape immediately above

    That is false. qcommon/alias.c:323-332, in Alias_ListAddNode:

        for (node = list->data_list; node != NULL; node = node->next) {
            if (!strcmp(node->alias_name, alias)) {
                Com_DPrintf("DUPLICATE ALIASES: %s and %s\\n", node->alias_name, alias);
                return qtrue;                       <-- returns WITHOUT adding
            }
        }

    The FIRST declaration of a name registers and every later one is discarded. So each pool is one
    line. The user's own console log carries the proof - "DUPLICATE ALIASES: snd_crate_woodsm2 and
    snd_crate_woodsm2" - which nobody had connected to the voice repetition.

    A real random pool is name + DIGITS: Alias_ListFindRandomRange scans the SORTED alias list for a
    contiguous run sharing a prefix, which is why `playsound warn_player_cover` legitimately picks
    from warn_player_cover01..05. So the fix is to number the members and keep playing the base name.

WHAT IT DOES NOT TOUCH
    ubersound.scr and uberdialog.scr also contain thousands of same-name aliases, and those are NOT
    this bug: they are retail's per-map variants, identical names carrying DIFFERENT `maps` fields, of
    which exactly one is admitted per map (bLoadForMap, scriptmaster.cpp:432). Renaming those would
    turn one correct line into several wrong ones. This tool therefore refuses to renumber any group
    whose members disagree about their maps field, and only runs on the two coop-authored files.

USAGE
    python docs/tools/fix_vo_pools.py [--check]
"""
import io, os, re, sys

MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
FILES = ["coop_aivoice.scr", "coop_chatter.scr"]

ALIAS = re.compile(r'^(\s*)(alias(?:cache)?)\s+(\S+)(\s+.*)$', re.I)
MAPSF = re.compile(r'maps\s+"([^"]*)"', re.I)


def process(path, apply, seen=None):
    if seen is None:
        seen = {}
    raw = open(path, "rb").read()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    text = raw.decode("latin-1").replace("\r\n", "\n")
    lines = text.split("\n")

    # pass 1 - group by name, and record each member's maps field
    order = {}
    for i, ln in enumerate(lines):
        m = ALIAS.match(ln)
        if not m:
            continue
        name = m.group(3)
        stem = name
        while stem and stem[-1].isdigit():
            stem = stem[:-1]
        mf = MAPSF.search(m.group(4))
        order.setdefault(stem.lower(), []).append((i, name, mf.group(1) if mf else None))

    renamed = skipped = 0
    for key, members in order.items():
        if len(members) < 2:
            continue
        # a group whose members disagree about maps is a per-map variant set, not a pool
        maps = set(x[2] for x in members)
        if len(maps) > 1:
            skipped += 1
            continue
        # strip any existing numeric suffix so a re-run renumbers rather than stacking digits
        base = members[0][1]
        while base and base[-1].isdigit():
            base = base[:-1]
        if not base:
            continue
        start = seen.get(base.lower(), 0)
        for n, (i, name, _mf) in enumerate(members, start=1):
            m = ALIAS.match(lines[i])
            lines[i] = "%s%s %s%d%s" % (m.group(1), m.group(2), base, start + n, m.group(4))
            renamed += 1
        seen[base.lower()] = start + len(members)

    out = "\n".join(lines)
    changed = out != text
    if apply and changed:
        open(path, "wb").write(out.encode("latin-1").replace(b"\n", nl))
    return renamed, skipped, changed


def main():
    check = "--check" in sys.argv
    total_r = total_s = 0
    stale = False
    # NUMBERED CONTINUOUSLY ACROSS BOTH FILES, not per file. coop_aivoice.scr and coop_chatter.scr
    # independently build pools under the SAME base names (40 collisions, all with different wavs),
    # so numbering each file from 1 produced a fresh set of duplicates for the engine to discard -
    # 1,256 of them in a single boot, which is how this was caught. A shared counter makes the two
    # files one continuous pool per name, which is also what they should have been all along: the
    # chatter lines and the aivoice lines are alternatives for the same situation.
    seen = {}
    for f in FILES:
        p = os.path.join(MOD, "ubersound", f)
        if not os.path.exists(p):
            print("  %s: not found" % f)
            continue
        r, s, changed = process(p, not check, seen)
        total_r += r
        total_s += s
        if check and changed:
            stale = True
        print("  %-22s %4d aliases numbered into pools, %d map-gated groups left alone%s"
              % (f, r, s, "  [STALE]" if (check and changed) else ""))
    print("  %d voice lines are now reachable that the engine was discarding" % total_r)
    if check and stale:
        print("  STALE - run without --check")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

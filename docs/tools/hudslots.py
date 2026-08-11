#!/usr/bin/env python3
"""
hudslots.py - sweep every ihuddraw_* call in the mod tree and report HUD slot ownership.

WHY THIS EXISTS (bug-1680, 2026-08-10)
    _research/hud_slot_map.md was hand-maintained and had drifted badly: it still listed
    cover.scr at 40-44 and ammobox at 45-47 long after both moved into the fade-exempt band,
    it offered 141-149 as a free reserve when only 149 was left, and it showed no conflict at
    all for objectives.scr, which quietly owns 135-142 and collides with the DBNO revive
    channel and the XP micro popup. A feature that trusted the table would have claimed an
    occupied slot. Hand-maintained inventories rot; this one is swept from the code instead.

    Slots BELOW 100 fade with the HUD when the player is calm (cg_drawtools.cpp:651-653), so
    any prompt a standing-still player must read has to be >= 100. That is why the >= 100 band
    is congested and why knowing what is genuinely free matters.

THE PART THAT MATTERS MOST
    A literal-slot grep is NOT sufficient and that is exactly how bug-1680 hid: several
    features compute the slot (`local.slot = 136 + local.line`). This tool therefore reports
    computed sites SEPARATELY and loudly rather than silently omitting them - absence from the
    literal table is not evidence a slot is free.

USAGE
    python docs/tools/hudslots.py                 # full report
    python docs/tools/hudslots.py 100 255         # restrict to a band
    python docs/tools/hudslots.py --free          # just the genuinely-unclaimed literals
"""

import collections
import glob
import os
import re
import sys

MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hzm-mohaa-coop-mod")
MOD = os.path.normpath(MOD)

MAX_HUDDRAW_ELEMENTS = 256  # qcommon/q_shared.h:1788
FADE_FLOOR = 100            # slots below this are multiplied by s_hudFadeAlpha when calm

CALL = re.compile(r"ihuddraw_(\w+)\s+(\S+)\s+(\S+)")


def sweep():
    literal = collections.defaultdict(set)
    computed = []
    for path in glob.glob(os.path.join(MOD, "**", "*.scr"), recursive=True):
        rel = os.path.relpath(path, MOD).replace(os.sep, "/")
        with open(path, "rb") as fh:
            raw = fh.read()
        for n, line in enumerate(raw.split(b"\n"), 1):
            text = line.decode("latin-1")
            if text.strip().startswith("//"):
                continue
            for m in CALL.finditer(text):
                slot = m.group(3)
                if slot.isdigit():
                    literal[int(slot)].add(rel)
                else:
                    computed.append((rel, n, slot, text.strip()[:100]))
    return literal, computed


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only_free = "--free" in sys.argv
    lo, hi = (int(args[0]), int(args[1])) if len(args) >= 2 else (0, MAX_HUDDRAW_ELEMENTS - 1)

    literal, computed = sweep()
    free = [s for s in range(lo, hi + 1) if s not in literal]

    if only_free:
        print(" ".join(str(s) for s in free))
        return 0

    print("HUD slot sweep - %s" % MOD)
    print("MAX_HUDDRAW_ELEMENTS = %d, fade-exempt from %d up\n" % (MAX_HUDDRAW_ELEMENTS, FADE_FLOOR))

    print("== LITERAL slot -> owner(s) ==")
    for slot in sorted(literal):
        if lo <= slot <= hi:
            mark = "     " if slot >= FADE_FLOOR else "FADE "
            print("%s%4d  %s" % (mark, slot, ", ".join(sorted(literal[slot]))))

    print("\n== COMPUTED slots - resolve these BY HAND before trusting the free list ==")
    if not computed:
        print("  (none)")
    for rel, n, expr, text in computed:
        print("  %s:%d  slot=%s   %s" % (rel, n, expr, text))

    print("\n== literal-unclaimed in %d-%d ==" % (lo, hi))
    print("  %s" % (", ".join(str(s) for s in free) if free else "(none)"))
    print("\n  NOT the same as 'free': a computed base above may cover some of these.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

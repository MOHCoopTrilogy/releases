#!/usr/bin/env python3
"""Harvest per-map scripted PATH BLOCKERS from a bot_blocklog soak (^~^~^ BOTBLOCK lines), to drive
auto-generated push_gates handlers (user 2026-09-22: mechanize the door/fence/debris fix across all maps).

Keeps only NAMED, scriptable blockers a `$targetname notsolid` can clear:
  * drops world=1  (a real navmesh GAP - not a scriptable object; needs nav regen, flagged separately)
  * drops class=Player  (bot-on-bot congestion, not an object)
  * drops empty targetname (can't be selected by $name)
  * drops Vehicle* (tanks/turrets - handled by MPARENAFIX carve + the bot lookahead; we WANT them solid)
Emits docs/tools/push_blockers.json  { map: [ {tn, class, hits}, ... ] }  and prints a review table.

  python docs/tools/bot_soak_blockers.py C:\\mohaa-coop-dev\\_soak_sweep
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

MIN_HITS = 8  # ignore one-off/noise blockers

LINE = re.compile(
    r'BOTBLOCK .*?\bworld=(\d).*?\bclass=(\S+).*?\bsolid=(-?\d+).*?\bmodel=(\S*).*?\btn=(\S*)'
)


def harvest_map(path):
    counts = defaultdict(int)
    cls_of = {}
    nav_gap = 0
    congestion = 0
    for line in open(path, 'r', encoding='latin-1', errors='replace'):
        if 'BOTBLOCK' not in line:
            continue
        m = LINE.search(line)
        if not m:
            continue
        world, cls, solid, model, tn = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        if world == '1':
            nav_gap += 1
            continue
        if cls == 'Player':
            congestion += 1
            continue
        if cls.startswith('Vehicle'):
            continue
        if not tn or tn == '':
            continue
        counts[tn] += 1
        cls_of[tn] = cls
    blockers = [
        {'tn': tn, 'class': cls_of[tn], 'hits': n}
        for tn, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= MIN_HITS
    ]
    return blockers, nav_gap, congestion


def main(sweepdir):
    logs = sorted(glob.glob(os.path.join(sweepdir, '*.log')))
    if not logs:
        print('no *.log in', sweepdir); return
    result = {}
    print('%-7s %6s %6s  %s' % ('MAP', 'navGap', 'congst', 'named scriptable blockers -> notsolid'))
    print('-' * 100)
    for p in logs:
        name = os.path.splitext(os.path.basename(p))[0]
        blockers, nav, cong = harvest_map(p)
        result[name] = blockers
        desc = ', '.join('%s(%s,%d)' % (b['tn'], b['class'], b['hits']) for b in blockers) or '(none)'
        print('%-7s %6d %6d  %s' % (name, nav, cong, desc[:90]))
    print('-' * 100)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'push_blockers.json')
    # [bug-2830/2834] MERGE, never overwrite. A blocker that is already fixed stops producing BOTBLOCK hits, and
    # user-review entries (hand-added, "manual": ...) never produce any - an overwrite silently re-opened them all.
    # Union by targetname per map; keep the larger hit count; never drop an existing entry.
    merged = json.load(open(out)) if os.path.exists(out) else {}
    for m, blockers in result.items():
        cur = merged.setdefault(m, [])
        idx = {b['tn']: b for b in cur}
        for b in blockers:
            if b['tn'] in idx:
                idx[b['tn']]['hits'] = max(idx[b['tn']].get('hits', 0), b['hits'])
            else:
                cur.append(b)
    json.dump(merged, open(out, 'w'), indent=2)
    nmaps = sum(1 for v in merged.values() if v)
    print('merged into %s  (%d maps with named blockers)' % (out, nmaps))
    print('note: navGap = world hits (nav regen job), congst = Player hits (bot-spacing job) - neither is a gate fix')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'C:\mohaa-coop-dev\_soak_sweep')

#!/usr/bin/env python3
"""
Read the coop probe bus out of a qconsole log and answer questions about a session.

[user 2026-08-22] "We need it to be able to understand extreme context of every situation."

THE HALF THAT MATTERS. Emitting records is the easy half; the reason the old tracker was
useless is that nobody could turn 1.3 MB of log into an answer. This does that:

    probe_read.py <log>                  session overview - what ran, what changed
    probe_read.py <log> --actors         one row per actor: final state + what happened to it
    probe_read.py <log> --ent 1042       full timeline for one entity
    probe_read.py <log> --surrendered    every actor ever flagged surrendered, and when
    probe_read.py <log> --aggro          when actors acquired enemies, and which
    probe_read.py <log> --diff           census-to-census STATE CHANGES only (the money view)
    probe_read.py <log> --events         every non-census record, chronological

--diff is the one to reach for. A census is a wall of text; the CHANGES between two censuses
are usually three lines, and they are the three lines that explain the bug.

Falls back to the older aggregate probes (AIBEHAV etc) so an existing log is still readable,
but flags them as identity-free.
"""
import io
import os
import re
import sys
import collections

PRB = re.compile(r'\^~\^~\^ PRB (\S+) (.*)$')
KV = re.compile(r'(\w+)=(\S*)')
# older identity-free probes, so a pre-probe-bus log still yields something
LEGACY = re.compile(r'\^~\^~\^ ([A-Z][A-Z0-9]*) (.*)$')


def parse(path):
    recs, legacy = [], []
    with io.open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            m = PRB.search(line)
            if m:
                d = dict(KV.findall(m.group(2)))
                d['_ev'] = m.group(1)
                recs.append(d)
                continue
            m = LEGACY.search(line)
            if m and m.group(1) != 'PRB':
                legacy.append((m.group(1), m.group(2).strip()))
    return recs, legacy


def _int(d, k, dflt=0):
    try:
        return int(d.get(k, dflt))
    except (TypeError, ValueError):
        return dflt


# fields whose change between two censuses is worth a line of output
WATCH = ['tm', 'hp', 'aiDis', 'noIdle', 'tbias', 'scene', 'surr', 'conv',
         'pers', 'wp', 'wg', 'pos', 'atk', 'hasEnemy']


def overview(recs, legacy):
    if not recs:
        print("  no PRB records - coop_probe was 0 for this session.")
        if legacy:
            kinds = collections.Counter(k for k, _ in legacy)
            print("  %d legacy aggregate probe lines (NO entity identity - cannot answer"
                  " 'which actor'):" % len(legacy))
            for k, n in kinds.most_common(12):
                print("      %-14s %d" % (k, n))
            print("\n  Set `coop_probe 129` (actor+census) and replay to get identity.")
        return
    kinds = collections.Counter(r['_ev'] for r in recs)
    ents = {r['ent'] for r in recs if r.get('ent', 'NULL') != 'NULL'}
    ts = [_int(r, 't', -1) for r in recs if 't' in r]
    print("  records %d | distinct entities %d | span %ds-%ds"
          % (len(recs), len(ents), min(ts) if ts else 0, max(ts) if ts else 0))
    print()
    for k, n in kinds.most_common():
        print("    %-22s %d" % (k, n))
    mask = [r for r in recs if r['_ev'] == 'probe.mask']
    if mask:
        m = mask[-1]
        on = [c for c in ('actor', 'anim', 'weapon', 'sound', 'script', 'player',
                          'feature', 'census') if m.get(c) == '1']
        print("\n  channels on: %s" % (', '.join(on) or 'none'))


def censuses(recs):
    """Group actor.snap records into ordered census frames keyed by timestamp."""
    frames = collections.OrderedDict()
    for r in recs:
        if r['_ev'] != 'actor.snap':
            continue
        frames.setdefault(_int(r, 't'), {})[r.get('ent')] = r
    return frames


def show_diff(recs):
    frames = censuses(recs)
    if len(frames) < 2:
        print("  need >=2 census frames; enable census (bit 128) and let it run.")
        return
    times = list(frames)
    prev = frames[times[0]]
    print("  baseline t=%ds: %d actors" % (times[0], len(prev)))
    for t in times[1:]:
        cur = frames[t]
        lines = []
        for ent, r in cur.items():
            if ent not in prev:
                lines.append("    + APPEARED  ent=%-5s tn=%-22s tm=%s" %
                             (ent, r.get('tn'), r.get('tm')))
                continue
            o = prev[ent]
            ch = ["%s %s->%s" % (f, o.get(f), r.get(f))
                  for f in WATCH if o.get(f) != r.get(f)]
            if ch:
                lines.append("    ~ ent=%-5s tn=%-22s %s" % (ent, r.get('tn'), '  '.join(ch)))
        for ent, o in prev.items():
            if ent not in cur:
                lines.append("    - GONE      ent=%-5s tn=%-22s tm=%s hp=%s" %
                             (ent, o.get('tn'), o.get('tm'), o.get('hp')))
        if lines:
            print("\n  t=%ds  (%d actors)" % (t, len(cur)))
            for l in lines:
                print(l)
        prev = cur


def show_actors(recs):
    frames = censuses(recs)
    if not frames:
        print("  no census frames - enable bit 128.")
        return
    last = frames[list(frames)[-1]]
    first_seen, ever_surr, ever_dis = {}, set(), set()
    for t, fr in frames.items():
        for ent, r in fr.items():
            first_seen.setdefault(ent, t)
            if r.get('surr') == '1':
                ever_surr.add(ent)
            if r.get('aiDis') == '1':
                ever_dis.add(ent)
    print("  %-6s %-24s %-8s %-6s %-5s %-5s %-6s %-4s %s"
          % ("ent", "targetname", "team", "hp", "surr", "aiDis", "enemy", "t0", "personality"))
    print("  " + "-" * 96)
    for ent, r in sorted(last.items(), key=lambda kv: _int(kv[1], 'ent')):
        print("  %-6s %-24s %-8s %-6s %-5s %-5s %-6s %-4s %s"
              % (ent, (r.get('tn') or '-')[:24], r.get('tm'), r.get('hp'),
                 '*' if ent in ever_surr else r.get('surr'),
                 '*' if ent in ever_dis else r.get('aiDis'),
                 r.get('hasEnemy'), first_seen.get(ent), r.get('pers')))
    print("\n  * = true at some point, even if not now.")
    print("  ever surrendered: %d   ever map-disabled: %d   present at end: %d"
          % (len(ever_surr), len(ever_dis), len(last)))


def show_ent(recs, ent):
    rows = [r for r in recs if r.get('ent') == str(ent)]
    if not rows:
        print("  no records for ent=%s" % ent)
        return
    print("  timeline for ent=%s (%d records)" % (ent, len(rows)))
    prev = {}
    for r in rows:
        ch = [f for f in WATCH if f in r and prev.get(f) != r.get(f)]
        detail = '  '.join("%s=%s" % (f, r[f]) for f in ch) if prev else \
                 '  '.join("%s=%s" % (f, r[f]) for f in WATCH if f in r)
        print("    t=%-5s %-16s %s" % (r.get('t'), r['_ev'], detail or '(no change)'))
        prev = {f: r.get(f) for f in WATCH if f in r}


def show_surrendered(recs):
    frames = censuses(recs)
    hits = collections.OrderedDict()
    for t, fr in frames.items():
        for ent, r in fr.items():
            if r.get('surr') == '1' and ent not in hits:
                hits[ent] = (t, r)
    ev = [r for r in recs if 'surrender' in r['_ev'] or 'convert' in r['_ev']]
    if not hits and not ev:
        print("  nothing was ever flagged surrendered.")
        return
    print("  %d actor(s) flagged surrendered:" % len(hits))
    for ent, (t, r) in hits.items():
        print("    ent=%-6s tn=%-22s tm=%-8s first seen surrendered t=%ds  pers=%s"
              % (ent, r.get('tn'), r.get('tm'), t, r.get('pers')))
    if ev:
        print("\n  surrender/convert events:")
        for r in ev:
            print("    t=%-5s %-20s ent=%-6s tn=%s" %
                  (r.get('t'), r['_ev'], r.get('ent'), r.get('tn')))


def show_aggro(recs):
    """Who lit up first, and - the question the old tracker could never answer - who did
    they pick? A german's .enemy may be a Player or another Actor. "12 germans engaging"
    means either twelve enemies shooting at the players or twelve enemies fighting the
    map's own allied cast, and those two have opposite fixes."""
    frames = censuses(recs)
    if not frames:
        print("  no census frames - enable bit 128.")
        return
    state, acquired = {}, []
    for t, fr in frames.items():
        for ent, r in fr.items():
            was, now = state.get(ent), r.get("hasEnemy")
            if now == "1" and was != "1":
                acquired.append((t, ent, r))
            state[ent] = now

    t0 = list(frames)[0]
    first = frames[t0]
    pre = [r for r in first.values() if r.get("hasEnemy") == "1"]
    print("  FIRST census t=%ss: %d of %d actors ALREADY had an enemy."
          % (t0, len(pre), len(first)))
    if pre:
        print("  (they aggroed before the first sample - lower coop_probeInterval)")
        for r in pre[:6]:
            print("      ent=%-6s tn=%-22s tm=%-8s -> foe %s/%s"
                  % (r.get("ent"), r.get("tn"), r.get("tm"),
                     r.get("foeCls"), r.get("foeTm")))

    if not acquired:
        print("")
        print("  no acquisition transitions captured.")
    else:
        print("")
        print("  ACQUISITION ORDER (who started it, and on whom):")
        print("  %-7s %-7s %-22s %-9s %-9s %-9s %s"
              % ("t", "ent", "targetname", "team", "role", "foeClass", "foeTeam"))
        print("  " + "-" * 86)
        for t, ent, r in acquired[:30]:
            print("  %-7s %-7s %-22s %-9s %-9s %-9s %s"
                  % (str(t) + "s", ent, (r.get("tn") or "-")[:22], r.get("tm"),
                     r.get("role"), r.get("foeCls"), r.get("foeTm")))

    tally = collections.Counter()
    for t, fr in frames.items():
        for r in fr.values():
            if r.get("hasEnemy") == "1":
                tally[r.get("foeCls", "-")] += 1
    if tally:
        tot = sum(tally.values())
        print("")
        print("  WHO ARE THEY FIGHTING (engaged samples, all censuses):")
        for cls, n in tally.most_common():
            print("      %-10s %5d  %5.1f%%" % (cls, n, 100.0 * n / tot))
        pl = tally.get("Player", 0)
        print("")
        if pl == 0:
            print("  VERDICT: NOT ONE engaged actor targeted a Player. This is the map's own")
            print("           cast fighting each other - an ally/scene-actor problem, NOT the")
            print("           players being detected.")
        elif pl == tot:
            print("  VERDICT: every engaged actor targeted a Player - they are detecting you,")
            print("           so look at what makes players targetable, not at the AI cast.")
        else:
            print("  VERDICT: MIXED - %.0f%% player-directed. Read the acquisition order:"
                  % (100.0 * pl / tot))
            print("           whoever acquired FIRST started the cascade.")

def show_events(recs):
    for r in recs:
        if r['_ev'] in ('actor.snap', 'probe.mask'):
            continue
        extra = '  '.join("%s=%s" % (k, v) for k, v in r.items()
                          if k not in ('_ev', 't', 'n'))
        print("  t=%-6s %-22s %s" % (r.get('t'), r['_ev'], extra))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    if not os.path.exists(path):
        print("  no such log: %s" % path)
        return 2
    recs, legacy = parse(path)
    mode = argv[2] if len(argv) > 2 else None
    if mode == '--actors':
        show_actors(recs)
    elif mode == '--diff':
        show_diff(recs)
    elif mode == '--ent':
        show_ent(recs, argv[3])
    elif mode == '--surrendered':
        show_surrendered(recs)
    elif mode == '--aggro':
        show_aggro(recs)
    elif mode == '--events':
        show_events(recs)
    else:
        overview(recs, legacy)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

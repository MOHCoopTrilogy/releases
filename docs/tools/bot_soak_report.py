#!/usr/bin/env python3
"""Before/after report for the push-map bot fixes (user 2026-09-22): compares a baseline soak dir against an
'after' soak dir and answers the three questions per map, for BOTH teams:
  1. spawn clean?  - %% of a team's stuck-time within 1500u of its own spawn (spawn-egress jam)
  2. not stuck?    - total stuck %% + worst stuck-episode seconds (does it self-resolve?)
  3. cross to the enemy side? - max fraction of the spawn->spawn distance the team's furthest bot reached

  python docs/tools/bot_soak_report.py <after_dir> [baseline_dir]
"""
import glob
import math
import os
import re
import sys
from collections import defaultdict

FIELD = re.compile(r'\b([a-z]+)=(-?\d+(?:\.\d+)?)')
NEAR = 1500.0
PROBE_S = 2


def parse(path):
    byent = defaultdict(list)
    first = {}
    for line in open(path, 'r', encoding='latin-1', errors='replace'):
        if 'BOTPROBE' not in line:
            continue
        kv = dict((k, float(v)) for k, v in FIELD.findall(line))
        if 'px' not in kv or 'e' not in kv:
            continue
        m = re.search(r'tm=([ax?])', line)
        kv['tm'] = m.group(1) if m else '?'
        e = int(kv['e'])
        if e not in first and kv.get('al', 1) >= 0.5:
            first[e] = (kv['tm'], (kv['px'], kv['py']))
        byent[e].append(kv)
    return byent, first


def team_metrics(byent, first):
    sp = {}
    for t in ('a', 'x'):
        pts = [p for tm, p in first.values() if tm == t]
        sp[t] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None
    sepd = math.hypot(sp['a'][0] - sp['x'][0], sp['a'][1] - sp['x'][1]) if sp['a'] and sp['x'] else 1.0
    out = {}
    for t in ('a', 'x'):
        tot = stuck = nearsp = 0
        maxep = 0
        maxreach = 0.0
        for e, S in byent.items():
            if not S or S[0]['tm'] != t:
                continue
            run = 0
            for s in S:
                if s.get('al', 1) < 0.5:
                    continue
                tot += 1
                if sp[t]:
                    r = math.hypot(s['px'] - sp[t][0], s['py'] - sp[t][1])
                    maxreach = max(maxreach, r)
                wants = abs(s.get('fm', 0)) > 20 or abs(s.get('rm', 0)) > 20
                if wants and s.get('spd', 0) < 12:
                    stuck += 1
                    run += 1
                    if sp[t] and math.hypot(s['px'] - sp[t][0], s['py'] - sp[t][1]) < NEAR:
                        nearsp += 1
                else:
                    maxep = max(maxep, run); run = 0
            maxep = max(maxep, run)
        out[t] = {
            'stuck_pct': round(100 * stuck / tot) if tot else 0,
            'near_pct': round(100 * nearsp / stuck) if stuck else 0,
            'maxep_s': maxep * PROBE_S,
            'reach_frac': round(maxreach / sepd, 2) if sepd > 1 else 0,
        }
    return out


def load(d):
    res = {}
    for p in sorted(glob.glob(os.path.join(d, '*.log'))):
        name = os.path.splitext(os.path.basename(p))[0]
        byent, first = parse(p)
        if byent:
            res[name] = team_metrics(byent, first)
    return res


def main(afterdir, basedir):
    A = load(afterdir)
    B = load(basedir) if basedir and os.path.isdir(basedir) else {}
    print('%-7s | %-26s | %-26s' % ('MAP', 'ALLIES  stuck / egress / reach', 'AXIS  stuck / egress / reach'))
    print('        | (arrow = baseline -> after; reach 1.0 = reached enemy spawn; egress = jam at own spawn)')
    print('-' * 90)
    def cell(t, mA, mB):
        a = mA[t]
        if mB:
            b = mB[t]
            return '%2d->%2d%% %2d->%2d%% %.1f->%.1f' % (
                b['stuck_pct'], a['stuck_pct'], b['near_pct'], a['near_pct'], b['reach_frac'], a['reach_frac'])
        return '%2d%%    %2d%%    %.1f    ' % (a['stuck_pct'], a['near_pct'], a['reach_frac'])
    for m in sorted(A):
        mB = B.get(m)
        print('%-7s | %-26s | %-26s' % (m, cell('a', A[m], mB), cell('x', A[m], mB)))
    print('-' * 90)
    # summary: how many maps now have BOTH teams reaching >=0.75 of the way across
    good = sum(1 for m in A if A[m]['a']['reach_frac'] >= 0.75 and A[m]['x']['reach_frac'] >= 0.75)
    print('%d/%d maps: BOTH teams reach >=75%% across' % (good, len(A)))


if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else r'C:\mohaa-coop-dev\_soak_final'
    b = sys.argv[2] if len(sys.argv) > 2 else r'C:\mohaa-coop-dev\mohaa-coop-dev_soak'
    main(a, b)

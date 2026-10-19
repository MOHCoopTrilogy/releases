#!/usr/bin/env python3
"""Classify every push map from a bot SOAK run into its AXIS failure mode, so we know which maps the m2l1
spawn-relocation recipe can fix versus which need a different lever (user 2026-09-22).

Discriminators (learned from m2l1 = fixable vs m5l1a = not):
  * PERSISTENCE - do axis snags self-resolve? episode <=8s everywhere => HEALTHY (leave alone).
  * NAV-BROKEN  - BOTH teams have long hangs => map geometry/nav, not a balance issue.
  * OBJECTIVE-PILE - axis stuck with tiny goal-distance (gd) => piling ON the objective; a spawn move just
                     relocates the pile. (m5l1a)
  * SPAWN-EGRESS  - axis jam is NEAR their own spawn with a LARGE gd => stuck trying to LEAVE toward a far
                    goal = a spawn cul-de-sac. THIS is what relocating the home spawn fixes. (m2l1)
  * EN-ROUTE      - persistent axis hang mid-route, not near spawn, not on the objective => needs the
                    catch-up assist, not spawns.

Only AUTHORED maps (in docs/tools/push_spawns.json) can be spawn-fixed by editing that file; BSP-derived push
maps get their spawns from gen_push_from_bsp.py and are marked (bsp).

  python docs/tools/bot_soak_classify.py C:\\mohaa-coop-dev\\mohaa-coop-dev_soak
"""
import glob
import json
import math
import os
import re
import sys
from collections import defaultdict

FIELD = re.compile(r'\b([a-z]+)=(-?\d+(?:\.\d+)?)')
NEAR = 1500.0
PROBE_S = 2  # ~seconds per BOTPROBE sample

try:
    AUTHORED = {s.get('map') for s in []}  # filled below
    _sp = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'push_spawns.json'), encoding='utf-8'))
    # push_spawns.json is a dict of map -> {spawns:[...]} OR a list; handle both
    if isinstance(_sp, dict):
        AUTHORED = set(_sp.keys())
    else:
        AUTHORED = set()
except Exception:
    AUTHORED = {'m1l2b', 'm2l1', 'm3l3', 'm4l1', 'm4l2', 'm5l1a', 'm5l1b'}


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


def team_stats(byent, first, team):
    xs = [p for tm, p in first.values() if tm == team]
    spawn = (sum(p[0] for p in xs) / len(xs), sum(p[1] for p in xs) / len(xs)) if xs else None
    stuck = []
    stuck_gd = []
    episodes = []
    for e, S in byent.items():
        if not S or S[0]['tm'] != team:
            continue
        run = 0
        for s in S:
            is_stuck = (abs(s.get('fm', 0)) > 20 or abs(s.get('rm', 0)) > 20) and s.get('spd', 0) < 12 and s.get('al', 1) >= 0.5
            if is_stuck:
                run += 1
                stuck.append((s['px'], s['py']))
                stuck_gd.append(s.get('gd', 0))
            else:
                if run:
                    episodes.append(run)
                run = 0
        if run:
            episodes.append(run)
    near = 0
    max_reach = 0.0
    if spawn:
        for e, S in byent.items():
            if not S or S[0]['tm'] != team:
                continue
            for s in S:
                if s.get('al', 1) >= 0.5:
                    r = math.hypot(s['px'] - spawn[0], s['py'] - spawn[1])
                    if r > max_reach:
                        max_reach = r
    if spawn and stuck:
        near = sum(1 for p in stuck if math.hypot(p[0] - spawn[0], p[1] - spawn[1]) < NEAR)
    stuck_gd.sort()
    return {
        'spawn': spawn,
        'n_stuck': len(stuck),
        'near_pct': round(100 * near / len(stuck)) if stuck else 0,
        'med_gd': round(stuck_gd[len(stuck_gd) // 2]) if stuck_gd else 0,
        'max_reach': round(max_reach),
        'max_ep_s': (max(episodes) * PROBE_S) if episodes else 0,
        'long_eps': sum(1 for r in episodes if r * PROBE_S > 12),
    }


def classify(path):
    byent, first = parse(path)
    name = os.path.splitext(os.path.basename(path))[0]
    if not byent:
        return name, 'NO-BOTS', {}
    ax = team_stats(byent, first, 'x')
    al = team_stats(byent, first, 'a')
    v = 'EN-ROUTE'
    if ax['max_ep_s'] <= 8 and ax['n_stuck'] < 120:
        v = 'HEALTHY'
    elif al['long_eps'] >= 3 and al['n_stuck'] > 300:
        v = 'NAV-BROKEN'
    elif ax['near_pct'] >= 55 and ax['max_reach'] > 4000:
        # jammed near spawn, but the team CAN reach far when it gets out => a spawn cul-de-sac (m2l1)
        v = 'SPAWN-EGRESS'
    elif ax['near_pct'] >= 55:
        # jammed near spawn AND boxed in (never gets far) => piling on a nearby objective (m5l1a)
        v = 'OBJECTIVE-PILE'
    return name, v, {'ax': ax, 'al': al}


FIXABLE = {'SPAWN-EGRESS'}


def main(outdir):
    logs = sorted(glob.glob(os.path.join(outdir, '*.log')))
    rows = [classify(p) for p in logs]
    print('%-7s %-14s %-4s %6s %6s %7s %7s %5s  %s' %
          ('MAP', 'VERDICT', 'auth', 'axStk', 'near%', 'reach', 'maxEp', 'alStk', 'note'))
    print('-' * 100)
    fix = []
    for name, v, d in rows:
        auth = 'yes' if name in AUTHORED else 'bsp'
        ax = d.get('ax', {})
        al = d.get('al', {})
        tag = ''
        if v in FIXABLE and name in AUTHORED:
            tag = '<-- SPAWN-FIX CANDIDATE'
            fix.append(name)
        elif v in FIXABLE:
            tag = '(spawn-egress but BSP-derived - fix via gen_push_from_bsp)'
        print('%-7s %-14s %-4s %6d %5d%% %7d %6ds %5d  %s' %
              (name, v, auth, ax.get('n_stuck', 0), ax.get('near_pct', 0), ax.get('max_reach', 0),
               ax.get('max_ep_s', 0), al.get('n_stuck', 0), tag))
    print('-' * 96)
    print('SPAWN-FIX candidates (authored, m2l1-style):', ', '.join(fix) if fix else 'none')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'C:\mohaa-coop-dev\mohaa-coop-dev_soak')

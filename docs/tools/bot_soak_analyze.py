#!/usr/bin/env python3
"""Analyse a bot SOAK run (docs/tools/bot_soak.ps1) - one <map>.log per push map of ^~^~^ BOTPROBE samples.

Per map it answers the questions the user asked for:
  * did bots even spawn (nav present)?
  * are they MOVING, or standing still / stuck?
  * are they grinding on OBJECTS that block them (blk rising while speed ~0)?
  * are they CONSTANTLY JUMPING (the injured jump-in-place / ledge-hammer tell)?
  * are they SPREAD across the map, or clumped in one area?
  * do they TRAVERSE to the enemy's side (reach the other team's spawn), i.e. make it across the map?
  * [user 2026-09-21] PER-TEAM TIMING - AXIS has always been slower; how long does each team take to cross,
    and where do they lose it (more stuck / more blocked / longer route)?

BOTPROBE line (fgame/playerbot.cpp), each prefixed with a [HH:MM:SS ...] log timestamp:
  ^~^~^ BOTPROBE e=# tm=a/x al=0/1 hp=# px py pz spd fm rm um fire=# blk=# jmp=# pth=# gd=# en=# ed=# seen pain

  python docs/tools/bot_soak_analyze.py C:\\mohaa-coop-dev\\_soak
"""
import glob
import math
import os
import re
import sys
from collections import Counter, defaultdict

SPD_STILL      = 12.0
WANT_MOVE      = 20
RESPAWN_JUMP   = 1500.0
STUCK_FRAC_BAD = 0.25
JUMP_FRAC_BAD  = 0.30
CELL           = 256.0
MIN_PATH_OK    = 1500.0
NEAR_SPAWN     = 500.0

FIELD = re.compile(r'\b([a-z]+)=(-?\d+(?:\.\d+)?)')
TS    = re.compile(r'\[(?:\d{4}-\d\d-\d\d )?(\d{2}):(\d{2}):(\d{2})')  # logs carry a date prefix now


def parse_log(path):
    bots = defaultdict(list)
    t0 = None
    with open(path, 'r', encoding='latin-1', errors='replace') as fh:
        for line in fh:
            if 'BOTPROBE' not in line:
                continue
            kv = dict((k, float(v)) for k, v in FIELD.findall(line))
            if 'e' not in kv or 'px' not in kv:
                continue
            mtm = re.search(r'\btm=([ax?])', line)
            kv['tm'] = mtm.group(1) if mtm else '?'
            mt = TS.search(line)
            if mt:
                secs = int(mt.group(1)) * 3600 + int(mt.group(2)) * 60 + int(mt.group(3))
                if t0 is None:
                    t0 = secs
                kv['t'] = float(secs - t0)
            else:
                kv['t'] = float(len(bots[int(kv['e'])]) * 2)  # fallback: sample index * 2s
            bots[int(kv['e'])].append(kv)
    return bots


def bot_team(samples):
    """A bot's team = its most common real tm. The FIRST sample is tm=? (bots probe before joining a team), and
    reading that one made every bot teamless - the ALLIES/AXIS columns printed '-' on every map."""
    c = Counter(s['tm'] for s in samples if s['tm'] in 'ax')
    return c.most_common(1)[0][0] if c else '?'


def analyse_bot(samples):
    path = 0.0
    xs, ys = [], []
    still_want = want = jump = grind = n_alive = 0
    blk_first = blk_last = None
    prev = None
    blk_hist = []
    for s in samples:
        alive = s.get('al', 1) >= 0.5
        if alive:
            n_alive += 1
            xs.append(s['px']); ys.append(s['py'])
        wants = abs(s.get('fm', 0)) > WANT_MOVE or abs(s.get('rm', 0)) > WANT_MOVE
        spd = s.get('spd', 0)
        if s.get('jmp', 0) >= 0.5 or s.get('um', 0) > 0:
            jump += 1
        if alive and prev is not None and prev.get('al', 1) >= 0.5:
            d = math.hypot(s['px'] - prev['px'], s['py'] - prev['py'])
            if d < RESPAWN_JUMP:
                path += d
        if wants:
            want += 1
            if spd < SPD_STILL:
                still_want += 1
                if len(blk_hist) >= 3 and s.get('blk', 0) > blk_hist[-3] + 0.5:
                    grind += 1
        b = s.get('blk', 0)
        if blk_first is None:
            blk_first = b
        blk_last = b
        blk_hist.append(b)
        prev = s
    n = len(samples)
    return {
        'n': n, 'alive': n_alive, 'tm': bot_team(samples) if samples else '?',
        'path': path,
        'still_want_frac': (still_want / want) if want else 0.0,
        'jump_frac': (jump / n) if n else 0.0,
        'grind_frac': (grind / want) if want else 0.0,
        'blk_total': (blk_last - blk_first) if (blk_first is not None) else 0,
        'xs': xs, 'ys': ys,
    }


MODDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'hzm-mohaa-coop-mod', 'coop_mod')


def push_homes(mapname):
    """Allies/axis HOME centres from the seeded Push zones (ZA[1] / ZX[1]) - the authoritative ends of the map.
    The first-samples centroid is only a fallback: Push spawns a team across every zone it holds (the front starts
    mid-map), so early samples are not all at home and the 0..100% scale came out shifted (allies at 50% in 1s)."""
    vec = r'\(\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\)'
    for fn in ('mp_push_maps.scr', 'mp_push_bsp.scr'):   # hand-authored first
        path = os.path.join(MODDIR, fn)
        if not os.path.exists(path):
            continue
        txt = open(path, encoding='latin-1').read()
        m = re.search(r'^seed_%s:(.*?)(?=^seed_|\Z)' % re.escape(mapname), txt, re.S | re.M)
        if not m:
            continue
        box = {}
        for k in ('ZAmin', 'ZAmax', 'ZXmin', 'ZXmax'):
            g = re.search(r'coop_mpPush%s\[1\]\s*=\s*%s' % (k, vec), m.group(1))
            if g:
                box[k] = (float(g.group(1)), float(g.group(2)))
        if len(box) == 4:
            c = lambda a, b: ((box[a][0] + box[b][0]) / 2, (box[a][1] + box[b][1]) / 2)
            return c('ZAmin', 'ZAmax'), c('ZXmin', 'ZXmax')
    return None, None


def team_centroid(bots_m, team, first_n=30):
    pts = []
    for e, samples in bots_m.items():
        if samples and bot_team(samples) == team:
            # only samples ON the team: pre-join tm=? samples sit wherever the bot first appeared, which put a team's
            # "home" on the wrong side and gave the axis a 2s 50%/80% crossing on every map
            mine = [s for s in samples if s['tm'] == team and s.get('al', 1) >= 0.5]
            for s in mine[:first_n]:
                pts.append((s['px'], s['py']))
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def team_timing(bots_m, team, A, X):
    """Front-progress (0=own spawn .. 1=enemy spawn) over time for a team, and time to cross thresholds.
    Progress is the projection of a bot onto the allies->axis axis; allies measure A->X, axis measure X->A."""
    if not A or not X:
        return None
    ax = (X[0] - A[0], X[1] - A[1])
    L2 = ax[0] * ax[0] + ax[1] * ax[1]
    if L2 < 1.0:
        return None
    own = A if team == 'a' else X

    def proj(p):
        pr = ((p[0] - A[0]) * ax[0] + (p[1] - A[1]) * ax[1]) / L2   # 0 at A, 1 at X
        return pr if team == 'a' else (1.0 - pr)

    # bucket by ~5s, take the FRONT (max progress among the team's alive bots) per bucket
    buckets = defaultdict(list)
    for e, samples in bots_m.items():
        if not samples or bot_team(samples) != team:
            continue
        for s in samples:
            if s.get('al', 1) >= 0.5 and s['tm'] == team:
                buckets[int(s.get('t', 0) // 5)].append((s.get('t', 0), proj((s['px'], s['py']))))
    if not buckets:
        return None
    series = []  # (t, frontProgress)
    for b in sorted(buckets):
        pts = buckets[b]
        t = sum(p[0] for p in pts) / len(pts)
        front = max(p[1] for p in pts)
        series.append((t, front))
    # cumulative max front (a front never "un-reaches")
    best = -9
    cum = []
    for t, f in series:
        best = max(best, f)
        cum.append((t, best))

    def time_to(th):
        for t, f in cum:
            if f >= th:
                return t
        return None
    maxfront = cum[-1][1] if cum else 0.0
    return {'t50': time_to(0.5), 't80': time_to(0.8), 'maxfront': maxfront}


def analyse_map(path):
    bots_m = parse_log(path)
    name = os.path.splitext(os.path.basename(path))[0]
    if not bots_m:
        return {'map': name, 'bots': 0, 'verdict': 'FAIL', 'note': 'NO BOTPROBE samples - bots never spawned (no nav?)'}
    per = {e: analyse_bot(s) for e, s in bots_m.items()}
    nb = len(per)
    cells = set(); allx = []; ally = []
    for m in per.values():
        for x, y in zip(m['xs'], m['ys']):
            cells.add((int(x // CELL), int(y // CELL))); allx.append(x); ally.append(y)
    coverage_cells = len(cells)
    extent = max((max(allx) - min(allx)) if allx else 0, (max(ally) - min(ally)) if ally else 0)

    def team_stats(t):
        ms = [m for m in per.values() if m['tm'] == t]
        if not ms:
            return None
        paths = sorted(m['path'] for m in ms)
        return {
            'n': len(ms), 'medpath': paths[len(paths) // 2],
            'still': max(m['still_want_frac'] for m in ms),
            'jump': max(m['jump_frac'] for m in ms),
            'grind': max(m['grind_frac'] for m in ms),
            'blk': max(m['blk_total'] for m in ms),
        }
    sa = team_stats('a'); sx = team_stats('x')

    A, X = push_homes(name)
    if not A or not X:
        A = team_centroid(bots_m, 'a'); X = team_centroid(bots_m, 'x')
    ta = team_timing(bots_m, 'a', A, X); tx = team_timing(bots_m, 'x', A, X)

    paths = sorted(m['path'] for m in per.values())
    med_path = paths[len(paths) // 2] if paths else 0
    barely = [e for e, m in per.items() if m['path'] < MIN_PATH_OK]
    worst_jump = max((m['jump_frac'] for m in per.values()), default=0)
    worst_still = max((m['still_want_frac'] for m in per.values()), default=0)
    worst_grind = max((m['grind_frac'] for m in per.values()), default=0)

    notes = []
    verdict = 'PASS'
    if med_path < MIN_PATH_OK:
        verdict = 'FAIL'; notes.append('median bot barely moved')
    if len(barely) > nb * 0.4:
        verdict = 'FAIL'; notes.append('%d/%d barely moved' % (len(barely), nb))
    if worst_jump > JUMP_FRAC_BAD:
        notes.append('jumping worst %.0f%%' % (worst_jump * 100)); verdict = 'WARN' if verdict == 'PASS' else verdict
    if worst_still > STUCK_FRAC_BAD:
        notes.append('stuck worst %.0f%%' % (worst_still * 100)); verdict = 'WARN' if verdict == 'PASS' else verdict
    # AXIS-vs-ALLIES asymmetry callout (the user's standing concern)
    if ta and tx:
        af = ta['maxfront']; xf = tx['maxfront']
        if af - xf > 0.20:
            notes.append('AXIS lags allies (front %.0f%% vs %.0f%%)' % (xf * 100, af * 100))
            verdict = 'WARN' if verdict == 'PASS' else verdict

    return {'map': name, 'bots': nb, 'verdict': verdict, 'med_path': med_path,
            'coverage_cells': coverage_cells, 'extent': int(extent),
            'sa': sa, 'sx': sx, 'ta': ta, 'tx': tx,
            'worst_jump': worst_jump, 'worst_still': worst_still, 'worst_grind': worst_grind,
            'note': '; '.join(notes) if notes else 'ok'}


def fmt_t(v):
    return '-' if v is None else ('%.0fs' % v)


def fmt_pct(v):
    return '-' if v is None else ('%.0f%%' % (v * 100))


def main(outdir):
    logs = sorted(glob.glob(os.path.join(outdir, '*.log')))
    if not logs:
        print('no *.log in', outdir); return
    rows = [analyse_map(p) for p in logs]
    print('%-7s %-4s %-4s %8s %5s  %-28s | %-28s' %
          ('MAP', 'VERD', 'bots', 'medPath', 'cells', 'ALLIES  path/50%/80%/front', 'AXIS  path/50%/80%/front'))
    print('-' * 120)
    for r in rows:
        if r['bots'] == 0:
            print('%-7s %-4s %-4d   %s' % (r['map'], r['verdict'], 0, r['note'])); continue
        sa, sx, ta, tx = r.get('sa'), r.get('sx'), r.get('ta'), r.get('tx')

        def teamcell(s, t):
            if not s:
                return '   -'
            return '%5.0f %s %s %s' % (s['medpath'],
                                       fmt_t(t['t50']) if t else '-', fmt_t(t['t80']) if t else '-',
                                       fmt_pct(t['maxfront']) if t else '-')
        print('%-7s %-4s %-4d %8.0f %5d  %-28s | %-28s' %
              (r['map'], r['verdict'], r['bots'], r['med_path'], r['coverage_cells'],
               teamcell(sa, ta), teamcell(sx, tx)))
        if r['note'] != 'ok':
            print('          -> %s' % r['note'])
    print('-' * 120)
    print('legend: path=median bot travel, 50%%/80%%=time for the team FRONT to cross half/most of the map,')
    print('        front=furthest the team got (100%% = enemy spawn). AXIS slower shows as bigger 50/80 times & lower front.')
    npass = sum(1 for r in rows if r['verdict'] == 'PASS')
    nwarn = sum(1 for r in rows if r['verdict'] == 'WARN')
    nfail = sum(1 for r in rows if r['verdict'] == 'FAIL')
    print('%d maps:  %d PASS  %d WARN  %d FAIL' % (len(rows), npass, nwarn, nfail))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'C:\mohaa-coop-dev\_soak')

#!/usr/bin/env python3
"""Extract per-map AXIS congestion chokepoints (and reachable flank waypoints) from a bot SOAK run, to drive
per-map bot congestion-routing (user 2026-09-21: place intermediate attract-nodes so axis bots split onto
flanking approaches instead of all funnelling through one bottleneck).

For each <map>.log it finds where AXIS bots pile up (want to move but speed ~0), clusters those into hotspots,
and for the worst hotspot proposes 2 FLANK waypoints: reachable points (positions a bot actually occupied in
the run, so navmesh-valid) at roughly the choke's forward depth but laterally offset to either side - i.e. an
alternate way past the jam. Emits a JSON keyed by map for the routing layer to consume.

  python docs/tools/bot_soak_chokes.py C:\\mohaa-coop-dev\\_soak [out.json]
"""
import glob
import json
import math
import os
import re
import sys
from collections import defaultdict

FIELD = re.compile(r'\b([a-z]+)=(-?\d+(?:\.\d+)?)')
CELL = 300.0
FLANK_MIN_LAT = 350.0    # a flank must be at least this far to the side of the choke
FLANK_MAX_LAT = 1400.0   # ...but not absurdly far
FLANK_FWD_BAND = 500.0   # ...and within this of the choke's forward depth


def parse(path):
    bots = defaultdict(list)
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
        bots[e].append(kv)
    return bots, first


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None


def map_chokes(path):
    bots, first = parse(path)
    name = os.path.splitext(os.path.basename(path))[0]
    if not bots:
        return name, None

    aspawn = centroid([p for tm, p in first.values() if tm == 'a'])
    xspawn = centroid([p for tm, p in first.values() if tm == 'x'])

    # axis stuck points + all reachable points (both teams = where the navmesh let bots go)
    stuck = []
    reach = []
    for e, samples in bots.items():
        tm = samples[0]['tm']
        for s in samples:
            if s.get('al', 1) < 0.5:
                continue
            p = (s['px'], s['py'], s.get('pz', 0))
            reach.append(p)
            if tm == 'x' and (abs(s.get('fm', 0)) > 20 or abs(s.get('rm', 0)) > 20) and s.get('spd', 0) < 12:
                stuck.append(p)
    if not stuck or not xspawn:
        return name, {'axis_spawn': xspawn, 'allies_spawn': aspawn, 'chokes': [], 'note': 'no axis congestion found'}

    # cluster stuck into CELL cells; the worst cells are the chokes
    cells = defaultdict(list)
    for p in stuck:
        cells[(int(p[0] // CELL), int(p[1] // CELL))].append(p)
    ranked = sorted(cells.items(), key=lambda kv: -len(kv[1]))
    chokes = []
    for (cx, cy), pts in ranked[:2]:
        if len(pts) < 3:
            break
        c = centroid(pts)
        # forward axis = from axis spawn toward the choke (their travel direction into the jam)
        fdir = (c[0] - xspawn[0], c[1] - xspawn[1])
        flen = math.hypot(*fdir) or 1.0
        fdir = (fdir[0] / flen, fdir[1] / flen)
        perp = (-fdir[1], fdir[0])
        fwd_at_choke = (c[0] - xspawn[0]) * fdir[0] + (c[1] - xspawn[1]) * fdir[1]
        # flank candidates: reachable points near the choke's forward depth, offset to each side
        best = {-1: None, 1: None}
        bestlat = {-1: 0, 1: 0}
        for p in reach:
            rel = (p[0] - xspawn[0], p[1] - xspawn[1])
            fwd = rel[0] * fdir[0] + rel[1] * fdir[1]
            lat = rel[0] * perp[0] + rel[1] * perp[1]
            if abs(fwd - fwd_at_choke) > FLANK_FWD_BAND:
                continue
            side = 1 if lat > 0 else -1
            al = abs(lat)
            if FLANK_MIN_LAT < al < FLANK_MAX_LAT and al > bestlat[side]:
                bestlat[side] = al
                best[side] = p
        flanks = [[round(p[0]), round(p[1]), round(p[2])] for p in (best[-1], best[1]) if p]
        chokes.append({
            'at': [round(c[0]), round(c[1]), None],  # z filled by the in-game floor-snap
            'stuck_samples': len(pts),
            'dist_from_axis_spawn': round(math.hypot(c[0] - xspawn[0], c[1] - xspawn[1])),
            'flanks': [[f[0], f[1], f[2]] for f in flanks],  # z = a real bot floor height; botobj_set re-snaps
        })
    return name, {
        'axis_spawn': [round(v) for v in xspawn] if xspawn else None,
        'allies_spawn': [round(v) for v in aspawn] if aspawn else None,
        'chokes': chokes,
    }


def main(outdir, outjson=None):
    logs = sorted(glob.glob(os.path.join(outdir, '*.log')))
    if not logs:
        print('no *.log in', outdir); return
    result = {}
    print('%-8s %-6s %s' % ('MAP', 'stuck', 'axis choke(s) -> flank waypoints'))
    print('-' * 100)
    for p in logs:
        name, data = map_chokes(p)
        result[name] = data
        if not data or not data.get('chokes'):
            print('%-8s %-6s %s' % (name, '-', (data or {}).get('note', 'no data')))
            continue
        for i, ch in enumerate(data['chokes']):
            tag = name if i == 0 else ''
            fl = ' | '.join('(%d,%d)' % (f[0], f[1]) for f in ch['flanks']) or 'NONE FOUND'
            print('%-8s %-6d choke@(%d,%d) d=%d -> flanks %s' %
                  (tag, ch['stuck_samples'], ch['at'][0], ch['at'][1], ch['dist_from_axis_spawn'], fl))
    print('-' * 100)
    if outjson:
        json.dump(result, open(outjson, 'w'), indent=2)
        print('wrote', outjson)
    return result


if __name__ == '__main__':
    args = sys.argv[1:]
    d = args[0] if args else r'C:\mohaa-coop-dev\_soak'
    o = args[1] if len(args) > 1 else os.path.join(d, 'axis_chokes.json')
    main(d, o)

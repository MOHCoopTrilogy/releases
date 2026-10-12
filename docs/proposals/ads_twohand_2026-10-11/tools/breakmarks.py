"""Break-off trace of a run_break2.py session, from the JOINER's log: per capture the view-animation sequence
(ADSFRAME anim index, time in ms since the `reload` command = the first frame of the capture) with the fire press and
every later press marked, the sight deviation at the end, and the shots counted (a shot = the fire animation starting).

    python breakmarks.py <session> [--fire <anim index of fire, default 3>]
"""
import re, sys, os
RUNS_DIR = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')
sess = sys.argv[1]
FIRE = int(sys.argv[sys.argv.index('--fire') + 1]) if '--fire' in sys.argv else None
cur, rows = None, {}
for ln in open(RUNS_DIR + '/%s/qconsole_joiner.log' % sess, encoding='latin-1', errors='replace'):
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        cur = m.group(2) if m.group(1) == 'begin' else None
        if cur:
            rows[cur] = []
        continue
    if not cur:
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+)(?: (\d+))?', ln)
    if m and 'echo' not in ln:
        rows[cur].append(('mark', m.group(1) + (m.group(2) or '')))
        continue
    if 'ADSFRAME' in ln:
        p = re.search(r't=(\d+).*pose=([-\d.]+).*anim=(\d+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
        if p:
            c = re.search(r'clip=(-?[0-9]+) ammo=(-?[0-9]+)', ln)
            rows[cur].append(('f', int(p.group(1)), float(p.group(2)), int(p.group(3)), float(p.group(4)), float(p.group(5)), int(c.group(1)) if c else None, int(c.group(2)) if c else None))
for tag, r in rows.items():
    fr = [x for x in r if x[0] == 'f']
    if not fr:
        print(tag, 'no frames'); continue
    t0 = fr[0][1]
    s0 = fr[0][4:6]
    seq, last, t, lastc = [], None, 0, None
    for x in r:
        if x[0] == 'mark':
            seq.append('[%s @%d]' % (x[1], t))
        else:
            t = x[1] - t0
            if x[3] != last:
                seq.append('%d:a%d' % (t, x[3])); last = x[3]
            if x[6] is not None and x[6] != lastc:
                seq.append('%d:CLIP%d' % (t, x[6])); lastc = x[6]
    dev_end = max(((x[4] - s0[0]) ** 2 + (x[5] - s0[1]) ** 2) ** 0.5 for x in fr[-5:])
    print(tag.split('__')[2], tag.split('__')[3])
    print('   ', ' '.join(seq))
    print('    frames %d, %.1f s, pose min %.2f, sight at the end %.2f deg from the start' % (len(fr), (fr[-1][1] - t0) / 1000.0, min(x[2] for x in fr), dev_end))

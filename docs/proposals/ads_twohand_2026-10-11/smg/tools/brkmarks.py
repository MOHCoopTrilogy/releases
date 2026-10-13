"""What the first-person rig did through a break-off capture (run_smg `sbreak`): every change of the probe's anim id,
pose factor (0 = hip framing, 1 = aim framing, x = between), clip name and clip ammo, by capture frame.

    python brkmarks.py <session> [tag substring, default brk]
"""
import re, sys
RUNS = 'G:/mohaa-adsanim3/runs'
sub = sys.argv[2] if len(sys.argv) > 2 else 'brk'
cur = None; i = 0; last = None; out = {}; marks = {}
for ln in open(RUNS + '/%s/qconsole.log' % sys.argv[1], encoding='latin-1'):
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        cur = m.group(2) if m.group(1) == 'begin' else None; i = 0; last = None
        continue
    m = re.search(r'DEMO (\w+) (\d+)', ln)
    if m and cur and 'echo' not in ln:
        marks.setdefault(cur, []).append('%s@%s' % (m.group(1), m.group(2)))
    if cur and sub in cur and 'ADSFRAME' in ln:
        a = re.search(r'anim=(-?\d+)', ln).group(1)
        p = float(re.search(r'pose=([\d.]+)', ln).group(1))
        c = re.search(r'clip=(\S+)', ln); am = re.search(r'ammo=(\S+)', ln)
        key = (a, '%.0f' % p if p in (0.0, 1.0) else 'x', c.group(1) if c else '', am.group(1) if am else '')
        if key != last:
            out.setdefault(cur, []).append('%d:a%s p%s %s %s' % ((i,) + key))
            last = key
        i += 1
for k, v in out.items():
    print(k.split('__')[3], '| marks', ' '.join(marks.get(k, [])))
    print('    ', '  '.join(s.strip() for s in v)[:700])

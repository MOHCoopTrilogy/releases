r"""Break-off timing of a `--brk fire:...` run from its log: for every brk tag, the view-anim id and the clip count over
time (ADSFRAME probe), from the reload mark on - prints the changes and the time from the trigger (`DEMO intr`) to the
shot (the clip count dropping, or the fire anim starting).

    python brktime.py <run id>
view-anim ids: 1 idle, 2 charge (aim pose), 3 fire, 5 rechamber, 6 reload, 7 reload_single, 8 reload_end
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
log = os.path.join(hv.RUNS, sys.argv[1], 'qconsole.log')
tag = None; marks = {}; rows = []; out = []
rx = re.compile(r'ADSFRAME t=(\d+) .*? anim=(-?\d+) .*? clip=(-?\d+)')
for ln in open(log, encoding='latin-1', errors='replace'):
    if '^~^~^' not in ln:
        continue
    if 'ABSCEN begin' in ln:
        tag = ln.split('ABSCEN begin')[1].strip(); marks = {}; rows = []; pend = []
        continue
    if tag is None:
        continue
    if 'ABSCEN end' in ln:
        out.append((tag, marks, rows)); tag = None
        continue
    m = re.search(r'DEMO (\w+) (\d+)', ln)
    if m:
        pend.append(m.group(1)); continue
    m = rx.search(ln)
    if m:
        t, a, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        for k in pend:
            marks[k] = t
        pend = []
        rows.append((t, a, c))
for tag, marks, rows in out:
    if 'brk' not in tag:
        continue
    t0 = marks.get('reload'); ti = marks.get('intr')
    print(tag.split('__')[3], 'reload at 0, trigger at %+d ms' % (ti - t0))
    prev = None; shot = None
    for t, a, c in rows:
        if t < t0:
            prev = (a, c); continue
        if (a, c) != prev:
            print('   %+5d ms  (%+5d from the trigger)  anim %d  clip %d' % (t - t0, t - ti, a, c))
            if shot is None and t >= ti and prev and (c < prev[1] or (a == 3 and prev[0] != 3)):
                shot = t
            prev = (a, c)
    print('   PRESS TO SHOT: %s' % ('%d ms' % (shot - ti) if shot else 'no shot'))

"""how long each first-person row really plays in a measured demo: run lengths of the ADSFRAME `anim=` id between the
DEMO marks of every `__demo__after` capture in a session's qconsole.log (one ADSFRAME line = one client frame).
    python tools/animruns.py <session>
Also prints the capture index at each change (captures per client frame from the DEMO marks)."""
import re, sys

import dbslib as _L
RUN = '%s/%s/qconsole.log' % (_L.RUNS, sys.argv[1])
cur = None; seq = {}; marks = {}; times = {}
for ln in open(RUN, encoding='latin-1', errors='replace'):
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        cur = m.group(2) if m.group(1) == 'begin' else None
        continue
    if not cur:
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
    if m and 'echo' not in ln:
        marks.setdefault(cur, []).append((m.group(1), int(m.group(2)), len(seq.get(cur, []))))
        continue
    if 'ADSFRAME' in ln:
        q = re.search(r'anim=(-?\d+)', ln)
        seq.setdefault(cur, []).append(int(q.group(1)) if q else -1)
        t = re.search(r'\bt=(\d+)', ln) or re.search(r'time=(\d+)', ln)
        times.setdefault(cur, []).append(int(t.group(1)) if t else None)
for tag, s in seq.items():
    mk = marks.get(tag, [])
    print(tag, 'client frames', len(s), 'marks (name, capture, client frame):', mk)
    if len(mk) >= 2:
        (n0, c0, f0), (n1, c1, f1) = mk[0], mk[1]
        print('   client frames per capture between %s and %s: %.2f' % (n0, n1, (f1 - f0) / float(max(1, c1 - c0))))
    runs = []; a = None; n = 0; st = 0
    for i, v in enumerate(s):
        if v != a:
            if a is not None:
                runs.append((a, st, n))
            a, n, st = v, 0, i
        n += 1
    runs.append((a, st, n))
    f0 = mk[0][2] if mk else 0
    print('   runs from the first mark (anim id, start client frame rel., length): ', [(a, st - f0, n) for a, st, n in runs if st + n > f0][:14])
    if times.get(tag) and times[tag][0] is not None:
        print('   ms per client frame: %.2f' % ((times[tag][-1] - times[tag][0]) / float(len(s) - 1)))

"""Per-segment numbers for a `demo` capture (run_2h.py) from the engine's own ^~^~^ ADSFRAME probe: the capture is
split at its ^~^~^ DEMO markers (raise / fire / fire / reload / lower); per segment the ADS pose factor range and how
far the sight line strays (deg) from the settled aim just before the first shot.

    python democheck.py <session> [tag substring]
"""
import sys, re
sess = sys.argv[1]
sub = sys.argv[2] if len(sys.argv) > 2 else '__demo__'
log = open('G:/mohaa-adsanim3/runs/%s/qconsole.log' % sess, encoding='latin-1', errors='replace').read().splitlines()
cur, seg, rows, order = None, None, {}, {}
for ln in log:
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m:
        cur = m.group(2) if (m.group(1) == 'begin' and sub in m.group(2)) else None
        if cur:
            seg = 'hip'; rows[cur] = {}; order[cur] = ['hip']
        continue
    if not cur:
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
    if m and 'echo' not in ln:
        seg = m.group(1) + ('2' if m.group(1) in order[cur] else '')
        order[cur].append(seg)
        continue
    if 'ADSFRAME' in ln:
        p = re.search(r't=(\d+) .*pose=([-\d.]+).* anim=(\d+) .*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
        if p:
            rows[cur].setdefault(seg, []).append((float(p.group(2)), float(p.group(4)), float(p.group(5)), int(p.group(3))))
for tag, segs in rows.items():
    print(tag)
    ref = segs.get('raise', [])
    if not ref:
        print('   no raise segment'); continue
    y0, p0 = ref[-1][1:3]
    for s in order[tag]:
        r = segs.get(s, [])
        if not r:
            continue
        devs = [((x[1] - y0) ** 2 + (x[2] - p0) ** 2) ** 0.5 for x in r]
        tail = devs[-max(1, len(devs) // 6):]
        print('   %-8s samples %4d  pose %.2f..%.2f  sight dev max %5.2f deg  (last sixth max %5.2f)  anims %s' % (
            s, len(r), min(x[0] for x in r), max(x[0] for x in r), max(devs), max(tail), sorted({x[3] for x in r})))

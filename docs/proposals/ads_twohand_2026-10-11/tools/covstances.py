"""Stance entries of the EMPTIED aimed reloads (run_2h `--rempty`: tag stance <st>E, the capture starts WITH the last
shot and the gun reloads by itself). coverage.py's scan takes its reference from the capture's 4th sample and counts the
first 15 % as an edge - here that is the shot's recoil. This pass re-reads the same logs: reference = the settled aim
at the END of the capture, the first 25 samples (the recoil) left out, then the same verdict rule
(pose > 0.9, max dev <= 6 deg, edges <= 1.5 deg). Written into coverage_status.json `reload.<stance>` with `emptied: true`.

    python covstances.py pa9 pa13 pa14 pa15 pa16
"""
import sys, re, json, os
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs')
P = r'C:\mohaa-coop-dev\docs\proposals\ads_twohand_2026-10-11\tools\coverage_status.json'
KEY = {'beretta': 'it_w_beretta'}
d = json.load(open(P))
for sess in sys.argv[1:]:
    rows, cur = {}, None
    for ln in open('%s/%s/qconsole.log' % (RUNS, sess), encoding='latin-1', errors='replace'):
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m:
            cur = m.group(2) if m.group(1) == 'begin' else None
            if cur:
                rows[cur] = []
            continue
        if cur and 'ADSFRAME' in ln:
            p = re.search(r'pose=([-\d.]+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
            if p:
                rows[cur].append((float(p.group(1)), float(p.group(2)), float(p.group(3))))
    for tag, r in rows.items():
        m = re.match(r'ab__%s__(\w+?)__(\w+?)E__reload__after$' % re.escape(sess), tag)
        if not m or len(r) < 60:
            continue
        gun, st = m.groups()
        y0 = sum(x[1] for x in r[-5:]) / 5.0; p0 = sum(x[2] for x in r[-5:]) / 5.0
        rr = r[25:]
        devs = [((x[1] - y0) ** 2 + (x[2] - p0) ** 2) ** 0.5 for x in rr]
        k = max(1, int(len(devs) * 0.15))
        edge = max(devs[:k] + devs[-k:])
        ok = min(x[0] for x in rr) > 0.9 and max(devs) <= 6.0 and edge <= 1.5
        e = d.setdefault('models/weapons/%s.tik' % KEY.get(gun, gun), {}).setdefault('reload', {})
        for junk in (st + 'E',):
            e.pop(junk, None)
        if st == 'stand' and e.get('stand', {}).get('run') and not e['stand'].get('emptied'):
            pass                                   # a demo's standing entry (coverage.py scan) is kept
        else:
            e[st] = dict(run=sess, ok=bool(ok), dev=round(max(devs), 2), edge=round(edge, 2), end=round(max(devs[-5:]), 2),
                         pmin=round(min(x[0] for x in rr), 2), emptied=True)
        print('%-4s %-18s %-7s pose min %.2f  dev max %5.2f  edge %.2f  end %.2f  %s' % (sess, gun, st, min(x[0] for x in rr), max(devs), edge, max(devs[-5:]), 'ok' if ok else 'not ok'))
json.dump(d, open(P, 'w'), indent=1, sort_keys=True)

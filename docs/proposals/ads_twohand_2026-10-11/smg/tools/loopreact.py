"""per-round reaction of the gun in an aimed revolver reload: peak-to-peak of the engine's sight / bore probe over the
loop part of the capture (run_2h demo, --demoempty).   python loopreact.py <session> [first] [last]  (capture frames after the reload mark)"""
import re, sys
RUNS_DIR = __import__('os').environ.get('ADS_RUNS', 'G:/mohaa-adsanim3/runs').rstrip('/')   # another lane's harness: set ADS_RUNS
import numpy as np
sess = sys.argv[1]; a = int(sys.argv[2]) if len(sys.argv) > 2 else 110; b = int(sys.argv[3]) if len(sys.argv) > 3 else 260
cur = None; rows = {}; mark = {}
for ln in open(RUNS_DIR + '/%s/qconsole.log' % sess, encoding='latin-1'):
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        cur = m.group(2) if m.group(1) == 'begin' else None; continue
    if not cur: continue
    m = re.search(r'DEMO reload (\d+)', ln)
    if m and 'echo' not in ln: mark[cur] = len(rows.get(cur, []))
    if 'ADSFRAME' in ln:
        s = re.search(r'sight=\(([-\d.]+) ([-\d.]+)\) bore=\(([-\d.]+) ([-\d.]+)\) cant=([-\d.]+)', ln)
        rows.setdefault(cur, []).append([float(x) for x in s.groups()])
for k, v in rows.items():
    if k not in mark: continue
    X = np.array(v)[mark[k] + a: mark[k] + b]
    d = X.max(0) - X.min(0)
    hf = np.abs(np.diff(X, axis=0)).max(0)
    print('%-14s loop frames %d-%d: sight swing yaw %.2f pitch %.2f deg, cant %.2f deg; fastest frame-to-frame pitch %.2f deg' % (k.split('__')[2], a, b, d[0], d[1], d[4], hf[1]))

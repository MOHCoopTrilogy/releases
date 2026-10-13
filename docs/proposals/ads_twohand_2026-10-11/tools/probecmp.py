"""probecmp.py <sessA> <sessB> <tag part, e.g. colt45__yaw160e> [step]
ADSFRAME rows (rear sight R, grip G screen px, view pitch from ADSRIG) of the same demo in two runs, aligned at the
DEMO reload mark - what moved the gun between two runs of the same clips."""
import sys, re, os
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs')


def rows(sess, part):
    log = open('%s/%s/qconsole.log' % (RUNS, sess), encoding='latin-1', errors='replace').read().splitlines()
    cur, out, marks, pitch = False, [], {}, 0.0
    for ln in log:
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m and 'echo' not in ln:
            cur = m.group(1) == 'begin' and ('__%s__demo' % part) in m.group(2)
            continue
        if not cur:
            continue
        m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
        if m and 'echo' not in ln:
            marks.setdefault(m.group(1), len(out))
            continue
        m = re.search(r'ADSRIG .* pitch=([-\d.]+)', ln)
        if m:
            pitch = float(m.group(1))
        if 'ADSFRAME' in ln:
            g = lambda k: [float(v) for v in re.search(k + r'=\(([-\d.]+) ([-\d.]+)\)', ln).groups()]
            out.append(dict(t=int(re.search(r't=(\d+)', ln).group(1)), anim=int(re.search(r'anim=(\d+)', ln).group(1)),
                            R=g('R'), G=g('G'), F=g('F'), sight=g('sight'), sh=g('sh'), pitch=pitch,
                            relief=float(re.search(r'relief=([-\d.]+)', ln).group(1))))
    return out, marks


a, ma = rows(sys.argv[1], sys.argv[3])
b, mb = rows(sys.argv[2], sys.argv[3])
step = int(sys.argv[4]) if len(sys.argv) > 4 else 10
print('marks', sys.argv[1], ma, '|', sys.argv[2], mb)
ra, rb = ma['reload'], mb['reload']
print('k(rel)  anim  A: R.y   G.y  sight.y relief pitch | B: R.y   G.y  sight.y relief pitch | dG.y dR.y')
for k in range(-40, min(len(a) - ra, len(b) - rb), step):
    x, y = a[ra + k], b[rb + k]
    print('%5d  %d/%d  %7.2f %7.2f %6.3f %6.3f %5.2f | %7.2f %7.2f %6.3f %6.3f %5.2f | %6.2f %6.2f' % (
        k, x['anim'], y['anim'], x['R'][1], x['G'][1], x['sight'][1], x['relief'], x['pitch'],
        y['R'][1], y['G'][1], y['sight'][1], y['relief'], y['pitch'], y['G'][1] - x['G'][1], y['R'][1] - x['R'][1]))

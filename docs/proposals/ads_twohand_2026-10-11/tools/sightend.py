"""Sight line around the END of an aimed reload (ADSFRAME probe): does the gun come back to the settled aim, or does
it sit off it while the clip plays and move once the clip is over (a rig-solve target captured mid-recoil, bug-3597)?

    python sightend.py <session> [tag substring] [--around N]
prints, per demo capture: the settled sight (yaw pitch, deg) before the first shot, at the last shot's markers, the
sight on the clip's last 12 frames and on the 40 frames after the animation index returns to the aim pose.
"""
import os, re, sys
RUNS_DIR = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')
sess = sys.argv[1]
sub = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else ''
cur, rows = None, {}
for ln in open(RUNS_DIR + '/%s/qconsole.log' % sess, encoding='latin-1', errors='replace'):
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        cur = m.group(2) if m.group(1) == 'begin' else None
        if cur:
            rows[cur] = []
        continue
    if not cur:
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
    if m and 'echo' not in ln:
        rows[cur].append(('mark', m.group(1)))
        continue
    if 'ADSFRAME' in ln:
        p = re.search(r'pose=([-\d.]+) w=([-\d.]+) gate=([-\d.]+) anim=(\d+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
        if p:
            rows[cur].append(('f', float(p.group(1)), float(p.group(2)), float(p.group(3)), int(p.group(4)), float(p.group(5)), float(p.group(6))))
for tag, r in rows.items():
    if sub not in tag or '__demo__' not in tag:
        continue
    fr = [x for x in r if x[0] == 'f']
    idx = {}
    n = 0
    for x in r:
        if x[0] == 'mark':
            idx.setdefault(x[1], []).append(n)
        else:
            n += 1
    if 'fire' not in idx:
        continue
    f0 = idx['fire'][0]
    base = fr[f0 - 2]
    print(tag.split('__')[2], '| settled aim before the first shot: sight (%.3f %.3f)' % (base[5], base[6]))
    # the last change of the anim index back to the aim pose (2) before the lower marker
    low = idx.get('lower', [len(fr)])[0]
    k = low - 1
    while k > 0 and fr[k][4] == fr[low - 1][4]:
        k -= 1
    endclip = k + 1
    def show(a, b, step=1):
        return ' '.join('%d:a%d g%.2f (%.2f %.2f)' % (i, fr[i][4], fr[i][3], fr[i][5] - base[5], fr[i][6] - base[6]) for i in range(max(0, a), min(len(fr), b), step))
    lf = idx['fire'][-1]
    print('   last shot at %d, clip ends at %d, lower at %d   [frame: anim gate (sight yaw, pitch MINUS the settled aim)]' % (lf, endclip, low))
    print('   after the last shot :', show(lf, lf + 40, 4))
    print('   clip end            :', show(endclip - 12, endclip, 2))
    print('   after the clip      :', show(endclip, endclip + 44, 4))

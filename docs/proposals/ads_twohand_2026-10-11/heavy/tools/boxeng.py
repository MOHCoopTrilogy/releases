"""ENGINE centre-box measure of an aimed reload against the settled aim it RETURNS to (heavy lane).

The shared centrebox.py takes its baseline from the aim just before the reload. After automatic fire that aim has not
recovered from the recoil yet (BAR, runs hb1 / hb3: the gun sits lower for seconds - base cover 21-23 %, the settled
aim after the reload 27-28 %), so every frame AFTER the gun is back reads 4-5 % 'extra' although it is the aim itself.
Here, as in the offline offbox.py: covered = pixels that differ from the same view without the first-person model
(`__ref.jpg`, centrebox.py's own rule, smoke excluded); a frame's EXTRA = share of the box covered in that frame that
the settled aim at the END of the reload capture (mask grown 6 px) does not cover. Bar: under 2 % in every frame.

    python boxeng.py <session> [gun] [--dump] [--json out.json]
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv

_j = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
args = [a for a in sys.argv[1:] if not a.startswith('--') and a != _j]
sess, guns = args[0], args[1:]
RUN = '%s/%s/' % (hv.RUNS, sess)
log = open(RUN + 'qconsole.log', encoding='latin-1', errors='replace').read().splitlines()
marks, sight, cur = {}, {}, None
for ln in log:
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m:
        cur = m.group(2) if (m.group(1) == 'begin' and '__demo__after' in m.group(2)) else None
        continue
    if not cur:
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
    if m and 'echo' not in ln:
        marks.setdefault(cur, []).append((m.group(1), int(m.group(2)), len(sight.get(cur, []))))
        continue
    if 'ADSFRAME' in ln:
        p = re.search(r'sight=\(([-\d.]+) ([-\d.]+)\)', ln)
        if p:
            sight.setdefault(cur, []).append((float(p.group(1)), float(p.group(2))))


def grow(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return o


out = {}
for tag in marks:
    gun = tag.split('__')[2]
    if guns and gun not in guns:
        continue
    ref = RUN + tag + '__ref.jpg'
    fs = sorted(glob.glob(RUN + tag + '__[0-9][0-9][0-9][0-9].jpg'))
    if not os.path.isfile(ref) or not fs:
        print(gun, 'no reference / frames'); continue
    Rf = np.asarray(Image.open(ref).convert('RGB')).astype(np.int16)
    H, W = Rf.shape[:2]
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)
    Rb = Rf[y0:y1, x0:x1]
    mk = {n: (f, si) for n, f, si in marks[tag]}
    rel, low = mk['reload'][0], mk['lower'][0]

    def mask(i):
        Fm = np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)[y0:y1, x0:x1]
        d = Fm - Rb
        sm = np.abs(d).sum(axis=2)
        return (sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))
    end = mask(low - 3)
    for k in range(4, 12):
        end = end | mask(low - k)
    aimm = grow(end, 6)
    ex = [float((mask(i) & ~aimm).mean()) for i in range(rel, low)]
    sg = sight.get(tag, [])
    s0 = mk['reload'][1]; s1 = mk['lower'][1]
    seg = sg[s0:s1]
    endp = seg[-1] if seg else (0, 0)
    dev = max((((a - endp[0]) ** 2 + (b - endp[1]) ** 2) ** 0.5 for a, b in seg), default=0.0)
    tail = max((((a - endp[0]) ** 2 + (b - endp[1]) ** 2) ** 0.5 for a, b in seg[-12:]), default=0.0)
    over = [(rel + i, e) for i, e in enumerate(ex) if e > 0.02]
    print('%-10s %s  box EXTRA vs the settled aim after the reload: max %.1f %% (capture f%d), frames over 2 %%: %d of %d | settled aim covers %.1f %% | sight line: max %.2f deg off, last 12 frames within %.2f deg' % (
        gun, tag.split('__')[3], 100 * max(ex), rel + int(np.argmax(ex)), len(over), len(ex), 100 * end.mean(), dev, tail))
    if '--dump' in sys.argv:
        print('   over:', ' '.join('%d:%.0f' % (f, 100 * e) for f, e in over) or '-')
    out[gun + ':' + tag.split('__')[3]] = dict(xmax=round(100 * max(ex), 2), over=len(over), n=len(ex), dev=round(dev, 2), end=round(tail, 2), run=sess)
if '--json' in sys.argv:
    p = sys.argv[sys.argv.index('--json') + 1]
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.update(out)
    json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)

"""ENGINE centre-box measure of an aimed reload against the settled aim it RETURNS to (heavy lane).

The shared centrebox.py takes its baseline from the aim just before the reload. After automatic fire that aim has not
recovered from the recoil yet (BAR, runs hb1 / hb3: the gun sits lower for seconds - base cover 21-23 %, the settled
aim after the reload 27-28 %), so every frame AFTER the gun is back reads 4-5 % 'extra' although it is the aim itself.
Here, as in the offline offbox.py: covered = pixels that differ from the same view without the first-person model
(`__ref.jpg`, centrebox.py's own rule, smoke excluded); a frame's EXTRA = share of the box covered in that frame that
the settled aim at the END of the reload capture (mask grown 6 px) does not cover. Bar: under 2 % in every frame.

    python boxeng.py <session> [gun] [--dump] [--json out.json] [--align 8] [--cbx [--empty] [--add]]
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv

_j = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
ALIGN = int(sys.argv[sys.argv.index('--align') + 1]) if '--align' in sys.argv else 0
args = [a for a in sys.argv[1:] if not a.startswith('--') and a != _j and not (ALIGN and a == str(ALIGN))]
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
CBX = []
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
        Ff = np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)
        # --align N: the VIEW itself can sit a few pixels off the reference while the reload plays (prone breathing,
        # the braced view riding the gun's reaction - run hd1 braced: 6 px, which over 20 bullet holes read 4-6 %
        # 'cover' with no model in the box). The frame is compared at the view shift within +-N px that explains the
        # most of it; the model's own cover cannot be shifted away (it differs from the reference wherever it is).
        def at(dx, dy, st=1):
            d = Ff[y0 + dy:y1 + dy:st, x0 + dx:x1 + dx:st] - Rb[::st, ::st]
            sm = np.abs(d).sum(axis=2)
            return (sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))
        if not ALIGN:
            return at(0, 0)
        sh = min(((at(dx, dy, 3).sum(), abs(dx) + abs(dy), dx, dy) for dy in range(-ALIGN, ALIGN + 1) for dx in range(-ALIGN, ALIGN + 1)))
        return at(sh[2], sh[3])
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
    # --cbx [--empty]: the lane's centrebox.json (shared coverage.py schema: tik / tik#empty -> dev, xmax, xfr, run),
    # the WORST stance of the session. An emptied gun: the first 20 capture frames are the last shot's kick and smoke
    # (the shared centrebox.py rule) and are not the reload.
    k0 = 20 if '--empty' in sys.argv else 0
    exr = ex[k0:]
    CBX.append(dict(st=tag.split('__')[3], xmax=round(100 * max(exr), 2), xfr=round(100.0 * sum(1 for e in exr if e > 0.02) / len(exr), 1), dev=round(dev, 2), end=round(tail, 2)))
if '--json' in sys.argv:
    p = sys.argv[sys.argv.index('--json') + 1]
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.update(out)
    json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)
if '--cbx' in sys.argv and CBX:
    import cov_h
    tik = cov_h.KEY.get(guns[0] if guns else 'bar')
    p = os.path.join(hv.LANE, 'centrebox.json')
    d = json.load(open(p)) if os.path.isfile(p) else {}
    key = tik + ('#empty' if '--empty' in sys.argv else '')
    old = d.get(key, {}) if '--add' in sys.argv else {}
    per = dict(old.get('stances', {}))
    for c in CBX:
        per[c['st']] = dict(xmax=c['xmax'], xfr=c['xfr'], end=c['end'], run=sess)
    d[key] = dict(xmax=max(v['xmax'] for v in per.values()), xfr=max(v['xfr'] for v in per.values()), dev=max([c['dev'] for c in CBX] + [old.get('dev', 0.0)]),
                  run='+'.join(sorted(set(v['run'] for v in per.values()))), stances=per, align=ALIGN,
                  note='cg_adsSway 0, cg_weaponBreath 0; vs the settled aim after the reload' + ('; first 20 capture frames (last shot) skipped' if '--empty' in sys.argv else ''))
    json.dump(d, open(p, 'w', newline=chr(10)), indent=1, sort_keys=True)
    print('centrebox.json', key, d[key]['xmax'], d[key]['run'])

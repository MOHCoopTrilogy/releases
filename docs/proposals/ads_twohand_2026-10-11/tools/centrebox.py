"""Stay-on-target measure for an aimed reload (user 2026-10-12: "you reload without losing your target").

From a run_2h `demo` capture: the centre box = the middle 20 % of the screen width and height around the aim point.
Per frame of the reload segment, the share of the box covered by the first-person model (gun, hands, sleeves) = pixels
that differ from the same view captured WITHOUT the first-person model (`<tag>__ref.jpg`). The settled aim itself covers
part of the box (the sights sit on the aim point), so the numbers are:
  base   coverage of the box in the settled aim, just before the reload
  max    highest coverage during the reload
  over   share of reload frames whose coverage exceeds base by more than 5 points   <- the target is 0 %
  dev    largest sight-line deviation during the reload, degrees (engine ADSFRAME probe)

    python centrebox.py <session> [gun ...] [--json out.json]
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
args = [a for a in sys.argv[1:] if not a.startswith('--')]
sess, guns = args[0], args[1:]
RUN = 'G:/mohaa-adsanim/runs/%s/' % sess
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
out = {}
for tag in marks:
    gun = tag.split('__')[2]
    if guns and gun not in guns:
        continue
    ref = RUN + tag + '__ref.jpg'
    fs = sorted(glob.glob(RUN + tag + '__[0-9][0-9][0-9][0-9].jpg'))
    if not os.path.isfile(ref) or not fs:
        print(gun, 'no reference / frames'); continue
    R = np.asarray(Image.open(ref).convert('RGB')).astype(np.int16)
    H, W = R.shape[:2]
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)
    Rb = R[y0:y1, x0:x1]
    mk = {n: (f, si) for n, f, si in marks[tag]}
    fire0 = [f for n, f, si in marks[tag] if n == 'fire'][0]
    rel, low = mk['reload'][0], mk['lower'][0]

    def cov(i):
        # covered = clearly not the background: a big change (dark steel, sleeve), or a smaller one that is NOT grey
        # (skin). Muzzle smoke is a small grey shift and no longer counts (an emptied gun reloads in its own smoke).
        Fm = np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)[y0:y1, x0:x1]
        d = Fm - Rb
        sm = np.abs(d).sum(axis=2)
        return float(((sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))).mean())
    empty = 'empty' in mk
    if empty:                                                               # the settled aim before the first shot;
        # the reload starts by itself after the last shot, inside that shot's flash and smoke (run td3: 30 % 'cover'
        # for 16 frames with the hands exactly as before): skip them, and take the baseline from the settled aim
        # at the end of the capture as well as before the first shot (the aim sways by a few points)
        # (not before the first shot: a long string of shots walks the view up, run te4)
        base = float(np.median([cov(i) for i in range(min(low, len(fs)) - 8, min(low, len(fs)) - 2)]))
        rel = rel + 20
    else:
        base = float(np.median([cov(i) for i in range(rel - 6, rel - 1)]))  # the settled aim just before the reload
    cv = [cov(i) for i in range(rel, min(low, len(fs)))]
    s = sight[tag]
    r0 = s[mk['fire'][1] - 1] if 'fire' in mk else s[0]
    r0 = s[[si for n, f, si in marks[tag] if n == 'fire'][0] - 1]
    seg = s[mk['reload'][1] + (6 if empty else 0): mk['lower'][1]]
    dev = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg) if seg else float('nan')
    end = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg[-5:]) if seg else float('nan')
    over = float(np.mean([c > base + 0.05 for c in cv]))
    gun = gun + ('_empty' if empty else '')
    out[gun] = dict(run=sess, base=round(100 * base, 1), max=round(100 * max(cv), 1), over=round(100 * over, 1), dev=round(dev, 2), end=round(end, 2), frames=len(cv))
    print('%-14s centre box: base %5.1f %%  max %5.1f %%  frames over base+5: %5.1f %%   sight dev max %6.2f deg, ends %.2f   (%d frames)' % (
        gun, 100 * base, 100 * max(cv), 100 * over, dev, end, len(cv)))
for a in sys.argv[1:]:
    if a.startswith('--json='):
        p = a[7:]
        d = json.load(open(p)) if os.path.isfile(p) else {}
        d.update(out)
        json.dump(d, open(p, 'w'), indent=1, sort_keys=True)

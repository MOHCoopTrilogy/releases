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

AS PLAYED (2026-10-13, the lanes' standard): with a run_2h.py --tail 360:4 capture (mark `DEMO settle`) the figure is
the box cover BEYOND THE SETTLED AIM'S SWAY ENVELOPE (swayenv.py: everything the settled aim covers through a whole
sway / breath period after the reload, grown 6 px), every frame compared with the model-less reference shifted to that
frame's own background (the shots walk the view; make_shifter as smg/tools/reloadbox.py). Then xmax / xfr ARE the
envelope figures (env: true) and the old six-frame figures are kept as x6max / x6fr. Runs without the tail read as
before.
"""
import sys, os, re, glob, json
RUNS_DIR = __import__('os').environ.get('ADS_RUNS', 'G:/mohaa-adsanim/runs').rstrip('/')   # another lane's harness: set ADS_RUNS
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import swayenv


def make_shifter(Rf, box):
    """reference crop shifted to a frame's own background (two top strips the first-person model never reaches);
    the SMG lane's (smg/tools/reloadbox.py), on arrays"""
    Rg = Rf.sum(axis=2).astype(np.float32)
    strips = ((slice(20, 200), slice(40, 440)), (slice(20, 200), slice(840, 1240)))

    def shifted_ref(F):
        Fg = F.sum(axis=2).astype(np.float32)
        best = (1e18, 0, 0)
        for dy in range(-10, 11):
            for dx in range(-6, 7):
                e = 0.0
                for ys, xs in strips:
                    a = Fg[ys, xs]
                    b = Rg[ys.start - dy:ys.stop - dy, xs.start - dx:xs.stop - dx]
                    e += float(np.abs(a[::2, ::2] - b[::2, ::2]).mean())
                if e < best[0]:
                    best = (e, dy, dx)
        _, dy, dx = best
        return Rf[box[2] - dy:box[3] - dy, box[0] - dx:box[1] - dx], (dy, dx)
    return shifted_ref
args = [a for a in sys.argv[1:] if not a.startswith('--')]
sess, guns = args[0], args[1:]
RUN = RUNS_DIR + '/%s/' % sess
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
    _ts = tag.split('__')[3]
    if '_yaw' in _ts:                       # a stance demo (run_2h --dstances): key <gun>@<stance>
        gun = gun + '@' + _ts.split('_yaw')[0]
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
    def mask(i):
        Fm = np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)[y0:y1, x0:x1]
        d = Fm - Rb
        sm = np.abs(d).sum(axis=2)
        return (sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))

    def grow(m, r=6):                       # the aim sways a few pixels: its own mask, widened
        o = m.copy()
        for dy in range(-r, r + 1, 2):
            for dx in range(-r, r + 1, 2):
                o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
        return o
    empty = 'empty' in mk
    tail = 'settle' in mk
    cend = mk['settle'][0] if tail else min(low, len(fs))       # first frame after the dense reload capture
    _sh = make_shifter(R, (x0, x1, y0, y1))
    _mc, _shifts = {}, {}

    def mask_s(i):                          # the mask against the reference shifted to this frame's own background
        if i not in _mc:
            F = np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)
            Rs, _shifts[i] = _sh(F)
            d = F[y0:y1, x0:x1] - Rs
            sm = np.abs(d).sum(axis=2)
            _mc[i] = (sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))
        return _mc[i]
    if empty:                                                               # the settled aim before the first shot;
        # the reload starts by itself after the last shot, inside that shot's flash and smoke (run td3: 30 % 'cover'
        # for 16 frames with the hands exactly as before): skip them, and take the baseline from the settled aim
        # at the end of the capture as well as before the first shot (the aim sways by a few points)
        # (not before the first shot: a long string of shots walks the view up, run te4)
        base = float(np.median([cov(i) for i in range(min(low, len(fs)) - 8, min(low, len(fs)) - 2)]))
        rel = rel + 20
    else:
        base = float(np.median([cov(i) for i in range(rel - 6, rel - 1)]))  # the settled aim just before the reload
    cv = [cov(i) for i in range(rel, cend)]
    # EXTRA cover: box pixels covered by hand / gun that the settled aim does NOT cover (its sights sit in the
    # box). This is the figure for 'is the centre clear': it does not go down when the gun leaves the aim.
    bf = list(range(min(low, len(fs)) - 8, min(low, len(fs)) - 2)) if empty else list(range(rel - 6, rel - 1))
    aimmask = grow(np.mean([mask(i) for i in bf], axis=0) > 0.3)
    ex = [float((mask(i) & ~aimmask).mean()) for i in range(rel, cend)]
    xmax, xfr = 100 * max(ex), 100 * float(np.mean([e > 0.02 for e in ex]))
    envd = {}
    if tail:
        settled = list(range(cend, min(low, len(fs)) - 2))
        aim_raw = np.mean([mask_s(i) for i in settled[-6:]], axis=0) > 0.3
        # the dry-pose rule (default; --nodry switches it off; the SMG lane's rule for an EMPTIED gun): the dry gun's own pose - the three frames after the
        # skipped flash frames - belongs to the reference as well (a slide locked back stands higher in the box than
        # the loaded gun's). Only valid where the hands are still out of the box in those frames: LOOK at them.
        dry_raw = (np.mean([mask_s(i) for i in range(rel, rel + 3)], axis=0) > 0.5) if (empty and '--nodry' not in sys.argv) else None      # DEFAULT since 2026-10-13 (coordinator: the dry gun's own pose is part of the reference, as in the SMG lane); --nodry = the old figure
        exe, envc = swayenv.envelope_extra(mask_s, grow, range(rel, cend), settled, aim_raw, also=dry_raw)
        aimg = grow(aim_raw)
        alone = [float((mask_s(i) & ~aimg).mean()) for i in settled[:-8]]
        ex6 = [float((mask_s(i) & ~aimg).mean()) for i in range(rel, cend)]
        shl = [_shifts[i] for i in range(rel, cend)]
        envd = dict(env=True, dry=bool(dry_raw is not None), x6max=round(100 * max(ex6), 1), x6fr=round(100 * float(np.mean([e > 0.02 for e in ex6])), 1),
                    env_cover=round(100 * envc, 1), env_n=len(settled), aim_cover=round(100 * float(aim_raw.mean()), 1),
                    alone=round(100 * max(alone), 1), xat=rel + int(np.argmax(exe)),
                    shift=list(max(shl, key=lambda q: abs(q[0]) + abs(q[1]))))
        ex = exe
        xmax, xfr = 100 * max(ex), 100 * float(np.mean([e > 0.02 for e in ex]))
        print('%-16s AS PLAYED: beyond the aim\'s sway ENVELOPE (%d settled frames, covers %.1f %% of the box; the six-frame aim %.1f %%): max %.2f %% (capture f%d), %d frames over 2 %% | vs the six-frame mask: max %.1f %% | settled aim ALONE vs that mask: max %.1f %% | largest background shift %s px' % (
            gun + ('_empty' if empty else ''), len(settled), 100 * envc, envd['aim_cover'], xmax, envd['xat'], sum(1 for e in ex if e > 0.02), envd['x6max'], envd['alone'], envd['shift']))
    if '--dump' in sys.argv:
        print(gun, 'reload starts at capture frame', rel, '| frames over 2 %:', ' '.join('%d:%.0f' % (rel + k, 100 * e) for k, e in enumerate(ex) if e > 0.02))
    s = sight[tag]
    r0 = s[mk['fire'][1] - 1] if 'fire' in mk else s[0]
    r0 = s[[si for n, f, si in marks[tag] if n == 'fire'][0] - 1]
    seg = s[mk['reload'][1] + (6 if empty else 0): (mk['settle'][1] if tail else mk['lower'][1])]
    dev = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg) if seg else float('nan')
    end = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg[-5:]) if seg else float('nan')
    over = float(np.mean([c > base + 0.05 for c in cv]))
    if '--cycle' in sys.argv and not empty:
        # the PER-SHOT segment (a hand-cycled gun racks / bolts after every shot): first fire marker to the reload
        # marker, the first frames of each shot left out (flash); same aim mask, same bar. Key <gun>_cycle.
        fires = [f for n, f, si in marks[tag] if n == 'fire']
        skip = set(k for f in fires for k in range(f, f + 10))        # flash + the shot's own recoil (10 frames since 2026-10-13: run pa18, the Welrod's kick alone read 3-5 % at +5..+8 with both hands still on the gun)
        idx = [i for i in range(fires[0], min(mk['reload'][0], len(fs))) if i not in skip]
        if tail:
            exc, _ = swayenv.envelope_extra(mask_s, grow, idx, settled, aim_raw)
        else:
            exc = [float((mask(i) & ~aimmask).mean()) for i in idx]
        sc = s[[si for n, f, si in marks[tag] if n == 'fire'][0]: mk['reload'][1]]
        devc = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in sc) if sc else float('nan')
        endc = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in sc[-5:]) if sc else float('nan')
        out[gun + '_cycle'] = dict(xmax=round(100 * max(exc), 1), xfr=round(100 * float(np.mean([e > 0.02 for e in exc])), 1), run=sess,
                                   dev=round(devc, 2), end=round(endc, 2), frames=len(exc), shots=len(fires), **({'env': True} if tail else {}))
        print('%-16s PER-SHOT cycle (%d shots): centre box covered beyond the aim: max %4.1f %%, in %4.1f %% of frames | sight dev max %5.2f deg, back to %.2f (%d frames)%s' % (
            gun, len(fires), 100 * max(exc), out[gun + '_cycle']['xfr'], devc, endc, len(exc),
            (' | over 2 %: ' + ' '.join('%d:%.0f' % (i, 100 * e) for i, e in zip(idx, exc) if e > 0.02)) if '--dump' in sys.argv else ''))
    gun = gun + ('_empty' if empty else '')
    out[gun] =dict(xmax=round(xmax, 1), xfr=round(xfr, 1), run=sess, base=round(100 * base, 1), max=round(100 * max(cv), 1), over=round(100 * over, 1), dev=round(dev, 2), end=round(end, 2), frames=len(cv), **envd)
    print('%-16s centre box COVERED beyond the aim: max %4.1f %%, in %4.1f %% of frames (>2 %%) | total cover base %4.1f max %4.1f | sight dev max %5.2f deg, ends %.2f (%d frames)' % (
        gun, xmax, xfr, 100 * base, 100 * max(cv), dev, end, len(cv)))
for a in sys.argv[1:]:
    if a.startswith('--json='):
        p = a[7:]
        d = json.load(open(p)) if os.path.isfile(p) else {}
        d.update(out)
        json.dump(d, open(p, 'w'), indent=1, sort_keys=True)

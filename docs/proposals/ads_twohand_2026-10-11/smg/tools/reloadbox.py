"""Engine measure of one `sdemo` capture (run_smg): where the reload really is (from the probe's `anim` field, not from
the harness's mark - an emptied gun starts by itself), and over exactly those frames
    extra   share of the centre box (middle 20 %) covered by the first-person model BEYOND the settled aim (the aim's
            own mask, taken from the last settled frames before the lower and grown 6 px, as centrebox.py)  - bar 2 %
    dev     largest sight-line deviation from the settled aim, degrees; `end` = over the last 5 frames - bar 0.05
    pose    lowest ADS pose factor (1.00 = the aim framing held throughout)
An emptied gun reloads in its own smoke: `--skip N` leaves the first N reload frames out of `extra` (reported).

    python reloadbox.py <session> <tag substring> [--skip 0] [--dump] [--json out.json key]
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
RUNS = 'G:/mohaa-adsanim3/runs/'


def load(sess, sub):
    run = RUNS + sess + '/'
    cur, marks, rows = None, {}, {}
    for ln in open(run + 'qconsole.log', encoding='latin-1', errors='replace'):
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m and 'echo' not in ln:
            cur = m.group(2) if m.group(1) == 'begin' else None
            continue
        if not cur or sub not in cur:
            continue
        m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
        if m and 'echo' not in ln:
            marks.setdefault(cur, []).append((m.group(1), int(m.group(2)), len(rows.get(cur, []))))
            continue
        if 'ADSFRAME' in ln:
            p = re.search(r'pose=([-\d.]+).*anim=(-?\d+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
            if p:
                rows.setdefault(cur, []).append((float(p.group(1)), int(p.group(2)), float(p.group(3)), float(p.group(4))))
    tags = sorted(rows)
    assert len(tags) == 1, tags
    tag = tags[0]
    fs = sorted(glob.glob(run + tag + '__[0-9][0-9][0-9][0-9].jpg'))
    return run, tag, marks[tag], rows[tag], fs


def mask(f, Rb, box):
    x0, x1, y0, y1 = box
    d = np.asarray(Image.open(f).convert('RGB')).astype(np.int16)[y0:y1, x0:x1] - Rb
    sm = np.abs(d).sum(axis=2)
    return (sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))


def grow(m, r=6):
    o = m.copy()
    for dy in range(-r, r + 1, 2):
        for dx in range(-r, r + 1, 2):
            o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return o


def measure(sess, sub, skip=0, dump=False):
    run, tag, marks, rows, fs = load(sess, sub)
    mk = {n: (f, si) for n, f, si in marks}
    # probe rows and screenshots are both one per frame from the ABSCEN begin: the mark's two counters give the offset
    off = [si - f for n, f, si in marks]
    o = int(round(np.median(off)))
    low = mk['lower'][0] if 'lower' in mk else len(fs)
    anim = lambda i: rows[min(len(rows) - 1, max(0, i + o))][1]
    settled = anim(low - 3)                     # the aim (or hip idle) id just before the lower
    first = [n for n in marks if n[0] == 'fire'][0][1]
    # the reload = the last run of frames before `low` whose anim id is neither the settled one nor a firing one
    fire_ids = set(anim(i) for i in range(first, min(first + 3, low)))
    i1 = low - 1
    while i1 > first and anim(i1) == settled:
        i1 -= 1
    i0 = i1
    rid = anim(i1)
    while i0 > first and anim(i0 - 1) == rid:
        i0 -= 1
    ref = run + tag + '__ref.jpg'
    Rf = np.asarray(Image.open(ref).convert('RGB')).astype(np.int16)
    H, W = Rf.shape[:2]
    box = (int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6))
    Rb = Rf[box[2]:box[3], box[0]:box[1]]
    base = [mask(fs[i], Rb, box) for i in range(low - 8, low - 2)]
    aimmask = grow(np.mean(base, axis=0) > 0.3)
    # After a long burst the VIEW is still creeping back for seconds: the wall behind the gun is then a pixel or two
    # off the reference and every timber edge counts as cover (run sb2: 7 % with nothing but the sights in the box).
    # The reference is therefore shifted to each frame's background first - the shift that best matches two strips of
    # the frame the first-person model never reaches (top left / top right).
    Rg = Rf.sum(axis=2).astype(np.float32)
    strips = ((slice(20, 200), slice(40, 440)), (slice(20, 200), slice(840, 1240)))

    def shifted_ref(f):
        Fg = np.asarray(Image.open(f).convert('RGB')).astype(np.int16).sum(axis=2).astype(np.float32)
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
    ex, shifts = [], []
    for i in range(i0, i1 + 1):
        Rs, sh = shifted_ref(fs[i])
        shifts.append(sh)
        ex.append(float((mask(fs[i], Rs, box) & ~aimmask).mean()))
    if dump:
        print('   background shift against the reference, px (dy, dx): first %s, largest %s' % (shifts[0], max(shifts, key=lambda s: abs(s[0]) + abs(s[1]))))
    s0 = rows[min(len(rows) - 1, low - 3 + o)]
    seg = [rows[min(len(rows) - 1, i + o)] for i in range(i0, i1 + 1)]
    dev = [((r[2] - s0[2]) ** 2 + (r[3] - s0[3]) ** 2) ** 0.5 for r in seg]
    res = dict(run=sess, tag=tag, reload=(i0, i1), frames=i1 - i0 + 1, anim=rid, settled=settled,
               extra_max=round(100 * max(ex[skip:]), 1), extra_frames_over=int(sum(e > 0.02 for e in ex[skip:])), skip=skip,
               extra_first=round(100 * max(ex[:skip] or [0]), 1), dev_max=round(max(dev), 2), dev_end=round(max(dev[-5:]), 3),
               pose_min=round(min(r[0] for r in seg), 2), base=round(100 * float(np.mean(base)), 1),
               back=round(max(((rows[min(len(rows) - 1, i + o)][2] - s0[2]) ** 2 + (rows[min(len(rows) - 1, i + o)][3] - s0[3]) ** 2) ** 0.5 for i in range(i1 + 4, min(low, i1 + 12))) if i1 + 4 < low else -1.0, 3))
    print('%s: reload = capture frames %d-%d (%d frames, anim %d; settled %d) | box beyond the aim max %.1f %% (%d frames over 2 %%%s) | '
          'sight dev max %.2f deg, last 5 frames %.3f, back on the aim after it %.3f | pose min %.2f' % (
              tag.split('__', 2)[2], i0, i1, res['frames'], rid, settled, res['extra_max'], res['extra_frames_over'],
              (', first %d frames skipped: max %.1f %%' % (skip, res['extra_first'])) if skip else '', res['dev_max'], res['dev_end'], res['back'], res['pose_min']))
    if dump:
        print('   over 2 %:', ' '.join('%d:%.0f' % (i0 + k, 100 * e) for k, e in enumerate(ex) if e > 0.02) or '-')
        print('   dev by 10 frames:', ' '.join('%.1f' % max(dev[k:k + 10]) for k in range(0, len(dev), 10)))
        # the fastest the sight line moves (a hop reads as a large step): deg per capture frame, with the clip frame (30 fps)
        st = [((seg[k + 1][2] - seg[k][2]) ** 2 + (seg[k + 1][3] - seg[k][3]) ** 2) ** 0.5 for k in range(len(seg) - 1)]
        top = sorted(range(len(st)), key=lambda k: -st[k])[:6]
        print('   fastest sight-line steps, deg / frame (clip frame):', ' '.join('%.3f (f%.0f)' % (st[k], k * 76.0 / len(seg)) for k in sorted(top)))
    return res


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    skip = int(sys.argv[sys.argv.index('--skip') + 1]) if '--skip' in sys.argv else 0
    if '--skip' in sys.argv:
        a.remove(str(skip))
    js = None
    if '--json' in sys.argv:
        k = sys.argv.index('--json'); js = (sys.argv[k + 1], sys.argv[k + 2]); a.remove(js[0]); a.remove(js[1])
    r = measure(a[0], a[1], skip, '--dump' in sys.argv)
    if js:
        d = json.load(open(js[0])) if os.path.isfile(js[0]) else {}
        d[js[1]] = r
        json.dump(d, open(js[0], 'w'), indent=1, sort_keys=True)

"""ENGINE centre-box measure for a run_rifle capture (the rifle lane's copy of the pistol lane's centrebox.py measure,
on G:/mohaa-adsanim2/runs and run_rifle's tags / marks).

Centre box = the middle 20 % of the screen. A frame's EXTRA cover = box pixels covered by the first-person model
(different from the same view captured without it, `__ref` / `__ref2`, the smaller of the two; a small grey shift =
muzzle smoke does not count) that the settled aim (the frames before the first mark, mask grown 6 px) does not cover.
Sight deviation from the cgame's ADSFRAME probe (deg from the settled aim).

    python rbox.py <session> [tag substring] [--dump] [--json=out.json]
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
RUNS = 'G:/mohaa-adsanim2/runs/'


def measure(sess, sub='', dump=False):
    RUN = RUNS + sess + '/'
    log = open(RUN + 'qconsole.log', encoding='latin-1', errors='replace').read().splitlines()
    marks, sight, anims, cur = {}, {}, {}, None
    for ln in log:
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m and 'echo' not in ln:
            cur = m.group(2) if m.group(1) == 'begin' else None
            continue
        if not cur:
            continue
        m = re.search(r'\^~\^~\^ RIFLE (\w+) (\d+)', ln)
        if m and 'echo' not in ln:
            marks.setdefault(cur, []).append((m.group(1), int(m.group(2)), len(sight.get(cur, []))))
            continue
        if 'ADSFRAME' in ln:
            p = re.search(r'sight=\(([-\d.]+) ([-\d.]+)\)', ln)
            if p:
                sight.setdefault(cur, []).append((float(p.group(1)), float(p.group(2))))
            q = re.search(r'anim=(\S+)', ln)
            if q:
                anims.setdefault(cur, []).append(q.group(1))
    out = {}
    for tag in marks:
        if sub and sub not in tag:
            continue
        fs = sorted(glob.glob(RUN + tag + '__[0-9][0-9][0-9][0-9].jpg'))
        refs = [RUN + tag + '__%s.jpg' % r for r in ('ref', 'ref2') if os.path.isfile(RUN + tag + '__%s.jpg' % r)]
        if not fs or not refs:
            print(tag, 'no frames / reference'); continue
        Rs = [np.asarray(Image.open(r).convert('RGB')).astype(np.int16) for r in refs]
        H, W = Rs[0].shape[:2]
        x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)

        # the shot's view kick turns the whole view for about 20 frames (the backdrop moves, the reference no longer
        # fits: run ra1 read 20-30 % with the centre clear): per frame the reference is shifted by the offset that
        # fits a band of backdrop the first-person model never reaches (the top 22 % of the screen)
        band = slice(0, int(H * 0.22))
        Gs = [Rr.sum(axis=2).astype(np.float32) for Rr in Rs]

        def shift_of(Fg, Rg):
            # coarse on a 4x reduced band, then +-4 px on every 4th column
            A4 = Fg[band][::4, 80:W - 80:4]; B4 = Rg[band][::4, 80:W - 80:4]
            best = (1e18, 0, 0)
            for dy in range(-26, 27):
                for dx in range(-12, 13):
                    b = np.roll(np.roll(B4, dy, axis=0), dx, axis=1)
                    a = A4
                    if dy > 0:
                        a = a[dy:]; b = b[dy:]
                    elif dy < 0:
                        a = a[:dy]; b = b[:dy]
                    e = float(np.abs(a - b).mean())
                    if e < best[0]:
                        best = (e, dy * 4, dx * 4)
            cy, cx = best[1], best[2]
            best = (1e18, cy, cx)
            A = Fg[band, 80:W - 80:4]
            for dy in range(cy - 4, cy + 5):
                Rr_ = np.roll(Rg, dy, axis=0)[band]
                for dx in range(cx - 4, cx + 5):
                    b = np.roll(Rr_, dx, axis=1)[:, 80:W - 80:4]
                    a = A
                    if dy > 0:
                        a = a[dy:]; b = b[dy:]
                    e = float(np.abs(a - b).mean())
                    if e < best[0]:
                        best = (e, dy, dx)
            return best

        def mask(i):
            Ff = np.asarray(Image.open(fs[i]).convert('RGB')).astype(np.int16)
            Fg = Ff.sum(axis=2).astype(np.float32)
            Fm = Ff[y0:y1, x0:x1]
            best = None
            for Rr, Rg in zip(Rs, Gs):
                e, dy, dx = shift_of(Fg, Rg)
                d = Fm - np.roll(np.roll(Rr, dy, axis=0), dx, axis=1)[y0:y1, x0:x1]
                sm = np.abs(d).sum(axis=2)
                mk = (sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))
                if best is None or mk.sum() < best.sum():
                    best = mk
                    kick[i] = (dy, dx)
            return best
        kick = {}

        def grow(m, r=6):
            o = m.copy()
            for dy in range(-r, r + 1, 2):
                for dx in range(-r, r + 1, 2):
                    o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
            return o
        mk = marks[tag]
        first = mk[0][1]; end = [f for n, f, s in mk if n == 'end'][0]
        start = [f for n, f, s in mk if n in ('reload', 'fire')][-1]
        if '__bolt__' in tag and anims.get(tag):
            # the cycle clip, not the shot: from the capture frame the view anim leaves the fire / aim row for the
            # cycle row (the first NEW anim id after the fire mark), + 4 frames (the 0.06 s blend out of the recoil)
            (_, f0, s0), (_, f1, s1) = [m for m in mk if m[0] == 'fire'][-1], [m for m in mk if m[0] == 'end'][0]
            an_ = anims[tag]
            k = next((i for i in range(s0 + 2, min(s1, len(an_))) if an_[i] != an_[s0 - 1] and an_[i] != an_[min(s0 + 1, len(an_) - 1)]), None)
            if k is None:
                k = next((i for i in range(s0 + 2, min(s1, len(an_))) if an_[i] != an_[s0 - 1]), s0)
            start = int(round(f0 + (k - s0) * (f1 - f0) / float(max(1, s1 - s0)))) + 4
        aimmask = grow(np.mean([mask(i) for i in range(max(0, first - 6), first)], axis=0) > 0.3)
        base = float(np.mean([mask(i).mean() for i in range(max(0, first - 6), first)]))
        ex = [float((mask(i) & ~aimmask).mean()) for i in range(start, min(end, len(fs)))]
        s = sight.get(tag, [])
        dev = endd = float('nan')
        if s:
            si0 = mk[0][2]; r0 = s[max(0, si0 - 1)]
            seg = s[[x for n, f, x in mk if n in ('reload', 'fire')][-1]:[x for n, f, x in mk if n == 'end'][0]]
            if seg:
                dev = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg)
                endd = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg[-5:])
        over = [(start + k, 100 * e) for k, e in enumerate(ex) if e > 0.02]
        an = anims.get(tag, [])
        seq = []
        for x in an:
            if not seq or seq[-1] != x:
                seq.append(x)
        out[tag] = dict(start=start, xmax=round(100 * max(ex), 1), over=len(over), frames=len(ex), base=round(100 * base, 1), dev=round(dev, 2), end=round(endd, 2), anims=seq[:12])
        print('%-52s from f%d' % (tag[4:-7], start), 'box beyond the aim: max %4.1f %%, %d of %d frames over 2 %% | aim covers %4.1f %% | sight dev max %5.2f deg, ends %.2f | anims %s' % (
            100 * max(ex), len(over), len(ex), 100 * base, dev, endd, ' '.join(seq[:8])))
        if dump:
            print('    largest view shift (px):', max((abs(v[0]) for v in kick.values()), default=0))
        if dump and over:
            print('    over 2 %:', ' '.join('%d:%.0f' % o for o in over))
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    o = measure(args[0], args[1] if len(args) > 1 else '', '--dump' in sys.argv)
    for a in sys.argv[1:]:
        if a.startswith('--json='):
            p = a[7:]
            d = json.load(open(p)) if os.path.isfile(p) else {}
            d.update(o)
            json.dump(d, open(p, 'w'), indent=1, sort_keys=True)

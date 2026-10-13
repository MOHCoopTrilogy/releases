"""ENGINE centre-box measure for a run_rifle capture (the rifle lane's copy of the pistol lane's centrebox.py measure,
on G:/mohaa-adsanim2/runs and run_rifle's tags / marks).

Centre box = the middle 20 % of the screen. A frame's EXTRA cover = box pixels covered by the first-person model
(different from the same view captured without it, `__ref` / `__ref2`, the smaller of the two; a small grey shift =
muzzle smoke does not count) that the settled aim (the frames before the first mark, mask grown 6 px) does not cover.
Sight deviation from the cgame's ADSFRAME probe (deg from the settled aim).

    python rbox.py <session> [tag substring] [--dump] [--json=out.json] [--zoom=<dir>]
--dump lists every frame over 2 % with WHERE in the box the cover sits; --zoom writes the box surround of those frames
with the extra cover tinted red (to see which part crosses the rim).
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim2/runs').rstrip('/') + '/'


def measure(sess, sub='', dump=False, zoomdir=None):
    RUN = RUNS + sess + '/'
    log = open(RUN + 'qconsole.log', encoding='latin-1', errors='replace').read().splitlines()
    marks, sight, anims, front, cur = {}, {}, {}, {}, None
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
            p2 = re.search(r' F=\(([-\d.]+) ([-\d.]+)\)', ln)       # the FRONT sight on screen (deg from the view axis)
            if p and p2:
                front.setdefault(cur, []).append((float(p2.group(1)), float(p2.group(2))))
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
            # SKIN-coloured box pixels (the hands; the bolt is dark / grey, the sleeve olive, the stock orange): the
            # HANDS-ONLY figure of a bolt cycle, whose own bolt is exempt from the bar (user 2026-10-12)
            r_, g_, b_ = Fm[:, :, 0], Fm[:, :, 1], Fm[:, :, 2]
            # (the spent case is brass: far more yellow than skin, g - b 60-110 against 30)
            skin[i] = (r_ > 110) & (r_ - g_ > 12) & (r_ - g_ < 65) & (r_ - b_ > 30) & (r_ - b_ < 110) & (g_ - b_ < 48)
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
        skin = {}

        def grow(m, r=6):
            o = m.copy()
            for dy in range(-r, r + 1, 2):
                for dx in range(-r, r + 1, 2):
                    o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
            return o
        mk = marks[tag]
        first = mk[0][1]; end = [f for n, f, s in mk if n == 'end'][0]
        start = [f for n, f, s in mk if n in ('reload', 'fire')][-1]
        segs = [(start, end)]
        if '__empty' in tag:
            # the automatic reload of an emptied gun: the mark sits 4 frames after the LAST SHOT - its recoil
            # (0.4 s, the whole rifle kicked through the box) is the shot's, not the reload's
            # RBOX_EMPTY_SKIP=100: a BOLT rifle cycles its bolt once more after the last shot (the between-shot clip, on
            # the sights, its own bolt in the box) before the automatic reload starts - skip it to read the reload alone
            segs = [(start + int(os.environ.get('RBOX_EMPTY_SKIP', '26')), end)]
        if '__bolt' in tag and anims.get(tag):
            # the cycle clip, not the shot: from the capture frame the view anim leaves the fire / aim row for the
            # cycle row (the first NEW anim id after the fire mark), + 4 frames (the 0.06 s blend out of the recoil).
            # One segment per shot (part bolt2 = two shots, two cycles), each up to the next fire mark / the end.
            an_ = anims[tag]
            fires = [m for m in mk if m[0] == 'fire']
            segs = []
            for j, (_, f0, s0) in enumerate(fires):
                _, f1, s1 = fires[j + 1] if j + 1 < len(fires) else [m for m in mk if m[0] == 'end'][0]
                k = next((i for i in range(s0 + 2, min(s1, len(an_))) if an_[i] != an_[s0 - 1] and an_[i] != an_[min(s0 + 1, len(an_) - 1)]), None)
                if k is None:
                    k = next((i for i in range(s0 + 2, min(s1, len(an_))) if an_[i] != an_[s0 - 1]), s0)
                segs.append(((f0 if os.environ.get('RBOX_FROM_FIRE') else int(round(f0 + (k - s0) * (f1 - f0) / float(max(1, s1 - s0)))) + 4), f1))
            start = segs[0][0]
        # the settled aim = EVERYTHING the breathing aim covers in the frames before the first mark (their union,
        # grown 6 px). It was `mean > 0.3` of six frames: the same pose then read 3-19 % 'aim covers' from one
        # capture to the next and the rifle's own breathing counted as cover (2026-10-12). For a figure of the CLIP
        # alone capture with `run_rifle.py --steady` (breath and sway off).
        pre = [mask(i) for i in range(max(0, first - 8), first)]
        if '__empty' in tag and os.environ.get('RBOX_EMPTY_REF', 'end') == 'end':
            # an emptied capture has only the END reference picture, and several quick shots walk the view up the wall:
            # against it the frames before the first shot differ over a third of the box (run rb32: 'aim covers'
            # 19-46 %, a mask that hides whatever is under it). The settled aim is taken from the capture's LAST
            # eight frames instead - the rifle is back on the aim there, in front of the same wall as the reference
            pre = [mask(i) for i in range(max(0, min(end, len(fs)) - 8), min(end, len(fs)))]
        aimmask = grow(np.any(pre, axis=0))
        base = float(np.mean([m_.mean() for m_ in pre]))
        fr = [i for a_, b_ in segs for i in range(a_, min(b_, len(fs)))]
        exm = {i: (mask(i) & ~aimmask) for i in fr}
        ex = [float(exm[i].mean()) for i in fr]
        hx = [float((exm[i] & skin[i]).mean()) for i in fr]
        # SWAY ENVELOPE (the lanes' standard since 2026-10-13, ..\..	ools\swayenv.py): a reload capture that runs on
        # after the rifle is back on the aim (`run_rifle.py --rframes` = the clip + a whole sway period, 5.7 s = 357
        # frames) is judged against EVERYTHING the settled aim covers through that tail (every 4th frame) and the
        # frames before the first mark - an emptied capture gets its proper settled reference this way. RBOX_ENV =
        # capture frames from the reload mark to the settled aim, per part (the tail starts there).
        envd = {}
        part = tag.split('__')[-2]
        t0 = dict(kv.split(':') for kv in os.environ.get('RBOX_ENV', 'reload:226,empty:330').split(',')).get(part.rstrip('D'))
        if t0 and '__bolt' not in tag:
            tail = list(range(start + int(t0), min(end, len(fs)), 4))
            if len(tail) >= 20:
                sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
                import swayenv
                clipf = [i for i in fr if i < start + int(t0)]
                pre_ = [mask(i) for i in range(max(0, first - 8), first)] if '__empty' not in tag else []
                am = np.any(pre_, axis=0) if pre_ else np.zeros_like(exm[fr[0]])
                mcache = {}

                def mof(i):
                    if i not in mcache:
                        mcache[i] = mask(i)
                    return mcache[i]
                env = swayenv.envelope(mof, tail, am)
                envg = grow(env)
                ee = {i: (mof(i) & ~envg) for i in clipf}
                ea = [float(ee[i].mean()) for i in clipf]
                eh = [float((ee[i] & skin[i]).mean()) for i in clipf]
                envd = dict(env_all=round(100 * max(ea), 1), env_all_at=clipf[int(np.argmax(ea))], env_hands=round(100 * max(eh), 1),
                            env_hands_at=clipf[int(np.argmax(eh))], env_over=sum(1 for e in ea if e > 0.02), env_frames=len(ea),
                            env_cover=round(100 * float(env.mean()), 1), env_tail=len(tail),
                            env_over_list=[(clipf[k], round(100 * e, 1)) for k, e in enumerate(ea) if e > 0.02])
        s = sight.get(tag, [])
        dev = endd = fdev = fdev2 = float('nan')
        if s:
            si0 = mk[0][2]; r0 = s[max(0, si0 - 1)]
            seg = s[[x for n, f, x in mk if n in ('reload', 'fire')][-1]:[x for n, f, x in mk if n == 'end'][0]]
            if '__bolt' in tag:
                # the CYCLE's sight movement, not the shot's recoil: the probe samples that belong to the measured
                # capture frames (sample index interpolated between the marks, one probe line per rendered frame)
                pts = sorted((f, x) for n, f, x in mk)
                s_of = lambda f: int(round(np.interp(f, [a_ for a_, b_ in pts], [b_ for a_, b_ in pts])))
                seg = [s[min(len(s) - 1, s_of(f))] for f in fr]
                fs_ = front.get(tag, [])
                if len(fs_) == len(s):
                    # F is in screen pixels of the 1280-wide weapon view (wfov 81.96 deg): 12.85 px per degree.
                    # fdev = every measured frame (the first ones still carry the SHOT's recoil, about 0.9 deg when the
                    # cycle clip starts); fdev2 = from 16 capture frames (0.26 s) into each cycle on = the cycle alone
                    f0_ = fs_[max(0, si0 - 1)]
                    fd = lambda f: (((fs_[min(len(s) - 1, s_of(f))][0] - f0_[0]) ** 2 + (fs_[min(len(s) - 1, s_of(f))][1] - f0_[1]) ** 2) ** 0.5) / 12.85
                    fdev = max(fd(f) for f in fr)
                    late = [f for a_, b_ in segs for f in range(a_ + 16, min(b_, len(fs)))]
                    fdev2 = max(fd(f) for f in late) if late else float('nan')
            if seg:
                dev = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg)
                endd = max(((a - r0[0]) ** 2 + (b - r0[1]) ** 2) ** 0.5 for a, b in seg[-5:])
        over = [(fr[k], 100 * e) for k, e in enumerate(ex) if e > 0.02]
        # WHERE in the box the extra cover sits (which part crosses the rim): share of it in the left / right half and
        # the upper / lower half, and the box edges it touches
        where = {}
        for i, pc in over:
            m_ = exm[i]; hh, ww = m_.shape; t_ = float(m_.sum())
            edges = ''.join(c for c, on in (('L', m_[:, :3].any()), ('R', m_[:, -3:].any()), ('T', m_[:3].any()), ('B', m_[-3:].any())) if on)
            where[i] = 'right %d %% low %d %% edges %s' % (100 * m_[:, ww // 2:].sum() / t_, 100 * m_[hh // 2:].sum() / t_, edges or '-')
        if zoomdir and over:
            os.makedirs(zoomdir, exist_ok=True)
            for i, pc in over:
                im = Image.open(fs[i]).convert('RGB')
                a_ = np.asarray(im).copy()
                sv = a_[y0:y1, x0:x1]; sv[exm[i]] = (0.4 * sv[exm[i]] + 0.6 * np.array([255, 0, 0])).astype(np.uint8)
                cx0, cy0 = max(0, x0 - (x1 - x0)), max(0, y0 - (y1 - y0))
                im2 = Image.fromarray(a_).crop((cx0, cy0, min(W, x1 + (x1 - x0)), min(H, y1 + (y1 - y0))))
                from PIL import ImageDraw
                ImageDraw.Draw(im2).rectangle((x0 - cx0, y0 - cy0, x1 - cx0, y1 - cy0), outline=(255, 230, 0))
                im2.save(os.path.join(zoomdir, '%s__f%04d.jpg' % (tag[4:-7], i)), quality=88)
        an = anims.get(tag, [])
        seq = []
        for x in an:
            if not seq or seq[-1] != x:
                seq.append(x)
        out[tag] = dict(start=start, xmax=round(100 * max(ex), 1), hands=round(100 * max(hx), 1), hands_at=fr[int(np.argmax(hx))], over=len(over), frames=len(ex), base=round(100 * base, 1), dev=round(dev, 2), fdev=round(fdev, 2), fdev2=round(fdev2, 2), end=round(endd, 2), anims=seq[:12])
        print('%-52s from f%d' % (tag[4:-7], start), 'box beyond the aim: HANDS (skin) max %4.1f %% at f%d, all %4.1f %%, %d of %d frames over 2 %% | aim covers %4.1f %% | rear sight vs front (sight dev) max %5.2f deg, ends %.2f | FRONT sight off the target max %.2f deg (%.2f after the recoil) | anims %s' % (
            100 * max(hx), fr[int(np.argmax(hx))], 100 * max(ex), len(over), len(ex), 100 * base, dev, endd, fdev, fdev2, ' '.join(seq[:8])))
        out[tag].update(envd)
        if envd:
            print('    BEYOND THE SWAY ENVELOPE (tail %d frames, envelope covers %.1f %%): hands max %.1f %% at f%d, everything max %.1f %% at f%d, %d of %d frames over 2 %%%s' % (
                envd['env_tail'], envd['env_cover'], envd['env_hands'], envd['env_hands_at'], envd['env_all'], envd['env_all_at'], envd['env_over'], envd['env_frames'],
                ('  [' + ' '.join('%d:%.1f' % o for o in envd['env_over_list'][:40]) + ']') if envd['env_over'] else ''))
        if dump:
            print('    largest view shift (px):', max((abs(v[0]) for v in kick.values()), default=0))
        if dump and over:
            print('    over 2 %:', ' '.join('%d:%.0f' % o for o in over))
            for i, pc in over:
                print('      f%d %4.1f %%  %s' % (i, pc, where[i]))
    return out


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    zd = next((a[7:] for a in sys.argv[1:] if a.startswith('--zoom=')), None)
    o = measure(args[0], args[1] if len(args) > 1 else '', '--dump' in sys.argv, zd)
    for a in sys.argv[1:]:
        if a.startswith('--json='):
            p = a[7:]
            d = json.load(open(p)) if os.path.isfile(p) else {}
            d.update(o)
            json.dump(d, open(p, 'w'), indent=1, sort_keys=True)

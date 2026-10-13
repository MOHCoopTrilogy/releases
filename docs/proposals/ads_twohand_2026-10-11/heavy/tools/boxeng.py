"""ENGINE centre-box measure of an aimed reload against the settled aim it RETURNS to (heavy lane).

The shared centrebox.py takes its baseline from the aim just before the reload. After automatic fire that aim has not
recovered from the recoil yet (BAR, runs hb1 / hb3: the gun sits lower for seconds - base cover 21-23 %, the settled
aim after the reload 27-28 %), so every frame AFTER the gun is back reads 4-5 % 'extra' although it is the aim itself.
Here, as in the offline offbox.py: covered = pixels that differ from the same view without the first-person model
(`__ref.jpg`, centrebox.py's own rule, smoke excluded); a frame's EXTRA = share of the box covered in that frame that
the settled aim at the END of the reload capture (mask grown 6 px) does not cover. Bar: under 2 % in every frame.

    python boxeng.py <session> [gun] [--dump] [--json out.json] [--align 8 | --sway] [--cbx [--empty] [--add]]

--sway = AS PLAYED (cg_adsSway / cg_weaponBreath on): the SMG lane's measure, its code (../../smg/tools/reloadbox.py:
mask / grow / make_shifter, bug-3641) - every frame is compared with the model-less reference shifted to that frame's
own BACKGROUND (two top strips the first-person model never reaches), the aim's mask is the mean of the six settled
frames before the lower grown 6 px. It also prints swaybox.py's figure: the settled aim ALONE over its own mask in the
frames between the clip's end (ADSFRAME anim id back on the aim's) and the mask frames. Sway and breath translate
the whole rig, so the gun at the return sits where the sway has it, not where the mask was taken: a reload cannot
read lower than the settled aim alone does. --align is the sway-off measure of bug-3619 and stays for old runs.
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv

_j = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
ALIGN = int(sys.argv[sys.argv.index('--align') + 1]) if '--align' in sys.argv else 0
SWAY = '--sway' in sys.argv
if SWAY:
    sys.path.insert(0, os.path.join(hv.LANE, '..', 'smg', 'tools'))
    import reloadbox as RBX                 # the SMG lane's measure, used as a library (its RUNS is not used here)
args = [a for a in sys.argv[1:] if not a.startswith('--') and a != _j and not (ALIGN and a == str(ALIGN))]
sess, guns = args[0], args[1:]
RUN = '%s/%s/' % (hv.RUNS, sess)
log = open(RUN + 'qconsole.log', encoding='latin-1', errors='replace').read().splitlines()
marks, sight, anims, cur = {}, {}, {}, None
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
            q = re.search(r'anim=(-?\d+)', ln)
            anims.setdefault(cur, []).append(int(q.group(1)) if q else -1)


def grow(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            o |= np.roll(np.roll(m, dy, axis=0), dx, axis=1)
    return o


out = {}
SW = []
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

    shifter = RBX.make_shifter(Rf, (x0, x1, y0, y1)) if SWAY else None

    def mask(i):
        if SWAY:
            return RBX.mask(fs[i], shifter(fs[i])[0], (x0, x1, y0, y1))
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
    if SWAY:
        base = [mask(i) for i in range(low - 8, low - 2)]
        end = np.mean(base, axis=0) > 0.3
        aimm = RBX.grow(end)
    else:
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
    alone = None
    if SWAY:
        # where the clip ends: the last capture frame whose anim id is not the settled aim's (marks carry both counters)
        an = anims.get(tag, [])
        o = s0 - rel
        aid = lambda i: an[min(len(an) - 1, max(0, i + o))] if an else -1
        # run_h.py --tail: a whole sway / breath period of the settled aim follows the reload window, captured
        # sparsely (mark `settle`) - the clip's end is looked for in the dense part only
        sid = an[min(len(an) - 1, s1 - 3)] if an else -1
        ce = (mk['settle'][0] if 'settle' in mk else low - 8) - 1
        while ce > rel and aid(ce) == sid:
            ce -= 1
        ce += 1                                             # first settled capture frame
        # BOXENG_CLIPLEN=N: a hands row the cgame plays PAST the server's idle / charge (apply_reloadfinish.py; FG 42
        # emptied: the anim id is the aim's again at 2.33 s, the row runs 3.0 s) - the clip is N capture frames long
        if os.environ.get('BOXENG_CLIPLEN'):
            ce = max(ce, min(low - 10, rel + int(os.environ['BOXENG_CLIPLEN'])))
        st = ex[ce - rel:low - 8 - rel]
        alone = (ce, len(st), 100 * max(st) if st else -1.0, sum(1 for e in st if e > 0.02))
        clip = ex[:ce - rel]
        # ENVELOPE: everything the settled aim covers anywhere in its sway (union of the settled frames, grown as the
        # mask is) - what the reload adds to the picture beyond the aim AS PLAYED
        env = end.copy()
        for i in range(ce, low - 2):
            env |= mask(i)
        envg = RBX.grow(env)
        exe = [float((mask(i) & ~envg).mean()) for i in range(rel, ce)]
        k0s = 0
        if '--empty' in sys.argv:
            under = [i for i in range(len(exe) - 5) if max(exe[i:i + 5]) <= 0.02]
            k0s = min(40, max(20, under[0] if under else 0))
        exs = exe[k0s:]
        ovr = [(rel + k0s + i, e) for i, e in enumerate(exs) if e > 0.02]
        print('   AS PLAYED (sway on) %s: clip = capture f%d-%d%s | vs the 6-frame aim mask: max %.1f %%, %d over | settled aim ALONE after the clip (%d frames) vs that mask: max %.1f %%, %d over | '
              'clip vs the aim\'s sway ENVELOPE (covers %.1f %%): max %.2f %% (f%d), %d over' % (
                  tag.split('__')[3], rel, ce - 1, (' (first %d = last shot skipped)' % k0s) if k0s else '', 100 * max(clip[k0s:]) if clip else -1,
                  sum(1 for e in clip[k0s:] if e > 0.02), alone[1], alone[2], alone[3], 100 * env.mean(), 100 * max(exs), rel + k0s + int(np.argmax(exs)), len(ovr)))
        if k0s:
            # the skip rule ends where the cover first stays under the bar, so the figure after it sits just under 2 %
            # by construction when 20-30 rounds of smoke are still drifting off (looked at, run hg3: grey puffs over the
            # door and backdrop edges in the leans, the gun has left the box by capture frame 18). After 40 frames:
            # BOXENG_AFTER=N (default 40): a hand-cycled gun's last shot is followed by its own pump and a second of smoke
            # before the reload starts (shotgun: the reload begins 74 frames after the shot = capture frame 63)
            AFT = int(os.environ.get('BOXENG_AFTER', '40'))
            print('      after the first %d capture frames (%.2f s; the smoke is gone): max %.2f %%' % (AFT, AFT * 0.016, 100 * max(exe[AFT:])))
            SWL = round(100 * max(exe[AFT:]), 2)
        else:
            SWL = None
        if '--dump' in sys.argv:
            print('   envelope over:', ' '.join('%d:%.1f' % (f, 100 * e) for f, e in ovr) or '-')
        SW.append(dict(st=tag.split('__')[3], xmax=round(100 * max(exs), 2), xfr=round(100.0 * len(ovr) / len(exs), 1), alone=round(alone[2], 2),
                       mask6=round(100 * max(clip[k0s:]), 2), end=round(tail, 2), dev=round(dev, 2), after40=SWL))
    print('%-10s %s  box EXTRA vs the settled aim after the reload: max %.1f %% (capture f%d), frames over 2 %%: %d of %d | settled aim covers %.1f %% | sight line: max %.2f deg off, last 12 frames within %.2f deg' % (
        gun, tag.split('__')[3], 100 * max(ex), rel + int(np.argmax(ex)), len(over), len(ex), 100 * end.mean(), dev, tail))
    if '--dump' in sys.argv:
        print('   over:', ' '.join('%d:%.0f' % (f, 100 * e) for f, e in over) or '-')
    out[gun + ':' + tag.split('__')[3]] = dict(xmax=round(100 * max(ex), 2), over=len(over), n=len(ex), dev=round(dev, 2), end=round(tail, 2), run=sess)
    # --cbx [--empty]: the lane's centrebox.json (shared coverage.py schema: tik / tik#empty -> dev, xmax, xfr, run),
    # the WORST stance of the session. An emptied gun: the first 20 capture frames are the last shot's kick and smoke
    # (the shared centrebox.py rule) and are not the reload.
    k0 = 20 if '--empty' in sys.argv else 0
    if k0:
        # 30 rounds of muzzle smoke hang longer than 20 frames (StG 44 braced at the wall: 8 % decaying to 2 % by f32,
        # run he2): the tail of the LAST SHOT ends where the cover first drops under the bar, 40 frames at most
        # (under for five frames running: a puff drifting back over the box at f20-21 read 2.02 % in the left lean)
        under = [i for i in range(len(ex) - 5) if max(ex[i:i + 5]) <= 0.02]
        k0 = min(40, max(k0, under[0] if under else 0))
    exr = ex[k0:]
    CBX.append(dict(st=tag.split('__')[3], xmax=round(100 * max(exr), 2), xfr=round(100.0 * sum(1 for e in exr if e > 0.02) / len(exr), 1), dev=round(dev, 2), end=round(tail, 2)))
if '--json' in sys.argv:
    p = sys.argv[sys.argv.index('--json') + 1]
    d = json.load(open(p)) if os.path.isfile(p) else {}
    d.update(out)
    json.dump(d, open(p, 'w', newline='\n'), indent=1, sort_keys=True)
if '--cbx' in sys.argv and (SW if SWAY else CBX):
    import cov_h
    p = os.path.join(hv.LANE, 'centrebox.json')
    d = json.load(open(p)) if os.path.isfile(p) else {}
    # the shared coverage.py reads GUN keys (the harness name, `<gun>_empty` for the emptied gun) and maps them to tiks
    key = (guns[0] if guns else 'bar') + ('_empty' if '--empty' in sys.argv else '')
    old = d.get(key, {}) if '--add' in sys.argv else {}
    per = dict(old.get('stances', {}))
    for c in (SW if SWAY else CBX):
        per[c['st']] = dict(xmax=c['xmax'], xfr=c['xfr'], end=c['end'], run=sess)
        if SWAY:
            per[c['st']].update(mask6=c['mask6'], alone=c['alone'], **({'after40': c['after40']} if c['after40'] is not None else {}))
    d[key] = dict(xmax=max(v['xmax'] for v in per.values()), xfr=max(v['xfr'] for v in per.values()), dev=max([c['dev'] for c in (SW if SWAY else CBX)] + [old.get('dev', 0.0)]),
                  run='+'.join(sorted(set(v['run'] for v in per.values()))), stances=per, align=ALIGN,
                  note=('AS PLAYED (cg_adsSway 0.1, cg_weaponBreath 1): xmax = beyond the settled aim\'s sway envelope; mask6 = vs the six-frame aim mask (SMG rule), alone = the settled aim alone vs that mask'
                        if SWAY else 'cg_adsSway 0, cg_weaponBreath 0; vs the settled aim after the reload') + ('; first 20 capture frames (last shot) skipped' if '--empty' in sys.argv else ''))
    json.dump(d, open(p, 'w', newline=chr(10)), indent=1, sort_keys=True)
    print('centrebox.json', key, d[key]['xmax'], d[key]['run'])

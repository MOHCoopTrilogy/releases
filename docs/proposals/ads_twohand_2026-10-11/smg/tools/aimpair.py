"""Aim-pose evidence from engine stills (run_smg `stills` captures): BEFORE / AFTER pair per gun with the centre box
drawn, the engine's own numbers (centre-box cover against the same view without the first-person model; the ADSFRAME
probe's pose factor and sight-line place), and a stance sheet of the AFTER run.

    python aimpair.py pair <before sess> <after sess> <gun> <out.jpg> [--stance stand] [--label "MP40"]
    python aimpair.py stances <sess> <gun> <out.jpg>           every stance captured for the gun, one row
    python aimpair.py numbers <sess> [gun ...]                  per gun and stance: pose, sight place, box cover
"""
import sys, os, re, glob, json
import numpy as np
from PIL import Image, ImageDraw
RUNS = 'G:/mohaa-adsanim3/runs/'


def frames(sess, gun, st):
    tag = 'ab__%s__%s__%s__aim__after' % (sess, gun, st)
    fs = sorted(glob.glob(RUNS + sess + '/' + tag + '__[0-9][0-9][0-9][0-9].jpg'))
    ref = RUNS + sess + '/' + tag + '__ref.jpg'
    return tag, fs, (ref if os.path.isfile(ref) else None)


def cover(f, ref):
    """share of the centre box (middle 20 %) covered by the first-person model, centrebox.py's own rule"""
    R = np.asarray(Image.open(ref).convert('RGB')).astype(np.int16)
    H, W = R.shape[:2]
    x0, x1, y0, y1 = int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6)
    d = np.asarray(Image.open(f).convert('RGB')).astype(np.int16)[y0:y1, x0:x1] - R[y0:y1, x0:x1]
    sm = np.abs(d).sum(axis=2)
    return float(((sm > 300) | ((sm > 60) & ((d.max(axis=2) - d.min(axis=2)) > 25))).mean())


def probe(sess):
    """{tag: [(pose, sx, sy), ...]} from the ADSFRAME lines between the ABSCEN marks"""
    out, cur = {}, None
    for ln in open(RUNS + sess + '/qconsole.log', encoding='latin-1', errors='replace'):
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m and 'echo' not in ln:
            cur = m.group(2) if m.group(1) == 'begin' else None
            continue
        if cur and 'ADSFRAME' in ln:
            p = re.search(r'pose=([-\d.]+).*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
            if p:
                out.setdefault(cur, []).append(tuple(float(x) for x in p.groups()))
    return out


def numbers(sess, gun, st, pr=None):
    tag, fs, ref = frames(sess, gun, st)
    if not fs:
        return None
    pr = pr if pr is not None else probe(sess)
    p = pr.get(tag, [])
    dev = max((a ** 2 + b ** 2) ** 0.5 for _, a, b in p) if p else float('nan')
    return dict(frames=len(fs), pose=round(min(x[0] for x in p), 2) if p else None, dev=round(dev, 2),
                box=round(100 * cover(fs[-1], ref), 1) if ref else None)


def panel(f, label, crop=(240, 150, 1040, 600), w=640):
    im = Image.open(f).convert('RGB')
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0), width=2)
    im = im.crop(crop)
    im = im.resize((w, int(round(im.height * w / float(im.width)))), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 15), fill=(255, 255, 255))
    d.text((4, 2), label, fill=(0, 0, 0))
    return im


def main():
    a = sys.argv[1:]
    opt = {}
    while '--stance' in a or '--label' in a or '--json' in a:
        for k in ('--stance', '--label', '--json'):
            if k in a:
                i = a.index(k); opt[k] = a[i + 1]; del a[i:i + 2]
    if a[0] == 'pair':
        sb, sa, gun, out = a[1:5]
        st = opt.get('--stance', 'stand')
        nb, na = numbers(sb, gun, st), numbers(sa, gun, st)
        lab = opt.get('--label', gun)
        fb, fa = frames(sb, gun, st)[1][-1], frames(sa, gun, st)[1][-1]
        pb = panel(fb, '%s BEFORE (released pose, run %s): centre box %.1f %%, sight line %.2f deg off' % (lab, sb, nb['box'], nb['dev']))
        pa = panel(fa, '%s AFTER (support hand as at the hip, run %s): centre box %.1f %%, %.2f deg' % (lab, sa, na['box'], na['dev']))
        S = Image.new('RGB', (pb.width * 2 + 6, pb.height), 'white')
        S.paste(pb, (0, 0)); S.paste(pa, (pb.width + 6, 0))
        S.save(out, quality=90)
        print(gun, 'before', nb, 'after', na, '->', out)
    elif a[0] == 'stances':
        sess, gun, out = a[1:4]
        pr = probe(sess)
        ps = []
        for st in ('stand', 'crouch', 'prone', 'standL', 'standR', 'crouchL', 'crouchR', 'braced'):
            n = numbers(sess, gun, st, pr)
            if n:
                ps.append(panel(frames(sess, gun, st)[1][-1], '%s %s: pose %s, %.2f deg, box %s %%' % (gun, st, n['pose'], n['dev'], n['box']), w=480))
        cols = 4
        S = Image.new('RGB', (480 * min(cols, len(ps)), ps[0].height * ((len(ps) + cols - 1) // cols)), 'white')
        for i, p in enumerate(ps):
            S.paste(p, ((i % cols) * 480, (i // cols) * p.height))
        S.save(out, quality=88)
        print(out, len(ps), 'stances')
    elif a[0] == 'numbers':
        sess = a[1]
        pr = probe(sess)
        guns = a[2:] or sorted(set(t.split('__')[2] for t in pr))
        res = {}
        for g in guns:
            for st in ('stand', 'crouch', 'prone', 'standL', 'standR', 'crouchL', 'crouchR', 'braced'):
                n = numbers(sess, g, st, pr)
                if n:
                    res.setdefault(g, {})[st] = n
                    print('%-10s %-8s pose %s  sight %.2f deg  box %s %%' % (g, st, n['pose'], n['dev'], n['box']))
        if opt.get('--json'):
            json.dump(res, open(opt['--json'], 'w'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main()

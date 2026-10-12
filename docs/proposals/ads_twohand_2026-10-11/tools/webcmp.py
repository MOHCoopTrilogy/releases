"""Side-by-side GIF of two demo captures from the reload press on (fast loop | slow loop), with the reload's measured
length (reload press -> back on the aim clip, from the engine's ADSFRAME anim ids).

    python webcmp.py <sessA> <sessB> <tag substring> <out.gif> [--step 5] [--w 300] [--labels "a|b"] [--crop x0,y0,x1,y1]
"""
import sys, re, glob, os, argparse
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser()
ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('sub'); ap.add_argument('out')
ap.add_argument('--step', type=int, default=5); ap.add_argument('--w', type=int, default=300)
ap.add_argument('--labels', default='A|B'); ap.add_argument('--crop', default='300,170,1020,720')
ap.add_argument('--colors', type=int, default=32); ap.add_argument('--tail', type=int, default=14)
a = ap.parse_args()
crop = [int(x) for x in a.crop.split(',')]


def load(sess):
    fs = sorted(glob.glob('G:/mohaa-adsanim/runs/%s/*%s*__[0-9][0-9][0-9][0-9].jpg' % (sess, a.sub)))
    tag = os.path.basename(fs[0]).rsplit('__', 1)[0]
    log = open('G:/mohaa-adsanim/runs/%s/qconsole.log' % sess, encoding='latin-1', errors='replace').read().splitlines()
    on, rel, t0, t1, seen = False, None, None, None, False
    for ln in log:
        m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
        if m:
            on = (m.group(1) == 'begin' and m.group(2) == tag); continue
        if not on:
            continue
        m = re.search(r'\^~\^~\^ DEMO reload (\d+)', ln)
        if m and 'echo' not in ln:
            rel = int(m.group(1)); continue
        if 'ADSFRAME' in ln:      # an empty gun starts its reload by itself, before the harness's reload key
            p = re.search(r't=(\d+) .* anim=(\d+) ', ln)
            if p:
                t, an = int(p.group(1)), int(p.group(2))
                if an in (6, 7, 8):
                    seen = True
                    if t0 is None:
                        t0 = t
                elif seen and t1 is None:
                    t1 = t
    return fs, rel, (t1 - t0) / 1000.0 if (t0 is not None and t1 is not None) else None


A, B = load(a.a), load(a.b)
la, lb = a.labels.split('|')
print('reload lengths (s):', A[2], B[2])
nA = int((A[2] or 4.3) / 0.016) + a.tail
nB = int((B[2] or 5.9) / 0.016) + a.tail
n = max(nA, nB)
H = a.w * (crop[3] - crop[1]) // (crop[2] - crop[0])
out = []
for k in range(-20, n - 14, a.step):
    S = Image.new('RGB', (a.w * 2 + 4, H + 16), (20, 20, 20))
    for j, (X, lab) in enumerate(((A, la), (B, lb))):
        i = max(0, min(len(X[0]) - 1, X[1] + k))
        im = Image.open(X[0][i]).convert('RGB').crop(crop).resize((a.w, H), Image.LANCZOS)
        S.paste(im, (j * (a.w + 4), 16))
        d = ImageDraw.Draw(S)
        d.text((j * (a.w + 4) + 3, 2), '%s  (%.1f s)' % (lab, X[2] or 0), fill=(255, 255, 255))
    out.append(S.quantize(colors=a.colors, dither=0))
out[0].save(a.out, save_all=True, append_images=out[1:], duration=16 * a.step, loop=0)
print(a.out, len(out), 'frames', os.path.getsize(a.out) // 1024, 'KB')

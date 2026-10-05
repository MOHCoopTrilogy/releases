"""runsheets.py - per-gun contact sheets + automatic single-frame pop scan for a run dir.
    python runsheets.py <run dir> <session> <out dir> [gun,...]
Pop score per frame f = min(d(f-1,f), d(f,f+1)) - d(f-1,f+1) on the lower-right (viewmodel) region, grey 160x90:
a frame that jumps away from BOTH neighbours while they agree. Prints the top 3 per gun.
"""
import sys, os, glob, numpy as np
from PIL import Image, ImageDraw
run, sess, out = sys.argv[1:4]
want = sys.argv[4].split(',') if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)
fs = glob.glob(os.path.join(run, 'ra__%s__*__[0-9][0-9][0-9][0-9].jpg' % sess))
guns = sorted(set(os.path.basename(f).split('__')[2] for f in fs))
for g in guns:
    if want and g not in want:
        continue
    L = sorted(glob.glob(os.path.join(run, 'ra__%s__%s__[0-9][0-9][0-9][0-9].jpg' % (sess, g))))
    A = [np.asarray(Image.open(f).convert('L').crop((320, 200, 1280, 720)).resize((160, 90)), dtype=float) for f in L]
    d = lambda i, j: float(np.abs(A[i] - A[j]).mean())
    pops = []
    for i in range(1, len(A) - 1):
        pops.append((min(d(i - 1, i), d(i, i + 1)) - d(i - 1, i + 1), i))
    pops.sort(reverse=True)
    print('%-16s %3d frames  pop top3 %s' % (g, len(L), ['f%d %.1f' % (i, s) for s, i in pops[:3]]))
    n = len(L); pick = [int(round(k * (n - 1) / 11)) for k in range(12)]
    S = Image.new('RGB', (4 * 320, 3 * 184)); dr = ImageDraw.Draw(S)
    for k, i in enumerate(pick):
        S.paste(Image.open(L[i]).convert('RGB').crop((320, 180, 1280, 720)).resize((320, 184)), ((k % 4) * 320, (k // 4) * 184))
        dr.rectangle([(k % 4) * 320, (k // 4) * 184, (k % 4) * 320 + 120, (k // 4) * 184 + 12], fill=(0, 0, 0))
        dr.text(((k % 4) * 320 + 2, (k // 4) * 184), '%s f%d' % (g, i), fill=(255, 255, 0))
    S.save(os.path.join(out, g + '.jpg'), quality=72)
    if os.environ.get('ALL'):   # every animation frame (every 2nd capture = 1/30 s), 60 per page (10 x 6), viewmodel region
        st = int(os.environ.get('ALL_STEP', '2')); idx = list(range(0, n, st)); per = 60; tw, th = 192, 108
        for pg in range(0, len(idx), per):
            P = Image.new('RGB', (10 * tw, 6 * th)); dp = ImageDraw.Draw(P)
            for k, i in enumerate(idx[pg:pg + per]):
                P.paste(Image.open(L[i]).convert('RGB').crop((320, 180, 1280, 720)).resize((tw, th)), ((k % 10) * tw, (k // 10) * th))
                dp.rectangle([(k % 10) * tw, (k // 10) * th, (k % 10) * tw + 36, (k // 10) * th + 11], fill=(0, 0, 0))
                dp.text(((k % 10) * tw + 2, (k // 10) * th), 'c%d' % i, fill=(255, 255, 0))
            P.save(os.path.join(out, '%s_all_p%d.jpg' % (g, pg // per)), quality=72)

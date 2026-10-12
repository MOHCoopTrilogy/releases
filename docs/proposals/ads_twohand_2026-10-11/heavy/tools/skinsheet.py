"""One still sheet for the BAR skin tone lift: before / after at the hip and in the aim, on the light wall, on a dark
backdrop and on a night map, the DP-28 in the same light as the yardstick, with the mean luminance of the gun's
pixels in each cell (pixels that differ from the same view without the first-person model).

    python skinsheet.py <day before> <day after> <night before> <night after> <out.jpg>
Sessions are run_h `demo` (dark backdrop / the night spot) + `demoy` (light wall) captures: frame 4 = hip idle, the
frame before the first shot = settled aim, `__ref` = the view without the model (taken in the aim).
"""
import sys, os, re, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw

db, da, nb, na, out = sys.argv[1:6]
W = 400


def frames(sess, gun, key):
    tag = 'ab__%s__%s__%s__demo__after' % (sess, gun, key)
    fs = sorted(glob.glob('%s/%s/%s__[0-9][0-9][0-9][0-9].jpg' % (hv.RUNS, sess, tag)))
    if not fs:
        return None
    log = open('%s/%s/qconsole.log' % (hv.RUNS, sess), encoding='latin-1', errors='replace').read()
    seg = log[log.find('ABSCEN begin ' + tag):]
    m = re.search(r'\^~\^~\^ DEMO fire (\d+)', seg)
    fire = int(m.group(1)) if m else 58
    ref = '%s/%s/%s__ref.jpg' % (hv.RUNS, sess, tag)
    return fs[4], fs[fire - 2], ref if os.path.isfile(ref) else None


def cell(path, ref, label):
    im = Image.open(path).convert('RGB')
    txt = label
    if ref:
        a = np.asarray(im).astype(np.int16); r = np.asarray(Image.open(ref).convert('RGB')).astype(np.int16)
        m = np.abs(a - r).sum(axis=2) > 90
        m[:, :200] = False; m[:80, :] = False                       # HUD corners / compass
        if m.mean() > 0.01:
            txt += '   gun pixels: mean %.0f / 255' % a[m].mean()
    im = im.resize((W, W * im.size[1] // im.size[0]), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 13), fill=(0, 0, 0)); d.text((3, 1), txt, fill=(255, 255, 255))
    return im


rows = []
for name, sb, sa, key in (('light wall', db, da, 'yaw165'), ('dark backdrop', db, da, 'stand'), ('night map m4l1', nb, na, 'stand')):
    B, A, D = frames(sb, 'bar', key), frames(sa, 'bar', key), frames(sb, 'dp28', key)
    if not (B and A):
        print('missing', name); continue
    r = [cell(B[1], B[2], 'BAR today, aim - ' + name), cell(A[1], A[2], 'BAR lifted, aim - ' + name)]
    if D:
        r.append(cell(D[1], D[2], 'DP-28 (yardstick), aim - ' + name))
    r += [cell(B[0], None, 'BAR today, hip - ' + name), cell(A[0], None, 'BAR lifted, hip - ' + name)]
    rows.append(r)
h = rows[0][0].size[1]
cols = max(len(r) for r in rows)
S = Image.new('RGB', (W * cols, h * len(rows)), 'white')
for y, r in enumerate(rows):
    for x, im in enumerate(r):
        S.paste(im, (x * W, y * h))
S.save(out, quality=88)
print(out, S.size)

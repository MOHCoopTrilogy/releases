"""WHAT is it that boxeng.py --sway counts? The centre box of chosen capture frames, 3x, with the pixels counted as
EXTRA (covered, outside the settled aim's grown mask) in red and the aim mask's edge in yellow; under each the frame's
figure, the background shift found (dy, dx) and the sight line's offset from the capture's end.

    python swayshow.py <session> <tag substring> <f,f,f | a:b:step> <out.jpg>
"""
import sys, os, re, glob
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
sys.path.insert(0, os.path.join(hv.LANE, '..', 'smg', 'tools'))
import reloadbox as RBX

sess, sub, sel, out = sys.argv[1:5]
RUN = '%s/%s/' % (hv.RUNS, sess)
fs = sorted(glob.glob(RUN + '*%s*__[0-9][0-9][0-9][0-9].jpg' % sub))
tag = os.path.basename(fs[0])[:-10]
fs = [f for f in fs if os.path.basename(f).startswith(tag + '__')]
low = None
sight, on, s_at = [], False, {}
for ln in open(RUN + 'qconsole.log', encoding='latin-1', errors='replace'):
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        on = m.group(1) == 'begin' and m.group(2) == tag
        continue
    if not on:
        continue
    m = re.search(r'\^~\^~\^ DEMO (\w+) (\d+)', ln)
    if m and 'echo' not in ln:
        s_at[m.group(1)] = (int(m.group(2)), len(sight))
        continue
    p = re.search(r'ADSFRAME.*sight=\(([-\d.]+) ([-\d.]+)\)', ln)
    if p:
        sight.append((float(p.group(1)), float(p.group(2))))
low = s_at['lower'][0]
o = s_at['lower'][1] - low
if ':' in sel:
    p = [int(x) for x in sel.split(':')]
    idx = list(range(p[0], p[1], p[2] if len(p) > 2 else 1))
else:
    idx = [int(x) for x in sel.split(',')]
Rf = np.asarray(Image.open(RUN + tag + '__ref.jpg').convert('RGB')).astype(np.int16)
H, W = Rf.shape[:2]
box = (int(W * 0.4), int(W * 0.6), int(H * 0.4), int(H * 0.6))
sh = RBX.make_shifter(Rf, box)
base = [RBX.mask(fs[i], sh(fs[i])[0], box) for i in range(low - 8, low - 2)]
aim = RBX.grow(np.mean(base, axis=0) > 0.3)
edge = aim & ~(np.roll(aim, 1, 0) & np.roll(aim, -1, 0) & np.roll(aim, 1, 1) & np.roll(aim, -1, 1))
end = sight[min(len(sight) - 1, low - 3 + o)]
tiles = []
for i in idx:
    Rs, d = sh(fs[i])
    m = RBX.mask(fs[i], Rs, box)
    ex = m & ~aim
    im = np.asarray(Image.open(fs[i]).convert('RGB'))[box[2]:box[3], box[0]:box[1]].copy()
    im[ex] = (255, 0, 0)
    im[edge & ~ex] = (255, 230, 0)
    t = Image.fromarray(im).resize((im.shape[1] * 3, im.shape[0] * 3), Image.NEAREST)
    c = Image.new('RGB', (t.size[0], t.size[1] + 16), (0, 0, 0))
    c.paste(t, (0, 0))
    s = sight[min(len(sight) - 1, i + o)]
    ImageDraw.Draw(c).text((3, t.size[1] + 2), 'f%d  extra %.1f %%  bg shift %s  sight %+.2f %+.2f deg' % (
        i, 100 * ex.mean(), d, s[0] - end[0], s[1] - end[1]), fill=(255, 255, 255))
    tiles.append(c)
cols = min(3, len(tiles))
rows = (len(tiles) + cols - 1) // cols
S = Image.new('RGB', (cols * tiles[0].size[0], rows * tiles[0].size[1]), (0, 0, 0))
for k, t in enumerate(tiles):
    S.paste(t, ((k % cols) * t.size[0], (k // cols) * t.size[1]))
S.save(out, quality=88)
print(out, S.size)

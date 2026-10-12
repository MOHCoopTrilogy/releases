"""Sheet of a session's settled-aim stills per stance (run_h `stills` part), centre box drawn, plus the engine's own
ADSFRAME numbers per stance (pose factor, sight-line deviation).

    python stances_h.py <session> <gun> <out.jpg> [--w 426]
"""
import sys, os, re, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw

sess, gun, out = sys.argv[1], sys.argv[2], sys.argv[3]
w = int(sys.argv[sys.argv.index('--w') + 1]) if '--w' in sys.argv else 426
ST = ('stand', 'crouch', 'prone', 'standL', 'standR', 'crouchL', 'crouchR', 'braced')
log = open('%s/%s/qconsole.log' % (hv.RUNS, sess), encoding='latin-1', errors='replace').read().splitlines()
num, cur = {}, None
for ln in log:
    m = re.search(r'ABSCEN (begin|end) (\S+)', ln)
    if m and 'echo' not in ln:
        cur = m.group(2) if m.group(1) == 'begin' else None
        continue
    if cur and 'ADSFRAME' in ln:
        num.setdefault(cur, []).append(ln)
ims = []
for st in ST:
    tag = 'ab__%s__%s__%s__aim__after' % (sess, gun, st)
    fs = sorted(glob.glob('%s/%s/%s__[0-9][0-9][0-9][0-9].jpg' % (hv.RUNS, sess, tag)))
    if not fs:
        continue
    im = Image.open(fs[-1]).convert('RGB')
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle((int(W * 0.4), int(H * 0.4), int(W * 0.6), int(H * 0.6)), outline=(255, 230, 0), width=2)
    im = im.resize((w, w * H // W), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    txt = '%s %s' % (gun, st)
    L = num.get(tag, [])
    if L:
        mm = re.search(r'pose=([\d.]+)', L[-1]); dv = re.search(r'dev=([-\d.]+)', L[-1])
        txt += '  ' + ' '.join(x for x in (('pose %s' % mm.group(1)) if mm else '', ('dev %s deg' % dv.group(1)) if dv else '') if x)
        print(st, L[-1][-150:])
    d.rectangle((0, 0, w, 14), fill=(0, 0, 0)); d.text((3, 1), txt, fill=(255, 255, 255))
    ims.append(im)
cols = 4
h = ims[0].size[1]
S = Image.new('RGB', (w * cols, h * ((len(ims) + cols - 1) // cols)), 'white')
for i, im in enumerate(ims):
    S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(out, quality=86)
print(out, len(ims), 'stances')

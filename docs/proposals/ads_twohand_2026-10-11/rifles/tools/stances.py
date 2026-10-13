"""Stance sheet: one capture frame per gun / part and stance (rows = specs, columns = stances), centre box drawn.

    python stances.py <out.jpg> "<run>|<gun>|<part>|<capture frame>|<label>" [...] [--w 320] [--stances stand,crouch,...]
"""
import sys, os, glob
from PIL import Image, ImageDraw
RUNS = os.environ.get('ADS_RUNS', 'G:/mohaa-adsanim2/runs').rstrip('/') + '/'
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
w = int(opt.get('w', 320))
ST = opt.get('stances', 'stand,crouch,prone,standL,standR,braced').split(',')
out, specs = args[0], args[1:]
h = w * 9 // 16
S = Image.new('RGB', (w * len(ST), (h + 12) * len(specs)), 'white')
d = ImageDraw.Draw(S)
for r, sp in enumerate(specs):
    run, gun, part, fr, label = sp.split('|')
    for c, st in enumerate(ST):
        fs = sorted(glob.glob(RUNS + '%s/ab__%s__%s__%s__%s__after__[0-9][0-9][0-9][0-9].jpg' % (run, run, gun, st, part)))
        if not fs:
            continue
        im = Image.open(fs[min(int(fr), len(fs) - 1)]).convert('RGB')
        W0, H0 = im.size
        ImageDraw.Draw(im).rectangle((int(W0 * 0.4), int(H0 * 0.4), int(W0 * 0.6), int(H0 * 0.6)), outline=(255, 225, 0), width=2)
        S.paste(im.resize((w, h), Image.LANCZOS), (c * w, r * (h + 12) + 12))
        d.text((c * w + 3, r * (h + 12)), '%s  %s  f%s (%s)' % (label, st, fr, run), fill=(0, 0, 0))
S.save(out, quality=86)
print(out, S.size)

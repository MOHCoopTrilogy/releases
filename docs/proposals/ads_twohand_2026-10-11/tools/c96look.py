"""c96look.py <out.jpg> <f0> <f1> <step> [empty|loaded] [crop x0,y0,x1,y1 as shares]  big tiles of the C96 aimed reload, cropped"""
import sys, os, subprocess
from PIL import Image
S = os.path.dirname(os.path.abspath(__file__))
out, f0, f1, st = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
which = sys.argv[5] if len(sys.argv) > 5 else 'empty'
crop = [float(v) for v in (sys.argv[6] if len(sys.argv) > 6 else '0.25,0.38,0.80,1.0').split(',')]
A = 'models/human/animation/viewmodel/pistol'
part = ('%s/coop_c96_reload_empty_ads.skc|reload_ads_empty' if which == 'empty' else '%s/coop_c96_reload_ads.skc|reload_ads_loaded') % A
W = 900; cols = 5
tmp = os.path.join(S, '_look_tmp.jpg')
r = subprocess.run([sys.executable, os.path.join(S, 'offbox.py'), 'mauser_c96', A + '/p38_ads2h.skc', part, '--w', str(W), '--sheet', tmp, '--every', '1', '--cols', str(cols)],
                   capture_output=True, text=True, cwd=os.path.join(S, 'stage'))
print('\n'.join(l for l in r.stdout.splitlines() if 'frames' in l or 'WORST' in l), r.stderr[-400:])
im = Image.open(tmp)
n = 73; rows = (n + cols - 1) // cols
tw, th = im.size[0] // cols, im.size[1] // rows
fr = list(range(f0, f1 + 1, st))
cw, ch = int(tw * (crop[2] - crop[0])), int(th * (crop[3] - crop[1]))
oc = min(len(fr), 5); orows = (len(fr) + oc - 1) // oc
sh = Image.new('RGB', (oc * cw, orows * ch), (0, 0, 0))
for k, f in enumerate(fr):
    x, y = (f % cols) * tw, (f // cols) * th
    t = im.crop((x + int(tw * crop[0]), y + int(th * crop[1]), x + int(tw * crop[2]), y + int(th * crop[3])))
    sh.paste(t, ((k % oc) * cw, (k // oc) * ch))
sh.save(out, quality=88)
print(out, sh.size, 'frames', fr)

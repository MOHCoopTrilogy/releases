"""Try variants of a heavybake set offline WITHOUT touching the staged clips: each variant is baked into a scratch
root and its frames are drawn from the eye (zoomed) in one sheet, one row per variant.

    cd heavy/assets; python ../tools/hktry.py <gun> <loaded|empty> <f,f,..> <out.jpg> [--zoom x0,y0,x1,y1] [--w 420]
          [--side] "k=v;k=v" ["k=v;..." ...]      (the k=v of heavybake --set, JSON values)
"""
import sys, os, json, argparse, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('gun'); ap.add_argument('which'); ap.add_argument('frames'); ap.add_argument('out')
ap.add_argument('--zoom'); ap.add_argument('--w', type=int, default=420); ap.add_argument('--side', action='store_true')
ap.add_argument('variants', nargs='+')
a = ap.parse_args()
import heavybake as HB
g = HB.GUNS[a.gun]
rows = []
for k, v in enumerate(a.variants):
    o = {}
    for kv in [x for x in v.split(';') if x.strip()]:
        key, val = kv.split('=', 1)
        try:
            o[key.strip()] = json.loads(val)
        except ValueError:
            o[key.strip()] = val
    root = os.path.join(hv.SCR, 'try', str(k))
    br = bool(o.pop('braced', 0))
    HB.bake(a.gun, root, a.which, o, br)
    clip = os.path.join(root, 'models', 'human', 'animation', (g['vdir'] + '/%s_reload_%sads%s.skc' % (a.gun, 'empty_' if a.which == 'empty' else '', 'b' if br else '')).replace('/', os.sep))
    print('CLIP', v, clip)
    out = os.path.join(hv.SCR, 'try', 'v%d.jpg' % k)
    ganim = g.get('gun_anim_' + a.which, 'reload_ads_empty' if a.which == 'empty' else 'reload')
    cmd = [sys.executable, os.path.join(hv.HERE, 'eyeview.py'), a.gun, '%s|%s' % (clip, ganim), a.frames, out, '--w', str(a.w), '--cols', '99']
    if a.zoom:
        cmd += ['--zoom', a.zoom]
    if a.side:
        cmd += ['--side']
    if g.get('prop'):
        cmd += ['--prop', g['prop']]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    im = Image.open(out).convert('RGB')
    ImageDraw.Draw(im).text((60, 4), v[:110], fill=(255, 255, 0))
    rows.append(im)
W = max(r.size[0] for r in rows)
S = Image.new('RGB', (W, sum(r.size[1] for r in rows)), 'white')
y = 0
for r in rows:
    S.paste(r, (0, y)); y += r.size[1]
S.save(a.out, quality=86)
print(a.out)

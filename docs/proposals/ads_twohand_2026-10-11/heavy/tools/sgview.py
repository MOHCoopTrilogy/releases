r"""Offline sheets of the staged aimed shotgun reload parts (eyeview.py per part, stacked):

    cd heavy/assets; IRONSIGHT_EXTRA_PAKS=<pk3 with the staged mesh> python ../tools/sgview.py <out prefix> [--w 360] [--parts start,single,end,endl] [--step 2]
writes <prefix>_a.jpg (start + single) and <prefix>_b.jpg (end + endl)
"""
import sys, os, subprocess, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image
P = {'start': ('shotgun_reload_ads.skc', 'reload', 23, None), 'single': ('shotgun_reload_single_ads.skc', 'reload_single', 20, 'models/ammo/shotgunshell.tik:0:15'),
     'end': ('shotgun_reload_end_ads.skc', 'reload_end', 32, None), 'endl': ('shotgun_reload_end_loaded_ads.skc', 'idle', 32, None),
     'brk': ('shotgun_reload_end_break_ads.skc', 'idle', 11, None)}
ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('--w', type=int, default=360); ap.add_argument('--parts', default='start,single,end,endl')
ap.add_argument('--step', type=int, default=2); ap.add_argument('--cols', type=int, default=8); ap.add_argument('--side', action='store_true')
a = ap.parse_args()
ims = {}
for p in a.parts.split(','):
    clip, anim, n, prop = P[p]
    tmp = os.path.join(hv.SCR, 'sgview_%s.jpg' % p)
    cmd = [sys.executable, os.path.join(hv.HERE, 'eyeview.py'), 'shotgun', 'viewmodel/shotgun/%s|%s' % (clip, anim), '0:%d:%d' % (n, a.step if p != 'end' and p != 'endl' else a.step + 1), tmp,
           '--aim', 'viewmodel/idle_shotgun00.skc', '--w', str(a.w), '--cols', str(a.cols)]
    cmd[3] = hv.staged('models/human/animation/viewmodel/shotgun/' + clip) + '|' + anim
    if prop:
        cmd += ['--prop', prop]
    if a.side:
        cmd += ['--side']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(p, (r.stdout + r.stderr)[-600:]); continue
    ims[p] = Image.open(tmp).convert('RGB')
for nm, ps in (('a', ('start', 'single')), ('b', ('end', 'endl', 'brk'))):
    L = [ims[p] for p in ps if p in ims]
    if not L:
        continue
    S = Image.new('RGB', (max(i.size[0] for i in L), sum(i.size[1] for i in L)), 'white')
    y = 0
    for i in L:
        S.paste(i, (0, y)); y += i.size[1]
    S.save('%s_%s.jpg' % (a.out, nm), quality=85); print('%s_%s.jpg' % (a.out, nm), S.size)

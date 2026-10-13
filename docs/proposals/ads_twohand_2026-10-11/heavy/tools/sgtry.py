r"""Try work-pose / hand variants of the aimed shotgun reload offline WITHOUT touching the staged clips: each variant is
a set of SG_* environment values for sgbake.py, baked into scratch and drawn (eyeview.py) at the given frames.

    cd heavy/assets; IRONSIGHT_EXTRA_PAKS=<pk3> python ../tools/sgtry.py <out.jpg> <part> <frames> "SG_WORK=1.6,20,4.6,0,0;SG_FWD=3" "SG_WORK=..." ...
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
from PIL import Image, ImageDraw
out, part, frames = sys.argv[1:4]
CL = {'start': ('shotgun_reload_ads.skc', 'reload', None), 'single': ('shotgun_reload_single_ads.skc', 'reload_single', 'models/ammo/shotgunshell.tik:0:15'),
      'end': ('shotgun_reload_end_ads.skc', 'reload_end', None), 'endl': ('shotgun_reload_end_loaded_ads.skc', 'idle', None)}
W = int(os.environ.get('SGTRY_W', '640'))
ims = []
for i, v in enumerate(sys.argv[4:]):
    env = dict(os.environ)
    for kv in v.split(';'):
        if kv.strip():
            k, val = kv.split('=', 1); env[k.strip()] = val.strip()
    root = os.path.join(hv.SCR, 'sgtry', 'v%d' % i)
    os.makedirs(root, exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(hv.HERE, 'sgbake.py'), '--only', part, '--root', root], capture_output=True, text=True, env=env)
    if r.returncode:
        print(v, (r.stdout + r.stderr)[-500:]); continue
    clip, anim, prop = CL[part]
    tmp = os.path.join(root, 'v.jpg')
    cmd = [sys.executable, os.path.join(hv.HERE, 'eyeview.py'), 'shotgun', os.path.join(root, 'models', 'human', 'animation', 'viewmodel', 'shotgun', clip) + '|' + anim,
           frames, tmp, '--aim', 'viewmodel/idle_shotgun00.skc', '--w', str(W), '--cols', '8'] + (['--prop', prop] if prop else []) + (['--side'] if os.environ.get('SGTRY_SIDE') else []) + (['--zoom', os.environ['SGTRY_ZOOM']] if os.environ.get('SGTRY_ZOOM') else [])
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode:
        print(v, (r.stdout + r.stderr)[-500:]); continue
    im = Image.open(tmp).convert('RGB')
    ImageDraw.Draw(im).text((40, 4), v, fill=(120, 0, 0))
    ims.append(im)
S = Image.new('RGB', (max(i.size[0] for i in ims), sum(i.size[1] for i in ims)), 'white')
y = 0
for im in ims:
    S.paste(im, (0, y)); y += im.size[1]
S.save(out, quality=86); print(out, S.size)

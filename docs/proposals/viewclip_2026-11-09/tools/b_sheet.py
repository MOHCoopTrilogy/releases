"""thumbnail sheet of after-only runs (VC_SIDES=b): one row per gun, frames across - for a quick scan for cuts / see-through.
    python b_sheet.py <out.jpg> <run dir> [...]        (B_FR env: frame keys, default reload 07/10/13, lean L, ADS, ADS reload, wall)"""
import os, sys
from PIL import Image, ImageDraw

FR = os.environ.get('B_FR', '07_reload,10_reload,13_reload,38_leanL,41_ads,44_adsreload,50_wall').split(',')
W, H = 300, 126
out, dirs = sys.argv[1], sys.argv[2:]
sheet = Image.new('RGB', (len(FR) * (W + 3) + 70, len(dirs) * (H + 3)), (10, 10, 10))
d = ImageDraw.Draw(sheet)
for j, dr in enumerate(dirs):
    d.text((3, j * (H + 3) + 3), os.path.basename(dr).replace('vc_', ''), fill=(255, 210, 0))
    for i, fr in enumerate(FR):
        p = os.path.join(dr, 'b_%s.jpg' % fr)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert('RGB')
        w, h = im.size
        im = im.crop((int(w * 0.12), int(h * 0.3), int(w * 0.88), h)).resize((W, H))
        sheet.paste(im, (70 + i * (W + 3), j * (H + 3)))
sheet.save(out, quality=76)
print('wrote', out)

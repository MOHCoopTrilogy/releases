"""review sheet for A/B runs: before (left) / after (right) for the frames most likely to show a cut.
    python ab_sheet.py <out.jpg> <run dir> [<run dir> ...]       (frames: reload 04/07/10/13, sprint, lean L, ADS, ADS reload)"""
import os, sys
from PIL import Image, ImageDraw

FR = os.environ.get('AB_FR', '07_reload,10_reload,13_reload,38_leanL,41_ads,44_adsreload').split(',')
W, H = 330, 138
out, dirs = sys.argv[1], sys.argv[2:]
sheet = Image.new('RGB', (len(dirs) * (2 * W + 20), len(FR) * (H + 4) + 20), (10, 10, 10))
d = ImageDraw.Draw(sheet)
for j, dr in enumerate(dirs):
    x0 = j * (2 * W + 20)
    d.text((x0 + 4, 4), os.path.basename(dr), fill=(255, 210, 0))
    for i, fr in enumerate(FR):
        for k, side in enumerate('ab'):
            p = os.path.join(dr, '%s_%s.jpg' % (side, fr))
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert('RGB')
            w, h = im.size
            im = im.crop((int(w * 0.15), int(h * 0.3), int(w * 0.85), h)).resize((W, H))
            sheet.paste(im, (x0 + k * (W + 4), 20 + i * (H + 4)))
sheet.save(out, quality=78)
print('wrote', out)

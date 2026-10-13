"""Contact sheet + old-vs-new strip from the look-test renders (reads only our own renders in media/).
    python sheet.py
"""
import os
from PIL import Image, ImageDraw, ImageFont
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'media')
try:
    F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 26)
except OSError:
    F = ImageFont.load_default()
TILES = [('left', 'left side'), ('right', 'right side'), ('top', 'top'),
         ('front34', 'three-quarter front'), ('aim', 'aim view, hammer down (as modelled)'), ('aim_cocked', 'aim view, hammer cocked'),
         ('boltback', 'bolt back + hammer cocked (posed here)'), ('boltback_top', 'open action from above'),
         ('aim_cocked_zoom', 'sight picture, zoomed: blade in the notch'), ('delivered', 'as delivered: stock, clip, 2 loose rounds'),
         ('old_left', "for comparison: the mod's current C96")]
TW, TH, COLS = 800, 450, 4


def tile(name, label, w=TW, h=TH):
    im = Image.open(os.path.join(M, name + '.jpg')).convert('RGB').resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, d.textlength(label, font=F) + 20, 38), fill=(20, 20, 20))
    d.text((10, 4), label, font=F, fill=(240, 240, 240))
    return im


rows = (len(TILES) + COLS - 1) // COLS
sh = Image.new('RGB', (TW * COLS, TH * rows), (40, 40, 40))
for i, (n, l) in enumerate(TILES):
    sh.paste(tile(n, l), ((i % COLS) * TW, (i // COLS) * TH))
sh.save(os.path.join(M, 'c96_look_sheet.jpg'), quality=90)
print('c96_look_sheet.jpg', sh.size)
if os.path.exists(os.path.join(M, 'old_left.jpg')):
    ov = Image.new('RGB', (1600, 1800), (40, 40, 40))
    ov.paste(tile('old_left', "the mod's current C96 (East's model): 4,788 triangles, 12 textures of 640x480", 1600, 900), (0, 0))
    ov.paste(tile('left', 'no12u model, pistol only: 10,560 triangles, one 4096x4096 PBR set', 1600, 900), (0, 900))
    ov.save(os.path.join(M, 'c96_old_vs_new.jpg'), quality=90)
    print('c96_old_vs_new.jpg', ov.size)

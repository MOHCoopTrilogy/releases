"""play a GIF back into a contact sheet (what the user will see, decoded):  python gifsheet.py <gif> <out.jpg> a:b:step [cols] [w]"""
import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]); a, b, st = [int(x) for x in sys.argv[3].split(':')]
cols = int(sys.argv[4]) if len(sys.argv) > 4 else 8; w = int(sys.argv[5]) if len(sys.argv) > 5 else 250
fr = []
for k in range(a, min(b, im.n_frames), st):
    im.seek(k); f = im.convert('RGB'); f = f.resize((w, w * f.height // f.width)); ImageDraw.Draw(f).text((3, 2), 'g%d' % k, fill=(255, 255, 0)); fr.append(f)
S = Image.new('RGB', (w * cols, fr[0].height * ((len(fr) + cols - 1) // cols)))
for i, f in enumerate(fr): S.paste(f, ((i % cols) * w, (i // cols) * fr[0].height))
S.save(sys.argv[2], quality=84); print(sys.argv[2], len(fr), 'of', im.n_frames)

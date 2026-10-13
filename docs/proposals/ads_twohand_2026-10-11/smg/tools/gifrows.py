"""Several GIFs played back onto ONE sheet, a row per GIF (decoded frames, what the user will see):
    python gifrows.py <out.jpg> <step> <w> <gif> [<gif> ...]"""
import sys
from PIL import Image, ImageDraw
out, step, w = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
rows = []
for g in sys.argv[4:]:
    im = Image.open(g)
    fr = []
    for k in range(0, im.n_frames, step):
        im.seek(k)
        f = im.convert('RGB')
        f = f.resize((w, w * f.height // f.width))
        ImageDraw.Draw(f).text((3, 2), 'g%d' % k, fill=(255, 255, 0))
        fr.append(f)
    rows.append(fr)
H = max(f.height for r in rows for f in r)
S = Image.new('RGB', (w * max(len(r) for r in rows), H * len(rows)))
for i, r in enumerate(rows):
    for j, f in enumerate(r):
        S.paste(f, (j * w, i * H))
S.save(out, quality=84)
print(out, S.size)

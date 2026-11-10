import sys
from PIL import Image, ImageDraw
out, names = sys.argv[1], sys.argv[2:]
w, h = 645, 270
cols = 4
S = Image.new('RGB', (w * cols, h * ((len(names) + cols - 1) // cols)))
for i, n in enumerate(names):
    im = Image.open(n + '.jpg').resize((w, h)); ImageDraw.Draw(im).text((6, 22), n, fill=(255, 255, 0))
    S.paste(im, ((i % cols) * w, (i // cols) * h))
S.save(out, quality=78)

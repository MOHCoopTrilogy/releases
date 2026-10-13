"""gifqa.py <gif> <out.jpg> [n] - n evenly spaced frames of a GIF as one sheet (to look at what was made)"""
import sys
from PIL import Image, ImageSequence
g = Image.open(sys.argv[1])
fr = [f.convert("RGB").copy() for f in ImageSequence.Iterator(g)]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
idx = [round(i * (len(fr) - 1) / (n - 1)) for i in range(n)]
w, h = fr[0].size
cols = 6
sh = Image.new("RGB", (cols * w, ((n + cols - 1) // cols) * h))
for k, i in enumerate(idx):
    sh.paste(fr[i], ((k % cols) * w, (k // cols) * h))
sh.save(sys.argv[2], quality=85)
print(len(fr), "frames", fr[0].size, "->", sh.size)

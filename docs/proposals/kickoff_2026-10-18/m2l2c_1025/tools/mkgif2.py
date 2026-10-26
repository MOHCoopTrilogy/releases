"""mkgif2.py <run_dir> <regex> <out.gif> [ms] [width] - frames whose name matches regex, sorted, to a GIF"""
import sys, os, re
from PIL import Image
d, rx, out = sys.argv[1:4]
ms = int(sys.argv[4]) if len(sys.argv) > 4 else 200
w = int(sys.argv[5]) if len(sys.argv) > 5 else 800
fs = sorted(f for f in os.listdir(d) if f.endswith('.jpg') and re.search(rx, f))
ims = []
for f in fs:
    im = Image.open(os.path.join(d, f)).convert('RGB'); im = im.resize((w, int(im.height * w / im.width)))
    ims.append(im.quantize(colors=96, dither=Image.NONE))
os.makedirs(os.path.dirname(out), exist_ok=True)
ims[0].save(out, save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=True)
print(len(fs), 'frames', os.path.getsize(out) // 1024, 'KB')

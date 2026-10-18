"""mkgif.py <run_dir> <prefix> <out.gif> - frames <prefix>_NNNN.jpg -> 960px GIF (ms per frame 200)."""
import sys, glob, os
from PIL import Image
d, pre, out = sys.argv[1:4]
fs = sorted(glob.glob(os.path.join(d, pre + "_*.jpg")))
ims = []
for f in fs:
    im = Image.open(f).convert("RGB"); w = 960; im = im.resize((w, int(im.height * w / im.width)))
    ims.append(im.quantize(colors=128, dither=Image.NONE))
os.makedirs(os.path.dirname(out), exist_ok=True)
ims[0].save(out, save_all=True, append_images=ims[1:], duration=200, loop=0, optimize=True)
print(len(fs), "frames", os.path.getsize(out) // 1024, "KB")

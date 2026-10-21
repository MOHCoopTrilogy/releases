"""mkgif2.py <out.gif> <ms> <width> <run_dir> <prefix> [<prefix> ...] - frames <prefix>_NNNN.jpg of each prefix, in order -> one GIF.
A prefix may end in :a-b to take frames a..b (inclusive, by index) and :a-b:s to step."""
import sys, glob, os
from PIL import Image
out, ms, w, d = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
fs = []
for spec in sys.argv[5:]:
    parts = spec.split(":")
    got = sorted(glob.glob(os.path.join(d, parts[0] + "_[0-9][0-9][0-9][0-9].jpg")))
    if len(parts) > 1:
        a, b = [int(x) for x in parts[1].split("-")]
        step = int(parts[2]) if len(parts) > 2 else 1
        got = got[a:b + 1:step]
    fs += got
ims = []
for f in fs:
    im = Image.open(f).convert("RGB")
    im = im.resize((w, int(im.height * w / im.width)))
    ims.append(im.quantize(colors=128, dither=Image.NONE))
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
ims[0].save(out, save_all=True, append_images=ims[1:], duration=ms, loop=0, optimize=True)
print(len(fs), "frames", os.path.getsize(out) // 1024, "KB ->", out)

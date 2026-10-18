"""make_gif.py <frame glob> <out.gif> [ms] - 960 px wide GIF from frame dumps, shrunk until under 7.5 MB."""
import glob, os, sys
from PIL import Image
fs = sorted(glob.glob(sys.argv[1]))
out = sys.argv[2]
ms = int(sys.argv[3]) if len(sys.argv) > 3 else 200
W = 960
for step in (1, 2):
    for w in (W, 800, 640):
        ims = [Image.open(f).convert("RGB") for f in fs[::step]]
        ims = [im.resize((w, int(im.height * w / im.width)), Image.LANCZOS).quantize(128, dither=Image.Dither.NONE) for im in ims]
        ims[0].save(out, save_all=True, append_images=ims[1:], duration=ms * step, loop=0, optimize=True)
        sz = os.path.getsize(out)
        if sz < 7.5e6:
            print(out, w, len(ims), "frames", round(sz / 1e6, 2), "MB")
            sys.exit(0)
print("could not get under 7.5MB")

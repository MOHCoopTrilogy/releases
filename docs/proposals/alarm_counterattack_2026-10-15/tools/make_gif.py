"""make_gif.py <out.gif> <ms_per_frame> <glob-or-dir> [step] - 960 px wide GIF from harness frame dumps (<= 8 MB), plus a QA contact strip.
Prints size and frame count; writes <out>_qa.jpg (every frame, small) so every frame can be inspected."""
import glob, os, sys
from PIL import Image

out, ms, pat = sys.argv[1], int(sys.argv[2]), sys.argv[3]
step = int(sys.argv[4]) if len(sys.argv) > 4 else 1
fs = sorted(glob.glob(pat))[::step]
from PIL import ImageStat
ims = []
for f in fs:
    im = Image.open(f).convert("RGB")
    r, g, b = ImageStat.Stat(im).mean
    if os.environ.get("SKIPRED") and r > 1.6 * g + 8:   # full-screen damage flash: a pop in a short GIF
        continue
    h = int(im.height * 960 / im.width)
    ims.append(im.resize((960, h), Image.LANCZOS))
pal = [i.quantize(colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for i in ims]
pal[0].save(out, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=True, disposal=2)
print(out, len(ims), "frames", round(os.path.getsize(out) / 1e6, 2), "MB", round(len(ims) * ms / 1000.0, 1), "s")
cols = 6
th = [i.resize((320, int(320 * i.height / i.width))) for i in ims]
rows = (len(th) + cols - 1) // cols
S = Image.new("RGB", (cols * 320, rows * th[0].height))
for k, t in enumerate(th):
    S.paste(t, ((k % cols) * 320, (k // cols) * th[0].height))
S.save(out.replace(".gif", "_qa.jpg"), quality=80)

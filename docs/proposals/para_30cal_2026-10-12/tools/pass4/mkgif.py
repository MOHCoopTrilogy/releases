"""mkgif.py <out.gif> <width> <crop x0,y0,x1,y1> <glob>:<every>:<ms>[:first[:last]] ... - a GIF from several frame runs,
each with its own step and frame time."""
import glob, os, sys
from PIL import Image
out, w = sys.argv[1], int(sys.argv[2])
crop = [int(v) for v in sys.argv[3].split(",")]
ims, dur = [], []
for spec in sys.argv[4:]:
    drive = ""
    if len(spec) > 2 and spec[1] == ":":
        drive, spec = spec[:2], spec[2:]
    p = spec.split(":")
    fs = sorted(glob.glob(drive + p[0]))
    a = int(p[3]) if len(p) > 3 else 0
    b = int(p[4]) if len(p) > 4 else len(fs)
    for f in fs[a:b][::int(p[1])]:
        im = Image.open(f).convert("RGB").crop(crop)
        ims.append(im.resize((w, int(im.height * w / im.width)), Image.LANCZOS))
        dur.append(int(p[2]))
pal = ims[len(ims) // 2].quantize(160, method=Image.MEDIANCUT, dither=Image.NONE)
q = [im.quantize(160, palette=pal, dither=Image.NONE) for im in ims]
q[0].save(out, save_all=True, append_images=q[1:], duration=dur, loop=0, optimize=True)
print(out, len(q), "frames", os.path.getsize(out) // 1024, "KB", "%.1fs" % (sum(dur) / 1000.0))

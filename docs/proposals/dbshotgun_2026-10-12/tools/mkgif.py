"""engine frames -> a GIF (for the user):  python tools/mkgif.py out.gif width ms_per_frame frame1.jpg frame2.jpg ..
    env GIF_COLORS (default 96), GIF_MAXMB (default 3.0: the width is stepped down by 10 % until the file fits)
One palette for the whole clip (taken from a strip of sample frames), so frames differ only where the picture does."""
import sys, os, io
from PIL import Image

out, w, ms = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
files = sys.argv[4:]
colors = int(os.environ.get('GIF_COLORS', 96))
maxmb = float(os.environ.get('GIF_MAXMB', 3.0))
src = [Image.open(f).convert('RGB') for f in files]
while True:
    h = round(src[0].height * w / src[0].width)
    small = [im.resize((w, h), Image.LANCZOS) for im in src]
    step = max(1, len(small) // 8)
    strip = Image.new('RGB', (w, h * len(small[::step])))
    for i, im in enumerate(small[::step]):
        strip.paste(im, (0, i * h))
    pal = strip.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    fr = [im.quantize(palette=pal, dither=Image.NONE) for im in small]
    buf = io.BytesIO()
    fr[0].save(buf, format='GIF', save_all=True, append_images=fr[1:], duration=ms, loop=0, optimize=False)
    if buf.tell() <= maxmb * 1024 * 1024 or w < 240:
        break
    w = int(w * 0.9)
open(out, 'wb').write(buf.getvalue())
print('wrote', out, len(fr), 'frames', '%d px wide' % w, '%.2f MB' % (buf.tell() / 1048576.0))

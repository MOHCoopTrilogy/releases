"""make_gifs.py <run dir> <out media dir>: the ring drain (rf*.tga) and the heal-bar fill (hf*.tga) as 960 px GIFs.
Each frame is a 480x270 NATIVE-pixel crop (ring: round the crosshair; bar: round the bar) scaled 2x with bicubic, so the
edge quality in the GIF is the engine's, not a downscale of the whole 1080p picture. Also writes a montage PNG of every
frame for QA."""
import os, sys
from PIL import Image

run, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
CROPS = {"rf": ((780, 400, 1140, 680), 4), "hf": ((760, 395, 1240, 665), 8)}   # prefix -> (box, fps)


def build(prefix, name):
    box, fps = CROPS[prefix]
    import re, datetime
    ts = [datetime.datetime.strptime(m.group(1), "%H:%M:%S") for m in re.finditer(r"\[\d{4}-\d\d-\d\d (\d\d:\d\d:\d\d) UTC[^\]]*\] Wrote screenshots/%s\d+\.tga" % prefix, open(os.path.join(run, "qconsole.log"), encoding="latin-1").read())]
    if len(ts) > 4:     # real capture rate from the engine's own log (1 s resolution, so averaged over the whole burst)
        fps = max(2.0, min(12.0, (len(ts) - 1) / max(1.0, (ts[-1] - ts[0]).total_seconds())))
        print(prefix, "capture fps", round(fps, 2))
    files = sorted(f for f in os.listdir(run) if f.startswith(prefix) and f.endswith(".tga"))
    if prefix == "rf":
        files = files[3:]      # the first frames still ease from the previous test value (s_selfShown): drop them
    if not files:
        print("no frames for", prefix)
        return
    W = 960
    bw, bh = box[2] - box[0], box[3] - box[1]
    frames = [Image.open(os.path.join(run, f)).convert("RGB").crop(box).resize((W, W * bh // bw), Image.BICUBIC) for f in files]
    # ONE shared palette (from a strip of every 4th frame) so frames differ only where the picture does
    strip = Image.new("RGB", (frames[0].width, frames[0].height * len(frames[::4])))
    for i, f in enumerate(frames[::4]):
        strip.paste(f, (0, i * f.height))
    base = strip.quantize(128, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = [f.quantize(palette=base, dither=Image.NONE) for f in frames]
    path = os.path.join(out, name)
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=int(1000 / fps), loop=0, optimize=False)
    print(path, len(frames), "frames", os.path.getsize(path) // 1024, "KB")
    cols = 6
    rows = (len(frames) + cols - 1) // cols
    m = Image.new("RGB", (cols * 240, rows * 135))
    for i, f in enumerate(frames):
        m.paste(f.resize((240, 135)), ((i % cols) * 240, (i // cols) * 135))
    m.save(os.path.join(out, name.replace(".gif", "_frames.png")))


build("rf", "ring_drain_hd.gif")
build("hf", "heal_bar_fill_hd.gif")

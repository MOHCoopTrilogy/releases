"""sheet.py <out.jpg> <cols> <thumb_w> <file|glob> ... [every=N] [crop=x0,y0,x1,y1] - a contact sheet of frames.
gif:  sheet.py --gif <out.gif> <width> <ms> <glob> ... [every=N] [crop=...] [colors=N]"""
import glob, os, sys
from PIL import Image, ImageDraw
a = sys.argv[1:]
opts = dict(x.split("=", 1) for x in a if "=" in x and not os.path.exists(x) and "*" not in x.split("=")[0] and ":" not in x.split("=")[0])
a = [x for x in a if x.split("=")[0] not in opts]
every = int(opts.get("every", 1))
crop = [int(v) for v in opts["crop"].split(",")] if "crop" in opts else None


def files(pats):
    out = []
    for p in pats:
        out += sorted(glob.glob(p)) if "*" in p else [p]
    return out[::every]


def load(f):
    im = Image.open(f).convert("RGB")
    return im.crop(crop) if crop else im


if a[0] == "--gif":
    out, w, ms = a[1], int(a[2]), int(a[3])
    fs = files(a[4:])
    ims = []
    for f in fs:
        im = load(f)
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
        ims.append(im)
    n = int(opts.get("colors", 128))
    pal = ims[len(ims) // 2].quantize(n, method=Image.MEDIANCUT, dither=Image.NONE)
    q = [im.quantize(n, palette=pal, dither=Image.NONE) for im in ims]
    q[0].save(out, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True)
    print(out, len(q), "frames", os.path.getsize(out) // 1024, "KB")
else:
    out, cols, tw = a[0], int(a[1]), int(a[2])
    fs = files(a[3:])
    ims = [load(f) for f in fs]
    th = int(ims[0].height * tw / ims[0].width)
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
    d = ImageDraw.Draw(sh)
    for i, im in enumerate(ims):
        x, y = (i % cols) * tw, (i // cols) * th
        sh.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        lab = os.path.basename(fs[i]).rsplit(".", 1)[0][-14:]
        d.rectangle([x, y, x + 7 * len(lab) + 4, y + 12], fill=(0, 0, 0))
        d.text((x + 2, y), lab, fill=(255, 255, 0))
    sh.save(out, quality=85)
    print(out, len(ims), "frames", sh.size)

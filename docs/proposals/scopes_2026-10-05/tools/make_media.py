"""make_media.py - before/after GIFs and every-frame contact sheets from run_scopes.py captures.

    python make_media.py gif   <before_sess> <after_sess> <gun> <out.gif> [--w 640]
    python make_media.py sheet <sess> <gun> <mode> <out.jpg> [--thumb 192]
    python make_media.py still <sess> <gun> <mode> <frame> <out.jpg>

Frame timing follows run_scopes.capture (fixedtime 16): every-frame segments are 16 ms of game time per frame, the
breathing / held-breath segments 64 ms, the exhale 32 ms. GIFs keep that real time (every-frame segments are
shown at every 2nd frame, 32 ms) and carry a small segment caption so the viewer knows what is happening.
"""
import os, sys, glob, argparse
from PIL import Image, ImageDraw, ImageFont

RUNS = r"G:\mohaa-scopes\runs"
FULL = [("hip", 3, 16), ("scope in", 30, 16), ("scan right", 45, 16), ("stop", 12, 16), ("scan left", 45, 16),
        ("settle", 20, 16), ("breathing", 40, 64), ("breath held", 30, 64), ("exhale", 10, 32), ("scope out", 24, 16)]
FAST = [("hip", 3, 16), ("scope in", 30, 16), ("scoped", 6, 16), ("scope out", 24, 16)]


def frames(sess, gun, mode):
    fs = sorted(glob.glob(os.path.join(RUNS, sess, "sc__%s__%s__%s__*.jpg" % (sess, gun, mode))))
    return fs


def layout(n):
    for lay in (FULL, FAST):
        if sum(c for _, c, _ in lay) == n:
            out = []
            for name, c, ms in lay:
                out += [(name, ms)] * c
            return out
    return [("", 16)] * n


def font(sz):
    for f in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def gif(a):
    fb, fa = frames(a.before, a.gun, "before"), frames(a.after, a.gun, "after")
    assert fb and fa and len(fb) == len(fa), (len(fb), len(fa))
    lay = layout(len(fa))
    w = a.w
    h = w * 9 // 16
    f = font(max(12, w // 32))
    out, dur = [], []
    k = 0
    while k < len(fa):
        name, ms = lay[k]
        step = (2 if name in ("scope in", "scope out") else 3) if ms == 16 else (2 if ms == 64 else 1)
        im = Image.new("RGB", (w * 2 + 6, h + 0), (20, 20, 20))
        im.paste(Image.open(fb[k]).convert("RGB").resize((w, h), Image.LANCZOS), (0, 0))
        im.paste(Image.open(fa[k]).convert("RGB").resize((w, h), Image.LANCZOS), (w + 6, 0))
        d = ImageDraw.Draw(im)
        for x, t in ((8, "TODAY"), (w + 14, "NEW")):
            d.text((x + 1, 7), t, fill=(0, 0, 0), font=f)
            d.text((x, 6), t, fill=(255, 235, 160), font=f)
        d.text((w * 2 + 6 - 8 - d.textlength(name, font=f) + 1, h - 8 - f.size + 1), name, fill=(0, 0, 0), font=f)
        d.text((w * 2 + 6 - 8 - d.textlength(name, font=f), h - 8 - f.size), name, fill=(235, 235, 235), font=f)
        out.append(im.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE))
        dur.append(ms * step)
        k += step
    dur[-1] = 900
    out[0].save(a.out, save_all=True, append_images=out[1:], duration=dur, loop=0, optimize=True, disposal=1)
    print("gif", a.out, len(out), "frames", "%.1f MB" % (os.path.getsize(a.out) / 1e6))


def sheet(a):
    fs = frames(a.sess, a.gun, a.mode)
    assert fs, "no frames"
    lay = layout(len(fs))
    tw = a.thumb
    th = tw * 9 // 16
    cols = 12
    rows = (len(fs) + cols - 1) // cols
    im = Image.new("RGB", (cols * tw, rows * (th + 2)), (0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font(11)
    for i, p in enumerate(fs):
        x, y = (i % cols) * tw, (i // cols) * (th + 2)
        im.paste(Image.open(p).convert("RGB").resize((tw, th), Image.BILINEAR), (x, y))
        d.text((x + 3, y + 2), "%d %s" % (i, lay[i][0]), fill=(255, 255, 0), font=f)
    im.save(a.out, quality=82)
    print("sheet", a.out, len(fs), "frames")


def still(a):
    fs = frames(a.sess, a.gun, a.mode)
    Image.open(fs[a.frame]).save(a.out, quality=92)
    print("still", a.out)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("gif"); g.add_argument("before"); g.add_argument("after"); g.add_argument("gun")
    g.add_argument("out"); g.add_argument("--w", type=int, default=640)
    s = sub.add_parser("sheet"); s.add_argument("sess"); s.add_argument("gun"); s.add_argument("mode")
    s.add_argument("out"); s.add_argument("--thumb", type=int, default=192)
    t = sub.add_parser("still"); t.add_argument("sess"); t.add_argument("gun"); t.add_argument("mode")
    t.add_argument("frame", type=int); t.add_argument("out")
    a = ap.parse_args()
    {"gif": gif, "sheet": sheet, "still": still}[a.cmd](a)


if __name__ == "__main__":
    main()

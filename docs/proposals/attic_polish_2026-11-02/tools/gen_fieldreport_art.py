"""gen_fieldreport_art.py <out.png> - the FIELD REPORT dispatch board's face (v1.10.62; the What's New card's in-world home).

A plywood board screwed to the post by the long desk: FIELD REPORT stencilled across the top in olive-drab paint (the Army's own
stencil letter), and two message forms pinned below it (a ruled form with a small printed header, a carbon copy behind it), each
with a drawing pin.  No filler text: the forms are blank ruled forms, the only words are FIELD REPORT and the printed form
headers.  Drawn with PIL (no generated imagery); 1024 x 1365 (the board is 0.60 x 0.80 m)."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = sys.argv[1]
W, H = 1024, 1365
FD = r"C:\Windows\Fonts"
rng = np.random.default_rng(1944)


def grain(h, w, base, amp, seed, stretch=8):
    r = np.random.default_rng(seed)
    g = r.normal(0, 1, (h, w // stretch + 1)).astype(np.float32)
    g = np.asarray(Image.fromarray(((g * 40) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) - 128
    blot = np.asarray(Image.fromarray((r.random((9, 7)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 - 0.5
    return np.array(base, np.float32)[None, None, :] + (g * amp / 40 + blot * 18)[..., None]


# plywood: horizontal grain, darker weathered edges, four screws
img = grain(H, W, (150, 118, 80), 14, 1)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
edge = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy])
img -= (np.clip(1 - edge / 40.0, 0, 1) ** 2 * 45)[..., None]
board = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
d = ImageDraw.Draw(board)
for sx, sy in ((40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)):
    d.ellipse((sx - 9, sy - 9, sx + 9, sy + 9), fill=(70, 66, 60))
    d.line((sx - 6, sy, sx + 6, sy), fill=(40, 38, 34), width=3)

# FIELD / REPORT stencilled in olive-drab paint on two lines (as large as the board allows: it has to read at 720p from across the
# room), slightly uneven coverage like a hand-held stencil
TOP = 470
stencil = Image.new("L", (W, TOP), 0)
sd = ImageDraw.Draw(stencil)
f = ImageFont.truetype(os.path.join(FD, "STENCIL.TTF"), 240)
while max(sd.textlength(t, font=f) for t in ("FIELD", "REPORT")) > W - 120:
    f = ImageFont.truetype(os.path.join(FD, "STENCIL.TTF"), f.size - 6)
for t, y in (("FIELD", 50), ("REPORT", 50 + f.size * 0.92)):
    sd.text(((W - sd.textlength(t, font=f)) / 2, y), t, font=f, fill=255)
cov = np.asarray(stencil, np.float32) / 255
cov *= np.clip(0.80 + rng.normal(0, 0.12, cov.shape), 0.45, 1.0)
cov = np.asarray(Image.fromarray((cov * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
a = np.asarray(board, np.float32)
paint = np.array([72, 78, 46], np.float32)
a[0:TOP] = a[0:TOP] * (1 - cov[..., None]) + paint * cov[..., None]
board = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def form(w, h, seed, header=True):
    p = Image.fromarray(np.clip(grain(h, w, (226, 218, 196), 5, seed, 2), 0, 255).astype(np.uint8), "RGB")
    pd = ImageDraw.Draw(p)
    ink = (60, 58, 70)
    if header:
        fh = ImageFont.truetype(os.path.join(FD, "BOD_B.TTF"), 34)
        for t, y in (("WAR DEPARTMENT", 26), ("MESSAGE", 66)):
            pd.text(((w - pd.textlength(t, font=fh)) / 2, y), t, font=fh, fill=ink)
        pd.line((30, 112, w - 30, 112), fill=ink, width=3)
    for k in range(10):
        y = 150 + k * 52
        if y > h - 40:
            break
        pd.line((40, y, w - 40, y), fill=(150, 160, 185), width=2)
    pd.rectangle((0, 0, w - 1, h - 1), outline=(170, 160, 140), width=2)
    return p


back = form(520, 640, 7, header=False).rotate(-3.5, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0))
front = form(560, 700, 8).rotate(1.8, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0))


def paste_shadowed(dst, src, x, y):
    m = Image.fromarray((np.asarray(src).sum(2) > 0).astype(np.uint8) * 255)
    sh = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 110), (x + 8, y + 10), m)
    dst = Image.alpha_composite(dst.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(7))).convert("RGB")
    dst.paste(src, (x, y), m)
    return dst


board = paste_shadowed(board, back, 330, 540)
board = paste_shadowed(board, front, 170, 510)
d = ImageDraw.Draw(board)
for px, py, col in ((450, 540, (150, 30, 26)), (720, 570, (40, 70, 140))):
    d.ellipse((px - 14, py - 14, px + 14, py + 14), fill=col)
    d.ellipse((px - 6, py - 9, px + 1, py - 3), fill=tuple(min(255, c + 80) for c in col))
board.save(out)
print("field report board ->", out, board.size)

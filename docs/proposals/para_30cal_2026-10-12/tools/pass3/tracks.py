"""tracks.py <out.gif> <title> <before_run> <after_run> <refx> <refy> [span=1300] [step=2] - BEFORE | AFTER, drawn from the
positions the test driver logged once a second (P3 POS lines in each run's qconsole.log): the squad's men 1-5 (blue,
numbered; trail = the last 20s), the living Germans within 1800u (red), the hold point (yellow cross, 300u ring).
A plot of logged positions - NOT a game capture."""
import os, re, sys
from PIL import Image, ImageDraw
out, title, rb, ra = sys.argv[1:5]
rx, ry = float(sys.argv[5]), float(sys.argv[6])
opt = dict(a.split("=", 1) for a in sys.argv[7:])
SPAN = float(opt.get("span", 1300))
STEP = int(opt.get("step", 2))
W = 360
RUNS = "G:/mohaa-hudfeed5/runs"


def load(run):
    t = open(os.path.join(RUNS, run, "qconsole.log"), "rb").read().decode("latin-1")
    fr = {}
    for m in re.finditer(r"P3 POS t=(\d+)([^\r\n]*)", t):
        men, ger = {}, []
        for k, x, y in re.findall(r" (\d):(-?\d+),(-?\d+)", m.group(2)):
            men[int(k)] = (float(x), float(y))
        for x, y in re.findall(r" g:(-?\d+),(-?\d+)", m.group(2)):
            ger.append((float(x), float(y)))
        fr[int(m.group(1))] = (men, ger)
    tele = len(re.findall(r"P3 TELE", t)) if "PSQ t=" not in t or "rescue" not in t else len(re.findall(r"PSQ t=[\d.]+ rescue", t))
    return fr, tele


def t0(fr):
    ts = sorted(t for t, (men, g) in fr.items() if men)
    return ts[0] if ts else 0


def xy(p):
    return (W / 2 + (p[0] - rx) / SPAN * (W / 2), W / 2 - (p[1] - ry) / SPAN * (W / 2))


def panel(fr, start, t, label):
    im = Image.new("RGB", (W, W + 34), (24, 26, 30))
    d = ImageDraw.Draw(im)
    for r in (300, 600, 900, 1200):
        rr = r / SPAN * (W / 2)
        d.ellipse([W / 2 - rr, W / 2 - rr, W / 2 + rr, W / 2 + rr], outline=(52, 56, 62))
    d.line([W / 2 - 7, W / 2, W / 2 + 7, W / 2], fill=(240, 210, 60), width=2)
    d.line([W / 2, W / 2 - 7, W / 2, W / 2 + 7], fill=(240, 210, 60), width=2)
    cur = fr.get(start + t)
    k = start + t
    while cur is None and k > start:
        k -= 1
        cur = fr.get(k)
    if cur:
        for back in range(20, 0, -1):
            a, b = fr.get(start + t - back), fr.get(start + t - back + 1)
            if a and b:
                for m in a[0]:
                    if m in b[0]:
                        d.line([xy(a[0][m]), xy(b[0][m])], fill=(70, 110, 170), width=1)
        for g in cur[1]:
            x, y = xy(g)
            d.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(210, 60, 50))
        far = 0
        for m, p in cur[0].items():
            x, y = xy(p)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(90, 170, 255), outline=(255, 255, 255))
            d.text((x + 6, y - 6), str(m), fill=(255, 255, 255))
            if m <= 4:
                far = max(far, ((p[0] - rx) ** 2 + (p[1] - ry) ** 2) ** 0.5)
        d.text((6, W + 2), "%s   t=%3ds   men alive %d   farthest %4du" % (label, t, len(cur[0]), far), fill=(230, 230, 230))
    else:
        d.text((6, W + 2), label, fill=(230, 230, 230))
    d.text((6, W + 17), "blue = squad   red = Germans   cross = hold point   rings 300u", fill=(150, 150, 150))
    return im


fb, tb = load(rb)
fa, ta = load(ra)
sb, sa = t0(fb), t0(fa)
n = min(max(fb) - sb, max(fa) - sa, int(opt.get("secs", 100)))
frames = []
for t in range(0, n, STEP):
    im = Image.new("RGB", (2 * W + 6, W + 34 + 18), (10, 10, 10))
    ImageDraw.Draw(im).text((6, 3), title + "  (plotted from logged positions, not a game capture)", fill=(255, 255, 255))
    im.paste(panel(fb, sb, t, "BEFORE"), (0, 18))
    im.paste(panel(fa, sa, t, "AFTER"), (W + 6, 18))
    frames.append(im.convert("P", palette=Image.ADAPTIVE, colors=32))
frames[0].save(out, save_all=True, append_images=frames[1:], duration=250, loop=0, optimize=True)
frames[len(frames) * 2 // 3].convert("RGB").save(out[:-4] + "_still.jpg", quality=90)
print(out, len(frames), "frames", os.path.getsize(out) // 1024, "KB")

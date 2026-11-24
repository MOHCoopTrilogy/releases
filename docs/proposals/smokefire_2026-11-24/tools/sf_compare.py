"""sf_compare.py <runs/tag dir> <outdir> [A B]  - old|new media from an sf_run.py capture (same replay, same moments).

Per effect (user 2026-11-24: "your screenshots were mostly black marks on the ground"):
  <k>_<name>_HERO.jpg   ONE side-by-side still at the most dramatic moment (largest change from the clean frame,
                        both sides summed), cropped in on the effect
  <k>_<name>.gif        opens ON the hero frame (a phone preview shows the subject), then replays from a beat before
                        the blast; the first 2 s are slowed down (each 100 ms capture held 250 ms), later frames 400 ms
  <k>_<name>.jpg        the sheet of all non-burst moments (for reading, not for phones)
Crop: SF_CROP (default 0.62 of the frame, centred SF_CY of the height down, default 0.52) - the effect fills the frame.
Labels: SF_LA / SF_LB (defaults "OLD - v1.10.91" / "NEW")."""
import os, re, sys
from PIL import Image, ImageChops, ImageDraw, ImageStat

src, out = sys.argv[1], sys.argv[2]
va, vb = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("A", "B")
LA, LB = os.environ.get("SF_LA", "OLD - v1.10.91"), os.environ.get("SF_LB", "NEW")
CROP, CY = float(os.environ.get("SF_CROP", "0.62")), float(os.environ.get("SF_CY", "0.52"))
W = int(os.environ.get("SF_W", "560"))
os.makedirs(out, exist_ok=True)
rx = re.compile(r"^.+?_(%s|%s)_(\d+)_(.+)_(\d{4,5})\.jpg$" % (va, vb))
F = {}
for v in (va, vb):
    d = os.path.join(src, v)
    for fn in os.listdir(d):
        m = rx.match(fn)
        if m:
            F.setdefault((int(m.group(2)), m.group(3)), {}).setdefault(int(m.group(4)), {})[v] = os.path.join(d, fn)


def crop(im):
    w, h = im.size
    cw, ch = int(w * CROP), int(h * CROP)
    cx, cy = w // 2, int(h * CY)
    x0, y0 = max(0, cx - cw // 2), max(0, min(h - ch, cy - ch // 2))
    return im.crop((x0, y0, x0 + cw, y0 + ch))


def load(p, w):
    im = crop(Image.open(p).convert("RGB"))
    return im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)


def pair(a, b, label, w=W):
    A, B = load(a, w), load(b, w)
    im = Image.new("RGB", (2 * w + 6, A.height + 26), (16, 16, 16))
    im.paste(A, (0, 26)); im.paste(B, (w + 6, 26))
    d = ImageDraw.Draw(im)
    d.text((8, 6), LA, fill=(220, 220, 220)); d.text((w + 14, 6), LB, fill=(255, 210, 120))
    d.text((2 * w - 150, 6), label, fill=(200, 200, 200))
    return im


def change(p0, p):
    a, b = crop(Image.open(p0).convert("L")), crop(Image.open(p).convert("L"))
    return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]


for (k, name), times in sorted(F.items()):
    both = sorted(t for t, vv in times.items() if va in vv and vb in vv)
    if len(both) < 2 or both[0] != 0:
        continue
    t0 = both[0]
    score = {t: change(times[t0][va], times[t][va]) + change(times[t0][vb], times[t][vb]) for t in both[1:]}
    hero = max(score, key=score.get)
    lab = lambda t: "%s  +%.1f s" % (name, t / 1000.0)   # noqa: E731
    pair(times[hero][va], times[hero][vb], lab(hero), w=900).save(os.path.join(out, "%02d_%s_HERO.jpg" % (k, name)), quality=90)
    seq = [t for t in both if t <= 6000]
    if len(seq) > 6:
        fr, du = [pair(times[hero][va], times[hero][vb], lab(hero))], [1400]
        for t in seq:
            fr.append(pair(times[t][va], times[t][vb], lab(t)))
            du.append(250 if 0 < t <= 2000 else (300 if t == 0 else 400))
        fr[0].save(os.path.join(out, "%02d_%s.gif" % (k, name)), save_all=True, append_images=fr[1:], duration=du, loop=0,
                   optimize=True)
    rows = [pair(times[t][va], times[t][vb], lab(t)) for t in both if t == 0 or t == hero or t not in range(1, 3001, 100)]
    sh = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r_ in rows:
        sh.paste(r_, (0, y)); y += r_.height
    sh.save(os.path.join(out, "%02d_%s.jpg" % (k, name)), quality=82)
    print("%s hero +%.1f s, %d frames" % (name, hero / 1000.0, len(both)))

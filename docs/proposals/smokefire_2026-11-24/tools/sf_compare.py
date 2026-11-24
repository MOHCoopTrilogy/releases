"""sf_compare.py <runs/tag dir> <outdir> [A B]  - side-by-side A|B sheets and GIFs from an sf_run.py capture.
Frames are matched by shot index + time stamp in the file name (<tag>_<variant>_<k>_<name>_<ms>.jpg), so the left and
right halves of every frame are the same moment of the same replay. Sheets: the non-burst times; GIFs: the burst."""
import os, re, sys
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
va, vb = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("A", "B")
os.makedirs(out, exist_ok=True)
rx = re.compile(r"^.+?_(%s|%s)_(\d+)_(.+)_(\d{4})\.jpg$" % (va, vb))
F = {}
for v in (va, vb):
    d = os.path.join(src, v)
    for fn in os.listdir(d):
        m = rx.match(fn)
        if m:
            F.setdefault((int(m.group(2)), m.group(3)), {}).setdefault(int(m.group(4)), {})[v] = os.path.join(d, fn)


def pair(a, b, label, w=int(os.environ.get("SF_W", "640"))):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    h = int(A.height * w / A.width)
    A, B = A.resize((w, h)), B.resize((w, h))
    im = Image.new("RGB", (2 * w + 4, h + 22), (20, 20, 20))
    im.paste(A, (0, 22)); im.paste(B, (w + 4, 22))
    d = ImageDraw.Draw(im)
    d.text((6, 4), "%s  (before: v1.10.91)" % va, fill=(230, 230, 230))
    d.text((w + 10, 4), "%s  (after: Phase 0)" % vb, fill=(230, 230, 230))
    d.text((2 * w - 120, 4), label, fill=(255, 210, 120))
    return im


for (k, name), times in sorted(F.items()):
    both = sorted(t for t, vv in times.items() if va in vv and vb in vv)
    if not both:
        continue
    steps = [b - a for a, b in zip(both, both[1:])]
    burst = [t for i, t in enumerate(both) if 0 < t <= 3000 and (i + 1 < len(both) and both[i + 1] - t <= 150 or i > 0 and t - both[i - 1] <= 150)]
    rest = [t for t in both if t not in burst]
    if burst:
        fr = [pair(times[t][va], times[t][vb], "%s +%.1f s" % (name, t / 1000.0)) for t in [0] + burst if t in times and va in times[t] and vb in times[t]]
        fr[0].save(os.path.join(out, "%02d_%s.gif" % (k, name)), save_all=True, append_images=fr[1:], duration=120, loop=0)
    sel = [0] + rest if 0 in both else rest
    if burst:
        sel = sorted(set(sel + burst[::max(1, len(burst) // 4)]))
    rows = [pair(times[t][va], times[t][vb], "%s +%.1f s" % (name, t / 1000.0)) for t in sel]
    if rows:
        sh = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)), (0, 0, 0))
        y = 0
        for r in rows:
            sh.paste(r, (0, y)); y += r.height
        sh.save(os.path.join(out, "%02d_%s.jpg" % (k, name)), quality=85)
    print(name, "frames", len(both), "burst", len(burst))

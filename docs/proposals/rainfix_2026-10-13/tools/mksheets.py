"""mksheets.py <rundir> <outdir> <prefix> - evidence from a run03 'views' / 'gif' run:
  <prefix>_<view>_before_after.jpg   one still before (left) and after (right), labelled, full height
  <prefix>_views_sheet.jpg           every view, before | after, small
  <prefix>_downpour_before_after.gif the 'gif' plan's stills, before (left) / after (right)
Stills are engine screenshots, one per console step (about 0.7 s apart) - the GIF is a sequence of separate frames
of the same fixed view, not consecutive frames."""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
rundir, outdir, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(outdir, exist_ok=True)
res = json.load(open(os.path.join(rundir, "results.json")))
try:
    FONT = ImageFont.truetype("arial.ttf", 22)
    SMALL = ImageFont.truetype("arial.ttf", 15)
except Exception:
    FONT = SMALL = ImageFont.load_default()


def label(im, text, font=FONT):
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=font)
    d.rectangle((0, 0, w + 14, font.size + 10), fill=(0, 0, 0))
    d.text((7, 4), text, fill=(255, 255, 255), font=font)
    return im


def pair(fb, fa, width, tb="before", ta="after", font=FONT):
    a = Image.open(fb).convert("RGB")
    b = Image.open(fa).convert("RGB")
    h = int(a.size[1] * width / a.size[0])
    a = label(a.resize((width, h), Image.LANCZOS), tb, font)
    b = label(b.resize((width, h), Image.LANCZOS), ta, font)
    s = Image.new("RGB", (width * 2 + 6, h), (255, 255, 255))
    s.paste(a, (0, 0))
    s.paste(b, (width + 6, 0))
    return s


rows = {r["tag"]: r for r in res["rows"]}
views = [t[2:-7] for t in rows if t.startswith("v_") and t.endswith("_before")]
small = []
for v in views:
    fb = rows["v_%s_before" % v]["files"]
    fa = rows["v_%s_after" % v]["files"]
    if not fb or not fa:
        continue
    fb, fa = os.path.join(rundir, fb[0]), os.path.join(rundir, fa[0])
    W = Image.open(fb).size[0]
    big = pair(fb, fa, min(W, 1280), "before - " + v.replace("_", " "), "after - " + v.replace("_", " "))
    big.save(os.path.join(outdir, "%s_%s_before_after.jpg" % (prefix, v)), quality=90)
    small.append(pair(fb, fa, 560, "before - " + v.replace("_", " "), "after", SMALL))
for c in range(0, len(small), 4):
    part = small[c:c + 4]
    h = sum(s.size[1] + 6 for s in part)
    sh = Image.new("RGB", (part[0].size[0], h), (255, 255, 255))
    y = 0
    for s in part:
        sh.paste(s, (0, y))
        y += s.size[1] + 6
    sh.save(os.path.join(outdir, "%s_views_sheet_%d.jpg" % (prefix, c // 4 + 1)), quality=88)
    print("sheet", c // 4 + 1, sh.size, len(part), "views")

gb = sorted(f for f in os.listdir(rundir) if f.startswith("g_before_"))
ga = sorted(f for f in os.listdir(rundir) if f.startswith("g_after_"))
if gb and ga:
    frames = []
    for b, a in zip(gb, ga):
        frames.append(pair(os.path.join(rundir, b), os.path.join(rundir, a), 640, "before", "after", SMALL)
                      .convert("P", palette=Image.ADAPTIVE, colors=128))
    frames[0].save(os.path.join(outdir, "%s_downpour_before_after.gif" % prefix), save_all=True,
                   append_images=frames[1:], duration=90, loop=0, optimize=False)
    print("gif", len(frames), "frames")

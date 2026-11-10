"""make_contacts.py <runs dir> <out dir> - one before|after contact sheet per resolution from the survey runs (sv_before_<res>, sv_after_<res>)
plus a 100% crop sheet of the defects that are too small to judge in a thumbnail."""
import os, sys
from PIL import Image, ImageDraw, ImageFont

runs, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
F = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 18)
FB = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 22)
NAMES = {"720": "1280x720", "1080": "1920x1080 (= 2560x1440 layout)", "219": "1920x804 (= 3440x1440, 21:9)", "43": "1440x1080 (4:3)", "1440": "2560x1440", "3440": "3440x1440 (21:9)"}


def shots(tag, res):
    d = os.path.join(runs, "sv_%s_%s" % (tag, res))
    return {f.split("_", 3)[3].rsplit(".", 1)[0]: os.path.join(d, f) for f in os.listdir(d) if f.endswith(".tga")} if os.path.isdir(d) else {}


for res in ("720", "1080", "1440", "3440", "219", "43"):
    b, a = shots("before", res), shots("after", res)
    keys = sorted(set(b) | set(a))
    if not keys:
        continue
    tw = 520
    sample = Image.open((a or b)[keys[0]])
    th = int(tw * sample.height / sample.width)
    W = 16 + 2 * (tw + 12) + 210
    H = 60 + len(keys) * (th + 12)
    S = Image.new("RGB", (W, H), (22, 22, 22))
    d = ImageDraw.Draw(S)
    d.text((16, 14), "attic main menu  %s   BEFORE  |  AFTER" % NAMES[res], font=FB, fill=(235, 225, 200))
    for i, k in enumerate(keys):
        y = 60 + i * (th + 12)
        d.text((16, y + th // 2 - 10), k, font=F, fill=(220, 220, 200))
        for j, src in enumerate((b, a)):
            if k in src:
                S.paste(Image.open(src[k]).convert("RGB").resize((tw, th), Image.LANCZOS), (226 + j * (tw + 12), y))
    p = os.path.join(out, "contact_%s.jpg" % res)
    S.save(p, quality=86)
    print(p, S.size, len(keys), "rows")

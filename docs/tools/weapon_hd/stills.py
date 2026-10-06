"""Zoom sheets from a run_ingame.py batch: python docs/tools/weapon_hd/stills.py <tag> <outdir>
One JPG per gun: [before idle | after idle] over [before ADS | after ADS], each cropped to the gun region at 1:1."""
import os, sys, glob
from PIL import Image, ImageDraw
RUNS = r"G:/mohaa-weaponhd/runs"
tag, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
BOX = {"1p_idle": (0.40, 0.45, 0.95, 1.0), "1p_ads": (0.25, 0.35, 0.75, 1.0)}
guns = sorted({os.path.basename(p).split("__")[2] for p in glob.glob(os.path.join(RUNS, tag + "after", "whd__*.png"))})
n = 0
for g in guns:
    rows = []
    for v, b in BOX.items():
        pair = []
        for s in ("before", "after"):
            p = os.path.join(RUNS, tag + s, "whd__%s%s__%s__%s.png" % (tag, s, g, v))
            if not os.path.exists(p):
                break
            im = Image.open(p).convert("RGB")
            W, H = im.size
            pair.append(im.crop((int(b[0] * W), int(b[1] * H), int(b[2] * W), int(b[3] * H))))
        if len(pair) == 2:
            rows.append(pair)
    if not rows:
        continue
    cw = max(r[0].size[0] for r in rows)
    sheet = Image.new("RGB", (cw * 2 + 8, sum(r[0].size[1] for r in rows) + 8 * len(rows)), "white")
    y = 0
    for a, c in rows:
        sheet.paste(a, (0, y)); sheet.paste(c, (cw + 8, y))
        d = ImageDraw.Draw(sheet)
        d.text((6, y + 6), "BEFORE", fill=(255, 255, 0)); d.text((cw + 14, y + 6), "AFTER (HD)", fill=(255, 255, 0))
        y += a.size[1] + 8
    sheet.save(os.path.join(out, "%s_%s.jpg" % (tag, g)), quality=90)
    n += 1
print(n, "gun sheets ->", out)

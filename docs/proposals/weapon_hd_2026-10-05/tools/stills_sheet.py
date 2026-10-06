"""Before/after (/heavy) still sheets from an in-engine run.

    python stills_sheet.py before after                     run 1
    python stills_sheet.py before2 after2 heavy2            run 2

For every gun x view: full frames side by side (scaled) -> stills/full_<g>_<view>.jpg, and a 1.5x crop of the gun
region of each session side by side -> stills/zoom_<g>_<view>.jpg. Raw PNGs stay in G:/mohaa-weaponhd/runs/<session>.
"""
import os, sys, glob
from PIL import Image, ImageDraw
RUNS = r"G:/mohaa-weaponhd/runs"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stills")
os.makedirs(OUT, exist_ok=True)
BOX = {"1p_idle": (0.36, 0.55, 0.66, 1.0), "1p_ads": (0.30, 0.45, 0.70, 1.0), "3p_close": (0.30, 0.35, 0.75, 0.95),
       "3p_wide": (0.30, 0.30, 0.75, 0.95), "3p_a": (0.25, 0.30, 0.80, 1.0), "3p_b": (0.20, 0.30, 0.80, 1.0),
       "3p_c": (0.25, 0.30, 0.80, 1.0)}
sess = sys.argv[1:]
n = 0
for g in ("kar98", "thompson", "colt45"):
    for v, b in BOX.items():
        ims = []
        for s in sess:
            p = os.path.join(RUNS, s, "whd__%s__%s__%s.png" % (s, g, v))
            if os.path.exists(p):
                ims.append((s, Image.open(p).convert("RGB")))
        if len(ims) != len(sess):
            continue
        W, H = ims[0][1].size
        bx = (int(b[0] * W), int(b[1] * H), int(b[2] * W), int(b[3] * H))
        crops = [(s, im.crop(bx)) for s, im in ims]
        cw, ch = crops[0][1].size
        z = Image.new("RGB", (cw * len(crops) + 8 * (len(crops) - 1), ch), "white")
        for i, (s, c) in enumerate(crops):
            z.paste(c, (i * (cw + 8), 0))
            ImageDraw.Draw(z).text((i * (cw + 8) + 6, 6), s, fill=(255, 255, 0))
        z.resize((z.size[0] * 3 // 2, z.size[1] * 3 // 2), Image.LANCZOS).save(os.path.join(OUT, "zoom_%s_%s.jpg" % (g, v)), quality=92)
        f = Image.new("RGB", (W // 2 * len(ims) + 8 * (len(ims) - 1), H // 2), "white")
        for i, (s, im) in enumerate(ims):
            f.paste(im.resize((W // 2, H // 2), Image.LANCZOS), (i * (W // 2 + 8), 0))
        f.save(os.path.join(OUT, "full_%s_%s.jpg" % (g, v)), quality=88)
        n += 1
print(n, "views")

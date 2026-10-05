"""sweep_sheets.py - every-frame BEFORE/AFTER contact sheets of the run-3 360-degree sweeps, plus per-frame difference
numbers, so the defect spots can be picked by eye and by measure.

    python sweep_sheets.py            -> SCRATCH\\waterfix\\sheets\\<map>_p<k>.jpg, sweep_stats.json
    python sweep_sheets.py gif MAP K F0 F1 NAME     -> evidence\\NAME.gif (frames F0..F1 of that sweep, BEFORE | AFTER)
    python sweep_sheets.py still MAP K F NAME       -> evidence\\NAME.jpg (full-res BEFORE | AFTER pair)
"""
import glob, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

RUNS = r"G:\mohaa-wwtest\runs_waterfix"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\waterfix\sheets"
EVID = os.path.join(HERE, "evidence")
try:
    FONT = ImageFont.truetype("arialbd.ttf", 20)
    SMALL = ImageFont.truetype("arial.ttf", 14)
except OSError:
    FONT = SMALL = ImageFont.load_default()


def frame(mp, which, k, f):
    p = os.path.join(RUNS, "sw_%s_%s" % (mp, which), "sw_%s_%s_p%d_%02d.jpg" % (mp, which, k, f))
    return Image.open(p).convert("RGB") if os.path.exists(p) else None


def label(im, text, font=FONT):
    im = im.copy()
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=font)
    d.rectangle([0, 0, w + 12, font.size + 10], fill=(0, 0, 0))
    d.text((6, 4), text, fill=(255, 255, 255), font=font)
    return im


def sheets():
    os.makedirs(OUT, exist_ok=True)
    stats = {}
    for d in sorted(glob.glob(os.path.join(RUNS, "sw_*_old"))):
        mp = os.path.basename(d)[3:-4]
        for k in range(6):
            if frame(mp, "old", k, 0) is None or frame(mp, "new", k, 0) is None:
                continue
            tw, th = 256, 144
            sheet = Image.new("RGB", (tw * 10, (th * 2 + 6) * 6), (255, 255, 255))
            rows = []
            for f in range(60):
                a, b = frame(mp, "old", k, f), frame(mp, "new", k, f)
                if a is None or b is None:
                    continue
                A, B = np.asarray(a, np.float32), np.asarray(b, np.float32)
                la, lb = A.mean(2), B.mean(2)
                hud = np.zeros_like(la, bool)
                hud[:200, :] = True                      # HUD text rows
                diff = np.abs(la - lb)[~hud]
                rows.append({"f": f, "yaw": 6 * f, "mean_before": round(float(la[~hud].mean()), 1),
                             "mean_after": round(float(lb[~hud].mean()), 1), "changed_px": round(float((diff > 12).mean()), 3),
                             "white_before": round(float((la[~hud] > 200).mean()), 4), "white_after": round(float((lb[~hud] > 200).mean()), 4)})
                x, y = (f % 10) * tw, (f // 10) * (th * 2 + 6)
                sheet.paste(label(a.resize((tw, th)), "B %d %d" % (f, 6 * f), SMALL), (x, y))
                sheet.paste(label(b.resize((tw, th)), "A %d" % f, SMALL), (x, y + th))
            sheet.save(os.path.join(OUT, "%s_p%d.jpg" % (mp, k)), quality=85)
            stats["%s_p%d" % (mp, k)] = rows
    json.dump(stats, open(os.path.join(OUT, "sweep_stats.json"), "w"), indent=1)
    for key, rows in stats.items():
        if rows:
            best = sorted(rows, key=lambda r: -r["changed_px"])[:3]
            print(key, "most changed:", [(r["f"], r["changed_px"], r["white_before"], r["white_after"]) for r in best])


def pair(a, b):
    W, H = a.size
    im = Image.new("RGB", (W * 2 + 6, H), (255, 255, 255))
    im.paste(label(a, "BEFORE (live v1.10.13)"), (0, 0))
    im.paste(label(b, "AFTER (waterfix)"), (W + 6, 0))
    return im


def gif(mp, k, f0, f1, name, scale=0.42):
    frames = []
    rng = range(f0, f1 + 1) if f1 >= f0 else list(range(f0, 60)) + list(range(0, f1 + 1))
    for f in rng:
        a, b = frame(mp, "old", k, f), frame(mp, "new", k, f)
        if a is None or b is None:
            continue
        W, H = a.size
        sw, sh = int(W * scale), int(H * scale)
        frames.append(pair(a.resize((sw, sh), Image.LANCZOS), b.resize((sw, sh), Image.LANCZOS)))
    # slow pan feel: each 6-degree step held 2 frames at 12 fps would stutter; 1 step per 120 ms
    q = [fr.quantize(colors=192, method=Image.MEDIANCUT, dither=Image.NONE) for fr in frames]
    p = os.path.join(EVID, name + ".gif")
    q[0].save(p, save_all=True, append_images=q[1:], duration=160, loop=0, optimize=True)
    print(p, os.path.getsize(p) // 1024, "KB", len(q), "frames")


def still(mp, k, f, name):
    p = os.path.join(EVID, name + ".jpg")
    pair(frame(mp, "old", k, f), frame(mp, "new", k, f)).save(p, quality=90)
    print(p)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sheets()
    elif a[0] == "gif":
        gif(a[1], int(a[2]), int(a[3]), int(a[4]), a[5])
    elif a[0] == "still":
        still(a[1], int(a[2]), int(a[3]), a[4])

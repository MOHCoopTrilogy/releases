"""cand.py - full-size candidate viewer for picking: a 2-column montage of named frames of one scouted level.

    python tools/cand.py <map> <frame> [<frame> ...]   # -> SCRATCH/cand/<map>.jpg (each frame at 960x540, labelled)
"""
import os
import sys

from PIL import Image, ImageDraw

RUNS = r"G:\mohaa-tileart\runs"
OUT = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\7ee3b4ee-deea-4563-b7bc-c7746a82f4e9\scratchpad\cand"


def main(a):
    mp, frames = a[0], a[1:]
    cols = 3
    W, H = 640, 360
    rows = (len(frames) + cols - 1) // cols
    S = Image.new("RGB", (cols * W, rows * (H + 14)), (16, 16, 16))
    d = ImageDraw.Draw(S)
    for k, f in enumerate(frames):
        p = os.path.join(RUNS, "full_" + mp, mp + "_" + f + ".jpg")
        x, y = (k % cols) * W, (k // cols) * (H + 14)
        d.text((x + 2, y), f, fill=(255, 255, 0))
        if os.path.exists(p):
            S.paste(Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS), (x, y + 14))
    os.makedirs(OUT, exist_ok=True)
    o = os.path.join(OUT, mp + ".jpg")
    S.save(o, quality=85)
    print(o)


if __name__ == "__main__":
    main(sys.argv[1:])

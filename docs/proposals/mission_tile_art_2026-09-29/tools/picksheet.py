"""picksheet.py - one contact sheet per scouted level, for picking (dark / featureless frames dropped).

    python tools/picksheet.py <map> [<map> ...]      # -> set/picks/<map>.jpg
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
LOMEAN, LOSTD = (6, 6) if os.environ.get("DARK") else (20, 14)
RUNS = r"G:\mohaa-tileart\runs"


def main(maps):
    os.makedirs(os.path.join(PROP, "set", "picks"), exist_ok=True)
    for mp in maps:
        fs = sorted(glob.glob(os.path.join(RUNS, "full_" + mp, "*.jpg")))
        keep = []
        for f in fs:
            im = Image.open(f).convert("L").resize((96, 54))
            st = ImageStat.Stat(im)
            if st.mean[0] < LOMEAN or st.stddev[0] < LOSTD:
                continue
            keep.append(f)
        tw, th, cols = 256, 144, 8
        rows = max(1, (len(keep) + cols - 1) // cols)
        S = Image.new("RGB", (cols * tw, rows * (th + 12)), (16, 16, 16))
        d = ImageDraw.Draw(S)
        for k, f in enumerate(keep):
            x, y = (k % cols) * tw, (k // cols) * (th + 12)
            S.paste(Image.open(f).convert("RGB").resize((tw, th)), (x, y + 12))
            d.text((x + 2, y), os.path.basename(f)[len(mp) + 1:-4], fill=(255, 255, 0))
        S.save(os.path.join(PROP, "set", "picks", mp + ".jpg"), quality=80)
        print(mp, "frames", len(fs), "kept", len(keep))


if __name__ == "__main__":
    main(sys.argv[1:])

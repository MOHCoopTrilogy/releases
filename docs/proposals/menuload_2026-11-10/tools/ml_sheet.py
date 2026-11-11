r"""ml_sheet.py - contact sheets of the ml_rooms.py frame sequences (one PNG per leg: every 2nd frame, 5 columns, 320 px wide)
and a per-leg "big change" list (mean abs frame-to-frame difference): a model popping in after the camera settled shows as a
spike AFTER the move has ended.

    python ml_sheet.py <run dir>     -> <run dir>\sheets\<leg>.png + sheets\diff.txt
"""
import os, sys
from PIL import Image, ImageChops, ImageStat


def leg_sheet(d, out, step=2, cols=5, w=320):
    fs = sorted(f for f in os.listdir(d) if f.endswith(".jpg"))
    ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in fs]
    if not ims:
        return []
    h = int(ims[0].height * w / ims[0].width)
    pick = ims[::step]
    rows = (len(pick) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
    for i, im in enumerate(pick):
        sheet.paste(im.resize((w, h)), ((i % cols) * w, (i // cols) * h))
    sheet.save(out)
    small = [im.resize((192, 108)) for im in ims]
    return [round(sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3, 2) for a, b in zip(small, small[1:])]


def main(run):
    od = os.path.join(run, "sheets")
    os.makedirs(od, exist_ok=True)
    lines = []
    for leg in sorted(os.listdir(run)):
        d = os.path.join(run, leg)
        if not os.path.isdir(d) or leg == "sheets":
            continue
        diffs = leg_sheet(d, os.path.join(od, leg + ".png"))
        lines.append("%-22s frames=%d max_step=%.1f at %d | %s" % (leg, len(diffs) + 1, max(diffs or [0]),
                     (diffs.index(max(diffs)) + 1) if diffs else 0, " ".join("%.0f" % x for x in diffs)))
    open(os.path.join(od, "diff.txt"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])

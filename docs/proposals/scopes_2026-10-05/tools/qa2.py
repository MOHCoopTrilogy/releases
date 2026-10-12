"""qa2.py - contact sheets and numbers for the scope runs (G:/mohaa-hudfeed/runs/<session>).
    qa2.py sheet <session> <substr[,substr..]> <out.jpg> [tile_w=480] [cols=4] [crop=0]   crop = centre square, px of source
    qa2.py lens <session> <substr>            lens centre / radius / housing level per still
    qa2.py strip <session> <prefix> <out.jpg> [step=2] [tile_w=320] [cols=8] [first=0] [last=9999]
"""
import os, sys, glob
import numpy as np
from PIL import Image, ImageDraw
RUNS = "G:/mohaa-hudfeed/runs"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa2")
os.makedirs(OUT, exist_ok=True)


def files(sess, subs):
    fs = sorted(glob.glob(os.path.join(RUNS, sess, "*.png")) + glob.glob(os.path.join(RUNS, sess, "*.jpg")))
    return [f for f in fs if any(s in os.path.basename(f) for s in subs.split(","))]


def sheet(fs, out, tw=480, cols=4, crop=0, labels=None):
    tiles = []
    for k, f in enumerate(fs):
        im = Image.open(f).convert("RGB")
        if crop:
            w, h = im.size
            im = im.crop((w // 2 - crop // 2, h // 2 - crop // 2, w // 2 + crop // 2, h // 2 + crop // 2))
        th = int(round(tw * im.size[1] / im.size[0]))
        im = im.resize((tw, th), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        lab = labels[k] if labels else os.path.basename(f).rsplit(".", 1)[0]
        d.rectangle((0, 0, 7 * len(lab) + 6, 13), fill=(0, 0, 0))
        d.text((3, 1), lab, fill=(255, 255, 0))
        tiles.append(im)
    if not tiles:
        print("no files")
        return
    rows = (len(tiles) + cols - 1) // cols
    th = max(t.size[1] for t in tiles)
    S = Image.new("RGB", (cols * tw, rows * th), (40, 0, 40))
    for k, t in enumerate(tiles):
        S.paste(t, ((k % cols) * tw, (k // cols) * th))
    S.save(out, quality=88)
    print(out, S.size, len(tiles), "tiles")


def lens(f, R_frac=0.465):
    im = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    L = im @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    H, W = L.shape
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - cx, yy - cy) / H
    # where the lens ends along 24 rays: the outermost radius whose 5-px mean is still over a third of the inner level
    inner = float(np.median(L[(r < 0.30)]))
    thr = max(8.0, inner * 0.33)
    ends = []
    for a in np.linspace(0, 2 * np.pi, 24, endpoint=False):
        best = 0.0
        for rr in np.arange(0.30, 0.75, 0.002):
            x, y = int(round(cx + rr * H * np.cos(a))), int(round(cy + rr * H * np.sin(a)))
            if 2 <= x < W - 2 and 2 <= y < H - 2 and L[y - 2:y + 3, x - 2:x + 3].mean() > thr:
                best = rr
        ends.append(best)
    ends = np.array(ends)
    offx = (ends[0] - ends[12]) / 2 * H
    offy = (ends[6] - ends[18]) / 2 * H
    hs = (r > R_frac * 1.10)
    hud = hs & (L > 70)
    hv = L[hs & ~hud]
    return {"inner": inner, "r_med": float(np.median(ends)), "r_min": float(ends.min()), "r_max": float(ends.max()),
            "offx_px": float(offx), "offy_px": float(offy), "house_mean": float(hv.mean()) if hv.size else -1,
            "house_p99": float(np.percentile(hv, 99)) if hv.size else -1, "house_max": float(hv.max()) if hv.size else -1,
            "hud_px": int(hud.sum()), "size": (W, H)}


def main():
    cmd = sys.argv[1]
    if cmd == "sheet":
        a = sys.argv[2:]
        sheet(files(a[0], a[1]), os.path.join(OUT, a[2]), int(a[3]) if len(a) > 3 else 480, int(a[4]) if len(a) > 4 else 4,
              int(a[5]) if len(a) > 5 else 0)
    elif cmd == "lens":
        for f in files(sys.argv[2], sys.argv[3]):
            m = lens(f)
            print("%-44s %dx%d inner %5.1f  lens r/H med %.3f (min %.3f max %.3f) off %+.1f,%+.1f px  housing mean %.2f p99 %.1f max %.0f  hud px %d" % (
                os.path.basename(f)[:44], m["size"][0], m["size"][1], m["inner"], m["r_med"], m["r_min"], m["r_max"], m["offx_px"],
                m["offy_px"], m["house_mean"], m["house_p99"], m["house_max"], m["hud_px"]))
    elif cmd == "strip":
        a = sys.argv[2:]
        step = int(a[3]) if len(a) > 3 else 2
        fs = sorted(glob.glob(os.path.join(RUNS, a[0], a[1] + "*.jpg")))
        first, last = (int(a[6]) if len(a) > 6 else 0), (int(a[7]) if len(a) > 7 else 9999)
        fs = [f for f in fs if first <= int(f.rsplit("__", 1)[1][:4]) <= last][::step]
        sheet(fs, os.path.join(OUT, a[2]), int(a[4]) if len(a) > 4 else 320, int(a[5]) if len(a) > 5 else 8,
              labels=[f.rsplit("__", 1)[1][:4] for f in fs])


if __name__ == "__main__":
    main()

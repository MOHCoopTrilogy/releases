"""check_faces.py - [benchfix] the hand check of every spot's whole face (cg_engraveFaceCheck runs).

Each shot <tag>_NN_<key>__<spot>.jpg shows the face's usable cells tiled with flat magenta squares; the ENGRAVETILE lines
printed with it (just after "Wrote screenshots/<shot>.jpg") give each square's corners and the cells it stands for. A tile
under MIN_VISIBLE magenta is covered (a hand, the sight, the screen edge): its cells are reported, and
merge_engrave_spots.py (EG_TILEFAIL) clears them from the face, so MOVE never takes a piece there.

    python docs/tools/engrave/check_faces.py <run dir> --out tiles.json
"""
import glob, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw

MIN_VISIBLE = 0.8


def main():
    run = sys.argv[1]
    log = open(os.path.join(run, "qconsole.log"), encoding="latin-1", errors="replace").read().splitlines()
    tiles, pending = {}, None
    for line in log:
        m = re.search(r"Wrote screenshots/(\S+)\.jpg", line)
        if m:
            pending = m.group(1)
            continue
        m = re.search(r"ENGRAVETILE key=(\S+) spot=(\S+) cells=(\d+) (\d+) (\d+) (\d+) px ([-\d. ]+)", line)
        if m and pending:
            v = [float(x) for x in m.group(7).split()]
            tiles.setdefault(pending, []).append((m.group(1), m.group(2), [int(m.group(k)) for k in (3, 4, 5, 6)],
                                                  [(v[i], v[i + 1]) for i in range(0, 8, 2)]))
    out, ntile, nbad = {}, 0, 0
    for f in sorted(glob.glob(os.path.join(run, "*.jpg"))):
        tag = os.path.splitext(os.path.basename(f))[0]
        if tag not in tiles:
            continue
        im = np.asarray(Image.open(f).convert("RGB")).astype(int)
        H, W = im.shape[:2]
        mag = (im[..., 0] > 140) & (im[..., 2] > 140) & (im[..., 1] < 100)
        for key, spot, cells, pts in tiles[tag]:
            cx, cy = sum(p[0] for p in pts) / 4.0, sum(p[1] for p in pts) / 4.0
            pts2 = [(cx + (x - cx) * 0.8, cy + (y - cy) * 0.8) for x, y in pts]
            mask = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mask).polygon(pts2, fill=255)
            mk = np.asarray(mask) > 0
            area = int(mk.sum())
            frac = float((mag & mk).sum()) / area if area else 0.0
            ntile += 1
            if area < 4 or frac < MIN_VISIBLE:
                nbad += 1
                out.setdefault("%s__%s" % (key, spot), []).append(cells)
    print("%d tiles, %d covered, on %d faces" % (ntile, nbad, len(out)))
    if "--out" in sys.argv:
        json.dump(out, open(sys.argv[sys.argv.index("--out") + 1], "w"), indent=0)


if __name__ == "__main__":
    main()

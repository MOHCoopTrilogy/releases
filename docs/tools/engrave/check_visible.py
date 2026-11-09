"""check_visible.py - the hand check for the engraving anchors (cg_engraveCheck 1 runs).

For each per-gun screenshot of the check run, the last ENGRAVEQUAD line printed before it gives the quad's corners on
screen; the quad is drawn flat magenta, depth-tested, so the magenta pixels inside that polygon are the part the hands
(and anything else) leave in view. A gun FAILS when under MIN_VISIBLE of the quad is visible, or when the quad is not
on screen at all.

    python docs/tools/engrave/check_visible.py <run dir with qconsole.log + <tag>_NN_<gun>.jpg> [--out report.json]
exit 1 when any gun fails.
"""
import glob, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw

MIN_VISIBLE = 0.85


def main():
    run = sys.argv[1]
    log = open(os.path.join(run, "qconsole.log"), encoding="latin-1", errors="replace").read().splitlines()
    # cg_engraveQuadNow prints the corners in the frame the shot captures, which logs just AFTER "Wrote ..."
    quad, pending = {}, None
    for line in log:
        if "SPTEST gun " in line:
            pending = None   # a gun with no anchor prints no quad: never pair its shot with the next gun's
        m = re.search(r"Wrote screenshots/(\S+)\.jpg", line)
        if m:
            pending = m.group(1)
            continue
        m = re.search(r"ENGRAVEQUAD key=(\S+) px ([-\d. ]+)", line)
        if m and pending:
            v = [float(x) for x in m.group(2).split()]
            quad[pending] = (m.group(1), [(v[i], v[i + 1]) for i in range(0, 8, 2)])
            pending = None
    res, bad = {}, 0
    for f in sorted(glob.glob(os.path.join(run, "*.jpg"))):
        tag = os.path.splitext(os.path.basename(f))[0]
        gun = re.sub(r"^.*?_\d\d_", "", tag)
        if tag not in quad:
            res[gun] = dict(ok=False, why="no quad printed (no anchor, or not drawn)")
            bad += 1
            continue
        key, pts = quad[tag]
        # shrink the polygon 8% toward its centre: the quad's own anti-aliased edge and the JPEG ring are not occlusion
        cx, cy = sum(p[0] for p in pts) / 4.0, sum(p[1] for p in pts) / 4.0
        pts = [(cx + (x - cx) * 0.92, cy + (y - cy) * 0.92) for x, y in pts]
        im = np.asarray(Image.open(f).convert("RGB")).astype(int)
        H, W = im.shape[:2]
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).polygon(pts, fill=255)
        mk = np.asarray(mask) > 0
        area = int(mk.sum())
        mag = (im[..., 0] > 140) & (im[..., 2] > 140) & (im[..., 1] < 100)
        vis = int((mag & mk).sum())
        frac = vis / area if area else 0.0
        ok = area > 20 and frac >= MIN_VISIBLE
        bad += 0 if ok else 1
        res[gun] = dict(ok=ok, key=key, area_px=area, visible=round(frac, 3), tik="models/weapons/%s.tik" % key)
    for g, r in sorted(res.items()):
        print("%-28s %s %s" % (g, "ok  " if r["ok"] else "FAIL", r.get("visible", r.get("why"))))
    print("%d guns, %d fail" % (len(res), bad))
    if "--out" in sys.argv:
        json.dump(res, open(sys.argv[sys.argv.index("--out") + 1], "w"), indent=1)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

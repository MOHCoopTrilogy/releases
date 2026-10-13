"""Software views of a whole gun (all surfaces that use one sheet) with a given texture: right side, left side,
top, bottom, front three-quarter, rear three-quarter. For looking at a sheet on the mesh before the engine.

    python gunview.py <skd vpath or file> <texture: image file | stem in the pak set> <out.jpg> [--surf a,b] [--scale 16]
        [--islands]   colour by UV island instead of the texture (labels: <surface initial><id>)
Bone note: positions are the skd's bone-space offsets of each vertex's main bone; the bones used are printed.
"""
import os, sys
import numpy as np
from PIL import Image
import rplib as L
import soft3d
VIEWS = [("right", 0, 90, 0), ("left", 180, 90, 0), ("top", 0, 0, 0), ("bottom", 0, 180, 0), ("front34", 140, 65, 0),
         ("rear34", 40, 65, 0)]


def main():
    a = sys.argv[1:]
    surf = None; scale = 16.0
    if "--surf" in a:
        i = a.index("--surf"); surf = a[i + 1].split(","); del a[i:i + 2]
    if "--scale" in a:
        i = a.index("--scale"); scale = float(a[i + 1]); del a[i:i + 2]
    isl = "--islands" in a
    if isl:
        a.remove("--islands")
    src, tex, out = a[:3]
    S = L.load_skd(src, surf)
    if os.path.isfile(tex):
        T = np.asarray(Image.open(tex).convert("RGB"), np.float32)
    else:
        T = L.read_image(tex)[0]
    parts = []
    for n, s in S.items():
        if isl:
            # island colours: paint a private texture per surface by island id
            W = 512
            im = L.island_map(s, W, W, os.path.join(L.WORK, "_tmp_isl.png"), label=False)
            parts.append((s, np.asarray(im, np.float32)))
        else:
            parts.append((s, T))
    tiles = []
    for name, yaw, pitch, roll in VIEWS:
        tiles.append(soft3d.render(parts, yaw, pitch, scale=scale, roll=roll, gain=1.5, bg=(150, 156, 160), wrap=True))
    W = max(t.shape[1] for t in tiles[:2]) * 2 + 8
    rows = [tiles[0:2], tiles[2:4], tiles[4:6]]
    H = sum(max(t.shape[0] for t in r) + 8 for r in rows)
    sh = np.zeros((H, max(W, max(sum(t.shape[1] + 8 for t in r) for r in rows)), 3), np.float32) + 255
    y = 0
    for r in rows:
        x = 0
        for t in r:
            sh[y:y + t.shape[0], x:x + t.shape[1]] = t; x += t.shape[1] + 8
        y += max(t.shape[0] for t in r) + 8
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    Image.fromarray(sh.astype(np.uint8)).save(out, quality=90)
    print(out, sh.shape)


if __name__ == "__main__":
    main()

"""Before | after sheets from two run folders (PNG stills of run_rp.py).

    python sheet.py <before_dir> <after_dir> <out.jpg> <view[@x0,y0,x1,y1]> [...] [--scale 1.0] [--cols 1]

Each view is one tile: before on the left, after on the right, same crop of the same still name, labelled.
A crop is in full-frame pixels; without one the whole frame is used. --cols lays the tiles in several columns.
"""
import os, sys
from PIL import Image, ImageDraw


def main():
    a = sys.argv[1:]
    scale = 1.0; cols = 1
    if "--scale" in a:
        i = a.index("--scale"); scale = float(a[i + 1]); del a[i:i + 2]
    if "--cols" in a:
        i = a.index("--cols"); cols = int(a[i + 1]); del a[i:i + 2]
    bdir, adir, out = a[:3]
    tiles = []
    for v in a[3:]:
        name, _, crop = v.partition("@")
        box = tuple(int(x) for x in crop.split(",")) if crop else None
        pair = []
        for d in (bdir, adir):
            p = os.path.join(d, name + ".png")
            if not os.path.exists(p):
                pair.append(None); continue
            im = Image.open(p).convert("RGB")
            if box:
                im = im.crop(box)
            if scale != 1.0:
                im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
            pair.append(im)
        ref = pair[0] or pair[1]
        if ref is None:
            print("missing", name); continue
        w, h = ref.size
        t = Image.new("RGB", (2 * w + 6, h + 18), (255, 255, 255))
        d = ImageDraw.Draw(t)
        for k, im in enumerate(pair):
            if im is not None:
                t.paste(im, (k * (w + 6), 18))
        d.text((3, 3), name + "  before", fill=(0, 0, 0)); d.text((w + 9, 3), name + "  after", fill=(0, 0, 0))
        tiles.append(t)
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    W = max(sum(t.size[0] + 10 for t in r) for r in rows); H = sum(max(t.size[1] for t in r) + 8 for r in rows)
    sh = Image.new("RGB", (W, H), (255, 255, 255)); y = 0
    for r in rows:
        x = 0
        for t in r:
            sh.paste(t, (x, y)); x += t.size[0] + 10
        y += max(t.size[1] for t in r) + 8
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sh.save(out, quality=90)
    print(out, sh.size)


if __name__ == "__main__":
    main()

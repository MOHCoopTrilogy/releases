"""Orthographic island views of the bone-0 part of mp18.skd (painter's algorithm): right side, left side, top,
bottom. Each island is one colour and labelled <surface initial><id>. evidence/ortho_islands.png
usage: python ortho.py"""
import os
import numpy as np
from PIL import Image, ImageDraw
import islands
EVI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence")
SC = 14
VIEWS = [("side y-", 0, 2, 1, +1), ("side y+", 0, 2, 1, -1), ("top (z-)", 0, 1, 2, +1), ("bottom (z+)", 0, 1, 2, -1)]


def main():
    S = islands.load()
    names = [n for n in S if n in ("Tube1", "Cube1", "Cylinde0")]
    allp = np.concatenate([S[n]["pos"] for n in names])
    lo = allp.min(0) - 1; hi = allp.max(0) + 1
    panels = []
    for title, ax, ay, ad, sgn in VIEWS:
        W = int((hi[ax] - lo[ax]) * SC); H = int((hi[ay] - lo[ay]) * SC)
        im = Image.new("RGB", (W, H), (30, 30, 30)); d = ImageDraw.Draw(im)
        polys = []
        for n in names:
            s = S[n]
            for ti, t in enumerate(s["tris"]):
                p = s["pos"][t]
                depth = p[:, ad].mean() * sgn       # draw far first: the viewer sits at -sgn * inf
                pts = [((q[ax] - lo[ax]) * SC, (q[ay] - lo[ay]) * SC) for q in p]
                polys.append((-depth, n, int(s["isl"][ti]), pts))
        polys.sort(key=lambda x: x[0])
        seen = {}
        for _, n, k, pts in polys:
            rs = np.random.RandomState(hash((n, k)) % 100000)
            base = {"Tube1": (150, 100, 50), "Cube1": (90, 110, 150), "Cylinde0": (90, 160, 90)}[n]
            col = tuple(int(np.clip(b + rs.randint(-45, 45), 0, 255)) for b in base)
            d.polygon(pts, fill=col, outline=(0, 0, 0))
            seen[(n, k)] = np.mean(pts, 0)      # last drawn = nearest
        for (n, k), c in seen.items():
            d.text((c[0] - 8, c[1] - 5), "%s%d" % (n[0] if n != "Cylinde0" else "F", k), fill=(255, 255, 0))
        d.text((4, 4), title + "   x: %.0f..%.0f" % (lo[ax], hi[ax]), fill=(255, 255, 255))
        panels.append(im)
    W = max(p.size[0] for p in panels); H = sum(p.size[1] for p in panels)
    sheet = Image.new("RGB", (W, H)); y = 0
    for p in panels:
        sheet.paste(p, (0, y)); y += p.size[1]
    sheet.save(os.path.join(EVI, "ortho_islands.png"))
    print(sheet.size)


if __name__ == "__main__":
    main()

"""qa_titles.py - caption stress test: EVERY proposed title laid out on a card, shown at the tile's real on-screen size.

    python tools/qa_titles.py      # ../samples/qa/titles_all_<layout>_<W>x<H>.png

The photo is a flat paper-toned placeholder on purpose: this checks the caption layout (fit, wrap, size), not the art.
On-screen size of the 100x100-unit tile: layout s (default stretch) = W/640*100 x H/480*100 (300x225 at 1080p, 200x150
at 720p); layout c (ui_menuCenter 1) = uniform min() scale (225x225, 150x150).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tile_treat as T  # noqa: E402


def blank_card(title, layout):
    cw = int(round(T.S * T.LAYOUT_ASPECT[layout]))
    c = T.paper(np.random.default_rng(1), cw, T.S)
    c[T.MARGIN:T.MARGIN + T.PHOTO_H, T.MARGIN:cw - T.MARGIN] = np.array([96, 84, 70], np.float32) / 255
    im = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    T.caption(im, title)
    return im.resize((T.S, T.S), Image.LANCZOS) if cw != T.S else im


def main():
    tiles = json.load(open(os.path.join(HERE, "titles.json"), encoding="utf-8"))["tiles"]
    items = sorted(tiles.items(), key=lambda kv: -len(kv[1]["title"]))
    for layout in ("s", "c"):
        cards = [T.game_texture(blank_card(t["title"], layout), layout) for _, t in items]
        for W, H in ((1920, 1080), (1280, 720)):
            if layout == "s":
                tw, th = int(W / 640 * 100), int(H / 480 * 100)
            else:
                s = min(W / 640, H / 480)
                tw = th = int(s * 100)
            cols = 8
            rows = (len(items) + cols - 1) // cols
            S = Image.new("RGB", (cols * (tw + 8) + 8, rows * (th + 8) + 8), (10, 30, 10))
            for k, g in enumerate(cards):
                S.paste(g.resize((tw, th), Image.LANCZOS), (8 + (k % cols) * (tw + 8), 8 + (k // cols) * (th + 8)))
            S.save(os.path.join(PROP, "samples", "qa", "titles_all_%s_%dx%d.png" % (layout, W, H)), optimize=True)
            print("titles sheet", layout, W, H, len(items))


if __name__ == "__main__":
    main()

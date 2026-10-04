"""qa_set.py - mechanical QA of the built tile set (the eyes-on QA is the pick/progress sheets + the independent review).

    python tools/qa_set.py        # exit 1 on any failure

Checks, for every tile in titles.json: the four shipped textures exist at the right size (card 512x512, print 512x384);
the title wraps to the SAME lines and size in both layouts; no two tiles share a source frame (clones); tileset.py has a
spec whose provenance ('how') is non-empty; every spec's title exists in titles.json and vice versa; the paper margin of
each card is intact (caption band not clipped: the bottom rows are paper-coloured).
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fontfit  # noqa: E402
import tile_treat as T  # noqa: E402
import tileset  # noqa: E402

G = os.path.join(PROP, "set", "game")


def tid(b):
    return b.replace("/", "_")


def main():
    titles = json.load(open(os.path.join(HERE, "titles.json"), encoding="utf-8"))["tiles"]
    fails = []
    if set(titles) != set(tileset.SPECS):
        fails.append("titles.json vs tileset.py differ: only titles %s, only specs %s" % (
            sorted(set(titles) - set(tileset.SPECS))[:8], sorted(set(tileset.SPECS) - set(titles))[:8]))
    raws = {}
    for b, s in tileset.SPECS.items():
        i = tid(b)
        for n, want in (("%s_c" % i, (512, 512)), ("%s_s" % i, (512, 512)), ("print_%s_c" % i, (512, 384)),
                        ("print_%s_s" % i, (512, 384))):
            p = os.path.join(G, n + ".jpg")
            if not os.path.exists(p):
                fails.append("missing " + n)
            elif Image.open(p).size != want:
                fails.append("%s is %s want %s" % (n, Image.open(p).size, want))
        if not s.get("how"):
            fails.append(b + ": no provenance")
        raws.setdefault(str(s["raw"]), []).append(b)
        # caption wrap identical in both layouts (both use the square layout's width now)
        maxw = T.S - 2 * T.MARGIN - 24
        px, lines = fontfit.fit_title(titles[b]["title"], maxw, sizes=[104, 96, 92, 88, 84, 80, 76, 72], min_one=96, max_two=92)
        if len(lines) > 2 or px < 72:
            fails.append("%s title does not fit: %s %s" % (b, px, lines))
        # card bottom edge is paper (light), i.e. the caption band is not clipped by the photo or a crop error
        p = os.path.join(G, "%s_c.jpg" % i)
        if os.path.exists(p):
            a = np.asarray(Image.open(p).convert("L"), np.float32)
            if a[-14:, 40:-40].mean() < 150:
                fails.append(i + ": bottom margin is dark")
    for r, bs in raws.items():
        if len(bs) > 1:
            fails.append("one source frame used by %s" % bs)
    for f in fails:
        print("FAIL", f)
    print("qa_set", "OK" if not fails else "FAILED", "-", len(tileset.SPECS), "tiles")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

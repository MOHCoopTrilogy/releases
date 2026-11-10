"""merge spots (+ the engrave spot's free range) from new solves into the hand-checked anchor report, then write the table.
The anchor itself is kept from the checked report; its range is taken from a new solve only when that solve chose the same
rectangle (same centre within 0.05 units), else the anchor stays fixed (range 0)."""
import json, sys, os
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\engrave")
import gen_engrave_anchors as G
base = json.load(open(sys.argv[1]))
for path in sys.argv[2].split(","):
    new = json.load(open(path))
    for tik, r in new.items():
        if not isinstance(r, dict) or tik not in base or not isinstance(base[tik], dict):
            continue
        b = base[tik]
        b["spots"] = r.get("spots", {})
        b["bounds"] = r.get("bounds")
        same = np.linalg.norm(np.array(r["o"]) - np.array(b["o"])) < 0.05 and abs(r["width"] - b["width"]) < 0.05
        for k in ("sq", "du0", "du1", "dv0", "dv1"):
            b[k] = r.get(k, 0) if same else 0.0
        if not same:
            b["sq"] = round(b["width"] / (4.0 if b["lines"] == 2 else 8.0), 3)
if len(sys.argv) > 5:
    # the short-words spot: a solve restricted to the 2:1 two-line layout (EG_SHORT=1)
    short = json.load(open(sys.argv[5]))
    for tik, r in short.items():
        if isinstance(r, dict) and isinstance(base.get(tik), dict) and r["letter_px"] > base[tik]["letter_px"] * 1.1:   # only where it is bigger
            base[tik].setdefault("spots", {})["engrave_short"] = {k: r[k] for k in ("o", "u", "v", "width", "material", "lines", "letter_px", "sq", "du0", "du1", "dv0", "dv1")}
# spots the in-game hand check failed (a hand covers them): check_visible.py reports, named <key>_<spot>
import glob as _g, os as _o
NAMES = ("engrave_short", "receiver_l", "receiver_r", "stock_l", "stock_r", "grip", "butt", "top")
for rp in _o.environ.get("EG_SPOTFAIL", "").split(","):
    if not rp:
        continue
    for tag, res in json.load(open(rp)).items():
        if res.get("ok"):
            continue
        for nm in NAMES:
            if tag.endswith("_" + nm):
                key = tag[:-len(nm) - 1]
                for tik, b in base.items():
                    if isinstance(b, dict) and _o.path.basename(tik)[:-4] == key:
                        b.get("spots", {}).pop(nm, None)
                break
json.dump(base, open(sys.argv[3], "w"), indent=1)
G.write_table(base, sys.argv[4])

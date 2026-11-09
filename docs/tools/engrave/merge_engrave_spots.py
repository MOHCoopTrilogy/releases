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
        same = np.linalg.norm(np.array(r["o"]) - np.array(b["o"])) < 0.05 and abs(r["width"] - b["width"]) < 0.05
        for k in ("sq", "du0", "du1", "dv0", "dv1"):
            b[k] = r.get(k, 0) if same else 0.0
        if not same:
            b["sq"] = round(b["width"] / (4.0 if b["lines"] == 2 else 8.0), 3)
json.dump(base, open(sys.argv[3], "w"), indent=1)
G.write_table(base, sys.argv[4])

"""merge spots (+ the engrave spot's free range) from new solves into the hand-checked anchor report, then write the table.
The anchor itself is kept from the checked report; its range is taken from a new solve only when that solve chose the same
rectangle (same centre within 0.05 units), else the anchor stays fixed (range 0)."""
import json, sys, os
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\engrave")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
        # [benchfix] the face the anchor sits on (MOVE's limit): the new solve's grid, re-centred on the checked anchor when the
        # anchor lies on the same plane in the same frame (else no grid: the anchor keeps its fixed place)
        b["face"] = None
        f = r.get("face")
        if f:
            ou, ov = np.array(r["u"]), np.array(r["v"])
            d = np.array(b["o"]) - np.array(r["o"])
            n = np.cross(ou, ov)
            if np.dot(ou, b["u"]) > 0.99 and np.dot(ov, b["v"]) > 0.99 and abs(d @ n) < 0.05:
                b["face"] = dict(f, u0=round(f["u0"] - float(d @ ou), 3), v0=round(f["v0"] - float(d @ ov), 3))
        # else the face of a named spot on the anchor's own plane (the solver's choice moved, the face did not)
        for c in ([] if b["face"] else r.get("spots", {}).values()):
            f = c.get("face")
            if not f:
                continue
            ou, ov = np.array(c["u"]), np.array(c["v"])
            d = np.array(b["o"]) - np.array(c["o"])
            n = np.cross(ou, ov)
            if np.dot(ou, b["u"]) > 0.99 and np.dot(ov, b["v"]) > 0.99 and abs(d @ n) < 0.05:
                b["face"] = dict(f, u0=round(f["u0"] - float(d @ ou), 3), v0=round(f["v0"] - float(d @ ov), 3))
                break
        if not same:
            b["sq"] = round(b["width"] / (4.0 if b["lines"] == 2 else 8.0), 3)
if len(sys.argv) > 5:
    # the short-words spot: a solve restricted to the 2:1 two-line layout (EG_SHORT=1)
    short = json.load(open(sys.argv[5]))
    for tik, r in short.items():
        if isinstance(r, dict) and isinstance(base.get(tik), dict) and r["letter_px"] > base[tik]["letter_px"] * 1.1:   # only where it is bigger
            base[tik].setdefault("spots", {})["engrave_short"] = {k: r.get(k) for k in ("o", "u", "v", "width", "material", "lines", "letter_px", "sq", "du0", "du1", "dv0", "dv1", "face")}
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
# [benchfix] face cells a hand covers (check_faces.py reports: "<key>__<spot>": [[i0, j0, i1, j1], ...]) are cleared
TILEFAIL = {}
for rp in os.environ.get("EG_TILEFAIL", "").split(","):
    if rp:
        for k, v in json.load(open(rp)).items():
            TILEFAIL.setdefault(k, []).extend(v)


def clear_tiles(key, name, f):
    if not f or ("%s__%s" % (key, name)) not in TILEFAIL:
        return f
    b = np.unpackbits(np.frombuffer(bytes.fromhex(f["bits"]), np.uint8))[:f["nu"] * f["nv"]].reshape(f["nv"], f["nu"]).copy()
    for i0, j0, i1, j1 in TILEFAIL["%s__%s" % (key, name)]:
        b[j0:j1, i0:i1] = 0
    return dict(f, bits=np.packbits(b.reshape(-1)).tobytes().hex())


for tik, b in base.items():
    if isinstance(b, dict):
        key = os.path.basename(tik)[:-4]
        b["face"] = clear_tiles(key, "engrave", b.get("face"))
        for nm, c in b.get("spots", {}).items():
            c["face"] = clear_tiles(key, nm, c.get("face"))
json.dump(base, open(sys.argv[3], "w"), indent=1)
G.write_table(base, sys.argv[4])

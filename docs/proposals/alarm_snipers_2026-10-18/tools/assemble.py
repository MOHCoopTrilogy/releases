"""assemble.py - union of every spot that PASSED an in-engine audit (earlier final round _round4 + the vanilla-source round in spotcheck/), minus manual-QA drops,
>= 600 u apart, best 6 per map, written back to docs/tools/sniper_spots.json (audited False: asn_chk.py verifies and photographs the result once more)."""
import json, math, os
H = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(H, "..", "..", "..", "tools")
OUT = os.path.join(TOOLS, "sniper_spots.json")
cur = json.load(open(OUT))
old = json.load(open(os.path.join(H, "sniper_spots_v7_before_vanilla.json")))
MAPS = ["e2l1", "e3l1", "e3l2", "m1l1", "m2l1", "m3l2", "m4l1", "m4l2", "m4l3", "t1l1", "t3l1"]
def key(p):
    return (round(p[0]), round(p[1]), round(p[2] * 4))
def load(path):
    return json.load(open(path)) if os.path.exists(path) else []
for m in MAPS:
    pool = {}
    for src in (old.get(m, {}).get("spots", []), cur.get(m, {}).get("spots", [])):
        for s in src:
            pool[key(s["pos"])] = s
    good = {}
    for d in ("_round4", ""):
        for r in load(os.path.join(H, "spotcheck", d, m + ".json") if d else os.path.join(H, "spotcheck", m + ".json")):
            k = key(r["pos"])
            if r["verdict"] == "PASS":
                good[k] = True
            else:
                good.pop(k, None)
    # the older 3-spot final audit also lives in git (spotcheck before _round4): its passers are the same positions as _round4 entries
    cand = [pool[k] for k in good if k in pool]
    cand.sort(key=lambda s: -(s["routeDz"] / 8.0 + s["los"] / 3.0 + s["body"] / 6.0))
    picked = []
    for s in cand:
        if len(picked) >= 6:
            break
        if all(math.hypot(s["pos"][0] - p["pos"][0], s["pos"][1] - p["pos"][1]) >= 600 for p in picked):
            picked.append(s)
    for i, p in enumerate(picked):
        p.setdefault("cluster", i + 1)
        p.setdefault("side", 0)
    cur.setdefault(m, {})["spots"] = picked
    cur[m]["audited"] = False
    print(m, "passers", len(good), "in pool", len(cand), "picked", len(picked))
json.dump(cur, open(OUT, "w"), indent=1, sort_keys=True)

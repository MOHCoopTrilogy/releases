"""readme_tables.py - markdown tables for the README from docs/tools/sniper_spots.json (counts + per-spot trace results)."""
import json, os, sys
J = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools", "sniper_spots.json")))
maps = sys.argv[1:] or sorted(J)
print("| map | spots | buildings | sides |\n|---|---:|---:|---:|")
for m in maps:
    s = J[m]["spots"]
    print("| %s | %d | %d | %d |" % (m, len(s), len({x["cluster"] for x in s}), len({x["side"] for x in s})))
print()
for m in maps:
    s = J[m]["spots"]
    if not s:
        continue
    print("#### %s\n\n| # | spot x y floor-z | floor dz | normal z | corner dz (4) | headroom | shader | elev | LOS head/body | bldg | side |\n|---:|---|---:|---:|---|---:|---|---:|---|---:|---:|" % m)
    for i, x in enumerate(s, 1):
        g = x["ground"]
        print("| %d | %s %s %s | %s | %s | %s | %s | %s | %s | %s/%s | %s | %s |" % (i, x["pos"][0], x["pos"][1], x["pos"][2], g["floorDz"], g["normalZ"], g["cornerDz"], g["headroom"], g["shader"].split("/")[-1], x["elev"], x["los"], x["body"], x["cluster"], x["side"]))
    print()

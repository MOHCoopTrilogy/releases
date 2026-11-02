"""mk_v9spec.py <v7_s3.json> <v7_s4.json> <outdir> - the v9 specs: v7 + int_ceil/int_zmax on the top-tier sites + five roof-edge notches (23-27)."""
import json, sys, os
s = json.load(open(sys.argv[1])); t = json.load(open(sys.argv[2])); out = sys.argv[3]
s["src"] = "H:/hzm_work/maprebuild/v4/c2.bsp"            # the v4 crumble-chunk map, same base as v7 (md5 da3e482b10f7b0da47f62014dd073c56)
s["dst"] = os.path.join(out, "c3.bsp").replace("\\", "/")
t["src"] = s["dst"]; t["dst"] = os.path.join(out, "c4.bsp").replace("\\", "/")
TOP = (6, 18, 19, 20, 21)          # top-tier wall sites (z 990/1000..1190): their v7 interior ceiling rose to z 1310 over the 1216 roof
def N(n, x0, x1, r, seed):
    # a bite out of the roofline: the whole top tier (brush 1993: y 3080..3176, z 960..1216) between x0 and x1
    return dict(n=n, axis=1, sign=-1, box=[[x0, 3072, 960], [x1, 3184, 1224]], hole_r=r, K=10, seed=seed, interior=True, depth=300, notch=True)
NOTCH = [N(23, -2640, -2010, 150, 101), N(24, -1440, -860, 140, 103), N(25, -250, 370, 150, 107), N(26, 940, 1290, 110, 109), N(27, -3660, -3205, 130, 113)]
for S in s["structures"]:
    if S["name"] != "facade": continue
    for B in S["breaches"]:
        if B["n"] in TOP: B["int_ceil"] = 1206; B["int_zmax"] = 1210
    S["breaches"] += NOTCH
json.dump(s, open(os.path.join(out, "v9_s3.json"), "w")); json.dump(t, open(os.path.join(out, "v9_s4.json"), "w"))
print("specs ->", out)

"""mk_v10spec.py <v7_s3.json> <v7_s4.json> <outdir> - map v10 specs (= v9 + the payoff rebuild, user 2026-11-02):

* the facade is split in three structures:
    facade  = the lower tiers (brushes 3497 3505 3496 3506 3501 2729 + 3504, the door strip), cuts moved to -890 so the
              DOOR BREACH (28) - the climax hole at the foot of the wall - lives in one chunk; lower breaches 1 2 3 22 + 28
    ledge   = the long protruding ledge band (4563) in the same six spans: crumble_ledge_1..6 break off and drop first
    upper   = the cornice tier (3393) + the top tier (1993), cut into SIX LONG PIECES at x -3175 -1980 -780 -275 410 (the only x
              values where no cornice / top-tier / roof-notch breach box sits, so every breach stays whole inside one piece);
              breaches 4 5 6 11 13-21 + roof notches 23-27 move here. crumble_upper_1..6 are what the climax knocks down.
* yardwall_s (the "grey hut" the camera faces: the yard's south wall with the three lit windows) gains its lower wall (1088) and four
  ragged holes 29-32 below the windows, with burning rooms behind them.
Everything else (booms, cover, hangar, the other crumble structures, pclip boxes) is the v7/v9 spec unchanged."""
import json, sys, os
s = json.load(open(sys.argv[1])); t = json.load(open(sys.argv[2])); out = sys.argv[3]
s["src"] = "H:/hzm_work/maprebuild/v4/c2.bsp"
s["dst"] = os.path.join(out, "c3.bsp").replace("\\", "/")
t["src"] = s["dst"]; t["dst"] = os.path.join(out, "c4.bsp").replace("\\", "/")

TOP = (6, 18, 19, 20, 21)
UPPER_SITES = (4, 5, 6, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21)


def N(n, x0, x1, r, seed):
    return dict(n=n, axis=1, sign=-1, box=[[x0, 3072, 960], [x1, 3184, 1224]], hole_r=r, K=10, seed=seed, interior=True, depth=300, notch=True)


NOTCH = [N(23, -2640, -2010, 150, 101), N(24, -1440, -860, 140, 103), N(25, -250, 370, 150, 107), N(26, 940, 1290, 110, 109), N(27, -3660, -3205, 130, 113)]
DOOR = dict(n=28, axis=1, sign=-1, box=[[-880, 3000, -512], [-60, 3048, 300]], hole_r=260, K=10, seed=127, interior=False)
YARD = [dict(n=29, axis=1, sign=-1, box=[[-2480, 952, -512], [-2120, 984, -296]], hole_r=80, K=10, seed=131, interior=True, depth=260),
        dict(n=30, axis=1, sign=-1, box=[[-2080, 952, -512], [-1720, 984, -296]], hole_r=90, K=10, seed=137, interior=True, depth=260),
        dict(n=31, axis=1, sign=-1, box=[[-1680, 952, -512], [-1320, 984, -296]], hole_r=85, K=10, seed=139, interior=True, depth=260),
        dict(n=32, axis=1, sign=-1, box=[[-1280, 952, -512], [-1100, 984, -296]], hole_r=60, K=10, seed=149, interior=True, depth=220)]

new = []
for S in s["structures"]:
    if S["name"] == "facade":
        lower = [B for B in S["breaches"] if B["n"] not in UPPER_SITES]
        upper = [B for B in S["breaches"] if B["n"] in UPPER_SITES]
        for B in upper:
            if B["n"] in TOP:
                B["int_ceil"] = 1206; B["int_zmax"] = 1210
        S["brushes"] = [3497, 3505, 3496, 3506, 3501, 2729, 3504]
        S["cuts"] = [-5600, -4400, -3200, -2000, -890, 400]
        S["breaches"] = lower + [DOOR]
        new.append(dict(name="upper", axis=0, cuts=[-3175, -1980, -780, -275, 410], brushes=[3393, 1993], pivot="base", breaches=upper + NOTCH))
        # the long protruding ledge band (4563: y 2752..3008, z 320..576) in the same six spans: it breaks off and drops first
        new.append(dict(name="ledge", axis=0, cuts=[-3175, -1980, -780, -275, 410], brushes=[4563], pivot="base"))
    if S["name"] == "yardwall_s":
        S["brushes"] = S["brushes"] + [1088]
        S["breaches"] = S.get("breaches", []) + YARD
s["structures"] += new
json.dump(s, open(os.path.join(out, "v10_s3.json"), "w")); json.dump(t, open(os.path.join(out, "v10_s4.json"), "w"))
print("specs ->", out)

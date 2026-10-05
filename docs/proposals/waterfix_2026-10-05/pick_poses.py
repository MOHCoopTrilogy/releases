"""pick_poses.py MAP... - outdoor pathnodes next to tall walls / water, for 360-degree sweep captures (poses.json)"""
import json, math, os, sys
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\tools")
import ww_look as L
from ww_fs import FS
from find_spots import nodes, lookup

fs = FS(); out = {}
for mp in sys.argv[1:]:
    S = L.Scene(fs, "maps/%s.bsp" % mp); S.build_occlusion()
    H, x0, y0, cell = S.occ
    wm = S.cls == 1
    wc = S.xyz[wm].mean(1) if wm.any() else np.zeros((0, 3))
    cands = []
    for p in nodes(S):
        g = float(lookup(H, x0, y0, cell, p[None])[0])
        if not (p[2] - 64 < g < p[2] + 8):          # roofed, or the node floats
            continue
        ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        score = 0.0
        for r in (96, 160, 256, 384):
            q = np.stack([p[0] + r * np.cos(ang), p[1] + r * np.sin(ang), np.zeros_like(ang)], 1)
            h = lookup(H, x0, y0, cell, q)
            score += float(((h > g + 150) & (h < g + 900)).mean())   # tall walls / roofs around
        wd = float(np.hypot(wc[:, 0] - p[0], wc[:, 1] - p[1]).min()) if len(wc) else 1e9
        if len(wc) and wd < 450 and all(c[:, 2].mean() < g for c in [wc[np.hypot(wc[:, 0] - p[0], wc[:, 1] - p[1]) < 450]]):
            score += 1.5
        cands.append((score, p[0], p[1], g))
    cands.sort(reverse=True)
    pick = []
    for sc, x, y, g in cands:
        if sc < 0.5:
            break
        if all(math.hypot(x - a, y - b) > 900 for a, b, _ in pick):
            pick.append((x, y, g))
        if len(pick) == 3:
            break
    out[mp] = [[round(x, 1), round(y, 1), round(g + 82.0, 1)] for x, y, g in pick]
    print(mp, out[mp], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "poses.json"), "w"), indent=1)

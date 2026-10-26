"""ice_scout.py MAP - contact sheet of candidate camera poses that see the frozenriver ice (offline look-dev, read-only).
Reuses docs/proposals/water_wetness_2026-09-27/tools (ww_look Scene / render). Output: %WW_WORK%/ice_scout_<map>.jpg + .json"""
import os, sys, json, math
import numpy as np
from PIL import Image
WW = r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\tools"
sys.path.insert(0, WW)
import ww_look as L
from ww_fs import FS

def ice_ids(S):
    return np.array([i for i, s in enumerate(S.shaders) if "frozenriver" in s[0].lower()])

def cands(S, tri_ice, n=14):
    ents = S.bsp.entities(); pts = []
    for e in ents:
        cn = e.get("classname", "")
        if cn.startswith("info_pathnode") or cn.startswith("info_player") or cn.startswith("info_waypoint") or cn.startswith("script_origin"):
            try: pts.append([float(v) for v in e.get("origin", "").split()[:3]])
            except Exception: pass
    xyz = S.xyz[tri_ice]; c = xyz.reshape(-1, 3); lo, hi = c.min(0), c.max(0); mid = (lo + hi) / 2; z0 = float(c[:, 2].mean())
    occ, ox, oy, cell = S.occ
    # ring points around the ice, at the top-down ground height
    ring = []
    for t in np.linspace(0, 2 * math.pi, 40, endpoint=False):
        for k in (0.6, 0.9, 1.15):
            x = mid[0] + k * (hi[0] - lo[0]) / 2 * math.cos(t) * 1.15; y = mid[1] + k * (hi[1] - lo[1]) / 2 * math.sin(t) * 1.15
            ix = int((x - ox) / cell); iy = int((y - oy) / cell)
            if 0 <= ix < occ.shape[1] and 0 <= iy < occ.shape[0]:
                ring.append([x, y, float(occ[iy, ix])])
    out = []
    for p in pts + ring:
        p = np.array(p)
        if not (z0 - 60 < p[2] < z0 + 500): continue
        d = np.hypot(p[0] - mid[0], p[1] - mid[1])
        for j in range(8):
            yaw = j * math.pi / 4 + 0.2
            tgt = p + np.array([1500 * math.cos(yaw), 1500 * math.sin(yaw), -100.0])
            out.append((p + [0, 0, 56], tgt))
    sc = []
    for eye, tgt in out:
        cam, yaw, el = L.look_camera(eye, tgt, 96, 54)
        z, tid, bary = L.render_geometry(S, eye, cam, 96, 54)
        w = float(np.isin(tid, tri_ice).mean()); sk = float((tid < 0).mean())
        sc.append(w + 0.3 * min(sk, 0.25))
    order = np.argsort(sc)[::-1]; picked = []
    for i in order:
        if all(np.linalg.norm(out[i][0] - out[j][0]) > 250 or abs(sc[i] - sc[j]) > 0.15 for j in picked): picked.append(i)
        if len(picked) >= n: break
    return [(out[i][0], out[i][1], sc[i]) for i in picked]

def main(m):
    fs = FS(); S = L.Scene(fs, "maps/%s.bsp" % m); S.build_occlusion()
    ids = ice_ids(S); tri_ice = np.nonzero(np.isin(S.shv, ids))[0]
    print(m, "ice tris", len(tri_ice), flush=True)
    cs = cands(S, tri_ice); tiles = []; meta = []
    for k, (eye, tgt, sc) in enumerate(cs):
        cam, yaw, el = L.look_camera(eye, tgt, 480, 270)
        z, tid, bary = L.render_geometry(S, eye, cam, 480, 270); G = L.gbuf(S, eye, cam, 480, 270, tid, bary)
        base, alb, lmv = L.shade_base(S, G, 480, 270)
        img = L.fog_and_sky(S, base, G, cam, 480, 270, eye)
        t = L.label(L.to8(L.grade(img)), "%d  %.2f eye %s" % (k, sc, [int(v) for v in eye]), size=14)
        tiles.append(t); meta.append(dict(k=k, score=sc, eye=[float(v) for v in eye], tgt=[float(v) for v in tgt]))
    cols = 3; rows = (len(tiles) + cols - 1) // cols
    sheet = np.zeros((rows * 270, cols * 480, 3), np.uint8)
    for i, t in enumerate(tiles): sheet[(i // cols) * 270:(i // cols + 1) * 270, (i % cols) * 480:(i % cols + 1) * 480] = t
    os.makedirs(L.WORK, exist_ok=True)
    Image.fromarray(sheet).save(os.path.join(L.WORK, "ice_scout_%s.jpg" % m.replace("/", "_")), quality=85)
    json.dump(meta, open(os.path.join(L.WORK, "ice_scout_%s.json" % m.replace("/", "_")), "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])

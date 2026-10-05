"""find_spots.py - offline: where did v1.10.13 visibly fail? Candidate camera poses for the defect captures.

    python find_spots.py water m3l2 t1l2 ...   water the shipped soft-map test left WITHOUT sky (old e < 0.3) although
                                               nothing is over it (sharp map open) - "no reflection at all" areas
    python find_spots.py eave m5l1b m4l2 ...   long straight wet/dry lines: floor points under a roof edge (sharp tap
                                               sheltered) next to exposed floor - "cut off at angles"
Writes spots_<mode>.json: per map, the biggest clusters and a pathnode eye 250-700 u away that looks at each.
Read-only on the game data (the look-dev FS/BSP tools).
"""
import json, math, os, sys
import numpy as np
from scipy import ndimage

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\tools")
import ww_look as L  # noqa: E402
from ww_fs import FS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def engine_soft(H, cell):
    """tr_hzm_wet.c v1.10.3 R_HZMWaterBuildSoftOcclusion: floor empty cells at min-512, 4x4 mean, sigma 48 u."""
    real = H > -1e4
    floor = float(H[real].min()) - 512.0
    Hf = np.where(real, H, floor).astype(np.float32)
    ny, nx = Hf.shape
    pad = np.full(((ny + 3) // 4 * 4, (nx + 3) // 4 * 4), floor, np.float32)
    pad[:ny, :nx] = Hf
    m = pad.reshape(pad.shape[0] // 4, 4, pad.shape[1] // 4, 4).mean((1, 3))
    m = ndimage.gaussian_filter(m, sigma=48.0 / (cell * 4))
    return ndimage.zoom(m, 4, order=1)[:ny, :nx]


def samples(xyz, step=24.0):
    """points on triangles on a ~step grid (barycentric lattice)"""
    out = []
    for t in xyz:
        a, b, c = t
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a))
        n = max(1, int(math.sqrt(area) / step))
        for i in range(n + 1):
            for j in range(n + 1 - i):
                u, v = i / max(n, 1), j / max(n, 1)
                out.append(a + (b - a) * u + (c - a) * v)
    return np.array(out) if out else np.zeros((0, 3))


def lookup(G, x0, y0, cell, p):
    i = np.clip(((p[:, 0] - x0) / cell).astype(int), 0, G.shape[1] - 1)
    j = np.clip(((p[:, 1] - y0) / cell).astype(int), 0, G.shape[0] - 1)
    return G[j, i]


def nodes(S):
    out = []
    for e in S.bsp.entities():
        cn = e.get("classname", "")
        if cn.startswith("info_pathnode") or cn.startswith("info_player"):
            out.append([float(v) for v in e.get("origin", "0 0 0").split()[:3]])
    return np.array(out) if out else np.zeros((0, 3))


def pose_for(S, H, x0, y0, cell, target, nd, dmin=250, dmax=700):
    best = None
    for p in nd:
        d = math.hypot(target[0] - p[0], target[1] - p[1])
        if not (dmin < d < dmax):
            continue
        g = float(lookup(H, x0, y0, cell, p[None])[0])
        if g > p[2] + 40:          # node under a roof: skip
            continue
        eye = np.array([p[0], p[1], max(g, p[2] - 32) + 82.0])
        if eye[2] < target[2] + 30:
            continue
        # crude line of sight on the max-height map
        ok = True
        for s in np.linspace(0.1, 0.92, 24):
            q = eye + (target - eye) * s
            if float(lookup(H, x0, y0, cell, q[None])[0]) > q[2] + 4:
                ok = False
                break
        if ok and (best is None or abs(d - 420) < abs(best[1] - 420)):
            best = (eye, d)
    return best


def clusters(mask_pts, cell=48.0, minn=6):
    if len(mask_pts) == 0:
        return []
    key = np.floor(mask_pts[:, :2] / cell).astype(int)
    mn = key.min(0)
    grid = np.zeros(tuple(key.max(0) - mn + 1), bool)
    grid[tuple((key - mn).T)] = True
    lab, n = ndimage.label(grid, structure=np.ones((3, 3)))
    out = []
    for k in range(1, n + 1):
        sel = lab[tuple((key - mn).T)] == k
        if sel.sum() >= minn:
            out.append((int(sel.sum()), mask_pts[sel].mean(0), mask_pts[sel]))
    return sorted(out, key=lambda c: -c[0])


def main():
    mode, maps = sys.argv[1], sys.argv[2:]
    fs = FS()
    res = {}
    for mp in maps:
        S = L.Scene(fs, "maps/%s.bsp" % mp)
        S.build_occlusion()
        H, x0, y0, cell = S.occ
        nd = nodes(S)
        if mode == "water":
            wm = S.cls == 1
            if not wm.any():
                continue
            pts = samples(S.xyz[wm])
            Hs = engine_soft(H, cell)
            hs = lookup(Hs, x0, y0, cell, pts)
            hh = lookup(H, x0, y0, cell, pts)
            z = pts[:, 2]
            e_old = np.clip((z + 8.0 - hs + 2.0 + 48.0) / 50.0, 0, 1)
            open_ = hh < z + 8.0
            dead = open_ & (e_old < 0.3)
            res[mp] = {"water_pts": int(len(pts)), "open_frac": float(open_.mean()),
                       "dead_frac_of_open": float(dead.sum() / max(open_.sum(), 1)), "spots": []}
            for n, c, cp in clusters(pts[dead])[:4]:
                pz = pose_for(S, H, x0, y0, cell, c, nd)
                res[mp]["spots"].append({"n": n, "target": [round(v, 1) for v in c],
                                         "eye": [round(v, 1) for v in pz[0]] if pz else None})
        else:
            fm = (S.cls == 0) & (S.mdl <= 0)
            nrm = np.cross(S.xyz[:, 1] - S.xyz[:, 0], S.xyz[:, 2] - S.xyz[:, 0])
            nz = np.abs(nrm[:, 2]) / np.maximum(np.linalg.norm(nrm, axis=1), 1e-6)
            pts = samples(S.xyz[fm & (nz > 0.9)], 16.0)
            hh = lookup(H, x0, y0, cell, pts)
            shel = hh > pts[:, 2] + 40.0
            # sheltered points with exposed floor within 16 u, under a roof edge 40-400 u up
            ex = pts[~shel]
            from scipy.spatial import cKDTree
            tr = cKDTree(ex[:, :2]) if len(ex) else None
            near = np.array([len(tr.query_ball_point(p[:2], 16.0)) > 0 for p in pts[shel]]) if tr is not None else np.zeros(0, bool)
            edge = pts[shel][near] if len(near) else np.zeros((0, 3))
            res[mp] = {"floor_pts": int(len(pts)), "sheltered_frac": float(shel.mean()), "edge_pts": int(len(edge)), "spots": []}
            for n, c, cp in clusters(edge, cell=64.0, minn=8)[:5]:
                # straightness: the ratio of the cluster's principal axes
                d = cp[:, :2] - cp[:, :2].mean(0)
                ev = np.linalg.eigvalsh(np.cov(d.T)) if len(cp) > 2 else np.array([1, 1])
                pz = pose_for(S, H, x0, y0, cell, c, nd)
                res[mp]["spots"].append({"n": n, "straight": round(float(ev[-1] / max(ev[0], 1e-3)), 1),
                                         "target": [round(v, 1) for v in c],
                                         "eye": [round(v, 1) for v in pz[0]] if pz else None})
        print(mp, json.dumps(res[mp])[:900], flush=True)
    json.dump(res, open(os.path.join(HERE, "spots_%s.json" % mode), "w"), indent=1)


if __name__ == "__main__":
    main()

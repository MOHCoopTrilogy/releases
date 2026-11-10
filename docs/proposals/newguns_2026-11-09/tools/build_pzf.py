"""H:/hzm_work/newguns/build/pzf/tris.npz (bl_extract.py) -> <out>/models/weapons/coop_panzerfaust/coop_panzerfaust.skd
                                                       + <out>/models/projectiles/coop_panzerfaust/coop_pzfhead.skd (the flying warhead)

Bones = the Panzerschreck's (origin, Box01, panzer01, tag_barrel, tag_eject), same names and order, so its view clips drive it; the
whole launcher rides panzer01 (the shipped tube's bone). Surfaces: `pzftube*` (tube, trigger lever, sight leaf) and `pzfhead*` (the
warhead + its tail, outside the tube): the tik hides pzfhead the frame the shot leaves, so the spent tube is what the player drops.
The projectile is the same warhead on one bone (origin), nose along +x, centred on its tail end like the retail shells.
    python build_pzf.py [out_root]
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools")
import pzflib as L
import skx as X

BONES = [('origin', 'worldbone'), ('Box01', 'origin'), ('panzer01', 'origin'), ('tag_barrel', 'origin'), ('tag_eject', 'origin')]
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(L.BUILD, 'ship')


def corners(A, bone, M, conv=None):
    out = []
    Minv = np.linalg.inv(M[:3])
    for tri in A:
        if conv is None:
            g = L.to_gun(tri[:, :3]); gn = L.nrm_gun(tri[:, 3:6])
        else:
            g, gn = conv(tri[:, :3]), conv(tri[:, 3:6], True)
        p = (g - M[3]) @ Minv
        n = gn @ Minv; n = n / np.linalg.norm(n, axis=1, keepdims=True)
        uv = tri[:, 6:8].astype(float)
        c = [(bone, p[k], n[k], (float(uv[k, 0]), float(1.0 - uv[k, 1]))) for k in range(3)]
        if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:
            c = [c[0], c[2], c[1]]
        out.append(c)
    out.sort(key=lambda c: c[0][1][0] + c[1][1][0] + c[2][1][0])
    return out


def main():
    d = np.load(os.path.join(L.BUILD, 'tris.npz'))
    A, part = d['corners'], d['part']
    M2 = np.load(os.path.join(os.path.dirname(L.BUILD), 'pzs_affine_2.npy'))
    head = np.isin(part, list(L.HEAD_PARTS))
    surfs = X.split_surfaces('pzftube', corners(A[~head], 2, M2))
    surfs += X.split_surfaces('pzfhead', corners(A[head], 2, M2))
    od = os.path.join(OUT, 'models', 'weapons', 'coop_panzerfaust'); os.makedirs(od, exist_ok=True)
    skd = X.build_skd('coop_panzerfaust', BONES, surfs)
    open(os.path.join(od, 'coop_panzerfaust.skd'), 'wb').write(skd)
    G = L.to_gun(A[:, :, :3]).reshape(-1, 3)
    GH = L.to_gun(A[head][:, :, :3]).reshape(-1, 3)
    F, R = L.to_gun(L.PIN_TIP), L.to_gun(L.LEAF_TOP)
    # projectile: the warhead in its own frame, metres -> game units like the launcher, nose +x, z UP (an entity model), origin at
    # the tail's end (it leaves the tube tail-first from tag_barrel... the retail shells put the origin at their middle: kept simple)
    tail = A[head][:, :, 0].min()
    def conv(p, normal=False):
        p = np.asarray(p, float)
        if normal:
            return p / np.maximum(np.linalg.norm(p, axis=-1, keepdims=True), 1e-9)
        return np.stack([p[..., 0] - tail, p[..., 1] - L.AXIS_Y, p[..., 2]], -1) * L.S
    ps = X.split_surfaces('pzfshell', corners(A[head], 0, np.vstack([np.eye(3) * 0.52, np.zeros(3)]), conv))
    pd = os.path.join(OUT, 'models', 'projectiles', 'coop_panzerfaust'); os.makedirs(pd, exist_ok=True)
    open(os.path.join(pd, 'coop_pzfhead.skd'), 'wb').write(X.build_skd('coop_pzfhead', [('origin', 'worldbone')], ps))
    json.dump(dict(surfaces=[s[0] for s in surfs], gun_min=G.min(0).tolist(), gun_max=G.max(0).tolist(), head_max_x=float(GH[:, 0].max()),
                   F=F.tolist(), R=R.tolist(), S=L.S, T=L.T.tolist()), open(os.path.join(L.BUILD, 'coop_panzerfaust.json'), 'w'), indent=1)
    print('skd %d bytes, %d surfaces, %d tris; gun x %.2f..%.2f; F %s R %s' % (len(skd), len(surfs), sum(len(s[1]) for s in surfs),
          G[:, 0].min(), G[:, 0].max(), np.round(F, 3), np.round(R, 3)))


if __name__ == '__main__':
    main()

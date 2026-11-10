"""H:/hzm_work/newguns/build/mp28/tris.npz (bl_extract.py) + atlas.json (mp28_sheet.py) -> <out>/models/weapons/coop_bergmann/coop_bergmann.skd

Bones = the Sten Mk II's (origin, Sten_SMG, Sten_Bolt, Sten_Clip, tag_barrel, tag_eject), same names and order, so the Sten's view
and reload clips drive it: the gun rides Sten_SMG, the MAGAZINE rides Sten_Clip (the Sten's reloads carry its magazine off and back
on that bone - the MP 28's also feeds from the LEFT). The bolt handle stays on the body (the Sten's open-bolt clips stroke
Sten_Bolt every shot; its handle is a different shape). Bone frames solved from the shipped Sten (sten_affine_<bone>.npy).
    python build_mp28.py [out_root]
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools")
import mp28lib as L
import skx as X

BONES = [('origin', 'worldbone'), ('Sten_SMG', 'origin'), ('Sten_Bolt', 'Sten_SMG'), ('Sten_Clip', 'Sten_SMG'),
         ('tag_barrel', 'Sten_SMG'), ('tag_eject', 'Sten_SMG')]
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(L.BUILD, 'ship')


def corners(A, mats, bone, M, atlas):
    out = []
    Minv = np.linalg.inv(M[:3])
    N = atlas['size']
    for tri, mat in zip(A, mats):
        g = L.to_gun(tri[:, :3]); gn = L.nrm_gun(tri[:, 3:6])
        p = (g - M[3]) @ Minv
        n = gn @ Minv; n = n / np.linalg.norm(n, axis=1, keepdims=True)
        uv = tri[:, 6:8].astype(float)
        if mat not in atlas['tiles'] or uv.max() > 1.001 or uv.min() < -0.001:      # tiled UVs (the recoil spring): one flat texel
            fl = atlas['tiles']['Flat']; u = np.full(3, fl['u']); v = np.full(3, fl['v'])
        else:
            t = atlas['tiles'][mat]
            u = (t['x'] + t['pad'] + uv[:, 0] * t['inner']) / N
            v = (t['y'] + t['pad'] + (1.0 - uv[:, 1]) * t['inner']) / N
        c = [(bone, p[k], n[k], (float(u[k]), float(v[k]))) for k in range(3)]
        if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:
            c = [c[0], c[2], c[1]]
        out.append(c)
    out.sort(key=lambda c: c[0][1][0] + c[1][1][0] + c[2][1][0])
    return out


def main():
    d = np.load(os.path.join(L.BUILD, 'tris.npz'))
    A, part, mat = d['corners'], d['part'], d['mat']
    atlas = json.load(open(os.path.join(L.BUILD, 'atlas.json')))
    M1 = np.load(os.path.join(os.path.dirname(L.BUILD), 'sten_affine_1.npy'))
    M3 = np.load(os.path.join(os.path.dirname(L.BUILD), 'sten_affine_3.npy'))
    mag = np.isin(part, list(L.MAG_PARTS))
    surfs = X.split_surfaces('mp28', corners(A[~mag], mat[~mag], 1, M1, atlas))
    ms = X.split_surfaces('mp28clip', corners(A[mag], mat[mag], 3, M3, atlas)); assert len(ms) == 1
    surfs.append(('mp28clip',) + tuple(ms[0][1:]))
    od = os.path.join(OUT, 'models', 'weapons', 'coop_bergmann'); os.makedirs(od, exist_ok=True)
    skd = X.build_skd('coop_bergmann', BONES, surfs)
    open(os.path.join(od, 'coop_bergmann.skd'), 'wb').write(skd)
    G = L.to_gun(A[:, :, :3]).reshape(-1, 3)
    json.dump(dict(surfaces=[s[0] for s in surfs], gun_min=G.min(0).tolist(), gun_max=G.max(0).tolist(), S=L.S, T=L.T.tolist()),
              open(os.path.join(L.BUILD, 'coop_bergmann.json'), 'w'), indent=1)
    print('skd %d bytes, %d surfaces, %d verts, %d tris; gun x %.2f..%.2f' % (len(skd), len(surfs), sum(len(s[2]) for s in surfs),
          sum(len(s[1]) for s in surfs), G[:, 0].min(), G[:, 0].max()))
    for s in surfs:
        print('  %-10s v %4d t %4d' % (s[0], len(s[2]), len(s[1])))


if __name__ == '__main__':
    main()

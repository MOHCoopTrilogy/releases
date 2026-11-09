"""build/tris.npz (bl_extract.py) + build/atlas.json (atlas.py) -> ship/models/weapons/fg42/coop_fg42hd_irons.skd

Bones = the shipped FG 42's, same names and order (origin, FG42, tag_eject, tag_barrel, coop_chg), so DaRKaNGeL's fg42.skc and
every coop_* clip of ads_twohand_2026-10-11/heavy drive it unchanged. Rigid: every part rides `FG42`; the magazine is ONE surface
named `fg42clip` (the tiks hide it during the reloads); the charging handle is the SHIPPED `coop_handle` surface, byte-equivalent
(it rides `coop_chg`, whose clips were authored for it); the source's own Bolt (the handle) is not used.
    python build_mesh.py
"""
import os, sys, json, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import fglib as L
import skx as X
import skd as K
import gen_wpnfix_pak as W

BONES = [('origin', 'worldbone'), ('FG42', 'origin'), ('tag_eject', 'FG42'), ('tag_barrel', 'FG42'), ('coop_chg', 'FG42')]
DROP = {'Bolt'}
NAME = os.environ.get('FG_NAME', 'coop_fg42hd_irons')
OUT = os.path.join(L.SHIP, 'models', 'weapons', 'fg42')


def corners(A, mats, atlas):
    out = []
    N = atlas['size']
    for tri, mat in zip(A, mats):
        t = atlas['tiles'][mat]
        p = L.to_raw(tri[:, :3]); n = L.nrm_raw(tri[:, 3:6])
        uv = tri[:, 6:8].astype(float)
        u = (t['x'] + t['pad'] + np.clip(uv[:, 0], 0, 1) * t['inner']) / N
        v = (t['y'] + t['pad'] + (1.0 - np.clip(uv[:, 1], 0, 1)) * t['inner']) / N      # skd v: 0 = top row
        c = [(1, p[k], n[k], (u[k], v[k])) for k in range(3)]
        fn = np.cross(p[1] - p[0], p[2] - p[0])
        if np.dot(fn, n.sum(0)) > 0:
            c = [c[0], c[2], c[1]]
        out.append(c)
    out.sort(key=lambda c: c[0][1][0] + c[1][1][0] + c[2][1][0])
    return out


def old_handle():
    w, b = W.carriers('models/weapons/fg42/coop_fg42_irons.skd')[-1]
    s = [s for s in K.read(b)['surfaces'] if s['name'] == 'coop_handle'][0]
    verts = [(v['n'], v['uv'], v['bone'], v['pos']) for v in s['verts']]
    return ('coop_handle', np.asarray(s['tris'], int), verts)


def main():
    d = np.load(os.path.join(L.BUILD, 'tris.npz'))
    A, obj, mat = d['corners'], d['obj'], d['mat']
    atlas = json.load(open(os.path.join(L.BUILD, 'atlas.json')))
    keep = np.array([o not in DROP for o in obj])
    mag = keep & (obj == 'Magazine')
    rest = keep & (obj != 'Magazine')
    surfs = X.split_surfaces('fg42hd', corners(A[rest], mat[rest], atlas))
    ms = X.split_surfaces('fg42clip', corners(A[mag], mat[mag], atlas))
    assert len(ms) == 1
    surfs.append(('fg42clip',) + tuple(ms[0][1:]))
    surfs.append(old_handle())
    os.makedirs(OUT, exist_ok=True)
    skd = X.build_skd('fg42', BONES, surfs)
    open(os.path.join(OUT, NAME + '.skd'), 'wb').write(skd)
    pts = np.array([np.asarray(off) for s in surfs[:-1] for (_n, _uv, _b, off) in s[2]])
    meta = dict(surfaces=[s[0] for s in surfs], bmin=pts.min(0).tolist(), bmax=pts.max(0).tolist(),
                aperture=L.to_raw(L.R_SRC).tolist(), post=L.to_raw(L.F_SRC).tolist(), pitch=L.PITCH, scale=L.S)
    json.dump(meta, open(os.path.join(L.BUILD, NAME + '.json'), 'w'), indent=1)
    print('skd %s %d bytes, %d surfaces, %d verts, %d tris' % (NAME, len(skd), len(surfs), sum(len(s[2]) for s in surfs),
                                                            sum(len(s[1]) for s in surfs)))
    for s in surfs:
        print('  %-12s v %4d t %4d' % (s[0], len(s[2]), len(s[1])))


if __name__ == '__main__':
    main()

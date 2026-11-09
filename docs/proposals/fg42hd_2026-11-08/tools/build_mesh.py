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
SCOPED = os.environ.get('FG_SCOPE') == '1'
NAME = os.environ.get('FG_NAME', 'coop_fg42hd' if SCOPED else 'coop_fg42hd_irons')
RECEIVER_TOP = -2.2      # local raw z of the receiver top under the scope (measured: -2.30..-2.56 over x -2..10)
OUT = os.path.join(L.SHIP, 'models', 'weapons', 'fg42')


def corners(A, mats, atlas):
    out = []
    N = atlas['size']
    for tri, mat in zip(A, mats):
        p = L.to_raw(tri[:, :3]); n = L.nrm_raw(tri[:, 3:6])
        if mat == 'Ring':                                    # one plain steel texel of the sheet (the Rear_sight tile)
            u = np.full(3, L.RING_UV[0]); v = np.full(3, L.RING_UV[1])
        else:
            t = atlas['tiles'][mat]
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
    # [QA 2026-11-08] the diopter's aperture LOOP is real size - a pin-hole at game scale, and the ADS view looked at the back of the
    # range drum. It is replaced by a THIN GHOST RING (fglib.RING_*) raised just clear of the drum on a short stem, so the eye looks
    # through a ring around the front post and the drum sits below it as a narrow stalk. The sight row's R is the ring centre.
    loop = (obj == 'Rear_sight') & (A[:, :, 2].min(1) > L.APER_Z0)
    keep = keep & ~loop
    ring = L.ring_tris()
    if SCOPED:                                   # the scoped gun: no diopter (the ZFG 42 sits over it), no ghost ring
        keep = keep & (obj != 'Rear_sight')
        ring = ring[:0]
    A = np.concatenate([A, ring])
    obj = np.concatenate([obj, np.array(['Ring'] * len(ring))])
    mat = np.concatenate([mat, np.array(['Ring'] * len(ring))])
    keep = np.concatenate([keep, np.ones(len(ring), bool)])
    mag = keep & (obj == 'Magazine')
    rest = keep & (obj != 'Magazine')
    surfs = X.split_surfaces('fg42hd', corners(A[rest], mat[rest], atlas))
    ms = X.split_surfaces('fg42clip', corners(A[mag], mat[mag], atlas))
    assert len(ms) == 1
    surfs.append(('fg42clip',) + tuple(ms[0][1:]))
    if SCOPED:
        import scope_mesh as SM
        st = SM.build(RECEIVER_TOP)
        def sc(mt):
            out = []
            for m, c in st:
                if m in mt:
                    cc = [(1, p, n, uv) for (p, n, uv) in c]
                    fn = np.cross(cc[1][1] - cc[0][1], cc[2][1] - cc[0][1])
                    if np.dot(fn, c[0][1] + c[1][1] + c[2][1]) > 0:
                        cc = [cc[0], cc[2], cc[1]]
                    out.append(cc)
            return out
        surfs += X.split_surfaces('fg42hdsc', sc(('steel',)))
        z = X.split_surfaces('fg42cup', sc(('cup',)))      # the rubber eyecup (its own surface: one shader, drawn as is at the eye)
        assert len(z) == 1
        surfs.append(('fg42cup',) + tuple(z[0][1:]))
        lz = X.split_surfaces('fg42lens', sc(('lens', 'glass')))   # objective + ocular glass: coop_scope_glass_blue, the lens pass's glass
        assert len(lz) == 1
        surfs.append(('fg42lens',) + tuple(lz[0][1:]))
    surfs.append(old_handle())
    os.makedirs(OUT, exist_ok=True)
    skd = X.build_skd('fg42', BONES, surfs)
    open(os.path.join(OUT, NAME + '.skd'), 'wb').write(skd)
    pts = np.array([np.asarray(off) for s in surfs[:-1] for (_n, _uv, _b, off) in s[2]])
    meta = dict(surfaces=[s[0] for s in surfs], bmin=pts.min(0).tolist(), bmax=pts.max(0).tolist(),
                aperture=L.to_raw(L.RING_C).tolist(), post=L.to_raw(L.F_SRC).tolist(), pitch=L.PITCH, scale=L.S)
    json.dump(meta, open(os.path.join(L.BUILD, NAME + '.json'), 'w'), indent=1)
    print('skd %s %d bytes, %d surfaces, %d verts, %d tris' % (NAME, len(skd), len(surfs), sum(len(s[2]) for s in surfs),
                                                            sum(len(s[1]) for s in surfs)))
    for s in surfs:
        print('  %-12s v %4d t %4d' % (s[0], len(s[2]), len(s[1])))


if __name__ == '__main__':
    main()

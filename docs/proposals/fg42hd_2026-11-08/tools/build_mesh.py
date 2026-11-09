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


def old_surface(rel, name):
    w, b = W.carriers(rel)[-1]
    s = [s for s in K.read(b)['surfaces'] if s['name'] == name][0]
    verts = [(v['n'], v['uv'], v['bone'], v['pos']) for v in s['verts']]
    return (name, np.asarray(s['tris'], int), verts)


def old_handle():
    return old_surface('models/weapons/fg42/coop_fg42_irons.skd', 'coop_handle')


FS_X, FS_Z = (48.5, 53.5), -1.7           # the front sight's post + hood on the source barrel (local raw; the barrel top is ~ -1.0)
SCOPE_Z, SCOPE_X = -4.4, (-8.6, 8.6)      # the shipped scope + its mount in coop_fg42.skd's fg42base: everything above the old receiver


def old_scope():
    """the shipped scope out of coop_fg42.skd's `fg42base` (triangles above its receiver, between the scope's ends), verbatim, plus
    a mount block from the shipped mount's foot down onto the new, lower receiver, textured from the mount's own texel"""
    w, b = W.carriers('models/weapons/fg42/coop_fg42.skd')[-1]
    s = [s for s in K.read(b)['surfaces'] if s['name'] == 'fg42base'][0]
    P = np.array([np.asarray(v['pos'], float).reshape(-1, 3)[0] for v in s['verts']])
    T = np.asarray(s['tris'], int)
    C = P[T].mean(1)
    sel = (C[:, 2] < SCOPE_Z) & (C[:, 0] > SCOPE_X[0]) & (C[:, 0] < SCOPE_X[1])
    T = T[sel]
    used = sorted(set(T.ravel()))
    remap = {o: i for i, o in enumerate(used)}
    verts = [(s['verts'][o]['n'], s['verts'][o]['uv'], s['verts'][o]['bone'], s['verts'][o]['pos']) for o in used]
    tris = [[remap[a] for a in t] for t in T]
    # the mount's foot: the lowest selected vertices under the scope's middle
    mp = P[used]
    foot = mp[(mp[:, 0] > -2.5) & (mp[:, 0] < 3.5)]
    fz = foot[:, 2].max()                                    # -z is up: the mount's lowest point
    x0, x1 = foot[:, 0].min(), foot[:, 0].max()
    y0, y1 = foot[:, 1].min(), foot[:, 1].max()
    # a dark steel texel of the scope's own sheet: the mount's foot vertex sampled a light-grey texel and the block read as a pale box (QA #3)
    from PIL import Image
    import io as _io
    sheet = np.asarray(Image.open(_io.BytesIO(W.carriers('textures/fg42/fg42.jpg')[-1][1])).convert('L'), float)
    lum = [sheet[min(int(v[1] % 1 * sheet.shape[0]), sheet.shape[0] - 1), min(int(v[0] % 1 * sheet.shape[1]), sheet.shape[1] - 1)]
           for v in (s['verts'][o]['uv'] for o in used)]
    order = np.argsort(lum)
    pick = order[int(0.25 * len(order))]                     # the darker quarter, not the darkest (that is a black seam)
    uv = s['verts'][used[pick]]['uv']
    bone = s['verts'][used[0]]['bone']
    lo, hi = np.array([x0, y0, fz - 0.15]), np.array([x1, y1, RECEIVER_TOP])
    Pq = lambda i, j, k: [(lo, hi)[i][0], (lo, hi)[j][1], (lo, hi)[k][2]]
    faces = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
             ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)])]
    for n, idx in faces:
        q = [np.array(Pq(*t)) for t in idx]
        base = len(verts)
        for p in q:
            verts.append((list(map(float, n)), uv, bone, [list(map(float, p))] if isinstance(s['verts'][0]['pos'][0], (list, tuple)) else list(map(float, p))))
        for a, bb, c in ((0, 1, 2), (0, 2, 3)):
            fn = np.cross(q[bb] - q[a], q[c] - q[a])
            tri = [base + a, base + bb, base + c] if np.dot(fn, n) < 0 else [base + a, base + c, base + bb]   # retail winding
            tris.append(tri)
    print('  shipped scope: %d tris, mount foot z %.2f -> receiver %.2f' % (len(tris), fz, RECEIVER_TOP))
    return ('fg42scope', np.asarray(tris, int), verts)


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
    if SCOPED:                                   # the scoped gun: no diopter (the scope sits over it), no ghost ring
        keep = keep & (obj != 'Rear_sight')
        ring = ring[:0]
        # and the front sight folded away (the scoped FG 42's was folded flat): its post and hood rose into the scope's view, and the
        # hood read as the irons' ghost ring leaking onto the front post (QA #3)
        cx = L.to_raw(A[:, :, :3].reshape(-1, 3)).reshape(-1, 3, 3).mean(1)
        keep = keep & ~((obj == 'Barrel') & (cx[:, 0] > FS_X[0]) & (cx[:, 0] < FS_X[1]) & (cx[:, 2] < FS_Z))
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
        # [QA 2026-11-08 #3] the SHIPPED scope (coop_fg42.skd through v1.10.65, which the user found fine and which the lens view was
        # tuned on) rides the new body unchanged: same bone, same local coordinates, so it sits exactly on the shipped scope sight row.
        # The in-house ZFG 42 (scope_mesh.py, removed) read as an oversized can, blocky and mounted too high. Only a mount block is new:
        # the shipped mount stopped at the old receiver, the new one is lower.
        surfs.append(old_scope())
        surfs.append(old_surface('models/weapons/fg42/coop_fg42.skd', 'fg42lens'))
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

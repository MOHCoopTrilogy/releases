"""H:/hzm_work/newguns/build/bren/tris.npz (bl_extract.py, NG_ROTX=90) -> <out>/models/weapons/coop_bren/coop_bren.skd (+ .json)

Bones = the Vickers-Berthier's (origin, vickers, tag_eject, Rechamber, tag_barrel), same names and order, so the VB's view and
reload animations drive it. The gun rides `vickers`; the cocking handle (source part 37, right side) rides `Rechamber` (the VB's
handle bone, which its reloads stroke); the magazine is ONE surface `brenclip` (the tik hides it during the reloads).
Bone-local frames: solved from the shipped VB mesh against its idle pose (gun = local @ M[:3] + M[3]; vb_affine_<bone>.npy).
[QA 2026-11-09] the bipod is FOLDED forward under the barrel (the source has it deployed): each leg turns about its top.
    python build_bren.py [out_root]
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\fg42hd_2026-11-08\tools")
import brenlib as L
import skx as X

BONES = [('origin', 'worldbone'), ('vickers', 'origin'), ('tag_eject', 'vickers'), ('Rechamber', 'vickers'), ('tag_barrel', 'vickers')]
MAG_PARTS = {4, 5, 6, 7}
HANDLE_PARTS = {37}
LEG_PARTS = {18, 20}
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(L.BUILD, 'ship')
# [newguns2 2026-11-09] THE SIGHTS ARE REBUILT ON THE MODEL (bren_sights.py): the source's own arm + aperture leaf (34), aperture
# disc (49), front blade / ears (55 / 16) and the ring on the magazine catch (35) are dropped; the drum (32, 33) stays where it is
# (it already sits on the line, left of the magazine). The v1.10.68 stopgaps are gone: no SIGHT_DY shear, no floating ring.
DROP_PARTS = {34, 49, 35, 16, 55}
NEW_PART0 = 60
SIGHT_LUM = float(os.environ.get('BREN_SIGHT_LUM', '72'))   # the new sight parts' steel (sheet luminance; the receiver averages ~50)
# [newguns2] the carrying handle (grip 2, arm 3, barrel collar 8) is turned down to the RIGHT about the bore, the way it is
# folded for firing: upright it stood in the aperture's view right of the blade (the sights are on the left)
CARRY_PARTS, HANDLE_DEG = {2, 3, 8}, float(os.environ.get('BREN_HANDLE_DEG', '95'))


def rot_to(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b)); s = np.linalg.norm(v)
    if s < 1e-9:
        return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k * ((1 - c) / s ** 2)


def fold_legs(A, part):
    A = A.copy()
    for lp in LEG_PARTS:
        m = part == lp
        P = A[m][:, :, :3].reshape(-1, 3)
        h = P[np.argmax(P[:, 2])]                                   # the leg's top: its hinge on the yoke
        foot = P[P[:, 2] < P[:, 2].min() + 0.3].mean(0)
        sy = np.sign(foot[1])
        t = np.array([-1.0, -sy * 0.015, -0.07])                    # forward (source -x), legs together, a little down
        R = rot_to(foot - h, t)
        q = A[m]
        q[:, :, :3] = (q[:, :, :3] - h) @ R.T + h
        q[:, :, 3:6] = q[:, :, 3:6] @ R.T
        A[m] = q
        print('  leg %d hinge %s foot %s -> %s' % (lp, np.round(h, 2), np.round(foot, 2), np.round((foot - h) @ R.T + h, 2)))
    return A


def sight_parts(cand_uv, BS):
    """bren_sights.parts() (gun frame) -> source-frame corner rows (T, 3, 8). Textured from a 40-texel window of the sheet's
    receiver steel (picked among the receiver's own UVs: mean luminance nearest SIGHT_LUM, some grain), mapped planar so the
    parts carry the steel's grain; the first look (one flat texel) read as a black cut-out in game"""
    from PIL import Image
    sheet = np.asarray(Image.open(os.path.join(L.BUILD, 'bren.png')).convert('L'), float)
    h, w = sheet.shape
    best = None
    for uv in cand_uv[::7]:
        x, y = int(uv[0] * (w - 1)), int((1 - uv[1]) * (h - 1))
        if x < 20 or y < 20 or x > w - 21 or y > h - 21:
            continue
        win = sheet[y - 20:y + 20, x - 20:x + 20]
        if win.std() < 8:
            continue
        sc = abs(win.mean() - SIGHT_LUM)
        if best is None or sc < best[0]:
            best = (sc, uv, win.mean(), win.std())
    c = best[1]
    half = 18.0 / w
    Ls = np.array([-1.0, 1.0, -1.0])
    rows, ids = [], []
    for k, (name, tris) in enumerate(BS.parts().items()):
        P = np.array([t for t, n in tris]).reshape(-1, 3)
        ctr = (P.min(0) + P.max(0)) / 2
        span = max(float((P.max(0) - P.min(0)).max()), 1e-6)
        sc = 1.8 * half / span                  # the whole part inside the window: continuous UVs, no seams (a wrap drew one)
        for tri, n in tris:
            src = ((tri - L.T) / L.S) * Ls
            ns = n * Ls
            q = tri - ctr
            uu = c[0] + (q[:, 1] + 0.5 * q[:, 0]) * sc * 0.67
            vv = c[1] + (q[:, 2] + 0.3 * q[:, 0]) * sc * 0.77
            rows.append([list(src[i]) + list(ns) + [uu[i], vv[i]] for i in range(3)])
            ids.append(NEW_PART0 + k)
    print('  sight parts: %d tris, steel window uv %s (mean %.0f, grain %.0f)' % (len(rows), np.round(c, 4), best[2], best[3]))
    return np.array(rows, np.float32), np.array(ids)


def fold_handle(A, part):
    """turn the handle parts about the bore axis (source frame: the bore is the x line at z = BORE_SRC_Z, y = 0)"""
    A = A.copy()
    a = math.radians(HANDLE_DEG)
    # gun frame: +y right, +z down; up (-z) -> right (+y) is a turn of +a about +x in (y, z): y' = y c - z s, z' = y s + z c.
    # source frame: (y, z)_src = (y, -z)_gun, so the same turn is y' = y c + z s, z' = -y s + z c about the bore
    c, s_ = math.cos(a), math.sin(a)
    m = np.isin(part, list(CARRY_PARTS))
    for off in (0, 3):
        y = A[m][:, :, off + 1].copy(); z = A[m][:, :, off + 2].copy()
        z0 = L.BORE_SRC_Z if off == 0 else 0.0
        q = A[m]
        q[:, :, off + 1] = y * c + (z - z0) * s_
        q[:, :, off + 2] = -y * s_ + (z - z0) * c + z0
        A[m] = q
    return A


def to_local(g, M):
    """gun frame -> bone-local (inverse of gun = local @ M[:3] + M[3])"""
    return (g - M[3]) @ np.linalg.inv(M[:3])


def corners(A, bone, M):
    out = []
    Minv = np.linalg.inv(M[:3])
    for tri in A:
        g = L.to_gun(tri[:, :3]); gn = L.nrm_gun(tri[:, 3:6])
        p = to_local(g, M)
        n = gn @ Minv; n = n / np.linalg.norm(n, axis=1, keepdims=True)
        uv = tri[:, 6:8].astype(float)
        c = [(bone, p[k], n[k], (float(uv[k, 0]), float(1.0 - uv[k, 1]))) for k in range(3)]
        if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n.sum(0)) > 0:      # retail winding: cross . n < 0
            c = [c[0], c[2], c[1]]
        out.append(c)
    out.sort(key=lambda c: c[0][1][0] + c[1][1][0] + c[2][1][0])
    return out


def main():
    d = np.load(os.path.join(L.BUILD, 'tris.npz'))
    A, part = d['corners'], d['part']
    A = fold_legs(A, part)
    A = fold_handle(A, part)
    keep = ~np.isin(part, list(DROP_PARTS))
    import bren_sights as BS
    new, newp = sight_parts(A[part == 0][:, :, 6:8].reshape(-1, 2), BS)
    A = np.concatenate([A[keep], new]); part = np.concatenate([part[keep], newp])
    M1 = np.load(os.path.join(L.BUILD, 'vb_affine_1.npy')); M3 = np.load(os.path.join(L.BUILD, 'vb_affine_3.npy'))
    mag = np.isin(part, list(MAG_PARTS)); hnd = np.isin(part, list(HANDLE_PARTS)); body = ~(mag | hnd)
    surfs = X.split_surfaces('bren', corners(A[body], 1, M1))
    ms = X.split_surfaces('brenclip', corners(A[mag], 1, M1)); assert len(ms) == 1
    surfs.append(('brenclip',) + tuple(ms[0][1:]))
    hs = X.split_surfaces('brenchg', corners(A[hnd], 3, M3)); assert len(hs) == 1
    surfs.append(('brenchg',) + tuple(hs[0][1:]))
    od = os.path.join(OUT, 'models', 'weapons', 'coop_bren'); os.makedirs(od, exist_ok=True)
    skd = X.build_skd('coop_bren', BONES, surfs)
    open(os.path.join(od, 'coop_bren.skd'), 'wb').write(skd)
    G = np.concatenate([L.to_gun(A[:, :, :3])]).reshape(-1, 3)
    row = BS.row()
    F, Rr = np.array(row['F']), np.array(row['R'])
    json.dump(row, open(os.path.join(L.BUILD, 'sight_bren2.json'), 'w'), indent=1)
    meta = dict(F=F.tolist(), R=Rr.tolist(), surfaces=[s[0] for s in surfs], gun_min=G.min(0).tolist(), gun_max=G.max(0).tolist(), S=L.S, T=L.T.tolist())
    json.dump(meta, open(os.path.join(L.BUILD, 'coop_bren.json'), 'w'), indent=1)
    np.savez(os.path.join(L.BUILD, 'gun_final.npz'), G=L.to_gun(A[:, :, :3]), uv=A[:, :, 6:8], part=part)   # previews (bren_sights.py view)
    print('skd %d bytes, %d surfaces, %d verts, %d tris; gun x %.2f..%.2f' % (len(skd), len(surfs), sum(len(s[2]) for s in surfs),
          sum(len(s[1]) for s in surfs), G[:, 0].min(), G[:, 0].max()))
    for s in surfs:
        print('  %-10s v %4d t %4d' % (s[0], len(s[2]), len(s[1])))


if __name__ == '__main__':
    main()

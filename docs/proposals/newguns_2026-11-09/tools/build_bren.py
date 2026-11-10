"""H:/hzm_work/newguns/build/bren/tris.npz (bl_extract.py, NG_ROTX=90) -> <out>/models/weapons/coop_bren/coop_bren.skd (+ .json)

Bones = the Vickers-Berthier's (origin, vickers, tag_eject, Rechamber, tag_barrel), same names and order, so the VB's view and
reload animations drive it. The gun rides `vickers`; the cocking handle (source part 37, right side) rides `Rechamber` (the VB's
handle bone, which its reloads stroke); the magazine is ONE surface `brenclip` (the tik hides it during the reloads).
Bone-local frames: solved from the shipped VB mesh against its idle pose (gun = local @ M[:3] + M[3]; vb_affine_<bone>.npy).
[QA 2026-11-09] the bipod is FOLDED forward under the barrel (the source has it deployed): each leg turns about its top.
    python build_bren.py [out_root]
"""
import os, sys, json
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
# [newguns 2026-11-09 c] SIGHTS FURTHER LEFT: the ghost ring (+ sight arm) and the front blade (+ bracket) move SIGHT_DY gun
# units left (gun frame +y = right, +z = down), eased to zero between SIGHT_Z0 and SIGHT_Z1 so the brackets stay on the receiver /
# barrel top. ADS showed the top magazine standing right above the aperture with the line only 1.24 u left of its centre.
SIGHT_DY = -0.70   # (ng12-16: the dark block at the eye was the source rear-sight housing on the ring line, fixed by the virtual rear row)
SIGHT_BOXES = [(-10.2, -8.3), (34.0, 36.6)]          # gun-frame x ranges: rear ring, front blade
SIGHT_Z0, SIGHT_Z1 = -3.6, -4.2                       # above the receiver / barrel top (up = -z)


def sight_shift(g):
    g = np.array(g, float)
    inx = np.zeros(len(g), bool)
    for x0, x1 in SIGHT_BOXES:
        inx |= (g[:, 0] > x0) & (g[:, 0] < x1)
    w = np.clip((SIGHT_Z0 - g[:, 2]) / (SIGHT_Z0 - SIGHT_Z1), 0.0, 1.0) * inx
    g[:, 1] += SIGHT_DY * w
    return g


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


def to_local(g, M):
    """gun frame -> bone-local (inverse of gun = local @ M[:3] + M[3])"""
    return (g - M[3]) @ np.linalg.inv(M[:3])


def corners(A, bone, M):
    out = []
    Minv = np.linalg.inv(M[:3])
    for tri in A:
        g = sight_shift(L.to_gun(tri[:, :3])); gn = L.nrm_gun(tri[:, 3:6])
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
    # [ADS] the source aperture disc (part 49) out, a ghost ring in (brenlib.RING_*), textured from the sight arm's steel
    from PIL import Image
    sheet = np.asarray(Image.open(os.path.join(L.BUILD, 'bren.png')).convert('L'), float)
    cand = A[part == 0][:, :, 6:8].reshape(-1, 2)          # a mid-grey receiver-steel texel (the arm's mean UV fell on wood)
    lum = sheet[((1 - cand[:, 1]) * (sheet.shape[0] - 1)).astype(int).clip(0, sheet.shape[0] - 1),
                (cand[:, 0] * (sheet.shape[1] - 1)).astype(int).clip(0, sheet.shape[1] - 1)]
    uv = cand[np.argsort(lum)[len(lum) * 3 // 4]]
    ring = L.ring_tris(uv)
    keep = part != 49
    A = np.concatenate([A[keep], ring]); part = np.concatenate([part[keep], np.full(len(ring), 49)])
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
    F, Rr = L.sight_row()
    F, Rr = F + np.array([0.0, SIGHT_DY, 0.0]), Rr + np.array([0.0, SIGHT_DY, 0.0])   # both points sit in the moved parts
    meta = dict(F=F.tolist(), R=Rr.tolist(), surfaces=[s[0] for s in surfs], gun_min=G.min(0).tolist(), gun_max=G.max(0).tolist(), S=L.S, T=L.T.tolist())
    json.dump(meta, open(os.path.join(L.BUILD, 'coop_bren.json'), 'w'), indent=1)
    print('skd %d bytes, %d surfaces, %d verts, %d tris; gun x %.2f..%.2f' % (len(skd), len(surfs), sum(len(s[2]) for s in surfs),
          sum(len(s[1]) for s in surfs), G[:, 0].min(), G[:, 0].max()))
    for s in surfs:
        print('  %-10s v %4d t %4d' % (s[0], len(s[2]), len(s[1])))


if __name__ == '__main__':
    main()

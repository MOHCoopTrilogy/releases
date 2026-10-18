"""no12u Mauser C96 (build/tris.npz from bl_extract.py) -> ship/models/weapons/coop_c96n/c96n.skd + bind clip.

    python build_mesh.py

Bones (all POSROT, identity bind at the gun origin; the clips move them):
    origin; tag_barrel, tag_eject, Box01, p38clip (the P38 skeleton the retail/our hand + torso rows know)
    coop_slide  the bolt (source bone `Slide`)      moves along x (rearward = -x)
    coop_tog    the hammer (`Hammer`)               turns about the lateral axis through its pin
    coop_trig   the trigger (`Trigger`)             turns about the lateral axis through its top
Root (frame, barrel, sights, grips, magazine well, safety) and Ring (lanyard ring) ride on `origin`.
Not in the game mesh: Stock, StockCup, Clip + rounds (the server's stripper-clip prop is used), FreshBullet, EjectBullet.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c96lib as L
import skx as X

BONES = [('origin', 'worldbone'), ('tag_barrel', 'origin'), ('tag_eject', 'origin'), ('Box01', 'origin'), ('p38clip', 'Box01'),
         ('coop_slide', 'origin'), ('coop_tog', 'origin'), ('coop_trig', 'origin')]
BI = {n: i for i, (n, _) in enumerate(BONES)}
PART_BONE = {'Root': 'origin', 'Ring': 'origin', 'Slide': 'coop_slide', 'Hammer': 'coop_tog', 'Trigger': 'coop_trig'}
PART_PREFIX = {'Root': 'c96f', 'Ring': 'c96r', 'Slide': 'c96b', 'Hammer': 'c96h', 'Trigger': 'c96t'}
NAME = 'c96n'
MDIR = os.path.join(L.STAGE, 'models', 'weapons', 'coop_c96n')

# pivots in BU (source frame): hammer pin, trigger top
HAM_PIV_BU = np.array([0.0, 0.4705, -0.0923])
TRIG_PIV_BU = np.array([0.0, 0.7941, -0.0457])
# tag points (BU): muzzle centre, ejection port (right side of the receiver, over the bolt front)
TAG_BARREL_BU = np.array([0.0, L.MUZ_Y, L.BORE_Z])
TAG_EJECT_BU = np.array([0.10, 0.95, 0.12])


def corners(A, part):
    out = []
    bi = BI[PART_BONE[part]]
    for tri in A:
        p = L.to_raw(tri[:, :3]); n = L.nrm_raw(tri[:, 3:6])
        uv = tri[:, 6:8].astype(float).copy(); uv[:, 1] = 1.0 - uv[:, 1]
        c = [(bi, p[k], n[k], uv[k]) for k in range(3)]
        fn = np.cross(p[1] - p[0], p[2] - p[0])
        if np.dot(fn, n.sum(0)) > 0:                 # retail winding: cross . n < 0
            c = [c[0], c[2], c[1]]
        out.append(c)
    out.sort(key=lambda c: (c[0][1][0] + c[1][1][0] + c[2][1][0]))
    return out


def main():
    d = np.load(os.path.join(L.BUILD, 'tris.npz'))
    A, part = d['corners'], d['part']
    surfs = []
    for pn in ('Root', 'Slide', 'Hammer', 'Trigger', 'Ring'):
        cs = corners(A[part == pn], pn)
        surfs += X.split_surfaces(PART_PREFIX[pn], cs)
    # unique surface names: split_surfaces numbers per call, the prefixes differ
    os.makedirs(MDIR, exist_ok=True)
    skd = X.build_skd('P38', BONES, surfs)        # internal name kept as the mod's guns carry it
    open(os.path.join(MDIR, 'c96n.skd'), 'wb').write(skd)
    pts = np.array([np.asarray(off) for s in surfs for (_n, _uv, _b, off) in s[2]])
    bmin, bmax, rad = pts.min(0), pts.max(0), float(np.linalg.norm(pts, axis=1).max())
    meta = dict(surfaces=[s[0] for s in surfs], bmin=bmin.tolist(), bmax=bmax.tolist(), radius=rad,
                ham_piv=L.to_raw(HAM_PIV_BU).tolist(), trig_piv=L.to_raw(TRIG_PIV_BU).tolist(),
                tag_barrel=L.to_raw(TAG_BARREL_BU).tolist(), tag_eject=L.to_raw(TAG_EJECT_BU).tolist(), pitch=L.PITCH_DEG)
    json.dump(meta, open(os.path.join(L.BUILD, 'mesh.json'), 'w'), indent=1)
    nt = sum(len(s[1]) for s in surfs); nv = sum(len(s[2]) for s in surfs)
    print('skd %d bytes, %d surfaces, %d verts, %d tris' % (len(skd), len(surfs), nv, nt))
    for s in surfs:
        print('  ', s[0], len(s[2]), len(s[1]))
    print('bounds raw', np.round(bmin, 2), np.round(bmax, 2), 'radius', round(rad, 1))
    print('hammer pivot raw', np.round(meta['ham_piv'], 2), 'trigger pivot', np.round(meta['trig_piv'], 2))


if __name__ == '__main__':
    main()

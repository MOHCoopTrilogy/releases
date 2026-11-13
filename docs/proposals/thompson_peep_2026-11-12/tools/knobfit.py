"""knobfit.py - lower the Thompson actuator knob (its own surface) toward the receiver top, in the SKD.

The M1928-pattern meshes carry the cocking knob as a separate surface on its own bone (Thompson50 / coop_tommy28:
`Skin5`; coop_tommy1928d: `Skin3k`). Every vertex ABOVE the receiver-top plane is pulled toward it: gun-space height h
above the plane becomes h * scale (gun up = -z). Vertex order, UVs, weights and every other surface stay byte-identical
(only the offset floats of that surface's vertices change), so the knob's own animation still drives it.

    python knobfit.py <tik> <surface> <in.skd> <out.skd> [--drop 0.25 --neck 0.4] [--scale 1] [--plane z]
"""
import sys, struct, argparse
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
import gungeo, skdlib  # noqa: E402


def lower(data, tik, surf, scale=1.0, plane=None, drop=0.0, neck=0.4):
    m = skdlib.read_skd(data)
    ss = [s for s in m.surfaces if s.name == surf][0]
    g = gungeo.load_gun(tik)
    gs = [s for s in g['surfs'] if s['name'] == surf][0]
    P = np.asarray(gs['P'], float)
    for v in ss.verts:
        assert len(v[2]) == 1 and not v[3], 'knob vertex is not single-bone'
    O = np.array([v[2][0][2] for v in ss.verts], float)
    A = np.c_[O, np.ones(len(O))]
    sol, *_ = np.linalg.lstsq(A, P, rcond=None)
    assert np.abs(A @ sol - P).max() < 1e-3, 'vfs mesh != input mesh (or more than one bone)'
    L, b = sol[:3], sol[3]
    Li = np.linalg.inv(L)
    if plane is None:
        plane = P[:, 2].max()                    # the knob's own base (lowest point, z up = -z)
    Q = P.copy()
    up = Q[:, 2] < plane
    Q[up, 2] = plane + (Q[up, 2] - plane) * scale
    if drop:
        # shorten the STEM, keep the knurled cap: the cap (height >= neck above the base) moves down by `drop`, the
        # stem below it is compressed (h' = h - drop * min(1, h / neck))
        h = plane - Q[:, 2]
        Q[:, 2] += drop * np.clip(h / neck, 0.0, 1.0)
    O2 = (Q - b) @ Li
    out = bytearray(data)
    voff = ss.raw_off + struct.unpack_from('<8i', data, ss.raw_off + 68)[4]
    for i, v in enumerate(ss.verts):
        nw, nm = struct.unpack_from('<2i', data, voff + 20)
        assert nw == 1 and nm == 0
        struct.pack_into('<3f', out, voff + 28 + 8, *O2[i])
        voff += 28 + 20
    out = bytes(out)
    chk = skdlib.read_skd(out)
    for so, sn in zip(m.surfaces, chk.surfaces):
        if so.name != surf:
            assert so.vert_bytes == sn.vert_bytes
    return out, dict(surface=surf, scale=scale, drop=drop, neck=neck, plane=round(float(plane), 3), top_before=round(float(P[:, 2].min()), 3),
                     top_after=round(float(Q[:, 2].min()), 3))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('tik'); ap.add_argument('surf'); ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--scale', type=float, default=1.0); ap.add_argument('--plane', type=float, default=None)
    ap.add_argument('--drop', type=float, default=0.0); ap.add_argument('--neck', type=float, default=0.4)
    a = ap.parse_args()
    out, info = lower(open(a.src, 'rb').read(), a.tik, a.surf, a.scale, a.plane, a.drop, a.neck)
    open(a.dst, 'wb').write(out)
    print(a.dst, info)

"""lyman.py - model a raised Lyman rear-sight leaf with a round aperture on the 1928 Tommy (coop_tommy1928d).

Why (user decision 2026-11-13, "make it based on real life"): on the real M1928 the Lyman rear sight is mounted high
enough that the shooter sees the front blade OVER the actuator knob. On coop_tommy1928d the only rear reference was the
pair of protective ears (tops 1.18 in above the bore); the actual leaf base sits lower still, and the knob cap - already
sitting on the receiver - hid all but ~3 px of the blade. So a raised leaf is added standing on the leaf base, with its
aperture centred where the eye line clears the knob and shows the whole blade; the engine's sight row (cg_adssights.h
`thompsonsmg_tommy1928d` R) is moved to that aperture centre.

The leaf is APPENDED to surface `Skin6` (the sight base's surface, bone 1 'tommy gun new'): its vertices after the
existing ones (collapse index = the surface minimum, collapse onto vertex 0, like add_part.py), its triangles after the
existing ones; existing bytes untouched. Geometry: a convex plate (rectangle with chamfered top corners), both faces
triangulated around a round aperture, the aperture bore and the plate's outer edge walls. UVs: every vertex takes the
UV centroid of the Skin6 triangle nearest the leaf base (flat dark steel of the sight base itself).

    python lyman.py <in.skd> <out.skd> [--zc -5.60] [--dia 0.20]
"""
import sys, struct, argparse
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
import gungeo, skdlib  # noqa: E402

TIK = "models/weapons/thompsonsmg_tommy1928d.tik"
SURF = "Skin6"
X0, X1 = -6.715, -6.665          # leaf thickness 0.05 u, centred on the leaf base (x -6.81..-6.57)
YC = -0.7918                     # the front blade's y (cg_adssights.h F)
HALFW = 0.19                     # leaf half width (inside the ears: y -1.37..-0.18)
ZBASE = -5.010                   # 0.02 u into the leaf base (its top z -5.03)


def build(data, zc=-5.60, dia=0.20, n=20):
    m = skdlib.read_skd(data)
    ss = [s for s in m.surfaces if s.name == SURF][0]
    g = gungeo.load_gun(TIK)
    gs = [s for s in g['surfs'] if s['name'] == SURF][0]
    P = np.asarray(gs['P'], float)
    single = [i for i, v in enumerate(ss.verts) if len(v[2]) == 1 and v[2][0][0] == 1 and not v[3]]
    O = np.array([ss.verts[i][2][0][2] for i in single], float)
    A = np.c_[O, np.ones(len(O))]
    sol, *_ = np.linalg.lstsq(A, P[single], rcond=None)
    assert np.abs(A @ sol - P[single]).max() < 1e-3, 'vfs mesh != input mesh'
    L, b = sol[:3], sol[3]
    Li = np.linalg.inv(L)
    tri = gs['tri']
    cen = P[tri].mean(1)
    k = int(np.argmin(np.linalg.norm(cen - np.array([-6.69, YC, -5.03]), axis=1)))
    uv = gs['UV'][tri[k]].mean(0)
    r = dia / 2.0
    ztop = zc - r - 0.09                                     # 0.09 u of leaf above the aperture
    cham = 0.06
    poly = np.array([(YC - HALFW, ZBASE), (YC + HALFW, ZBASE), (YC + HALFW, ztop + cham), (YC + HALFW - cham, ztop),
                     (YC - HALFW + cham, ztop), (YC - HALFW, ztop + cham)])   # (y, z), up = -z
    c2 = np.array([YC, zc])
    assert ztop < zc - r and ZBASE > zc + r
    verts, tris = [], []

    def addv(pg, ng):
        no = ng @ Li
        verts.append(((np.asarray(pg) - b) @ Li, no / np.linalg.norm(no)))
        return len(verts) - 1

    def tri_oriented(a, b_, c, pa, pb, pc, nout):
        if np.cross(np.asarray(pb) - pa, np.asarray(pc) - pa) @ nout > 0:      # retail winding: normal . n < 0
            b_, c = c, b_
        tris.append((a, b_, c))
    th = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / n
    H = [c2 + r * np.array([np.cos(a), np.sin(a)]) for a in th]
    pang = np.arctan2(poly[:, 1] - c2[1], poly[:, 0] - c2[0])

    def ray_hit(a):
        d = np.array([np.cos(a), np.sin(a)]); best = None
        for k_ in range(len(poly)):
            p0, p1 = poly[k_], poly[(k_ + 1) % len(poly)]
            try:
                t_, s_ = np.linalg.solve(np.array([d, p0 - p1]).T, p0 - c2)
            except np.linalg.LinAlgError:
                continue
            if t_ > 0 and -1e-9 <= s_ <= 1 + 1e-9 and (best is None or t_ < best):
                best = t_
        return c2 + best * d
    Opts = [ray_hit(a) for a in th]
    rims = {}
    for x, nx in ((X0, -1.0), (X1, 1.0)):
        ng = np.array([nx, 0.0, 0.0])
        P3 = lambda yz, x=x: np.array([x, yz[0], yz[1]])
        hid = [addv(P3(h), ng) for h in H]
        oid = [addv(P3(o), ng) for o in Opts]
        cid = [addv(P3(pc), ng) for pc in poly]
        rims[x] = hid
        for k_ in range(n):
            a0, a1 = th[k_], th[(k_ + 1) % n] + (2 * np.pi if k_ == n - 1 else 0)
            mid = []
            for j in range(len(poly)):
                pa_ = pang[j]
                while pa_ < a0:
                    pa_ += 2 * np.pi
                if a0 < pa_ < a1:
                    mid.append((pa_, j))
            mid.sort()
            ring = [(oid[k_], Opts[k_])] + [(cid[j], poly[j]) for _, j in mid] + \
                   [(oid[(k_ + 1) % n], Opts[(k_ + 1) % n]), (hid[(k_ + 1) % n], H[(k_ + 1) % n])]
            for j in range(len(ring) - 1):
                tri_oriented(hid[k_], ring[j][0], ring[j + 1][0], P3(H[k_]), P3(ring[j][1]), P3(ring[j + 1][1]), ng)
    # aperture bore (normals inward) and outer edge walls (normals outward), own vertices for flat shading
    for loop, inward in ((H, True), (list(poly), False)):
        m_ = len(loop)
        for k_ in range(m_):
            p0, p1 = loop[k_], loop[(k_ + 1) % m_]
            mid2 = (p0 + p1) / 2
            nyz = (c2 - mid2) if inward else (mid2 - c2)
            if not inward:
                e = p1 - p0; nyz = np.array([e[1], -e[0]])
                if nyz @ (mid2 - c2) < 0:
                    nyz = -nyz
            ng = np.r_[0.0, nyz / np.linalg.norm(nyz)]
            q = [np.array([X0, *p0]), np.array([X0, *p1]), np.array([X1, *p1]), np.array([X1, *p0])]
            ids = [addv(p, ng) for p in q]
            for t in ((0, 1, 2), (0, 2, 3)):
                tri_oriented(ids[t[0]], ids[t[1]], ids[t[2]], q[t[0]], q[t[1]], q[t[2]], ng)
    # ---- append to the surface
    off = ss.raw_off
    ntri, nvert, static, oTri, oVerts, oColl, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
    assert [oTri, oVerts, oColl, oCI] == sorted([oTri, oVerts, oColl, oCI])
    ci = struct.unpack_from('<%di' % nvert, data, off + oCI)
    tb = bytearray(data[off + oTri: off + oVerts]); vb = bytearray(data[off + oVerts: off + oColl])
    cb = bytearray(data[off + oColl: off + oCI]); ib = bytearray(data[off + oCI: off + oEnd])
    for t in tris:
        tb += struct.pack('<3i', *(nvert + i for i in t))
    for o_, no in verts:
        vb += struct.pack('<3f2f2i', *no, float(uv[0]), float(uv[1]), 1, 0) + struct.pack('<if3f', 1, 1.0, *o_)
        cb += struct.pack('<i', 0); ib += struct.pack('<i', min(ci))
    head = bytearray(data[off: off + oTri])
    oV2 = oTri + len(tb); oC2 = oV2 + len(vb); oI2 = oC2 + len(cb); oE2 = oI2 + len(ib)
    struct.pack_into('<8i', head, 68, ntri + len(tris), nvert + len(verts), static, oTri, oV2, oC2, oE2, oI2)
    surf = bytes(head) + bytes(tb) + bytes(vb) + bytes(cb) + bytes(ib)
    out = bytearray(data[:off]) + surf + bytearray(data[off + oEnd:])
    grow = len(surf) - oEnd
    struct.pack_into('<5i', out, 72, m.numSurfaces, m.numBones, m.ofsBones, m.ofsSurfaces, m.ofsEnd + grow)
    tail = list(struct.unpack_from('<4i', out, 132))
    struct.pack_into('<4i', out, 132, *[(x + grow if x >= off + oEnd else x) if x else x for x in tail])
    out = bytes(out)
    chk = skdlib.read_skd(out)
    for so, sn in zip(m.surfaces, chk.surfaces):
        if so.name == SURF:
            assert sn.vert_bytes[:len(so.vert_bytes)] == so.vert_bytes and sn.tri_bytes[:len(so.tri_bytes)] == so.tri_bytes
        else:
            assert so.vert_bytes == sn.vert_bytes and so.tri_bytes == sn.tri_bytes
    R = (round((X0 + X1) / 2, 4), YC, zc)
    return out, dict(verts=len(verts), tris=len(tris), R=R, dia=dia, leaf_top=round(ztop, 3), uv=[round(float(x), 4) for x in uv])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--zc', type=float, default=-5.60); ap.add_argument('--dia', type=float, default=0.20)
    a = ap.parse_args()
    raw = open(a.src, 'rb').read()
    out, info = build(raw, a.zc, a.dia)
    open(a.dst, 'wb').write(out)
    print(a.dst, info)

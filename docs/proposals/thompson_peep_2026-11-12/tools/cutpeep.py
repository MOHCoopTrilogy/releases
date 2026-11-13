"""cutpeep.py - cut a real round peep hole through the Thompson M1/M1A1 rear-sight plate (the `site` surface).

Why: the retail ThompsonSMG.skd draws its rear peep only as an ALPHA hole in the texture `thompsite` (alphaFunc GE128).
Every texture that wins in the shipped pak set has lost that alpha: the HD weapons pack's thompsite.dds
(zzzzzzzzzz_coop_hd_wpn_1low.pk3) is DXT1 with no alpha, and the 13 `fs2` finishes map the plate to .jpg. So in game the
plate is solid and the front post is invisible when aiming (0 % of the post visible, offline and in engine).
A hole in the MESH works for every finish and every texture, whatever its alpha.

What changes, in the `site` surface only (every other surface byte-identical):
  * the two plate faces (front x ~ -6.645, rear x ~ -6.762, each a 6-vertex convex hexagon) are re-triangulated around
    a round hole of N segments, centred on the sight row's R (cg_adssights.h `thompson`: y -0.7969, z -5.5601 = the retail alpha hole);
  * a tube of N quads joins the two hole rims (the bore of the aperture, 0.12 u deep = the plate's thickness);
  * the 12 retail vertices keep their index, bytes and collapse data; the new vertices are APPENDED with collapse index
    = the surface's minimum (30) -> the plate drops out at exactly the LOD where the retail plate already did (its first
    triangle uses vertex 10, ci 31; the renderer stops at the first degenerate triangle);
  * positions / UVs / normals of new face vertices = the face's own affine map fitted on its 6 retail vertices (UVs of
    the painted ring continue exactly); tube vertices take the rim UV and an inward radial normal.
  * winding = the retail face's own winding sense (some finish shaders may cull).
Idempotent: a `site` surface that already has more than 12 vertices is left alone.

    python cutpeep.py <tik> <in.skd> <out.skd> [--dia 0.22] [--n 20]
"""
import sys, os, struct, argparse
import numpy as np
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
import gungeo, skdlib  # noqa: E402

R_THOMPSON = (-6.7622, -0.7969, -5.5601)       # cg_adssights.h row `thompson` (= `thompson_27a1`): the retail alpha hole
# In engine (live cgame, cg_adsSightSolve 2 + cg_adsSightDebug 1, 2026-11-12/13 runs `dbg` + `after2`, standing,
# 1600x900, wfov 82) the settled rig keeps the post tip within 2.7 px of screen centre, but the idle breathing sway
# swings the rear aperture R against it by -12..+12 px (mean +1.5 px over 9 samples): R = the right centre, and the hole
# has to be wide enough that the tip stays inside through that sway (1 px = 0.01 u at the plate) -> DIA 0.22 u.
# (A first cut moved the hole up 0.065 u from ONE sample at +9.6 px; the second run showed that was a sway phase.)
UP_SHIFT = 0.0


def cut(data, tik, dia=0.22, n=20, centre=None):
    if centre is None:
        centre = (R_THOMPSON[0], R_THOMPSON[1], R_THOMPSON[2] - UP_SHIFT)
    m = skdlib.read_skd(data)
    si = [i for i, s in enumerate(m.surfaces) if s.name == 'site']
    assert len(si) == 1, 'no site surface'
    ss = m.surfaces[si[0]]
    if ss.numVerts != 12:
        return data, dict(skipped='site has %d verts (already cut?)' % ss.numVerts)
    off = ss.raw_off
    ntri, nvert, static, oTri, oVerts, oColl, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
    assert [oTri, oVerts, oColl, oCI, oEnd] == sorted([oTri, oVerts, oColl, oCI, oEnd])
    tris = np.array(struct.unpack('<%di' % (ntri * 3), ss.tri_bytes)).reshape(-1, 3)
    coll = list(struct.unpack_from('<%di' % nvert, data, off + oColl))
    ci = list(struct.unpack_from('<%di' % nvert, data, off + oCI))
    # gun-space positions of the retail vertices (gungeo frame = the sight row's frame) and the bone-offset frame
    g = gungeo.load_gun(tik)
    gs = [s for s in g['surfs'] if s['name'] == 'site'][0]
    P = np.asarray(gs['P'], float)
    for v in ss.verts:
        assert len(v[2]) == 1 and abs(v[2][0][1] - 1.0) < 1e-6 and not v[3], 'site vertex is not single-bone'
    bone = ss.verts[0][2][0][0]
    assert all(v[2][0][0] == bone for v in ss.verts)
    O = np.array([v[2][0][2] for v in ss.verts], float)
    A = np.c_[O, np.ones(len(O))]
    sol, *_ = np.linalg.lstsq(A, P, rcond=None)
    assert np.abs(A @ sol - P).max() < 1e-4, 'the vfs mesh is not the input mesh'
    L, b = sol[:3], sol[3]
    Li = np.linalg.inv(L)
    UV = np.array([v[1] for v in ss.verts], float)
    NR = np.array([v[0] for v in ss.verts], float)
    # the two faces: split the retail vertices by gun x
    xm = P[:, 0].mean()
    faces = {'front': [i for i in range(12) if P[i, 0] > xm], 'rear': [i for i in range(12) if P[i, 0] <= xm]}
    assert all(len(v) == 6 for v in faces.values()), faces
    c2 = np.array(centre[1:], float)
    r = dia / 2.0
    newv = []          # (offset xyz, normal, uv)
    newt = []

    def addv(o, nrm, uv):
        newv.append((np.asarray(o, float), np.asarray(nrm, float), np.asarray(uv, float)))
        return 12 + len(newv) - 1

    rims = {}
    for fname, idx in faces.items():
        idx = np.array(idx)
        YZ = P[idx][:, 1:]
        # affine maps (y, z) -> gun x, uv, normal fitted on the face's 6 vertices
        Af = np.c_[YZ, np.ones(len(idx))]
        mx = np.linalg.lstsq(Af, P[idx][:, 0], rcond=None)[0]
        muv = np.linalg.lstsq(Af, UV[idx], rcond=None)[0]
        mn = np.linalg.lstsq(Af, NR[idx], rcond=None)[0]
        assert np.abs(Af @ muv - UV[idx]).max() < 2e-3, 'face UV is not affine'

        def attrs(yz, mx=mx, muv=muv, mn=mn, uvw=0.0):   # bound per face (a late-binding closure put both rims on the rear face)
            q = np.r_[yz, 1.0]
            # uvw: the painted ring of the texture sits on the retail hole; the rim samples it shifted onto the new
            # hole (1), the plate outline keeps its own UVs (0), the fan in between interpolates (no seam)
            qt = np.r_[yz + uvw * (np.asarray(R_THOMPSON[1:]) - c2), 1.0]
            pg = np.array([q @ mx, yz[0], yz[1]])
            nn = q @ mn
            nn = nn / (np.linalg.norm(nn) + 1e-12)
            return (pg - b) @ Li, nn, qt @ muv, pg
        # outer convex polygon in angular order about the hole centre
        ang = np.arctan2(YZ[:, 1] - c2[1], YZ[:, 0] - c2[0])
        order = np.argsort(ang)
        poly = YZ[order]
        # the hole must sit inside the face with margin
        for k in range(len(poly)):
            p0, p1 = poly[k], poly[(k + 1) % len(poly)]
            e = p1 - p0
            nrm2 = np.array([e[1], -e[0]]) / np.linalg.norm(e)
            dist = abs((c2 - p0) @ nrm2)
            assert dist > r + 0.02, 'hole too close to the plate edge (%.3f)' % dist
        # winding sense of the retail face triangles (gun space, about +x)
        ft = [t for t in tris if all(i in idx for i in t)]
        sgn = np.sign(np.mean([np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])[0] for t in ft]))
        th = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / n
        H = [c2 + r * np.array([np.cos(a), np.sin(a)]) for a in th]

        def ray_hit(a):
            d = np.array([np.cos(a), np.sin(a)])
            best = None
            for k in range(len(poly)):
                p0, p1 = poly[k], poly[(k + 1) % len(poly)]
                M = np.array([d, p0 - p1]).T
                try:
                    t_, s_ = np.linalg.solve(M, p0 - c2)
                except np.linalg.LinAlgError:
                    continue
                if t_ > 0 and -1e-9 <= s_ <= 1 + 1e-9 and (best is None or t_ < best):
                    best = t_
            return c2 + best * d
        Opts = [ray_hit(a) for a in th]
        hid = [addv(*attrs(h, uvw=1.0)[:3]) for h in H]
        oid = [addv(*attrs(o)[:3]) for o in Opts]
        cid = {}
        for k, pc in enumerate(poly):
            cid[k] = addv(*attrs(pc)[:3])
        pang = np.arctan2(poly[:, 1] - c2[1], poly[:, 0] - c2[0])

        def tri2(a_, b_, c_, pa, pb, pc):
            # (pa, pb, pc) in (y, z): orient so that the gun-space x component of the normal has the retail sign
            cr = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])   # = n_x of (0, y, z) points
            if abs(cr) < 1e-12:
                return
            if np.sign(cr) != sgn:
                b_, c_ = c_, b_
            newt.append((a_, b_, c_))
        for k in range(n):
            a0, a1 = th[k], th[(k + 1) % n] + (2 * np.pi if k == n - 1 else 0)
            mid = []
            for j in range(len(poly)):
                pa_ = pang[j]
                while pa_ < a0:
                    pa_ += 2 * np.pi
                if a0 < pa_ < a1:
                    mid.append((pa_, j))
            mid.sort()
            ring = [(oid[k], Opts[k])] + [(cid[j], poly[j]) for _, j in mid] + [(oid[(k + 1) % n], Opts[(k + 1) % n]), (hid[(k + 1) % n], H[(k + 1) % n])]
            for j in range(len(ring) - 1):
                tri2(hid[k], ring[j][0], ring[j + 1][0], H[k], ring[j][1], ring[j + 1][1])
        rims[fname] = dict(H=H, attrs=attrs, sgn=sgn)
    # the bore: quads between the two rims, inward normals, rim UVs
    fr, re_ = rims['front'], rims['rear']
    tube_f, tube_r = [], []
    for k in range(n):
        for rim, lst in ((fr, tube_f), (re_, tube_r)):
            o_, _, uv_, pg = rim['attrs'](rim['H'][k], uvw=1.0)
            ng = np.r_[0.0, c2 - rim['H'][k]]
            ng /= np.linalg.norm(ng)
            no = ng @ Li
            no /= np.linalg.norm(no)
            lst.append((addv(o_, no, uv_), pg))
    for k in range(n):
        k1 = (k + 1) % n
        q = [tube_f[k], tube_f[k1], tube_r[k1], tube_r[k]]
        for t in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
            pa, pb, pc = (x[1] for x in t)
            nrm3 = np.cross(pb - pa, pc - pa)
            inward = np.r_[0.0, c2 - (pa[1:] + pb[1:] + pc[1:]) / 3]
            # retail-like sense: the visible side's normal follows the same sign rule as the faces' sgn about +x
            if np.sign(nrm3 @ inward) != fr['sgn']:
                t = (t[0], t[2], t[1])
            newt.append(tuple(x[0] for x in t))
    # ---- write the surface back
    vb = bytearray(ss.vert_bytes)
    for o_, nn, uv_ in newv:
        vb += struct.pack('<3f2f2i', *nn, float(uv_[0]), float(uv_[1]), 1, 0)
        vb += struct.pack('<if3f', bone, 1.0, *o_)
    tb = bytearray()
    for t in newt:
        tb += struct.pack('<3i', *t)
    nv2 = 12 + len(newv)
    cmin = min(ci)
    coll2 = coll + [0] * len(newv)
    ci2 = ci + [cmin] * len(newv)
    # retail section order is tri, verts, coll, ci
    head = bytearray(data[off: off + oTri])
    oTri2 = oTri; oVerts2 = oTri2 + len(tb); oColl2 = oVerts2 + len(vb); oCI2 = oColl2 + 4 * nv2; oEnd2 = oCI2 + 4 * nv2
    struct.pack_into('<8i', head, 68, len(newt), nv2, static, oTri2, oVerts2, oColl2, oEnd2, oCI2)
    surf = bytes(head) + bytes(tb) + bytes(vb) + struct.pack('<%di' % nv2, *coll2) + struct.pack('<%di' % nv2, *ci2)
    out = bytearray(data[:off]) + surf + bytearray(data[off + oEnd:])
    grow = len(surf) - oEnd
    end = m.ofsEnd + grow
    struct.pack_into('<5i', out, 72, m.numSurfaces, m.numBones, m.ofsBones, m.ofsSurfaces, end)
    tail = list(struct.unpack_from('<4i', out, 132))
    struct.pack_into('<4i', out, 132, *[(x + grow if x >= off + oEnd else x) if x else x for x in tail])
    out = bytes(out)
    chk = skdlib.read_skd(out)
    for so, sn in zip(m.surfaces, chk.surfaces):
        if so.name == 'site':
            assert sn.vert_bytes[:len(so.vert_bytes)] == so.vert_bytes and sn.numVerts == nv2
        else:
            assert sn.vert_bytes == so.vert_bytes and sn.tri_bytes == so.tri_bytes, so.name
    return out, dict(verts_added=len(newv), tris=len(newt), dia=dia, n=n, grow=grow)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('tik'); ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--dia', type=float, default=0.22); ap.add_argument('--n', type=int, default=20)
    a = ap.parse_args()
    out, info = cut(open(a.src, 'rb').read(), a.tik, a.dia, a.n)
    open(a.dst, 'wb').write(out)
    print(a.dst, info)

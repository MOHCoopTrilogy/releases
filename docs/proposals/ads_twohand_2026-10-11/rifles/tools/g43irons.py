"""Iron-sight G43 (user 2026-10-12): a STAGED copy of models/weapons/g43/g43.skd with the scope, its two turrets, two
rings, the mount and the lens taken out -> assets/models/weapons/g43/coop_g43_irons.skd. The scoped G43 mesh is not
touched (new file name, same model directory, so every g43 gun clip still resolves).

What is removed is chosen by CONNECTED COMPONENT (shared vertex position) of the rest mesh, matched by triangle count
and bounding box (gun frame as gungeo loads it: x forward, y right, z down, tik-scaled u):
    surface g43 (the 559-tri one): 180 tris scope tube, 58 mount, 22 + 16 turrets, 12 + 12 rings
    surface svt_lens: the whole surface (8 tris) - the surface block is dropped from the file
Only TRIANGLES are dropped; the vertices, their order, UVs, weights and the LOD collapse maps stay byte-identical
(a finish variant's re-texture and the LOD chain keep working; the orphaned vertices are never indexed).

    python g43irons.py [--dump] [--out <skd>]      --dump: print the vertices of the sight pieces (for the sight row)
"""
import sys, os, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import staged
import boltnear as BN
gungeo, vfs = BN.gungeo, BN.vfs
SRC_TIK = 'models/weapons/g43.tik'
SRC_SKD = 'models/weapons/g43/g43.skd'
OUT = staged.path('models/weapons/g43/coop_g43_irons.skd')
# (tris, xmin, xmax, zmin, zmax) of the components to drop from the big g43 surface
DROP = [(180, -1.1, 6.8, -7.1, -5.1), (58, 1.0, 4.7, -6.2, -3.6), (22, 2.3, 3.3, -7.1, -6.7), (16, 2.3, 3.3, -6.8, -5.9),
        (12, -0.3, 1.1, -6.2, -5.5), (12, 4.5, 5.9, -6.2, -5.5)]
DROP_SURF = ['svt_lens']


def comps(P, tri):
    key = {}
    vid = np.array([key.setdefault(tuple(np.round(p, 3)), len(key)) for p in P])
    par = list(range(len(key)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for a, b, c in vid[tri]:
        ra = find(a); par[find(b)] = ra; par[find(c)] = ra
    out = {}
    for ti, (a, b, c) in enumerate(tri):
        out.setdefault(find(vid[a]), []).append(ti)
    return list(out.values())


YC = -1.1565                      # the front post's centre line (y), the notch is cut on it
PLATE = dict(x0=11.965, x1=12.204, y0=-1.809, y1=-0.458, zb=-4.78, zt=-5.267)
NOTCH = dict(half=0.10, foot=0.03, depth=0.17)     # V notch: 0.20 u wide at the top, 0.06 u flat foot, 0.17 u deep


def plate_tris(s):
    """the rear sight's notch plate: 12 tris, x 11.965..12.204 (a solid block in the retail mesh - no notch)"""
    hit = []
    for tl in comps(s['P'], s['tri']):
        pts = s['P'][np.unique(s['tri'][tl])]
        if len(tl) == 12 and abs(pts[:, 0].min() - PLATE['x0']) < 0.01 and abs(pts[:, 0].max() - PLATE['x1']) < 0.01:
            hit.append(tl)
    assert len(hit) == 1, len(hit)
    return hit[0]


def notch_mesh():
    """the plate again, with a V notch on the post's line: convex pieces in (y, z) extruded along x, flat normals.
    returns (verts [(P, n)], tris) in the gun frame"""
    p, n = PLATE, NOTCH
    zt, zb, zn = p['zt'], p['zb'], p['zt'] + n['depth']
    yl, yr = YC - n['half'], YC + n['half']
    fl, fr = YC - n['foot'], YC + n['foot']
    pieces = [[(p['y0'], zb), (p['y0'], zt), (yl, zt), (fl, zn), (fl, zb)],          # left shoulder
              [(fl, zb), (fl, zn), (fr, zn), (fr, zb)],                               # under the notch
              [(fr, zb), (fr, zn), (yr, zt), (p['y1'], zt), (p['y1'], zb)]]           # right shoulder
    verts, tris = [], []

    def face(pts, nrm):
        base = len(verts)
        for q in pts:
            verts.append((np.array(q, float), np.array(nrm, float)))
        for i in range(1, len(pts) - 1):
            t = (base, base + i, base + i + 1)
            pa, pb, pc = (verts[k][0] for k in t)
            if np.cross(pb - pa, pc - pa) @ np.array(nrm, float) > 0:       # retail winding: cross . n < 0
                t = (t[0], t[2], t[1])
            tris.append(t)
    for poly in pieces:
        face([(p['x0'], y, z) for y, z in poly], (-1, 0, 0))
        face([(p['x1'], y, z) for y, z in poly], (1, 0, 0))
        cy = sum(q[0] for q in poly) / len(poly); cz = sum(q[1] for q in poly) / len(poly)
        for i in range(len(poly)):
            (ya, za), (yb, zb2) = poly[i], poly[(i + 1) % len(poly)]
            if abs(ya - yb) < 1e-6 and abs(ya - fl) < 1e-6 or abs(ya - yb) < 1e-6 and abs(ya - fr) < 1e-6:
                continue                                                      # the seams between the pieces
            nn = np.array([0.0, -(zb2 - za), (yb - ya)]); nn /= np.linalg.norm(nn)
            if nn @ np.array([0.0, (ya + yb) / 2 - cy, (za + zb2) / 2 - cz]) < 0:
                nn = -nn
            face([(p['x0'], ya, za), (p['x1'], ya, za), (p['x1'], yb, zb2), (p['x0'], yb, zb2)], nn)
    return verts, tris


def rebuild(data, b, s, kill, notch):
    """the surface block without the `kill` triangles and (notch) with the notched plate appended.
    returns (block, bytes shorter)"""
    off = b['off']
    order = sorted([('tri', b['oT']), ('verts', b['oV']), ('coll', b['oC']), ('ci', b['oCI'])], key=lambda x: x[1])
    assert [o[0] for o in order] == ['tri', 'verts', 'coll', 'ci'], order
    nt, nv = b['nt'], b['nv']
    tri = bytearray(data[off + b['oT']: off + b['oV']]); ver = bytearray(data[off + b['oV']: off + b['oC']])
    col = bytearray(data[off + b['oC']: off + b['oCI']]); ci = bytearray(data[off + b['oCI']: off + b['oEnd']])
    assert len(tri) == nt * 12 and len(col) == nv * 4 and len(ci) == nv * 4
    tri_file = np.frombuffer(bytes(tri), dtype='<i4').reshape(-1, 3)
    assert np.array_equal(tri_file, np.asarray(s['tri'])), 'triangle order differs'
    keep = [i for i in range(nt) if i not in kill]
    tri = bytearray(tri_file[keep].astype('<i4').tobytes())
    ntri, nvert = len(keep), nv
    if notch:
        import skdlib
        m = skdlib.read_skd(data)
        sv = [x for x in m.surfaces if x.raw_off == off][0]
        pl = sorted(set(int(v) for t in plate_tris(s) for v in np.asarray(s['tri'])[t]))
        bone = sv.verts[pl[0]][2][0][0]
        assert all(len(sv.verts[v][2]) == 1 and sv.verts[v][2][0][0] == bone for v in pl)
        # gun frame <- bone offsets, fitted on every single-weight vertex of this bone in the surface
        idx = [i for i, v in enumerate(sv.verts) if len(v[2]) == 1 and v[2][0][0] == bone]
        O = np.array([sv.verts[i][2][0][2] for i in idx]); P = np.asarray(s['P'])[idx]
        A = np.hstack([O, np.ones((len(O), 1))])
        X, res, rk, _ = np.linalg.lstsq(A, P, rcond=None)
        err = np.abs(A @ X - P).max()
        assert err < 1e-3, err
        M, t = X[:3], X[3]
        Mi = np.linalg.inv(M)
        # flat metal tone: the uv of the plate's eye-side face
        # (NOT the mean uv of the plate's vertices: its faces sit on different islands of the sheet and their mean is a
        # black texel - run rb24 drew the notch plate pure black)
        T3 = np.asarray(s['tri'])[plate_tris(s)]
        Pp = np.asarray(s['P'])
        eye = [tr for tr in T3 if (np.cross(Pp[tr[1]] - Pp[tr[0]], Pp[tr[2]] - Pp[tr[0]]) / np.linalg.norm(np.cross(Pp[tr[1]] - Pp[tr[0]], Pp[tr[2]] - Pp[tr[0]])))[0] > 0.9]
        assert len(eye) == 2, len(eye)
        uv = np.asarray(s['UV'])[np.array(eye).ravel()].mean(axis=0)
        cidx = struct.unpack_from('<%di' % nv, ci)
        verts, tris = notch_mesh()
        for a, bb, c in tris:
            tri += struct.pack('<3i', nv + a, nv + bb, nv + c)
        for p, n in verts:
            o = (p - t) @ Mi
            nl = n @ M.T; nl = nl / np.linalg.norm(nl)          # rows of M are orthogonal x scale: n_bone = M n / |.|
            ver += struct.pack('<3f2f2i', float(nl[0]), float(nl[1]), float(nl[2]), float(uv[0]), float(uv[1]), 1, 0)
            ver += struct.pack('<if3f', bone, 1.0, float(o[0]), float(o[1]), float(o[2]))
            col += struct.pack('<i', 0)
            ci += struct.pack('<i', min(cidx))
        ntri += len(tris); nvert += len(verts)
        print('   notch plate: +%d verts +%d tris on bone %d, fit error %.5f u, uv %.3f %.3f' % (len(verts), len(tris), bone, err, uv[0], uv[1]))
    head = bytearray(data[off: off + b['oT']])
    oT = b['oT']; oV = oT + len(tri); oC = oV + len(ver); oCI = oC + len(col); oEnd = oCI + len(ci)
    ssp = struct.unpack_from('<i', data, off + 68 + 8)[0]
    struct.pack_into('<8i', head, 68, ntri, nvert, ssp, oT, oV, oC, oEnd, oCI)
    blk = head + tri + ver + col + ci
    print('surface %-9s %d -> %d tris, %d -> %d verts' % (b['name'], nt, ntri, nv, nvert))
    return blk, b['oEnd'] - len(blk)


def surf_blocks(data):
    numS, numB, ofsB, ofsS, ofsE = struct.unpack_from('<5i', data, 72)
    off, out = ofsS, []
    for i in range(numS):
        name = data[off + 4:off + 68].split(b'\0')[0].decode('latin-1')
        nt, nv, ssp, oT, oV, oC, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
        out.append(dict(off=off, name=name, nt=nt, nv=nv, oT=oT, oV=oV, oC=oC, oEnd=oEnd, oCI=oCI))
        off += oEnd
    return out, (numS, numB, ofsB, ofsS, ofsE)


def main():
    staged.off()
    g = gungeo.load_gun(SRC_TIK, 'idle', 0)
    data = vfs.read(SRC_SKD)
    blocks, (numS, numB, ofsB, ofsS, ofsE) = surf_blocks(data)
    print('skd %d bytes, version %d, surfaces %d, bones %d, ofsBones %d ofsSurfaces %d ofsEnd %d, header ints after lod %s'
          % (len(data), struct.unpack_from('<i', data, 4)[0], numS, numB, ofsB, ofsS, ofsE, struct.unpack_from('<4i', data, 132)))
    assert [b['name'].lower() for b in blocks] == [s['name'].lower() for s in g['surfs']], 'surface order differs'
    last_end = blocks[-1]['off'] + blocks[-1]['oEnd']
    print('surfaces end at %d (file %d)' % (last_end, len(data)))
    if '--dump' in sys.argv:
        for s in g['surfs']:
            for tl in comps(s['P'], s['tri']):
                pts = s['P'][np.unique(s['tri'][tl])]
                if pts[:, 0].min() > 11.0 and pts[:, 0].max() < 17.0 or pts[:, 0].min() > 40.0:
                    print(s['name'], len(tl), 'tris')
                    for p in pts[np.lexsort((pts[:, 1], pts[:, 2]))]:
                        print('   x %7.3f y %7.3f z %7.3f' % tuple(p))
        return
    out = bytearray()
    out += data[:ofsS]
    shift_total, nsurf = 0, 0
    for b, s in zip(blocks, g['surfs']):
        blk = bytearray(data[b['off']:b['off'] + b['oEnd']])
        if b['name'].lower() in DROP_SURF:
            print('surface %-9s dropped whole (%d tris)' % (b['name'], b['nt']))
            shift_total += len(blk)
            continue
        kill = set()
        if b['name'].lower() == 'g43' and b['nt'] == 559:
            cs = comps(s['P'], s['tri'])
            for cnt, x0, x1, z0, z1 in DROP:
                hit = []
                for tl in cs:
                    pts = s['P'][np.unique(s['tri'][tl])]
                    if len(tl) == cnt and abs(pts[:, 0].min() - x0) < 0.06 and abs(pts[:, 0].max() - x1) < 0.06 \
                            and abs(pts[:, 2].min() - z0) < 0.06 and abs(pts[:, 2].max() - z1) < 0.06:
                        hit.append(tl)
                assert len(hit) == 1, (cnt, x0, len(hit))
                kill |= set(hit[0])
            if '--nonotch' not in sys.argv:
                kill |= set(plate_tris(s))
        if kill:
            blk, cut = rebuild(data, b, s, kill, notch=('--nonotch' not in sys.argv))
            shift_total += cut
        out += blk
        nsurf += 1
    tail = data[last_end:]
    out += tail
    struct.pack_into('<5i', out, 72, nsurf, numB, ofsB, ofsS, ofsE - shift_total)
    # version-dependent offsets after lodIndex (boxes, morph targets): move the ones that pointed past the surfaces
    for pos in (136, 144):
        v = struct.unpack_from('<i', data, pos)[0]
        if v >= last_end and v <= len(data):
            struct.pack_into('<i', out, pos, v - shift_total)
            print('header offset at %d: %d -> %d' % (pos, v, v - shift_total))
    dst = OUT
    if '--out' in sys.argv:
        dst = sys.argv[sys.argv.index('--out') + 1]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bytes(out))
    print('wrote %s  %d bytes (was %d)' % (dst, len(out), len(data)))
    # read it back
    import skdlib
    m = skdlib.read_skd(bytes(out))
    print('read back: surfaces', [(s.name, s.numTriangles, s.numVerts) for s in m.surfaces], 'bones', len(m.bones))


if __name__ == '__main__':
    main()

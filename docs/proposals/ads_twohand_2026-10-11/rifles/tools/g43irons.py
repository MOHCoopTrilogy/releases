"""Iron-sight G43 (user 2026-10-12): a STAGED copy of models/weapons/g43/g43.skd with the scope, its two turrets, two
rings, the mount and the lens taken out -> assets/models/weapons/g43/coop_g43_irons.skd, and its two sights rebuilt as
a surface of their own (`coop_sight`, shader coop_g43_sight: dark steel on EVERY finish). The scoped G43 mesh is not
touched (new file name, same model directory, so every g43 gun clip still resolves).

Removed, chosen by CONNECTED COMPONENT (shared vertex position) of the rest mesh, matched by triangle count and bounding
box (gun frame as gungeo loads it: x forward, y right, z down, tik-scaled u):
    surface g43 (the 559-tri one): 180 tris scope tube, 58 mount, 22 + 16 turrets, 12 + 12 rings;
                                   12 tris rear notch plate (a SOLID block in the retail mesh - no notch),
                                   10 tris front post (0.085 u wide at the tip = 2 px at 1280x720)
    surface svt_lens: the whole surface (8 tris) - the surface block is dropped from the file
Only TRIANGLES are dropped there; the vertices, their order, UVs, weights and the LOD collapse maps stay byte-identical
(a finish variant's re-texture and the LOD chain keep working; the orphaned vertices are never indexed).

Added, surface `coop_sight` (coordinator's look-test notes 2026-10-12):
    the tangent sight's NOTCH PLATE: 0.95 u wide (the slider's width; the retail block was 1.35), chamfered top
        corners, a notch 0.30 u wide at the top / 0.20 u at the foot / 0.19 u deep on the front post's line, top 0.06 u
        higher than the retail block (daylight down to the slider behind it), a worn-steel edge band 0.04 u wide round
        the top and the notch on the eye's side
    the FRONT POST: 0.19 u wide at the tip, 0.22 u at the foot (was 0.085 / 0.155), same height and place, inside the
        untouched hood ring
+ assets/scripts/coop_g43_sight.shader, assets/textures/coop_wpn/g43_sight.tga (64x64: dark blued steel | worn edge).

    python g43irons.py [--out <skd>]
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
        (12, -0.3, 1.1, -6.2, -5.5), (12, 4.5, 5.9, -6.2, -5.5),
        (12, 11.965, 12.204, -5.267, -4.772),        # rear notch plate
        (10, 41.742, 42.158, -4.388, -4.155)]        # front post
DROP_SURF = ['svt_lens']
YC = -1.1565                      # the front post's centre line (y); the notch is cut on it
PLATE = dict(x0=11.965, x1=12.204, half=0.475, zb=-4.78, zt=-5.33, cham=0.12)
NOTCH = dict(top=0.15, foot=0.10, depth=0.19)
BAND = 0.04                       # worn edge band on the eye's side (u)
POST = dict(x0=41.742, x1=42.158, zb=-4.155, zt=-4.388, top=0.095, foot=0.11)
UV_DARK, UV_EDGE = 0.25, 0.75     # texture columns: dark steel | worn edge
SHADER = """// HZM coop [rifle lane 2026-10-12] iron-sight G43 (tools/g43irons.py): the tangent sight's notch plate and the front
// post, dark steel on every finish. rgbGen lightingSpherical is what every model shader of the mod uses (lightingDiffuse
// draws BLACK on a model in this engine, bug-3696); the unlit floor keeps the sights from going black in a dark room.
// rgbGen const takes three bare numbers - NO parentheses (bug-1913).
coop_g43_sight
{
	{
		map textures/coop_wpn/g43_sight.tga
		rgbGen const 0.30 0.30 0.30
	}
	{
		map textures/coop_wpn/g43_sight.tga
		blendFunc add
		rgbGen lightingSpherical
	}
}
"""


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


def surf_blocks(data):
    numS, numB, ofsB, ofsS, ofsE = struct.unpack_from('<5i', data, 72)
    off, out = ofsS, []
    for i in range(numS):
        name = data[off + 4:off + 68].split(b'\0')[0].decode('latin-1')
        nt, nv, ssp, oT, oV, oC, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
        out.append(dict(off=off, name=name, nt=nt, nv=nv, oT=oT, oV=oV, oC=oC, oEnd=oEnd, oCI=oCI))
        off += oEnd
    return out, (numS, numB, ofsB, ofsS, ofsE)


def without(data, b, s, kill):
    """the surface block without the `kill` triangles (vertices and collapse maps untouched)"""
    off = b['off']
    order = sorted([('tri', b['oT']), ('verts', b['oV']), ('coll', b['oC']), ('ci', b['oCI'])], key=lambda x: x[1])
    assert [o[0] for o in order] == ['tri', 'verts', 'coll', 'ci'], order
    nt = b['nt']
    tri = data[off + b['oT']: off + b['oV']]
    rest = data[off + b['oV']: off + b['oEnd']]
    assert len(tri) == nt * 12
    tri_file = np.frombuffer(tri, dtype='<i4').reshape(-1, 3)
    assert np.array_equal(tri_file, np.asarray(s['tri'])), 'triangle order differs'
    keep = [i for i in range(nt) if i not in kill]
    tri = tri_file[keep].astype('<i4').tobytes()
    cut = 12 * (nt - len(keep))
    head = bytearray(data[off: off + b['oT']])
    ssp = struct.unpack_from('<i', data, off + 68 + 8)[0]
    struct.pack_into('<8i', head, 68, len(keep), b['nv'], ssp, b['oT'], b['oV'] - cut, b['oC'] - cut, b['oEnd'] - cut, b['oCI'] - cut)
    print('surface %-9s %d -> %d tris' % (b['name'], nt, len(keep)))
    return bytes(head) + tri + rest, cut


class Mesh:
    """flat-shaded faces in the gun frame; verts (P, n, uv), tris wound like the retail meshes (cross(b-a, c-a) . n < 0)"""
    def __init__(self):
        self.v, self.t = [], []

    def face(self, pts, n, u, vs=None):
        n = np.asarray(n, float); n = n / np.linalg.norm(n)
        base = len(self.v)
        for k, q in enumerate(pts):
            self.v.append((np.asarray(q, float), n, (u, vs[k] if vs else 0.5)))
        for i in range(1, len(pts) - 1):
            t = (base, base + i, base + i + 1)
            pa, pb, pc = (self.v[k][0] for k in t)
            if np.linalg.norm(np.cross(pb - pa, pc - pa)) < 1e-9:
                continue
            if np.cross(pb - pa, pc - pa) @ n > 0:
                t = (t[0], t[2], t[1])
            self.t.append(t)

    def prism(self, poly, x0, x1, u, top_u=None):
        """a convex (y, z) polygon extruded along x; side faces that look UP (z negative) take top_u"""
        cy = sum(q[0] for q in poly) / len(poly); cz = sum(q[1] for q in poly) / len(poly)
        sg = 0.0
        for i in range(len(poly)):                                   # convex?
            a, b, c = poly[i], poly[(i + 1) % len(poly)], poly[(i + 2) % len(poly)]
            s = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            assert sg == 0.0 or s * sg >= -1e-9, ('not convex', poly)
            if abs(s) > 1e-9:
                sg = s
        vz = lambda z: min(0.95, max(0.05, 0.15 + 0.7 * (z - PLATE['zt']) / (PLATE['zb'] - PLATE['zt'])))
        self.face([(x0, y, z) for y, z in poly], (-1, 0, 0), u, [vz(z) for y, z in poly])
        self.face([(x1, y, z) for y, z in poly], (1, 0, 0), u, [vz(z) for y, z in poly])
        for i in range(len(poly)):
            (ya, za), (yb, zb) = poly[i], poly[(i + 1) % len(poly)]
            nn = np.array([0.0, -(zb - za), (yb - ya)])
            nn = nn / np.linalg.norm(nn)
            if nn @ np.array([0.0, (ya + yb) / 2 - cy, (za + zb) / 2 - cz]) < 0:
                nn = -nn
            uu = top_u if (top_u is not None and nn[2] < -0.2) else u
            self.face([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], nn, uu)


def sight_mesh():
    m = Mesh()
    p, n = PLATE, NOTCH
    W, c, zt, zb = p['half'], p['cham'], p['zt'], p['zb']
    zn = zt + n['depth']
    Y = lambda y: YC + y
    left = [(Y(-W), zb), (Y(-W), zt + c), (Y(-W + c), zt), (Y(-n['top']), zt), (Y(-n['foot']), zn), (Y(-n['foot']), zb)]
    mid = [(Y(-n['foot']), zb), (Y(-n['foot']), zn), (Y(n['foot']), zn), (Y(n['foot']), zb)]
    right = [(Y(n['foot']), zb), (Y(n['foot']), zn), (Y(n['top']), zt), (Y(W - c), zt), (Y(W), zt + c), (Y(W), zb)]
    for poly in (left, mid, right):
        m.prism(poly, p['x0'], p['x1'], UV_DARK, top_u=UV_EDGE)
    # the worn edge on the eye's side: a band inside the outline, from the left chamfer's foot round the notch to the right one
    line = [(Y(-W), zt + c), (Y(-W + c), zt), (Y(-n['top']), zt), (Y(-n['foot']), zn), (Y(n['foot']), zn), (Y(n['top']), zt), (Y(W - c), zt), (Y(W), zt + c)]
    nrm = []
    for i in range(len(line) - 1):
        d = np.array(line[i + 1]) - np.array(line[i]); nrm.append(np.array([-d[1], d[0]]) / np.linalg.norm(d))
    inset = []
    for i in range(len(line)):
        if i == 0:
            v = nrm[0]
        elif i == len(line) - 1:
            v = nrm[-1]
        else:
            v = (nrm[i - 1] + nrm[i]) / (1.0 + nrm[i - 1] @ nrm[i])
        inset.append(np.array(line[i]) + BAND * v)
    xe = p['x0'] - 0.012                                               # a hair nearer the eye than the dark face
    for i in range(len(line) - 1):
        q = [line[i], line[i + 1], tuple(inset[i + 1]), tuple(inset[i])]
        m.face([(xe, y, z) for y, z in q], (-1, 0, 0), UV_EDGE, [0.3, 0.3, 0.7, 0.7])
    # front post
    o = POST
    post = [(Y(-o['foot']), o['zb']), (Y(-o['top']), o['zt']), (Y(o['top']), o['zt']), (Y(o['foot']), o['zb'])]
    m.prism(post, o['x0'], o['x1'], UV_DARK)
    return m


def write_tga(path, a):
    a = np.asarray(a, np.uint8)
    h, w = a.shape[:2]
    hd = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, 24, 0x00)     # bottom-up rows: the engine ignores a top-down flag (run rb27 warning)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(hd + a[::-1, :, ::-1].tobytes())


def sight_tex(n=64):
    """u < 0.5: dark blued steel, a little lighter toward the top (v small), fine horizontal matting;
    u > 0.5: the worn edge"""
    rng = np.random.RandomState(11)
    y, x = np.mgrid[0:n, 0:n]
    v = (y + 0.5) / n
    dark = 50.0 - 16.0 * v + 5.0 * np.cos(2 * np.pi * v * 12) + 4.0 * rng.rand(n, n)
    edge = 150.0 - 20.0 * v + 10.0 * rng.rand(n, n)
    val = np.where(x < n // 2, dark, edge)
    return np.clip(np.stack([val * 0.97, val * 0.99, val * 1.05], -1), 0, 255)


def main():
    staged.off()
    g = gungeo.load_gun(SRC_TIK, 'idle', 0)
    data = vfs.read(SRC_SKD)
    blocks, (numS, numB, ofsB, ofsS, ofsE) = surf_blocks(data)
    assert [b['name'].lower() for b in blocks] == [s['name'].lower() for s in g['surfs']], 'surface order differs'
    last_end = blocks[-1]['off'] + blocks[-1]['oEnd']
    assert last_end == len(data) == ofsE
    out = bytearray(data[:ofsS])
    shift_total, nsurf, bone = 0, 0, None
    import skdlib
    m0 = skdlib.read_skd(data)
    for b, s, sv in zip(blocks, g['surfs'], m0.surfaces):
        if b['name'].lower() in DROP_SURF:
            print('surface %-9s dropped whole (%d tris)' % (b['name'], b['nt']))
            shift_total += b['oEnd']
            continue
        blk = data[b['off']:b['off'] + b['oEnd']]
        if b['name'].lower() == 'g43' and b['nt'] == 559:
            cs = comps(s['P'], s['tri'])
            kill = set()
            for cnt, x0, x1, z0, z1 in DROP:
                hit = []
                for tl in cs:
                    pts = s['P'][np.unique(s['tri'][tl])]
                    if len(tl) == cnt and abs(pts[:, 0].min() - x0) < 0.06 and abs(pts[:, 0].max() - x1) < 0.06 \
                            and abs(pts[:, 2].min() - z0) < 0.06 and abs(pts[:, 2].max() - z1) < 0.06:
                        hit.append(tl)
                assert len(hit) == 1, (cnt, x0, len(hit))
                kill |= set(hit[0])
                if x0 > 11:                                          # the two sights: which bone do they hang on?
                    vi = np.unique(s['tri'][hit[0]])
                    bs = {sv.verts[int(v)][2][0][0] for v in vi}
                    assert len(bs) == 1 and (bone is None or bone in bs), bs
                    bone = bs.pop()
            blk, cut = without(data, b, s, kill)
            shift_total += cut
        out += blk
        nsurf += 1
    struct.pack_into('<5i', out, 72, nsurf, numB, ofsB, ofsS, ofsE - shift_total)
    for pos in (136, 144):
        v = struct.unpack_from('<i', data, pos)[0]
        if v >= last_end and v <= len(data):
            struct.pack_into('<i', out, pos, v - shift_total)
    assert len(out) == ofsE - shift_total
    # the sights' own surface
    BOLT = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
    sys.path.insert(0, BOLT)
    _c = os.getcwd(); os.chdir(BOLT)
    import add_bead as AB
    os.chdir(_c)
    sm = sight_mesh()
    res = AB.add_surface(bytes(out), SRC_TIK, 'coop_sight', sm.v, sm.t, bone)
    dst = OUT
    if '--out' in sys.argv:
        dst = sys.argv[sys.argv.index('--out') + 1]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(res)
    m = skdlib.read_skd(res)
    print('coop_sight: %d verts, %d tris on bone %d (%s)' % (len(sm.v), len(sm.t), bone, m.bones[bone].name))
    print('wrote %s  %d bytes (was %d): surfaces %s' % (dst, len(res), len(data), [(s.name, s.numTriangles, s.numVerts) for s in m.surfaces]))
    if '--out' not in sys.argv:
        p = staged.path('scripts/coop_g43_sight.shader'); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', newline='\n').write(SHADER)
        write_tga(staged.path('textures/coop_wpn/g43_sight.tga'), sight_tex())
        print('wrote', p, 'and textures/coop_wpn/g43_sight.tga')
    print('sight row: F %s  R %s' % ([round((POST['x0'] + POST['x1']) / 2, 4), YC, POST['zt']], [round((PLATE['x0'] + PLATE['x1']) / 2, 4), YC, PLATE['zt']]))


if __name__ == '__main__':
    main()

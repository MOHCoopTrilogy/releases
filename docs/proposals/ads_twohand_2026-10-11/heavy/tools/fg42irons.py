"""Iron-sight FG 42 (user 2026-10-13: "we also need a version of the fg42 with ironsights too if possible"): a STAGED
copy of models/weapons/fg42/fg42.skd (DaRKaNGeL's re-rigged mesh) without the scope ->
assets/models/weapons/fg42/coop_fg42_irons.skd. The scoped mesh is not touched (new file name, same model directory, so
every fg42 gun clip still resolves). The recipe and the helpers are the rifle lane's (rifles/tools/g43irons.py).

What the retail mesh has (tools/fg42parts.py, gun frame x forward / y right / z down, tik-scaled u):
    surface fg42base: 76 tris scope tube, 96 tris turret block + ring + the arched mount, 26 tris the mount's foot on
                      the receiver, and the rifle (stock 98, receiver 95, handguard 80, grip 78, trigger group 58,
                      magazine housing 47); NO rear sight at all
    surface fg42lens: 8 tris, the rear lens
    surface fg42barrel: a front sight - a slab 0.29 u wide and 0.84 u tall on a foot, with a stud pointing BACK at the
                      eye that covers its lower two thirds - and barrel, brake, bipod, spike
Removed (triangles only; vertices, UVs, weights and the LOD collapse maps stay byte-identical): the three scope
components, the whole lens surface, the retail front sight slab (46 tris).
Added, surface `coop_sight` (shader coop_fg42_sight, dark steel on every finish) - the FG 42's FOLDING sights, raised:
    REAR, on the receiver's rear tube: a foot, a stalk, the range drum across it and an APERTURE RING on top
          (outer r 0.46 u, hole r 0.21 u, 0.22 u thick; a worn band round its rim on the eye's side)
    FRONT, on the retail foot near the muzzle: a hinge block and a tapered POST 0.38 u wide at the tip, a worn-bright band across its top
Sight line: post tip -> the aperture's centre.

    python fg42irons.py [--out <skd>]
"""
import sys, os, struct, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hv
RT = os.path.normpath(os.path.join(hv.LANE, '..', 'rifles', 'tools'))
sys.path.insert(0, RT)
import staged
import g43irons as G
gungeo, vfs = G.gungeo, G.vfs
SRC_TIK = 'models/weapons/FG42.tik'
SRC_SKD = 'models/weapons/fg42/fg42.skd'
OUT = hv.staged('models/weapons/fg42/coop_fg42_irons.skd')
# (surface, tris, xmin, xmax, zmin, zmax) of the components to drop
DROP = [('fg42base', 96, -3.6, 1.4, -8.1, -5.2), ('fg42base', 76, -4.1, 4.0, -7.9, -6.5), ('fg42base', 26, -4.1, 0.4, -5.2, -4.3),
        ('fg42barrel', 46, 25.4, 27.5, -5.4, -4.5)]
DROP_SURF = ['fg42lens']
YC = -0.855                         # the gun's centre plane (the retail front sight's)
E = lambda k, d: float(os.environ.get(k, d))
REAR = dict(x=E('FG_RX', -6.2), top=E('FG_RTOP', -4.02), zc=E('FG_RZ', -5.44), ro=E('FG_RO', 0.46), ri=E('FG_RI', 0.21), th=0.22, band=0.05)
# coordinator 2026-10-13 (look test hj23): the 0.26 u post (4 px at 1280) was nearly lost on dark foliage - 0.38 u at
# the tip (about 6 px) and a worn-bright band across its top on the eye's side
POST = dict(x0=26.62, x1=26.92, zb=-4.74, zt=E('FG_PZ', -5.50), top=0.19, foot=0.22, band=0.10)
UD, UE = G.UV_DARK, G.UV_EDGE
SHADER = G.SHADER.replace('coop_g43_sight', 'coop_fg42_sight').replace('g43_sight.tga', 'fg42_sight.tga').replace(
    '[rifle lane 2026-10-12] iron-sight G43 (tools/g43irons.py): the tangent sight\'s notch plate and the front',
    '[heavy lane 2026-10-13] iron-sight FG 42 (tools/fg42irons.py): the rear aperture sight and the front').replace(
    '// post, dark steel on every finish.', '// post (both raised), dark steel on every finish.')


def box(m, x0, x1, y0, y1, z0, z1, u=UD):
    m.prism([(y0, z0), (y1, z0), (y1, z1), (y0, z1)], x0, x1, u)


def sight_mesh():
    m = G.Mesh()
    r = REAR
    x0, x1 = r['x'] - r['th'] / 2, r['x'] + r['th'] / 2
    N = 14
    ang = [2 * math.pi * k / N for k in range(N + 1)]
    pt = lambda rad, a: (YC + rad * math.sin(a), r['zc'] - rad * math.cos(a))
    for k in range(N):
        a, b = ang[k], ang[k + 1]
        ro, rb, ri = r['ro'], r['ro'] - r['band'], r['ri']
        # eye side: a worn band round the rim, the rest dark; far side dark; outer and inner walls dark
        m.face([(x0 - 0.004, ) + pt(ro, a), (x0 - 0.004, ) + pt(ro, b), (x0 - 0.004, ) + pt(rb, b), (x0 - 0.004, ) + pt(rb, a)], (-1, 0, 0), UE, [0.3, 0.3, 0.7, 0.7])
        m.face([(x0, ) + pt(rb, a), (x0, ) + pt(rb, b), (x0, ) + pt(ri, b), (x0, ) + pt(ri, a)], (-1, 0, 0), UD)
        m.face([(x1, ) + pt(ro, a), (x1, ) + pt(ro, b), (x1, ) + pt(ri, b), (x1, ) + pt(ri, a)], (1, 0, 0), UD)
        mid = (a + b) / 2
        nout = (0.0, math.sin(mid), -math.cos(mid))
        m.face([(x0, ) + pt(ro, a), (x1, ) + pt(ro, a), (x1, ) + pt(ro, b), (x0, ) + pt(ro, b)], nout, UD)
        m.face([(x0, ) + pt(ri, a), (x1, ) + pt(ri, a), (x1, ) + pt(ri, b), (x0, ) + pt(ri, b)], tuple(-v for v in nout), UD)
    zring = r['zc'] + r['ro'] - 0.03                         # the ring's lowest point (z down)
    # the stalk (a flat leaf, as the real folding sight's), the range drum across it, the foot on the receiver
    box(m, r['x'] - 0.15, r['x'] + 0.15, YC - 0.17, YC + 0.17, zring, r['top'])
    zd = (zring + r['top']) / 2 + 0.02; rd = 0.24
    oct_ = [(r['x'] + rd * math.cos(2 * math.pi * k / 8 + math.pi / 8), zd + rd * math.sin(2 * math.pi * k / 8 + math.pi / 8)) for k in range(8)]
    for sgn, y in ((-1, YC - 0.42), (1, YC + 0.42)):
        m.face([(x, y, z) for x, z in oct_], (0, sgn, 0), UE if sgn < 0 else UD)
    for k in range(8):
        (xa, za), (xb, zb) = oct_[k], oct_[(k + 1) % 8]
        n = np.array([(xa + xb) / 2 - r['x'], 0.0, (za + zb) / 2 - zd])
        m.face([(xa, YC - 0.42, za), (xa, YC + 0.42, za), (xb, YC + 0.42, zb), (xb, YC - 0.42, zb)], n, UD)
    box(m, r['x'] - 0.42, r['x'] + 0.42, YC - 0.30, YC + 0.30, r['top'] - 0.10, r['top'] + 0.06)
    # front: a hinge block on the retail foot and the post
    o = POST
    box(m, 26.40, 27.30, YC - 0.19, YC + 0.19, -4.76, -4.50)
    m.prism([(YC - o['foot'], o['zb']), (YC - o['top'], o['zt']), (YC + o['top'], o['zt']), (YC + o['foot'], o['zb'])], o['x0'], o['x1'], UD, top_u=UE)
    zb_ = o['zt'] + o['band']; wb = o['top'] + (o['foot'] - o['top']) * o['band'] / (o['zb'] - o['zt'])
    xe = o['x0'] - 0.012                                   # a hair nearer the eye than the dark face
    m.face([(xe, YC - o['top'], o['zt']), (xe, YC + o['top'], o['zt']), (xe, YC + wb, zb_), (xe, YC - wb, zb_)], (-1, 0, 0), UE, [0.3, 0.3, 0.7, 0.7])
    return m


def main():
    staged.off()
    g = gungeo.load_gun(SRC_TIK, 'idle', 0)
    data = vfs.read(SRC_SKD)
    BOLT = hv.BOLT
    sys.path.insert(0, BOLT)
    _c = os.getcwd(); os.chdir(BOLT)
    import add_bead as AB
    import skdlib
    os.chdir(_c)
    blocks, (numS, numB, ofsB, ofsS, ofsE) = G.surf_blocks(data)
    if len(data) > ofsE:                     # this re-export carries 4 stray bytes after the last surface (SKMD v5)
        print('dropping %d trailing bytes after ofsEnd' % (len(data) - ofsE)); data = data[:ofsE]
    assert [b['name'].lower() for b in blocks] == [s['name'].lower() for s in g['surfs']], 'surface order differs'
    last_end = blocks[-1]['off'] + blocks[-1]['oEnd']
    assert last_end == len(data) == ofsE
    m0 = skdlib.read_skd(data)
    out = bytearray(data[:ofsS])
    shift_total, nsurf, bone = 0, 0, None
    for b, s, sv in zip(blocks, g['surfs'], m0.surfaces):
        nm = b['name'].lower()
        if nm in DROP_SURF:
            print('surface %-10s dropped whole (%d tris)' % (b['name'], b['nt']))
            shift_total += b['oEnd']
            continue
        blk = data[b['off']:b['off'] + b['oEnd']]
        want = [d for d in DROP if d[0] == nm]
        if want:
            cs = G.comps(s['P'], s['tri'])
            kill = set()
            for _, cnt, x0, x1, z0, z1 in want:
                hit = []
                for tl in cs:
                    pts = s['P'][np.unique(s['tri'][tl])]
                    if len(tl) == cnt and abs(pts[:, 0].min() - x0) < 0.08 and abs(pts[:, 0].max() - x1) < 0.08 \
                            and abs(pts[:, 2].min() - z0) < 0.08 and abs(pts[:, 2].max() - z1) < 0.08:
                        hit.append(tl)
                assert len(hit) == 1, (nm, cnt, x0, len(hit))
                kill |= set(hit[0])
                vi = np.unique(s['tri'][hit[0]])
                bs = {sv.verts[int(v)][2][0][0] for v in vi}
                assert len(bs) == 1 and (bone is None or bone in bs), ('bone', nm, cnt, bs, bone)
                bone = bs.pop()
            blk, cut = G.without(data, b, s, kill)
            shift_total += cut
        out += blk
        nsurf += 1
    struct.pack_into('<5i', out, 72, nsurf, numB, ofsB, ofsS, ofsE - shift_total)
    for pos in (136, 144):
        v = struct.unpack_from('<i', data, pos)[0]
        if v >= last_end and v <= len(data):
            struct.pack_into('<i', out, pos, v - shift_total)
    assert len(out) == ofsE - shift_total
    sm = sight_mesh()
    res = AB.add_surface(bytes(out), SRC_TIK, 'coop_sight', sm.v, sm.t, bone)
    dst = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else OUT
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(res)
    m = skdlib.read_skd(res)
    print('coop_sight: %d verts, %d tris on bone %d (%s)' % (len(sm.v), len(sm.t), bone, m.bones[bone].name))
    print('wrote %s  %d bytes (was %d): surfaces %s' % (dst, len(res), len(data), [(s.name, s.numTriangles, s.numVerts) for s in m.surfaces]))
    if '--out' not in sys.argv:
        p = hv.staged('scripts/coop_fg42_sight.shader'); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', newline='\n').write(SHADER)
        # the G43 sheet (dark 50 | edge 150 of 255) read MID-GREY on this gun beside a near-black receiver (run hj22):
        # darker steel, a duller edge
        tex = G.sight_tex().astype(float)
        n = tex.shape[1]
        tex[:, :n // 2] *= 0.52; tex[:, n // 2:] *= 0.66
        G.write_tga(hv.staged('textures/coop_wpn/fg42_sight.tga'), tex)
        print('wrote', p, 'and textures/coop_wpn/fg42_sight.tga')
    F = [round((POST['x0'] + POST['x1']) / 2, 4), YC, POST['zt']]; R = [REAR['x'], YC, REAR['zc']]
    print('sight row: F %s  R %s  (sight radius %.1f u, line %.2f deg to the bore axis)' % (F, R, F[0] - R[0], math.degrees(math.atan2(R[2] - F[2], F[0] - R[0]))))


if __name__ == '__main__':
    main()

"""beltgun.py - belt-fed guns get an OPENING TOP COVER (reload authenticity phase B, group 8).

    python beltgun.py <gun>          gun = mg42 | m1919

1. MESH: a copy of the gun's skd with one new bone, 'cover' (parent origin, no rest offset), and the top-cover
   vertices (a box in gun space, chosen from a side-view plot) re-weighted from 'origin' to it. Vertex offsets are
   unchanged and the bone's identity pose IS the closed cover, so every animation without cover channels (idle, fire,
   AI, third person) draws the gun exactly as before.
2. WORLD RELOAD ANIM: the gun's idle pose for the whole reload (same frame time as the BAR torso, 98 frames) plus
   'cover rot' / 'cover pos' channels: the cover swings open about its FRONT hinge (rear edge up), holds, closes.
   pos = hinge - R(hinge) so the rotation is about the hinge, in model units.
3. BELT PROP (mg42 only): the gun skd listing only the 'shellbelt' surface - a gun-space prop for the frozen-tag trick.
Writes into hzm-mohaa-coop-mod (paths that override the xw pack's).
"""
import sys, os, struct, math
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import vfs, skdlib, gungeo
import numpy as np
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'

GUNS = {
    # box in GAME units (gun frame: x fwd, y right, z down) from tools side plots; hinge = front edge of the cover
    'mg42': dict(tik='models/weapons/mg42portable.tik', skd='models/weapons/mg42portable/mg42.skd', idle='models/weapons/mg42portable/mg42.skc',
                 surf='mg421', box=((2.3, 10.8), (-3.0, 3.0), (-6.6, -3.9)), hinge=(10.6, 0.0, -4.0),
                 out_skc='models/weapons/mg42portable/coop_mg42_reload.skc', belt='shellbelt'),
    'm1919': dict(tik='models/weapons/30calportable.tik', skd='models/weapons/30calportable/30cal.skd', idle='models/weapons/30calportable/30cal.skc',
                  surf='weapon', box=((1.8, 17.2), (-3.0, 3.0), (-6.4, -4.6)), hinge=(17.2, 0.0, -4.8),
                  out_skc='models/weapons/30calportable/coop_30cal_reload.skc', belt=None),
}
# cover angle keys over the 98-frame reload (deg, + = rear edge UP), frame: angle
COVER_KEYS = [(0, 0.0), (12, 0.0), (22, 70.0), (50, 70.0), (56, 0.0), (97, 0.0)]


def ease(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def angle_at(f):
    for (fa, a), (fb, b) in zip(COVER_KEYS, COVER_KEYS[1:]):
        if fa <= f <= fb:
            return a + (b - a) * ease((f - fa) / float(fb - fa))
    return 0.0


def build_skd(spec, scale):
    """add bone 'cover' and move the cover's TRIANGLES onto it. Vertices shared with body triangles are DUPLICATED
    (body keeps the original on 'origin', the cover uses a copy on 'cover'), so opening the cover cannot stretch the
    receiver sides; cover-only vertices are simply re-weighted. LOD collapse arrays are all zero in these meshes and
    are extended with zeros."""
    d = bytes(vfs.read(spec['skd'])); m = skdlib.read_skd(d)
    assert m.version == 5 and all(b.name != 'cover' for b in m.bones)
    newbone = m.numBones
    (x0, x1), (y0, y1), (z0, z1) = spec['box']
    sc = [x for x in m.surfaces if x.name == spec['surf']][0]
    so = sc.raw_off
    nT, nV, st, oT, oV, oC, oE, oCI = struct.unpack_from('<8i', d, so + 68)
    tris = np.frombuffer(d[so + oT: so + oT + 12 * nT], dtype='<i4').reshape(-1, 3).copy()
    recs, inbox = [], []
    voff = so + oV
    for v in range(nV):
        nw, nm = struct.unpack_from('<2i', d, voff + 20)
        ln = 28 + 16 * nm + 20 * nw
        r = bytearray(d[voff: voff + ln]); recs.append(r)
        wb = 28 + 16 * nm
        p = np.zeros(3); only0 = True
        for w in range(nw):
            bi, bw = struct.unpack_from('<if', r, wb + 20 * w)
            p += bw * np.array(struct.unpack_from('<3f', r, wb + 20 * w + 8)); only0 &= (bi == 0)
        p *= scale
        inbox.append(only0 and x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1)
        voff += ln
    assert voff == so + oC
    cov = np.array([all(inbox[k] for k in t) for t in tris])
    used_by_body = set(int(k) for t, c in zip(tris, cov) if not c for k in t)
    remap = {}
    def to_cover(r):
        r = bytearray(r); nw, nm = struct.unpack_from('<2i', r, 20)
        for w in range(nw):
            struct.pack_into('<i', r, 28 + 16 * nm + 20 * w, newbone)
        return r
    for t, c in zip(tris, cov):
        if not c:
            continue
        for k in t:
            k = int(k)
            if k in remap:
                continue
            if k in used_by_body:
                remap[k] = len(recs); recs.append(to_cover(recs[k]))
            else:
                recs[k] = to_cover(recs[k]); remap[k] = k
    for ti in range(len(tris)):
        if cov[ti]:
            tris[ti] = [remap[int(k)] for k in tris[ti]]
    nV2 = len(recs)
    vb = b''.join(bytes(r) for r in recs)
    oT2 = 100; oV2 = oT2 + 12 * nT; oC2 = oV2 + len(vb); oCI2 = oC2 + 4 * nV2; oE2 = oCI2 + 4 * nV2
    hdr = bytearray(d[so: so + 100])
    struct.pack_into('<8i', hdr, 68, nT, nV2, st, oT2, oV2, oC2, oE2, oCI2)
    surf = bytes(hdr) + tris.astype('<i4').tobytes() + vb + bytes(4 * nV2) + bytes(4 * nV2)
    assert len(surf) == oE2
    d2 = d[:so] + surf + d[so + oE:]
    dsurf = len(surf) - oE
    # the bone record, inserted right after the last bone (= start of the surfaces)
    chans = bytes('cover rot', 'ascii') + bytes(1) + bytes('cover pos', 'ascii') + bytes(1)
    rec = bytearray(84 + 12 + len(chans))
    rec[0:5] = b'cover'; rec[32:38] = b'origin'
    struct.pack_into('<5i', rec, 64, 1, 84, 96, 96 + len(chans), 96 + len(chans))
    struct.pack_into('<3f', rec, 84, 1.0, 1.0, 1.0)
    rec[96:] = chans
    ins = m.ofsSurfaces
    out = bytearray(d2[:ins] + rec + d2[ins:])
    shift = len(rec)
    numSurf, numBones, ofsBones, ofsSurf, ofsEnd = struct.unpack_from('<5i', out, 72)
    struct.pack_into('<5i', out, 72, numSurf, numBones + 1, ofsBones, ofsSurf + shift, ofsEnd + shift + dsurf)
    for k in range(6):                           # trailing header offsets (boxes / morphs) that pointed past the end
        v = struct.unpack_from('<i', out, 132 + 4 * k)[0]
        if ins <= v <= len(d):
            struct.pack_into('<i', out, 132 + 4 * k, v + shift + dsurf)
    chk = skdlib.read_skd(bytes(out))
    assert [b.name for b in chk.bones][-1] == 'cover' and [x.name for x in chk.surfaces] == [x.name for x in m.surfaces]
    return bytes(out), (int(cov.sum()), len(remap), nV2 - nV)


def build_skc(spec, scale):
    idle = vfs.read(spec['idle'])
    assert struct.unpack_from('<i', idle, 4)[0] == 13
    ver, flags, nb, ft = struct.unpack_from('<3if', idle, 4)
    td = struct.unpack_from('<3f', idle, 20); tad = struct.unpack_from('<f', idle, 32)[0]
    nch, ofs_names, nfr = struct.unpack_from('<3i', idle, 36)
    names = [idle[ofs_names + 32 * i: ofs_names + 32 * i + 32] for i in range(nch)]
    blk0 = bytearray(idle[48:96]); vals0 = idle[struct.unpack_from('<i', blk0, 44)[0]: struct.unpack_from('<i', blk0, 44)[0] + 16 * nch]
    n = 98; NCH = nch + 2; ft = 1.0 / 30.0
    hdr = 48; ofs_vals = hdr + 48 * n; ofs_ch = ofs_vals + n * NCH * 16; end = ofs_ch + 32 * NCH
    out = bytearray(end)
    struct.pack_into('<4s3if3ff3i', out, 0, b'SKAN', 13, flags, end, ft, 0.0, 0.0, 0.0, 0.0, NCH, ofs_ch, n)
    H = np.array(spec['hinge']) / scale           # model units
    for f in range(n):
        b = bytearray(blk0); struct.pack_into('<i', b, 44, ofs_vals + f * NCH * 16)
        struct.pack_into('<3f', b, 28, 0.0, 0.0, 0.0)  # per-frame delta: none
        out[hdr + 48 * f: hdr + 48 * f + 48] = b
        base = ofs_vals + f * NCH * 16
        out[base: base + 16 * nch] = vals0
        a = math.radians(angle_at(f))
        # rotation about the gun Y axis: rear edge (smaller x) goes UP (-z): +a about +y maps (-1,0,0) toward (0,0,-1)
        q = (0.0, math.sin(a / 2), 0.0, math.cos(a / 2))   # + = rear edge UP (z- is up), checked numerically
        Rm = np.array(skdlib.quat_to_mat3(q))            # the evaluator's convention: p_world = p @ Rm + pos
        p = H - H @ Rm
        struct.pack_into('<4f', out, base + 16 * nch, *q)
        struct.pack_into('<4f', out, base + 16 * nch + 16, p[0], p[1], p[2], 0.0)
    for i, nm in enumerate(names):
        out[ofs_ch + 32 * i: ofs_ch + 32 * i + 32] = nm
    out[ofs_ch + 32 * nch: ofs_ch + 32 * nch + 9] = b'cover rot'
    out[ofs_ch + 32 * (nch + 1): ofs_ch + 32 * (nch + 1) + 9] = b'cover pos'
    return bytes(out)


def main():
    g = sys.argv[1]; spec = GUNS[g]
    t = gungeo.parse_tik(spec['tik']); scale = t['scale']
    skd, moved = build_skd(spec, scale)
    p = os.path.join(MOD, spec['skd'].replace('/', os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(skd)
    skc = build_skc(spec, scale)
    open(os.path.join(MOD, spec['out_skc'].replace('/', os.sep)), 'wb').write(skc)
    print(g, 'scale', scale, 'cover tris / verts / duplicated', moved, '->', p)
    if spec.get('belt'):
        m = skdlib.read_skd(skd); s = [x for x in m.surfaces if x.name == spec['belt']][0]
        b = bytearray(skd); struct.pack_into('<i', b, 72, 1); struct.pack_into('<i', b, 84, s.raw_off)
        bp = os.path.join(os.path.dirname(p), 'coop_belt.skd'); open(bp, 'wb').write(bytes(b))
        print('belt prop skd', bp)


if __name__ == '__main__':
    main()

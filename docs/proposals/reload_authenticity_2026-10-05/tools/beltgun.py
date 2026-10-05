"""beltgun.py - belt-fed guns: movable top cover + charging handle, belt model, world reload anim (phase B polish).

    python beltgun.py <gun>          gun = mg42 | m1919

MESH (a mod override of the xw skd; every animation without the new channels draws the gun exactly as before):
  * bone 'cover'   - the top-cover triangles (box from side/top plots), shared vertices duplicated so nothing stretches;
  * bone 'chandle' - the charging-handle triangles (right side);
  * m1919: the ammo box (surface 'crate') is REMOVED (user: "remove ammo box for 30"); a 'belt' surface is added - a
    short length of linked rounds hanging from the feedway on the left (the MG42's shellbelt strip, moved/rescaled),
    the belt the gun carries when loaded.
PROPS: a belt-only copy of the skd (coop_belt.skd) for the hand.
WORLD RELOAD (coop_*_reload.skc, 98 frames at 1/30 s = the BAR torso): idle pose + 'cover rot/pos' (opens about the
front hinge, rear edge up) + 'chandle pos' (charging handle travel) from beltsched.py - the same timeline the hands use.
"""
import sys, os, struct, math
sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfs, skdlib, gungeo
import numpy as np
import beltsched as BS
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'

GUNS = {
    'mg42': dict(tik='models/weapons/mg42portable.tik', skd='models/weapons/mg42portable/mg42.skd',
                 idle='models/weapons/mg42portable/mg42.skc', body='mg421', handle_surf='mg422',
                 out_skc='models/weapons/mg42portable/coop_mg42_reload.skc', belt_surf='shellbelt', drop=None, add_belt=None),
    'm1919': dict(tik='models/weapons/30calportable.tik', skd='models/weapons/30calportable/30cal.skd',
                  idle='models/weapons/30calportable/30cal.skc', body='weapon', handle_surf='weapon',
                  out_skc='models/weapons/30calportable/coop_30cal_reload.skc', belt_surf='belt', drop='crate',
                  # the MG42 belt strip: top end (7.6, -4.7, -4.1) -> the M1919 feedway (14.3, -2.4, -4.6), game units
                  add_belt=dict(src='models/weapons/mg42portable/mg42.skd', surf='shellbelt', src_scale=0.52,
                                shift=(14.3 - 7.6, -2.4 + 4.7, -4.6 + 4.1))),
}


class Surf:
    pass


def parse_surfaces(d, m):
    out = []
    for s in m.surfaces:
        o = s.raw_off
        nT, nV, st, oT, oV, oC, oE, oCI = struct.unpack_from('<8i', d, o + 68)
        S = Surf(); S.name = s.name; S.hdr = bytearray(d[o: o + 100]); S.st = st
        S.tris = np.frombuffer(d[o + oT: o + oT + 12 * nT], dtype='<i4').reshape(-1, 3).copy()
        S.recs = []
        voff = o + oV
        for v in range(nV):
            nw, nm = struct.unpack_from('<2i', d, voff + 20)
            ln = 28 + 16 * nm + 20 * nw
            S.recs.append(bytearray(d[voff: voff + ln])); voff += ln
        out.append(S)
    return out


def rec_pos(r, scale):
    nw, nm = struct.unpack_from('<2i', r, 20); wb = 28 + 16 * nm
    p = np.zeros(3); bones = set()
    for w in range(nw):
        bi, bw = struct.unpack_from('<if', r, wb + 20 * w)
        p += bw * np.array(struct.unpack_from('<3f', r, wb + 20 * w + 8)); bones.add(bi)
    return p * scale, bones


def set_bone(r, bone):
    r = bytearray(r); nw, nm = struct.unpack_from('<2i', r, 20)
    for w in range(nw):
        struct.pack_into('<i', r, 28 + 16 * nm + 20 * w, bone)
    return r


def split(S, box, bone, scale):
    """move every triangle whose 3 vertices are origin-weighted and inside box onto `bone`; shared vertices duplicated"""
    (x0, x1), (y0, y1), (z0, z1) = box
    inbox = []
    for r in S.recs:
        p, bones = rec_pos(r, scale)
        inbox.append(bones == {0} and x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1)
    sel = np.array([all(inbox[k] for k in t) for t in S.tris])
    body_use = set(int(k) for t, c in zip(S.tris, sel) if not c for k in t)
    remap = {}
    for t, c in zip(S.tris, sel):
        if not c:
            continue
        for k in t:
            k = int(k)
            if k in remap:
                continue
            if k in body_use:
                remap[k] = len(S.recs); S.recs.append(set_bone(S.recs[k], bone))
            else:
                S.recs[k] = set_bone(S.recs[k], bone); remap[k] = k
    for i in range(len(S.tris)):
        if sel[i]:
            S.tris[i] = [remap[int(k)] for k in S.tris[i]]
    return int(sel.sum())


def ser_surface(S):
    nT, nV = len(S.tris), len(S.recs)
    vb = b''.join(bytes(r) for r in S.recs)
    oT = 100; oV = oT + 12 * nT; oC = oV + len(vb); oCI = oC + 4 * nV; oE = oCI + 4 * nV
    h = bytearray(S.hdr); h[4:68] = S.name.encode('latin1')[:63].ljust(64, b'\0')
    struct.pack_into('<8i', h, 68, nT, nV, S.st, oT, oV, oC, oE, oCI)
    return bytes(h) + S.tris.astype('<i4').tobytes() + vb + bytes(8 * nV)


def bone_rec(name, chans):
    cb = b''.join(c.encode('ascii') + bytes(1) for c in chans)
    rec = bytearray(96 + len(cb))
    rec[0:len(name)] = name.encode('ascii'); rec[32:38] = b'origin'
    struct.pack_into('<5i', rec, 64, 1, 84, 96, 96 + len(cb), 96 + len(cb))
    struct.pack_into('<3f', rec, 84, 1.0, 1.0, 1.0)
    rec[96:] = cb
    return bytes(rec)


def build_skd(g, spec, scale):
    d = bytes(vfs.read(spec['skd'])); m = skdlib.read_skd(d)
    assert m.version == 5 and all(b.name not in ('cover', 'chandle') for b in m.bones)
    sch = BS.GUNS[g]
    surfs = parse_surfaces(d, m)
    nb = m.numBones
    body = [s for s in surfs if s.name == spec['body']][0]
    n_cover = split(body, sch['cover_box'], nb, scale)
    n_handle = sum(split(s, sch['handle_box'], nb + 1, scale) for s in surfs if s.name != spec['drop'])
    if spec['drop']:
        surfs = [s for s in surfs if s.name != spec['drop']]
    if spec['add_belt']:
        ab = spec['add_belt']
        sd = bytes(vfs.read(ab['src'])); sm = skdlib.read_skd(sd)
        src = [s for s in parse_surfaces(sd, sm) if s.name == ab['surf']][0]
        nb2 = Surf(); nb2.name = 'belt'; nb2.hdr = bytearray(src.hdr); nb2.st = src.st; nb2.tris = src.tris.copy(); nb2.recs = []
        for r in src.recs:
            r = bytearray(r); nw, nm = struct.unpack_from('<2i', r, 20); wb = 28 + 16 * nm
            for w in range(nw):
                o = np.array(struct.unpack_from('<3f', r, wb + 20 * w + 8))
                struct.pack_into('<i', r, wb + 20 * w, 0)
                struct.pack_into('<3f', r, wb + 20 * w + 8, *((o * ab['src_scale'] + np.array(ab['shift'])) / scale))
            nb2.recs.append(r)
        surfs.append(nb2)
    bones_end = m.ofsSurfaces
    head = bytearray(d[:bones_end]) + bone_rec('cover', ['cover rot', 'cover pos']) + bone_rec('chandle', ['chandle rot', 'chandle pos'])
    sb = b''.join(ser_surface(s) for s in surfs)
    tail = d[m.ofsEnd:] if m.ofsEnd < len(d) else b''
    out = head + sb + tail
    struct.pack_into('<5i', out, 72, len(surfs), nb + 2, m.ofsBones, len(head), len(head) + len(sb))
    for k in range(6):                   # trailing header offsets (boxes / morphs) that pointed at the old end
        v = struct.unpack_from('<i', d, 132 + 4 * k)[0]
        if v == m.ofsEnd:
            struct.pack_into('<i', out, 132 + 4 * k, len(head) + len(sb))
    chk = skdlib.read_skd(bytes(out))
    assert [b.name for b in chk.bones][-2:] == ['cover', 'chandle'], [b.name for b in chk.bones]
    return bytes(out), (n_cover, n_handle, [s.name for s in surfs])


def build_skc(g, spec, scale):
    idle = vfs.read(spec['idle'])
    assert struct.unpack_from('<i', idle, 4)[0] == 13
    ver, flags, nb, ft = struct.unpack_from('<3if', idle, 4)
    nch, ofs_names, nfr = struct.unpack_from('<3i', idle, 36)
    names = [idle[ofs_names + 32 * i: ofs_names + 32 * i + 32] for i in range(nch)]
    blk0 = bytearray(idle[48:96]); v0 = struct.unpack_from('<i', blk0, 44)[0]; vals0 = idle[v0: v0 + 16 * nch]
    n = 98; NCH = nch + 4; ft = 1.0 / 30.0
    hdr = 48; ofs_vals = hdr + 48 * n; ofs_ch = ofs_vals + n * NCH * 16; end = ofs_ch + 32 * NCH
    out = bytearray(end)
    struct.pack_into('<4s3if3ff3i', out, 0, b'SKAN', 13, flags, end, ft, 0.0, 0.0, 0.0, 0.0, NCH, ofs_ch, n)
    Hm = np.array(BS.GUNS[g]['hinge']) / scale
    for f in range(n):
        b = bytearray(blk0); struct.pack_into('<i', b, 44, ofs_vals + f * NCH * 16); struct.pack_into('<3f', b, 28, 0, 0, 0)
        out[hdr + 48 * f: hdr + 48 * f + 48] = b
        base = ofs_vals + f * NCH * 16
        out[base: base + 16 * nch] = vals0
        a = math.radians(BS.cover_angle(g, f))
        q = (0.0, math.sin(a / 2), 0.0, math.cos(a / 2))
        Rm = np.array(skdlib.quat_to_mat3(q))
        p = Hm - Hm @ Rm
        struct.pack_into('<4f', out, base + 16 * nch, *q)
        struct.pack_into('<4f', out, base + 16 * nch + 16, p[0], p[1], p[2], 0.0)
        struct.pack_into('<4f', out, base + 16 * nch + 32, 0.0, 0.0, 0.0, 1.0)
        struct.pack_into('<4f', out, base + 16 * nch + 48, BS.handle_dx(g, f) / scale, 0.0, 0.0, 0.0)
    for i, nm in enumerate(names):
        out[ofs_ch + 32 * i: ofs_ch + 32 * i + 32] = nm
    for k, nm in enumerate([b'cover rot', b'cover pos', b'chandle rot', b'chandle pos']):
        out[ofs_ch + 32 * (nch + k): ofs_ch + 32 * (nch + k) + len(nm)] = nm
    return bytes(out)


def main():
    g = sys.argv[1]; spec = GUNS[g]
    t = gungeo.parse_tik(spec['tik']); scale = t['scale']
    skd, info = build_skd(g, spec, scale)
    p = os.path.join(MOD, spec['skd'].replace('/', os.sep)); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(skd)
    open(os.path.join(MOD, spec['out_skc'].replace('/', os.sep)), 'wb').write(build_skc(g, spec, scale))
    m = skdlib.read_skd(skd); s = [x for x in m.surfaces if x.name == spec['belt_surf']][0]
    bsk = bytearray(skd); struct.pack_into('<i', bsk, 72, 1); struct.pack_into('<i', bsk, 84, s.raw_off)
    open(os.path.join(os.path.dirname(p), 'coop_belt.skd'), 'wb').write(bytes(bsk))
    print(g, 'scale', scale, 'cover tris %d, handle tris %d, surfaces %s' % info)


if __name__ == '__main__':
    main()

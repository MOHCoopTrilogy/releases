#!/usr/bin/env python3
"""MOHAA skeletor in Python (stdlib only): the stock human .skd bone block, .skc (SKAN v13) frames, and the engine's
forward kinematics, so converted animations can be checked offline and written. Our own code.

Conventions, read from openmohaa skeletor/skeletorbones.cpp (verified 2026-11-15 against engine bone dumps):
  * a bone transform is 4 rows: axes x, y, z, then the origin; row-vector composition: global = local * parent
  * a quaternion channel (x, y, z, w) becomes the local rows by QuatToMat (q_math.c)
  * bone types (skd bone 'jt'): 0 Rotation (fixed offset from the skd + '<bone> rot'), 1 PosRot ('<bone> pos' +
    '<bone> rot'), 2 IKshoulder (thigh: offset from the skd, no channel), 3 IKelbow (calf), 4 IKwrist (foot: the
    '<foot> pos' / '<foot> rot' channels are the MODEL-space target the shoulder/elbow are solved to), 5 HoseRot /
    6 AvRot helpers; '<bone> rotFK' channels are ignored by the engine (bonetable.cpp: CHANNEL_NONE)
"""
import math
import struct


def quat_to_rows(q):
    x, y, z, w = q
    x2, y2, z2 = x + x, y + y, z + z
    xx, xy, xz, yy, yz, zz = x * x2, x * y2, x * z2, y * y2, y * z2, z * z2
    wx, wy, wz = w * x2, w * y2, w * z2
    return [[1.0 - (yy + zz), xy - wz, xz + wy],
            [xy + wz, 1.0 - (xx + zz), yz - wx],
            [xz - wy, yz + wx, 1.0 - (xx + yy)]]


def rows_to_quat(m):
    """inverse of quat_to_rows (m: 3 rows), w >= 0"""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)
    n = math.sqrt(sum(v * v for v in q)) or 1.0
    q = tuple(v / n for v in q)
    return tuple(-v for v in q) if q[3] < 0 else q


def mul(a, b):
    """row-vector 4x3 transforms: (a then b) = a * b"""
    r = [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    o = [a[3][0] * b[0][j] + a[3][1] * b[1][j] + a[3][2] * b[2][j] + b[3][j] for j in range(3)]
    return r + [o]


def inv(a):
    r = [[a[j][i] for j in range(3)] for i in range(3)]
    o = [-(a[3][0] * r[0][j] + a[3][1] * r[1][j] + a[3][2] * r[2][j]) for j in range(3)]
    return r + [o]


def read_skd_bones(b):
    """[(name, parent, jt, offset (3), lengths/extra floats)] in file order"""
    nsurf, nbones, ofsb = struct.unpack_from("<3i", b, 72)
    o, out = ofsb, []
    for _ in range(nbones):
        name = b[o:o + 32].split(b"\0")[0].decode("latin-1")
        par = b[o + 32:o + 64].split(b"\0")[0].decode("latin-1")
        jt, ov, oc, orf, oe = struct.unpack_from("<5i", b, o + 64)
        vals = struct.unpack_from("<10f", b, o + ov) if ov else ()
        out.append((name, par, jt, vals))
        o += oe
    return out


def read_skc(b):
    hdr = struct.unpack_from("<4s3if3ff3i", b, 0)
    assert hdr[0] == b"SKAN" and hdr[1] == 13, "not an uncompressed SKAN v13"
    flags, frametime, nc, o_ch, nf = hdr[2], hdr[4], hdr[9], hdr[10], hdr[11]
    chans = [b[o_ch + 32 * i:o_ch + 32 * i + 32].split(b"\0")[0].decode("latin-1") for i in range(nc)]
    frames = []
    for f in range(nf):
        ov = struct.unpack_from("<i", b, 48 + 48 * f + 44)[0]
        frames.append({c: struct.unpack_from("<4f", b, ov + 16 * i) for i, c in enumerate(chans)})
    return {"flags": flags, "frametime": frametime, "channels": chans, "frames": frames}


def write_skc(frametime, channels, frames, flags=0, deltas=None):
    """SKAN v13: 48 header | nf x 48 frame headers | nf x nc x 16 data | nc x 32 names. frames: [{channel: 4 floats}]"""
    nc, nf = len(channels), len(frames)
    ofs_data = 48 + 48 * nf
    ofs_names = ofs_data + 16 * nc * nf
    total = ofs_names + 32 * nc
    head = []
    data = bytearray()
    for f, fr in enumerate(frames):
        pos = fr.get("Bip01 pos", (0, 0, 0, 0))
        dl = deltas[f] if deltas else (0.0, 0.0, 0.0)
        head.append(struct.pack("<3f3ff3ffi", -60.0, -60.0, 0.0, 60.0, 60.0, 180.0, 110.0, dl[0], dl[1], dl[2], 0.0,
                                ofs_data + 16 * nc * f))
        for c in channels:
            data += struct.pack("<4f", *fr[c])
    names = b"".join(c.encode("latin-1").ljust(32, b"\0") for c in channels)
    hdr = struct.pack("<4s3if3ff3i", b"SKAN", 13, flags, total, frametime, 0.0, 0.0, 0.0, 0.0, nc, ofs_names, nf)
    out = hdr + b"".join(head) + bytes(data) + names
    assert len(out) == total
    return out


def fk(bones, ch):
    """{bone: 4x3 rows} for one frame of channels ch {name: 4 floats}, as skeletorbones.cpp computes them"""
    T = {}
    by = {b[0]: b for b in bones}
    ident = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0], [0.0, 0.0, 0.0]]

    def get(name):
        if name in T:
            return T[name]
        if name not in by:
            return ident
        nm, par, jt, v = by[name]
        P = get(par) if par in by else None
        if jt == 0:        # Rotation
            loc = quat_to_rows(ch.get(nm + " rot", (0, 0, 0, 1))) + [list(v[0:3])]
            T[nm] = mul(loc, P) if P else loc
        elif jt == 1:      # PosRot
            loc = quat_to_rows(ch.get(nm + " rot", (0, 0, 0, 1))) + [list(ch.get(nm + " pos", (0, 0, 0, 0))[:3])]
            T[nm] = mul(loc, P) if P else loc
        elif jt in (2, 3, 4):
            _ik(by, nm, get, ch, T)
        else:              # helpers: not needed for skinning the converted bodies
            T[nm] = P or ident
        return T[nm]
    for b in bones:
        get(b[0])
    return T


def _ik(by, nm, get, ch, T):
    """IKshoulder / IKelbow / IKwrist of one leg (or arm) chain, solved together"""
    if by[nm][2] == 2:
        sh = nm
    elif by[nm][2] == 3:
        sh = by[nm][1]
    else:
        sh = by[by[nm][1]][1]
    el = [b for b in by if by[b][1] == sh and by[b][2] == 3][0]
    wr = [b for b in by if by[b][1] == el and by[b][2] == 4][0]
    upper, lower = by[el][3][0], by[wr][3][0]
    base = [row[:] for row in get(by[sh][1])]
    off = by[sh][3][4:7]           # IKshoulder data: 4 floats (a base quaternion), then the offset
    base[3] = [base[3][j] + off[0] * base[0][j] + off[1] * base[1][j] + off[2] * base[2][j] for j in range(3)]
    base[0] = [-x for x in base[0]]
    base[2] = [-x for x in base[2]]
    wq = ch.get(wr + " rot", (0, 0, 0, 1))
    tgt = quat_to_rows(wq) + [list(ch.get(wr + " pos", (0, 0, 0, 0))[:3])]
    c0 = [tgt[3][j] - base[3][j] for j in range(3)]
    dist = math.sqrt(sum(x * x for x in c0)) or 1e-9
    c0 = [x / dist for x in c0]
    cr = lambda a, b: [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    c1 = cr(base[2], c0)
    c1 = [c1[j] + cr(tgt[2], c0)[j] for j in range(3)]
    l1 = math.sqrt(sum(x * x for x in c1))
    c1 = [x / l1 for x in c1] if l1 else [0.0, 1.0, 0.0]
    c2 = cr(c0, c1)
    wpos = tgt[3][:]
    mx = upper + lower - 0.001
    if dist > mx:
        dist = mx
        wpos = [base[3][j] + c0[j] * mx for j in range(3)]
    cosu = min(1.0, (dist * dist + upper * upper - lower * lower) / (2 * dist * upper))
    cose = -((lower * lower + upper * upper - dist * dist) / (2 * upper * lower))
    ln = -math.sqrt(max(0.0, 1.0 - cosu * cosu))
    a0 = [c0[j] * cosu - c1[j] * ln for j in range(3)]
    a1 = [c1[j] * cosu + c0[j] * ln for j in range(3)]
    S = [a0, a1, c2, base[3]]
    T[sh] = S
    fl = math.sqrt(max(0.0, 1.0 - cose * cose))
    o = [S[3][j] + S[0][j] * upper for j in range(3)]
    e0 = [S[0][j] * cose - S[1][j] * fl for j in range(3)]
    e1 = [S[1][j] * cose + S[0][j] * fl for j in range(3)]
    T[el] = [e0, e1, S[2][:], o]
    T[wr] = quat_to_rows(wq) + [wpos]

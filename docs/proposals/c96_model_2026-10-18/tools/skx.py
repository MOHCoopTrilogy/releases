"""SKD v5 / SKC v13 writing for a NEW multi-bone, multi-surface model.

The mod's existing writers are one-bone containers (docs/tools/gen_coop_sea.py build_skd / build_skc, ironsights
skdlib.build_container_skd) or patch an existing file (ads_bolt add_part.py / gen_fire.py). This module is the same
byte layout as those (surface block, bone block, SKAN header / frame / channel table), generalised to N POSROT bones,
one bone index per vertex, N surfaces and N frames - nothing else is new. Layout references: gen_coop_sea.py:427-494,
add_part.py:31 (bone block), gen_fire.py:36 (multi-frame SKAN), engine code/tiki/tiki_skel.cpp.

Conventions (skdlib.py header): vertex offsets and normals are BONE-LOCAL, row vectors: p = off @ R + t;
world = local * parent. Triangles are wound like the retail meshes: cross(b - a, c - a) . n < 0.
Limits (engine): a surface must stay under TIKI_MAX_VERTEXES 1000 (renderer collapse[] buffer) - MAXV / MAXT below.
"""
import struct
import numpy as np

MAXV = 900
MAXT = 1700


def _c(s, n):
    b = s.encode('latin-1')
    assert len(b) < n, s
    return b + b'\0' * (n - len(b))


def bone_block(name, parent):
    ch = (name + ' rot').encode('latin-1') + b'\0' + (name + ' pos').encode('latin-1') + b'\0'
    end = 96 + len(ch)
    blk = _c(name, 32) + _c(parent, 32) + struct.pack('<5i', 1, 84, 96, end, end) + struct.pack('<3f', 1.0, 1.0, 1.0) + ch
    assert len(blk) == end
    return blk


def surface_block(name, tris, verts):
    """tris: (T,3) int; verts: list of (normal3, uv2, bone index, offset3)"""
    nT, nV = len(tris), len(verts)
    assert nV < 1000 and nT < 2000, (name, nV, nT)
    vb = bytearray()
    for n, uv, bi, off in verts:
        vb += struct.pack('<3f2f2i', *n, *uv, 1, 0)
        vb += struct.pack('<if3f', bi, 1.0, *off)
    tb = np.asarray(tris, '<i4').tobytes()
    oT = 100; oV = oT + nT * 12; oC = oV + nV * 48; oCI = oC + nV * 4; oE = oCI + nV * 4
    hdr = struct.pack('<4s64s8i', b'SKL ', _c(name, 64), nT, nV, 0, oT, oV, oC, oE, oCI)
    # identity collapse + all-zero collapse index (bug-1002: the engine reads both unconditionally)
    blob = hdr + tb + bytes(vb) + struct.pack('<%di' % nV, *range(nV)) + struct.pack('<%di' % nV, *([0] * nV))
    assert len(blob) == oE
    return blob


def build_skd(name, bones, surfaces):
    """bones: [(name, parent)], parents first; surfaces: [(name, tris, verts)]"""
    bb = b''.join(bone_block(n, p) for n, p in bones)
    sb = b''.join(surface_block(*s) for s in surfaces)
    total = 148 + len(bb) + len(sb)
    hdr = struct.pack('<4si64s5i10i4i', b'SKMD', 5, _c(name, 64), len(surfaces), len(bones), 148, 148 + len(bb), total,
                      *([0] * 10), 0, total, 0, total)
    assert len(hdr) == 148
    return hdr + bb + sb


def build_skc(channels, frames, frame_time, bmin, bmax, radius):
    """channels: names ('<bone> pos' / '<bone> rot'); frames: [F][C] of 4 floats (pos: x y z 0; rot: quat x y z w)"""
    nf, nc = len(frames), len(channels)
    o_fr = 48; o_val = o_fr + 48 * nf; o_ch = o_val + 16 * nc * nf; end = o_ch + 32 * nc
    out = bytearray(end)
    struct.pack_into('<4s3if3ff3i', out, 0, b'SKAN', 13, 0, end, frame_time, 0.0, 0.0, 0.0, 0.0, nc, o_ch, nf)
    for f in range(nf):
        ov = o_val + 16 * nc * f
        struct.pack_into('<6ff3ffi', out, o_fr + 48 * f, *bmin, *bmax, radius, 0.0, 0.0, 0.0, 0.0, ov)
        assert len(frames[f]) == nc
        for c in range(nc):
            struct.pack_into('<4f', out, ov + 16 * c, *frames[f][c])
    for i, n in enumerate(channels):
        out[o_ch + 32 * i: o_ch + 32 * i + 32] = _c(n, 32)
    return bytes(out)


def split_surfaces(prefix, tri_corners):
    """tri_corners: list of triangles, each 3 x (bone index, offset3, normal3, uv2), ALREADY in file winding.
    -> [(name, tris, verts)] with shared vertices welded and every surface under MAXV / MAXT."""
    out = []
    idx = {}; verts = []; tris = []

    def flush():
        nonlocal idx, verts, tris
        if tris:
            out.append(('%s%d' % (prefix, len(out) + 1), np.asarray(tris, int), verts))
        idx = {}; verts = []; tris = []

    for tri in tri_corners:
        keys = [(c[0], tuple(np.round(c[1], 4)), tuple(np.round(c[2], 3)), tuple(np.round(c[3], 5))) for c in tri]
        new = sum(1 for k in set(keys) if k not in idx)
        if len(verts) + new > MAXV or len(tris) + 1 > MAXT:
            flush()
        t = []
        for k, c in zip(keys, tri):
            if k not in idx:
                idx[k] = len(verts)
                verts.append((tuple(c[2]), tuple(c[3]), c[0], tuple(c[1])))
            t.append(idx[k])
        if len(set(t)) == 3:
            tris.append(t)
    flush()
    return out


def quat(axis, deg):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    h = np.radians(deg) / 2
    return (*(a * np.sin(h)), float(np.cos(h)))

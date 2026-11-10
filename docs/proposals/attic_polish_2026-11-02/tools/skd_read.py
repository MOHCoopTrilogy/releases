"""skd_read.py - read an SKD v5/v6 model written by skx.build_skd / build_models2 (one surface list, bone-local offsets).

read_skd(bytes) -> dict(name, bones=[(name, parent)], surfaces=[dict(name, tris (T,3), verts=[(n3, uv2, bone, off3)])])
Only what the attic's own baked models use: one weight per vertex (the first weight is read, extra weights are skipped).
"""
import struct
import numpy as np


def read_skd(b):
    ident, ver, name, nS, nB, oB, oS, end = struct.unpack_from('<4si64s5i', b, 0)
    assert ident == b'SKMD', ident
    name = name.split(b'\0')[0].decode('latin-1')
    bones, o = [], oB
    for _ in range(nB):
        bn = b[o:o + 32].split(b'\0')[0].decode('latin-1')
        bp = b[o + 32:o + 64].split(b'\0')[0].decode('latin-1')
        bend = struct.unpack_from('<5i', b, o + 64)[4]
        bones.append((bn, bp))
        o += bend
    surfs, o = [], oS
    for _ in range(nS):
        sid, sname, nT, nV, _st, oT, oV, oC, oE, oCI = struct.unpack_from('<4s64s8i', b, o)
        sname = sname.split(b'\0')[0].decode('latin-1')
        tris = np.frombuffer(b, '<i4', nT * 3, o + oT).reshape(-1, 3).copy()
        verts, p = [], o + oV
        for _v in range(nV):
            nx, ny, nz, u, v, nw, nm = struct.unpack_from('<3f2f2i', b, p)
            p += 28
            first = None
            for _w in range(nw):
                bi, w, ox, oy, oz = struct.unpack_from('<if3f', b, p)
                p += 20
                if first is None:
                    first = (bi, (ox, oy, oz))
            p += 20 * 0
            p += nm * 16           # morphs (none in the attic models)
            verts.append(((nx, ny, nz), (u, v), first[0], first[1]))
        surfs.append(dict(name=sname, tris=tris, verts=verts))
        o += oE
    return dict(name=name, bones=bones, surfaces=surfs)

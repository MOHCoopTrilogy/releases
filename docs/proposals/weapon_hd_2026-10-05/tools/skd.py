"""Minimal SKD (skeletal mesh) reader: per surface, triangles + per-vertex UV, normal and the first
bone-space position. Layout from tiki/tiki_shared.h (skelHeader_t / skelSurface_t / skeletorVertex_t,
skeletorMorph_t 16 B, skelWeight_t 20 B) and tiki_skel.cpp (morphs precede weights)."""
import struct
def read(b):
    ident, ver = struct.unpack_from("<4sI", b, 0)
    assert ident in (b"SKMD",), ident
    nsurf, nbones, ofsb, ofss, ofse = struct.unpack_from("<5i", b, 72)
    surfs = []; off = ofss
    for _ in range(nsurf):
        sid, = struct.unpack_from("<i", b, off)
        name = b[off + 4:off + 68].split(b"\0")[0].decode("latin1")
        ntri, nv, _sp, ofst, ofsv, ofsc, ofsend, ofsci = struct.unpack_from("<8i", b, off + 68)
        tsize = (ofsv - ofst) // max(1, ntri)
        tris = [struct.unpack_from("<3i", b, off + ofst + i * 12) for i in range(ntri)] if tsize == 12 else \
               [struct.unpack_from("<3h", b, off + ofst + i * 6) for i in range(ntri)]
        verts = []; p = off + ofsv
        for _v in range(nv):
            nx, ny, nz, u, v, nw, nm = struct.unpack_from("<5f2i", b, p); p += 28
            p += 16 * nm
            ws = []
            for _w in range(nw):
                bi, bw, ox, oy, oz = struct.unpack_from("<if3f", b, p); p += 20
                ws.append((bi, bw, (ox, oy, oz)))
            best = max(ws, key=lambda w: w[1]) if ws else (0, 1, (0, 0, 0))
            pos = [0.0, 0.0, 0.0]
            for (bi, bw, o) in ws:
                if bi == best[0]:
                    pos = list(o)
            verts.append(dict(n=(nx, ny, nz), uv=(u, v), bone=best[0], pos=tuple(pos)))
        surfs.append(dict(name=name, tris=tris, verts=verts))
        off += ofsend
    return dict(version=ver, surfaces=surfs)

"""bspedit.py - lossless reader/writer for MOHAA/Spearhead/Breakthrough BSP (ident '2015', v17-21; written against v19).
Layout kept verbatim: header(12) + 28 x (off,len); lumps laid out in header order with the ORIGINAL inter-lump padding
and the original trailing bytes. Unchanged file -> identical bytes (tested by roundtrip()).
Struct sizes (v19): shader 140, plane 16, brushside 12, brush 12, model 40, surface 108, drawvert 44, leaf 64, node 36."""
import struct, hashlib, sys, re
NAMES = "shaders planes lightmaps surfaces drawverts drawidx leafbrushes leafsurfs leafs nodes sideeq brushsides brushes models ents vis lgpal lgoff lgdata spherelights spherevis lightdefs terrain terrainidx smdata smdef smidx dummy".split()
IX = {n: i for i, n in enumerate(NAMES)}
SZ = {"shaders": 140, "planes": 16, "surfaces": 108, "drawverts": 44, "drawidx": 4, "leafbrushes": 4, "leafsurfs": 4, "leafs": 64,
      "nodes": 36, "sideeq": 32, "brushsides": 12, "brushes": 12, "models": 40}
class Bsp:
    def __init__(s, data):
        s.ident, s.ver, s.cksum = struct.unpack_from("<4sii", data, 0)
        assert s.ident == b"2015" and s.ver == 19, (s.ident, s.ver)
        s.table = [struct.unpack_from("<ii", data, 12 + 8 * i) for i in range(28)]
        s.lumps = [bytearray(data[o:o + l]) for o, l in s.table]
        order = sorted((i for i in range(28) if s.table[i][1] > 0), key=lambda i: (s.table[i][0], i))
        s.empty = {}   # zero-length lumps: (anchor lump idx or None, offset delta from that lump's original end)
        for i in range(28):
            if s.table[i][1] == 0:
                cand = [j for j in order if s.table[j][0] + s.table[j][1] <= s.table[i][0]]
                a = max(cand, key=lambda j: s.table[j][0]) if cand else None
                s.empty[i] = (a, s.table[i][0] - (s.table[a][0] + s.table[a][1] if a is not None else 0))
        # gaps: padding bytes preceding each lump (in file order) and the tail
        pos = 236; s.gaps = {}
        for i in order:
            o, l = s.table[i]
            assert o >= pos, ("overlap", NAMES[i])
            s.gaps[i] = bytes(data[pos:o]); pos = o + l
        s.align4 = True; pe = 236
        for i in order:
            if s.gaps[i] != b"\x00" * ((-pe) % 4): s.align4 = False
            pe = s.table[i][0] + s.table[i][1]
        s.order = order; s.tail = bytes(data[pos:])
        s.hdrpad = bytes(data[12 + 8 * 28:236])  # empty normally
    def get(s, n): return s.lumps[IX[n]]
    def count(s, n): return len(s.lumps[IX[n]]) // SZ[n]
    def rec(s, n, i, fmt): return struct.unpack_from(fmt, s.lumps[IX[n]], i * SZ[n])
    def tobytes(s):
        out = bytearray(236); out[0:12] = struct.pack("<4sii", s.ident, s.ver, s.cksum)
        pos = 236; tab = [None] * 28
        for i in s.order:
            g = b"\x00" * ((-pos) % 4) if s.align4 else s.gaps[i]
            out += g; pos += len(g)
            tab[i] = (pos, len(s.lumps[i])); out += s.lumps[i]; pos += len(s.lumps[i])
        out += s.tail
        for i, (a, d) in s.empty.items():
            tab[i] = ((tab[a][0] + tab[a][1] if a is not None else 0) + d, 0)
        for i, (o, l) in enumerate(tab): struct.pack_into("<ii", out, 12 + 8 * i, o, l)
        return bytes(out)
    # --- decoded views --------------------------------------------------------------
    def shaders(s):
        b = s.get("shaders"); out = []
        for i in range(len(b) // 140):
            nm = bytes(b[i*140:i*140+64]).split(b"\0")[0].decode("latin1")
            sf, cf, sub = struct.unpack_from("<3i", b, i*140+64)
            out.append((nm, sf, cf, sub, bytes(b[i*140+76:i*140+140]).split(b"\0")[0].decode("latin1")))
        return out
    def planes(s):
        b = s.get("planes"); return [struct.unpack_from("<4f", b, i*16) for i in range(len(b)//16)]
    def brush(s, i):
        fs, ns, sh = s.rec("brushes", i, "<3i")
        sides = [s.rec("brushsides", fs + k, "<3i") for k in range(ns)]
        return fs, ns, sh, sides
    def models(s):
        b = s.get("models"); return [struct.unpack_from("<6f4i", b, i*40) for i in range(len(b)//40)]
    def surf(s, i): return struct.unpack_from("<3i4i5i3f9f2if".replace("9f", "9f"), s.get("surfaces"), i*108)
    def entities(s):
        t = bytes(s.get("ents")).split(b"\0")[0].decode("latin1")
        return t
def roundtrip(path):
    d = open(path, "rb").read(); b = Bsp(d); o = b.tobytes()
    return o == d, hashlib.sha256(d).hexdigest()[:12], hashlib.sha256(o).hexdigest()[:12], len(d), len(o)
if __name__ == "__main__":
    print(roundtrip(sys.argv[1]))

import itertools
def brush_aabb(b, i, planes=None, eps=0.05):
    """AABB of brush i from plane triples (None if degenerate)."""
    planes = planes or b.planes()
    fs, ns, sh, sides = b.brush(i)
    P = [planes[s[0]] for s in sides]
    pts = []
    for a, c, d in itertools.combinations(range(len(P)), 3):
        n = [P[a][:3], P[c][:3], P[d][:3]]; dd = [P[a][3], P[c][3], P[d][3]]
        det = (n[0][0]*(n[1][1]*n[2][2]-n[1][2]*n[2][1]) - n[0][1]*(n[1][0]*n[2][2]-n[1][2]*n[2][0]) + n[0][2]*(n[1][0]*n[2][1]-n[1][1]*n[2][0]))
        if abs(det) < 1e-6: continue
        def cr(u, v): return (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        c1, c2, c3 = cr(n[1], n[2]), cr(n[2], n[0]), cr(n[0], n[1])
        x = tuple((dd[0]*c1[k] + dd[1]*c2[k] + dd[2]*c3[k]) / det for k in range(3))
        if all(P[k][0]*x[0] + P[k][1]*x[1] + P[k][2]*x[2] - P[k][3] <= eps for k in range(len(P))): pts.append(x)
    if not pts: return None
    return [min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]

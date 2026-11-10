#!/usr/bin/env python3
"""Proof of concept: pull the render geometry out of Frontline Xbox .cpt
level-art chunks (and .msh models) into Wavefront OBJ. Our own code.

What is known (found 2026-11-08, matches the ResHax .msh notes):
  mesh descriptor  = u32 vb_off, u32 ib_off, u16 vcount, u16 icount  (offsets
                     relative to the start of the chunk)
  vertex (28 bytes)= f32 x,y,z | u32 packed normal | u32 BGRA colour (baked
                     light) | f32 u,v
  indices          = u16 triangle strips, stitched with repeated indices
What is NOT known yet: the material/texture binding of each mesh, the chunk
transform (chunks looked to be pre-placed in world space), and the header tree.

Discovery is by validation: every 4-aligned position where a descriptor
decodes to a vertex block followed by an index block whose indices are all
< vcount is accepted. False positives are improbable for vcount>=3.

usage: cpt2obj.py <out.obj> <chunk.cpt|.msh> [...]   (several chunks -> one OBJ)
"""
import struct, sys

VSTRIDE = 28


def find_meshes(d):
    n = len(d)
    out = []
    for p in range(0, n - 12, 4):
        vb, ib, vc, ic = struct.unpack_from("<IIHH", d, p)
        if not (3 <= vc and 3 <= ic and vb % 4 == 0 and vb + vc * VSTRIDE <= ib <= n - ic * 2):
            continue
        if ib - (vb + vc * VSTRIDE) > 16:          # index block follows the vertices
            continue
        idx = struct.unpack_from(f"<{ic}H", d, ib)
        if max(idx) >= vc:
            continue
        x, y, z = struct.unpack_from("<3f", d, vb)
        if not all(abs(t) < 1e5 for t in (x, y, z)):
            continue
        out.append((p, vb, ib, vc, idx))
    return out


def strip_to_tris(idx):
    tris = []
    for i in range(len(idx) - 2):
        a, b, c = idx[i], idx[i + 1], idx[i + 2]
        if a == b or b == c or a == c:
            continue
        tris.append((a, b, c) if i % 2 == 0 else (b, a, c))
    return tris


def main(out, files):
    vbase, nmesh, ntri = 1, 0, 0
    lo, hi = [1e9] * 3, [-1e9] * 3
    with open(out, "w", newline="\n") as o:
        for fn in files:
            d = open(fn, "rb").read()
            for p, vb, ib, vc, idx in find_meshes(d):
                o.write(f"o {fn.replace(chr(92), '/').rsplit('/', 1)[-1]}_{p:x}\n")
                for i in range(vc):
                    x, y, z, _n, col, u, v = struct.unpack_from("<3fII2f", d, vb + i * VSTRIDE)
                    r, g, b = (col >> 16) & 255, (col >> 8) & 255, col & 255
                    o.write(f"v {x:.4f} {z:.4f} {-y:.4f} {r/255:.3f} {g/255:.3f} {b/255:.3f}\n")
                    for k, t in enumerate((x, y, z)):
                        lo[k], hi[k] = min(lo[k], t), max(hi[k], t)
                for i in range(vc):
                    _, _, _, _, _, u, v = struct.unpack_from("<3fII2f", d, vb + i * VSTRIDE)
                    o.write(f"vt {u:.5f} {1 - v:.5f}\n")
                tris = strip_to_tris(idx)
                for a, b, c in tris:
                    o.write(f"f {a+vbase}/{a+vbase} {b+vbase}/{b+vbase} {c+vbase}/{c+vbase}\n")
                vbase += vc
                nmesh += 1
                ntri += len(tris)
    print(f"{nmesh} meshes, {vbase-1} verts, {ntri} tris, bounds {lo} .. {hi}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

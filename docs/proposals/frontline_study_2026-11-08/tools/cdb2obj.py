#!/usr/bin/env python3
"""Proof of concept: Frontline .cdb collision chunk -> OBJ triangle soup.
Our own code. Partially decoded 2026-11-08 (version 7 chunks):

  u32 version(7) | u32 size | u32 nverts | u32 vert_off | u32 ntris | u32 n5 |
  u32 n6 | u32 n7 | u32 0 | u32 tri_off | u32 sec2_off | u32 sec3_off | u32 sec4_off
  verts : nverts x f32[3]                     (world space, metres, Z up)
  tris  : ntris  x {u32 v0,v1,v2 as BYTE OFFSETS into the chunk; f32 unknown}
  sec2..4: plane records (normal, d, flags, -> tri) and what looks like a
           BVH / surface-type table - not needed to get the walls.
usage: cdb2obj.py <out.obj> <chunk.cdb> [...]
"""
import struct, sys


def main(out, files):
    base, ntot = 1, 0
    with open(out, "w", newline="\n") as o:
        for fn in files:
            d = open(fn, "rb").read()
            h = struct.unpack_from("<13I", d, 0)
            if h[0] != 7:
                print("skip (version)", fn, h[0])
                continue
            nv, voff, nt, toff = h[2], h[3], h[4], h[9]
            o.write(f"o {fn.replace(chr(92), '/').rsplit('/', 1)[-1]}\n")
            for i in range(nv):
                x, y, z = struct.unpack_from("<3f", d, voff + 12 * i)
                o.write(f"v {x:.4f} {z:.4f} {-y:.4f} 0.9 0.4 0.2\n")
            bad = 0
            for i in range(nt):
                a, b, c, _f = struct.unpack_from("<3If", d, toff + 16 * i)
                ia, ib, ic = ((t - voff) // 12 for t in (a, b, c))
                if max(ia, ib, ic) >= nv or min(ia, ib, ic) < 0:
                    bad += 1
                    continue
                o.write(f"f {ia+base} {ib+base} {ic+base}\n")
            base += nv
            ntot += nt - bad
            print(fn, nv, "verts", nt, "tris", bad, "rejected")
    print("total tris", ntot)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

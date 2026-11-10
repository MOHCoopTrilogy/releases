#!/usr/bin/env python3
"""MOH European Assault .cdb (version 17) collision mesh -> triangles / OBJ. Our own code, stdlib only.

Reverse-engineered 2026-11-09 from the user's own Xbox USA disc (Frontline's .cdb is v7 and differs):
  0x00 u32 version(17), u32 size, u32 nverts, u32 vert_off(0x30), u32 ntris,
       u32 tri_off, u32 surf_off, u32 n7, u32 sec8_off, u32 n9, u32 sec10_off, u32 0
  verts: nverts x f32[3]                 (world space, metres, Z up)
  tris : ntris x {u16 a, u16 b, u16 c, u16 flags}
  surf : ntris x 4 bytes                 (surface/material id per triangle; byte0 = 0, then id x3)
  sec8/sec10: tree and plane data (not needed for the brush build)

usage: eacdb.py <out.obj> <file.cdb> [...]
"""
import struct, sys


def read(d):
    h = struct.unpack_from("<12I", d, 0)
    if h[0] != 17:
        raise ValueError(f"cdb version {h[0]} (want 17)")
    nv, voff, nt, toff, soff = h[2], h[3], h[4], h[5], h[6]
    verts = [struct.unpack_from("<3f", d, voff + 12 * i) for i in range(nv)]
    tris, surf = [], []
    for i in range(nt):
        a, b, c, fl = struct.unpack_from("<4H", d, toff + 8 * i)
        if max(a, b, c) >= nv or a == b or b == c or a == c:
            continue
        tris.append((a, b, c))
        surf.append((fl, d[soff + 4 * i + 1]))
    return verts, tris, surf


def main(argv):
    base = 1
    with open(argv[1], "w", newline="\n") as o:
        for fn in argv[2:]:
            v, t, _s = read(open(fn, "rb").read())
            for x, y, z in v:
                o.write(f"v {x:.4f} {z:.4f} {-y:.4f}\n")
            for a, b, c in t:
                o.write(f"f {a + base} {b + base} {c + base}\n")
            base += len(v)
            print(fn, len(v), "verts", len(t), "tris")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

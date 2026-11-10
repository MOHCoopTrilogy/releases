#!/usr/bin/env python3
"""MOH European Assault level-art cell (.cpt v37, EAGL4 'solid') -> meshes / OBJ. Our own code, stdlib only.

Reverse-engineered 2026-11-09 from the user's own Xbox USA disc. Frontline's .cpt is v18 with float
vertices; EA's v37 differs:
  0x00 u32 version(0x25), u32 size, ...; 0x80 an ELF ET_REL header (EM 8, section headers stripped);
  internal pointers = file offset - 0xC0.
  Per static mesh, in file order:
    u32 0x00050000 | ... | +0x10 u32 index count | +0x30 u16 triangle strip
    "Colours\\0"  (C)
      C+0x88 f32[4] position scale (s,s,s,1), typically 1/64
      C+0xA8 f32[3] position origin (world, metres, Z up)
      C+0xB8 f32    UV scale, typically 1/1024
    stream records {u32 tail, u32 size, u32 type, u32 1, u32 self} + data + 0xBBBBBBBB trailer:
      type 6 = int16 x3 positions; then three type-4 streams of the same count:
      UV (int16 x2), colour (BGRA, A=0xFF, baked light), packed normal - told apart by content
    shader name "<Cell>_<n>_<m>_RM = Moh3_Cpt_<shader>"; draw record marked 0xDDDDDDDD.

usage: eacpt.py <out.obj> <cell.cpt> [...]
"""
import re, struct, sys

PB = 0xC0
CONST = struct.pack("<4f", 0.0, 1.0, 2.0, 255.0)


def streams(d):
    out = []
    for m in re.finditer(rb"\x01\x00\x00\x00", d):
        h = m.start() - 12
        if h < 0 or h % 4:
            continue
        a, size, typ, one, b = struct.unpack_from("<5I", d, h)
        if b + PB == h + 20 and typ in (4, 6) and 0 < size < 0x400000:
            out.append((h + 20, size, typ))
    return out


def classify4(blob, n):
    w = struct.unpack_from(f"<{n}I", blob, 0)
    if all((x >> 24) == 0xFF for x in w):
        return "col"
    # UVs: two int16 that are mostly modest; normals: packed bits spread over the full word
    s = struct.unpack_from(f"<{2 * n}h", blob, 0)
    if sum(abs(v) < 20000 for v in s) > 1.8 * n:
        return "uv"
    return "nrm"


def find_index(d, lo, hi):
    """nearest index block before `hi`: u32 0x00050000 at X-0x10, count at X, strip at X+0x20"""
    for x in range(hi - 0x24, max(lo, 0x14), -4):
        if struct.unpack_from("<I", d, x - 0x10)[0] != 0x00050000:
            continue
        c = struct.unpack_from("<I", d, x)[0]
        if 3 <= c < 65536 and x + 0x20 + 2 * c <= hi:
            return x + 0x20, c
    return None


def meshes(d):
    st = streams(d)
    res = []
    for k, (p, size, typ) in enumerate(st):
        if typ != 6:
            continue
        n = size // 6
        # attribute streams follow in a fixed order: UV, [UV2 on Texture2 meshes], colour (BGRA;
        # alpha = layer blend on Texture2), packed normal
        run = []
        for q, s2, t2 in st[k + 1:k + 5]:
            if t2 != 4 or s2 // 4 != n:
                break
            run.append(q)
        names = {4: ("uv", "uv2", "col", "nrm"), 3: ("uv", "col", "nrm"), 2: ("uv", "col"), 1: ("uv",)}
        att = dict(zip(names.get(len(run), ()), run))
        last = (run[-1] + 4 * n) if run else p + size
        # shader constants: f32 [0, 1, 2, 255]; scale at +0x20, origin at +0x40, UV scale at +0x50.
        # (Texture1 meshes tag this block "Colours", Texture2 meshes "NVerts" with an extra matrix.)
        c = d.rfind(CONST, max(0, p - 0x4000), p)
        if c < 0:
            continue
        sc = struct.unpack_from("<4f", d, c + 0x20)
        org = struct.unpack_from("<3f", d, c + 0x40)
        uvs = struct.unpack_from("<f", d, c + 0x50)[0]
        if not (0 < sc[0] < 1 and sc[3] == 1.0):
            continue
        prev = res[-1]["end"] if res else 0
        ib = find_index(d, prev, c)
        if not ib:
            continue
        idx = struct.unpack_from(f"<{ib[1]}H", d, ib[0])
        if max(idx) >= n:
            continue
        sh = re.search(rb"([\w]+_RM) = (Moh3_\w+)", d[last:last + 0x1000])
        pos = [tuple(struct.unpack_from("<3h", d, p + 6 * i)[j] * sc[j] + org[j] for j in range(3)) for i in range(n)]
        uv = [tuple(v * uvs for v in struct.unpack_from("<2h", d, att["uv"] + 4 * i)) for i in range(n)] if "uv" in att else None
        col = [d[att["col"] + 4 * i: att["col"] + 4 * i + 4] for i in range(n)] if "col" in att else None
        uv2 = [tuple(v * uvs for v in struct.unpack_from("<2h", d, att["uv2"] + 4 * i)) for i in range(n)] if "uv2" in att else None
        res.append({"pos": pos, "uv": uv, "uv2": uv2, "col": col, "idx": idx, "end": last,
                    "name": sh.group(1).decode() if sh else "", "shader": sh.group(2).decode() if sh else ""})
    return res


def strip_tris(idx):
    for i in range(len(idx) - 2):
        a, b, c = idx[i], idx[i + 1], idx[i + 2]
        if a == b or b == c or a == c:
            continue
        yield (a, b, c) if i % 2 == 0 else (b, a, c)


def main(argv):
    base, nt, nm = 1, 0, 0
    with open(argv[1], "w", newline="\n") as o:
        for fn in argv[2:]:
            for m in meshes(open(fn, "rb").read()):
                nm += 1
                o.write(f"o {m['name']}\n")
                for i, (x, y, z) in enumerate(m["pos"]):
                    if m["col"]:
                        b, g, r, _a = m["col"][i]
                        o.write(f"v {x:.4f} {z:.4f} {-y:.4f} {min(1, 2 * r / 255):.3f} {min(1, 2 * g / 255):.3f} {min(1, 2 * b / 255):.3f}\n")  # x2: shader const
                    else:
                        o.write(f"v {x:.4f} {z:.4f} {-y:.4f}\n")
                for a, b, c in strip_tris(m["idx"]):
                    o.write(f"f {a + base} {b + base} {c + base}\n")
                    nt += 1
                base += len(m["pos"])
    print(argv[1], nm, "meshes", nt, "tris")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

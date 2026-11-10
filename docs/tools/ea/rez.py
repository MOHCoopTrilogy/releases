#!/usr/bin/env python3
"""MOH European Assault 'BRGR' resource archive (asyncstr.rez) reader. Our own code, stdlib only.

Layout (reverse-engineered 2026-11-09 from the user's own Xbox USA disc):
  0x00 'BRGR', u32 version(1), u32 name-table end
  0x0C codec names, 4 bytes each: 'LZSS', 'RLE ', 'NONE'
  0x18 u32 1, u32 count
  0x20 count x {u32 off, u32 usize, u32 nameinfo, u32 csize}
       nameinfo & 0x7FFFF = name offset relative to 0x18; nameinfo >> 19 = flags (codec)
  names: NUL-terminated build paths (z:/moh4/working/XBOX_US/data/...)

usage:
  rez.py list <file.rez>
  rez.py extract <file.rez> <outdir> [substring]
"""
import os, struct, sys


def lzss(src, usize):
    """EA BRGR LZSS. Flag byte, LSB first, 1 = literal byte. 0 = 2-byte token {lo, hi}:
    off12 = lo | (hi & 0x0F) << 8, length = (hi >> 4) + 3, copy from out[-(4096 - off12)]
    (verified: comp_stream_data.xml decodes to exact usize and well-formed XML)."""
    out = bytearray()
    i, n = 0, len(src)
    bits = flags = 0
    while len(out) < usize and i < n:
        if bits == 0:
            flags = src[i]; i += 1; bits = 8
            continue
        bit = flags & 1; flags >>= 1; bits -= 1
        if bit:
            out.append(src[i]); i += 1
        else:
            if i + 1 >= n:
                break
            lo, hi = src[i], src[i + 1]; i += 2
            p = len(out) - (4096 - (lo | ((hi & 0x0F) << 8)))
            for k in range((hi >> 4) + 3):
                out.append(out[p + k] if p + k >= 0 else 0)
    return bytes(out[:usize])


def entries(data):
    if data[:4] != b"BRGR":
        raise ValueError("not BRGR")
    count = struct.unpack_from("<I", data, 0x1C)[0]
    out = []
    for k in range(count):
        off, usize, ninfo, csize = struct.unpack_from("<IIII", data, 0x20 + 16 * k)
        no = 0x18 + (ninfo & 0x7FFFF)
        name = data[no:data.index(b"\0", no)].decode("latin-1")
        out.append((name, off, usize, csize, ninfo >> 19))
    return out


def payload(data, e, codec_override=None):
    name, off, usize, csize, flags = e
    raw = data[off:off + csize]
    if csize == usize:
        return raw
    return lzss(raw, usize)


def main(argv):
    data = open(argv[2], "rb").read()
    es = entries(data)
    if argv[1] == "list":
        for e in es:
            print(f"{e[0]}\t{e[1]}\t{e[2]}\t{e[3]}\t{e[4]}")
    elif argv[1] == "extract":
        sub = argv[4].lower() if len(argv) > 4 else ""
        for e in es:
            if sub not in e[0].lower():
                continue
            rel = e[0].split("/data/", 1)[-1]
            dst = os.path.join(argv[3], *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as o:
                o.write(payload(data, e))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

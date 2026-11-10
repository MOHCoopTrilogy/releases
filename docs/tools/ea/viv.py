#!/usr/bin/env python3
"""EA BIG/VIV archive TOC reader (BIGF / BIG4 / C0FB). Our own code, stdlib only.

Layouts (public, e.g. wiki.xentax.com "EA BIG", OpenSAGE/ Gibbed docs):
  BIGF/BIG4: magic[4], u32 archive size, u32BE count, u32BE header size,
             then count x { u32BE offset, u32BE size, cstring name }.
  C0FB     : u16BE 0xC0FB, u16BE header size, u16BE count,
             then count x { u24BE offset, u24BE size, cstring name }.
Entries can themselves be RefPack-compressed (first u16 = 0x10FB / 0x11FB);
see refpack.py.
"""
import struct


def parse_toc(buf):
    """buf = archive bytes (at least the header). Returns list of (name, off, size)."""
    out = []
    if buf[:4] in (b"BIGF", b"BIG4", b"BIGH"):
        count, hsize = struct.unpack_from(">II", buf, 8)
        p = 16
        for _ in range(count):
            off, size = struct.unpack_from(">II", buf, p)
            p += 8
            e = buf.index(b"\0", p)
            out.append((buf[p:e].decode("latin-1"), off, size))
            p = e + 1
    elif buf[:4] == b"BIG3":
        # MOH:EA loading.viv: u32LE size, u32BE count, u32BE header size, count x {u24BE off, u24BE size, name}
        count = struct.unpack_from(">I", buf, 8)[0]
        p = 16
        for _ in range(count):
            off = int.from_bytes(buf[p:p + 3], "big")
            size = int.from_bytes(buf[p + 3:p + 6], "big")
            p += 6
            e = buf.index(b"\0", p)
            out.append((buf[p:e].decode("latin-1"), off, size))
            p = e + 1
    elif buf[:2] == b"\xc0\xfb":
        hsize, count = struct.unpack_from(">HH", buf, 2)
        p = 6
        for _ in range(count):
            off = int.from_bytes(buf[p:p + 3], "big")
            size = int.from_bytes(buf[p + 3:p + 6], "big")
            p += 6
            e = buf.index(b"\0", p)
            out.append((buf[p:e].decode("latin-1"), off, size))
            p = e + 1
    else:
        raise ValueError("not a BIG/VIV archive")
    return out


def header_len(head16):
    if head16[:4] in (b"BIGF", b"BIG4", b"BIGH"):
        return struct.unpack_from(">I", head16, 12)[0]
    if head16[:2] == b"\xc0\xfb":
        return struct.unpack_from(">H", head16, 2)[0] + 64
    return 0


if __name__ == "__main__":
    # viv.py <archive> <outdir>   - unpack every member (reads the archive only)
    import os, sys
    data = open(sys.argv[1], "rb").read()
    for name, off, size in parse_toc(data):
        dst = os.path.join(sys.argv[2], name.replace("\\", "/"))
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        with open(dst, "wb") as o:
            o.write(data[off:off + size])
    print("unpacked", sys.argv[1])

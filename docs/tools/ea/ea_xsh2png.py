#!/usr/bin/env python3
"""decode every image in .xsh / .viv(of .xsh) files to PNG (stdlib zlib writer). ea_xsh2png.py <outdir> <file>..."""
import os, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shpx, viv  # noqa: E402

def png(path, w, h, rgba):
    raw = b"".join(b"\0" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw, 9)) + ch(b"IEND", b""))

def blobs(fn):
    d = open(fn, "rb").read()
    if d[:4] == b"SHPX":
        yield os.path.basename(fn), d
    else:
        for name, off, size in viv.parse_toc(d):
            if d[off:off + 4] == b"SHPX":
                yield name.replace("/", "_"), d[off:off + size]

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for fn in sys.argv[2:]:
    tag = os.path.basename(os.path.dirname(fn))
    for name, b in blobs(fn):
        try:
            for k, im in enumerate(shpx.decode(b)):
                w, h, rgba = im["w"], im["h"], im["rgba"]
                if rgba is None:
                    print("type", im["type"], fn, name); continue
                png(os.path.join(out, f"{tag}_{name}_{k}.png"), w, h, rgba)
        except Exception as ex:
            print("fail", fn, name, ex)

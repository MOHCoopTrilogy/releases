#!/usr/bin/env python3
"""EA SHPX (Xbox "shape") texture decoder. Our own code; stdlib only.

Container (EA SSH family, public: wiki.xentax "EA SSH FSH Image"):
  "SHPX" | u32 size | u32 count | char[4] dir id | count x {char[4] name, u32 off}
Image block at off: u8 type | u24 block size (incl. 16-byte header, 0 = last)
                    | u16 w | u16 h | 4 x u16 misc | pixels
Following blocks (attached to the image, located by block size): palette
(type 0x2A / 42: 16-byte header, u16 count, BGRA entries), name (0x70), ...

Pixel types seen on the Frontline Xbox disc (ResHax notes + this disc):
  123 = 8-bit palettised, Morton swizzled
  125 = 32-bit BGRA, Morton swizzled
   96 = DXT1, 97 = DXT3, 98 = DXT5 (Xbox DXT is not swizzled)
Returns (w, h, rgba_bytes) per image.
"""
import struct


def unswizzle_index(x, y, w, h):
    # Xbox linear Morton order, interleave the bits of the smaller dimension
    off, bit, sx, sy = 0, 0, 1, 1
    mw, mh = w, h
    while sx < mw or sy < mh:
        if sx < mw:
            off |= ((x & sx) and 1) << bit
            bit += 1
            sx <<= 1
        if sy < mh:
            off |= ((y & sy) and 1) << bit
            bit += 1
            sy <<= 1
    return off


def morton_table(w, h):
    return [unswizzle_index(x, y, w, h) for y in range(h) for x in range(w)]


def _rgb565(c):
    return (((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31)


def decode_dxt(data, w, h, kind):
    out = bytearray(w * h * 4)
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    step = 8 if kind == 1 else 16
    p = 0
    for by in range(bh):
        for bx in range(bw):
            blk = data[p:p + step]
            p += step
            if len(blk) < step:
                return bytes(out)
            alpha = [255] * 16
            cb = blk
            if kind == 3:
                a = int.from_bytes(blk[:8], "little")
                alpha = [((a >> (4 * i)) & 15) * 17 for i in range(16)]
                cb = blk[8:]
            elif kind == 5:
                a0, a1 = blk[0], blk[1]
                bits = int.from_bytes(blk[2:8], "little")
                tab = [a0, a1] + ([((6 - i) * a0 + (i + 1) * a1) // 7 for i in range(6)] if a0 > a1
                                  else [((4 - i) * a0 + (i + 1) * a1) // 5 for i in range(4)] + [0, 255])
                alpha = [tab[(bits >> (3 * i)) & 7] for i in range(16)]
                cb = blk[8:]
            c0, c1, idx = struct.unpack_from("<HHI", cb, 0)
            r0, r1 = _rgb565(c0), _rgb565(c1)
            if c0 > c1 or kind != 1:
                cols = [r0 + (255,), r1 + (255,),
                        tuple((2 * a + b) // 3 for a, b in zip(r0, r1)) + (255,),
                        tuple((a + 2 * b) // 3 for a, b in zip(r0, r1)) + (255,)]
            else:
                cols = [r0 + (255,), r1 + (255,), tuple((a + b) // 2 for a, b in zip(r0, r1)) + (255,), (0, 0, 0, 0)]
            for i in range(16):
                x, y = bx * 4 + (i & 3), by * 4 + (i >> 2)
                if x < w and y < h:
                    c = cols[(idx >> (2 * i)) & 3]
                    o = 4 * (y * w + x)
                    out[o:o + 4] = bytes((c[0], c[1], c[2], c[3] if kind == 1 else alpha[i]))
    return bytes(out)


def decode(buf, base=0):
    """buf[base:] starts with SHPX. Yields dicts {name, w, h, type, rgba}."""
    assert buf[base:base + 4] == b"SHPX", "not SHPX"
    size, count = struct.unpack_from("<II", buf, base + 4)
    for k in range(count):
        name = buf[base + 16 + 8 * k: base + 20 + 8 * k].decode("latin-1")
        off, = struct.unpack_from("<I", buf, base + 20 + 8 * k)
        p = base + off
        t = buf[p]
        bsz = int.from_bytes(buf[p + 1:p + 4], "little")
        w, h = struct.unpack_from("<HH", buf, p + 4)
        pix = buf[p + 16: p + (bsz if bsz else size - off)]
        # attached blocks
        pal = None
        q = p + bsz if bsz else 0
        while q and q < base + size:
            bt = buf[q]
            bs2 = int.from_bytes(buf[q + 1:q + 4], "little")
            if bt in (0x2A, 0x2D, 0x21, 0x22, 0x23, 0x24):
                n, = struct.unpack_from("<H", buf, q + 4)
                pal = buf[q + 16: q + 16 + 4 * n]
            if not bs2:
                break
            q += bs2
        rgba = None
        if t == 123 and pal:
            tab = morton_table(w, h)
            out = bytearray(w * h * 4)
            for i, s in enumerate(tab):
                if s >= len(pix):
                    continue
                c = pix[s] * 4
                b_, g_, r_, a_ = pal[c:c + 4] if c + 4 <= len(pal) else (0, 0, 0, 255)
                out[4 * i:4 * i + 4] = bytes((r_, g_, b_, a_))
            rgba = bytes(out)
        elif t == 125:
            tab = morton_table(w, h)
            out = bytearray(w * h * 4)
            for i, s in enumerate(tab):
                b_, g_, r_, a_ = pix[4 * s:4 * s + 4]
                out[4 * i:4 * i + 4] = bytes((r_, g_, b_, a_))
            rgba = bytes(out)
        elif t in (96, 97, 98):
            rgba = decode_dxt(pix, w, h, {96: 1, 97: 3, 98: 5}[t])
        yield {"name": name, "w": w, "h": h, "type": t, "rgba": rgba}

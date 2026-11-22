#!/usr/bin/env python3
"""European Assault character light: the level's baked irradiance probes (our own code, stdlib only; run on the
player's own disc, the output stays in the player's own pak).

Decoded 2026-11-17 (code decode, H:/hzm_work/eapolish/cellarlight/DECODE.md; XBE 0x191950 / 0x18f5b0 / 0x1d30d0):
the original lights a character from SH9 irradiance probes, NOT from the world's vertex light. Each
IrradianceVolumeTrigger names a probe set by its VolumeID (record w22); the probes are one level-stream chunk of
type 0xec5d66b5:
  +0x90: 17 x 16 bytes {u32 nodes_off, u16 count, u16 root, u32 flags, f32 scale}   (pointers = chunk offset - 0x20)
  node (0xa0 bytes): f32 x, f32 y (EA ground plane, the eadb record frame), 27 f32 irradiance coefficients
    (coefficient-major k0 RGB .. k8 RGB, Ramamoorthi-Hanrahan rows), +0x84 u32 offset of its triangles (byte
    triples of node indices), +0x88 u32 their count, kd-tree words.
At run time the character's probe is the nodes' barycentric blend over the triangle it stands in (2-D), so the
mean irradiance over the sphere is k0 + k2/3 per channel - a texture multiplier (the default probe is ~0.66).
Local lights (muzzle flashes, grenades) add on top; the cellar lantern has none: its warmth is its probe node."""
import math
import struct

TYPE = 0xec5d66b5


def _chunk(stream):
    n = struct.unpack_from("<I", stream, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(stream):
        cid, typ, sz, _x = struct.unpack_from("<4I", stream, p)
        if sz < 16:
            break
        if typ == TYPE:
            return stream[p:p + sz]
        p += sz
    return None


def volumes(stream):
    """{VolumeID: (nodes [(x, y, mean RGB 0..1)], triangles [(i, j, k)], scale)} in the EA frame (metres)"""
    ch = _chunk(stream)
    if ch is None:
        return {}
    out = {}
    for i in range(17):
        off, cnt, _root, _fl, scale = struct.unpack_from("<IHHIf", ch, 0x90 + 16 * i)
        nodes, tris = [], set()
        for k in range(cnt):
            o = off + 0x20 + 0xa0 * k
            if o + 0xa0 > len(ch):
                break
            f = struct.unpack_from("<29f", ch, o)
            sh = [f[2 + 3 * c:5 + 3 * c] for c in range(9)]
            nodes.append((f[0], f[1], [sh[0][c] + sh[2][c] / 3.0 for c in range(3)]))
            to, tc = struct.unpack_from("<II", ch, o + 0x84)
            for t in range(min(tc, 64)):
                b = to + 0x20 + 3 * t
                tri = tuple(ch[b:b + 3])
                if len(tri) == 3 and max(tri) < cnt:
                    tris.add(tri)
        if nodes:
            out[i] = (nodes, sorted(tris), scale or 1.0)
    return out


def probe_at(vol, x, y):
    """mean irradiance (RGB, texture multiplier) at EA ground point (x, y): the barycentric blend over the triangle
    that holds it (the runtime's 0x1917c0 / 0x1933c0); outside every triangle the nearest triangle's blend with its
    weights clamped to the triangle; one node = that node, two = their lerp by projection"""
    nodes, tris, scale = vol
    if len(nodes) == 1 or not tris:
        if len(nodes) >= 2:
            (ax, ay, ca), (bx, by, cb) = nodes[0], nodes[1]
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ((dx * dx + dy * dy) or 1.0)))
            return [(ca[c] * (1 - t) + cb[c] * t) * scale for c in range(3)]
        return [v * scale for v in nodes[0][2]]
    best = None
    for (i, j, k) in tris:
        (ax, ay, ca), (bx, by, cb), (cx, cy, cc) = nodes[i], nodes[j], nodes[k]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        w1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
        w2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
        w3 = 1.0 - w1 - w2
        out_by = -min(w1, w2, w3, 0.0)
        if best is None or out_by < best[0]:
            ws = [max(0.0, w) for w in (w1, w2, w3)]
            s = sum(ws) or 1.0
            best = (out_by, [w / s for w in ws], (ca, cb, cc))
    _o, ws, cs = best
    return [sum(ws[n] * cs[n][c] for n in range(3)) * scale for c in range(3)]

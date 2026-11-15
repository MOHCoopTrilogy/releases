#!/usr/bin/env python3
"""European Assault character animations, read from a level stream. Our own code, stdlib only; runs on the PLAYER's
PC inside the converter, output only into the player's own converted pak.

Reverse-engineered 2026-11-15 from the user's own Xbox USA disc (1_11 level_a.str + the game's default.xbe):

bank   - chunk type 0x7c5686d5. Pointers inside it are offsets from the chunk start + 0x20 (P). The chunk word at +0x28
         is the clip count n, then n x (u32 clip name hash, u32 offset of the clip record from P), sorted by hash.
types  - every record starts with a type id = eahash("EALA::Character::<Class>") (the engine's own name hash, a
         Jenkins one-at-a-time variant: h = ((c + h) * 0x401), h ^= h >>s 6 per signed char; then h *= 9,
         h ^= h >>s 11, h *= 0x8001; >>s = arithmetic shift). The same hash names the clips, joints and anim states.
AnimationData (clip): +4 u32, +8 f32 duration (s), +12 ptr KeyList, +16 ptr JointList, +20 u32 joints j,
         +24 2 x j ptrs: (rotation channel, translation channel) per joint.
KeyList: +4 u16 count, +6 u16 key frames (30 frames per second; frame 0 first). Every channel holds one value per key.
JointList: +4 u32 count, +8 count x u32 joint name hash (eahash("JO_pelvis") ...).
rotation channels (quaternion x, y, z, w):
  F4Constant   +4 int16 x4 / 32767                                   (one value for the whole clip)
  F4Channel    +4 u16 n, +6 n x int16 x4 / 32767
  F4SingleAxis +4 int16 x3 axis / 32767, +10 u16 n, +12 n x int16 s / 32767: q = (axis * s, sqrt(1 - s*s))
  F4StoreXYZ / XYW / XZW / YZW  +4 u16 x3 scales / 65536, +10 u16 n, +12 n x u32: three stored components
         (bits 22-31: 10 bits, 11-21: 11 bits, 0-10: 11 bits; value = q * 2 / (2^bits - 1) * scale - scale) in the
         order the name gives, the missing one = sqrt(1 - sum of squares); the W-storing variants keep W >= 0
  F4Smallest3  (in the engine, not used by 1_11)
translation channels (x, y, z, metres):
  F3Constant   +4 f32 x3
  F3Channel    +4 3 ptrs to F1 channels: F1Constant (+4 f32), F1Linear (+4 a, +8 b: a + b t), F1Cubic (+4..+16:
               ((a t + b) t + c) t + d), F1Channel (+4 u16 n, +8 n x f32), F1Quant8 / F1Quant16 (+4 f32 base,
               +8 f32 scale, +12 u16 n, +14 n x u8 / u16: base + scale q)
  (t of Linear / Cubic = the sample's time in seconds - TO VERIFY, no 1_11 clip has been checked with them yet)
Values between keys: linear for scalars and vectors, shortest-path slerp for quaternions.
"""
import math
import struct

import eachar

CHUNK_ANIM = 0x7c5686d5
FPS = 30.0


def _sar(x, n):
    x &= 0xffffffff
    if x & 0x80000000:
        x -= 1 << 32
    return (x >> n) & 0xffffffff


def eahash(s):
    h = 0
    for c in (s.encode("latin-1") if isinstance(s, str) else s):
        c = c - 256 if c > 127 else c
        h = ((c + h) * 0x401) & 0xffffffff
        h ^= _sar(h, 6)
    h = (h * 9) & 0xffffffff
    h ^= _sar(h, 11)
    return (h * 0x8001) & 0xffffffff


T = {eahash("EALA::Character::" + n): n for n in (
    "AnimationData KeyList JointList F1Constant F1Linear F1Cubic F1Quant8 F1Quant16 F1Channel F3Channel F3Constant "
    "F4Channel F4Constant F4SingleAxis F4Smallest3 F4StoreXYW F4StoreXYZ F4StoreXZW F4StoreYZW").split()}


class Bank:
    def __init__(self, d):
        for p, cid, typ, sz in eachar._chunks(d):
            if typ == CHUNK_ANIM:
                break
        else:
            raise ValueError("no animation bank in this stream")
        self.d, self.P = d, p + 0x20
        n = struct.unpack_from("<I", d, p + 0x28)[0]
        self.clips = dict(struct.unpack_from("<II", d, p + 0x2c + 8 * i) for i in range(n))

    def _t(self, a):
        return T.get(struct.unpack_from("<I", self.d, a)[0])

    def clip(self, h):
        """{duration, keys, joints: {joint hash: (rot record addr, pos record addr)}}"""
        d, P = self.d, self.P
        a = P + self.clips[h]
        assert self._t(a) == "AnimationData"
        dur = struct.unpack_from("<f", d, a + 8)[0]
        kl, jl, nj = struct.unpack_from("<III", d, a + 12)
        kn = struct.unpack_from("<H", d, P + kl + 4)[0]
        keys = struct.unpack_from("<%dH" % kn, d, P + kl + 6)
        jn = struct.unpack_from("<I", d, P + jl + 4)[0]
        jh = struct.unpack_from("<%dI" % jn, d, P + jl + 8)
        ptr = struct.unpack_from("<%dI" % (2 * nj), d, a + 24)
        return {"duration": dur, "keys": keys,
                "joints": {jh[i]: (P + ptr[2 * i], P + ptr[2 * i + 1]) for i in range(min(nj, jn))}}

    # ---- channel values at key index k ----
    def _scalar(self, a, k, t):
        d = self.d
        ty = self._t(a)
        if ty == "F1Constant":
            return struct.unpack_from("<f", d, a + 4)[0]
        if ty == "F1Linear":
            x, y = struct.unpack_from("<2f", d, a + 4)
            return x + y * t
        if ty == "F1Cubic":
            c3, c2, c1, c0 = struct.unpack_from("<4f", d, a + 4)
            return ((c3 * t + c2) * t + c1) * t + c0
        if ty == "F1Channel":
            return struct.unpack_from("<f", d, a + 8 + 4 * k)[0]
        if ty == "F1Quant8":
            b, s = struct.unpack_from("<2f", d, a + 4)
            return b + s * d[a + 14 + k]
        if ty == "F1Quant16":
            b, s = struct.unpack_from("<2f", d, a + 4)
            return b + s * struct.unpack_from("<H", d, a + 14 + 2 * k)[0]
        raise ValueError("scalar channel %r" % ty)

    def pos(self, a, k, t=0.0):
        ty = self._t(a)
        if ty == "F3Constant":
            return struct.unpack_from("<3f", self.d, a + 4)
        if ty == "F3Channel":
            return tuple(self._scalar(self.P + q, k, t) for q in struct.unpack_from("<3I", self.d, a + 4))
        raise ValueError("translation channel %r" % ty)

    def rot(self, a, k):
        d = self.d
        ty = self._t(a)
        if ty == "F4Constant":
            return tuple(v / 32767.0 for v in struct.unpack_from("<4h", d, a + 4))
        if ty == "F4Channel":
            return tuple(v / 32767.0 for v in struct.unpack_from("<4h", d, a + 6 + 8 * k))
        if ty == "F4SingleAxis":
            ax = [v / 32767.0 for v in struct.unpack_from("<3h", d, a + 4)]
            s = struct.unpack_from("<h", d, a + 12 + 2 * k)[0] / 32767.0
            return (ax[0] * s, ax[1] * s, ax[2] * s, math.sqrt(max(0.0, 1.0 - s * s)))
        if ty in ("F4StoreXYZ", "F4StoreXYW", "F4StoreXZW", "F4StoreYZW"):
            sc = [v / 65536.0 for v in struct.unpack_from("<3H", d, a + 4)]
            u = struct.unpack_from("<I", d, a + 12 + 4 * k)[0]
            f = ((u >> 22) & 0x3ff) * 2.0 / 1023.0 * sc[0] - sc[0]
            g = ((u >> 11) & 0x7ff) * 2.0 / 2047.0 * sc[1] - sc[1]
            h = (u & 0x7ff) * 2.0 / 2047.0 * sc[2] - sc[2]
            m = math.sqrt(max(0.0, 1.0 - f * f - g * g - h * h))
            if ty == "F4StoreXYZ":
                return (f, g, h, m)
            q = {"F4StoreXYW": (f, g, m, h), "F4StoreXZW": (f, m, g, h), "F4StoreYZW": (m, f, g, h)}[ty]
            return tuple(-v for v in q) if q[3] < 0 else q
        raise ValueError("rotation channel %r" % ty)

    def sample(self, clip, time):
        """{joint hash: (quaternion x y z w, translation)} at time (s), keys interpolated"""
        keys = clip["keys"]
        fr = time * FPS
        i = 0
        while i + 1 < len(keys) and keys[i + 1] <= fr:
            i += 1
        j = min(i + 1, len(keys) - 1)
        f = 0.0 if j == i or keys[j] == keys[i] else max(0.0, min(1.0, (fr - keys[i]) / float(keys[j] - keys[i])))
        out = {}
        for jh, (ra, pa) in clip["joints"].items():
            q = slerp(self.rot(ra, i), self.rot(ra, j), f)
            p0, p1 = self.pos(pa, i, time), self.pos(pa, j, time)
            out[jh] = (q, tuple(p0[c] + (p1[c] - p0[c]) * f for c in range(3)))
        return out


def slerp(a, b, t):
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0:
        b, dot = tuple(-x for x in b), -dot
    if dot > 0.9995:
        q = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(min(1.0, dot))
        s = math.sin(th)
        wa, wb = math.sin((1 - t) * th) / s, math.sin(t * th) / s
        q = tuple(wa * x + wb * y for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in q)) or 1.0
    return tuple(x / n for x in q)


def qmat(q):
    """3x3 rotation matrix (rows) of quaternion (x, y, z, w), column-vector convention: v' = M v"""
    x, y, z, w = q
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]

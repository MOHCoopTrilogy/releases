#!/usr/bin/env python3
"""Frontline (Xbox) audio extraction for the BYO converter. Our own code.

Decoding is done by vgmstream-cli built locally from source (ISC licence,
https://github.com/vgmstream/vgmstream, pilot built at commit
6802153425adde134e49394fc653455166d7d2f2). This module only cuts the
containers apart so vgmstream can read them, and reads the subtitle text.

.abk (Frontline Xbox, magic "AB\\x09\\0"): an EA AudioBank whose sample data is
  a standard little-endian "BNKl" bank (version 4/5) somewhere inside. vgmstream
  reads the BNKl directly. Each BNK entry's PT header carries an "SMUL" block:
    "SMUL" u32 size, u32 nlang(5), u32 a, u32 b, u32 off[nlang]  (EN offset = 0)
    then NUL-terminated strings: EN, ES, IT, FR, DE at those offsets.
  An empty EN string means the line is not subtitled in English (e.g. German
  speech in the English release).
main.mus: concatenated EA SCHl streams (SCHl..SCEl); each is cut into its own
  .asf so vgmstream decodes it (same recipe as the PS3 musx work, FEATURES.md).
"""
import os
import struct
import subprocess
import wave

LANGS = ("en", "es", "it", "fr", "de")


def bnk_entries(abk):
    """-> (bnk_bytes, [ {stream: 1-based vgmstream index, subs: {lang: text}} ])"""
    o = abk.find(b"BNKl")
    if o < 0:
        return None, []
    bnk = abk[o:]
    ver = bnk[4]
    n = struct.unpack_from("<H", bnk, 6)[0]
    table = 0x0C if ver == 2 else 0x14
    heads = []
    for i in range(n):
        eo = table + 4 * i
        rel = struct.unpack_from("<I", bnk, eo)[0]
        if rel:
            heads.append(eo + rel)
    out = []
    for k, h in enumerate(heads):
        nxt = heads[k + 1] if k + 1 < len(heads) else min(len(bnk), h + 0x800)
        lim = min(nxt, h + 0x800) if nxt > h else h + 0x800
        s = bnk.find(b"SMUL", h, lim)
        subs = {}
        if s >= 0:
            size, nl = struct.unpack_from("<II", bnk, s + 4)
            if 1 <= nl <= 8:
                offs = struct.unpack_from(f"<{nl}I", bnk, s + 12 + 8)
                base = s + 12 + 8 + 4 * nl
                for li, lo in enumerate(offs):
                    e = bnk.find(b"\0", base + lo, s + size)
                    if e < 0:
                        e = s + size
                    txt = bnk[base + lo:e].decode("latin-1").strip()
                    if li < len(LANGS) and txt:
                        subs[LANGS[li]] = txt
        out.append({"stream": k + 1, "subs": subs})
    return bnk, out


def split_schl(data):
    """Cut a concatenation of EA SCHl streams into separate stream byte strings."""
    out, p, start = [], 0, None
    while p + 8 <= len(data):
        tag = data[p:p + 4]
        size = struct.unpack_from("<I", data, p + 4)[0]
        if tag == b"SCHl":
            start = p
        if size < 8 or p + size > len(data):
            break
        p += size
        if tag == b"SCEl" and start is not None:
            out.append(data[start:p])
            start = None
            nxt = data.find(b"SCHl", p)      # streams are padded/aligned between each other
            if nxt < 0:
                break
            p = nxt
    return out


def music_map(mpf):
    """Frontline's per-level music map (<level>M.mpf, EA PathFinder 'xDFP' version 3) -> the order the level's
    music segments play in: {"order": [seg, ...], "loop": i, "alt": [[seg, ...], ...]} with 0-based segment
    numbers into the level's .mus (in stream order) and `loop` the index in `order` the walk returns to
    (None = it ends).  `alt` are the other sections (started by a game event, e.g. the mission's end).

    Layout (little endian): 'xDFP', u8 version (3) ... u16 node count at 0x12, u16 node offsets (in 4-byte units)
    from 0x24.  A node is 12 bytes - u16 sample (0 = a section's entry, 0xffff = end, else 1-based segment),
    u8 branch count at +5 - then 4 bytes per branch (u8 lo, u8 hi, u16 next node).  The walk takes a node's
    first branch that leads to a node."""
    if mpf[:4] != b"xDFP" or mpf[4] != 3:
        return None
    n = struct.unpack_from("<H", mpf, 0x12)[0]
    offs = [4 * o for o in struct.unpack_from(f"<{n}H", mpf, 0x24)]
    nodes = []
    for o in offs:
        if o + 12 > len(mpf):
            return None
        sample = struct.unpack_from("<H", mpf, o)[0]
        nb = mpf[o + 5]
        nxt = [struct.unpack_from("<H", mpf, o + 12 + 4 * k + 2)[0] for k in range(nb) if o + 16 + 4 * k <= len(mpf)]
        nodes.append((sample, [t for t in nxt if t < n]))
    walks = []
    for i, (sample, _) in enumerate(nodes):
        if sample != 0:
            continue
        order, seen, loop, cur = [], {}, None, i
        while True:
            sample, nxt = nodes[cur]
            if sample == 0xFFFF:
                break
            if cur in seen:
                loop = seen[cur]
                break
            if sample:
                seen[cur] = len(order)
                order.append(sample - 1)
            elif cur != i:
                break
            if not nxt:
                break
            cur = nxt[0]
        if order:
            walks.append((order, loop))
    if not walks:
        return None
    return {"order": walks[0][0], "loop": walks[0][1], "alt": [w[0] for w in walks[1:]]}


def vgm_decode(vgm, src, dst, stream=None):
    args = [vgm, "-o", dst]
    if stream:
        args += ["-s", str(stream)]
    args.append(src)
    r = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
    return r.returncode == 0 and os.path.exists(dst)


def wav_seconds(path):
    with wave.open(path) as w:
        return w.getnframes() / float(w.getframerate())

#!/usr/bin/env python3
"""European Assault scripted voice lines: cue -> speech stream. Our own code; runs on the PLAYER's PC, output local.

Decoded 2026-11-10 (user's own Xbox USA disc, 1_11):
  - a scripted line's cue key (strings.viv, e.g. 10285_RUP#2_DefendChurch) has the UBER event id CRC32(key);
  - SOUND/Audio.ubr ('UBER') holds per event a record  ... u32 INDEX, u32 0x80000000, u32 event id, u32 0xfd0fb324,
    u32 event id ...  - INDEX is the event's line in SOUND/str.ast;
  - str.ast is a BIG4 archive (big-endian count at +8, entries {u32 off, u32 size} BE + name\\0 from +16) of SCHl
    streams (EA MicroTalk), one per line, in that order. Member names are a hash we do not need.
vgmstream (already bundled for the music) decodes a member to WAV.
"""
import re
import struct
import zlib


def ubr_index(ubr):
    """{event id: str.ast member index}"""
    out = {}
    for m in re.finditer(re.escape(struct.pack("<I", 0xFD0FB324)), ubr):
        o = m.start()
        if o < 12:
            continue
        idx, flag, ev = struct.unpack_from("<III", ubr, o - 12)
        ev2 = struct.unpack_from("<I", ubr, o + 4)[0]
        if flag == 0x80000000 and ev == ev2 and idx < 100000:
            out[ev] = idx
    return out


def ast_members(ast):
    cnt = struct.unpack_from(">I", ast, 8)[0]
    o, ents = 16, []
    for _i in range(cnt):
        off, sz = struct.unpack_from(">II", ast, o)
        o += 8
        e = ast.find(b"\0", o)
        ents.append((off, sz, ast[o:e].decode("latin-1")))
        o = e + 1
    return ents


def lines(ubr, ast, keys):
    """{cue key: SCHl bytes} for the cue keys whose event the UBER maps"""
    idx = ubr_index(ubr)
    ents = ast_members(ast)
    out = {}
    for k in keys:
        ev = int(k[1:], 16) if k.startswith("#") else zlib.crc32(k.encode()) & 0xffffffff
        i = idx.get(ev)
        if i is None or i >= len(ents):
            continue
        off, sz, _nm = ents[i]
        if sz > 0 and ast[off:off + 4] == b"SCHl":
            out[k] = ast[off:off + sz]
    return out

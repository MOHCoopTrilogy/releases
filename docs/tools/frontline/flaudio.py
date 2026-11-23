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


def wav_mono(path):
    """[discbot 2026-11-16] the client refuses stereo WAVs for sound effects ("is a stereo wav file", "Couldn't load
    sound"), and the ambience beds are played as loopsounds: average the channels to one, 16-bit PCM kept"""
    import wave, array, io
    with wave.open(path, "rb") as w:
        ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if ch == 1 or sw != 2:
        return open(path, "rb").read()
    a = array.array("h", raw)
    m = array.array("h", ((a[i] + a[i + 1]) // 2 for i in range(0, len(a) - 1, 2)))
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(m.tobytes())
    return out.getvalue()


def wav_seconds(path):
    with wave.open(path) as w:
        return w.getnframes() / float(w.getframerate())


# ---- [flfix2 round 17] ambience beds and positional loops ----------------------------------------------------
# Decoded 2026-11-13 on the user's disc (TRACE_ambience.md). <l>STRBNK.ABK is a header-only AudioBank whose sounds
# are streamed from <l>STRBNK.AST: a count-prefixed run of refs 0xC000|k, then one 12-byte entry per ref
# {u32 type, u32 intro offset, u32 loop offset} into the .AST (EA "streamed looped": an intro segment, then the
# loop body). AmbienceTrigger's argument n is ref 0xC000|n. Positional sounds go through the level's
# <l>propSnd.som ("SOMI"): table A {u16 sound set, u16 sub, u16 sound id, u16 index into table B}, table B
# 14 bytes {u8 first, u8 last, u16 bank code, u16 pitch lo, u16 pitch hi, u16 volume (32767 = 1), u16 flags, u16}.
# A record's link of category 11 names its sound set; PLAYSOUND(id) picks the set's row. Bank code low nibble =
# which run of 0x4000|slot refs in the bank's .ABK header (0-based); first..last index into that run. Evidence:
# the three code-0x72 rows (entries 7, 27, 30) land exactly on 11SCRBNK's three loop-flagged samples.

def _ref_runs(hdr, tag):
    """count-prefixed runs of u32 refs whose high nibble of 16 bits is `tag` (4 = BNK slot, 0xC = streamed)"""
    runs, i = [], 0
    while i + 8 <= len(hdr):
        c = struct.unpack_from("<I", hdr, i)[0]
        if 0 < c < 512 and i + 4 + 4 * c <= len(hdr):
            v = struct.unpack_from(f"<{c}I", hdr, i + 4)
            if all(x >> 12 == tag for x in v) and len(set(v)) == c:
                runs.append((i, [x & 0xFFF for x in v]))
                i += 4 + 4 * c
                continue
        i += 4
    return runs


def ast_loops(abk):
    """<l>STRBNK.ABK -> [(intro_offset, loop_offset)] per streamed sound, in ref order (bed n = entry n)"""
    runs = _ref_runs(abk, 0xC)
    if not runs:
        return []
    at, refs = runs[0]
    base = at + 4 + 4 * len(refs)
    out = []
    for k in range(len(refs)):
        _t, intro, loop = struct.unpack_from("<III", abk, base + 12 * k)
        out.append((intro, loop))
    return out


def schl_at(data, off):
    """the one SCHl..SCEl stream starting at `off`"""
    s = split_schl(data[off:])
    return s[0] if s else None


def som_sound(som, sound_set, sound_id, sub=None):
    """-> {first, last, code, volume (0..1), flags} of a sound set's PLAYSOUND id, or None.
    [anvil 2026-11-23] A set can hold several rows for one id, told apart by the second key word = the record's
    category-12 link (1_3 Alarm_ParentScript set 449 id 57: sub 786 -> an empty bank slot, sub 991 -> the alarm bell
    the emulator plays). sub=None keeps the first row (the converter's behaviour so far)."""
    if som[:4] != b"SOMI":
        return None
    na, nb, oa, ob = struct.unpack_from("<4I", som, 0x10)
    for i in range(na):
        key, _sub, sid, bi = struct.unpack_from("<4H", som, oa + 8 * i)
        if key == sound_set and sid == sound_id and bi < nb and (sub is None or _sub == sub):
            lo, hi, code, _p0, _p1, vol, fl, _z = struct.unpack_from("<BBHHHHHH", som, ob + 14 * bi)
            return {"first": lo, "last": hi, "code": code, "volume": vol / 32767.0, "flags": fl}
    return None


def bank_stream(abk, code, entry):
    """bank code + entry (som_sound) -> 1-based vgmstream stream index into the .ABK's BNKl, or None"""
    o = abk.find(b"BNKl")
    if o < 0:
        return None
    runs = _ref_runs(abk[:o], 0x4)
    g = code & 0x0F
    if g >= len(runs) or entry >= len(runs[g][1]):
        return None
    slot = runs[g][1][entry]
    bnk = abk[o:]
    n = struct.unpack_from("<H", bnk, 6)[0]
    table = 0x0C if bnk[4] == 2 else 0x14
    live = [i for i in range(n) if struct.unpack_from("<I", bnk, table + 4 * i)[0]]
    return live.index(slot) + 1 if slot in live else None

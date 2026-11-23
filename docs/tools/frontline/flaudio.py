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


# ---- [decodeaudit 2026-11-23] AEMS module graphs of an .ABK header (gap 5 barks, gap 11 vehicle bank) ----
# Header word [0x10] -> module descriptors, 0x1c bytes {u16 sub, u16 ?, u32 objects (root included), u32 EventSystem
# module index, u32 object offset, ...}, running up to the first object list. Object {u32 id, u8 type, u8 sub,
# u16 nout, u32 link}; link block = nout x (u32 ptr, u32 count) then the targets (port << 16 | node); objects follow
# the root (node 0) in link-chain order (each link block starts where the previous one ended). Same reading as
# codedecode tools/fl_aemsobj.py, which documents the node types.

def aems_modules(abk):
    H = abk[:abk.find(b"BNKl")]
    t = struct.unpack_from("<I", H, 0x10)[0]
    out, end = [], len(H)
    while t + 0x1C <= end:
        sub, _u, nobj, mi, oo = struct.unpack_from("<HHIII", H, t)
        if not (0 < nobj < 4096 and 0x40 <= oo < len(H)):
            break
        out.append({"sub": sub, "objects": nobj, "module": mi, "off": oo})
        end = min(end, oo)
        t += 0x1C
    return out


def _link_end(H, link, n):
    if n == 0:
        return link + 4
    pairs = struct.unpack_from("<%dI" % (2 * n), H, link)
    return link + 8 * n + 4 * sum(pairs[1::2])


def aems_graph(abk, module):
    """-> {node: {id, type, inl, out: [[(port, node)..] per output]}} of the module with EventSystem index `module`"""
    H = abk[:abk.find(b"BNKl")]
    md = [m for m in aems_modules(abk) if m["module"] == module]
    if not md:
        return {}
    root = md[0]["off"]
    _i, _t, _s, rn, rl = struct.unpack_from("<IBBHI", H, root)
    objs, nxt, o = [], _link_end(H, rl, rn), root + 12
    while o < len(H) - 12 and len(objs) < md[0]["objects"] - 1:
        oid, t, s, n, link = struct.unpack_from("<IBBHI", H, o)
        if (0x40 < oid < 0x10000 or oid == 0) and 0 < t < 0x40 and n < 64 and nxt <= link <= nxt + 8 \
                and link < len(H) and link % 4 == 0:
            objs.append((o, oid, t, s, n, link))
            nxt = _link_end(H, link, n)
            o += 12
        else:
            o += 4
    g = {}
    for k, (o, oid, t, s, n, link) in enumerate(objs):
        end = objs[k + 1][0] if k + 1 < len(objs) else o + 12
        inl = struct.unpack_from("<%di" % max(0, (end - o - 12) // 4), H, o + 12)
        pairs = struct.unpack_from("<%dI" % (2 * n), H, link) if n else ()
        outs, p = [], link + 8 * n
        for c in pairs[1::2]:
            outs.append([(x >> 16, x & 0xFFFF) for x in struct.unpack_from("<%dI" % c, H, p)])
            p += 4 * c
        g[k + 1] = {"id": oid, "type": (t, s), "inl": inl, "out": outs}
    return g


def aems_set_slots(abk, node):
    """BNK slots of a 04.0b sample-set node"""
    H = abk[:abk.find(b"BNKl")]
    p, c = struct.unpack_from("<II", H, node["inl"][0])
    return [x & 0xFFF for x in struct.unpack_from("<%dI" % c, H, p)]


def aems_table(abk, node):
    """a 1e.01 lookup node -> {index: value} over its whole input range lo..hi (n entries spread evenly over it:
    the 11VehBnk gates hold 128 entries for 0..255)"""
    H = abk[:abk.find(b"BNKl")]
    to, n, lo, hi, es = node["inl"][:5]
    vals = list(H[to:to + n]) if es == 1 else list(struct.unpack_from("<%dh" % n, H, to))
    span = hi - lo + 1
    if span == n or span > 4096:
        return {lo + i: v for i, v in enumerate(vals)}
    return {lo + x: vals[min(n - 1, x * n // span)] for x in range(span)}


def bark_slots(abk, module=15, event_param=0x968, events=range(1, 11)):
    """[decodeaudit 2026-11-23, gap 5] the AI bark module of an 11LOAD bank (EventSystem module 15; sent by the soldier
    classes' voice behaviour 2, L0040: AEMSEVENT block {15, event, speaker type, GETSOUNDINFO(0,2), (1,2), 0}).
    Param 0x968 = the event (1..10) picks, per voice family, a sample index range inside the family's sample set:
    a 09.xx selector node whose input 0 is the event (directly or through a 1e.01 table) and whose inputs 1..n are
    08.01 random-range nodes (lo, hi); the selector feeds port 6 (sample index) of the set. The family order is the
    5-way switch on the speaker-type class (0x969 -> table [1,1,1,1,2,2,2,3,4,3,5,5,5]): family 0 = German speakers,
    family 1 = American. -> {family: {event: [BNK slots]}} (slots that are empty in the BNK are kept; the caller
    drops them)."""
    g = aems_graph(abk, module)
    if not g:
        return {}
    feeds = {}                                              # (node, port) -> [source node]
    for k, nd in g.items():
        for outs in nd["out"]:
            for port, dst in outs:
                feeds.setdefault((dst, port), []).append(k)
    sets = [k for k, nd in g.items() if nd["type"] == (4, 0x0B)]
    pnode = [k for k, nd in g.items() if nd["id"] == event_param and nd["type"] == (1, 0)]
    if not pnode:
        return {}
    pnode = pnode[0]
    # family order: the switch (type 0a.xx) whose outputs reach the sets' port 7
    sw = [k for k, nd in g.items() if nd["type"][0] == 0x0A]
    order = []
    if sw:
        for outs in g[sw[0]]["out"]:
            for port, dst in outs:
                if port == 7 and dst in sets:
                    order.append(dst)
    res = {}
    for fam, sk in enumerate(order):
        base = aems_set_slots(abk, g[sk])
        sel = [s for s in feeds.get((sk, 6), []) if g[s]["type"][0] == 0x09]
        if not sel:
            continue
        sel = sel[0]
        src0 = feeds.get((sel, 0), [])
        if pnode in src0:
            pick = {e: e for e in events}
        else:
            tabs = [s for s in src0 if g[s]["type"] == (0x1E, 1) and pnode in feeds.get((s, 0), [])]
            if not tabs:
                continue
            tb = aems_table(abk, g[tabs[0]])
            pick = {e: tb.get(e, 0) for e in events}
        ranges = {}
        for port in range(1, 16):
            rn = [s for s in feeds.get((sel, port), []) if g[s]["type"] == (8, 1)]
            if rn:
                lo, hi = g[rn[0]]["inl"][:2]
                ranges[port] = (lo, hi)
        fam_res = {}
        for e in events:
            r = ranges.get(pick[e])
            if r:
                fam_res[e] = [base[i] for i in range(r[0], r[1] + 1) if i < len(base)]
        res[fam] = fam_res
    return res


def bnk_live_streams(abk):
    """BNK slot -> 1-based vgmstream stream index (live slots only)"""
    bnk = abk[abk.find(b"BNKl"):]
    n = struct.unpack_from("<H", bnk, 6)[0]
    table = 0x0C if bnk[4] == 2 else 0x14
    live = [i for i in range(n) if struct.unpack_from("<I", bnk, table + 4 * i)[0]]
    return {s: k + 1 for k, s in enumerate(live)}


def vehicle_loops(abk, vtype, module=16, speed_param=0x12E2, type_param=0x1CB9):
    """[decodeaudit 2026-11-23, gap 11] the engine loops of a vehicle bank (11VehBnk, EventSystem module 16). The
    vehicle classes send AEMSEVENT {16, GETSOUNDINFO(3,5), (1,5), (0,5), 32000, 0, type} while the engine runs
    (HierobjVehicle behaviour 1: start on event 209 state 1 = the path is taken, stop at state 2 = death);
    type = behaviour-1 m4: HierobjVehicle 2, GunVehicle 3, TankVehicle 1. Param 0x1cb9 (type) -> a 1e.01 table ->
    port 6 (sample index) of each set; param 0x12e2 (0..255, the running level the engine feeds) -> 1e.01 gate tables
    -> port 7 (on / off): the set on at level 0 and off at 255 is the idle loop (1_1: on 0..11), the one off at 0 and
    on at 255 the drive loop (on from 4). The two remaining sets are one-shots fired when the level crosses a band (gear changes); not taken.
    -> {"idle": slot, "drive": slot} (BNK slots; None where the type's slot is empty)"""
    g = aems_graph(abk, module)
    if not g:
        return {}
    feeds = {}
    for k, nd in g.items():
        for outs in nd["out"]:
            for port, dst in outs:
                feeds.setdefault((dst, port), []).append(k)
    pid = {nd["id"]: k for k, nd in g.items() if nd["type"] == (1, 0)}
    live = bnk_live_streams(abk)
    out = {}
    for sk, nd in g.items():
        if nd["type"] != (4, 0x0B):
            continue
        gate = [s for s in feeds.get((sk, 7), []) if g[s]["type"] == (0x1E, 1) and pid.get(speed_param) in feeds.get((s, 0), [])]
        tsel = [s for s in feeds.get((sk, 6), []) if g[s]["type"] == (0x1E, 1) and pid.get(type_param) in feeds.get((s, 0), [])]
        if not gate or not tsel:
            continue
        gt = aems_table(abk, g[gate[0]])
        idx = aems_table(abk, g[tsel[0]]).get(vtype)
        base = aems_set_slots(abk, nd)
        slot = base[idx] if idx is not None and idx < len(base) else None
        kind = "idle" if gt.get(0) and not gt.get(255) else ("drive" if gt.get(255) and not gt.get(0) else None)
        if kind:
            out[kind] = slot if slot in live else None
    return out

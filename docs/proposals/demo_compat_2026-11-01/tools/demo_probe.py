"""demo_probe.py - read a MOHAA/OpenMOHAA protocol-17 client demo (.dm_17) offline.

Prints the gamestate (serverinfo, model configstrings) and, for every snapshot, the
model + frameInfo anim indices of each entity. Built to answer "which anim numbers
does this old demo carry?" without starting the game.

Ports (same names as the engine, code/qcommon/msg.cpp + code/client/cl_parse.cpp):
  MSG_ReadBits (Huffman byte stream + raw sub-byte bits), MSG_ReadScrambledBigString,
  CL_ParseGamestate, CL_ParseSnapshot, CL_ParsePacketEntities, MSG_ReadDeltaEntity,
  MSG_ReadDeltaPlayerstate. The netfield tables and NetByteToStrChar are regex-read
  from msg.cpp at run time, so they track the engine instead of a copy.

Only the bit COUNT of each field matters for staying in sync; values are kept as the
raw packed ints except the few we use (modelindex, frameInfo[].index, eType, number).

usage: python demo_probe.py <demo.dm_17> [--engine <openmohaa-hzm root>] [--json out.json]
"""
import argparse, json, os, re, struct, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "_research", "assetaudit"))
import q3huffman  # noqa: E402

GENTITYNUM_BITS = 12
MAX_GENTITIES = 1 << GENTITYNUM_BITS
FLOAT_INT_BITS = 13
SOUND_ENTNUM_BITS = GENTITYNUM_BITS + 1
SOUND_INDEX_BITS = 11
CS_MODELS = 32
MAX_MODELS = 2048
SVC = dict(bad=0, nop=1, gamestate=2, configstring=3, baseline=4, serverCommand=5,
           download=6, snapshot=7, centerprint=8, locprint=9, cgameMessage=10, EOF=11)


class Overflow(Exception):
    pass


# ---------------------------------------------------------------- engine tables
def load_tables(engine):
    src = open(os.path.join(engine, "code", "qcommon", "msg.cpp"), encoding="latin-1").read()

    def fields(name, macro):
        body = re.search(name + r"\[\]\s*=\s*\{(.*?)\n\};", src, re.S).group(1)
        out = []
        for m in re.finditer(macro + r"\(([^)]*\)?)\)\s*,\s*([-\w]+)\s*,\s*netFieldType_t::(\w+)", body):
            bits = m.group(2)
            bits = GENTITYNUM_BITS if bits == "GENTITYNUM_BITS" else int(bits)
            out.append((m.group(1), bits, m.group(3)))
        return out

    ent = fields("entityStateFields_ver_15", "NETF")
    ps = fields("playerStateFields_ver_15", "PSF")
    body = re.search(r"NetByteToStrChar\[256\]\s*=\s*\{(.*?)\};", src, re.S).group(1)
    body = re.sub(r"//[^\n]*", "", body)
    tbl = [int(x, 0) for x in re.findall(r"0x[0-9a-fA-F]+|\d+", body)]
    assert len(tbl) == 256, len(tbl)
    return ent, ps, tbl


# ---------------------------------------------------------------- bit reader
class Msg:
    def __init__(self, data, codec):
        self.d = data + b"\0\0\0\0"
        self.nbits = len(data) * 8
        self.bit = 0
        self.sym, self.len = codec._sym, codec._len
        self.mask = (1 << codec.max_len) - 1

    def raw_bit(self):
        b = (self.d[self.bit >> 3] >> (self.bit & 7)) & 1
        self.bit += 1
        return b

    def huff_byte(self):
        p = self.bit
        if p >= self.nbits:
            raise Overflow()
        b = p >> 3
        w = (self.d[b] | (self.d[b + 1] << 8) | (self.d[b + 2] << 16) | (self.d[b + 3] << 24)) >> (p & 7)
        i = w & self.mask
        s = self.sym[i]
        if s < 0 or s > 255:
            raise Overflow()
        self.bit += self.len[i]
        if self.bit > self.nbits:
            raise Overflow()
        return s

    def bits(self, n):
        sgn = n < 0
        n = abs(n)
        v = 0
        nb = n & 7
        if nb:
            if self.bit + nb > self.nbits:
                raise Overflow()
            for i in range(nb):
                v |= self.raw_bit() << i
            n -= nb
        for i in range(0, n, 8):
            v |= self.huff_byte() << (i + nb)
        if sgn:  # MSG_ReadNegateValue_ver_15
            v = ~(v >> 1) if v & 1 else v >> 1
        return v

    def byte(self):
        return self.bits(8) & 0xFF

    def short(self):
        v = self.bits(16) & 0xFFFF
        return v - 0x10000 if v & 0x8000 else v

    def long(self):
        v = self.bits(32) & 0xFFFFFFFF
        return v - (1 << 32) if v & 0x80000000 else v

    def float(self):
        return struct.unpack("<f", struct.pack("<I", self.bits(32) & 0xFFFFFFFF))[0]


def read_sstring(m, tbl):
    out = []
    while len(out) < 8191:
        c = tbl[m.byte()]
        if not c:
            break
        out.append("." if c == 37 else chr(c))
    return "".join(out)


# ---------------------------------------------------------------- field readers
def read_regular(m, bits):
    if bits == 0:
        if not m.bits(1):
            return 0
        if not m.bits(1):
            return m.bits(-FLOAT_INT_BITS)
        return m.bits(32)
    return m.bits(bits) if m.bits(1) else 0


def read_field(m, bits, typ, old):
    if typ == "regular":
        return read_regular(m, bits)
    if typ == "angle":
        return m.bits(abs(bits))
    if typ == "animTime":
        return m.bits(bits) if m.bits(1) else old
    if typ in ("animWeight", "scale", "alpha"):
        return m.bits(bits)
    if typ in ("coord", "coordExtra"):  # MSG_ReadDeltaCoord(Extra), on the packed value
        full, small = (16, 8) if typ == "coord" else (18, 10)
        if not m.bits(1):
            return m.bits(full)
        v = m.bits(small)
        d = (v >> 1) + 1
        return old + (-d if v & 1 else d)
    if typ == "velocity":
        return m.bits(17)
    if typ == "simple":
        return m.bits(bits) if m.bits(1) else old
    raise ValueError("field type " + typ)


def null_state(ent_fields):
    st = {f[0]: 0 for f in ent_fields}
    for k in ("bone_tag[0]", "bone_tag[1]", "bone_tag[2]", "bone_tag[3]", "bone_tag[4]"):
        st[k] = -1
    st["parent"] = MAX_GENTITIES - 2
    return st


def read_delta_entity(m, frm, number, ent_fields):
    if m.bits(1) == 1:
        return None  # removed
    to = dict(frm)
    to["number"] = number
    if m.bits(1) == 0:
        return to
    lc = m.byte()
    if lc > len(ent_fields):
        raise ValueError("lc %d > %d" % (lc, len(ent_fields)))
    for i in range(lc):
        name, bits, typ = ent_fields[i]
        if m.bits(1):
            to[name] = read_field(m, bits, typ, frm.get(name, 0))
    return to


def read_delta_ps(m, frm, ps_fields):
    to = dict(frm)
    lc = m.byte()
    for i in range(lc):
        name, bits, typ = ps_fields[i]
        if m.bits(1):
            to[name] = read_field(m, bits, typ, frm.get(name, 0))
    if m.bits(1):
        if m.bits(1):
            b = m.long()
            for i in range(32):
                if b & (1 << i):
                    m.short()
        for width in (8, 16, 16, 16):  # items(byte) ammo_amount ammo_name max_ammo (shorts)
            if m.bits(1):
                b = m.byte() if width == 8 else m.short()
                for i in range(width):
                    if b & (1 << i):
                        m.short()
    return to


# ---------------------------------------------------------------- demo walk
def probe(path, engine, max_snaps=None, samples=None):
    ent_fields, ps_fields, tbl = load_tables(engine)
    codec = q3huffman.get_codec(os.path.join(engine, "code"))
    raw = open(path, "rb").read()
    pos = 0
    cs = {}
    baselines = {}
    snaps = {}  # messageNum -> (ps, {num: state})
    report = dict(file=os.path.basename(path), snapshots=0, bad=0, ents=defaultdict(lambda: defaultdict(int)),
                  first_time=None, last_time=None, servercmds=[])
    frametime = 0.05
    while pos + 8 <= len(raw):
        seq, ln = struct.unpack_from("<iI", raw, pos)
        pos += 8
        if ln == 0xFFFFFFFF or pos + ln > len(raw):
            break
        m = Msg(raw[pos:pos + ln], codec)
        pos += ln
        try:
            m.long()  # reliableAcknowledge
            while True:
                cmd = m.byte()
                if cmd == SVC["EOF"]:
                    break
                if cmd == SVC["nop"]:
                    continue
                if cmd == SVC["serverCommand"]:
                    m.long()
                    s = read_sstring(m, tbl)
                    if len(report["servercmds"]) < 40:
                        report["servercmds"].append(s[:160])
                elif cmd == SVC["gamestate"]:
                    m.long()
                    while True:
                        c = m.byte()
                        if c == SVC["EOF"]:
                            break
                        if c == SVC["configstring"]:
                            i = m.short()
                            cs[i] = read_sstring(m, tbl)
                        elif c == SVC["baseline"]:
                            n = (m.bits(GENTITYNUM_BITS) - 1) % MAX_GENTITIES
                            st = read_delta_entity(m, null_state(ent_fields), n, ent_fields)
                            if st:
                                baselines[n] = st
                        else:
                            raise ValueError("gamestate cmd %d" % c)
                    m.long(); m.long()
                    frametime = m.float()
                elif cmd == SVC["snapshot"]:
                    t = m.long(); m.byte()
                    dn = m.byte(); m.byte()
                    old = snaps.get(seq - dn) if dn else None
                    if dn and old is None:
                        report["bad"] += 1
                        break  # cannot follow this delta; skip the rest of the message
                    al = m.byte()
                    for _ in range(al):
                        m.byte()
                    ps = read_delta_ps(m, old[0] if old else {}, ps_fields)
                    oldents = old[1] if old else {}
                    ents = {}
                    olds = sorted(oldents)
                    oi = 0
                    while True:
                        nn = (m.bits(GENTITYNUM_BITS) - 1) % MAX_GENTITIES
                        if nn == MAX_GENTITIES - 1:
                            break
                        while oi < len(olds) and olds[oi] < nn:
                            ents[olds[oi]] = oldents[olds[oi]]; oi += 1
                        if oi < len(olds) and olds[oi] == nn:
                            st = read_delta_entity(m, oldents[nn], nn, ent_fields); oi += 1
                        else:
                            base = baselines.get(nn) or null_state(ent_fields)
                            st = read_delta_entity(m, base, nn, ent_fields)
                        if st:
                            ents[nn] = st
                    while oi < len(olds):
                        ents[olds[oi]] = oldents[olds[oi]]; oi += 1
                    snaps[seq] = (ps, ents)
                    for k in [k for k in snaps if k < seq - 40]:
                        del snaps[k]
                    report["snapshots"] += 1
                    report["first_time"] = report["first_time"] or t
                    report["last_time"] = t
                    if samples is not None and report["snapshots"] % 20 == 0:
                        for st in ents.values():
                            mdl = cs.get(CS_MODELS + st.get("modelindex", 0), "")
                            if "player/" in mdl or "human/" in mdl:
                                samples.append(dict(t=t, n=st["number"], model=mdl, ef=st.get("eFlags", 0),
                                    vel=[st.get("pos.trDelta[%d]" % k, 0) for k in range(3)],
                                    org=[st.get("netorigin[%d]" % k, 0) for k in range(3)],
                                    fi=[(f, st.get("frameInfo[%d].index" % f, 0), st.get("frameInfo[%d].weight" % f, 0))
                                        for f in range(16) if st.get("frameInfo[%d].weight" % f, 0)],
                                    aw=st.get("actionWeight", 0)))
                    for st in ents.values():
                        mi = st.get("modelindex", 0)
                        if not mi:
                            continue
                        model = cs.get(CS_MODELS + mi, "?%d" % mi)
                        for f in range(16):
                            k = "frameInfo[%d].index" % f
                            w = st.get("frameInfo[%d].weight" % f, 0)
                            if k in st and (w or f == 0):
                                report["ents"][model][st[k]] += 1
                    break  # the rest (sounds, cgame messages) is not needed
                else:
                    break  # centerprint / locprint / cgameMessage: stop, nothing needed after
        except Overflow:
            report["bad"] += 1
        if max_snaps and report["snapshots"] >= max_snaps:
            break
    report["configstrings"] = cs
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("demo")
    ap.add_argument("--engine", default=os.path.join(REPO, "openmohaa-hzm"))
    ap.add_argument("--json")
    ap.add_argument("--max", type=int)
    ap.add_argument("--samples")
    a = ap.parse_args()
    smp = [] if a.samples else None
    r = probe(a.demo, a.engine, a.max, smp)
    if a.samples:
        json.dump(smp, open(a.samples, "w"))
    cs = r["configstrings"]
    print("file", r["file"], "snapshots", r["snapshots"], "unparsed", r["bad"],
          "time %s..%s" % (r["first_time"], r["last_time"]))
    print("serverinfo:", cs.get(0, "")[:600])
    for model, hist in sorted(r["ents"].items(), key=lambda kv: -sum(kv[1].values())):
        if not model.lower().endswith(".tik"):
            continue
        top = sorted(hist.items(), key=lambda kv: -kv[1])[:12]
        print("%-48s %s" % (model[:48], " ".join("%d:%d" % kv for kv in top)))
    if a.json:
        out = dict(r)
        out["ents"] = {k: dict(v) for k, v in r["ents"].items()}
        json.dump(out, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()

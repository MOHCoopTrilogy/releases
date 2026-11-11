#!/usr/bin/env python3
"""European Assault smart-object meshes (.sob: the railgun, radio tower, bridge, gates, tombstones, crates ...) from
level_a.str. Our own code, stdlib only; runs on the PLAYER's PC inside the converter, output stays local.

Reverse-engineered 2026-11-10 on the user's own Xbox USA disc (1_11):
  - a smart object's mesh chunk (type 0x4215C... 1108745932) holds one ELF per art part (_Art_0, _Art_1 ...): the
    chunk header lists, from 0x50, the 32-bit ids of the parts' symbol objects;
  - the level's RTC chunk ('RTC\\0' at +0x20; entries {id, off, size} from +0x38) holds one stripped-ELF tail per
    part (.shstrtab/.strtab/.symtab/.rel.data + section headers, eartc's layout): symbols __Model:::<part>,
    __BBOX:::<part> (f32 min[3], max[3], local metres), __VB:::__GPvb_16..19 (positions, uv, colour, normal),
    __RM:::__GP_RM_<part>_<n>, and R_MIPS_32 relocations to the __EAGL::TAR texture shapes (as in a .cpt cell);
  - positions are int16 x3 normalised to the box: local = centre + (v + 16384) / 8192 * half-extent;
  - index strips: u32 0x00040000 at X-0x10, count at X, u16 strip at X+0x20 (the .cpt rule with 4 for 5).
.data of each ELF starts at ELF+0x40; symbol values are .data offsets.
"""
import re
import struct

import eacpt

RTC_TYPE_MARK = b"RTC\0"
# smart objects the mission changes (blown up / opened): inline brush models, the rest is world geometry
DYNAMIC = {"SMA_RailGun6", "SMA_RadioTower5", "XD_Rus1_ammo_dump", "SMA_WoodBridge6", "SP_R1_LeftHandGate",
           "SP_R1_RightHandGate"}


def chunks(d):
    n = struct.unpack_from("<I", d, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(d):
        cid, typ, sz, x = struct.unpack_from("<4I", d, p)
        if sz < 16:
            break
        yield p, typ, d[p:p + sz]
        p += sz


class Store:
    def __init__(self, stream):
        self.objs = {}
        self.models = {}        # part name -> (chunk bytes, elf offset, symbols, relocs)
        rtc = None
        mesh_chunks = []
        for p, typ, c in chunks(stream):
            if c[0x20:0x24] == RTC_TYPE_MARK:
                rtc = c
            elif c.find(b"\x7fELF", 0, 0x400) == 0x120:
                mesh_chunks.append(c)
        if rtc is None:
            return
        o = 0x38
        while o + 12 <= len(rtc):
            h, off, sz = struct.unpack_from("<3I", rtc, o)
            if not (0 < sz < 0x100000 and 0x20 + off + sz <= len(rtc)):
                break
            if self.objs and off < max(v[0] for v in self.objs.values()):
                break
            self.objs[h] = (off, sz)
            o += 12
        self.rtc = rtc
        for c in mesh_chunks:
            elfs = [m.start() for m in re.finditer(b"\x7fELF", c)]
            ids = [h for h in struct.unpack_from("<%dI" % ((0x120 - 0x50) // 4), c, 0x50) if h in self.objs]
            for e, h in zip(elfs, ids):
                syms, rel = self._object(c, e, h)
                if not syms:
                    continue
                part = next((s[0][10:] for s in syms if s[0].startswith("__Model:::")), None)
                if part:
                    self.models[part] = (c, e, syms, rel)

    def _object(self, c, e, h):
        off, sz = self.objs[h]
        ob = self.rtc[0x20 + off:0x20 + off + sz]
        shnum, = struct.unpack_from("<H", c, e + 0x30)
        shstrndx, = struct.unpack_from("<H", c, e + 0x32)
        base = next((b for b in range(0, len(ob) - 80, 4)
                     if ob[b:b + 40] == bytes(40) and struct.unpack_from("<3I", ob, b + 40) == (1, 1, 3)), None)
        if base is None or shnum == 0:
            return None, None
        sh = [struct.unpack_from("<10I", ob, base + 40 * k) for k in range(shnum)]
        try:
            delta = sh[shstrndx][4] - ob.index(b"\0.data\0")
        except (ValueError, IndexError):
            return None, None

        def sec(k):
            s = sh[k]
            return ob[s[4] - delta:s[4] - delta + s[5]]
        symk = next((k for k, s in enumerate(sh) if s[1] == 2), None)
        relk = next((k for k, s in enumerate(sh) if s[1] == 9), None)
        if symk is None:
            return None, None
        tab, st = sec(symk), sec(sh[symk][6])
        syms = []
        for i in range(0, len(tab) - 15, 16):
            nm, val, size, info, other, shndx = struct.unpack_from("<IIIBBH", tab, i)
            end = st.find(b"\0", nm)
            syms.append((st[nm:end].decode("latin-1"), val, size, shndx))
        rel = []
        if relk is not None:
            t = sec(relk)
            rel = sorted((struct.unpack_from("<I", t, i)[0], struct.unpack_from("<I", t, i + 4)[0] >> 8)
                         for i in range(0, len(t) - 7, 8))
        return syms, rel

    def parts(self, sob):
        """the art parts of a smart object, by .sob base name (e.g. SMA_RailGun6): intact only (no _D)"""
        return sorted(p for p in self.models if re.match(re.escape(sob) + r"_Art_\d+$", p))

    def mesh(self, part):
        """{pos (local metres), uv, col, tris, tex} for one art part, or None"""
        c, e, syms, rel = self.models[part]
        data = e + 0x40
        sd = {s[0]: s[1] for s in syms}
        bb = sd.get("__BBOX:::" + part)
        if bb is None:
            return None
        mn = struct.unpack_from("<3f", c, data + bb)
        mx = struct.unpack_from("<3f", c, data + bb + 12)
        if not all(abs(v) < 500 for v in mn + mx) or any(mx[k] < mn[k] for k in range(3)):
            return None
        cen = [(mn[k] + mx[k]) / 2 for k in range(3)]
        half = [(mx[k] - mn[k]) / 2 for k in range(3)]
        out = []
        prev_end = 0
        seg = c[e - 0x80:]
        st = eacpt.streams(seg)
        for k, (p, size, typ) in enumerate(st):
            if typ != 6:
                continue
            n = size // 6
            run = []
            for q, s2, t2 in st[k + 1:k + 5]:
                if t2 != 4 or s2 // 4 != n:
                    break
                run.append(q)
            att = {}
            for q in run:
                kind = eacpt.classify4(seg[q:q + 4 * n], n)
                if kind == "uv" and "uv" in att:
                    kind = "uv2"          # Texture2 meshes: a second UV set before the colour
                att.setdefault(kind, q)
            # an indexed strip (index block between the previous mesh and this one), else the vertices ARE the strip
            ib = None
            for x in range(p - 0x24, max(prev_end, 0x14), -4):
                if struct.unpack_from("<I", seg, x - 0x10)[0] == 0x00040000:
                    cnt = struct.unpack_from("<I", seg, x)[0]
                    if 3 <= cnt < 65536 and x + 0x20 + 2 * cnt <= p:
                        ib = (x + 0x20, cnt)
                        break
            idx = struct.unpack_from("<%dH" % ib[1], seg, ib[0]) if ib else tuple(range(n))
            prev_end = (run[-1] + 4 * n) if run else p + size
            if not idx or max(idx) >= n:
                continue
            pos = []
            for i in range(n):
                v = struct.unpack_from("<3h", seg, p + 6 * i)
                pos.append(tuple(cen[j] + (v[j] + 16384) / 8192.0 * half[j] for j in range(3)))
            uv = [tuple(t / 1024.0 for t in struct.unpack_from("<2h", seg, att["uv"] + 4 * i)) for i in range(n)] \
                if "uv" in att else [(0.0, 0.0)] * n
            col = [seg[att["col"] + 4 * i:att["col"] + 4 * i + 4] for i in range(n)] if "col" in att else None
            last = (run[-1] + 4 * n) if run else p + size
            nm = re.search(rb"([\w]+)_RM = (Moh3_\w+)", seg[last:last + 0x1000])
            out.append({"pos": pos, "uv": uv, "col": col, "tris": list(eacpt.strip_tris(idx)),
                        "tex": self.texture(part, nm.group(1).decode() if nm else None),
                        "shader": nm.group(2).decode() if nm else ""})
        return out

    def texture(self, part, rmname):
        """the texture shape the render model's relocations reference ([its __RM symbol, the next one))"""
        c, e, syms, rel = self.models[part]
        rms = sorted(s[1] for s in syms if s[0].startswith("__RM:::"))
        lo, hi = 0, 1 << 30
        if rmname:
            v = next((s[1] for s in syms if s[0] == "__RM:::__GP_RM_" + rmname), None)
            if v is not None:
                lo = v
                hi = next((x for x in rms if x > v), v + 0x4000)
        for off, si in rel:
            if lo <= off < hi and si < len(syms) and "TAR:::" in syms[si][0]:
                m = re.search(r"SHAPENAME=([^,;]+),(\d+)", syms[si][0])
                if m:
                    return m.group(1)
        return None


def placed(stream, db, skip_classes=(), light=150.0):
    """every smart-object placement of the level as world-space meshes (eacore.meshes() dicts, metres) grouped by
    placement: [(record, sob name, [meshes])]"""
    S = Store(stream)
    out = []
    for r in db.recs:
        if r.cls in skip_classes or r.pos == (0.0, 0.0, 0.0):
            continue
        path = r.s(15) or ""
        if not path.lower().endswith(".sob"):
            continue
        sob0 = path.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
        for sob in (sob0, sob0 + "_D"):
            # the destroyed variant (<sob>_D_Art_n) of the ones the mission blows up, placed with the same transform
            if sob != sob0 and sob0 not in DYNAMIC:
                continue
            out += _placement(S, r, sob, light)
    return out


def _placement(S, r, sob, light):
    out = []
    if True:
        parts = S.parts(sob)
        ms = []
        for part in parts:
            for m in S.mesh(part) or []:
                if not m["tris"]:
                    continue
                cols = [(c[2], c[1], c[0], c[3]) for c in m["col"]] if m["col"] else [(128, 128, 128, 255)] * len(m["pos"])
                cols = [(min(255, 2 * a), min(255, 2 * b), min(255, 2 * cc), d) for a, b, cc, d in cols]
                ms.append({"cell": "sob", "draw": len(ms), "tex": m["tex"], "tex2": None, "shader": m["shader"],
                           "verts": [world(v, r.rot, r.pos) for v in m["pos"]], "cols": cols, "uvs": m["uv"],
                           "uvs2": None, "tris": m["tris"], "sob": sob, "placement": r.name})
        if ms:
            # EA lights smart objects at run time; their vertex colour is only a dark tint (mean ~30, x2 = 60 against
            # the world's baked ~140): unlit they read as black masses (the railgun) - bring each placement to the
            # level's light, keeping its own shading
            allc = [c for m in ms for c in m["cols"]]
            mean = sum(c[0] + c[1] + c[2] for c in allc) / (3.0 * max(1, len(allc)))
            k = light / mean if mean > 1 else 1.0
            for m in ms:
                m["cols"] = [(min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)), c[3])
                             for c in m["cols"]]
            out.append((r, sob, ms))
    return out


def world(pos, rot, at):
    """local (metres) -> world metres with the placement's 3x3 rows and position"""
    r = rot
    return tuple(at[j] + pos[0] * r[0 + j] + pos[1] * r[3 + j] + pos[2] * r[6 + j] for j in range(3))

#!/usr/bin/env python3
"""MOH European Assault entity placements from level_a.str. Our own code, stdlib only.

Reverse-engineered 2026-11-09 (user's own Xbox USA disc):
  level_a.str = header {u32 1, u32 hash, u32 size, u32 size, u32 0, u32 ntypes} + ntypes x {hash, count},
  then chunks {u32 id, u32 type, u32 size (incl. this header), u32 x} back to back to EOF.
  The level object database is the chunk holding 'STRING TABLE START'. Just before that marker sits the
  string index: N x u32 offsets; string i lives at (marker - off[k_marker]) + off[i], where k_marker is the
  index whose string is the marker itself. Records refer to strings by INDEX.
  Placed objects: {u32 name index, u32 class index, u32 record size, f32 rot[3][3], f32 pos[3], ...}
  e.g. JA_NPCSpawnPoint_SQ01_Village_01 / NPCSpawnPoint. Positions are world metres, Z up (the .cpt/.cdb frame).
  String-valued properties (e.g. a smart object's .sob path) are string indices too.

usage: eaents.py <level_a.str>   -> TSV name, class, x, y, z, yaw, rec offset
"""
import math, struct, sys


def chunks(d):
    n = struct.unpack_from("<I", d, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(d):
        cid, typ, sz, x = struct.unpack_from("<4I", d, p)
        if sz < 16:
            break
        yield p, typ, d[p:p + sz]
        p += sz


class ObjectDB:
    def __init__(self, d):
        for p, typ, c in chunks(d):
            st = c.find(b"STRING TABLE START\0")
            if st >= 0:
                break
        else:
            raise ValueError("no object database chunk")
        self.c, self.st, self.chunk_off = c, st, p
        # walk back over the u32 offset table (strictly increasing, ends right before the marker)
        offs = []
        q = st - 4
        while q >= 0:
            v = struct.unpack_from("<I", c, q)[0]
            if offs and v >= offs[-1]:
                break
            offs.append(v)
            q -= 4
        offs.reverse()
        self.tstart = q + 4
        k = next(i for i in range(min(16, len(offs) - 1))
                 if c[st - offs[i] + offs[i + 1]: st - offs[i] + offs[i + 1] + 1] != b"" and
                 c.startswith(b"STRING TABLE START", st - offs[i] + offs[i]))
        self.base = st - offs[k]
        self.offs = offs

    def string(self, i):
        if not (0 <= i < len(self.offs)):
            return None
        o = self.base + self.offs[i]
        # the index offsets drift by a few bytes between pool sections: snap to the start of the string
        # that contains the target (the previous NUL), which is the name the designer typed
        o = self.c.rfind(b"\0", self.st, o + 1) + 1 if o > self.st else o
        e = self.c.find(b"\0", o)
        t = self.c[o:e]
        return t.decode("latin-1") if t and all(32 <= b < 127 for b in t) else None

    def placements(self):
        c, seen = self.c, set()
        for q in range(0, self.tstart - 64, 4):
            a, b, size = struct.unpack_from("<3I", c, q)
            if not (0x30 <= size <= 0x400) or a >= len(self.offs):
                continue
            m = struct.unpack_from("<12f", c, q + 12)
            rows = [m[0:3], m[3:6], m[6:9]]
            if not all(abs(sum(v * v for v in r) - 1.0) < 0.02 for r in rows):
                continue
            name, cls = self.string(a), self.string(b)
            if not name:
                continue
            pos = m[9:12]
            if not all(abs(v) < 5000 for v in pos) or (name, q) in seen:
                continue
            seen.add((name, q))
            yaw = math.degrees(math.atan2(rows[0][1], rows[0][0]))
            yield {"name": name, "class": cls or "", "pos": pos, "yaw": yaw, "rot": rows, "off": q, "size": size}


def main(argv):
    db = ObjectDB(open(argv[1], "rb").read())
    for o in db.placements():
        x, y, z = o["pos"]
        print(f"{o['name']}\t{o['class']}\t{x:.2f}\t{y:.2f}\t{z:.2f}\t{o['yaw']:.0f}\t{o['off']:#x}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

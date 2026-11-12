#!/usr/bin/env python3
"""European Assault level object database (level_a.str), decoded properly. Our own code, stdlib only.

Reverse-engineered 2026-11-10 on the user's own Xbox USA disc (1_11). Replaces the name lookup in eaents.py, which
read the u32 table before 'STRING TABLE START' as a string index and snapped to the nearest string: that gave the
WRONG name for most records (e.g. the railgun's placement came out as a squad marker 140 m away, bug-ea-dbnames).

Layout of the object-DB chunk (the one holding 'STRING TABLE START'):
  header u32[40]: [26] = offset of the record area - 0x20, [27] = record count, [28] = string count
  records back to back: {u32 name, u32 class, u32 size (incl. header), f32 rot[3][3], f32 pos[3], fields...}
    name / class / string-valued fields are INDICES into the string pool (pool order, NUL-separated, from the
    marker 'STRING TABLE START' = string 0). Positions: world metres, Z up (the .cdb frame).
  fields after pos are u32/f32 properties; pointers into the record itself are chunk offsets (record-relative).
Links: there are no object ids. Objects JOIN activation GROUPS (u32 ids 0x29xxxx / 0x2axxxx / 0x2exxxx, plus death
  channels 0x200xx): a sender lists target groups and the message it sends (CRC32 of the message name: Activate,
  Deactivate, ObjectiveSucceeded, Play ...); every object that carries the group id in its membership slot receives it.

Nothing here is EA data; run it on the player's own disc only, and keep its output local.
"""
import struct
import zlib

MSG = {zlib.crc32(s.encode()) & 0xffffffff: s for s in (
    "Activate", "Deactivate", "ObjectiveSucceeded", "Play", "Charge_Set", "CSA_DemoCharge")}
# 0.7.22: further message ids named by their CRC32 (found by a dictionary search over the level file's words): they
# are emitted under these names (was h<crc>) and recognised as messages, but MSG above stays the set the converter
# acts on. Still unnamed: h7cbb21c1 (always sent with Disable) and hbd5a5da6 (sent with Vanish).
NAMES = {zlib.crc32(s.encode()) & 0xffffffff: s for s in (
    "Disable", "Vanish", "ObjectiveAdd", "IncrementCounter", "StartTimer")}

# class -> field index (from the record start, in u32s) of the group the object belongs to; checked on 1_11
MEMBER = {"SquadDefinition": 20, "NPCSpawnPoint": 72, "SmartObject": 19, "TreadedVehicle": 32,
          "WeaponPowerup": 28, "SMA_RailGun6": 21}


def is_group(w):
    """activation group / channel ids: 0x29xxxx, 0x2axxxx, 0x2exxxx (object groups), 0x200xx (death / count
    channels) and the 0x11xxxx-0x1dxxxx ids that sit in the same target lists (other id spaces; harmless when
    nothing we port belongs to them)"""
    h = w >> 12
    return h in (0x291, 0x2a1, 0x2e1) or 0x20000 <= w < 0x21000 or (0x110 <= h <= 0x1df and (w & 0xfff) != 0)


class DB:
    def __init__(self, data):
        for p, c in _chunks(data):
            st = c.find(b"STRING TABLE START\0")
            if st >= 0:
                break
        else:
            raise ValueError("no object database chunk")
        self.c = c
        self.raw = data      # the whole level file (rig event tables live outside the object chunk)
        self.strs = []
        o = st
        while True:
            e = c.find(b"\0", o)
            if e < 0:
                break
            self.strs.append(c[o:e].decode("latin-1"))
            o = e + 1
        h = struct.unpack_from("<40I", c, 0)
        q, n = h[26] + 0x20, h[27]
        self.recs = []
        for i in range(n):
            a, b, sz = struct.unpack_from("<3I", c, q)
            if sz < 60 or sz > 0x10000 or a >= len(self.strs) or b >= len(self.strs):
                raise ValueError("record walk broke at %#x" % q)
            w = struct.unpack_from("<%dI" % (sz // 4), c, q)
            rot = struct.unpack_from("<9f", c, q + 12)
            pos = struct.unpack_from("<3f", c, q + 48)
            self.recs.append(Rec(self, i, q, self.strs[a], self.strs[b], w, rot, pos))
            q += sz
        self.by_name = {}
        for r in self.recs:
            self.by_name.setdefault(r.name, r)
        self.groups = {}
        for r in self.recs:
            for k, x in r.group_fields():
                self.groups.setdefault(x, []).append((r, k))

    def s(self, i):
        return self.strs[i] if 0 <= i < len(self.strs) else None

    def of(self, cls):
        return [r for r in self.recs if r.cls == cls]

    def members(self, g):
        """records that BELONG to group g (by their class's membership slot)"""
        out = []
        for r, k in self.groups.get(g, []):
            if MEMBER.get(r.cls) == k:
                out.append(r)
        return out

    def senders(self, g):
        return [r for r, k in self.groups.get(g, []) if MEMBER.get(r.cls) != k]


class Rec:
    def __init__(self, db, idx, off, name, cls, w, rot, pos):
        self.db, self.idx, self.off, self.name, self.cls, self.w = db, idx, off, name, cls, w
        self.rot, self.pos = rot, pos
        import math
        self.yaw = math.degrees(math.atan2(rot[1], rot[0])) % 360

    def f(self, i):
        return struct.unpack("<f", struct.pack("<I", self.w[i]))[0] if i < len(self.w) else None

    def u(self, i):
        return self.w[i] if i < len(self.w) else None

    def s(self, i):
        return self.db.s(self.w[i]) if i < len(self.w) else None

    def group_fields(self):
        return [(k, x) for k, x in enumerate(self.w[15:], 15) if is_group(x)]

    def group(self):
        k = MEMBER.get(self.cls)
        if k is not None and k < len(self.w) and is_group(self.w[k]):
            return self.w[k]
        return None

    def targets(self):
        """groups this record sends to (every group id except its own membership slot)"""
        k = MEMBER.get(self.cls)
        return [x for j, x in self.group_fields() if j != k]

    def messages(self):
        return [MSG[x] for x in self.w[15:] if x in MSG]

    def strings(self):
        """string-valued fields that look like paths or names (index > 16: small values are counts)"""
        out = []
        for k, x in enumerate(self.w[15:], 15):
            if 16 < x < len(self.db.strs):
                t = self.db.strs[x]
                if len(t) > 3 and (t[0].isalpha() or t[0] in "@Z"):
                    out.append((k, t))
        return out

    def volume(self):
        """trigger shape: (kind, a, b, c ...) the first fields after pos; kind 1 ~ sphere(radius), 2 ~ box"""
        return (self.u(15), self.f(16), self.f(17), self.f(18), self.f(19), self.f(20), self.f(21))

    def npc(self):
        """NPCSpawnPoint: archetype, character definition, weapon (string fields 18, 19, 20)"""
        return {"archetype": self.s(18), "character": self.s(19), "weapon": self.s(20)}

    def death_channels(self):
        return [x for x in self.w[73:] if 0x20000 <= x < 0x21000]


def _chunks(d):
    n = struct.unpack_from("<I", d, 0x14)[0]
    p = 0x18 + 8 * n
    while p + 16 <= len(d):
        cid, typ, sz, x = struct.unpack_from("<4I", d, p)
        if sz < 16:
            break
        yield p, d[p:p + sz]
        p += sz


def team_of(character):
    c = (character or "").lower()
    if "\\german\\" in c or "/german/" in c or "nemesis" in c:
        return "axis"
    if "russian" in c or "partisan" in c or "\\allies\\" in c or "soviet" in c:
        return "allies"
    return None


if __name__ == "__main__":
    import sys
    db = DB(open(sys.argv[1], "rb").read())
    for r in db.recs:
        print(f"{r.idx}\t{r.cls}\t{r.name}\t{r.pos[0]:.2f}\t{r.pos[1]:.2f}\t{r.pos[2]:.2f}\t{r.yaw:.0f}\t"
              f"g={r.group() and hex(r.group())}\tto={[hex(x) for x in r.targets()]}\t{r.messages()}")

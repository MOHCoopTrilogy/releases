#!/usr/bin/env python3
"""Frontline (Xbox) level reader - the core of the BYO converter. Our own code.

Reads one level straight out of the user's disc image (never writes to it) and
returns plain Python data: render meshes with resolved textures, collision
triangles, entity instances and the navpoint graph.

Format notes (decoded 2026-11-08, see docs/proposals/frontline_study_2026-11-08):

.cpt (version 18) art chunk header, u32 words:
  [0]=18 [1]=size [2]=2
  [3],[4]  = S1 offset,count : 128-byte TEXTURE records
  [5],[6]  = S2 offset,count : 128-byte texture records (alias table)
  [7],[8]  = DRAW offset,count : 20-byte {u32 node, u32 0, u32 tex_rec_ptr,
                                         u32 geom_ptr, u32 n}
  The base chunk <l>_ART.cpt only has S1 (shared textures) at [3],[4].
  texture record (u32 words): [25]=w [26]=h [28]=SHPX offset in this chunk
                              (0 = not local) [31]=index (S1: into the BASE
                              chunk's S1; S2: into this chunk's S1)
  geometry at geom_ptr+12: {u32 vb, u32 ib, u16 nv, u16 ni}; 28-byte vertex
  {f32 x,y,z; u32 packed normal; u32 BGRA colour; f32 u,v}; u16 strips.
.cdb (version 7) collision: see collision().
.bpd (version 9) placement: section table at 16: (offset,count) pairs;
  sec1 = navpoints, 24 bytes {f32 x,y,z; u32 ?; u32 packed (low byte = edge
  count); u32 edge-list offset}; sec3 = entity instances, variable records
  {u32 type hash, u32 size, u32, u32, f32 x,y,z,w, ...} with the behaviour
  chain as inline C strings.
"""
import re
import struct

from xdvdfs import XDVDFS
import viv
import shpx

VSTRIDE = 28


class Disc:
    def __init__(self, image_path):
        self.fs = XDVDFS(image_path)
        self.index = {p.upper(): (sz, sec) for p, sz, sec, d in self.fs.walk() if not d}

    def read(self, path):
        sz, sec = self.index[path.upper()]
        return self.fs.read(sec, sz)

    def viv_members(self, path):
        data = self.read(path)
        return {name: data[off:off + size] for name, off, size in viv.parse_toc(data)}


def level_dir(level):
    m = level.split("_")[0]
    return f"DATA/{m}/{level}/"


class Level:
    def __init__(self, disc, level):
        self.level = level
        d = level_dir(level)
        self.files = disc.viv_members(d + "level.viv")
        self.comp = disc.viv_members(d + "comp.viv")
        self.disc = disc
        self._texcache = {}
        base = self.files[f"{level}_ART.cpt"]
        h = struct.unpack_from("<5I", base, 0)
        self.base = base
        self.base_tex = [struct.unpack_from("<32I", base, h[3] + 128 * i) for i in range(h[4])]
        # second shared table (header words 5,6): what a cell's S2 records index (decoded 2026-11-08: 115/115
        # width/height matches). Resolving S2 into the cell's own S1 instead had mis-textured ~10% of the draws.
        h2 = struct.unpack_from("<7I", base, 0)
        self.base_tex2 = [struct.unpack_from("<32I", base, h2[5] + 128 * i) for i in range(h2[6])]
        self.cells = sorted(k for k in self.comp if k.endswith(".cpt"))

    # ---------------- textures ----------------
    def _tex_from(self, chunk_name, buf, rec):
        """Resolve a texture record to a stable key; decode on first use."""
        if rec[28]:
            key = f"{chunk_name}@{rec[28]:x}"
            if key not in self._texcache:
                self._texcache[key] = next(shpx.decode(buf, rec[28]))
            return key
        return None

    def texture(self, key):
        return self._texcache.get(key)

    def resolve_base(self, idx):
        if idx >= len(self.base_tex):
            return None
        return self._tex_from(f"{self.level}_ART.cpt", self.base, self.base_tex[idx])

    # ---------------- render meshes ----------------
    def meshes(self):
        """Yield dict(cell, tex, verts[(x,y,z)], cols[(r,g,b,a)], uvs[(u,v)], tris[(a,b,c)])."""
        for cell in self.cells:
            buf = self.comp[cell]
            h = struct.unpack_from("<14I", buf, 0)
            S1, n1, S2, n2, DR, nd = h[3], h[4], h[5], h[6], h[7], h[8]
            s1 = [struct.unpack_from("<32I", buf, S1 + 128 * i) for i in range(n1)]

            def resolve(ptr):
                rec = struct.unpack_from("<32I", buf, ptr)
                k = self._tex_from(cell, buf, rec)
                if k:
                    return k
                if S1 <= ptr < S1 + 128 * n1:
                    if rec[25] == 0:
                        return None
                    return self.resolve_base(rec[31])
                if S2 <= ptr < S2 + 128 * n2:
                    j = rec[31]
                    if j < len(self.base_tex2):
                        return self._tex_from(f"{self.level}_ART.cpt", self.base, self.base_tex2[j])
                return None

            for i in range(nd):
                node, _z, tptr, gptr, _n = struct.unpack_from("<5I", buf, DR + 20 * i)
                vb, ib, nv, ni = struct.unpack_from("<IIHH", buf, gptr + 12)
                if nv < 3 or ni < 3 or vb + nv * VSTRIDE > len(buf):
                    continue
                verts, cols, uvs = [], [], []
                for k in range(nv):
                    x, y, z, _nrm, col, u, v = struct.unpack_from("<3fII2f", buf, vb + k * VSTRIDE)
                    verts.append((x, y, z))
                    cols.append(((col >> 16) & 255, (col >> 8) & 255, col & 255, (col >> 24) & 255))
                    uvs.append((u, v))
                idx = struct.unpack_from(f"<{ni}H", buf, ib)
                tris = []
                for t in range(ni - 2):
                    a, b, c = idx[t], idx[t + 1], idx[t + 2]
                    if a == b or b == c or a == c or max(a, b, c) >= nv:
                        continue
                    tris.append((a, b, c) if t % 2 == 0 else (b, a, c))
                yield {"cell": cell, "draw": i, "tex": resolve(tptr), "verts": verts,
                       "cols": cols, "uvs": uvs, "tris": tris}

    # ---------------- collision ----------------
    def collision(self):
        """Yield (cell, verts, tris[(a,b,c,f)]) from the .cdb chunks.
        .cdb v7: u32 7, size, nverts, vert_off, ntris, ?, ?, ?, 0, tri_off, ...
        tri = {u32 v0,v1,v2 byte offsets; u32 flags}."""
        for name in sorted(k for k in self.comp if k.endswith(".cdb")):
            d = self.comp[name]
            h = struct.unpack_from("<13I", d, 0)
            if h[0] != 7:
                continue
            nv, voff, nt, toff = h[2], h[3], h[4], h[9]
            verts = [struct.unpack_from("<3f", d, voff + 12 * i) for i in range(nv)]
            tris = []
            for i in range(nt):
                # 4th word = the triangle's flag word (decoded 2026-11-10, flconvert.COLL_*): low 11 bits = surface
                # material, bit 22 = volume (non-solid), bit 23 = special surface
                a, b, c, f = struct.unpack_from("<4I", d, toff + 16 * i)
                ia, ib, ic = ((t - voff) // 12 for t in (a, b, c))
                if 0 <= min(ia, ib, ic) and max(ia, ib, ic) < nv:
                    tris.append((ia, ib, ic, f))
            yield name, verts, tris

    # ---------------- placement ----------------
    def _bpd(self):
        return self.files[f"{self.level}_P.bpd"]

    def bpd_sections(self):
        d = self._bpd()
        return [struct.unpack_from("<2I", d, 16 + 8 * i) for i in range(12)]

    def named_paths(self):
        """[flpolish] .bpd section 0: named paths {id: [(x, y, z), ...]} - the routes Frontline's TankVehicle
        (StartOnPath) and its StayOnPath patrol soldiers follow. Record = u32 id, u32 count, u32 offset of count
        float xyz points in the same file."""
        d = self._bpd()
        off, cnt = self.bpd_sections()[0]
        out = {}
        for i in range(cnt):
            pid, n, o = struct.unpack_from("<3I", d, off + 12 * i)
            if n < 1 or n > 256 or o + 12 * n > len(d):
                continue
            out[pid] = [struct.unpack_from("<3f", d, o + 12 * k) for k in range(n)]
        return out

    def navpoints(self):
        d = self._bpd()
        off, cnt = self.bpd_sections()[1]
        out = []
        for i in range(cnt):
            x, y, z, a, packed, eoff = struct.unpack_from("<3f3I", d, off + 24 * i)
            out.append({"i": i, "pos": (x, y, z), "a": a, "packed": packed, "eoff": eoff})
        return out

    def entities(self):
        d = self._bpd()
        off, cnt = self.bpd_sections()[3]
        p, out = off, []
        for i in range(cnt):
            rid, size = struct.unpack_from("<II", d, p)
            if size < 32 or p + size > len(d):
                break
            body = d[p:p + size]
            x, y, z, w = struct.unpack_from("<4f", body, 16)
            strs = [s.decode() for s in re.findall(rb"[A-Za-z_][A-Za-z0-9_]{3,}(?=\x00)", body)]
            out.append({"i": i, "off": p, "type": rid, "size": size, "pos": (x, y, z),
                        "strs": strs, "raw": body})
            p += size
        return out

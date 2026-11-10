#!/usr/bin/env python3
"""MOH European Assault (Xbox) level reader for the BYO converter. Our own code, stdlib only.

Same interface as flcore.Level (Frontline), so flconvert.py drives both games:
  meshes()    -> dict(cell, draw, tex, verts, cols, uvs, tris)   (tex = texture key or None)
  texture(k)  -> shpx dict {name, w, h, type, rgba}
  collision() -> (name, verts, tris[(a, b, c, flags)])
  navpoints() / entities()

Sources inside DATA/1/<level>/ (reads the disc image in place, never writes it):
  asyncstr.rez  BRGR + LZSS (rez.py): CMPn/<l>_Art_cN.cpt (render, eacpt.py) + .rtc (symbols and
                relocations, eartc.py: mesh -> texture SHAPENAME), CMP0/<l>_C_C0.cdb (collision, eacdb.py)
  level_a.str   EAGL4 resident stream: the SHPX texture blocks, keyed by shape name.
"""
import re
import struct

import rez
import eacpt
import eacdb
import eartc
import shpx
from flcore import Disc  # noqa: F401  (same XDVDFS disc reader)


def level_dir(level):
    return f"DATA/{level.split('_')[0]}/{level}/"


class Level:
    def __init__(self, disc, level):
        self.disc, self.level = disc, level
        d = level_dir(level)
        data = disc.read(d + "asyncstr.rez")
        self.rez = {}
        for e in rez.entries(data):
            key = e[0].split("/data/", 1)[-1].split("/", 2)[-1]       # "CMP0/1_11_Art_c0.cpt"
            self.rez[key] = rez.payload(data, e)
        self.stream = disc.read(d + "level_a.str")
        self._tex = None
        self.cells = sorted((k for k in self.rez if k.endswith(".cpt")),
                            key=lambda k: int(re.search(r"_c(\d+)\.cpt$", k).group(1)))

    # ---------------- textures ----------------
    def _index_textures(self):
        self._tex = {}
        for m in re.finditer(b"SHPX", self.stream):
            o = m.start()
            size, count = struct.unpack_from("<II", self.stream, o + 4)
            if not (16 < size < 16 << 20 and 0 < count < 64):
                continue
            try:
                for im in shpx.decode(self.stream, o):
                    if im["rgba"] is not None:
                        self._tex.setdefault(im["name"], im)
            except (struct.error, IndexError, ValueError):
                continue

    def texture(self, key):
        if self._tex is None:
            self._index_textures()
        return self._tex.get(key.split("#")[0].split("+")[0]) if key else None

    def texture2(self, key):
        """the top layer of a two-layer key 'base+top'"""
        if not key or "+" not in key:
            return None
        if self._tex is None:
            self._index_textures()
        return self._tex.get(key.split("#")[0].split("+")[1])

    @staticmethod
    def hint(key):
        """shader hint for the converter: 'glow' = blended, no depth write (from the EAGL render state)"""
        return key.split("#", 1)[1] if key and "#" in key else None

    # ---------------- render meshes ----------------
    def meshes(self):
        for cell in self.cells:
            cpt = self.rez[cell]
            rtc = self.rez.get(cell[:-4] + ".rtc")
            bind, state = {}, {}
            if rtc:
                c = eartc.Cell(cpt, rtc)
                rms = sorted((v, n[len("__RM:::__GP_RM_"):]) for n, v, s, sh in c.syms if n.startswith("__RM:::__GP_RM_"))
                for i, (v, n) in enumerate(rms):
                    hi = rms[i + 1][0] if i + 1 < len(rms) else v + 0x4000
                    t = c.textures_in(v, hi)
                    if t:
                        bind[n] = t
                    s = c.state_in(v, hi)
                    if s:
                        state[n] = s
            for k, m in enumerate(eacpt.meshes(cpt)):
                name = m["name"][:-3] if m["name"].endswith("_RM") else m["name"]
                shapes = bind.get(name, [])
                tex = shapes[0][0] if shapes else None
                if tex and len(shapes) > 1 and m.get("uv2"):
                    tex = shapes[0][0] + "+" + shapes[1][0]   # two-layer terrain: base + top (vertex-alpha blended)
                st = state.get(name)
                if tex and st and st["blend"] and not st["zwrite"]:
                    tex += "#glow"        # translucent light card (blend, no depth write): drawn blended, not opaque
                cols = [(min(255, 2 * b[2]), min(255, 2 * b[1]), min(255, 2 * b[0]), b[3]) for b in m["col"]]  # x2: shader const if m["col"] else [(255, 255, 255, 255)] * len(m["pos"])
                uvs = m["uv"] or [(0.0, 0.0)] * len(m["pos"])
                yield {"cell": cell, "draw": k, "tex": tex, "tex2": shapes[1][0] if len(shapes) > 1 else None,
                       "shader": m["shader"], "verts": m["pos"], "cols": cols, "uvs": uvs, "uvs2": m.get("uv2"),
                       "tris": list(eacpt.strip_tris(m["idx"]))}

    # ---------------- collision ----------------
    def collision(self):
        for name in sorted(k for k in self.rez if k.endswith(".cdb")):
            verts, tris, surf = eacdb.read(self.rez[name])
            yield name, verts, [(a, b, c, float(s[1])) for (a, b, c), s in zip(tris, surf)]

    # ---------------- placement (entity decode pending; see STUDY.md) ----------------
    def navpoints(self):
        return []

    def entities(self):
        return []

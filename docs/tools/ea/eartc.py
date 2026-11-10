#!/usr/bin/env python3
"""MOH European Assault .rtc reader: the stripped ELF tail of a .cpt cell. Our own code, stdlib only.

Reverse-engineered 2026-11-09 (user's own Xbox USA disc).
.cpt: 0x00 header (... at word 21: object count, then {elf off, elf size} pairs), ELF header at 0x80,
      .data at ELF+0x40 (= file 0xC0), section headers stripped.
.rtc: 'RTC\\0', u32 0x4C, u32 nobj, u32 size, ...; per object {u32 kind, u32 off, u32 end}.
      Object 0 holds .shstrtab, .strtab, .symtab, .rel.data and the section header table (at its end),
      all at "ELF offset - delta", where delta = sh_off(.shstrtab) - rtc offset of .shstrtab.
Relocations in .rel.data are R_MIPS_32 (type 2): the u32 at .data+off points at symbol S.
Texture attribute symbols:  __EAGL::TAR:::moh_tar=g<N>~<shader>_<SHAPE>;SHAPENAME=<SHAPE>,<n>;...
Render models:              __RM:::__GP_RM_<cell>_<a>_<b>

usage: eartc.py <cell.cpt> <cell.rtc>   -> prints per render model the texture shapes it references
"""
import re, struct, sys

SHAPE_RE = re.compile(r"SHAPENAME=([^,;]+),(\d+)")


class Cell:
    def __init__(self, cpt, rtc):
        self.c, self.r = cpt, rtc
        shoff, = struct.unpack_from("<I", cpt, 0x80 + 0x20)
        shnum, = struct.unpack_from("<H", cpt, 0x80 + 0x30)
        shstrndx, = struct.unpack_from("<H", cpt, 0x80 + 0x32)
        obj0_end, = struct.unpack_from("<I", rtc, 0x20)
        # the section header table is the last thing in object 0
        # ...possibly followed by padding: find the null header followed by .data (PROGBITS)
        guess = obj0_end - shnum * 40
        base = next(b for b in range(guess - 0x80, guess + 0x84, 4)
                    if rtc[b:b + 40] == bytes(40) and struct.unpack_from("<3I", rtc, b + 40) == (1, 1, 3))
        self.sh = [struct.unpack_from("<10I", rtc, base + 40 * k) for k in range(shnum)]
        self.delta = self.sh[shstrndx][4] - rtc.index(b"\0.data\0")
        self.syms = self._symbols()
        self.rel = self._relocs()

    def _rtc(self, k):
        s = self.sh[k]
        o = s[4] - self.delta
        return self.r[o:o + s[5]]

    def _symbols(self):
        sym_k = next(k for k, s in enumerate(self.sh) if s[1] == 2)
        tab, strtab = self._rtc(sym_k), self._rtc(self.sh[sym_k][6])
        out = []
        for i in range(0, len(tab), 16):
            nm, val, size, info, other, shndx = struct.unpack_from("<IIIBBH", tab, i)
            e = strtab.find(b"\0", nm)
            out.append((strtab[nm:e].decode("latin-1"), val, size, shndx))
        return out

    def _relocs(self):
        rel_k = next(k for k, s in enumerate(self.sh) if s[1] == 9)
        tab = self._rtc(rel_k)
        return sorted((struct.unpack_from("<I", tab, i)[0], struct.unpack_from("<I", tab, i + 4)[0] >> 8)
                      for i in range(0, len(tab), 8))

    def state_in(self, lo, hi):
        """EAGL render state (GeoPrimState) referenced in [lo, hi): blend / zwrite / alpha test / cull"""
        import bisect
        i = bisect.bisect_left(self.rel, (lo, -1))
        while i < len(self.rel) and self.rel[i][0] < hi:
            name = self.syms[self.rel[i][1]][0]
            if "GeoPrimState:::" in name:
                st = {"blend": "ABM_BLEND" in name or "XBOXEXTOBJ_SetAlphaBlend" in name,
                      "add": "XBO_ADD" in name and "INVCONSTANTALPHA" not in name,
                      "zwrite": "SetZWritesEnable=false" not in name,
                      "atest": "SetAlphaTestEnable=true" in name and "SetAlphaCompareValue=240" in name,
                      "cull": "SetCullEnable=false" not in name}
                return st
            i += 1
        return None

    def textures_in(self, lo, hi):
        """texture shapes referenced by relocations at .data offsets [lo, hi)"""
        import bisect
        i = bisect.bisect_left(self.rel, (lo, -1))
        out = []
        while i < len(self.rel) and self.rel[i][0] < hi:
            name = self.syms[self.rel[i][1]][0]
            m = SHAPE_RE.search(name) if "TAR:::" in name else None
            if m and (m.group(1), int(m.group(2))) not in out:
                out.append((m.group(1), int(m.group(2))))
            i += 1
        return out


def main(argv):
    c = Cell(open(argv[1], "rb").read(), open(argv[2], "rb").read())
    print(len(c.syms), "symbols", len(c.rel), "relocs")
    for name, val, size, shndx in c.syms:
        if name.startswith("__RM:::"):
            print(name[7:], hex(val), size, c.textures_in(val, val + max(size, 4)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

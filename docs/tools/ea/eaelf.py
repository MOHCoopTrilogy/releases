#!/usr/bin/env python3
"""ELF32 (little-endian) reader for EAGL4 objects embedded in MOH:EA .cpt / .rtc / level_a.str.
Our own code, stdlib only. ELF is a public format (System V gABI).

EA .cpt v37: 0x80-byte header (u32 version 0x25, u32 size, section table), then an ELF ET_REL
object whose symbols name the render models (e.g. '<Name>_RM'), shaders and texture refs.

usage:
  eaelf.py scan <file>              -> offsets of every embedded ELF
  eaelf.py sections <file> [elfoff] -> section table
  eaelf.py symbols <file> [elfoff]  -> symbol table (value, size, section, name)
"""
import struct, sys


class Elf:
    def __init__(self, data, base=0):
        if data[base:base + 4] != b"\x7fELF":
            raise ValueError("no ELF at 0x%x" % base)
        self.d, self.b = data, base
        (self.type, self.machine, _, self.entry, self.phoff, self.shoff, self.flags, _,
         _, _, self.shentsize, self.shnum, self.shstrndx) = struct.unpack_from(
            "<HHIIIIIHHHHHH", data, base + 16)
        self.sh = []
        for k in range(self.shnum):
            self.sh.append(struct.unpack_from("<IIIIIIIIII", data, base + self.shoff + k * self.shentsize))
        so = self.sh[self.shstrndx][4] if self.shnum else 0
        self.names = [self._cstr(base + so + s[0]) for s in self.sh]

    def _cstr(self, o):
        e = self.d.index(b"\0", o)
        return self.d[o:e].decode("latin-1")

    def section(self, k):
        s = self.sh[k]
        return self.d[self.b + s[4]: self.b + s[4] + s[5]]

    def symbols(self):
        for k, s in enumerate(self.sh):
            if s[1] != 2:  # SHT_SYMTAB
                continue
            strtab = self.b + self.sh[s[6]][4]
            tab = self.section(k)
            for i in range(0, len(tab), 16):
                name, value, size, info, other, shndx = struct.unpack_from("<IIIBBH", tab, i)
                yield self._cstr(strtab + name), value, size, info, shndx

    def relocs(self):
        """yield (target_section, offset, symbol_index, type) for every SHT_REL entry."""
        for k, s in enumerate(self.sh):
            if s[1] != 9:  # SHT_REL
                continue
            tab = self.section(k)
            for i in range(0, len(tab), 8):
                off, info = struct.unpack_from("<II", tab, i)
                yield s[7], off, info >> 8, info & 0xFF


def scan(data):
    o = data.find(b"\x7fELF\x01\x01\x01")
    while o >= 0:
        yield o
        o = data.find(b"\x7fELF\x01\x01\x01", o + 4)


def main(argv):
    data = open(argv[2], "rb").read()
    if argv[1] == "scan":
        for o in scan(data):
            try:
                e = Elf(data, o)
                print(f"0x{o:08x}\tshnum={e.shnum}\t{','.join(e.names[:12])}")
            except Exception as ex:  # noqa: BLE001
                print(f"0x{o:08x}\tbad {ex}")
        return 0
    base = int(argv[3], 0) if len(argv) > 3 else next(scan(data))
    e = Elf(data, base)
    if argv[1] == "sections":
        for k, s in enumerate(e.sh):
            print(f"{k}\t{e.names[k]}\ttype={s[1]}\toff=0x{s[4]:x}\tsize={s[5]}\tlink={s[6]}\tinfo={s[7]}")
    elif argv[1] == "symbols":
        for name, value, size, info, shndx in e.symbols():
            print(f"0x{value:08x}\t{size}\t{shndx}\t{info:02x}\t{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

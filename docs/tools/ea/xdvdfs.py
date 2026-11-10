#!/usr/bin/env python3
"""Read-only XDVDFS (Xbox disc filesystem) reader. Our own code, stdlib only.

Handles both a bare XISO and a full Redump image (video partition + game
partition); the game partition is found by probing the known XGD offsets for
the "MICROSOFT*XBOX*MEDIA" volume descriptor at partition+0x10000.

Format reference (public): xboxdevwiki.net/XDVDFS.
  volume descriptor @ sector 32: magic[20], root_sector u32, root_size u32,
  filetime u64, ..., magic again @ +0x7EC.
  dirent: u16 left (dwords), u16 right (dwords), u32 sector, u32 size,
          u8 attrib, u8 namelen, name[namelen], pad to 4 bytes.
  Entries never straddle a 2048-byte sector; 0xFF fills the gap.

usage:
  xdvdfs.py list    <image>                 -> TSV path,size,sector,dir
  xdvdfs.py extract <image> <outdir> [glob]  -> copy files out (never writes the image)
"""
import fnmatch, os, struct, sys

SECTOR = 2048
MAGIC = b"MICROSOFT*XBOX*MEDIA"
PART_OFFSETS = [0, 0x18300000, 0xFD90000, 0x2080000]  # XISO, XGD1, XGD2, XGD3


class XDVDFS:
    def __init__(self, path):
        self.f = open(path, "rb")  # read-only
        self.base = None
        for off in PART_OFFSETS:
            self.f.seek(off + 32 * SECTOR)
            if self.f.read(20) == MAGIC:
                self.base = off
                break
        if self.base is None:
            raise ValueError("no XDVDFS volume descriptor found")
        self.f.seek(self.base + 32 * SECTOR + 20)
        self.root_sector, self.root_size = struct.unpack("<II", self.f.read(8))

    def read(self, sector, size):
        self.f.seek(self.base + sector * SECTOR)
        return self.f.read(size)

    def walk(self, sector=None, size=None, prefix=""):
        if sector is None:
            sector, size = self.root_sector, self.root_size
        if size == 0:
            return
        data = self.read(sector, size)
        seen = set()
        stack = [0]
        while stack:
            off = stack.pop()
            if off in seen or off + 14 > len(data):
                continue
            seen.add(off)
            left, right, sec, sz, attr, nlen = struct.unpack_from("<HHIIBB", data, off)
            if left == 0xFFFF and right == 0xFFFF and sec == 0xFFFFFFFF:
                continue
            name = data[off + 14: off + 14 + nlen].decode("latin-1")
            path = prefix + name
            if attr & 0x10:
                yield path + "/", sz, sec, True
                yield from self.walk(sec, sz, path + "/")
            else:
                yield path, sz, sec, False
            if left not in (0, 0xFFFF):
                stack.append(left * 4)
            if right not in (0, 0xFFFF):
                stack.append(right * 4)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    fs = XDVDFS(argv[2])
    if argv[1] == "list":
        print(f"# partition_base=0x{fs.base:X}", file=sys.stderr)
        print("path\tsize\tsector\tis_dir")
        for p, sz, sec, d in sorted(fs.walk()):
            print(f"{p}\t{sz}\t{sec}\t{int(d)}")
    elif argv[1] == "extract":
        out, pat = argv[3], (argv[4] if len(argv) > 4 else "*")
        for p, sz, sec, d in fs.walk():
            if d or not fnmatch.fnmatch(p.lower(), pat.lower()):
                continue
            dst = os.path.join(out, *p.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            fs.f.seek(fs.base + sec * SECTOR)
            with open(dst, "wb") as o:
                left = sz
                while left:
                    chunk = fs.f.read(min(left, 1 << 22))
                    o.write(chunk)
                    left -= len(chunk)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

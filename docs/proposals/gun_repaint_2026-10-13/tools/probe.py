"""Which file wins today for a texture stem (engine order: .dds anywhere > .jpg anywhere > .tga; inside one
extension the last pak in name order), and every other copy. Read-only over the GOG pak set.

    python probe.py <stem or substring> [...]        e.g. textures/models/weapons/colt/colt45s2
    python probe.py --grep <regex>                   list vpaths matching
"""
import os, sys, re, io
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import vfs
from PIL import Image


def info(vp, which=-1):
    data = vfs.read(vp, which)
    if data[:4] == b"DDS ":
        import struct
        h, w = struct.unpack("<II", data[12:20]); mips = struct.unpack("<I", data[28:32])[0]
        return "%dx%d %s mips=%d %d bytes" % (w, h, data[84:88].decode("latin-1"), mips, len(data))
    try:
        im = Image.open(io.BytesIO(data))
        return "%dx%d %s %d bytes" % (im.size[0], im.size[1], im.mode, len(data))
    except Exception as e:
        return "? %d bytes %r" % (len(data), e)


def show(stem):
    stem = os.path.splitext(stem.lower())[0]
    idx = vfs.index()
    won = False
    for ext in (".dds", ".jpg", ".tga", ".png"):
        l = idx.get(stem + ext)
        if not l:
            continue
        for k, (p, n) in enumerate(l):
            last = k == len(l) - 1
            tag = "WINS" if (last and not won) else "    "
            print("  %s %-5s %-44s %s" % (tag, ext, os.path.basename(p), info(stem + ext, k)))
        won = True
    if not won:
        print("  (nothing)")


def main():
    a = sys.argv[1:]
    if a and a[0] == "--grep":
        rx = re.compile(a[1], re.I)
        for k in sorted(vfs.index()):
            if rx.search(k):
                print(k, "<-", os.path.basename(vfs.index()[k][-1][0]))
        return
    for s in a:
        print(s)
        show(s)


if __name__ == "__main__":
    main()

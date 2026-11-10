#!/usr/bin/env python3
"""Inventory a Frontline Xbox image: every disc file plus every file inside
every BIG/VIV archive, with its magic. Writes TSV + JSON summary (names, sizes
and 4-byte magics only - no asset data leaves the image).

usage: inventory.py <image.iso> <out_dir>
"""
import collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xdvdfs import XDVDFS, SECTOR  # noqa: E402
import viv  # noqa: E402


def magic_str(b):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in b[:4]) + "|" + b[:4].hex()


def ext_of(name):
    n = name.rsplit("/", 1)[-1]
    return n.rsplit(".", 1)[-1].lower() if "." in n else "(none)"


def main(img, outdir):
    fs = XDVDFS(img)
    rows = []
    for path, size, sec, is_dir in sorted(fs.walk()):
        if is_dir:
            continue
        head = fs.read(sec, min(size, 64))
        rows.append(dict(container="", path=path, size=size, ext=ext_of(path), magic=magic_str(head), level=level_of(path)))
        hl = viv.header_len(head) if size >= 16 else 0
        if hl:
            toc = viv.parse_toc(fs.read(sec, min(size, hl + 4096)))
            for name, off, isz in toc:
                ih = fs.read(sec + off // SECTOR, (off % SECTOR) + 8)[off % SECTOR:]
                m = magic_str(ih)
                if ih[:2] in (b"\x10\xfb", b"\x11\xfb"):
                    m = "REFPACK|" + ih[:2].hex()
                elif len(ih) > 5 and ih[1:2] == b"\xfb" and ih[0] & 0xFE == 0x10:
                    m = "REFPACK|" + ih[:2].hex()
                rows.append(dict(container=path, path=name, size=isz, ext=ext_of(name), magic=m, level=level_of(path)))
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "inventory.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("container\tpath\tsize\text\tmagic\tlevel\n")
        for r in rows:
            f.write("\t".join(str(r[k]) for k in ("container", "path", "size", "ext", "magic", "level")) + "\n")
    summ = {"disc": collections.defaultdict(lambda: [0, 0]), "in_archives": collections.defaultdict(lambda: [0, 0]),
            "magics_in_archives": collections.Counter(), "per_level_disc_bytes": collections.Counter()}
    for r in rows:
        k = "in_archives" if r["container"] else "disc"
        summ[k][r["ext"]][0] += 1
        summ[k][r["ext"]][1] += r["size"]
        if r["container"]:
            summ["magics_in_archives"][r["ext"] + " " + r["magic"]] += 1
        else:
            summ["per_level_disc_bytes"][r["level"]] += r["size"]
    out = {
        "image": os.path.basename(img), "partition_base": hex(fs.base),
        "disc_files": sum(1 for r in rows if not r["container"]),
        "archive_members": sum(1 for r in rows if r["container"]),
        "disc_by_ext": {k: {"count": v[0], "bytes": v[1]} for k, v in sorted(summ["disc"].items())},
        "archive_members_by_ext": {k: {"count": v[0], "bytes": v[1]} for k, v in sorted(summ["in_archives"].items(), key=lambda kv: -kv[1][1])},
        "archive_member_magics": dict(summ["magics_in_archives"].most_common()),
        "disc_bytes_per_level": dict(sorted(summ["per_level_disc_bytes"].items())),
    }
    with open(os.path.join(outdir, "inventory.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
    print(out["disc_files"], "disc files,", out["archive_members"], "archive members")


def level_of(path):
    p = path.split("/")
    if len(p) >= 3 and p[0] == "DATA" and p[1].isdigit() and "_" in p[2]:
        return p[2]
    return p[1] if len(p) > 2 else "root"


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

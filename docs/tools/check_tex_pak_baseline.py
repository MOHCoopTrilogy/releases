#!/usr/bin/env python3
"""Build gate: the 1.3 GB texture pak must not change by accident (bug-3901).

build.ps1 packs every file under textures/ models/ gfx/ env/ of the mod tree into
zzzzzz_co-op_hzm_mod_assets_tex.pk3. The updater reuses a player's copy as long as the pak's
sha256 equals the released one, and the packer is deterministic over (path, size, mtime) of
every member - so ONE added, removed, edited or merely re-touched file means every player
downloads 1.3 GB again. v1.10.22 did exactly that with 318 new files.

New art ships through the small fixes pak instead (docs/tools/gen_fixes_pak.py, sources under
docs/tools/assets/fixes/), never by dropping files into those four folders.

  check (default)      compare the tree with docs/tools/tex_pak_baseline.tsv; exit 1 and name
                       every offending file when they differ
  --full               also CRC every file's content (slow; the default trusts size + mtime,
                       which is exactly what the packer's own input digest trusts)
  --allow-change       report the differences but exit 0 (build.ps1 -AllowTexPakChange, or
                       HZM_ALLOW_TEX_PAK_CHANGE=1) - for a DELIBERATE tex pak release only
  --restore-mtimes     for files whose content still matches the baseline but whose mtime was
                       touched (a git checkout does that): put the baseline mtime back
  --write-baseline     re-pin the baseline from the current tree. Cross-checked against the
                       built pak in build_out/ (member names, sizes) and, when that pak is the
                       one in manifests/latest.json, records the release it belongs to.
                       --no-pak-check skips the cross-check (CRCs then come from the tree).

The file selection mirrors build.ps1 ($allFiles filter + the bucket rule). Keep them in step.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
import zlib

DEV = r"C:\mohaa-coop-dev"
SRC = os.path.join(DEV, "hzm-mohaa-coop-mod")
BASELINE = os.path.join(DEV, "docs", "tools", "tex_pak_baseline.tsv")
PAK_NAME = "zzzzzz_co-op_hzm_mod_assets_tex.pk3"
PAK = os.path.join(DEV, "build_out", PAK_NAME)
MANIFEST = os.path.join(DEV, "manifests", "latest.json")

TEX_DIRS = ("textures", "models", "gfx", "env")           # build.ps1: $paks[1].Dirs
EXCLUDE_EXT = (".bak", ".pk3", ".mp4")                    # build.ps1: $allFiles filter
EXCLUDE_NAMES = (".gitignore", ".gitattributes", "readme.md")
EXCLUDE_SUFFIX = ".pre_upscale_nobuild"
TICKS_EPOCH = 621355968000000000                          # .NET ticks at 1970-01-01
MAX_LIST = 40


def ticks_of(st):
    return st.st_mtime_ns // 100 + TICKS_EPOCH


def hidden(st):
    return bool(getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_HIDDEN)


def scan(src):
    """rel path (forward slashes) -> (size, mtime ticks, full path), as build.ps1 would pack."""
    out = {}
    for top in os.listdir(src):
        if top.lower() not in TEX_DIRS:
            continue
        root = os.path.join(src, top)
        if not os.path.isdir(root) or hidden(os.stat(root)):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            keep = []
            for d in dirnames:
                if d.lower() == ".git":
                    continue
                if hidden(os.stat(os.path.join(dirpath, d))):   # Get-ChildItem without -Force
                    continue
                keep.append(d)
            dirnames[:] = keep
            for name in filenames:
                low = name.lower()
                if os.path.splitext(low)[1] in EXCLUDE_EXT:
                    continue
                if low in EXCLUDE_NAMES or low.endswith(EXCLUDE_SUFFIX):
                    continue
                full = os.path.join(dirpath, name)
                st = os.stat(full)
                if hidden(st):
                    continue
                rel = os.path.relpath(full, src).replace("\\", "/")
                out[rel] = (st.st_size, ticks_of(st), full)
    return out


def crc_of(path):
    crc = 0
    with open(path, "rb") as fh:
        while True:
            buf = fh.read(1 << 20)
            if not buf:
                break
            crc = zlib.crc32(buf, crc)
    return "%08x" % (crc & 0xFFFFFFFF)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            buf = fh.read(1 << 22)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def read_baseline(path):
    meta, rows = {}, {}
    with open(path, "r", encoding="utf-8", newline="") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line:
                continue
            if line.startswith("#"):
                if "=" in line:
                    k, v = line[1:].split("=", 1)
                    meta[k.strip()] = v.strip()
                continue
            rel, size, ticks, crc = line.split("\t")
            rows[rel] = (int(size), int(ticks), crc)
    return meta, rows


def show(title, items):
    if not items:
        return
    print("  %s: %d" % (title, len(items)))
    for it in items[:MAX_LIST]:
        print("    " + it)
    if len(items) > MAX_LIST:
        print("    ... and %d more" % (len(items) - MAX_LIST))


def write_baseline(args):
    tree = scan(args.src)
    crcs, meta = {}, {}
    if args.no_pak_check:
        print("no pak check: CRC of %d tree files ..." % len(tree))
        for rel, (_s, _t, full) in tree.items():
            crcs[rel] = crc_of(full)
        meta["pak"] = "not checked"
    else:
        if not os.path.isfile(args.pak):
            print("REFUSED: %s is missing - build first, or pass --no-pak-check." % args.pak)
            return 1
        with zipfile.ZipFile(args.pak) as zf:
            members = {i.filename: (i.file_size, "%08x" % i.CRC) for i in zf.infolist()}
        only_tree = sorted(set(tree) - set(members))
        only_pak = sorted(set(members) - set(tree))
        size_diff = sorted(r for r in set(tree) & set(members) if tree[r][0] != members[r][0])
        if only_tree or only_pak or size_diff:
            print("REFUSED: the tree is not what %s was packed from." % args.pak)
            show("in the tree, not in the pak", only_tree)
            show("in the pak, not in the tree", only_pak)
            show("size differs", size_diff)
            return 1
        crcs = {r: members[r][1] for r in tree}
        pak_sha = sha256_of(args.pak)
        meta["pak"] = PAK_NAME
        meta["pak_size"] = str(os.path.getsize(args.pak))
        meta["pak_sha256"] = pak_sha
        meta["release"] = "unreleased build (not the pak in manifests/latest.json)"
        try:
            with open(args.manifest, "r", encoding="utf-8-sig") as fh:
                man = json.load(fh)
            for f in man.get("files", []):
                if f.get("path", "").endswith("/" + PAK_NAME) and f.get("sha256", "").lower() == pak_sha:
                    meta["release"] = str(man.get("version"))
        except (OSError, ValueError) as exc:
            print("note: manifest not read (%s)" % exc)
    tmp = args.baseline + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# tex pak baseline - written by docs/tools/check_tex_pak_baseline.py --write-baseline. Do not hand-edit.\n")
        for k in sorted(meta):
            fh.write("# %s=%s\n" % (k, meta[k]))
        fh.write("# files=%d\n" % len(tree))
        fh.write("# columns=path<TAB>size<TAB>mtime (.NET utc ticks)<TAB>crc32\n")
        for rel in sorted(tree):
            fh.write("%s\t%d\t%d\t%s\n" % (rel, tree[rel][0], tree[rel][1], crcs[rel]))
    os.replace(tmp, args.baseline)
    print("tex pak baseline: written, %d files, release %s -> %s" % (len(tree), meta.get("release", "?"), args.baseline))
    return 0


def check(args):
    if not os.path.isfile(args.baseline):
        print("tex pak baseline: FAILED - %s is missing." % args.baseline)
        return 1
    meta, base = read_baseline(args.baseline)
    tree = scan(args.src)
    added = sorted(set(tree) - set(base))
    removed = sorted(set(base) - set(tree))
    changed, touched, restored = [], [], []
    for rel in sorted(set(tree) & set(base)):
        size, ticks, full = tree[rel]
        bsize, bticks, bcrc = base[rel]
        if size != bsize:
            changed.append("%s (size %d -> %d)" % (rel, bsize, size))
        elif ticks != bticks:
            if crc_of(full) != bcrc:
                changed.append("%s (content differs, same size)" % rel)
            elif args.restore_mtimes:
                ns = (bticks - TICKS_EPOCH) * 100
                os.utime(full, ns=(ns, ns))
                restored.append(rel)
            else:
                touched.append(rel)
        elif args.full and crc_of(full) != bcrc:
            changed.append("%s (content differs, same size and mtime)" % rel)
    if restored:
        show("mtime restored (content was unchanged)", restored)
    if not (added or removed or changed or touched):
        print("tex pak baseline: ok - %d files match release %s" % (len(tree), meta.get("release", "?")))
        return 0
    print("%s would no longer be the released pak (release %s):" % (PAK_NAME, meta.get("release", "?")))
    show("ADDED (not in the released pak)", added)
    show("REMOVED (in the released pak)", removed)
    show("CHANGED", changed)
    show("TOUCHED (same content, new mtime - the pak bytes still change; --restore-mtimes fixes it)", touched)
    print("  Every player would re-download 1.3 GB. New or changed art belongs in the fixes pak")
    print("  (docs/tools/gen_fixes_pak.py, sources under docs/tools/assets/fixes/), not under")
    print("  textures/ models/ gfx/ env/ of the mod tree.")
    if changed or touched:
        print("  A CHANGED file that is a pinned base of the fixes pak (a git checkout of the mod tree puts the")
        print("  fixed copy back): python docs/tools/gen_fixes_pak.py restore")
    if args.allow_change:
        print("  Deliberate tex pak release: after publishing, run this script with --write-baseline.")
        print("tex pak baseline: OVERRIDDEN - %d added, %d removed, %d changed, %d touched"
              % (len(added), len(removed), len(changed), len(touched)))
        return 0
    print("  Deliberate tex pak release: build.ps1 -AllowTexPakChange (or HZM_ALLOW_TEX_PAK_CHANGE=1),")
    print("  then --write-baseline once it is published.")
    print("tex pak baseline: FAILED - %d added, %d removed, %d changed, %d touched"
          % (len(added), len(removed), len(changed), len(touched)))
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--baseline", default=BASELINE)
    ap.add_argument("--pak", default=PAK)
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--no-pak-check", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--allow-change", action="store_true")
    ap.add_argument("--restore-mtimes", action="store_true")
    args = ap.parse_args()
    if args.write_baseline:
        return write_baseline(args)
    return check(args)


if __name__ == "__main__":
    sys.exit(main())

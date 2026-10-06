"""bug-3397: make the generated finish shaders name each base texture EXACTLY as the gun's own shader does.

    python docs/tools/fix_skin_case.py           # dry run: list the rewrites
    python docs/tools/fix_skin_case.py --write   # rewrite scripts/coop_skins.shader + coop_clip_skins.shader

WHY. The renderers' image cache matches names case- and extension-sensitively (R_FindImageFile compares the stored
imgName with strcmp), while the pak filesystem is case-insensitive. gen_skins.py / gen_clip_art.py lower-cased every
base path (`textures/models/weapons/thompsonsmg/thompsonsmg.tga`) while the gun's own shader says
`textures/models/weapons/ThompsonSMG/ThompsonSMG.tga`, so the SAME file was uploaded twice whenever a finish or a
finished magazine was registered next to the stock gun - 6 MB per Thompson at 2048, 12+ MB at 4096 (imagelist of the
weapon-HD run). The same split existed for 21 more weapon textures.

Canonical spelling = the `map` token of the WINNING non-coop shader that draws the texture (retail/HRRTM/xw). Only
`map` lines whose path matches a canonical one case-insensitively (extension ignored) are rewritten; the file's
line endings are preserved (binary-mode replace, count-asserted). Generators were patched to emit the canonical
token too (gen_skins.py `canon()`), so a re-run cannot bring the split back. Scripts live in the CODE pak, so this
does not touch the assets_tex pak.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "docs", "tools", "weapon_hd"))
import jobs, vfs
FILES = [os.path.join(ROOT, "hzm-mohaa-coop-mod", "scripts", f) for f in ("coop_skins.shader", "coop_clip_skins.shader")]


def canonical():
    """lower(path without extension) -> the token the winning non-coop shader uses"""
    idx = vfs.index()
    canon = {}
    for p in vfs.paks():
        if "co-op_hzm" in os.path.basename(p):
            continue
        for n in sorted([n for (pp, n) in sum((idx[k] for k in idx if k.startswith("scripts/") and k.endswith(".shader")), [])
                         if pp == p], key=str.lower, reverse=True):
            t = vfs._zips[p].read(n).decode("latin-1", "replace")
            for m in re.finditer(r"(?mi)^\s*(?:map|clampmap)\s+(textures/\S+|models/\S+)", t):
                canon[re.sub(r"\.\w+$", "", m.group(1)).lower()] = m.group(1)
    return canon


def main(write=None):
    if write is None:
        write = "--write" in sys.argv
    canon = canonical()
    total = 0
    for f in FILES:
        b = open(f, "rb").read()
        reps = {}
        for m in re.finditer(rb"(?m)^(\s*map\s+)(\S+)", b):
            tok = m.group(2).decode("latin-1")
            c = canon.get(re.sub(r"\.\w+$", "", tok).lower())
            if c and c != tok:
                reps[tok] = c
        nb = b
        for tok, c in sorted(reps.items()):
            n = len(re.findall(rb"(?m)^(\s*map\s+)" + re.escape(tok.encode()) + rb"(?=\s)", nb))
            assert n > 0
            nb = re.sub(rb"(?m)^(\s*map\s+)" + re.escape(tok.encode()) + rb"(?=\s)", lambda mm: mm.group(1) + c.encode(), nb)
            print("%-22s %3d x %s -> %s" % (os.path.basename(f), n, tok, c))
            total += n
        assert nb.count(b"\r\n") == b.count(b"\r\n") and nb.count(b"\n") == b.count(b"\n"), "line endings changed"
        if write and nb != b:
            open(f, "wb").write(nb)
    print("%d map line(s) %s" % (total, "rewritten" if write else "would be rewritten (dry run)"))


if __name__ == "__main__":
    main()

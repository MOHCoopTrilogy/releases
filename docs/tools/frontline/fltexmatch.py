#!/usr/bin/env python3
"""Texture-upgrade CANDIDATE finder (authoring aid, run by us - not by the player's converter).

For the most-used opaque textures of a converted level, rank the higher-resolution textures the mod already
ships (the user's installed HD/world/foliage paks) by a simple look descriptor (colour mean/spread on a 4x4
grid + gradient-direction histogram) and write contact sheets: Frontline texture | top candidates. A human
reviews the sheets; accepted swaps go into fl_texmap.json with a reason - the converter only applies that table,
so every player's conversion stays identical.

usage: fltexmatch.py <converted.pk3> <level> <outdir> [--top 16]
"""
import io
import math
import os
import sys
import zipfile

from PIL import Image, ImageFilter

PAKS = [r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzzz_hd_world.pk3",
        r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzz-AA_HD_Project_Pak1.pk3",
        r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzz-AA_HD_Project_Pak2.pk3",
        r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzz-AA_HD_Project_Pak3.pk3",
        r"G:\GOG\Medal of Honor - Allied Assault War Chest\maintt\zzzzz-AA_HD_Project_Pak4.pk3"]
KEYS = ("brick", "plaster", "stone", "cobble", "roof", "wood", "tile", "street", "road", "ground", "dirt",
        "grass", "wall", "rock", "concrete", "shingle", "slate", "pave", "mud", "gravel")
SKIP = ("sign", "text", "letter", "poster", "word", "logo", "decal", "font")


def desc(im):
    im = im.convert("RGB").resize((32, 32), Image.BILINEAR)
    px = im.load()
    f = []
    for gy in range(4):
        for gx in range(4):
            cells = [px[x, y] for y in range(gy * 8, gy * 8 + 8) for x in range(gx * 8, gx * 8 + 8)]
            for c in range(3):
                f.append(sum(p[c] for p in cells) / 64.0 / 255.0)
    g = im.convert("L").filter(ImageFilter.FIND_EDGES).resize((16, 16))
    gh = [0.0] * 4
    lp = im.convert("L").load()
    for y in range(1, 31):
        for x in range(1, 31):
            dx = lp[x + 1, y] - lp[x - 1, y]
            dy = lp[x, y + 1] - lp[x, y - 1]
            a = int(((math.atan2(dy, dx) + math.pi) / math.pi * 2)) % 4
            gh[a] += math.hypot(dx, dy)
    s = sum(gh) or 1.0
    f += [3.0 * v / s for v in gh]
    mean = sum(f[:48]) / 48
    f.append(4.0 * math.sqrt(sum((v - mean) ** 2 for v in f[:48]) / 48))
    return f


def main(pk3, level, out, top=16):
    os.makedirs(out, exist_ok=True)
    z = zipfile.ZipFile(pk3)
    sh = z.read(f"scripts/fl_{level}.shader").decode()
    alpha = {l.strip() for l in sh.split("\n") if l.startswith("textures/")}
    alpha_names, cur = set(), None
    for line in sh.splitlines():
        if line.startswith("textures/"):
            cur = line.strip()
        if "alphaFunc" in line:
            alpha_names.add(cur)
    import struct
    b = z.read(f"maps/mfl_{level}.bsp")
    so, sl = struct.unpack_from("<ii", b, 12)
    names = [b[so + 140 * i: so + 140 * i + 64].split(bytes(1))[0].decode() for i in range(sl // 140)]
    fo, fln = struct.unpack_from("<ii", b, 12 + 8 * 3)
    use = {}
    for i in range(fln // 108):
        shn, _, _, _, _, _, ni = struct.unpack_from("<7i", b, fo + 108 * i)
        use[names[shn]] = use.get(names[shn], 0) + ni // 3
    fl = []
    for n in sorted(z.namelist(), key=lambda n: -use.get(n[:-4], 0)):
        if n.startswith(f"textures/fl/{level}/") and n.endswith(".tga") and n[:-4] not in alpha_names:
            im = Image.open(io.BytesIO(z.read(n)))
            fl.append((n, im))
    cands = []
    for pk in PAKS:
        if not os.path.exists(pk):
            continue
        pz = zipfile.ZipFile(pk)
        for n in sorted(pz.namelist()):
            ln = n.lower()
            if not ln.startswith("textures/") or not ln.endswith((".tga", ".jpg", ".png")):
                continue
            if not any(k in ln for k in KEYS) or any(k in os.path.basename(ln) for k in SKIP):
                continue
            try:
                im = Image.open(io.BytesIO(pz.read(n)))
                im.load()
            except Exception:
                continue
            if min(im.size) < 256:
                continue
            cands.append((os.path.basename(pk), n, im.size, desc(im), im.convert("RGB").resize((128, 128))))
    print(len(fl), "frontline opaque textures,", len(cands), "candidates")
    rows = []
    for n, im in fl:
        d = desc(im)
        sc = sorted(((sum((a - b) ** 2 for a, b in zip(d, c[3])), i) for i, c in enumerate(cands)))[:3]
        rows.append((n, im, [(cands[i], s) for s, i in sc]))
    sheet_rows = rows[:top] if top else rows
    S = Image.new("RGB", (4 * 132, 132 * len(sheet_rows)), (30, 30, 30))
    with open(os.path.join(out, "candidates.tsv"), "w", newline="\n") as f:
        for r, (n, im, best) in enumerate(sheet_rows):
            S.paste(im.convert("RGB").resize((128, 128)), (0, r * 132))
            for k, (c, s) in enumerate(best):
                S.paste(c[4], ((k + 1) * 132, r * 132))
                f.write(f"{n}\t{k}\t{c[0]}\t{c[1]}\t{c[2][0]}x{c[2][1]}\t{s:.3f}\n")
    S.save(os.path.join(out, "candidates.jpg"), quality=85)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 16)

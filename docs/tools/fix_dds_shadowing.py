# -*- coding: utf-8 -*-
"""[user 2026-09-08] "texture work beyond this map".

Fixes the DDS-SHADOWING class game-wide: an HD upscale that is already installed but never loads,
because R_LoadImage rewrites the extension to .dds and tries LoadDDS FIRST whenever texture
compression is on (and it is: r_ext_compressed_textures 1, the engine reports s3tc in use). So a
stock 128x128 .dds beats a 512x512 HD .jpg every time, silently, with no warning anywhere. That is
bug-1129's class, and a full sweep of all 11,211 texture basenames found 63 live instances left.

NOTHING IS UPSCALED HERE. The larger image already exists in some pak; it just loses. This re-encodes
that existing larger image as DXT .dds with a full mip chain and ships it in a pak that out-sorts
every other, so the file the user already installed finally gets used. No GPU, no ESRGAN, no
hallucination risk - which is exactly why it is worth doing separately from the m3l1a 4x pass.

THE PAK NAME IS LOAD-BEARING. Paks sort alphabetically and the LAST one wins; the HD packs reach
zzzzzzzz_hd_seamfix (eight z) and the mod's own terrain pak is nine. This is ten, and sorts after
zzzzzzzzzz_coop_hd_m3l1a.pk3 ('s' > 'm'), which is harmless: the m3l1a pass already un-shadowed its
own textures, so the two do not overlap in practice, and where they did the newer/larger wins.

  python docs/tools/fix_dds_shadowing.py            report only
  python docs/tools/fix_dds_shadowing.py --write    build the pak
"""
import io
import os
import sys
import glob
import struct
import zipfile

from PIL import Image

GL2 = os.path.join("G:", os.sep, "mohaa-gl2")
ROOTS = ["main", "mainta", "maintt"]
MODROOT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
STAGE = r"C:\mohaa-coop-dev\_hd_shadowfix"
PAK = os.path.join(MODROOT, "zzzzzzzzzz_coop_hd_shadowfix.pk3")
SELF = os.path.basename(PAK).lower()

Image.MAX_IMAGE_PIXELS = None
EXT_RANK = {".dds": 0, ".jpg": 1, ".tga": 2}

MOUNTS = []
for r in reversed(ROOTS):
    for p in sorted(glob.glob(os.path.join(GL2, r, "*.pk3")), reverse=True):
        if os.path.basename(p).lower() == SELF:
            continue                       # never let a previous run of this tool be its own input
        try:
            MOUNTS.append((r + "/" + os.path.basename(p), zipfile.ZipFile(p)))
        except Exception:
            pass


def dims(b, ext):
    try:
        if ext == ".dds" and b[:4] == b"DDS ":
            _s, _f, h, w = struct.unpack("<4I", b[4:20])
            return w, h
        if ext == ".tga":
            return struct.unpack("<HH", b[12:16])
        if ext == ".jpg":
            i = 2
            while i < len(b) - 9:
                if b[i] != 0xFF:
                    i += 1
                    continue
                mk = b[i + 1]
                if mk in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", b[i + 5:i + 9])
                    return w, h
                i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    except Exception:
        pass
    return None


def save_dds_mipped(img, path, fmt):
    """DXT with a FULL mip chain - Pillow writes level 0 only, and the engine does not synthesise
    mips for a DDS the way it does for TGA/JPG, so a mipless sheet shimmers worse than the small
    texture it replaced."""
    levels = []
    w, h = img.size
    cur = img
    while True:
        buf = io.BytesIO()
        cur.save(buf, format="DDS", pixel_format=fmt)
        levels.append(buf.getvalue())
        if w == 1 and h == 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
        cur = img.resize((w, h), Image.LANCZOS)
    head = bytearray(levels[0][:128])
    struct.pack_into("<I", head, 8, struct.unpack_from("<I", head, 8)[0] | 0x20000)
    struct.pack_into("<I", head, 28, len(levels))
    struct.pack_into("<I", head, 108, struct.unpack_from("<I", head, 108)[0] | 0x8 | 0x400000)
    with io.open(path, "wb") as f:
        f.write(bytes(head))
        for lv in levels:
            f.write(lv[128:])


def main():
    cand = {}
    for pi, (tag, z) in enumerate(MOUNTS):
        for n in z.namelist():
            ln = n.lower()
            if not ln.startswith("textures/"):
                continue
            base, ext = os.path.splitext(ln)
            if ext not in EXT_RANK:
                continue
            cand.setdefault(base, []).append((pi, ext, tag, z, n))

    shadowed = []
    for base, lst in cand.items():
        lst.sort(key=lambda e: (EXT_RANK[e[1]], e[0]))
        sized = []
        for pi, ext, tag, z, n in lst:
            d = dims(z.read(n), ext)
            if d:
                sized.append((pi, ext, tag, z, n, d))
        if not sized:
            continue
        win = sized[0]
        best = max(sized, key=lambda e: e[5][0] * e[5][1])
        if best[5][0] * best[5][1] > win[5][0] * win[5][1]:
            shadowed.append((base, win, best))

    shadowed.sort(key=lambda s: -(s[2][5][0] * s[2][5][1]))
    print("texture basenames examined: %d" % len(cand))
    print("HD images installed but SHADOWED by a smaller winner: %d\n" % len(shadowed))
    print("%-52s %-16s %-16s %s" % ("texture", "loads today", "installed but dead", "from"))
    for base, win, best in shadowed[:70]:
        print("%-52s %4dx%-4d %-5s %4dx%-4d %-5s %s"
              % (base[9:][:52], win[5][0], win[5][1], win[1],
                 best[5][0], best[5][1], best[1], os.path.basename(best[2])[:26]))

    if "--write" not in sys.argv:
        print("\n(report only - pass --write to build the pak)")
        return

    os.makedirs(STAGE, exist_ok=True)
    made = fail = 0
    for base, win, best in shadowed:
        _pi, ext, tag, z, name, d = best
        out = os.path.join(STAGE, (base + ".dds").replace("/", os.sep))
        try:
            im = Image.open(io.BytesIO(z.read(name)))
            im.load()
        except Exception as e:
            print("  UNREADABLE %-44s %s" % (base, e))
            fail += 1
            continue
        alpha = None
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            a = im.convert("RGBA").split()[3]
            if min(a.getdata()) < 250:
                alpha = a
        rgba = im.convert("RGB").convert("RGBA")
        if alpha is not None:
            rgba.putalpha(alpha)
            fmt = "DXT5"
        else:
            fmt = "DXT1"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            save_dds_mipped(rgba, out, fmt)
            made += 1
        except Exception as e:
            print("  DDS-WRITE-FAIL %-40s %s" % (base, e))
            fail += 1

    files = sorted((os.path.relpath(p, STAGE).replace(os.sep, "/"), p)
                   for p in glob.glob(os.path.join(STAGE, "**", "*.dds"), recursive=True))
    tmp = PAK + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, p in files:
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            z.writestr(zi, io.open(p, "rb").read())
    if os.path.exists(PAK):
        os.remove(PAK)
    os.rename(tmp, PAK)
    print("\nwritten=%d failed=%d -> %s (%.1f MB)" % (made, fail, PAK, os.path.getsize(PAK) / 1048576.0))


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""Build the CC0 terrain replacement pack.

WHY DDS AND NOT JPG: R_LoadImage tries "<name>.dds" FIRST whenever r_ext_compressed_textures
is on - and it IS on in the live config (renderergl2/tr_image.c:2473, saved config "1", engine
default 0). It returns immediately on a hit. All six target textures already ship a .dds in the
HD packs, so a .jpg replacement would be silently ignored no matter which pak it sat in:
extension order beats pak priority here. The replacement has to be a .dds too.

WHY THE PAK NAME HAS NINE Z's: paks are sorted alphabetically and each is PREPENDED to the
search path, so the LAST name wins. The HD packs go up to "zzzzzzzz_hd_seamfix" (eight). Nine
beats it. Ship this as anything less and the upscales keep winning.

WHY _nh AND NOT _n: the shader collapse probes "<diffuse>_nh" as IMGTYPE_NORMALHEIGHT first and
only sets the parallax bit on that hit; height lives in the ALPHA channel, which is why the
normal map is DXT5 (alpha) while colour is DXT1 (none). Verified swizzleNormalmap is FALSE on
this GPU (it needs RGTC to be ABSENT, and RGTC is supported), so alpha is the right channel.
"""
import io, os, sys, zipfile, json, urllib.request, shutil
from PIL import Image
import struct


def save_dds_mipped(img, path, fmt):
    """Write a DXT DDS WITH A FULL MIP CHAIN.

    Pillow writes a single level, and renderergl2/tr_image.c:3322 CLEARS IMGFLAG_MIPMAP on any
    compressed image whose mip count is short of log2(max(w,h))+1. The result is ground with no
    mipmapping at all - which on a texture stretched over 512-unit patches aliases far worse than
    the upscale we are replacing. So: encode each level separately, strip each 128-byte header,
    concatenate, and patch the level-0 header with DDSD_MIPMAPCOUNT / the count / DDSCAPS_MIPMAP.
    """
    levels, cur = [], img
    while True:
        buf = io.BytesIO()
        cur.save(buf, format="DDS", pixel_format=fmt)
        raw = buf.getvalue()
        if not levels:
            header = bytearray(raw[:128])
        levels.append(raw[128:])
        if cur.size[0] <= 1 and cur.size[1] <= 1:
            break
        cur = cur.resize((max(1, cur.size[0] // 2), max(1, cur.size[1] // 2)), Image.LANCZOS)

    DDSD_MIPMAPCOUNT, DDSCAPS_COMPLEX, DDSCAPS_MIPMAP = 0x20000, 0x8, 0x400000
    flags = struct.unpack_from("<I", header, 8)[0] | DDSD_MIPMAPCOUNT
    struct.pack_into("<I", header, 8, flags)
    struct.pack_into("<I", header, 28, len(levels))
    caps = struct.unpack_from("<I", header, 108)[0] | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP
    struct.pack_into("<I", header, 108, caps)

    with open(path, "wb") as f:
        f.write(bytes(header))
        for lv in levels:
            f.write(lv)
    return len(levels)


UA = "Mozilla/5.0 mohaa-coop-mod"
OUT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\_terrain_pack"
CACHE = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\16396f85-9f5f-4159-8516-3f08362e0a18\scratchpad\acg"

# asset -> the retail texture path it replaces. Chosen by eye against the live textures.
JOBS = [
    ("Ground037", "textures/wilderness/m3l3grass_1rough",             2048),  # 22.7% of all terrain
    ("Ground054", "textures/algiers/grndset_2af",                     1024),  # 11.3%
    ("Ground108", "textures/models/items/rubblebase",                 1024),  # 10.0%
    ("Snow006",   "textures/central_europe_winter/forstsnow_lite256", 1024),  #  9.0%
    ("Grass004",  "textures/mohtest/nu_earth_set3grassa",             2048),  #  8.4%
    ("Ground107", "textures/mohtest/rubble2c",                        1024),  #  7.3%
]

def fetch(url, dst):
    if os.path.exists(dst) and os.path.getsize(dst) > 10000:
        return dst
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)
    return dst

RETAIL_STATS = {   # (mean, std) of the texture each one replaces
    "textures/wilderness/m3l3grass_1rough": (55, 35),
    "textures/algiers/grndset_2af": (128, 41),
    "textures/models/items/rubblebase": (85, 59),
    "textures/central_europe_winter/forstsnow_lite256": (198, 19),
    "textures/mohtest/nu_earth_set3grassa": (37, 41),
    "textures/mohtest/rubble2c": (72, 33),
}


def match_levels(img, target_mean, target_std):
    """Match an albedo's LEVEL and CONTRAST to the texture it replaces.

    First attempt matched the mean with a flat multiply. That fixed the brightness and broke the
    look: scaling by 0.43 to darken also scales the spread, so the structure the material was chosen
    for got crushed and the result read FLATTER than the AI upscale it replaced - worse on the one
    axis the whole exercise was meant to improve.

    Matching mean AND standard deviation instead moves the histogram onto the original's without
    compressing it: out = (in - mean_in) * (std_target / std_in) + mean_target. The material keeps its
    own detail; only where it sits and how far it spreads are borrowed. MOHAA lightmaps are baked",
    against the original, so both of those have to match or the level's lighting balance shifts.
    """
    import numpy as np
    a = np.asarray(img, dtype=np.float64)
    m, sd = a.mean(), a.std()
    if sd < 1.0 or not target_mean or not target_std:
        return img
    k = target_std / sd
    k = max(0.5, min(2.2, k))       # a wild contrast rescale means the asset is simply the wrong pick
    out = (a - m) * k + target_mean
    out = np.clip(out, 0, 255).astype("uint8")
    return Image.fromarray(out), m, sd, out.mean(), out.std()

def pick(names, *keys):
    for k in keys:
        for n in names:
            if k.lower() in n.lower():
                return n
    return None

# Guarded so this module can be IMPORTED for save_dds_mipped without re-running the whole
# download-and-rebuild, which silently wiped staged composites when it was imported mid-session.
def main():
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for asset, target, res in JOBS:
        zf = os.path.join(CACHE, "%s_2K-JPG.zip" % asset)
        print("[%s] fetching -> %s" % (asset, target))
        try:
            fetch("https://ambientcg.com/get?file=%s_2K-JPG.zip" % asset, zf)
        except Exception as e:
            print("   DOWNLOAD FAILED:", e); continue
        z = zipfile.ZipFile(zf)
        names = z.namelist()
        nc = pick(names, "_Color.jpg", "Color")
        nn = pick(names, "NormalGL", "Normal")
        nd = pick(names, "Displacement", "Height")
        if not nc:
            print("   no colour map in zip; has:", names[:6]); continue

        col = Image.open(io.BytesIO(z.read(nc))).convert("RGB").resize((res, res), Image.LANCZOS)
        tm, ts = RETAIL_STATS.get(target, (None, None))
        r = match_levels(col, tm, ts)
        if isinstance(r, tuple):
            col, m0, s0, m1, s1 = r
            print("   levels      mean %.0f->%.0f  contrast %.0f->%.0f  (target %s/%s)" % (m0, m1, s0, s1, tm, ts))
        dst = os.path.join(OUT, target.replace("/", os.sep) + ".dds")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        nmip = save_dds_mipped(col, dst, "DXT1")
        total += os.path.getsize(dst)
        print("   colour  %-46s %5d KB  %d mips" % (target + ".dds", os.path.getsize(dst)//1024, nmip))

        if nn:
            nres = min(res, 1024)                       # normals tolerate half the colour resolution
            nrm = Image.open(io.BytesIO(z.read(nn))).convert("RGB").resize((nres, nres), Image.LANCZOS)
            if nd:
                hgt = Image.open(io.BytesIO(z.read(nd))).convert("L").resize((nres, nres), Image.LANCZOS)
            else:
                hgt = Image.new("L", (nres, nres), 128)  # flat - parallax then does nothing, safely
            rgba = Image.merge("RGBA", (*nrm.split(), hgt))
            dstn = os.path.join(OUT, target.replace("/", os.sep) + "_nh.dds")
            nmipn = save_dds_mipped(rgba, dstn, "DXT5")  # DXT5: alpha survives, and alpha IS the height
            total += os.path.getsize(dstn)
            print("   normal+height %-40s %5d KB  %d mips (height in alpha)" % (target + "_nh.dds", os.path.getsize(dstn)//1024, nmipn))
        else:
            print("   NO normal map in zip - parallax will fall back to the generated one")

    print("total %.1f MB written to %s" % (total/1e6, OUT))


if __name__ == "__main__":
    main()

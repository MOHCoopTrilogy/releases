# -*- coding: utf-8 -*-
"""[user 2026-09-08] "upscale everything else on this map that hasnt been ... Id appreciate it being
4x upscaled honestly."

Upscales every texture m3l1a draws that is still below 2048, using the recipe proven by
docs/tools/upscale_skins.py and upscale_vehicles.py: Real-ESRGAN 4x, a validator (luma correlation
>= 0.65 plus a black-output guard) with a Lanczos fallback, and DDS output WITH A FULL MIP CHAIN.

WHAT DIFFERS FROM THE VEHICLE RUN, and why:

1. IT SHIPS 4x, NOT A 2x SUPERSAMPLE. The vehicle run rendered at 4x and downsampled to 2x. The
   user asked for 4x, so 4x is what lands - but CAPPED AT 2048 on the long side. Uncapped, the
   bunker concrete (a real 2048) would become 8192 and the run would add 1.0 GB to a texture pak
   that is already 1.2 GB; capped it is ~310 MB, and everything the map is actually authored at -
   the 512s and below, which is where the low-res you can see lives - still gets its full 4x.
   A source already at or above the cap is skipped: there is nothing to gain.

2. IT SHIPS INTO A 10-z PAK. 42 of the 158 targets are currently won by zzzzzzz_dds_hdmem.pk3,
   zzzzzzz_dds_override.pk3, zzzzzzzz_hd_seamfix.pk3 or zzzzzzzzz_coop_terrain.pk3, all of which
   OUT-SORT the coop texture pak (zzzzzz_, six z). Writing them into the normal tex pak would
   produce files that can never load - the exact failure the 2026-08 audit found 21 live instances
   of. zzzzzzzzzz_coop_hd_m3l1a.pk3 (ten z) out-sorts every one of them. `.pk3` is already excluded
   from build.ps1's pack sweep (build.ps1:146), so it is copied like the terrain pak, not repacked.

3. THE SOURCE IS THE WINNING FILE, NOT THE HIGHEST-RESOLUTION ONE. Whatever the engine loads today
   is what the player sees, so that is what gets improved - except that a "fake" resolution (a 1024
   that carries 512 of detail, which is the whole Higgins story) is upscaled from its own pixels
   anyway; ESRGAN reconstructs better from the blurry 1024 than from nothing.

  python docs/tools/upscale_m3l1a.py            run (resumable - skips outputs already written)
  python docs/tools/upscale_m3l1a.py --pack     just rebuild the pk3 from what is already staged
  python docs/tools/upscale_m3l1a.py --limit N  do N targets and stop (for a smoke run)
"""
import io
import os
import sys
import math
import time
import glob
import pickle
import struct
import zipfile
import subprocess

from PIL import Image

GL2 = os.path.join("G:", os.sep, "mohaa-gl2")
MODROOT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
ESR = r"C:\mohaa-coop-dev\_tools\realesrgan\realesrgan-ncnn-vulkan.exe"
STAGE = r"C:\mohaa-coop-dev\_hd_m3l1a"          # outside the mod tree: never swept into a pak
PAK = os.path.join(MODROOT, "zzzzzzzzzz_coop_hd_m3l1a.pk3")
PKL = os.path.join(os.path.expandvars(r"%TEMP%"), "m3l1a_upscale_targets.pkl")
WORK = os.path.join(os.path.expandvars(r"%TEMP%"), "m3l1a_up")
LOG = os.path.join(WORK, "log.txt")
os.makedirs(WORK, exist_ok=True)
os.makedirs(STAGE, exist_ok=True)

Image.MAX_IMAGE_PIXELS = None


def log(m):
    print(m, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(m + "\n")


def corr(a_img, b_img):
    a = list(a_img.convert("L").resize((64, 64)).getdata())
    b = list(b_img.convert("L").resize((64, 64)).getdata())
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a)) or 1
    vb = math.sqrt(sum((y - mb) ** 2 for y in b)) or 1
    return cov / (va * vb)


def brightness(img):
    d = list(img.convert("L").resize((64, 64)).getdata())
    return sum(d) / len(d)


def save_dds_mipped(img, path, fmt):
    """A DXT .dds WITH A FULL MIP CHAIN.

    TRAPS T6: "ship DXT .dds overrides with a full mip chain". Pillow's DDS writer emits level 0
    only, and R_LoadDDS does NOT synthesise mips for a DDS the way the engine does for TGA/JPG - so
    a mipless 2048 sheet aliases and shimmers at distance, which would make the upscale look WORSE
    than the texture it replaced at exactly the range you usually see it from.

    Each level is compressed by Pillow, then its 128-byte header is stripped and the payloads are
    concatenated under level 0's header with the mip fields patched - so the block encoding stays
    Pillow's and only the container changes.
    """
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
    struct.pack_into("<I", head, 8, struct.unpack_from("<I", head, 8)[0] | 0x20000)     # MIPMAPCOUNT
    struct.pack_into("<I", head, 28, len(levels))
    struct.pack_into("<I", head, 108, struct.unpack_from("<I", head, 108)[0] | 0x8 | 0x400000)
    with io.open(path, "wb") as f:
        f.write(bytes(head))
        for lv in levels:
            f.write(lv[128:])


def pak_path(tag):
    root, name = tag.split("/", 1)
    return os.path.join(GL2, root, name)


def build_pak():
    files = []
    for p in glob.glob(os.path.join(STAGE, "**", "*.dds"), recursive=True):
        rel = os.path.relpath(p, STAGE).replace(os.sep, "/")
        files.append((rel, p))
    files.sort()
    if not files:
        log("nothing staged - no pak written")
        return
    tmp = PAK + ".tmp"
    # deterministic: fixed timestamp and sorted order, so an unchanged run produces an identical pk3
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for rel, p in files:
            zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            z.writestr(zi, io.open(p, "rb").read())
    if os.path.exists(PAK):
        os.remove(PAK)
    os.rename(tmp, PAK)
    log("packed %d files -> %s (%.1f MB)" % (len(files), PAK, os.path.getsize(PAK) / 1048576.0))


def main():
    if "--pack" in sys.argv:
        build_pak()
        return
    targets = pickle.load(io.open(PKL, "rb"))
    limit = 0
    for i, a in enumerate(sys.argv):
        if a == "--limit":
            limit = int(sys.argv[i + 1])
    targets.sort(key=lambda r: -r["pct"])            # biggest visual share first
    if limit:
        targets = targets[:limit]
    log("=== m3l1a 4x upscale: %d targets, cap 2048 ===" % len(targets))

    done = fell = fail = skip = 0
    for n, r in enumerate(targets, 1):
        t = r["tex"]
        rel = t["base"] + ".dds"                     # textures/....dds
        out = os.path.join(STAGE, rel.replace("/", os.sep))
        if os.path.exists(out):
            skip += 1
            continue
        try:
            z = zipfile.ZipFile(pak_path(t["pak"]))
            raw = z.read(t["entry"])
            im = Image.open(io.BytesIO(raw))
            im.load()
        except Exception as e:
            log("UNREADABLE %-46s %s" % (r["shader"][:46], e))
            fail += 1
            continue

        ow, oh = r["ow"], r["oh"]
        alpha = None
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            a = im.convert("RGBA").split()[3]
            if min(a.getdata()) < 250:               # a real alpha channel, not an opaque one
                alpha = a
        rgb = im.convert("RGB")

        ti, to = os.path.join(WORK, "in.png"), os.path.join(WORK, "out.png")
        for f in (ti, to):
            if os.path.exists(f):
                os.remove(f)
        rgb.save(ti)
        try:
            subprocess.run([ESR, "-i", ti, "-o", to, "-s", "4", "-t", "256", "-j", "1:1:1"],
                           capture_output=True, timeout=900)
        except Exception:
            pass

        good = False
        up = None
        if os.path.exists(to):
            try:
                up = Image.open(to).convert("RGB")
                good = (corr(rgb, up) >= 0.65) and not (brightness(up) < 8 and brightness(rgb) > 20)
            except Exception:
                good = False
        big = up.resize((ow, oh), Image.LANCZOS) if good else rgb.resize((ow, oh), Image.LANCZOS)
        if not good:
            fell += 1
            log("FALLBACK(lanczos) %s" % r["shader"][:60])

        big = big.convert("RGBA")
        if alpha is not None:
            big.putalpha(alpha.resize((ow, oh), Image.LANCZOS))
            fmt = "DXT5"
        else:
            fmt = "DXT1"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        try:
            save_dds_mipped(big, out, fmt)
        except Exception as e:
            log("DDS-WRITE-FAIL %-40s %s" % (r["shader"][:40], e))
            fail += 1
            continue
        done += 1
        log("  %3d/%3d  %-46s %4dx%-4d -> %4dx%-4d %s%s"
            % (n, len(targets), r["shader"][:46], t["w"], t["h"], ow, oh, fmt,
               "  [was won by %s]" % os.path.basename(t["pak"]) if r.get("outranked") else ""))
        if done % 4 == 0:
            time.sleep(5)                            # sustained runs have corrupted output before

    log("DONE written=%d lanczos_fallback=%d failed=%d already_present=%d" % (done, fell, fail, skip))
    build_pak()


if __name__ == "__main__":
    main()

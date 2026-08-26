"""Vehicle / prop texture upscale (user-approved 2026-08-24).

Same proven recipe as the player-skin run (docs/tools/upscale_skins.py): Real-ESRGAN 4x, validator
(luma correlation >= 0.65 + black-output guard) with a Lanczos fallback, shipped as a 2x supersample,
GPU cooldown every 2 images.

THREE THINGS DIFFER, and each one is a trap the skin run did not have to face:

1. SOURCE IS THE RETAIL PAK, not a file in the mod tree. Nothing is overwritten, so there is no
   backup step - the original stays untouched inside main/mainta/maintt.

2. OUTPUT MUST BE .dds, NOT .tga. 211 of the 273 targets are currently won by a `.dds`, and
   R_LoadImage probes .dds BEFORE .jpg/.tga (renderergl2/tr_image.c). Shipping an upscaled .tga
   would lose to the retail .dds and the entire run would be invisible - which is exactly the
   failure the audit found 21 live instances of. Pillow writes DXT1/DXT5 with the correct FOURCC
   and the engine's loader accepts both (tr_image_dds.c:403-413).

3. PAK PRIORITY IS PART OF THE PROBLEM. Within a directory the LAST-SORTING pk3 wins, and
   maintt > mainta > main. The coop tex pak is `zzzzzz_co-op_hzm_mod_assets_tex.pk3` (6 z), which
   beats every stock pak (`pak1`, `Pak2`) but LOSES to `zzzzzzz_dds_*` (7 z) and
   `zzzzzzzz_hd_*` (8 z). Targets currently won by one of those are SKIPPED and reported rather
   than silently produced into a file that can never load.

Alpha: DXT5 when the source has a meaningful alpha channel, DXT1 otherwise (4x smaller).
"""
import io, os, math, time, pickle, zipfile, subprocess, sys
from PIL import Image

ROOT = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/"
ESR = "C:/mohaa-coop-dev/_tools/realesrgan/realesrgan-ncnn-vulkan.exe"
WORK = os.path.expandvars(r"%TEMP%\claude\C--mohaa-coop-dev\16396f85-9f5f-4159-8516-3f08362e0a18\scratchpad\upveh")
TARGETS = os.path.expandvars(r"%TEMP%\claude\C--mohaa-coop-dev\16396f85-9f5f-4159-8516-3f08362e0a18\scratchpad\veh2.pkl")
os.makedirs(WORK, exist_ok=True)
LOG = os.path.join(WORK, "log.txt")

# paks that OUT-SORT the coop tex pak - a target won by one of these cannot be beaten from it
OUTRANK = ("zzzzzzz_", "zzzzzzzz_")


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
    """Write a DXT .dds WITH A FULL MIP CHAIN.

    TRAPS T6 says plainly: "ship DXT .dds overrides with a full mip chain". Pillow's DDS writer emits
    level 0 only (mipCount=0), and R_LoadDDS then reports numMips=1 (tr_image_dds.c:300-305) - the
    engine does NOT synthesise mips for a DDS the way it does for TGA/JPG. A mipless 1024 vehicle
    sheet aliases and shimmers at distance, which would make the "upscale" look WORSE than the 512
    retail texture it replaced at exactly the range you usually see a vehicle from.

    Built by letting Pillow compress each level, then stripping its 128-byte header and concatenating
    the payloads under level 0's header with the mip fields patched - so the block encoding stays
    Pillow's and only the container changes.
    """
    import struct as _st

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
    flags = _st.unpack_from("<I", head, 8)[0] | 0x20000          # DDSD_MIPMAPCOUNT
    _st.pack_into("<I", head, 8, flags)
    _st.pack_into("<I", head, 28, len(levels))                   # dwMipMapCount
    caps = _st.unpack_from("<I", head, 108)[0] | 0x8 | 0x400000  # COMPLEX | MIPMAP
    _st.pack_into("<I", head, 108, caps)

    with io.open(path, "wb") as f:
        f.write(bytes(head))
        for lv in levels:
            f.write(lv[128:])


targets = pickle.load(io.open(TARGETS, "rb"))
skipped_rank = [t for t in targets if os.path.basename(t["win_pak"]).startswith(OUTRANK)]
work = [t for t in targets if t not in skipped_rank]
log("targets %d | skipped (out-ranked pak, cannot win from the coop pak) %d | to process %d"
    % (len(targets), len(skipped_rank), len(work)))
for t in skipped_rank:
    log("  SKIP-RANK %-52s won by %s" % (t["stem"].replace("textures/models/", ""), t["win_pak"]))

done = fell = fail = skipped = 0
for i, t in enumerate(sorted(work, key=lambda r: -(r["sw"] * r["sh"])), 1):
    stem = t["stem"]                                   # textures/models/vehicles/x/y
    out = os.path.join(ROOT, stem + ".dds").replace("/", os.sep)
    if os.path.exists(out):
        skipped += 1
        continue
    try:
        raw = zipfile.ZipFile(t["src_pak"]).read(t["src_entry"])
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        log("UNREADABLE %s : %s" % (stem, e)); fail += 1; continue

    w, h = im.size
    alpha = None
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        a = im.convert("RGBA").split()[3]
        if min(a.getdata()) < 250:                     # a real alpha channel, not an opaque one
            alpha = a
    rgb = im.convert("RGB")

    ti, to = os.path.join(WORK, "in.png"), os.path.join(WORK, "out.png")
    for f in (ti, to):
        if os.path.exists(f):
            os.remove(f)
    rgb.save(ti)
    try:
        subprocess.run([ESR, "-i", ti, "-o", to, "-s", "4", "-t", "256", "-j", "1:1:1"],
                       capture_output=True, timeout=300)
    except Exception:
        pass

    good = False
    if os.path.exists(to):
        up = Image.open(to).convert("RGB")
        good = (corr(rgb, up) >= 0.65) and not (brightness(up) < 8 and brightness(rgb) > 20)
    if good:
        two = up.resize((w * 2, h * 2), Image.LANCZOS)
    else:
        two = rgb.resize((w * 2, h * 2), Image.LANCZOS)
        fell += 1
        log("FALLBACK(lanczos) %s" % stem.replace("textures/models/", ""))

    if alpha is not None:
        two = two.convert("RGBA")
        two.putalpha(alpha.resize((w * 2, h * 2), Image.LANCZOS))
        fmt = "DXT5"
    else:
        two = two.convert("RGBA")                      # Pillow's DXT1 writer wants RGBA in
        fmt = "DXT1"

    os.makedirs(os.path.dirname(out), exist_ok=True)
    try:
        save_dds_mipped(two, out, fmt)
    except Exception as e:
        log("DDS-WRITE-FAIL %s : %s" % (stem, e)); fail += 1; continue

    done += 1
    if done % 2 == 0:
        time.sleep(10)                                 # GPU cooldown - sustained runs corrupt output
    if done % 20 == 0:
        log("  progress %d/%d done=%d fallback=%d fail=%d" % (i, len(work), done, fell, fail))

log("DONE: written=%d lanczos_fallback=%d failed=%d already_present=%d rank_skipped=%d"
    % (done, fell, fail, skipped, len(skipped_rank)))

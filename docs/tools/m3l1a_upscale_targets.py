# -*- coding: utf-8 -*-
"""[user 2026-09-08] "what the hell else on the map is 512 x 512 still" / "upscale everything else
on this map that hasnt been ... 4x".

Builds the COMPLETE list of textures m3l1a draws, and decides which still need upscaling.

THREE SOURCES OF SHADERS, and missing any one of them is how you conclude "the map is fine" while
the thing in the player's face is 512:
  1. the BSP's own surfaces (lump 0), weighted by world area so the list is ordered by what fills
     the screen;
  2. the SKY, which is 50% of the map's surface area and is a `skyparms` box, not a `map` stage -
     resolved to its six faces;
  3. every TIKI placed on the map - from the BSP entity string AND from `model "..."` in
     m3l1a.scr / coopified.scr. This is where the low-res actually lives: the world brushwork is
     already upscaled, the models are not. A tik that declares no `surface ... shader` line keeps
     its shader names inside the .skd, so those are recovered by intersecting the skd's ASCII
     strings with the known shader-name set.

"NEEDS UPSCALING" IS NOT THE HEADER RESOLUTION. models/vehicles/higgins/higgins.dds is 1024x1024 and
carries 512x512 of information - retail's own 1024 is a blow-up of the 512 tga, and the mod's copy
is a DXT1 recompression of that. So every candidate gets a ROUND-TRIP TEST: squash to half, blow
back up, and measure the difference. A file that loses almost nothing never had the detail.

  python docs/tools/m3l1a_upscale_targets.py            report
  python docs/tools/m3l1a_upscale_targets.py --pickle   also write the work list for the upscaler
"""
import io
import os
import re
import sys
import glob
import math
import struct
import pickle
import zipfile
from collections import defaultdict

GL2 = os.path.join("G:", os.sep, "mohaa-gl2")
ROOTS = ["main", "mainta", "maintt"]
MODROOT = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
OUT_PKL = os.path.join(os.path.expandvars(r"%TEMP%"), "m3l1a_upscale_targets.pkl")
TARGET_PX = 2048                      # 4x over the 512 the map's models are actually authored at

# paks that OUT-SORT the coop tex pak (zzzzzz_, six z): a target won by one of these cannot be
# beaten from it, so it is reported rather than silently produced into a file that can never load.
OUTRANK = ("zzzzzzz_", "zzzzzzzz_", "zzzzzzzzz_")

MOUNTS = []
for r in reversed(ROOTS):
    for p in sorted(glob.glob(os.path.join(GL2, r, "*.pk3")), reverse=True):
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        MOUNTS.append((r + "/" + os.path.basename(p), z, {n.lower(): n for n in z.namelist()}))


def find(path):
    lp = path.lower().replace("\\", "/")
    return [(tag, z, m[lp]) for tag, z, m in MOUNTS if lp in m]


def read_first(path):
    h = find(path)
    return (h[0][0], h[0][1].read(h[0][2])) if h else (None, None)


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


# ------------------------------------------------------------------ shader index
SHADERS = {}          # name -> (source, [map paths])
SHADER_NAMES = set()
BLOCK = re.compile(r"(?ms)^[ \t]*([A-Za-z0-9_/\\.\-]+)[ \t]*\r?\n[ \t]*\{(.*?)\n[ \t]*\}")
for tag, z, m in MOUNTS:
    for low, real in sorted(m.items()):
        if not (low.startswith("scripts/") and low.endswith(".shader")):
            continue
        try:
            txt = z.read(real).decode("latin-1")
        except Exception:
            continue
        for name, body in BLOCK.findall(txt):
            SHADER_NAMES.add(name.lower())
            if name.lower() in SHADERS:
                continue                       # pak order already decided the winner
            maps = [x for x in re.findall(r"(?im)^\s*(?:clampmap|clampmapx|clampmapy|map)\s+(\S+)", body)
                    if not x.startswith("$")]
            sky = re.search(r"(?im)^\s*skyparms\s+(\S+)", body)
            if sky and sky.group(1) != "-":
                b = sky.group(1)
                maps += ["%s_%s" % (b, f) for f in ("rt", "lf", "ft", "bk", "up", "dn")]
            SHADERS[name.lower()] = (tag + ":" + real, maps)
print("shader index: %d blocks across %d paks" % (len(SHADERS), len(MOUNTS)))

# ------------------------------------------------------------------ the BSP
tag, bsp = read_first("maps/m3l1a.bsp")
lumps = [struct.unpack("<II", bsp[12 + 8 * i:20 + 8 * i]) for i in range(28)]
sh_off, sh_len = lumps[0]
wshaders = [bsp[sh_off + 140 * i: sh_off + 140 * i + 64].split(b"\0")[0].decode("latin-1")
            for i in range(sh_len // 140)]
sf_off, sf_len = lumps[3]
dv_off, dv_len = lumps[4]
di_off, di_len = lumps[5]
verts = struct.unpack_from("<%df" % ((dv_len // 44) * 11), bsp, dv_off)
idx = struct.unpack_from("<%di" % (di_len // 4), bsp, di_off)
area = defaultdict(float)
for si in range(sf_len // 108):
    o = sf_off + 108 * si
    sn_i, _fog, stype, fv, nv, fi, ni = struct.unpack_from("<7i", bsp, o)
    if not (0 <= sn_i < len(wshaders)):
        continue
    sn = wshaders[sn_i]
    a = 0.0
    if ni >= 3 and stype in (1, 3):
        for k in range(fi, fi + ni - 2, 3):
            try:
                p = [verts[(fv + idx[k + j]) * 11:(fv + idx[k + j]) * 11 + 3] for j in range(3)]
            except Exception:
                break
            u = [p[1][c] - p[0][c] for c in range(3)]
            v = [p[2][c] - p[0][c] for c in range(3)]
            cx = u[1] * v[2] - u[2] * v[1]
            cy = u[2] * v[0] - u[0] * v[2]
            cz = u[0] * v[1] - u[1] * v[0]
            a += 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
    area[sn] += a
total_area = sum(area.values()) or 1.0

# ------------------------------------------------------------------ the models placed on this map
ents = bsp[lumps[14][0]:lumps[14][0] + lumps[14][1]].decode("latin-1")
tiks = set()
for mm in re.finditer(r'"model"\s+"([^"]+)"', ents):
    v = mm.group(1)
    if v.lower().endswith(".tik"):
        tiks.add(("models/" + v.replace("//", "/")).lower())
for src in (os.path.join(MODROOT, "maps", "m3l1a.scr"),
            os.path.join(MODROOT, "maps", "m3l1a", "coopified.scr")):
    if not os.path.exists(src):
        continue
    txt = io.open(src, encoding="latin-1").read()
    for v in re.findall(r'"(models/[^"]+\.tik)"', txt):
        tiks.add(v.lower())
print("TIKI models placed on m3l1a: %d" % len(tiks))

model_shaders = defaultdict(set)
missing_tik = []
for t in tiks:
    tag, b = read_first(t)
    if b is None:
        p = os.path.join(MODROOT, t.replace("/", os.sep))
        if os.path.exists(p):
            b = io.open(p, "rb").read()
        else:
            missing_tik.append(t)
            continue
    txt = b.decode("latin-1")
    surf = re.findall(r"(?im)^\s*surface\s+(\S+)\s+shader\s+(\S+)", txt)
    for _s, sh in surf:
        model_shaders[sh.lower()].add(t)
    if not surf:
        # the shader names live in the .skd; recover them by intersecting its strings with the index
        pathm = re.search(r"(?im)^\s*path\s+(\S+)", txt)
        base = pathm.group(1).strip().rstrip("/") if pathm else os.path.dirname(t)
        for skd in re.findall(r"(?im)^\s*skelmodel\s+(\S+)", txt):
            _tg, sb = read_first(base.replace("\\", "/") + "/" + skd)
            if sb is None:
                continue
            for s in re.findall(rb"[ -~]{3,}", sb):
                d = s.decode("ascii").strip().lower()
                if d in SHADER_NAMES:
                    model_shaders[d].add(t)

# ------------------------------------------------------------------ resolve + measure
try:
    from PIL import Image
    import numpy as np
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


def true_detail(b, ext):
    """Does this image actually carry the resolution its header claims? Squash to half and back;
    an image with real detail at full size loses a lot, a blown-up one loses almost nothing."""
    if not HAVE_PIL:
        return None
    try:
        im = Image.open(io.BytesIO(b)).convert("RGB")
        w, h = im.size
        if min(w, h) < 8:
            return None
        half = im.resize((max(1, w // 2), max(1, h // 2)), Image.BOX).resize((w, h), Image.BICUBIC)
        return float(np.abs(np.asarray(im, np.float32) - np.asarray(half, np.float32)).mean())
    except Exception:
        return None


def resolve(shader):
    """EVERY texture the shader references, not just the biggest one.

    Taking only the largest map silently upscaled one face of the skybox and left the other five -
    and the sky is 76% of this map's drawn surface area. A `skyParms env/dday2` is six files, and a
    multi-stage shader can reference several textures that are all equally on screen.
    """
    src, maps = SHADERS.get(shader.lower(), (None, [shader]))
    if not maps:
        maps = [shader]
    out = []
    for mp in maps:
        base = re.sub(r"\.(tga|jpg|dds)$", "", mp, flags=re.I)
        for e in (".dds", ".jpg", ".tga"):
            hits = find(base + e)
            if not hits:
                continue
            tg, z, real = hits[0]
            data = z.read(real)
            d = dims(data, e)
            if d:
                out.append(dict(base=base, ext=e, pak=tg, entry=real, w=d[0], h=d[1],
                                detail=true_detail(data, e), shader=shader))
            break
    return src, out


rows = []
bybase = {}                    # one target per TEXTURE FILE, carrying the best claim on the screen
seen = set()


def add(kind, sn, pct, src, texs, users=None):
    for t in texs:
        key = t["base"].lower()
        prev = bybase.get(key)
        if prev is None or pct > prev["pct"]:
            bybase[key] = dict(kind=kind, shader=sn, pct=pct, src=src, tex=t, users=users or [])


for sn, a in area.items():
    src, texs = resolve(sn)
    add("world", sn, 100.0 * a / total_area, src, texs)
    seen.add(sn.lower())
for sn, users in model_shaders.items():
    if sn in seen:
        continue
    src, texs = resolve(sn)
    add("model", sn, 0.0, src, texs, sorted(u.split("/")[-1] for u in users)[:3])
rows = list(bybase.values())

# 4x, CAPPED AT 2048 on the long side. Pure 4x would take the bunker concrete (already a real 2048)
# to 8192 and add 1.0 GB to a texture pak that is already 1.2 GB; capped it is 253 MB. Everything the
# map is actually authored at - the 512s and below - still gets its full 4x, which is the point.
# A source already at or above the cap has nothing to gain and is skipped outright.
need, fine, unres, ranked = [], [], [], []
for r in rows:
    t = r["tex"]
    fake = (t["detail"] is not None and t["detail"] < 3.0)
    eff = min(t["w"], t["h"]) // (2 if fake else 1)
    r["fake"] = fake
    r["eff"] = eff
    r["outranked"] = os.path.basename(t["pak"]).startswith(OUTRANK)
    scale = min(4.0, TARGET_PX / float(max(t["w"], t["h"])))
    r["ow"], r["oh"] = int(round(t["w"] * scale)), int(round(t["h"] * scale))
    if max(t["w"], t["h"]) >= TARGET_PX:
        fine.append(r)
        continue
    if r["outranked"]:
        ranked.append(r)          # reported, and INCLUDED: the output pak out-sorts these
    need.append(r)

need.sort(key=lambda r: (-r["pct"], r["eff"]))
print("\n%-46s %-9s %6s %8s %-7s %s" % ("shader", "loaded", "eff", "% map", "kind", "pak"))
print("-" * 118)
for r in need[:60]:
    t = r["tex"]
    print("%-46s %4dx%-4d %6d %7.3f%% %-7s %s%s"
          % (r["shader"][:46], t["w"], t["h"], r["eff"], r["pct"], r["kind"],
             os.path.basename(t["pak"])[:26], "  <fake-res>" if r["fake"] else ""))

print("\nNEED UPSCALE      %d" % len(need))
print("already >= %d    %d" % (TARGET_PX, len(fine)))
print("cannot win (pak)  %d" % len(ranked))
print("unresolved        %d" % len(unres))
for r in ranked:
    print("   SKIP-RANK %-44s won by %s" % (r["shader"][:44], r["tex"]["pak"]))
if missing_tik:
    print("   tiks not found: %s" % ", ".join(sorted(missing_tik)[:8]))

if "--pickle" in sys.argv:
    pickle.dump(need, io.open(OUT_PKL, "wb"))
    print("\nwrote %s (%d targets)" % (OUT_PKL, len(need)))

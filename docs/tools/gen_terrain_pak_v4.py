# -*- coding: utf-8 -*-
"""Terrain pak v4 = v3 + the ground textures drawn ONLY on multiplayer maps (bug-2950 family; MP approved 2026-09-26).

Base: terrain pak v3 (sha256 0551ae73..., asserted) = gen_terrain_pak_v3.py's output, installed in the mod folder.
Every v3 member stays byte-identical. v4 ADDS:

  1. MP-ONLY GROUND TEXTURES, colour re-matched to retail with the v3 recipe (gen_terrain_pak_v3.banded_match: hue
     to retail, 4-16u band into 0.9-1.1x retail with the photo's own gain capped, finest band untouched, measured
     'texel' exception, periodic FFT filters, exponential toe; own DXT encoder, 2x2 box mips) and the v3 gates.
     Scope, decided per IMAGE from every BSP of the PLAYER stack (retail paks + manifests/latest.json; the dev-only
     y_hzm_maptour.pk3 and the loose GOG maps are not in it):
       ground      terrain patches + brush/soup/bezier triangles with |n.z| >= 0.7 (the census rule of the vet and
                   tilefix) make up >= GROUND_SHARE of the image's drawn area - a wall texture that only caps a
                   ledge is not a ground texture;
       MP-only     EVERY map that draws it (any surface) is maps/dm|obj|lib/*, and no TIKI model references it;
       Omaha       excluded BY MAP (m3l1a, m3l1b, e3l1, e3l2 and their _sml, obj/obj_team3) AND BY NAME (V2.OMAHA:
                   omaha/obeach/ocean/seabed/wetsand/shoreline/surf/wake ...) - absolute, user rule;
       diffuse     used only as the first-stage, first-bundle, opaque diffuse of its shaders (no alphaFunc / blend /
                   later-stage use: its alpha or blend role would change);
       owned       not shipped in any extension by a pak that sorts ABOVE this one (tilefix, m3l1a, shadowfix, skies,
                   in the GOG install or the mod folder): a copy here would be dead;
       retail      has a retail counterpart (retail paks, non-DDS original preferred), same aspect;
       live        today's file is NOT retail (an HD pack's copy) - matching retail to itself changes nothing;
       needs it    today's file FAILS a v3 gate (chroma > 3, brightness > 2%, 4-16u structure outside 0.8-1.25x
                   retail); a texture that already passes is left alone.
     Output format = today's format: DDS DXT1 -> DXT1 with today's header; DDS DXT5 -> DXT5 with today's ALPHA blocks
     copied verbatim at every level and colour from the own encoder (the Pillow DXT5 red-skew guard, bug-2953);
     jpg/tga -> same format and size.
  2. gl2 RELIEF SIBLINGS (bug-2984): for a DDS diffuse, R_HZM_GenerateNormalMapFromSource (tr_image.c:3109) builds
     the generated relief from the first png/tga/jpg SIBLING (imageLoaders order, tr_image.c:2444), not the DDS.
     For every DDS this pak changes - v4's and v3's composites - whose relief is generated (no authored _nh) and
     whose sibling exists and is not owned by a pak above this one: ship <name>.<today's sibling ext> at today's
     sibling size, made from the NEW image (v4: the float output; v3: its decoded level 0), so relief matches what
     is drawn. JPEG q95 with today's chroma subsampling, TGA RLE, PNG - deterministic. With
     r_ext_compressed_textures 0 a sibling can also be the diffuse, so it carries the same brightness gate.

GATES (v3's, per changed texture, on the ENCODED file): chroma <= 3 and |luma - retail| <= 2% of retail; fine grain
<= 1.15 x max(retail, today); 4-16u structure 0.8-1.25x retail (n/a when retail's texel is coarser than 2u - it cannot
resolve the band - then only the hue is matched); wrap seam not worse (decoded vs block lines, and before encode);
mips >= 16 px within 1 level of level 0, smaller within max(today, 1.5) (565 limit); no encoder lean (decoded level-0 mean within
0.75 of the float per channel); 4-colour blocks; today's header. Pak: v3 members byte-identical, sorted, fixed
timestamps, CRC, every new member (and sibling as the height source) resolves to this pak on the live and plain-GOG
stacks, nothing Omaha by name or by map; two runs give the same sha256.

  python docs/tools/gen_terrain_pak_v4.py --out <dir>          scan + build + sheets
  --scan-only   print the scope funnel and stop      --jobs N   worker processes (default 6)
  --no-sheets   --no-stack-check
It never writes outside --out and never touches hzm-mohaa-coop-mod or a game folder.
"""
import argparse, hashlib, io, json, os, re, struct, sys, time, zipfile
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_terrain_pak_v2 as V2          # noqa: E402
import gen_terrain_pak_v3 as V3          # noqa: E402

Image.MAX_IMAGE_PIXELS = None
REPO = V2.REPO
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
SRC_DEFAULT = V2.SRC_DEFAULT
SRC_SHA = "0551ae731009f761d131d1a636c6e6984550045ab068e3532933573c46b84849"      # terrain v3 (bug-2985)
PAK_NAME = V2.PAK_NAME
GOG_DEFAULT = V2.GOG_DEFAULT
FIXED_TS = (2026, 9, 27, 0, 0, 0)

MP_PREFIX = ("maps/dm/", "maps/obj/", "maps/lib/")
OMAHA_MAPS = ("m3l1a", "m3l1b", "e3l1", "e3l2", "obj/obj_team3")
GATE_CHROMA, GATE_BRIGHT, GATE_FINE, GATE_MID = 3.0, 0.02, 1.15, (0.8, 1.25)
GROUND_SHARE = 0.25             # a 'ground texture': at least this share of its drawn area faces up/down
MAX_RETAIL_TEXEL_U = 2.0         # retail texel coarser than this cannot resolve the 4u band edge
LEAN_MAX = 0.75                  # |decoded level-0 mean - float mean| per channel (encoder lean guard, bug-2953)
SMALL_MIP_MAX = 1.5              # levels < 16 px: a BC1 block's 565 palette steps 8.2 levels on R/B, its 1/3 points
                                 # 2.7 apart, so a flat tiny level can miss its mean by up to 1.37 - or today's drift
SAME_ART_R = 0.8                 # low-pass luma correlation live vs retail at which the colour FIELD is transferred
IMG_EXT = (".dds", ".jpg", ".tga", ".png", ".jpeg")          # R_LoadImage order for a .tga request, compression on
HEIGHT_EXT = (".png", ".tga", ".jpg", ".jpeg")               # imageLoaders order (tr_image.c:2444)
RETAIL_EXT = (".jpg", ".tga", ".png", ".jpeg", ".dds")       # the original art first, the retail DXT copy last

gate = V2.gate
sha = V2.sha


def is_omaha_map(p):
    k = p[5:-4]
    return any(k == o or k.startswith(o + "_") for o in OMAHA_MAPS)


def is_mp_map(p):
    return p.startswith(MP_PREFIX)


# ============================================================================================ shaders
_TOK = re.compile(r'"[^"]*"|\{|\}|[^\s{}"]+')


def parse_shader_roles(txt):
    """{shader: [(image base, role)]}; role 'diffuse' = first stage, first bundle, no alphaFunc and no blend that
    reads it as anything but an opaque replace; everything else 'other'."""
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    out, depth, name = {}, 0, None
    stages, cur = [], None
    for ln in txt.replace("\r", "").split("\n"):
        toks = _TOK.findall(re.sub(r"//.*", "", ln))
        line = []
        for t in toks:
            if t == "{":
                depth += 1
                if depth == 1:
                    stages = []
                elif depth == 2:
                    cur = dict(imgs=[[]], alpha=False, blend=None)
            elif t == "}":
                if depth == 2 and cur is not None:
                    stages.append(cur)
                    cur = None
                depth -= 1
                if depth == 0 and name is not None:
                    roles = []
                    for si, st in enumerate(stages):
                        for bi, imgs in enumerate(st["imgs"]):
                            for im in imgs:
                                opaque = not st["alpha"] and st["blend"] in (None, "gl_one gl_zero")
                                roles.append((im, "diffuse" if (si == 0 and bi == 0 and opaque) else "other"))
                    out.setdefault(name, roles)
                    name = None
            elif depth == 0:
                name = t.strip('"').lower().replace("\\", "/")
            else:
                line.append(t.strip('"'))
        if depth == 2 and cur is not None and line:
            k = line[0].lower()
            if k == "nextbundle":
                cur["imgs"].append([])
            elif k in ("map", "clampmap", "clampmapx", "clampmapy") and len(line) > 1:
                if not line[1].startswith("$"):
                    cur["imgs"][-1].append(V3.strip_ext(line[1].lower().replace("\\", "/")))
            elif k in ("animmap", "animmapphase") and len(line) > 2:
                cur["imgs"][-1] += [V3.strip_ext(x.lower().replace("\\", "/")) for x in line[2 if k == "animmap" else 3:]
                                    if not x.startswith("$")]
                cur["alpha"] = True                     # animated: never touch
            elif k == "alphafunc":
                cur["alpha"] = True
            elif k == "blendfunc":
                cur["blend"] = " ".join(x.lower() for x in line[1:3])
    return out


def shader_roles(stack):
    """name -> [(image, role)] with T6 precedence (highest pak; within a pak the alphabetically first file)."""
    best = {}
    for path in sorted(p for p in stack.copies if p.startswith("scripts/") and p.endswith(".shader")):
        i, m = stack.winner(path)
        for nm, roles in parse_shader_roles(stack.read(i, m).decode("latin1")).items():
            if nm not in best or i > best[nm][0]:
                best[nm] = (i, roles)
    return {k: v[1] for k, v in best.items()}


def tiki_images(stack, shaders):
    """Images any TIKI surface reaches (surface ... shader X): a model can be spawned on any map."""
    out = set()
    for path in sorted(p for p in stack.copies if p.endswith(".tik")):
        i, m = stack.winner(path)
        txt = stack.read(i, m).decode("latin1", "replace")
        for mt in re.finditer(r"(?im)^\s*surface\s+\S+\s+shader\s+(\S+)", txt):
            s = mt.group(1).strip('"').lower().replace("\\", "/")
            if s in shaders:
                out.update(im for im, r in shaders[s])
            out.add(V3.strip_ext(s))
            out.add(V3.strip_ext(os.path.dirname(path) + "/" + s))
    return out


# ================================================================================================ BSP
def bsp_scan4(b):
    """-> shader names, {idx: surfaces+patches}, {idx: ground area}, {idx: [(U, area)]} (ground only)."""
    ident, version = struct.unpack_from("<4si", b, 0)
    n = 29 if version <= 18 else 28
    L = [struct.unpack_from("<ii", b, 12 + 8 * i) for i in range(n)]
    if version <= 18:
        L = L[:13] + L[14:]

    def lump(i):
        o, l = L[i]
        return b[o:o + l]
    sh = lump(0)
    names = [sh[i * 140:i * 140 + 64].split(b"\0")[0].decode("latin1").lower().replace("\\", "/")
             for i in range(len(sh) // 140)]
    dv = lump(4)
    nv = len(dv) // 44
    V = np.frombuffer(dv[:nv * 44], dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2),
                                                     ("n", "<f4", 3), ("c", "u1", 4)]))
    IX = np.frombuffer(lump(5), "<i4")
    sfr = lump(3)
    cnt, gnd, dens, tot = {}, {}, {}, {}

    def tris(idx, sn):
        P = V["xyz"][idx].astype(np.float64)
        S = V["st"][idx].astype(np.float64)
        cr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ar = 0.5 * np.linalg.norm(cr, axis=1)
        nz = np.where(ar > 1e-6, cr[:, 2] / np.maximum(2 * ar, 1e-9), 0.0)
        g = np.abs(nz) >= 0.7
        tot[sn] = tot.get(sn, 0.0) + float(ar.sum())
        if not g.any():
            return
        a = float(ar[g].sum())
        gnd[sn] = gnd.get(sn, 0.0) + a
        d1, d2 = S[g, 1] - S[g, 0], S[g, 2] - S[g, 0]
        u = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]).sum()
        if a > 1.0 and u > 1e-9:
            dens.setdefault(sn, []).append((float(np.sqrt(a / u)), a))
    for i in range(len(sfr) // 108):
        sn, fog, st, fv, nvx, fi, nix = struct.unpack_from("<7i", sfr, i * 108)
        if not (0 <= sn < len(names)) or st not in (1, 2, 3):
            continue
        cnt[sn] = cnt.get(sn, 0) + 1
        if st in (1, 3) and nix >= 3:
            tris(IX[fi:fi + nix].reshape(-1, 3) + fv, sn)
        elif st == 2:
            pw, ph = struct.unpack_from("<2i", sfr, i * 108 + 96)
            if pw >= 2 and ph >= 2 and pw * ph == nvx:
                g = np.arange(pw * ph).reshape(ph, pw)
                q = np.stack([g[:-1, :-1].ravel(), g[:-1, 1:].ravel(), g[1:, :-1].ravel(), g[1:, 1:].ravel()], 1)
                tris(np.concatenate([q[:, [0, 1, 2]], q[:, [1, 3, 2]]]) + fv, sn)
    tr = lump(22)
    for i in range(len(tr) // 388):
        o = i * 388
        tc = struct.unpack_from("<8f", tr, o + 4)
        shn = struct.unpack_from("<H", tr, o + 40)[0]
        cnt[shn] = cnt.get(shn, 0) + 1
        gnd[shn] = gnd.get(shn, 0.0) + 512.0 * 512.0
        tot[shn] = tot.get(shn, 0.0) + 512.0 * 512.0
        ss = max(abs(tc[4] - tc[0]), abs(tc[2] - tc[0]))
        tt = max(abs(tc[5] - tc[1]), abs(tc[3] - tc[1]))
        if ss > 1e-6 and tt > 1e-6:
            dens.setdefault(shn, []).append((512.0 / float(np.sqrt(ss * tt)), 512.0 * 512.0))
    return names, cnt, gnd, dens, tot


def census(stack):
    shaders = shader_roles(stack)
    img = {}                              # image -> dict(maps=set, gmaps={map: area}, roles=set, shaders=set, dens=[])
    maps = sorted(p for p in stack.copies if p.startswith("maps/") and p.endswith(".bsp"))
    readable = []
    for path in maps:
        i, m = stack.winner(path)
        b = stack.read(i, m)
        if b[:4] not in (b"2015", b"EALA"):
            continue
        readable.append(path)
        names, cnt, gnd, dens, tot = bsp_scan4(b)
        for si, c in cnt.items():
            nm = names[si]
            roles = shaders.get(nm, [(V3.strip_ext(nm), "diffuse")])
            for im, role in roles:
                d = img.setdefault(im, dict(maps=set(), gmaps={}, roles=set(), shaders=set(), dens=[], area=0.0))
                d["area"] += tot.get(si, 0.0)
                d["maps"].add(path)
                d["roles"].add(role)
                d["shaders"].add(nm)
                if si in gnd and role == "diffuse":
                    d["gmaps"][path] = d["gmaps"].get(path, 0.0) + gnd[si]
                    if not is_omaha_map(path):
                        d["dens"] += dens.get(si, [])
    return shaders, img, readable


def area_median(d):
    if not d:
        return None
    v = np.array(sorted(d))
    cw = np.cumsum(v[:, 1])
    return float(v[np.searchsorted(cw, cw[-1] / 2.0), 0])


# ============================================================================================ scope
def pak_rank_name(stack, i):
    return os.path.basename(stack.srcs[i][1]).lower()


def above_names(gog, extra=()):
    """Lower-case image bases shipped (any extension) by a pak that sorts above PAK_NAME - GOG maintt and the
    mod folder (tilefix / m3l1a / shadowfix / skies ride there before they are deployed) - plus any STAGED pak
    named with --also-above (e.g. a tilefix build not yet in the mod folder)."""
    out, paks = {}, list(extra)
    for d in (os.path.join(gog, "maintt"), MOD):
        for p in sorted(os.listdir(d)):
            if p.lower().endswith(".pk3") and V2.fs_key(p) > V2.fs_key(PAK_NAME):
                paks.append(os.path.join(d, p))
    for p in paks:
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                nl = n.lower().replace("\\", "/")
                if nl.startswith("textures/"):
                    out.setdefault(V3.strip_ext(nl), set()).add(os.path.basename(p))
    return out, paks


def winner_ext(stack, base, exts, retail=None, skip=()):
    """First extension in `exts` with a copy; highest-priority copy of it. retail True/False filters."""
    for e in exts:
        for i, m in reversed(stack.copies.get(base + e, [])):
            pn = pak_rank_name(stack, i)
            if pn in skip:
                continue
            is_ret = bool(V3.RETAIL_PAK.match(pn))
            if retail is not None and is_ret != retail:
                continue
            return dict(ext=e, i=i, member=m, pak=pn, retail=is_ret)
    return None


def scope(stack, img, tiks, owned, v3_bases):
    """-> (candidates [dict], funnel {reason: [bases]})"""
    funnel = {}
    cands = []

    def drop(reason, b):
        funnel.setdefault(reason, []).append(b)
    for b in sorted(img):
        d = img[b]
        if not d["gmaps"]:
            continue                                            # not ground anywhere
        if not b.startswith("textures/"):
            drop("not under textures/", b)
            continue
        if not all(is_mp_map(p) for p in d["maps"]):
            continue                                            # drawn on a campaign / lobby / briefing map
        drop_r = None
        gshare = sum(d["gmaps"].values()) / max(d["area"], 1e-9)
        if any(is_omaha_map(p) for p in d["maps"]):
            drop_r = "Omaha by map"
        elif V2.OMAHA.search(b):
            drop_r = "Omaha by name"
        elif b in tiks:
            drop_r = "TIKI model uses it"
        elif "other" in d["roles"]:
            drop_r = "alpha / blend / non-diffuse use"
        elif gshare < GROUND_SHARE:
            drop_r = "mostly wall (ground < %d%% of its drawn area)" % round(100 * GROUND_SHARE)
        elif b in v3_bases:
            drop_r = "v3 member"
        elif b in owned:
            drop_r = "owned by a pak above (%s)" % ",".join(sorted(owned[b]))
        if drop_r:
            drop(drop_r, b)
            continue
        live = winner_ext(stack, b, IMG_EXT)
        ret = winner_ext(stack, b, RETAIL_EXT, retail=True)
        if not ret:
            drop("no retail counterpart", b)
            continue
        if live["retail"]:
            drop("today's file is retail", b)
            continue
        U = area_median(d["dens"])
        if not U:
            drop("no ground density sample", b)
            continue
        cands.append(dict(base=b, live=live, ret=ret, U=U, maps=sorted(d["maps"]), ground_share=round(gshare, 3),
                          gmaps={k: round(v) for k, v in sorted(d["gmaps"].items())}, shaders=sorted(d["shaders"])))
    return cands, funnel


# ============================================================================================ images
_WSTACK = None


def _init_worker(gog):
    global _WSTACK
    _WSTACK = V3.Stack(gog)


def read_img(stack, rec):
    return stack.read(rec["i"], rec["member"])


def decode(b, ext):
    """Level 0 as float RGBA + DDS info (DXT1/DXT5 parsed; a DX10 header - hdmem's BC7 - decoded by Pillow, info
    fourcc b'DX10')."""
    if ext == ".dds":
        if b[84:88] == b"DX10":
            im = Image.open(io.BytesIO(b))
            im.load()
            h, w = struct.unpack_from("<II", b, 12)
            return np.asarray(im.convert("RGBA")).astype(np.float64), dict(fourcc=b"DX10", w=w, h=h,
                                                                             dxgi=struct.unpack_from("<I", b, 128)[0])
        info = V2.dds_parse(b)
        return V2.dds_decode_level(b, info, 0).astype(np.float64), info
    im = Image.open(io.BytesIO(b))
    im.load()
    return np.asarray(im.convert("RGBA")).astype(np.float64), None


def bc1_exact_decode(blk, H, Wd):
    """Spec BC1 4-colour decode in float (the palette the encoder optimises), cropped to H x Wd."""
    H4, W4 = max(4, (H + 3) // 4 * 4), max(4, (Wd + 3) // 4 * 4)
    b = np.frombuffer(blk, np.uint8).reshape(-1, 8)
    c0 = b[:, 0].astype(np.int64) | (b[:, 1].astype(np.int64) << 8)
    c1 = b[:, 2].astype(np.int64) | (b[:, 3].astype(np.int64) << 8)
    pal = V2._palette(np.stack([c0 >> 11, (c0 >> 5) & 63, c0 & 31], 1), np.stack([c1 >> 11, (c1 >> 5) & 63, c1 & 31], 1))
    bits = (b[:, 4:8].astype(np.uint64) << (8 * np.arange(4, dtype=np.uint64))).sum(1)
    idx = ((bits[:, None] >> (2 * np.arange(16, dtype=np.uint64))) & np.uint64(3)).astype(np.int64)
    R = np.take_along_axis(pal, idx[..., None].repeat(3, -1), 1)
    return R.reshape(H4 // 4, W4 // 4, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(H4, W4, 3)[:H, :Wd]


DC_STEPS, DC_RANGE, DC_OK = 7, 4.0, 0.1


def bc1_encode_dc(img):
    """V3.bc1_encode with the image mean held. Found building v4: on flat, saturated art (carpet, panelling, dark
    river bed) the per-block 565 rounding repeats block after block, so the decoded mean leans up to 1.8 levels on
    R/B - the very colour this pak exists to match. Feeding the error back overshoots (the quantiser is a staircase:
    -1.6 -> +1.4 -> -1.3 ...), so instead bisect a per-channel INPUT offset (|offset| <= DC_RANGE) on the exact
    spec decode's mean error and keep the encode with the smallest |lean|. The image content is not altered: only
    where the encoder's rounding falls moves."""
    H, Wd = img.shape[:2]
    img = np.asarray(img, np.float64)

    def run(off):
        blk = V3.bc1_encode(np.clip(img + off, 0, 255))
        return blk, (bc1_exact_decode(blk, H, Wd) - img).reshape(-1, 3).mean(0)
    off = np.zeros(3)
    blk, lean = run(off)
    best = (float(np.abs(lean).max()), blk)
    lo = np.where(lean < 0, 0.0, -DC_RANGE)
    hi = np.where(lean < 0, DC_RANGE, 0.0)
    for _ in range(DC_STEPS):
        if best[0] < DC_OK:
            break
        off = 0.5 * (lo + hi)
        blk, lean = run(off)
        m = float(np.abs(lean).max())
        if m < best[0]:
            best = (m, blk)
        lo = np.where(lean < 0, off, lo)                       # decoded too dark on this channel: push the input up
        hi = np.where(lean < 0, hi, off)
    return best[1]


def encode_dds_v4(level0, today_dds, fourcc):
    """DXT1 (today's header) / DXT5 (today's header and ALPHA blocks verbatim at every level) / DX10 today -> DXT1
    with a new header (gl1 cannot read DX10; it drew the jpg/tga). Float 2x2 box mips to 1x1, each level encoded
    with bc1_encode_dc - never Pillow (bug-2953)."""
    if fourcc == b"DX10":
        H, Wd = level0.shape[:2]
        hdr, _ = V2.encode_level(np.zeros((H, Wd, 3), np.uint8), "DXT1")
        hdr = bytearray(hdr)
        n = V2.full_mips(Wd, H)
        struct.pack_into("<I", hdr, 8, struct.unpack_from("<I", hdr, 8)[0] | V2.DDSD_MIPMAPCOUNT | V2.DDSD_LINEARSIZE)
        struct.pack_into("<I", hdr, 20, max(1, (Wd + 3) // 4) * max(1, (H + 3) // 4) * 8)
        struct.pack_into("<I", hdr, 28, n)
        struct.pack_into("<I", hdr, 108, struct.unpack_from("<I", hdr, 108)[0] | V2.DDSCAPS_COMPLEX | V2.DDSCAPS_MIPMAP)
        assert struct.unpack_from("<I", hdr, 80)[0] & 1 == 0
        out, cur = bytearray(hdr), level0
        for k in range(n):
            if k:
                cur = V2.box_half(cur)
            out += bc1_encode_dc(np.clip(cur, 0, 255))
        info = V2.dds_parse(bytes(out))
        assert info["end"] == len(out) and info["levels"][-1][:2] == (1, 1)
        return bytes(out)
    info = V2.dds_parse(today_dds)
    assert info["fourcc"] == fourcc and info["end"] == len(today_dds)
    assert info["mips"] == V2.full_mips(info["w"], info["h"]) and info["levels"][-1][:2] == (1, 1)
    assert level0.shape[:2] == (info["h"], info["w"])
    out, cur = bytearray(today_dds[:128]), level0
    for k, (w, h, off, sz) in enumerate(info["levels"]):
        if k:
            cur = V2.box_half(cur)
        colour = np.frombuffer(bc1_encode_dc(np.clip(cur, 0, 255)), np.uint8).reshape(-1, 8)
        if fourcc == b"DXT1":
            assert colour.nbytes == sz
            out += colour.tobytes()
        else:
            old = np.frombuffer(today_dds[off:off + sz], np.uint8).reshape(-1, 16)
            assert colour.shape[0] == old.shape[0]
            out += np.concatenate([old[:, :8], colour], axis=1).tobytes()
    assert len(out) == len(today_dds)
    return bytes(out)


def brightness(a, ref):
    lr = V3.luma(ref).mean()
    return float((V3.luma(a).mean() - lr) / max(lr, 1e-6))


def same_art(live, ret, U):
    """Correlation of the two pictures' luma at 32u (retail Fourier-resampled to the live grid)."""
    H, Wd = live.shape[:2]
    Hr, Wr = ret.shape[:2]
    upp, upp_r = U / np.sqrt(H * Wd), U / np.sqrt(Hr * Wr)
    a = np.fft.irfft2(np.fft.rfft2(V3.luma(live)) * V3._gauss(V3._f2(H, Wd), 16.0 / upp), s=(H, Wd))
    r = V3.coarse_up(V3.luma(ret), 16.0, upp_r, (H, Wd))
    return float(np.corrcoef(a.ravel(), r.ravel())[0, 1])


def look_today(live, ret, U):
    s_r, s_l = V3.look(ret, U), V3.look(live, U)
    return dict(chroma=V3.chroma(s_l["mean"], s_r["mean"]), bright=brightness(live, ret), mid=s_l["mid"] / s_r["mid"],
                fine=s_l["fine"], retail_fine=s_r["fine"], retail_mid=s_r["mid"])


def needs_fix(t, mid_ok_applies):
    why = []
    if t["chroma"] > GATE_CHROMA:
        why.append("chroma %.1f" % t["chroma"])
    if abs(t["bright"]) > GATE_BRIGHT:
        why.append("brightness %+.1f%%" % (100 * t["bright"]))
    if mid_ok_applies and not (GATE_MID[0] <= t["mid"] <= GATE_MID[1]):
        why.append("4-16u %.2fx" % t["mid"])
    return why


def encode_plain(img, ext, like_bytes):
    """jpg (q95, today's chroma subsampling) / tga (RLE) / png - deterministic."""
    im = Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8), "RGB")
    buf = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        from PIL import JpegImagePlugin
        samp = -1
        try:
            samp = JpegImagePlugin.get_sampling(Image.open(io.BytesIO(like_bytes)))
        except Exception:
            pass
        im.save(buf, "JPEG", quality=95, subsampling=samp if samp in (0, 1, 2) else 2, optimize=True)
    elif ext == ".tga":
        im.save(buf, "TGA", rle=True)
    else:
        im.save(buf, "PNG", compress_level=9)
    return buf.getvalue()


def resize_to(img, H, Wd):
    h, w = img.shape[:2]
    if (h, w) == (H, Wd):
        return img
    if h % H == 0 and w % Wd == 0:
        return img.reshape(H, h // H, Wd, w // Wd, 3).mean((1, 3))
    return np.dstack([V3.band_up(img[..., k], np.ones((h, w // 2 + 1)), (H, Wd)) for k in range(3)])


def dxt_bad_blocks(b):
    info = V2.dds_parse(b)
    step, co = (8, 0) if info["fourcc"] == b"DXT1" else (16, 8)
    bad = 0
    for (w, h, off, sz) in info["levels"]:
        blk = np.frombuffer(b[off:off + sz], np.uint8).reshape(-1, step)[:, co:co + 8]
        c0 = blk[:, 0].astype(np.int32) | (blk[:, 1].astype(np.int32) << 8)
        c1 = blk[:, 2].astype(np.int32) | (blk[:, 3].astype(np.int32) << 8)
        bad += int(((c0 < c1) | ((c0 == c1) & (blk[:, 4:8].astype(np.int64).sum(1) != 0))).sum())
    return bad


DXGI_BPB = {71: 8, 72: 8, 74: 16, 75: 16, 77: 16, 78: 16, 80: 8, 81: 8, 83: 16, 84: 16, 98: 16, 99: 16}


def dx10_levels(b):
    """Mip levels of a DX10-header DDS (BC1/2/3/4/5/7): [(w, h, rgb mean)] - each level re-wrapped in its own
    header and decoded by Pillow (which decodes level 0 only)."""
    h, w = struct.unpack_from("<II", b, 12)
    mips = max(1, struct.unpack_from("<I", b, 28)[0])
    bpb = DXGI_BPB[struct.unpack_from("<I", b, 128)[0]]
    out, off, cw, ch = [], 148, w, h
    for _ in range(mips):
        sz = max(1, (cw + 3) // 4) * max(1, (ch + 3) // 4) * bpb
        hdr = bytearray(b[:148])
        struct.pack_into("<II", hdr, 12, ch, cw)
        struct.pack_into("<I", hdr, 20, sz)
        struct.pack_into("<I", hdr, 28, 1)
        im = Image.open(io.BytesIO(bytes(hdr) + b[off:off + sz]))
        im.load()
        out.append((cw, ch, np.asarray(im.convert("RGB")).reshape(-1, 3).astype(float).mean(0)))
        off += sz
        cw, ch = max(1, cw // 2), max(1, ch // 2)
    return out


def mip_devs(b):
    if b[84:88] == b"DX10":
        mm = [(min(w, h), m) for w, h, m in dx10_levels(b)]
    else:
        inf = V2.dds_parse(b)
        mm = [(min(w, h), V2.dds_decode_level(b, inf, k)[..., :3].reshape(-1, 3).astype(float).mean(0))
              for k, (w, h, o, s) in enumerate(inf["levels"])]
    big = max([float(np.abs(x - mm[0][1]).max()) for d, x in mm if d >= 16] or [0.0])
    small = max([float(np.abs(x - mm[0][1]).max()) for d, x in mm if d < 16] or [0.0])
    return big, small


def height_sibling(stack, base, owned):
    """Today's gl2 height source for a DDS diffuse, or why there is none to fix."""
    for e in ("_nh", "_n"):
        for x in IMG_EXT:
            if (base + e + x) in stack.copies:
                return None, "authored %s%s - relief not generated" % (e, x)
    hs = winner_ext(stack, base, HEIGHT_EXT, skip={PAK_NAME})
    mine = winner_ext(stack, base, HEIGHT_EXT)
    if not hs:
        return None, "no png/tga/jpg sibling - no generated relief today"
    if mine and mine["pak"] == PAK_NAME and HEIGHT_EXT.index(mine["ext"]) < HEIGHT_EXT.index(hs["ext"]):
        return None, "terrain pak already ships an earlier-extension sibling"
    if V2.fs_key(hs["pak"]) > V2.fs_key(PAK_NAME) and not V3.RETAIL_PAK.match(hs["pak"]):
        return None, "sibling owned by %s (sorts above)" % hs["pak"]
    if base in owned:
        return None, "a pak above ships this name"
    return hs, None


def make_sibling(stack, hs, img, ref_luma_img):
    sb = read_img(stack, hs)
    im = Image.open(io.BytesIO(sb))
    W0, H0 = im.size
    src = resize_to(np.clip(img[..., :3], 0, 255), H0, W0)
    out = encode_plain(src, hs["ext"], sb)
    dec, _ = decode(out, hs["ext"])
    info = dict(path=hs["ext"], today=hs["pak"], size=[W0, H0], bytes=len(out),
                brightness=round(brightness(dec[..., :3], ref_luma_img), 4))
    return out, info, dec[..., :3]


def build_one(job):
    """Worker: one MP-only texture -> dict(members={name: bytes}, report, thumbs)."""
    stack = _WSTACK
    b = job["base"]
    live_rec, ret_rec, U = job["live"], job["ret"], job["U"]
    rep = dict(base=b, U=round(U, 1), live=live_rec["pak"] + ":" + live_rec["ext"], retail=ret_rec["pak"] + ":" + ret_rec["ext"],
               maps=job["maps"], gates={})
    try:
        lb = read_img(stack, live_rec)
        live4, linfo = decode(lb, live_rec["ext"])
        live = live4[..., :3]
        ret = decode(read_img(stack, ret_rec), ret_rec["ext"])[0][..., :3]
        rep["size"] = [live.shape[1], live.shape[0]]
        rep["retail_size"] = [ret.shape[1], ret.shape[0]]
        if abs(live.shape[0] / live.shape[1] - ret.shape[0] / ret.shape[1]) > 1e-9:
            rep["skip"] = "aspect differs from retail"
            return dict(report=rep, members={})
        if live.shape[0] % 4 or live.shape[1] % 4:
            rep["skip"] = "size not a multiple of 4"
            return dict(report=rep, members={})
        if linfo is not None and linfo["fourcc"] not in (b"DXT1", b"DXT5", b"DX10"):
            rep["skip"] = "DDS format %s" % linfo["fourcc"]
            return dict(report=rep, members={})
        if linfo is not None and linfo["fourcc"] != b"DX10" and not (
                linfo["mips"] == V2.full_mips(linfo["w"], linfo["h"]) and linfo["end"] == len(lb)):
            rep["skip"] = "DDS mip chain short/odd"
            return dict(report=rep, members={})
        texel_r = U / np.sqrt(ret.shape[0] * ret.shape[1])
        band_ok = texel_r <= MAX_RETAIL_TEXEL_U
        t = look_today(live, ret, U)
        rep["today"] = {k: round(v, 4) for k, v in t.items()}
        rep["retail_texel_u"] = round(texel_r, 2)
        why = needs_fix(t, band_ok)
        rep["why"] = why
        if not why:
            rep["skip"] = "passes the v3 gates today"
            return dict(report=rep, members={})
        r_art = same_art(live, ret, U)
        method = "field" if r_art >= SAME_ART_R else "global"
        rep["same_art_r"] = round(r_art, 3)
        if band_ok:
            out, info = V3.banded_match(live, ret, method, U)
        else:                                                      # hue only: retail cannot resolve the 4-16u band
            saved = (V3.MID_TARGET, V3.STRUCT_MIN)
            V3.MID_TARGET, V3.STRUCT_MIN = (0.0, 1e9), -1.0
            try:
                out, info = V3.banded_match(live, ret, method, U)
            finally:
                V3.MID_TARGET, V3.STRUCT_MIN = saved
            info["hue_only"] = True
        rep["method"] = info
        ext = live_rec["ext"]
        if ext == ".dds":
            new = encode_dds_v4(out, lb, linfo["fourcc"])
            dec = V2.dds_decode_level(new, V2.dds_parse(new), 0)[..., :3].astype(np.float64)
        else:
            new = encode_plain(out, ext, lb)
            dec = decode(new, ext)[0][..., :3]
        members = {b + ext: new}
        # ---- gates on the encoded file
        s_r, s_n = V3.look(ret, U), V3.look(dec, U)
        g = rep["gates"]
        ch = V3.chroma(s_n["mean"], s_r["mean"])
        br = brightness(dec, ret)
        g["chroma"] = dict(ok=ch <= GATE_CHROMA, v4=round(ch, 2), today=round(t["chroma"], 2))
        g["brightness"] = dict(ok=abs(br) <= GATE_BRIGHT, v4=round(br, 4), today=round(t["bright"], 4))
        lim = GATE_FINE * max(s_r["fine"], t["fine"])
        g["fine"] = dict(ok=s_n["fine"] <= lim, v4=round(s_n["fine"], 2), limit=round(lim, 2), today=round(t["fine"], 2))
        mr = s_n["mid"] / s_r["mid"]
        g["mid"] = dict(ok=(GATE_MID[0] <= mr <= GATE_MID[1]) if band_ok else True, v4=round(mr, 3), today=round(t["mid"], 3),
                        applies=band_ok)
        zt, zn = V3.wrap_z(live, block=(ext == ".dds")), V3.wrap_z(dec, block=(ext == ".dds"))
        zta, zf = V3.wrap_z(live), V3.wrap_z(out)
        g["wrap"] = dict(ok=zn <= max(1.10 * zt, zt + 0.10) and zf <= max(1.10 * zta, zta + 0.10),
                         v4=round(zn, 3), today=round(zt, 3), float=round(zf, 3), today_all=round(zta, 3))
        lean = [round(float(dec[..., k].mean() - out[..., k].mean()), 3) for k in range(3)]
        g["lean"] = dict(ok=max(abs(x) for x in lean) <= LEAN_MAX, v4=lean)
        if ext == ".dds":
            ni = V2.dds_parse(new)
            same_hdr = new[:128] == lb[:128] if linfo["fourcc"] != b"DX10" else ni["fourcc"] == b"DXT1"
            g["format"] = dict(ok=same_hdr and ni["end"] == len(new) and ni["mips"] == V2.full_mips(ni["w"], ni["h"])
                               and ni["levels"][-1][:2] == (1, 1), fourcc=ni["fourcc"].decode(), mips=ni["mips"],
                               today=linfo["fourcc"].decode() + ("" if linfo["fourcc"] != b"DX10" else " dxgi %d" % linfo["dxgi"]))
            bad = dxt_bad_blocks(new)
            g["blocks"] = dict(ok=bad == 0, bad=bad)
            nb, ns = mip_devs(new)
            tb, ts = mip_devs(lb)
            g["mips"] = dict(ok=nb <= 1.0 and ns <= max(ts, SMALL_MIP_MAX), v4_big=round(nb, 2), v4_small=round(ns, 2),
                             today_big=round(tb, 2), today_small=round(ts, 2))
            if linfo["fourcc"] == b"DXT5":
                a_ok = all((V2.dds_decode_level(new, ni, k)[..., 3] == V2.dds_decode_level(lb, linfo, k)[..., 3]).all()
                           for k in range(ni["mips"]))
                g["alpha"] = dict(ok=a_ok)
        else:
            g["format"] = dict(ok=dec.shape == live.shape, fmt=ext)
        # ---- gl2 relief sibling
        if ext == ".dds":
            hs, why_not = height_sibling(stack, b, job["owned"])
            if hs:
                sib, sinfo, sdec = make_sibling(stack, hs, out, ret)
                members[b + hs["ext"]] = sib
                sinfo["ok"] = abs(sinfo["brightness"]) <= GATE_BRIGHT
                g["sibling"] = sinfo
            else:
                rep["sibling"] = why_not
        rep["ok"] = all(v.get("ok", True) for v in g.values())
        rep["bytes"] = sum(len(v) for v in members.values())
        n = 160
        rep_th = [V3.world_view(a, U, 2 * U, n) for a in (ret, live, dec)]
        return dict(report=rep, members=members if rep["ok"] else {}, thumbs=[np.asarray(x) for x in rep_th])
    except Exception as e:                                         # a broken input is a skip with its reason, never a crash
        rep["skip"] = "error %s: %s" % (type(e).__name__, e)
        return dict(report=rep, members={})


# ============================================================================================ sheets
def _font(sz):
    try:
        return ImageFont.load_default(size=sz)
    except Exception:
        return ImageFont.load_default()


def contact_sheets(outdir, rows, per_page=10):
    """rows: (title, [lines], [retail, today, v4] thumbs as uint8 arrays)."""
    paths = []
    T, gap, lab = 160, 8, 15
    for p0 in range(0, len(rows), per_page):
        chunk = rows[p0:p0 + per_page]
        Wd = 3 * T + 4 * gap + 430
        Hh = 34 + len(chunk) * (T + lab + gap) + gap
        sh = Image.new("RGB", (Wd, Hh), (24, 24, 28))
        dr = ImageDraw.Draw(sh)
        f, fb = _font(12), _font(14)
        dr.text((gap, 8), "terrain v4 - MP-only ground, retail | today | v4 (2x2 repeats at the texture's world scale)"
                "   page %d/%d" % (p0 // per_page + 1, (len(rows) + per_page - 1) // per_page), fill=(240, 240, 240), font=fb)
        y = 34
        for title, lines, th in chunk:
            for k, (cl, a) in enumerate(zip(("retail", "today", "v4"), th)):
                x = gap + k * (T + gap)
                dr.text((x, y), cl, fill=(220, 220, 150), font=f)
                sh.paste(Image.fromarray(a, "RGB"), (x, y + lab))
            tx = gap + 3 * (T + gap)
            dr.text((tx, y), title, fill=(240, 240, 240), font=fb)
            for j, ln in enumerate(lines):
                dr.text((tx, y + 20 + 15 * j), ln[:70], fill=(210, 210, 210), font=f)
            y += T + lab + gap
        pth = os.path.join(outdir, "mp_page%02d.png" % (p0 // per_page + 1))
        sh.save(pth, optimize=True)
        paths.append(pth)
    return paths


# ================================================================================================ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--gog", default=GOG_DEFAULT)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--scan-only", action="store_true")
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--no-stack-check", action="store_true")
    ap.add_argument("--only", default="", help="debug: comma list of image base substrings")
    ap.add_argument("--also-above", action="append", default=[],
                    help="a staged pak that will sort above this one (its names are left to it)")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    for forbidden in (MOD, a.gog, V2.LIVE_BASE, V2.APPDATA_HOME):
        if forbidden:
            assert not os.path.normcase(out).startswith(os.path.normcase(os.path.abspath(forbidden))), \
                "refusing to write into " + forbidden
    os.makedirs(out, exist_ok=True)
    t0 = time.time()

    print("== source")
    src_bytes = open(a.src, "rb").read()
    if not gate("source pak is terrain v3 (sha256 0551ae73...)", sha(src_bytes) == SRC_SHA, sha(src_bytes)):
        sys.exit(2)
    src = V2.read_pak(a.src)
    v3_bases = {V3.strip_ext(n.lower()) for n in src if n.lower().startswith("textures/")}

    print("== player stack census")
    stack = V3.Stack(a.gog)
    print("  [INFO] manifest %s; %d paks; left out: %s" % (stack.manifest_version, len(stack.srcs), ", ".join(stack.left_out)))
    shaders, img, readable = census(stack)
    mp_maps = sorted(p for p in readable if is_mp_map(p))
    print("  [INFO] %d BSPs read, %d MP (dm/obj/lib): %s" % (len(readable), len(mp_maps), ", ".join(p[5:-4] for p in mp_maps)))
    tiks = tiki_images(stack, shaders)
    for p in a.also_above:
        assert V2.fs_key(os.path.basename(p)) > V2.fs_key(PAK_NAME), p
        print("  [INFO] also above: %s sha256 %s" % (p, sha(open(p, "rb").read())))
    owned, above = above_names(a.gog, a.also_above)
    print("  [INFO] paks above %s (GOG maintt + mod folder): %s" % (PAK_NAME, ", ".join(sorted({os.path.basename(p) for p in above}))))
    cands, funnel = scope(stack, img, tiks, owned, v3_bases)
    n_mp_ground = sum(len(v) for v in funnel.values()) + len(cands)
    print("  [INFO] MP-only ground images: %d; candidates (retail exists, today's file is an HD copy): %d" % (n_mp_ground, len(cands)))
    for r, v in sorted(funnel.items()):
        print("    - %-48s %3d  %s" % (r, len(v), ", ".join(x.split("/")[-1] for x in v[:8]) + (" ..." if len(v) > 8 else "")))
    report = dict(source=dict(path=a.src, sha256=SRC_SHA), player_stack=dict(manifest=stack.manifest_version, left_out=stack.left_out),
                  mp_maps=[p[5:-4] for p in mp_maps], funnel={k: v for k, v in sorted(funnel.items())},
                  candidates=[c["base"] for c in cands])
    if a.scan_only:
        with open(os.path.join(out, "scope_v4.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(dict(report, cands=[dict(c, live={k: c["live"][k] for k in ("ext", "pak")},
                                                ret={k: c["ret"][k] for k in ("ext", "pak")}) for c in cands]), fh, indent=1)
        return

    print("== build (%d workers)" % a.jobs)
    if a.only:
        cands = [c for c in cands if any(s in c["base"] for s in a.only.split(","))]
    jobs = [dict(c, owned=owned) for c in cands]
    results = []
    with ProcessPoolExecutor(a.jobs, initializer=_init_worker, initargs=(a.gog,)) as ex:
        for k, r in enumerate(ex.map(build_one, jobs, chunksize=1)):
            results.append(r)
            rp = r["report"]
            state = rp.get("skip") or ("OK" if rp.get("ok") else "GATE FAIL " + ",".join(k2 for k2, v in rp["gates"].items() if not v.get("ok", True)))
            print("  [%3d/%d] %-52s %s" % (k + 1, len(jobs), rp["base"][9:], state))
    new_members = {}
    shipped, failed, skipped = [], [], []
    for r in results:
        rp = r["report"]
        if rp.get("skip"):
            skipped.append(rp)
        elif rp.get("ok"):
            shipped.append(r)
            new_members.update(r["members"])
        else:
            failed.append(rp)

    print("== v3 composite relief siblings")
    v3_sibs = {}
    for m, (method, rspec) in V3.SCOPE.items():
        base = V3.strip_ext(m)
        hs, why_not = height_sibling(stack, base, owned)
        if not hs:
            print("  [INFO] %s: %s" % (base.split("/")[-1], why_not))
            continue
        d0 = V2.dds_decode_level(src[m][0], V2.dds_parse(src[m][0]), 0)[..., :3].astype(np.float64)
        ret = V3.load_retail(a.gog, rspec)
        sib, sinfo, sdec = make_sibling(stack, hs, d0, d0)
        gate("v3 relief sibling %s%s (today %s, %dx%d): brightness vs the v3 dds" % (base.split("/")[-1], hs["ext"], hs["pak"],
             *sinfo["size"]), abs(sinfo["brightness"]) <= GATE_BRIGHT, "%+.2f%%, %d bytes" % (100 * sinfo["brightness"], sinfo["bytes"]))
        v3_sibs[base + hs["ext"]] = sib
        report.setdefault("v3_siblings", {})[base + hs["ext"]] = sinfo

    print("== pak")
    members = dict(src)
    for n, bts in sorted(list(new_members.items()) + list(v3_sibs.items())):
        assert n not in members, n
        members[n] = (bts, FIXED_TS, V2.NEW_ATTR)
    pak = V2.write_pak(members)
    with zipfile.ZipFile(io.BytesIO(pak)) as z:
        gate("zip CRC test", z.testzip() is None)
        cm = {zi.filename: z.read(zi) for zi in z.infolist()}
        order = [zi.filename for zi in z.infolist()]
    gate("entries sorted", order == sorted(order), "%d members" % len(order))
    gate("every v3 member byte-identical", all(cm[n] == src[n][0] for n in src), "%d v3 members" % len(src))
    added = sorted(set(cm) - set(src))
    gate("no added member Omaha by name", not any(V2.OMAHA.search(n) for n in added), "%d added" % len(added))
    om = [n for n in added if any(is_omaha_map(p) for p in img.get(V3.strip_ext(n.lower()), {}).get("maps", ()))]
    gate("no added member drawn on an Omaha map (m3l1a/m3l1b/e3l1/e3l2/obj_team3)", not om, ", ".join(om))
    sp = [n for n in new_members if not all(is_mp_map(p) for p in img[V3.strip_ext(n.lower())]["maps"])]
    gate("every new texture member is MP-only", not sp, ", ".join(sp))
    sh = [n for n in added if V3.strip_ext(n.lower()) in owned]
    gate("no added member shadowed by a pak above", not sh, ", ".join(sh))
    if not a.no_stack_check and added:
        names = {n.lower() for n in cm}
        V2.stack_check("live G:/mohaa-gl2", V2.search_order(V2.LIVE_BASE, V2.LIVE_HOME, a.gog), names, added)
        if V2.APPDATA_HOME and os.path.isdir(V2.APPDATA_HOME):
            V2.stack_check("plain GOG launch", V2.search_order(a.gog, V2.APPDATA_HOME, None), names, added)
    for r in shipped:
        rp = r["report"]
        gate("v4 gates: " + rp["base"].split("/")[-1], rp["ok"], "; ".join(
            "%s %s" % (k, "/".join(str(v.get(x)) for x in ("today", "v4") if x in v)) for k, v in rp["gates"].items()
            if k in ("chroma", "brightness", "mid")))
    fn = "zzzzzzzzz_coop_terrain.v4.pk3"
    with open(os.path.join(out, fn), "wb") as fh:
        fh.write(pak)
    report["pak"] = dict(file=fn, sha256=sha(pak), bytes=len(pak), members=len(cm), added=len(added))
    report["shipped"] = [r["report"] for r in shipped]
    report["gate_failed"] = failed
    report["skipped"] = skipped

    # gate table (TSV)
    cols = ["base", "maps", "live", "retail", "method", "chroma_today", "chroma_v4", "bright_today", "bright_v4", "mid_today",
            "mid_v4", "fine_v4", "fine_lim", "wrap_today", "wrap_v4", "mips_big", "lean_max", "sibling", "why"]
    with open(os.path.join(out, "gate_table_v4.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for rp in [r["report"] for r in shipped] + failed:
            g = rp["gates"]
            m = rp.get("method", {})
            fh.write("\t".join(str(x) for x in [
                rp["base"][9:], ",".join(p[5:-4] for p in rp["maps"]), rp["live"], rp["retail"],
                m.get("method", "") + ("/hue-only" if m.get("hue_only") else ""),
                g["chroma"]["today"], g["chroma"]["v4"], g["brightness"]["today"], g["brightness"]["v4"],
                g["mid"]["today"], g["mid"]["v4"] if g["mid"]["applies"] else "n/a", g["fine"]["v4"], g["fine"]["limit"],
                g["wrap"]["today"], g["wrap"]["v4"], g.get("mips", {}).get("v4_big", ""), max(abs(x) for x in g["lean"]["v4"]),
                g.get("sibling", {}).get("path", rp.get("sibling", "")), ";".join(rp["why"]) + ("" if rp["ok"] else " GATE-FAIL")]) + "\n")

    if not a.no_sheets:
        sd = os.path.join(out, "sheets")
        os.makedirs(sd, exist_ok=True)
        rows = []
        for r in sorted(shipped, key=lambda r: -r["report"]["gates"]["chroma"]["today"]):
            rp = r["report"]
            g = rp["gates"]
            rows.append((rp["base"][9:], [
                "maps: " + ", ".join(p[5:-4] for p in rp["maps"]),
                "today: %s   retail: %s   %s" % (rp["live"], rp["retail"], rp["method"]["method"]),
                "chroma %.1f -> %.1f   brightness %+.1f%% -> %+.1f%%" % (g["chroma"]["today"], g["chroma"]["v4"],
                                                                       100 * g["brightness"]["today"], 100 * g["brightness"]["v4"]),
                "4-16u %.2fx -> %s   fine %.1f (limit %.1f)" % (g["mid"]["today"], ("%.2fx" % g["mid"]["v4"]) if g["mid"]["applies"]
                                                                   else "n/a (hue only)", g["fine"]["v4"], g["fine"]["limit"]),
                "relief sibling: %s" % (g["sibling"]["path"] + " " + "x".join(map(str, g["sibling"]["size"])) if "sibling" in g
                                        else rp.get("sibling", "-"))], [x.astype(np.uint8) for x in r["thumbs"]]))
        pages = contact_sheets(sd, rows)
        print("  sheets:", len(pages), sd)

    report["gates"] = V2.GATES
    with open(os.path.join(out, "gates_v4.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    bad = [x for x in V2.GATES if not x["ok"]]
    print("\nMP-only ground %d | candidates %d | shipped %d | gate-failed %d | skipped %d | v3 siblings %d"
          % (n_mp_ground, len(cands), len(shipped), len(failed), len(skipped), len(v3_sibs)))
    print("%d gates, %d failed   (%.0fs)" % (len(V2.GATES), len(bad), time.time() - t0))
    print("  %s  %s  %d" % (fn, sha(pak), len(pak)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

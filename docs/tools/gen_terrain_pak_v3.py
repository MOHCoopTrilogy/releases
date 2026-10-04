# -*- coding: utf-8 -*-
"""Terrain pak v3 - Phase 2 of the vetted ground-seam plan: BANDED colour re-match (bug-2950).

Plan: docs/proposals/seams_2026-09-25/vet_seams.md (Phase 2, F1, F2, F10, F11). Base: terrain pak v2d_s060
(sha256 c53eced3..., asserted) = the Phase-1 pak built by gen_terrain_pak_v2.py --delean. This script is its
sibling: it imports v2's DDS parse/decode, pak writer and stack check, and changes COLOUR ONLY.

WHAT CHANGES (Omaha-free scope; every other member stays byte-identical, all 7 _nh included):
  standalone ground   m3l3grass_1rough, grndset_2af, forstsnow_lite256
  live composites     m3l3grass_1trans, _1blast, _set2, _set2rad, _bocroadt (vet F1, F3)
Excluded (Omaha-coupled, user decision D2=a): rubble2c, rubblebase, nu_earth_set3grassa, m3l3grass_1.
Dead (never drawn, left alone): m3l3grass_bocroad, _bocroad_new, _bocroadc, _bocroadx.
Both lists are CHECKED here against every BSP of the player stack (map_usage): each changed texture must
be drawn somewhere and never on m3l1a/e3l1/e3l2; each excluded one is printed with the Omaha map that
couples it.

THE MATCH (vet F2: banded, never naive; no ESRGAN, no sharpening - bug-1129/2164 worms):
Bands are in WORLD units at each texture's real scale (units per repeat measured from the BSPs), the
same bands the audit's look metric uses (phys.stats): fine < 4u, mid 4-16u, coarse > 16u.
  1. hue      - grndset_2af / forstsnow_lite256: per-channel mean moved to retail's (a constant; the
                photo keeps its own large-scale pattern). The m3l3grass set (1rough + the composites):
                per-channel COARSE FIELD (Gaussian sigma COARSE_SIGMA_U world units, periodic) replaced
                by retail's, so each part of a transition tile (dirt band, crater, road, grass corner)
                gets retail's colour there, and 1rough - whose borders retail's composites share - gets
                the same treatment so the set meets itself consistently.
  2. contrast - each channel's 4-16u band is moved into MID_TARGET x retail's (inside already: left).
                The photo's own band is amplified at most GAIN_CAP x; beyond that the photo's soft
                patches turn into distinct spots (seen at 2-3x on 1rough, blotches at 7x on grndset_2af),
                so any remaining energy is retail's own 4-16u band, Fourier-resampled (band-limited).
  3. fine     - the band below 4u (the photo's own grain) is left exactly as it is.
  Exception by MEASUREMENT, not by name: if the photo's luma 4-16u band is < STRUCT_MIN x retail's it
  does not have retail's structure at all (grndset_2af: CC0 fine sand vs retail gravel, 0.21x) - then
  every band from one retail texel up is retail's own (the vet's banded-B split point) and the photo
  keeps only the band finer than retail's texel. Gravel comes back; the photo's sand grain stays.
All filters are periodic (FFT), so the operation cannot create a wrap seam. Values past 0/255 go
through a small exponential toe (TOE levels) instead of a hard clamp, so they keep their order.

COMPOSITES - why a direct banded correction and not a rebuilt recipe (vet F11): the generator of the 10
composite tiles is lost, and re-deriving it from the pixels is not possible offline. Block correlation
of the composites against every member of the pak shows each is a blend of the CC0 grass photo that is
also in m3l3grass_1rough (r 0.5-0.9 at the same pixel positions) with layers that are NOT in the pak -
set2/set2rad's dirt (r 0.2-0.3 with anything shipped), bocroadt's road - and those ambientCG sources are
not cached and downloading is out of scope. The composites also no longer share their border strips
the way retail's set does (retail 1rough/1blast/1trans borders identical, RMS 0.0-2.5; CC0 RMS 16-20),
so a rebuilt recipe could not even be checked against the shipped files. What CAN be done exactly is
the correction itself: a transition tile's layout lives in its coarse colour field, so matching that
field (not one global mean) to its retail counterpart puts retail's colour back at each edge where the
tile meets its designed neighbour, while keeping the CC0 detail.

RETAIL COUNTERPARTS are pinned by sha256. m3l3grass_bocroadt uses the AA original (main/Pak2.pk3 .tga):
the CC0 composite and the pre-CC0 HD copy both follow its layout, and its map (m5l2b) is an AA map;
Breakthrough's mainta/pak1.pk3 copy is a different picture (a T-junction), not a counterpart.

GATES (vet F10) - every gate is an assert-style check; exit 1 if any fails:
  chroma <= 3 vs retail on every changed texture (decoded level 0 of the NEW dds)
  fine grain  (luma finer than 1u)  <= 1.15 x max(retail, pre-CC0 player file)
  mid structure (luma 4-16u)        in 0.8 .. 1.25 x retail
  wrap seam: z of the new level 0 <= max(1.10 x today's z, today's z + 0.10), before AND after encode
             (decoded z measured against interior 4x4-block lines: the wrap line is always one)
  mip means: levels >= 16px within 1 level of level 0; smaller levels no worse than today's file
  _nh normal maps byte-identical to v2d_s060 (tilt unchanged); every other member byte-identical
  DXT1, full box mip chain to 1x1, today's header, 4-colour blocks only
  deterministic: the pak is built twice in-process and must be identical (and two runs must match)
Mips: 2x2 BOX in float from the processed level 0 (not Lanczos, vet F10/F17). DXT1 blocks come from this
file's own least-squares encoder (bc1_encode), not Pillow (TRAPS T2: Pillow's DXT encoder skews).

It never writes outside --out and never touches hzm-mohaa-coop-mod or a game folder. Deploying is a
separate manual step (copy over hzm-mohaa-coop-mod\\zzzzzzzzz_coop_terrain.pk3, then build.ps1, game closed).

  python docs/tools/gen_terrain_pak_v3.py --out <dir>             pak + gates.json + sheets
  --no-sheets   skip the PNG sheets     --no-double   skip the in-process second build
  --usage-only  print the map-usage table and stop
"""
import argparse, hashlib, io, json, os, re, struct, sys, zipfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_terrain_pak_v2 as V2          # noqa: E402  (DDS parse/decode, BC helpers, pak writer, stack check)

REPO = V2.REPO
SRC_DEFAULT = V2.SRC_DEFAULT
SRC_SHA = "c53eced33f11edb7a817cf8446f52826caf7b17b3eb3a75e8a2aa9213bbae8b8"      # v2d_s060 (bug-2953)
PAK_NAME = V2.PAK_NAME
GOG_DEFAULT = V2.GOG_DEFAULT
FIXED_TS = (2026, 9, 26, 0, 0, 0)
DEV_ONLY = {"zzzzzzzz_hd_seamfix.pk3", "zzzzzzzz_hd_groundfix.pk3", "y_hzm_maptour.pk3"}   # dev install only

COARSE_SIGMA_U = 32.0      # composites: colour field coarser than this (world units) comes from retail
GAIN_CAP = 1.5             # the photo's own 4-16u band is never amplified more than this (spots above)
STRUCT_MIN = 1.0 / 3.0     # photo's 4-16u luma band below this x retail's: it lacks retail's structure
MID_TARGET = (0.9, 1.1)    # each channel's 4-16u band is moved only as far as this window x retail's
BAND_FINE_U, BAND_MID_U, BAND_MOTTLE_U = 4.0, 16.0, 64.0    # phys.stats bands (fine < 4u < mid < 16u)
GATE_CHROMA = 3.0
GATE_FINE = 1.15
GATE_MID = (0.8, 1.25)

OMAHA_MAPS = ("maps/m3l1a.bsp", "maps/e3l1.bsp", "maps/e3l2.bsp")
WATCH_MAPS = {"maps/m3l1b.bsp": "Omaha bluffs (lights rule; user decision D3)",
              "maps/obj/obj_team3.bsp": "MP Omaha Beach"}

W = "textures/wilderness/"
# changed member -> method + retail counterpart (game dir, pak, member, sha256)
SCOPE = {
    W + "m3l3grass_1rough.dds": ("field", ("main", "Pak2.pk3", W + "m3l3grass_1rough.jpg",
                                            "6cddfae697b2f983e11d30b651e899379914b8989f8434fe75de65cd6dab9677")),
    "textures/algiers/grndset_2af.dds": ("global", ("main", "Pak2.pk3", "textures/algiers/grndset_2af.jpg",
                                         "6083f21c20bdc3e74d549e2c051fd8f4b80d7e1191f0ad1d18bfddf8a04f76c3")),
    "textures/central_europe_winter/forstsnow_lite256.dds": ("global", (
        "main", "Pak2.pk3", "textures/central_europe_winter/forstsnow_lite256.jpg",
        "aef22037d7af978e8c65c7a6ebf5fade30a5b19f35f331d8127d623566b4b4e9")),
    W + "m3l3grass_1trans.dds": ("field", ("main", "Pak2.pk3", W + "m3l3grass_1trans.jpg",
                                           "5bd4c31a484b86af7e020d3a9127884710890e53ed097caca77fb483c046049c")),
    W + "m3l3grass_1blast.dds": ("field", ("main", "Pak2.pk3", W + "m3l3grass_1blast.jpg",
                                           "c8f3341e3ed6af8e0ced90b2fe7fddbd3daf9f5b2c39e76552254b96422f604c")),
    W + "m3l3grass_set2.dds": ("field", ("main", "Pak2.pk3", W + "m3l3grass_set2.jpg",
                                         "4002167ea123b2786a391eeb04d4d3c6f3c74356c4452e38a5b4c8d4983c85bf")),
    W + "m3l3grass_set2rad.dds": ("field", ("main", "Pak2.pk3", W + "m3l3grass_set2rad.jpg",
                                            "a31f41ceda98efe8c95ba8ece2f2f6fe2e1966f02af1bad2fb977717e7f1ee7a")),
    W + "m3l3grass_bocroadt.dds": ("field", ("main", "Pak2.pk3", W + "m3l3grass_bocroadt.tga",
                                             "64f41155962a72907c766233efbbf486dd8841ae52ad1fe002a78232f8580bd2")),
}
# retail of two unchanged neighbours, for the family sheet only
RETAIL_EXTRA = {"rubble2c": ("main", "Pak2.pk3", "textures/mohtest/rubble2c.jpg",
                             "5f45fe8e1a810fe18da93e3506b007a8e058def94c31bb12f806fd7474aeea08"),
                "m3l3grass_1": ("main", "Pak2.pk3", W + "m3l3grass_1.jpg",
                                "493ab608ca4056ae0e4d37881201801093391a2b78b11816e4a6f5cd431886ce")}
EXCLUDED = ["textures/mohtest/rubble2c.dds", "textures/models/items/rubblebase.dds",
            "textures/mohtest/nu_earth_set3grassa.dds", W + "m3l3grass_1.dds"]
DEAD = [W + "m3l3grass_bocroad.dds", W + "m3l3grass_bocroad_new.dds", W + "m3l3grass_bocroadc.dds",
        W + "m3l3grass_bocroadx.dds"]
NH = [n for n in ("textures/algiers/grndset_2af_nh.dds", "textures/central_europe_winter/forstsnow_lite256_nh.dds",
                  "textures/models/items/rubblebase_nh.dds", "textures/mohtest/nu_earth_set3grassa_nh.dds",
                  "textures/mohtest/rubble2c_nh.dds", W + "m3l3grass_1rough_nh.dds", W + "m3l3grass_bocroad_nh.dds")]
EXPECTED_MEMBERS = 25       # v2d_s060: 17 colour DDS + 7 _nh + CREDITS_terrain.txt

gate = V2.gate
sha = V2.sha


def base_of(member):
    return member[:-4].lower()


# =========================================================================================== player stack
RETAIL_PAK = re.compile(r"^pak\d+\w*\.pk3$", re.I)
MANIFEST = os.path.join(REPO, "manifests", "latest.json")


class Stack:
    """The PLAYER stack: GOG main < mainta < maintt, paks sorted like FS_PathCmp (files.cpp:3111), keeping
    only retail paks and the paks the release manifest ships (manifests/latest.json). Everything else in
    the dev install is left out and listed: zzzzzzzz_hd_seamfix/_groundfix (bug-2952), y_hzm_maptour.pk3
    (the dev map tour - its obj/omaha_beach, bobobjaa0x, capturedbase ... never reach a player), and any
    newer-than-release pak. Loose files are left out too (the GOG tree's loose maps/ are dev builds)."""

    def __init__(self, gog, dev=False):
        self.srcs, self.copies, self._z, self.left_out = [], {}, {}, []
        shipped = set()
        with open(MANIFEST, "rb") as fh:
            man = json.load(fh)
        for f in man["files"]:
            if f["path"].lower().endswith(".pk3"):
                shipped.add(f["path"].replace("\\", "/").split("/")[-1].lower())
        self.manifest_version = man.get("version")
        for game in ("main", "mainta", "maintt"):
            d = os.path.join(gog, game)
            for p in sorted((f for f in os.listdir(d) if f.lower().endswith(".pk3")), key=V2.fs_key):
                if not (dev or RETAIL_PAK.match(p) or p.lower() in shipped):
                    self.left_out.append(game + "/" + p)
                    continue
                i = len(self.srcs)
                self.srcs.append(("pak", os.path.join(d, p)))
                with zipfile.ZipFile(os.path.join(d, p)) as z:
                    for n in z.namelist():
                        self.copies.setdefault(n.lower().replace("\\", "/"), []).append((i, n))
        assert dev or not any(os.path.basename(p).lower() in DEV_ONLY for k, p in self.srcs)

    def name(self, i):
        k, p = self.srcs[i]
        return ("LOOSE " if k == "dir" else "") + os.path.relpath(p, os.path.dirname(os.path.dirname(p)))

    def read(self, i, member):
        k, p = self.srcs[i]
        if k == "dir":
            with open(member, "rb") as fh:
                return fh.read()
        if p not in self._z:
            self._z[p] = zipfile.ZipFile(p)
        return self._z[p].read(member)

    def winner(self, path, skip=()):
        for i, m in reversed(self.copies.get(path, [])):
            if os.path.basename(self.srcs[i][1]).lower() in skip:
                continue
            return i, m
        return None


# ============================================================================================= shaders
_TOK = re.compile(r'"[^"]*"|\{|\}|[^\s{}"]+')


def parse_shader_images(txt):
    """{shader name lower: set(image bases)} - every map/clampmap/animmap image in any stage or bundle."""
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    out, depth, name, imgs = {}, 0, None, None
    for ln in txt.replace("\r", "").split("\n"):
        toks = _TOK.findall(re.sub(r"//.*", "", ln))
        line = []
        for t in toks:
            if t == "{":
                if depth == 0:
                    imgs = set()
                depth += 1
            elif t == "}":
                depth -= 1
                if depth == 0 and name is not None:
                    out.setdefault(name, imgs)
                    name = None
            elif depth == 0:
                name = t.strip('"').lower().replace("\\", "/")
            else:
                line.append(t.strip('"'))
        if depth >= 1 and line:
            k = line[0].lower()
            cand = []
            if k in ("map", "clampmap", "clampmapx", "clampmapy") and len(line) > 1:
                cand = [line[1]]
            elif k == "animmap" and len(line) > 2:
                cand = line[2:]
            elif k == "animmapphase" and len(line) > 3:
                cand = line[3:]
            for c in cand:
                if not c.startswith("$"):
                    imgs.add(strip_ext(c.lower().replace("\\", "/")))
    return out


def strip_ext(p):
    b, e = os.path.splitext(p)
    return b if e.lower() in (".tga", ".jpg", ".jpeg", ".png", ".dds") else p


def shader_table(stack):
    """name -> image set. Highest-priority pak wins; within one source the alphabetically FIRST file
    (TRAPS T6, bug-2485)."""
    best = {}
    files = sorted(p for p in stack.copies if p.startswith("scripts/") and p.endswith(".shader"))
    for path in files:
        i, m = stack.winner(path)
        txt = stack.read(i, m).decode("latin1")
        for nm, imgs in parse_shader_images(txt).items():
            old = best.get(nm)
            if old is None or i > old[0]:
                best[nm] = (i, path, imgs)
    return {k: v[2] for k, v in best.items()}


# ================================================================================================= BSP
def bsp_scan(b):
    """-> (shader names, {shader idx: [planar, patch, trisoup, terrain]}, {shader idx: [(U, weight)]}, ws)
    U = world units per texture repeat (geometric mean of s and t), from planar/trisoup triangles
    (sqrt(world area / uv area)) and LOD terrain patches (512 / sqrt(span_s * span_t))."""
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
    cnt, dens = {}, {}
    dv = lump(4)
    nv = len(dv) // 44
    V = np.frombuffer(dv[:nv * 44], dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2),
                                                     ("n", "<f4", 3), ("c", "u1", 4)]))
    IX = np.frombuffer(lump(5), "<i4")
    sfr = lump(3)
    for i in range(len(sfr) // 108):
        sn, fog, st, fv, nvx, fi, nix = struct.unpack_from("<7i", sfr, i * 108)
        if not (0 <= sn < len(names)) or st not in (1, 2, 3):
            continue
        c = cnt.setdefault(sn, [0, 0, 0, 0])
        c[st - 1] += 1
        if st in (1, 3) and nix >= 3:
            idx = IX[fi:fi + nix].reshape(-1, 3) + fv
            P = V["xyz"][idx].astype(np.float64)
            S = V["st"][idx].astype(np.float64)
            a = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1).sum()
            d1, d2 = S[:, 1] - S[:, 0], S[:, 2] - S[:, 0]
            u = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]).sum()
            if a > 1.0 and u > 1e-9:
                dens.setdefault(sn, []).append((float(np.sqrt(a / u)), float(a)))
        elif st == 2:                                   # bezier patch: triangulate the control grid
            pw, ph = struct.unpack_from("<2i", sfr, i * 108 + 96)
            if pw >= 2 and ph >= 2 and pw * ph == nvx:
                g = np.arange(pw * ph).reshape(ph, pw)
                q = np.stack([g[:-1, :-1].ravel(), g[:-1, 1:].ravel(), g[1:, :-1].ravel(), g[1:, 1:].ravel()], 1)
                tri = np.concatenate([q[:, [0, 1, 2]], q[:, [1, 3, 2]]]) + fv
                P = V["xyz"][tri].astype(np.float64)
                S = V["st"][tri].astype(np.float64)
                a = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1).sum()
                d1, d2 = S[:, 1] - S[:, 0], S[:, 2] - S[:, 0]
                u = 0.5 * np.abs(d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]).sum()
                if a > 1.0 and u > 1e-9:
                    dens.setdefault(sn, []).append((float(np.sqrt(a / u)), float(a)))
    tr = lump(22)
    for i in range(len(tr) // 388):
        o = i * 388
        tc = struct.unpack_from("<8f", tr, o + 4)
        shn = struct.unpack_from("<H", tr, o + 40)[0]
        cnt.setdefault(shn, [0, 0, 0, 0])[3] += 1
        ss = max(abs(tc[4] - tc[0]), abs(tc[2] - tc[0]))
        tt = max(abs(tc[5] - tc[1]), abs(tc[3] - tc[1]))
        if ss > 1e-6 and tt > 1e-6:
            dens.setdefault(shn, []).append((512.0 / float(np.sqrt(ss * tt)), 512.0 * 512.0))
    ent = lump(14).decode("latin1", "replace")
    return names, cnt, dens, ("remapshader" in ent.lower())


def map_usage(stack, bases):
    """Every BSP of the player stack: which maps draw each image base, how, and at what world scale."""
    shaders = shader_table(stack)
    img2sh = {}
    for nm, imgs in shaders.items():
        for im in imgs:
            img2sh.setdefault(im, set()).add(nm)
    use = {b: dict(maps={}, shaders=set(), dens=[]) for b in bases}
    remap, skipped = [], []
    bsps = sorted(p for p in stack.copies if p.startswith("maps/") and p.endswith(".bsp"))
    for path in bsps:
        i, m = stack.winner(path)
        b = stack.read(i, m)
        if b[:4] not in (b"2015", b"EALA"):                  # AA v19 / Spearhead+Breakthrough v21
            skipped.append(path)
            continue
        names, cnt, dens, rm = bsp_scan(b)
        if rm:
            remap.append(path)
        for si, c in cnt.items():
            nm = names[si]
            imgs = shaders.get(nm, {nm})                 # no definition: the image IS the shader name
            for im in imgs:
                if im in use:
                    u = use[im]
                    u["shaders"].add(nm)
                    mc = u["maps"].setdefault(path, [0, 0, 0, 0])
                    for k in range(4):
                        mc[k] += c[k]
                    if path not in OMAHA_MAPS:
                        u["dens"] += dens.get(si, [])
    for b in bases:
        d = use[b]["dens"]
        if d:
            v = np.array(sorted(d))
            cw = np.cumsum(v[:, 1])
            use[b]["U"] = float(v[np.searchsorted(cw, cw[-1] / 2.0), 0])      # area-weighted median
        else:
            use[b]["U"] = None
        use[b]["shaders"] = sorted(use[b]["shaders"])
        del use[b]["dens"]
    return use, len(bsps) - len(skipped), remap + ["UNREADABLE " + s for s in skipped]


def usage_str(u):
    parts = []
    for p, (pl, pa, ts, te) in sorted(u["maps"].items()):
        s = []
        if te:
            s.append("%d terrain" % te)
        if pl + ts:
            s.append("%d brush" % (pl + ts))
        if pa:
            s.append("%d curve" % pa)
        parts.append("%s (%s)" % (p[5:-4], ", ".join(s)))
    return "; ".join(parts) if parts else "NOT DRAWN"


# ================================================================================================ images
def decode_any(b):
    im = Image.open(io.BytesIO(b))
    im.load()
    return np.asarray(im.convert("RGB")).astype(np.float64)


def dds_level0(b):
    return V2.dds_decode_level(b, V2.dds_parse(b), 0)[..., :3].astype(np.float64)


def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def chroma(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.abs(a / a.sum() - b / b.sum()).sum() * 100)


def look(rgb, U):
    """phys.stats (the audit's look metric) on luma at world scale: upp = world units per texel."""
    L = luma(rgb)
    H, Wd = L.shape
    upp = U / np.sqrt(H * Wd)

    def g(su):
        return ndimage.gaussian_filter(L, max(su / upp, 0.35), mode="wrap")
    b1, b4, b16, b64 = g(1.0), g(4.0), g(16.0), g(64.0)
    return dict(fine=float((L - b1).std()), sharp=float((L - b4).std()), mid=float((b4 - b16).std()),
                mottle=float((b16 - b64).std()), mean=[round(float(rgb[..., k].mean()), 2) for k in range(3)])


def wrap_z(rgb, block=False):
    """tex_metrics.line_scores: coherent step across the wrap / median interior step, both axes, max.
    block=True (for a DECODED DXT image): the wrap line is always a 4x4 block boundary, so compare it
    with the interior block-boundary lines only - against all interior lines the DXT block grid alone
    reads as a 'seam' (grndset_2af: 1.29 vs 1.02 on the same decode; the float output is 1.02/1.12)."""
    L = luma(rgb)
    zs = []
    for Lx in (L, L.T):
        Hh = Lx.shape[0]
        D = np.roll(Lx, -1, axis=1) - Lx
        S = ndimage.gaussian_filter1d(D, max(1.0, Hh / 64.0), axis=0, mode="wrap")
        Ls = np.abs(S).mean(0)
        ref = Ls[3:-1:4] if block else Ls[:-1]
        zs.append(float(Ls[-1] / max(np.median(ref), 1e-3)))
    return max(zs)


# ================================================================================================ bands
def _f2(H, Wd):
    fy = np.fft.fftfreq(H)[:, None]
    fx = np.fft.rfftfreq(Wd)[None, :]
    return fy * fy + fx * fx                      # (cycles per texel)^2


def _gauss(f2, sigma_px):
    return np.exp(-2.0 * np.pi ** 2 * sigma_px ** 2 * f2)


def _rweights(H, Wd):
    w = np.full((1, Wd // 2 + 1), 2.0)
    w[0, 0] = 1.0
    if Wd % 2 == 0:
        w[0, -1] = 1.0
    return w


def band_std(X, H, Wd, tf):
    return float(np.sqrt((_rweights(H, Wd) * np.abs(X * tf) ** 2).sum()) / (H * Wd))


def coarse_up(ret_ch, sigma_u, upp_r, shape):
    """Retail channel low-passed at sigma_u (periodic), resampled to `shape` by exact Fourier
    interpolation (the Gaussian has removed everything near retail's Nyquist)."""
    Hr, Wr = ret_ch.shape
    return band_up(ret_ch, _gauss(_f2(Hr, Wr), sigma_u / upp_r), shape)


def band_up(ret_ch, tf_r, shape):
    """Retail channel filtered by tf_r (at retail resolution), Fourier-resampled to `shape`."""
    Hr, Wr = ret_ch.shape
    H, Wd = shape
    X = np.fft.rfft2(ret_ch) * tf_r
    X[Hr // 2, :] = 0.0
    X[:, -1] = 0.0
    Y = np.zeros((H, Wd // 2 + 1), complex)
    hh = Hr // 2
    Y[:hh, :Wr // 2 + 1] = X[:hh]
    Y[H - hh:, :Wr // 2 + 1] = X[Hr - hh:]
    return np.fft.irfft2(Y * (H * Wd) / (Hr * Wr), s=(H, Wd))


def _bisect(f, target, lo, hi, n=50):
    """f monotonic increasing; the x in [lo, hi] with f(x) == target (clamped to the interval)."""
    if f(hi) <= target:
        return hi
    if f(lo) >= target:
        return lo
    for _ in range(n):
        x = 0.5 * (lo + hi)
        if f(x) < target:
            lo = x
        else:
            hi = x
    return 0.5 * (lo + hi)


def banded_match(live, ret, method, U):
    """live, ret: float RGB (any sizes, same aspect). Returns (out float RGB, info).

    1. structure check: luma 4-16u band of the photo vs retail's. Below STRUCT_MIN the photo does not
       HAVE retail's structure (grndset_2af: fine sand vs retail's gravel, 0.21x) and no gain can make it
       - amplifying a near-empty band 7x only makes soft blotches. Then mode 'texel': every band from
       retail's texel size up (sigma = 1 retail texel, the split of the vet's banded B) is retail's own,
       Fourier-resampled (band-limited, no sharpening); the photo keeps the band finer than retail.
    2. otherwise hue ('global' mean or 'field' > COARSE_SIGMA_U), then per channel the 4-16u band:
       moved only into MID_TARGET x retail's std (already inside: untouched) - the photo's own band
       gained, the gain capped at GAIN_CAP; if the cap stops short, the rest of the energy comes from
       retail's own 4-16u band (same resampling).
    The band finer than 4u is never touched in mode 2; below retail's texel never in mode 1."""
    H, Wd = live.shape[:2]
    Hr, Wr = ret.shape[:2]
    assert abs(H / Wd - Hr / Wr) < 1e-9, (live.shape, ret.shape)
    upp, upp_r = U / np.sqrt(H * Wd), U / np.sqrt(Hr * Wr)
    f2, f2r = _f2(H, Wd), _f2(Hr, Wr)
    mid_tf = _gauss(f2, BAND_FINE_U / upp) - _gauss(f2, BAND_MID_U / upp)
    mid_tf_r = _gauss(f2r, BAND_FINE_U / upp_r) - _gauss(f2r, BAND_MID_U / upp_r)
    r_struct = band_std(np.fft.rfft2(luma(live)), H, Wd, mid_tf) / band_std(np.fft.rfft2(luma(ret)), Hr, Wr, mid_tf_r)
    mode = "texel" if r_struct < STRUCT_MIN else method
    out = np.empty_like(live)
    info = dict(method=mode, struct_ratio=round(r_struct, 3), upp=round(upp, 4), upp_retail=round(upp_r, 4),
                gain=[], retail_band=[], shift=[])
    for k in range(3):
        x = live[..., k]
        if mode == "texel":
            s = upp_r                                                  # one retail texel, in world units
            lo_live = np.fft.irfft2(np.fft.rfft2(x) * _gauss(f2, s / upp), s=(H, Wd))
            y = x - lo_live + coarse_up(ret[..., k], s, upp_r, (H, Wd))
            info["shift"].append(round(float(y.mean() - x.mean()), 2))
            out[..., k] = y
            continue
        if mode == "global":
            y = x + (ret[..., k].mean() - x.mean())
        else:
            lo_live = np.fft.irfft2(np.fft.rfft2(x) * _gauss(f2, COARSE_SIGMA_U / upp), s=(H, Wd))
            y = x - lo_live + coarse_up(ret[..., k], COARSE_SIGMA_U, upp_r, (H, Wd))
        info["shift"].append(round(float(y.mean() - x.mean()), 2))
        Y = np.fft.rfft2(y)
        rband = band_std(np.fft.rfft2(ret[..., k]), Hr, Wr, mid_tf_r)
        own = band_std(Y, H, Wd, mid_tf) / rband
        target = rband * min(max(own, MID_TARGET[0]), MID_TARGET[1])      # move only into the target window
        g = _bisect(lambda gg: band_std(Y, H, Wd, mid_tf * (1.0 + (gg - 1.0) * mid_tf)), target, 0.05, GAIN_CAP)
        Z = Y * (1.0 + (g - 1.0) * mid_tf)
        b = 0.0
        if band_std(Z, H, Wd, mid_tf) < target * 0.999:
            RB = np.fft.rfft2(band_up(ret[..., k], mid_tf_r, (H, Wd)))
            b = _bisect(lambda bb: band_std(Z + bb * RB, H, Wd, mid_tf), target, 0.0, 4.0)
            Z = Z + b * RB
        info["gain"].append(round(g, 4))
        info["retail_band"].append(round(b, 4))
        out[..., k] = np.fft.irfft2(Z, s=(H, Wd))
    info["would_clip_pct"] = [round(100 * float(((out[..., k] < 0) | (out[..., k] > 255)).mean()), 3) for k in range(3)]
    info["toe_pct"] = [round(100 * float(((out[..., k] < TOE) | (out[..., k] > 255 - TOE)).mean()), 3) for k in range(3)]
    return toe(out), info


TOE = 4.0


def toe(x):
    """Identity on [TOE, 255-TOE]; below/above, a smooth exponential knee into (0, TOE] / [255-TOE, 255)
    (value and slope continuous), so the few texels the band gain pushes past the rails keep their order
    - detail stays - instead of flattening to 0/255."""
    y = np.array(x, np.float64)
    lo = y < TOE
    y[lo] = TOE * np.exp((y[lo] - TOE) / TOE)
    hi = y > 255.0 - TOE
    y[hi] = 255.0 - TOE * np.exp((255.0 - TOE - y[hi]) / TOE)
    return y


# ============================================================================================ DXT1 encode
def _bc1_chunk(P, Wv):
    m = P.mean(1, keepdims=True)
    sw = np.sqrt(Wv)
    Cc = (P - m) * sw
    cov = np.einsum("nki,nkj->nij", Cc, Cc)
    ax = np.linalg.eigh(cov)[1][:, :, -1] / sw
    ax /= np.maximum(np.linalg.norm(ax, axis=1, keepdims=True), 1e-12)
    t = ((P - m) * ax[:, None, :]).sum(-1)
    e0q = V2._quant(m[:, 0] + t.max(1)[:, None] * ax)
    e1q = V2._quant(m[:, 0] + t.min(1)[:, None] * ax)
    idx, err = V2._assign(P, e0q, e1q, Wv)
    lim = np.array([31, 63, 31])
    for _ in range(2):
        f0, f1 = V2._lsfit(P, idx, Wv)
        c0q, c1q = V2._quant(f0), V2._quant(f1)
        cidx, cerr = V2._assign(P, c0q, c1q, Wv)
        bt = cerr < err
        e0q[bt], e1q[bt], idx[bt], err[bt] = c0q[bt], c1q[bt], cidx[bt], cerr[bt]
        for which in (0, 1):
            for ch in (0, 1, 2):
                for step in (-1, 1):
                    t0, t1 = e0q.copy(), e1q.copy()
                    tg = t0 if which == 0 else t1
                    tg[:, ch] = np.clip(tg[:, ch] + step, 0, lim[ch])
                    cidx, cerr = V2._assign(P, t0, t1, Wv)
                    bt = cerr < err
                    e0q[bt], e1q[bt], idx[bt], err[bt] = t0[bt], t1[bt], cidx[bt], cerr[bt]
    c0 = (e0q[:, 0] << 11) | (e0q[:, 1] << 5) | e0q[:, 2]
    c1 = (e1q[:, 0] << 11) | (e1q[:, 1] << 5) | e1q[:, 2]
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    idx = np.where(swap[:, None], np.array([1, 0, 3, 2])[idx], idx)
    idx = np.where((c0 == c1)[:, None], 0, idx)                       # never 3-colour mode (black/transparent)
    bits = (idx.astype(np.uint64) << (2 * np.arange(16, dtype=np.uint64))).sum(1)
    out = np.zeros((P.shape[0], 8), np.uint8)
    out[:, 0], out[:, 1] = c0 & 255, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 255, c1 >> 8
    for k in range(4):
        out[:, 4 + k] = (bits >> np.uint64(8 * k)) & np.uint64(255)
    return out


def bc1_encode(img, Wv=(1.0, 1.0, 1.0), chunk=16384):
    """Deterministic DXT1 colour encoder for float RGB 0..255 (v2's least-squares scheme with coordinate
    descent on all three channels, uniform RGB error, always 4-colour mode). Blocks row-major."""
    H, Wd = img.shape[:2]
    H4, W4 = max(4, (H + 3) // 4 * 4), max(4, (Wd + 3) // 4 * 4)
    img = np.pad(img, ((0, H4 - H), (0, W4 - Wd), (0, 0)), mode="edge")
    P = img.reshape(H4 // 4, 4, W4 // 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 3).astype(np.float64)
    Wv = np.asarray(Wv, np.float64)
    return b"".join(_bc1_chunk(P[c:c + chunk], Wv).tobytes() for c in range(0, P.shape[0], chunk))


def encode_dds(level0, today_dds):
    """today's header (DXT1, same size, full chain asserted) + our blocks for a float box-mip chain."""
    info = V2.dds_parse(today_dds)
    assert info["fourcc"] == b"DXT1" and info["end"] == len(today_dds)
    assert info["mips"] == V2.full_mips(info["w"], info["h"]) and info["levels"][-1][:2] == (1, 1)
    assert level0.shape[:2] == (info["h"], info["w"])
    out = bytearray(today_dds[:128])
    cur = level0
    for k, (w, h, off, sz) in enumerate(info["levels"]):
        if k:
            cur = V2.box_half(cur)
        assert cur.shape[:2] == (h, w)
        blk = bc1_encode(np.clip(cur, 0, 255))
        assert len(blk) == sz
        out += blk
    assert len(out) == len(today_dds)
    return bytes(out)


def dxt1_bad_blocks(b):
    info = V2.dds_parse(b)
    bad = 0
    for (w, h, off, sz) in info["levels"]:
        blk = np.frombuffer(b[off:off + sz], np.uint8).reshape(-1, 8)
        c0 = blk[:, 0].astype(np.int32) | (blk[:, 1].astype(np.int32) << 8)
        c1 = blk[:, 2].astype(np.int32) | (blk[:, 3].astype(np.int32) << 8)
        bad += int(((c0 < c1) | ((c0 == c1) & (blk[:, 4:8].astype(np.int64).sum(1) != 0))).sum())
    return bad


# ================================================================================================ build
def load_retail(gog, spec):
    game, pak, member, want = spec
    with zipfile.ZipFile(os.path.join(gog, game, pak)) as z:
        real = [n for n in z.namelist() if n.lower() == member]
        assert len(real) == 1, (pak, member, real)
        b = z.read(real[0])
    assert sha(b) == want, "retail %s changed: %s" % (member, sha(b))
    return decode_any(b)


def pre_cc0(stack, base):
    """The file a PLAYER had before the CC0 pack: gl2 order (.dds first), terrain pak + dev-only excluded."""
    for e in (".dds", ".jpg", ".tga", ".png"):
        w = stack.winner(base + e, skip={PAK_NAME})
        if w:
            return stack.name(w[0]) + ":" + base.split("/")[-1] + e, decode_any(stack.read(*w))
    return None, None


def process(src, gog, stack, U_of):
    """-> {member: (new dds bytes, info)}"""
    res = {}
    for member, (method, rspec) in SCOPE.items():
        today = src[member][0]
        live = dds_level0(today)
        ret = load_retail(gog, rspec)
        U = U_of[base_of(member)]
        out, info = banded_match(live, ret, method, U)
        new = encode_dds(out, today)
        info["U"] = round(U, 1)
        res[member] = (new, info, out)
    return res


def build_pak(src, res):
    members = dict(src)
    for m, (new, info, _) in res.items():
        members[m] = (new, FIXED_TS, src[m][2])
    return V2.write_pak(members)


# ============================================================================================== sheets
def _font(sz):
    try:
        return ImageFont.load_default(size=sz)
    except Exception:
        return ImageFont.load_default()


def world_view(rgb, U, win_u, px, cx=0.5, cy=0.5):
    """A win_u x win_u world window (tiling as needed) centred at (cx, cy) of the tile, rendered to px x px
    with area filtering when shrinking and bicubic when enlarging - identical world scale for every panel."""
    H, Wd = rgb.shape[:2]
    upp = U / np.sqrt(H * Wd)
    n = int(round(win_u / upp))
    ys = (np.arange(n) + int(cy * H) - n // 2) % H
    xs = (np.arange(n) + int(cx * Wd) - n // 2) % Wd
    crop = np.clip(rgb[ys][:, xs], 0, 255).astype(np.uint8)
    im = Image.fromarray(crop, "RGB")
    return im.resize((px, px), Image.BOX if n > px else Image.BICUBIC)


def sheet_texture(path, member, U, maps_str, ret, today, new, st):
    name = member.split("/")[-1][:-4]
    P = 420
    rs = st["retail_src"]
    cols = [("RETAIL (%s %s)" % (rs.split(":")[0], os.path.splitext(rs)[1]), ret, st["retail"]),
            ("TODAY v2d_s060", today, st["today"]),
            ("v3 (this pak)", new, st["v3"])]
    rows = [("2 x 2 repeats = %d x %d world units (same scale in all three)" % (2 * U, 2 * U), 2 * U, 0.5, 0.5),
            ("close-up: %d x %d world units (retail texels enlarged)" % (96, 96), 96.0, 0.5, 0.5)]
    gap, top, lab = 10, 58, 18
    Wd = 3 * P + 4 * gap
    Hh = top + len(rows) * (P + lab + gap) + 70
    sh = Image.new("RGB", (Wd, Hh), (24, 24, 28))
    dr = ImageDraw.Draw(sh)
    f, fb = _font(13), _font(15)
    dr.text((gap, 6), "%s   (%s; %.0f units per repeat)" % (member, st["method_txt"], U), fill=(240, 240, 240), font=fb)
    dr.text((gap, 26), "drawn on: " + maps_str[:170], fill=(190, 190, 190), font=f)
    y = top
    for rl, win, cx, cy in rows:
        dr.text((gap, y), rl, fill=(220, 220, 150), font=f)
        for i, (cl, img, s) in enumerate(cols):
            sh.paste(world_view(img, U, win, P, cx, cy), (gap + i * (P + gap), y + lab))
        y += P + lab + gap
    for i, (cl, img, s) in enumerate(cols):
        x = gap + i * (P + gap)
        dr.text((x, y), cl, fill=(235, 235, 235), font=fb)
        dr.text((x, y + 20), "mean RGB %5.1f %5.1f %5.1f   chroma vs retail %.1f" % (*s["mean"], s["chroma"]),
                fill=(210, 210, 210), font=f)
        dr.text((x, y + 38), "fine %.1f   mid(4-16u) %.1f   mottle %.1f" % (s["fine"], s["mid"], s["mottle"]),
                fill=(210, 210, 210), font=f)
    sh.save(path, optimize=True)


def sheet_index(path, rows, header):
    T, gap, lab = 230, 8, 16
    Wd = 3 * T + 4 * gap + 330
    Hh = 40 + len(rows) * (T + lab + gap) + gap
    sh = Image.new("RGB", (Wd, Hh), (24, 24, 28))
    dr = ImageDraw.Draw(sh)
    f, fb = _font(12), _font(15)
    dr.text((gap, 8), header, fill=(240, 240, 240), font=fb)
    y = 40
    for name, U, ret, today, new, txt in rows:
        for i, (cl, img) in enumerate((("retail", ret), ("today v2d", today), ("v3", new))):
            x = gap + i * (T + gap)
            dr.text((x, y), "%s  %s" % (name if i == 0 else "", cl), fill=(220, 220, 150), font=f)
            sh.paste(world_view(img, U, 2 * U, T), (x, y + lab))
        tx = gap + 3 * (T + gap)
        for j, line in enumerate(txt):
            dr.text((tx, y + lab + 4 + 16 * j), line, fill=(215, 215, 215), font=f)
        y += T + lab + gap
    sh.save(path, optimize=True)


def sheet_family(path, tiles, U):
    """The m4l3 complaint pair set: rubble2c (as players draw it) over _1trans over _1rough, and
    m3l3grass_1 | _1rough | _1blast, each tile one repeat, retail / today / v3 side by side."""
    T, gap = 200, 14
    f, fb = _font(13), _font(15)
    cols = ("retail", "today", "v3")
    Wd = 3 * (3 * T) + 4 * gap
    Hh = 60 + 3 * T + gap + T + 60
    sh = Image.new("RGB", (Wd, Hh), (24, 24, 28))
    dr = ImageDraw.Draw(sh)
    dr.text((gap, 8), "m3l3grass transition set, one repeat per tile (m4l3 / m3l3 / e2l3). Top: rubble2c over "
            "_1trans over _1rough (retail shares their borders). Bottom: m3l3grass_1 | _1rough | _1blast",
            fill=(240, 240, 240), font=fb)
    for c, col in enumerate(cols):
        x0 = gap + c * (3 * T + gap)
        dr.text((x0, 34), col.upper(), fill=(220, 220, 150), font=fb)
        for r, nm in enumerate(("rubble2c", "m3l3grass_1trans", "m3l3grass_1rough")):
            img = tiles[nm][c]
            sh.paste(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").resize((T, T), Image.BOX),
                     (x0 + T, 56 + r * T))
            dr.text((x0 + 4, 56 + r * T + T // 2), nm.replace("m3l3grass_", "")[:12], fill=(200, 200, 200), font=f)
        for k, nm in enumerate(("m3l3grass_1", "m3l3grass_1rough", "m3l3grass_1blast")):
            img = tiles[nm][c]
            sh.paste(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").resize((T, T), Image.BOX),
                     (x0 + k * T, 56 + 3 * T + gap))
    dr.text((gap, Hh - 40), "rubble2c and m3l3grass_1 are Omaha-coupled and unchanged in v3 (rubble2c colour comes "
            "from zzzzzzzzzz_coop_hd_m3l1a.pk3).", fill=(190, 190, 190), font=f)
    sh.save(path, optimize=True)


# ================================================================================================ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="staging dir (never the mod tree or a game folder)")
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--gog", default=GOG_DEFAULT)
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--no-double", action="store_true")
    ap.add_argument("--no-stack-check", action="store_true")
    ap.add_argument("--usage-only", action="store_true")
    ap.add_argument("--no-dev-usage", action="store_true", help="skip the dev-install usage report")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    for forbidden in (os.path.join(REPO, "hzm-mohaa-coop-mod"), a.gog, V2.LIVE_BASE, V2.APPDATA_HOME):
        if forbidden:
            assert not os.path.normcase(out).startswith(os.path.normcase(os.path.abspath(forbidden))), \
                "refusing to write into " + forbidden
    os.makedirs(out, exist_ok=True)

    print("== source")
    src_bytes = open(a.src, "rb").read()
    if not gate("source pak is v2d_s060 (sha256 c53eced3...)", sha(src_bytes) == SRC_SHA, sha(src_bytes)):
        sys.exit(2)
    src = V2.read_pak(a.src)
    gate("source member set", len(src) == EXPECTED_MEMBERS and "CREDITS_terrain.txt" in src
         and all(m in src for m in list(SCOPE) + EXCLUDED + DEAD + NH)
         and not any("omaha_set4_shoreline" in n.lower() for n in src), "%d members" % len(src))
    gate("no Omaha asset in scope", not any(V2.OMAHA.search(n) for n in SCOPE), ", ".join(n.split("/")[-1] for n in SCOPE))

    print("== map usage (player stack: retail paks + release manifest paks)")
    stack = Stack(a.gog)
    print("  [INFO] manifest %s; %d paks in the stack; left out (not retail, not in the manifest): %s"
          % (stack.manifest_version, len(stack.srcs), ", ".join(stack.left_out) or "none"))
    bases = [base_of(m) for m in list(SCOPE) + EXCLUDED + DEAD]
    use, nbsp, remap = map_usage(stack, bases)
    gate("no BSP carries a worldspawn remapshader", not remap, "%d BSPs scanned; %s" % (nbsp, remap or "none"))
    for m in SCOPE:
        u = use[base_of(m)]
        om = [p for p in u["maps"] if p in OMAHA_MAPS]
        wm = ["%s=%s" % (p[5:-4], WATCH_MAPS[p]) for p in u["maps"] if p in WATCH_MAPS]
        gate("live, Omaha-free: " + m.split("/")[-1], u["maps"] and not om and u["U"],
             "%s | shaders %s | %s units/repeat%s" % (usage_str(u), ",".join(s.split("/")[-1] for s in u["shaders"]),
                                                      u["U"] and round(u["U"]), ("  WATCH " + "; ".join(wm)) if wm else ""))
    for m in EXCLUDED:
        u = use[base_of(m)]
        om = [p[5:-4] for p in u["maps"] if p in OMAHA_MAPS]
        gate("excluded, Omaha-coupled: " + m.split("/")[-1], bool(om), "draws on %s | all: %s" % (om, usage_str(u)))
    for m in DEAD:
        u = use[base_of(m)]
        print("  [INFO] dead member %s: %s" % (m.split("/")[-1], usage_str(u)))
    # the DEV install (what the user's own machine draws) adds maps players never get - report them
    dev_extra = {}
    if not a.no_dev_usage:
        dstack = Stack(a.gog, dev=True)
        duse, _, _ = map_usage(dstack, [base_of(m) for m in SCOPE])
    for m in (SCOPE if not a.no_dev_usage else []):
        extra = sorted(set(duse[base_of(m)]["maps"]) - set(use[base_of(m)]["maps"]))
        dev_extra[m] = extra
        om = [p for p in extra if p in OMAHA_MAPS]
        gate("dev install adds no Omaha map: " + m.split("/")[-1], not om, "dev-only maps drawing it: %s" % (
            ", ".join(p[5:-4] for p in extra) or "none"))
        if any("omaha" in p for p in extra):
            print("  [WATCH] %s is drawn on a DEV-ONLY map named omaha: %s (y_hzm_maptour.pk3, third-party MP "
                  "map, not in any release; not m3l1a)" % (m.split("/")[-1], [p for p in extra if "omaha" in p]))
    report = dict(source=dict(path=a.src, sha256=SRC_SHA), coarse_sigma_u=COARSE_SIGMA_U,
                  player_stack=dict(manifest=stack.manifest_version, left_out=stack.left_out),
                  dev_only_maps={m: v for m, v in dev_extra.items()},
                  usage={b: dict(maps={p: c for p, c in u["maps"].items()}, shaders=u["shaders"], U=u["U"])
                         for b, u in use.items()})
    if a.usage_only:
        print(json.dumps({b: usage_str(u) for b, u in use.items()}, indent=1))
        return
    U_of = {base_of(m): use[base_of(m)]["U"] for m in SCOPE}

    print("== banded re-match + DXT1 encode")
    res = process(src, a.gog, stack, U_of)
    pak = build_pak(src, res)
    if not a.no_double:
        res2 = process(src, a.gog, stack, U_of)
        gate("deterministic rebuild (in-process)", build_pak(src, res2) == pak, sha(pak))
    with zipfile.ZipFile(io.BytesIO(pak)) as z:
        gate("zip CRC test", z.testzip() is None)
        cm = {zi.filename: z.read(zi) for zi in z.infolist()}
        order = [zi.filename for zi in z.infolist()]
    gate("entries sorted", order == sorted(order))
    gate("member set == v2d_s060", set(cm) == set(src), "%d members" % len(cm))
    unchanged = [n for n in src if n not in SCOPE]
    diff = [n for n in unchanged if cm[n] != src[n][0]]
    gate("every other member byte-identical to v2d_s060", not diff,
         "%d/%d identical (incl. all %d _nh = tilt unchanged, CREDITS, conctrmdrk, excluded + dead)" % (
             len(unchanged) - len(diff), len(unchanged), len(NH)))
    gate("_nh normal maps byte-identical (colour only)", all(cm[n] == src[n][0] for n in NH))
    gate("excluded (Omaha-coupled) members byte-identical", all(cm[n] == src[n][0] for n in EXCLUDED))
    gate("changed members actually changed", all(cm[n] != src[n][0] for n in SCOPE))

    print("== gates per texture")
    per = {}
    for m, (new_b, info, outf) in res.items():
        name = m.split("/")[-1][:-4]
        U = info["U"]
        today = dds_level0(src[m][0])
        new0 = dds_level0(cm[m])
        ret = load_retail(a.gog, SCOPE[m][1])
        pre_src, pre = pre_cc0(stack, base_of(m))
        s_ret, s_today, s_new, s_pre = look(ret, U), look(today, U), look(new0, U), look(pre, U)
        mr = s_ret["mean"]
        for s in (s_ret, s_today, s_new, s_pre):
            s["chroma"] = round(chroma(s["mean"], mr), 2)
        ninfo = V2.dds_parse(cm[m])
        gate("DXT1 full box mip chain, today's header: " + name,
             ninfo["fourcc"] == b"DXT1" and ninfo["mips"] == V2.full_mips(ninfo["w"], ninfo["h"])
             and ninfo["levels"][-1][:2] == (1, 1) and cm[m][:128] == src[m][0][:128] and ninfo["end"] == len(cm[m]),
             "%dx%d, %d levels" % (ninfo["w"], ninfo["h"], ninfo["mips"]))
        bad = dxt1_bad_blocks(cm[m])
        gate("4-colour blocks only: " + name, bad == 0, "%d blocks a decoder would read as 3-colour" % bad)
        gate("chroma <= %g: %s" % (GATE_CHROMA, name), s_new["chroma"] <= GATE_CHROMA,
             "v3 %.2f (today %.2f, pre-CC0 %.2f) | mean RGB retail %s today %s v3 %s" % (
                 s_new["chroma"], s_today["chroma"], s_pre["chroma"], mr, s_today["mean"], s_new["mean"]))
        lim = GATE_FINE * max(s_ret["fine"], s_pre["fine"])
        gate("fine grain <= %.2f x max(retail, pre-CC0): %s" % (GATE_FINE, name), s_new["fine"] <= lim,
             "v3 %.2f <= %.2f (retail %.2f, pre-CC0 %.2f, today %.2f)" % (s_new["fine"], lim, s_ret["fine"],
                                                                           s_pre["fine"], s_today["fine"]))
        r = s_new["mid"] / s_ret["mid"]
        gate("mid structure %.2f-%.2f x retail: %s" % (GATE_MID[0], GATE_MID[1], name), GATE_MID[0] <= r <= GATE_MID[1],
             "v3 %.2f = %.2fx retail %.2f (today %.2f = %.2fx)" % (s_new["mid"], r, s_ret["mid"], s_today["mid"],
                                                                 s_today["mid"] / s_ret["mid"]))
        zt, zn = wrap_z(today, block=True), wrap_z(new0, block=True)      # decoded vs decoded
        zta, zf = wrap_z(today), wrap_z(outf)                                # today (all lines) vs v3 before encode
        gate("wrap seam not worse: " + name, zn <= max(1.10 * zt, zt + 0.10) and zf <= max(1.10 * zta, zta + 0.10),
             "decoded (vs block lines) v3 %.2f / today %.2f | v3 before encode %.2f / today %.2f | retail %.2f"
             % (zn, zt, zf, zta, wrap_z(ret)))
        # mip means stay put (box chain). >= 16x16: within 1 level. Smaller (<= 16 blocks, 565 quantisation
        # dominates): no worse than today's own file at those levels.
        def lvl_dev(b):
            inf = V2.dds_parse(b)
            mm = [(min(w, h), dds_level0_level(b, k).reshape(-1, 3).mean(0)) for k, (w, h, o, s) in enumerate(inf["levels"])]
            big = max(float(np.abs(x - mm[0][1]).max()) for d, x in mm if d >= 16)
            small = max([float(np.abs(x - mm[0][1]).max()) for d, x in mm if d < 16] or [0.0])
            return big, small
        nb_, ns_ = lvl_dev(cm[m])
        tb_, ts_ = lvl_dev(src[m][0])
        gate("mip means follow level 0 (box chain): " + name, nb_ <= 1.0 and ns_ <= max(ts_, 1.0),
             "max |mean(level k) - mean(level 0)|: levels >= 16px v3 %.2f (today %.2f); smaller v3 %.2f (today %.2f)"
             % (nb_, tb_, ns_, ts_))
        rms = [round(float(np.sqrt(((new0[..., k] - outf[..., k]) ** 2).mean())), 2) for k in range(3)]
        print("  [INFO] %s: method %s, U %.0f, shift %s, 4-16u gain %s, past the rails %s%% (toe'd %s%%), "
              "DXT1 RMS R,G,B %s" % (name, info["method"], U, info["shift"], info["gain"], info["would_clip_pct"],
                                     info["toe_pct"], rms))
        method_txt = {"global": "per-channel mean -> retail, 4-16u band -> retail",
                      "field": "per-channel colour field > %gu -> retail, 4-16u band -> retail" % COARSE_SIGMA_U,
                      "texel": "photo lacks retail's structure (4-16u %.2fx): retail's own bands >= 1 retail texel "
                               "(%.1fu), photo's finer grain kept" % (info["struct_ratio"], info["upp_retail"]),
                      }[info["method"]]
        per[m] = dict(info=info, retail_src="%s/%s:%s" % SCOPE[m][1][:3], pre_src=pre_src, dxt1_rms=rms,
                      retail=s_ret, pre=s_pre, today=s_today, v3=s_new, wrap_z=dict(today=round(zt, 3), v3=round(zn, 3)),
                      member_sha256=sha(cm[m]), method_txt=method_txt, maps=usage_str(use[base_of(m)]))

    if not a.no_stack_check:
        names = {n.lower() for n in cm}
        V2.stack_check("live G:/mohaa-gl2", V2.search_order(V2.LIVE_BASE, V2.LIVE_HOME, a.gog), names, sorted(SCOPE))
        if V2.APPDATA_HOME and os.path.isdir(V2.APPDATA_HOME):
            V2.stack_check("plain GOG launch", V2.search_order(a.gog, V2.APPDATA_HOME, None), names, sorted(SCOPE))

    fn = "zzzzzzzzz_coop_terrain.v3.pk3"
    with open(os.path.join(out, fn), "wb") as fh:
        fh.write(pak)
    report["pak"] = dict(file=fn, sha256=sha(pak), bytes=len(pak))
    report["textures"] = per

    if not a.no_sheets:
        print("== sheets")
        sd = os.path.join(out, "sheets")
        os.makedirs(sd, exist_ok=True)
        rows = []
        tiles = {}
        for m, st in per.items():
            name = m.split("/")[-1][:-4]
            U = st["info"]["U"]
            ret = load_retail(a.gog, SCOPE[m][1])
            today = dds_level0(src[m][0])
            new0 = dds_level0(cm[m])
            sheet_texture(os.path.join(sd, "sheet_%s.png" % name), m, U, st["maps"], ret, today, new0, st)
            rows.append((name, U, ret, today, new0, [
                {"global": "hue: per-channel mean -> retail", "field": "hue: colour field > %gu -> retail" % COARSE_SIGMA_U,
                 "texel": "retail bands >= 1 retail texel + photo grain"}[st["info"]["method"]],
                "chroma vs retail: today %.1f -> v3 %.1f" % (st["today"]["chroma"], st["v3"]["chroma"]),
                "mid 4-16u: today %.2fx -> v3 %.2fx retail" % (st["today"]["mid"] / st["retail"]["mid"],
                                                             st["v3"]["mid"] / st["retail"]["mid"]),
                "fine: retail %.1f today %.1f v3 %.1f" % (st["retail"]["fine"], st["today"]["fine"], st["v3"]["fine"]),
                "maps: " + ", ".join(p.split(" ")[0] for p in st["maps"].split("; "))[:44]]))
            if name in ("m3l3grass_1trans", "m3l3grass_1rough", "m3l3grass_1blast"):
                tiles[name] = (ret, today, new0)
        sheet_index(os.path.join(sd, "index.png"), rows, "Terrain pak v3 (banded colour re-match) - retail | today "
                    "(v2d_s060) | v3, 2x2 repeats at each texture's world scale.  pak sha256 %s" % sha(pak)[:16])
        # family sheet: rubble2c + m3l3grass_1 as PLAYERS draw them (unchanged in v3)
        for nm, member in (("rubble2c", "textures/mohtest/rubble2c"), ("m3l3grass_1", W + "m3l3grass_1")):
            w = stack.winner(member + ".dds")
            drawn = decode_any(stack.read(*w)) if w and os.path.basename(stack.srcs[w[0]][1]).lower() != PAK_NAME \
                else dds_level0(src[member + ".dds"][0])
            tiles[nm] = (load_retail(a.gog, RETAIL_EXTRA[nm]), drawn, drawn)
        sheet_family(os.path.join(sd, "family_m3l3grass.png"), tiles, 512)
        print("  ", sd)

    report["gates"] = V2.GATES
    with open(os.path.join(out, "gates_v3.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1)
    bad = [g for g in V2.GATES if not g["ok"]]
    print("\n%d gates, %d failed" % (len(V2.GATES), len(bad)))
    print("  %s  %s  %d" % (fn, sha(pak), len(pak)))
    sys.exit(1 if bad else 0)


def dds_level0_level(b, k):
    return V2.dds_decode_level(b, V2.dds_parse(b), k)[..., :3].astype(np.float64)


if __name__ == "__main__":
    main()

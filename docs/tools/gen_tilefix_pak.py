# -*- coding: utf-8 -*-
"""Tile-wrap seam repair pak - Phase 3 of the vetted ground-seam plan (bug-2984, v2 bug-2991; family bug-2950..2954).

Plan: docs/proposals/seams_2026-09-25/vet_seams.md - Phase 3, findings F13-F18 and F23 (the vet is authoritative
over report_seams.md). User decisions: D1 the dev-only paks (zzzzzzzz_hd_seamfix / _groundfix) are set aside, so the
install IS the player stack; D2 Omaha-coupled textures stay unfixed, excluded BY MAP (vet F14).

Writes ONE pak, zzzzzzzzzz_coop_hd_a_tilefix.pk3, into --out (never the mod tree or a game folder):

  textures/.../<name>.dds   for every in-scope ground texture whose tile wrap shows a seam retail does not have.
      Source = the HD art (the jpg/tga the hdmem/override DDS was encoded from - accepted only when its high-pass
      correlates with the decoded DDS like DXT noise allows, so a re-upscale of the same retail art is refused - or
      the live jpg/tga itself); never a decoded DXT (vet F16). Repair = periodic-plus-smooth (Moisan) wrap correction
      applied to the LOW-FREQUENCY part of the wrap jump only (jump profiles low-passed along the edge before the
      Poisson solve): no cross-fade, no mirror (vet F18), mean and interior detail kept = today's look. The widest
      along-edge low-pass that clears Z_TARGET x the z limit is kept (binary search); "amplified" textures (retail
      itself draws an authored line there, vet class amp) are corrected only down to retail's own z (smallest alpha).
      Then a PERIODIC Lanczos-3 resample (wrap taps, bug-1247) to the live size, power-of-two (r_roundImagesDown 1),
      encoded once with gen_terrain_pak_v2.bc_colour_blocks (Pillow's DXT encoder skews red - TRAPS T2, bug-2953),
      DXT1 no alpha, float 2x2 BOX mips to 1x1 (vet F10/F17).
  textures/.../<name>.jpg   ONLY where the gl2 generated relief itself carries the seam: for a DDS diffuse,
      R_HZM_GenerateNormalMapFromSource (tr_image.c:3109) builds the relief from the first png/tga/jpg SIBLING, so a
      DDS-only fix leaves a lighting line at every repeat. Same name, extension and size as today's sibling, the same
      repair (stronger rungs if the relief needs them), gated on the engine's own height maths (engine_genheight).
      With r_ext_compressed_textures 0 this file is also the diffuse, hence the brightness/p99/clip gates on it too.
  textures/mohtest/cathedarchlrg.dds   the black stained-glass fix (bug-2954): retail RGB (panes are painted under an
      all-zero alpha, the surface has no shader def = opaque), 4x Lanczos + mild unsharp 1.2/55/3 on an S-wrap /
      T-edge padded canvas, clamped to the source range, DXT1 no alpha, box mips - the gen_terrain_pak_v2 conctrmdrk
      recipe, but with that file's own encoder instead of Pillow's. No ESRGAN.

Player stack = retail + the paks in manifests/latest.json (+ STAGED_NEWER); every other installed pak (dev-only
seamfix/groundfix, y_hzm_maptour, ...) and this pak itself are ignored as inputs.

Scope (all asserted/logged into <out>/tilefix_scope.json and <out>/tilefix_report.json):
  candidates  ground images (terrain patches, brush/soup/bezier-patch triangles with |n.z| >= 0.7) of every map the
              stack loads, whose live wrap z >= 2 while retail z < 1.5 (new), or live > 1.5x an authored retail
              line with retail z < 2.5 (amp), or a live soft/mirrored border band where retail has none (soft).
  excluded    - OMAHA BY MAP: any image any shader / static model / entity model draws on m3l1a, m3l1b, e3l1, e3l2
                (D2) and the MP Omaha Beach map obj/obj_team3 (conservative addition); Omaha-named assets.
              - names a protected coop pak ships in ANY extension (m3l1a, shadowfix, skies, the CC0 terrain pak,
                fxfix, and anything that sorts above this pak) - a .dds here would out-rank their .jpg/.tga.
              - with --sp-only: drawn ONLY on MP maps (dm/ obj/ lib/) - the v1 scope (MP approved 2026-09-26).
              - never drawn across its wrap (no triangle's s/t range crosses an integer), alpha-used, clamp-only,
                no retail reference, no matching HD source.
              - CONTENT_CUT below (reviewed at native resolution against retail: the HD art slices an object at the
                wrap, which a low-frequency correction cannot fix and no gate sees - vet F16).
              - gate failures (listed with the binding gate; gate_whatif in the report counts relaxed limits).

Gates (vet F10/F16), on the ENCODED file: wrap z <= max(1.2, retail z); correction p99 <= 12 levels and clipped <= 0.05%
of channel values, counting only values the clamp cuts by more than 2 levels (both relaxed from the vet's 8 / any-clamp,
user-approved 2026-09-26, bug-2991); border band >= min(0.85, 0.95 x retail band); mean-luma shift <= 2%,
chroma shift <= 1.5; per-mip z (512..64 px) <= max(limit, the same level of the float box chain) + 0.5; brightness
sanity; DXT1, power-of-two, full mip chain, 4-colour blocks only. Pak: sorted entries, fixed timestamps, member bytes
re-built for a sample and compared; every member resolves to this pak on the live G:/mohaa-gl2 stack; sorts above
hdmem (7 z), override (7 z), fxfix (8 z), terrain (9 z) and below the m3l1a / shadowfix / skies paks.
Two independent runs (fresh --cache) give the same sha256.

Known residual: the HD art is upscaled per tile, so its wrap also carries a 1-px high-frequency crack (per-pixel wrap
step 2-4x the interior vs ~1x in retail). A low-frequency repair leaves it by design; it is invisible at the 3x3 scale.

  python docs/tools/gen_tilefix_pak.py --out <dir>                 scan + build + sheets (~10 min cold, 12 workers)
  python docs/tools/gen_tilefix_pak.py --out <dir> --stage scan    scope only (writes <out>/tilefix_scope.json)
  python docs/tools/gen_tilefix_pak.py --out <dir> --stage sheets  redraw the contact sheets from a finished build
  --only a,b   restrict the build to these image bases (debug)      --jobs N   worker processes
  --baseline R  an earlier tilefix_report.json: report + sheet what this build newly admits      --sp-only   v1 scope
  --cache DIR  census/metrics/build-result cache (keys: member CRCs, BUILD_VERSION, gen_terrain_pak_v2 source)
"""
import argparse, hashlib, io, json, math, os, re, struct, sys, time, zipfile
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")              # one BLAS thread per worker process (they run in parallel)
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_terrain_pak_v2 as TV2          # bc_colour_blocks, box_half, dds_parse, dds_decode_level, full_mips, fs_key

Image.MAX_IMAGE_PIXELS = None
REPO = os.path.dirname(os.path.dirname(HERE))
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LIVE_BASE = r"G:\mohaa-gl2"
LIVE_HOME = r"G:\mohaa-gl2\home"
APPDATA_HOME = os.path.join(os.environ["APPDATA"], "openmohaa") if os.environ.get("APPDATA") else ""
PAK_NAME = "zzzzzzzzzz_coop_hd_a_tilefix.pk3"
FIXED_TS = (2026, 9, 26, 0, 0, 0)
NEW_ATTR = 0x81B60000
ENC_W = (1.0, 1.0, 1.0)                  # colour weights for bc_colour_blocks (its default weights are for normal maps)

RETAIL = {("main", n) for n in ("pak0.pk3", "pak1.pk3", "pak2.pk3", "pak3.pk3", "pak4.pk3", "pak5.pk3", "pak6enuk.pk3", "pak7.pk3")}
RETAIL |= {("mainta", "pak%d.pk3" % i) for i in range(1, 6)}
RETAIL |= {("maintt", "pak%d.pk3" % i) for i in range(1, 5)}
DEV_ONLY = {"zzzzzzzz_hd_seamfix.pk3", "zzzzzzzz_hd_groundfix.pk3"}          # D1: set aside, never in a manifest
MANIFEST = os.path.join(REPO, "manifests", "latest.json")   # the PLAYER stack = retail + the paks this lists
# staged by publish_release.ps1 but newer than latest.json (env/hzmhd/* only - no name overlap, kept for the checks)
STAGED_NEWER = {"zzzzzzzzzz_coop_hd_skies.pk3"}
PROTECTED_BELOW = {"zzzzzzzzz_coop_terrain.pk3", "zzzzzzzz_hd_fxfix.pk3"}    # coop fix paks this pak would override
SHADOWFIX = "zzzzzzzzzz_coop_hd_shadowfix.pk3"
M3L1A_PAK = "zzzzzzzzzz_coop_hd_m3l1a.pk3"
OMAHA_MAPS = ("m3l1a", "m3l1b", "e3l1", "e3l2")                            # D2 (vet F14 + the user's m3l1b)
OMAHA_MP = ("obj/obj_team3",)                                              # MP Omaha Beach - conservative
OMAHA_TOK = re.compile(r"(omaha|obeach|ocean|seabed|wetsand|shoreline|surf|wake|dday)", re.I)
NONART = re.compile(r"(water|ocean|sky|tree|caulk|nodraw|clip|trigger|sprite|foliage|leaf|leaves|bush|glass|window|"
                    r"noise|opaque|caustic|fog|shadow|decal|hint|skip|origin|areaportal|common/|null|black|mirror|"
                    r"lightfixture|/fx|coop_fx|subpen_water|lava|ivy|vine|hedge|grasspatch|cattail|reed)", re.I)
IMG_EXT = (".dds", ".jpg", ".jpeg", ".tga", ".png", ".pcx", ".bmp")
SPECIAL = ("$lightmap", "$whiteimage", "*white", "$fromentity", "$blackimage")

# Reviewed 3x3 tilings (tilefix sheets, 2026-09-26): the wrap cuts through STRUCTURE (a stone field meeting gravel,
# a plank or kerb ending mid-object). A wrap correction only moves low frequencies, so these stay visible whatever the
# gates say (vet F16). Left for a rebuild from the original art (user decision 7). Filled from the review.
CONTENT_CUT = {
    "textures/general_structure/floor4": "planks: the HD art ends a plank/knot on the T wrap; retail runs through",
    "textures/it_terrain/it_t_2-1grass512-02": "grass tufts sliced on the S wrap (HD only; retail continuous)",
    "textures/misc_outside/mosswall": "leaf cluster sliced on the S wrap (HD only)",
    "textures/misc_outside/bocroad_set1b": "one quadrant is different ground (blurred scrub) - both wraps cut it",
    "textures/af_extwall/af-e-stonewall03highpass": "a different stone block starts exactly on the S wrap; retail's courses continue",
    "textures/af_extwall/af-e-stonewall03dusty": "same art as stonewall03highpass: stone block cut on the S wrap",
    # v2 review (relaxed gates + MP scope admitted 55 more; these 10 slice an object or switch surface at the wrap)
    "textures/af_extwall/af-e-stonewall03": "same art family: stone block cut on the S wrap",
    "textures/af_extwall/af-e-concrete2a": "one quadrant is a different, rough concrete - both wraps cut it",
    "textures/af_extwall/af-e-concrete2b": "same art as concrete2a: rough quadrant cut by both wraps",
    "textures/af_extwall/af-e-wallcastle05a": "quadrants of different grain (smooth vs rough) meet on the wraps",
    "textures/das_boot/corded_handle": "the weave changes direction across the T wrap",
    "textures/misc_outside/mudpath_trans2": "a pink stone is sliced by the T wrap",
    "textures/mohtest/cityrbbl1a": "the big rock at the centre is sliced by the S wrap; retail's is whole",
    "textures/mohtest/rubble2": "quadrants of different rubble meet on both wraps",
    "textures/mohtest/rubble2b": "same art as rubble2: different rubble per quadrant",
    "textures/mohtest/whtrckwal1": "a wall stone ends mid-stone on the S wrap",
}

# Gate limits (vet F10 / F16)
Z_FLOOR = 1.2
P99_MAX = 12.0             # user-approved 2026-09-26 (vet F16 had 8): correction p99, 8-bit levels, all channel values
CLIP_MAX = 0.0005          # share of channel values the [0,255] clamp cuts by MORE than CLIP_LEVELS (approved; vet: any)
CLIP_LEVELS = 2
BAND_FLOOR = 0.85
BAND_RETAIL = 0.95
BRIGHT_MAX = 0.02
CHROMA_MAX = 1.5
MIP_SLACK = 0.5
Z_TARGET = 0.88            # the ladder aims below the z limit: the DXT encode adds block-edge noise at the wrap
MIP_MIN = 64               # per-mip z from 512 down to 64 px; at 32 px and below a DXT level is mostly 4x4-block edges
LADDER = tuple(1.0 / d for d in (16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 128))   # along-edge low-pass sigma / edge length
TILE_MIN = 0.01                                      # min share of drawn area whose triangles cross the wrap
SRC_HP_MIN = 0.80           # HD source vs the decoded live DDS at the DDS size: SAME ART when the high-pass (L - blur 2)
SRC_LF_MIN = 0.98           # correlates like DXT noise allows (own encoder ~0.95), the low-pass (blur 4) correlates,
SRC_MEAN_MAX = 4.0         # and no channel mean moves more than 4 levels. A re-upscale of the same retail art fails the
                           # high-pass test (its invented detail differs).

CATH = "textures/mohtest/cathedarchlrg"
BUILD_VERSION = 6          # bump on any change to the per-texture build maths (keys the --cache build results)


def _jdefault(o):
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def strip_ext(p):
    b, e = os.path.splitext(p)
    return b if e.lower() in IMG_EXT or e.lower() == ".jpeg" else p


# ================================================================================================= the pak stack
def stack_layers(gog, home, extra=None):
    """Mount order, LOWEST priority first, as FS_Startup builds it: main, mainta, maintt; per game the GOG dir then the
    homepath dir (the live basepath G:/mohaa-gl2 junctions into GOG - same files); each dir's paks sorted with
    FS_PathCmp (files.cpp:2834, :3111) and prepended, then the loose dir on top (files.cpp:3140-3155).
    extra = (game, dirpath, pakname, path) inserts a virtual pak at its sorted place (the staged tilefix pak)."""
    layers, seen = [], set()
    for game in ("main", "mainta", "maintt"):
        for root in (gog, home):
            if not root:
                continue
            d = os.path.join(root, game)
            if not os.path.isdir(d):
                continue
            key = os.path.normcase(os.path.realpath(d))
            if key in seen:
                continue
            seen.add(key)
            paks = [(f, os.path.join(d, f)) for f in os.listdir(d) if f.lower().endswith(".pk3")]
            if extra and os.path.normcase(os.path.realpath(extra[1])) == key:
                paks = [p for p in paks if p[0].lower() != extra[2].lower()] + [(extra[2], extra[3])]
            for f, p in sorted(paks, key=lambda x: TV2.fs_key(x[0])):
                layers.append(dict(kind="pak", game=game, dir=d, name=f, path=p,
                                   retail=(game, f.lower()) in RETAIL and root == gog))
            layers.append(dict(kind="dir", game=game, dir=d, name="<loose " + d + ">", path=d, retail=False))
    return layers


def _relevant(lo):
    e = os.path.splitext(lo)[1]
    return e in IMG_EXT or e in (".shader", ".bsp", ".tik") or lo.startswith("scripts/")


class Stack:
    def __init__(self, layers, skip_paks=()):
        self.layers = layers
        self.members = {}
        self._z = {}
        for rank, L in enumerate(layers):
            if L["kind"] == "pak":
                if L["name"].lower() in skip_paks:
                    continue
                with zipfile.ZipFile(L["path"]) as z:
                    for zi in z.infolist():
                        if zi.is_dir():
                            continue
                        lo = zi.filename.replace("\\", "/").lower()
                        if _relevant(lo):
                            self.members.setdefault(lo, []).append((rank, zi.filename, zi.CRC, zi.file_size))
            else:
                for sub in ("textures", "maps", "scripts", "models", "env"):
                    top = os.path.join(L["path"], sub)
                    if not os.path.isdir(top):
                        continue
                    for dp, dn, fn in os.walk(top):
                        for f in fn:
                            full = os.path.join(dp, f)
                            lo = os.path.relpath(full, L["path"]).replace("\\", "/").lower()
                            if _relevant(lo):
                                self.members.setdefault(lo, []).append((rank, full, None, os.path.getsize(full)))
        for v in self.members.values():
            v.sort(key=lambda r: r[0])

    def read(self, rank, name):
        L = self.layers[rank]
        if L["kind"] == "dir":
            with open(name, "rb") as fh:
                return fh.read()
        if rank not in self._z:
            self._z[rank] = zipfile.ZipFile(L["path"])
        return self._z[rank].read(name)

    def winner(self, path, retail_only=False, exclude_ranks=()):
        for rank, n, crc, sz in reversed(self.members.get(path.lower(), [])):
            if retail_only and not self.layers[rank]["retail"]:
                continue
            if rank in exclude_ranks:
                continue
            return self.rec(path, rank, n, crc, sz)
        return None

    def rec(self, path, rank, n, crc, sz):
        L = self.layers[rank]
        return dict(path=path.lower(), rank=rank, member=n, crc=crc, size=sz, pak=L["name"], game=L["game"],
                    loose=L["kind"] == "dir", retail=L["retail"])

    def resolve(self, name, req_ext=".tga", retail_only=False, compressed=True):
        """What gl2 R_LoadImage (tr_image.c:2462) draws: .dds first with r_ext_compressed_textures 1; a .tga request
        tries .jpg first (OpenMOHAA); then the requested extension; then the loader table png,tga,jpg,jpeg,pcx,bmp."""
        base = strip_ext(name.lower().replace("\\", "/"))
        order = [".dds"] if compressed else []
        if req_ext in (".tga",):
            order += [".jpg", ".tga"]
        elif req_ext:
            order += [req_ext]
        order += [e for e in (".png", ".tga", ".jpg", ".jpeg", ".pcx", ".bmp") if e not in order]
        for e in order:
            w = self.winner(base + e, retail_only=retail_only)
            if w:
                return w
        return None

    def height_source(self, base, exclude_ranks=()):
        """The non-DDS sibling R_HZM_GenerateNormalMapFromSource (tr_image.c:3109) decodes as the height field for a
        DDS diffuse: imageLoaders order png, tga, jpg, jpeg, pcx, bmp (tr_image.c:2444)."""
        for e in (".png", ".tga", ".jpg", ".jpeg", ".pcx", ".bmp"):
            w = self.winner(base + e, exclude_ranks=exclude_ranks)
            if w:
                return w
        return None


def decode_rgba(b):
    """Level 0 as float RGBA (DDS via Pillow; Pillow reads level 0 of a mipped DDS)."""
    im = Image.open(io.BytesIO(b))
    im.load()
    return np.asarray(im.convert("RGBA")).astype(np.float64)


# ====================================================================================================== shaders
_tok = re.compile(r'"[^"]*"|\{|\}|[^\s{}"]+')


def parse_shader_text(txt):
    txt = re.sub(r"//[^\n]*", "", txt)
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    stream = []
    for ln_no, ln in enumerate(txt.replace("\r", "").split("\n")):
        for t in _tok.findall(ln):
            stream.append((ln_no, t))
    res, depth, name = {}, 0, None
    glob, stages, cur, last = [], [], None, {1: None, 2: None}
    for ln_no, t in stream:
        if depth == 0:
            if t == "{":
                depth, glob, stages, cur, last = 1, [], [], None, {1: None, 2: None}
            elif t != "}":
                name = t.strip('"')
            continue
        if t == "{":
            depth += 1
            if depth == 2:
                cur, last[2] = [], None
            continue
        if t == "}":
            if depth == 2 and cur is not None:
                stages.append(cur)
                cur = None
            depth -= 1
            if depth == 0 and name:
                res.setdefault(name.lower(), dict(name=name, glob=glob, stages=stages))
                name = None
            continue
        if depth == 1:
            if last[1] != ln_no:
                glob.append([])
                last[1] = ln_no
            glob[-1].append(t)
        elif depth == 2 and cur is not None:
            if last[2] != ln_no:
                cur.append([])
                last[2] = ln_no
            cur[-1].append(t)
    return res


def load_shaders(st):
    """name -> (def, file). Whole-file override by path (the highest-priority copy of each scripts/*.shader); a name
    in several files resolves to the highest-priority pak and, within one pak, the alphabetically FIRST file (TRAPS T6,
    bug-2485)."""
    files = {}
    for path, cands in st.members.items():
        if path.startswith("scripts/") and path.endswith(".shader"):
            rank, n, _, _ = cands[-1]
            files[path] = (rank, n)
    table = {}
    for path in sorted(files):
        rank, member = files[path]
        try:
            txt = st.read(rank, member).decode("latin1")
        except Exception:
            continue
        for nm, d in parse_shader_text(txt).items():
            if nm not in table or rank > table[nm][2]:
                table[nm] = (d, path, rank)
    return table


def stage_images(d):
    """Every image a shader draws: (image, stage_lines, is_first_bundle) for map/clampmap/animmap frames, both bundles."""
    out = []
    for st in d["stages"]:
        first = True
        for ln in st:
            k = ln[0].lower()
            if k == "nextbundle":
                first = False
                continue
            if k in ("map", "clampmap", "clampmapx", "clampmapy") and len(ln) > 1:
                out.append((ln[1].strip('"'), st, first, k))
            elif k == "animmap" and len(ln) > 2:
                for f in ln[2:]:
                    out.append((f.strip('"'), st, first, k))
    return out


def shader_image_bases(name, table):
    d = table.get(name.lower())
    if not d:
        return {strip_ext(name.lower())}
    out = set()
    for img, _, _, _ in stage_images(d[0]):
        lo = img.lower()
        if lo in SPECIAL or lo.startswith("$") or lo.startswith("*"):
            continue
        out.add(strip_ext(lo))
    return out


def diffuse_of(name, table):
    """(image base, requested ext, alpha_used, clamp) of the shader's diffuse = first bundle of the first stage map."""
    d = table.get(name.lower())
    if not d:
        return strip_ext(name.lower()), os.path.splitext(name.lower())[1] or ".tga", False, False
    for img, st, first, k in stage_images(d[0]):
        lo = img.lower()
        if not first or lo in SPECIAL or lo.startswith("$") or lo.startswith("*"):
            continue
        keys = [ln[0].lower() for ln in st]
        alpha = "alphafunc" in keys or any(ln[0].lower() == "blendfunc" and "alpha" in " ".join(ln[1:]).lower() for ln in st)
        return strip_ext(lo), os.path.splitext(lo)[1] or ".tga", alpha, k.startswith("clampmap")
    return None, None, False, False


def image_refs(table):
    """image base -> list of (shader, requested ext, alpha_used) over EVERY shader stage referencing it."""
    refs = {}
    for nm, (d, _, _) in table.items():
        for img, st, first, k in stage_images(d):
            lo = img.lower()
            if lo in SPECIAL or lo.startswith("$") or lo.startswith("*"):
                continue
            keys = [ln[0].lower() for ln in st]
            alpha = "alphafunc" in keys or any(ln[0].lower() == "blendfunc" for ln in st)
            refs.setdefault(strip_ext(lo), []).append((nm, os.path.splitext(lo)[1], alpha))
    return refs


# ========================================================================================================= BSPs
def bsp_lumps(b):
    ident, version = struct.unpack_from("<4si", b, 0)
    n = 29 if version <= 18 else 28
    L = [struct.unpack_from("<ii", b, 12 + 8 * i) for i in range(n)]
    if version <= 18:
        L = L[:13] + L[14:]           # LUMP_FOGS at 13 existed up to version 18 (qfiles.h:496)
    return version, L


def parse_bsp(b):
    """shaders; ground area per shader (planar/soup triangles and bezier control-grid triangles with |n.z| >= 0.7,
    sky excluded) + terrain patch counts; static model and entity model paths; worldspawn message."""
    version, L = bsp_lumps(b)

    def lump(i):
        o, l = L[i]
        return b[o:o + l]
    sh = lump(0)
    shaders, sflags = [], []
    for i in range(len(sh) // 140):
        shaders.append(sh[i * 140:i * 140 + 64].split(b"\0")[0].decode("latin1").lower())
        sflags.append(struct.unpack_from("<i", sh, i * 140 + 64)[0])
    dv = lump(4)
    nv = len(dv) // 44
    DV = np.frombuffer(dv[:nv * 44], dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2),
                                                      ("n", "<f4", 3), ("c", "u1", 4)]))
    V = DV["xyz"].astype(np.float64)
    ST = DV["st"].astype(np.float64)
    IX = np.frombuffer(lump(5), "<i4")
    sf = lump(3)
    ground, drawn, wrapped = {}, {}, {}
    for i in range(len(sf) // 108):
        sn, fog, stp, fv, nvx, fi, nix = struct.unpack_from("<7i", sf, i * 108)
        if not (0 <= sn < len(shaders)) or sflags[sn] & 0x4:       # SURF_SKY
            continue
        if stp in (1, 3):
            if nix < 3:
                continue
            idx = IX[fi:fi + nix].reshape(-1, 3) + fv
        elif stp == 2:
            pw, ph = struct.unpack_from("<2i", sf, i * 108 + 96)
            if pw < 2 or ph < 2 or pw * ph > nvx:
                continue
            g = np.arange(pw * ph).reshape(ph, pw) + fv
            a0, a1, a2, a3 = g[:-1, :-1].ravel(), g[:-1, 1:].ravel(), g[1:, :-1].ravel(), g[1:, 1:].ravel()
            idx = np.concatenate([np.stack([a0, a1, a2], 1), np.stack([a1, a3, a2], 1)])
        else:
            continue
        if idx.max() >= nv:
            continue
        P = V[idx]
        cr = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        ar = np.linalg.norm(cr, axis=1) * 0.5
        nz = np.where(ar > 1e-6, cr[:, 2] / np.maximum(2 * ar, 1e-9), 0)
        g = np.abs(nz) >= 0.7
        if g.any():
            ground[sn] = ground.get(sn, 0.0) + float(ar[g].sum())
        # does the texture's WRAP line get drawn? a triangle whose s or t range strictly crosses an integer
        T = ST[idx]
        lo, hi = T.min(1) + 1e-3, T.max(1) - 1e-3
        cross = (np.floor(lo) != np.floor(hi)).any(1) & (hi > lo).all(1)
        drawn[sn] = drawn.get(sn, 0.0) + float(ar.sum())
        wrapped[sn] = wrapped.get(sn, 0.0) + float(ar[cross].sum())
    tr = lump(22)
    terr = {}
    for i in range(len(tr) // 388):
        shn = struct.unpack_from("<H", tr, i * 388 + 40)[0]
        terr[shn] = terr.get(shn, 0) + 1
    models = set()
    sm = lump(25)
    for i in range(len(sm) // 164):
        m = sm[i * 164:i * 164 + 128].split(b"\0")[0].decode("latin1").lower().replace("\\", "/")
        if m:
            models.add(m)
    ent = lump(14).decode("latin1", "replace")
    msg = ""
    first = True
    for blk in re.findall(r"\{([^{}]*)\}", ent):
        kv = re.findall(r'"([^"]*)"\s+"([^"]*)"', blk)
        for k, v in kv:
            kl = k.lower()
            if kl == "model" and v and not v.startswith("*"):
                models.add(v.lower().replace("\\", "/"))
            if first and kl == "message":
                msg = v
        first = False
    return dict(version=version, shaders=shaders, ground={str(k): round(v) for k, v in ground.items()},
                terrain={str(k): v for k, v in terr.items()}, models=sorted(models), message=msg,
                drawn={str(k): round(v) for k, v in drawn.items()}, wrapped={str(k): round(v) for k, v in wrapped.items()})


CENSUS_VERSION = 2


def tik_shaders(st, path, seen=None, depth=0):
    """Shader/image names a TIKI (and its $includes) puts on surfaces. Names without a folder are also tried relative
    to the tik's 'path' / own folder - conservative for the Omaha exclusion."""
    seen = set() if seen is None else seen
    p = path.lower().replace("\\", "/")
    if not p.startswith("models/") and not p.startswith("/"):
        p = "models/" + p
    p = p.lstrip("/")
    if p in seen or depth > 6:
        return set()
    seen.add(p)
    w = st.winner(p)
    if not w:
        return set()
    try:
        txt = st.read(w["rank"], w["member"]).decode("latin1", "replace")
    except Exception:
        return set()
    txt = re.sub(r"//[^\n]*", "", txt)
    out = set()
    pdir = os.path.dirname(p)
    m = re.search(r"^\s*path\s+(\S+)", txt, re.M)
    if m:
        pdir = m.group(1).strip('"').lower().replace("\\", "/").rstrip("/")
    for m in re.finditer(r"\bshader\s+\"?([^\s\"]+)", txt, re.I):
        n = m.group(1).lower()
        out.add(n)
        if "/" not in n:
            out.add(pdir + "/" + n)
    for m in re.finditer(r"\$include\s+\"?([^\s\"]+)", txt, re.I):
        out |= tik_shaders(st, m.group(1), seen, depth + 1)
    return out


# ================================================================================================= wrap metrics
def line_scores(L, axis):
    """(tex_metrics.py) coherent step across every column (axis=1) / row (axis=0) boundary incl. the WRAP, smoothed
    ALONG the boundary (sigma n/64, wrap) so per-pixel noise cancels. -> wrap, median interior, per-pixel wrap and
    median per-pixel interior."""
    if axis == 0:
        L = L.T
    H, W = L.shape
    D = np.roll(L, -1, axis=1) - L
    S = ndimage.gaussian_filter1d(D, max(1.0, H / 64.0), axis=0, mode="wrap")
    Ls = np.abs(S).mean(0)
    Lp = np.abs(D).mean(0)
    return float(Ls[W - 1]), float(np.median(Ls[:-1])), float(Lp[W - 1]), float(np.median(Lp[:-1]))


def band_metric(L):
    hp = np.abs(L - ndimage.gaussian_filter(L, 1.5, mode="wrap"))
    out = []
    for ax in (0, 1):
        p = hp.mean(axis=ax)
        p = ndimage.uniform_filter1d(p, max(3, len(p) // 128), mode="wrap")
        w = max(2, len(p) // 16)
        border = np.concatenate([p[:w], p[-w:]])
        out.append(float(border.min() / max(np.median(p), 1e-6)))
    return round(min(out), 3)


def wrap_metrics(L):
    z, pix = [], []
    for ax in (1, 0):
        w, med, wp, medp = line_scores(L, ax)
        z.append(w / max(med, 1e-3))
        pix.append(wp / max(medp, 1e-3))
    return dict(z=round(max(z), 3), pix=round(max(pix), 3), band=band_metric(L))


def cut_score(L):
    """Structure discontinuity across the wrap that a low-frequency correction cannot touch: per boundary, the local
    detail energy (|L - blur 1.5|) and mid-band structure (|blur 2 - blur 8|) in a strip either side, profiles smoothed
    along the boundary; |left - right| at the wrap vs the median interior boundary. ~1 on seamless art."""
    H, W = L.shape
    hp = np.abs(L - ndimage.gaussian_filter(L, 1.5 * W / 1024.0 + 0.5, mode="wrap"))
    mb = np.abs(ndimage.gaussian_filter(L, 2.0 * W / 1024.0 + 0.5, mode="wrap") - ndimage.gaussian_filter(L, 8.0 * W / 1024.0 + 1, mode="wrap"))
    best = 0.0
    for F in (hp, mb):
        for ax in (1, 0):
            A = F if ax == 1 else F.T
            h, w = A.shape
            s = max(2, w // 128)
            cs = np.cumsum(np.concatenate([A[:, -s:], A, A[:, :s]], 1), axis=1)
            # strip means left/right of boundary between col c and c+1 (wrap-padded)
            cols = np.arange(w)
            left = (cs[:, cols + s] - cs[:, cols]) / s
            right = (cs[:, cols + 2 * s] - cs[:, cols + s]) / s
            d = ndimage.gaussian_filter1d(left - right, max(1.0, h / 64.0), axis=0, mode="wrap")
            prof = np.abs(d).mean(0)
            best = max(best, float(prof[w - 1] / max(np.median(prof[:-1]), 1e-6)))
    return round(best, 3)


def classify(zl, zr, bl, br):
    if zr < 1.5 and zl >= 2.0:
        return "new"
    if bl < 0.75 and br >= 0.85:
        return "soft"
    if zr >= 1.5 and zl >= 2.0 and zl > 1.5 * zr and zr < 2.5:
        return "amp"
    return None


# ===================================================================================== engine height (gl2 relief)
def engine_genheight(rgb, maxsize=256):
    """R_HZM_HeightFromRGBA -> R_HZM_HalveHeight to <= r_hzmGenNormalMaxSize -> one R_HZM_BlurHeight (wrap), integer
    maths as tr_image.c:2815-2880 (live: r_hzmGenNormalMaxSize 256, r_hzmGenNormalBlur 1, autoexec.cfg:1704-1705)."""
    a = np.clip(np.round(rgb[..., :3]), 0, 255).astype(np.int64)
    h = (a[..., 0] >> 2) + (a[..., 1] >> 1) + (a[..., 2] >> 2)
    h = (h * h) // 255
    H, W = h.shape
    while max(H, W) > maxsize and H > 2 and W > 2:
        nh, nw = H >> 1, W >> 1
        h = (h[:2 * nh:2, :2 * nw:2] + h[1:2 * nh:2, :2 * nw:2] + h[:2 * nh:2, 1:2 * nw:2] + h[1:2 * nh:2, 1:2 * nw:2]) >> 2
        H, W = nh, nw
    t = (np.roll(h, 1, 1) + 2 * h + np.roll(h, -1, 1)) >> 2
    h = (np.roll(t, 1, 0) + 2 * t + np.roll(t, -1, 0)) >> 2
    return h.astype(np.float64)


# ================================================================================================= repair maths
def lanczos_matrix(n_in, n_out, a=3):
    """Periodic Lanczos-a resampling matrix (taps wrap: the texture tiles, so its resample must too - bug-1247)."""
    if n_in == n_out:
        return None
    from scipy import sparse
    scale = n_out / float(n_in)
    k = min(scale, 1.0)
    support = a / k
    rows, cols, vals = [], [], []
    for i in range(n_out):
        c = (i + 0.5) / scale - 0.5
        xs = np.arange(int(np.floor(c - support)), int(np.ceil(c + support)) + 1)
        t = (xs - c) * k
        w = np.sinc(t) * np.sinc(t / a)
        w[np.abs(t) >= a] = 0.0
        w /= w.sum()
        rows.append(np.full(len(xs), i))
        cols.append(xs % n_in)
        vals.append(w)
    return sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n_out, n_in))


def periodic_resize(img, H2, W2):
    H, W = img.shape[:2]
    My, Mx = lanczos_matrix(H, H2), lanczos_matrix(W, W2)
    chans = []
    for c in range(img.shape[2]):
        x = img[..., c]
        if My is not None:
            x = My @ x
        if Mx is not None:
            x = (Mx @ x.T).T
        chans.append(np.asarray(x))
    return np.dstack(chans)


def harmonic_correction(u, sig_frac, alpha):
    """Moisan periodic-plus-smooth: s solves the periodic Poisson problem whose sources are the wrap jumps; p = u - s
    is periodic. Here the jump profiles are LOW-PASSED along their edge first (sigma = sig_frac x edge length), so only
    the low-frequency offset is removed - no cross-fade, no mirror, interior detail untouched. alpha scales it."""
    H, W = u.shape
    jv = u[:, 0] - u[:, W - 1]
    jh = u[0, :] - u[H - 1, :]
    if sig_frac:
        jv = ndimage.gaussian_filter1d(jv, max(0.5, sig_frac * H), mode="wrap")
        jh = ndimage.gaussian_filter1d(jh, max(0.5, sig_frac * W), mode="wrap")
    v = np.zeros_like(u)
    v[0, :] -= jh
    v[H - 1, :] += jh
    v[:, 0] -= jv
    v[:, W - 1] += jv
    q, r = np.arange(W), np.arange(H)
    den = 2 * np.cos(2 * np.pi * q / W)[None, :] + 2 * np.cos(2 * np.pi * r / H)[:, None] - 4
    den[0, 0] = 1.0
    S = np.fft.fft2(v) / den
    S[0, 0] = 0.0
    return alpha * np.real(np.fft.ifft2(S))


def pot_down(n):
    p = 1
    while p * 2 <= n:
        p *= 2
    return p


# ===================================================================================================== encoding
DDSD = 0x1 | 0x2 | 0x4 | 0x1000 | 0x20000 | 0x80000      # CAPS HEIGHT WIDTH PIXELFORMAT MIPMAPCOUNT LINEARSIZE
DDSCAPS = 0x1000 | 0x8 | 0x400000                        # TEXTURE COMPLEX MIPMAP


def encode_dxt1(img):
    """float (H,W,3) 0..255, power-of-two -> DXT1 DDS bytes, float 2x2 box mips down to 1x1, one encoder."""
    H, W = img.shape[:2]
    assert H == pot_down(H) and W == pot_down(W), (H, W)
    cur = np.clip(img, 0.0, 255.0)
    levels = []
    while True:
        levels.append(TV2.bc_colour_blocks(cur, ENC_W))
        if cur.shape[0] == 1 and cur.shape[1] == 1:
            break
        cur = TV2.box_half(cur)
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<7I", hdr, 4, 124, DDSD, H, W, len(levels[0]), 0, len(levels))
    struct.pack_into("<2I", hdr, 76, 32, 0x4)             # DDS_PIXELFORMAT size, DDPF_FOURCC (no ALPHAPIXELS)
    hdr[84:88] = b"DXT1"
    struct.pack_into("<I", hdr, 108, DDSCAPS)
    return bytes(hdr) + b"".join(levels)


def check_dds_format(b):
    info = TV2.dds_parse(b)
    three = 0
    for (w, h, off, sz) in info["levels"]:
        blk = np.frombuffer(b[off:off + sz], np.uint8).reshape(-1, 8)
        c0 = blk[:, 0].astype(np.int32) | (blk[:, 1].astype(np.int32) << 8)
        c1 = blk[:, 2].astype(np.int32) | (blk[:, 3].astype(np.int32) << 8)
        ix = blk[:, 4:8].astype(np.int64).sum(1)
        three += int(((c0 < c1) | ((c0 == c1) & (ix != 0))).sum())
    ok = (info["fourcc"] == b"DXT1" and info["mips"] == TV2.full_mips(info["w"], info["h"]) and info["end"] == len(b)
          and info["levels"][-1][:2] == (1, 1) and info["w"] == pot_down(info["w"]) and info["h"] == pot_down(info["h"])
          and three == 0 and struct.unpack_from("<I", b, 80)[0] & 1 == 0)
    return ok, info, three


def chroma_shift(a, b):
    ma = a[..., :3].reshape(-1, 3).mean(0)
    mb = b[..., :3].reshape(-1, 3).mean(0)
    return float(np.abs(ma / max(ma.sum(), 1e-6) - mb / max(mb.sum(), 1e-6)).sum() * 100.0)


# ======================================================================================================= worker
_WST = {}


def _wstack(layers_json):
    key = hash(layers_json)
    if key not in _WST:
        _WST.clear()
        _WST[key] = _ZipReader(json.loads(layers_json))
    return _WST[key]


class _ZipReader:
    def __init__(self, layers):
        self.layers, self._z = layers, {}

    def read(self, rank, name):
        L = self.layers[rank]
        if L["kind"] == "dir":
            with open(name, "rb") as fh:
                return fh.read()
        if rank not in self._z:
            self._z[rank] = zipfile.ZipFile(L["path"])
        return self._z[rank].read(name)


def _dec(rd, rec, want_levels=False):
    b = rd.read(rec["rank"], rec["member"])
    if b[:4] == b"DDS " and want_levels:
        return b
    return decode_rgba(b)


def measure_job(args):
    """Scan-stage metrics for one ground image: live (player stack) and retail level 0."""
    layers_json, base, live, retail, hs, hs_retail = args
    rd = _wstack(layers_json)
    out = dict(base=base)
    try:
        a = _dec(rd, retail)
        out["retail"] = dict(shape=list(a.shape[:2]), **wrap_metrics(luma(a)))
        a = _dec(rd, live)
        L = luma(a)
        out["live"] = dict(shape=list(a.shape[:2]), **wrap_metrics(L), cut=cut_score(L),
                           alpha_lt250=round(float((a[..., 3] < 250).mean()), 5), mean_luma=round(float(L.mean()), 2))
        if hs:
            h = engine_genheight(_dec(rd, hs))
            out["relief_live"] = dict(shape=list(h.shape), **wrap_metrics(h))
        if hs_retail:
            h = engine_genheight(_dec(rd, hs_retail))
            out["relief_retail"] = dict(shape=list(h.shape), **wrap_metrics(h))
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, e)
    return out


def repair_image(src, zr, br, cls, target_hw):
    """Choose the gentlest correction that clears the wrap gates; returns (image at target size, repaired image at
    source size, stats) or (None, None, stats).

    Rung 0 is 'no correction' (a seam made only by the DDS step goes away by encoding once from the source). Otherwise,
    for each strength alpha (1.0 for new/soft; for amp - retail already draws a line there - the smallest alpha that
    brings z down to retail's own, searched upward), binary-search the LADDER for the WIDEST along-edge low-pass whose
    z clears Z_TARGET x the limit (margin for the DXT encode, which adds block-edge noise at the wrap). z falls and the
    correction grows as sigma narrows, so the widest passing rung is also the smallest correction: if it breaks the
    p99/clip gates, no narrower rung can pass - and a larger alpha cannot either."""
    H, W = src.shape[:2]
    z_src = wrap_metrics(luma(src))["z"]
    z_lim = max(Z_FLOOR, zr)
    z_tgt = Z_TARGET * z_lim
    band_lim = min(BAND_FLOOR, BAND_RETAIL * br)
    tries, memo = [], {}

    def ev(sig, al):
        key = (sig, al)
        if key in memo:
            return memo[key]
        if al == 0.0:
            corr = np.zeros_like(src[..., :3])
        else:
            corr = np.dstack([harmonic_correction(src[..., k], sig, al) for k in range(3)])
        rep = src[..., :3] - corr
        clip_any = float(((rep < -0.5) | (rep > 255.5)).mean())         # vet v_harmonic definition (reported)
        clipped = float(((rep < -CLIP_LEVELS - 0.5) | (rep > 255.5 + CLIP_LEVELS)).mean())   # the gated one
        rep = np.clip(rep, 0.0, 255.0)
        out = np.clip(periodic_resize(rep, *target_hw), 0.0, 255.0)
        wm = wrap_metrics(luma(out))
        p99 = float(np.percentile(np.abs(corr), 99)) if al else 0.0
        t = dict(sigma=round(sig, 5), alpha=round(al, 3), z=wm["z"], pix=wm["pix"], band=wm["band"], p99=round(p99, 2),
                 cmax=round(float(np.abs(corr).max()), 1), clipped=round(clipped, 6), clipped_any=round(clip_any, 6))
        t["z_ok"] = bool(t["z"] <= z_tgt)
        t["ok"] = bool(t["z_ok"] and p99 <= P99_MAX and clipped <= CLIP_MAX)       # band: gated on the encoded file
        tries.append(t)
        memo[key] = (t, out, rep)
        return memo[key]

    def done(hit):
        t, out, rep = hit
        return out, rep, dict(z_src=z_src, z_lim=z_lim, z_target=round(z_tgt, 3), band_lim=round(band_lim, 3), chosen=t,
                              tries=tries)
    hit = ev(0.0, 0.0)
    if hit[0]["ok"]:
        return done(hit)
    if cls == "amp":
        a0 = float(np.clip(1.0 - z_lim / max(z_src, 1e-6), 0.05, 1.0))
        alphas = sorted({round(a0 + (1.0 - a0) * f, 3) for f in (0.0, 0.25, 0.5, 0.75, 1.0)})
    else:
        alphas = [1.0]
    for al in alphas:
        lo, hi, best = 0, len(LADDER) - 1, None          # LADDER runs widest -> narrowest
        if not ev(LADDER[hi], al)[0]["z_ok"]:
            continue                                     # even the narrowest rung leaves the seam: try a stronger alpha
        while lo <= hi:
            mid = (lo + hi) // 2
            if ev(LADDER[mid], al)[0]["z_ok"]:
                best, hi = mid, mid - 1
            else:
                lo = mid + 1
        hit = ev(LADDER[best], al)
        if hit[0]["ok"]:
            return done(hit)
        break                                            # p99/clip only grow from here
    return None, None, dict(z_src=z_src, z_lim=z_lim, z_target=round(z_tgt, 3), band_lim=round(band_lim, 3), chosen=None,
                            tries=tries)


def apply_repair(img, sig, al):
    if al == 0.0:
        return np.clip(img[..., :3], 0.0, 255.0)
    corr = np.dstack([harmonic_correction(img[..., k], sig, al) for k in range(3)])
    return np.clip(img[..., :3] - corr, 0.0, 255.0)


def build_sibling(rd, hs, src_rec, src, ch, job):
    """The repaired gl2 height source: the diffuse's (sigma, alpha) first, then stronger rungs, until the RELIEF wrap z
    (engine_genheight of the encoded file) clears max(1.2, retail relief z), inside the same p99/clip gates and the
    brightness limit (with r_ext_compressed_textures 0 this file is also the diffuse)."""
    hs_b = rd.read(hs["rank"], hs["member"])
    same = src_rec is not None and hs["rank"] == src_rec["rank"] and hs["member"] == src_rec["member"]
    base_img = src if same else decode_rgba(hs_b)[..., :3]
    lim = max(Z_FLOOR, job.get("relief_rz") or 0.0)
    ext = os.path.splitext(hs["path"])[1]
    L0 = luma(base_img).mean()
    rungs = [(ch["sigma"], ch["alpha"])]
    if ch["alpha"] < 1.0:
        rungs.append((ch["sigma"] or LADDER[0], 1.0))
    rungs += [(sg, 1.0) for sg in LADDER if not ch["sigma"] or sg < ch["sigma"]]
    tries = []
    for sg, al in rungs:
        if al == 0.0:
            corr = np.zeros_like(base_img)
        else:
            corr = np.dstack([harmonic_correction(base_img[..., k], sg, al) for k in range(3)])
        r = base_img - corr
        clipped = float(((r < -CLIP_LEVELS - 0.5) | (r > 255.5 + CLIP_LEVELS)).mean())
        p99 = float(np.percentile(np.abs(corr), 99)) if al else 0.0
        t = dict(sigma=round(sg, 5), alpha=round(al, 3), p99=round(p99, 2), clipped=round(clipped, 6))
        if p99 > P99_MAX or clipped > CLIP_MAX:
            t["stop"] = "p99/clip"
            tries.append(t)
            break                                   # narrower rungs only grow the correction
        sib = encode_sibling(np.clip(r, 0, 255), ext, hs_b)
        sd = decode_rgba(sib)
        t["relief_z"] = wrap_metrics(engine_genheight(sd))["z"]
        t["brightness"] = round(float((luma(sd).mean() - L0) / max(L0, 1e-6)), 4)
        tries.append(t)
        if t["relief_z"] <= lim and abs(t["brightness"]) <= BRIGHT_MAX and sd.shape[:2] == base_img.shape[:2]:
            return sib, dict(limit=round(lim, 3), chosen=t, tries=tries, how="repaired source" if same else "repair of today's sibling")
    return None, dict(limit=round(lim, 3), chosen=None, tries=tries)


def encode_sibling(img, ext, like_bytes):
    """The gl2 height source, same name/extension/size as today's: JPEG q95 keeping the source's chroma sampling,
    or RLE TGA / PNG. Deterministic (libjpeg, zlib)."""
    im = Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8), "RGB")
    buf = io.BytesIO()
    if ext == ".jpg" or ext == ".jpeg":
        from PIL import JpegImagePlugin
        samp = -1
        try:
            src = Image.open(io.BytesIO(like_bytes))
            samp = JpegImagePlugin.get_sampling(src)
        except Exception:
            pass
        im.save(buf, "JPEG", quality=95, subsampling=samp if samp in (0, 1, 2) else 2, optimize=True)
    elif ext == ".tga":
        im.save(buf, "TGA", rle=True)
    else:
        im.save(buf, "PNG", optimize=False, compress_level=9)
    return buf.getvalue()


def corner_crop(a, n=224):
    """Native-resolution n x n window centred on the wrap corner of a 2x2 tiling: both wrap lines cross its middle."""
    a = np.clip(a[..., :3], 0, 255).astype(np.uint8)
    H, W = a.shape[:2]
    t = np.tile(a, (2, 2, 1))
    h = min(n, H) // 2
    w = min(n, W) // 2
    return np.ascontiguousarray(t[H - h:H + h, W - w:W + w])


def thumb(a, n=256):
    a = np.clip(a[..., :3], 0, 255).astype(np.uint8)
    H, W = a.shape[:2]
    return np.asarray(Image.fromarray(a).resize((n, max(1, round(n * H / W))), Image.BOX))


def build_job(args):
    """Build one texture: source select/verify, repair, encode, gate; the gl2 height sibling when today's is seamed.
    Returns (report, {member: bytes}, previews)."""
    layers_json, job = args
    rd = _wstack(layers_json)
    base = job["base"]
    rep = dict(base=base, cls=job["cls"], gates={}, source=None)
    try:
        live_b = rd.read(job["live"]["rank"], job["live"]["member"])
        today = decode_rgba(live_b)
        TH, TW = today.shape[:2]
        src_rec = None
        if live_b[:4] == b"DDS ":
            target = (TH, TW)
            best = None
            for s in job["sources"]:
                a = decode_rgba(rd.read(s["rank"], s["member"]))
                r = a[..., :3] if a.shape[:2] == target else periodic_resize(a[..., :3], *target)
                La, Lt = luma(r), luma(today)
                hpf = lambda L: L - ndimage.gaussian_filter(L, 2.0, mode="wrap")
                lpf = lambda L: ndimage.gaussian_filter(L, 4.0, mode="wrap")
                hpc = float(np.corrcoef(hpf(La).ravel(), hpf(Lt).ravel())[0, 1])
                lfc = float(np.corrcoef(lpf(La).ravel(), lpf(Lt).ravel())[0, 1])
                dm = np.abs(r.reshape(-1, 3).mean(0) - today[..., :3].reshape(-1, 3).mean(0))
                cand = dict(pak=s["pak"], path=s["path"], crc=s["crc"], shape=list(a.shape[:2]), hp_corr=round(hpc, 4),
                            lf_corr=round(lfc, 4), mean_d=[round(float(x), 2) for x in dm])
                rep.setdefault("source_tries", []).append(cand)
                if hpc >= SRC_HP_MIN and lfc >= SRC_LF_MIN and dm.max() <= SRC_MEAN_MAX and (best is None or hpc > best[0]["hp_corr"]):
                    best = (cand, a, s)
            if best is None:
                rep["fail"] = "no-hd-source"
                return rep, {}, None
            rep["source"], src, src_rec = best
        else:
            src, src_rec = today, job["live"]
            target = (pot_down(TH), pot_down(TW))
            rep["source"] = dict(pak=job["live"]["pak"], path=job["live"]["path"], crc=job["live"]["crc"],
                                 shape=[TH, TW], hp_corr=1.0, lf_corr=1.0, live_is_source=True)
        if (src[..., 3] < 250).mean() > 0.001 and job.get("alpha_used"):
            rep["fail"] = "alpha-used"
            return rep, {}, None
        out, src_rep, rs = repair_image(src[..., :3], job["zr"], job["br"], job["cls"], target)
        rep["repair"] = rs
        if out is None:
            rep["fail"] = "gate: no ladder step passes z/p99/clip"
            return rep, {}, (thumb(today), thumb(src))
        ch = rs["chosen"]
        dds = encode_dxt1(out)
        ok, info, three = check_dds_format(dds)
        g = rep["gates"]
        g["format"] = dict(ok=ok, detail="DXT1 %dx%d %d mips, 3-colour blocks %d, %d B" % (info["w"], info["h"], info["mips"], three, len(dds)))
        d0 = TV2.dds_decode_level(dds, info, 0).astype(np.float64)
        ref = today[..., :3] if today.shape[:2] == target else np.clip(periodic_resize(today[..., :3], *target), 0, 255)
        wm = wrap_metrics(luma(d0))
        z_lim, band_lim = rs["z_lim"], rs["band_lim"]
        g["z"] = dict(ok=wm["z"] <= z_lim, value=wm["z"], limit=round(z_lim, 3), today=job["zl"], retail=job["zr"])
        g["p99"] = dict(ok=ch["p99"] <= P99_MAX, value=ch["p99"], limit=P99_MAX)
        g["clipped"] = dict(ok=ch["clipped"] <= CLIP_MAX, value=ch["clipped"], limit=CLIP_MAX,
                            definition="share of channel values clamped by more than %d levels" % CLIP_LEVELS,
                            any_clamp=ch.get("clipped_any"))
        g["band"] = dict(ok=wm["band"] >= band_lim, value=wm["band"], limit=band_lim, retail=job["br"], today=job["bl"])
        lo, lr = luma(d0).mean(), luma(ref).mean()
        g["brightness"] = dict(ok=abs(lo - lr) / max(lr, 1e-6) <= BRIGHT_MAX, value=round(float((lo - lr) / max(lr, 1e-6)), 4),
                               limit=BRIGHT_MAX)
        cs = chroma_shift(d0, ref)
        g["chroma"] = dict(ok=cs <= CHROMA_MAX, value=round(cs, 3), limit=CHROMA_MAX)
        # per-mip z vs the same level of the float box chain before encoding: the encode must not add a seam (at 32 px and
        # below every wrap is also a DXT block edge on smooth art, so a fixed limit would measure the block grid)
        mz, iz, cur = [], [], np.clip(out, 0.0, 255.0)
        for k in range(1, info["mips"]):
            cur = TV2.box_half(cur)
            w, h = info["levels"][k][:2]
            if min(w, h) < MIP_MIN:
                break
            mz.append(wrap_metrics(luma(TV2.dds_decode_level(dds, info, k).astype(np.float64)))["z"])
            iz.append(wrap_metrics(luma(cur))["z"])
        g["mip_z"] = dict(ok=all(z <= max(z_lim, i) + MIP_SLACK for z, i in zip(mz, iz)), value=mz, ideal=iz,
                          limit="max(%.3f, ideal) + %.1f" % (z_lim, MIP_SLACK))
        dark_o, dark_r = float((luma(d0) < 16).mean()), float((luma(ref) < 16).mean())
        g["sanity"] = dict(ok=bool(np.isfinite(d0).all() and lo > 0.9 * lr and dark_o <= dark_r + 0.02 and d0.std() > 0.5 * ref.std()),
                           detail="mean luma %.1f (today %.1f), luma<16 %.2f%% (today %.2f%%), std %.1f (today %.1f)" % (
                               lo, lr, 100 * dark_o, 100 * dark_r, d0.std(), ref.std()))
        hp = lambda A: float(np.std(A - ndimage.gaussian_filter(A, 1.5, mode="wrap")))
        rep["detail_ratio"] = round(hp(luma(d0)) / max(hp(luma(ref)), 1e-6), 3)
        rep["pix"] = dict(today=job["pix"], out=wm["pix"])
        rep["cut"] = dict(today=job["cut"], out=cut_score(luma(d0)))
        members = {base + ".dds": dds}
        # --- gl2 height sibling (R_HZM_GenerateNormalMapFromSource decodes the first png/tga/jpg sibling)
        hs = job.get("hs")
        rep["relief"] = dict(today=job.get("relief_z"), retail=job.get("relief_rz"), sibling=None)
        if hs and job.get("need_sibling"):
            sib, sinfo = build_sibling(rd, hs, src_rec, src[..., :3], ch, job)
            rep["relief"]["sibling_ladder"] = sinfo
            if sib is not None:
                members[hs["path"]] = sib
                rep["relief"]["sibling"] = dict(path=hs["path"], today_pak=hs["pak"], bytes=len(sib), **sinfo["chosen"])
                g["relief_z"] = dict(ok=True, value=sinfo["chosen"]["relief_z"], limit=sinfo["limit"], today=job.get("relief_z"))
            else:
                rep["relief"]["kept"] = "no sibling rung passes relief z + p99/clip/brightness: today's relief seam stays"
        rep["ok"] = all(v["ok"] for v in g.values())
        if not rep["ok"]:
            rep["fail"] = "gate: " + ",".join(k for k, v in g.items() if not v["ok"])
        rep["members"] = {k: dict(sha256=sha(v), bytes=len(v)) for k, v in members.items()}
        return rep, members, (thumb(ref), thumb(d0))
    except Exception as e:
        import traceback
        rep["fail"] = "error %s: %s" % (type(e).__name__, e)
        rep["trace"] = traceback.format_exc()[-1500:]
        return rep, {}, None


# ================================================================================================ cathedarchlrg
def build_cathedarchlrg(st, table):
    """bug-2954: retail-derived opaque DXT1 (the conctrmdrk recipe of gen_terrain_pak_v2.build_conc, own encoder)."""
    rep = {}
    assert CATH not in table, "cathedarchlrg gained a shader definition - re-check the opaque premise"
    rec = st.resolve(CATH, ".tga", retail_only=True, compressed=False)
    assert rec and rec["retail"] and rec["path"].endswith(".tga"), rec
    raw = st.read(rec["rank"], rec["member"])
    a = decode_rgba(raw)
    rgb = a[..., :3].astype(np.uint8)
    h, w = rgb.shape[:2]
    S, P = 4, 8
    pad = np.pad(rgb, ((0, 0), (P, P), (0, 0)), mode="wrap")        # S: arches repeat side by side (st crosses 1.0)
    pad = np.pad(pad, ((P, P), (0, 0), (0, 0)), mode="edge")        # T: no top<->bottom bleed
    up = Image.fromarray(pad, "RGB").resize((pad.shape[1] * S, pad.shape[0] * S), Image.LANCZOS)
    up = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=3))        # bug-1129 recipe
    out = np.asarray(up)[P * S:P * S + h * S, P * S:P * S + w * S].astype(np.float64)
    lo, hi = rgb.reshape(-1, 3).min(0), rgb.reshape(-1, 3).max(0)
    out = np.clip(out, lo, hi)                                      # bug-1247: clamp to the source range
    H2, W2 = pot_down(out.shape[0]), pot_down(out.shape[1])
    if (H2, W2) != out.shape[:2]:
        out = np.asarray(Image.fromarray(out.astype(np.uint8)).resize((W2, H2), Image.LANCZOS)).astype(np.float64)
    dds = encode_dxt1(out)
    ok, info, three = check_dds_format(dds)
    d0 = TV2.dds_decode_level(dds, info, 0).astype(np.float64)
    rm, nm = a[..., :3].reshape(-1, 3).mean(0), d0[..., :3].reshape(-1, 3).mean(0)
    Lr, Ln = luma(a), luma(d0)
    rep["retail"] = dict(pak=rec["pak"], member=rec["member"], crc=rec["crc"], sha256=sha(raw), shape=[h, w],
                         alpha_zero_pct=round(100 * float((a[..., 3] == 0).mean()), 1))
    rep["gates"] = dict(
        format=dict(ok=ok, detail="DXT1 %dx%d %d mips, 3-colour blocks %d" % (info["w"], info["h"], info["mips"], three)),
        mean_rgb=dict(ok=bool(np.all(np.abs(nm - rm) <= 6.0)), retail=[round(x, 1) for x in rm], out=[round(x, 1) for x in nm]),
        not_black=dict(ok=bool(Ln.mean() > 0.9 * Lr.mean() and (Ln < 16).mean() <= (Lr < 16).mean() + 0.05),
                       detail="luma %.1f (retail %.1f), luma<16 %.1f%% (retail %.1f%%)" % (Ln.mean(), Lr.mean(), 100 * (Ln < 16).mean(),
                                                                                         100 * (Lr < 16).mean())),
        opaque=dict(ok=bool(all((TV2.dds_decode_level(dds, info, k)[..., 3] == 255).all() for k in range(info["mips"])))))
    rep["ok"] = all(v["ok"] for v in rep["gates"].values())
    rep["dds_sha256"], rep["bytes"] = sha(dds), len(dds)
    return rep, dds, (rgb, d0.astype(np.uint8))


# ===================================================================================================== pak I/O
def write_pak(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(members):
            zi = zipfile.ZipInfo(name, date_time=FIXED_TS)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = NEW_ATTR
            zi.create_system = 0
            z.writestr(zi, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return buf.getvalue()


# ===================================================================================================== sheets
def _font(sz):
    try:
        return ImageFont.load_default(size=sz)
    except Exception:
        return ImageFont.load_default()


def tile3(a, px):
    """3x3 tiling of a (H,W,3) uint8, scaled so one tile is px wide (BOX)."""
    t = np.tile(a, (3, 3, 1))
    H, W = a.shape[:2]
    return Image.fromarray(t).resize((3 * px, max(1, round(3 * px * H / W))), Image.BOX)


def sheet_pair(path, title, rows, px=300, crops=None):
    """rows: [(label, before uint8, after uint8, note)] -> PNG with BEFORE | AFTER 3x3 tilings per row; with crops
    ([(before, after)] per row) also the native-resolution wrap corner, before above after, at 2x."""
    f, fb = _font(14), _font(16)
    tw = 3 * px
    cw = 0
    if crops:
        cw = max(2 * c[0].shape[1] for c in crops) + 20
    rh = [max(tile3(b, px).height, (4 * crops[i][0].shape[0] + 30) if crops else 0) for i, (_, b, _, _) in enumerate(rows)]
    Hs = 34 + sum(h + 44 for h in rh)
    sheet = Image.new("RGB", (2 * tw + 30 + cw, Hs), (22, 22, 26))
    dr = ImageDraw.Draw(sheet)
    dr.text((10, 8), title, fill=(240, 240, 240), font=fb)
    y = 34
    for i, ((lab, b, a, note), h) in enumerate(zip(rows, rh)):
        dr.text((10, y), lab, fill=(235, 220, 150), font=f)
        dr.text((10, y + 18), note, fill=(190, 190, 190), font=f)
        sheet.paste(tile3(b, px), (10, y + 40))
        sheet.paste(tile3(a, px), (20 + tw, y + 40))
        if crops:
            cb, ca = crops[i]
            x0 = 30 + 2 * tw
            up = lambda c: Image.fromarray(c).resize((2 * c.shape[1], 2 * c.shape[0]), Image.NEAREST)
            dr.text((x0, y + 24), "wrap corner, native res x2: today / tilefix", fill=(190, 190, 190), font=f)
            sheet.paste(up(cb), (x0, y + 40))
            sheet.paste(up(ca), (x0, y + 40 + 2 * cb.shape[0] + 10))
        y += h + 44
    sheet.save(path, optimize=True)


# textures the user is asked to judge first (shown when included), then the largest by ground area fill the sheets
SHOWCASE = ("textures/algiers/grndset_1", "textures/central_europe_winter/forstsnow_rough256",
            "textures/general_structure/bunker_roof_int", "textures/misc_outside/bocagegrass_1uf")


def write_sheets(out, report, pv, log):
    """User contact sheets (few, representative) + one index image + one 3x3 image per content-cut texture; and the
    review sheets used to find content cuts (every included texture, worst cut score first)."""
    sd = os.path.join(out, "sheets")
    rd = os.path.join(out, "review")
    for d in (sd, rd):
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            if f.endswith(".png"):
                os.remove(os.path.join(d, f))
    inc = {r["base"]: r for r in report["included"]}

    def pair(b):
        k = b.replace("/", "~")
        return pv[k + "__0"], pv[k + "__1"]

    def note(r):
        c = r["repair"]["chosen"]
        g = r["gates"]
        return ("%s | wrap z %.2f -> %.2f (retail %.2f) | correction p99 %.1f | brightness %+.2f%% chroma %.2f | maps %s" % (
            r["cls"], g["z"]["today"], g["z"]["value"], g["z"]["retail"], c["p99"], 100 * g["brightness"]["value"],
            g["chroma"]["value"], ", ".join(report["maps_of"].get(r["base"], [])[:6])))
    order = [b for b in SHOWCASE if b in inc]
    by_area = sorted(inc, key=lambda b: -report["area_of"].get(b, 0))
    for cls in ("new", "amp", "soft"):
        for b in by_area:
            if inc[b]["cls"] == cls and b not in order and sum(1 for x in order if inc[x]["cls"] == cls) < (4 if cls == "new" else 2):
                order.append(b)
    sheets = [order[i:i + 3] for i in range(0, len(order), 3)][:4]
    # newly admitted (vs --baseline): the worst correction first, so the relaxed gates are judged at their edge
    na = sorted(report.get("newly_admitted", []), key=lambda r: -r["p99"])
    na = [r["base"] for r in na if r["base"] in inc]
    rel = [b for b in na if not next(x for x in report["newly_admitted"] if x["base"] == b)["why"].startswith("MP")][:3]
    mpo = [b for b in na if b not in rel and next(x for x in report["newly_admitted"] if x["base"] == b)["why"].startswith("MP")]
    mpo = sorted(mpo, key=lambda b: -report["area_of"].get(b, 0))[:3]
    for tag, grp in (("relaxed_gates", rel), ("mp_only", mpo)):
        if grp:
            rows = [(b[9:], pair(b)[0], pair(b)[1], note(inc[b])) for b in grp]
            cr = [(pv[b.replace("/", "~") + "__2"], pv[b.replace("/", "~") + "__3"]) for b in grp]
            sheet_pair(os.path.join(sd, "tilefix_new_%s.png" % tag), "NEWLY ADMITTED (%s)  LEFT: today   MIDDLE: tilefix"
                       "   RIGHT: wrap corner at native resolution" % tag.replace("_", " "), rows, px=200, crops=cr)
    for n, grp in enumerate(sheets, 1):
        rows = [(b[9:], pair(b)[0], pair(b)[1], note(inc[b])) for b in grp]
        cr = [(pv[b.replace("/", "~") + "__2"], pv[b.replace("/", "~") + "__3"]) for b in grp] \
            if all(b.replace("/", "~") + "__2" in pv for b in grp) else None
        sheet_pair(os.path.join(sd, "tilefix_%d.png" % n), "LEFT: today (3x3 tiling, the wrap lines are at 1/3 and 2/3)"
                   "   MIDDLE: tilefix pak   RIGHT: the wrap corner at native resolution", rows, px=200, crops=cr)
    # cathedarchlrg: retail | today | new
    tiles = [("RETAIL TGA RGB (panes under alpha 0)", pv.get("cath_before")), ("TODAY: hdmem DDS", pv.get("cath_today")),
             ("tilefix: retail-derived DXT1", pv.get("cath_after"))]
    tiles = [(l, a) for l, a in tiles if a is not None]
    H = 520
    ims = [(l, Image.fromarray(np.ascontiguousarray(a[..., :3])).resize((max(1, round(H * a.shape[1] / a.shape[0])), H),
                                                                          Image.LANCZOS)) for l, a in tiles]
    W = sum(i.width for _, i in ims) + 20 * (len(ims) + 1)
    sh = Image.new("RGB", (W, H + 60), (22, 22, 26))
    dr = ImageDraw.Draw(sh)
    dr.text((10, 6), "cathedarchlrg (bug-2954) - m4l1, mohdm2, mohdm4, obj_team4, siegecastle", fill=(240, 240, 240), font=_font(16))
    x = 20
    for l, i in ims:
        dr.text((x, 30), l, fill=(235, 220, 150), font=_font(13))
        sh.paste(i, (x, 50))
        x += i.width + 20
    sh.save(os.path.join(sd, "cathedarchlrg_before_after.png"), optimize=True)
    # index: every included texture, 3x3 AFTER thumbnail
    names = sorted(inc)
    cols, px = 16, 40
    cw, chh = 3 * px + 8, 3 * px + 22
    rows_n = (len(names) + cols - 1) // cols
    idx = Image.new("RGB", (cols * cw + 8, rows_n * chh + 40), (22, 22, 26))
    dr = ImageDraw.Draw(idx)
    dr.text((8, 8), "tilefix index: %d textures (3x3 tiling each, after repair) + cathedarchlrg" % len(names),
            fill=(240, 240, 240), font=_font(16))
    f9 = _font(9)
    for i, b in enumerate(names):
        x, y = 8 + (i % cols) * cw, 34 + (i // cols) * chh
        im = tile3(pair(b)[1], px)
        im.thumbnail((3 * px, 3 * px), Image.BOX)             # non-square textures fit the cell
        idx.paste(im, (x, y))
        dr.text((x, y + 3 * px + 2), b.split("/")[-1][:22], fill=(200, 200, 200), font=f9)
    idx.save(os.path.join(sd, "tilefix_index.png"), optimize=True)
    # content cut: one 3x3 image each (today | wrap-corrected, to show the correction cannot hide it)
    for e in report["excluded"].get("content-cut", []):
        k = "cc_" + e["base"].replace("/", "~")
        if k + "__0" in pv:
            cr = [(pv[k + "__2"], pv[k + "__3"])] if k + "__2" in pv else None
            sheet_pair(os.path.join(sd, "contentcut_%s.png" % e["base"].split("/")[-1]),
                       "CONTENT CUT - not shipped: %s  (%s)" % (e["base"][9:], e.get("note", "")),
                       [("3x3: left today, middle with the wrap correction - the cut stays", pv[k + "__0"], pv[k + "__1"],
                         "maps: " + ", ".join(report["maps_of"].get(e["base"], [])[:8]))], px=200, crops=cr)
    # review sheets (internal): every included texture, highest cut score first
    rv = sorted(inc, key=lambda b: -inc[b]["cut"]["out"])
    per, px = 12, 110
    for n in range(0, len(rv), per):
        grp = rv[n:n + per]
        sh = Image.new("RGB", (4 * (3 * px + 12) + 12, 3 * (3 * px + 30) + 12), (22, 22, 26))
        dr = ImageDraw.Draw(sh)
        for i, b in enumerate(grp):
            x, y = 12 + (i % 4) * (3 * px + 12), 12 + (i // 4) * (3 * px + 30)
            sh.paste(tile3(pair(b)[1], px), (x, y + 16))
            dr.text((x, y), "%s  cut %.1f  %s" % (b.split("/")[-1][:30], inc[b]["cut"]["out"], inc[b]["cls"]),
                    fill=(235, 220, 150), font=_font(11))
        sh.save(os.path.join(rd, "review_%02d.png" % (n // per + 1)))
    log("sheets: %d user sheets + index + cathedarchlrg + %d content-cut images -> %s; %d review sheets -> %s" % (
        len(sheets), len(report["excluded"].get("content-cut", [])), sd, (len(rv) + per - 1) // per, rd))


# ======================================================================================================== main
def scan(st, args, log):
    table = load_shaders(st)
    refs = image_refs(table)
    log("shaders: %d defined" % len(table))
    # --- census over every map the stack loads
    maps = sorted(p for p in st.members if p.startswith("maps/") and p.endswith(".bsp"))
    cache_p = os.path.join(args.cache, "census.json")
    cache = json.load(open(cache_p)) if os.path.isfile(cache_p) else {}
    census = {}
    for p in maps:
        w = st.winner(p)
        key = "v%d|%s|%s|%s|%s" % (CENSUS_VERSION, w["pak"], w["member"], w["crc"], w["size"])
        if cache.get(p, {}).get("key") == key:
            census[p] = cache[p]
            continue
        try:
            census[p] = dict(key=key, pak=w["pak"], **parse_bsp(st.read(w["rank"], w["member"])))
        except Exception as e:
            census[p] = dict(key=key, pak=w["pak"], error=str(e))
    os.makedirs(os.path.dirname(cache_p), exist_ok=True)
    with open(cache_p, "w") as fh:
        json.dump(census, fh)
    log("maps: %d BSPs (%d unreadable)" % (len(census), sum(1 for c in census.values() if "error" in c)))

    def mapname(p):
        return p[5:-4]

    def is_mp(mn):
        return mn.split("/")[0] in ("dm", "obj", "lib")

    def is_omaha(mn):
        b = mn.split("/")[-1]
        b = b[:-4] if b.endswith("_sml") else b
        return (b in OMAHA_MAPS and "/" not in mn) or mn in OMAHA_MP

    # --- every image an Omaha map draws (shader lump incl. unused sides, static + entity models via their tiks)
    omaha_imgs, omaha_maps = set(), []
    for p, c in census.items():
        mn = mapname(p)
        if "error" in c or not is_omaha(mn):
            continue
        omaha_maps.append(dict(map=mn, pak=c["pak"], message=c["message"], shaders=len(c["shaders"]), models=len(c["models"])))
        for s in c["shaders"]:
            omaha_imgs |= shader_image_bases(s, table)
        for m in c["models"]:
            if m.endswith(".tik"):
                for s in tik_shaders(st, m):
                    omaha_imgs |= shader_image_bases(s, table)
    for om in list(OMAHA_MAPS) + list(OMAHA_MP):
        assert any(o["map"] == om for o in omaha_maps), "Omaha map not found in the stack: " + om
    log("omaha: %d maps, %d images drawn there" % (len(omaha_maps), len(omaha_imgs)))

    # --- ground images
    ground = {}
    for p, c in census.items():
        if "error" in c or p.endswith("_sml.bsp"):
            continue
        mn = mapname(p)
        for sid in set(c["ground"]) | set(c["terrain"]):
            sn = c["shaders"][int(sid)]
            base, ext, alpha, clamp = diffuse_of(sn, table)
            if not base:
                continue
            g = ground.setdefault(base, dict(ext=ext, shaders=set(), maps={}, area=0.0, patches=0, alpha=False, clamp_only=True))
            g["shaders"].add(sn)
            a = c["ground"].get(sid, 0) + 512 * 512 * c["terrain"].get(sid, 0)
            g["area"] += a
            g["patches"] += c["terrain"].get(sid, 0)
            m = g["maps"].setdefault(mn, [0, 0])
            m[0] += a
            m[1] += c["terrain"].get(sid, 0)
            g["alpha"] |= alpha
            g["clamp_only"] &= clamp
    # where is the wrap line actually drawn? every surface of every shader whose diffuse is the image (walls too);
    # LOD terrain always tiles (neighbouring patches continue the texture)
    for p, c in census.items():
        if "error" in c or p.endswith("_sml.bsp"):
            continue
        for sid in set(c["drawn"]) | set(c["terrain"]):
            base = diffuse_of(c["shaders"][int(sid)], table)[0]
            if base in ground:
                g = ground[base]
                t = 512 * 512 * c["terrain"].get(sid, 0)
                g["drawn"] = g.get("drawn", 0) + c["drawn"].get(sid, 0) + t
                g["wrapped"] = g.get("wrapped", 0) + c["wrapped"].get(sid, 0) + t
    tot = sum(g["area"] for g in ground.values())
    log("ground images: %d" % len(ground))

    # --- protected names
    prot = {}
    tf_key = TV2.fs_key(PAK_NAME)
    for rank, L in enumerate(st.layers):
        if L["kind"] != "pak":
            continue
        nm = L["name"].lower()
        above = L["game"] == "maintt" and TV2.fs_key(nm) > tf_key
        if above or nm in PROTECTED_BELOW:
            prot[nm] = set()
    for path, cands in st.members.items():
        for rank, n, crc, sz in cands:
            nm = st.layers[rank]["name"].lower()
            if nm in prot:
                prot[nm].add(strip_ext(path))

    # --- measure
    jobs = []
    rows = {}
    layers_json = json.dumps(st.layers)
    for base, g in sorted(ground.items()):
        r = dict(base=base, ext=g["ext"], area_pct=round(100 * g["area"] / tot, 4), patches=g["patches"],
                 maps=sorted(g["maps"]), alpha_shader=g["alpha"], clamp_only=g["clamp_only"],
                 wrap_frac=round(g.get("wrapped", 0) / max(g.get("drawn", 0), 1), 4), wrapped_area=g.get("wrapped", 0))
        rows[base] = r
        if NONART.search(base):
            r["skip"] = "non-art"
            continue
        live = st.resolve(base, g["ext"])
        retail = st.resolve(base, g["ext"], retail_only=True, compressed=False)
        r["live"] = live and dict(pak=live["pak"], path=live["path"], crc=live["crc"])
        r["retail"] = retail and dict(pak=retail["pak"], path=retail["path"])
        if not live or not retail:
            r["skip"] = "no live" if not live else "no retail reference"
            continue
        if live["path"].endswith(".dds"):
            hs = st.height_source(base)
        else:
            hs = live
        hs_retail = None
        for e in (".png", ".tga", ".jpg", ".jpeg"):
            hs_retail = st.winner(base + e, retail_only=True)
            if hs_retail:
                break
        r["height_source"] = hs and dict(pak=hs["pak"], path=hs["path"])
        jobs.append((layers_json, base, live, retail, hs, hs_retail))
    mcache_p = os.path.join(args.cache, "metrics.json")
    mcache = json.load(open(mcache_p)) if os.path.isfile(mcache_p) else {}
    todo, res = [], {}
    for j in jobs:
        key = "|".join(str(x and (x["pak"], x["member"], x["crc"])) for x in j[2:])
        if mcache.get(j[1], {}).get("key") == key:
            res[j[1]] = mcache[j[1]]
        else:
            todo.append((j, key))
    log("measuring %d images (%d cached)" % (len(todo), len(jobs) - len(todo)))
    if todo:
        with ProcessPoolExecutor(args.jobs) as ex:
            for (j, key), m in zip(todo, ex.map(measure_job, [t[0] for t in todo], chunksize=2)):
                m["key"] = key
                res[j[1]] = m
    with open(mcache_p, "w") as fh:
        json.dump(res, fh)

    # --- classify + exclude
    scope = dict(candidates=[], excluded={}, counts={})

    def excl(reason, base, **kw):
        scope["excluded"].setdefault(reason, []).append(dict(base=base, **kw))

    for base, r in sorted(rows.items()):
        if "skip" in r:
            continue
        m = res.get(base, {})
        if "error" in m or "live" not in m or "retail" not in m:
            excl("unreadable", base, err=m.get("error"))
            continue
        lv, rt = m["live"], m["retail"]
        cls = classify(lv["z"], rt["z"], lv["band"], rt["band"])
        r.update(zl=lv["z"], zr=rt["z"], bl=lv["band"], br=rt["band"], pix=lv["pix"], cut=lv["cut"], cls=cls,
                 alpha_lt250=lv["alpha_lt250"], relief_z=(m.get("relief_live") or {}).get("z"),
                 relief_rz=(m.get("relief_retail") or {}).get("z"))
        if not cls:
            continue
        info = dict(cls=cls, zl=lv["z"], zr=rt["z"], maps=r["maps"][:12], area_pct=r["area_pct"], patches=r["patches"],
                    live=r["live"]["pak"])
        om_maps = [mm for mm in r["maps"] if is_omaha(mm)]
        if om_maps or base in omaha_imgs:
            excl("omaha-by-map", base, omaha_maps=om_maps or ["(model/shader on an Omaha map)"], **info)
            continue
        if OMAHA_TOK.search(base):
            excl("omaha-named", base, **info)
            continue
        owner = [p for p, ns in prot.items() if base in ns]
        if owner:
            excl("shadowfix-owned" if SHADOWFIX in owner else "protected-pak", base, owner=owner, **info)
            continue
        if r["alpha_shader"] and lv["alpha_lt250"] > 0.001:
            excl("alpha-used", base, **info)
            continue
        if r["clamp_only"]:
            excl("clamp-only", base, **info)
            continue
        if args.sp_only and not any(not is_mp(mm) for mm in r["maps"]):
            excl("mp-only", base, **info)
            continue
        if r["patches"] == 0 and r["wrap_frac"] < TILE_MIN:
            excl("never-tiles", base, wrap_frac=r["wrap_frac"], **info)
            continue
        if base in CONTENT_CUT:
            excl("content-cut", base, note=CONTENT_CUT[base], cut=lv["cut"], **info)
            continue
        scope["candidates"].append(dict(r))
    scope["counts"] = dict(ground_images=len(rows), measured=len(res),
                           classified={c: sum(1 for r in rows.values() if r.get("cls") == c) for c in ("new", "amp", "soft")},
                           candidates=len(scope["candidates"]),
                           excluded={k: len(v) for k, v in scope["excluded"].items()})
    scope["omaha_maps"] = omaha_maps
    scope["omaha_image_count"] = len(omaha_imgs)
    scope["protected_paks"] = {p: len(ns) for p, ns in prot.items()}
    scope["player_stack_skipped"] = sorted(args.skip)
    scope["rows"] = rows
    return scope, table, refs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--gog", default=GOG)
    ap.add_argument("--home", default=LIVE_HOME)
    ap.add_argument("--stage", default="all", choices=("scan", "build", "all", "sheets"))
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--no-sheets", action="store_true")
    ap.add_argument("--cache", default="", help="census/metrics cache dir (default <out>/cache); inputs are keyed by CRC")
    ap.add_argument("--include-mp", action="store_true",
                    help="(default since the user approved it 2026-09-26; kept so old command lines still work)")
    ap.add_argument("--sp-only", action="store_true",
                    help="leave out textures drawn ONLY on MP maps (dm/ obj/ lib/) - the v1 scope")
    ap.add_argument("--manifest", default=MANIFEST, help="release manifest that defines the player stack")
    ap.add_argument("--baseline", default="", help="an earlier tilefix_report.json: list what this build adds/drops")
    args = ap.parse_args()
    args.out = os.path.abspath(args.out)
    args.cache = os.path.abspath(args.cache or os.path.join(args.out, "cache"))
    os.makedirs(args.cache, exist_ok=True)
    for forbidden in (os.path.join(REPO, "hzm-mohaa-coop-mod"), args.gog, LIVE_BASE, APPDATA_HOME):
        if forbidden:
            fa = os.path.normcase(os.path.abspath(forbidden))
            assert not os.path.normcase(args.out).startswith(fa), "refusing to write into " + forbidden
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    def log(s):
        print("[%6.1fs] %s" % (time.time() - t0, s), flush=True)

    if args.stage == "sheets":
        with open(os.path.join(args.out, "tilefix_report.json"), encoding="utf-8") as fh:
            write_sheets(args.out, json.load(fh), dict(np.load(os.path.join(args.out, "previews.npz"))), log)
        return
    layers = stack_layers(args.gog, args.home)
    args.skip = player_stack_skips(layers, args.manifest, log)
    st = Stack(layers, skip_paks=args.skip)
    log("stack: %d layers, %d indexed paths" % (len(layers), len(st.members)))
    scope, table, refs = scan(st, args, log)
    with open(os.path.join(args.out, "tilefix_scope.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({k: v for k, v in scope.items()}, fh, indent=1, default=_jdefault)
    log("scope: %s" % json.dumps(scope["counts"]))
    if args.stage == "scan":
        return
    build(st, scope, table, refs, args, log)


def player_stack_skips(layers, manifest, log):
    """Installed paks that are NOT the player stack: every non-retail pak absent from the release manifest (dev-only
    paks such as seamfix/groundfix (D1) or y_hzm_maptour), except STAGED_NEWER - plus THIS pak, which must never be
    read as its own input (once deployed it would be the live winner of every texture it repairs)."""
    with open(manifest, encoding="utf-8-sig") as fh:
        m = json.load(fh)
    listed = {os.path.basename(f["path"]).lower() for f in m["files"] if f["path"].lower().endswith(".pk3")}
    skip = {PAK_NAME} | DEV_ONLY
    for L in layers:
        nm = L["name"].lower()
        if L["kind"] == "pak" and not L["retail"] and nm not in listed and nm not in STAGED_NEWER:
            skip.add(nm)
    log("player stack = retail + manifest %s (%d paks); skipped as not shipped: %s" % (
        m.get("version"), len(listed), ", ".join(sorted(skip & {L["name"].lower() for L in layers})) or "-"))
    return skip


def gate_whatif(fails):
    """How many gate failures a relaxed limit would admit (ladder data only; the encoded-file gates would still apply).
    For the user's decision - nothing here changes what ships."""
    out = {}
    lad = [e for e in fails if e.get("repair") and e["repair"].get("chosen") is None]
    for p99m in (12, 16, 24):
        n = 0
        for e in lad:
            if any(t["z"] <= e["repair"]["z_lim"] * Z_TARGET and t["p99"] <= p99m and t.get("clipped", 1) <= CLIP_MAX
                   for t in e["repair"]["tries"]):
                n += 1
        out["p99<=%d, clip(>%d levels)<=0.05%%" % (p99m, CLIP_LEVELS)] = n
    out["ladder failures"] = len(lad)
    band_only = [e["base"] for e in fails if e.get("gates") and set(e["gates"]) == {"band"}]
    out["encoded-gate failures on band ONLY (band inherited from the HD art, the repair does not change it)"] = len(band_only)
    out["band_only"] = band_only
    return out


def _src_list(st, base):
    """Every non-retail, non-DDS copy of the image (the art a DXT pack can have been encoded from), best first."""
    out = []
    for e in (".jpg", ".tga", ".png", ".jpeg"):
        for rank, n, crc, sz in st.members.get(base + e, []):
            if not st.layers[rank]["retail"]:
                out.append(st.rec(base + e, rank, n, crc, sz))
    return sorted(out, key=lambda s: -s["rank"])


def build(st, scope, table, refs, args, log):
    GATES = []

    def gate(name, ok, detail=""):
        GATES.append(dict(gate=name, ok=bool(ok), detail=detail))
        print("  [%s] %s  %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
        return ok

    layers_json = json.dumps(st.layers)
    only = {("textures/" + o if not o.startswith("textures/") else o).lower() for o in args.only.split(",") if o}
    jobs = []
    for r in scope["candidates"]:
        base = r["base"]
        if only and base not in only:
            continue
        live = st.resolve(base, r["ext"])
        hs = st.height_source(base)
        # the vet's seam rule (classify) applied to the gl2 relief: a height sibling only where the relief itself
        # carries a new/amplified wrap seam
        rz, rrz = r.get("relief_z"), r.get("relief_rz") or 0.0
        need = bool(rz is not None and rz >= 2.0 and (rrz < 1.5 or rz > 1.5 * rrz))
        job = dict(base=base, cls=r["cls"], zl=r["zl"], zr=r["zr"], bl=r["bl"], br=r["br"], pix=r["pix"], cut=r["cut"],
                   live=live, sources=_src_list(st, base) if live["path"].endswith(".dds") else [],
                   alpha_used=r["alpha_shader"], hs=hs, need_sibling=need, relief_z=r.get("relief_z"),
                   relief_rz=r.get("relief_rz"))
        if not live["path"].endswith(".dds"):
            # the RGBA8 path generated today's relief from the diffuse itself; once a .dds exists the DDS path reads the
            # first png/tga/jpg sibling instead - only safe to repair in place when that sibling IS the live file
            job["need_sibling"] = need and hs and hs["path"] == live["path"]
            job["nondds_note"] = "live %s, height source after %s" % (live["path"], hs and hs["path"])
        jobs.append(job)
    log("build: %d jobs, %d with a height sibling" % (len(jobs), sum(1 for j in jobs if j["need_sibling"])))
    # build cache: a job's result is a pure function of its inputs (member CRCs in the job) and of this code
    import pickle
    code = ("BUILD_VERSION %d|" % BUILD_VERSION).encode() + open(os.path.abspath(TV2.__file__), "rb").read()
    bdir = os.path.join(args.cache, "build")
    os.makedirs(bdir, exist_ok=True)
    keys = [sha(code + json.dumps(j, sort_keys=True, default=_jdefault).encode())[:32] for j in jobs]
    done = {}
    for k in keys:
        f = os.path.join(bdir, k + ".pkl")
        if os.path.isfile(f):
            with open(f, "rb") as fh:
                done[k] = pickle.load(fh)
    todo = [(k, j) for k, j in zip(keys, jobs) if k not in done]
    log("  %d cached, %d to build" % (len(jobs) - len(todo), len(todo)))
    with ProcessPoolExecutor(args.jobs) as ex:
        for (k, j), res in zip(todo, ex.map(build_job, [(layers_json, j) for _, j in todo], chunksize=1)):
            done[k] = res
            with open(os.path.join(bdir, k + ".pkl"), "wb") as fh:
                pickle.dump(res, fh)
    results, members, previews = [], {}, {}
    if True:
        for i, (rep, mem, prev) in enumerate(done[k] for k in keys):
            results.append(rep)
            if rep.get("ok"):
                members.update(mem)
            if prev is not None:
                previews[rep["base"]] = prev
            if i % 25 == 0 or len(jobs) <= 30:
                log("  %d/%d %s %s" % (i + 1, len(jobs), rep["base"], "ok" if rep.get("ok") else rep.get("fail")))
    ok = [r for r in results if r.get("ok")]
    bad = [r for r in results if not r.get("ok")]
    log("built: %d ok, %d excluded by the build" % (len(ok), len(bad)))
    for r in bad:
        reason = r.get("fail", "?")
        key = "no-hd-source" if reason == "no-hd-source" else ("alpha-used" if reason == "alpha-used" else "gate-fail")
        scope["excluded"].setdefault(key, []).append(dict(base=r["base"], cls=r["cls"], reason=reason,
                                                          source=r.get("source"), tries=r.get("source_tries"),
                                                          repair=r.get("repair"), trace=r.get("trace"),
                                                          gates={k: v for k, v in r.get("gates", {}).items() if not v.get("ok")}))

    # --- cathedarchlrg (bug-2954)
    cath_rep, cath_dds, cath_prev = build_cathedarchlrg(st, table)
    gate("cathedarchlrg gates", cath_rep["ok"], json.dumps(cath_rep["gates"]))
    members[CATH + ".dds"] = cath_dds

    # --- pak-level asserts
    prot_names = set()
    for rank, L in enumerate(st.layers):
        nm = L["name"].lower()
        if L["kind"] == "pak" and (nm in PROTECTED_BELOW or (L["game"] == "maintt" and TV2.fs_key(nm) > TV2.fs_key(PAK_NAME))):
            prot_names |= {strip_ext(p) for p, c in st.members.items() if any(x[0] == rank for x in c)}
    gate("no member shadows a protected coop pak (m3l1a/shadowfix/skies/terrain/fxfix)",
         not any(strip_ext(m) in prot_names for m in members), "")
    gate("no Omaha-named member", not any(OMAHA_TOK.search(m) for m in members))
    om = {e["base"] for e in scope["excluded"].get("omaha-by-map", [])}
    gate("no Omaha-by-map member", not any(strip_ext(m) in om for m in members))
    gate("every member under textures/", all(m.startswith("textures/") for m in members))
    order = sorted([PAK_NAME, "zzzzzzz_dds_hdmem.pk3", "zzzzzzz_dds_override.pk3", "zzzzzzzz_hd_fxfix.pk3",
                    "zzzzzzzzz_coop_terrain.pk3", M3L1A_PAK, SHADOWFIX, "zzzzzzzzzz_coop_hd_skies.pk3"], key=TV2.fs_key)
    gate("sort position (files.cpp FS_PathCmp): above hdmem/override/fxfix/terrain, below m3l1a/shadowfix/skies",
         order.index(PAK_NAME) == 4 and order[5] == M3L1A_PAK, " < ".join(order))
    pak = write_pak(members)
    pak2 = write_pak(dict(sorted(members.items(), reverse=True)))
    gate("pak bytes independent of member insertion order", pak == pak2, sha(pak))
    with zipfile.ZipFile(io.BytesIO(pak)) as z:
        gate("zip CRC test", z.testzip() is None)
        names = [zi.filename for zi in z.infolist()]
    gate("entries sorted", names == sorted(names), "%d members" % len(names))
    # determinism: rebuild a spread sample from scratch and compare bytes
    samp = [j for k, j in enumerate(jobs) if k % max(1, len(jobs) // 6) == 0][:6]
    with ProcessPoolExecutor(min(args.jobs, len(samp) or 1)) as ex:
        again = list(ex.map(build_job, [(layers_json, j) for j in samp]))
    cmp = [(r2, m2) for (r2, m2, _) in again if r2.get("ok")]
    same = all(set(m2) <= set(members) and all(members[k] == v for k, v in m2.items()) for r2, m2 in cmp)
    gate("deterministic rebuild of %d sampled textures (%d built ok)" % (len(samp), len(cmp)), same and (cmp or not ok))
    out_pak = os.path.join(args.out, PAK_NAME)
    with open(out_pak, "wb") as fh:
        fh.write(pak)
    # --- resolve check with the pak mounted where build.ps1 puts it
    st2 = Stack(stack_layers(args.gog, args.home, extra=("maintt", os.path.join(args.gog, "maintt"), PAK_NAME, out_pak)),
                skip_paks=args.skip - {PAK_NAME})
    lost = []
    for m in members:
        b, e = os.path.splitext(m)
        w = st2.resolve(b, ".tga") if e == ".dds" else st2.height_source(b)
        if not w or w["pak"] != PAK_NAME:
            lost.append((m, w and w["pak"]))
    gate("every member resolves to this pak on the live stack (dds diffuse / gl2 height source)", not lost, str(lost[:5]))

    # --- report
    rep = dict(pak=dict(file=out_pak, sha256=sha(pak), bytes=len(pak), members=len(members),
                        dds=sum(1 for m in members if m.endswith(".dds")),
                        siblings=sorted(m for m in members if not m.endswith(".dds")),
                        raw_bytes=sum(len(v) for v in members.values())),
               counts=scope["counts"], included=ok, excluded=scope["excluded"], cathedarchlrg=cath_rep, gates=GATES,
               omaha_maps=scope["omaha_maps"], protected_paks=scope["protected_paks"])
    rep["gate_whatif"] = gate_whatif(scope["excluded"].get("gate-fail", []))
    rep["gate_limits"] = dict(z="<= max(%.1f, retail z)" % Z_FLOOR, p99=P99_MAX, clipped="<= %.2f%% of values, > %d levels" % (
        100 * CLIP_MAX, CLIP_LEVELS), band="min(%.2f, %.2f x retail)" % (BAND_FLOOR, BAND_RETAIL), brightness=BRIGHT_MAX,
        chroma=CHROMA_MAX, mip_z="max(limit, float chain) + %.1f, %d px and up" % (MIP_SLACK, MIP_MIN))
    rep["player_stack_skipped"] = sorted(args.skip)
    if args.baseline:
        with open(args.baseline, encoding="utf-8") as fh:
            old = {r["base"] for r in json.load(fh)["included"]}
        new = {r["base"] for r in ok}

        def why(r):
            mp = not any(not m.split("/")[0] in ("dm", "obj", "lib") for m in scope["rows"][r["base"]]["maps"])
            c = r["repair"]["chosen"]
            return "MP-only" if mp else ("relaxed gates (p99 %.1f, clip>%d %.4f%%)" % (c["p99"], CLIP_LEVELS, 100 * c["clipped"]))
        rep["newly_admitted"] = [dict(base=r["base"], cls=r["cls"], why=why(r), p99=r["repair"]["chosen"]["p99"],
                                      clipped=r["repair"]["chosen"]["clipped"], clipped_any=r["repair"]["chosen"].get("clipped_any"),
                                      z=[r["gates"]["z"]["today"], r["gates"]["z"]["value"], r["gates"]["z"]["retail"]],
                                      band=[r["gates"]["band"]["value"], r["gates"]["band"]["limit"]],
                                      brightness=r["gates"]["brightness"]["value"], chroma=r["gates"]["chroma"]["value"],
                                      maps=scope["rows"][r["base"]]["maps"][:8])
                                 for r in ok if r["base"] not in old]
        rep["dropped_vs_baseline"] = sorted(old - new)
    okb = {x["base"] for x in ok}
    rep["maps_of"] = {b: r["maps"] for b, r in scope["rows"].items() if b in okb or b in CONTENT_CUT}
    rep["area_of"] = {b: r["area_pct"] for b, r in scope["rows"].items() if b in okb}
    rep["counts"]["included"] = len(ok)
    rep["counts"]["included_by_class"] = {c: sum(1 for r in ok if r["cls"] == c) for c in ("new", "amp", "soft")}
    rep["counts"]["excluded_final"] = {k: len(v) for k, v in scope["excluded"].items()}
    with open(os.path.join(args.out, "tilefix_report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, default=_jdefault)
    crops = {}
    for r in ok:
        b = r["base"]
        dds = members[b + ".dds"]
        info = TV2.dds_parse(dds)
        d0 = TV2.dds_decode_level(dds, info, 0)
        rr = scope["rows"][b]
        lv = st.resolve(b, rr["ext"])
        t = decode_rgba(st.read(lv["rank"], lv["member"]))[..., :3]
        if t.shape[:2] != d0.shape[:2]:
            t = np.clip(periodic_resize(t, *d0.shape[:2]), 0, 255)
        crops[b] = (corner_crop(t), corner_crop(d0))
    # content-cut previews: today vs the default wrap correction, to show what the correction cannot hide
    for b in sorted(CONTENT_CUT):
        r = scope["rows"].get(b)
        live = r and st.resolve(b, r["ext"])
        if not live:
            continue
        a = decode_rgba(st.read(live["rank"], live["member"]))[..., :3]
        fixed = apply_repair(a, 1 / 48.0, 1.0)
        previews["cc_" + b] = (thumb(a), thumb(fixed))
        crops["cc_" + b] = (corner_crop(a), corner_crop(fixed))
    hd = st.resolve(CATH, ".tga")
    cath_today = decode_rgba(st.read(hd["rank"], hd["member"]))[..., :3].astype(np.uint8)
    np.savez_compressed(os.path.join(args.out, "previews.npz"),
                        **{("%s__%d" % (k.replace("/", "~"), i)): v[i] for k, v in previews.items() for i in (0, 1)},
                        **{("%s__%d" % (k.replace("/", "~"), i + 2)): v[i] for k, v in crops.items() for i in (0, 1)},
                        cath_before=cath_prev[0], cath_after=cath_prev[1], cath_today=cath_today)
    log("pak %s  sha256 %s  %d members (%d dds, %d siblings)  %.1f MB (raw %.1f MB)" % (
        out_pak, sha(pak), len(members), rep["pak"]["dds"], len(rep["pak"]["siblings"]), len(pak) / 1e6,
        rep["pak"]["raw_bytes"] / 1e6))
    bad_g = [g for g in GATES if not g["ok"]]
    log("%d pak gates, %d failed" % (len(GATES), len(bad_g)))
    if not args.no_sheets:
        write_sheets(args.out, rep, dict(np.load(os.path.join(args.out, "previews.npz"))), log)
    if bad_g:
        sys.exit(1)


if __name__ == "__main__":
    main()

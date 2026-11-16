#!/usr/bin/env python3
"""BYO converter: one Frontline (Xbox) level -> a MOHAA pk3 (BSP + textures +
shaders), generated on the player's own PC from their own disc. Our own code.

usage: flconvert.py <image.iso> <level e.g. 1_1> <out.pk3> [--scale 48]
                    [--mirror] [--flip-render] [--flip-collision] [--report r.json]

Nothing from the disc is ever written anywhere except <out.pk3>.
Determinism: sorted iteration everywhere, fixed zip timestamps, fixed TGA
encoding, so two runs on the same disc give the same sha256.
"""
import argparse
import glob
import hashlib
import io
import json
import math
import os
import struct
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flcore  # noqa: E402
import flbsp   # noqa: E402
import flpack  # noqa: E402
import flseam  # noqa: E402
import flgeom  # noqa: E402
import flclear
import flsheets  # noqa: E402
import flroutes  # noqa: E402
import flscene  # noqa: E402
import flpit  # noqa: E402
import flfit  # noqa: E402
import flcliff  # noqa: E402

CONVERTER_VERSION = "0.6.0"
FL_STEP = 38                  # Frontline step height at 48 u/m: its characters walk the original routes over 35-37u lips (route audit 2026-11-10); 34 left 28 of them blocked

# Frontline .cdb collision flag word (flcore.collision, decoded 2026-11-10 against the level's own AI nav graph):
#   bits 0-10 surface material, bit 23 special surface, bit 22 VOLUME. Material 14 + bit 22 = 450u-tall boxes standing
#   on trigger spots (the crawl hole into the town, the interrogation room): the original's AI navpoint links run
#   straight through them, so they never blocked a character. Converted as solid they were the invisible walls of the
#   user's playtest ("a lot of invisible walls everywhere, blocking progression"). Material 15 + bit 22 is the
#   river's surface and stays.
COLL_VOLUME = 1 << 22
COLL_MAT_VOLUME = (14, 15)   # 14 trigger volumes; 15 the river's WATER volume (its surface was walkable)
COLL_SPECIAL = 1 << 23
TAG_CLIFF = 0x7FFFF001        # [flpolish] collision added by us: edge-of-world clip (flcliff) / lip ramps (flclear)
TAG_RAMP = 0x7FFFF002
# [flfix2] open water (canal, river) is drawn with the MOD'S water: a stock shader name the gl2 water pass allowlists
# (hzm_waterwet.h HARBOUR preset) and whose stock script is the gl1 look. Nothing disc-derived is used for it. The
# name is the one the user accepted on screen (2026-11-11); pond / water_nodraw read as small drifting tiles or a flat
# blue sheet. FL_WATER_SHADER= (empty) is a debug switch only (the old blended vertex-alpha surface), never a default.
WATER_SHADER = os.environ.get("FL_WATER_SHADER", "textures/choppywater/tehao_indoorwater")
# [flfix2] the stock shader's own stages are drawn with the surface's
# texcoords: Frontline's (made for its small water tile) turned them into small drifting tiles. World-space instead,
# one tile per FL_WATER_TILE units (a stock pond brush face at its usual scale).
WATER_TILE = float(os.environ.get("FL_WATER_TILE", "512"))
CONTENTS_WATER = 0x20
CONTENTS_TRANSLUCENT = 0x20000000   # engine surfaceflags.h
SURF_PUDDLE = 0x200000             # engine surfaceflags.h: puddle impact effects / sounds
TAG_RIVERBED = 0x7FFFF005    # [flpolish] the bed under the canal's water volume (a player who falls in lands and drowns)
TAG_DRAWN = 0x7FFFF004       # [flpolish] collision on drawn geometry that a dropped player-clip sheet stood in front of


def coll_is_volume(f):
    return bool(f & COLL_VOLUME) and (f & 0x7FF) in COLL_MAT_VOLUME
MERGE_CELL = 1536.0
# reskinned hedge blocks: a face counts as standing up to this normal z. 0.5 dropped the three leaning skirt
# faces of 1_1 (normal z 0.51 to 0.59; draws 153, 491, 1231), which left the foot of the start lane's west
# hedge open to the fogged far ground: a bright wedge. The disc has no flat hedge tops. [flfix2 bug-11059]
RESKIN_NZ = 0.7
ZIP_TIME = (2002, 5, 28, 0, 0, 0)   # fixed timestamp for deterministic zips


def sky_faces(src_dir, prefix, flip_y):
    """[flfix2 bug-11058] The original's sky is a 6-face box centred on the eye (emulator trace TRACE_sky_fog.md):
    <prefix>_px/nx/py/ny/pz/nz.png, uv 0,0 = top-left texel, face corners as traced. Re-cut texel for texel into the
    engine's six sky images (rt bk lf ft up dn). flip_y: a mirrored build (map y = -original y).
    -> {suffix: (w, h, rgba bytes)} or None when the folder or a face is missing (the level then keeps its stock sky)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    F = {"py": ((-1, 1, 1), (1, 1, 1), (-1, 1, -1)), "px": ((1, 1, 1), (1, -1, 1), (1, 1, -1)),
         "ny": ((1, -1, 1), (-1, -1, 1), (1, -1, -1)), "nx": ((-1, -1, 1), (-1, 1, 1), (-1, -1, -1)),
         "pz": ((-1, -1, 1), (1, -1, 1), (-1, 1, 1)), "nz": ((-1, 1, -1), (1, 1, -1), (-1, -1, -1))}   # uv 00, 10, 01
    img = {}
    for k in F:
        fp = os.path.join(src_dir, f"{prefix}_{k}.png")
        if not os.path.isfile(fp):
            return None
        img[k] = Image.open(fp).convert("RGB")
    # engine sky faces (tr_sky.c MakeSkyVec): direction for image coordinate (s, t), s right, t up, both -1..1
    E = {"rt": lambda a, b: (1.0, -a, b), "lf": lambda a, b: (-1.0, a, b), "bk": lambda a, b: (a, 1.0, b),
         "ft": lambda a, b: (-a, -1.0, b), "up": lambda a, b: (-b, -a, 1.0), "dn": lambda a, b: (b, -a, -1.0)}
    # [look 2026-11-13, user: the disc skies look low quality] 512 px faces sampled bilinearly from the captured faces
    # (they were re-cut texel for texel at 128 px, so the engine magnified 128 px blocks). Nothing is invented: the
    # captures are only interpolated, as the original's own filtering did. Each texel's direction picks the source face
    # exactly as before; at a face border the neighbour face continues the sky, so the twelve edges stay continuous.
    import numpy as np
    N = int(os.environ.get("FL_SKY_SIZE", "512"))
    arr = {k: np.asarray(im, np.float32) for k, im in img.items()}
    out = {}
    c = (np.arange(N, dtype=np.float64) + 0.5) / N
    A = (c * 2 - 1)[None, :].repeat(N, 0)
    Bv = (1 - c * 2)[:, None].repeat(N, 1)
    for suf, vec in E.items():
        d = np.stack(np.broadcast_arrays(*vec(A, Bv)), -1).astype(np.float64)
        if flip_y:
            d[..., 1] = -d[..., 1]
        ax = np.abs(d).argmax(-1)
        col = np.zeros((N, N, 3), np.float32)
        for k in F:
            axis = "xyz".index(k[1])
            sel = (ax == axis) & ((d[..., axis] > 0) if k[0] == "p" else (d[..., axis] <= 0))
            if not sel.any():
                continue
            q = d[sel] / np.abs(d[sel][:, axis:axis + 1])
            v0, v1, v3 = (np.array(t, np.float64) for t in F[k])
            u = ((q - v0) * (v1 - v0)).sum(-1) / 4.0
            v = ((q - v0) * (v3 - v0)).sum(-1) / 4.0
            a = arr[k]
            h, w = a.shape[:2]
            x = np.clip(u * w - 0.5, 0, w - 1)
            y = np.clip(v * h - 0.5, 0, h - 1)
            x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
            x1 = np.minimum(x0 + 1, w - 1); y1 = np.minimum(y0 + 1, h - 1)
            fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
            col[sel] = (a[y0, x0] * (1 - fx) + a[y0, x1] * fx) * (1 - fy) + (a[y1, x0] * (1 - fx) + a[y1, x1] * fx) * fy
        rgba = np.empty((N, N, 4), np.uint8)
        rgba[..., :3] = np.clip(col + 0.5, 0, 255).astype(np.uint8)
        rgba[..., 3] = 255
        out[suf] = (N, N, rgba.tobytes())
    return out


def tga_bytes(w, h, rgba):
    """Uncompressed 32-bit TGA, bottom-up rows (origin lower-left)."""
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    rows = []
    for y in range(h - 1, -1, -1):
        row = rgba[y * w * 4:(y + 1) * w * 4]
        b = bytearray(row)
        b[0::4], b[2::4] = row[2::4], row[0::4]   # RGBA -> BGRA
        rows.append(bytes(b))
    return hdr + b"".join(rows)


class Xform:
    def __init__(self, scale, mirror, offset):
        self.s, self.m, self.o = scale, (-1.0 if mirror else 1.0), offset

    def __call__(self, p):
        return ((p[0] - self.o[0]) * self.s, (p[1] - self.o[1]) * self.s * self.m, (p[2] - self.o[2]) * self.s)


def face_normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    l = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    return (n[0] / l, n[1] / l, n[2] / l) if l > 1e-12 else None


def floor_vote(tris_xyz):
    """+1 if near-horizontal faces mostly point up with this winding."""
    up = down = 0
    for a, b, c in tris_xyz:
        n = face_normal(a, b, c)
        if n is None or abs(n[2]) < 0.9:
            continue
        if n[2] > 0:
            up += 1
        else:
            down += 1
    return up, down


def convert(img, level, out_pk3, scale=48.0, mirror=False, flip_render=None, flip_coll=None, report=None,
            sky_shader=None, vgm=None, mohaa_base=None):
    t0 = time.time()
    L = flcore.Level(flcore.Disc(img), level)
    # coop_fl_*: the engine loads scripted anims per map by NAME PREFIX (new_generic_human.tik "includes ...
    # coop" block); real coop maps use the same prefix, and isCoopEnabledMap accepts it
    mapname = "coop_fl_" + level
    tdir = f"textures/fl/{level}/"

    coll = list(L.collision())
    allc = [v for _, vs, _ in coll for v in vs]
    lo = [min(v[k] for v in allc) for k in range(3)]
    hi = [max(v[k] for v in allc) for k in range(3)]
    offset = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0)
    X = Xform(scale, mirror, offset)
    half = max(hi[0] - lo[0], hi[1] - lo[1]) * scale / 2
    if half > 16000:
        raise SystemExit(f"level too big for MAX_WORLD_COORD at scale {scale}: half-extent {half:.0f}")

    # mirroring reverses every winding
    def wind(a, b, c, flip):
        return (a, c, b) if flip != mirror else (a, b, c)

    # ---- winding votes (decided from the data, recorded in the report) ----
    up, down = floor_vote([(vs[a], vs[b], vs[c]) for _, vs, ts in coll for a, b, c, _ in ts])
    if flip_coll is None:
        flip_coll = down > up
    meshes = list(L.meshes())
    rup, rdown = floor_vote([(m["verts"][a], m["verts"][b], m["verts"][c]) for m in meshes for a, b, c in m["tris"]])
    if flip_render is None:
        # the vote makes floors counter-clockwise seen from above; id Tech 3 front faces are clockwise
        # (verified in-engine 2026-11-08: unflipped, the streets were back-face culled)
        flip_render = not (rdown > rup)

    B = flbsp.BSP()
    # [flfix2 bug-11057] the disc's vertex colour is a plain 1x modulate of the texture. The gl2 renderer multiplies
    # BSP vertex colours at load by 2^(r_mapOverBrightBits - r_overBrightBits) * r_mapOverBrightScale. The mod ships
    # r_mapOverBrightBits 2, r_overBrightBits 0 (coop_defaults.cfg) and r_mapOverBrightScale 0.71 = 2.84, which
    # saturated the disc's colours (about 200 of 255) to white: flat bright daylight. Cancelled here, in the
    # converted map only (no engine cvar is touched). Engine-derived constant, not a look choice.
    B.light_gain = float(os.environ.get("FL_LIGHT_GAIN") or flpack.spec(level).get("light_gain", 1.0 / (4.0 * 0.71)))
    B.vis_cell = 1024.0
    B.vis_radius = float(flpack.spec(level).get("vis_radius", 0))
    files = {}
    shader_lines = []
    tex_names = {}
    stats = {"tris": 0, "tris_textured": 0, "textures": 0, "alpha_textures": 0}

    texmap = {}
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fl_texmap.json")
    if os.path.exists(tmp) and not os.environ.get("FL_NO_TEXMAP"):
        with open(tmp) as f:
            texmap = json.load(f).get(level, {})

    _HD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hd")

    _eng_img = {}

    def _engine_image(path):
        """bytes of the image the renderer loads for <path> on the player's install: <stem>.dds from the last pak that
        has one (r_ext_compressed_textures, on by default), else the path itself from the last pak; None if neither"""
        if path in _eng_img:
            return _eng_img[path]
        stem = os.path.splitext(path)[0].lower()
        best = {}
        for game in ("main", "mainta", "maintt"):        # load order: the last one found wins
            for pk in sorted(glob.glob(os.path.join(mohaa_base or "", game, "*.pk3")), key=str.lower):
                try:
                    z = zipfile.ZipFile(pk)
                except Exception:
                    continue
                for n in z.namelist():
                    nl_ = n.lower()
                    if nl_ == stem + ".dds":
                        best["dds"] = (pk, n)
                    elif nl_ == path.lower():
                        best["own"] = (pk, n)
        data = None
        for kind in ("dds", "own"):
            if kind in best:
                try:
                    data = zipfile.ZipFile(best[kind][0]).read(best[kind][1])
                    from PIL import Image as _I
                    import io as _io2
                    _I.open(_io2.BytesIO(data)).load()        # a DDS PIL cannot decode falls through to the tga
                    break
                except Exception:
                    data = None
        _eng_img[path] = data
        return data

    def recolour_card(key, up):
        """[flfix2 round 19d] TGA bytes of the card image the engine draws for up["path"], luminance kept and recoloured to the disc card hue so its
        solid texels' mean equals the disc card's (gain 0.25..6), at most 512 px; None when either image is missing"""
        try:
            import io as _io
            import numpy as _np
            from PIL import Image
            t = L.texture(key)
            data = _engine_image(up["path"])
            if not (t and t["rgba"]) or data is None:
                return None
            d = _np.frombuffer(t["rgba"], _np.uint8).reshape(t["h"], t["w"], 4).astype(_np.float32)
            fl = d[d[..., 3] >= 128][:, :3].mean(0)
            im = Image.open(_io.BytesIO(data)).convert("RGBA")
            if max(im.size) > 512:
                im = im.resize((min(512, im.size[0]), min(512, im.size[1])), Image.LANCZOS)
            a = _np.asarray(im).astype(_np.float32)
            sol = a[..., 3] >= 128
            if not sol.any():
                return None
            # luminance from the drawn image, hue from the disc card: a per-channel gain (blue x9 on tree1_5) blew the
            # bark's blue noise into bright blue streaks (round 19d QA)
            lw = _np.array([0.299, 0.587, 0.114], _np.float32)
            lum = (a[..., :3] * lw).sum(-1)
            fl_l = float((fl * lw).sum())
            k = fl_l / max(1.0, float(lum[sol].mean()))
            a[..., :3] = _np.clip((lum * k)[..., None] * (fl / max(1.0, fl_l))[None, None, :], 0, 255)
            a[..., 3] = _np.where(a[..., 3] >= 128, 255, 0)
            o = a.astype(_np.uint8)
            return tga_bytes(o.shape[1], o.shape[0], o.tobytes())
        except Exception:
            return None

    def _local(up):
        """[look 2026-11-13] a texture shipped next to the converter (hd/<file>, CC0, credited in hd/CREDITS.txt): its
        bytes, or None. It is written into the converted pak under textures/hd/<file>."""
        if not up.get("local"):
            return None
        fp = os.path.join(_HD_DIR, up["local"])
        if not os.path.isfile(fp):
            return None
        up.setdefault("path", "textures/hd/" + up["local"])
        return open(fp, "rb").read()

    def upgrade_ok(up):
        """only when the player's own install carries the pak that holds the texture (or the converter ships it)"""
        if up.get("local"):
            data = _local(up)
            if data is None:
                return False
            files.setdefault(up["path"], data)
            return True
        if not mohaa_base:
            return False
        for game in ("maintt", "mainta", "main"):
            pk = os.path.join(mohaa_base, game, up["pak"])
            if os.path.exists(pk):
                try:
                    if up["path"] in zipfile.ZipFile(pk).namelist():
                        return True
                except Exception:
                    pass
        return False

    # share of each texture's triangles that are NOT vertical (foliage cards vs wall decals)
    _tf = {}
    for m in meshes:
        if not m["tex"]:
            continue
        for a, b, c in m["tris"]:
            n = face_normal(m["verts"][a], m["verts"][b], m["verts"][c])
            if n is None:
                continue
            t_ = _tf.setdefault(m["tex"], [0, 0])
            t_[0] += 1
            t_[1] += abs(n[2]) >= 0.3
    tex_flat = {k: v[1] / v[0] for k, v in _tf.items() if v[0]}
    # textures whose meshes carry real vertex alpha (Frontline's water: 203)
    vtx_alpha = {m["tex"] for m in meshes if m["tex"] and m["tris"] and min(c[3] for c in m["cols"]) < 250}
    _lv = sorted(c[0] + c[1] + c[2] for m in meshes for c in m["cols"] if not (c[0] == c[1] == c[2] == 255))
    _mv = _lv[len(_lv) // 2] // 3 if _lv else 128
    med_light = (_mv, _mv, _mv)
    grade = {}     # upgraded texture key -> per-channel gain toward Frontline's own texture colour

    def grade_for(key, up):
        """deterministic grade: scale the vertex colours so the HD texture's mean colour lands on Frontline's"""
        import io as _io
        from statistics import fmean
        t = L.texture(key)
        if not (t and t["rgba"]):
            return None
        # [look 2026-11-13] a cut-out card is graded on its solid texels only (the clear ones hold no colour)
        cut = bool(up.get("alpha"))
        if cut:
            sol = [i for i in range(0, len(t["rgba"]), 4) if t["rgba"][i + 3] >= 128]
            if not sol:
                return None
            fl = [fmean(t["rgba"][i + c] for i in sol) for c in range(3)]
        else:
            fl = [fmean(t["rgba"][c::4]) for c in range(3)]
        data = _local(up)
        if data is None:
            # [flfix2 round 19d] grade against the image the ENGINE draws: R_LoadImage tries <name>.dds first (the HD
            # DDS override paks), then the last pak in load order. The stock tree card 1dd980 was graded on Pak2's
            # 256 px tga (mean blue 25) while the dds drawn has mean blue 3: the lane's branch cards came out yellow.
            data = _engine_image(up["path"]) if up.get("path") else None
        if data is None:
            for game in ("maintt", "mainta", "main"):
                pk = os.path.join(mohaa_base, game, up["pak"]) if up.get("pak") else None
                if pk and os.path.exists(pk):
                    try:
                        data = zipfile.ZipFile(pk).read(up["path"])
                        break
                    except Exception:
                        continue
        if data is None:
            return None
        try:
            from PIL import Image
            im = Image.open(_io.BytesIO(data)).convert("RGBA").resize((64, 64))
            px = im.tobytes()
            idx = [i for i in range(0, len(px), 4) if px[i + 3] >= 128] if cut else list(range(0, len(px), 4))
            if not idx:
                return None
            hd = [fmean(px[i + c] for i in idx) for c in range(3)]
        except Exception:
            return None
        return tuple(max(0.3, min(1.2, round(f / max(1.0, h), 3))) for f, h in zip(fl, hd))

    debug_ids = {}

    water_keys = set()

    def tex_shader(key):
        if key in tex_names:
            return tex_names[key]
        if (key in vtx_alpha and WATER_SHADER and tex_flat.get(key, 0) >= 0.9 and not os.environ.get("FL_DEBUGCOLOR")
                and (L.texture(key) or {}).get("rgba") and min(L.texture(key)["rgba"][3::4]) >= 250):
            # [flfix2] Frontline's water (flat meshes with real vertex alpha and an OPAQUE texture; the soft shadow and
            # scorch decals also carry vertex alpha, but their texture has an alpha channel) -> the mod's water shader
            stats["water_shader"] = WATER_SHADER
            water_keys.add(key)
            stats["water_textures"] = stats.get("water_textures", 0) + 1
            tex_names[key] = B.shader(WATER_SHADER, 0, 0)
            return tex_names[key]
        if key is None:
            name = tdir + "untextured"
            if name not in files:
                # [flpolish] white: Frontline draws these untextured (1974 tris on 1_1) in their vertex colour alone;
                # the old blue-grey (40,70,90) stand-in tinted every one of them
                files[name + ".tga"] = tga_bytes(4, 4, bytes((255, 255, 255, 255)) * 16)
                shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\t{{\n\t\tmap {name}.tga\n\t\trgbGen vertex\n\t}}\n}}\n")
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        t = L.texture(key)
        short = key.replace(f"{level}_ART", "").replace(".cpt", "").replace("@", "_").strip("_")
        # [flfix2 bug-11034] no dot in a shader name: the engine strips a shader name at its last dot
        # (COM_StripExtension), so every texture of one object mesh ("Vehicle_Jeep_Body.msh_11a00", "..msh_13b00")
        # resolved to the same shader and the whole jeep wore its grille texture
        name = tdir + short.replace(".", "_")
        up = texmap.get(short)
        if up and upgrade_ok(up):
            # upgrade to a texture the mod already ships (fl_texmap.json); Frontline's vertex light stays on top
            sc = up.get("tc_scale", 1.0)
            tcm = ("\t\ttcMod scale %g %g\n" % (sc, sc)) if sc != 1.0 else ""
            # [look 2026-11-13] "alpha": a cut-out card (tree, bush) keeps its hard alpha edge and writes depth
            acut = "\t\talphaFunc GE128\n\t\tdepthWrite\n" if up.get("alpha") else ""
            # stock card recipe (scripts/trees.shader, TAnatural.shader): nomipmaps, or thin twigs dissolve into dashes
            # under GE128 at distance
            nomip = "\tnomipmaps\n" if up.get("alpha") else ""
            mpath = up["path"]
            rec_ = recolour_card(key, up) if up.get("alpha") and up.get("recolour", True) else None
            if rec_:
                # [flfix2 round 19d] the stock card the engine draws (the HD DDS override) has another hue than the disc
                # card (tree1_5: mean blue 2 against the disc's 18 - the lane's branch cards read yellow) and a vertex
                # grade cannot move hue past its clamp: the drawn image is written into this pak per-channel matched to
                # the disc card's solid texels, and mapped instead (player's own install data, private pak)
                mpath = name + "_hd.tga"
                files[mpath] = rec_
                stats.setdefault("recoloured_cards", []).append(short)
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n" + nomip + "\tcull none\n\t{\n\t\tmap " + mpath + "\n"
                                + tcm + acut + "\t\trgbGen vertex\n\t}\n}\n")
            stats["upgraded"] = stats.get("upgraded", 0) + 1
            if up.get("grade", True) and not rec_:
                g = grade_for(key, up)
                if g:
                    grade[key] = g
                    stats.setdefault("grades", {})[short] = g
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        rgba = t["rgba"] if t and t["rgba"] else bytes((255, 0, 255, 255)) * 16
        w, h = (t["w"], t["h"]) if t and t["rgba"] else (4, 4)
        files[name + ".tga"] = tga_bytes(w, h, rgba)
        stats["textures"] += 1
        if os.environ.get("FL_DEBUGCOLOR"):
            # QA aid: every texture becomes one flat, fullbright ID colour -> a screenshot pixel names the shader
            i = len(tex_names) + 1
            col = ((i * 37) % 251, (i * 91) % 241, (i * 173) % 239)
            debug_ids[col] = short
            files[name + ".tga"] = tga_bytes(4, 4, bytes(col + (255,)) * 16)
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tcull none\n\t{\n\t\tmap " + name
                                + ".tga\n\t\trgbGen identity\n\t}\n}\n")
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        has_alpha = any(a < 250 for a in rgba[3::4])
        n_px = max(1, len(rgba) // 4)
        part = sum(1 for a in rgba[3::4] if 0 < a < 250) / n_px
        soft = part > 0.10
        # [flpolish] FOLIAGE is cut out, not blended: the tree canopies near the drop (1e1a80 flat cards, 1e5c00 tilted
        # cards) have antialiased leaf edges (10-17% partial alpha) and were drawn as blended surfaces - no depth write,
        # unsorted, so the leaves behind showed through the leaves in front: the user's "tree billboards near the
        # beginning are broken: open or see-through". A mostly-clear texture (>= 40% fully transparent) with few soft
        # pixels (< 25%) used mainly on non-vertical cards is foliage -> alpha test with depth write.
        if soft and part < 0.25 and sum(1 for a in rgba[3::4] if a == 0) / n_px >= 0.40 and tex_flat.get(key, 0) >= 0.5:
            soft = False
            stats["foliage_cutout"] = stats.get("foliage_cutout", 0) + 1
        if key in vtx_alpha or soft:
            # translucent: Frontline's water carries its opacity in the vertex alpha (203); soft-edged decals
            # (grass fringes along hedges) carry it in the texture - alpha-TEST turned their pale fringe opaque
            ag = "\t\talphaGen vertex\n" if key in vtx_alpha else ""
            stats["blended"] = stats.get("blended", 0) + 1
            # [flfix2] soft ground decals (blob shadows under the MG nests and crates, scorch and stain patches) lie
            # 0.5-3u over the cobbles: without a depth offset they z-fight into hard black patches at range
            po = "\tpolygonOffset\n" if soft and tex_flat.get(key, 0) >= 0.9 else ""
            if po:
                stats["ground_decals"] = stats.get("ground_decals", 0) + 1
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n" + po + "\tcull none\n\t{\n\t\tmap "
                                + name + ".tga\n\t\tblendFunc blend\n\t\trgbGen vertex\n" + ag + "\t}\n}\n")
        elif has_alpha:
            stats["alpha_textures"] += 1
            shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\t{{\n\t\tmap {name}.tga\n"
                                f"\t\talphaFunc GE128\n\t\trgbGen vertex\n\t\tdepthWrite\n\t}}\n}}\n")
        else:
            # two-sided: Frontline mixes windings inside one mesh (terrain skirts, facades)
            shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\t{{\n\t\tmap {name}.tga\n"
                                f"\t\trgbGen vertex\n\t}}\n}}\n")
        tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
        return tex_names[key]

    # render-only reskins from fl_modelmap.json (MOHAA art from the player's install, nothing shipped)
    _mm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fl_modelmap.json")
    reskin = json.load(open(_mm)).get(level, {}).get("reskin", {}) if os.path.exists(_mm) else {}
    hidden = {(h["cell"], int(h["draw"])) for h in (json.load(open(_mm)).get(level, {}).get("hide", []) if os.path.exists(_mm) else [])}
    # [flfix2 round 19c] "foot": the disc's own texture is kept, but each standing face of it gets a skirt of that many
    # units below its lowest edge (same texture, its bottom row stretched), so where the ground falls away from a hedge
    # the player does not look under the box into the void (user 2026-11-13: the disc's own hedge boxes, see-through fixed)
    footmap = json.load(open(_mm)).get(level, {}).get("foot", {}) if os.path.exists(_mm) else {}

    def short_key(key):
        return str(key).replace(f"{level}_ART", "").replace(".cpt", "").replace("@", "_").strip("_")

    def reskin_shader(rk, core=False):
        # [flfix2 round 19, bug-11162] the card wears polygonOffset so it wins over its own opaque core (below), which
        # lies in the same plane; the core is the same image's leaf body (no alpha there) and has no offset
        name = tdir + rk["shader"] + ("_core" if core else "")
        if name not in tex_names:
            po = "" if core or not rk.get("core") else "\tpolygonOffset\n"
            shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n{po}\tnopicmip\n\t{{\n\t\tmap {rk['image']}\n"
                                f"\t\talphaFunc GE128\n\t\trgbGen vertex\n\t\tdepthWrite\n\t}}\n}}\n")
            tex_names[name] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
        return tex_names[name]

    _rkgrade = {}

    def reskin_grade(key, rk):
        """per-channel vertex-colour gain so the MOHAA image's OPAQUE mean lands on Frontline's own texture mean
        (grade_for's rule; the hedgerow's transparent sky band must not pull the mean)"""
        if key in _rkgrade:
            return _rkgrade[key]
        g = (1.0, 1.0, 1.0)
        try:
            import io as _io
            from PIL import Image
            from statistics import fmean
            t = L.texture(key)
            fl = [fmean(t["rgba"][c::4]) for c in range(3)] if t and t["rgba"] else None
            data = None
            for game in ("main", "mainta", "maintt"):        # last in load order wins
                for pk in sorted(glob.glob(os.path.join(mohaa_base, game, "*.pk3")), key=str.lower):
                    try:
                        z = zipfile.ZipFile(pk)
                        nm = {n.lower(): n for n in z.namelist()}.get(rk["image"].lower())
                        if nm:
                            data = z.read(nm)
                    except Exception:
                        pass
            if fl and data:
                im = Image.open(_io.BytesIO(data)).convert("RGBA").resize((128, 128))
                px = [q for q in im.getdata() if q[3] >= 128]
                hd = [fmean(q[c] for q in px) for c in range(3)]
                g = tuple(max(0.3, min(1.2, round(f / max(1.0, h), 3))) for f, h in zip(fl, hd))
        except Exception:
            pass
        _rkgrade[key] = g
        stats.setdefault("reskin_grade", {})[short_key(key)] = list(g)
        return g

    _cols = {}

    def reskin_columns(k):
        """(x, y) -> (bottom, top) of the reskinned texture's geometry within 40u: one hedge wall = one column"""
        if k not in _cols:
            g = {}
            for mm in meshes:
                if mm["tris"] and mm["tex"] and short_key(mm["tex"]) == k:
                    for v in mm["verts"]:
                        q = X(v)
                        g.setdefault((int(q[0] // 40), int(q[1] // 40)), []).append(q[2])
            _cols[k] = g

        def f(x, y):
            zs = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    zs += _cols[k].get((int(x // 40) + dx, int(y // 40) + dy), [])
            return (min(zs), max(zs)) if zs else (0.0, 0.0)
        return f

    # [flfix2 bug-11064] A texture axis the level never tiles (every UV of that texture within 0..1) is sampled right
    # on its edge rows; the mod's renderer wraps and filters, so the opposite edge row bleeds in as a thin line (the
    # pale line down the middle of the start lane, where the road texture is mirrored at v = 0, and the white streaks
    # at the edges of branch cards against the sky). Those axes are pulled in by half a texel: 0 and 1 land on the
    # centres of the edge rows. Axes that tile are left alone.
    uv_rng = {}
    for m in meshes:
        if m["tris"] and m["uvs"]:
            r_ = uv_rng.setdefault(m["tex"], [9.0, -9.0, 9.0, -9.0])
            us_ = [q[0] for q in m["uvs"]]
            vs_ = [q[1] for q in m["uvs"]]
            r_[0] = min(r_[0], min(us_)); r_[1] = max(r_[1], max(us_))
            r_[2] = min(r_[2], min(vs_)); r_[3] = max(r_[3], max(vs_))
    uv_inset = {}
    for k_, r_ in uv_rng.items():
        t_ = L.texture(k_) if k_ is not None else None
        if not t_ or not t_.get("w") or not t_.get("h"):
            continue
        iu_ = t_["w"] if (r_[0] >= -0.002 and r_[1] <= 1.002) else 0
        iv_ = t_["h"] if (r_[2] >= -0.002 and r_[3] <= 1.002) else 0
        if iu_ or iv_:
            uv_inset[k_] = (iu_, iv_)
    stats["uv_inset_textures"] = len(uv_inset)
    # [flfix2 round 19, bug-11163] some of the disc's big out-of-bounds ground triangles carry UVs shared by pairs of
    # vertices (c6 draws 358 / 535 / 741 / 1242 on 1_1: zero UV area), so the texture is smeared along one line - the
    # dark streaked ground the user saw from a window by the wall objective. Such a ground triangle (|n.z| >= 0.4,
    # >= 10000 u^2) of a TILING texture gets planar world UVs at that texture's own median floor density (the units
    # per repeat of its well-mapped floor triangles). Nothing else is touched.
    floor_rep = {}
    for m in meshes:
        if not m["tris"] or not m["tex"] or m["tex"] in uv_inset:
            continue
        P_ = [X(v) for v in m["verts"]]
        U_ = m["uvs"]
        for a, b, c in m["tris"]:
            e1 = [P_[b][i] - P_[a][i] for i in range(3)]
            e2 = [P_[c][i] - P_[a][i] for i in range(3)]
            nn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
            ar2 = math.sqrt(sum(x * x for x in nn))
            uva2 = abs((U_[b][0] - U_[a][0]) * (U_[c][1] - U_[a][1]) - (U_[c][0] - U_[a][0]) * (U_[b][1] - U_[a][1]))
            if ar2 > 1.0 and abs(nn[2]) >= 0.9 * ar2 and uva2 > 1e-9:
                floor_rep.setdefault(m["tex"], []).append(math.sqrt(ar2 / uva2))   # world units per UV unit
    floor_rep = {k_: sorted(v_)[len(v_) // 2] for k_, v_ in floor_rep.items() if len(v_) >= 8}
    batches = {}
    for m in meshes:
        if not m["tris"]:
            continue
        sh = tex_shader(m["tex"])
    for m in meshes:
        if not m["tris"]:
            continue
        if (m["cell"], m["draw"]) in hidden:          # fl_modelmap.json "hide": render-only removal (reason per entry)
            stats["hidden_draws"] = stats.get("hidden_draws", 0) + 1
            continue
        sh = tex_shader(m["tex"])
        P = [X(v) for v in m["verts"]]
        tris = [wind(a, b, c, flip_render) for a, b, c in m["tris"]]
        # vertex normals
        acc = [[0.0, 0.0, 0.0] for _ in P]
        for a, b, c in tris:
            n = face_normal(P[a], P[b], P[c])
            if n:
                for i in (a, b, c):
                    acc[i][0] += n[0]; acc[i][1] += n[1]; acc[i][2] += n[2]
        verts = []
        for i, p in enumerate(P):
            l = math.sqrt(sum(x * x for x in acc[i])) or 1.0
            r, g, b, va = m["cols"][i]
            if r == g == b == 255:
                # Frontline marks some draws "unlit" with pure-white vertex colour; under id Tech 3's vertex
                # overbright that blows out (the white strip along the hedge alley) -> the level's median light
                r, g, b = med_light
            gr = grade.get(m["tex"])
            if gr:
                r, g, b = (min(255, int(round(c * k))) for c, k in zip((r, g, b), gr))
            u, v = m["uvs"][i]
            ins_ = uv_inset.get(m["tex"])
            if ins_:
                if ins_[0]:
                    u = (0.5 + min(1.0, max(0.0, u)) * (ins_[0] - 1)) / ins_[0]
                if ins_[1]:
                    v = (0.5 + min(1.0, max(0.0, v)) * (ins_[1] - 1)) / ins_[1]
            if m["tex"] in water_keys:
                u, v = p[0] / WATER_TILE, p[1] / WATER_TILE
            nrm = tuple(x / l for x in acc[i])
            if m["tex"] in water_keys:
                # the water pass draws only where the vertex normal points up (hzmwater_fp.glsl: var_NormalZ >= 0.7, a stock
                # brush face's own normal); Frontline winds its water sheet the other way, so the summed face normals
                # point DOWN and the pass discarded every pixel: the canal showed the stock stages alone
                nrm = (0.0, 0.0, 1.0)
            verts.append((p, (u, v), nrm, (r, g, b, va if m["tex"] in vtx_alpha else 255)))
        rep_ = floor_rep.get(m["tex"]) if m["tex"] not in water_keys else None
        if rep_:
            # [flfix2 round 19, bug-11163] zero-UV-area floor triangles -> planar world UVs (see floor_rep above)
            nt_ = []
            for a, b, c in tris:
                A_, B_, C_ = verts[a], verts[b], verts[c]
                uva2 = abs((B_[1][0] - A_[1][0]) * (C_[1][1] - A_[1][1]) - (C_[1][0] - A_[1][0]) * (B_[1][1] - A_[1][1]))
                n_ = face_normal(A_[0], B_[0], C_[0])
                if uva2 > 1e-9 or n_ is None or abs(n_[2]) < 0.4:      # embankment slopes too (c6 240: n.z 0.67)
                    nt_.append((a, b, c))
                    continue
                e1 = [B_[0][i] - A_[0][i] for i in range(3)]
                e2 = [C_[0][i] - A_[0][i] for i in range(3)]
                if math.sqrt(sum(x * x for x in (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2],
                                                 e1[0] * e2[1] - e1[1] * e2[0]))) / 2 < 10000.0:
                    nt_.append((a, b, c))
                    continue
                k0 = len(verts)
                for q in (A_, B_, C_):
                    verts.append((q[0], (q[0][0] / rep_, -q[0][1] / rep_), q[2], q[3]))
                nt_.append((k0, k0 + 1, k0 + 2))
                stats["uv_planar_tris"] = stats.get("uv_planar_tris", 0) + 1
            tris = nt_
        ft_ = footmap.get(short_key(m["tex"])) if m["tex"] else None
        if ft_:
            # [flfix2 round 19c] foot skirt (see footmap): per plane of standing faces, every edge on the plane's lowest
            # height gets a quad down to that height - skirt, with the edge's own UVs and colours
            sk_ = float(ft_.get("skirt", 96))
            pl_ = {}
            for a, b, c in tris:
                n = face_normal(verts[a][0], verts[b][0], verts[c][0])
                if not n or abs(n[2]) > RESKIN_NZ:
                    continue
                hl = math.hypot(n[0], n[1]) or 1.0
                hx, hy = n[0] / hl, n[1] / hl
                if hx < -1e-6 or (abs(hx) < 1e-6 and hy < 0):
                    hx, hy = -hx, -hy
                k_ = (round(math.degrees(math.atan2(hy, hx)) / 3), round((hx * verts[a][0][0] + hy * verts[a][0][1]) / 6))
                pl_.setdefault(k_, []).append((a, b, c))
            add_ = []
            for k_, ts_ in pl_.items():
                # [round 19d] the hedge's foot is bumpy: skirt every BOUNDARY edge of the plane's faces that has its own
                # triangle above it (was: only edges at the plane's lowest height - the pale void sliver in hedgeFar)
                pk3_ = lambda v: (round(v[0][0], 1), round(v[0][1], 1), round(v[0][2], 1))     # noqa: E731
                ecount_ = {}
                for t_ in ts_:
                    for i, j in ((t_[0], t_[1]), (t_[1], t_[2]), (t_[2], t_[0])):
                        ek_ = tuple(sorted((pk3_(verts[i]), pk3_(verts[j]))))
                        ecount_[ek_] = ecount_.get(ek_, 0) + 1
                for t_ in ts_:
                    for i, j, k in ((t_[0], t_[1], t_[2]), (t_[1], t_[2], t_[0]), (t_[2], t_[0], t_[1])):
                        if ecount_[tuple(sorted((pk3_(verts[i]), pk3_(verts[j]))))] != 1:
                            continue
                        if verts[k][0][2] - max(verts[i][0][2], verts[j][0][2]) < 8.0:
                            continue          # a side or top edge, not a foot
                        # the texture CONTINUES down the skirt (its UV gradient along -z on this triangle), not one
                        # stretched row (that read as a striped band under the hedges)
                        P0, P1, P2 = verts[i][0], verts[j][0], verts[k][0]
                        e1 = [P1[q] - P0[q] for q in range(3)]
                        e2 = [P2[q] - P0[q] for q in range(3)]
                        g11 = sum(x * x for x in e1); g22 = sum(x * x for x in e2); g12 = sum(x * y for x, y in zip(e1, e2))
                        det_ = g11 * g22 - g12 * g12
                        duv_ = (0.0, 0.0)
                        if abs(det_) > 1e-6:
                            r1, r2 = -sk_ * e1[2], -sk_ * e2[2]               # d . e1, d . e2 with d = (0, 0, -skirt)
                            ca, cb = (r1 * g22 - r2 * g12) / det_, (r2 * g11 - r1 * g12) / det_
                            U0, U1, U2 = verts[i][1], verts[j][1], verts[k][1]
                            duv_ = (ca * (U1[0] - U0[0]) + cb * (U2[0] - U0[0]), ca * (U1[1] - U0[1]) + cb * (U2[1] - U0[1]))
                        b_ = len(verts)
                        for q in (verts[i], verts[j]):
                            verts.append(q)
                        for q in (verts[j], verts[i]):
                            verts.append(((q[0][0], q[0][1], q[0][2] - sk_), (q[1][0] + duv_[0], q[1][1] + duv_[1]), q[2], q[3]))
                        add_ += [(b_, b_ + 1, b_ + 2), (b_, b_ + 2, b_ + 3)]
            tris = list(tris) + add_
            stats["foot_tris"] = stats.get("foot_tris", 0) + len(add_)
        rk = reskin.get(short_key(m["tex"])) if m["tex"] else None
        if rk:
            # fl_modelmap.json "reskin": render-only swap to MOHAA art from the player's own install (e.g. Frontline's
            # opaque hedge boxes -> the MOHAA bocage hedgerow card). Each vertical face is re-mapped as a facade:
            # u along the face (rk.tile units per repeat), v bottom -> top over the whole image, and the top raised by
            # rk.overshoot of the face height so the image's alpha crown rises above the old flat top. Collision is
            # built from Frontline's .cdb separately and is not touched.
            sh = reskin_shader(rk)
            gk = reskin_grade(m["tex"], rk)
            # one wall = the triangles of this draw that share a plane (stacked quads map as one face, and a
            # neighbouring taller hedge can no longer stretch it - that put the image's transparent band mid-wall)
            planes_ = {}
            for a, b, c in tris:
                n = face_normal(verts[a][0], verts[b][0], verts[c][0])
                if not n or abs(n[2]) > RESKIN_NZ:
                    continue
                hl = math.hypot(n[0], n[1]) or 1.0
                hx, hy = n[0] / hl, n[1] / hl
                if hx < -1e-6 or (abs(hx) < 1e-6 and hy < 0):
                    hx, hy = -hx, -hy
                pk_ = (round(math.degrees(math.atan2(hy, hx)) / 3), round((hx * verts[a][0][0] + hy * verts[a][0][1]) / 6))
                zz = planes_.setdefault(pk_, [1e9, -1e9])
                for i in (a, b, c):
                    zz[0] = min(zz[0], verts[i][0][2])
                    zz[1] = max(zz[1], verts[i][0][2])
                planes_.setdefault(("t", a, b, c), pk_)
            nv, nt = [], []
            cv_, ct_ = [], []
            for a, b, c in tris:
                T = [verts[a], verts[b], verts[c]]
                n = face_normal(T[0][0], T[1][0], T[2][0])
                if not n or abs(n[2]) > RESKIN_NZ:
                    continue                          # only the standing faces of the block
                z0, z1 = planes_[planes_[("t", a, b, c)]]
                if z1 - z0 < 4:
                    continue
                hl = math.hypot(n[0], n[1]) or 1.0
                tx, ty = -n[1] / hl, n[0] / hl
                # [flfix2 round 19b] uneven crown: the overshoot varies per hedge face (a fixed hash of its plane) by
                # +-overshoot_jitter, so neighbouring segments do not share one straight top line
                pk2_ = planes_[("t", a, b, c)]
                jit_ = ((pk2_[0] * 7919 + pk2_[1] * 104729) % 1000) / 999.0 * 2.0 - 1.0     # deterministic, -1..1
                ztop = z0 + (z1 - z0) * (1.0 + float(rk.get("overshoot", 0.25)) + float(rk.get("overshoot_jitter", 0.0)) * jit_)
                base = len(nv)
                for q in T:
                    p = q[0]
                    # the wall's top-quarter vertices rise by the crown FROM THEIR OWN HEIGHT: Frontline's bumpy hedge
                    # profile is kept and the image's alpha crown sits on it (v1/v2 flattened the tops)
                    pz = p[2] + (ztop - z1) if p[2] >= z0 + (z1 - z0) * 0.75 else p[2]
                    uu = (p[0] * tx + p[1] * ty) / float(rk.get("tile", 128))
                    # [flfix2 round 19b] v_range: the image rows the card uses, top -> bottom (skips the empty top band
                    # so the leaf body reaches higher, and the bottom rows next to the wrap seam: the orange line)
                    vr0_, vr1_ = rk.get("v_range", (0.0, 1.0))
                    vv = vr0_ + (vr1_ - vr0_) * (ztop - pz) / max(1.0, ztop - z0)
                    cr, cg, cb = (min(255, int(round(q[3][k] * gk[k]))) for k in range(3))
                    nv.append(((p[0], p[1], pz), (uu, vv), q[2], (cr, cg, cb, 255)))
                nt.append((base, base + 1, base + 2))
                if rk.get("core"):
                    # [flfix2 round 19, bug-11162] the opaque CORE: the original's own hedge face, unraised, in the image's
                    # leaf body (v core[0]..core[1] top -> bottom, no alpha there), darker (the inside of the hedge). The
                    # card's gappy crown band covers the top third of the original's opaque box; through its gaps the
                    # player saw through the hedge, at the level's edge into the void ("into nothingness"). The core
                    # fills them with leaves where the original was solid; above the old top the crown stays open.
                    v0_, v1_ = rk["core"]
                    kd_ = float(rk.get("core_shade", 0.75))
                    cb_ = len(cv_)
                    sk_ = float(rk.get("core_skirt", 0))
                    for q in T:
                        p = q[0]
                        uu = (p[0] * tx + p[1] * ty) / float(rk.get("tile", 128))
                        vv = v1_ - (v1_ - v0_) * (p[2] - z0) / max(1.0, z1 - z0)
                        if sk_ and p[2] <= z0 + 0.25 * (z1 - z0):
                            # the foot goes core_skirt further down: where the ground falls away from a hedge the
                            # original showed the void under the box (the light band under the hedgerows)
                            p = (p[0], p[1], p[2] - sk_)
                        cr, cg, cb = (min(255, int(round(q[3][k] * gk[k] * kd_))) for k in range(3))
                        cv_.append(((p[0], p[1], p[2]), (uu, vv), q[2], (cr, cg, cb, 255)))
                    ct_.append((cb_, cb_ + 1, cb_ + 2))
            if ct_:
                ccx = sum(v[0][0] for v in cv_) / len(cv_)
                ccy = sum(v[0][1] for v in cv_) / len(cv_)
                batches.setdefault((reskin_shader(rk, core=True), int(ccx // MERGE_CELL), int(ccy // MERGE_CELL)),
                                   []).append((cv_, ct_))
                stats["reskin_core_tris"] = stats.get("reskin_core_tris", 0) + len(ct_)
            stats["reskinned_tris"] = stats.get("reskinned_tris", 0) + len(nt)
            if not nt:
                continue
            verts, tris = nv, nt
        cx = sum(v[0][0] for v in verts) / len(verts)
        cy = sum(v[0][1] for v in verts) / len(verts)
        batches.setdefault((sh, int(cx // MERGE_CELL), int(cy // MERGE_CELL)), []).append((verts, tris))
        stats["tris"] += len(tris)
        if m["tex"]:
            stats["tris_textured"] += len(tris)

    # seam bridges: close Frontline's hairline floor gaps that would show the sky (flseam.py has the rules)
    # collision grid: seam bridges only close gaps in WALKABLE floors; flpack places actors with it
    grid = flgeom.TriGrid([(X(vs[a]), X(vs[b]), X(vs[c])) for _, vs, ts in coll for a, b, c, _f in ts
                          if not coll_is_volume(_f)])
    if not os.environ.get("FL_NO_SEAMS"):
        draws = [(key[0], verts, tris) for key in sorted(batches) for verts, tris in batches[key]]
        def on_floor(x, y, z):
            # beside a walkable floor: Frontline's collision often has the same seam as its render mesh
            return any(grid.ground(x + dx, y + dy, z + 24, z - 24) is not None
                       for dx, dy in ((0, 0), (24, 0), (-24, 0), (0, 24), (0, -24)))
        br = flseam.bridges(draws, on_floor)
        br += flseam.bridges(draws + br, on_floor)     # pass 2: the corner gaps between neighbouring bridges
        for sh_, verts, tris in br:
            cx = sum(v[0][0] for v in verts) / len(verts)
            cy = sum(v[0][1] for v in verts) / len(verts)
            batches.setdefault((sh_, int(cx // MERGE_CELL), int(cy // MERGE_CELL)), []).append((verts, tris))
        stats["seam_bridges"] = len(br)
        # hand-located corner holes no edge pair spans (fl_levels.json "patches": polygon + texture + reason)
        pq = flseam.patches(draws + br, flpack.spec_xy(level, X, "patches"), lambda i: B.shaders[i][0])
        for sh_, verts, tris in pq:
            cx = sum(v[0][0] for v in verts) / len(verts)
            cy = sum(v[0][1] for v in verts) / len(verts)
            batches.setdefault((sh_, int(cx // MERGE_CELL), int(cy // MERGE_CELL)), []).append((verts, tris))
        stats["seam_patches"] = len(pq)

    # Merge the ~8.5k tiny Frontline draws into few big surfaces (same shader, same 1536u cell, <= the engine's
    # SHADER_MAX_VERTEXES 2048 per surface): the draw-call count, not the triangle count, sank GL2 to ~36 fps.
    nmerged = 0
    for key in sorted(batches):
        cv, ci = [], []
        for verts, tris in batches[key]:
            if len(cv) + len(verts) > 2000 or len(ci) + 3 * len(tris) > 12000:
                B.add_soup(key[0], cv, ci)
                nmerged += 1
                cv, ci = [], []
            base = len(cv)
            cv.extend(verts)
            ci.extend(base + i for t in tris for i in t)
        if cv:
            B.add_soup(key[0], cv, ci)
            nmerged += 1
    stats["surfaces"] = nmerged

    # sky box (quads around the world, both windings) so the void renders as a MOHAA sky
    # [flfix2 bug-11058] the original's own sky box when its six faces are at hand (FL_SKY_DIR + the level's
    # "sky_faces" prefix; private captures, never shipped); otherwise the stock sky named in the level table
    _sf = None
    if not sky_shader and os.environ.get("FL_SKY_DIR") and flpack.spec(level).get("sky_faces"):
        _sf = sky_faces(os.environ["FL_SKY_DIR"], flpack.spec(level)["sky_faces"], mirror)
    if _sf:
        sky_shader = f"textures/fl/{level}/sky"
        for _suf, (_w, _h, _px) in _sf.items():
            files[f"env/fl_{level}_sky_{_suf}.tga"] = tga_bytes(_w, _h, _px)
        shader_lines.append(f"{sky_shader}\n{{\n\tsurfaceparm sky\n\tsurfaceparm noimpact\n\tsurfaceparm nolightmap\n"
                            f"\tskyParms env/fl_{level}_sky 512 -\n"
                            # the original's sky is never fogged: nofog is a stage word, so a stage that draws nothing carries it
                            f"\t{{\n\t\tmap $whiteimage\n\t\tblendFunc GL_ZERO GL_ONE\n\t\tnofog\n\t}}\n}}\n")
    stats["sky"] = sky_shader or flpack.spec(level).get("sky", "textures/sky/mohday1")
    sky = B.shader(sky_shader or flpack.spec(level).get("sky", "textures/sky/mohday1"), 0x4 | flbsp.SURF_NOLIGHTMAP, 0)
    blo = [max(min(s["bounds"][0][k] for s in B.surfaces) - 1024, -16300) for k in range(3)]
    bhi = [min(max(s["bounds"][1][k] for s in B.surfaces) + 1024 + 4096 * (k == 2), 16300) for k in range(3)]
    corners = [(x, y, z) for z in (blo[2], bhi[2]) for y in (blo[1], bhi[1]) for x in (blo[0], bhi[0])]
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        vs = [(corners[i], (0.0, 0.0), (0.0, 0.0, 1.0), (255, 255, 255, 255)) for i in q]
        if _sf:
            # planar faces, normal toward the level, as stock maps carry their sky
            _c = [sum(corners[i][k] for i in q) / 4.0 for k in range(3)]
            _m = [(blo[k] + bhi[k]) / 2.0 for k in range(3)]
            _ax = max(range(3), key=lambda k: abs(_m[k] - _c[k]))
            _n = [0.0, 0.0, 0.0]
            _n[_ax] = 1.0 if _m[_ax] > _c[_ax] else -1.0
            B.add_face(sky, vs, [0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2], _n)
            continue
        B.add_soup(sky, vs, [0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2])

    clip = B.shader("textures/common/fl_collision", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP, flbsp.CONTENTS_SOLID)
    nb = rejected = 0
    wound = []
    wtags = []
    volumes = 0
    idmap = {}                    # [flpolish] wound triangle -> (disc chunk, triangle index), for flsheets' keep list
    # [anvil] fl_levels "volume_mats": more volume-flagged materials that are not solid (1_3: material 18 = a
    # volume sheet across the health-135 alcove that the original's AI routes pass through; 1_1: none -> unchanged)
    XVOL_ = tuple(flpack.spec(level).get("volume_mats", ()))
    riverbed = []
    for name, vs, ts in coll:
        if os.environ.get("FL_COLL_ONLY") and os.environ["FL_COLL_ONLY"] not in name:
            continue
        P = [X(v) for v in vs]
        for ti_, (a, b, c, f) in enumerate(ts):
            if coll_is_volume(f) or ((f & COLL_VOLUME) and (f & 0x7FF) in XVOL_):
                volumes += 1
                if (f & 0x7FF) == 15:
                    # [flpolish] the river: no walkable surface, but a bed 160u under it so a player who falls in
                    # lands (the mission script drowns him there, fl_water) instead of falling out of the world
                    a2, b2, c2 = wind(a, b, c, flip_coll)
                    riverbed.append(tuple((q[0], q[1], q[2] - 160.0) for q in (P[a2], P[b2], P[c2])))
                continue
            a2, b2, c2 = wind(a, b, c, flip_coll)
            wound.append((P[a2], P[b2], P[c2]))
            wtags.append(f)
            idmap[wound[-1]] = (name, ti_)
    stats["coll_volumes_dropped"] = volumes
    wound += riverbed
    wtags += [TAG_RIVERBED] * len(riverbed)
    stats["riverbed_tris"] = len(riverbed)
    # invisible blocker columns (trees, posts) shrunk to what is drawn inside them (flfit.py)
    colboxes = []
    rtris = [(X(m["verts"][a]), X(m["verts"][b]), X(m["verts"][c])) for m in meshes if m["tris"]
             and (m["cell"], m["draw"]) not in hidden for a, b, c in m["tris"]]
    # [anvil] the player-only wrap material: 3 on 1_1, 1 on 1_3 (1012 tris of material 1 + special; its m3 has no
    # special bit). fl_levels "wrap_mat", default 3 = 1_1 unchanged; flfit's column pass reads the same material
    WRAP_MAT = int(os.environ.get("FL_WRAP_MAT") or flpack.spec(level).get("wrap_mat", 3))   # env: dev baseline only
    flfit.MAT_SPECIAL = WRAP_MAT
    if not os.environ.get("FL_NO_FIT"):
        # the floor under a column, measured WITHOUT the special-surface boxes themselves (their inner faces read as
        # floors and floated the fitted box ~50u up: a crawl-height slab under the tree)
        g_nm = flgeom.TriGrid([t for t, f in zip(wound, wtags) if (f & 0x7FF) != flfit.MAT_SPECIAL])
        wound, wtags, colboxes, stats["columns"] = flfit.fit_columns(
            wound, wtags, rtris, lambda x, y, zt, zb: g_nm.ground(x, y, zt - 4, zb))
    # [flpolish] blocked only by what you can see (flsheets.py): Frontline's floating player-clip sheets are dropped
    # (all but the reviewed level-boundary ones, fl_levels.json "clip_keep") and the drawn geometry they stood in front
    # of gets collision of its own
    if not os.environ.get("FL_NO_SHEETS"):
        wound, wtags, drawn_coll, stats["sheets"] = flsheets.replace(
            wound, wtags, [idmap.get(t) for t in wound], lambda f: (f & 0x7FF) == WRAP_MAT and bool(f & COLL_SPECIAL),
            rtris, keep=flpack.spec(level).get("clip_keep", []))
        # the original's AI routes stay open (flroutes.py): no drawn-geometry collision across them, and the gaps the
        # original's narrower body walks through are cut wide enough for MOHAA's box (collision only)
        route_segs = flroutes.routes([X(n_["pos"]) for n_ in L.navpoints()], flgeom.TriGrid(wound))
        drawn_coll, stats["sheets"]["drawn_kept_off_routes"] = flroutes.keep_drawn(drawn_coll, route_segs)
        wound += drawn_coll
        wtags += [TAG_DRAWN] * len(drawn_coll)
        wound, wtags, stats["routes"] = flroutes.carve(
            wound, wtags, route_segs, keep=lambda f: (f & 0x7FF) == WRAP_MAT and bool(f & COLL_SPECIAL) and f < TAG_CLIFF,
            dense=flpack.spec_xy(level, X, "route_widen"))
        # ...and the sheets that stay (the level's boundaries where nothing is drawn) get a VISIBLE edge: a barbed-wire
        # fence along their foot (MOHAA's own textures/mohcommon/barbwire from the player's install)
        gk_ = flgeom.TriGrid([t for t, f in zip(wound, wtags) if f != TAG_RIVERBED])   # fences stand on land, not the canal bed
        wire = B.shader("textures/mohcommon/barbwire", 0, 0)
        nfe = 0
        # user 2026-11-11: invisible walls are fine where the original had them; no fence the original did not draw
        kept_ = stats["sheets"].pop("kept_tris")
        for (x0, y0, z0), (x1, y1, z1) in (flsheets.edges(kept_, gk_.ground, drawn=flgeom.TriGrid(rtris, cell=128.0))
                                           if flpack.spec(level).get("boundary_wire") else []):
            L_ = math.hypot(x1 - x0, y1 - y0)
            q = [((x0, y0, z0), (0.0, 1.0)), ((x1, y1, z1), (L_ / 64.0, 1.0)),
                 ((x1, y1, z1 + 64.0), (L_ / 64.0, 0.0)), ((x0, y0, z0 + 64.0), (0.0, 0.0))]
            B.add_soup(wire, [(pp, st, (0.0, 0.0, 1.0), med_light + (255,)) for pp, st in q], [0, 1, 2, 0, 2, 3])
            nfe += 1
        stats["sheets"]["visible_edges"] = nfe
    # headroom: crawl holes / doorways sized for Frontline's smaller player get MOHAA crouch / stand clearance
    # (flclear.py; collision only, the drawn walls are untouched)
    caps = []
    if not os.environ.get("FL_NO_CLEAR"):
        wound, caps, hr = flclear.normalise(wound, flpack.spec(level).get("headroom"), wtags, rtris)
        wtags = hr.pop("tags")
        stats["headroom"] = hr
    # lips 19-34u high get walkable clip ramps (flclear.ledge_ramps): Frontline steps over them, MOHAA (18) did not
    # OFF by default (fl_levels.json "ramps": true opts in): measured on 1_1 they let the walk audit climb onto wall tops
    # and out of the world (void falls 7 -> 239) while removing 5 of 146 route blocks
    if flpack.spec(level).get("ramps") and not os.environ.get("FL_NO_RAMPS"):
        rp, stats["ramps"] = flclear.ledge_ramps(wound, flpack.spec(level).get("headroom"))
        wound += rp
        wtags += [TAG_RAMP] * len(rp)
    # the edges of the world: a clip wall wherever a walkable floor ends over nothing (flcliff.py)
    if not os.environ.get("FL_NO_CLIFF"):
        # against the collision AS BUILT (skins dropped, headroom carved), not the disc's: a dropped player-clip sheet
        # still read as 'a wall already stands here' and the edge got no clip (walk audit: void falls 7 -> 25)
        # the canal bed does not count as ground past an edge: the quays keep their edge (Frontline's player never
        # entered the water either); the bed only catches someone who gets in anyway
        cw, stats["cliffs"] = flcliff.walls(wound, flgeom.TriGrid([t for t, f in zip(wound, wtags) if f != TAG_RIVERBED]))
        wound += cw
        wtags += [TAG_CLIFF] * len(cw)
        pw, stats["parapets"] = flcliff.parapets(wound, flgeom.TriGrid([t for t, f in zip(wound, wtags) if f != TAG_RIVERBED]))
        wound += pw
        wtags += [TAG_CLIFF] * len(pw)
        # [flpolish] ...and a DRAWN skirt under the same edge: the floor's own texture and light carried 512u straight
        # down, so a player at the edge sees a quay wall / bank instead of the white void under the level (visaudit:
        # 287 rays into the void along the town's west edge; user: "floors open and expose the underside of the map")
        rt_sh = []
        for m in meshes:
            if not m["tris"] or (m["cell"], m["draw"]) in hidden or not m["tex"]:
                continue
            P_ = [X(v) for v in m["verts"]]
            for a, b, c in m["tris"]:
                n_ = face_normal(P_[a], P_[b], P_[c])
                if n_ is None or abs(n_[2]) < 0.7:
                    continue
                col = tuple(sum(m["cols"][i][k] for i in (a, b, c)) // 3 for k in range(3))
                rt_sh.append((((P_[a][0] + P_[b][0] + P_[c][0]) / 3, (P_[a][1] + P_[b][1] + P_[c][1]) / 3,
                               (P_[a][2] + P_[b][2] + P_[c][2]) / 3), m["tex"], col))
        rgrid = {}
        for cen, tex, col in rt_sh:
            rgrid.setdefault((int(cen[0] // 64), int(cen[1] // 64)), []).append((cen, tex, col))
        nsk = 0
        for k_ in range(0, len(cw), 2):
            a_, b_ = cw[k_][0], cw[k_][1]           # the wall's bottom edge = the floor edge (minus 8)
            mx, my, mz = (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2, (a_[2] + b_[2]) / 2 + 8
            best = None
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for cen, tex, col in rgrid.get((int(mx // 64) + dx, int(my // 64) + dy), ()):
                        d2 = (cen[0] - mx) ** 2 + (cen[1] - my) ** 2 + 4 * (cen[2] - mz) ** 2
                        if d2 < 96 * 96 and (best is None or d2 < best[0]):
                            best = (d2, tex, col)
            if best is None:
                continue
            sh_ = tex_shader(best[1])
            L_ = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
            top_a, top_b = a_[2] + 7, b_[2] + 7
            vs_ = [((a_[0], a_[1], top_a), (0.0, 0.0), (0.0, 0.0, 1.0), best[2] + (255,)),
                   ((b_[0], b_[1], top_b), (L_ / 128.0, 0.0), (0.0, 0.0, 1.0), best[2] + (255,)),
                   ((b_[0], b_[1], top_b - 512), (L_ / 128.0, 4.0), (0.0, 0.0, 1.0), best[2] + (255,)),
                   ((a_[0], a_[1], top_a - 512), (0.0, 4.0), (0.0, 0.0, 1.0), best[2] + (255,))]
            B.add_soup(sh_, vs_, [0, 1, 2, 0, 2, 3])
            nsk += 1
        stats["skirts"] = nsk
        # ...and a drawn GROUND under the whole level, 512u under its lowest floor, in the level's most used floor
        # texture at the level's median light: a look over the edge of the world, or through a gap in a floor, lands
        # on ground instead of the white void (Frontline draws nothing there; its own player never stood at those edges)
        if rt_sh:
            cnt = {}
            for _cen, tex, _col in rt_sh:
                cnt[tex] = cnt.get(tex, 0) + 1
            gtex = max(sorted(cnt), key=lambda t: cnt[t])
            gz = min(c[2] for c, _t, _c in rt_sh) - 512.0
            gx0, gy0 = [min(c[k] for c, _t, _c in rt_sh) - 4096 for k in (0, 1)]
            gx1, gy1 = [max(c[k] for c, _t, _c in rt_sh) + 4096 for k in (0, 1)]
            gx0, gy0, gx1, gy1 = max(gx0, -15800), max(gy0, -15800), min(gx1, 15800), min(gy1, 15800)
            gcol = tuple(int(v * 0.7) for v in med_light) + (255,)
            gsh = tex_shader(gtex)
            T = 2048.0
            ng = 0
            yy = gy0
            while yy < gy1:
                xx = gx0
                while xx < gx1:
                    x2, y2 = min(xx + T, gx1), min(yy + T, gy1)
                    q = [((xx, yy, gz), (xx / 128.0, yy / 128.0)), ((x2, yy, gz), (x2 / 128.0, yy / 128.0)),
                         ((x2, y2, gz), (x2 / 128.0, y2 / 128.0)), ((xx, y2, gz), (xx / 128.0, y2 / 128.0))]
                    B.add_soup(gsh, [(pp, st, (0.0, 0.0, 1.0), gcol) for pp, st in q], [0, 1, 2, 0, 2, 3])
                    ng += 1
                    xx += T
                yy += T
            stats["under_ground_tiles"] = ng
        # [flfix2 bug-11115] floorless pockets (Frontline houses are shells with no ground floor): through a window the
        # original shows its sky box there, one flat dark colour below the horizon; our skirt + under-ground fill
        # read as "under the map" (user, the window by the jeep road). A render-only lid in that colour closes each
        # pocket that drawn walls cut off from the outside (flpit.py); the level's edges keep their skirt and ground.
        pl_ = flpack.spec(level).get("pit_lid")
        if pl_ and not os.environ.get("FL_NO_PITLID"):
            ptris = []
            for m in meshes:
                if not m["tris"] or (m["cell"], m["draw"]) in hidden:
                    continue
                P_ = [X(v) for v in m["verts"]]
                ptris += [(P_[a], P_[b], P_[c]) for a, b, c in m["tris"]]
            rects_, stats["pit_lids"] = flpit.lids(ptris)
            lname = tdir + "pit_lid"
            shader_lines.append(lname + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm nomarks\n\tcull none\n\t{\n\t\tmap $whiteimage\n"
                                "\t\trgbGen vertex\n\t}\n}\n")
            lsh = B.shader(lname, flbsp.SURF_NOLIGHTMAP, 0)
            lcol = tuple(int(v) for v in pl_["rgb"]) + (255,)
            for zl, ax, ay, bx, by in rects_:
                q = [((ax, ay, zl), (0.0, 0.0)), ((bx, ay, zl), (1.0, 0.0)), ((bx, by, zl), (1.0, 1.0)), ((ax, by, zl), (0.0, 1.0))]
                B.add_soup(lsh, [(pp, st, (0.0, 0.0, 1.0), lcol) for pp, st in q], [0, 1, 2, 0, 2, 3])
    # [flpolish] each collision brush carries its SOURCE in its (nodraw) shader name, so the walk audit can tell an
    # original player-clip boundary from a wall, a fitted column, a headroom cap or our edge-of-world clip
    def clip_for(tag):
        if tag == TAG_CLIFF:
            nm = "cliff"
        elif tag == TAG_RAMP:
            nm = "ramp"
        elif tag == TAG_DRAWN:
            nm = "drawn"
        elif tag == TAG_RIVERBED:
            nm = "riverbed"
        else:
            nm = "m%d%s%s" % (tag & 0x7FF, "s" if tag & COLL_SPECIAL else "", "v" if tag & COLL_VOLUME else "")
        # [flfix2 round 19, bug-11164] the canal bed is a puddle surface: a round that goes through the water lands on
        # it and the cgame picked its impact by surface type - none = the stone puff and chips (seen through the water)
        sf_ = SURF_PUDDLE if tag == TAG_RIVERBED else 0
        return B.shader("textures/common/fl_coll_" + nm, flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP | sf_, flbsp.CONTENTS_SOLID)
    for (a2, b2, c2), tg in zip(wound, wtags):
        if B.add_prism(clip_for(tg), a2, b2, c2, thickness=float(os.environ.get("FL_THICK", "4")), centered=True) is None:
            rejected += 1
        else:
            nb += 1
    # [flfix2] the water itself: a CONTENTS_WATER volume from the river's surface (material 15) down to its bed, so
    # the engine knows a player is in water (splash, wading, the underwater view) before the script drowns him
    nwv = 0
    if WATER_SHADER:
        # [flfix2 round 19, bug-11164] as stock water (surfaceparm water + trans): CONTENTS_WATER | CONTENTS_TRANSLUCENT,
        # and the puddle surface type on its sides, so every impact the engine resolves on it is the water splash/sound
        wsh = B.shader("textures/common/fl_water_vol", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP | SURF_PUDDLE,
                       CONTENTS_WATER | CONTENTS_TRANSLUCENT)
        for (a2, b2, c2), tg in zip(wound, wtags):
            if tg != TAG_RIVERBED:
                continue
            a3, b3, c3 = [(q[0], q[1], q[2] + 160.0) for q in (a2, b2, c2)]
            ux, uy = b3[0] - a3[0], b3[1] - a3[1]
            vx, vy = c3[0] - a3[0], c3[1] - a3[1]
            if ux * vy - uy * vx < 0:
                b3, c3 = c3, b3                       # normal up: the slab lies under the surface
            if B.add_prism(wsh, a3, b3, c3, thickness=157.0, centered=False) is not None:
                nwv += 1
    stats["water_volume_brushes"] = nwv
    for lo_, hi_ in caps:
        B.add_brush_planes(B.shader("textures/common/fl_coll_cap", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP,
                                    flbsp.CONTENTS_SOLID), [], lo_, hi_)
        nb += 1
    for lo_, hi_ in colboxes:
        B.add_brush_planes(B.shader("textures/common/fl_coll_column", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP,
                                    flbsp.CONTENTS_SOLID), [], lo_, hi_)
        nb += 1
    if os.environ.get("FL_DEBUGCOLL"):
        # QA aid (never shipped): draw every collision triangle, tinted by its Frontline material, so screenshots show
        # where collision is and what kind it is (red = material 3 / special, cyan = caps excluded)
        pal = {3: (255, 40, 40), 13: (255, 255, 0), 15: (0, 120, 255), 2047: (255, 140, 0)}
        dbg = {}
        for t, f in zip(wound, wtags):
            m = f & 0x7FF
            col = pal.get(m, (60, 255, 60))
            nm = tdir + "dbgcoll_%d" % m
            if nm not in tex_names:
                files[nm + ".tga"] = tga_bytes(4, 4, bytes(col + (255,)) * 16)
                shader_lines.append(nm + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tcull none\n\t{\n\t\tmap " + nm
                                    + ".tga\n\t\tblendFunc add\n\t\trgbGen identity\n\t}\n}\n")
                tex_names[nm] = B.shader(nm, flbsp.SURF_NOLIGHTMAP, 0)
            key_ = (tex_names[nm], int(t[0][0] // MERGE_CELL), int(t[0][1] // MERGE_CELL))
            bk = dbg.setdefault(key_, [])
            if len(bk) >= 1998:
                B.add_soup(key_[0], list(bk), list(range(len(bk))))
                bk.clear()
            bk.extend((p, (0.0, 0.0), (0.0, 0.0, 1.0), (255, 255, 255, 255)) for p in t)
        for key_, bk in sorted(dbg.items()):
            if bk:
                B.add_soup(key_[0], list(bk), list(range(len(bk))))

    # [flpolish] Frontline's own OBJECT MESHES (.msh: the door, the falling house chunks, the jeep's wheels, the
    # planes, bombs, rockets, the U-boat) as inline brush models, each in its own local frame, so the mission script
    # moves them by origin/angles (script_object $fl_om<k>). Which mesh goes where is fl_levels.json ("set_pieces"
    # entries with "mesh", and "object_meshes" for the ones that stand on a record); converted on the player's PC.
    om_ents = []
    cover_obst = []
    # local frame mirrored in y like the world; flscene.raw_angles conjugates the rotations to match
    Xr = lambda q: (q[0] * X.s, q[1] * X.s * X.m, q[2] * X.s)          # noqa: E731 - local frame: no recentre
    recs_ = {e.get("i"): e for e in L.entities()}
    om_specs = []
    for k_, spc in enumerate(flpack.spec(level).get("set_pieces", []), 1):
        if spc.get("mesh"):
            om_specs.append(("sp%d" % k_, spc, None))
    for spc in flpack.spec(level).get("object_meshes", []):
        if spc.get("class"):
            # one per record of that class, numbered in record order (the order of the script's level.fl_list)
            n_ = 0
            for e_ in L.entities():
                if spc["class"] in e_["strs"]:
                    n_ += 1
                    om_specs.append(("%s%d" % (spc["name"], n_), spc, e_))
            continue
        om_specs.append((spc["name"], spc, recs_.get(spc.get("object"))))
    nom = 0
    for tag_, spc, rec_ in om_specs:
        draws = L.mesh(spc["mesh"])
        if not draws:
            continue
        surf_ids = []
        lo_ = [1e9] * 3
        hi_ = [-1e9] * 3
        for m in draws:
            if not m["tris"]:
                continue
            P = [Xr(v) for v in m["verts"]]
            tris = [wind(a, b, c, flip_render) for a, b, c in m["tris"]]
            acc = [[0.0, 0.0, 0.0] for _ in P]
            for a, b, c in tris:
                n = face_normal(P[a], P[b], P[c])
                if n:
                    for i in (a, b, c):
                        acc[i][0] += n[0]; acc[i][1] += n[1]; acc[i][2] += n[2]
            verts = []
            for i, p_ in enumerate(P):
                l_ = math.sqrt(sum(x * x for x in acc[i])) or 1.0
                r_, g_, b_, a_ = m["cols"][i]
                # object meshes carry PS2-range vertex colour (0x80 = full): doubled, or they render near black
                r_, g_, b_ = (min(255, 2 * c_) for c_ in (r_, g_, b_))
                verts.append((p_, m["uvs"][i], tuple(x / l_ for x in acc[i]), (r_, g_, b_, 255)))
                for q in range(3):
                    lo_[q] = min(lo_[q], p_[q])
                    hi_[q] = max(hi_[q], p_[q])
            surf_ids.append(B.add_soup(tex_shader(m["tex"]), verts, [i for t in tris for i in t]))
        if not surf_ids:
            continue
        brushes_ = []
        if spc.get("solid"):
            # the door blocks while it is shut: one box on its own bounds (moves with it)
            brushes_.append(B.add_brush_planes(clip, [], lo_, hi_))
        for b0_, b1_ in spc.get("boxes", []):
            # explicit clip boxes in the mesh's own frame, disc metres (the standing ends of the breached wall)
            c0_, c1_ = Xr(b0_), Xr(b1_)
            brushes_.append(B.add_brush_planes(clip, [], [min(c0_[q], c1_[q]) for q in range(3)],
                                               [max(c0_[q], c1_[q]) for q in range(3)]))
        B.models.append({"surfaces": surf_ids, "brushes": brushes_})
        nom += 1
        kv = [("classname", "script_object"), ("model", "*%d" % len(B.models)), ("targetname", "fl_om_" + tag_)]
        if rec_ is not None:
            o_ = X(rec_["pos"])
            a_ = flscene.raw_angles(struct.unpack("<4f", struct.pack("<4I", *flscene.words(rec_)[7:11])), X.m < 0)
            kv += [("origin", "%.1f %.1f %.1f" % o_), ("angles", "%.1f %.1f %.1f" % a_)]
        om_ents.append(kv)
        if rec_ is not None and spc.get("solid"):
            # [flfix2 round 21] a solid prop on a record (the crates): flcover keeps the cover nodes out of its box
            cover_obst.append({"name": tag_, "pos": o_, "yaw": a_[1], "lo": lo_, "hi": hi_,
                               "tag": flscene.words(rec_)[14] if len(flscene.words(rec_)) > 14 else 0})
    stats["object_meshes"] = nom

    # ---- entities ----
    ents = L.entities()
    player = next((e for e in ents if "Player" in e["strs"]), None)
    sp = flpack.spec(level)
    ws = [("classname", "worldspawn"), ("message", f"Frontline {level} (converted locally, converter {CONVERTER_VERSION})"),
          ("farplane", "0" if os.environ.get("FL_DEBUGCOLOR") else str(os.environ.get("FL_FARPLANE") or sp.get("farplane", 12000))), ("farplane_color", sp.get("farplane_color", "0.55 0.6 0.65")),
          # [flfix2 bug-11058] fog start (the engine takes 18% of the far plane when this is 0)
          ("farplane_bias", str(sp.get("farplane_bias", 0))),
          # [flfix2 bug-11058] with the far plane as a cull plane the sky hull (further off than the fog end) is never
          # drawn and the void shows the fog colour; the level table can switch the culling off (fog only)
          ("farplane_cull", str(sp.get("farplane_cull", 1))),
          ("ambientlight", os.environ.get("FL_AMBIENT") or str(sp.get("ambientlight", "40 40 40"))),
          # [flpolish] engine extensions this map opts into (HZM engine >= 1.10.73; older engines ignore the keys):
          # entity coordinates past +-8192 (the jeep's start behind the gate) and Frontline's own step height (its body
          # walks over the 19-34u lips and kerbs MOHAA's 18u step snags on). server/sv_init.c reads both.
          ("hzm_widecoords", "1"), ("hzm_stepsize", str(sp.get("step_height", FL_STEP)))]
    # [anvil] fl_levels "nav_spacing" (default 64 = 1_1 unchanged): 1_3 has 5380 navpoints, and the engine stops the map
    # at more than MAX_PATHNODES 4096 (navigate.h) path + cover nodes ("Exceeded MAX_PATHNODES", server crash, bug-11264)
    NAV_SP = float(sp.get("nav_spacing", 64))
    kept = []
    for n in L.navpoints():
        p = X(n["pos"])
        # Frontline packs navpoints tighter than MOHAA's PathSearch accepts ("Duplicate node ... not linked")
        if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < NAV_SP * NAV_SP and abs(p[2] - q[2]) < 48 for q in kept):
            continue
        kept.append(p)
    # [flfix2 round 21] the disc's AI cover points as MOHAA cover nodes (flcover.py has the decode and the flag mapping);
    # the same list goes into the data script (flpack: level.fl_cov_*). FL_NO_COVER=1 leaves the nodes out. Counted
    # before the stamp below, so a build with other cover nodes gets a new map_time (the engine rebuilds the .pth).
    import flcover
    acts_ = [(X(e_["pos"]), flscene.team(e_), (flscene.ids(e_) or [0])[0]) for e_ in L.entities() if flscene.kind(e_) == 3]
    L.cover = flcover.points(L, X, grid, cover_obst, acts_, B, float(sp.get("step_height", FL_STEP)))
    taken_ = {(int(f"{q[0]:.0f}"), int(f"{q[1]:.0f}")) for q in kept}
    nav_ = [(q[0], q[1], flcover.floor_at(grid, q[0], q[1], q[2]) or q[2]) for q in kept]
    cnodes_ = [] if os.environ.get("FL_NO_COVER") else flcover.nodes(L.cover, taken_, nav_)
    stats["cover_points"] = len(L.cover)
    stats["cover_nodes"] = len(cnodes_)
    if len(kept) + len(cnodes_) > 4000:   # [anvil bug-11264] MAX_PATHNODES 4096 less headroom
        print("WARNING: %d path + %d cover nodes - over the engine limit, raise nav_spacing" % (len(kept), len(cnodes_)))
    print("pathnodes %d + cover %d" % (len(kept), len(cnodes_)))
    # [flfix2] bug-10969: the engine keeps the AI path graph it builds for a map in <home>/maps/<map>.pth and reuses it
    # while the BSP's map_time matches (navigate.cpp ArchiveLoadNodes). We wrote none, so every conversion matched every
    # other: the graph of the FIRST conversion was used for all later ones (soldiers that stand still, 'couldn't find
    # end node'). A stamp that changes with the converter and with what it built makes the engine rebuild it once.
    import zlib
    ws.append(("map_time", "hzm-%s-%d-%08x" % (CONVERTER_VERSION, flpack.CONV_BUILD, zlib.crc32(repr(sorted(
        (k, v) for k, v in stats.items() if isinstance(v, int))).encode()) & 0xffffffff)))
    B.entity(ws)
    for kv in om_ents:
        B.entity(kv)
    for p in kept:
        B.entity([("classname", "info_pathnode"), ("origin", f"{p[0]:.0f} {p[1]:.0f} {p[2] + 16:.0f}")])
    for x_, y_, z_, c_ in cnodes_:
        B.entity([("classname", "info_pathnode"), ("origin", f"{x_} {y_} {z_ + 16:.0f}"),
                  ("angle", f"{c_['node_yaw']:.0f}"), ("spawnflags", str(c_["flags"]))])

    # spawn points on Frontline's own navpoints (they are known-walkable): the 8 nearest the player start
    # for the allies/coop start and the 8 nearest the far end for axis - one shared point jams 8 bodies
    def nearest(o, k):
        return sorted(kept, key=lambda q: ((q[0] - o[0]) ** 2 + (q[1] - o[1]) ** 2, q))[:k]
    if player and kept:
        ps = X(player["pos"])
        far = max(kept, key=lambda q: (q[0] - ps[0]) ** 2 + (q[1] - ps[1]) ** 2)
        for i, q in enumerate(nearest(ps, 8)):
            yaw = math.degrees(math.atan2(-q[1], -q[0])) % 360
            for cls in (("info_player_start",) if i == 0 else ()) + ("info_player_deathmatch", "info_player_allied"):
                B.entity([("classname", cls), ("origin", f"{q[0]:.0f} {q[1]:.0f} {q[2] + 40:.0f}"), ("angle", f"{yaw:.0f}")])
        for q in nearest(far, 8):
            yaw = math.degrees(math.atan2(-q[1], -q[0])) % 360
            B.entity([("classname", "info_player_axis"), ("origin", f"{q[0]:.0f} {q[1]:.0f} {q[2] + 40:.0f}"), ("angle", f"{yaw:.0f}")])

    import flvis
    B.vis_occluders = flvis.occluders([(X(vs[a]), X(vs[b]), X(vs[c])) for _, vs, ts in coll for a, b, c, _f in ts
                                       if not coll_is_volume(_f)])
    bsp_path = out_pk3 + ".bsp.tmp"
    info = B.write(bsp_path)
    with open(bsp_path, "rb") as f:
        files[f"maps/{mapname}.bsp"] = f.read()
    os.remove(bsp_path)
    files[f"scripts/fl_{level}.shader"] = "".join(shader_lines).encode()
    # [flchar] the disc's own characters as MOHAA models (flchar.py, user approval 2026-11-15); the mission script
    # uses one only once its sheet passed QA (level.fl_chr_own). Never fails the conversion.
    import flchar
    try:
        chr_lines = flchar.build(L, level, mohaa_base, files)
    except Exception as e_:
        chr_lines = []
        print("flchar: characters skipped (%s)" % e_)
    pack = flpack.build(L.disc, L, level, X, vgm, files, mohaa_base=mohaa_base, grid=grid,
                        extra_lines=chr_lines) if vgm else None
    # [flfix2] tier-1 textures (TEXTURES.md, approved 2026-11-11): CC0 ground / roof / plank / stone, cut-out upscale
    import flhd
    hd_rep = flhd.apply(files, level, flpack.spec(level), mapname)

    os.makedirs(os.path.dirname(os.path.abspath(out_pk3)), exist_ok=True)
    with zipfile.ZipFile(out_pk3, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in sorted(files):
            zi = zipfile.ZipInfo(name, ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, files[name])
    sha = hashlib.sha256(open(out_pk3, "rb").read()).hexdigest()
    rep = {"level": level, "map": mapname, "converter": CONVERTER_VERSION, "scale": scale, "mirror": mirror,
           "flip_render": flip_render, "flip_collision": flip_coll,
           "votes": {"collision_up_down": [up, down], "render_up_down": [rup, rdown]},
           "brushes": nb, "prism_rejected": rejected, "bsp": info, "vis": getattr(B, "vis_stats", None), "stats": stats,
           "textured_pct": round(100.0 * stats["tris_textured"] / max(1, stats["tris"]), 2),
           "pk3": os.path.basename(out_pk3), "sha256": sha, "seconds": round(time.time() - t0, 1),
           "player_start": X(player["pos"]) if player else None, "offset_m": offset, "pack": pack}
    if debug_ids:
        rep["debug_ids"] = {"%d,%d,%d" % k: v for k, v in debug_ids.items()}
    if report:
        with open(report, "w") as f:
            json.dump(rep, f, indent=1, default=str)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("level")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=48.0)
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--flip-render", dest="flip_render", action="store_const", const=True, default=None)
    ap.add_argument("--flip-collision", dest="flip_coll", action="store_const", const=True, default=None)
    ap.add_argument("--report")
    ap.add_argument("--vgmstream")
    ap.add_argument("--mohaa", help="the MOHAA install (basepath) - read for the alias bridge")
    a = ap.parse_args()
    r = convert(a.image, a.level, a.out, a.scale, a.mirror, a.flip_render, a.flip_coll, a.report,
                vgm=a.vgmstream, mohaa_base=a.mohaa)
    print(json.dumps({k: r[k] for k in ("map", "brushes", "prism_rejected", "textured_pct", "seconds", "sha256", "votes",
                                        "flip_render", "flip_collision", "pack")}, default=str))

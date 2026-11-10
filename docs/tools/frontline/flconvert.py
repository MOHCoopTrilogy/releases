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
import flclear  # noqa: E402
import flfit  # noqa: E402
import flcliff  # noqa: E402

CONVERTER_VERSION = "0.3.0"

# Frontline .cdb collision flag word (flcore.collision, decoded 2026-11-10 against the level's own AI nav graph):
#   bits 0-10 surface material, bit 23 special surface, bit 22 VOLUME. Material 14 + bit 22 = 450u-tall boxes standing
#   on trigger spots (the crawl hole into the town, the interrogation room): the original's AI navpoint links run
#   straight through them, so they never blocked a character. Converted as solid they were the invisible walls of the
#   user's playtest ("a lot of invisible walls everywhere, blocking progression"). Material 15 + bit 22 is the
#   river's surface and stays.
COLL_VOLUME = 1 << 22
COLL_MAT_VOLUME = (14,)


def coll_is_volume(f):
    return bool(f & COLL_VOLUME) and (f & 0x7FF) in COLL_MAT_VOLUME
MERGE_CELL = 1536.0
ZIP_TIME = (2002, 5, 28, 0, 0, 0)   # fixed timestamp for deterministic zips


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

    def upgrade_ok(up):
        """only when the player's own install carries the pak that holds the texture"""
        if not mohaa_base:
            return False
        for game in ("maintt", "mainta", "main"):
            pk = os.path.join(mohaa_base, game, up["pak"])
            if os.path.exists(pk):
                try:
                    return up["path"] in zipfile.ZipFile(pk).namelist()
                except Exception:
                    return False
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
        fl = [fmean(t["rgba"][c::4]) for c in range(3)]
        for game in ("maintt", "mainta", "main"):
            pk = os.path.join(mohaa_base, game, up["pak"])
            if os.path.exists(pk):
                try:
                    from PIL import Image
                    im = Image.open(_io.BytesIO(zipfile.ZipFile(pk).read(up["path"]))).convert("RGB").resize((64, 64))
                    px = im.tobytes()
                    hd = [fmean(px[c::3]) for c in range(3)]
                    return tuple(max(0.3, min(1.2, round(f / max(1.0, h), 3))) for f, h in zip(fl, hd))
                except Exception:
                    return None
        return None

    debug_ids = {}

    def tex_shader(key):
        if key in tex_names:
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
        name = tdir + short
        up = texmap.get(short)
        if up and upgrade_ok(up):
            # upgrade to a texture the mod already ships (fl_texmap.json); Frontline's vertex light stays on top
            sc = up.get("tc_scale", 1.0)
            tcm = ("\t\ttcMod scale %g %g\n" % (sc, sc)) if sc != 1.0 else ""
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tcull none\n\t{\n\t\tmap " + up["path"] + "\n"
                                + tcm + "\t\trgbGen vertex\n\t}\n}\n")
            stats["upgraded"] = stats.get("upgraded", 0) + 1
            if up.get("grade", True):
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
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tcull none\n\t{\n\t\tmap "
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

    def short_key(key):
        return str(key).replace(f"{level}_ART", "").replace(".cpt", "").replace("@", "_").strip("_")

    def reskin_shader(rk):
        name = tdir + rk["shader"]
        if name not in tex_names:
            shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\tnopicmip\n\t{{\n\t\tmap {rk['image']}\n"
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
            verts.append((p, (u, v), tuple(x / l for x in acc[i]), (r, g, b, va if m["tex"] in vtx_alpha else 255)))
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
                if not n or abs(n[2]) > 0.5:
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
            for a, b, c in tris:
                T = [verts[a], verts[b], verts[c]]
                n = face_normal(T[0][0], T[1][0], T[2][0])
                if not n or abs(n[2]) > 0.5:
                    continue                          # only the vertical faces of the block
                z0, z1 = planes_[planes_[("t", a, b, c)]]
                if z1 - z0 < 4:
                    continue
                hl = math.hypot(n[0], n[1]) or 1.0
                tx, ty = -n[1] / hl, n[0] / hl
                ztop = z0 + (z1 - z0) * (1.0 + float(rk.get("overshoot", 0.25)))
                base = len(nv)
                for q in T:
                    p = q[0]
                    # the wall's top-quarter vertices rise by the crown FROM THEIR OWN HEIGHT: Frontline's bumpy hedge
                    # profile is kept and the image's alpha crown sits on it (v1/v2 flattened the tops)
                    pz = p[2] + (ztop - z1) if p[2] >= z0 + (z1 - z0) * 0.75 else p[2]
                    uu = (p[0] * tx + p[1] * ty) / float(rk.get("tile", 128))
                    vv = (ztop - pz) / max(1.0, ztop - z0)
                    cr, cg, cb = (min(255, int(round(q[3][k] * gk[k]))) for k in range(3))
                    nv.append(((p[0], p[1], pz), (uu, vv), q[2], (cr, cg, cb, 255)))
                nt.append((base, base + 1, base + 2))
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
        pq = flseam.patches(draws + br, flpack.spec(level).get("patches", []), lambda i: B.shaders[i][0])
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
    sky = B.shader(sky_shader or flpack.spec(level).get("sky", "textures/sky/mohday1"), 0x4 | flbsp.SURF_NOLIGHTMAP, 0)
    blo = [max(min(s["bounds"][0][k] for s in B.surfaces) - 1024, -16300) for k in range(3)]
    bhi = [min(max(s["bounds"][1][k] for s in B.surfaces) + 1024 + 4096 * (k == 2), 16300) for k in range(3)]
    corners = [(x, y, z) for z in (blo[2], bhi[2]) for y in (blo[1], bhi[1]) for x in (blo[0], bhi[0])]
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        vs = [(corners[i], (0.0, 0.0), (0.0, 0.0, 1.0), (255, 255, 255, 255)) for i in q]
        B.add_soup(sky, vs, [0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2])

    clip = B.shader("textures/common/fl_collision", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP, flbsp.CONTENTS_SOLID)
    nb = rejected = 0
    wound = []
    wtags = []
    volumes = 0
    for name, vs, ts in coll:
        if os.environ.get("FL_COLL_ONLY") and os.environ["FL_COLL_ONLY"] not in name:
            continue
        P = [X(v) for v in vs]
        for a, b, c, f in ts:
            if coll_is_volume(f):
                volumes += 1
                continue
            a2, b2, c2 = wind(a, b, c, flip_coll)
            wound.append((P[a2], P[b2], P[c2]))
            wtags.append(f)
    stats["coll_volumes_dropped"] = volumes
    # invisible blocker columns (trees, posts) shrunk to what is drawn inside them (flfit.py)
    colboxes = []
    rtris = [(X(m["verts"][a]), X(m["verts"][b]), X(m["verts"][c])) for m in meshes if m["tris"]
             and (m["cell"], m["draw"]) not in hidden for a, b, c in m["tris"]]
    if not os.environ.get("FL_NO_FIT"):
        # the floor under a column, measured WITHOUT the special-surface boxes themselves (their inner faces read as
        # floors and floated the fitted box ~50u up: a crawl-height slab under the tree)
        g_nm = flgeom.TriGrid([t for t, f in zip(wound, wtags) if (f & 0x7FF) != flfit.MAT_SPECIAL])
        wound, wtags, colboxes, stats["columns"] = flfit.fit_columns(
            wound, wtags, rtris, lambda x, y, zt, zb: g_nm.ground(x, y, zt - 4, zb))
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
        wtags += [0] * len(rp)
    # the edges of the world: a clip wall wherever a walkable floor ends over nothing (flcliff.py)
    if not os.environ.get("FL_NO_CLIFF"):
        cw, stats["cliffs"] = flcliff.walls(wound, grid)
        wound += cw
        wtags += [0] * len(cw)
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
    for a2, b2, c2 in wound:
        if B.add_prism(clip, a2, b2, c2, thickness=float(os.environ.get("FL_THICK", "4")), centered=True) is None:
            rejected += 1
        else:
            nb += 1
    for lo_, hi_ in caps + colboxes:
        B.add_brush_planes(clip, [], lo_, hi_)
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

    # ---- entities ----
    ents = L.entities()
    player = next((e for e in ents if "Player" in e["strs"]), None)
    sp = flpack.spec(level)
    ws = [("classname", "worldspawn"), ("message", f"Frontline {level} (converted locally, converter {CONVERTER_VERSION})"),
          ("farplane", "0" if os.environ.get("FL_DEBUGCOLOR") else str(sp.get("farplane", 12000))), ("farplane_color", sp.get("farplane_color", "0.55 0.6 0.65")),
          ("ambientlight", "40 40 40")]
    B.entity(ws)
    kept = []
    for n in L.navpoints():
        p = X(n["pos"])
        # Frontline packs navpoints tighter than MOHAA's PathSearch accepts ("Duplicate node ... not linked")
        if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < 64 * 64 and abs(p[2] - q[2]) < 48 for q in kept):
            continue
        kept.append(p)
        B.entity([("classname", "info_pathnode"), ("origin", f"{p[0]:.0f} {p[1]:.0f} {p[2] + 16:.0f}")])

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
    pack = flpack.build(L.disc, L, level, X, vgm, files, mohaa_base=mohaa_base, grid=grid) if vgm else None

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

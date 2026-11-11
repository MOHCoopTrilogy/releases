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

CONVERTER_VERSION = "0.7.5"   # 0.7.5 an entity light grid from the baked vertex light (tanks and soldiers no longer daylit at night), silent panic bark; 0.7.4 baked light written for the mod's world gain (the night was near three times too bright), two-layer terrain upgrades graded (crater rims), far glows given back the fog share, silent bark aliases; 0.7.2 particle sizes are half extents (quads twice as wide); 0.7.1 the level's own global fog record sets the far plane and its colour (the village is a night level), width and height end scales of a particle kept apart; 0.7.0 the level's own particle systems (eafx: emitters + sprite sheets from the disc's ProcParticleType records; engine convfx); 0.6.1 music events by the .mpf's own table (eamusic); [eapolish] eadb names (the eaents lookup gave wrong names), the EA logic VM tables (eavm)
MERGE_CELL = 1536.0
ZIP_TIME = (2002, 5, 28, 0, 0, 0)   # fixed timestamp for deterministic zips



def tank_route(grid, a, b, cell=48.0, half=64.0, wide=144.0, margin=480.0, only_check=False, room=True):
    """[eapolish] waypoints (excluding a and b) for a tank driving from a to b over open ground: A* on a cell grid
    of the collision (a cell is open when it has ground within a step of its neighbour and a tank-sized box above
    it hits no triangle), then string-pulled to the fewest points a straight drive between keeps on open cells.
    [] when the straight line is already open or no route is found (the leg then drives straight, as before)."""
    import heapq
    x0, x1 = min(a[0], b[0]) - margin, max(a[0], b[0]) + margin
    y0, y1 = min(a[1], b[1]) - margin, max(a[1], b[1]) + margin
    nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
    zref = (a[2] + b[2]) / 2.0
    zc, wc = {}, {}

    def clear(x, y, g, hw):
        c = (x, y, g + 30 + 50)
        return not any(flgeom.tri_box(c, (hw, hw, 50), *grid.tris[t]) for t in grid.near(x, y, hw + 4))

    def gz(i, j):
        if (i, j) not in zc:
            x, y = x0 + i * cell, y0 + j * cell
            g = grid.ground(x, y, zref + 200, zref - 300)
            zc[(i, j)] = g if g is not None and clear(x, y, g, half) else None
        return zc[(i, j)]

    def roomy(i, j):
        # a tank is ~300u long and swings wide on a turn: keep the route well off walls where the ground allows
        if (i, j) not in wc:
            g = gz(i, j)
            wc[(i, j)] = g is not None and clear(x0 + i * cell, y0 + j * cell, g, wide)
        return wc[(i, j)]

    def cell_of(p):
        return (min(nx - 1, max(0, int(round((p[0] - x0) / cell)))), min(ny - 1, max(0, int(round((p[1] - y0) / cell)))))

    def open_line(p, q, need_room=True):
        n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (cell / 2)))
        last = None
        for k in range(n + 1):
            t = k / n
            c = cell_of((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
            z = gz(*c)
            if z is None or (last is not None and abs(z - last) > 40) or (need_room and not roomy(*c)):
                return False
            last = z
        return True

    if only_check:
        return open_line(a, b, need_room=room)
    if open_line(a, b):
        return []
    s0, s1 = cell_of(a), cell_of(b)
    for c in (s0, s1):         # the placements themselves may sit against cover: let the search start and end there
        if gz(*c) is None:
            zc[c] = grid.ground(x0 + c[0] * cell, y0 + c[1] * cell, zref + 200, zref - 300) or zref
    openl = [(0.0, s0)]
    came, cost = {s0: None}, {s0: 0.0}
    while openl:
        _, c = heapq.heappop(openl)
        if c == s1:
            break
        zc0 = gz(*c)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if not (di or dj):
                    continue
                n2 = (c[0] + di, c[1] + dj)
                if not (0 <= n2[0] < nx and 0 <= n2[1] < ny):
                    continue
                z2 = gz(*n2)
                if z2 is None or abs(z2 - zc0) > 32:
                    continue
                nc = cost[c] + math.hypot(di, dj) * cell * (1.0 if roomy(*n2) else 4.0)
                if nc < cost.get(n2, 1e18):
                    cost[n2] = nc
                    came[n2] = c
                    h = math.hypot(n2[0] - s1[0], n2[1] - s1[1]) * cell
                    heapq.heappush(openl, (nc + h, n2))
    if s1 not in came:
        return []
    path = []
    c = s1
    while c is not None:
        path.append((x0 + c[0] * cell, y0 + c[1] * cell, gz(*c) + 16))
        c = came[c]
    path.reverse()
    out, cur, k = [], a, 1
    while k < len(path) - 1:
        # pull as far as a line keeps well off walls; only where the route itself runs close (a lane between
        # houses) pull over merely open cells - never a 48u staircase of right-angle bends the autopilot cannot follow
        j = k
        while j + 1 < len(path) and open_line(cur, path[j + 1]):
            j += 1
        if j == k:
            while j + 1 < len(path) and open_line(cur, path[j + 1], need_room=False):
                j += 1
        if j + 1 >= len(path):
            break
        out.append(path[j])
        cur = path[j]
        k = j + 1
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
            sky_shader=None, vgm=None, mohaa_base=None, game="fl"):
    t0 = time.time()
    # game: "fl" = Frontline (flcore), "ea" = European Assault (eacore); same Level interface
    if game == "ea":
        import eacore
        L = eacore.Level(flcore.Disc(img), level)
    else:
        L = flcore.Level(flcore.Disc(img), level)
    # coop_fl_*: the engine loads scripted anims per map by NAME PREFIX (new_generic_human.tik "includes ...
    # coop" block); real coop maps use the same prefix, and isCoopEnabledMap accepts it
    mapname = f"coop_{game}_" + level
    tdir = f"textures/{game}/{level}/"

    coll = list(L.collision())
    allc = [v for _, vs, _ in coll for v in vs]
    lo = [min(v[k] for v in allc) for k in range(3)]
    hi = [max(v[k] for v in allc) for k in range(3)]
    zrange_m = (lo[2], hi[2])          # collision height range (metres), for placement sanity
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
    # [eapolish] EA smart objects (easob.py): the railgun, radio tower, ammo dump, bridge, gates, tombstones, crates
    # are separate meshes placed by the object DB. Static ones join the world; the ones the mission changes (blown
    # up, opened) become inline brush models the script can remove or swing. Their collision is built from the
    # drawn triangles (blocked only by what you can see).
    sob_static, sob_dyn = [], []
    if game == "ea" and not os.environ.get("EA_NO_SOB"):
        import easob
        import eadb as _eadb
        for rec, sob, ms in easob.placed(L.stream, _eadb.DB(L.stream)):
            base_ = sob[:-2] if sob.endswith("_D") else sob
            (sob_dyn if base_ in easob.DYNAMIC else sob_static).append((rec, sob, ms))
        for _r, _s, ms in sob_static:
            meshes += ms
    rup, rdown = floor_vote([(m["verts"][a], m["verts"][b], m["verts"][c]) for m in meshes for a, b, c in m["tris"]])
    if flip_render is None:
        # the vote makes floors counter-clockwise seen from above; id Tech 3 front faces are clockwise
        # (verified in-engine 2026-11-08: unflipped, the streets were back-face culled)
        flip_render = not (rdown > rup)

    B = flbsp.BSP()
    B.vis_cell = 1024.0
    B.vis_radius = float(flpack.spec(level, game).get("vis_radius", 0))
    files = {}
    shader_lines = []
    tex_names = {}
    stats = {"tris": 0, "tris_textured": 0, "textures": 0, "alpha_textures": 0}

    texmap = {}
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{game}_texmap.json")
    if os.path.exists(tmp) and not os.environ.get("FL_NO_TEXMAP"):
        with open(tmp) as f:
            texmap = json.load(f).get(level, {})

    def upgrade_ok(up):
        """only when the player's own install carries the pak that holds the texture"""
        if not mohaa_base:
            return False
        for gdir in ("maintt", "mainta", "main"):
            pk = os.path.join(mohaa_base, gdir, up["pak"])
            if os.path.exists(pk):
                try:
                    return up["path"] in zipfile.ZipFile(pk).namelist()
                except Exception:
                    return False
        return False

    # textures whose meshes carry real vertex alpha (Frontline's water: 203)
    vtx_alpha = {m["tex"] for m in meshes if m["tex"] and m["tris"] and min(c[3] for c in m["cols"]) < 250}
    _lv = sorted(c[0] + c[1] + c[2] for m in meshes for c in m["cols"] if not (c[0] == c[1] == c[2] == 255))
    _mv = _lv[len(_lv) // 2] // 3 if _lv else 128
    med_light = (_mv, _mv, _mv)
    grade = {}     # upgraded texture key -> per-channel gain toward Frontline's own texture colour
    grade2 = {}    # EA two-layer key -> (base layer gain, top layer gain); mixed per vertex by the layer weight

    def grade_for(key, up, hi=1.2):
        """deterministic grade: scale the vertex colours so the HD texture's mean colour lands on Frontline's"""
        import io as _io
        from statistics import fmean
        t = L.texture(key)
        if not (t and t["rgba"]):
            return None
        fl = [fmean(t["rgba"][c::4]) for c in range(3)]
        for gdir in ("maintt", "mainta", "main"):
            pk = os.path.join(mohaa_base, gdir, up["pak"])
            if os.path.exists(pk):
                try:
                    from PIL import Image
                    im = Image.open(_io.BytesIO(zipfile.ZipFile(pk).read(up["path"]))).convert("RGB").resize((64, 64))
                    px = im.tobytes()
                    hd = [fmean(px[c::3]) for c in range(3)]
                    return tuple(max(0.3, min(hi, round(f / max(1.0, h), 3))) for f, h in zip(fl, hd))
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
                files[name + ".tga"] = tga_bytes(4, 4, bytes((40, 70, 90, 255)) * 16)
                shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\t{{\n\t\tmap {name}.tga\n\t\trgbGen vertex\n\t}}\n}}\n")
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        t = L.texture(key)
        short = key.replace(f"{level}_ART", "").replace(".cpt", "").replace("@", "_").replace("#", "_").replace("+", "_").strip("_")
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
        if "+" in key and getattr(L, "texture2", None) and L.texture2(key):
            # EA two-layer terrain (Moh3_Cpt_Texture2*): base layer, then the top layer from the 2nd UV set
            # (lightmap texcoords) blended by the vertex alpha EA stores as the layer weight
            t2 = L.texture2(key)
            k1, k2 = key.split("#")[0].split("+")
            map1, map2, tc1, tc2 = name + ".tga", name + "_l2.tga", "", ""
            up1, up2 = texmap.get(k1), texmap.get(k2)
            if up1 and upgrade_ok(up1):
                map1 = up1["path"]
                tc1 = ("\t\ttcMod scale %g %g\n" % (up1["tc_scale"], up1["tc_scale"])) if up1.get("tc_scale", 1.0) != 1.0 else ""
                stats["upgraded"] = stats.get("upgraded", 0) + 1
            if up2 and upgrade_ok(up2):
                map2 = up2["path"]
                tc2 = ("\t\ttcMod scale %g %g\n" % (up2["tc_scale"], up2["tc_scale"])) if up2.get("tc_scale", 1.0) != 1.0 else ""
                stats["upgraded"] = stats.get("upgraded", 0) + 1
            else:
                files[name + "_l2.tga"] = tga_bytes(t2["w"], t2["h"], t2["rgba"])
            # an upgraded layer is graded to the disc texture's own mean like a single upgraded texture is; without
            # it the HD snow sat darker than the meshes beside it that keep the disc's snow in their own texture
            # (the craters' rims showed as pale boxes on the ground)
            _g1 = grade_for(k1, up1, 2.0) if (up1 and upgrade_ok(up1) and up1.get("grade", True)) else None
            _g2 = grade_for(k2, up2, 2.0) if (up2 and upgrade_ok(up2) and up2.get("grade", True)) else None
            if _g1 or _g2:
                grade2[key] = (_g1 or (1.0, 1.0, 1.0), _g2 or (1.0, 1.0, 1.0))
                stats.setdefault("grades2", {})[short_key(key)] = [list(grade2[key][0]), list(grade2[key][1])]
            stats["two_layer"] = stats.get("two_layer", 0) + 1
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tcull none\n\t{\n\t\tmap " + map1 + "\n" + tc1 +
                                "\t\trgbGen vertex\n\t}\n\t{\n\t\tmap " + map2 + "\n\t\ttcGen lightmap\n" + tc2 +
                                "\t\tblendFunc blend\n\t\trgbGen vertex\n\t\talphaGen vertex\n\t}\n}\n")
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        if key.split("#")[0] in texmap.get("additive", []):
            # authored per level (ea_texmap.json "additive"): fire/lamp light cards whose render state does not
            # carry blend flags but which EA draws additively - opaque they read as a solid orange board
            stats["additive"] = stats.get("additive", 0) + 1
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n"
                                "\tcull none\n\t{\n\t\tmap " + name + ".tga\n\t\tblendFunc add\n\t\trgbGen vertex\n\t}\n}\n")
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        if getattr(L, "hint", None) and L.hint(key) == "glow":
            # EA light cards (EAGL render state: alpha blend, no depth write) - drawn as soft translucent light
            stats["glow"] = stats.get("glow", 0) + 1
            shader_lines.append(name + "\n{\n\tsurfaceparm nolightmap\n\tsurfaceparm trans\n\tsurfaceparm nonsolid\n"
                                "\tcull none\n\t{\n\t\tmap " + name + ".tga\n\t\tblendFunc blend\n\t\trgbGen vertex\n\t}\n}\n")
            tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
            return tex_names[key]
        has_alpha = any(a < 250 for a in rgba[3::4])
        n_px = max(1, len(rgba) // 4)
        soft = sum(1 for a in rgba[3::4] if 0 < a < 250) / n_px > 0.10
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
    _mm = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{game}_modelmap.json")
    reskin = json.load(open(_mm)).get(level, {}).get("reskin", {}) if os.path.exists(_mm) else {}

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
                if not (game == "ea" and m["tex"] and m["tex"].split("#")[0] in texmap.get("additive", [])):
                    r, g, b = med_light
            gr = grade.get(m["tex"])
            if gr:
                r, g, b = (min(255, int(round(c * k))) for c, k in zip((r, g, b), gr))
            g2_ = grade2.get(m["tex"])
            if g2_:
                _w = va / 255.0
                r, g, b = (min(255, int(round(c * (ka * (1.0 - _w) + kb * _w)))) for c, ka, kb in zip((r, g, b), g2_[0], g2_[1]))
            u, v = m["uvs"][i]
            if m.get("uvs2") and m["tex"] and "+" in m["tex"]:
                # EA two-layer terrain: vertex alpha = the top layer's weight, uv2 rides in the lightmap texcoords
                verts.append((p, (u, v), tuple(x / l for x in acc[i]), (r, g, b, va), m["uvs2"][i]))
                continue
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
                    pz = ztop if p[2] >= z1 - 1.0 else p[2]          # only the column's top edge rises
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

    # [eapolish] the dynamic smart objects as inline models (script_object "*N", targetname ea_sob_<placement>)
    sob_models = []
    for rec, sob, ms in sob_dyn:
        sids, tri_world = [], []
        # hinged leaves (the gates) are built around their hinge - the placement's own origin - and the entity's
        # "origin" puts them back: a script_object rotates about that point, so the gate swings instead of vanishing
        piv = X(rec.pos) if "Gate" in sob else (0.0, 0.0, 0.0)
        for m in ms:
            P = [tuple(q[k] - piv[k] for k in range(3)) for q in (X(v) for v in m["verts"])]
            tris = [wind(a, b, c, flip_render) for a, b, c in m["tris"]]
            vv = []
            for i, q in enumerate(P):
                r_, g_, b_, _a = m["cols"][i]
                vv.append((q, m["uvs"][i], (0.0, 0.0, 1.0), (r_, g_, b_, 255)))
            sids.append(B.add_soup(tex_shader(m["tex"]), vv, [i for t in tris for i in t]))
            tri_world += [(P[a], P[b], P[c]) for a, b, c in tris]
        sob_models.append((rec, sob, sids, tri_world, piv))
        stats["sob_dynamic_tris"] = stats.get("sob_dynamic_tris", 0) + len(tri_world)
    stats["sob_static"] = len(sob_static)
    stats["sob_dynamic"] = len(sob_dyn)

    # seam bridges: close Frontline's hairline floor gaps that would show the sky (flseam.py has the rules)
    # collision grid: seam bridges only close gaps in WALKABLE floors; flpack places actors with it
    grid = flgeom.TriGrid([(X(vs[a]), X(vs[b]), X(vs[c])) for _, vs, ts in coll for a, b, c, _f in ts])
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
        pq = flseam.patches(draws + br, flpack.spec(level, game).get("patches", []), lambda i: B.shaders[i][0])
        for sh_, verts, tris in pq:
            cx = sum(v[0][0] for v in verts) / len(verts)
            cy = sum(v[0][1] for v in verts) / len(verts)
            batches.setdefault((sh_, int(cx // MERGE_CELL), int(cy // MERGE_CELL)), []).append((verts, tris))
        stats["seam_patches"] = len(pq)

    # Merge the ~8.5k tiny Frontline draws into few big surfaces (same shader, same 1536u cell, <= the engine's
    # SHADER_MAX_VERTEXES 2048 per surface): the draw-call count, not the triangle count, sank GL2 to ~36 fps.
    def pieces(verts, tris, maxv=2000, maxi=12000):
        """split one draw into pieces under the per-surface limits (EA terrain meshes exceed 2048 verts)"""
        if len(verts) <= maxv and 3 * len(tris) <= maxi:
            yield verts, tris
            return
        remap, pv, pt = {}, [], []
        for tri in tris:
            new = [i for i in tri if i not in remap]
            if len(pv) + len(new) > maxv or 3 * (len(pt) + 1) > maxi:
                yield pv, pt
                remap, pv, pt = {}, [], []
            for i in tri:
                if i not in remap:
                    remap[i] = len(pv)
                    pv.append(verts[i])
            pt.append(tuple(remap[i] for i in tri))
        if pt:
            yield pv, pt

    nmerged = 0
    for key in sorted(batches):
        cv, ci = [], []
        for verts, tris in (pc for vt in batches[key] for pc in pieces(*vt)):
            if cv and (len(cv) + len(verts) > 2000 or len(ci) + 3 * len(tris) > 12000):
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
    sky = B.shader(sky_shader or flpack.spec(level, game).get("sky", "textures/sky/mohday1"), 0x4 | flbsp.SURF_NOLIGHTMAP, 0)
    blo = [max(min(s["bounds"][0][k] for s in B.surfaces) - 1024, -16300) for k in range(3)]
    bhi = [min(max(s["bounds"][1][k] for s in B.surfaces) + 1024 + 4096 * (k == 2), 16300) for k in range(3)]
    corners = [(x, y, z) for z in (blo[2], bhi[2]) for y in (blo[1], bhi[1]) for x in (blo[0], bhi[0])]
    for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        vs = [(corners[i], (0.0, 0.0), (0.0, 0.0, 1.0), (255, 255, 255, 255)) for i in q]
        B.add_soup(sky, vs, [0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2])

    clip = B.shader("textures/common/fl_collision", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP, flbsp.CONTENTS_SOLID)
    nb = rejected = 0
    ctris = []
    for name, vs, ts in coll:
        if os.environ.get("FL_COLL_ONLY") and os.environ["FL_COLL_ONLY"] not in name:
            continue
        P = [X(v) for v in vs]
        for a, b, c, _f in ts:
            a2, b2, c2 = wind(a, b, c, flip_coll)
            ctris.append((P[a2], P[b2], P[c2]))
    added_drawn = []
    # [eapolish] 2026-11-10 user: invisible walls are fine where the original had them (1:1 is the bar): the
    # original's own collision is kept as it is - the clip-sheet rebuild (drop / drawn collision / wire) is opt-in
    if game == "ea" and os.environ.get("EA_SHEETS") == "1":
        # [eapolish] blocked only by what you can see (the Frontline polish rule, flsheets.py): a steep collision
        # triangle with nothing drawn within 12u is a floating clip sheet. Sheets standing in front of drawn
        # geometry (within 160u) are dropped and that drawn geometry gets collision of its own; sheets out in the
        # open, with nothing drawn near (the level's boundaries), stay and get a visible barbed-wire edge.
        import flsheets
        rtris = [tuple(X(v) for v in (m["verts"][a], m["verts"][b], m["verts"][c])) for m in meshes for a, b, c in m["tris"]]
        rtris += [tuple(tuple(v[k] + pv[k] for k in range(3)) for v in t) for _r, _s, _sid, tw, pv in sob_models for t in tw]
        RG = flgeom.TriGrid(rtris, cell=128.0)

        def drawn_near(t, r):
            cx = sum(v[0] for v in t) / 3
            cy = sum(v[1] for v in t) / 3
            cz = sum(v[2] for v in t) / 3
            for j in RG.near(cx, cy, r + 2):
                if flgeom.tri_box((cx, cy, cz), (r, r, r), *RG.tris[j]):
                    return True
            return False
        # long steep collision triangles (EA's trench and bank walls run 800-2,800u in one triangle) are judged piece
        # by piece: split until no edge is over 192u, so the parts standing off the drawn bank (40-80u away) count as
        # floating sheets and the parts on it stay (ea_geothin: 41 invisible spots, 94 of their 119 contacts on these)
        def _split(t, out):
            a, b, c = t
            e = [math.dist(a, b), math.dist(b, c), math.dist(c, a)]
            if max(e) <= 192.0:
                out.append(t)
                return
            ab = tuple((a[k] + b[k]) / 2 for k in range(3))
            bc = tuple((b[k] + c[k]) / 2 for k in range(3))
            ca = tuple((c[k] + a[k]) / 2 for k in range(3))
            for s in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)):
                _split(s, out)
        split_ct = []
        for t in ctris:
            nn = face_normal(*t)
            if nn is not None and abs(nn[2]) < 0.7:
                _split(t, split_ct)
            else:
                split_ct.append(t)
        stats["coll_split"] = len(split_ct) - len(ctris)
        ctris = split_ct
        CG = flgeom.TriGrid(ctris)

        def void_beside(t, n):
            # no floor within 2048u below a point 48u off either face: the sheet holds a level edge
            cx = sum(v[0] for v in t) / 3
            cy = sum(v[1] for v in t) / 3
            zb = min(v[2] for v in t)
            hl = math.hypot(n[0], n[1]) or 1.0
            for sg in (1, -1):
                x, y = cx + sg * 48 * n[0] / hl, cy + sg * 48 * n[1] / hl
                if CG.ground(x, y, zb + 64, zb - 2048) is None:
                    return True
            return False
        # reviewed keep list (ea_levels.json "clip_keep": collision triangle indexes, deterministic per disc level):
        # sheets the walk audit found holding a level edge (dropping them let the walker fall out of the world)
        clip_keep = set(flpack.spec(level, game).get("clip_keep", []))
        tags, keep = [], []
        for k, t in enumerate(ctris):
            n = face_normal(*t)
            # a sheet: steep and, at its centroid OR at two of its three corner-ward points, nothing drawn within 12u
            # (the centroid alone let large clip triangles with one drawn corner through: 41 invisible spots)
            sheet = False
            if n is not None and abs(n[2]) < 0.7:
                if not drawn_near(t, 12.0):
                    sheet = True
                else:
                    c3 = [sum(v[k] for v in t) / 3 for k in range(3)]
                    und = 0
                    for v in t:
                        q = tuple(c3[k] * 0.3 + v[k] * 0.7 for k in range(3))
                        if not drawn_near((q, q, q), 12.0):
                            und += 1
                    sheet = und >= 2
            tags.append(1 if sheet else 0)
            if sheet and (not drawn_near(t, 64.0) or void_beside(t, n) or k in clip_keep):
                keep.append((k,))
        ctris, _tg, added_drawn, srep = flsheets.replace(ctris, tags, [(k,) for k in range(len(ctris))],
                                                         lambda f: f == 1, rtris, keep=keep, near=96.0)
        kept_tris = srep.pop("kept_tris")
        stats["sheets_dropped"] = srep.pop("dropped_list", [])
        stats["sheets"] = srep
        # the edges of the world (flcliff.py, the Frontline polish recipe): where a walkable floor now ends over
        # nothing, a 160u clip wall - drawn as the same barbed-wire edge, so it is never an invisible wall
        import flcliff
        cw, stats["cliffs"] = flcliff.walls(ctris + added_drawn, flgeom.TriGrid(ctris + added_drawn))
        ctris += cw
        kept_tris += cw
        # barbed wire ONLY where an edge has nothing visible to stop the player: a kept sheet (or edge wall) with the
        # original's drawn geometry within 96u (a bank, a trench wall, rubble, a house) already shows why the way ends
        # - there the drawn geometry gets collision of its own (as for the dropped sheets) and no wire is strung
        # (coordinator 2026-11-10: wire along every trench wall would look absurd)
        bare, by_drawn = [], []
        for t in kept_tris:
            (by_drawn if drawn_near(t, 96.0) else bare).append(t)
        if by_drawn:
            _o, _f, more_drawn, _r = flsheets.replace(by_drawn + [], [1] * len(by_drawn), [(k,) for k in range(len(by_drawn))],
                                                      lambda f: f == 1, rtris, keep=[], near=96.0)
            added_drawn += more_drawn
        stats["sheets"]["edges_by_drawn"] = len(by_drawn)
        stats["sheets"]["edges_bare"] = len(bare)
        kept_tris = bare
        wire = B.shader("textures/mohcommon/barbwire", 0, 0)
        GW = flgeom.TriGrid(ctris)
        nfe = 0
        for (x0, y0, z0), (x1, y1, z1) in flsheets.edges(kept_tris, GW.ground):
            L_ = math.hypot(x1 - x0, y1 - y0)
            q = [((x0, y0, z0), (0.0, 1.0)), ((x1, y1, z1), (L_ / 64.0, 1.0)),
                 ((x1, y1, z1 + 64.0), (L_ / 64.0, 0.0)), ((x0, y0, z0 + 64.0), (0.0, 0.0))]
            B.add_soup(wire, [(pp, st, (0.0, 0.0, 1.0), med_light + (255,)) for pp, st in q], [0, 1, 2, 0, 2, 3])
            nfe += 1
        stats["sheets"]["visible_edges"] = nfe
    for t in ctris:
        if B.add_prism(clip, *t, thickness=float(os.environ.get("FL_THICK", "4")), centered=True) is None:
            rejected += 1
        else:
            nb += 1
    drawnclip = B.shader("textures/common/ea_coll_drawn", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP, flbsp.CONTENTS_SOLID)
    for t in added_drawn:
        if B.add_prism(drawnclip, *t, thickness=4.0, centered=True) is not None:
            nb += 1

    # [eapolish] visible collision for the smart objects: thin slabs on their drawn triangles
    sobclip = B.shader("textures/common/ea_coll_sob", flbsp.SURF_NODRAW | flbsp.SURF_NOLIGHTMAP, flbsp.CONTENTS_SOLID)
    # 1:1 (user 2026-11-10): a smart object whose own collision is already in the level's .cdb (the railgun, the
    # bridge, the ammo dump: 27-88 triangles inside its box) keeps exactly that; only the ones the .cdb leaves
    # without collision (tower, tombstones, gates, crates) get collision on their drawn triangles. Doubling the
    # railgun's made 5 invisible contacts on the route that the original did not have.
    _cg = flgeom.TriGrid([(X(vs[a]), X(vs[b]), X(vs[c])) for _, vs, ts in coll for a, b, c, _f in ts])

    def own_coll(tris_world):
        xs = [v[0] for t in tris_world for v in t]
        ys = [v[1] for t in tris_world for v in t]
        zs = [v[2] for t in tris_world for v in t]
        if not xs:
            return False
        lo_, hi_ = (min(xs) - 16, min(ys) - 16, min(zs) - 16), (max(xs) + 16, max(ys) + 16, max(zs) + 16)
        n_ = 0
        for j in _cg.near((lo_[0] + hi_[0]) / 2, (lo_[1] + hi_[1]) / 2, max(hi_[0] - lo_[0], hi_[1] - lo_[1]) / 2 + 16):
            c_ = [sum(v[k] for v in _cg.tris[j]) / 3 for k in range(3)]
            if all(lo_[k] <= c_[k] <= hi_[k] for k in range(3)):
                n_ += 1
        return n_ >= 10
    for _r, _s, ms in sob_static:
        tw = [tuple(X(v) for v in (m["verts"][a], m["verts"][b], m["verts"][c])) for m in ms for a, b, c in m["tris"]]
        if own_coll(tw):
            stats["sob_own_coll"] = stats.get("sob_own_coll", 0) + 1
            continue
        for t in tw:
            if B.add_prism(sobclip, *t, thickness=4.0, centered=True) is not None:
                stats["sob_coll"] = stats.get("sob_coll", 0) + 1
    sob_ents = []
    for rec, sob, sids, tri_world, piv in sob_models:
        tw_world = [tuple(tuple(v[k] + piv[k] for k in range(3)) for v in t) for t in tri_world]
        if own_coll(tw_world):
            bids = []                     # the .cdb already carries its collision (1:1)
            stats["sob_own_coll"] = stats.get("sob_own_coll", 0) + 1
        else:
            bids = [b for b in (B.add_prism(sobclip, *t, thickness=4.0, centered=True) for t in tri_world) if b is not None]
        B.models.append({"surfaces": sids, "brushes": bids})
        kv = [("classname", "script_object"), ("model", "*%d" % len(B.models)),
              ("targetname", ("ea_sobD_" if sob.endswith("_D") else "ea_sob_") + rec.name)]
        if piv != (0.0, 0.0, 0.0):
            kv.append(("origin", "%.1f %.1f %.1f" % piv))
        sob_ents.append(kv)

    # ---- entities ----
    ents = L.entities()
    player = next((e for e in ents if "Player" in e["strs"]), None)
    sp = dict(flpack.spec(level, game))
    if game == "ea" and not os.environ.get("EA_NO_DISCFOG"):
        # the level's own global fog record: colour 0..255, where the fog starts and where it reaches its most (m),
        # and that most in percent. MOHAA's far plane fog is a straight ramp from the eye to opaque, so the far
        # plane goes where that ramp passes the record's most at the record's far distance.
        import eadb as _eadbf
        for _r in _eadbf.DB(L.stream).recs:
            if _r.cls == "FogTrigger" and _r.name.upper().endswith("_GBL") and len(_r.w) >= 30:
                _col = [_r.u(i) for i in (23, 24, 25)]
                _far, _most = _r.f(28), _r.f(29)
                if all(0 <= c <= 255 for c in _col) and 5.0 < _far < 2000.0 and 1.0 <= _most <= 100.0:
                    # 0.7.3: the record's fog starts at its near distance, climbs to its most at its far distance
                    # and stays there. The engine's fog is a ramp from farplane_bias to opaque at the far plane, so
                    # the far plane goes where the same slope would reach opaque, and farplane_maxfog (engine
                    # extension) stops the ramp at the record's most; the far plane then no longer culls.
                    _st = _r.f(27)
                    _st = _st * 48.0 if 0.0 <= _st < _far else 0.0
                    sp["farplane"] = int(max(2400.0, min(16000.0, _st + (_far * 48.0 - _st) * 100.0 / _most)))
                    sp["farplane_color"] = "%.3f %.3f %.3f" % tuple(c / 255.0 for c in _col)
                    if _st > 1.0:
                        sp["farplane_bias"] = "%d" % _st
                    if _most < 99.0:
                        sp["farplane_maxfog"] = "%.3f" % (_most / 100.0)
                        sp["farplane_cull"] = "0"
                    stats["disc_fog"] = [sp["farplane"], sp["farplane_color"], sp.get("farplane_bias"), sp.get("farplane_maxfog")]
                break
    ws = [("classname", "worldspawn"), ("message", f"{ {'fl': 'Frontline', 'ea': 'European Assault'}[game]} {level} (converted locally, converter {CONVERTER_VERSION})"),
          ("farplane", "0" if os.environ.get("FL_DEBUGCOLOR") else str(sp.get("farplane", 12000))), ("farplane_color", sp.get("farplane_color", "0.55 0.6 0.65")),
          ("ambientlight", os.environ.get("EA_AMBIENT", "12 14 17") if game == "ea" else "40 40 40")]
    ws += [(k, sp[k]) for k in ("farplane_bias", "farplane_maxfog", "farplane_cull") if k in sp]
    B.entity(ws)
    if game == "ea":
        # [eapolish] the Panzers' driving paths: each tank squad's SquadObjective points in order (the original orders
        # its TreadedVehicle squads along them). One 2-node info_vehiclepoint path per leg, ea_tkp_<squad>_<n> ->
        # ..._e, from the previous point (the tank's placement for the first leg) to objective point n.
        import re as _re3
        import eadb as _eadb3
        _db3 = _eadb3.DB(L.stream)
        for tv in _db3.of("TreadedVehicle"):
            sq = tv.s(29) or ""
            pts = sorted((int(m.group(1)), r.pos) for r in _db3.of("SquadObjective_New")
                         for m in [_re3.match(r"^(?:JA|BR)_SquadObjective_" + _re3.escape(sq) + r"_(\d+)$", r.name)] if m)
            prev = X(tv.pos)
            for num, pm in pts:
                q = X(pm)
                g = grid.ground(q[0], q[1], q[2] + 160, q[2] - 400)
                q = (q[0], q[1], (g if g is not None else q[2]) + 16)
                tn = "ea_tkp_%s_%d" % (sq, num)
                # converter 0.6.1: the original's tanks drive its navmesh between the points (roads and open ground);
                # a straight 2-node leg ran Panzer 3 into a house. Route each leg over open ground on the collision.
                way = tank_route(grid, prev, q)
                stats["tank_route_pts"] = stats.get("tank_route_pts", 0) + len(way)
                chain = [prev] + way + [q]
                names = [tn] + ["%s_w%d" % (tn, k + 1) for k in range(len(way))] + [tn + "_e"]
                for k, (pt, nm) in enumerate(zip(chain, names)):
                    kv = [("classname", "info_vehiclepoint"), ("origin", "%.0f %.0f %.0f" % pt), ("targetname", nm)]
                    if k + 1 < len(names):
                        kv.append(("target", names[k + 1]))
                    B.entity(kv)
                prev = q
                stats["tank_legs"] = stats.get("tank_legs", 0) + 1
    for kv in sob_ents:
        B.entity(kv)
    kept = []
    if game == "ea" and not os.environ.get("EA_NO_NODES"):
        # [eapolish] EA's AI walks a navmesh we do not decode; MOHAA's AI paths on info_pathnodes, and with none every
        # runto failed ("Path not found ... MoveToPatrolCurrentNode": the squads never moved, bug-eap-aikills).
        # Nodes on a 224u grid of free standing spots around the original's own AI places (spawn points, squad
        # objective points, triggers, the player start), at their floor heights.
        import eadb as _eadb2
        _db = _eadb2.DB(L.stream)
        anchors = [X(r.pos) for r in _db.recs if r.cls in ("NPCSpawnPoint", "SquadObjective_New", "BasicTrigger",
                                                            "Player", "ICSPoint", "MMGPoint") and r.pos != (0.0, 0.0, 0.0)]
        cells = {}
        for a in anchors:
            for gx in range(int((a[0] - 1600) // 160), int((a[0] + 1600) // 160) + 1):
                for gy in range(int((a[1] - 1600) // 160), int((a[1] + 1600) // 160) + 1):
                    x, y = gx * 160 + 80, gy * 160 + 80
                    if (x - a[0]) ** 2 + (y - a[1]) ** 2 > 1600 ** 2:
                        continue
                    g = grid.ground(x, y, a[2] + 160, a[2] - 260)
                    if g is None:
                        continue
                    key = (gx, gy, int(g // 96))
                    if key in cells:
                        continue
                    cells[key] = (x, y, g) if grid.box_free(x, y, g, lift=18.0, margin=2.0) else None
        nodes = sorted(v for v in cells.values() if v)
        for x, y, g in nodes[:3800]:
            kept.append((x, y, g))
            B.entity([("classname", "info_pathnode"), ("origin", f"{x:.0f} {y:.0f} {g + 16:.0f}")])
        stats["pathnodes"] = min(len(nodes), 3800)
        kept = []          # not the coop spawn ring source below (that stays around the player start)
    for n in L.navpoints():
        p = X(n["pos"])
        # Frontline packs navpoints tighter than MOHAA's PathSearch accepts ("Duplicate node ... not linked")
        if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < 64 * 64 and abs(p[2] - q[2]) < 48 for q in kept):
            continue
        kept.append(p)
        B.entity([("classname", "info_pathnode"), ("origin", f"{p[0]:.0f} {p[1]:.0f} {p[2] + 16:.0f}")])

    # spawn points on Frontline's own navpoints (they are known-walkable): the 8 nearest the player start
    # for the allies/coop start and the 8 nearest the far end for axis - one shared point jams 8 bodies
    # no disc start/navpoints decoded (EA entity DB is partial): the level spec names a start in metres and
    # spawn spots are found on the collision around it (deterministic ring search, flgeom.free_spot)
    if player is None and game == "ea" and sp.get("objects", {}).get("start"):
        # EA: the disc's own squad start from the object DB (eapack resolves the same name for the data script);
        # the BSP needs info_player_start for SP (coop spawns come from the script's flags)
        import eapack
        o = eapack.find_object(L, sp["objects"]["start"], X, grid, zrange_m)
        if o:
            player = {"pos": tuple(o["pos"]), "strs": ["Player"]}
    if player is None and sp.get("start"):
        player = {"pos": tuple(sp["start"]), "strs": ["Player"]}
    if player and not kept:
        ps = X(player["pos"])
        for r in (0, 96, 192):
            for k in range(1 if r == 0 else 8):
                a = 2 * math.pi * k / 8
                spot, moved = grid.free_spot((ps[0] + r * math.cos(a), ps[1] + r * math.sin(a), ps[2]))
                if moved >= 0 and all((spot[0] - q[0]) ** 2 + (spot[1] - q[1]) ** 2 > 48 * 48 for q in kept):
                    kept.append(spot)
        far_m = sp.get("far")
        if far_m:
            fp = X(tuple(far_m))
            for k in range(8):
                a = 2 * math.pi * k / 8
                spot, moved = grid.free_spot((fp[0] + 96 * math.cos(a), fp[1] + 96 * math.sin(a), fp[2]))
                if moved >= 0:
                    kept.append(spot)

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

    if game == "ea" and not os.environ.get("EA_NO_VCGAIN"):
        # EA's baked vertex light means texture x colour x 2 (colour 128 = 1.0; eacore doubles it already). The mod's
        # renderer multiplies every world vertex colour again at map load by its world gain (r_mapOverBrightBits 2 with
        # r_mapOverBrightScale 0.71 = 2.83, both pinned by the mod's autoexec), so the night village came out near
        # three times as bright as the disc lights it and the snow clipped to white. Divide the gain back out.
        _k = 1.0 / float(os.environ.get("EA_WORLD_GAIN", "2.83"))
        for _s in B.surfaces:
            _s["verts"] = [v[:3] + ((int(v[3][0] * _k + 0.5), int(v[3][1] * _k + 0.5), int(v[3][2] * _k + 0.5), v[3][3]),) + tuple(v[4:])
                           for v in _s["verts"]]
        stats["world_gain"] = round(1.0 / _k, 3)
        # models take their light from a grid written out of the same vertex colours (see flbsp._light_grid)
        B.grid_light = float(os.environ.get("EA_ENT_LIGHT", "1.0"))
        stats["ent_light_gain"] = B.grid_light
    import flvis
    B.vis_occluders = flvis.occluders([(X(vs[a]), X(vs[b]), X(vs[c])) for _, vs, ts in coll for a, b, c, _f in ts])
    bsp_path = out_pk3 + ".bsp.tmp"
    info = B.write(bsp_path)
    with open(bsp_path, "rb") as f:
        files[f"maps/{mapname}.bsp"] = f.read()
    os.remove(bsp_path)
    files[f"scripts/{game}_{level}.shader"] = "".join(shader_lines).encode()
    if game == "ea":
        import eapack     # EA: level data script from the disc's object DB + strings (audio: separate step)
        pack = eapack.build(L, level, X, files, sp, grid, zrange_m, mohaa_base=mohaa_base, vgm=vgm)
        dk = f"maps/coop_ea_{level}_data.scr"
        if sob_static or sob_dyn:      # [eapolish] the smart objects are real geometry: the script drops its stand-ins
            files[dk] = files[dk].replace(b"\tlevel.ea_data_ok = 1", b"\tlevel.ea_sob = 1\n\tlevel.ea_data_ok = 1")
    else:
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
    ap.add_argument("--game", default="fl", choices=("fl", "ea"))
    ap.add_argument("--mohaa", help="the MOHAA install (basepath) - read for the alias bridge")
    a = ap.parse_args()
    r = convert(a.image, a.level, a.out, a.scale, a.mirror, a.flip_render, a.flip_coll, a.report,
                vgm=a.vgmstream, mohaa_base=a.mohaa, game=a.game)
    print(json.dumps({k: r[k] for k in ("map", "brushes", "prism_rejected", "textured_pct", "seconds", "sha256", "votes",
                                        "flip_render", "flip_collision", "pack")}, default=str))

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

CONVERTER_VERSION = "0.1.0"
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
    mapname = "mfl_" + level
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
    files = {}
    shader_lines = []
    tex_names = {}
    stats = {"tris": 0, "tris_textured": 0, "textures": 0, "alpha_textures": 0}

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
        short = key.replace(f"{level}_ART", "").replace(".cpt", "").replace("@", "_").strip("_")
        name = tdir + short
        rgba = t["rgba"] if t and t["rgba"] else bytes((255, 0, 255, 255)) * 16
        w, h = (t["w"], t["h"]) if t and t["rgba"] else (4, 4)
        files[name + ".tga"] = tga_bytes(w, h, rgba)
        stats["textures"] += 1
        has_alpha = any(a < 250 for a in rgba[3::4])
        if has_alpha:
            stats["alpha_textures"] += 1
            shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\t{{\n\t\tmap {name}.tga\n"
                                f"\t\talphaFunc GE128\n\t\trgbGen vertex\n\t\tdepthWrite\n\t}}\n}}\n")
        else:
            # two-sided: Frontline mixes windings inside one mesh (terrain skirts, facades)
            shader_lines.append(f"{name}\n{{\n\tsurfaceparm nolightmap\n\tcull none\n\t{{\n\t\tmap {name}.tga\n"
                                f"\t\trgbGen vertex\n\t}}\n}}\n")
        tex_names[key] = B.shader(name, flbsp.SURF_NOLIGHTMAP, 0)
        return tex_names[key]

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
            r, g, b, _a = m["cols"][i]
            u, v = m["uvs"][i]
            verts.append((p, (u, v), tuple(x / l for x in acc[i]), (r, g, b, 255)))
        idx = [i for t in tris for i in t]
        B.add_soup(sh, verts, idx)
        stats["tris"] += len(tris)
        if m["tex"]:
            stats["tris_textured"] += len(tris)

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
    for name, vs, ts in coll:
        if os.environ.get("FL_COLL_ONLY") and os.environ["FL_COLL_ONLY"] not in name:
            continue
        P = [X(v) for v in vs]
        for a, b, c, _f in ts:
            a2, b2, c2 = wind(a, b, c, flip_coll)
            if B.add_prism(clip, P[a2], P[b2], P[c2], thickness=float(os.environ.get("FL_THICK", "4")), centered=True) is None:
                rejected += 1
            else:
                nb += 1

    # ---- entities ----
    ents = L.entities()
    player = next((e for e in ents if "Player" in e["strs"]), None)
    sp = flpack.spec(level)
    ws = [("classname", "worldspawn"), ("message", f"Frontline {level} (converted locally, converter {CONVERTER_VERSION})"),
          ("farplane", str(sp.get("farplane", 12000))), ("farplane_color", sp.get("farplane_color", "0.55 0.6 0.65")),
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

    bsp_path = out_pk3 + ".bsp.tmp"
    info = B.write(bsp_path)
    with open(bsp_path, "rb") as f:
        files[f"maps/{mapname}.bsp"] = f.read()
    os.remove(bsp_path)
    files[f"scripts/fl_{level}.shader"] = "".join(shader_lines).encode()
    pack = flpack.build(L.disc, L, level, X, vgm, files, mohaa_base=mohaa_base) if vgm else None

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
           "brushes": nb, "prism_rejected": rejected, "bsp": info, "stats": stats,
           "textured_pct": round(100.0 * stats["tris_textured"] / max(1, stats["tris"]), 2),
           "pk3": os.path.basename(out_pk3), "sha256": sha, "seconds": round(time.time() - t0, 1),
           "player_start": X(player["pos"]) if player else None, "offset_m": offset, "pack": pack}
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

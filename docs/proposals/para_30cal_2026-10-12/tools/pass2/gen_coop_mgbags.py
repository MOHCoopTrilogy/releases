"""gen_coop_mgbags.py - GENERATES the paratrooper .30 cal's sandbag rest (bug-3562).

    models/static/coop_mg_bags.tik
    models/static/coop_mg_bags/coop_mg_bags.skd, .skc
    scripts/coop_mgbags.shader

User 2026-10-12: "Make sure the sandbag isn't invisible on the sides too please for the 30 cal gunner". The first
pass used the retail models/static/sandbag_link_topcap.tik scaled to 0.65: that is the END CAP of a sandbag wall, a
shell with no faces where it joins the wall and none underneath, so from the side and from behind it was see-through.
None of the retail sandbag models is closed all round (they are wall sections) - this one is.

THREE BAGS a man could carry: two on the ground side by side, one across the seam on top. Each is a closed
superellipsoid (a pillow), so there is no angle from which a face is missing, and nothing depends on cull none.
21.5 u from the ground to the top, 34 u wide, 33 u deep. The two lower bags reach 6 u BELOW the origin: the rest is
bedded on the lowest ground under it and that skirt fills whatever the ground does under the rest of it (parasquad.scr
allows 8 u across the footprint) - no gap, no floating edge.
Model space: +X = the way the gun points, +Y = left, +Z = up; origin = on the ground under the middle of the pile.
Texture: the retail sandbag sheet (textures/models/sandbags/sb_1): each bag is mapped onto one of the plain burlap
panels of its middle row, top and underside both. Its OWN shader, coop_mg_bags (rgbGen lightingSpherical): the retail
static_sb_1 is `rgbGen vertex`, made for sandbags compiled into a map with baked vertex light - on a model spawned in
play it has no vertex colours to read, and the first walk-round of this model showed it going black from some sides.
Bone: Box01 (POSROT, identity pose) through gen_coop_sea's self-tested SKD v5 / SKC v13 writers.

    python docs/tools/gen_coop_mgbags.py [--out <mod root>] [--check]
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = HERE if os.path.exists(os.path.join(HERE, "gen_coop_sea.py")) else "C:/mohaa-coop-dev/docs/tools"
sys.path.insert(0, TOOLS)
import gen_coop_sea as sea  # noqa: E402
skdlib = sea.skdlib

NORMAL_LEN = 0.999
SEG_T, SEG_P = 14, 9          # around, pole to pole
E1, E2 = 0.55, 0.45           # superellipsoid exponents: flat top and underside, a rounded-rectangle plan
TOP = 21.5                    # parasquad.scr mgTry: "the bags are 21.5u high"
SKIRT = 6.0
# (centre x, y, z; half sizes x, y, z; yaw deg; the burlap panel (u0, v0, u1, v1) of sb_1)
BAGS = [
    ((8.2, 0.6, (10.0 - SKIRT) / 2.0), (8.6, 17.0, (10.0 + SKIRT) / 2.0), 4.0, (0.03, 0.37, 0.30, 0.60)),
    ((-8.0, -0.8, (10.0 - SKIRT) / 2.0), (8.6, 16.6, (10.0 + SKIRT) / 2.0), -5.0, (0.36, 0.37, 0.63, 0.60)),
    ((0.2, 0.0, 15.3), (9.2, 17.0, 6.2), 2.0, (0.69, 0.37, 0.96, 0.60)),
]


def spow(w, e, fn):
    c = fn(w)
    return math.copysign(abs(c) ** e, c)


def bag(centre, half, yaw, uvr, base):
    (cx, cy, cz), (a, b, h) = centre, half
    cyaw, syaw = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cols = SEG_T + 1
    svl = []
    for j in range(SEG_P + 1):
        phi = -math.pi / 2 + math.pi * j / SEG_P
        for i in range(cols):
            th = -math.pi + 2 * math.pi * i / SEG_T
            x = a * spow(phi, E1, math.cos) * spow(th, E2, math.cos)
            y = b * spow(phi, E1, math.cos) * spow(th, E2, math.sin)
            z = h * spow(phi, E1, math.sin)
            nx = spow(phi, 2 - E1, math.cos) * spow(th, 2 - E2, math.cos) / a
            ny = spow(phi, 2 - E1, math.cos) * spow(th, 2 - E2, math.sin) / b
            nz = spow(phi, 2 - E1, math.sin) / h
            k = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / k * NORMAL_LEN, ny / k * NORMAL_LEN, nz / k * NORMAL_LEN
            # the panel from above: its long side along the bag
            u = uvr[0] + (y / b * 0.5 + 0.5) * (uvr[2] - uvr[0])
            v = uvr[1] + (x / a * 0.5 + 0.5) * (uvr[3] - uvr[1])
            wx, wy = x * cyaw - y * syaw, x * syaw + y * cyaw
            wnx, wny = nx * cyaw - ny * syaw, nx * syaw + ny * cyaw
            svl.append(((wnx, wny, nz), (u, v), (cx + wx, cy + wy, cz + z)))
    tris = []
    for j in range(SEG_P):
        for i in range(SEG_T):
            p0 = base + j * cols + i
            p1 = p0 + 1
            p2 = p0 + cols
            p3 = p2 + 1
            tris.append((p0, p1, p3))
            tris.append((p0, p3, p2))
    return svl, tris


def retail_front_sign():
    """+1 when the retail models' triangles run counter-clockwise seen from outside, -1 when clockwise: measured on
    the retail sandbag wall, so that ours face the same way."""
    import zipfile
    z = zipfile.ZipFile("G:/GOG/Medal of Honor - Allied Assault War Chest/main/Pak0.pk3")
    m = skdlib.read_skd(z.read("models/static/sandbags/sandbag_link_main.skd"))
    s = m.surfaces[0]
    idx = struct.unpack("<%di" % (len(s.tri_bytes) // 4), s.tri_bytes)
    pos = [v[2][0][2] for v in s.verts]
    nrm = [v[0] for v in s.verts]
    tot = 0
    for t in range(0, len(idx), 3):
        a, b, c = (pos[idx[t]], pos[idx[t + 1]], pos[idx[t + 2]])
        e1 = [b[k] - a[k] for k in range(3)]
        e2 = [c[k] - a[k] for k in range(3)]
        fn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        n = [sum(nrm[idx[t + q]][k] for q in range(3)) for k in range(3)]
        d = sum(fn[k] * n[k] for k in range(3))
        tot += 1 if d > 0 else -1
    return 1 if tot > 0 else -1


def build():
    svl, tris = [], []
    for (centre, half, yaw, uvr) in BAGS:
        s, t = bag(centre, half, yaw, uvr, len(svl))
        svl += s
        tris += t
    # face them the way the retail models face
    want = retail_front_sign()
    pos = [v[2] for v in svl]
    nrm = [v[0] for v in svl]
    out = bytearray()
    flipped = 0
    for (a, b, c) in tris:
        pa, pb, pc = pos[a], pos[b], pos[c]
        e1 = [pb[k] - pa[k] for k in range(3)]
        e2 = [pc[k] - pa[k] for k in range(3)]
        fn = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        n = [nrm[a][k] + nrm[b][k] + nrm[c][k] for k in range(3)]
        d = sum(fn[k] * n[k] for k in range(3))
        if d * want < 0:
            b, c = c, b
            flipped += 1
        out += struct.pack("<3i", a, b, c)
    assert len(svl) <= sea.TIKI_MAX_VERTEXES and len(tris) <= sea.TIKI_MAX_TRIANGLES
    return [("bags", bytes(out), svl)], want, flipped


def closed(surfaces):
    """every edge of every bag is shared by exactly two triangles once coincident vertices (the seam, the poles)
    are welded - i.e. no hole anywhere"""
    (_, tri_bytes, svl) = surfaces[0]
    idx = struct.unpack("<%di" % (len(tri_bytes) // 4), tri_bytes)
    key = {}
    weld = []
    for v in svl:
        k = tuple(round(c, 3) for c in v[2])
        weld.append(key.setdefault(k, len(key)))
    edges = {}
    for t in range(0, len(idx), 3):
        tri = [weld[idx[t + q]] for q in range(3)]
        if len(set(tri)) < 3:
            continue
        for q in range(3):
            e = tuple(sorted((tri[q], tri[(q + 1) % 3])))
            edges[e] = edges.get(e, 0) + 1
    bad = [e for e, n in edges.items() if n != 2]
    return len(bad) == 0, len(edges)


def tik_text(nverts, ntris):
    return """TIKI
// HZM coop [2026-10-12, bug-3562] THE PARATROOPER .30 CAL'S SANDBAG REST - GENERATED by docs/tools/gen_coop_mgbags.py;
// edit the generator, never this file.
// Three closed bags (two on the ground, one across them): %d verts / %d tris, 21.5 u high, 34 u wide, 33 u deep, the
// lower two reaching 6 u below the origin so that uneven ground never shows a gap. Spawned by coop_mod/parasquad.scr
// (mgSetup) as a NON-SOLID script_model, +X toward the enemy, origin on the lowest ground under it.
setup
{
\tscale 1.0
\tpath models/static/coop_mg_bags
\tskelmodel coop_mg_bags.skd
\tsurface bags shader coop_mg_bags
}

animations
{
\tidle coop_mg_bags.skc
}
""" % (nverts, ntris)


def shader_text():
    return """// HZM coop [2026-10-12, bug-3562] the paratrooper .30 cal's sandbag rest - GENERATED by docs/tools/gen_coop_mgbags.py;
// edit the generator, never this file. The retail sandbag sheet, lit as an entity (the retail static_sb_1 is
// rgbGen vertex: baked light of a map-compiled model, nothing to read on a model spawned in play).
coop_mg_bags
{
\tqer_editorimage textures/models/sandbags/sb_1.tga
\t{
\t\tmap textures/models/sandbags/sb_1.tga
\t\trgbGen lightingSpherical
\t}
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=sea.MOD)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    ref_skd = open(sea.REF_SKD, "rb").read()
    ref_skc = open(sea.REF_SKC, "rb").read()
    bone_block = ref_skd[148:264]
    frame_time = sea.selftest_skc_writer(ref_skc)
    surfaces, want, flipped = build()
    ok, nedges = closed(surfaces)
    assert ok, "the mesh has an open edge"
    svl = surfaces[0][2]
    nverts, ntris = len(svl), len(surfaces[0][1]) // 12
    skd = sea.build_skd("coop_mg_bags.skd", surfaces, bone_block, tail_from_ref=True)
    m = skdlib.read_skd(skd)
    assert m.numSurfaces == 1 and m.surfaces[0].numVerts == nverts and m.surfaces[0].numTriangles == ntris
    offs = [v[2] for v in svl]
    bmin = tuple(min(o[i] for o in offs) - 1.0 for i in range(3))
    bmax = tuple(max(o[i] for o in offs) + 1.0 for i in range(3))
    assert abs(bmax[2] - 1.0 - TOP) < 0.01 and abs(bmin[2] + 1.0 + SKIRT) < 0.01
    radius = max(math.sqrt(sum(c * c for c in o)) for o in offs) + 1.0
    skc = sea.build_skc(frame_time, bmin, bmax, radius, sea.CHANNELS, [(0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)])
    outs = [(os.path.join(args.out, "models", "static", "coop_mg_bags", "coop_mg_bags.skd"), skd),
            (os.path.join(args.out, "models", "static", "coop_mg_bags", "coop_mg_bags.skc"), skc),
            (os.path.join(args.out, "models", "static", "coop_mg_bags.tik"), sea.ascii_lf(tik_text(nverts, ntris))),
            (os.path.join(args.out, "scripts", "coop_mgbags.shader"), sea.ascii_lf(shader_text()))]
    drift = 0
    for (path, data) in outs:
        if args.check:
            if not os.path.exists(path) or open(path, "rb").read() != data:
                print("DRIFT", path)
                drift += 1
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").write(data)
    print("coop_mg_bags: %d verts, %d tris, %d edges all shared by two faces, retail front sign %+d (%d flipped), "
          "x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f" % (nverts, ntris, nedges, want, flipped, bmin[0] + 1, bmax[0] - 1,
                                                    bmin[1] + 1, bmax[1] - 1, bmin[2] + 1, bmax[2] - 1))
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())

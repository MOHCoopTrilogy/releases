#!/usr/bin/env python
"""gen_coop_headlights.py - every shipped asset of the vehicle-headlight Phase H (vet_headlights.md section 3).

WHAT IT WRITES (every shipped byte of the pk3 side is derived here - TRAPS T2):
  hzm-mohaa-coop-mod/textures/coop_fx/headlamp_glow.tga        64x64 warm lamp glow, no plateau, dithered
  hzm-mohaa-coop-mod/textures/coop_fx/headbeam.tga             32x128 beam ramp (length) x dim-underside (around)
  hzm-mohaa-coop-mod/models/fx/coop_headbeam/coop_headbeam.skd the fog beam: an elliptical cone, SKD v5, 1 bone
  hzm-mohaa-coop-mod/models/fx/coop_headbeam/coop_headbeam.skc a 1-frame idle, SKC v13, identity pose
  hzm-mohaa-coop-mod/models/fx/coop_headbeam.tik               the beam model
  hzm-mohaa-coop-mod/models/fx/coop_headlamp.tik               the lamp glow model (retail unitsquare mesh)
  hzm-mohaa-coop-mod/textures/coop_fx/lampflare.tga            64x64 lamp lens flare (Phase S2): core + faint streak
  hzm-mohaa-coop-mod/scripts/coop_headlights.shader            coop_headlamp_glow + coop_headbeam + hzmLampFlare (T6)

WHO DRAWS THEM. Nothing on the server. cgame's CG_CoopHeadlights (openmohaa-hzm/code/cgame/cg_view.c) adds one
glow per lamp and - in fog or rain only - one beam per lamp, per viewer, while cg_hzmHeadlights resolves on. No
script, tik or shader of retail is overridden: every name here is new (TRAPS T6 "stop fighting for the name"),
and the HD FX pack's corona_util texture is left alone (vet F19: every .spr is sized from its image, so swapping
it would resize every muzzle glow in the game).

THE GLOW uses `deformVertexes lightglow` on the retail unitsquare - the retail corona recipe
(main/Pak0 models/fx/searchlight.tik). lightglow billboards the quad AND pulls it toward the eye by its radius, which
is what stops the glow being cut by the hood and lamp housing (vet F20). It therefore needs renderer_opengl2's
Phase R restore (r_hzmLightGlow) - cgame refuses to draw it otherwise. The texture is a small hot core over a soft
halo that reaches exactly 0 at the quad edge: no plateau (research R1: a plateau clips flat white under HDR and
shows a hard rim), and a mean far below 0.1 so only the core reaches bloom.

THE BEAM uses `rgbGen dot` (Phase R2) with `alphaGen entity`: rgb = (N.V)^2 gives the soft volumetric silhouette on
BOTH renderers the same way (gl1 has always written RGB), and cgame fades it through the entity alpha. The cone is
elliptical - 14 deg half-angle across, 5 deg up/down - because a round cone pitched down meets the road a quarter of
the way along, while it is still bright, and draws a hard line there. The texture's length ramp reaches 0 at 70%
of the length and its underside is dimmed to 15%, so the only part that can touch the ground is already dark.
`cull none`: both walls of the cone add, which is what a lit volume looks like, and nothing depends on winding.

THE LENS FLARE (Phase S2, docs/proposals/headlights_2026-09-25/plan_phaseS.md section 5) is drawn by
renderer_opengl2 itself (tr_hzm_spot_rb.c), not by a model: a screen-space sprite, additive, in the scene before the
tonemap, occluded by GPU occlusion queries. Its texture is NEUTRAL (the renderer tints it per class: warm headlight,
cool searchlight) and small by design: a hot core that never reaches 1.0 (no plateau to clip flat under HDR - research
R1), a faint horizontal streak, a soft halo, and a border that is exactly 0 so the quad edge can never show. It is its
own texture on purpose - the HD FX pack's textures/sprites/flare.tga is a 2048 starburst (vet F16/F19).

TGA ROW ORDER: bottom-left origin, and the engine's LoadTGA puts the file's FIRST row at t = 1 (the
gen_breakfoam.py convention, verified in-game there). So row r holds t = 1 - r / (H - 1).

    python docs/tools/gen_coop_headlights.py            # writes everything, verifies, prints a summary
    python docs/tools/gen_coop_headlights.py --check    # verify only (no writes), exit 1 on drift
"""
import argparse
import math
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_coop_sea as sea  # noqa: E402  the self-tested SKD v5 / SKC v13 writers (reproduce us_helmetfit.skc)
skdlib = sea.skdlib

ROOT = sea.ROOT
MOD = sea.MOD
OUT_GLOW_TGA = os.path.join(MOD, "textures", "coop_fx", "headlamp_glow.tga")
OUT_BEAM_TGA = os.path.join(MOD, "textures", "coop_fx", "headbeam.tga")
OUT_BEAM_DIR = os.path.join(MOD, "models", "fx", "coop_headbeam")
OUT_BEAM_SKD = os.path.join(OUT_BEAM_DIR, "coop_headbeam.skd")
OUT_BEAM_SKC = os.path.join(OUT_BEAM_DIR, "coop_headbeam.skc")
OUT_BEAM_TIK = os.path.join(MOD, "models", "fx", "coop_headbeam.tik")
OUT_GLOW_TIK = os.path.join(MOD, "models", "fx", "coop_headlamp.tik")
OUT_SHADER = os.path.join(MOD, "scripts", "coop_headlights.shader")
OUT_FLARE_TGA = os.path.join(MOD, "textures", "coop_fx", "lampflare.tga")

# ---------------------------------------------------------------- the numbers
WARM = (1.00, 0.78, 0.54)     # ~2800 K incandescent (research section 3: 2700-2900 K, colour ~(1.00, 0.76, 0.50))

GLOW_N = 64                   # texels a side
GLOW_CORE = (0.68, 0.070)     # (peak, gaussian radius as a fraction of the half-width): a ~2 px hot core
GLOW_HALO = (0.30, 0.280)     # the soft halo around it
GLOW_TIK_SCALE = 12           # unitsquare is +-0.953 -> an ~23 u quad, lightglow radius ~11.4 u (research A1)

BEAM_W, BEAM_H = 32, 128      # s = around the cone, t = along it
BEAM_FADE_IN = 0.05           # t over which the beam rises from the lamp glass (hides the ring at the apex)
BEAM_END = 0.70               # the length ramp is exactly 0 from here on (vet: "ramp to 0 by 70% of the length")
                              # S3a: cgame cg_view.c HL_BEAM_VISIBLE == BEAM_END * BEAM_LEN (420 u) - change BOTH
BEAM_UNDER = 0.15             # brightness of the underside (sin theta = -1) relative to the top
BEAM_LEN = 600.0              # u; visible part ~420 u (research: pool reach ~400 u, retail beam ~600 u)
BEAM_R0 = (5.0, 4.0)          # (across, up/down) radius at the lamp: a 7-inch lamp
BEAM_HALF_DEG = (14.0, 5.0)   # half-angles (across, up/down); cgame pitches the whole cone down a further 2 deg
BEAM_SIDES = 16
BEAM_RINGS = (0.0, 0.12, 0.35, 0.70, 1.0)   # fractions of the length (t) that carry a ring of vertices
NORMAL_LEN = 0.999            # R_VaoPackNormal wraps int16 at >= 1.0000153 (gen_coop_sea NORMAL_CAP note)
SEED = 20260925               # dither PRNG seed: deterministic output (build.ps1's packer is deterministic, bug-237)

FLARE_N = 64                  # texels a side (the renderer draws it ~0.05 x viewport height at most, vet: < 0.3% area)
FLARE_CORE = (0.62, 0.130)    # (peak, gaussian radius as a fraction of the half-width): the hot point
                              # [2026-09-26, bug-2999] radius 0.060 -> 0.130: a ~2 px core never read as a lamp
FLARE_HALO = (0.14, 0.300)    # the soft glow around it
FLARE_STREAK = (0.16, 0.030)  # (peak, vertical gaussian radius): the faint horizontal streak


def smoothstep(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def q8(v, rng):
    """0..1 float -> byte with +-0.5 LSB triangular dither (the gradients are BPTC/DXT-compressed at load, vet F19)."""
    d = (rng.random() - rng.random()) * 0.5
    return max(0, min(255, int(math.floor(v * 255.0 + 0.5 + d))))


def tga(w, h, rows_bgra):
    """18-byte uncompressed 32-bit TGA, bottom-left origin (gen_surfcell.py's writer; the 5-byte colour-map spec is
    mandatory even with no colour map - bug-2485)."""
    hdr = struct.pack("<BBBHHBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 8)
    assert len(hdr) == 18
    body = b"".join(rows_bgra)
    assert len(body) == w * h * 4
    return hdr + body


# ---------------------------------------------------------------- textures
def glow_value(x, y):
    """intensity at texel centre (x, y); r = 1 at the quad's half-width"""
    c = (GLOW_N - 1) * 0.5
    r = math.hypot((x - c) / (GLOW_N * 0.5), (y - c) / (GLOW_N * 0.5))
    if r >= 1.0:
        return 0.0
    core = GLOW_CORE[0] * math.exp(-(r / GLOW_CORE[1]) ** 2)
    halo = GLOW_HALO[0] * math.exp(-(r / GLOW_HALO[1]) ** 2)
    window = (1.0 - r * r) ** 2
    return (core + halo) * window


def build_glow():
    rng = random.Random(SEED)
    rows = []
    vals = []
    for y in range(GLOW_N):
        row = bytearray()
        for x in range(GLOW_N):
            v = glow_value(x, y)
            vals.append(v)
            r, g, b = (q8(v * WARM[0], rng), q8(v * WARM[1], rng), q8(v * WARM[2], rng))
            a = q8(v, rng)
            if v <= 0.0:
                r = g = b = a = 0
            row += bytes((b, g, r, a))
        rows.append(bytes(row))
    peak = max(vals)
    mean = sum(vals) / len(vals)
    # no plateau: the peak is below 1.0, so nothing is clipped flat in the texture itself
    assert peak < 0.99, "glow peak %.3f - a plateau" % peak
    assert mean < 0.10, "glow mean %.3f - too broad, it would bloom as a disc (research R1)" % mean
    # the border is exactly black, so the quad edge can never show
    for y in (0, GLOW_N - 1):
        assert set(rows[y]) == {0}, "glow border row %d not black" % y
    for y in range(GLOW_N):
        assert rows[y][0:4] == b"\x00\x00\x00\x00" and rows[y][-4:] == b"\x00\x00\x00\x00", "glow border col"
    return tga(GLOW_N, GLOW_N, rows), peak, mean


def flare_value(x, y):
    """intensity at texel centre (x, y); u, v in -1..1 across the quad"""
    c = (FLARE_N - 1) * 0.5
    u = (x - c) / (FLARE_N * 0.5)
    v = (y - c) / (FLARE_N * 0.5)
    r = math.hypot(u, v)
    if r >= 1.0 or abs(u) >= 1.0 or abs(v) >= 1.0:
        return 0.0
    core = FLARE_CORE[0] * math.exp(-(r / FLARE_CORE[1]) ** 2)
    halo = FLARE_HALO[0] * math.exp(-(r / FLARE_HALO[1]) ** 2)
    streak = FLARE_STREAK[0] * math.exp(-(v / FLARE_STREAK[1]) ** 2) * (1.0 - u * u) ** 3
    window = (1.0 - r * r) ** 2
    total = core + halo + streak
    assert total < 0.98, "flare sum %.3f would clip - a plateau" % total
    return total * window


def build_flare():
    rng = random.Random(SEED + 2)
    rows = []
    vals = []
    for y in range(FLARE_N):
        row = bytearray()
        for x in range(FLARE_N):
            v = flare_value(x, y)
            vals.append(v)
            g = q8(v, rng)
            if v <= 0.0:
                g = 0
            row += bytes((g, g, g, g))   # neutral: the renderer tints it per flare class
        rows.append(bytes(row))
    peak = max(vals)
    mean = sum(vals) / len(vals)
    assert peak < 0.99, "flare peak %.3f - a plateau" % peak
    assert mean < 0.03, "flare mean %.4f - too broad for a small flare" % mean
    for y in (0, FLARE_N - 1):
        assert set(rows[y]) == {0}, "flare border row %d not black" % y
    for y in range(FLARE_N):
        assert rows[y][0:4] == b"\x00\x00\x00\x00" and rows[y][-4:] == b"\x00\x00\x00\x00", "flare border col"
    # the streak is horizontal: more energy along the centre row than down the centre column
    mid = FLARE_N // 2
    row_sum = sum(flare_value(x, mid) for x in range(FLARE_N))
    col_sum = sum(flare_value(mid, y) for y in range(FLARE_N))
    assert row_sum > col_sum * 1.2, "flare streak not horizontal (%.3f vs %.3f)" % (row_sum, col_sum)
    return tga(FLARE_N, FLARE_N, rows), peak, mean


def beam_ramp(t):
    if t >= BEAM_END:
        return 0.0
    return smoothstep(0.0, BEAM_FADE_IN, t) * (1.0 - t / BEAM_END) ** 2


def beam_around(s):
    theta = 2.0 * math.pi * s   # s = 0 on the +Y (left) side, 0.25 on top, 0.75 underneath (matches the mesh)
    return BEAM_UNDER + (1.0 - BEAM_UNDER) * smoothstep(-1.0, 0.3, math.sin(theta))


def build_beam_tga():
    rng = random.Random(SEED + 1)
    rows = []
    for r in range(BEAM_H):
        t = 1.0 - r / float(BEAM_H - 1)     # LoadTGA: the file's first row is t = 1
        row = bytearray()
        for c in range(BEAM_W):
            s = c / float(BEAM_W - 1)
            v = beam_ramp(t) * beam_around(s)
            rr, gg, bb = (q8(v * WARM[0], rng), q8(v * WARM[1], rng), q8(v * WARM[2], rng))
            if v <= 0.0:
                rr = gg = bb = 0
            row += bytes((bb, gg, rr, 255))
        rows.append(bytes(row))
    # every row at or beyond 70% of the length is black: the ground contact happens where nothing is drawn
    for r in range(BEAM_H):
        t = 1.0 - r / float(BEAM_H - 1)
        if t >= BEAM_END:
            assert all(rows[r][i] == 0 for i in range(0, BEAM_W * 4) if i % 4 != 3), "beam row t=%.3f not black" % t
    # the lamp end (t = 0, the LAST file row) is black too, so the apex ring never shows
    assert all(rows[BEAM_H - 1][i] == 0 for i in range(0, BEAM_W * 4) if i % 4 != 3), "beam apex row not black"
    return tga(BEAM_W, BEAM_H, rows)


# ---------------------------------------------------------------- the beam mesh
def build_cone():
    """One surface: BEAM_SIDES segments around (seam vertex duplicated, s 0..1), len(BEAM_RINGS) rings along +X.
    Returns [(name, tri_bytes, [(normal, uv, offset)])] in gen_coop_sea's surface shape."""
    ta = (math.tan(math.radians(BEAM_HALF_DEG[0])), math.tan(math.radians(BEAM_HALF_DEG[1])))
    cols = BEAM_SIDES + 1
    svl = []
    for f in BEAM_RINGS:
        x = f * BEAM_LEN
        ry = BEAM_R0[0] + x * ta[0]
        rz = BEAM_R0[1] + x * ta[1]
        for i in range(cols):
            s = i / float(BEAM_SIDES)
            th = 2.0 * math.pi * s
            y = ry * math.cos(th)
            z = rz * math.sin(th)
            ny, nz = math.cos(th) / ry, math.sin(th) / rz      # outward ellipse normal, radial (vet: radial normals)
            k = NORMAL_LEN / math.hypot(ny, nz)
            svl.append(((0.0, ny * k, nz * k), (s, f), (x, y, z)))
    tris = bytearray()
    for j in range(len(BEAM_RINGS) - 1):
        for i in range(BEAM_SIDES):
            a = j * cols + i
            b = a + 1
            c = a + cols
            d = c + 1
            tris += struct.pack("<3i", a, c, d)
            tris += struct.pack("<3i", a, d, b)
    assert len(svl) <= sea.TIKI_MAX_VERTEXES and len(tris) // 12 <= sea.TIKI_MAX_TRIANGLES
    return [("beam", bytes(tris), svl)]


def verify_cone(skd_bytes, surfaces):
    m = skdlib.read_skd(skd_bytes)
    assert m.version == 5 and m.numBones == 1 and m.numSurfaces == 1
    assert m.bones[0].name == sea.BONE_NAME.decode() and m.bones[0].jointType == 1
    (name, tri_bytes, svl) = surfaces[0]
    s = m.surfaces[0]
    assert s.name == name and s.numVerts == len(svl) and s.numTriangles == len(tri_bytes) // 12 and s.has_collapse
    assert s.tri_bytes == tri_bytes
    for (v, (normal, uv, off)) in zip(s.verts, svl):
        (rn, ruv, wl, ml) = v
        assert len(wl) == 1 and wl[0][0] == 0 and abs(wl[0][1] - 1.0) < 1e-6 and not ml
        assert all(abs(a - b) < 1e-6 for a, b in zip(rn, normal))
        assert all(abs(a - b) < 1e-6 for a, b in zip(ruv, uv))
        assert all(abs(a - b) < 1e-3 for a, b in zip(wl[0][2], off))
        assert math.sqrt(sum(c * c for c in rn)) < 1.0000153, "normal would wrap in R_VaoPackNormal"
    idx = struct.unpack("<%di" % (len(tri_bytes) // 4), tri_bytes)
    assert min(idx) == 0 and max(idx) == len(svl) - 1


# ---------------------------------------------------------------- text assets
def glow_tik():
    return """TIKI
// HZM coop [2026-09-25] VEHICLE HEADLIGHT LAMP GLOW (Phase H) - GENERATED by docs/tools/gen_coop_headlights.py;
// edit the generator, never this file.
//
// Drawn ONLY by cgame (cg_view.c CG_CoopHeadlights): one per lamp, per viewer, never spawned by a script. It is the
// retail corona recipe (main/Pak0 models/fx/searchlight.tik) with its own shader and texture: the retail unitsquare
// mesh, and a shader using deformVertexes lightglow, which billboards the quad and pulls it toward the eye so the hood
// cannot cut it (vet F20). The HD FX pack's corona_util texture is NOT touched (vet F19).
setup
{
\tscale %d
\tpath models/fx/unitsquare
\tskelmodel unitsquare.skd
\tsurface material1 shader coop_headlamp_glow
}

animations
{
\tidle unitsquare.skc
}
""" % GLOW_TIK_SCALE


def beam_tik(nverts, ntris):
    return """TIKI
// HZM coop [2026-09-25] VEHICLE HEADLIGHT FOG BEAM (Phase H) - GENERATED by docs/tools/gen_coop_headlights.py;
// edit the generator, never this file.
//
// Drawn ONLY by cgame (cg_view.c CG_CoopHeadlights), one per lamp, per viewer, and only in fog or rain on a dark
// map - never in clear air. An elliptical cone along +X from the lamp: %d u long, %g x %g deg half-angles, %d verts /
// %d tris. Shader coop_headbeam: rgbGen dot (soft silhouette, Phase R2) + alphaGen entity (cgame's fade).
// Bone: Box01 (POSROT, identity pose), the shipping coop_helmets container pattern via gen_coop_sea's writers.
setup
{
\tscale 1.0
\tpath models/fx/coop_headbeam
\tskelmodel coop_headbeam.skd
\tsurface beam shader coop_headbeam
}

animations
{
\tidle coop_headbeam.skc
}
""" % (int(BEAM_LEN), BEAM_HALF_DEG[0], BEAM_HALF_DEG[1], nverts, ntris)


def shader_text():
    return """// HZM coop [2026-09-25] VEHICLE HEADLIGHTS (Phase H) - GENERATED by docs/tools/gen_coop_headlights.py;
// edit the generator, never this file. Both names exist ONLY here (TRAPS T6: one name, one coop file).
// Drawn only by cgame's CG_CoopHeadlights (openmohaa-hzm/code/cgame/cg_view.c), gl2 only, never on Omaha.

// The lamp glow. deformVertexes lightglow = the retail corona recipe (billboard + pull toward the eye), which needs
// renderer_opengl2's Phase R restore; cgame will not draw this while r_hzmLightGlow is off. rgbGen entity: cgame
// sets the per-viewer intensity (it fades to 0 as you move to the side of the vehicle). Own texture - the HD FX
// pack's corona_util is left alone, because every .spr is sized from its image (vet F19).
coop_headlamp_glow
{
\tqer_editorimage textures/coop_fx/headlamp_glow.tga
\tdeformVertexes lightglow
\tcull none
\tnopicmip
\t{
\t\tclampmap textures/coop_fx/headlamp_glow.tga
\t\tblendFunc GL_ONE GL_ONE
\t\trgbGen entity
\t}
}

// The fog beam. rgbGen dot: rgb = (N.V)^2 * 1.2, so the cone's silhouette is dark and its face is lit - the soft
// volumetric edge, identical on gl1 and gl2 (Phase R2 ports gl1's RGB write). A single-bundle, deform-free dot stage
// would collapse into gl2's LIGHTALL and draw flat; Phase R2's CollapseStagesToGLSL skip keeps it generic.
// alphaGen entity + GL_SRC_ALPHA GL_ONE: additive, scaled by cgame's per-viewer fade.
// qer_hzmSoftEdge 32 (headlight S3b): renderer_opengl2 fades the beam out within 32 u of whatever is behind it (a soft
// particle's depth fade), so it never ends in a hard line on the ground, a wall or a soldier. Every renderer that does
// not know it skips it with the other qer* editor keywords.
coop_headbeam
{
\tqer_editorimage textures/coop_fx/headbeam.tga
\tqer_hzmSoftEdge 32
\tcull none
\tnopicmip
\t{
\t\tclampmap textures/coop_fx/headbeam.tga
\t\tblendFunc GL_SRC_ALPHA GL_ONE
\t\trgbGen dot 0 1.2
\t\talphaGen entity
\t}
}

// The lamp lens flare (Phase S2). NOT a model: renderer_opengl2 draws it (tr_hzm_spot_rb.c RB_HZM_SpotFlares) as a
// screen-space sprite in the scene, before the tonemap, for each flare cgame sends while r_hzmFlares resolves on.
// The renderer looks the name up in CreateExternalShaders and forces depth test off, no fog colour adjust and no
// global fog on it; occlusion is measured separately with GPU occlusion queries. rgbGen vertex: the renderer writes
// the colour (class tint x intensity x visibility x fog). If this shader is missing (an older pk3) the renderer
// draws no flares at all rather than a white square.
hzmLampFlare
{
\tqer_editorimage textures/coop_fx/lampflare.tga
\tnopicmip
\tnomipmaps
\tcull none
\t{
\t\tclampmap textures/coop_fx/lampflare.tga
\t\tblendFunc GL_ONE GL_ONE
\t\trgbGen vertex
\t\tnofog
\t}
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped files match; write nothing")
    args = ap.parse_args()

    ref_skd = open(sea.REF_SKD, "rb").read()
    ref_skc = open(sea.REF_SKC, "rb").read()
    bone_block = ref_skd[148:264]
    frame_time = sea.selftest_skc_writer(ref_skc)

    glow_bytes, glow_peak, glow_mean = build_glow()
    beam_bytes = build_beam_tga()
    flare_bytes, flare_peak, flare_mean = build_flare()

    surfaces = build_cone()
    nverts = len(surfaces[0][2])
    ntris = len(surfaces[0][1]) // 12
    skd = sea.build_skd("coop_headbeam.skd", surfaces, bone_block, tail_from_ref=True)
    verify_cone(skd, surfaces)
    offs = [v[2] for v in surfaces[0][2]]
    bmin = tuple(min(o[i] for o in offs) - 1.0 for i in range(3))
    bmax = tuple(max(o[i] for o in offs) + 1.0 for i in range(3))
    radius = max(math.sqrt(sum(c * c for c in o)) for o in offs) + 1.0
    skc = sea.build_skc(frame_time, bmin, bmax, radius, sea.CHANNELS,
                        [(0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)])
    a = skdlib.read_skc(skc)
    assert a.numFrames == 1 and list(a.channels) == list(sea.CHANNELS)

    outputs = [
        (OUT_GLOW_TGA, glow_bytes),
        (OUT_BEAM_TGA, beam_bytes),
        (OUT_BEAM_SKD, skd),
        (OUT_BEAM_SKC, skc),
        (OUT_BEAM_TIK, sea.ascii_lf(beam_tik(nverts, ntris))),
        (OUT_GLOW_TIK, sea.ascii_lf(glow_tik())),
        (OUT_FLARE_TGA, flare_bytes),
        (OUT_SHADER, sea.ascii_lf(shader_text())),
    ]
    drift = 0
    for (path, data) in outputs:
        if args.check:
            have = open(path, "rb").read() if os.path.exists(path) else None
            ok = have == data
            print("%s %s" % ("ok   " if ok else "DRIFT", os.path.relpath(path, ROOT)))
            drift += (not ok)
        else:
            # Phase S [2026-09-26]: never rewrite an unchanged file - its mtime is the pk3 entry's mtime and part of
            # build.ps1's bucket digest (bug-237), so a same-bytes rewrite still churns the shipped pak.
            if os.path.exists(path) and open(path, "rb").read() == data:
                print("same  %s" % os.path.relpath(path, ROOT))
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").write(data)
            print("wrote %s (%d bytes)" % (os.path.relpath(path, ROOT), len(data)))

    print("glow: %dx%d, peak %.3f, mean %.4f, tik scale %d" % (GLOW_N, GLOW_N, glow_peak, glow_mean, GLOW_TIK_SCALE))
    print("flare: %dx%d, peak %.3f, mean %.4f (neutral; tinted per class by the renderer)"
          % (FLARE_N, FLARE_N, flare_peak, flare_mean))
    print("beam: %d verts / %d tris, %d u long, far ellipse %.0f x %.0f u, ramp 0 from t %.2f; bounds %s..%s r %.0f"
          % (nverts, ntris, BEAM_LEN,
             BEAM_R0[0] + BEAM_LEN * math.tan(math.radians(BEAM_HALF_DEG[0])),
             BEAM_R0[1] + BEAM_LEN * math.tan(math.radians(BEAM_HALF_DEG[1])),
             BEAM_END, tuple(round(v) for v in bmin), tuple(round(v) for v in bmax), radius))
    if drift:
        sys.exit(1)


if __name__ == "__main__":
    main()

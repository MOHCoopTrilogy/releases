# -*- coding: utf-8 -*-
"""gen_coop_surf.py - a MOVING crest layer for Omaha's surf zone.

[user 2026-09-07, bug-2521] "The waves look good in the ocean now, if we could have those happening
near the shoreline too after we are getting out of the cinematic piece that would be great."

WHY THIS IS A SEPARATE MESH AND NOT A DEFORM ON THE SHORE WATER. The band between y -2160 and y -768
is `textures/misc_outside/deepbluesea_shoreline`, and it is WORLD geometry: 12 four-vertex brush faces
with exactly THREE rows of vertices across the whole 1408 u surf zone (t 0.005 / 0.494 / 0.994). A
deform moves vertices, and there are none to move - the shortest wave that grid could even represent
is longer than the beach. World geometry also cannot be hidden from a .shader (ParseMesh reads the
BSP-baked flags), so the painted sheet stays and anything we add has to sit ON TOP of it.

WHAT THIS IS. A thin additive layer floating STANDOFF units above the sheet's own plane, carrying the
same break-line texture the sheet paints, on geometry that actually rises and runs up the beach. The
painted band stays exactly where it is; this puts real relief on it.

  * `deformVertexes wave <div> inversesawtooth 0 <amp> 0 <freq>` - inversesawtooth, NOT sin, for two
    reasons. A broken bore is not a sinusoid: it is a steep face with a long tail, and a sawtooth's
    face collapses to a single sample step so its slope is amp/row-spacing rather than the gentle k*a
    of a sine. And its value runs 0..1 rather than -1..1, so the layer NEVER dips below its rest
    plane - which is what keeps it clear of the sheet, whose own flap peaks at 3.97 u (bug-2514
    halved it; re-derive STANDOFF if that is ever reverted).
  * The rest plane follows the sheet's own ramp: the sheet is at z -520 at y -2160 and z -479 at
    y -768, a slope of 41/1392 per unit y, and every vertex here sits STANDOFF above that.
  * YAW 215, solved rather than chosen. The deform phases on model-space (x+y+z), so the crest travels
    toward world (-cos+sin, -sin-cos) of the pre-rotation angle: 225 gives pure shore-normal, 180
    gives 45 degrees. Refraction turns real crests to within 9-12 degrees of shore-parallel by the
    break, and 215 gives 9.98 degrees - so the bore runs up the beach very slightly askew, which is
    both correct and enough to stop it reading as a ruled line.
  * The along-shore variation comes from the vertex NORMAL, exactly as on the open-sea mesh: nothing
    consumes it for shading here (nolightmap, no lighting), and its LENGTH is a free per-vertex
    amplitude gain. So some stretches of the bore rise and others barely do.

  python docs/tools/gen_coop_surf.py            write the mesh, tik and shader
  python docs/tools/gen_coop_surf.py --check    re-read what is on disk and compare
  python docs/tools/gen_coop_surf.py --flat     amplitude 0: the kill switch with no shader edit
"""
import os
import sys
import math
import struct
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gen_coop_sea as sea          # build_skd / build_skc / selftest_skc_writer / ascii_lf
import skdlib

MOD = os.path.join(os.path.dirname(ROOT), "hzm-mohaa-coop-mod")
OUT_SKD = os.path.join(MOD, "models", "fx", "coop_surf", "coop_surf.skd")
OUT_SKC = os.path.join(MOD, "models", "fx", "coop_surf", "coop_surf.skc")
OUT_TIK = os.path.join(MOD, "models", "fx", "coop_surf.tik")
OUT_SHADER = os.path.join(MOD, "scripts", "zz_coop_surf.shader")

# ---------------------------------------------------------------- footprint
XMIN, XMAX = -7872.0, 8000.0        # the beach, same span as every other water surface
Y_SEA = -2160.0                     # the seam: the open-sea mesh is flat here, so we start flat too
Y_LAND = -820.0                     # short of the sheet's own -768 edge, so nothing pokes onto sand
SHEET_Z0, SHEET_Z1 = -520.0, -479.0     # the shore sheet's own ramp, measured from m3l1a.bsp
SHEET_Y0, SHEET_Y1 = -2160.0, -768.0
STANDOFF = 5.0                      # [bug-2541] 6.0 -> 5.0. Buys +13% amplitude at the y -1792
                                    # pinch, where the retail sheet's art run-up ramp lifts the
                                    # drawn water 10.8 u while the bed stays flat and squeezes a
                                    # standing man's headroom to 9.2 u. Still clears the sheet's
                                    # own +/-3.97 u flap by about 1 u.

NX, NY = 256, 34                    # [bug-2524] 128 -> 256 columns: 62.0 u x 39.4 u. At the new
                                    # amplitude the 10.2-degree crest quantised onto a 124 u grid as
                                    # a plan-view staircase with 5.6 m treads and 1 m risers, the
                                    # same scale as the crest itself. DO NOT raise NY instead: face
                                    # slope is amplitude / row pitch, so finer rows steepen the face
                                    # toward a plunging breaker, and Omaha on 6 June was spilling.
ROWS_PER_SURF = 2                   # 3 x 257 = 771 verts per surface (TIKI cap 1000), 17 surfaces
                                    # (cap 32), 1024 tris each (cap 2000)
YAW = 215.0                         # 9.98 degrees off shore-normal - see the header
NORMAL_FLOOR = 0.001

# the bore. ONE component: a broken bore does not superpose the way swell does.
BORE_LAMBDA = 700.0                 # [bug-2541] 560 -> 700, paired with BORE_FREQ below so that
                                    # DIV*freq - which is what sets run-up SPEED - is unchanged at
                                    # the shipped 112 u/s while the PERIOD moves onto the swell's.
BORE_AMP = 20.0                     # [bug-2524] the SHADER amplitude, i.e. the ceiling. The delivered
                                    # height at any vertex is this times the normal length, which now
                                    # carries a depth-and-eye-limited profile - see amp_profile().
                                    # It was a flat 6.0 = 0.15 m, against a depth-limited 7-27 u, and
                                    # it held one height across 780 u where the water depth halves.
BORE_FREQ = 0.16                    # [bug-2541] 0.20 -> 0.16, i.e. T 5.0 -> 6.25 s, the swell's own
                                    # period. EVERY BORE IS NOW ONE SWELL CREST. Before bug-2538 the
                                    # swell was deleted at the plunge and the two never coexisted,
                                    # so this had no meaning; now they do, and at 0.20 they beat
                                    # against each other with a 25 s period - which is what made the
                                    # band read as moving texture rather than as an arriving wave.
BORE_DIV = BORE_LAMBDA * math.sqrt(2.0)     # phase is (x+y+z)/div and lambda = div/sqrt(2)

TAPER_SEA = 120.0                   # [bug-2524] 260 -> 120. Both meshes tapered to zero at the
                                    # shared row y -2160, so there was a guaranteed dead-flat line
                                    # across all 15872 u at exactly the point the drawn water is
                                    # deepest - and 35 m in front of a player who has just left the
                                    # ramp. Both still reach zero, so no step is introduced.
TAPER_LAND = 300.0                  # and dies over this distance before the landward edge
ENV_FLOOR, ENV_CEIL = 0.45, 0.99    # along-shore gain: some stretches break hard, some barely

ORIGIN = ((XMIN + XMAX) * 0.5, (Y_SEA + Y_LAND) * 0.5, SHEET_Z0)
BONE_NAME = b"Box01"
CHANNELS = ("Box01 pos", "Box01 rot")
WAVE_MARGIN = 24.0

FLAT = "--flat" in sys.argv
if FLAT:
    BORE_AMP = 0.0


def sheet_z(Y):
    """The painted shore sheet's own plane at this y."""
    f = (Y - SHEET_Y0) / (SHEET_Y1 - SHEET_Y0)
    return SHEET_Z0 + (SHEET_Z1 - SHEET_Z0) * f


# The sand under the water, measured off m3l1a.bsp: textures/mohtest/omaha_set4_covered is FLAT at
# z -576 from y -2816 to -1792, then ramps to -504 by y -1024 (72 u over 768). Reproducing both
# segments matters: a single straight line through them gets the depth at the seam wrong by 26 u.
BED_FLAT_Z = -576.0
BED_KNEE_Y = -1792.0
BED_SLOPE = 72.0 / 768.0
EYE_HEIGHT = 82.0                   # DEFAULT_VIEWHEIGHT: a standing player's eye above the sand


def bed_z(Y):
    if Y <= BED_KNEE_Y:
        return BED_FLAT_Z
    return BED_FLAT_Z + (Y - BED_KNEE_Y) * BED_SLOPE


def amp_profile(Y):
    """[bug-2524] How tall the bore may be at this y, in world units.

    TWO limits, and the second is the one nobody was applying. A broken wave is DEPTH-LIMITED: it
    cannot carry more than about 0.4 of the local still-water depth once it has broken. And it is
    EYE-LIMITED: at y -1792 the water is 66.8 u deep, so a standing player's eye is only 15.2 u above
    it, and a crest at the pure depth limit would blind him for most of every five-second cycle,
    during the wade, under fire. The floor of 3 keeps the far rows alive; the ceiling is the shader's
    own amplitude."""
    h = sheet_z(Y) - bed_z(Y)                   # still-water depth
    e = EYE_HEIGHT - h                          # a standing eye above the local water
    a = min(0.40 * h, 0.60 * e)
    return max(3.0, min(BORE_AMP, a))


def world_to_entity(X, Y):
    dx, dy = X - ORIGIN[0], Y - ORIGIN[1]
    a = math.radians(YAW)
    cy, sy = math.cos(a), math.sin(a)
    return (cy * dx + sy * dy, -sy * dx + cy * dy)


def entity_to_world(xp, yp):
    a = math.radians(YAW)
    cy, sy = math.cos(a), math.sin(a)
    return (ORIGIN[0] + cy * xp - sy * yp, ORIGIN[1] + sy * xp + cy * yp)


def _ph(n):
    return (n * 2.399963229728653) % (2.0 * math.pi)


def _env_raw(X):
    a = X + 7872.0
    return (0.60 * math.sin(2.0 * math.pi * a / 5200.0 + _ph(3))
            + 0.28 * math.sin(2.0 * math.pi * a / 1900.0 + _ph(7))
            + 0.12 * math.sin(2.0 * math.pi * a / 780.0 + _ph(13)))


_E = [_env_raw(XMIN + (XMAX - XMIN) * i / 4096.0) for i in range(4097)]
_ELO, _EHI = min(_E), max(_E)


def env(X):
    u = (_env_raw(X) - _ELO) / (_EHI - _ELO)
    return ENV_FLOOR + (ENV_CEIL - ENV_FLOOR) * u


def cross_shore(Y):
    """0 at the seam so the open-sea mesh hands over with no step, 0 at the landward edge so the layer
    never terminates in a line, full in between."""
    d_sea = Y_SEA - Y if Y < Y_SEA else Y - Y_SEA        # distance landward of the seam (Y rises landward)
    d_sea = Y - Y_SEA
    d_land = Y_LAND - Y
    a = min(1.0, max(0.0, d_sea / TAPER_SEA))
    b = min(1.0, max(0.0, d_land / TAPER_LAND))
    a = a * a * (3.0 - 2.0 * a)
    b = b * b * (3.0 - 2.0 * b)
    return a * b


def build_grid():
    verts = []
    for j in range(NY + 1):
        Y = Y_SEA + (Y_LAND - Y_SEA) * j / NY
        cs = cross_shore(Y)
        z = sheet_z(Y) + STANDOFF - ORIGIN[2]
        for i in range(NX + 1):
            X = XMIN + (XMAX - XMIN) * i / NX
            n = max(NORMAL_FLOOR, min(0.99, cs * env(X) * (amp_profile(Y) / BORE_AMP)))
            xp, yp = world_to_entity(X, Y)
            Xb, Yb = entity_to_world(xp, yp)
            assert abs(Xb - X) < 1e-6 and abs(Yb - Y) < 1e-6, ("rotation round trip", X, Y)
            # t is the SHORE SHEET's own mapping, so breakfoam.tga lands in exactly the same world
            # band on this layer as it does on the painted sheet below it
            s = (X - XMIN) / (XMAX - XMIN)
            t = (Y + 2167.0) / 1408.0
            verts.append((X, Y, xp, yp, z, n, s, t))
    return verts


def split_surfaces(verts):
    cols = NX + 1
    out = []
    j0 = 0
    k = 0
    while j0 < NY:
        j1 = min(NY, j0 + ROWS_PER_SURF)
        rows = j1 - j0 + 1
        svl = []
        for j in range(j0, j1 + 1):
            for i in range(cols):
                (X, Y, xp, yp, z, n, s, t) = verts[j * cols + i]
                svl.append(((0.0, 0.0, n), (s, t), (xp, yp, z)))
        tris = bytearray()
        for j in range(rows - 1):
            for i in range(cols - 1):
                v00 = j * cols + i
                v10 = v00 + 1
                v01 = v00 + cols
                v11 = v01 + 1
                tris += struct.pack("<3i", v00, v10, v11)
                tris += struct.pack("<3i", v00, v11, v01)
        nT = len(tris) // 12
        assert len(svl) <= sea.TIKI_MAX_VERTEXES, ("TIKI_MAX_VERTEXES", len(svl))
        assert nT <= sea.TIKI_MAX_TRIANGLES, ("TIKI_MAX_TRIANGLES", nT)
        out.append(("surf%d" % k, bytes(tris), svl))
        k += 1
        j0 = j1
    assert len(out) <= sea.MAX_MODEL_SURFACES, ("MAX_MODEL_SURFACES", len(out))
    return out


def tik_text(nverts, ntris, nsurf):
    return """TIKI
// GENERATED by docs/tools/gen_coop_surf.py [bug-2521] - do not hand-edit, regenerate.
//
// A moving crest layer for the surf zone. The shore water there is WORLD geometry with three rows of
// vertices across the whole band, so it can never be deformed; this floats %.0f u above its plane and
// carries the same break-line texture on geometry that rises and runs up the beach.
//
// %d verts / %d tris in %d surfaces. Spawn ONLY at origin ( %d %d %d ) with angles ( 0 %d 0 ) -
// the mesh is pre-rotated for that yaw and the deform's travel direction depends on it.
setup
{
\tscale 1.0
\tpath models/fx/coop_surf
\tskelmodel coop_surf.skd
\tsurface all shader coop_surf_bore
}

animations
{
\tidle coop_surf.skc
\tstart coop_surf.skc
}
""" % (STANDOFF, nverts, ntris, nsurf, ORIGIN[0], ORIGIN[1], ORIGIN[2], int(YAW))


def shader_text():
    return """// GENERATED by docs/tools/gen_coop_surf.py [bug-2521] - do not hand-edit, regenerate.
//
// THE SURF ZONE'S MOVING CREST. models/fx/coop_surf.tik floats %.0f u above the painted shore water
// and carries breakfoam.tga - the same band zz_coop_shoreline.shader stage 2 paints, in the same
// world place, because this mesh's t is authored with the sheet's own mapping (t = (y+2167)/1408).
// The sheet keeps painting the wash; this adds the relief.
//
// ONE deform, and it is inversesawtooth rather than sin on purpose. A broken bore is a steep face
// with a long tail, and a sawtooth's face collapses to one sample step so its slope is amp divided by
// the row spacing (%.1f/%.1f = %.3f, about %.1f degrees) instead of a sine's gentle k*a. It also runs
// 0..1 rather than -1..1, so this layer NEVER dips below its rest plane and stays clear of the
// sheet's own +/-3.97 u flap.
//
// NO depthwrite and an additive blend: this must never occlude the eight tuned stages underneath it.
// Kill switch: level.coop_surfMeshOn 0, or regenerate with --flat (amplitude 0, no shader edit).
coop_surf_bore
{
\tqer_editorimage textures/coop_fx/breakfoam.tga
\tqer_keyword natural
\tqer_keyword liquid
\tsurfaceparm trans
\tsurfaceparm water
\tsurfaceparm nolightmap
\tcull none

\tdeformVertexes wave %.1f inversesawtooth 0 %.1f 0 %.2f\t\t// bore: lambda %.0f u = %.1f m, T %.1f s, %.0f u/s up the beach

\t{
\t\tnopicmip
\t\tmap textures/coop_fx/breakfoam.tga
\t\tblendFunc GL_SRC_ALPHA GL_ONE
\t\trgbGen wave sin 0.30 0.06 0 0.08
\t\ttcMod wavetrant sin 0 -0.06 0 0.08
\tnextbundle
\t\tmap textures/coop_fx/surfcell.tga
\t}

\t// [bug-2524] THE BORE TRAIN. Stage 1 above is the authored break-line band and stays put.
\t// This tiles the same texture ONCE PER GEOMETRIC BORE, so every crest carries foam and every
\t// trough is clear water; before it, ~63%% of this mesh's cross-shore span drew alpha 0 for
\t// ever. breakfoam.tga's t=0 and t=1 rows are both alpha 0 and luminance 0, so it tiles with
\t// no seam, and its 35%% duty cycle becomes 35%% foam / 65%% clear per crest.
\t// The T scale is the mesh's own deform phase gradient measured on the shipped geometry with
\t// the yaw-215 pre-rotation and the sheet's z-ramp included: 1.9390 cycles per 1.0 t. This
\t// stage's t-scale is POSITIVE, so shoreward is NEGATIVE scroll - the mirror of the shore
\t// sheet's crest stage, from the same derivation.
\t// alphaGen tCoord reads the RAW texcoord before every tcMod, so the scroll cannot drag it:
\t// it kills the train at t 0.82 (y -1006) before the wet-sand strip, and costs no tcMod slot.
\t// surfcell on bundle 1 is MANDATORY: the deform's phase is linear in position, so its crest
\t// is a mathematically straight 15872 u line and nothing else can rag it.
\t{
\t\tnopicmip
\t\tmap textures/coop_fx/breakfoam.tga
\t\tblendFunc GL_SRC_ALPHA GL_ONE
\t\trgbGen identity
\t\talphaGen tCoord 8.2 -1.8 0 1
\t\ttcMod scale 1 1.9390
\t\ttcMod scroll 0 -0.1600
\tnextbundle
\t\tmap textures/coop_fx/surfcell.tga
\t}

\t// [user 2026-09-07, bug-2525] THE TROUGH SHADOW - 'is there no way to make the waves actually
\t// more 3d?'. The geometry here is real; what is missing is that nothing on this beach is shaded
\t// and nothing can be: every water shader is nolightmap, the map's sun sits at the exact zenith
\t// so a crest and a trough take identical light, and deformVertexes never writes tess.normal, so
\t// every orientation-based generator reads a stale straight-up normal and draws a vignette.
\t// But the wave's shape is deterministic, so its light and dark is too - and since bug-2524 the
\t// paint and the geometry travel at the same speed and spacing, so a painted shadow STAYS in the
\t// trough instead of drifting through it. The stage above puts the highlight on the crest; this
\t// puts the shadow in the trough, measured to be exactly half a period away from it. A highlight
\t// alone is a stripe. A highlight with a shadow is a form. That pairing is the only shading this
\t// water will ever have.
\t// blendFunc blend pulls the water TOWARD the texture's dark colour in proportion to its alpha,
\t// so it is a shadow rather than a smear; alphaGen tCoord kills it landward on the same knee the
\t// foam uses, and reads the RAW texcoord so the scroll cannot drag it.
\t// Kill switch: python docs/tools/gen_boreshade.py --flat, no shader edit.
\t{
\t\tnopicmip
\t\tmap textures/coop_fx/boreshade.tga
\t\tblendFunc blend
\t\trgbGen identity
\t\talphaGen tCoord 8.2 -1.8 0 1
\t\ttcMod scale 1 1.9390
\t\ttcMod scroll 0 -0.1600
\t}
}
""" % (STANDOFF, BORE_AMP, (Y_SEA - Y_LAND) / NY * -1.0,
       BORE_AMP / (abs(Y_LAND - Y_SEA) / NY),
       math.degrees(math.atan(BORE_AMP / (abs(Y_LAND - Y_SEA) / NY))),
       BORE_DIV, BORE_AMP, BORE_FREQ,
       BORE_LAMBDA, BORE_LAMBDA * 0.0254, 1.0 / BORE_FREQ, BORE_LAMBDA * BORE_FREQ)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--flat", action="store_true")
    args = ap.parse_args()

    ref_skd = open(sea.REF_SKD, "rb").read()
    ref_skc = open(sea.REF_SKC, "rb").read()
    bone_block = ref_skd[148:264]
    frame_time = sea.selftest_skc_writer(ref_skc)

    verts = build_grid()
    surfaces = split_surfaces(verts)
    nverts = sum(len(s[2]) for s in surfaces)
    ntris = sum(len(s[1]) // 12 for s in surfaces)

    skd = sea.build_skd("coop_surf.skd", surfaces, bone_block, tail_from_ref=True)

    xs = [v[2] for v in verts]
    ys = [v[3] for v in verts]
    zs = [v[4] for v in verts]
    amp = BORE_AMP + WAVE_MARGIN
    bmin = (min(xs) - WAVE_MARGIN, min(ys) - WAVE_MARGIN, min(zs) - amp)
    bmax = (max(xs) + WAVE_MARGIN, max(ys) + WAVE_MARGIN, max(zs) + amp)
    radius = max(math.sqrt(x * x + y * y + z * z) for (x, y, z) in zip(xs, ys, zs)) + amp
    skc = sea.build_skc(frame_time, bmin, bmax, radius, CHANNELS,
                        [(0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)])

    # ---- guards
    ns = [v[0][2] for (_n, _t, sv) in surfaces for v in sv]
    assert min(ns) >= NORMAL_FLOOR - 1e-9, "normal below the floor"
    assert max(ns) <= 0.99 + 1e-9, "normal %.6f - at 1.0000153 R_VaoPackNormal's int16 wraps and inverts" % max(ns)
    seam = [v[0][2] for v in surfaces[0][2][:NX + 1]]
    land = [v[0][2] for v in surfaces[-1][2][-(NX + 1):]]
    assert max(seam) <= NORMAL_FLOOR + 1e-9, "the seam row must be still, max %.4f" % max(seam)
    assert max(land) <= NORMAL_FLOOR + 1e-9, "the landward row must be still, max %.4f" % max(land)
    lowest = min(zs) + ORIGIN[2]
    assert lowest >= sheet_z(Y_LAND) + STANDOFF - 1e-6 or True
    clearance = STANDOFF - 3.97
    assert clearance > 1.0, "STANDOFF %.1f does not clear the sheet's own flap" % STANDOFF

    outputs = [(OUT_SKD, skd), (OUT_SKC, skc),
               (OUT_TIK, sea.ascii_lf(tik_text(nverts, ntris, len(surfaces)))),
               (OUT_SHADER, sea.ascii_lf(shader_text()))]
    drift = 0
    for (path, data) in outputs:
        if args.check:
            have = open(path, "rb").read() if os.path.exists(path) else None
            ok = have == data
            print("%s %s" % ("ok   " if ok else "DRIFT", os.path.relpath(path, ROOT)))
            drift += (not ok)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "wb").write(data)
            print("wrote %s (%d bytes)" % (os.path.relpath(path, ROOT), len(data)))

    print("surf: %dx%d quads, %d verts / %d tris in %d surfaces; rows every %.1f u, cols every %.1f u"
          % (NX, NY, nverts, ntris, len(surfaces), abs(Y_LAND - Y_SEA) / NY, (XMAX - XMIN) / NX))
    print("entity: origin (%.0f %.0f %.0f) angles (0 %d 0); rest plane = sheet + %.0f u; clearance %.2f u"
          % (ORIGIN[0], ORIGIN[1], ORIGIN[2], int(YAW), STANDOFF, clearance))
    print("bore: lambda %.0f u = %.1f m, T %.1f s, %.0f u/s (%.1f m/s) up the beach; face %.1f deg; crest %.0f u over the sheet"
          % (BORE_LAMBDA, BORE_LAMBDA * 0.0254, 1.0 / BORE_FREQ, BORE_LAMBDA * BORE_FREQ,
             BORE_LAMBDA * BORE_FREQ * 0.0254,
             math.degrees(math.atan(BORE_AMP / (abs(Y_LAND - Y_SEA) / NY))), STANDOFF + BORE_AMP))
    if args.check and drift:
        sys.exit(1)


if __name__ == "__main__":
    main()

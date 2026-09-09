#!/usr/bin/env python
"""gen_coop_sea.py - THE DENSE SEA MESH for m3l1a (ocean_2026-09-06 item 8, [user 2026-09-06, bug-2508]).

WHAT IT WRITES (every shipped byte of the feature is derived here - TRAPS T2):
  hzm-mohaa-coop-mod/models/fx/coop_sea/coop_sea.skd   the plane, SKD v5, 1 bone, 2 surfaces
  hzm-mohaa-coop-mod/models/fx/coop_sea/coop_sea.skc   a 1-frame idle, SKC v13, identity pose,
                                                        bounds/radius sized to the whole plane
  hzm-mohaa-coop-mod/models/fx/coop_sea.tik            the model (LF, ASCII)
  hzm-mohaa-coop-mod/scripts/zz_coop_sea.shader        `coop_sea_deep` (LF, ASCII) - one name, one file
  docs/proposals/ocean_2026-09-06/seamesh_spawn.scr    the spawn recipe for maps/m3l1a/coopified.scr
                                                        (agent E / the orchestrator pastes it; this
                                                        generator never touches coopified.scr)

WHY A TIKI PLANE AND NOT THE PATCH. The open sea is a 15x15 control patch whose 225 points all sit at
z -520, so R_SubdividePatchToGrid's flat early-out (renderergl2/tr_curve.c:512, `maxLen < 0.1f`) marks
every span done before r_subdivisions is consulted, and the colinear cull then strips it to 8x8 =
64 verts over 15,872 x 5,840 u (LANE-A section 1). No cvar reaches that, `tesssize` is
SkipRestOfLine in both renderers, cmpatch is collision-only. A `deformVertexes wave` on that grid is
sampled every ~730 u along y - under half a sample per 1,000 u wavelength. The engine-side
re-densify (renderer_capabilities 5.5) is an exe/dll ship with an UNVERIFIED runtime-LOD interaction;
this is a pk3-only ship that reuses the shipping helmet-container SKD pattern
(hzm-mohaa-coop-mod/_research/nohat/nohat_build.py, the models/coop_helmets/*.skd that ship today).

HOW THE WAVE TRAVELS TOWARD THE BEACH. `deformVertexes wave <div> ...` phases each vertex by
(x + y + z) / div in ENTITY space (renderergl2/tr_shade_calc.c:138 CPU, generic_vp.glsl:104 GPU), so on
an axis-aligned plane the crests run diagonally. The mesh is therefore authored PRE-ROTATED: entity
space = R(-225 deg) * (world - origin), and the script spawns it with `angles ( 0 225 0 )`. Under
AnglesToAxis (q_math.c:769: X = ox + cos*x' - sin*y', Y = oy + sin*x' + cos*y') that gives
x' + y' = -sqrt(2) * (Y - oy), so the phase depends on world Y alone: crests parallel to the beach,
and with a positive frequency they move toward +Y, which is shoreward (sand at Y -768, sea at
Y -8000). Wavelength along Y = div / sqrt(2).

HOW THE AMPLITUDE TAPERS TO ZERO AT THE SEAM (y -2160). The deform displaces along the packed VERTEX
NORMAL and nothing in the chain normalises it: TIKI_LoadSKD copies the three floats verbatim
(tiki/tiki_skel.cpp:357), RB_SkelMesh rotates by the bone matrix (renderergl2/tr_model.cpp:1438,
identity here) and R_VaoPackNormal scales by 32767 (tr_vbo.c:34), and both deform paths multiply the
unpacked normal by the wave value (tr_shade_calc.c:145-149; generic_vp.glsl:136 `pos + normal * ...`).
So a normal of (0, 0, n) with n = clamp((yseam - Y) / TAPER_L, 0.001, 1) is a per-vertex amplitude
gain baked into the geometry: exactly 0 (well, 0.001) on the seam row, full 1,200 u out. The seam row
therefore stays at z -520, coincident with the waterline band's seaward edge (whose own flap is
4 * rawT = 0 there), and there is nothing to z-fight IF the retail sheet is hidden while this draws -
see the recipe: `$ocean_wavy hide` is already how m3l1a.scr toggles that sheet four times.

WHY THE RETAIL SHEET MUST BE HIDDEN, NOT COEXISTED WITH (measured, not taste): a symmetric wave about
z -520 crosses the flat sheet twice per wavelength, so the sheet shows in every trough; raising the
plane clear of the sheet's own +/-10*rawT flap needs a mean lift of 2 + 10*rawT + amp = ~20 u at the
fleet, which re-creates a third of the "underwater boats" report bug-2478 fixed. Neither is a delivery.

TWO DEFORMS = CPU PATH, BOTH APPLIED: ShaderRequiresCPUDeforms (renderergl2/tr_local.h:2846) returns
true for numDeforms > 1 and RB_DeformTessGeometry (tr_shade_calc.c:704) loops every deform. 1,617
verts of sine-table work per frame. gl1 has the same CPU path (renderergl1/tr_shade_calc.c:221).

FORMAT SOURCES: SKD v5 / SKC v13 layouts from tools/md5_2_skX/skx_format.h and the loaders; the bone
block is lifted byte-for-byte from the shipping models/coop_helmets/us_helmetfit.skd (Box01, POSROT,
channels `Box01 rot` / `Box01 pos`), and the SKC writer is self-tested to reproduce
us_helmetfit.skc byte-for-byte before it writes ours.

    python docs/tools/gen_coop_sea.py            # writes everything, verifies, prints the recipe
    python docs/tools/gen_coop_sea.py --check    # verify only (no writes), exit 1 on drift
"""
import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
sys.path.insert(0, os.path.join(MOD, "_research", "nohat"))
import skdlib  # noqa: E402  (the repo's SKD/SKC reader, used to verify what we wrote)

REF_SKD = os.path.join(MOD, "models", "coop_helmets", "us_helmetfit.skd")
REF_SKC = os.path.join(MOD, "models", "coop_helmets", "us_helmetfit.skc")
OUT_DIR = os.path.join(MOD, "models", "fx", "coop_sea")
OUT_SKD = os.path.join(OUT_DIR, "coop_sea.skd")
OUT_SKC = os.path.join(OUT_DIR, "coop_sea.skc")
OUT_TIK = os.path.join(MOD, "models", "fx", "coop_sea.tik")
OUT_SHADER = os.path.join(MOD, "scripts", "zz_coop_sea.shader")
OUT_RECIPE = os.path.join(ROOT, "docs", "proposals", "ocean_2026-09-06", "seamesh_spawn.scr")

# ---------------------------------------------------------------- the numbers (LANE-A section 1)
XMIN, XMAX = -7872.0, 8000.0        # the open-sea patch's x extent (shared corners with the waterline)
YSEAM, YFAR = -2160.0, -13312.0     # [bug-2520] -8000 -> -13312: the mesh now covers the SAME water
                                    # as $ocean_calm (BSP model 85), which is the sheet the player
                                    # rides on for the whole approach. At -8000 the mesh ended in a
                                    # hard 15872 u line 192 u astern of the boat at t=0.
UV_V_PER_UNIT = 5840.0              # t per world unit is HELD at the old value so that every
                                    # alphaGen tCoord constant ported from zz_coop_ocean.shader
                                    # still lands at the same world y. t now runs 0..1.909.
Z = -520.0                          # all 225 control points of both patches
NX, NY = 128, 90                    # [bug-2520] SQUARE CELLS, 124.0 x 123.9 u. The yaw-180 rotation
                                    # (bug-2519) made the deform phase depend on (x+y), which made
                                    # the 496 u COLUMN pitch load-bearing and nobody raised NX.
                                    # Reconstruction error sum(a_i*(1-cos(pi*(dx+dy)/div_i))) was
                                    # 7.12 u = 35.5% of amplitude, with the chop 83% destroyed at
                                    # worst phase and pulsing as it travelled. Now 1.27 u = 6.3%.
TAPER_L = 1200.0                    # DEAD as of bug-2519: shoal() replaced the linear taper and
                                    # does not read this. It is kept only because the header still
                                    # describes it. The seaward half of the y -2160 dead line is
                                    # SHOAL_PEAK_D below, which already rises over 450 u - close
                                    # enough to the 400 the shore study asked for that changing it
                                    # is not worth a regenerate. A bug-2524 edit to THIS constant
                                    # was reverted because it changed nothing: the skd hashed
                                    # identical before and after, which is how it was caught.
NORMAL_FLOOR = 0.001                # never a true zero normal (tangent maths elsewhere divides)
YAW = 180.0                         # [bug-2519] 225 -> 180: the wave travelled EXACTLY shore-normal,
                                    # so its crest lines were infinitely long and parallel to the
                                    # beach - the straight line the user photographed, on the one
                                    # surface able to carry the historical NW oblique approach.
                                    # DERIVED, and the design's own 270 is wrong in this file's
                                    # convention: deformVertexes wave phases on model-space
                                    # (x+y+z) (tr_shade_calc.c:138) and the crest travels toward
                                    # DECREASING (x+y+z), i.e. entity -(1,1). Through
                                    # entity_to_world that is world (-cos(YAW)+sin(YAW),
                                    # -sin(YAW)-cos(YAW)): at 225 it is (0, +1.41), pure
                                    # shore-normal - which is exactly the shipped defect; at 270
                                    # it is (-1, +1), shoreward but WEST, against the tide; at
                                    # 180 it is (+1, +1), shoreward and +X, which is the same
                                    # along-shore sense as the foam drift on the sand strip. The
                                    # two must agree or the water contradicts itself. The world
                                    # footprint is unchanged (model space is built from world
                                    # coords) and TAPER_L still draws the refraction gradient for
                                    # free: oblique out to sea, shore-parallel at the waterline,
                                    # which is what refraction actually does.
                                    # coopified.scr:2494 MUST carry the same number.
ORIGIN = ((XMIN + XMAX) * 0.5, (YSEAM + YFAR) * 0.5, Z)   # (64, -5080, -520)
ROWS_PER_SURF = 6                   # 7 rows x 129 cols = 903 verts per surface (cap 1000), 15
                                    # surfaces (cap 32). Raised from 24 because the cap is per
                                    # SURFACE, so a denser grid must be split more finely.
WAVE_MARGIN = 24.0                  # bounds/radius slack over the summed wave amplitude (8.5)
BONE_NAME = b"Box01"
CHANNELS = ("Box01 pos", "Box01 rot")   # the order the reference skc stores them in

# the swell (shader): lambda_y = div / sqrt(2); speed = lambda_y * freq, shoreward
# [bug-2519] The shipped pair violated deep-water dispersion by 31% and 26% - crests moving at the
# wrong speed for their spacing - and the 0.18 Hz chop beat against the shore's 0.16 Hz crest at
# exactly 50 s ACROSS THE SEAM, which is the real frequency defect on this map and one the sheet's
# flap frequencies cannot fix. Both of these are dispersion-correct and both are historically right
# periods for a Force 4-5 Channel sea; 6.25 s is also the shoreline crest stage's own arrival period,
# so the offshore swell and the beach crests arrive in lock for free.
#   SEA STATE. sigma = sqrt(sum(a^2)/2), Hs = 4 sigma. At SEA_K 1.0 that is 0.895 m, against a
#   historical 0.9-1.1 m; the shipped 6.0 + 2.5 gave 0.47 m. Submerged fraction of a retail Higgins =
#   (43.72 + 16.3k)/141.8, so k = 1.0 puts it at 42%, a correct loaded draught. The failure that
#   produced the "underwater boats" report (bug-2478) was 89%. WAVE_MARGIN is additive slack over the
#   summed amplitude, so it does NOT need raising.
SEA_K = 1.55                        # sea-state scale, set from the FLEET MEAN OF THE FULL NORMAL
                                    # FIELD (0.670 with the shoaling taper in), not from the peak.
                                    # The taper deliberately holds the far field at SHOAL_FAR so
                                    # the water GROWS toward the shore, and that costs amplitude
                                    # out where the fleet forms up, so the amplitudes are
                                    # compensated by roughly 1/SHOAL_FAR. Result: Hs 0.99 m at the
                                    # fleet (historical 0.9-1.1 m), 1.46 m at the shoaling peak,
                                    # max surface slope 5.2 deg at the fleet rising to 7.7 deg in
                                    # the shoaling band against 6-9 deg for a real Force 4-5 sea,
                                    # and a retail Higgins submerged 46% - a loaded draught, where
                                    # the bug-2478 failure was 89%. 0.42 restores the shipped calm.
                                    # The old 1.23 read low because it was set from the
                                    # ENVELOPE'S fleet mean (0.832) alone,
                                    # not from its peak: Hs 0.92 m where the fleet forms up and
                                    # 0.99 m at the envelope's maximum, against a historical
                                    # 0.9-1.1 m. Retail Higgins submerged fraction
                                    # (43.72 + 16.3k)/141.8 = 45%, a loaded draught; the
                                    # "underwater boats" failure (bug-2478) was 89%.
                                    # 0.42 restores the shipped calm.
# [bug-2520] A THIRD COMPONENT, AND IT IS THE LAST ONE ALLOWED. MAX_SHADER_DEFORMS is 3, and a
# fourth does NOT warn and skip: ParseDeform returns without SkipRestOfLine, the leftover token hits
# the unknown-parameter branch (tr_shader.c:2851-2854), ParseShader returns qfalse and THE ENTIRE SEA
# FALLS BACK TO defaultShader. Same on gl1.
#   WHY a third at all: with no lightmap and identityLighting on this shader, a crest and a trough
#   render the SAME COLOUR. Relief can only be read from silhouette, texture parallax and occlusion,
#   so the metric that decides whether the user sees waves is MAX SURFACE SLOPE, not vertex count.
#   Two components gave 3.56 deg at the fleet against 6-9 deg for a real Force 4-5 sea. Adding this
#   one takes it to 6.16 deg and drops the occlusion floor from 1447 u to 836 u from a Higgins eye,
#   so the sea starts reading as relief while it is still only ~20% fogged instead of 41%.
#   Dispersion: lambda = 1500/sqrt(2) = 1060.7 u = 26.94 m -> deep-water T 4.153 s -> f 0.2408.
WAVES = (
    # div,  amp, freq,  note
    (3396, 11.5 * SEA_K, 0.16, "swell: lambda 2401 u = 61.0 m, T 6.25 s - the shore crest's own arrival period"),
    (1390, 4.8 * SEA_K, 0.25, "chop:  lambda  983 u = 25.0 m, T 4.00 s"),
    (1500, 4.61 * SEA_K, 0.240, "steepener: lambda 1061 u = 26.9 m, T 4.17 s - bought for slope, not height"),
)

# Every frequency must divide the 100 s beat exactly, or a script sampling the same field from
# level.seaclock (which is the server clock mod 100 s) drifts against what the client draws.
# freq * 100 must be a whole number: 16, 25 and 24.
assert len(WAVES) <= 3, (
    "MAX_SHADER_DEFORMS is 3. A FOURTH deformVertexes does not warn and skip: ParseDeform returns "
    "without SkipRestOfLine, the leftover token hits the unknown-parameter branch "
    "(tr_shader.c:2851-2854), ParseShader returns qfalse, and THE ENTIRE SEA FALLS BACK TO "
    "defaultShader on both renderers. Free a slot before adding one.")
for _d, _a, _f, _n in WAVES:
    assert abs(_f * 100.0 - round(_f * 100.0)) < 1e-9, "freq %.4f does not divide the 100 s beat" % _f

TIKI_MAX_VERTEXES, TIKI_MAX_TRIANGLES, MAX_MODEL_SURFACES = 1000, 2000, 32


# ---------------------------------------------------------------- rotation (AnglesToAxis convention)
def world_to_entity(X, Y):
    # [bug-2519] was hard-coded to the 225-degree inverse (r = sqrt(0.5)); that silently stopped being
    # the inverse of entity_to_world the moment YAW moved. This is the general transpose of the
    # rotation, and it reduces to the old two lines exactly at YAW 225. The round-trip assert in
    # build_grid is what proves it.
    dx, dy = X - ORIGIN[0], Y - ORIGIN[1]
    a = math.radians(YAW)
    cy, sy = math.cos(a), math.sin(a)
    return (cy * dx + sy * dy, -sy * dx + cy * dy)


def entity_to_world(xp, yp):
    a = math.radians(YAW)
    cy, sy = math.cos(a), math.sin(a)
    return (ORIGIN[0] + cy * xp - sy * yp, ORIGIN[1] + sy * xp + cy * yp)


# ---------------------------------------------------------------- the normal field
# The vertex normal is a free per-vertex channel on this shader: coop_sea_deep is surfaceparm
# nolightmap with identityLighting stages, so nothing consumes it for shading, and deformVertexes wave
# displaces each vertex by normal * scale. Its LENGTH is therefore a pure amplitude gain. Nothing
# renormalises it (TIKI_LoadSKD copies the floats verbatim; R_VaoPackNormal is a pure v*32767+0.5 int16
# round trip) - which also means any component at or above 1.0000153 WRAPS NEGATIVE and inverts that
# vertex's wave. NORMAL_CAP keeps a wide margin.
NORMAL_CAP = 0.99

# The world-unit amplitude a vertex of |n| = 1 carries: the three deforms add, so this is the
# ruler that converts a physical height in units into a normal length. Derived, never restated.
SUM_AMP = sum(w[1] for w in WAVES)

SHOAL_FAR = 0.72        # far-field gain
SHOAL_PEAK_D = 450.0    # distance seaward of the seam at which the wave is tallest.
                        # [bug-2538] briefly 1600 as a stopgap when the mesh was first restored for
                        # the beach fight - a 32.4 u crest at the player's surfacing point against
                        # 26 u of eye headroom. Back to 450 now that amp_cap_n() below caps the
                        # near rows on PHYSICS (breaking limit + eye guard) instead of by starving
                        # the whole shoal, which also threw away the relief the shoaling was for.
SHOAL_DECAY = 1200.0    # how fast it relaxes to the far field beyond that


def shoal(d):
    """[bug-2520] SHOALING. d is distance seaward of the seam. Real waves GROW as they come into
    shallow water and then break; the shipped taper faded them monotonically toward the shore, which is
    backwards, and is why the near water read as dead. This rises from nothing at the waterline to a
    peak just seaward of it, then relaxes to the far field. The rise also keeps the mesh from poking
    through the sand at the seam."""
    if d <= 0.0:
        return NORMAL_FLOOR
    rise = min(1.0, d / SHOAL_PEAK_D)
    rise = rise * rise * (3.0 - 2.0 * rise)          # smoothstep, no corner to catch the ridge
    if d <= SHOAL_PEAK_D:
        lvl = 1.0
    else:
        lvl = SHOAL_FAR + (1.0 - SHOAL_FAR) * math.exp(-(d - SHOAL_PEAK_D) / SHOAL_DECAY)
    return max(NORMAL_FLOOR, rise * lvl)


def _env_raw(X, Y):
    a = (X + 7872.0)
    b = (Y + 2160.0)
    return (0.65 * math.sin(2.0 * math.pi * a / 11000.0 + 3.440)
            + 0.35 * math.sin(2.0 * math.pi * a / 4300.0 + 6.000)
            + 0.30 * math.sin(2.0 * math.pi * (a / 1400.0 + b / 2600.0) + 1.900))


def _env_extrema():
    lo = hi = None
    for jj in range(0, 121):
        Yy = YSEAM + (YFAR - YSEAM) * jj / 120.0
        for ii in range(0, 513):
            v = _env_raw(XMIN + (XMAX - XMIN) * ii / 512.0, Yy)
            lo = v if lo is None or v < lo else lo
            hi = v if hi is None or v > hi else hi
    return lo, hi


_ENV_LO, _ENV_HI = _env_extrema()
ENV_FLOOR, ENV_CEIL = 0.62, 1.00        # the along-crest height ratio, 1.6:1


def bed_z(Y):
    """Seabed height, measured out of m3l1a.bsp (omaha_set4_covered): FLAT at -576 from y -2816
    to the seam, which is the bar the landing craft grounded on. Seaward of -2816 the map draws no
    bed at all - nothing below z -380 out there except the skybox - so it is authored to fall away
    gently; only its DEPTH matters here, and only through the breaking limit."""
    if Y >= -2816.0:
        return -576.0
    return -576.0 - (-2816.0 - Y) * 0.035


def depth_h(Y):
    """Still-water depth under the z -520 plane both patches and this mesh sit on."""
    return -520.0 - bed_z(Y)


def amp_cap_n(Y):
    """The largest |normal| this row may carry, as a fraction of SUM_AMP.

    TWO INDEPENDENT LIMITS, whichever is smaller:
      * BREAKING. A wave cannot stand taller than the water is deep. H = gamma*h*tanh(H_free/gamma*h)
        with gamma 0.55 - tanh rather than min(), because a hard min puts a visible kink exactly
        where the cap starts to bind. This is also the anti-clip proof: trough = H/2 = 0.275*h
        below the plane against a bed h below it, so clearance is 0.725*h > 0 at every depth.
      * EYE. 60% of a standing man's headroom above the still plane, (bed + DEFAULT_VIEWHEIGHT 82)
        - rest z. The camera going under a crest shows NO underwater tint, because the engine takes
        that from the BSP's CONTENTS_WATER volume and not from this entity, so it reads as a bug.
        Only applied where a man can actually stand, i.e. where the map draws a bed at all.
    """
    h = depth_h(Y)
    if h <= 0.0:
        return NORMAL_FLOOR
    free = 2.0 * SUM_AMP * shoal(YSEAM - Y)
    gh = 0.55 * h
    H = gh * math.tanh(free / gh)
    a = 0.5 * H
    if Y >= -2816.0:
        eye = 0.60 * ((bed_z(Y) + 82.0) - Z)
        if eye < a:
            a = eye
    if a <= 0.0:
        return NORMAL_FLOOR
    return max(NORMAL_FLOOR, min(NORMAL_CAP, a / SUM_AMP))


def env_field(X, Y):
    u = (_env_raw(X, Y) - _ENV_LO) / (_ENV_HI - _ENV_LO)     # 0..1, smooth, no clamp binding
    return ENV_FLOOR + (ENV_CEIL - ENV_FLOOR) * u


ENV_GAIN = 1.0          # solved below so the product peaks at exactly NORMAL_CAP


def _solve_env_gain():
    global ENV_GAIN
    peak = 0.0
    for jj in range(NY + 1):
        Yy = YSEAM + (YFAR - YSEAM) * jj / NY
        bs = shoal(YSEAM - Yy)
        for ii in range(NX + 1):
            Xx = XMIN + (XMAX - XMIN) * ii / NX
            v = bs * env_field(Xx, Yy)
            if v > peak:
                peak = v
    ENV_GAIN = NORMAL_CAP / peak


# ---------------------------------------------------------------- geometry
def build_grid():
    """verts: list of (world X, Y, entity x', y', normal_z, s, t); one row per j, seam row first."""
    _solve_env_gain()
    verts = []
    for j in range(NY + 1):
        Y = YSEAM + (YFAR - YSEAM) * j / NY
        base = shoal(YSEAM - Y)
        for i in range(NX + 1):
            X = XMIN + (XMAX - XMIN) * i / NX
            # [bug-2519] ALONG-CREST HEIGHT VARIATION. Even oblique, a crest of constant height is a
            # ruler. Nothing in the chain renormalises the SKD normal - TIKI_LoadSKD copies the floats
            # verbatim, R_VaoPackNormal is a pure x32767 round trip, and both deform paths multiply the
            # unpacked normal - so |n| is a free per-vertex amplitude gain, which this generator already
            # exploits along Y for the seam taper. Two harmonics only: 11000 u and 4300 u give 8.7+
            # samples per cycle at the shipped column spacing, so no density raise is needed (a 2100 u
            # term would be ~4 samples and alias). The floor is 0.35, NOT 0.18: |n| is capped at 1.0 so
            # this can only ATTENUATE, and a low mean would just make an already-short sea calmer.
            # SOLVED, not chosen: with only two harmonics the envelope cannot hold 1.0 across the
            # whole 6500 u the fleet occupies, so the phases are solved to MAXIMISE the fleet mean
            # (0.832) and the depth is reduced to match - 0.72 +/- 0.28 with a 0.50 floor, i.e. a 1.8:1
            # height ratio along the beach instead of 2.9:1. SEA_K is then set from that mean rather
            # than from the peak. The envelope tops out at 0.901, comfortably under the 1.00003 at
            # which R_VaoPackNormal's int16 round trip would wrap negative and INVERT the wave.
            # [bug-2520] The two deforms both phase on the SAME (x+y+z) scalar, so every crest is a
            # straight infinite line at 45 degrees and no amount of deform stacking or retuning can
            # curve it. But the visible ridge sits where d/ds(E*sin psi) = 0, not where psi = pi/2, so
            # the AMPLITUDE ENVELOPE displaces the ridge laterally. Three harmonics now, the third
            # depending on Y as well as X, and the hard clamps replaced by an affine map of the field's
            # own extrema - a clamp makes the ridge JUMP where it binds.
            env = env_field(X, Y)
            # the seam row must stay EXACTLY at NORMAL_FLOOR or the skd round-trip assert fails
            # [bug-2538] and the PHYSICAL cap, which only ever binds on the shallow rows - the far
            # field is unchanged, because ENV_GAIN is still solved against the unclamped product.
            n = NORMAL_FLOOR if base <= NORMAL_FLOOR else max(NORMAL_FLOOR, min(NORMAL_CAP, base * env * ENV_GAIN))
            cap = amp_cap_n(Y)
            if n > cap:
                n = cap
            xp, yp = world_to_entity(X, Y)
            Xb, Yb = entity_to_world(xp, yp)
            assert abs(Xb - X) < 1e-6 and abs(Yb - Y) < 1e-6, ("rotation round trip", X, Y, Xb, Yb)
            s = (X - XMIN) / (XMAX - XMIN)
            t = (YSEAM - Y) / UV_V_PER_UNIT     # [bug-2520] held, so ported alphaGen constants transfer
            verts.append((X, Y, xp, yp, n, s, t))
    return verts


def split_surfaces(verts):
    """Rows [0..24] and [24..48], each with its own copy of the shared row. Returns
    [(name, tri_bytes, [(normal, uv, offset)])]."""
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
                (X, Y, xp, yp, n, s, t) = verts[j * cols + i]
                svl.append(((0.0, 0.0, n), (s, t), (xp, yp, 0.0)))
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
        assert len(svl) <= TIKI_MAX_VERTEXES, ("TIKI_MAX_VERTEXES", len(svl))
        assert nT <= TIKI_MAX_TRIANGLES, ("TIKI_MAX_TRIANGLES", nT)
        out.append(("sea%d" % k, bytes(tris), svl))
        k += 1
        j0 = j1
    assert len(out) <= MAX_MODEL_SURFACES
    return out


# ---------------------------------------------------------------- SKD v5 writer (nohat_build.build_skd shape)
def build_skd(name, surfaces, bone_block, tail_from_ref):
    blobs = []
    for (surfname, tri_bytes, svl) in surfaces:
        nT = len(tri_bytes) // 12
        nV = len(svl)
        vb = bytearray()
        for (normal, uv, off) in svl:
            vb += struct.pack("<3f2f2i", *normal, *uv, 1, 0)      # normal, st, numWeights=1, numMorphs=0
            vb += struct.pack("<if3f", 0, 1.0, *off)               # bone 0, weight 1, bone-local offset
        assert len(vb) == nV * 48
        ofsTri = 100
        ofsVerts = ofsTri + nT * 12
        ofsColl = ofsVerts + nV * 48
        ofsCollIdx = ofsColl + nV * 4
        ofsEnd = ofsCollIdx + nV * 4
        sn = surfname.encode("ascii")
        assert len(sn) < 64
        hdr = struct.pack("<4s64s8i", b"SKL ", sn + b"\x00" * (64 - len(sn)),
                          nT, nV, 0, ofsTri, ofsVerts, ofsColl, ofsEnd, ofsCollIdx)
        assert len(hdr) == 100
        # identity collapse + all-zero collapse index: the bug-1002 rule (the engine reads both
        # unconditionally, tiki_skel.cpp:391-400) in the form every shipped coop_helmets skd uses.
        coll = struct.pack("<%di" % nV, *range(nV))
        collidx = struct.pack("<%di" % nV, *([0] * nV))
        blob = hdr + bytes(tri_bytes) + bytes(vb) + coll + collidx
        assert len(blob) == ofsEnd
        blobs.append(blob)
    body = b"".join(blobs)
    assert len(bone_block) == 116 and bone_block[0:6] == BONE_NAME + b"\x00"
    total = 148 + len(bone_block) + len(body)
    nm = name.encode("ascii")
    assert len(nm) < 64
    if tail_from_ref:
        tail = (0, total, 0, total)     # numBoxes, ofsBoxes, numMorphTargets, ofsMorphTargets - as us_helmetfit.skd
    else:
        tail = (0, 0, 0, 0)
    header = struct.pack("<4si64s5i10i4i", b"SKMD", 5, nm + b"\x00" * (64 - len(nm)),
                         len(surfaces), 1, 148, 148 + len(bone_block), total,
                         *([0] * 10), *tail)
    assert len(header) == 148
    return header + bone_block + body


# ---------------------------------------------------------------- SKC v13 writer (1 frame, identity pose)
def build_skc(frame_time, bounds_min, bounds_max, radius, channels, values, flags=0):
    """Layout measured from us_helmetfit.skc (192 bytes): 48 header | 48 frame | numChannels*16 data |
    numChannels*32 names. frame.iOfsChannels is the ABSOLUTE offset of this frame's channel data."""
    n = len(channels)
    assert len(values) == n
    ofs_data = 48 + 48
    ofs_names = ofs_data + 16 * n
    total = ofs_names + 32 * n
    frame = struct.pack("<3f3ff3ffi", *bounds_min, *bounds_max, radius, 0.0, 0.0, 0.0, 0.0, ofs_data)
    assert len(frame) == 48
    data = b"".join(struct.pack("<4f", *v) for v in values)
    names = b""
    for c in channels:
        cb = c.encode("ascii")
        assert len(cb) < 32
        names += cb + b"\x00" * (32 - len(cb))
    header = struct.pack("<4s3if3ff3i", b"SKAN", 13, flags, total, frame_time,
                         0.0, 0.0, 0.0, 0.0, n, ofs_names, 1)
    assert len(header) == 48
    out = header + frame + data + names
    assert len(out) == total
    return out


def selftest_skc_writer(ref_bytes):
    """The writer must reproduce the shipping reference byte-for-byte from its own decoded fields."""
    a = skdlib.read_skc(ref_bytes)
    (bmin0, bmin1, bmin2, bmax0, bmax1, bmax2, radius) = struct.unpack_from("<7f", ref_bytes, 48)
    vals = [skdlib.skc_channel(a, 0, i) for i in range(a.numChannels)]
    mine = build_skc(a.frameTime, (bmin0, bmin1, bmin2), (bmax0, bmax1, bmax2), radius,
                     tuple(a.channels), vals, a.flags)
    assert mine == ref_bytes, "SKC writer does not reproduce us_helmetfit.skc"
    return a.frameTime


# ---------------------------------------------------------------- text assets
def ascii_lf(text):
    text.encode("ascii")  # raises on anything non-ASCII (T1: em-dash, BOM, curly quotes)
    assert "\r" not in text
    return text.encode("ascii")


def tik_text(surfaces, nverts, ntris):
    lines = ["\tsurface %s shader coop_sea_deep" % s[0] for s in surfaces]
    return """TIKI
// HZM coop [user 2026-09-06, bug-2508] THE DENSE SEA - m3l1a open-sea plane (ocean_2026-09-06 item 8).
// GENERATED by docs/tools/gen_coop_sea.py - do not hand-edit; edit the generator and re-run.
//
// A %dx%d-quad plane over the open-sea patch's footprint (x %d..%d, y %d..%d, z %d): %d verts /
// %d tris in %d surfaces (TIKI caps 1000 verts / 2000 tris per surface). The retail patch draws that
// footprint as 8x8 = 64 verts, so a `deformVertexes wave` on it is under-sampled (~730 u rows); this
// mesh samples every %.0f u along y. Its shader (scripts/zz_coop_sea.shader, `coop_sea_deep`) carries
// two travelling waves; the vertex NORMAL length is the per-vertex amplitude gain, tapering to ~0 on
// the seam row at y %d so the plane meets the waterline band there with no step and no z-fight.
//
// The mesh is PRE-ROTATED so that the entity yaw below lays it into the world. That rotation is what
// decides which way the deform travels, and the generator prints the value it baked on every run -
// read it there, never from this comment. The spawn in coopified.scr::coop_seaMeshStart MUST carry
// the same yaw and the same origin ( %d %d %d ).
//
// Bone: Box01 (POSROT, identity pose in coop_sea.skc), lifted from the shipping coop_helmets
// container pattern. No LOD file, so RB_SkelMesh renders every vertex (pLOD NULL).
//
// SPAWN (script side; the recipe is docs/proposals/ocean_2026-09-06/seamesh_spawn.scr):
//   kill switch level.coop_seaMeshOn (default 1); hide $ocean_wavy while this shows and show it back
//   when this is removed - the retail sheet is coplanar with the seam row and would z-fight it.
setup
{
\tscale 1.0
\tpath models/fx/coop_sea
\tskelmodel coop_sea.skd
%s
}

init
{
\tserver
\t{
\t\tclassname effectentity
\t\tnotsolid
\t}
}

animations
{
\tidle coop_sea.skc
}
""" % (NX, NY, int(XMIN), int(XMAX), int(YFAR), int(YSEAM), int(Z), nverts, ntris, len(surfaces),
       (YSEAM - YFAR) / NY, int(YSEAM), int(ORIGIN[0]), int(ORIGIN[1]), int(ORIGIN[2]), "\n".join(lines))


def shader_text():
    w = "\n".join("\tdeformVertexes wave %d sin 0 %g 0 %g\t\t// %s" % (d, a, f, note) for (d, a, f, note) in WAVES)
    lam = " / ".join("%.0f" % (d / math.sqrt(2)) for (d, a, f, note) in WAVES)
    return """// HZM coop [user 2026-09-06, bug-2508] THE DENSE SEA - shader for models/fx/coop_sea.tik (m3l1a).
// GENERATED by docs/tools/gen_coop_sea.py - do not hand-edit; edit the generator and re-run.
//
// A restatement of textures/misc_outside/deepbluesea as it ships in zz_coop_ocean.shader (the two
// retail stages, the bug-2507 lid: blendFunc blend + depthwrite + alphaGen entity so `alpha 0.6` on
// the entity works the same way) with the retail `flap` hinge replaced by two TRAVELLING waves. On
// the 64-vert patch a wave is under-sampled; on the coop_sea mesh (121.7 u rows) it is not.
//
// `deformVertexes wave <div> sin <base> <amp> <phase> <freq>` phases each vertex by (x+y+z)/div in
// entity space. NOTE the crest-normal wavelength is div/sqrt(2) = %s u, but the spacing along world
// X and along world Y is div itself - text here once said otherwise, and that is exactly the sort of
// sentence a later session uses to pick a wavelength.
// The per-vertex amplitude is the mesh's own normal length (0 on the seam row, 1 from 1200 u out),
// so nothing here needs to know where the seam is. Two deforms put this shader on the CPU deform
// path (tr_local.h:2846), where both are applied (tr_shade_calc.c:704-715); 1,617 verts, trivial.
//
// KILL SWITCH for the look: this file (the script switch is level.coop_seaMeshOn). To tune: amp is
// vertical units at full taper (summed %g), div = wavelength * 1.4142, freq = 1 / period.
// Keep the summed amplitude near the retail sheet's own +/-8.5 at the fleet (bug-2478) or the boats
// drown again. One name, one coop file (TRAPS T6). No lightmap stage: this is an entity.
coop_sea_deep
{
\tqer_editorimage textures/misc_outside/ocean2.tga
\tqer_keyword natural
\tqer_keyword liquid
\tqer_keyword ocean
\tqer_trans .4
\tsurfaceparm trans
\tsurfaceparm water
\tsurfaceparm nolightmap
\tcull none

%s

\t{
\t\tnopicmip
\t\tdepthwrite
\t\tmap textures/misc_outside/oceandday1.tga
\t\tblendFunc blend
\t\talphaGen entity
\t\trgbGen identityLighting
\t\ttcMod scale 16 22
\t\ttcMod scroll 0.01 .03
\tnextbundle
\t\tmap textures/misc_outside/oceandday1.tga
\t\ttcMod scale -16 22
\t\ttcMod scroll 0.01 0.04
\t}
\t{
\t\tnopicmip
\t\tmap textures/misc_outside/oceandday1.tga
\t\tblendFunc GL_SRC_ALPHA GL_ONE
\t\talphaGen tCoord 0 4 0 1
\t\ttcMod scale .2 .5
\t\ttcMod scroll 0 .005
\tnextbundle
\t\tmap textures/misc_outside/oceandday1.tga
\t\ttcMod scale .2 .5
\t\ttcMod scroll 0 .01
\t}
}
""" % (lam, sum(a for (d, a, f, note) in WAVES), w)


def recipe_text():
    return """//=========================================================================
// [user 2026-09-06, bug-2508] THE DENSE SEA - spawn recipe for maps/m3l1a/coopified.scr.
// GENERATED by docs/tools/gen_coop_sea.py (this file is the paste source; it is not shipped).
//
// HOOKS: `thread coop_seaMeshStart` right after maps/m3l1a.scr:2545 `$ocean_wavy show` (the run-in
// start), `waitthread coop_seaMeshStop` at the ramp drop BEFORE the RAMPUW plunge sets the lid
// (coopified.scr:13142 `$ocean_wavy alpha 0.6` needs the retail sheet back). The mesh REPLACES the
// retail sheet while it is up: the two are coplanar on the seam row and would z-fight, and a wave
// crossing a flat sheet shows the sheet in every trough (gen_coop_sea.py header).
//
// KILL SWITCH: level.coop_seaMeshOn 0 (default 1). PROBE: '^~^~^ SEAMESH on' / '^~^~^ SEAMESH off'.
// ORIGIN and YAW are the mesh's own (centred on the patch footprint): change
// neither without regenerating the mesh.
//=========================================================================
coop_seaMeshStart:
//=========================================================================
	if(level.coop_seaMeshOn == NIL){ level.coop_seaMeshOn = 1 }
	if(!level.coop_seaMeshOn){ println("^~^~^ SEAMESH off (coop_seaMeshOn 0)"); end }
	if(level.coop_seaMesh != NIL && level.coop_seaMesh != NULL){ end }		//already up
	local.m = spawn script_model model "models/fx/coop_sea.tik"
	if(local.m == NULL || local.m == NIL){ println("^~^~^ SEAMESH FAIL spawn returned NULL"); end }		//entity-pool guard
	local.m.origin = ( %d %d %d )
	local.m.angles = ( 0 %d 0 )
	local.m notsolid		//T9: after the tik landed, never before
	local.m.targetname = "coop_seamesh"
	level.coop_seaMesh = local.m
	if($ocean_wavy != NULL && $ocean_wavy != NIL){ $ocean_wavy hide }		//coplanar seam row; the mesh is the sea now
	println("^~^~^ SEAMESH on origin=%d,%d,%d yaw=%d verts=%d")
end

//=========================================================================
coop_seaMeshStop:
//=========================================================================
	if(level.coop_seaMesh == NIL || level.coop_seaMesh == NULL){ end }
	level.coop_seaMesh remove
	level.coop_seaMesh = NULL
	if($ocean_wavy != NULL && $ocean_wavy != NIL){ $ocean_wavy show }		//the retail sheet (and the bug-2507 lid) come back
	println("^~^~^ SEAMESH off")
end
""" % (int(ORIGIN[0]), int(ORIGIN[1]), int(ORIGIN[2]), int(YAW),
       int(ORIGIN[0]), int(ORIGIN[1]), int(ORIGIN[2]), int(YAW),
       (NX + 1) * (NY + 1) + (NX + 1) * (NY // ROWS_PER_SURF - 1))   # 1650: the shared rows are stored twice


# ---------------------------------------------------------------- verification of what was written
def verify_skd(data, surfaces):
    m = skdlib.read_skd(data)
    assert m.version == 5 and m.numBones == 1 and m.numSurfaces == len(surfaces)
    assert m.bones[0].name == BONE_NAME.decode() and m.bones[0].jointType == 1
    assert sorted(m.bones[0].channels) == sorted(CHANNELS)
    for (s, (name, tri_bytes, svl)) in zip(m.surfaces, surfaces):
        assert s.name == name and s.numVerts == len(svl) and s.numTriangles == len(tri_bytes) // 12
        assert s.has_collapse
        assert s.tri_bytes == tri_bytes
        for (v, (normal, uv, off)) in zip(s.verts, svl):
            (rn, ruv, wl, ml) = v
            assert len(wl) == 1 and wl[0][0] == 0 and abs(wl[0][1] - 1.0) < 1e-6 and not ml
            for a, b in zip(rn, normal):
                assert abs(a - b) < 1e-6
            for a, b in zip(wl[0][2], off):
                assert abs(a - b) < 1e-3
        # every triangle index in range
        idx = struct.unpack("<%di" % (len(tri_bytes) // 4), tri_bytes)
        assert min(idx) == 0 and max(idx) == len(svl) - 1
    # a sample of world positions round-trips through the entity rotation
    (name, tri_bytes, svl) = surfaces[0]
    for k in (0, NX, (NX + 1) * ROWS_PER_SURF):
        xp, yp, zp = svl[k][2]
        X, Y = entity_to_world(xp, yp)
        assert XMIN - 1e-3 <= X <= XMAX + 1e-3 and YFAR - 1e-3 <= Y <= YSEAM + 1e-3, (X, Y)
    # the seam row is (almost) still; the far rows are at the along-crest envelope's gain, not at 1.0
    # (bug-2519 - before the envelope this asserted exactly 1.0, which is why it is worth restating:
    # the far edge is now base 1.0 x env(X), and env is bounded by construction).
    assert abs(svl[0][0][2] - NORMAL_FLOOR) < 1e-9
    ns = [v[0][2] for (_n, _tb, sv) in surfaces for v in sv]
    assert min(ns) >= NORMAL_FLOOR - 1e-9, "a normal fell below the floor: %.6f" % min(ns)
    assert max(ns) <= NORMAL_CAP + 1e-9, \
        "normal length %.6f - at or above 1.0000153 R_VaoPackNormal's int16 wraps and INVERTS that vertex" % max(ns)
    far = [v[0][2] for v in surfaces[-1][2][-(NX + 1):]]
    assert 0.20 <= min(far) and max(far) <= NORMAL_CAP + 1e-9, \
        "far-edge gain %.3f..%.3f outside the shoaling envelope" % (min(far), max(far))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the shipped files match; write nothing")
    args = ap.parse_args()

    ref_skd = open(REF_SKD, "rb").read()
    ref_skc = open(REF_SKC, "rb").read()
    bone_block = ref_skd[148:264]
    frame_time = selftest_skc_writer(ref_skc)

    verts = build_grid()
    surfaces = split_surfaces(verts)
    nverts = sum(len(s[2]) for s in surfaces)
    ntris = sum(len(s[1]) // 12 for s in surfaces)

    skd = build_skd("coop_sea.skd", surfaces, bone_block, tail_from_ref=True)
    verify_skd(skd, surfaces)

    # bounds in entity space over every vertex, plus the wave travel
    xs = [v[2] for v in verts]
    ys = [v[3] for v in verts]
    amp = sum(a for (d, a, f, note) in WAVES) + WAVE_MARGIN
    bmin = (min(xs) - WAVE_MARGIN, min(ys) - WAVE_MARGIN, -amp)
    bmax = (max(xs) + WAVE_MARGIN, max(ys) + WAVE_MARGIN, amp)
    radius = max(math.sqrt(x * x + y * y) for (x, y) in zip(xs, ys)) + amp
    skc = build_skc(frame_time, bmin, bmax, radius, CHANNELS,
                    [(0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)])
    a = skdlib.read_skc(skc)
    assert a.numFrames == 1 and list(a.channels) == list(CHANNELS)
    assert skdlib.skc_channel(a, 0, 1) == (0.0, 0.0, 0.0, 1.0)

    outputs = [
        (OUT_SKD, skd),
        (OUT_SKC, skc),
        (OUT_TIK, ascii_lf(tik_text(surfaces, nverts, ntris))),
        (OUT_SHADER, ascii_lf(shader_text())),
        (OUT_RECIPE, ascii_lf(recipe_text())),
    ]
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

    print("mesh: %dx%d quads, %d verts / %d tris in %d surfaces; rows every %.1f u, cols every %.1f u"
          % (NX, NY, nverts, ntris, len(surfaces), (YSEAM - YFAR) / NY, (XMAX - XMIN) / NX))
    print("entity: origin (%d %d %d) angles (0 %d 0); bounds x' %.0f..%.0f y' %.0f..%.0f radius %.0f"
          % (ORIGIN[0], ORIGIN[1], ORIGIN[2], YAW, bmin[0], bmax[0], bmin[1], bmax[1], radius))
    for (d, amp_, f, note) in WAVES:
        lam = d / math.sqrt(2)
        print("wave: div %d -> lambda_y %.0f u, %.1f rows/wavelength, amp %.1f, period %.1f s, %.0f u/s shoreward - %s"
              % (d, lam, lam / ((YSEAM - YFAR) / NY), amp_, 1.0 / f, lam * f, note))
    if drift:
        sys.exit(1)


if __name__ == "__main__":
    main()

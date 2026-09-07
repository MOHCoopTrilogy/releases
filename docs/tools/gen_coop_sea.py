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
YSEAM, YFAR = -2160.0, -8000.0      # rawT 0 at the seam, 1 at the far edge (zz_coop_ocean.shader)
Z = -520.0                          # all 225 control points of both patches
NX, NY = 32, 48                     # quads: 496 u in x, 121.7 u in y (the patch draws ~730 u rows)
TAPER_L = 1200.0                    # amplitude reaches 1.0 this far seaward of the seam
NORMAL_FLOOR = 0.001                # never a true zero normal (tangent maths elsewhere divides)
YAW = 225.0                         # the entity yaw the mesh is pre-rotated for
ORIGIN = ((XMIN + XMAX) * 0.5, (YSEAM + YFAR) * 0.5, Z)   # (64, -5080, -520)
ROWS_PER_SURF = 24                  # 25 rows x 33 cols = 825 verts, 1536 tris per surface (caps 1000/2000)
WAVE_MARGIN = 24.0                  # bounds/radius slack over the summed wave amplitude (8.5)
BONE_NAME = b"Box01"
CHANNELS = ("Box01 pos", "Box01 rot")   # the order the reference skc stores them in

# the swell (shader): lambda_y = div / sqrt(2); speed = lambda_y * freq, shoreward
WAVES = (
    # div,  amp, freq,  note
    (5091, 6.0, 0.10, "long swell: lambda 3600 u, 10 s (the sheet's flap period, bob-sync stays valid), 360 u/s"),
    (1697, 2.5, 0.18, "short chop: lambda 1200 u, 5.6 s, 216 u/s; 10 rows per wavelength"),
)

TIKI_MAX_VERTEXES, TIKI_MAX_TRIANGLES, MAX_MODEL_SURFACES = 1000, 2000, 32


# ---------------------------------------------------------------- rotation (AnglesToAxis convention)
def world_to_entity(X, Y):
    dx, dy = X - ORIGIN[0], Y - ORIGIN[1]
    r = math.sqrt(0.5)
    return (-(dx + dy) * r, (dx - dy) * r)


def entity_to_world(xp, yp):
    a = math.radians(YAW)
    cy, sy = math.cos(a), math.sin(a)
    return (ORIGIN[0] + cy * xp - sy * yp, ORIGIN[1] + sy * xp + cy * yp)


# ---------------------------------------------------------------- geometry
def build_grid():
    """verts: list of (world X, Y, entity x', y', normal_z, s, t); one row per j, seam row first."""
    verts = []
    for j in range(NY + 1):
        Y = YSEAM + (YFAR - YSEAM) * j / NY
        n = max(NORMAL_FLOOR, min(1.0, (YSEAM - Y) / TAPER_L))
        for i in range(NX + 1):
            X = XMIN + (XMAX - XMIN) * i / NX
            xp, yp = world_to_entity(X, Y)
            Xb, Yb = entity_to_world(xp, yp)
            assert abs(Xb - X) < 1e-6 and abs(Yb - Y) < 1e-6, ("rotation round trip", X, Y, Xb, Yb)
            s = (X - XMIN) / (XMAX - XMIN)
            t = (YSEAM - Y) / (YSEAM - YFAR)
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
// The mesh is PRE-ROTATED by -225 degrees so that `angles ( 0 225 0 )` on the entity lays it
// axis-aligned in the world: that turns the deform's (x+y+z) phase into a function of world Y alone,
// which is what makes the crests parallel to the beach and travel shoreward. Spawn it ONLY with that
// yaw and ONLY at origin ( %d %d %d ).
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
// entity space. The mesh is pre-rotated for yaw 225, so x+y = -sqrt(2)*(Y - oy): the wavelength
// along world Y is div/sqrt(2) = %s u and a positive freq moves the crests toward +Y = the beach.
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
\t\tblendFunc add
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
// ORIGIN and YAW are the mesh's own (pre-rotated for yaw 225, centred on the patch footprint): change
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
    # the seam row is (almost) still, the far rows are at full gain
    assert abs(svl[0][0][2] - NORMAL_FLOOR) < 1e-9
    assert abs(surfaces[-1][2][-1][0][2] - 1.0) < 1e-9
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

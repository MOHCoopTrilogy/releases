# LANE A - what m3l1a / m3l1b water actually is today, measured

Every number below was read out of the shipped BSPs / paks / engine source in this session.
Helper scripts in this same directory: mywater.py, detail.py, sweep.py, bspents.py,
grepshader.py, findshader.py.

## 1. Geometry (m3l1a.bsp, main/Pak5.pk3, ident "2015", version 19, 5,300,576 bytes)

| surface | shader | type | submodel | surf | verts | tris | Z | Y span |
|---|---|---|---|---|---|---|---|---|
| open ocean | misc_outside/deepbluesea | PATCH 15x15 | *84 `$ocean_wavy` | 1 | 225 ctrl | - | -520.0 exactly, all 225 | -8000..-2160 |
| far ocean | misc_outside/deepbluesea_runup | PATCH 15x15 | *85 `$ocean_calm` | 1 | 225 ctrl | - | -520.0 exactly, all 225 | -13312..-2160 |
| waterline | misc_outside/deepbluesea_shoreline | PLANAR | *0 (world) | 12 | 48 | 24 | -520.0 .. -479.0 | -2160..-768 |
| wet sand | mohtest/omaha_set4_shoreline | PLANAR | *0 | 6 | 24 | 12 | -504 .. -480 | -1024..-768 |

There are TWO flat 225-point patches, not one. `$ocean_calm` (deepbluesea_runup) reaches more
than twice as far out (11,152 units deep vs 5,840) and overlaps `$ocean_wavy` completely in
Y -8000..-2160.

- BSP surfaceFlags on all three water shaders = 0x10010100 = NOLIGHTMAP | ROCK | BACKSIDE.
  contentFlags = 0x20000020 = CONTENTS_WATER | CONTENTS_TRANSLUCENT. **No SURF_PUDDLE.**
- The waterline is a 6-column x 2-row grid of quads. Column X breaks: -7872, -2304, -704, 320,
  1344, 2368, 8000. Row Y breaks: -2160, -1472, -768.
- **The waterline band is NOT flat.** Z = -520.0 at Y -2160, -499.8 at Y -1472, -479.0 at
  Y -768: a 41-unit rise over 1,392 units (~1.7 deg). Vertex normal (0.00, -0.03, 1.00).
- T runs 0.0050 (seaward) to 0.9936 (sand) across those 1,392 units = **1,408 world units per
  1.0 of T**. (The crest stage's comment says 1409; correct.)
- m3l1b carries an IDENTICAL waterline: 12 quads / 48 verts, band Y -8128..-6736 (1,392u
  again), Z -512..-471 (41u again), T 0.001..0.989. Every tuning number transfers 1:1.

### Why the patches cannot be made denser - mechanism, verified

`R_SubdividePatchToGrid` (renderergl2/tr_curve.c:445) tests `if ( maxLen < 0.1f )` at
tr_curve.c:512 and marks the column complete BEFORE the `maxLen <= r_subdivisions->value`
test at tr_curve.c:524. All 225 control points sit at Z -520.0, so maxLen is 0 for every
column and row. The colinear cull at tr_curve.c:570-594 then strips the 7 odd interior
indices in each direction: **15 -> 8**. Final drawn mesh = **8x8 = 64 verts / 98 tris** per
patch. No cvar reaches this.

gl1 additionally honours the BSP per-surface `subdivisions` field (4.0 here, tr_bsp.c:786);
gl2 ignores it and passes nothing (tr_bsp.c:892). Irrelevant - both hit the same 0.1f early-out.

`tesssize` is `SkipRestOfLine` in both renderers (gl1 tr_shader.c:2307, gl2 tr_shader.c:2654).
Confirmed.

Ceilings if a denser mesh were ever supplied: MAX_PATCH_SIZE 32 (BSP control grid),
MAX_GRID_SIZE 65 (in-memory grid) - gl1 tr_local.h:771-772, gl2 tr_local.h:1204-1205 -
SHADER_MAX_VERTEXES 2048 (qcommon/qfiles.h:40). A 65x65 grid over the deepbluesea footprint
gives 248u x 91u vertex spacing.

## 2. The deform that is already running, and what it really does

`deformVertexes flap <s|t> <div> <wave...> <min> <max>`; parser gl2 tr_shader.c:2237-2290,
`bulgeWidth` = min, `bulgeHeight` = max. Evaluated in `RB_CalcFlapVertexes`
(renderergl2/tr_shade_calc.c:171-238): `scale` is WAVEVALUE(**time only**), `vertexScale =
(max - min) * st[coord] + min`, offset = scale * vertexScale * normal. It is a hinge, not a
wave - every vertex peaks in the same instant, only the amplitude varies along T.

| shader | flap line | period | peak vertical displacement |
|---|---|---|---|
| deepbluesea (`$ocean_wavy`) | `flap t 10 sin 0 10 0 .10 0 10` | 10.0 s | +/-100u at T=1 (Y -8000) on gl1; **gl2 clamps vertexScale to 8.0** (tr_shade_calc.c:206-207) so +/-80u |
| deepbluesea_runup (`$ocean_calm`) | `flap t 10 sin 0 3 0 .10 0 3` | 10.0 s | +/-9u at T=1 |
| deepbluesea_shoreline (coop) | `flap t 10 sin 0 4 0 .08 0 4` | 12.5 s | +/-0.08u at the seam, +/-7.9u mid-band, +/-15.9u at the sand |

**Previously unrecorded gl1/gl2 divergence:** the ocean patch's far edge swings 100 units on
gl1 and 80 on gl2, because of the HZM clamp added during the gl2 port. Same shader, different
water. The shoreline's max is 4, so the clamp never fires there and the two renderers agree.

## 3. Stage census - where the headroom actually is

MAX_SHADER_STAGES = 8 in both (gl1 tr_local.h:278, gl2 tr_local.h:252).
gl2 rejects the whole shader on a 9th (tr_shader.c:2529-2531, `return qfalse`).
**gl1 has no bound check at all** - the stage loop at tr_shader.c:2249-2266 does `s++` with no
test, writing past `unfoggedStages[8]`. Both halves of the warning in zz_coop_shoreline.shader
are correct.
NUM_TEXTURE_BUNDLES: gl1 = 2 (tr_local.h:476), gl2 = 7 (tr_local.h:509).

| shader | stages used | free | maps an override would touch |
|---|---|---|---|
| **misc_outside/deepbluesea_shoreline** (coop overrides it) | 8 | **0** | 7: m3l1a, m3l1b, dogwhite, omaha_beach, obj_team3, mp_anzio_lib, obj_hms_hood |
| **misc_outside/deepbluesea** (retail) | 2 | **6** | 1: m3l1a only |
| **misc_outside/deepbluesea_runup** (retail) | 2 | **6** | 4: m3l1a + obj_team3 (patch), dogwhite + omaha_beach (planar) |
| **mohtest/omaha_set4_shoreline** (retail; 1 stage, `clampmapy` + `$lightmap` bundle) | 1 | **7** | 3: m3l1a, m3l1b, obj_team3 |
| misc_outside/deepbluesea_runup_nowave (retail) | 2 | 6 | 1: mp_anzio_lib |

## 4. TWO OF THE EIGHT SHORELINE STAGES DRAW NOTHING

Stages 1 and 2 of `deepbluesea_shoreline` are the retail "fading continuation of the ocean"
layers. Both use the two-parameter form:

    alphaGen tCoord 1.8  -0.01      (stage 1, blendFunc blend)
    alphaGen tCoord 1.01 -0.5       (stage 2, blendFunc GL_SRC_ALPHA GL_ONE)

The parser (gl1 tr_shader.c:1521-1555) initialises `alphaConst = -1` and only overwrites it if
a FOURTH token is present. It is not. `RB_CalcAlphaFromTexCoords` (gl1 tr_shade_calc.c:1137-1151)
then does `f = f - Q_max((int)(f - alphaCap), 0)` with alphaCap = -1, which drives alpha to
**exactly 0 for every T**. Verified numerically: T = 0.005 / 0.25 / 0.4936 / 0.75 / 0.994 all
give alpha 0. gl2 reproduces it on purpose - tr_shade.c:1828-1831 collapses the -1 sentinel to
`aLo = aHi = 0`, and generic_vp.glsl:237 does `clamp(f, 0.0, 0.0)`.

Consequences, measured:

- The **effective** stage count of the waterline is 6, not 8. Two free slots are already inside
  the shader, and reclaiming them costs nothing visually because they contribute nothing today.
  That is the answer to "how would you free a stage".
- The waterline has **no base water colour at all**. What is actually drawn is four additive
  `wash2` layers plus the coop blood (alpha-blended) plus the coop crest (additive), over
  whatever is behind the surface. That is a concrete explanation for the shoreline reading thin
  and for the hard seam the user reported at Y = -2160.
- Giving stage 1 its 4th parameter (`alphaGen tCoord 1.8 -0.01 0 1`) yields alpha 255 at the
  ocean join falling to 0 at the sand - exactly the ocean-into-shore fade the retail comment
  claims it already is. Zero new stages, zero new art, one token.
- UNVERIFIED: whether retail MOHAA 1.11's renderer also produced alpha 0 here. The OpenMOHAA
  comment asserts it did ("which is why the water shaders look right on gl1"), but that is an
  assertion about intent, not a measurement.

The four `wash2` stages are two mirrored pairs at exact antiphase (rgbGen phases .35 / .85 and
.325 / .825; wavetrant phases .5 / 0 and .45 / .95; tcMod scale +8 / -8). Dropping one of each
pair frees 2 more stages at the cost of halving the wash pulse rate. So up to **4 of 8** slots
are recoverable on the waterline without touching the crest or the blood.

## 5. What each existing layer contributes

| layer | what it adds | verdict |
|---|---|---|
| shoreline stages 1-2 (retail alphaGen tCoord) | **nothing** - alpha 0 | dead fill cost |
| shoreline stages 3-6 (4x wash2, blendFunc add, `rgbGen wave sin .15 .525 <phase> -.04`, period 25 s) | the entire visible waterline: additive foam, mirrored pairs, antiphase | the only thing painting the water |
| shoreline stage 7 (coop blood, 2026-08-31) | bloodwash.tga, alpha 5 -> 152 ramped along T (verified numerically), `tcMod scale 16 2` | works; is what hides the seam today |
| shoreline stage 8 (coop crest, 2026-09-04) | ocean2a_shore.jpg, blendFunc add, `tcMod scale 8 -6`, `scroll 0.01 0.16`, `wavetrant sin 0 0.30 0 0.08` | crest every 1408/6 = 235u, arriving every 6.25 s = exactly half the 12.5 s flap. Gated by `ifCvarnot coop_noCrest 1`; `ri.Cvar_Get(token, "0", 0)` at gl2 tr_shader.c:1985 means the cvar defaults to 0, so the stage is **ON out of the box** (verified through the evaluatedValue logic at tr_shader.c:1993-2004) |
| flap on the shoreline | +/-16u vertical hinge at the sand edge, 12.5 s | present; reads as breathing, not waves |
| flap on `$ocean_wavy` | +/-80..100u hinge at the horizon, 10 s | present, and large; the ocean sheet pivots about the Y -2160 join |

## 6. `$ocean_wavy` / `$ocean_calm` - what is on screen when

Both are `script_object` at origin 0 0 0 (BSP entity lump). Script control, coop m3l1a.scr:

- :574 `$ocean_wavy hide` at map init -> only `$ocean_calm` (deepbluesea_runup) is drawn.
- :2522 `$ocean_wavy show`, :2524 `$ocean_calm hide` during the Higgins run-in.
- :1335 `$ocean_wavy show` when `level.progress == "water"`.
- :1373 `$ocean_wavy hide` on the next progress step.
- coopified.scr:13072 hide, :13169 and :13998 show, for the underwater camera beat.

**`$ocean_calm` is hidden at :2524 and never shown again** (one occurrence in the file).
So from the ramp onward, whenever `$ocean_wavy` is also hidden, **no open ocean surface is
drawn at all** - the horizon past Y -2160 is skybox plus farplane fog (5700 at that stage,
m3l1a.scr:1376; 2000 / 4000 / 6700 by `g_ddayfog` at :1340-1346).
UNVERIFIED on screen whether the fog fully covers that; it is a one-minute in-game check.

**Opaque from below** is now explained rather than just observed: `deepbluesea` stage 0 has **no
blendFunc at all**, so it is an opaque depth-writing stage; `deepbluesea_runup` stage 0 carries
an explicit `depthwrite`. `deepbluesea_shoreline` stage 0 is `blendFunc blend` with no
depthwrite, so the waterline is translucent and writes no depth.
`cull none` on all three - every water face is drawn twice.

Both renderers support `sort underwater` -> SS_UNDERWATER, "for items that should be drawn in
front of the water plane" (gl1 tr_local.h:263, tr_shader.c:2109-2110; gl2 tr_shader.c:2403).

## 7. Underwater - what is actually running

**gl2 only.** `renderergl1/tr_postprocess_gl1.c` contains no underwater code (grepped); gl1
players get only the FOV warp. The entire underwater look is invisible on gl1.

Signal chain: `CG_CalcFov` calls `CG_PointContents(cg.refdef.vieworg, -1)` and tests
`CONTENTS_WATER | SLIME | LAVA` (cg_view.c:5766-5773), eases a 0..1 (in ~0.3 s, out ~1 s) and
publishes `r_ppUnderwater` (cg_view.c:5800). Renderer pass: tr_postprocess.c:1523-1690 plus
`glsl/underwater_fp.glsl` (312 lines).

**A depth texture IS bound and IS read.** `GL_BindToTMU(tr.renderDepthImage, TB_LEVELSMAP)`
(tr_postprocess.c:1632); the shader reconstructs eye distance as `d = P14 / (P10 + (2*zw - 1))`
(underwater_fp.glsl:150-154) from `rb_viewProj` latched projection terms. The pass writes to
`tr.globalFogFbo`, the colour-only alias of screenScratchFbo's colour image, specifically to
avoid sampling an attachment of the bound FBO (tr_postprocess.c:1502-1512, tr_fbo.c:320-329).
This is a working, shipped, **depth-aware** full-screen pass - the pattern any future
refraction / caustics / god-ray work would reuse.

Fog and occlusion numbers, all live cvars (tr_postprocess.c:1464-1471):

| cvar | default | meaning |
|---|---|---|
| r_ppUnderwaterVis | 900 | units at which green transmittance falls to 37% |
| (derived) farClamp | vis * 6 = **5400 units** | beyond this, solid silt |
| (derived) sigma | R 3.10/900, G 1.00/900, B 1.90/900 | per-channel Beer-Lambert; red dies first |
| r_ppUnderwaterSilt | `0.075 0.155 0.135` | grey-green Channel water |
| r_ppUnderwaterBlur | 1.0 | 9 texels at 1080p at full murk; 12-tap golden-angle spiral + centre |
| r_ppUnderwaterParticles / Shafts / Ripple | 1.0 | motes / light shafts / UV refraction |
| r_ppUnderwaterAmt | 1.0 | master scalar |
| r_ppUnderwaterDebug | 0 | 1 absorption, 2 murk, 3 distance ramp, 4 raw depth (sampler test) |

What it occludes: **everything, by distance**, plus the sky. A pixel with `zw >= 0.9999999`
(nothing wrote depth - skybox, or any blendfunc surface with no depthWrite) is forced to
farDist and absorbs to solid silt (underwater_fp.glsl:160-164). That is what currently hides
the unfinished seabed and the skybox wall below the waterline on m3l1a.

Already present in that pass: refraction (two-octave sine UV warp), per-channel extinction,
multiplicative noise density, depth-scaled scatter blur, two parallax mote layers, vertical
light shafts, a small vignette. **Caustics and true light shafts anchored to the surface are
the two obvious absentees.**

Audio: the 26.5 s one-shot bed is `coop_uwBedStart` (coopified.scr:13454), threaded from
:12198 and stopped at :12612; `level.coop_uwBedPlay` / `coop_uwBedVol` gate it. Not a loop -
the fade is baked into the wav.

## 8. Sub-question: splash against objects - what would carry it

The primitive already exists and is already in this map.

`models/animate/fx_water_spray.tik` (main/Pak0.pk3) is documented in its own QUAKED block as
**"water splashing over boats effect"**. It is `classname effectentity`, `notsolid`,
`rendereffects +dontdraw`, and its whole body is one `originemitter water_spray_clouds` using
`oceanspray.spr`: `count 1  spawnrate 5  life 1.5  scale 2  scalerate .25  randvelaxis crandom
30 crandom 30 256  accel 0 -300 -450  fadein .5  fadedelay .75`. It carries **no sound at
all**, and it is toggled by `emitteron` / `emitteroff` on the `start` / `stop` anims - i.e. it
is designed to be left parked on an object and switched.

Already in play:

- 12 baked `animate_fx_water-spray` entities in m3l1a.bsp bound to the Higgins boats
  (`higgins1_spray_left/right` and friends) - the retail devs already used it for exactly this.
- 17 baked `animate_fx_mortar-water` entities (the big `spritely_water.spr` + `waterplume.spr`
  column, which DOES carry `arty_exp_water`).
- coop `coop_waterShots` (coopified.scr:3316-3360) already spawns `fx_water_spray` as a
  `script_model` for rounds hitting the water, deliberately silent.
- `coop_lensSplashAt` -> `coop_lensSplash` -> `CG_CoopLensSplash` (cg_view.c:5269) -> the rain
  bead pass; bullets crossing into `CONTENTS_FLUID` raise it directly at cg_parsemsg.cpp:762-781
  with a 650-unit falloff.

So splash-against-objects needs **no new engine code and no new art**: a script spawns one
`fx_water_spray` per waterline obstacle and toggles it. The obstacle table already exists and
is already generated from the BSP - `docs/tools/gen_m3l1a_obstacles.py` emits
`maps/m3l1a/obstacles.scr` with X / Y / radius for all 401 static models, and the hedgehog /
minepole / ramp / barbwire families in the tidal flat are exactly what a wave breaks against.

**The one real obstacle is phase.** To fire the splash when the crest arrives, the script must
know the shader's clock, and it cannot:

- shader wave phase = `tess.shaderTime = backEnd.refdef.floatTime` (gl2 tr_shade.c:179),
  `tr.refdef.floatTime = tr.refdef.time * 0.001` (tr_scene.c:466),
  `cg.time = cg.snap->serverTime` (cg_snapshot.c:524) - i.e. **absolute** server time in ms.
- script `level.time = (svsTime - svsStartTime) / 1000` (fgame/level.cpp:1109-1112) - i.e.
  server time **rebased to map start**.

They differ by a constant `svsStartTime` the script cannot see. Options, cheapest first:
(a) ignore it - the crest is a 6.25 s global sine and a constant offset is invisible to a
viewer with nothing to compare against; (b) publish `cg.time / 1000` once from the cgame into a
cvar the script reads, resolving the offset exactly (one line, the `r_ppUnderwater` idiom);
(c) do the whole thing client-side in cgame, where shaderTime is directly available.

## 9. Textures in play, and the .dds hazard

| image | retail | HD / coop | notes |
|---|---|---|---|
| oceandday1 | 256x256 jpg (main/Pak2.pk3) | **1024x1024 jpg** in `zzzzzz_co-op_hzm_mod_assets_tex.pk3` | used by 6 of the 8 shoreline stages, both bundles |
| wash2 | 256x256 jpg (main/Pak2.pk3) | 1024 jpg in `zzzzz-AA_HD_Project_Pak3.pk3`, **and a 1024 wash2.dds in `zzzzzzz_dds_hdmem.pk3`, which wins** | the four additive wash stages |
| ocean2a_shore | **256x256 jpg, retail only** | none, and no .dds | the crest. Re-verified: referenced by no shader anywhere except zz_coop_shoreline.shader |
| ocean2 | 256x256 tga | 1024 tga in the coop tex pak | editor image only |

All water stages are `nopicmip`, so none of these ever drop resolution.
`ocean2a_shore` at 256x256 is the lowest-resolution image in the whole waterline, and it is the
crest - the one layer the user is looking at. UNVERIFIED whether upscaling it helps or hurts
(it is a banded spray field; ESRGAN on that class of art is the documented corruption risk).

The mod also ships `scripts/coop_water_overrides.shader`, which overrides only
`textures/misc_outside/northafrika_shoreline` (m1l3c) to strip its alphaGen / wavetrant lines.
Not m3l1a. Worth reading before adding a second water override file - the name-priority trap
(zz_ prefix, `FindShaderInShaderText` returns the first match in reverse-listing order) is
documented at the top of zz_coop_shoreline.shader and applies to any new file.

## 10. Where the headroom is - this lane's view only

1. **2 free stages already inside deepbluesea_shoreline** (the alpha-0 retail pair) - free.
2. **6 free stages on deepbluesea** (`$ocean_wavy`, m3l1a-only, zero collateral) - the surface
   with 64 verts and a +/-80..100u hinge already on it.
3. **7 free stages on mohtest/omaha_set4_shoreline** - the wet-sand strip, only m3l1a, m3l1b
   and obj_team3. This is where wash-following wet-sand darkening belongs, and it is currently
   a single `clampmapy` + lightmap.
4. **6 free stages on deepbluesea_runup** (`$ocean_calm`) - but it is hidden for most of the map.
5. 2 more stages recoverable on the shoreline by collapsing the antiphase `wash2` pairs, at the
   cost of halving the wash pulse rate.
6. The gl2 depth-aware post pass is a shipped, proven pattern with a bound depth texture.

## 11. What I could not determine offline

- Whether the ocean genuinely disappears from the horizon after the wade (both patches hidden)
  or the farplane fog covers it. Settle it: load m3l1a, get `level.progress` past "water", look
  seaward, and/or `r_showtris`.
- Whether retail MOHAA 1.11 also produced alpha 0 from the 2-parameter `alphaGen tCoord`.
  Settle it: run the same map under `MOHAA.exe` and compare the waterline.
- The actual fill cost of 8 blended, `cull none`, `nopicmip` stages over a 15,872 x 1,392 unit
  band. It is 24 triangles of geometry and a large fraction of the lower frame in fill - that
  is a reasoned estimate, not a measurement. Settle it: `r_speeds` / GPU time with
  `coop_noCrest 1` and with the two dead stages removed.
- Whether the gl2 `vertexScale > 8.0f` clamp on the ocean flap is visible as a gl1/gl2
  difference at the horizon. Settle it: same shot, `cl_renderer opengl1` vs `opengl2`.

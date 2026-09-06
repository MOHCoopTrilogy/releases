# Ocean / shoreline / underwater — modern techniques vs. what this engine can actually do

Lane: *what modern games do, minimum renderer feature per technique, reachability here.*
Everything below is cited to code or measured from `maps/m3l1a.bsp`.
Read-only pass. Nothing under `C:\mohaa-coop-dev` was modified.

Paths: `E/` = `C:\mohaa-coop-dev\openmohaa-hzm\code\`, `M/` = `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`.

---

## 0. Corrections to the brief — read these first

Three of the premises I was handed are wrong or incomplete. Two of them change what is buildable.

**0.1 — `renderergl1` DOES have FBOs and GLSL.** The brief says "renderergl1 has no FBO or GLSL at
all." It has both, capability-gated behind runtime-resolved function pointers:
`qglCreateShader` at `E/renderergl1/tr_postprocess_gl1.c:520`, `qglGenFramebuffers` at `:569`,
with a full availability guard at `:601-602`. It also does **grab passes** —
`qglCopyTexSubImage2D(GL_TEXTURE_2D, 0,0,0,0,0, s.width, s.height)` at `:871, :876, :1093, :1112,
:1130`. What gl1 lacks is per-surface GLSL: the main scene draw is still fixed-function, and there
is no `renderergl1/glsl/` directory. So gl1 can carry full-screen effects but not shader-stage
programs. This does not change any ranking below, but "gl1 can't do post" is not a valid reason to
reject anything.

**0.2 — There is a SECOND flat ocean patch nobody has mentioned.** `$ocean_wavy` = submodel `*84` =
`textures/misc_outside/deepbluesea` is documented. There is also **submodel `*85`**, surface 1644,
`textures/misc_outside/deepbluesea_runup`: another 15x15 / 225-control-point patch, **also every
control point at z = -520.0 exactly**, spanning y -13312..-2160, x -7872..8000. It sits *seaward*
of `*84` and is nearly twice as deep in y. Any proposal that replaces or animates "the ocean" and
touches only `*84` will leave a visible discontinuity at y = -2160 where `*85` stays flat.
(Given the session's own history — "the real obstruction turned out to be an ocean patch nobody had
looked for" — this is the same class of miss, one submodel further out.)

**0.3 — There is a dedicated wet-sand surface with SEVEN FREE SHADER STAGES.**
`textures/mohtest/omaha_set4_shoreline`: 6 planar worldspawn quads, 24 verts, 12 tris,
z -504..-480, **y -1024..-768**, x -7872..8000, `contentFlags 0x1` (solid), `surfaceparm sand`.
Its retail definition (`main/Pak0.pk3 scripts/mohtest.shader`) is **one stage / two bundles**:
`clampmapy textures/mohtest/omaha_set4_shoreline.tga` + `nextbundle map $lightmap`.
That is the swash zone. It is a *different shader name* from the 8-stage-capped
`deepbluesea_shoreline`, so **wet-sand and shore-locked foam work has 7 free stages and needs to
free nothing.** The brief framed the stage cap as the binding constraint on all shoreline work; it
is the binding constraint on the *water* shader only.

Note this surface already has HZM history: `E/renderergl2/tr_shader.c:817-840` (bug-2227) records
that it is **the only `clampmapy` in main/mainta/maintt**, and that gl2 was clamping S as well,
smearing one texel column across the whole 15,872-unit beach — "the blurred texture where the water
meets the sand". That is fixed. It also means the T axis of this surface is authored, deliberately,
as a **wet→dry gradient read once from waterline to dry sand**. A shore distance field already
exists here, in the art.

---

## 1. Measured ground truth (re-verified from the BSP, not from notes)

Source: `G:\GOG\...\main\Pak5.pk3!maps/m3l1a.bsp`, ident `2015`, version 19, 5,300,576 bytes.
157 shaders, 2088 surfaces, 10,826 drawverts, 246 models, 273 terrain patches.
Reader: `scratchpad/water/bspwater.py` (lump layout from `E/qcommon/qfiles.h:479-513`,
`dsurface_t` stride 108 from `:665-688`, `drawVert_t` stride 44 from `:636-643`; both lump lengths
divide exactly, which is the alignment check).

| surface set | type | count | verts | tris | extent | notes |
|---|---|---|---|---|---|---|
| `misc_outside/deepbluesea_shoreline` | PLANAR (SF_FACE), worldspawn | 12 | **48** | **24** | z -520..-479, y -2160..-768, x -7872..8000, t 0.005..0.994 | the waterline. **CONFIRMED exactly as briefed.** |
| `misc_outside/deepbluesea` | PATCH 15x15, submodel `*84` | 1 | 225 | — | **z -520.0 flat**, y -8000..-2160 | `subdivisions 4.0` stored in the BSP |
| `misc_outside/deepbluesea_runup` | PATCH 15x15, submodel `*85` | 1 | 225 | — | **z -520.0 flat**, y -13312..-2160 | **NOT in the brief** |
| `mohtest/omaha_set4_shoreline` | PLANAR, worldspawn | 6 | 24 | 12 | z -504..-480, y -1024..-768 | **solid sand**, 1 stage used |

Derived numbers that matter later:

* The waterline is **not horizontal**. z -520 at y -2160 → z -479 at y -768: **41 units of rise over
  1392 units**, a 1.69° slope. Fine for a mirror plane, fatal for anything that assumes z is constant.
* The two ocean patches are **perfectly planar** — every one of the 225 control points on each is at
  z = -520.0 with zero variance.
* **There is no seabed brush geometry.** Every brush surface entirely below z -510 is a beach
  obstacle: `general_industrial/ibeam_vert` (54), `das_boot/ironwall1` (54), `general_structure/jh_conc2`
  (25), `german/minen_post` (10), barrels. The sea floor is **terrain** (LUMP_TERRAIN), shader
  `textures/test/omaha_pjspick3` — 2 stages used, 6 free. (Terrain-patch stride 388 inferred from
  the lump length dividing exactly; the shader names it yields are all real, so I am confident, but
  mark this **PARTIALLY VERIFIED**.)
* worldspawn: `suncolor "85 88 89"` → luminance 87.2. That clears the 48 gate at
  `E/renderergl2/tr_postprocess.c:487`, so **`RB_SunRays` already runs on this map** whenever the
  sun is within the 0.25 dot cutoff (`:468`).

---

## 2. Renderer capability ledger — the answers the techniques depend on

| Capability | Present? | Citation |
|---|---|---|
| Scene **depth texture**, sampleable in post | **YES** | `tr.renderDepthImage` GL_DEPTH_COMPONENT24, `E/renderergl2/tr_image.c:3578`; attached `tr_fbo.c:301/317`; bound for sampling `GL_BindToTMU(tr.renderDepthImage, TB_LEVELSMAP)` `tr_postprocess.c:1633` |
| **Linear** depth copy (R32F) | **YES** | `tr.hdrDepthImage` GL_R32F `tr_image.c:3573`, `tr.hdrDepthFbo` `tr_fbo.c:408` |
| Full-size **colour scratch** for round-trip passes | **YES** | `tr.screenScratchImage` `tr_image.c:3565`; `tr.screenScratchFbo` `tr_fbo.c:315`; **colour-only alias** `tr.globalFogFbo` `tr_fbo.c:327` exists precisely so a depth-sampling pass can write colour without a feedback loop |
| **Render-to-texture** | **YES** | every FBO above; `FBO_Blit` / `FBO_FastBlit` |
| **Second camera pass** with arbitrary origin+axis | **YES, and it ships** | `R_RenderView(&newParms)` at `E/renderergl2/tr_sky_portal.cpp:184`, origin from `tr.refdef.sky_origin` |
| **Planar mirror** machinery | **YES, wired** | `R_MirrorViewBySurface` `tr_main.c:1430`, invoked `tr_main.c:1701` for any `shader->sort <= SS_PORTAL`; `sort portal` sets `shader.isPortal` `tr_shader.c:2739-2742` |
| …but a portal **anchor entity** | **NO — nothing emits one** | `RT_PORTALSURFACE` appears in the whole tree only as the enum `E/renderercommon/tr_types.h:87` plus 5 renderer *consumers*. No `fgame`/`cgame`/`client` code ever sets `reType = RT_PORTALSURFACE`. `R_GetPortalOrientations` therefore falls to `return qfalse` at `tr_main.c:1259` and the surface **draws nothing at all** |
| Mirror on a **patch** surface | **BROKEN by construction** | `R_PlaneForSurface` `tr_main.c:1097-1131` handles SF_FACE / SF_TRIANGLES / SF_POLY; **SF_GRID falls to `default:` → normal (1,0,0), dist 0** (`:1127-1130`) |
| Mirror recursion / count | **1 per frame, no nesting** | `break` at `tr_main.c:1704`; `if (tr.viewParms.isPortal) return qfalse` `tr_main.c:1437` |
| **Cubemaps / IBL** | present, **off by default** | `r_cubeMapping` default `"0"`, `CVAR_LATCH`, `tr_init.c:1528`; force-disabled below GL 3.0 `tr_init.c:482-484`; HZM auto-probe placement `tr_bsp.c:2618`, `MAX_AUTO_CUBEMAPS 64` `tr_local.h:2547` |
| Shader stage sampling the **scene colour** (`$screen`) | **NO** | stage image parse accepts only `$whiteimage` / `$lightmap` / `$deluxemap` — `tr_shader.c:732-747`; everything else goes to `R_FindImageFile` `:793` |
| `tcGen environment` / `environment2` / `vector` | **YES, implemented** | parse `tr_shader.c:1787-1810`; executed `glsl/generic_vp.glsl:149,156`, `glsl/lightall_vp.glsl:106,113` |
| `alphaGen dot` (**Fresnel**) | **PARSED, NOT IMPLEMENTED IN gl2** | parse `tr_shader.c:1626-1702`; gl2 explicitly lists it unimplemented at `tr_shade.c:801`; gl1 implements it — `RB_CalcAlphaFromDot`, `E/renderergl1/tr_shade_calc.c:1075` |
| `alphaGen lightingSpecular` (sun glint) | **YES**, in the vertex program | `tr_shade.c:745`; `glsl/generic_vp.glsl:216` |
| `alphaGen sCoord/tCoord` (**shore distance ramp**) | **YES**, vertex program | `tr_shade.c:751-753`; already used by the blood stage in `M/scripts/zz_coop_shoreline.shader` |
| `tcMod turb` / `wavetrant` | **YES** | `tr_shader.c:475, :650`; `tr_shade.c:218, :247` |
| **Terrain** honours full shader pipeline (stages/deform/tcGen) | **YES** | `RB_DrawTerrainTris` `tr_surface.c:1352` batches into `tess` via `RB_CHECKOVERFLOW` `:1366` |
| **G-buffer / normals+roughness** | **NO** | forward shaded; HDR FBO + post blits only |
| **Per-object velocity** | **NO** | camera motion blur only |

### Deform budget — the number that decides §3

* `MAX_SHADER_STAGES 8` — `E/renderergl2/tr_local.h:252`, `E/renderergl1/tr_local.h:278`.
* **`MAX_SHADER_DEFORMS 3`** — `tr_local.h:426`; over-limit warning `tr_shader.c:2103`.
  **`zz_coop_shoreline.shader` uses one of three.** Two deform slots are free on the waterline.
* All deforms in the list execute — `RB_DeformTessGeometry` loops `numDeforms`, `tr_shade_calc.c:704-716`.
* Any shader with **more than one** deform goes down the **CPU** path — `ShaderRequiresCPUDeforms`,
  `tr_local.h:2842-2863`. On 48 vertices that is free.
* `deformVertexes wave <div> …` → `deformationSpread = 1.0f / div` (`ParseDeform`, `tr_shader.c` ~`:2166+`),
  and the per-vertex phase offset is `(xyz[0]+xyz[1]+xyz[2]) * deformationSpread` —
  `RB_CalcDeformVertexes`, `tr_shade_calc.c:133-141`.
* **Displacement is along the vertex normal, and only along the vertex normal** — `tr_shade_calc.c:143-148`.
  This single fact kills Gerstner (see §3.1).

---

## 3. The techniques, each with its minimum renderer feature and a verdict

### 3.1 Gerstner / FFT waves — **NOT REACHABLE as such. Sum-of-sines is.**

*What modern games do.* Tessendorf FFT (Sea of Thieves, AC: Black Flag, Crysis) or a stack of 4–8
Gerstner waves evaluated in a vertex/domain shader on a dense grid — screen-space-projected grid or
clipmap, typically 100k–1M verts in view. Gerstner's defining property is **horizontal** vertex
displacement: `x += Q·A·D·cos(…)`, `z += A·sin(…)`. That is what sharpens crests and hollows troughs.
Without it you have a sine sheet, not an ocean.

*Minimum renderer feature.* (a) horizontal per-vertex displacement, (b) vertex density ≥ ~2 samples
per wavelength.

*Reachability here.* **Both fail.**

(a) `deformVertexes wave` moves each vertex by `offset[] * scale` where `offset` is the unpacked
vertex **normal** (`tr_shade_calc.c:143-148`). On a water plane every normal is +Z. There is no
keyword that displaces horizontally per-vertex: `deformVertexes move` translates **every vertex by
the same vector** (uniform, not phase-varying), and `bulge` also rides the normal. So a crest can
rise and fall but can never lean. **Gerstner is off the table without new engine code.**

(b) Density. Measured: the visible ocean is 225 control points, and the flat-patch path *reduces*
that. `R_SubdividePatchToGrid` computes `maxLen` then hits `if (maxLen < 0.1f)` at
`E/renderergl2/tr_curve.c:515` — which is **before** the `if (maxLen <= r_subdivisions->value)` test
at `:529`. On a plane `maxLen` is 0 for every span, so the flat patch is never subdivided **and no
cvar can change that.** BRIEF CONFIRMED. It then gets *worse*: the colinear-cull pass at `:570-593`
deletes every interior column/row marked 999 — and because `for (i=1; i<width-1; i++)` does **not**
decrement `i` after a removal, it deletes roughly every second one. 15 → **~8**. So the final grid
is about **8x8 = 64 verts over 15,872 x 5,840 units ≈ one vertex every 2,270u in x**.

That is also the real, measurable reason retail commented out its own wave. Both
`deepbluesea` and `deepbluesea_runup` carry, verbatim:

```
////	deformvertexes wave 1000 sin 0 40 0 .20
	deformvertexes flap t 10 sin 0 10 0 .10 0 10
```

`div 1000` → spread 0.001 → **one full cycle per 1000 world units**. At ~2,270u vertex spacing that
is **under half a sample per wavelength** — roughly 4.5x below Nyquist. It would not have produced
waves; it would have produced random per-vertex jitter that visibly crawls as the camera moves.
The seam story the project has been carrying is *also* true (amplitude 40 against a shoreline band
that shares the z = -520 edge at y = -2160 would tear by up to 40 units), but under-sampling is the
prior and larger failure, and it is the one that is measurable.

*What IS reachable:* **sum-of-two-sines, on a mesh you supply** (§3.2). Two `deformVertexes wave`
entries with different `div` and `freq` in the two free deform slots give crossing swells; add
`deformVertexes normal` for micro-chop on the shading normal. That is the 2003 water look done
well — Far Cry 1 / HL2 tier — not the 2015 look. Be honest with the user about which.

**Verdict: cosmetic-only variant reachable (sum-of-sines). True Gerstner requires an engine change
(a new `DEFORM_GERSTNER` case in `RB_DeformTessGeometry`, ~60 lines) AND a dense mesh, so it is
gated on §3.2 regardless.**

---

### 3.2 Replacing the water surface with a denser mesh — **REACHABLE via entity model. cmpatch is not the route.**

This is the linchpin. Four candidate routes; I checked all four.

**(a) `cmpatch/<map>.txt` — NO. It is collision-only, definitively.**
`E/qcommon/cm_load.c:1263-1287` reads the file and does exactly one thing per index:
`cm.brushes[idx].contents = 0;`. `cm_load.c` is the qcommon **collision** model. Render surfaces
come from `tr_bsp.c`'s independent parse of the same file. cmpatch cannot add, subdivide, or even
hide a visible surface. **BRIEF QUESTION ANSWERED: cmpatch is collision-only.**

**(b) Denser BSP patch — NO without a recompile,** and even a recompile doesn't help by itself:
`subdivisions` is stored per-surface in the BSP (`dsurface_t.subdivisions`, `E/qcommon/qfiles.h:687`
— it reads 4.0 on both ocean patches) but the flat early-out at `tr_curve.c:515` ignores it. You
would have to author control points that are *not* coplanar so `maxLen ≥ 0.1`. That is a BSP edit.

**(c) `script_model` / TIKI / MD3 plane — YES.** MD3 is a live loader in gl2
(`MOD_MESH`, `E/renderergl2/tr_model.c:75, :408`), and `RE_RegisterModel` dispatches on file
extension through `modelLoaders[]` (`tr_model.c:308-318`). Entity surfaces batch into the same
`tess` and therefore get the **same** `RB_DeformTessGeometry` (`tr_shade.c:2631`). Budget:
`SHADER_MAX_VERTEXES 2048` (`E/qcommon/qfiles.h:40`) is a *batch* limit, not a model limit —
`RB_CHECKOVERFLOW` (`tr_local.h:3183`) simply flushes and starts a new batch, and because
`DEFORM_WAVE`'s phase is `(x+y+z)*spread` in the **model** space of that entity, the wave stays
continuous across the split. So a tiled water plane of arbitrary total density is legal.

Sizing it honestly: to hit 2 samples per 1000u wavelength across the 15,872 x 5,840 unit ocean you
need ~500u spacing → 32 x 12 = **~380 verts**, one batch, trivially cheap. To hit 4 samples you need
~2,900 verts across ~2 batches. **This is not a performance problem. It is an art-asset and
placement problem.**

Real risks, stated plainly:
* Sorting. An entity water plane sorts by entity depth against a translucent world surface. The
  existing `deepbluesea_runup` writes depth (`depthwrite` in its first stage) and `deepbluesea` is
  fully opaque (§3.5); expect z-fighting at z = -520 unless the old surfaces are suppressed.
* Suppressing the old surfaces is the hard half. There is no runtime "hide this BSP face". Retiring
  them means overriding `deepbluesea` / `deepbluesea_runup` / `deepbluesea_shoreline` to a
  `surfaceparm nodraw`-style definition, which is a **global** rename-scoped change affecting every
  map that uses those names, not just m3l1a. That is the same contested-shader machinery
  `zz_coop_shoreline.shader` documents at its head, and the same blast radius.
* Submodels `*84`/`*85` are `bmodel` entities; whether the mod can bind/hide them from script is
  **UNVERIFIED** and would settle a much cheaper variant of this whole item.

**(d) Terrain — NO at runtime**, but worth knowing terrain honours full shaders (`tr_surface.c:1352`),
which is what makes §3.6 caustics work.

**Verdict: reachable, cosmetic-only (no exe/dll ship) if the old surfaces can be suppressed by
shader override alone. Medium-high effort, medium risk, high payoff — it unblocks 3.1, 3.3 and 3.5.**

---

### 3.3 Shoreline: foam driven by shore distance, wet-sand wash, splash-on-objects

*What modern games do.* Bake a **signed distance to shoreline** into a texture or vertex channel,
then drive: foam intensity `= 1 - saturate(d/w)`; a swash line that moves with the wave phase; wet
sand as a darkened + gloss-boosted blend keyed on `wetness = step(swashLine, d)` with a slow dry-out
falloff; and foam **accumulation** in front of obstacles from a depth-difference term
(the modern trick is "intersection foam": `foam = 1 - saturate((sceneDepth - surfaceDepth) * k)`).

*Minimum renderer features.* (1) a per-pixel shore-distance signal; (2) a phase clock shared with
the wave; (3) for intersection foam, **scene depth readable by the water surface's own shader**.

*Reachability.*

(1) **Already free.** On the 12 waterline quads the **T texcoord is the shore distance field**, and
this is measured, not asserted: t runs 0.005 at the seaward edge to 0.994 at the water's edge over a
1392-unit band → **1,409 world units per unit of T**. `alphaGen tCoord` is implemented in gl2
(`tr_shade.c:751-753`) and the shipped blood stage already exploits it. On the sand strip,
`clampmapy` means the *art itself* is a single wet→dry ramp across T (`tr_shader.c:823-828`).

(2) **Already free and already solved once.** Every relevant generator — `deformVertexes flap`'s
scale (`RB_CalcFlapVertexes`), `rgbGen wave`, `tcMod scroll`, `tcMod wavetrant` — is a function of
**time alone and globally identical**. That is exactly what the existing crest stage's 6.25s / 12.5s
phase lock relies on. So a stage on `omaha_set4_shoreline` can be locked to the same clock as the
crest on `deepbluesea_shoreline`, across a 15,872-unit beach, for free. **This is the single most
under-exploited fact in the whole system.**

(3) **NOT reachable.** Intersection foam needs the water's fragment shader to sample scene depth.
There is no `$screen`/`$depth` stage token (`tr_shader.c:732-747`), and gl2's shader-stage path is
`generic`/`lightall`, not a per-shader custom program. Depth-difference foam therefore needs an
engine change.

**Concrete, high-value, zero-renderer-change moves, in order:**

* **Wet-sand swash on `omaha_set4_shoreline`.** 7 free stages. A multiply stage
  (`blendFunc GL_DST_COLOR GL_ZERO`) over a T-gradient with `tcMod scroll` in T and `clampmapy`
  already clamping the axis gives a **darkening line that runs up and down the beach**, phase-locked
  to the 12.5s flap. This is the effect the user is describing when they say the wash doesn't respond
  to the beach, and it costs **one shader file** and touches nothing that is at its cap.
* **Foam that stays put at the water's edge.** Also on the sand shader, additive, `alphaGen tCoord`
  with the ramp peaked at the wet end, phase-locked. The existing crest stage scrolls *shoreward*
  (correctly); this is the complementary term that does **not** scroll and instead pulses in place.
* **Splash-against-objects:** the obstacle inventory already exists and is *generated* —
  `docs/tools/gen_m3l1a_obstacles.py` derives every hedgehog / minepole / Belgian-gate origin and
  radius from `LUMP_STATICMODELDEF` and emits `level.coop_obstX/Y/R`. Spawning a small looping splash
  FX at each obstacle inside the wash band, phase-locked to the same 12.5s clock, is **script + FX
  work against a table that is already built.** No renderer, no shader cap. This is the cheapest
  visible win on the whole list.

**Verdict: highest gain-per-risk on the board. All three are cosmetic-only. Do these first.**

---

### 3.4 Reflection and refraction

**(a) Planar reflection (mirror).** *Modern equivalent:* render the scene from the mirrored camera
into an RT, sample with a normal-perturbed screen-space UV, blend by Fresnel.

Minimum features: mirrored second camera pass (**YES** — `tr_sky_portal.cpp:184` proves a live one);
a surface flagged as a portal (**YES** — `sort portal`, `tr_shader.c:2739-2742`); a portal anchor
entity (**NO — nothing in the game code emits `RT_PORTALSURFACE`**); a valid surface plane
(**only on SF_FACE**, `tr_main.c:1097-1131`).

So the gap is small and precisely located: **a cgame-side `RT_PORTALSURFACE` refEntity placed within
64 units of the water plane** (`d > 64 || d < -64` cull, `tr_main.c:1190`), with
`origin == oldorigin` to select the mirror branch (`tr_main.c:1194-1207`). That is on the order of
20 lines in cgame.

But then the constraints bite hard:
* Only the **12 waterline SF_FACE quads** can carry it. The two ocean patches are **SF_GRID** and get
  a degenerate `(1,0,0)` plane at `tr_main.c:1127-1130` — a mirror there reflects across a vertical
  plane through the world origin. Garbage, silently, with no warning.
* **One mirror per frame** (`tr_main.c:1704`), and the 12 quads sit on ~4 distinct planes. You get a
  reflection on one of them.
* Cost is a **full extra scene render**. On the Omaha beach beat — the highest actor count in the
  game — that is the worst possible place to double scene cost.
* `sort portal` reorders the water against everything translucent near it.

**Verdict: reachable but a bad trade for this shot. Needs a dll ship (cgame). Rank low.**

**(b) Screen-space refraction.** Minimum feature: the water shader samples the scene colour behind
it. **Absent** — no `$screen` token (`tr_shader.c:732-747`). The *primitive* exists in both renderers
(`FBO_FastBlit`; gl1's `qglCopyTexSubImage2D` grab pass at `tr_postprocess_gl1.c:871`), so this is
"engine work that is clearly possible", not "architecturally blocked". Cost: a new stage token, a
colour grab before the water sort bucket, and a `TCGEN_SCREEN`. Exe + dll ship. **Rank low; high
effort, and the payoff over a good `tcMod turb` fake is small at these grazing view angles.**

**(c) Cheap cubemap / skybox-only reflection — REACHABLE TODAY, and this is the one to take.**
`tcGen environment` is parsed (`tr_shader.c:1787`) and executed in the vertex programs
(`generic_vp.glsl:149`, `lightall_vp.glsl:106`). A sphere-map stage of the map's own sky, additive
or blended over the water, gives view-dependent sky reflection with **zero renderer change**.
Pair it with `alphaGen lightingSpecular` (implemented, `generic_vp.glsl:216`) for sun glitter — and
m3l1a has a real sun (`suncolor "85 88 89"`, luminance 87.2).

**The blocker for doing this properly is Fresnel, and Fresnel is a ~30-line gl2 fix.**
`alphaGen dot`/`oneMinusDot` is what makes a reflection strengthen at grazing angles and vanish at
nadir — without it a sky reflection reads as a flat sheen. It is **parsed** in gl2
(`tr_shader.c:1626-1702`) but explicitly **not implemented**: `tr_shade.c:801` lists
`AGEN_DOT, AGEN_ONE_MINUS_DOT` among "still unimplemented in gl2". gl1 has it:
`RB_CalcAlphaFromDot`, `E/renderergl1/tr_shade_calc.c:1075-1093` —
`f = dot(N, normalize(viewOrigin - xyz))²`, lerped between `alphaMin` and `alphaMax`.

Porting it is contained (it is per-vertex, and gl2 already has the identical `AGEN_SCOORD/TCOORD`
"done entirely in vertex program" idiom right above at `tr_shade.c:751`). **And it is not water-only:**
the same `tr_shade.c` comment records **9 shipped stages** using `alphaGen dot` — foliage in
`trees.shader` and `coop_1936_imports.shader` — that are rendering with the wrong alpha in the
shipping renderer today. **This is the best single engine change on the list: small, testable, fixes
an existing bug, and unlocks the whole reflection lane.**

**Verdict: (c) is the reflection answer. `tcGen environment` today (cosmetic-only); the gl2
`alphaGen dot` port (renderer dll ship) to make it read correctly and to fix 9 existing stages.**

---

### 3.5 The surface seen from below — **A ONE-LINE FIX, AND I CAN NAME THE LINE**

The 2026-09-05 finding "`*84` is OPAQUE FROM BELOW" has a precise cause, and it is in the retail
data, not the engine.

`textures/misc_outside/deepbluesea` (`main/Pak0.pk3 scripts/misc_outside.shader`) — first stage:

```
{ nopicmip
  map textures/misc_outside/oceandday1.tga
  rgbGen identityLighting
  tcMod scale 16 22
  tcMod scroll 0.01 .03
nextbundle ... }
```

**No `blendFunc`.** No blend func means `GLS_DEFAULT` — fully opaque. `cull none` makes it
double-sided, so from underneath you get an opaque ceiling. By contrast `deepbluesea_runup`'s first
stage is `blendFunc blend` + `depthwrite`, and `deepbluesea_shoreline`'s is `blendFunc blend`. **The
open-ocean patch is the only one of the three that is opaque, and it is opaque by omission.**

Adding `blendFunc blend` + an `alphaGen` to a `zz_`-scoped override of `deepbluesea` makes the
surface translucent from both sides. That is the prerequisite for Snell's window, for seeing the
Higgins hull silhouette from underwater, and for the "look up at the surface" beat the map wants.
**Cosmetic-only, one shader file, no ship.** Caveat: it changes `deepbluesea` on every map that uses
it, and it will expose whatever is above the water on maps where nothing was meant to be visible.

*What modern games do here:* total internal reflection past the ~48.6° critical angle, so the
surface becomes a mirror of the sea floor outside a bright circular "Snell's window". That needs a
per-pixel view vector on the water surface — not reachable from a stage. A convincing cheat is a
second stage with `tcGen environment` and `alphaGen oneMinusDot` (again gated on the §3.4 Fresnel
port) that brightens toward the vertical.

---

### 3.6 Underwater — mostly built. Here is what is genuinely missing.

The brief asks for the fog distance and what it occludes. Answering precisely:

**It is not a fog volume.** It is a post-process, `RB_HZMExtraFx` → `underwater_fp.glsl`, and it is
already a depth-driven Beer-Lambert volume — better than most of what I would otherwise be proposing:

* Reference distance `r_ppUnderwaterVis` = **900 game units** (≈22.9 m), `tr_postprocess.c:1464`.
* Per-channel extinction `σ = (3.10, 1.00, 1.90) / vis` — `tr_postprocess.c:1618`. Red dies ~3.1x
  faster than green; blue 1.9x (silt). At 900u: red 4%, green 37%.
* **Far clamp = `vis * 6.0` = 5,400 units**, `tr_postprocess.c:1551` — six e-foldings of green,
  T_g = 0.0025, i.e. solid silt.
* **What it occludes: everything, including the sky.** It reads `tr.renderDepthImage` per pixel
  (`tr_postprocess.c:1633`) and a pixel that wrote no depth — the skybox — is clamped to the far
  distance and resolves to opaque silt (`underwater_fp.glsl` head note). That is deliberate: it is
  what hides the skybox wall continuing below the waterline on m3l1a (bug-2320), and it means the
  effect is a genuine volume, not a filter.
* Already present and tunable live: depth-scaled scatter blur (12-tap golden-angle,
  `r_ppUnderwaterBlur`), two-layer parallax **particulate** with density-modulating noise
  (`r_ppUnderwaterParticles`), **light shafts** (`r_ppUnderwaterShafts`), refraction ripple
  (`r_ppUnderwaterRipple`), silt colour `0.075 0.155 0.135`.

So of the five things the brief lists under "underwater", **three are done**: depth-based colour
extinction and murk (done, and done properly), particulate (done), god rays (a screen-space
approximation is done). What is actually missing:

* **Caustics on the sea floor — REACHABLE, cosmetic-only.** *Modern method:* project an animated
  caustic pattern along the light direction, usually two counter-scrolling copies of a Voronoi
  caustic tile multiplied together (which kills the obvious tiling), masked by depth-below-surface
  and by `N·L`. *Minimum feature:* a world-space planar projection of texcoords on the receiving
  surface. **`tcGen vector` is parsed (`tr_shader.c:1807-1810`) and implemented in the vertex
  programs.** And terrain honours the full shader path (`RB_DrawTerrainTris` → `tess`,
  `tr_surface.c:1352-1366`). The submerged seabed terrain shader `textures/test/omaha_pjspick3` uses
  **2 of 8 stages**. Two additive `tcGen vector` stages with opposite `tcMod scroll` and a `rgbGen
  wave` breathing term is the classic recipe and it fits with 6 stages to spare. The honest
  limitation: it will also draw above the waterline unless the shader is used only underwater — and
  since `omaha_pjspick3` shows 4 patches with `baseZ <= -480` and none above, that may already be
  true. **UNVERIFIED — needs the terrain heightmap decoded, not just `baseZ`.** That check is cheap
  and it is the one thing that decides this item.
* **True volumetric god rays from the surface.** `RB_SunRays` (`tr_postprocess.c:455`) already runs
  on this map. It is a screen-space radial blur from the projected sun, so underwater it produces a
  plausible shaft fan for free — but it is gated on `dot(sunDirection, viewAxis) >= 0.25` (`:468`),
  i.e. **only when you are looking at the sun**. Underwater the shafts should be visible looking
  *along* the surface too. Relaxing that gate while `r_ppUnderwater > 0` is a few lines in the post
  chain. **Renderer dll ship, small.**
* **The surface seen from below** — that is §3.5, and it is a shader-data fix.

---

## 4. What modern games actually do for *this exact shot* — and what transfers

The WWII beach landing (Saving Private Ryan / *MoH: Frontline* Omaha / *CoD:WWII* Normandy /
*Hell Let Loose*) leans on five things, in this order of visual weight:

| Technique | Weight in the shot | Transfers here? |
|---|---|---|
| **Foam and wash keyed to the shoreline**, not scrolling past it | highest — it is what makes the sea look attached to the land | **YES, today, on a 1-stage surface with 7 free slots** (§3.3) |
| **Wet-sand darkening that follows the swash** | very high, and almost free | **YES, today** (§3.3) |
| **Water interaction with objects** — foam collars on obstacles, splash on impact | high; it is what sells "the sea is a place with things in it" | **YES** — script/FX using the already-generated obstacle table (§3.3) |
| **Fresnel-weighted sky/sun reflection** | high at eye height on a beach, where you are at a grazing angle | `tcGen environment` today; **needs the ~30-line gl2 `alphaGen dot` port to read right** (§3.4c) |
| **Gerstner swell with leaning crests** | high in wide shots, low in the ramp shot | **NO** without engine work + a new mesh (§3.1, §3.2) |
| Screen-space reflection / refraction | modest at these angles | **NO** without a G-buffer / `$screen` |
| Depth-based extinction underwater | very high | **ALREADY DONE, and done well** (§3.6) |

The load-bearing observation: at a landing-craft ramp the camera is **at water level**, looking at a
**grazing angle**. At grazing angles, geometric wave shape contributes far less than *reflection,
foam and the wet/dry line* — the surface is seen almost edge-on, so vertical displacement is
foreshortened while Fresnel reflectance approaches 1. **The expensive items (waves with real shape)
are the ones that matter least in the shot the user is actually building. The cheap items matter
most.** That is unusually convenient and it drives the ranking.

---

## 5. Ranking — (visual gain) / (risk x effort)

| # | Item | Gain | Effort | Risk | Ships | Verdict |
|---|---|---|---|---|---|---|
| 1 | **Wet-sand swash + shore-locked foam on `omaha_set4_shoreline`** (§0.3, §3.3) | High | Low | Low | **shader only** | Do first. 7 free stages, an authored wet→dry gradient, and a global time clock that phase-locks to the existing crest for free. |
| 2 | **Splash / foam collars on beach obstacles** (§3.3) | High | Low-Med | Low | script + FX | The obstacle table is already *generated* by `gen_m3l1a_obstacles.py`. No renderer, no shader cap. |
| 3 | **`deepbluesea` translucency from below** (§3.5) | Med-High | Very low | Med | **shader only** | One missing `blendFunc`. Unblocks every "look up at the surface" beat. Risk is global blast radius on other maps. |
| 4 | **Caustics on the submerged terrain** (§3.6) | High | Low-Med | Low-Med | **shader only** | `tcGen vector` implemented, terrain honours full shaders, 6 free stages. Gated on one cheap check. |
| 5 | **Port `alphaGen dot` to gl2** (§3.4c) | Med, then High | Low (~30 lines) | Low | renderer dll | Fixes 9 shipped stages that are wrong today, *and* unlocks Fresnel water. Best engine change on the list by a distance. |
| 6 | **`tcGen environment` sky reflection + `alphaGen lightingSpecular` glitter** (§3.4c) | Med alone, High after #5 | Low | Low | shader only | Cheap now, much better after #5. |
| 7 | **Second deform slot on the waterline** (§3.1) | Low-Med | Very low | Low | shader only | 2 of 3 deform slots free; a cross-swell `deformVertexes wave` on 48 verts is free CPU. Small effect, tiny cost. |
| 8 | **Relax the `RB_SunRays` view gate while underwater** (§3.6) | Med | Low | Low | renderer dll | Existing pass, wrong gate for the underwater case. |
| 9 | **Dense entity water plane + sum-of-sines** (§3.2, §3.1) | High in wide shots | High | High | shader + script (+ maybe dll) | The only route to waves with shape. Blocked on suppressing 3 retail surfaces globally. A project, not a pass. |
| 10 | **Planar reflection via `RT_PORTALSURFACE`** (§3.4a) | Med | Med | High | cgame dll | Doubles scene cost in the highest-actor-count scene in the game; patches cannot carry it; one mirror per frame. |
| 11 | **Screen-space refraction (`$screen` token)** (§3.4b) | Low-Med | High | Med | exe + dll | Payoff over a good `tcMod turb` fake is small at grazing angles. |
| — | Gerstner/FFT, SSR, deferred water | — | — | — | — | **Not reachable.** No horizontal per-vertex displacement, no G-buffer, no per-object velocity. |

---

## 6. What I could NOT determine offline, and what would settle it

1. **Whether the submerged terrain shader `textures/test/omaha_pjspick3` also appears above the
   waterline.** Decides whether caustics (#4) can be scoped by shader name alone or need a second
   shader. *Settled by:* decoding `dterPatch_t.heightmap[9][9]` x `scale` + `baseZ` for the 4
   patches instead of trusting `baseZ` alone. ~20 lines on top of `scratchpad/water/terrain.py`.
2. **Terrain-patch stride 388.** Inferred from `105924 / 388 = 273` dividing exactly and the shader
   names coming out real. Not read from a `sizeof` assertion. *Settled by:* one `sizeof(dterPatch_t)`
   print, or the engine's own terrain-lump stride in `tr_bsp.c`.
3. **Whether the mod can hide or rebind BSP submodels `*84`/`*85` from script.** If yes, item #9's
   hardest half (suppressing the retail surfaces without a global shader override) collapses to a
   per-map script line, and #9 moves up several places. *Settled by:* grepping `fgame` for
   submodel/bmodel entity binding and testing `hide` on a `*NN` model on a live server.
4. **Actual frame cost of the mirror pass on the Omaha ramp beat.** I have the algorithmic answer (a
   full second `R_RenderView`) but not a number on this map with 100+ actors. *Settled by:* a
   timedemo with `r_portalOnly 1` (`tr_init.c:1962`).
5. **Whether `alphaGen dot` on water reads correctly at m3l1a's eye height and 1.69° slope.**
   *Settled by:* running gl1 (which implements it) with a test shader and comparing — a genuinely
   free A/B, since gl1 still ships.
6. **Whether any other map's `deepbluesea` view would break if it became translucent** (#3's risk).
   *Settled by:* the BSP sweep already written — run `bspwater.py` over all 160 shipped BSPs and
   list every map with a `deepbluesea` surface plus what sits above it.

---

## 7. Two traps worth recording regardless of what gets built

* **`alphaGen dot` is a silent no-op in the shipping renderer.** It parses without complaint
  (`tr_shader.c:1626`) and then falls to `default:` in gl2's alpha switch, leaving whatever the
  `rgbGen` put there — `tr_shade.c:795-812`. There *is* a warning, but it is `PRINT_DEVELOPER`, i.e.
  gated behind `developer 1`. Anyone authoring Fresnel water against gl1 and shipping to gl2 will
  get a different picture with no visible error. The same applies to `AGEN_NOISE`, `AGEN_SKYALPHA`,
  `AGEN_ONE_MINUS_SKYALPHA`, `AGEN_HEIGHT_FADE`.
* **A flat patch cannot be densified by any cvar, and `r_subdivisions` will look like it should
  work.** The flat early-out is at `tr_curve.c:515` and the `r_subdivisions` test is at `:529` —
  fourteen lines later, permanently unreachable for a plane. The colinear cull at `:570-593` then
  *halves* the grid, using a loop that skips every other candidate. Both ocean patches on m3l1a are
  exactly planar (225/225 control points at z = -520.0), so both are subject to this.

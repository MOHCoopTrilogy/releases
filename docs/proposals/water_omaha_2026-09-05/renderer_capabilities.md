# What this renderer can actually do for water
## Lane: renderergl2 / renderergl1 capability audit, m3l1a measured from the BSP
### 2026-09-05. Every claim carries a file:line or a measured number. Nothing under C:\mohaa-coop-dev was edited.

Paths are relative to `C:\mohaa-coop-dev\openmohaa-hzm\code\` unless stated.

---

# 0. SCORECARD ON THE PRIOR CLAIMS

Re-verified from source and from `main/Pak5.pk3 maps/m3l1a.bsp` (BSP ident `2015`, version 19).

| Prior claim | Verdict | Evidence |
|---|---|---|
| MAX_SHADER_STAGES is 8 in both renderers | **TRUE** | `renderergl2/tr_local.h:252`, `renderergl1/tr_local.h:278` |
| gl2 rejects the ENTIRE shader on a 9th stage | **TRUE** | `renderergl2/tr_shader.c:2529-2531` returns `qfalse` -> `:4520-4523` sets `shader.defaultShader = qtrue` |
| gl1 has no bound check and writes past the array | **TRUE** | `renderergl1/tr_shader.c:2249-2266` - the stage branch has no `s >= MAX_SHADER_STAGES` test at all; `ParseStage(&unfoggedStages[s], ...)` with `unfoggedStages[MAX_SHADER_STAGES]` at `:38` and `texMods[MAX_SHADER_STAGES][4]` at `:40` |
| Retail `deformvertexes wave` is commented out above `flap` | **TRUE** | `main/Pak0.pk3 scripts/misc_outside.shader`, `textures/misc_outside/deepbluesea` |
| Waterline is 12 four-vertex quads / 48 verts / 24 tris | **TRUE but INCOMPLETE** | 12 x `deepbluesea_shoreline` PLANAR, 4 verts each - surfaces 610-617, 633-636. There are **6 more** quads in the same band using `textures/mohtest/omaha_set4_shoreline` (surfaces 621,623,625,627,629,631). See section 7. |
| Open ocean is a 15x15 patch, all 225 control points at z -520 | **TRUE** | surface 1643, `patchWidth=15 patchHeight=15`, unique z set = `{-520.0}` exactly |
| Collapses to 8x8 via the `maxLen < 0.1f` early-out, which runs BEFORE the `r_subdivisions` test | **TRUE** | `renderergl2/tr_curve.c:515-522` (early-out) precedes `:529` (`maxLen <= r_subdivisions->value`); the 999 marks are then culled at `:570-582`. Simulated faithfully: 15x15 flat -> **8x8**, 9x9 -> 5x5, 33x33 -> 17x17 |
| `tessSize` is SkipRestOfLine'd at runtime in both | **TRUE** | `renderergl2/tr_shader.c:2654-2657`, `renderergl1/tr_shader.c:2307-2310` |
| `$ocean_wavy` is submodel *84, deepbluesea, z -520, y -8000..-2160, 225 verts | **TRUE** | entity lump: `{"model" "*84" "targetname" "ocean_wavy" "classname" "script_object"}` |
| renderergl1 has no FBO or GLSL at all | **FALSE - this is wrong** | `renderergl1/tr_postprocess_gl1.c` is 1220 lines of GLSL post-processing with its own FBOs and its own **depth texture** (`GL_DEPTH_COMPONENT24` at `:623`, `sceneFbo` at `:629-632`). SSAO, DoF, bloom, tonemap, FXAA, sharpen, low-health, raindrops, heat haze, god rays, suppression all run there. See 2.4. |

## NEW findings the prior passes did not have

1. **There is a SECOND ocean patch.** Surface 1644, submodel **\*85**, shader `textures/misc_outside/deepbluesea_runup`, also 15x15, also **every control point at z -520 exactly**, spanning x -7872..8000, **y -13312..-2160** - i.e. it lies beyond/under \*84 and covers more than twice the area. Its entity is `{"model" "*85" "targetname" "ocean_calm" "classname" "script_object"}`. Any plan that hides or replaces `$ocean_wavy` and forgets `$ocean_calm` leaves a second flat 8x8 sheet of ocean in shot.
2. **The seam is now measured**, and the historical reason for backing out `deformvertexes wave` is confirmed and quantified. See 5.1 - the ocean patch and the shoreline quads do **not** share vertices along y=-2160 except at the two extreme corners.
3. **A shader with ANY `deformVertexes` is permanently excluded from the entire gl2 lighting path** - no normal maps, no specular, no cubemap reflection. `renderergl2/tr_shader.c:3221-3225`. This is the most consequential constraint in this report. See 4.3.
4. **gl2 has a fully working "render an arbitrary camera into an arbitrary FBO" facility**, already used three ways in shipping code. See 2.2. This is the green light for planar reflection.
5. **`RB_SurfacePolychain` never writes `tess.normal`** (`renderergl2/tr_surface.c`, whole function) - so runtime-injected geometry silently breaks every normal-dependent shader feature. See 5.4.

---

# 1. MEASURED GEOMETRY - m3l1a water, from the BSP

Parser: `bsp.py` / `bsp2.py` in this directory. Struct layout from `qcommon/qfiles.h:665-690` (`dsurface_t`, 108 bytes), `:646-652` (`drawVert_t`, 44 bytes), `:544-548` (`dshader_t`, 140 bytes), `:516-535` (`dheader_t` + `Q_GetLumpByVersion`).

Map totals: 157 shaders, 2088 surfaces, 10826 drawverts, 246 models.

| surf | submodel | shader | type | verts | patch | z range | x range | y range |
|---:|---|---|---|---:|---|---|---|---|
| 1643 | \*84 `$ocean_wavy` | `misc_outside/deepbluesea` | PATCH | 225 | 15x15 | -520 flat | -7872..8000 | -8000..-2160 |
| 1644 | \*85 `$ocean_calm` | `misc_outside/deepbluesea_runup` | PATCH | 225 | 15x15 | -520 flat | -7872..8000 | -13312..-2160 |
| 610-617, 633-636 | \*0 world | `misc_outside/deepbluesea_shoreline` | PLANAR x12 | 4 each | - | -520..-479 | -7872..8000 | -2160..-768 |
| 621,623,625,627,629,631 | \*0 world | `mohtest/omaha_set4_shoreline` | PLANAR x6 | 4 each | - | -504..-480 | -7872..8000 | -1024..-768 |

**Actual rendered density of the ocean.** After `R_SubdividePatchToGrid` the 15x15 patch is an **8x8 grid = 64 vertices, 98 triangles** over 15872 x 5840 units. The kept columns are the even control indices; world positions:

```
x: 8000.0  5732.6  3465.1  1197.7  -1069.7  -3337.1  -5604.6  -7872.0     (2267.4u apart)
y: -2160.0 -2994.3 -3828.6 -4662.8 -5497.2  -6331.4  -7165.7  -8000.0     ( 834.3u apart)
```

For scale: **MOHAA terrain** on this same map is a 9x9 heightfield per 512x512 patch (`renderergl2/tr_terrain.c:802,814` place the far corner at `patch->x0 + 512.0f`; `:1511` `float heightmap[81]`) = **64-unit vertex spacing**. The beach under the water is ~35x denser in x and ~13x denser in y than the water on top of it.

**Actual density of the waterline.** The 12 `deepbluesea_shoreline` quads are not uniform:

```
surf 635: x 2368 -> 8000   = 5632 units wide, ONE quad, 4 vertices
surf 633: x -7872 -> -2304 = 5568 units wide, ONE quad, 4 vertices
surf 612: x -704 -> 320    = 1024 units wide
```

At the two ends of the beach the wash has vertices **5632 units apart**. No per-vertex effect of any kind can shape it there.

The quads are **sloped**, not flat: z -520 at the seaward edge (y=-2160) rising to -479.0 at the landward edge (y=-768). Over 1392 units that is a 1.7-degree ramp.

---

# 2. WHAT THE RENDERER ACTUALLY HAS

## 2.1 There IS a usable depth texture. YES.

`tr.renderDepthImage` is a real `GL_DEPTH_COMPONENT24` texture, `renderergl2/tr_image.c:3578`:

```c
tr.renderDepthImage = R_CreateImage("*renderdepth", NULL, width, height, IMGTYPE_COLORALPHA,
                                    IMGFLAG_NO_COMPRESSION | IMGFLAG_CLAMPTOEDGE, GL_DEPTH_COMPONENT24);
```

Attached as `GL_DEPTH_ATTACHMENT` to `renderFbo` (`tr_fbo.c:301`), `msaaResolveFbo` (`:294`), `screenScratchFbo` (`:317`), `sunRaysFbo` (`:336`), and **already sampled by shipping post passes**: `tr_postprocess.c:243`, `:1218`, `:1372`, `:1633` (`GL_BindToTMU(tr.renderDepthImage, TB_LEVELSMAP)`).

`glsl/underwater_fp.glsl` already reconstructs exact eye distance from it: `z_ndc = 2*zw - 1; d = P14 / (P10 + z_ndc)`, with `zw >= 0.9999999` treated as sky.

**Consequence:** every depth-driven water effect - extinction by distance, depth-based shoreline foam, soft-edge intersection, screen-space caustic projection - is reachable in the post chain today with **no new engine facility**, only a new pass.

**What depth alone does NOT give you:** normals. There is no G-buffer. gl1's own SSAO comment says so explicitly (`renderergl1/tr_postprocess_gl1.c:171`, "crude screen-space ambient occlusion from the depth buffer (no normals)"). You can derive a screen-space normal by differencing reconstructed positions - fine for a flat water plane, bad at silhouettes. Enough for a refraction offset; **not** enough for correct SSR.

## 2.2 Render-to-texture from a second camera. YES - fully supported, already used three ways.

`viewParms_t` carries `targetFbo`, `targetFboLayer`, `targetFboCubemapIndex` (`tr_local.h:1125-1127`). `RB_DrawSurfs` binds it at `tr_backend.c:350-358`. `R_RenderView(&parms)` with those set renders a complete world pass from an arbitrary origin/axis into an arbitrary FBO. Shipping call sites:

* **Cubemap probes**: `R_RenderCubemapSide`, `tr_main.c:3606-3730` - `parms.targetFbo = tr.renderCubeFbo` (`:3721`), `parms.flags = VPF_NOVIEWMODEL | VPF_NOCUBEMAPS` (`:3702`), fov 90, six sides. Called from `tr_bsp.c:2895` at map load.
* **Sun shadow cascades**: `tr_main.c:3555` `shadowParms.targetFbo = tr.sunShadowFbo[level]`.
* **Projected shadows**: `tr_main.c:2668` `shadowParms.targetFbo = tr.pshadowFbos[i]`.

Suppression flags available (`tr_local.h:1096-1111`): `VPF_NOVIEWMODEL`, `VPF_NOCUBEMAPS`, `VPF_DEPTHCLAMP`, `VPF_ORTHOGRAPHIC`, `VPF_FARPLANEFRUSTUM`.

**Consequence: a planar reflection pass is architecturally free.** Mirror the camera through z = -520, render into a half-res FBO with `VPF_NOVIEWMODEL|VPF_NOCUBEMAPS`, bind the result. The plumbing exists; the work is a new FBO, a mirrored `viewParms_t`, an oblique near-plane clip (or a "cull below z=-520" hack), and a way to bind that texture to a shader stage (2.5).

Also note there is a *second* proven recursive-view precedent: `renderergl2/tr_sky_portal.cpp:113-200` `R_Sky_Render` calls `R_RenderView(&newParms)` for the 3D skybox - into the same framebuffer rather than an FBO, but it proves nested `R_RenderView` is safe in this fork (with the HZM caveat at `:196-200` that the outer view's matrices must be re-derived afterwards).

## 2.3 Mirror/portal surfaces. EXISTS IN THE RENDERER, DEAD IN THIS GAME.

`R_MirrorViewBySurface` (`tr_main.c:1430`, called at `:1701`) and `R_GetPortalOrientations` (`:1144`) are intact Q3 mirror code, and the parser accepts `portal` (`tr_shader.c:2739-2742`).

Two independent reasons it cannot be used for water:

1. **No game-side producer.** `R_GetPortalOrientations:1180-1187` requires a `refEntity_t` with `reType == RT_PORTALSURFACE` within 64 units of the surface plane, and returns `qfalse` if none is found (`:1258-1268`). A repo-wide grep for `RT_PORTALSURFACE` returns **only** `renderercommon/tr_types.h:87` and four renderer sites. **Nothing in `fgame/`, `cgame/` or `client/` ever creates one.**
2. **`R_PlaneForSurface` does not handle `SF_GRID`.** Its switch (`tr_main.c`) covers `SF_FACE`, `SF_TRIANGLES`, `SF_POLY`, and `default:` returns `normal = (1,0,0), dist = 0`. Both ocean patches are `MST_PATCH` -> `SF_GRID`. A patch can never be a mirror here.

The 12 shoreline quads *are* `SF_FACE` and pass test 2 - but test 1 still kills it. Using the portal path means writing the game-side `RT_PORTALSURFACE` emitter too, at which point the direct `targetFbo` route in 2.2 is strictly simpler.

## 2.4 renderergl1 also has FBOs, GLSL and a depth copy. (Corrects the brief.)

`renderergl1/tr_postprocess_gl1.c:1-7`:

> "the engine renders the frame NORMALLY to the backbuffer; `RB_PostFxApply` copies it into a texture, runs shader passes on the copy, and draws the result back. No render-target redirect."

It resolves `qglGenFramebuffers`/`qglCreateProgram`/etc as extension pointers (`:15-45`), creates `sceneColor` + `sceneDepth` (`GL_DEPTH_COMPONENT24`, `:621-623`) and `sceneFbo` (`:629-632`), and grabs the frame with `qglCopyTexSubImage2D` (`:871, 876, 1093-1206`). `RB_PostFxApply` is called from `renderergl1/tr_backend.c:1037` and `:1302`.

**Consequence:** any post-chain water effect can be brought to gl1 too. gl1 is not the "no shaders" renderer the brief assumed. It *is* still the weaker one for forward-path work (2 texture bundles, no lightall/normal-map path, no HDR FBO), and it is the binding constraint on shader authoring - but not on post.

## 2.5 There is NO `$currentRender`. Screen-space refraction needs an engine hook.

The shader parser's special map names are exactly three (`renderergl2/tr_shader.c:732, 737, 747`): `$whiteimage`, `$lightmap`, `$deluxemap`. A world shader stage cannot sample the framebuffer.

The machinery to add one is present: `FBO_BlitFromTexture` / `FBO_Blit` (`tr_fbo.c`), `tr.screenScratchFbo` / `screenScratchImage` (`tr_local.h:2224, 2243`), and gl1's `qglCopyTexSubImage2D`. A grab-pass would be:

* a new special map name (say `$screenmap`) binding a dedicated copy image;
* a hook in `RB_DrawSurfs` that, on crossing from `< SS_BLEND0` to the water's sort key (sort keys at `tr_local.h:224-248`), blits the colour buffer into that image once per view.

Roughly 60-100 lines across both renderers. Medium effort, medium risk (sort-order interactions, MSAA resolve timing). It is the **only** route to true refraction.

## 2.6 Cubemap IBL exists and is wired, but is OFF and probe-limited.

* `r_cubeMapping` default **"0"**, `CVAR_ARCHIVE | CVAR_LATCH` (`tr_init.c:1528`); force-disabled below GL 3.0 (`:482-485`).
* `r_cubemapSize` default 128 (`:1529`). `MAX_AUTO_CUBEMAPS` 64 (`tr_local.h:2547`).
* `glsl/lightall_fp.glsl:23-24, 43-44, 509-537` does real roughness-mipped IBL: `textureCubeLod(u_CubeMap, R + parallax, ROUGHNESS_MIPS * roughness) * u_EnableTextures.w`, multiplied by `EnvironmentBRDF(roughness, NE, specular.rgb)`. Binding at `tr_shade.c:2104-2119`.
* HZM already wrote automatic probe placement from `info_pathnode` with farthest-point sampling (`tr_bsp.c:2610-2760`), because MOHAA maps contain zero `misc_cubemap` and zero `info_player_deathmatch`.
* Probes render at map load through the 2.2 machinery (`tr_bsp.c:2880-2900`) and can be baked to `cubemaps/<map>/NNN.dds` (`RB_ExportCubemaps`, `tr_backend.c:2430-2492`), so they can be **pre-baked and shipped in the pk3**.
* Dynamic per-frame cubemap re-render is present but `if (0)`'d out at `tr_scene.c:697-709`.

**The catch:** a cubemap is only sampled by the lightall program group, and 4.3 shows any `deformVertexes` disqualifies a shader from that group.

---

# 3. SHADER STAGE AND BUNDLE LIMITS - exact numbers and exact failure modes

| Limit | gl2 | gl1 | Cite |
|---|---:|---:|---|
| `MAX_SHADER_STAGES` | 8 | 8 | `renderergl2/tr_local.h:252`, `renderergl1/tr_local.h:278` |
| `NUM_TEXTURE_BUNDLES` (declared) | 7 | 2 | `renderergl2/tr_local.h:509`, `renderergl1/tr_local.h:476` |
| `NUM_TEXTURE_BUNDLES` (actually rendered as `nextbundle`) | **2** | 2 | `renderergl2/tr_shade.c:2063-2091` - the generic path handles `bundle[0]` and `bundle[1]` only; bundles 2-6 are the lightall slots (`TB_NORMALMAP`=2 ... `TB_CUBEMAP`=6, `tr_local.h:497-508`) |
| `TR_MAX_TEXMODS` per bundle | 4 | 4 | `tr_local.h:406` / `:390` |
| `MAX_SHADER_DEFORMS` | 3 | 3 | `renderergl2/tr_local.h:426` |
| `SHADER_MAX_VERTEXES` (tess batch) | 2048 | 2048 | `qcommon/qfiles.h:40` |
| `SHADER_MAX_INDEXES` | 12288 | 12288 | `qcommon/qfiles.h:41` |
| `MAX_GRID_SIZE` | 65 | 65 | `tr_local.h:1205` / `:772` |
| `MAX_PATCH_SIZE` (BSP control points) | 32 | 32 | `tr_local.h:1204` / `:771` |
| `MAX_POLYS` / `MAX_POLYVERTS` (runtime injection) | 131072 / 524288 | - | `renderergl2/tr_local.h:3886-3887` |

**gl2 9th-stage failure:** `tr_shader.c:2529` `if (s >= MAX_SHADER_STAGES) { warn; return qfalse; }`; `FindShader` at `:4520` catches it and sets `shader.defaultShader = qtrue`, so the surface renders as the checkerboard.

**gl1 9th-stage failure:** there is no check. `renderergl1/tr_shader.c:2249` goes straight to `ParseStage(&unfoggedStages[s], text, picmip)` and `:2265` does `s++` unconditionally. `unfoggedStages` is `static shaderStage_t[8]` at `:38`, `texMods` is `static texModInfo_t[8][4]` at `:40`. A 9th stage writes past both - silent corruption of file-scope statics.

### Freeing a stage in `zz_coop_shoreline.shader`

The file uses all 8. Concrete routes, in order of safety:

1. **Merge the four `wash2` stages into two.** Stages 3-6 are four near-identical additive `wash2` passes differing only in `tcMod scale` sign (+8/-8), `rgbGen wave` phase (.35/.325/.85/.825) and `wavetrant` phase (.5/.45/0/.95). Dropping the .325 and .825 members frees **two** stages and halves the beat density of the wash rather than removing it. *Needs a visual A/B; I cannot measure "looks the same" offline.*
2. **Move the blood stage onto a replacement water surface.** It lives on this shader only because this shader *is* the near-shore band by construction. If section 5 puts a new surface over the same band, the blood moves and frees a slot.
3. **Do NOT expect `ifCvar` to free a slot.** gl1's `ParseStage` still does `s++` for a stage disabled by `ifCvarnot` (`renderergl1/tr_shader.c:2251-2266`), leaving an inactive hole. It only guarantees the hole is at the end.
4. **Do NOT plan on bundles.** `nextbundle` gives you `bundle[1]` and nothing more at draw time in either renderer (`tr_shade.c:2063`). Every `wash2` stage already spends both.

---

# 4. deformVertexes - every mode, what it costs, and the exclusion nobody documented

## 4.1 The modes that exist

Parsed at `renderergl2/tr_shader.c:2082-2295`, dispatched at `tr_shade_calc.c:696-756`:

| Mode | Parse | CPU impl | GPU? | What it does |
|---|---|---|---|---|
| `wave <spread> <func> <base> <amp> <phase> <freq>` | `:2166-2189` | `RB_CalcDeformVertexes` | **YES** (`DGEN_WAVE_*`) | displace along vertex normal; phase offset `= (x+y+z) * spread` - a travelling plane wave along the (1,1,1) diagonal |
| `bulge <width> <height> <speed>` | `:2136-2163` | `RB_CalcBulgeVertexes` | **YES** (`DGEN_BULGE`) | displace along normal; phase `*= st.x` - a wave in texture space along S |
| `move <vec> <func> ...` | `:2211-2226` | `RB_CalcMoveVertexes` | no | rigid translate of the whole surface |
| `normal <freq> <amp>` | `:2192-2209` | `RB_CalcDeformNormals` | no | perturbs *normals* only, with noise; positions untouched |
| `flap s\|t <div> <func> <base> <amp> <phase> <freq> <min> <max>` | `:2237-2290` | `RB_CalcFlapVertexes` | no | MOHAA-specific. See 4.2 |
| `autoSprite`, `autoSprite2`, `projectionShadow`, `text0-7`, `lightglow` | - | - | no | not water-relevant |

GPU implementation: `glsl/generic_vp.glsl:90-135` `DeformPosition()`, driven by `u_DeformGen` / `u_DeformParams` set at `tr_shade.c:333-372`. Only `deforms[0]` is ever sent to the GPU (`tr_shade.c:341`, "only support the first one").

## 4.2 `flap` is a hinge, not a wave - and the code says so

`RB_CalcFlapVertexes` (`tr_shade_calc.c`): the wave `scale` is `WAVEVALUE(table, base, amplitude, phase, frequency)` with **no per-vertex term at all** - time only. The per-vertex part is `vertexScale = (max - min) * st[coordsToUse] + min`, a linear ramp of *amplitude* along S or T. Every vertex rises and falls **in the same instant**; only how far varies.

Note the HZM clamp in that function: `if (vertexScale > 8.0f) vertexScale = 8.0f;`. So `deepbluesea`'s `flap t 10 sin 0 10 0 .10 0 10` delivers at most `10 * 8 = 80` units of lift, not `10 * 10`, and saturates for every vertex with raw `t > 0.8`.

## 4.3 THE BIG ONE: any deform disqualifies a shader from the entire lighting path

`renderergl2/tr_shader.c:3216-3225`:

```c
static int CollapseStagesToGLSL(void)
{
    int i, j, numStages;
    qboolean skip = qfalse;

    // skip shaders with deforms
    if (shader.numDeforms != 0)
    {
        skip = qtrue;
    }
```

plus the second gate at `:3502` (`if (shader.numDeforms == 0)`, "convert any remaining lightingdiffuse stages to a lighting pass") and `:3468` (`if (r_sunlightMode->integer && shader.numDeforms == 0)`).

Consequences, all cited:

* `glslShaderGroup` is never set to `tr.lightallShader`; the stage renders through `tr.genericShader`.
* `normalMap` / `bumpMap` (`tr_shader.c:1058-1069`), `specularMap` (`:1071`), `normalScale` (`:1194-1226`), `specularScale` (`:1229+`), `parallaxDepth` (`:1180-1191`) are parsed but **do nothing**.
* `USE_CUBEMAP` in `lightall_fp.glsl:509-537` is unreachable - no IBL reflection.
* `r_sunlightMode` shadowing is skipped for that surface.

The reverse is equally true: **`lightall_vp.glsl` has no `DeformPosition` at all** (`USE_DEFORM_VERTEXES` appears only in `generic_vp.glsl`), and `LIGHTDEF_*` (`tr_local.h:792-802`) has no deform bit. The two paths are mutually exclusive by construction.

**So today the choice is binary: geometric waves, OR per-pixel normal-mapped specular/reflective water. Never both.**

### Cost of lifting that exclusion (engine work, gl2 only)

* **(a) CPU-deform + lightall.** Change `CollapseStagesToGLSL` to allow shaders whose deforms run on the CPU, and make `ShaderRequiresCPUDeforms` (`tr_local.h:2842-2864`) return `qtrue` for any shader that collapsed to lightall. `RB_DeformTessGeometry` already writes `tess.xyz` before stage iteration, and `RB_SurfaceVaoCached` already refuses the VAO fast path when CPU deforms are on (`tr_surface.c:414-416`), so lightall would read the deformed tess. **~30-50 lines, no new GLSL, no new program permutations.**
* **(b) GPU deform in lightall.** Add `LIGHTDEF_USE_DEFORM_VERTEXES` and port `DeformPosition` into `lightall_vp.glsl`. This **doubles `LIGHTDEF_COUNT` from 0x80 to 0x100** (`tr_local.h:802`) - 128 -> 256 lightall permutations compiled at startup. Not worth it when (a) exists.

Recommend (a). **UNVERIFIED:** I have not tested that lightall correctly consumes a CPU-deformed `tess.xyz`; the reasoning is structural.

## 4.4 GPU vs CPU deform - the rules

`ShaderRequiresCPUDeforms` (`tr_local.h:2842-2864`) returns **true** (CPU) when:
* `numDeforms > 1` - **any second deform forces the whole shader to CPU**;
* the deform is anything other than `wave` or `bulge`;
* `backEnd.refdef.floatTime != (float)backEnd.refdef.floatTime` (precision guard at high level time).

CPU deforms also cost the VAO cache (`tr_surface.c:414-416`), so the surface re-uploads through the dynamic tess path every frame. At 64 verts that is free; at 2000 verts / 60 fps it is ~120k vertex writes per second - still nothing, but it is the reason to prefer a single `wave` (GPU) over two deforms.

---

# 5. CAN A DENSER WATER SURFACE BE INTRODUCED WITHOUT A BSP RECOMPILE?

Five routes. Two dead, three live.

## 5.1 Subdivide the existing patch - DEAD by data, and the seam is now measured

`r_subdivisions` (default 4, `CVAR_ARCHIVE|CVAR_LATCH`, `tr_init.c:1464`) cannot help: `renderergl2/tr_curve.c:515-522` tests `maxLen < 0.1f` **before** `:529` tests `maxLen <= r_subdivisions->value`, and a perfectly flat patch has `maxLen == 0` exactly. Verified: all 225 control points of both patches are at z = -520.000000.

There is a **latent gl1-only hook** worth knowing about. `renderergl1/tr_bsp.c:784-790`:

```c
subdivisions = LittleFloat(ds->subdivisions);
if (subdivisions)                    grid = R_SubdividePatchToGrid(width, height, subdivisions * (r_subdivisions->value / 10.0), points);
else if (surf->shader->subdivisions) grid = R_SubdividePatchToGrid(width, height, surf->shader->subdivisions * (...), points);
else                                 grid = R_SubdividePatchToGrid(width, height, r_subdivisions->value, points);
```

Both special branches are dead in practice: `ds->subdivisions` is **0.0** for both m3l1a patches (measured), and `shader_t.subdivisions` (`renderergl1/tr_local.h:576`) is **never assigned anywhere in gl1** because `tesssize` is `SkipRestOfLine`'d (`renderergl1/tr_shader.c:2307`). Even if it were set, the flat early-out at `renderergl1/tr_curve.c:423` fires first. gl2 dropped the parameter entirely - its `R_SubdividePatchToGrid` (`tr_curve.c:445`) takes no subdivision argument.

The BSP shader lump *does* record `subdivisions = 4` for `deepbluesea` and `deepbluesea_runup` (0 for the shoreline) - the compiler knew these were meant to tessellate.

**The seam, measured.** The ocean patch's edge at y = -2160 and the shoreline quads' seaward edge at y = -2160 share vertices at **only two x positions**:

```
ocean 8x8 edge x:  8000.0  5732.6  3465.1  1197.7  -1069.7  -3337.1  -5604.6  -7872.0
shoreline edge x:  8000.0   2368    1344     320     -704     -2304            -7872.0
shared:            8000.0                                                      -7872.0
```

Any displacement that varies with x therefore tears the seam open everywhere between the two corners, no matter how carefully the two shaders' deform parameters are matched. (The z-slope difference is a red herring: the shoreline ramp is 1.7 degrees, so matched displacements along differing normals separate by only `amp * sin(1.7deg) = 0.03 * amp`.) **The seam is a topology problem, not a parameter problem, and no shader-only change can fix it.**

## 5.2 `cmpatch` - DEAD. Collision-only, and subtractive-only.

`qcommon/cm_load.c:1239-1290`. The entire effect of a cmpatch entry is one line:

```c
cm.brushes[idx].contents = 0;
```

It runs in `CM_LoadMap`, touches only `cm.brushes`, and never reaches `s_worldData` or any renderer structure. There is no add path, no vertex path, no surface path. `cmpatch/<map>_metal.txt` (`:1342-1370`) likewise only rewrites brush *side* surface flags in the collision model.

**cmpatch cannot add, subdivide, or even hide a visible surface. Full stop.**

## 5.3 Replace the ocean with a spawned model - LIVE, and the strong cosmetic-only option

Both ocean patches are **submodels owned by `script_object` entities**:

```
{ "model" "*84" "origin" "0 0 0" "targetname" "ocean_wavy" "classname" "script_object" }
{ "model" "*85" "origin" "0 0 0" "targetname" "ocean_calm" "classname" "script_object" }
```

so the script layer can already address them (hiding a bmodel from script is game-side - **UNVERIFIED**, see section 9).

A spawned `script_model` carrying a purpose-built TIKI plane goes through `SF_TIKI_SKEL` -> `RB_SkelMesh` (dispatch table at `renderergl2/tr_surface.c:1602-1624`), which writes **both** position and normal into tess (`tr_model.cpp:1664-1665`, `outXyz = tess.xyz[baseVertex]; outNormal = tess.normal[baseVertex];`). On a spawned model, therefore:

* `deformVertexes wave` works (GPU path, single deform);
* `alphaGen dot` / `oneMinusDot` work (they need normals);
* `tcGen environment` works (`generic_vp.glsl GenTexCoords`, `TCGEN_ENVIRONMENT_MAPPED`);
* mesh density is whatever you author, subject only to `SHADER_MAX_VERTEXES = 2048` per tess batch, which `RB_CHECKOVERFLOW` (`tr_local.h:3183`) splits automatically.

Density budget: a **45x45 grid = 2025 verts / 3872 tris** fits in exactly one tess batch. Across the 15872 x 5840 ocean that is **353 x 130 unit spacing** - 6.4x finer in both axes than today's 8x8, and about where a `deformVertexes wave` starts reading as swell rather than as a folding sheet. A 65x65 (4225 verts) costs three batches and gives 248 x 91 units.

Costs and risks:
* **Shader-name contest.** The `zz_` naming discipline documented in `zz_coop_shoreline.shader` (bug-2228) applies to any new water shader name.
* **Sorting.** A blended model plane and the world shoreline quads will fight at the join unless the world surfaces are hidden or the model is offset.
* **`deepbluesea`'s first stage is opaque** (`rgbGen identityLighting`, no `blendFunc`), which is exactly why the patch reads opaque from below. A replacement can choose otherwise.
* **Static-model LOD.** `RB_StaticMesh` applies `skelmodel->pLOD` under `r_staticlod` (`tr_model.cpp:2074-2113`); ship the TIKI with no LOD chain, or set `r_staticlod 0`.
* **UNVERIFIED:** maximum vertex count a MOHAA `.skd`/TIKI surface can carry, and whether a 16000-unit-wide model spawns and culls sanely.

## 5.4 Runtime poly injection from cgame - LIVE, cheapest to prototype, one gotcha

`cgi->R_AddPolyToScene` (`cgame/cg_public.h:300`) reaches `RE_AddPolyToScene2` (`renderergl2/tr_scene.c:910-934`, registered at `tr_init.c:2608` and `:2646`). Already used routinely in this build: `cg_beam.cpp:329,361,771,849,1433,1457`, `cg_marks.c:297,331`.

Headroom: `MAX_POLYS 131072`, `MAX_POLYVERTS 524288` (`tr_local.h:3886-3887`), overridable via `r_maxpolys` / `r_maxpolyverts` (`tr_init.c:2021-2022`). A **64x64 quad grid = 4096 polys / 16384 verts** is 3% of both budgets. cgame could evaluate a sum-of-Gerstner-waves on the CPU each frame and emit already-displaced vertices - no `deformVertexes` needed, arbitrary wave shape, and it is a **cgame.dll-only ship**.

**The gotcha:** `RB_SurfacePolychain` (`renderergl2/tr_surface.c`) writes `tess.xyz`, `tess.texCoords` and `tess.color` and **never `tess.normal`**. `polyVert_t` has no normal field to write. So on an `SF_POLY` surface the normal is whatever the previous surface in the same tess batch left there, and everything normal-dependent is undefined:

* `deformVertexes wave` / `flap` / `bulge` (all displace along `tess.normal`);
* `alphaGen dot` / `oneMinusDot` - which is what **retail's own `sf_deepbluesea` and `sf_ddayocean` use**;
* `tcGen environment` / `environmentmodel`.

Fixing it is ~8 lines per renderer: compute the fan's face normal from `verts[0..2]` and `R_VaoPackNormal` it into every vertex of the fan. That is a genuinely useful change beyond water (it also fixes beams and marks). **Until then, a poly water mesh must use only normal-free stages** - plain `map`, `rgbGen wave/const/vertex`, `alphaGen const/vertex/tCoord/sCoord`, `tcMod *`, `blendFunc *`. Enough for a scrolling, crested, tinted sheet; not enough for the retail look.

Second, smaller issue: `RE_AddPolyToScene2` never assigns `poly->fogIndex`, and `R_AddPolygonSurfaces` (`tr_scene.c:127`) reads it. The legacy `RE_AddPolyToScene` at `:137-200` does compute it, but that entry point is not the registered one. In practice `backEndData->polys` is hunk-allocated and zero, so poly surfaces get `fogIndex 0` = **no fog**. `R_AddPolygonSurfaces` also passes `cubeMap = 0` explicitly, so no IBL either.

## 5.5 Engine-side re-densification of the existing patch - LIVE, smallest diff, cleanest result

`ParseMesh` (`renderergl2/tr_bsp.c`) reads `patchWidth`/`patchHeight`, fills `points[]`, then calls `R_SubdividePatchToGrid(grid, width, height, points)`. Add a shader-name test before that call and pass a "force full subdivision" flag through to `R_SubdividePatchToGrid` which (i) skips the `maxLen < 0.1f` early-out at `tr_curve.c:515-522` and (ii) skips the colinear cull at `:570-595`. A 15x15 control patch then subdivides freely up to `MAX_GRID_SIZE 65`, yielding **65x65 = 4225 verts / 8192 tris** - 248 x 91 unit spacing.

**Smallest possible diff** (two guarded `if`s plus a flag), and it keeps everything: the surface stays a world `SF_GRID` with correct normals, correct fog, correct cubemap index, correct sorting, correct PVS. Works with `deformVertexes wave` on the GPU path.

Two things to watch:
* **Runtime grid LOD may undo it at range.** `RB_SurfaceGrid` (`tr_surface.c:906+`) decimates rows/columns whose `widthLodError[i] > LodErrorForVolume(...)`, where `LodErrorForVolume` returns `r_lodCurveError->value / distance` and `r_lodCurveError` defaults to **250** (`tr_init.c:1913`, `CVAR_ARCHIVE|CVAR_CHEAT`). Inserted columns get `errorTable = 1.0f/maxLen`, and on a near-flat patch `maxLen` is tiny, giving a huge error value that survives LOD - so it probably behaves correctly by accident. **UNVERIFIED**; needs an `r_showtris` check in-game.
* **The seam of 5.1 remains.** This does not densify the shoreline quads, which are `SF_FACE` and have no subdivision step in `ParseFace` at all. Pair with 5.3 or 5.4 for the waterline band, or add a hard "amplitude tapers to zero at y = -2160" term.

## 5.6 What is NOT available

* **`func_group` / brush additions**: there is no runtime BSP surface-add path anywhere. `s_worldData.surfaces` is sized and filled once in `R_LoadSurfaces`.
* **Terrain**: `SF_TERRAIN_PATCH` comes from `LUMP_TERRAIN` (`qcommon/qfiles.h:508`). No runtime add.
* **BSP recompile**: `code/tools/ommap/` **is present in this tree** (it is where `tesssize` is actually consumed - `tools/ommap/shaders.c:544-545`), but recompiling m3l1a needs the original `.map` source, which is not in the paks. Not a route.

---

# 6. REFLECTION AND REFRACTION - reachability, ranked

| Technique | Reachable? | What it needs | Ship |
|---|---|---|---|
| **`tcGen environment` sphere-map** | **NOW, no engine work** | a reflection texture + a stage; works alongside `deformVertexes` because it is a generic-path tcGen (`generic_vp.glsl GenTexCoords`, `TCGEN_ENVIRONMENT_MAPPED`). Computed **per-vertex**, so on today's 8x8 grid with all normals (0,0,1) it is one smooth gradient, not shimmer. Pair with `deformVertexes normal` (`RB_CalcDeformNormals`, CPU-only, perturbs normals with noise) or with any denser mesh from section 5 to make it live. | pk3 only |
| **Baked cubemap IBL** | **Reachable, blocked by 4.3** | `r_cubeMapping 1` (latched), probes already auto-placed (`tr_bsp.c:2610-2760`), bakeable to `cubemaps/<map>/*.dds` and shippable. Needs the water shader to reach `lightallShader`, i.e. **drop every `deformVertexes`** or do the 4.3(a) engine change. Also needs `r_normalMapping 1` (default 1) plus a `normalMap` stage; `r_specularMapping` defaults to **0** (`tr_init.c:1498`). | pk3 + cvars, or exe/dll for 4.3(a) |
| **Planar reflection (true mirror of the scene)** | **Reachable - machinery is shipping** | New FBO + mirrored `viewParms_t` + `R_RenderView` (2.2), an oblique/manual clip below z=-520, and a special map name to bind the result (2.5). Half-res is standard - the shipping cubemap path already renders at 128px. Cost is roughly one extra world pass: on a beach that means the whole skybox, ships and Higgins boats drawn twice. | **exe + cgame** |
| **Screen-space refraction (what is under the water, warped)** | **Reachable, needs a grab pass** | 2.5. Depth is already there so the warp can be depth-scaled correctly. Highest visual-gain-per-line in this family: it also gives correct "the sand looks wobbly through the water" and depth-faded shorelines. | **exe + cgame** |
| **Screen-space reflections (SSR)** | **NOT reachable honestly** | SSR needs per-pixel normals to build the reflection ray. There is no G-buffer - `renderergl2` is forward + HDR FBO + post blits, and there is no normal target in the FBO list at `tr_local.h:2238-2258`. Depth-derived normals are adequate on a flat plane, but the *reflected* geometry still has to be found by ray-marching depth, and everything off-screen or occluded is missing. On a beach shot the interesting reflections are the sky and the horizon ships - mostly off-screen. **Do not propose SSR.** Planar reflection is strictly better and costs about the same. |
| **Portal-surface mirror** | **Dead** | 2.3 - no game-side `RT_PORTALSURFACE` producer, and `R_PlaneForSurface` cannot derive a plane from `SF_GRID`. |

---

# 7. THE SIX QUADS NOBODY OVERRODE

`textures/mohtest/omaha_set4_shoreline`, surfaces 621/623/625/627/629/631, band y **-1024..-768**, z -504..-480. Definition (`main/Pak0.pk3 scripts/mohtest.shader`):

```
textures/mohtest/omaha_set4_shoreline
{
    qer_keyword sand
    qer_keyword terrain
    surfaceparm sand
    {
        clampmapy textures/mohtest/omaha_set4_shoreline.tga
    nextbundle
        map $lightmap
    }
}
```

BSP flags: `surfaceFlags 0x01000000`, `contentFlags 0x00000001` (CONTENTS_SOLID). This is the **wet-sand strip** - solid ground, one stage, two bundles, completely static, and **not overridden by the mod**. It has **7 free stages**.

That makes it the natural, nearly free home for "wet-sand darkening that follows the wash": one stage with `rgbGen wave` at the *same* frequency and phase as the shoreline shader's `flap` (`freq .08`, i.e. a 12.5 s period) darkens and brightens the sand in lockstep with the wash, with zero geometry, zero script, and no risk to the 8-stage shader. It is 6 quads / 24 verts so nothing per-vertex will work there, but `rgbGen wave` and `tcMod` are per-surface/per-pixel and do.

---

# 8. RANKED - (visual gain) / (risk x effort)

"Ship": **pk3** = cosmetic only, no binary; **cgame** = cgame.dll; **exe** = exe + cgame + game ship together per this project's rules.

| # | Item | Gain | Risk | Effort | Ship | Notes |
|---:|---|---|---|---|---|---|
| 1 | Wet-sand response on `omaha_set4_shoreline` (section 7) | med | **very low** | ~1 h | **pk3** | 7 free stages, untouched shader, phase-locked to the existing flap |
| 2 | Merge the redundant `wash2` pairs to free 2 stages (section 3) | none alone | low | ~1 h | **pk3** | Unblocks everything else on the 8-stage shader |
| 3 | `tcGen environment` + `deformVertexes normal` sky-tint reflection on the ocean patch | med | low | ~2 h | **pk3** | Works with the existing deform; coarse but cheap. Two deforms forces CPU - only 64 verts, so free |
| 4 | Engine re-densification of both ocean patches to 65x65 (5.5) + `deformVertexes wave` | **high** | med | ~1 d | **exe** | Smallest engine diff of any geometry route. Must be paired with a y-taper or with #5 or the seam tears |
| 5 | Runtime cgame Gerstner mesh over the waterline band (5.4) | **high** | med | ~2-3 d | **cgame** | No exe ship. Constrained to normal-free shader stages until #6 |
| 6 | Give `RB_SurfacePolychain` a real face normal (~8 lines x2 renderers) | enabler | low | ~2 h | **exe** | Unblocks #5 fully; also fixes beams and marks |
| 7 | Screen-space refraction grab pass (2.5) | **high** | med-high | ~3-4 d | **exe** | Largest single look change available. Depth is already there |
| 8 | Underwater caustics as a post pass (2.1) | med-high | low-med | ~1-2 d | **exe** | `underwater_fp.glsl` already reconstructs eye distance; projecting a caustic tile onto the reconstructed world position is a small addition to an existing shader |
| 9 | Spawned dense TIKI water plane replacing \*84/\*85 (5.3) | **high** | med-high | ~3-5 d | **pk3 + script** | Only route that is cosmetic-only *and* gives real geometry. Needs the script-side hide of **both** submodels and a TIKI authoring pipeline |
| 10 | Lift the deform/lightall exclusion, design (a) (4.3) | enabler, **high** | med | ~1 d | **exe** | Unlocks normal-mapped specular + cubemap IBL on any deformed water shader |
| 11 | Bake + ship cubemap probes, enable `r_cubeMapping` (2.6) | med | low | ~0.5 d | **pk3 + cvar** | Only pays off after #10 |
| 12 | Planar reflection pass (2.2) | **very high** | high | ~1-2 w | **exe** | Doubles world draw cost on the map with the most geometry in the game. Do it last, behind a cvar, at half res |
| - | SSR | - | - | - | - | **Do not attempt.** No G-buffer, and the reflections you want are off-screen |

---

# 9. WHAT I COULD NOT DETERMINE, AND WHAT WOULD SETTLE IT

1. **Whether a MOHAA script can hide a `script_object` bmodel** (`$ocean_wavy hide` / `$ocean_calm hide`). Game-side, outside this lane. **Settle it:** rcon the hide on m3l1a and look. If `hide` does not work, note that a shader override *can* make a surface invisible (`blendFunc GL_ZERO GL_ONE`, no depthwrite) but **cannot** use `surfaceparm nodraw` - `ParseMesh`/`ParseFace` test `s_worldData.shaders[ds->shaderNum].surfaceFlags & SURF_NODRAW` from the **BSP lump**, not from the runtime shader.
2. **Maximum vertex count per TIKI/`.skd` surface**, and whether a 16000-unit model spawns and culls sanely. **Settle it:** author a 45x45 test plane, spawn it, check `r_showtris` and the console for overflow warnings.
3. **Whether densified grid columns survive `LodErrorForVolume` at range** (5.5). **Settle it:** `r_showtris 1` at the water's edge and at the far end of the beach, with `r_lodCurveError` at default 250 and at 0.
4. **Whether merging the two redundant `wash2` stages is visually lossless** (section 3, item 1). **Settle it:** A/B screenshots at the same time-of-day and camera.
5. **Whether lightall correctly consumes a CPU-deformed `tess.xyz`** (4.3 design (a)). **Settle it:** prototype behind an `r_hzm*` cvar.
6. **The gl1 poly/normal situation.** I verified gl2's `RB_SurfacePolychain` omits normals; I did **not** open gl1's. **Settle it:** read `renderergl1/tr_surface.c RB_SurfacePolychain`.
7. **Whether `r_cubeMapping 1` is stable on this fork today.** It is `CVAR_LATCH`, defaults 0, and `vid_restart` from an open menu is a known crash in this renderer (noted at `tr_bsp.c:2645`). **Settle it:** set it in the cfg and boot cold.
8. **What the above-water global fog occludes on m3l1a.** I found the *underwater* far clamp (`r_ppUnderwaterVis` default **900** units, `tr_postprocess.c:1464`) and the silt colour (`r_ppUnderwaterSilt "0.075 0.155 0.135"`, `:1469`), but `rb_globalFog`'s distance is set per-map from the game side and I did not trace it.

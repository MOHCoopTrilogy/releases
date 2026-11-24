# Volumetric smoke for the biggest moments - design note (2026-11-23, PROTOTYPE, off by default)

User, asked "is it 3D?": the sprite approach stays for everything, plus true 3D volumes for a few big sources -
**"Do it"**. Scope: burning-wreck columns (up to 3 at once), artillery / barrage banks, optionally big fires' plumes.
Owner of the sprite Phase 1 work is another session (`H:\hzm_work\smokefire_eng`, branch `smokefire-eng`); this
work lives on its own engine worktree `H:\hzm_work\volsmoke-eng`, branch `volsmoke-eng` off `rel-1.10.38-engine`,
and touches none of its files. **Nothing here ships or turns on without the user's sign-off.**

## 1. Approach (one sentence)

A gl2-only screen pass, run once per frame for the main world view between the opaque scene and the sprite list,
raymarches a handful of analytic smoke primitives (column, bank) eroded by tiling 3D noise, lit by the map's sun,
sky and light grid and by the scene's dynamic lights (the wreck's own `firelight`), at half or quarter resolution,
depth-clipped against the scene-depth snapshot, then composited at full resolution with a depth-aware upsample.

## 2. Precedent copied (fix methodology)

| need | recipe already in the tree |
|---|---|
| world-space ray per pixel against the scene depth | `tr_hzm_mist.c` / `hzmmist_fp.glsl` (camera basis in `u_HzmCont0..3`, planar depth -> distance, IGN jitter) |
| half-res trace target, try-compiled programs, failure = feature off with one reason line, 3D noise texture, GL timestamp ring | `tr_hzm_clouds.c` (`R_HZM_Clouds_InitGL`, `RB_HZM_VclGpuMark`) |
| the depth snapshot and its valid flag | `RB_HZM_SceneDepthSnapshot` / `backEnd.softDepthValid` (`tr_backend.c`) - bug-4290: never reuse a stale snapshot |
| forward global fog of a fragment at a known distance | `vclouds_composite_fp.glsl` (the fog fraction formula of `generic_fp.glsl ApplyGlobalFog`) via `RB_SetGlobalFogUniforms` |
| a shader keyword that gl1 ignores | `qer_hzmSoftEdge` (`tr_shader.c`): new keywords only as `qer_*` (gl1 skips them; a stage keyword would fail the shader) |

## 3. Emitter hook - content only, no API bump

A volume source is **a sprite whose shader carries `qer_hzmVolSmoke <kind> <radius> <height> <density> <rise>`**
(kind 0 column, 1 bank). In `RB_SpriteSurfs` (gl2 backend), for the main world view, such sprites in the view's own
list become this view's sources: origin, sprite scale, `shaderRGBA` (rgb = smoke albedo tint, a = density multiplier
/ fade). A second keyword `qer_hzmVolSmokeAlt` marks the **old sprite column** that the volume replaces: markers and
Alt sprites are skipped by the sprite list only in a view where the volume ran, and drawn everywhere else. So:

- **tik / map script / fxwreck**: a source is an ordinary `originemitter` emitting the marker sprite (life, fadein,
  fadedelay, scalerate come free from the tempmodel system). Overlapping long-life particles at one origin are
  merged (alpha summed) so a 12 s particle respawned every 10 s cross-fades seamlessly. A script spawns it like any
  emitter tik (`spawn ... anim start`); `fxwreck.scr` needs no change - `coop_wreck.tik` gains one emitter, and its
  `col` emitter's shader gains `qer_hzmVolSmokeAlt`. fxwreck's rank-1..3 "full" wrecks are exactly the user's cap.
- **gl1 and r_hzmVolSmoke 0**: the marker shader's only stage is `blendFunc GL_ZERO GL_ONE` (invisible) and the
  Alt sprites draw as today - the sprite fallback is automatic, per frame, with no reload.
- **Live A/B**: `r_hzmVolSmoke 0 / 1 (low) / 2 (high)`, flags 0, default 0 (TRAPS T7: never ARCHIVE a knob that
  is meant to ship with a changed default). `r_hzmVolSmokeDebug` 1 = volume only over black, 2 = transmittance,
  3 = source bounds. `r_hzmVolSmokeTune "sun=1 amb=1 ext=1 fire=1 shadow=1"` look-dev overrides.
- No `re.*` / `cgi.*` entry, no protocol, no new uniform rows (the programs reuse the existing `u_HzmCont*`,
  `u_HzmFx*`, `u_VclNoise`, `u_VclVerts`, fog and depth names - the uniform table is by name), no capacity-family
  constant raised. Its own cap `HZM_VOLSMOKE_MAX 8` sizes the per-frame source texture (8 x 16 RGBA32F) and is
  checked at compile time against the texture height.

## 4. The volume (GLSL)

- **Column**: axis bends downwind with height (`axis(h) = base + wind * (h/H)^1.5`, wind = shader rise/shear +
  `vss_wind_x/y`); radius widens `R * (0.55 + 1.6 h/H)`; radial falloff, soft base and top. **Bank**: a flattened
  ellipsoid hugging the ground. Both eroded by two octaves of a 64^3 tiling Perlin-Worley texture generated at
  R_Init, advected upward at the rise speed and slowly swirled around the axis (rolling billows), seeded by the
  source origin so no two columns match.
- **Lighting**: Beer-Lambert extinction, energy-conserving step integration; a 3-4 step light march toward the sun
  (self-shadowing; the dark core and lit rim come from this); dual-lobe Henyey-Greenstein (g 0.55 / -0.25);
  sky ambient from `tr.hzmSkyZenith` (top) to the light-grid value at the source (bottom, ground bounce) so night
  maps stay dark; up to 4 nearest scene dlights (the wreck's `firelight` flicker) with an analytic half-way
  occlusion term - the fire lights the underside of its own column.
- **Fog**: each sample is fogged at its own distance with the forward-fog parameters (`u_GlobalFogParams/Color`),
  so a far column fades into the fog like the terrain behind it and is not over-fogged as the background would be.
- **Cast shadow** (high only): for an opaque pixel inside a source's sun-shadow footprint, the sun transmittance
  through the volume darkens the sun share of the destination (folded into the blend alpha).
- **Intersections**: the march ends at the scene depth, so the volume meets walls and ground softly by
  construction (no card edges).

## 5. Composite order

`RB_SpriteSurfs`, main world view only (not portal / portal-sky / shadow / cube / PiP / `RDF_NOWORLDMODEL`):
depth snapshot (taken if no sprite took it) -> trace (half or quarter res, RGBA16F: premultiplied scattered light,
transmittance) -> composite onto the HDR scene, blend `ONE, SRC_ALPHA` -> the sprite list as today -> post
(haze, bloom, tone). Consequences:

- sprites **in front** of a volume (muzzle smoke, impacts, the wreck's flame and embers) draw correctly over it;
- sprites **behind** a dense volume also draw over it (known limitation; the old column - the main sprite load at
  the same spot - is culled by the Alt keyword). The fix, if the look is approved, is a one-tap read of the volume
  transmittance in the sprite program (a GENERICDEF-free uniform branch) - not in this prototype.
- bloom and tone see the smoke (bright fire-lit undersides bloom; no double tone map).

## 6. Resolution, noise, upsample

Trace at 1/2 (high) or 1/4 (low) of the scene size, scissored to the screen rectangle of the sources' bounds
(computed on the CPU from the 8 box corners; full screen when the eye is inside one). Per ray the march covers only
the merged [t0, t1] spans of the source boxes, clipped to the scene depth; 40 (high) / 20 (low) steps shared over the
spans, start jittered by interleaved-gradient noise. Composite: 4 nearest trace texels, bilinear weights times a
depth-similarity weight against the full-res depth (each trace texel's depth is re-read at the exact full-res pixel
the trace used), which keeps smoke from bleeding across a silhouette (haloing). No temporal history in the prototype
(no ghosting risk); if the stills show grain, a reprojected 1-frame history is the next step.

## 7. Cost and budget

Target <= 1.5 ms GPU at 1440p for 3 columns on the user's RTX 5070 Ti. Estimate: half-res 1440p = 1280x720 rays;
3 columns cover ~25-40 % of the screen in a close shot -> ~0.3 M marched rays x 40 steps x (2 noise taps + 3 light
steps x 1 tap) ~ 60 M filtered 3D taps (R8, cache-friendly) ~ 0.4-0.8 ms; composite ~0.1 ms. Measured with an own
GPU timestamp ring (`r_hzmVolSmokeProbe 1`, `^~^~^ VOLSMOKEGPU p50/p99/max`) and the frame total from `r_gfxProbe 1`
(bit 2 is not used: it pins time and freezes the animation, TRAPS T14). Timing run is the only uncapped run.

## 8. Risks

| risk | mitigation |
|---|---|
| marker particle PVS-culled by cgame (`cg_cullTempModels`) when the wreck base is hidden but the column is not -> the column pops out | prototype measures it; integration = a one-line cgame bypass for marker sprites (ships cgame + gl2 together), or the marker emitted mid-column |
| sorting vs sprites behind the volume | section 5; old column culled; transmittance tap in the sprite program later |
| fill-rate on mid GPUs / 4K | quarter-res low preset, scissor, span-limited march, step cap; Intel iGPU off (clouds rule) |
| banding / grain | IGN jitter, energy-conserving integration, RGBA16F target |
| haloing at silhouettes | depth-aware upsample (section 6) |
| a stale or missing depth snapshot (bug-4290, bug-1211 class) | per-frame valid flag; no snapshot target (`hdrDepthFbo`) = feature off with a reason line |
| gl1 | markers invisible, Alt sprites draw: the sprite look, unchanged |
| look intensity overshoot (third time, PLAN section 8) | density and albedo per shader; A/B against the shipped column before any default |
| two sessions appending to the uniform table / backend | no new uniform rows; one new file + three small hooks |
| Omaha | the pass does nothing without a source; no Omaha content gets one |

## 9. Integration (after sign-off)

gl2 DLL + one content change (`coop_wreck.tik` vol emitter + Alt keyword on the column shader, under new names per
the PLAN's naming rule), optional cgame PVS bypass (ship together), a Quality-preset row value through
`gen_menu_graphics.py` (Low 1 / High 2 / off on Intel), barrage banks from the artillery tiks, fire plumes from
`coop_fin_fire_big.tik`. No mod script change is required.

## 10. Vetting record (2026-11-23, before coding)

One independent read-only review (engine / renderer lens), given this note and the code paths, not the conclusions.
Confirmed: by-name uniform lookup (a `sampler3D` through a `GLSL_INT` row is what the clouds already do), the invisible
`GL_ZERO GL_ONE` marker is accepted by `SPR_RegisterSprite` and harmless in both renderers, both parsers skip `qer*`,
tempmodel alpha/scale reach `RE_AddRefSpriteToScene` unchanged, `hdrDepthImage` is R32F window depth at scene size and
exists whenever `r_softParticles` (default 1) is on, the state to restore is `FBO_Bind(old)` + `SetViewportAndScissor`.
**Changed as a result (all folded into sections 3-5 as built):**
- **Sources are extracted in the BACKEND** from the view's own sprite list in `RB_SpriteSurfs`, not in
  `R_AddSpriteSurfaces`: mirror / portal views are spawned from inside the main view's sort and would have overwritten a
  frontend global, and `frameCount` does not separate two world scenes in one frame. The sprite list skips markers and
  Alt sprites **only in a view where the volume ran**, so the scope lens, glass / water reflections and portals keep
  the sprite column instead of showing nothing.
- **View gate**: no `RDF_NOWORLDMODEL`, no 2D, no `targetFbo`, not portal / portal-sky, none of `VPF_SHADOWMAP |
  DEPTHSHADOW | PSHADOW | ONLYVIEWMODEL | HZMXRAY | HZMPIP | HZMPLANAR` (the lens gun view has no target FBO).
- **Fog** is computed from `rb_globalFog` directly - `RB_SetGlobalFogUniforms` reads stale `tess` state and calls
  `ONE, SRC_ALPHA` unfoggable. With `r_globalFogForward 0` (screen fog pass) the samples are left unfogged and the pass
  fogs smoke and sprites alike at background depth.
- Depth bound through `R_MsaaDepthMinMaxOr`; 3D noise / table bound only via `GL_BindMultiTexture` (DSA cache).
- Over-cap sources: merge, then rank by apparent size, one loud warning (T4). Marker emitters must not use
  `collision` (its smoke lighting overwrites the rgb = albedo).
- Worst case flagged: eye inside a column = full-screen trace (~1.5-2.5 ms estimated) - early exit at T < 0.01 added,
  measured explicitly (the "up" camera).
Not changed: glass / water that write no depth get smoke composited over them (a sorting limitation, listed).

The GLSL lint (`glsl_variant_lint.py --post`) does not see function-local programs (the clouds' are not linted
either); both programs are TRY-built, so a driver reject turns the feature off with a reason line - the runtime
`^~^~^ VOLSMOKEBUILD supported=1` line is the compile proof.

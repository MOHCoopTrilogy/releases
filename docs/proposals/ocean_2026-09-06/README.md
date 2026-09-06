# The sea you ride on, the break, and the shore - Omaha (m3l1a) research, 2026-09-06

Research only; nothing under the project was edited. Builds on `docs/proposals/water_omaha_2026-09-05/`
(LANE-A geometry, `renderer_capabilities.md`, `WATER_MODERN_TECHNIQUES.md`) - those numbers are not
re-derived here unless this pass changed them. Its #1 (wet-sand swash) is BUILT (bug-2485, ragged by
bug-2493); the obstacle wash is built (bug-2479); the open-sea flap was tamed (bug-2478). This pass
starts from #2 and adds measurements the earlier lanes did not take. Paths: `E/` =
`openmohaa-hzm/code/`, `M/` = `hzm-mohaa-coop-mod/`; the pak copies that WIN are named per TRAPS T6
(`docs/TRAPS.md:308-356` - pak order decides, the `zz_` prefix buys nothing).

## 0. New this pass - measurements and corrections

1. **The waterline sheet's S is one continuous 0..1 across the whole beach** (BSP drawverts, surfaces
   610-617/633-636): S = 0.000 at x -7872, 1.000 at x 8000 = 15,872 u per S on every quad, and T is
   two rows, 0.005-0.494 and 0.494-0.994, continuous. So on the SHEET any `tcMod scale N 1` is
   seamless for any N, and **`tcMod scale 62 1` is a 256 u tile - the same period as the sand rag**.
   The sand strip (621-631) is the opposite: S restarts at 0.250 on every quad, 256 u per S, and
   every quad's x-min is a multiple of 256 from -7872, so the sand's rag phase is `0.25 + (x+7872)/256`
   on all six quads. A sheet bake at scale 62 with its column offset shifted by 0.25 S **coincides with
   the sand rag along the entire beach.** This is what makes a matching sheet edge possible at all.
2. **The straight edge has two causes, not one.** During the flood half of the flap the sheet ends at
   the quad edge y -768 (an alpha cut). During the ebb the sheet dips below the sand plane - rest
   height above the strip is 17.5 u at y -1024 and 1 u at y -768 (LANE-A) against a 16T dip at the
   trough (`M/scripts/zz_coop_shoreline.shader:35`), so for T > ~0.86 the sheet is under the sand and
   its visible edge is plane-meets-plane: a straight line by geometry, moving seaward. A static edge
   bake fixes the first cause only. Section 3 gives the smallest change that removes both.
3. **Additive stages cannot be masked after the fact.** Four of the six live sheet stages are
   `blendFunc add`; a later multiply/blend stage darkens or repaints the framebuffer (sand included)
   but cannot subtract light already added. An additive stage's edge is its own content, or its own
   alpha under `GL_SRC_ALPHA GL_ONE`. That rules out every "mask stage" idea in one line.
4. **`alphaGen lightingSpecular` in gl2 is lit by a hard-coded point, not the sun**:
   `E/renderergl2/glsl/generic_vp.glsl:216-223` uses `vec3(-960.0, 1980.0, 96.0)` in model space
   (the ioquake3 placeholder). On the world sheet that is a lamp 2,700 u inland, up the bluff. And
   **Omaha's sun is vertical**: worldspawn `sundirection "270 360 0"` (`map_entities/m3l1a_entities.txt:9`)
   through `AngleVectorsLeft` (`E/renderergl2/tr_sphere_shade.cpp:1290`) has zero horizontal
   component, so a physically correct sun glint on this map sits at the nadir, invisible from eye
   height. Sun glint is the wrong tool for Omaha; a sky sheen is the right one (section 4).
5. **gl1's `alphaGen dot` writes RGB, not alpha** (`E/renderergl1/tr_shade_calc.c:1075-1092`,
   `colors[0] = colors[1] = colors[2]`), and `dotView` prints one `PRINT_ALL` line PER VERTEX PER FRAME
   (`:1742-1760`). Any Fresnel port to gl2 must decide which behaviour is "parity"; never author
   `alphaGen dotView` on gl1.
6. **Retail shipped a Higgins wake and never used it on this map.** `main/Pak0.pk3 models/fx/wake.tik`
   (QUAKED `fx_water_higginswake`, skelmodel `wake.skd`: 1 surface, 44 verts / 52 tris, scale 0.52,
   textures `wake.tga`/`wake2.tga` beside it) drawn by `scripts/wake.shader` `wake`:
   `deformvertexes wave 30 sin 0 10 0 .2`, two scrolling `oceandday` layers and a `$lightmap`
   multiply. Zero references in `M/maps/m3l1a.scr`, the entity lump, or any coop map script (only
   the build-mode catalog lists it). Spearhead adds `models/emitters/waterWake.tik` (flat sprites,
   `life 15`, `accel -5 0 0`) and `waterRing.tik` (`life 10`), both `originemitter`-only, in
   `mainta/pak1` and `maintt/pak1` with their `effects.shader` sprites. These are the retail recipes
   the fix methodology asks for first.
7. **Retail's own better ocean exists in maintt**: `sf_ddayocean` / `sf_deepbluesea`
   (`maintt/pak1.pk3 scripts/misc_outside.shader`) use `deformVertexes bulge`, `tcMod turb`, an
   `alphaGen sCoord 2 -.1 .3 .6` (four params - retail knew), and a froth layer on
   `alphaGen oneMinusDot -1 1.1`. Two of those are gl2 gaps: `alphaGen dot` family unimplemented
   (`E/renderergl2/tr_shade.c:801`) and `tcMod bulge` never ported (bug-1242). UNVERIFIED which BSP
   references them; the recipe is what matters.
8. **No reflection/refraction pass exists.** `git -C openmohaa-hzm log`: `895358f8` "depth-driven
   water, refracting lens blood" is the underwater post pass plus `bloodspatter_fp.glsl`'s droplet
   lens (`E/renderergl2/tr_postprocess.c:1430-1484`, `r_ppBlood*`). A grep of renderergl2 for
   refract/reflection/cubemap finds only the (off) cubemap IBL and those post passes. The prior
   lane's finding stands: planar reflection = new FBO pass, refraction = a `$screen` grab pass.
9. **The bug-2493 texture generator is not in the repo.** `docs/tools/` has `gen_bloodwash.py` only;
   nothing under the tree mentions `wetsand_swash` except a public doc. The ragged sand textures are
   generated assets with no generator - TRAPS T2 territory. Restore it before touching them again.

## 1. What exists

**Geometry** (LANE-A, unchanged): open sea = two flat 15x15 patches drawn as 8x8 (`$ocean_wavy`
*84 y -8000..-2160, `$ocean_calm` *85 y -13312..-2160, both z -520; `$ocean_calm` hidden for good at
`M/maps/m3l1a.scr:2530`); waterline = 12 quads y -2160..-768, z -520 rising to -479; sand strip = 6
quads y -1024..-768, z -504..-480. `M/maps/m3l1a/coopified.scr:7395-7400` (`coop_waterZ`) is the
piecewise surface any script placement should use.

**Stages and program path.** MAX_SHADER_STAGES 8 (`E/renderergl2/tr_local.h:252`). gl2 sends any shader
with a deform down the generic program and every deform-free shader into lightall
(`E/renderergl2/tr_shader.c:3216-3225`); lightall drops `alphaGen sCoord/tCoord` (bug-2486) and the
generic path drops normal/specular/cubemap. Consequences per surface:

| surface | shader (winning copy) | deform | path | live stages | free |
|---|---|---|---|---|---|
| open sea | `M/scripts/zz_coop_ocean.shader` (flap max 1, `:71`) | flap t | generic | 2 | 6 |
| far sea (hidden) | retail `deepbluesea_runup` (maintt pak1) `flap t 10 sin 0 3 0 .10 0 3` | flap t | generic | 2 | 6 |
| waterline | `M/scripts/zz_coop_shoreline.shader` (`:35` flap `sin 0 4 0 .08 0 4`) | flap t | generic | 8 declared, **6 drawing** (stages 1-2 are alpha 0, LANE-A section 4) | 0 declared, **2 dead** |
| sand strip | `M/scripts/zz_coop_wetsand.shader` (no deform, on purpose `:74-76`) | none | lightall | 3 | 5 |
| seabed terrain | retail `textures/test/omaha_pjspick3` | none | lightall | 2 | 6 |

**Renderer vocabulary that is real on gl2** (parser `E/renderergl2/tr_shader.c`): deforms `wave`
(GPU), `bulge` (GPU), `move`, `normal` (CPU, `tr_shade_calc.c:242-247`), `flap s|t` (CPU, HZM clamp at
`tr_shade_calc.c:205/224`), autosprite; tcMods `turb scale scroll stretch transform rotate wavetrans
wavetrant entityTranslate` (`:445-660`); `tcGen environment/environmentmodel` in the vertex program
(`generic_vp.glsl:149-165`); alphaGen implemented: const, wave, entity, vertex, lightingSpecular
(hard-coded light), portal, sCoord/tCoord (4-param, generic only), distFade family
(`tr_shade.c:707-800`); alphaGen parsed-but-dead: dot, oneMinusDot, dotView, oneMinusDotView,
heightFade, noise, skyAlpha (`tr_shader.c:1626-1728`, `tr_shade.c:801`); `sort nearest` and
`sort underwater` (`tr_shader.c:2400-2402`). `tcMod turb` is a per-vertex matrix term
(`tr_shade.c:218-275`), so on a 4- or 64-vertex surface it is a smooth wobble, not chop.

**Post and lighting in play** (`coop_defaults.cfg:13,52,76`; `autoexec.cfg:1379,1545,1554,1595`):
`cg_effectdetail 1`, `r_ppBloom 1` (threshold 0.6), `r_ppSSAO 1`, `r_cubeMapping 0`,
`r_hzmGenNormals 1` at strength 1.5, `r_hzmSpecular 0.04`. The HZM specular applies only to stages
whose normal map was synthesised (`E/renderergl2/tr_shade.c:966-985`), i.e. lightall stages; no
water shader reaches it (deformed), and a deform-free water sheet is `surfaceparm nolightmap` with
no `lightingDiffuse`, so it would get no light vector either. **Specular on water is a generic-path
question, full stop.** Sky is `textures/sky/d-day2` = `skyParms env/dday2 512 -` (maintt pak1
`sky.shader`), fogged toward `farplane_color (.62 .62 .61)` (`M/maps/m3l1a.scr:194`;
`E/renderergl2/tr_sky.c:481-487`), farplane 2500/5000/8300 by `g_ddayfog` during the run-in
(`m3l1a.scr:1243-1253`).

## 2. The ride

**How the boats move.** Not a spline: script movers. `$higgins_fleet` (a `script_origin` at
`384 -7104 -256`, entities `:530-533`) does `movenorth 1800` in 10 s coop / 20 s SP (180 u/s), then
`movenorth 600` in 10 s (`m3l1a.scr:2422-2452`); then `$higgins1_move2` runs four legs
(32 u/3 s with 15 deg pitch-up, 160/2 s, 1224/10 s, 368/6 s, `:2472-2496`). The chain
model -> origin -> move -> move2 -> fleet is bound at `:694-745`, with `movedown 20` on every hull
(`:742`, the bug-2478 waterline). The bob is `higgins_wave_motions` (`:748-843`): six 1 s legs
(-6, -3, +3, +6, +3, -3 u) = **12 u peak-to-peak on a 6 s period**, roll +/-1.5 deg, pitch 1-2.5 deg,
alternating sign each cycle. The bow spray pair (`animate/fx_water_spray.tik`, entities `:479-481`
and `:1068-1070`: +/-200 x, +648 y, +32 z off the hull origin at `384 -7808 -504`, `:543`) is
switched `anim start`/`stop` per leg (`:772-799`) with the `wave_crash` alias on boat 1.

**What the sea does under it.** `zz_coop_ocean.shader:71` heaves the open sheet +/-10 x rawT on a
10 s cycle (rawT 0 at the seam, 1 at y -8000), so under the fleet at y -7100..-5000 it is +/-6..9 u
- the same order as the bob, **on a different period (6 s vs 10 s) with an unknowable phase**
(shader time is absolute server ms, script `level.time` is rebased; LANE-A section 8). Half of every
minute the hull and the sea move against each other. That is the residue of the "boats underwater"
report, and no shader edit reaches it.

**What would make it read as sea, from the boat, in order of payoff:**

- **Sync the bob to the sheet.** Cheapest: change the six legs to a 10 s cycle so the two never beat
  against each other (script only; phase still arbitrary but constant). Exact: cgame publishes
  `cg.time / 1000` once into a cvar the script reads (the `r_ppUnderwater` idiom, cg_view.c:5800),
  which resolves the phase - one line of cgame. Either is a bigger visual gain than anything below
  because the hull is the only object the eye can measure the water against.
- **A wake.** Spawn `models/fx/wake.tik`'s recipe as a coop `script_model` bound to `$higgins1` at
  the stern (the origin sits near the stern - the bow spray is 648 u ahead and the hull is 610 u
  long, bug-2478). Mint `models/fx/coop_wake.tik` rather than spawning the retail tik: its init block
  is `classname drivablevehicle` + `setsize/seatoffset/gravity/vehiclespeed/canjump`, none of which a
  script_model wants, and its shader's `$lightmap` multiply stage is meaningless on an entity - copy
  the shader under a coop-only name without that stage (T6: one file, one name). The wave deform works
  on it because a TIKI mesh writes real normals (`E/renderergl2/tr_model.cpp:1664-1665`), GPU path, no
  cap issues. Add a trail: `waterWake.tik`'s `originemitter` parked on a second carrier at the stern
  (`spawnrate 1`, `life 15` = ~15 flat sprites alive, `sort nearest` in its shader) - the carrier rule
  is satisfied, a script_model renders exactly its `originemitter` blocks
  (`E/cgame/cg_commands.cpp:5285-5310`, bug-2477). Budget: MAX_TEMPMODELS 4096
  (`E/cgame/cg_commands.h:749`), spawn counts scale by `cg_effectdetail` (`cg_tempmodels.cpp:1163`) which
  the mod ships at 1.0 (5x retail's 0.2 - the existing bow spray is already five times denser than
  retail's look; check it is not already too much before adding).
- **Whitecaps and foam streaks on the open sheet**: 6 free stages on `deepbluesea` (m3l1a-only). One
  additive `froth2.tga` (Pak2) stage, `tcMod scale 4 1`, a slow shoreward `tcMod scroll`, `rgbGen wave
  sin 0.3 0.2 0 0.10` (locked to the flap's 0.10 Hz so streaks brighten on the lift), plus `tcMod
  turb` for a lazy wobble. Per-pixel, so the 8x8 mesh is irrelevant. Keep summed additive rgb under
  ~0.7 or `r_ppBloom` (threshold 0.6) smears it into a glow.
- **A second frequency on the deep sheet is NOT reachable on the patch**: any `deformVertexes wave`
  is under-sampled at 2,270 u vertex spacing (WATER_MODERN_TECHNIQUES 3.1). A second `flap` is just a
  second hinge. Real swell needs a denser mesh - item 8 below.
- **Horizon**: the fog colour already matches the sky; the honest limitation is `$ocean_calm` being
  hidden after `:2530` so the sea past y -8000 is fog over nothing at farplane 5000-8300. Showing
  `$ocean_calm` again during the run-in (it is coplanar and now the only sheet that still heaves
  +/-9 u; LANE-A found the two can only avoid interpenetrating at ocean max 0.47) is a one-line test
  worth a screenshot before deciding.

## 3. The break and the shore

**Why the sheet's edge is straight** - section 0 items 2-3. The blood stage
(`zz_coop_shoreline.shader:131-163`) is the loudest part: `blendFunc blend`, `alphaGen tCoord 0.02
0.60 0 0.60` (`:157`) puts a 60 %-alpha red sheet on the quad edge at y -768, and its
`tcMod scale 16 2` tiles T twice so no bake can pin an edge to the band. The four wash stages and
the crest are additive and tile 8x/6x in T with T-wavetrant surge, so their content also cannot be
pinned. Nothing a 9th stage could do is missing; the cap is not the blocker here.

**The smallest change that rags it (recommended - item 1):** stop drawing the sheet over the sand
strip, and let the strip - already ragged and moving (bug-2493) - own the swash.

- On all six live sheet stages, fade alpha along raw T with the four-parameter form, generic path,
  works on gl2 (bug-1249) and gl1: `alphaGen tCoord 8.2 -10 0 1` = alpha 1 for T <= 0.72, 0 at
  T 0.82 (y -1160 to -1020, seaward of the strip's sea edge and of the ebb intersection at T ~0.86).
  Wash x4 and crest change `blendFunc add` to `GL_SRC_ALPHA GL_ONE` (identical when alpha is 1); the
  blood keeps `blend` and swaps its ramp for the same fade. `alphaGen` reads the RAW texcoord
  (`generic_vp.glsl:229-238`), so the wavetrant surge does not move the fade. ~12 tokens, zero stages,
  zero textures, and both causes of the line vanish: the sheet has no edge at y -768 (alpha 0 there)
  and it is transparent before it dips under the sand. The crest's shoreward run dying at T 0.82 is
  the wave collapsing at the break, which is what the user asked for on 09-04.
- Move the blood in the swash onto `zz_coop_wetsand.shader` (5 free): `clampmapy` a private
  `coop_fx/swashblood.tga` with slicks x a ragged reach baked into alpha (the sand's T runs 1.0 at
  the sea edge to 0 at the land edge, `zz_coop_wetsand.shader:12-14`), `tcMod scale 1 1` (256 u,
  seamless), `tcMod wavetrant sin 0.45 0.75 0 0.08` so it drains with the wet line (`:112`), and the
  bug-2493 column offset so its rag is the wet line's rag. Lightall honours texture alpha
  (`:56-57`); do NOT use `alphaGen tCoord` there (bug-2486). `gen_bloodwash.py` already makes a
  seamless integer-frequency field (bug-2230); it needs an alpha-reach term, and the sand generator
  needs to be checked in first (section 0 item 9).
- Measured caveat: from the boat the strip is wet dark sand plus foam pulses rather than a film of
  water - which is what a swash zone looks like at eye height, and what bug-2485 was tuned to
  ("sand drying under a visible sheet" was the defect it fixed).

**If the user wants water visibly over the strip instead:** keep the blood on the sheet as
`clampmapy` + `tcMod scale 62 1` + `tcMod scroll 0.002 0` (no T scroll or the edge drifts), alpha 0
on its top rows, edge rag baked with the sand's offset shifted 0.25 S (section 0 item 1) and moved by
a wavetrant in phase with the flap. That rags and moves the blood only; the additive stages still cut
straight, so it is strictly weaker than the hand-off.

**Reclaim the two dead retail stages (item 2)** - they draw nothing today (alpha 0, LANE-A
section 4) and cost fill. Replace them, in place, with: (a) a base water tint - the same stage with
`alphaGen tCoord 1.8 -0.01 0 1` so the ocean colour actually fades in from the seam, giving the
waterline a body it has never had; (b) a break-line foam stage: `clampmapy` a copy of
`wetsand_foam.tga`'s band placed at T 0.55-0.72 of the sheet, `blendFunc GL_SRC_ALPHA GL_ONE`,
`tcMod scale 62 1`, `tcMod wavetrant sin 0 0.06 0 0.08`, `rgbGen wave sin 0.3 0.25 0 0.08` - a foam
line that pulses where the crests die, phase-locked to the flap and to the sand's foam for free. Two
private textures, no new stage count, still 8/8.

**A second thin surface for the break - rejected.** A script_model plane over the sheet must sit
inside the flap's +/-16 u travel; the sheet is `blendFunc blend` with no depthwrite so the two would
interleave per pixel by sort order, and `sort nearest`/entity sorting cannot follow a per-vertex
deform. Every effect proposed above fits in stages that inherit the deform, which is why the blood
was made a stage in the first place (`zz_coop_shoreline.shader:120-125`).

**Spray at the obstacles** is built (`coopified.scr:7462-7568`, five transient `fx_water_spray`
carriers near a player, not phase-locked, `coop_obstWashOn`). The visible upgrade is a **foam
collar**: park `waterRing.tik`'s `originemitter` (flat rings, `life 10`, `spawnrate 2`) on the 34
lane obstacles from the generated table rather than all 61 - 34 permanent carriers is the cost, and
the rings read as water piling against the steel between surges. Phase is the same unknown as the
wash; the cgame clock publish in section 2 fixes both at once.

## 4. Lighting and post

- **Sun glint**: not on this map (section 0 item 4). The one-line engine fix that makes
  `alphaGen lightingSpecular` honest everywhere else is to replace the literal in
  `generic_vp.glsl:218` with the bridged sun (`tr.sunDirection`, `E/renderergl2/tr_local.h:2341`,
  filled from worldspawn at `tr_bsp.c:3688-3700`) via a uniform; renderer dll, no data change. Rank
  low for Omaha, worth doing for e-series water where the sun is oblique.
- **Sky sheen (the Omaha answer)**: a `tcGen environment` stage on the deep sheet and on the reclaimed
  tint stage, mapping an authored sphere map baked from `env/dday2` (private texture), `blendFunc
  GL_SRC_ALPHA GL_ONE`, `alphaGen const 0.25`. Works today on the generic path (`generic_vp.glsl:
  149-155`); per-vertex, so on 48/64 verts it is a smooth grazing-angle gradient, which at eye height
  is the correct look. Without Fresnel it is a flat sheen at nadir too - hence:
- **Fresnel**: port `alphaGen dot` / `oneMinusDot` into `generic_vp.glsl`'s `CalcColor` beside the
  sCoord branch (`:229-238`), where `normal` and `viewer` are already in scope (`:213`) and
  `u_AlphaGenParams` already carries min/max. ~15 lines GLSL plus the two enum cases in
  `tr_shade.c:707-800`; write ALPHA (gl1 writes RGB - decide parity or fix gl1 too). Every water
  shader is deformed, so every water shader reaches it. It also fixes the nine foliage stages listed
  at `tr_shade.c:795-800`. Best engine change on the list, unchanged from the prior lane.
- **gl2 post**: nothing above the surface is water-aware; the shipped set is bloom/SSAO/sharpen/FXAA
  (`tr_postprocess.c` cvar list). The one interaction to design around is bloom on additive foam.
  Underwater (`r_ppUnderwater*`, `:1464-1471`) is done and out of scope.
- **What gl1 loses**: nothing from any shader-only item (flap, 4-param tCoord, wavetrant, clampmapy,
  tcGen environment all exist on gl1); it has its own `alphaGen dot` (RGB); it never had lightall
  specular. gl1 still has no 9th-stage bound check (LANE-A section 3) - the reclaim-in-place design
  keeps every shader at or under 8.

## 5. Ranked

Ship codes: **pk3** = shader/texture/script only; **cgame**/**exe** = binaries (exe ships with cgame+game).

| # | Item | Cost | gl1/gl2 | Risk | From the boat / from the sand | Measure |
|---|---|---|---|---|---|---|
| 1 | Sheet hand-off fade (6 stages, tCoord 4-param) + swash blood on the sand shader | pk3: ~12 tokens + 1 texture + 1 stage on wetsand | identical | low; blood look changes at the strip, A/B with the user | boat: crests visibly break and die at one line; sand: no straight line at any phase, blood recedes with the wet line | shot from (0,-900,-450) looking +/-X along the beach at flood and trough; `coop_noCrest 1` to isolate; `developer 1` for alphaGen warnings |
| 2 | Reclaim the two dead stages: water tint + break-line foam | pk3: 2 stages rewritten in place, 1 texture | identical | low; stays 8/8 | boat: the waterline gains body and a white line where waves fall over; sand: foam line pulses with the swash | same shots; `r_showtris` unaffected; verify stage count by parse (no checkerboard) |
| 3 | Bow wake mesh + stern trail on `$higgins1` | pk3: coop_wake.tik + shader + waterWake carrier, script bind | identical | med: retail tik's vehicle keys (mint a copy); trail sprites on a 180 u/s hull | boat: looking astern the sea is disturbed by the hull; sand: n/a | `cg_showemitters 1` for the trail; screenshot astern at y -5500 |
| 4 | Bob synced to the sheet | pk3 (10 s legs) or +1 line cgame (clock publish, exact) | identical | low | boat: hull and sea rise together; the last of the "underwater boats" | side view at y -6000 across two cycles |
| 5 | Open-sea foam streaks + sky sheen on `deepbluesea` | pk3: 2-3 stages of 6 free, 1 sphere-map texture | identical (sheen weaker on gl1's 2 bundles) | low-med; bloom smear if too bright | boat: sea has texture at range and catches the sky at grazing angles | ride shots at farplane 5000; toggle `r_ppBloom` |
| 6 | Port `alphaGen dot`/`oneMinusDot` to gl2 | engine ~15 lines GLSL + 2 cases, renderer dll | gl2 gains; gl1 already (RGB) | low; parity choice | boat: sheen goes to zero looking down, to full at the horizon; froth collars (retail sf_ddayocean recipe) become authorable | A/B the same shader on `cl_renderer opengl1` vs `opengl2` |
| 7 | `lightingSpecular` from the real sun | engine 1 uniform, renderer dll | gl2 only | low | nothing on Omaha (vertical sun); glint on oblique-sun water maps | e-series water shot |
| 8 | Dense sea mesh + travelling wave (engine re-densify of the flat patch, or a spawned TIKI plane) | exe (patch route) or pk3 + TIKI pipeline | gl2 first | high; the seam at y -2160 must taper to zero | boat: real swell; the only item that changes the wide shot | `r_showtris 1` at the water's edge and far out |

**What is blocked by the 8-stage cap:** nothing above - 1 uses no stage, 2 reclaims dead ones, 3-5 use
free budgets. **What the lightall alphaGen gap (bug-2486) blocks:** any `alphaGen sCoord/tCoord` on
the deform-free sand shader (item 1's swash blood, item 2's sibling foam if ever moved there) - bake
the reach into alpha until it is fixed. **The one-line fix**: in `CollapseStagesToGLSL`'s diffuse loop
(`E/renderergl2/tr_shader.c:3216+`) skip stages whose alphaGen is `AGEN_SCOORD`/`AGEN_TCOORD` so they
stay on the generic program, as gl1 draws them. It would let the sand-shader stages drop their alpha
bakes and would revive retail `afrika_shoreline`'s ramps on gl2 - which is exactly the look the user
rejected for `northafrika_shoreline` (`M/scripts/coop_water_overrides.shader:4-14`), so it needs its
own A/B and is not a free win.

## 6. Prior work - do not redo

From `.wolf/buglog.json` (tags water/shader/ocean/shoreline/wet-sand/gl2/higgins): **1242** wavetrant
ported to gl2; **1249** alphaGen sCoord/tCoord ported (generic only, `r_hzmAlphaGenCoord`); **2226**
two-param tCoord = undefined clamp on gl2 (open; always write four); **2227** clampmapy clamped S too
(fixed); **2228** gl2 shader precedence was inverted - every override was dead until 08-31 (fixed;
precedence is pak order, bug-2485/TRAPS T6); **2230** blood ramped along T to hide the seam; **2249**
blood retint; **2320/2355** underwater post pass (done, depth-aware); **2445** gl1 DDS crash on m3l1a
(never ship a same-name `.dds` beside these textures); **2477** script_model carriers render only
`originemitter` blocks; **2478** ocean flap max 10 -> 1, coop hulls to -563.7; **2479** obstacle wash;
**2485** wet-sand swash + foam (baked alpha, not alphaGen); **2486** lightall alphaGen gap (open);
**2493** ragged wet line, 256 u period (the sheet's edge explicitly deferred - item 1 here);
**2487/2496** the Higgins sink (mover blocking, unrelated to water look). Already rejected: a shader
foam collar on the obstacle shaders (2479 - wets all 143 plus other maps), floating blood planes
(cannot follow the deform), a 9th stage (both renderers), `r_subdivisions`/`tesssize`/`cmpatch` for
mesh density (LANE-A / renderer_capabilities 5.1-5.2), SSR (no G-buffer), portal mirrors (no
`RT_PORTALSURFACE` producer, patches have no plane).

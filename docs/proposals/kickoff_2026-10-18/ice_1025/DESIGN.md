# Ice and cold-water remaster - DESIGN (proposal, nothing built)

PART A (frozenriver ice, APPROVED 2026-10-25) is sections 1-7. PART B (MAIN target after the user clarification: the cold
harbour water of the Norway U-boat pens and the fjord of the m2l2b U-boat cutscene) is section 8, awaiting approval.

2026-10-25. Status: PROPOSAL, awaiting approval. No engine, mod, deploy or install was touched.

## 1. What "ice water" is in this stack (inventory, from the BSPs of the shipped paks)

One shader draws every ice surface that is not a decal: `textures/central_europe_winter/frozenriver`
(`scripts/central_europe_winter.shader`, maintt/pak1). It is NOT water to the engine: `surfaceparm snow`,
solid, two stages (`frozenriver` texture, then `$lightmap` multiply), no gloss, no reflection, no normal map.
The texture is the HD Project 1024^2 JPG (retail was 34 KB): a blurred blue-white mottle - it reads as dirty snow.

| map | display name | ice | notes |
|---|---|---|---|
| m6l2a | The Communications Blackout | one flat plane z -288, 1.9k x 0.9k u (1.70M u^2) | frozen village canal at night, lit windows |
| m6l2b | The Schmerzen Express | one flat plane z -88, 2.6k x 5.2k u (6.1M u^2) | frozen river canyon, snow banks, bridge, dark |
| mp_verschneit_dm | (MP) | same geometry as m6l2a | |
| mohdm5 | (MP) | same geometry as m6l2b | |

Every ice surface is one horizontal quad set (|n.z| = 1), all four maps; nothing else uses the shader.
Searched: every BSP in main/mainta/maintt for ice/frozen/frost/glacier/slush names, plus every snow-themed map for
water-flagged or turb/scroll shaders. Not ice, not in scope: `icecicles` (alpha decal on m6l3a/e, t2l1, t2l2,
mp_castello_obj; optional extra), `t2fogplane` (a fog plane carrying `surfaceparm water` on the Bastogne maps).
The Norway maps m2l1/m2l3 and Spearhead Bastogne t2l3/t2l4 have no ice or water surface at all; they are snow ground.
`frozenriver` is not in the Omaha family and is not on the `HZM_WATER` allowlist today (decision "ice on snow maps"
in water_wetness research.md 1.1) - so the earlier water remaster never touched it. This builds on that pass, it does
not redo it.

Renderer paths: gl2 (default) draws it with the generic lightall program, stage 0 texture x stage 1 lightmap. gl1 draws
the same two stages fixed-function-style. Both look identical today.

## 2. Looks today (in-game BEFORE stills, `before/`, and the offline pairs in `offline/`)

Flat, matte, texture-stretched (one 1024 px tile per ~256 u, smeared at grazing angle), no highlight at any angle,
no depth, no cracks, edges against snow banks are a hard line. Reads as a snowfield painted blue.

## 3. Proposed look

An **ice material** for `frozenriver` only, as a new mode of the existing gl2 water pass (`tr_hzm_water.c`,
`hzmwater_fp.glsl`: same extra premultiplied pass, same sky probe `tr.hzmSkyCube`, same ripple/normal plumbing, same
Omaha exclusion, same `r_hzmWater` master and 1.5 s fade). Ingredients (all in the offline prototype
`tools/ice_look.py`, numbers there are the GLSL starting values):

1. **Thin-ice colour model.** Clear ice is dark cold blue (deep water showing through); bubbles/cracks scatter white.
   Albedo = lerp(deep blue, white, f(luminance of the crack texture)). Lightmap kept: diffuse = albedo x BSP lightmap,
   so lamplight from the village windows and shadows still fall on it correctly.
2. **Cracked-ice texture, two layers.** CC0 ambientCG Ice001 + Ice004 (2K, colour + GL normal + roughness), sampled at
   two non-commensurate scales (640 u / 1090 u, second rotated 35 deg) and blended by a low-frequency mask: no visible
   repetition on the 6M u^2 river. Mipped, so no shimmer in the distance.
3. **Gloss.** Schlick fresnel (F0 0.04) reflecting the map's sky probe (fogged like the real sky), GGX sun/moon glint
   with roughness from the roughness map, normal-mapped by the crack normals, Toksvig-style fade with distance (the same
   anti-sparkle rule the water pass already passed: no added sparkle, far field stable).
4. **Frost and snow drift.** The ORIGINAL frozenriver texture is kept as a matte frosted layer: low-frequency patches
   plus a drift band (about 170 u) along the snow banks, from a distance-to-bank map built at load from the same
   top-down occlusion grid the wetness pass already makes. Gloss is zero under frost.
5. **gl1 fallback** (no GLSL): a new shader script override `zz_coop_ice.shader` in our own pak: the cracked-ice colour
   (blue-graded copy, baked from the same textures) as stage 0, a second crack layer at another scale and rotation
   (`tcMod`) multiplied in, `$lightmap`, and a `sky` env-map stage (`tcGen environment`, additive, low) for a cheap
   sheen. No fresnel/normal map, but it kills the smear and the flat blue.
   gl2 uses the same script with the water-pass tag, so the pak is shared.

Optional, priced separately (not in the base): planar reflection of the village (windows and walls in the ice). The
renderer can do a second camera pass (renderer_capabilities.md 2.2) but it is a whole extra scene pass for two maps;
recommend skipping, the sky probe + glint carries the look, as the offline stills show.

## 4. Prototype evidence

`offline/*_AB.jpg`: BEFORE vs AFTER from the offline renderer (the same engine-faithful look-dev tool as the water
remaster; BEFORE is the retail stages, AFTER is the proposed kernel), same camera:
`a0`/`a9` village canal (m6l2a), `b13`/`b4` river canyon (m6l2b). QA'd by eye: no clipping, no stretched or garbled
text/patterns, cracks continuous across the quad seam, no tiling pattern visible, banks do not glow. Known limits of
the mock: no reflection of buildings, no animated glint (the gl2 build adds the glint; offline it is a still), no snow
particles. `before/`: in-game gl2 stills (see section 6).

## 5. Maps covered / cost

Maps: m6l2a, m6l2b, mp_verschneit_dm, mohdm5 (all 4, one shader). Bonus (not asked): the `icecicles` decal could get a
refractive/bright edge, tiny.

Cost estimate (engine ~300 lines C + ~120 lines GLSL, mod: 1 shader file + 4 textures):
- GPU: one extra pass over 1.7-6.1M u^2, always the same few hundred thousand pixels at most; ~3 texture fetches x2
  layers + 1 cube fetch, below the existing water pass cost. Measured on build.
- Memory: ice colour/normal+rough packed, 2 tiles at 1024^2 DXT = about 2.7 MB with mips (shipped 1K, not 2K).
- Load: nothing new except the distance-to-bank map (a 2D distance transform on the existing occlusion grid, ms).
- Risk: low; scope is one shader name on four maps, switchable (`r_hzmWater 0` = today's look, bit-identical gate
  as the water pass). Worktrees: mod off coop-wip, engine off release-1.10.36, under H:\hzm_work\ice1025_*.
- Effort: 1 build session + 1 in-game verification session (stills + short motion clip for sparkle/shimmer).

## 6. Textures and credits

Source: ambientCG Ice001, Ice004 (Ice002/003 evaluated, rejected: green / near-black), CC0 1.0, "Ice 001/004",
https://ambientcg.com/a/Ice001 , /Ice004 . Downloaded 2K-JPG zips into `H:\hzm_work\ice1025_textures\` (own folder,
treated as data). Procedural PBR sets (ambientCG "PBRProcedural"). CC0 needs no attribution; it will be recorded in
`docs/SKIN_CREDITS.md`-style credits (`CREDITS_ICE.md` here) and in the release credits.
New art goes only under our own paths: `textures/hzm/ice_*.tga` (the T6 private path) and `scripts/zz_coop_ice.shader`;
nothing existing is overridden except the shader name `frozenriver` for the gl1 route (a new shader-file entry that
wins by file order - to be checked by `asset_collision_audit` before merge). Omaha textures and skybox untouched.

## 7. Decisions needed from you

1. Approve the ice material approach (gl2 pass mode + shader script).
2. Planar reflection of buildings: skip (recommended) or price it.
3. Base look: this dark deep-blue clear ice with cracks (as the stills), or lighter/whiter "snowy ice"? One parameter.

## 8. PART B - cold harbour water (U-boat pens m2l2a / m2l2b / m2l2c, co_lobby7, the m2l2b U-boat cutscene)

### 8.1 Inventory
Every water surface in these maps is the same pair, one huge flat plane per map (bbox x -8064..8064, y -6224..5824):
`textures/misc_outside/subpen_water4` (z -720, opaque, stage 0 `ocean1b` x `$lightmap`) with
`textures/misc_outside/canal_sludge` (z -712, additive: scrolling `ocean2_green` + `oceanbrite`, `deformVertexes wave`,
lightmap multiply) laid 8 u above it. Area 107-117M u^2 per map. Both are already on the `HZM_WATER` allowlist (slots 10 and 9),
so the shipped r_hzmWater pass draws a sky-reflection layer over them today. The same shaders are also used by m3l2, t1l2, e2l2,
e3l3 and MP maps; the new mode is gated per shader and map so those do not change unless asked.
The U-boat cutscene is `maps/m2l2b.scr` (`coop_sub_finale*`, `coop_mod/subsink.scr`, `cutscene.scr` cameras): cam1 (-991 -2367 -225)
looks out of the pen mouth along the channel (the boat, a blizzard, open fjord water out to y 5700); the finale cam
(-1420 -6421 -135) frames the neighbouring pen for the sinking. The cutscene uses the same two shaders - there is no separate water.
Renderer paths: gl2 (default): retail stages + the r_hzmWater premultiplied layer. gl1: retail stages only.

### 8.2 What it looks like today (offline renders of the shipped state, `offline/water_*_AB.jpg`, top half)
A milky white-grey sheet, the brightest thing in the frame: no depth, no swell, a speckle tile scrolling (the retail `ocean1b` and
`oceanbrite` stages sum to near white under the pen fog), black speckle bands at the quay edges. The existing pass adds only a faint
sky layer on top of the white. In motion it reads as scrolling noise.
In-game BEFORE stills: queued (`tools/chain_before.sh`, log `tools/chain_before.log`, output G:\mohaa-hudfeed5\runs_ice1025);
the harness could not start while other sessions held heavy.lock (see the report for status).

### 8.3 Proposed: a COLD HARBOUR mode of the same pass (extend, not parallel)
Selected per allowlist slot (subpen_water4 + canal_sludge on the Norway maps, a mode flag beside the allowlist index), so
`r_hzmWater 0` still returns today's look. Prototype: `tools/water_look.py`.
1. **Body colour replaces the milk.** The layer covers the retail stages: dark green-grey-black (deep 0.012 0.034 0.036 to shallow
   0.045 0.100 0.095 by view angle), a little sky scatter, and the BSP lightmap still brightens lamp pools. Retail stages stay
   underneath for gl1 and load parity.
2. **Slow heavy swell, not a tile.** Three world-space sine swells (900 / 520 / 310 u, slopes 0.030 / 0.022 / 0.016, different headings,
   slow phase) give the long undulation; chop is world-space noise at two scales, faded with range (the existing anti-sparkle rule) and
   flattened into oily slicks by a 700 u mask. World space, so no seams.
3. **Real reflections.** Schlick fresnel F0 0.02 (cap 0.8) of the sky probe, GGX moon/sun glint, plus PLANAR reflection of the pen (walls,
   lamps, the opening) - most of what makes the stills read as water. Planar = one extra low-res scene pass from the mirrored camera, only
   on these maps and only when the water is on screen (renderer_capabilities 2.2: a second-camera render exists); cvar-gated with the
   sky-only version as fallback. Reflection is distorted by the swell/chop slope and blurred with range.
4. **Ice crust, slush and floes at the quay walls.** Thin cracked ice (ambientCG Ice001, the CC0 set of part A) as plates whose density
   rises toward the walls (distance map built at load from near-vertical faces that reach the waterline; a top-down height map cannot be
   used, the pens are roofed), drifting a few units with the swell; open fjord water gets sparse floes only. Plates are matte and flat
   with a dark water seam. Pure shading in the same pass: no geometry, no collision.
5. **Wet dark edges (optional, small).** Darken quay-wall fragments within about 50 u above the waterline (the water z is a uniform).
6. **Wake and foam for the U-boat (feasible, priced separately).** Cheapest robust version: script-side. The cutscene already steps the
   hull origin every tick, so `subsink.scr` can publish hull x, y, heading, speed in cvars that the shader reads to add a V-wake and bow
   foam on the water plane. About 100 lines GLSL + a few script lines. Not in the base estimate and not in the stills.
7. **gl1 fallback:** `zz_coop_coldwater.shader` overriding the two shaders in our own pak: dark teal stage 0 (the body colours), a slow
   two-layer `tcMod` scroll/rotate chop detail, `$lightmap`, a sky `tcGen environment` sheen. No planar reflection, no swell, floes only
   as a crust strip painted at the walls.

### 8.4 Prototype evidence
`offline/water_pbcut1_AB.jpg` (cutscene cam1: pen mouth onto the fjord), `water_pa9_AB.jpg` (m2l2a pen canal), `water_pbfin_AB.jpg`
(m2l2b pen canal / finale pen). BEFORE = shipped state, AFTER = prototype, same camera, same fog and grade. QA by eye: no clipping, no
garbled patterns, planar reflection of the pen roof and opening is correct, floes thin out into open water, far water fades into the
fog without sparkle. Known weaknesses of the mock (to tune in the build): the pen canals mirror a black roof so near water goes very
dark in pa9 (a body-brightness floor / sky-lift parameter is planned); floes are sparse in pa9; the mock is a still, so swell motion,
slick drift and glint stability need the in-engine motion check (as the earlier water pass had). The boat and the blizzard are not
in the stills.

### 8.5 Cost
Engine about 450 lines C (mode flag, wall-distance map at load, planar render target + pass, cvars) + about 200 lines GLSL. Mod: the gl1
shader file, one tileable chop texture, the ice pair from part A, optional wake script. GPU: the pass exists; added 3 sines, 2 noise
scales, a half-resolution planar pass on three maps (measured at build, cvar-switchable). Memory: planar target 640x360 RGBA16F ~2 MB.
Risk: medium for the planar pass (render-target lifecycle across vid_restart; the earlier water plan documented the pitfalls), low for
the rest. Omaha untouched (same HZM_WaterWetOmahaMap exclusion; none of the Norway maps is in it). Other maps sharing the shaders do
not change unless opted in. Effort: one engine build session + one verification session (stills, motion, 30 s cutscene capture),
after approval.

### 8.6 Decisions for the user
1. Approve cold harbour water (a mode of the existing pass) for m2l2a/b/c, co_lobby7 and the cutscene.
2. Planar reflections of the pen: yes (recommended) or sky-only.
3. U-boat wake and foam: include now or later.
4. Same look on the other maps that share these two shaders (m3l2, t1l2, e2l2, e3l3, MP): not unless you say so.
5. How icy: floes only at the walls (as shown) or a heavier slush skin over the whole pen water.

## Status (2026-10-26)

On by default (gl2, `r_hzmWater` -1 = auto): COLD (pens, cutscene sea), ICE (frozenriver on m6l2a/b, mohdm5), CHANNEL (Omaha sea and shoreline sheets, water only), HARBOUR (Bizerte), POND (m4l0). RIVER is OFF (`HZM_RIVER_PRESET_ON 0`): the v6 still is flat; later task needs flow direction, ripples and bank reflections.

Cvars: `r_hzmWaterPreset` 1, `r_hzmWaterPlanar` 0 (opt-in), `r_hzmWaterPlanarDbg` 0, `r_hzmWaterBody` 2.0, `r_hzmWaterFloe` 1.0, `r_hzmWaterIce` 0.7, `r_hzmWaterContact` 1.

GPU: pens about +0.1 ms (noise level); Omaha about 0 (3.68 to 3.66 ms); planar about +0.4 to 0.6 ms (off by default). Contact foam not measured separately.

gl1 fallback: `scripts/zz_coop_coldwater.shader` (pens water good). The gl1 frozenriver override is patchy and too blue (second cracked-ice layer blends DST*SRC*2); soften later. Known limit: hull rim also faintly rims quay walls (depth cannot tell them apart).

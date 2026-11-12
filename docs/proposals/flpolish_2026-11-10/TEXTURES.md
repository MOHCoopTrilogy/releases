# SEALED ORDERS (coop_fl_1_1) - texture decision list

Status: **tier 1 approved by the user 2026-11-11 ("I want that done") and implemented** in the converter
(`docs/tools/frontline/flhd.py`, config `fl_levels.json` "1_1" -> "hd", CC0 files in `docs/tools/frontline/hd/`).
Tiers 2 and 3 are untouched and wait for the user's verdict on the before/after stills, which do not exist yet (no
visible client may run while the user is playing). No image from the disc is in this file, in git or in any release.
The user's remark this answers: "I feel like frontline textures look super old."

## How it was measured

`H:\hzm_work\flpolish\fix2\texinv.py` over conversion v58 (inventory: `texinv58.json`, local): every surface of the
BSP with its shader, world area, texel density (world units per texel, `upt`), and the closest a standing player on
the walkable floor can get (`d_min`, median `d_med`, in units). `px` = screen pixels one texel covers at the median
approach on a 1920 wide, fov 90 view: above ~2 the texel is visibly a block. `impact` = area near the route x `px`.
The rank is by impact.

- 434 textures. Sizes: 128x128 (124), 64x64 (121), 128x64 (105), 64x32 (27); the two largest are 256x128.
- 43 are cut-outs (branches, hedges, window walls). Median density 0.78 units per texel, but the big surfaces are
  far coarser: the 30 below carry 81 % of the impact, the top 6 carry 48 %.
- For scale: stock MOHAA wall textures sit at about 0.25-0.5 units per texel, the mod's HD set at 0.12-0.25.

## Ranked list (top 30) and treatment

Treatments: **a** leave - **b** existing MOHAA/mod shader - **c** local upscale at convert time (player's own disc
image, nothing shipped) - **d** detail texture as a second stage - **e** CC0 replacement (see Credits).

| # | id | what | size | upt | closest / median | px | share (cum.) | treatment |
|---|---|---|---|---|---|---|---|---|
| 1 | 54200 | cobbles, the streets | 256x128 | 8.1 | 42 / 939 | 8.1 | 14 % | **e** cobblestone_05, one tile per 176u, tinted to the original mean (85 84 75) |
| 2 | 124280 | bare tree, cut-out | 256x128 | 1.7 | 10 / 530 | 3.0 | 22 % | **c** 4x, edge-bleed (see defects) |
| 3 | b3600 | cobbles, yards | 128x128 | 2.1 | 44 / 234 | 10.3 | 29 % | **e** cobblestone_05 (same as 1 so streets and yards join) |
| 4 | 1dd980 | bare tree, cut-out | 128x128 | 2.0 | 77 / 479 | 3.6 | 36 % | **c** |
| 5 | 6180 | whitewashed wall with stained base | 128x128 | 2.1 | 5 / 270 | 6.8 | 42 % | **c + d** (the stain band is positional: keep the image) |
| 6 | d980 | water | 128x128 | 26.4 | 182 / 2520 | 9.6 | 48 % | **b** done: `textures/misc_outside/pond` (approved) |
| 7 | 12c380 | bush, cut-out | 128x128 | 2.9 | 108 / 572 | 4.5 | 50 % | **c** |
| 8 | 78380 | ruined house front (windows), cut-out | 128x128 | 3.2 | 87 / 500 | 6.1 | 53 % | **c** only: unique image |
| 9 | 16a380 | canal bank, dark moss band | 128x64 | 1.6 | 26 / 73 | 18.8 | 55 % | **c + d** (band is positional) |
| 10 | 4f880 | roof slates | 64x64 | 2.2 | 26 / 396 | 4.9 | 57 % | **e** roof_slates_03, 192u |
| 11 | 21b80 | plain plaster | 128x128 | 1.1 | 4 / 189 | 5.4 | 59 % | **c + d**; **e** worn_plaster_wall is the tier-3 option |
| 12 | 14f200 | fir tree line (backdrop), cut-out | 128x128 | 6.1 | 250 / 1538 | 3.9 | 61 % | **c** |
| 13 | 5ed80 | vertical planks | 128x128 | 1.6 | 7 / 101 | 14.7 | 62 % | **e** old_planks_02, 128u |
| 14 | c0_16dc00 | branches, cut-out | 128x128 | 1.3 | 23 / 72 | 18.1 | 64 % | **c** |
| 15-16 | 15b680, 15f800 | leafy branches, cut-out | 128x128 | 2.3 | 100 / 590 | 3.4 | 67 % | **c** |
| 17 | c6_150000 | branches, cut-out | 128x128 | 1.3 | 12 / 51 | 25.2 | 68 % | **c** |
| 18 | f2b80 | house front with shutters, cut-out | 128x128 | 2.6 | 54 / 941 | 2.6 | 70 % | **c** only: unique image |
| 19-20 | 157500, 153380 | overhanging branches, cut-out | 128x128 | 2.1 | 19 / 380 | 5.0 | 72 % | **c** |
| 21 | 1eeb00 | round shadow blob | 32x32 | 8.1 | 52 / 64 | 96.6 | 73 % | defect, see below |
| 22 | 1ea100 | rubble decal | 128x128 | 1.5 | 58 / 61 | 22.6 | 75 % | **c** |
| 23 | 50f00 | timber beam | 32x128 | 2.0 | 4 / 207 | 7.5 | 76 % | **c + d** |
| 24 | 1e1a80 | bush from above, cut-out | 128x128 | 2.0 | 91 / 500 | 3.7 | 77 % | **c** |
| 25 | a680 | mud / earth | 64x64 | 2.0 | 3 / 198 | 11.4 | 77 % | **e** brown_mud_dry, 256u (with c6_124400, c0_132880) |
| 26 | 41180 | plank wall, weathered | 128x128 | 1.3 | 2 / 52 | 21.4 | 78 % | **c + d** |
| 27 | d080 | corrugated / plank strip | 64x32 | 2.8 | 28 / 386 | 7.0 | 79 % | **c + d** |
| 28 | 165e80 | dark stone blocks | 128x128 | 0.7 | 7 / 49 | 12.6 | 80 % | **c + d** |
| 29 | 3eb80 | rubble stone wall | 128x64 | 1.4 | 60 / 236 | 5.8 | 80 % | **c + d** |
| 30 | ccf80 | mossy plaster | 128x128 | 1.4 | 4 / 279 | 6.9 | 81 % | **c + d** |

Also in tier 1, further down the rank: 4aa80 (stone wall) -> rock_wall_08, 192u; 38280 (grey planks) ->
weathered_planks, 128u.

Rule kept throughout: a lettered sign, a poster, a house front, anything with a feature at a fixed place on the
wall keeps the disc's own image (treatment c at most). Only homogeneous, tiling materials are candidates for b or e.

## Tier 1 as built (flfix2, 2026-11-11)

The user's bar: "they arent jarring, fit the scene and are high quality". Each replacement was judged on a sheet at
equal world scale, the disc's texture above and the tinted CC0 one below (`H:/hzm_work/flpolish/fix2/hd_swap_sheet.jpg`,
candidates in `hd_cand_sheet.jpg`, cut-outs in `hd_cut_sheet.jpg`; local only). The replacement is tinted to the mean
colour of the disc's own texture at conversion time, so hue and value stay the level's; `tile` is the world size of
one repeat and `repeat` re-tiles the surfaces' UVs in the BSP so the new tile is drawn at its real scale.

| id | what | CC0 asset (Poly Haven, CC0 1.0) | world units per tile | verdict |
|---|---|---|---:|---|
| 54200 | street cobbles (largest ground area) | `cobblestone_05` https://polyhaven.com/a/cobblestone_05 | 173 (old repeat / 12 x 6) | pass |
| b3600 | cobbles, second sheet | `cobblestone_05` | 135 (/ 2 x 2) | pass |
| a680 | bare earth | `brown_mud_dry` https://polyhaven.com/a/brown_mud_dry | 128 | pass |
| c6_124400 | dark earth | `brown_mud_dry` | 121 | pass |
| c0_132880 | dark earth | `brown_mud_dry` | 180 | pass |
| 4f880 | roof slates | `grey_roof_tiles_02` https://polyhaven.com/a/grey_roof_tiles_02 | 143 | pass; courses a little smaller than the original's |
| 5ed80 | plank walls | `old_planks_02` https://polyhaven.com/a/old_planks_02 | 205 | pass at repeat 1 (planks about 20u, original about 25u) |
| 4aa80 | rough stone wall | `old_stone_wall` https://polyhaven.com/a/old_stone_wall | 124 | weakest: hue and moss match, but it is rubble where the original is coursed block. First one to revert if it reads wrong in the stills |
| 38280 | board / shingle rows | none | - | **not done**: no CC0 candidate has the original's rows of short boards; the disc texture stays |

Rejected after the sheet: `roof_slates_03` (slates far too fine, a seam band every 143u), `rock_wall_08` (brown rubble,
loses the mossy wall), `old_planks_02` at repeat 2 (6u planks), `weathered_planks` for 38280 (thin vertical lines).

Cut-outs (11 tree and bush cards, listed in "hd" -> "cutout"): 4x Lanczos of the disc's own image on the player's
machine, leaf colour bled into the clear texels first, alpha resampled with the colour. On the sheet the cut edge is
round instead of stair-stepped, with no halo and no key-colour fringe. The gain is modest; no learned upscaler is
used, so nothing is invented.

Evidence: conversion v61 logs `flhd: 8 swapped, 11 cut-outs upscaled, 0 skipped, 3198 verts re-tiled`; headless boot
of v61 loads with no script or shader error. Pak size 30.6 MB -> 50.7 MB (eight 1k TGAs and the 4x cards).

Not verified: **nothing of this has been seen in a game client.** The sheets are flat tiles; lighting, mip-mapping,
the re-tiled UVs on real surfaces and the seams against untouched neighbours can only be judged in the stills.
Failure behaviour: a missing `hd/` file or any error keeps the disc's texture; a re-tile failure drops all swaps.
Release packaging: `hzmconv.spec` now bundles `flhd` and `hd/` (2.9 MB).

## Tiers and what each would honestly buy

| tier | what | textures | visible gain | cost |
|---|---|---|---|---|
| 0 | water (done) | 1 | the canal stops being a cyan film; reads as water | none (stock shader by name) |
| 1 | CC0 replacement of the homogeneous ground / roof / plank / rough stone materials, UVs re-tiled | 9 (2 cobble, 3 earth, 1 slate, 1 stone, 2 plank) | large: the streets are 29 % of everything a player sees close up and go from 8 units per texel to 0.17; this is the change that makes the level stop looking like 2002. Risk: a different stone pattern than the original's; hue and brightness are matched, pattern is not | +9 MB pak (1024 JPG), about 5 s convert time; needs the files on the player's machine (see Delivery) |
| 2 | 4x local upscale (Lanczos + unsharp) of the next ~70 textures, plus a fine detail stage on the opaque ones | ~70 | moderate: edges and cut-outs get clean, walls stop shimmering at distance, but no new information is created - a 128 wall is still a soft wall, just not blocky. Honest estimate: a third of tier 1's effect | pak 30.6 -> 73.5 MB with tiers 1 + 2 (measured on the throwaway build), +40 s convert time |
| 3 | CC0 plaster / stone on the plain walls (21b80, ccf80, 3eb80, 165e80) | 4-8 | moderate, and the riskiest for "does it still look like Frontline": walls carry the level's character. Recommend only after tier 1 is seen in game | as tier 1 |

Not proposed: AI upscalers (hallucinated detail on lettering and faces, tens of minutes per level on a player's
machine), normal/specular maps (the level's vertex lighting has no per-pixel light to drive them).

Recommendation: tier 1 now, tier 2 for cut-outs only (the tree and branch edges are where 128 px hurts most after
the ground), look, then decide on the rest.

## Delivery (why tier 1 is not free)

Nothing disc-derived may ship; CC0 images may. So tier 1 would ship 7 CC0 JPGs (about 9 MB at 1024) in the mod pak
under `textures/fl_hd/`, and the converter would point the listed materials at them and re-tile the UVs. A player
without the mod update gets the disc's own texture exactly as today. Tier 2 runs wholly on the player's machine.

## Defects found on the way (separate from "old")

| id | defect | proposed fix |
|---|---|---|
| 67180 | degenerate UVs: one texel smeared over whole faces (stretch 5058) | clamp/regenerate UVs when a face's UV area is ~0 |
| 6180, 21b80, ccf80, 68280 | UV stretch 13-29 on some faces (long walls mapped once) | none proposed; it is the original's mapping |
| 1eeb00, 1ee600 | the original's baked shadow blobs (56 and 18 triangles; round ones under trees around -6035 3446, square ones around -1955 4395 near the MG nest). They are blended and look right under a tree (seen on camera), but a square one with nothing standing on it reads as a black patch on the cobbles - the likely "black patch" of the playtest; NOT confirmed on camera which object the original had there | find what stood on each square blob in the placement records; if it is something we do not place, drop that blob; add polygonOffset so they never z-fight |
| all cut-outs | alpha-tested edges show the magenta/dark key colour as a fringe when filtered | bleed the neighbouring colour into the keyed texels at convert time (part of tier 2 for cut-outs, cheap enough to do on its own) |
| 180480, c0_142e00, 17ce80, 39380 | extreme UV stretch (4000-14800) on small faces | same fix as 67180 |

## Throwaway build (local only, not committed)

`H:\hzm_work\flpolish\fix2\texswap.py <in.pk3> <out.pk3> texinv58.json` (env `TEX_T1`, `TEX_T2`, `TEX_WATER`) builds
a pak with tier 1 and tier 2 applied: `H:\hzm_work\flpolish\v58tex_fl_1_1.pk3`. The before/after pair of the same
view has NOT been captured yet: a visible client may not be started while the user is playing. Views are listed
in `H:\hzm_work\flpolish\fix2\viewlist.txt` (ground, start, wall, roof).

## Credits (CC0, Poly Haven - https://polyhaven.com/license)

Downloaded as 1k diffuse JPG, each into its own folder under `H:\hzm_work\flpolish\texdl\`; URL list in
`texdl\_index\sources.json` (pattern `https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/<asset>/<asset>_diff_1k.jpg`).

| asset | page | licence | proposed for |
|---|---|---|---|
| cobblestone_05 | https://polyhaven.com/a/cobblestone_05 | CC0 | 54200, b3600 |
| brown_mud_dry | https://polyhaven.com/a/brown_mud_dry | CC0 | a680, c6_124400, c0_132880 |
| roof_slates_03 | https://polyhaven.com/a/roof_slates_03 | CC0 | 4f880 |
| rock_wall_08 | https://polyhaven.com/a/rock_wall_08 | CC0 | 4aa80 |
| old_planks_02 | https://polyhaven.com/a/old_planks_02 | CC0 | 5ed80 |
| weathered_planks | https://polyhaven.com/a/weathered_planks | CC0 | 38280 |
| worn_plaster_wall | https://polyhaven.com/a/worn_plaster_wall | CC0 | tier 3 candidate for 21b80 |

Another 21 candidates were downloaded and rejected on a contact sheet (wrong period, too clean, wrong scale); they
are listed in `sources.json` and used nowhere.

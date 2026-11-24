# Smoke and Fire - next update plan (2026-11-24, PLANNING ONLY)

Brief (user): *"Make our next update centered around smoke and fire. Beef up all existing fire and smoke animations that
the game uses, to make it more realistic, dramatic and modern."* Scope additions: the same for the bring-your-own-disc
missions (Frontline: Sealed Orders `coop_fl_1_1`, Anchor & Anvil `coop_fl_1_3`; Euro Assault: Their Dying Breath
`coop_ea_1_11`) - first fidelity-first, then (user 2026-11-24, "Yes modern") the same modern look on the original's events, section 6; and **Hell Let Loose as the look target** for base-game explosions, vehicle deaths and fire.

Status: nothing built, nothing committed, no deploy. Baselines read: mod `5778458cf`, engine `H:\hzm_work\eng-hotfix13661`
(`rel-1.10.38-engine` 402fee29). Research scripts and caches (not project files): the session scratchpad `fx2\`
(`vfs.py`, `sweep.py`, `cov.py`, `size.py` over the LIVE pak stack, 84 pk3s, homepath wins).

---

## 0. The one thing to know first: this is round 2, not round 1

**`fx_1025` already shipped in v1.10.37** (`docs/proposals/kickoff_2026-10-18/fx_1025/` - DESIGN, BUILD, INVENTORY, COST;
mod `e61c056de`; README line "burning wrecks and scorch marks"). It gave us, and this plan builds on rather than redoes:

- gl2 per-sprite flipbook clock + `animMapOnce` + `animMapPhase` (the precondition for any flipbook);
- tik commands `firelight r g b radius flicker`, `hazeburst`, `hazespot` (8 screen-space shimmer spots);
- `coop_scorch` decals (cap `coop_scorchMax` 14, life `coop_scorchTime` 90, oldest fades);
- base blast on every surface; `coop_fx.pk3` flipbooks (fire 512 JPG 36/40 fr, flame 256 26 fr, smoke 256 40/32 fr,
  dust 24, puff 16, ember, scorch - all our own Blender Mantaflow / procedural renders, `CREDITS_FX.md`);
- 52 retail tik overrides, toolkit tiks `coop_blast_s/m/l/xl/air`, `coop_fire_s/m/l`, `coop_smokecol`, `coop_wreck(_lo/_pops)`;
- `coop_mod/fxwreck.scr` - wrecks burn until map end with distance LOD (3 full / 9 lo / 40 records).

Earlier smoke work, also kept: soft particles (bug-2594, `r_softParticles`, 24u), gl2 smoke lighting stub fixed (bug-1126),
lingering gun smoke / smoke whips (`coop_smokeWhip*`, toned down by bug-1200 - user: *"way too much, tune it down"*),
reinforcement smoke screens that really blind AI (`smokescreen.scr` + `coop_screensmoke.tik`, `docs/proposals/smoke_2026-10-15`),
tempmodel pool raised instead of cutting content (bugs 2217/2242/2303 - user: *"id rather the pool get increased than we lose
content"*), HD-pack impact density repaired (bug-1190 - user: *"MASSIVE smoke hits... way overkill"*), HD sprite size
re-scale (bug-11244), snow-blast soot (bug-10565). **Rejected before:** alpha-to-coverage for sprite edges (bug-2596, no MSAA);
warzone explosion variants (*"too..."*, FEATURES "REVERTED"); index for GetEmitTime (bug-3568, slower than the list).
**Lesson repeated three times (gore, impacts, gun smoke): intensity needs a user checkpoint per round.**

**Warning found by the vet - the fx_1025 sources are gone from the mod tree.** Mod commit `1a4cddf50` (2026-11-02,
mislabelled "coop_defaults.cfg: field-settings generator output after the attic merge") deleted 146 files, among them 25
`models/fx` tiks (`grenexp_base`, `bazookaexp_base`, `coop_blast_*`) and 38 emitters (`coop_wreck(_lo/_pops)`, `coop_fire_*`,
`coop_smokecol`, `fire`, `firegood`, `mortar_*`, ...) - the bug-10472/4437 pattern (`split_tex.py` strips changed `models/`
files at release and the stripped tree got committed). They survive only inside `zzzzzz_co-op_hzm_mod_assets_tey.pk3` and in
`e61c056de`; `fxwreck.scr` still spawns `coop_wreck.tik`. Not logged anywhere. fx_1025 also has **no FEATURES.md entry
or HISTORY.md line**, and bug-fx1025-1 still reads "prototype, not merged" although it shipped. The base engine checkout
`openmohaa-hzm` (`hzm-coop-working`) has no `firelight`; only `rel-1.10.38-engine` (eng-hotfix13661) does - **branch every
engine phase from `rel-1.10.38-engine`**.

---

## 1. Inventory

568 effect tiks (`models/fx` + `models/emitters`, all three games + mod + disc output), 393+ sprite shaders. Effective winner
= what loads after pak priority (homepath > basepath, alphabetical, later wins; gl2 tries `.dds` before `.tga`).
"fx25" = an fx_1025 override that wins; "lost" = a mod copy that loses on pak order.

| family | tiks | fx25 | lost | top un-upgraded (placed in maps / script refs) | effective sprites today |
|---|---:|---:|---:|---|---|
| Muzzle smoke (inline in ~1,190 weapon tiks + `snipesmoke` 645 refs, `garandsmoke` 55) + `coop_gunsmoke`, `coop_barrelsmoke` | 2 mod | - | - | every gun | `vsssource` 128 DDS x0.25 (=32u), `vsssource2` 32 px (Thompson/PPSh); 1 frame, blend |
| Bullet impacts `bh_*`, `fs_*` | 44 | 0 | 0 | all; winner is `zzzzzzzz_hd_fxfix` | `dustdrop` 256, `bh_dirt_piece` 8 px, VSS `bulletimpact` |
| Grenade | 25 | 1 | **2** (`grenexp_base`, `grenexp_snow`) | all `grenexp_<surface>`, rifle/M2 frag | **retail `gren_boom` 7 fr 256 px** - the most-seen blast in the game is still retail |
| Smoke grenades / screens | 7 | 0 | 0 | `nebelhandgranateexplosion` (5 maps), `m18_smoke_grenadeexplosion`, `signalsmoketrail`, `rdg-1`, `smokegrenadeexplosion` | `smokegrenade_*` / `hrpuffnstuff*` **128 px, 1 frame, no HD at all** |
| Artillery / mortar / Nebelwerfer | 43 | 6 | 0 | `heavyshellexp_dirt/snow/stone`, `mortar_snow_triggerable` (t2l2: 20), `nebelwerfer_death`, `granatwerfer*` | `mortar_dirthit` 1024x2048 DDS, `snowclump` 16 px |
| Rocket / tank shell | 19 | 1 | **1** (`bazookaexp_base`) | `bazookaexp_*`, `tankexp_dirt/snow/stone`, `explosion*shell` | `bridgecharge` 512, `puffystuff_light` (**draws 4x too big**) |
| Vehicle / aircraft death, smoke trails | 37 | 7 | 0 | `c47_fleet`, `explosionstukaround`, `planesmokeplume*`, `shermansmoke`, `tanksmoke`, `supplytruck_dmg` | `air_explosion` 10 fr 256; VSS `greasefire` |
| Flak | 17 | 4 | 0 | `exp_flak_far1-3`, `exp_flak_near01-03`, `_moving/_v2/_v3` (**missing shaders**) | `flak_cloud01/03/04` 128 px |
| Set-piece blasts | 52 | 11 | 0 | `tehao_explosiondust`, `cinematics_foregroundexplosion01-03` (e3l4: 18), `tehao_pilarexplosion`, `bombblast_snow`, `roof_banger`, `wall_exploder`, `barracks_explosion`, `explosion_conflagration`, `aircraft_explosion` | `vsssource`, `bridgecharge`, `grndblst1` 64x32, `cinematicexplosion_02` 19 fr |
| Map fires (torch, barrel, campfire, hall, candle, lantern) | 49 | 16 | 0 | `tehao_candleholder_withfire` (**255 placed**: montecassino 60, e3l4 51, montebattaglia 46), `candle_standing_fire` (e3l4 120), `lanternflame` (mp_anzio 20), `electrical_fire`, `hallfire2` | candle `tehao_candellight_02` 65 fr **32 px**; `campfire_02` 128 retail; `fire_ring` 576 x0.25 |
| Chimney / stack / ambient smoke, steam | 36+5 | 3 | 0 | `linger_smoke` (47 mod script refs), `smoke_smallfry` (m4l2 12), `tehao_steampipe`, `breath_steam_emitter`, `ddaysmoke(2)`, `cheapsmoke`, old-style `thin_*`/`wide*` | almost all `vsssource` / VSS |
| Sparks / electrical | 13 | 0 | 0 | `generic_spark` (15 maps, 72 placed), `adamspark` (m4l2 14), `welding_spark`, `trainsparks` | `corona_white` 64, `corona_util` 256 (**2x too big**), `trainspark_01` |
| Flamethrower | - | - | - | **none exists in any pak (AA/SH/BT)**. Only orphan art `flamer_01..25` (unused `simple_flame` shader) | - |
| Tank cannon / exhaust | ~6 | 0 | 0 | `tankcanon(2/_pov)`, `nebelwerfer_exhaust`, `grenadetrail` | retail |

Key lever: **every volumetric (VSS) plume renders `VSSSource.spr` / `VSSSource2.spr`** (`cg_volumetricsmoke.cpp:1167`) - plane
and tank smoke, grenade mist, impact linger, all muzzle smoke. One sprite pair touches a third of the game's smoke.

Where they are: worst maps e3l4 (160 placed, 19 upgraded - candles), montecassino/montebattaglia (candles), m4l2
(sparks + smallfry), t2l2 (mortar_snow_triggerable), e1l4/co_lobby8 (sparks, nebel smoke). Wreck hook `fxwreck.scr::wreck`
is called from `autotank.scr:617`, `autotruck.scr` (4), `alarmveh.scr:905` - **not** from `halftrack.scr`,
`vehicles_thinkers.scr`, `stationaryweapons.scr` (they spawn `fx_tank_explosion` and leave nothing). The fx_1025 toolkit
tiks (`coop_blast_*`, `coop_smokecol`) are spawned by **no** script.

### 1a. Defects found during the inventory (fix in Phase 0 - free visual wins)
| # | defect | evidence | effect in game |
|---|---|---|---|
| D0 | fx_1025 tik sources deleted from the mod tree (section 0) | `git show --stat 1a4cddf50` | the next release build that regenerates `assets_tey` may drop wrecks, blasts and map fires |
| D1 | `fx/grenexp_base.tik`, `fx/bazookaexp_base.tik`, `fx/grenexp_snow.tik` ship in `zzzzzz_co-op_hzm_mod_assets_tey.pk3`, which sorts **before** `zzzzzz_hd_fx` / `zzzzzzzz_hd_fxfix` (`co-op` < `hd`); the code pak `zzzzzz_co-op_hzm_mod_*` loses the same way. Root: `split_tex` moves every changed `models/` file into `assets_tey` each release | the winning hd_fxfix copy is byte-identical to retail (OPEN.md:570 and bug-10565 disagree on which grenexp loads - **read the deployed pk3 back before claiming either**, bug-1610) | hand grenade + bazooka blasts likely retail since v1.10.37; the bug-10565 cgame snow skip is live but the flash/fireball moved into `grenexp_snow` (`916cb7108`) - **snow grenades may have no flash today** |
| D2 | `puffystuff_light`, `generalfireball_01`, `sandstorm02` 4x too big; `corona_util` 2x | share textures with discstock 4x DDS, no `spritescale` re-emit (bug-11244 class) | blobs in shell/set-piece blasts. **`corona_util` is excluded**: it is the lightglow for ~6,000 lamps, muzzle glows and headlights, restored under an Omaha byte-identical rule (bug-2946) - A/B it separately with the headlight owner, or leave it |
| D3 | hd_fxfix `bh_wood_hard/lite`, `bh_dirt_hard/lite`, `bh_mud_hard/lite`: an emitter's `)` is commented out (e.g. `bh_wood_hard.tik:101`) | paren scan | impacts half-parse (bug-1190 class) |
| D4 | retail parse breaks: `barracks_explosion` (line 127 `(` for `)`), `exp_flak_near_moving` (stray `)` line 67); missing shaders `c47skytrain_fiery1/2`, `explosion1`, `explshock`, `explsmoke`; `smokegrenadeexplosion` includes a `_base.txt` no pak has (bug-11550). **Corrected 2026-11-24:** `hallfire2`, `wall_exploder`, `roof_banger`, `steamworks` are NOT broken - two-pass comment stripping (a `//****` banner opened a block comment) produced false positives (bug-11547) | `fx_coverage.py` | effects partly or wholly missing |
| D5 | mod `M18_Smoke_GrenadeExplosion_base.txt` (2026-07-01, 4fa27cd13): `spawnrate 0` server and client | file | the thrown M18 draws no smoke of its own. The paradrop marker is a separate `planesmokeplumeyellow.tik` from `paradrop.scr` (user asked for it, bug-1847); the M18 sprite `smokegrenade_allied` is **red** (bug-2201); the item handler deletes world M18/RDG/Nebel smokes (bug-484). Turning the emitter on would double the marker. **Ask: "should the thrown M18 show any smoke besides the yellow marker plume?"** |
| D6 | `cfx_fire_fb/_tk`, `cfx_flame`, `cfx_ember`: `blendfunc add` with no `rgbGen vertex` -> identityLighting (`tr_shader.c:2108-2120`) | code | tik `color` ignored; and because `add` = `GL_ONE GL_ONE` while the tempmodel fade drives alpha only (`cg_tempmodels.cpp:631-638`), the loop flame pops at end of life. **Fix = `blendFunc GL_SRC_ALPHA GL_ONE` + `alphaGen vertex` (+ `rgbGen vertex`)** - soft particles already treat that blend as additive (`tr_shade.c:1786`) |
| D7 | tik `spritegridlighting` sets `T2_SPRITEGRIDLIGHTING`, read only by the test-emitter UI (`cg_testemitter.cpp:1213`); smoke is lit only with `collision` (`cg_tempmodels.cpp:618-628`), via `R_GetLightingForSmoke` = lightgrid + a loop over every dlight per particle per frame, one frame late | code | the fx_1025 smoke blocks that ask for grid lighting are unlit. **Conflicts with bug-10524**, which blamed `spritegridlighting` for dark snow cards and removed it - one of the two readings is wrong; measure first. Gate to **blended** sprites only (with D6, additive fire would otherwise go dark at night) |
| D8 | doc drift: `docs/ENGINE.md:345` says tempmodels cap 2048 (code: `MAX_TEMPMODELS 4096`); fx_1025 DESIGN:74 says "first shader definition wins". The real rule (TRAPS:307, bug-2485, bug-2228): **pak order decides; within one pak the alphabetically first shader file wins; within one file the last definition** | code + TRAPS | wrong rule leads to wrong override strategy |
| D9 | sprites are added for **every** view - dlight cubemaps/shadow maps and up to 4 sun cascades run before the main view (`tr_scene.c:731-822`, main at `:986`), are sorted and thrown away (`tr_main.c:1791-1797`), but consume `MAX_SPRITESURFS` with no per-view cap; at 0x8000 the **main view's** sprites are refused (`tr_main.c:4085-4099`) | code | with ~7 views, ~4,700 live sprites starve the main view - the fx budget below sits close to that. Early return in `R_AddSpriteSurfaces` for `VPF_SHADOWMAP|VPF_DEPTHSHADOW` |
| D10 | `MAX_DRAWIMAGES` 4096 is a hard `ERR_DROP` (`tr_image.c:2218`); each 64-frame `animMap` = 64 images | code | Phase 1-2 sets + LOD sets add ~1,000 images on top of the HD packs - grep maptest logs for `^~^~^ IMAGECAP` on the heaviest maps before shipping |

---

## 2. Engine and renderer capabilities (gl2, `eng-hotfix13661`)

| capability | today | content-only? | to improve | risk |
|---|---|---|---|---|
| Soft particles | yes, sprite list only (tempmodels + VSS), global 24u, alpha/add/modulate-aware (`tr_shade.c:1748-1800`). Beams/polys via `qer_hzmSoftEdge`, which explicitly returns 0 inside the sprite list (`tr_hzm_spot_rb.c:814`) | yes | per-shader sprite distance = a small new branch (not a reuse) - big smoke wants 64-128u, sparks 8u | low |
| Flipbooks | per-sprite clock, once, phase; cap **64 frames** per stage (`MAX_IMAGE_ANIMATIONS`), hard frame switch, no blending, no atlas (UV 0..1 fixed, `tr_sprite.c:187`); each animated sprite with its own start time is its own draw (`tr_backend.c:3144-3156`) | yes (<=64 frames) | random start frame (`cg_tempmodels.cpp:1588`) - **low-med**: a 40-sprite burst goes from 1 draw to 40, and a backdated `animMapOnce` ends early - ignore the flag on Once stages, never on `VSSSource` (its shaderTime is a roll value, `cg_volumetricsmoke.cpp:1342`); atlas + crossfade - **high**: a new GENERICDEF bit doubles the generic programs 64 -> 128 (startup / vid_restart compile time), a 2nd diffuse TMU beside the soft-depth TMU, gl1 draws the whole sheet; but it also cuts `MAX_DRAWIMAGES` use to 1 image per set | low-med / high |
| Random variants | yes: `model a.spr b.spr c.spr` per particle | yes | - | - |
| Sprite lighting | one CPU colour per particle (lightgrid + all dlights, 1 frame late), only with `collision` (D7); flat across the quad; no normals; renderer skips dlight pass for sprites | partly | (a) honour `spritegridlighting` for blended sprites without the trace - low-med (per-particle dlight loop cost, D6 interaction); (b) per-corner lighting in `RB_DrawSprite` (fire lights the smoke's underside) - **med**: 4 grid lookups per sprite in the backend, and cgame and renderer must agree who lights (else double-lit or unlit), so they ship together; (c) 6-way lightmap / normal smoke - **high**, not proposed | low-med..high |
| Sort / blend | sprites draw after the whole main list; the sort key's distance term is a **squared** distance up to 2^28, clamped (not negative), overlapping the shader field from bit 17 by 12 bits (`tr_main.c:4071-4103`, `tr_local.h:2339`). The backend reads the shader from `refSprite->shaderNum`, so it affects order only, never crashes | - | **one** back-to-front order with shader batching only inside equal-depth runs. (A "blended first, then additive" split was rejected in review: fire behind a smoke bank would show through it.) 32-bit guard `tr_local.h:2342` | **med-high** (every effect's look, lost batching) |
| Limits | `MAX_SPRITES` 8192, `MAX_SPRITESURFS` 0x8000 (guard: SURFS >= SPRITES), tempmodels 4096/4000 seeded, beams 8192, **`MAX_DLIGHTS` 32 first-come** (`tr_scene.c:328`), per FRAME partitioned by scene (`r_firstSceneDlight`), marks 487 seeded, haze 8, **`MAX_DRAWIMAGES` 4096** (D10) | - | shadow-view sprites (D9) -> Phase 0; dlight **priority** must evict only inside the current scene's range and not reorder after the spot intake (`tr_scene.c:325`) - low-med | see T4 |
| Wind | tik `wind` -> global `vss_wind_x/y/z` (8/4/2), strength 8; nothing sets it per map; rain slant reads `vss_wind_x` (`cg_nature.cpp:372,696`). **Wind is a per-axis velocity TARGET, not a force** (`cg_tempmodels.cpp:884-920`) | yes (tik) | weather-driven wind via a free configstring (slots 29-31 pass protocol 6 unchanged, `bg_public.h:91-98`; only 3 free - budget them) = game.dll + cgame; set **x/y only** or columns stop rising; changes every retail tik that says `wind` and the rain slant | **med** |
| Collision | one trace per particle per physics tick (10 Hz) + lighting | yes | keep for debris/embers only | - |
| Heat haze | post pass: global warp, muzzle ripple, 8 spots (`heathaze_fp.glsl`), fed by 9 `Cvar_Set` per frame; **not depth-tested**; scene depth is sampled only for the muzzle mask, and each spot vec4 (u,v,r,s) is full | yes | depth test needs a 5th component -> new `r_ppHz%d` string format (`tr_postprocess.c:1404`) + uniforms = cgame + gl2 in lockstep, all four haze-family places | low-med |
| Emissive / bloom | `r_hdr 1` (LATCH) float buffer, threshold bloom 0.6 / 1.3, exposure-aware; one additive layer cannot exceed 1.0 | partly | `qer_hzmEmissive <mult>` scaling the float colours already pushed to GLSL (`tr_shade.c:622`) - no GLSL edit; must be `qer_` (unknown STAGE keywords fail the whole shader in gl1) | low |
| Fire dynamic light | `firelight` (3-sine flicker, cull `coop_fireLightDist` 1500), eligible for dlight shadows (2 lights / 4 maps, radius >= 120) - flicker makes shadows pulse and competes with muzzle flashes | yes | `noshadow` option (`hzm_dlight_noshadow` exists) - low; priority (above) | low |
| Camera shake | tik `viewkick` is **weapon recoil** (484 mod files) and returns unless the parent is the local client (`cg_commands.cpp:6296`); it writes the shared `cg.viewkick` recentre state - **reusing it would corrupt recoil**. Server `earthquake` exists (`g_main.cpp:884`), m3l1a uses `earthquake_radius` (bug-2204), `global/earthquake.scr` drives `jitter_*` | no | own visual offset at `cg_view.c:10090`, fed by (1) `CG_MakeExplosionEffect` (server explosion messages only) **and** (2) a new tik command beside `hazeburst` (set pieces, vehicle deaths, exploders never reach (1)); scaled down in ADS (it moves the crosshair off the aim point); suppressed while a server earthquake runs; **default 0** (warzone variants were rejected as too cinematic) | low-med |
| Live shader swap | `re.RemapShader` exists in both renderers (gl2 `tr_init.c:2851`) with **no caller** | - | a gl2 console command `r_hzmRemap <from> <to>` = truly live A/B for texture-only changes (VSS, muzzle, candles), no API bump | low |
| gl1 | no soft particles; `animMapOnce/Phase` OK; `nosoftparticles` **breaks the shader on gl1** (stage keyword) | - | policy: gl1 must only not crash | - |

**Capacity family (TRAPS T4) - constants that move together if raised:** sprites (`MAX_SPRITES` both renderers +
`MAX_SPRITESURFS` + its `#error` + the `advanced_graphics.urc` slider from `gen_menu_graphics.py`); dlights (`MAX_DLIGHTS` is a
32-bit per-surface mask + `shadowCubemaps[]` + `lightOrder[]`/`lightScore[]` + sphere-light arrays + gl1 - **do not raise; prioritise
instead**); haze (`HZ_MAX` 8, `r_ppHz0..7`, `tr_postprocess.c:1392`, GLSL `u_HzHaze0..7` - four hand-synced places); sort key
(shift + `SHADERNUM_BITS` <= 32); images (`MAX_DRAWIMAGES` 4096, D10). This plan raises **none** of them.

**Binary coupling (ship together or not at all):** new tik keywords (`randstart`, shake) need the matching cgame.dll in the
same release as the pk3; haze format and per-corner lighting = cgame + gl2; wind = game.dll + cgame (the public servers run
game.dll - coordinate). Any new `re.*` / `cgi.*` entry bumps `REF_API_VERSION` 15 or `CGAME_IMPORT_API_VERSION` 4 and pulls
in openmohaa.exe - **prefer cvar, console-command and shader-keyword designs**, which avoid all of it. A menu row driving
`r_*` cvars inherits build.ps1's menu/renderer pairing guard (build.ps1:315-325). Any `.glsl` edit: `glsl_variant_lint.py
--emit` + glslang (the build never compiles GLSL).

---

## 3. The Hell Let Loose look (base game AA/SH/BT; disc missions too since 2026-11-24, on their original events - section 6)

Studied from the brief's description of the look only - no HLL asset, texture, code or capture is used or shipped.
Each trait mapped to what our engine can do. Effort in days of agent work; risk per section 2.

| HLL trait | our implementation | engine? | effort | risk | cost |
|---|---|---|---|---|---|
| short bright flash | 2-4 frame white-hot core card (additive, `qer_hzmEmissive` 2-3x so bloom catches it) + ground-flash `blockdlight` 600-900u for 0.1 s (fx_1025 already flashes; make it shorter, brighter) | emissive keyword | 0.5 | low | 1 dlight, 1 sprite |
| dense rolling dark-cored fireball | new 512 px 48-64 frame fireball flipbook with a dark soot shell rolling over a bright core (Blender Mantaflow fire+smoke, rendered emission + density separately and composited); random start frame + 3 variants so no two blasts match | random start | 1.5 | low | 2-4 sprites |
| ground-hugging dust + shockwave ring | flat `parallel_oriented` ring sprite expanding fast along the ground normal (0.25 s) + low dust skirt that rolls outward and settles (dust flipbook at 512, soft distance 64u, wind drift) | per-shader soft | 1 | low | 6-10 sprites |
| thick black slow-rising columns lingering minutes on wrecks | `coop_wreck` column: big (300-600u) soft lit puffs, life 20-40 s, slow rise 15-30u/s, wind-sheared by `vss_wind`, emitted 0.5/s -> ~20-40 live per wreck; LOD by fxwreck rank; per-corner lighting so the underside glows orange from the firelight | wind, per-corner light | 1.5 | low-med | overdraw is the price: cap 3 full columns |
| flying debris, sparks, embers | debris already in retail tiks; add streaked spark sprites (`spriteGen oriented` along velocity, `collision` + `bouncefactor` for a few), ember fountain with `wind`, short life | no | 0.5 | low | 20-40 short sprites per blast |
| secondary fires on wrecks | `coop_wreck` gains 2-3 offset small flame loops on the hull + cook-off pops (exists) + wreck hooks added to `halftrack`, `vehicles_thinkers`, `stationaryweapons` | no | 0.5 | low | per fxwreck LOD |
| scorch decals | exists; add a larger dark crater variant for shells/vehicles and a soot streak on walls for wall-near blasts | no | 0.3 | low | marks pool |
| strong blast scene lighting | the flash dlight above + 1.5 s amber falloff (exists) - **dlight priority** so a blast always beats ambient fires for the 32 slots | priority | 0.5 | low-med | none new |
| camera shake by distance | own cgame view offset (not `viewkick` - that is recoil), fed by explosion messages and a new tik command; amplitude by size class and distance (0 at ~1500u), reduced in ADS, suppressed during a server earthquake; `coop_blastShake` **default 0** until the user picks a strength | yes (small) | 0.7 | low-med | none |
| heat shimmer over fire | exists (`hazespot`); depth-test the spots so soldiers in front are not warped (5th spot component, cgame + gl2 together) | depth test | 0.5 | low-med | - |

The disc missions get the same modern look on their original events (user 2026-11-24, section 6).

---

## 4. Proposal - phases, biggest visual win per effort first

Every phase: built on branches/worktrees, private harness only, one-key A/B (section 5), a 5-minute test script, judged
**in motion** (GIFs sent as soon as they exist, not just the first frame), **user signs off the look before merge**.
gl2 only; gl1 must not crash (one boot + one map check).

### Phase 0 - repair what is already broken - ~1.5 days, highest value per hour
0. **D0 first**: restore the 146 deleted fx_1025 files with `git show e61c056de:<path>` (never rebuilt from memory - the
   user's revert rule), log a bug, and keep fx tiks out of `split_tex`'s strip (or give them their own pak source dir).
1. D1: put every mod effect tik in a pak that sorts after `zzzzzzzz_hd_fxfix` (`zzzzzzzzzzzzz_coop_fx.pk3` holds only
   textures today; mind that `coop_late`/`scopeglass`/`wpnfix` sort after it - bugs 10394, 11270, 10921). Add a **build-time
   winner check** for tiks **and shaders** over the **shipped set** (`manifests/latest.json`, TRAPS "dev-only content skews
   audits"), not the dev install. Read the deployed pk3 back to settle OPEN.md:570 vs bug-10565. **This changes every grenade
   players see** (base blast now plays on every surface) - it is a look change: A/B + user checkpoint, not a silent fix.
2. D9: early return for sprites in shadow views (`R_AddSpriteSurfaces`, `VPF_SHADOWMAP|VPF_DEPTHSHADOW`) - correctness,
   low risk, gl2 only; then measure D10 (`IMAGECAP`) on the heaviest maps.
3. D2: extend `upscale_discstock.py hdpack_sprite_fixes()` to `puffystuff_light`, `generalfireball_01`, `sandstorm02`
   (not `corona_util`).
4. D3/D4: repaired copies - `gen_fixes_pak` is not dependable right now (1.10.86 pak hand-merged, bug-11370; missing source,
   bug-11328; "new" members must not sit in the mod tree, bug-4149), and hd_fxfix was hand-built by a scratchpad
   `mkfxfix.py` with one earlier paren repair in the animations block (bug-1892) - confirm D3 is a different defect, build a
   tracked generator, never leave a `*_bak.pk3` in a game dir (bug-1893). Paren/brace depth scan per TRAPS.
5. D6: `blendFunc GL_SRC_ALPHA GL_ONE` + `alphaGen vertex` + `rgbGen vertex` on the cfx fire shaders - look change, A/B.
6. D7 **after** D1: a measurement pass (probe what actually darkened bug-10524's snow cards), then `cg_hzmSmokeGridLight`
   for blended sprites only, A/B; list the retail tiks that will change.
7. D5: ask the user (reframed question in 1a). D8: fix `ENGINE.md:345` and fx_1025 DESIGN:74. Record fx_1025 in
   FEATURES/HISTORY, correct bug-fx1025-1's status, update the "Lingering gun smoke" entry (0.35 -> 0.15/0.1, bug-1200).

### Phase 1 - one new texture set, broadest reach (content) - ~3 days
**Scope split with the volumetric prototype (2026-11-24, coordinator):** burning-wreck columns (and later barrage banks)
become true 3D volumes on engine branch `volsmoke-eng` (`VOLUMETRIC.md`); the flipbooks here cover everything else -
muzzle smoke, grenade / shell smoke, smoke grenades incl. the M18, chimneys / stacks / steam. No work on wreck-column
sprites. Integration points: `coop_wreck.tik` and the `cfx_*` shaders ship from the fx pak overlay
(`docs/tools/assets/fx/pak/`, built by `gen_fx_pak.py`) - the mod-tree copies are pinned shadows that do not ship, so the
volumetric `vol` emitter and `qer_hzmVolSmokeAlt` keyword must go into the overlay copies; the Phase 1 soft-edge generator
re-emits shader bodies from the overlay as they are, so a `qer_hzmVolSmoke*` keyword there is preserved.
Done so far: soft particles per sprite (`r_hzmSpriteSoftPer`), D7 grid lighting (`cg_hzmSmokeGridLight`), scorch variants
(`cg_hzmScorchVar`), M18 coloured cloud, our own `cfx2_billow` (512 px, 40 fr) - all in layer `pak_p1`, all default off.
1. **Smoke master set** (own Blender renders, see section 7): 512 px, 48-64 frames, rolling billows - dark soot, grey
   battle smoke, white smoke-grenade, light dust - plus a 256 px LOD set. DXT5 `.dds` precompressed.
2. **VSS + muzzle**: new art under **new shader names**, retargeted tik by tik (muzzle blocks, VSS types), at the same world
   size and the **same mean brightness and alpha** as `vsssource` - the D-Day emitters tint it down (bug-2201) and m3l1a's
   smoke barrage depends on it. **Not a global `vsssource` image swap.** Intensity fixed (same alpha, life, count) - the user
   has twice said gun smoke was too much (bugs 1190/1200); only the texture improves. Live A/B via `r_hzmRemap`.
   **Omaha (m3l1a/m3l1b) and the disc missions are excluded** from every Phase 1-2 retarget unless the user says otherwise
   (memory: never touch Omaha; bug-3481: the user asked several times to cut the ocean fires 150 -> 45 s).
3. **Smoke grenades** (M18 if approved, nebel, RDG-1, signal): rolling dense bank on the screen-smoke recipe, coloured signal
   variants, longer hang, wind drift. Server `SmokeSprites` (what blinds AI) unchanged.
4. **Candles and lanterns** (255+ placed, 32 px today): a 128 px 64-frame candle flame flipbook at the same size, count and
   timing, `animMapPhase` kept so they do not flicker in sync; **no dlights** (fx_1025 reason: tiny and numerous).
5. **Chimneys / stacks / steam / `linger_smoke`**: retarget to the new set, wind-sheared; life unchanged on Omaha and
   the disc missions (`coop_ea_1_11.scr` calls `linger_smoke` 3 times; converted missions pull stock tiks, bug-11243) -
   ship as a new tik name for the base-game sites rather than editing `linger_smoke` itself.

### Phase 2 - Hell Let Loose blasts and wrecks (content + low-risk engine) - ~5 days
1. Engine batch on a branch from `rel-1.10.38-engine`, each behind its own cvar (flags 0 - see section 5): random start
   frame (`randstart`, ignored on Once stages), per-shader sprite soft distance, `qer_hzmEmissive`, `r_hzmRemap` console
   command, dlight priority (blasts > muzzle > fires, inside the scene's range), firelight `noshadow`, distance camera shake
   (own offset, default 0). Second tier, only if wanted: haze-spot depth test (cgame + gl2), weather wind x/y (game + cgame).
2. Section 3 content: fireball (3 variants, 512, 64 fr), flash core, shockwave ring + dust skirt, sparks/embers, crater
   scorch, wreck column + secondary fires; retarget grenade/bazooka/tank/shell/mortar surface variants (`*_dirt/snow/stone`)
   that fx_1025 left retail; wreck hooks for halftrack / vehicles_thinkers / stationaryweapons.
3. Flak bursts (dark rolling puff + flash, airburst no scorch), artillery dust columns with ring, Nebelwerfer trails.
4. Set pieces still retail: `cinematics_foregroundexplosion*`, `tehao_explosiondust`, `tehao_pilarexplosion`,
   `bombblast_snow`, `explosion_conflagration`, `aircraft_explosion`, `barracks_explosion` (after D4 repair).

### Phase 3 - modern smoke rendering (medium-risk engine) - ~5 days, only if Phase 1-2 look is approved and the user wants more
1. **Sprite-sheet atlas with frame crossfade** (high risk) - smooth slow smoke from 64 frames over 30 s without stepping;
   collapses the per-animated-sprite draw split and cuts `MAX_DRAWIMAGES` use to 1 per set. Costs a GENERICDEF bit (64 -> 128
   programs), a 2nd TMU, a gl1 `ifCvar` fallback stage; lint + glslang every variant.
2. **Per-corner sprite lighting** (med) - fire lights the underside of its own column; one owner (renderer) for lighting
   so cgame and renderer never double-light; ship cgame + gl2 together.
3. **Sort fix** (med-high) - one back-to-front order with batching only in equal-depth runs, so fire reads inside its smoke.
Deferred (high risk, not proposed now): 6-way lightmap smoke, raising `MAX_DLIGHTS`, GPU instancing, OIT.

### Phase 4 - disc missions: modern visuals on the original's events (section 6) - ~4 days, after the Phase 2 toolkit

### Order rationale
Phase 0 fixes things players already pay for (VRAM, tiks) but do not see. Phase 1 is one texture set reaching the whole
game. Phase 2 is the headline "dramatic" change. Phase 3 is the only part with medium risk, gated on the look.

---

## 5. A/B, presets and performance budget

**A/B (user rule: one key, 5-minute script, judged in motion, user signs off first).** Two tiers, honestly:
- **Live (one key, no reload)**: every renderer/cgame feature has its own cvar with 0 = byte-identical old behaviour,
  created with **flags 0 - never ARCHIVE or LATCH** (`r_softParticles` is ARCHIVE|LATCH and so is *not* a live precedent;
  an archived value beats a changed default for existing players - TRAPS T7, bug-1200 - so a knob meant to ship on must
  have its final value baked in as the code default): `cg_hzmSmokeGridLight`, `r_hzmSpriteSoftPer`, `r_hzmEmissive`,
  `r_hzmDlightPrio`, `coop_blastShake`, `cg_hzmFxRandStart`, later `r_ppHzDepth`, `r_hzmSpriteSort`, `r_hzmSpriteAtlas`.
  Texture-only changes (VSS/muzzle art, candles, smoke sets) A/B **live** through `r_hzmRemap` (the unused
  `re.RemapShader`). A dev bind flips the whole set (`fxab_old.cfg` / `fxab_new.cfg`, `bind F9 vstr coop_fxABnext`).
- **Content (one key + map restart)**: new art ships under **new names** (`cfx2_*`, `models/fx/coop2_*`); a console-only
  cgame remap `cg_hzmFxSet 0|1` routes the SFX-table effects (names are literals in `cg_specialfx.cpp:84-160`, loaded once
  per cgame init) back to the shipped files. Map-placed emitters come through `CS_MODELS`, which the cgame registers itself
  (`cg_main.c:468`), but the listen-server shared handle (`CG_ModelHandleShared`, bug-10543) makes a client substitution
  unsafe - so they switch with the pak present/absent and the test script does both boots. Do not call that tier live.
- Each test script: fixed camera spots (harness `fx_ingame.py` / `mkscenes.py` reuse), day + night + snow map (m5l2b,
  m6l2b, t2l4), same time stamps old vs new, GIF per family, 5 minutes total for the user in game.

**Quality presets**: fold into the **existing** Quality Preset row (`gen_menu_graphics.py` `PRESET_VALUES`;
`gate_presets` asserts High == DEFAULTS mirrored from `coop_defaults.cfg`, bug-3484) - no separate `coop_fxQuality` row.
Low = 256 sets, 1 full wreck, firelight 800u; High (default) = 512 sets, 3 full / 9 lo wrecks; Ultra = 5 full wrecks.
No "retail art" preset in the menu: map-placed emitters cannot switch live, and a setting is a promise. Nothing latched is
ever applied from a menu (DECISIONS: menu-triggered `vid_restart` crashes gl2); `cg_hzmFxSet` stays console-only.

**Budget (per frame, target: no change in the fx_1025 COST.md rows at 60 fps on the dev rig; must also hold on a
mid GPU - ask the user for a test machine or use `r_customwidth` 2560 as a fill-rate stand-in):**
| item | budget |
|---|---|
| live tempmodels in a heavy barrage (t2l4) | <= 1,500 of 4,000 (fx_1025 barrage: 401) |
| live sprites | <= 3,000 of 8,192 |
| dlights from fx | <= 12 of 32 at any time (priority keeps blasts) |
| full-screen smoke overdraw | cap: 3 wreck columns, soft-distance, `alphaGen distFade` near the camera |
| fx VRAM | high <= 150 MB, low <= 60 MB (512 px 64 fr DXT5 ~ 22 MB per set incl. mips) |
| first-use hitch | 0 visible: precache spawns for every new tik on mod-only maps |
| images | `MAX_DRAWIMAGES` headroom >= 500 on the heaviest map (`IMAGECAP` probe) |
| perf maps | t2l4 (snow barrage), e3l4 (candles), m4l2 (sparks), **m3l1b** (open worst case: 19 fps at 1440p, bug-3477 - measured as a guard even though Omaha art is excluded) |

**Testing discipline** (user prefs): one heavy job at a time (Blender renders `-t 4`, at most two at once; no render during
a harness run); test clients on the secondary 1920x1080 screen, muted; GIFs sent as soon as made; release README media are
in-game captures; public servers block deploys - schedule the release window.

---

## 6. Disc missions (Frontline, Euro Assault) - modern visuals on the original's events

**User decision 2026-11-24 ("Yes modern") - an approved EXCEPTION to disc fidelity-first, for smoke and fire only.**
Sealed Orders (`coop_fl_1_1`), Anchor & Anvil (`coop_fl_1_3`) and Their Dying Breath (`coop_ea_1_11`) get the SAME modern
(Hell Let Loose-style) smoke, fire and explosion visuals as the base games. Everything else in those missions stays
fidelity-first, and this exception is recorded as one row in each mission's FIDELITY list (not one row per effect).

| keep from the original (decoded, per effect) | swap for ours |
|---|---|
| placement: where a fire burns, which objects smoke, where a blast or the jeep mine goes off | the sprites, flipbooks, shaders and emitter look |
| trigger and timing: the script / event that starts it, its delay, its emit duration | the particle motion, colour and lighting (our modern look) |
| roughly its scale (footprint, column height) and duration (how long it burns / hangs) | flash dlights, firelight, scorch, shake per the base-game rules (section 3) |

**Assets:** nothing from the disc ships. The modern art is our own work (Blender / procedural renders, CC0-compatible,
section 7). The disc's own sprites stay only in the player's converted pak, used by the "old" side of the A/B.

**Hotfix in flight (not ours):** the Sealed Orders agent is hotfixing the current over-dense disc smoke (jeep mine, crate
breaks) back to the original's density now. This modern pass REPLACES those visuals later; it must take its scale and
duration targets from the hotfixed (original-density) numbers, not from the over-dense ones.

### 6a. How: a mapping layer in the converters, not new placements
Both converters already decode every effect to an event + a placement + numbers. The modern pass maps each decoded
effect to a class of our toolkit and emits a tik that uses OUR art with the ORIGINAL's footprint and timing:

| decoded effect class (by blend, colour, size, life, rate) | our modern tik family (base-game toolkit, sections 3-4) |
|---|---|
| additive warm, persistent | map fire `coop2_fire_s/m/l` (flame flipbook, embers, smoke column, firelight) scaled to the original footprint |
| additive burst, short life | blast `coop2_blast_s/m/l/xl` by the original's radius; flash dlight; scorch only where the original left a mark |
| alpha dark, rising, persistent | smoke column `coop2_smokecol` (lingering, wind-drifted) at the original's height and duration |
| alpha light / grey, burst | dust / debris puff `coop2_dust` (crate breaks, impacts) |
| alpha light, ground-hugging | mist / steam `coop2_mist` (EA creek mist keeps its own mist pass, `eafx.mist_key`, untouched) |
| sparks, embers | `coop2_sparks` |
| anything the classifier cannot place | stays on the disc's own conversion and is listed (never guessed silently) |

- **Frontline:** `docs/tools/frontline/flpfx.py` decodes kind-9 records (placed: .bpd section 3; by-type templates: section 4,
  incl. the scripts' CREATEPARTICLESYSTEMBYTYPE blasts, `fl_levels.json pfx_bytype`). Add `flpfx.modern(f)` -> class +
  scale/duration, emitted as a second tik per system (`fl_<level>_m_<id>.tik`) next to the disc one. The mission script
  already switches on `coop_flDiscFx` (`maps/coop_fl_1_1.scr:74`, `level.fl_fxDisc`): extend it to three states -
  **2 = modern (default after sign-off)**, 1 = the disc's own systems (today), 0 = the old stock stand-ins.
- **Euro Assault:** `docs/tools/ea/eafx.py` builds one tik per effects package (Action_CreateParticle, EffectsPackage
  placements). Same mapping at package level; new cvar **`coop_eaDiscFx`** (2 modern / 1 disc / 0 stock; there is no EA
  equivalent today - `coop_eaProjFx` is the projectile effect only) read by `maps/coop_ea_1_11.scr` where packages spawn.
- **Footprint match:** scale = original emit-box extent and peak particle size; duration = original emit duration +
  particle life; delay = the original's script timing, untouched. A converter self-check lists every effect with its
  original vs modern footprint and fails on a >1.5x size or duration mismatch (the over-dense-smoke class).
- **Converter rules:** bump `HZMCONV_VERSION` (`conv_guard`); re-convert the user's own disc paks on the live install
  only with their OK; `cg_effectdetail` stays ignored for converted maps (bug-eap-fxleafcull) for the disc side, but the
  modern side follows the base-game quality presets.
- **Display chain:** the disc missions keep the neutral display chain the user approved (no mod post-processing) unless
  the user says otherwise; the modern effects carry their own light (dlights, firelight, emissive) rather than relying on
  bloom / haze. Heat shimmer and camera shake are base-game features - offer them here as their own A/B, default off.

### 6b. A/B and proof
- One key per mission family: `coop_flDiscFx 2|1` and `coop_eaDiscFx 2|1` (latched per map start; a bind + map restart, the
  honest "content" tier of section 5). The 5-minute test per mission walks the decoded effect list in order (jeep mine,
  crate breaks, burning car and smoke column, street flames, bombed house for Sealed Orders; the U-4902 sinking and the
  barrels for Anchor & Anvil; the village fires, blasts and distant fires for Dying Breath).
- Proof: same moment, three columns - xemu reference (`H:\hzm_work\ref_xemu`), disc conversion (1), modern (2) - so the
  user judges "same place, same time, same size, modern look". The user signs off per mission.
- Order: after the base-game Phase 2 toolkit exists (the modern art is shared), so this is Phase 4.

---

## 7. Texture sourcing and licences

- **Default: our own renders.** Blender (GPL; outputs are ours) Mantaflow smoke/fire + Cycles volume, and the fx_1025
  procedural tools (`procfire.py`, `procsmoke.py`, `flipbook.py`, `mk_fx.py` in `fx_1025/tools`). Render emission and
  density separately so the fireball's dark shell and bright core can be graded independently; render each smoke set
  with a top light so the billows have form even with flat sprite lighting.
- **CC0 only if a specific asset's CC0 deed is verified and recorded** in `CREDITS_FX.md` (source URL, deed, date). No
  "free for use" packs without a licence file, **no asset from any other game** (HLL included), no AI-generated texture
  from a model trained on unknown data without the user's OK.
- Disc missions: converter output only (section 6).
- QA every sheet for clipping, seams at loop wrap, square embers, tan/cyan cores, frame-0 brightness (fx_1025 found all
  of these) - memory `no-ai-slop-visual-qa`.

---

## 8. Risks

| risk | where | mitigation |
|---|---|---|
| intensity overshoot (third time) | gun smoke, impacts, columns | same counts/alpha for muzzle + impacts; user checkpoint per round; presets |
| pak-order loss again (D1 class) | every new tik | build-time winner check over the live stack |
| shader rule confusion (last wins, not first) | overrides | new names for new art; winner check covers shaders too |
| gl1 shader load failure | `nosoftparticles`, any new stage keyword | new keywords only as `qer_*`; gl1 boot + one map |
| look change of all sprites | sort fix, grid lighting gate | own cvar, default old until signed off |
| dlight starvation | fires vs blasts vs muzzle | priority, cap fx at 12, `noshadow` on fires |
| overdraw / fill rate on mid GPUs | wreck columns, smoke banks | caps, LOD, soft fade near camera, test at high resolution |
| VRAM / first-use hitch | 512 px 64-frame sets | DXT5 precompressed, precache spawns, 256 LOD set |
| capacity family | sprites, haze | raise nothing; if ever raised, build break in the same commit (T4) |
| disc footprint drift (modern effect bigger / longer than the original) | FL/EA | converter self-check (>1.5x fails), three-column proof vs xemu, `coop_flDiscFx` / `coop_eaDiscFx` A/B |
| parallel sessions | shared engine/mod trees | check mtimes, buglog ids, branch per phase; worktree sessions cannot edit mod/engine/buglog - stage fixers in `docs/proposals` |
| public servers block deploys | release | coordinate the release window |
| release strip deletes fx sources again (D0) | `split_tex.py`, release commits | exclude fx tiks from the strip; winner check in the release gate |
| binary set mismatch | new tik keywords, haze format, wind | ship cgame/gl2/game.dll together; prefer cvar/command/keyword designs (no API bump) |
| incremental cgame build silently falls back to the GOG DLL | engine phases | hash-check the deployed DLL and grep it for the new strings (bug-fx1025-5, prefs) |
| Omaha regression | VSS/linger retargets | Omaha excluded; tinted emitters keep mean brightness; m3l1b in perf runs |
| camera shake stacking / ADS aim divergence | shake | own offset, ADS scale, suppressed during earthquakes, default 0 |

---

## 9. Decisions for the user (before any code)

1. Approve the order (Phase 0 -> 1 -> 2, Phase 3 only if wanted)?
2. M18: should the thrown M18 show any smoke besides the yellow marker plume (D5)?
2b. Omaha (m3l1a/m3l1b): stay excluded from the new smoke art (default), or include?
3. Retail tiks that say `spritegridlighting` will become lit (D7) - OK after an A/B?
4. Camera shake by distance: wanted, and how strong (HLL is strong)?
5. Wreck columns lingering minutes: cap 3 full columns on high - enough?
6. ~~Disc missions: colour over life~~ - superseded 2026-11-24: modern visuals on the original's events (section 6).
7. A mid-range test machine available, or accept the high-resolution fill-rate proxy?

---

## 10. Vetting record (2026-11-24)

Two independent read-only reviews, each given the plan and the code/history, not the conclusions:

- **Engine / renderer lens** (eng-hotfix13661): confirmed the 64-frame cap, fixed sprite UVs, per-start-time draw split,
  first-come `MAX_DLIGHTS`, the `nosoftparticles` gl1 failure, the VSS sprite lever and D7. Corrected and folded in: sort key
  (squared, clamped, order-only; the two-bucket fix was wrong), D6 (needs `GL_SRC_ALPHA GL_ONE` + `alphaGen vertex`), shadow-view
  sprites starving the main view (D9, moved to Phase 0), `viewkick` is recoil and cannot be reused, explosion messages miss
  tik blasts, haze depth needs a 5th component, wind is a velocity target, `r_softParticles` is not a live-A/B precedent,
  `re.RemapShader` gives a live texture A/B, `MAX_DRAWIMAGES` (D10), binary coupling. Re-rated: random start, haze depth,
  camera shake low -> low-med; wind -> med; per-corner lighting -> med; sort -> med-high; atlas+crossfade -> high.
- **Project history lens** (buglog, TRAPS, DECISIONS, prefs, FEATURES, OPEN): found D0 (fx_1025 sources deleted by
  `1a4cddf50`, verified with `git show --stat`), widened D1 (split_tex root; shipped-set winner check; snow-grenade flash
  regression; D1 is a look change), D5 reframed (bugs 1847, 2201, 484), D7 vs bug-10524, Omaha exclusion (bugs 2201, 2529,
  3481, 3477), disc missions' neutral display chain and `HZMCONV_VERSION`, camera-shake stacking (bug-2204) and the rejected
  "too cinematic" variants, cvar archive trap (T7, bug-1200), presets folded into the existing row (bug-3484), fixes-pak
  fragility (bugs 11370, 11328, 4149, 1892, 1893), `corona_util` excluded (bug-2946), shader-priority wording (bug-2485),
  engine baseline `rel-1.10.38-engine`, records missing for fx_1025, testing discipline.

Open after vetting (needs a measurement, not more reading): which `grenexp_base` actually loads (D1), what darkened
bug-10524's snow cards (D7), whether FL `flupscale.py` already upscales `textures/fl/<level>/pfx`, and the real
`IMAGECAP` headroom on e3l4 / t2l4.

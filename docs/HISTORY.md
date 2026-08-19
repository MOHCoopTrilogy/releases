# HISTORY — condensed chronology

One line per item. Status codes: `V` verified · `U` unverified · `D` code-disabled · `R` reverted ·
`O` open · `P` planned. Full detail in [FEATURES.md](FEATURES.md); open items in [OPEN.md](OPEN.md).

**⚠️ Coverage boundaries.** `.wolf/buglog.json` — the only structured record — begins **2026-06-26**.
Its first id is `bug-535`; **bugs 1–534 are not in the file**, and ~28 ids cited in source comments
(including bug-237, bug-239, bug-241) have no entry at all. The mod's own git history is real (1,393
commits back to 2020-01-08) but commits are enormous snapshot-shaped batches, so it cannot be
bisected usefully. **"Since day one" in practice means since 2026-06-21.** Dates before that are
lineage, not record.

---

## Before the buglog (2020-01 -> 2026-06-20)

Moved to **[archive/history-pre-2026-06-26.md](archive/history-pre-2026-06-26.md)** on
2026-08-17 to keep this file under budget: pre-history, the current era's opening, and the
pre-buglog months.

## 2026-06-26 → 06-30 — the buglog begins

| When | What |
|---|---|
| 06-26 | **`.wolf/buglog.json` starts** (first id `bug-535`). |
| 06-26 | `V` Coop reward items MP fixes: per-owner HUD (`ihuddraw_*` targets ONE client), drop-on-death re-pickup, radio to all players. ⭐ `loopsound … levelwide` is the only PVS-proof MP audio. |
| 06-26 | `U` m1l3b jeep multi-passenger seating **re-enabled** — it had been fully written then disabled with early `end`s. |
| 06-26 | `U` Sky-trace false-indoors fix — an up-trace **hits the skybox brush**, silently disabling the binoc airstrike AND the officer's Stuka/artillery waves. |
| 06-26 | `U` ~1300 "unknown animation thompson_*" errors fixed by moving `$include human_thompson.tik` into the unconditional block of `new_generic_human.tik`. |
| 06-27 | `U` Enemy count-scaling (per-spawn replication by player count). |
| 06-27 | `U` MG42 / mounted turret overheat, players and AI. |
| 06-27 | `U` Deployable ammo box. |
| 06-27 | `U` Officer German idle VO + alarm variety + dot-product heal-retreat. |
| 06-27 | `U` Reinforcement natural behaviour — spread radius **capped** (was uncapped to ~1240u = "battalions spawned inside walls"). |
| 06-27 | `V` `s_sfxduck` + m3l1a Omaha ramp-drop cinematic. ⭐ Uncovered that server-stuffed SETs of `CVAR_ARCHIVE` cvars are dropped unless whitelisted. |
| 06-27 | `U` Officer/paradrop bombing-run banked diving arc, auto-scaled from `$world.farplane`. |
| 06-27 | `V` `LoadTGA` hard-crash softened. ⭐ The first attempt patched the **wrong file** — there are five TGA parsers in-tree. |
| 06-28 | `V` Corpse persistence + despawn; `MAX_BODYQUEUE` 5→128; `EV_DeathSinkStart` gated to SP. |
| 06-28 | `U` Corpse blast impulse (`g_corpseImpulse`). Same research verdict: **ragdoll not feasible**. |
| 06-28 | `U` Weapon weight / view-model lag Phase 1. |
| 06-28 | gl2 migration **paused and reverted** (later rescoped — see 07-24). |
| 06-29 | `U` Sprint / walk / stamina three-speed movement. |
| 06-29 | `U` ADS on its own usercmd bit (**bit 13, the last free one**) + bash restored. |
| 06-29 | `U` Tinnitus (script layer). |
| 06-29 | `U` Wounded-AI blood trails. |
| 06-29 | `U` Suppression screen FX. |
| 06-29 | `U` Lingering gun smoke. |
| 06-29 | `O` **bug-165 — reload camera dip never visible.** Signal chain fully source-verified; still open, oldest live item. |
| 06-30 | `V` `md5_2_skX` model converter ported and round-trip validated. ⚠️ Raw output is engine-lethal without `skd_add_collapse.py`. |

---

## 2026-07-01 → 07-10

| When | What |
|---|---|
| 07-01 | `V` t2l2 halftrack + truck coop seating finalised. ⭐ **Riders are now SOLID** — supersedes the old notsolid rule. Root cause of judder: the rider's view was interpolated independently of the vehicle. |
| 07-02 | `U` Dynamic weather v2 — the custom v1 renderer **retired** in favour of driving the native SP system. |
| 07-03 | Weather never-fired bug fixed (theme read NIL because maps set it on the line *after* `main`). |
| 07-04 | `V` Full audio mixer (Master/Music/SFX/Ambience/Dialogue) + `s_sfxvolume`. |
| 07-04 | `U` Six-feature audio batch: reverb enabled, HRTF, occlusion low-pass, distance gun tails, CAS sharpen, corpse impulse. ⭐ **The auto-reverb driver was already built in the fork and forgotten.** |
| 07-04 | `V` Fresh recorded gun audio + 24 footstep surfaces + 44 impacts; distance model `INVERSE` → `LINEAR_DISTANCE_CLAMPED`. |
| 07-04 | `R` Warzone explosion variants and VFA wood footsteps rejected in play and backed out; artillery beds kept. |
| 07-04 | `U` Destroyable-objective failsafe (throbbox `BlowUp`). |
| 07-05 | **v1.1.33 release batch** — spawn protection, DBNO corpse-revive, sniper 3P parallax, stuka/arty warning, What's New pipeline. |
| 07-05 | **`CLAUDE.md` last updated.** Stale from here on. |
| 07-06 | `V` HUD fade (v1.1.36) — four live-report bugs fixed; compass exempt by user choice. |
| 07-06 | `U` Player emotes (salute / at-ease / stretch) via `forcelegsstate`. |
| 07-06 | `U` Staged 3P shoulder ADS. ⭐ `CG_AdsForceFirstPerson` is the single decider. |
| 07-06 | `U` m1l3a jeep seating ported from m1l3b. |
| 07-06 | Blender sprint carry-pose edit **paused by the user** mid-edit at arm-bone selection. |
| 07-07 | `U` XP / rank system Phase 1 built + deployed (~470 lines, 13 ranks, emblems). |
| 07-07 | `U` 3P free cam v2 (auto-face). ⭐ Zero-ABI client→cgame bridge via `cgi.get_camera_offset()`. |
| 07-07 | `U` Officer reinforcement player-count scaling. |
| 07-07 | `U` NAT hole-punch **phase 1 committed and verified end-to-end locally** (daemon + engine hooks). |
| 07-08 | `U` Coop Lobby #1 full build. Revert tag `checkpoint-lobby-working-20260708` in both repos. |
| 07-09 | `U` Exact-ammo respawn (new Sentient `getammo`/`setammo` events). |
| 07-09 | `U` `MAX_SOUNDS` 1024→1280; `MAX_GAMESTATE_CHARS` 41952→98304. |
| 07-09 | `O` **bug-431 — DBNO crawl plays opposite to movement.** No follow-up since. |
| 07-10 | `U` Live helmet switcher. ⭐ Placement derived by copying the gear helmet: `us_helmet.skd`'s 147 verts are single-weighted to bone 8, so its weight offsets **are** exact head-local coords. |
| 07-10 | `U` m3l1b cut FLAK 88 objective restored (the devs' own "TEMP TEMP TEMP PREMATURE POOPHEAD ENDING"). |

---

## 2026-07-11 → 07-20

| When | What |
|---|---|
| 07-11 | `U` e1l4 alarm can now be silenced (v1.1.45). |
| 07-11 | Feel/engine/challenges batch — challenge total reaches 185. |
| 07-12 | `U` ARMORY loadout picker Phase 1 (69 guns). ⭐ Required an **engine** fix — `FindResponder` v2. |
| 07-12 | `V` Retail objective audit: ~630 scripts, **no P0s**; 2 P1 strand risks on t2l1. Fixed `maps/m2l2b.scr:87` calling a label that never existed. |
| 07-12 | **Objectives script-panel RETIRED** — the user saw both displays at once ("obnoxious"). |
| 07-12 | `U` King Tiger 2nd-player MG gunner slot prototype. |
| 07-12 | `U` Frontline PS3 extraction: 339 cues / 175 ambience beds. ⭐ `main.musx` → chunk-walk split → rename `.asf` → vgmstream. |
| 07-13 | `V` Helmet pop-off mechanic fixed — **not cut content**; pops were firing all along but invisible. |
| 07-13 | `U` Cut-content dig + dialogue restoration wave 1 (~15 lines / 5 maps). ⭐ **The MP hitmarker is disabled at retail by a `null.wav` alias.** |
| 07-13 | `P` Bipod design research — BUILD weapon-stance supported aim, REJECT turret swap. |
| 07-13 | **Deployables skill tree REJECTED by the user.** |
| 07-16 | `U` Weapon unlock progression + cosmetic unlocks built + deployed. |
| 07-17 | `U` Build-mode geometry (14 primitives) + blueprint system. |
| 07-17 | `U`→**ON** Reactive Difficulty Director built and wired (`director.scr`) — recorded as "PLANNED, DO NOT BUILD," enabled by default in `autoexec.cfg:381`. |
| 07-17 | `V` Vehicle-turret invisible-to-1P-driver fixed (bug-647, game.dll only). |
| 07-17 | `U` ARMORY V3 rebuild. |
| 07-18 | `U` All four gore tiers built + deployed (`tr_gore.c`, 836 lines). |
| 07-18 | `R` **Decapitation v1 shipped → "the AI went all glitchy" → pulled** (bug-861). |
| 07-18 | `U` Corpse gurgle + wet blood-leak loop. ⭐ bug-822 root cause: `Actor::Remove` calls `Unregister(STRING_DEATH)`, so `self delete` on a live scenic actor fires the parked `waittill death`. |
| 07-18 | `U` Blast tinnitus in the engine (`RadiusDamage` stamps `coop_blastPing`). |
| 07-18 | `V` Weapons-on-back shipped — **EA shipped the system and disabled it with comment slashes**; 79 retail TIKs had commented `holstertag` lines. |
| 07-18 | `V` xw pack full shader audit: **pack is CLEAN** (9 dead paths, all unreferenced). Do not re-audit. |
| 07-18 | `U` Armory stufftext quote-truncation fixed, rcon-verified (bug-758). |
| 07-18 | **v1.2.0 release notes finalised — and never published.** The line continued 1.1.49 → 1.1.55. |
| 07-19 | `R` **Decapitation reverted from SOURCE** during the `MAX_MODELS` three-binary rebuild (bug-892), so a rebuild cannot reintroduce it. |
| 07-19 | `V` `MAX_MODELS` 1024→2048 (at 1024 full, further enemies register as model index 0 = **invisible**). ⚠️ `q_shared.h:1680` credits this to bug-866; it is bug-892. |
| 07-19 | WinDbg `cdb` installed; `game.pdb` now ships next to `game.dll` so dumps resolve exact lines. |
| 07-20 | `V` **The entity-pool saga resolves.** `set maxentities 2048` had shipped for years against a 10-bit wire — it added no entities, it **disabled `AllocEdict`'s overflow guard**, so the allocator handed out slot 1022 (WORLD). One lie = a weekend of use-after-free minidumps. Fixed by `GENTITYNUM_BITS` 10→11 + ~25 guards + `g_droppeditemlife 60`. |
| 07-20 | `V` e1l2 invisible walls solved — three species (33 solid landmines → `CONTENTS_WEAPONCLIP`; artillery TIK setsize tightened; a 225-segment retail playerclip web). |
| 07-20 | `R` Regional clip-strip **zones retired** — wrong-grained, let players out of bounds. Replaced by `cmpatch/<map>.txt` brush surgery. ⭐ **The server loads `<name>_sml.bsp`.** |
| 07-20 | `V` `MAX_ENTITIES_IN_SNAPSHOT` + `MAX_PARSE_ENTITIES` raised (bug-934). |

---

## 2026-07-21 → 07-29

| When | What |
|---|---|
| 07-21 | **`openmohaa.exe` deployed to the GOG root — and never updated since.** Everything after this date is source-only for players. |
| 07-21 | `O` **bug-1001 — build-mode blueprints render as featureless squares.** Zero `BUILD_BP_PLACE` lines in the session log. |
| 07-21 | `O` bug-1172 — **sandbox engine constants were pushed into the real install** by routine `build.ps1` runs. Emergency revert. |
| 07-21 | Game-accurate structures: BSP→blueprint extraction + shape kit (`bpv1`). |
| 07-22 | `V` **Addon-spawner restore — the strongest measured win in the project.** `addon_*` markers carry their model in `$ai_model`, not `.model`, so `spawner_create` recorded NIL and the engine spawned `models/nil.tik` in a loop. Storm ~7,000+ → 25; **~550 German AI restored trilogy-wide**; t2l1 1960→0, t2l2 3045→0, t1l3 1470→0. |
| 07-22 | `V` `$player`-array gag overrides (t2l3 14,501→0; t3l1 4766→0; t2l4_captain 20 sites). |
| 07-23 | `V` Autonomous combat-verification rig — `coop_botInput 1` injects the host usercmd and **fires real bullets** (a script `damage` event does not acquire a target). ⭐ Its headline catch: the ET3 jink **silently never fires**. |
| 07-23 | `D` AI dynamics step 1 (global personality) + step 2 (engine juke/hide timers) — measured, but gated on an **unseeded** cvar. |
| 07-23 | **Engine HEAD `819a6e93`. Everything after this is uncommitted.** |
| 07-23 | Mod HEAD `f10ac19` (v1.1.54). Everything after this is uncommitted. |
| 07-24 | **`game.dll` deployed — and never updated since.** |
| 07-24 | gl2 migration **rescoped** onto a fully isolated install at `G:\mohaa-gl2`. Empirically gl2 is healthy: boots, renders, 0 crashes, 0 real GLSL failures. |
| 07-24 | `D` AI squad brain (`aisquad.scr`) built — gate cvar unseeded. |
| 07-26 | **Manifest 1.1.55** — the current release. `openmohaa.exe` and `cgame.dll` still point at v1.1.51. |
| 07-27 | ⚠️ **A post-write hook clobbered `buglog.json`** with its own schema. 523 entries rebuilt from ~1.2 GB of transcripts. All 8 `.bak` snapshots later diffed: **zero historical loss**. |
| 07-27 | m3l3 groundfix pak built — **never shipped**, and built 19 minutes *after* the screenshot later cited as "the fix didn't work." |
| 07-28 | `V` gl2 batch: gun-over-menus (depth **rejection**, not draw order), settings-apply crash, renderer-zone leak (+53 MB/apply), frozen 2D shader clock, HZM grade never executing, invisible actors (**two independent mechanisms**). |
| 07-28 | `U` `MAX_SOUNDS` 1280→1600 + `MAX_RELIABLE_COMMANDS` 512→1024 + `MAX_CONFIGSTRINGS` 4096→8192, with a compile-time `#error` guard. |
| 07-28 | `V` `MAX_SNAPSHOT_ENTITIES` 1024→2048 — **bug-934's missed 4th member, found 8 days later**, silently discarding every entity past the 1024th with no log line. A warning was added alongside the fix. |
| 07-28 | `U` Headshot kill-cue hook **moved** `BulletAttack` → `ArmorDamage`; sandbox-verified 20/20. |
| 07-28 | `U` `coop_unsponge` bullet-sponge reconciliation sweep (bug-1212). |
| 07-28 | `R` **The +180 roll on `maps/m1l1.scr` — applied (bug-1173), reverted the same evening (bug-1184)** as an unverified guess. An in-code revert comment at line 1683 names the bug. **This is the doc set's commissioning example.** |
| 07-28 | `O` bug-1213 — m1l1 mangled actors, **six investigations, no guess shipped**; a gated `^~^~^ POSECHK` diagnostic delivered instead. |
| 07-28 | `V` `MAX_SKELMORPH` 12800→131072 (silent OOB write). |
| 07-28 | `V` `cgame.dll` + `renderer_opengl1.dll` deployed (22:57). **`openmohaa.exe` was not.** |
| 07-29 01:07–01:41 | Current binaries built in `.cmake` — **exe, game.dll and gl2 never deployed to the real install.** |
| 07-29 | `O` **Three S0 regressions found by a brand-new harness**, all correctly marked NOT FIXED: bug-1218 (m3l2 missing `level_end_trigger` label), bug-1219 (`SV_FindIndex overflow max=1280` — the deploy gap), bug-1220 (e2l2 NULL-listener ×12). |
| 07-29 | `U` Officer heal budget `coop_officerMaxHeals` (bug-1215). |
| 07-29 | The regression harness at `_research/regression/` becomes **the project's only working automated verification.** |
| 07-29 | This doc set written. |

---

## Release line

| Version | Note |
|---|---|
| 1.1.33 (07-05) | Spawn protection, DBNO corpse-revive, sniper 3P parallax, What's New pipeline |
| 1.1.36 (07-06) | HUD fade batch |
| 1.1.39 | DBNO cinematic anims, 3P free cam |
| 1.1.40 | Cover system (EXPERIMENTAL) |
| 1.1.45 (07-11) | e1l4 alarm |
| 1.1.48 | Weapons-on-back, cut dialogue, battle chatter, 150 death cries, 7 ambience beds, helmet switcher, armory, lobby — **all in one commit** |
| 1.1.49 (07-18) | Shipped. `zzzzz_xw_weapons.pk3` sourced from here. |
| **1.2.0** | **Notes finalised 07-18, NEVER PUBLISHED.** The `_final.md` file is unmarked and reads as authoritative — a trap. |
| 1.1.50 | `renderer_opengl1.dll` still sourced from here in the current manifest |
| 1.1.51 (07-21) | `openmohaa.exe`, `cgame.dll`, `renderer_opengl2.dll` still sourced from here |
| 1.1.52 – 1.1.54 | |
| **1.1.55** (07-26) | **Current.** `game.dll` from here; everything else older. |

---

## What the timeline shows

1. **Velocity is extremely high and verification is not.** Roughly 75 systems in ~5 weeks, of which
   ~15 have a recorded confirmation. The backlog is not features — it is playtests.
2. **The most expensive bugs were all silent.** The entity-pool stomp, the grenade veto, the grade
   uniform, the `Hunk_Clear` static, the snapshot discard: none of them logged anything. The project's
   biggest wins came from *proving execution*, not from reading code.
3. **The deploy pipeline is the current bottleneck.** The last full engine deploy was 07-21. Eight
   days of engine work — including three protocol constants — sits built but undeployed, and a live
   log (bug-1219) is already reporting the old limit.
4. **Two records systems degraded predictably**: the append-only ones (`memory.md`, `cerebrum.md`)
   became unreadable; the structured one (`buglog.json`) kept working. **Structure and a lookup key
   are the whole difference.**

---

## 2026-08-02 — PDF defect sweep, the limp, and two gl2 rendering bugs

46 buglog entries (bug-1251 → 1296). The day's shape: **most of the damage was silent-veto**, and the
runtime log — not static audit — found nearly all of it.

- **RC1 (bug-1251)** detonated every watched demolition charge ~0.3 s into map load across **16 sites**
  (`isalive` is `health > 0`, and all watched targets are health-less). Two soft locks, plus a
  downstream corruption of e3l2's POW chain that had been filed as its own bug.
- **`pain.scr` (bug-1275)**: `coop_painThread` was a boolean latch nothing ever cleared, so the coop
  pain handler ran **once per actor, ever** — every enemy a permanent bullet sponge. 15 log occurrences
  → 0 after the fix.
- **The armory loadout was being taken back by the maps themselves** (bug-1279). Maps run
  `replace.scr::takeAll` + SP-kit `item` gives from *behind* `waitForPlayer`, i.e. after
  `spawnInventory` already handed out the player's picks. Affected **11 maps**, not one.
- **Low-health limp shipped** (bug-1291/1292) — see FEATURES.md.
- **Two gl2 rendering bugs, both gl1-parity gaps**: sky faces were DXT1-compressed where gl1 loads them
  uncompressed (bug-1295); and the fog pass's sky exemption used a depth epsilon of `1e-5`, which —
  depth being nonlinear — exempted everything past **88–98% of zFar**, a slab up to 5500 units deep of
  ordinary geometry (bug-1296). That one epsilon explained *both* reported symptoms at once: unfogged
  bright distant geometry at `r_globalFogSky 0`, buried geometry at `1`.

**Three lessons worth carrying:**

1. **A failed `waittill` does not abort — it just does not wait.** Four scripts on e2l1 therefore ran
   before the map's entities existed, costing the map all its light styles and fire effects
   (bug-1294). Will recur on every remaining map; the log is the oracle, not a bulk sweep.
2. **Agreement between reviewers is not corroboration when they share a source.** A multi-agent audit
   plus two independent critique lenses all confirmed a vignette bug that did not exist — all three had
   inherited one unchecked premise (bug-1290). The "fix" would have been a real regression.
3. **The expensive fix was refuted by measurement.** A stencil sky-mask was designed and about to be
   built; resolving all 69 shaders in e2l1's BSP showed every tree already writes depth, so the premise
   was false and the actual fix was one epsilon.
- 2026-08-03: FORWARD PER-FRAGMENT GLOBAL FOG shipped and playtest-confirmed (bug-1304, r_globalFogForward 1 default) - ends the gl2 fog saga (white distant objects, erased effects, colour-space mismatch). Same batch: scripted suppression hook (bug-1305), e2l1 Paks-vs-vehicles fixes (bug-1307), glider blood skins (bug-1303/1306), restored cut pilot line + shot-up audio + windscreen + position-driven flak (bug-1301..1303).
- 2026-08-03: engine gore rules (user standing rule): coop_gorePermanent 1 = blood never wiped (monotonic tier, gore_reset no longer clears paint); coop_corpseShootable 1 = corpses take post-death fire (flat WEAPONCLIP bbox in BecomeCorpse). Plus e2l1 batch: officer re-anchor (bug-1319), crash-hang dizziness (bug-1322), AB41 death failsafe, truck-unload solidity failsafe.
- 2026-08-03 (late): VEHZOMBIE rescue live-verified (truck+AB41 die now); rails-red = retail aagun4 plant marker (not a bug); pilot wound on both temples; glider interior + jeep 4x ESRGAN upscale (5 textures); challenge #180 'Static Line Savior' (save McMartin on the pole, e2l1) + SR menu rebaked.
- 2026-08-04: PINNED CHALLENGES shipped - five per player under the secondary objectives, click-to-pin from the Service Record, per-player storage by cid (bug-1362/1364). Same batch: e3l4 supply-truck soft-lock failsafe (bug-1361, the Holdout test map), helmet/hat overlap root-caused to model-reload wiping surface flags (bug-1360).
- 2026-08-05: coverage sweep shipped (engine covtrace + maptest Phase 3 covwalk + diff reporter); layer-1 static scan found 170 dead alias refs on 43 trilogy maps
- 2026-08-07: V m1l1 loading screen rebuilt as a single BSP-rendered "case file" composite (recon photo + retypeset OSS letter + 3 stock briefing-slide photos, pinned on a corkboard); single 2048x2048 POT texture replaces the old two-tile TGA pair, new explicit `coop_load_m1l1` shader (force32bit) closes the one real gap vs. vanilla UI shaders
- 2026-08-07: U XP rebalance (downed fight/officer kill/assist/vehicle-destroy retuned, attacker-only vehicle-kill via new `coop_vehKillerNum` engine plumbing, air-strike-kill + Searchlight Disabled bonuses added) + Service Record reward-name overlap fix (curated 180+-entry `REWARD_NAMES` table, Armory-matched weapon names) + 11 named-NPC trilogy skins shipped as real armory unlocks (bug-1521)
- 2026-08-07 (later): pinned-challenge popup restricted to pins only (bug-1522) + pin checkbox made clickable + "N/5 Pinned" summary added (bug-1523, required an openmohaa.exe rebuild) + native MP-options skin selector redirected to the Armory instead of writing dm_playermodel directly (bug-1524)
- 2026-08-07 (even later): Service Record description-truncation fix (shrink-to-fit instead of ellipsis, bug-1525) + helmet-nodraw whole-roster audit (4 real overlap gaps fixed, bug-1526) + Armory model-viewer unlock-caption overlap fixed with a backing panel (bug-1527) + MEDALS & BADGES shipped: 12 category-derived meta-achievements, new Service Record tab, procedural placeholder art (bug-1528)
- 2026-08-07 (v1.2.2 release): U Service Record reorganized - 23 category tabs collapsed to 9 with a wraparound pager (the 5 weapon categories share one WEAPONS tab), per-challenge reward moved out of the baked row onto a `hovershader` reveal, several challenges recategorized. Same release: 13 new helmets/headgear each gated on a thematic challenge or rank, all 135 armory skins made bare-headed so a chosen helmet fits, helmet roster renumbered contiguous 1..135. Frost-on-lens REMOVED from snow (bug-1547, publisher deleted in cgame so it is inert regardless of a stale archived `r_ppFrost`). m1l3c fog profile; Grillo OSS-uniform gore on m2l1; fog-editor save fixed (`coop_fog_mapName` parsed a nullable `level.script`).
- 2026-08-07: R Service Record completion checkmark REVERTED after six attempts (bug-1546). The pin box is back to the v1.2.1 widget pair (`pinbox` + `pinmk` on `coop_uiP`); both the `coop_uiD` tick and the `coop_uiC` shader-path box are gone. Root cause of the whole saga: `CL_SyncSR_f` (`coop_srsync`) never executes from the disconnected menu, so five successive fixes living inside it could not take effect - see [TRAPS.md T3](TRAPS.md#t3). Standing rule from this: do not replace a working UI widget with an unverified rewrite.
- 2026-08-07 (v1.2.201 hotfix): V SFX-slider routing fixed (bug-1556) - CHAN_LOCAL/CHAN_LOCAL_SOUND were treated as menu chrome and never got the `s_sfxvolume` multiplier, so the challenge typewriter, injured cue, `snd_gasp` sprint breathing and `coop_headshot` stayed at unity while the rest of the world scaled; with the user's slider at 2.0 that read as "quieter even with the dial turned up". Diagnosed live over rcon. Same release: per-shot `COOP_BINOC_CHECK` print removed from `game.dll` (it shipped to players in 1.2.2, one console line per bullet) and the stock per-change music `DPrintf` removed so `developer 1` stays usable - it has to stay on, because build mode reports placements through `println`, which developer gates.
- 2026-08-07: V m3l1b full coop pass - it had NO spawn coverage end to end. Start spawns + a checkpoint on the map's own `level.clear_bunker >= 6` gate; 27-strong rear garrison spawning when the FLAK 88 objective opens; 34 build-mode props baked in. Three root causes closed on the restored FLAK objective: `$88mm_weapon1/2` are class **Animate** not TurretGun so `startFiring`/`setAimTarget` had never worked (bug-1553, driven by the model's own `fire_scripted` anim now); no flak FIRE alias listed `m3l1b` in its `maps` spec so nothing was audible either (bug-1548); and `bomb_thinker` hardcodes its own `bomb_tick_time`/`bomb_set_time` over ours, giving a silent 45s fuse that read as a dud (bug-1549 - now a 15s visible stopwatch and a one-press plant).
- 2026-08-07: O Build mode is a CAPTURE tool, not persistence - it writes `coop_mod/save/build_<map>.dat` and nothing loads it at runtime, so placements are lost on map reload until baked into a script (bug-1554). Not communicated to the user before they placed 34 objects.
- 2026-08-08: U helmet unlock gate made wear-time, not just pick-time (bug-1578) - `helmet_apply` now range-checks and re-validates the stored index and falls back to a DETERMINISTIC index 1, and a new `helmet_lockNotice` says "locked" once per distinct item instead of on every archived `,hn` resend (every join, every armory close). Same batch: m6l1c conversation-guard pass (bug-1579) - the `waittill animdone` outside its guard in `sciencesayto` was a guaranteed strander that would have taken the whole science-chat sequence and its actor release with it; 7 of 196 sweep sites done, 189 left. Two manned MG42 nests baked into `maps/m3l2.scr` from the 08-08 build-mode capture. **None of it is deployed** - the game was running, which `build.ps1` refuses.
- 2026-08-08 (later): U crewed AA emplacements - all three placeable AA guns get an animated gunner; the two mannable ones hand off to a player on mount and take the crew back on dismount. Two verified mechanisms: `QueryTurretSlotEntity 0` addresses a runtime-`spawnturret` cannon (retail does the same at e2l1 `FlakGunSetup`), and the `flak88_driver`/`aagun_driver` poses are in the SHARED human anim set. Same session: 4 manned MG42 nests on t2l1, `max_health` fix in the t2l1 tank gag (268 errors/session), officer radio NIL guard.
- 2026-08-08 (v1.2.3): U allied squads made survivable - health scales with player count and they go DOWN instead of dying, with the player's own DBNO animation, revivable by proximity at no medkit cost (allysquad.scr). That made it safe to narrow the engine blast shield to an opt-in flag (bug-1586), so mortars can finally wound and gib allies - the damage was being dropped before it, not the gore. Same release: new-objective toast, ambient barrage, crewed AA, t2l1 'keep the squad alive' objective, 29 dev prints gated, MAX_CVARS 4096->8192 (bug-1582).
- **2026-08-10** m2l2a stealth: master plan v2 vetted in 3 adversarial rounds (40 agents, ~270 findings). **Phase A shipped** - bug-1631 freeze arm deleted (VERIFIED: the papers guard now accepts and stays animated), all six disguise anim gates made per-target and latch-free (they had been unconditionally true - `thread` in a boolean returns a handle), one aggro rule via `attackentity` instead of the one-way `attackplayer` latch, scene-actor wreckers exempted after A3 instrumentation measured `coop_apply_personality` proning the card man, a Naxos watcher and an alarm runner. Full mission, zero Script Errors.
- **2026-08-10** **v1.2.5 released** (github + discord + baked field report). Phase A + B0 + B1 of the m2l2a plan: papers-checker freeze, six always-true disguise gates, latch-free aggro, scene-actor protection, MG42 per-map anim gating, engine null-deref crash fix, collision latch judged against the real bumper. Also the first release where auto-cover actually ships with its engine half (v1.2.4 shipped the toggle alone, bug-1635). Pre-publish gate added: staged game.dll sha256-matched against the built and live copies, and string-checked for the features it claims.
- **2026-08-10** - Player limping restored (bug-1669). Script `getcvar` is `Cvar_Get(name,"",0)`, so the first script read of an unregistered cvar CREATES it empty and permanently defeats the engine's own default; `coop_limpWarn` did exactly that to `coop_limp` at player setup. Fixed by pre-registering the engine-owned `coop_*` cvars in `G_InitGame`. Same fix silently restored `coop_tinnitusBlast` and `coop_goreDripCorpseTime`.
- **2026-08-10** - **Phase C: the player-initiated contain on m2l2a** (bugs 1682-1691). Nine defects in one session, each found by a probe not a hypothesis: `disable_ai` is only `enableEnemy = 0`, so the stagger never stunned anyone (damage is the only lever on an actor's think); the bust pistol had no ammo; it lost a RAISE RACE to the loadout's own pickups; a THIRD papers path ate the trigger; drawing any weapon clears `m_bIsDisguised`, so the room aggroed and the mechanic was unwinnable by construction; `coop_isProtectedActor` is true for the whole m2l2a cast, so reusing it for 'who notices a corpse' vetoed everybody; **`coop_stealthArmOnHurt` has no caller anywhere and has never run** - two earlier bugs reasoned about it as live; every proximity test was a 3D sphere reaching through floors. Two of my own diagnoses were wrong and were retracted in place rather than left as folklore.

- 2026-08-17 - TRAPS T11: the bug-1173/1184 commissioning example retired to here. bug-1173 recorded a `+180` roll correction on `maps/m1l1.scr` as applied; bug-1184, hours later, reverted it. Both entries correct, both present - but the record only agreed with the code if read to the END, and a later session read bug-1173 and stopped. `docs/generated/FIX_INDEX.md` now exists and both protocol files mandate it, so the rule survives in T11 without the story.

- 2026-08-19 - **MV wave 3 shipped**: 31 credited texture variants (Hobbs / GUANShire / DirtyHarry, DS-Servers archive) across 12 existing + 6 new host guns (kar98/p38/bazooka/mosin/svt/L42A1); fid ceiling 13->19; Leon excluded on explicit no-redistribute readmes (contact-first, SKIN_CREDITS.md). ui_wiring_audit caught wire_mv2's template stomping the loadout deep-fix wave (bug-1947) - the generator's loadout_finish rewrite is retired; the file is maintained in place.
- 2026-08-19 - **Leon wave shipped** (user decision: archive-era content = credit + remove-on-request, superseding Leon/East contact-first): 21 variants incl. the 16-gun Team Tactics pack; armory now 77 credited variants across 23 hosts. Six Leon DS singles = lost media (0-byte store node).
- 2026-08-19 (evening) - **Live-playtest mega-wave shipped**: surrender conversion (hold USE recruits a surrendered german), grenade kick, vault/mantle, gore package (corpse impulse, explosion chunks, decap re-add per bug-866 safe pattern, headshot brain chunks + eyeball dangle), 10s shellshock envelope, reload camera sway, colt thump A, 10s prone dwell, m3l3 church-clear re-gate, vehicle AI gunner tuning trio, weapon.scr variant normalization, TIKI_Error un-gated (bugs 1941-1953).

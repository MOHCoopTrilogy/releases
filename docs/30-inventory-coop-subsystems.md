# `coop_mod/` subsystem inventory

Every `.scr` under `hzm-mohaa-coop-mod/coop_mod/` as it exists on disk. `labels` is a count of
column-0 script entry points (a rough proxy for API surface). Description is the first real
comment line in the file - verbatim, not paraphrased. Blank means the file has no header comment.

| file | bytes | lines | labels | header comment (verbatim) |
|---|---:|---:|---:|---|
| `admin.scr` | 3507 | 87 | 5 | [204] chrissstrahl - All Admin Menu Commands would go in here, see developer.scr for examples |
| `ads.scr` | 1722 | 39 | 1 | HZM coop - AIM DOWN SIGHTS support (per-player), dedicated ADS button (RMB by default). |
| `ads_dbg.scr` | 518 | 11 | 1 | HZM coop - ADS diagnostic. Called from the AIM state's entrycommands in |
| `aibehav.scr` | 5885 | 120 | 1 | aibehav.scr - HZM coop ENEMY-BEHAVIOR TRACKER (2026-07-23) |
| `aicombat.scr` | 5119 | 119 | 3 | aicombat.scr - HZM coop AUTOMATED COMBAT DRIVER (2026-07-23) |
| `aihandler.scr` | 60328 | 1110 | 32 | [200] Smithy - this script is called every time an actor enters the world by exec it on their tiki (via shared new_generic_human.tik) |
| `aimaneuver.scr` | 7878 | 158 | 2 | aimaneuver.scr - HZM coop COMBAT MANEUVER layer (2026-07-23) |
| `aisquad.scr` | 7692 | 169 | 1 | aisquad.scr - HZM coop SQUAD BRAIN (2026-07-24) |
| `aivoice.scr` | 14892 | 359 | 9 | HZM coop - SITUATIONAL AI VOICE  (user report 2026-07-28: "make the dialogue more logical, |
| `ambience.scr` | 11481 | 233 | 5 | HZM coop - AMBIENCE BEDS + COMBAT MIXING (script-only; modeled on weather.scr::coop_weather_sound). |
| `ammobox.scr` | 10335 | 243 | 4 | HZM coop - player-deployable AMMO BOX. |
| `blueprint.scr` | 22944 | 561 | 17 | HZM coop - BLUEPRINT / PLAYER STRUCTURES (build-mode extension) |
| `bt_playerTank.scr` | 1624 | 36 | 1 | chrissstrahl - Exit Tank Script for BT-Coop |
| `buildmode.scr` | 37757 | 723 | 11 | HZM Coop - BUILD MODE (dev tool). Full docs: _research/build_mode.md |
| `buildmode_actors.scr` | 22310 | 411 | 4 | HZM Coop - BUILD MODE : ALLIED ACTORS + ANIMATION catalog (DATA + ghost animator). |
| `buildmode_catalog.scr` | 142428 | 2098 | 1 | HZM Coop - BUILD MODE model catalog (DATA ONLY). Generated from main/mainta/maintt Pak*.pk3 |
| `buildmode_sounds.scr` | 18954 | 369 | 10 | HZM Coop - BUILD MODE : placeable SOUND EMITTERS (catalog + SOUND-mode control bus). |
| `bunker.scr` | 13010 | 306 | 9 | HZM coop - COMPOSED STRUCTURES v2 (build-mode geometry construction kit) |
| `butler.scr` | 19305 | 498 | 15 | created by chrissstrahl on 2019.09.12 |
| `cannonThink.scr` | 4439 | 142 | 1 | This kind of function is used over and over again, so have it isolated for erference that it can be reused |
| `challenges.scr` | 115064 | 1929 | 48 | [303] HZM CHALLENGES / ACHIEVEMENTS SYSTEM - Phase 1 (tracking + persistence + unlocks + HUD toast + review) |
| `coop_placements.scr` | 32871 | 1021 | 3 | HZM coop - BAKED BUILD-MODE PLACEMENTS (generated from build_<map>.dat). |
| `coop_selftest.scr` | 13524 | 320 | 8 | coop_selftest.scr - HZM dev automated self-tests (2026-07-23) |
| `coop_selftest_dbno.scr` | 15585 | 424 | 9 | coop_selftest_dbno.scr - HZM dev automated DBNO-subsystem probes |
| `coop_selftest_engine.scr` | 13976 | 304 | 6 | coop_selftest_engine.scr - HZM dev engine-stress self-tests (2026-07-23) |
| `coop_selftest_keyitems.scr` | 23226 | 575 | 13 | coop_selftest_keyitems.scr - HZM dev automated self-tests (KEYITEMS) |
| `coop_selftest_objectives.scr` | 14445 | 401 | 14 | coop_selftest_objectives.scr - HZM dev objectives-subsystem probes |
| `coop_selftest_officer.scr` | 18323 | 474 | 12 | coop_selftest_officer.scr - HZM dev officer/DDA subsystem self-tests |
| `coop_selftest_scaling.scr` | 11498 | 259 | 8 | coop_selftest_scaling.scr - HZM dev scaling / $player-array / churn probes |
| `coop_selftest_triggers.scr` | 9118 | 229 | 9 | coop_selftest_triggers.scr - HZM dev automated self-tests: TRIGGERS |
| `coop_selftest_vehicles.scr` | 20615 | 494 | 11 | coop_selftest_vehicles.scr - HZM dev vehicle/ride/turret self-tests |
| `coop_selftest_weapons.scr` | 23468 | 594 | 11 | coop_selftest_weapons.scr - HZM dev automated self-tests: WEAPONS |
| `coop_selftest_xp.scr` | 28701 | 696 | 20 | coop_selftest_xp.scr - HZM dev automated self-tests: XP / CHALLENGES |
| `corpse.scr` | 1358 | 32 | 1 | [208] HZM coop - CORPSE DESPAWN. Dead AI bodies fade out and are removed after coop_corpseLife seconds |
| `cover.scr` | 10167 | 285 | 4 | Placement reach: trace along the view ray; if the ray lands on valid floor, place there. |
| `custom_items.scr` | 1603 | 37 | 2 | [200] Smithy - used for spawning any script built custom items we want |
| `dbno.scr` | 37048 | 927 | 19 |  |
| `dbno_test.scr` | 61 | 3 | 1 |  |
| `deathvox.scr` | 3973 | 76 | 2 | HZM coop - varied DEATH VOICES (+ native-VO mute for AI). |
| `developer.scr` | 57347 | 1578 | 42 | chrissstrahl - since the game refuses to let me use cheats in multiplayer |
| `director.scr` | 10609 | 227 | 3 | [user 2026-07-17] REACTIVE DIFFICULTY DIRECTOR - Phase 1 (plan: _research/director_dda_plan.md). |
| `e1l4alarm.scr` | 3221 | 76 | 4 | coop_mod/e1l4alarm.scr |
| `events.scr` | 2894 | 57 | 4 | [200] Smithy - 'built-in' events used for coop |
| `eventsystem.scr` | 7676 | 163 | 9 | [200] Smithy - Custom named events system now has own file. |
| `flchatter.scr` | 14722 | 317 | 7 | HZM coop - FRONTLINE BATTLE CHATTER (user-approved VO expansion, 2026-07-13). |
| `flmusic.scr` | 9561 | 200 | 7 | [311] HZM coop - FRONTLINE SCORE LAYER (Phase 1: stingers + war-ambience beds). |
| `gurgle.scr` | 7280 | 140 | 3 | HZM coop - subtle WET BLEED-OUT GURGLE near a fresh corpse. |
| `helmet.scr` | 50649 | 870 | 23 | [305] HZM coop - LIVE HELMET SWITCHER |
| `helmtest.scr` | 3758 | 96 | 1 | HZM dev probe (TEMPORARY): verify the retail sethelmet/pophelmet mechanic end to end. |
| `itemhandler.scr` | 130296 | 2651 | 88 | [200] Smithy - this script is called every time an item enters the world by exec it on their tiki |
| `keyitems.scr` | 8270 | 160 | 5 | [306] HZM coop - KEY MISSION ITEMS can never be permanently lost |
| `loadout.scr` | 36360 | 578 | 1 | [200] Smithy - this contains the weaponsloadout for coop |
| `loadoutpick.scr` | 34709 | 615 | 15 | [310] HZM coop ARMORY - per-player loadout picks (Phase 1). |
| `loadoutroster.scr` | 24873 | 775 | 2 | GENERATED by scratchpad/gen_loadout3.py -- DO NOT HAND-EDIT (regenerate instead) |
| `lobby.scr` | 51861 | 1127 | 23 | HZM Coop - Pre-Mission Lobby module.  Full spec: _research/coop_lobby1_build.md |
| `lobbyui.scr` | 9763 | 242 | 7 | [304] CLICKABLE LOBBY UI - a mouse cursor + button framework for the live |
| `m4l3_precache.scr` | 6104 | 157 | 0 |  |
| `main.scr` | 94118 | 1927 | 55 | VERSION 1.0 started by chrissstrahl on 2018.06.28 |
| `maplist.scr` | 3640 | 110 | 2 | [201] Smithy - used to populate the coop_mapsList array to check for next/previous map (and any other future properties we may want to give a map) |
| `maptest.scr` | 10231 | 239 | 3 | HZM Coop - Map Rotation Auto-Tester |
| `maptest_m5l3.scr` | 10638 | 284 | 4 | HZM Coop - m5l3 Scene-Walk Tester |
| `maptest_phase2.scr` | 13144 | 306 | 2 | HZM Coop - Phase 2 Map Tester |
| `maptest_vehicle.scr` | 18886 | 474 | 10 | HZM Coop - Vehicle Scene Tester (Phase 2 sibling) |
| `maptest_waypoints.scr` | 154495 | 4171 | 2 | HZM Coop - Phase 2 Map Tester: Pre-Extracted Waypoints |
| `medkit.scr` | 20190 | 505 | 4 |  |
| `mg42_hack.scr` | 1185 | 24 | 1 | chrissstrahl - scale health to players |
| `missioncomplete.scr` | 4481 | 77 | 1 | [200] chrissstrahl - 2020.06.14 |
| `mom_actions.scr` | 8952 | 173 | 18 | Created by chrissstrahl on 2018.07.02 - based on Multi Option Menu from Star Trek Elite Force II from 2009 for the HaZardModding Coop Mod |
| `mom_login.scr` | 5633 | 167 | 19 | Created by chrissstrahl on 2018.07.02 - based on Multi Option Menu from Star Trek Elite Force II from 2009 for the HaZardModding Coop Mod |
| `morale.scr` | 3641 | 77 | 1 | morale.scr - HZM coop SQUAD MORALE (ME1, coop_moraleEnable, default off) |
| `objective_drop.scr` | 7236 | 165 | 5 | Objective Bonus Drop |
| `objective_positions.scr` | 3691 | 89 | 1 | objective_positions.scr |
| `objectives.scr` | 22358 | 535 | 14 | Coop Side Objectives (optional / secondary) |
| `officer.scr` | 188172 | 4362 | 104 | Officer Boss + Radio Station |
| `officer_positions.scr` | 32104 | 588 | 1 | coop_officer_positions.scr |
| `paradrop.scr` | 28687 | 704 | 12 | Allied Paradrop System |
| `player.scr` | 77740 | 1549 | 33 | started by chrissstrahl on 2020.10.16 ([202]) |
| `precache.scr` | 7322 | 186 | 0 |  |
| `readygate.scr` | 14705 | 301 | 4 | HZM Coop - READY GATE (reusable "whole squad press [Use] to continue"). |
| `replace.scr` | 121480 | 2881 | 108 | chrissstrahl 23.06.2018 |
| `server.scr` | 13575 | 313 | 10 | started by chrissstrahl on 2020.10.16 ([202]) |
| `sndcache.scr` | 27392 | 728 | 1 | HZM coop - voice-pool precache (bug-1141 lag spikes). GENERATED by gen_sndcache.py - |
| `sound.scr` | 2294 | 63 | 4 | [203] Smithy - we can use this for sound related code |
| `spawnlocations.scr` | 170727 | 3548 | 183 | [200] chrissstrahl - fixed using unfiltred mapname (using now level.coop_mapname) |
| `strings.scr` | 34119 | 1301 | 34 | [200] Smithy - this is taken from xnull. Not mine, but is used by many. Will be useful to us. |
| `takecover.scr` | 2460 | 47 | 1 | [214] HZM coop - TAKE COVER v1 (player cover system). |
| `thirdperson.scr` | 2011 | 52 | 2 | HZM coop [237] - the 3rd-person bind now CYCLES three view modes (user): |
| `tinnitus.scr` | 8858 | 196 | 4 | HZM coop - TINNITUS / MUFFLED HEARING (per-player). |
| `tracescan.scr` | 5222 | 132 | 4 | coop_mod/tracescan.scr - server-side collision grid scanner (dev tool) |
| `variables.scr` | 19909 | 290 | 5 | started by chrissstrahl on 2020.10.16 ([202]) |
| `vehiclehandler.scr` | 3510 | 85 | 5 |  |
| `voidguard.scr` | 2370 | 56 | 1 | coop_mod/voidguard.scr - universal out-of-bounds safety net (all maps) |
| `weaponstate.scr` | 4581 | 93 | 1 | [200] Smithy |
| `weather.scr` | 14384 | 274 | 11 | HZM coop - WEATHER (v2): coop now drives the NATIVE SP trilogy weather system (global/weather.scr) so |
| `wounded.scr` | 27649 | 490 | 8 | [user 2026-07-17] WOUNDED GERMAN LIMP-AWAY. |
| `xp.scr` | 67844 | 1459 | 25 | [302] HZM XP SYSTEM - Phase 1 (tracking + persistence + end-of-map debrief + own-rank HUD) |

## `main.scr::main` boot chain, in source order

This is what the entry point ACTUALLY starts today, read straight out of `coop_mod/main.scr`.
It runs in a single frame - `wait`/`waitframe` are forbidden here.

| # | main.scr line | verb | target |
|---:|---|---|---|
| 1 | `coop_mod/main.scr:84` | `waitthread` | `coop_mod/variables.scr::main` |
| 2 | `coop_mod/main.scr:99` | `waitthread` | `coop_mod/server.scr::main` |
| 3 | `coop_mod/main.scr:103` | `thread` | `coop_mod/xp.scr::xp_init` |
| 4 | `coop_mod/main.scr:106` | `thread` | `coop_mod/challenges.scr::chal_init` |
| 5 | `coop_mod/main.scr:109` | `waitthread` | `coop_mod/spawnlocations.scr::main` |
| 6 | `coop_mod/main.scr:112` | `thread` | `coop_mod/player.scr::manage` |
| 7 | `coop_mod/main.scr:115` | `thread` | `coop_mod/aihandler.scr::coop_reinf_brain` |
| 8 | `coop_mod/main.scr:118` | `exec` | `coop_mod/loadout.scr` |
| 9 | `coop_mod/main.scr:121` | `thread` | `coop_mod/itemhandler.scr::disableAllWeaponsOnMenu` |
| 10 | `coop_mod/main.scr:128` | `thread` | `coop_mod/events.scr::initialiseEvents` |
| 11 | `coop_mod/main.scr:130` | `thread` | `coop_mod/buildmode.scr::coop_build_monitor` |
| 12 | `coop_mod/main.scr:132` | `thread` | `coop_mod/medkit.scr::coop_scan_health_entities` |
| 13 | `coop_mod/main.scr:133` | `thread` | `coop_mod/officer.scr::coop_officer_init` |
| 14 | `coop_mod/main.scr:134` | `thread` | `coop_mod/director.scr::director_main` |
| 15 | `coop_mod/main.scr:135` | `thread` | `coop_mod/weather.scr::coop_weather_init` |
| 16 | `coop_mod/main.scr:136` | `thread` | `coop_mod/ambience.scr::coop_ambience_init` |
| 17 | `coop_mod/main.scr:137` | `thread` | `coop_mod/flchatter.scr::flchatter_init` |
| 18 | `coop_mod/main.scr:138` | `thread` | `coop_mod/aivoice.scr::aivoice_init` |
| 19 | `coop_mod/main.scr:139` | `thread` | `coop_mod/flmusic.scr::coop_flmusic_filler` |
| 20 | `coop_mod/main.scr:146` | `thread` | `coop_mod/helmtest.scr::main` |
| 21 | `coop_mod/main.scr:152` | `thread` | `coop_mod/maptest.scr::coop_maptest_tick` |
| 22 | `coop_mod/main.scr:155` | `thread` | `coop_mod/maptest_phase2.scr::coop_maptest_phase2_tick` |
| 23 | `coop_mod/main.scr:160` | `thread` | `coop_mod/maptest_m5l3.scr::coop_maptest_m5l3_walk` |
| 24 | `coop_mod/main.scr:165` | `thread` | `coop_mod/maptest_vehicle.scr::coop_maptest_vehicle_tick` |
| 25 | `coop_mod/main.scr:169` | `thread` | `coop_mod/tracescan.scr::scan` |
| 26 | `coop_mod/main.scr:175` | `thread` | `coop_mod/coop_selftest.scr::weaptest_run` |
| 27 | `coop_mod/main.scr:178` | `thread` | `coop_mod/coop_selftest.scr::dbnotest_run` |
| 28 | `coop_mod/main.scr:181` | `thread` | `coop_mod/coop_selftest.scr::dbnoteam_run` |
| 29 | `coop_mod/main.scr:184` | `thread` | `coop_mod/coop_selftest.scr::xptest_run` |
| 30 | `coop_mod/main.scr:187` | `thread` | `coop_mod/coop_selftest.scr::scaletest_run` |
| 31 | `coop_mod/main.scr:192` | `thread` | `coop_mod/coop_selftest_scaling.scr::st_scaling_run` |
| 32 | `coop_mod/main.scr:195` | `thread` | `coop_mod/coop_selftest_engine.scr::st_engine_run` |
| 33 | `coop_mod/main.scr:198` | `thread` | `coop_mod/coop_selftest_vehicles.scr::st_vehicles_run` |
| 34 | `coop_mod/main.scr:201` | `thread` | `coop_mod/coop_selftest_objectives.scr::st_objectives_run` |
| 35 | `coop_mod/main.scr:204` | `thread` | `coop_mod/coop_selftest_triggers.scr::st_triggers_run` |
| 36 | `coop_mod/main.scr:207` | `thread` | `coop_mod/coop_selftest_officer.scr::st_officer_run` |
| 37 | `coop_mod/main.scr:210` | `thread` | `coop_mod/coop_selftest_keyitems.scr::st_keyitems_run` |
| 38 | `coop_mod/main.scr:213` | `thread` | `coop_mod/coop_selftest_dbno.scr::st_dbno_run` |
| 39 | `coop_mod/main.scr:216` | `thread` | `coop_mod/coop_selftest_xp.scr::st_xp_run` |
| 40 | `coop_mod/main.scr:219` | `thread` | `coop_mod/coop_selftest_weapons.scr::st_weapons_run` |
| 41 | `coop_mod/main.scr:222` | `thread` | `coop_mod/coop_selftest.scr::wintest_run` |
| 42 | `coop_mod/main.scr:225` | `thread` | `coop_mod/coop_selftest_officer.scr::st_officer_run` |
| 43 | `coop_mod/main.scr:231` | `thread` | `coop_mod/coop_selftest_engine.scr::st_engine_run` |
| 44 | `coop_mod/main.scr:238` | `thread` | `coop_mod/coop_selftest_objectives.scr::st_objectives_run` |
| 45 | `coop_mod/main.scr:242` | `thread` | `coop_mod/voidguard.scr::main` |
| 46 | `coop_mod/main.scr:251` | `thread` | `coop_mod/aimaneuver.scr::main` |
| 47 | `coop_mod/main.scr:255` | `thread` | `coop_mod/aisquad.scr::main` |
| 48 | `coop_mod/main.scr:257` | `thread` | `coop_mod/morale.scr::main` |
| 49 | `coop_mod/main.scr:261` | `thread` | `coop_mod/aibehav.scr::main` |
| 50 | `coop_mod/main.scr:266` | `thread` | `coop_mod/aicombat.scr::main` |
| 51 | `coop_mod/main.scr:272` | `thread` | `coop_mod/sndcache.scr::main` |
| 52 | `coop_mod/main.scr:278` | `thread` | `coop_mod/eventsystem.scr::isEventActive` |
| 53 | `coop_mod/main.scr:281` | `thread` | `coop_mod/eventsystem.scr::doEvent` |

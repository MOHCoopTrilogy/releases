# Coop 16-Player Scripted-Events & Objectives Plan (HZM)

Source: subagent research pass 2026-06-23. Plan only; no game files modified (a map-rotation
test is running in another process). Read-only analysis of the partial HZM map scripts plus the
vanilla Spearhead/Breakthrough originals.

This doc is the per-map **WHAT** (every scripted sequence + objective) and the **16-player scaling
plan**. The companion docs are the **HOW**: `coop_vehicle_onrails_plan.md` (vehicle Patterns A/B/C),
`coop_vanilla_vs_hzm_diff.md` (the conversion recipe), `hzm_coop_framework_guide.md` (hook contract).
The officer-boss layer is covered by `officer_coverage_audit.md`. This doc does NOT redo vehicle
patterns; it adds the non-vehicle events, objectives, and 16-player scaling on top.

---

## 0. STATE CORRECTION (important — memory was stale)

The `level_scripts_sh_bt.md` memory says the t-series is "pure vanilla, zero coop integration."
**That is no longer true.** Every target script in `hzm-mohaa-coop-mod/maps/` already has the coop
hook and the coop spawn gate:

- `waitthread coop_mod/main.scr::main` (first frame, before prespawn)
- `waitthread coop_mod/replace.scr::waitForPlayer` (replaces `level waittill spawn`)
- Music swapped from `$player stufftext "tmstart..."` to `exec coop_mod/replace.scr::tmstartloop`
  (in some maps; several `$player stufftext` music lines REMAIN — see per-map tables).

So these are **partially converted**, not unconverted. The remaining work is per-element 16-player
scaling: singular `$player` mutations, global `cuecamera`/`freezeplayer`, `parm.other==$player`
trigger gates, vehicle seating caps, and a couple of live parse-killer bugs. The vanilla pak scripts
remain the reference for the full event inventory where HZM stripped comments/music.

### Confirmed primitives my fixes build on (verified file:line)
- `coop_mod/main.scr:427 playersWarpto local.origin local.angle local.setSpawn` — loops `1..$player.size`, warps every player. Template for every "loop over all players" fix.
- `coop_mod/replace.scr:2507 validateTriggerActivator local.thread local.validActivator ...` — wraps a BSP trigger so only the valid activator (e.g. the vehicle) fires it; clones+re-arms for others. The fix for every `parm.other==$player` gate.
- `coop_mod/replace.scr:99 waitForPlayer` — coop spawn gate (already wired in all 12).
- Engine `addobjective <num> <status> <text> <loc>` **auto-replicates to all coop clients** (script_command_catalog.md). Both `global/obj.scr` and `global/objectives.scr` and `global/ObjMgr.scr` route through it -> **objective HUD state already broadcasts to all 16; no `coop_objectivesSendPlayer` call needed for these maps.**
- Per-player camera = `spawn Camera` + unique targetname + `spawn trigger_camerause target <name>` + `doUse <player>` + delete trigger (m1l1 pattern; engine_systems_advanced.md). NEVER bare `cuecamera`.
- `cuecamera`/`cueplayer`/`freezeplayer`/`releaseplayer` are GLOBAL (all clients) — confirmed camera.cpp.

---

## 0a. LIVE BUGS FOUND (fix regardless of 16-player work) — P0

Two **non-ASCII byte 0x92** (Windows-1252 right-single-quote) parse killers. Per
`mohaa_script_notes.md`, a single byte >0x7F silently aborts the ENTIRE file at compile — every
function in it stops loading, with no in-game error.

| File:line | Offending text | Impact |
|---|---|---|
| `maps/e3l2/objectives.scr:8` | `"Cover the Allied Prisoners`**`’`**`s Escape"` (InitObj "protectPOWs") | **Whole `objectives.scr` fails to load -> `InitObjectives` never runs -> e3l2 has ZERO objectives in coop.** This is why e3l2 "objectives never render." |
| `maps/e3l2/prisoner_section_1.scr:456` | `"You failed to protect the prisoner`**`’`**`s escape."` | Whole `prisoner_section_1.scr` fails -> the prisoner-protect section + its mission-fail never load. |

Fix: replace byte 0x92 with an ASCII apostrophe `'`. Verify with
`perl -ne 'print "$.\n" if /[^\x00-\x7F]/' <file>` returning nothing. The 12 main map `.scr`
files are clean (no BOM, no non-ASCII). This corrects the `e3l2_objectives_false_positive` memory:
the objective system is real (ObjMgr, 4 named objectives) but is currently **dead due to this byte**,
not a numbering issue.

---

## Element-type legend
- **CIN** intro cinematic/camera/menu showcase. **FRZ** freeze/cutscene. **VEH** vehicle ride/drive/turret. **ESC** escort/follow AI. **TIM** timed event. **SPWN** position/progress-gated enemy spawn. **DESTR** destructible/explosion. **DOOR** door/lift. **AMB** ambush/set-piece. **END** mission-end/handoff. **OBJ** objective.

---

# T-SERIES (Spearhead)

## t1l1 — Paratroop Drop / Barn Crash (cinematic intro) — Pattern A
Vanilla maps/t1l1.scr (10.8 KB). HZM 416 lines. `coop_feature_boss=0` (exempt). Win = allies do
endleveltrigger (line 288, currently commented; handoff is via the allied-driven barn sequence).

| Element | Type | SP assumption | Coop fix | 16-player consideration | Effort/Risk |
|---|---|---|---|---|---|
| Plane ride + parachute (`DoPlaneRide`, gags/T1L1_PlaneRide) | CIN/VEH | Single player harnessed to plane; cinematic camera on one POV | Pattern A: per-player ride-camera attached to plane/harness tag (mirror e2l1 gliderride coop_*); gate on a new `level.coop_planeRideOver` flag; on set delete all cams + cueplayer + physics_on | All 16 ride simultaneously; late joiner during ride gets a cam too; eject-on-death watcher | High / High (gags in BASE pak -> wrap in level script, don't edit pak) |
| `barn_hole`/`cutharness` (271-275) crash-through + harness cut | FRZ/CIN | `$player loopsound t1_barninside` (267) singular; harness cut assumes one player | Loop ambient loopsound over all players; cut every player's harness; tie to the ride-over flag | All players land in barn together | Med / Med |
| `SetupTruck` enemy truck drive + unload (145-188) | VEH/SPWN | `TruckGuyRun: self runto $player` (249) targets host only | Replace `$player` with nearest active player (`coop_mod/replace.scr::runtoClosest` pattern) | 4 truck guys should spread across players, not all rush host | Low / Low |
| 3 AA guns auto-fire setup (104-142) | TIM | aim targets are script_origins, player-agnostic | none (already coop-safe) | n/a | None |
| Stuka strafing flyovers (stuka_start/end 341-368) | TIM | flypath on script_models, player-agnostic | none | n/a | None |
| `artillery_message` use-prompt (297-306) | CIN | `getboundkey1` + throbtext is global text | none (broadcasts to all) | fine | None |
| 3 objectives (70-72, `global/objectives.scr::add_objectives`) | OBJ | rendezvous / destroy tank w/ AA / regroup | none — addobjective auto-replicates | completion is allied-driven / BSP; any player fine | None |

## t1l2 — Dutch Town / Flak88 — general hygiene + freeze
HZM 985 lines. Captain NPC `level.cappy` + `level.friendly2/3`. Win = `missioncomplete t1l3` (644).

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Intro freeze (143-149: `$player fullheal`, `freezeplayer`, `releaseplayer`) | FRZ/CIN | freezeplayer freezes EVERYONE; fullheal only host | Replace `freezeplayer/releaseplayer` with per-player physics_off + viewangles set in a `1..$player.size` loop; fullheal -> loop heal all | All 16 frozen for intro then released together; nobody can fight during it (acceptable, short) | Med / Med |
| `$player stufftext "tmstart Emmerich.mp3"` (93) + Gotha (555,560) + Labyrinth (719) | CIN | per-host music only | swap each to `exec coop_mod/replace.scr::tmstartloop` (mod already does this elsewhere) | all hear music | Low / Low |
| Captain `$cappy` escort + dialogue, squad death | ESC | trigger gate `parm.other==level.cappy` (748) and `parm.other!=friendly3/2` (703) | wrap gate so the captain (an NPC) still validates; player-touch variant -> validateTriggerActivator(any active player) | escort objective completes when cappy/any player reaches | Med / Med |
| 2x Flak88 destroy objectives | OBJ/DESTR | destroy-gun gates | none (addobjective replicates; destruction is damage-based, any player) | any player destroys | Low |
| `missioncomplete t1l3` (644) | END | — | none | first to finish triggers for all | None |

## t1l3 — Dutch Canal Town / Colonel / Bridge — Pattern (cutscene) + escort
HZM 1098 lines. Story colonel NPC (officer_trig path). Demo-charge bridge (4 charges). Win =
`missioncomplete t3l2`? No -> `missioncomplete t1l3`->next; bridge demolition is the set-piece.

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Intro freeze (145 `freezeplayer`, 152 `releaseplayer`, 143 fullheal, 57 takeall) | FRZ | global freeze; singular heal/takeall | per-player loop (physics_off + loadout); drop bare freezeplayer | all released together | Med / Med |
| Colonel NPC on `officer_trig1-5` scripted path; `thread objective1` at trig1 | ESC/SPWN | colonel follows the host; trig gated on player reach | colonel path is self-driven (fine); player-reach trig -> validateTriggerActivator(any active player) | colonel-elimination objective: complete when ANY player kills colonel | Med / Med |
| `parm.other.owner == $pushtank` (321) tank-push trigger | DESTR | gates on the scripted tank only | already entity-gated (the tank, not player) -> safe; verify $pushtank is the activator | n/a | Low |
| Demo-charge bridge: 4 charges (charge1-4), `charge_switch`, blowbridge w/ `cueplayer` (897,909) | DESTR/CIN | charges planted by host; `cueplayer` global after collapse cam | charge plant is item-use (any player can plant; count flags already global); the collapse uses a camera -> per-player ride-cam OR accept brief global cut then per-player cueplayer | charges plantable by any of 16; collapse cam should not steal a fighting player's view -> prefer per-player cam | Med / High (camera) |
| Flak cannon gag (80) | VEH/TIM | scripted | none | n/a | None |
| Objectives 1-6 incl. "plant 4 demo charges" (483-486) | OBJ | charge-count flags (level.charge1-4) are global | none — already level-global; addobjective replicates | "4 charges placed" completes regardless of who places them | Low |

## t2l1 — Ardennes / Nebelwerfers / Tiger Tanks — freeze + squad-fail + turret
HZM 2139 lines (largest after t2l3). 5 objectives mixing `global/obj.scr` + `global/objectives.scr`.
Win = all 4 objs complete -> `missioncomplete t2l2` (1961). **Mission-FAIL if squad dies.**

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Intro: `$player physics_off`(12), menu showcase w/ `freezeplayer`(306)+`releaseplayer`(337), `$player.viewangles`(307,339) | FRZ/CIN | global freeze; only host's view aimed; only host physics | Loop physics_off + viewangles over `1..$player.size`; drop bare freezeplayer (use per-player physics_off so others can't move either, or accept short global freeze). Set every player's viewangles to "0 155 0" | All 16 watch the date/place menu cards; released together | Med / Med |
| `$player fullheal`(239) `$player takeall`(240) + Thompson give (341) | — | host only | loop over all players (loadout already coop-aware elsewhere) | all armed | Low |
| `check_squad_death` (1854): mission-FAIL when friendly1/2/3 all dead | TIM/END(fail) | 3 NPC squad must survive; tuned for 1 human+3 AI | Keep as fail condition BUT consider: with 16 humans the NPC squad is less central. Lower risk = keep; the squad is `nodamage` early. Ensure fail only fires after combat starts, not if a late joiner | Don't let one careless player wipe NPCs and fail for all 16; consider relaxing to "objectives still completable" | Med / Med (design) |
| `parm.other.gun == panzerschrek` pickup (442) | DESTR | host's weapon check | check is on the activator's gun (any player) -> mostly fine; verify parm.other is a player | n/a | Low |
| Nebelwerfer player-turret (`playerturret_proj_think_aim`) | VEH/turret | one gunner | turret is single-seat by nature; any player can mount; others fight on foot | 16 players: 1 mans nebel, rest assault | Low |
| Sticky-bomb tank kills (Tiger1/2) | DESTR | host plants sticky | any player; flags global | any player | Low |
| `$player stufftext` music (35,1642,1643,1790,1791) | CIN | host-only music | swap to `tmstartloop` | all | Low |
| 5 objectives (obj.scr hidden + dynamic "[N remaining]" via nextobjective) | OBJ | nebel count flags global | none — flags already level-global; addobjective replicates the "[3 remaining]" text to all | counter shared across 16 | Low |

## t2l2 — Halftrack Escort / Snowy Forest — Pattern A/B (auto-driven) + turret
HZM 904 lines. `coop_feature_boss=0`. The halftrack (`level.playerjeep=$s1_jeep1`) is **auto-driven on
a scripted path** (`PLAYER_JEEP_Drive` 800-846 uses `self drive $path`), player mans the nebelwerfer
turret. Win = escort supply truck survives + reach `endlevel` -> `missioncomplete t2l3` (897).
**Mission-FAIL if truck destroyed** (check_truck_death 868-881).

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| `PLAYER_JEEP_CONTROLLER` + `PLAYER_JEEP_Drive` (100-101) | VEH | `PLAYER_JEEP_CONTROLLER` skips attaching `$player` in coop (gametype!=0) -> nobody is seated; halftrack auto-drives empty | Pattern A/B coop layer: since it auto-drives, treat as Pattern A ride — attach per-player ride-cam OR (better here) glue passengers to the halftrack via the m1l3b passenger-tag pattern extended to 16 seats; one player on the nebel turret | **Seat cap is the core 16 problem.** m1l3b helper caps at 8 (playerAttach2..8). Need 16-seat handler OR free-roam: let players walk alongside the slow halftrack (it pauses on the cliff) and re-board, with a geofence so stragglers warp up | High / High |
| Nebelwerfer turret (`$nebel1_turret0 playerturret_proj_think_aim`, 85) | VEH/turret | single gunner | single-seat; any player mounts; rotate on death | 1 gunner of 16 | Low |
| `triggerexplode` gate `parm.other == $player` (853) | DESTR | only host's touch fires scripted explosions along the route | `validateTriggerActivator` for "any active player OR the halftrack"; or accept any player (these are ambience explosions) | any of 16 passing fires it | Low |
| `triggerloop` speed-up gate `parm.other != $s1_truck1` (785) | VEH | gated on the supply truck (NPC) — correct | none (entity-gated, not player) | n/a | None |
| `$player fullheal`(94) `$player.health=1000`(95) | — | host only | loop all players, set health 1000 (the halftrack ride is dangerous) | all 16 tanky for the ride | Low |
| Supply-truck escort survival = win; destruction = `missionfailed` (868-881) | END | global truck health | none — truck health is global; missionfailed is global | one truck, shared fate (correct) | None |
| `$player playsound` VO (777,825 etc.) | — | host only hears | loop playsound over players OR use a broadcast; minor | all hear | Low |

## t2l3 — Bastogne Wave Defense — most complex t-series; defense set-piece
HZM 3330 lines (largest). German captured weapons. 3-wave defense + panzers + Stuka. Captain Ike NPC.
Win after waves -> `missioncomplete t2l4` (479). **FAIL via `level.axiswins=1`** (Germans reach
trigger5/8) AND squad death.

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Intro: `$player physics_off`(18), `$player fullheal`+`takeall`+German-weapon loadout (337-349), menu showcase `freezeplayer`(351)+`releaseplayer`(391)+`$player.viewangles`(352,392) | FRZ/CIN | global freeze, host-only loadout/view | loop loadout + viewangles over all players; drop bare freezeplayer (per-player physics_off) | all 16 get p38/kar98/mp40 + grenades; all watch Bastogne cards | Med / Med |
| Obj1-3 talk-to-captain / find medic / escort medic | ESC/OBJ | NPC escort gated on host reach | medic escort: complete when medic reaches captain (NPC-driven, fine); player-reach gates -> validateTriggerActivator(any player) | escort works with any player nearby | Med / Med |
| Obj4-6 defend right/left/right flanks (wave1/2/3); `enablegroup1ai`/`group5ai` tight 0.1s loops | SPWN/DEFEND | waves spawn vs the player area | none for spawning (area-based); ensure wave-clear counts AI not "player in zone" | 16 players spread across flanks — waves should target the defended volume, not one player | Med / Med |
| `level.axiswins=1` when Germans reach trigger5/trigger8 -> `missionfailed` (1744,1776, 2844-2885) | END(fail) | breach = loss, global | none — `axiswins` is level-global; missionfailed global; correct coop behavior | shared loss if line breached (intended) | None |
| Panzer tank drives (panzertankdrive/2), Stuka strafe | VEH/TIM/DESTR | scripted, player-agnostic | none | n/a | None |
| `$mp44trigger`/`$webbers_mp44` weapon pickup set-piece | DESTR/AMB | host picks up | any player pickup; flag global | any of 16 | Low |
| `$killzone` death zones | DOOR/hazard | radius/volume damage (volume = all inside) | verify killzone uses `volumedamage` (hits all) not `$player.origin` radiusdamage | all players in zone die (correct) | Low |

## t2l4 — Stavelot Town (Church/Hotel/Barn) — multi-building + kill-zones
HZM 1173 lines. Captain NPC `$cappy`. BazookaGuy set-piece. Sniper pickup. `KillThePlayer` boundary
death zones. Win -> `missioncomplete t2l4`->next (479? verify; uses spawn_8 ending via cappy).

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| `KillThePlayer` (414): `while(isalive $player){ radiusdamage $player.origin 900 400 }` boundary leave | DOOR/hazard | only host punished for leaving map bounds | Loop over all players: any player outside bounds gets radiusdamage at their own origin; or use a `volumedamage` trigger volume covering the out-of-bounds region (hits all) | All 16 must respect bounds; a single straggler shouldn't be the only one geofenced or the only survivor | Med / Med |
| Trigger gates `parm.other==$player || parm.other==$cappy` (852,866,882,897) — building entry spawns | SPWN/AMB | host or captain entry triggers building AI | `validateTriggerActivator` accepting any active player OR $cappy (extend the validActivator check to a small set) | any of 16 entering the church/hotel triggers the ambush | Med / Med |
| `$player fullheal` (77) | — | host | loop all | all | Low |
| Church/Hotel/Barn building AI mgmt (ChurchBoth/Inside/Outside, HotelGuys) | SPWN | area spawnsets | none (spawnset by named group) | scales fine | None |
| BazookaGuy special encounter at church tower | AMB/DESTR | scripted | none | n/a | None |
| Sniper rifle pickup (KAR98sniper) at tower | DESTR | host pickup | any player; ensure given to the activator | any of 16 | Low |
| `windowguy_*_show` flanking-ally flashes | TIM | scripted shows | none | n/a | None |
| Captain ending `gags/t2l4_captain.scr::DoEnding` at spawn_8 | END | NPC-driven | none | reach-trigger -> any player | Low |

## t3l1 — Berlin Streets / T-34 commandeer / Safe puzzle — general + puzzle
HZM 1214 lines. Russian weapons. Truck convoys, panzer waves. Safe-combination puzzle. Win =
eliminate guards + `missioncomplete t3l2` (592). T-34 is the OBJECTIVE (commandeer), AI prop until end.

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Intro freeze (279 `freezeplayer`, 286 `$player physics_off`, 313 `releaseplayer`), `$player takeall`(46)+Russian loadout, `$player fullheal`(63) | FRZ/CIN | global freeze; host-only loadout | loop loadout/heal over all players; drop bare freezeplayer (per-player physics_off + teleport via `playersWarpto` if an intro reposition is wanted) | all 16 armed with Soviet kit, frozen+released together | Med / Med |
| Safe-combination puzzle: `level.combination`(354), `level.usetrigger5`(355), `usetrigger5`(485), `objective5/6` | OBJ/DOOR | combination pickup + safe-open by host; uses `level.*` flags | already level-global flags -> ANY player who finds the combo / uses the safe sets it for all; verify the pickup/use trigger fires for any player (it sets level flags, so fine) | any of 16 solves it for the team | Low / Low |
| Objective7: kill 3 tankguards + reach `$objective7trigger` -> commandeer T-34 -> `missioncomplete t3l2` | OBJ/END | guards dead (any), trigger reach (host) | guard-dead loop is global; `$objective7trigger waittill trigger` fires on any player; `$player takeall`(590) host-only but cosmetic at transition | first player to reach trigger ends for all | Low |
| Truck convoys (S-10 at s10_1..3); `$player stufftext` Kleveburg music at s10_3 (721) | VEH/CIN | scripted drive; host-only music | swap stufftext->tmstartloop | n/a / all hear | Low |
| `stopgermans`/`restartgermans` AI pause for cutscene segments | TIM | global all_ai pause | none (global is fine in coop) | n/a | None |
| Panzer waves (panzer1-7) | SPWN | area | none | scales | None |

## t3l2 — Berlin / Player Drives T-34 / Bridge collapse — Pattern C + endgame cam
HZM 1514 lines. `coop_feature_boss=0`. **Player drives T-34 the whole map** via
`players_tank` (already coop-aware per vehicle plan). Campaign END:
`missiontransition briefing/briefingd1 1` (162). Endgame camera at 1294.

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| `$playertank players_tank` (33) — player-driven T-34 | VEH | `players_tank` setup; SP attachdriverslot gated, coop branch threads coop_selectDriverForTank | none in players_tank itself (already coop). **CRITICAL: verify `$coop_tankOffset` attaches to the T-34 cannon model** — players_tank scans for kingcannon.tik (King Tiger); T-34 differs. If mismatch, driver-select silently never lets anyone board. Add a coop setup block scanning the T-34 cannon (copy m5l2b.scr 62-81) | 1 driver of 16 mans the tank; other 15 fight on foot / ride along. Provide a board/dismount so the seat rotates on driver death | High / High (the silent-no-board risk) |
| Intro: `$player physics_off`(37), `takeall`(44,52), `holster`(53), `fullheal`(62), `physics_on`(138) | FRZ | host-only; only driver should be physics_off | Loop takeall/holster/fullheal over ALL players; ONLY the boarded driver gets physics_off (via coop_setDriverForTank). Drop the global `$player physics_off`(37)/`physics_on`(138) — let the tank layer own driver physics | non-drivers keep control and fight | Med / Med |
| `$player stufftext "tmstop; tmstartloop ...Schmerzen"` (139) + endgame `$player stufftext "tmstop"` (1300) | CIN | host-only music | swap to `tmstartloop`/`tmstop` coop replacements | all hear | Low |
| Bridge collapse exploder `parm.owner == $player && level.bridge_ready==1` (976) | DESTR | only host's tank shell collapses the bridge | `validateTriggerActivator` for the tank/any active player (the projectile owner should be whoever fired; accept any player or the tank driver) | any of 16 (or the tank) collapses it | Med / Med |
| Enemy tank waves by BSP trigger (s5..s50) | SPWN/VEH | area-triggered | none (area-based) | scales | None |
| `endgamecamera` (1294): `cuecamera $watch_camera`(1303) bomber flyby, `cueplayer`(1319) | CIN/END | global cuecamera locks all into bomber cam | This is the campaign-ending cinematic — a GLOBAL cut is arguably acceptable (mission is ending). If per-player desired, use per-player ride-cam pattern; otherwise keep global cuecamera but ensure no player is mid-respawn (gate on all alive/spectator-safe). End handoff missiontransition is global | all 16 watch the ending together (acceptable for campaign end) | Low / Low (accept global) |
| `killcheater`/`$cheaterkiller volumedamage` (1326-1330) bounds | DOOR/hazard | `volumedamage 6000` (volume hits all inside) — already coop-safe | none | all in zone punished | None |
| 3 objectives (destroy bridge / return to Soviets / defend bridge) | OBJ | BSP-trigger gated (`$objective2trigger waittill trigger`) | none — addobjective replicates; triggers fire on any player | any of 16 advances objective | Low |

---

# E-SERIES (Breakthrough) — the three under-integrated maps

## e3l2 — N.Africa Town / Modello Tanks / POWs — FULLY integrated except the parse bug
HZM 455 lines + sub-scripts. Coop hook, waitForPlayer, coop music, `ObjMgr` named objectives, stub
handlers all present. Win -> `missioncomplete e3l3` (NextLevel, 232).

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| **objectives.scr non-ASCII byte** (see 0a) | OBJ | — | replace 0x92 with `'` | unblocks ALL 4 objectives for all 16 | **P0 / High-value, trivial fix** |
| `PlayerUseKeyThread` (207): polls only `$player.useheld` | DESTR/use | only HOST's use-key drives cannon-destruction use prompts | Poll useheld across `1..$player.size`; set `level.player_use_just_pressed` if ANY player pressed (and ideally record which player for the cannon they're near) | any of 16 can use-destroy a Modello cannon | Med / Med |
| `startsniper2`: `$sniper2 favoriteenemy $player[1]` (339) | SPWN/AMB | sniper hard-targets player 1 | use nearest active player or leave to normal AI targeting | sniper shouldn't ignore 15 players to chase player1 | Low |
| Section-warp debug: `$player.origin/.angles/.viewangles` (84-149) | (debug) | host-only teleport; cvar-gated dev feature | loop `playersWarpto` if you want coop debug warps; low priority (debug only) | dev-only | Low |
| 3 Modello cannon destructions (Cannon1/2/3DestructionThread) + ObjMgr "[N Remaining]" | OBJ/DESTR | num_cannons_remaining global | none — level-global counter; ObjMgr replicates | shared count across 16 | None |
| Medic NPC (`medic_think`), balcony guys, MG42s, airplane bomb | ESC/SPWN/DESTR | area/NPC | none | scales | None |
| **prisoner_section_1.scr non-ASCII byte 456** | OBJ/END(fail) | — | replace 0x92 with `'` (unblocks protect-prisoner section) | restores the protectPOWs fail path | P0 / trivial |

## e3l3 — N.Africa / K5 Railguns / AB41 — minimally integrated (MINIMAL coop)
HZM 728 lines. Officer audit: rotation-SKIPPED (C crash, missing panzer TIKs, Issue #18). HZM uses
`coop_mod/replace.scr::missionfailed` (91) and missioncomplete e3l4 (87). NO `coop_mod/main.scr::main`
in the older survey — but verify current file head.

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Verify/add `coop_mod/main.scr::main` hook + `waitForPlayer` | (infra) | older versions lacked it | add the standard two HZM lines if absent (it has missionfailed/physics swaps but confirm the main hook) | enables coop spawn gate for 16 | Med / Med |
| Intro `$player physics_off/on` (105,130 — currently commented) | FRZ | host-only | if re-enabled, loop over players | all | Low |
| K5 railgun + AB41 objectives | OBJ/DESTR | destroy-gun gates | addobjective replicates; verify `global/objectives.scr` used (not the dead ObjMgr path) | any player destroys | Low |
| `missioncomplete e3l4` (87) / `missionfailed` (91) | END | — | missionfailed already coop-replaced | shared | None |
| **Blocker: rotation crash (missing panzer TIKs)** | (asset) | — | out of scope here (asset/precache fix); flagged in officer audit Issue #18 | must fix before 16-player test | High / High (asset) |

## e3l4 — N.Africa Castle / Radio Tower / Airstrike — campaign-end, well-integrated
HZM 312 lines. **Already has** coop hook (5), waitForPlayer (21), full linear objective chain (8
objectives via `global/objectives.scr`), GiveMedals, DoOutro, AND coop stub handlers (305-313). The
officer audit "no coop init" is stale. `coop_feature_boss=0` (campaign end).

| Element | Type | SP assumption | Coop fix | 16-player | Effort/Risk |
|---|---|---|---|---|---|
| Linear objective chain: DeliverSupplies->Defend Baker->Defend Charlie->Regroup->Radio->Defend Tower->Confirm Airstrike (43-94) | OBJ | sequential `waitthread ...ObjectiveX` blocks gate on host reaching/defending | each Objective* sub-thread likely waits on a BSP trigger (any player) or a defend-timer (global). Audit each `maps/e3l4/<Bunker|Tower|Castle>.scr` Objective fn for `$player`/`parm.other==$player` and convert to any-player/quorum | bunker defenses scale (more players = easier, acceptable); "reach" gates -> any player | Med / Med |
| `UpdateRegroupInCastleObjective` / `UpdateGoToRadioObjective` (237-266): `$player waitthread FindClosestNodeOnPath` | OBJ/compass | compass breadcrumb computed from HOST's position only | compute from nearest active player to the path, or just leave host-anchored (compass is a hint; minor). Better: loop and pick the player closest to the objective | 16 players get a compass arrow aimed from host's progress; cosmetic but can mislead | Low / Med |
| `$player heal 1` (146, InitLevel) | — | host-only (and a no-op hint) | loop or drop | trivial | Low |
| Jeep intro: `$jeepdriver`/`$jeeppassenger` attach to $startjeep (168-182) | CIN/VEH | NPC driver+passenger (not players) | none — these are NPCs decorating the start jeep; players are not seated | n/a | None |
| `$player loopsound`-style ambient (if any) | — | host-only | loop if present | minor | Low |
| Airstrike confirm (radio use) `ObjectiveConfirmAirstrike` | OBJ/use | host uses radio | audit the radio-use trigger -> any active player | any of 16 confirms | Low |
| GiveMedals + DoOutro + missiontransition | END | global medals/outro | none (global, campaign end) | all 16 see outro | None |

---

## Objectives sub-plan (cross-map)

**Good news:** every objective path in these 12 maps routes through the engine `addobjective`
command (via `global/obj.scr`, `global/objectives.scr`, or `global/ObjMgr.scr`), which
**auto-replicates objective text/state to all connected coop clients**. There is NO per-map
`coop_objectivesSendPlayer` work needed for HUD broadcast, and late joiners receive current
objective state from the engine's objective snapshot. This differs from the AA side-objective
slots 7/8 case (coop_objectives_hud memory) which used custom cvar stores — these maps use the
native store.

**Completion semantics to set per objective (the real 16-player decision):**
- **ANY-player (default, correct for most):** BSP-trigger objectives (`$objN_trigger waittill
  trigger`) fire on the first player to touch — completes for the team. This is the desired coop
  behavior for "reach X" / "destroy Y" objectives. No change needed; just confirm the trigger isn't
  additionally gated by `parm.other==$player`.
- **Counter-based (already global):** "[N remaining]" objectives (t2l1 nebelwerfers, e3l2 cannons,
  t2l3 waves) use `level.*` counters — inherently shared; replicate fine.
- **Escort/defend (NPC-driven or volume-defend):** complete when the NPC reaches goal / the defended
  volume holds — already player-agnostic.
- **FAIL conditions** (t2l1/t2l3 squad death, t2l2 truck death, t2l3 axiswins breach, e3l2 prisoner
  death): all are level-global and call global `missionfailed`. They are coop-correct as-is, EXCEPT
  the squad-death fails (t2l1/t2l3) — with 16 humans, a wiped 3-NPC squad failing the mission for
  everyone is a design risk. Recommend: gate squad-death fail behind "objectives not yet completable"
  or relax it for coop.

**The dead objective set (P0):** e3l2's 4 ObjMgr objectives are currently NON-FUNCTIONAL due to the
0x92 byte in `objectives.scr:8`. Fix the byte first; re-verify objectives render for all players.

---

## Prioritized conversion order (effort vs. value)

**P0 — trivial, high value (do first):**
1. Fix 2x non-ASCII 0x92 bytes (e3l2/objectives.scr:8, e3l2/prisoner_section_1.scr:456). Unblocks all e3l2 objectives + prisoner section. Minutes of work.

**P1 — general hygiene across all t-series (shared, repetitive, low risk):**
2. Replace bare `freezeplayer`/`releaseplayer` intros with per-player physics_off loops (t1l2,t1l3,t2l1,t2l3,t3l1). Same edit shape 5x -> build helper #3 below.
3. Loop singular `$player fullheal/takeall/holster/health/loadout` intros over `1..$player.size` (every t-map). Build helper #4.
4. Swap remaining `$player stufftext "tmstart..."` music to `tmstartloop` (t1l2,t2l1,t3l1,t3l2 etc.).
5. Wrap `parm.other==$player` trigger gates with `validateTriggerActivator` (t2l2:853, t2l4:852-897, t3l2:976, t1l3 colonel, t1l2:703/748). Build helper #5-friendly call sites.

**P2 — per-map set-pieces (medium):**
6. e3l2 `PlayerUseKeyThread` -> any-player use detection (cannon destruction).
7. t2l1 / t2l3 squad-death fail relaxation for 16 players (design call).
8. e3l4 objective sub-thread audit (`maps/e3l4/*.scr` Objective fns) for host-only gates + compass-from-host.

**P3 — vehicles at 16 (high effort, defer to vehicle plan + new helpers):**
9. t3l2 T-34: verify cannon-model offset (silent-no-board risk) — see vehicle plan CRITICAL note.
10. t2l2 halftrack 16-seat seating OR walk-alongside geofence.
11. t1l1 plane-ride per-player cameras (Pattern A) + e2l1-style eject.

**P4 — blocked/asset:**
12. e3l3 rotation crash (missing panzer TIKs, Issue #18) — asset/precache, out of this doc's scope; blocks 16-player testing of e3l3.

---

## Cross-map REUSABLE HELPERS to build (so we don't hand-code each map)

Ranked by how many of these 12 maps (and the already-converted maps) they de-duplicate:

1. **`coop_freezeAllPlayersForIntro` / `coop_releaseAllPlayers`** (NEW, highest reuse).
   Replaces bare `freezeplayer`/`releaseplayer`. Loops `1..$player.size`: per-player physics_off +
   optional viewangles set + drawhud control; release reverses it. Used by t1l2, t1l3, t2l1, t2l3,
   t3l1 (5 maps) and any future cinematic intro. Eliminates the global-freeze-steals-everyone bug.
   Model on `coop_mod/main.scr:427 playersWarpto` loop shape.

2. **`coop_applyToAllPlayers <label/cmd>`** (NEW, generic fan-out).
   A thin loop helper that runs a given per-player action (fullheal, takeall, loadout, give weapon,
   playsound, viewangles) over every non-spectator player. Collapses dozens of singular `$player X`
   intro lines across ALL t-maps into one call. (Even a convention + snippet, if a true higher-order
   call is awkward in MOHAA script, beats copy-paste.)

3. **`startRideCameras` / `stopRideCameras` (Pattern A generic)** (from vehicle plan helper #1).
   Per-player ride-camera spawn-manager + `trigger_camerause`+`doUse` switch + late-join + eject +
   `cueplayer` teardown. 5 near-duplicate copies exist (m1l1, e1l1/scene1, e1l4/Intro, e2l1). Needed
   for t1l1 plane ride and (optionally) t1l3 bridge-collapse cam and t3l2 endgame cam.

4. **`setupEscortVehicle` / 16-seat vehicle handler (Pattern B generic)** (from vehicle plan helper #2).
   Extend the m1l3b jeep-coop family (currently caps at 8 seats: playerAttach2..8) to **16 seats**,
   parameterized (vehicleEnt, passengerTag, gunName, seat offsets, seatCount). Needed for t2l2
   halftrack; shared with m1l3b/c and m2l3 truck. Includes the "walk-alongside + geofence stragglers"
   fallback for when 16 > available seats.

5. **`validateTriggerActivator` call-convention** (EXISTS, replace.scr:2507 — just apply it).
   The fix for every `parm.other==$player` / `parm.owner==$player` gate. Where a small set is valid
   (e.g. `$player || $cappy` in t2l4), extend to accept a validActivator LIST. Used by t2l2, t2l4,
   t3l2, t1l2, t1l3. No new helper — standardize usage + add a list-accepting variant.

6. **`coop_quorumGate <volume/origin> <count>` / `coop_anyPlayerInVolume`** (NEW, optional).
   For "wait for THE player to reach X" sequences where any-player isn't quite right (e.g. don't
   advance until N players are staged). Wraps a trigger/volume test over all players. Lower priority —
   most reach-gates are fine as any-player.

7. **Objective broadcast: NOT needed.** Engine `addobjective` already replicates to all 16 and seeds
   late joiners. Do NOT build a custom objective-broadcast helper for these maps (unlike the AA
   slots-7/8 case). Just ensure completion semantics (any/all/counter) are chosen correctly per the
   objectives sub-plan.

---

## Parse-hygiene reminders (apply to every edit)
- ASCII only. The 0x92 bytes above are the proof: one byte kills the whole file silently. Scan with
  `perl -ne 'print "$.\n" if /[^\x00-\x7F]/'` after editing; expect empty output.
- No UTF-8 BOM. Use Edit/Write tools (no BOM) or `-Encoding ASCII`. First byte must not be 0xEF.
- `$player` is 1-indexed; loops start at 1, go to `$player.size`; NULL-check each `$player[i]`.
- No bare negative as first token after `(` (write `( -N`); no em-dash; keep `while(`/`if(`
  conditions on one line.
- `$player.netname` (not `.name`); no `waittill death` on Player (poll health).
- `freezeplayer`/`cuecamera`/`cueplayer`/`releaseplayer` are GLOBAL — never use bare in a
  per-player context.

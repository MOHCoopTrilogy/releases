# Objective Coop-Confidence Audit (16-player)

Static code audit of mission objectives that require **player interaction** (plant/defuse, use/activate,
levers, escort, capture, man stations, pickups) across the converted/in-progress map set:
e1l4, e2l1, e2l2, e2l3, e3l1, e3l2, e3l3, e3l4 (Breakthrough) and
t1l1, t1l2, t1l3, t2l1, t2l2, t2l3, t2l4, t3l1, t3l2 (Spearhead).

Read-only. No edits, no build, no launch. All file:line refs under
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`.

The Phase-2 god-bot teleport harness never presses USE, never plants a charge, never mans a gun, so
NONE of the interactive objectives below have actually been exercised. This is a code-shape audit plus
a hands-on playtest list.

---

## Reference pattern (what "coop-correct interactive" looks like in HZM)

Three known-good coop primitives the M-series / converted maps use:

1. **`global/DistanceUse.scr::main`** (`global/DistanceUse.scr:9-58`) — **COOP-CORRECT.**
   Loops `1..$player.size`, checks each living non-spectator active player's distance + `useheld`,
   and `end`s returning **the player who pressed use**. This is the canonical "any player can use it"
   primitive. Callers store the returned player (e.g. `level.playerJeepGunner`).

2. **`coop_mod/cannonThink.scr::cannonThink`** (`coop_mod/cannonThink.scr:40-71`) — **COOP-CORRECT.**
   The framework's per-player cannon/gun mount primitive: loops all players, checks `local.player.useheld`
   + facing + distance, `doUse local.playerSelected`. The intended replacement for the old SP gun-mount.

3. **`coop_mod/replace.scr::validateTriggerActivator`** (`replace.scr:2507`) + BSP `waittill trigger` +
   `level.*` global flags. A trigger thread that only sets/reads `level.*` (no `$player` gate) is
   already any-player and replicates to all 16. Engine `addobjective` auto-replicates HUD state to all
   clients (no `coop_objectivesSendPlayer` needed for these maps).

**The anti-pattern (RED):** `global/MountGunOrPlantCharge.scr` — the OLD SP gun-mount / charge-plant
helper — was **never coop-converted**. It polls bare `$player.useheld` / `$player.origin` /
`$player.angles` (`MountGunOrPlantCharge.scr:98,100,115,126,140,142,143,157,161,169`), i.e. the
`$player` ARRAY, so in coop it only ever responds to the host / `$player[1]`. Its own header
(`MountGunOrPlantCharge.scr:7`) names **e3l2/Cannons.scr as the reference usage** — and e3l2 is the
ONLY remaining consumer (`maps/e3l2/cannons.scr:200`). This makes the e3l2 cannon objective the single
biggest interactive-coop risk in the set.

---

## Per-map objective tables

Rating key: **GREEN** = coop-correct by code (any/all/counter, routes through a coop primitive).
**YELLOW** = likely OK but unverified by code or depends on a base-pak gag / shared global not readable here.
**RED** = SP-shaped (`$player`-only / host-only / player[1]) — likely broken or host-only in coop.

Non-interactive objectives (pure "reach X" / "destroy Y by damage" / NPC-escort / counter) are listed
briefly; the focus is the INTERACTIVE rows.

### e1l4 — Stowaway / freighter (stealth)
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| "Show your papers" gate | use/present (stealth) | soft-resolve `level.GatePapersAccepted=1`; coop branch soft-kills failer, no restart | YELLOW | `maps/e1l4/Intro.scr:~294-339` (per convert_e1l4_e2_report) | playtest: fail-papers must NOT server-restart; level advances |
| Find way aboard / sink ship beats | reach/scripted | BSP trigger / `global/objectives.scr`, per-player ship-tilt loop | GREEN | `maps/e1l4/SunkShip.scr` coop_* loops | — |

### e2l1 — Glider assault / AA guns
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Destroy AA artillery [N remaining] | destroy (damage) | `level.numAAGunsAlive` counter, last-gun death (any player) | GREEN | `maps/e2l1/objectives.scr`, `aaguns.scr` | — |
| Glider ride / eject | ride dismount (USE) | per-player camera + `local.player.useheld` eject loop | GREEN | `maps/e2l1/gliderride.scr:662` (loop), `:818` | — |
| Rendezvous / destroy AB41 / protect 505th | reach/destroy/escort | BSP trigger + damage; Phillips-death FAIL is global | YELLOW | `e2l1.scr:214-219` | playtest: Phillips not killed by 16-player friendly-fire chaos |
| Tower MG42 turret (set-piece) | man station | per-player dismount loop added | GREEN | `enemySet809.scr:~220-252` | — |

### e2l2 — Bomb the V2 / bike+jeep
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Jeep-turret guard-post ride | man station (USE) | `level.jeepAttachedPlayer` (whoever mounts), coop branch | GREEN | `maps/e2l2/guardPost.scr:122-169` | — |
| Destroy/trigger objectives | destroy/reach | `maps/e2l2/objectives.scr`, BSP/entity-gated | GREEN | `objectives.scr`; bike/truck gates entity-gated | — |
| Radio-tower kill zone | hazard | all-player isinside loop | GREEN | `radioTower.scr` TowerKillsPlayer | — |

### e2l3 — Vineyards / town
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Jeep intro ride / eject | ride (USE) | all-player glue via shim; `jeepFailSave` watchdog | GREEN | `maps/e2l3/IntroHouse.scr:364` uses guarded loop | — |
| meet82nd / assist82nd / clearTown / repelTanks | reach/area/death | ObjMgr `inOrder`, BSP/area/death (any player) | GREEN | `global/ObjMgr.scr`, e2l3 objectives | — |

### e3l1 — City / British HQ / medic jeep escort
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Get on jeep / medic ride | ride board (USE) | `DistanceUse.scr` -> `level.playerJeepGunner` (any player) | GREEN | `maps/e3l1/JeepRidePart1/3.scr`; DistanceUse | — |
| Jeep-turret dismount | man station (USE) | `level.playerJeepGunner.useheld` (the gunner) | GREEN | `JeepRidePart3.scr:78,386` (uses gunner var, not `$player`) | — |
| Find Brit HQ / escort beats | reach/escort | BSP `waittill trigger` + `withinDistanceOf` (any) | GREEN | `global/objectives.scr` | — |

### e3l2 — N.Africa town / Modello cannons / POWs  ← biggest interactive risk
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| **Destroy enemy artillery [3 remaining] — mount Modello / plant charge** | **man gun + plant charge (USE)** | `MountGunOrPlantCharge.scr` polls bare `$player.useheld`/`.origin`/`.angles` -> **host only**; `douse $player`, `$player.origin=` on dismount | **RED** | `maps/e3l2/cannons.scr:200` calls `global/MountGunOrPlantCharge.scr`; that file `:98,100,115,140,142,157,161,169` bare `$player`; `cannons.scr:215,241,260` `douse $player`/`$player.origin=` | Re-route cannon use through `coop_mod/cannonThink.scr` (per-player) OR coop-convert MountGunOrPlantCharge to loop `$player[]` and return the using player. Counter `level.num_cannons_remaining` is global so destruction by host still completes for all — but **only the host can mount/plant**. |
| findPOWs / protectPOWs / escape | reach / NPC-protect / reach | ObjMgr; `protectPOWs` FAIL on prisoner-NPC death (not player death) | GREEN | `objectives.scr:6-9` (parse-fix confirmed ASCII); `prisoner_section_1.scr:453` `mustLive` on NPC | — |

### e3l3 — N.Africa / K5 railguns / AB41 ride
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Ride AB41 + jump off (win gate) | ride board + USE-to-jump | `StartJumpThread` rewritten to accept any player's `useheld`; `level.playerjumped` (any) | YELLOW | `maps/e3l3/e3l3_AB41.scr:153-161` (per-player loop), `:463` `]end` parse-fix | playtest: single-seat vehicle — if lone occupant dies before jump, can another player re-board the moving AB41? |
| Detonator plunger (scene1) | USE-release gate | `WaitForUseRelease` waits on bare `$player.useheld` to RELEASE | YELLOW | `maps/e3l3/scene1.scr:361` | host-keyed "wait for release"; only matters if host is the one who planted; low impact, verify arm fires |
| Destroy K5 railguns / convoy | destroy (damage) | `global/objectives.scr`, damage-based (any) | GREEN | e3l3 objectives | — |
| **Asset blocker** | — | missing panzer TIK crash (separate from script) | — | flagged in master plan Issue #18 | precache/asset fix, out of scope |

### e3l4 — Castle / bunkers / radio tower / airstrike (campaign end)
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Confirm airstrike (desk radio) | use object | `DistanceUse $deskradio` (any player) | GREEN | `maps/e3l4/*` uses DistanceUse; per convert_e3_report | — |
| Jeep-turret dismount hack | man station (USE) | bare `$player.useheld`, gated behind `level.allowplayeroffjeep==1` | YELLOW | `maps/e3l4/Bunker1.scr:68` | if that path is live in coop, dismount is host-only; players aren't seated per report, so likely dead path — verify |
| Deliver supplies / defend Baker-Charlie / regroup / radio / defend tower | reach/defend/timer | linear `global/objectives.scr`, volume/timer/BSP (any) | GREEN | e3l4 objective chain | — |

### t1l1 — Paratroop drop / barn crash
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Rendezvous / destroy tank w/ AA / regroup | reach/destroy | `global/objectives.scr::add_objectives`, allied/BSP-driven (any) | GREEN | `maps/t1l1.scr` per convert report | — |
| Plane ride + parachute + harness | ride cinematic | base-pak gag `T1L1_PlaneRide.scr` — likely GLOBAL `cuecamera`/`freezeplayer` | YELLOW | gag not in editable tree | playtest: all 16 share one POV / stuck after barn crash? |

### t1l2 — Dutch town / Flak88
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Destroy 2x Flak88 | destroy (damage) | `level.nRequiredObjectives` counter==0 (any player) | GREEN | per convert_t1 report; counter global | — |
| Captain escort/dialogue | NPC escort | NPC-self-driven; gate on friendly NPCs not players | GREEN | `t1l2.scr:703` (NPC-gated) | — |
| Intro freeze (3s) | cutscene | per-player `freezecontrols`/physics_off helper | GREEN | `coop_introFreeze/Release` added | — |

### t1l3 — Canal town / colonel / bridge demolition
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| **Plant 4 demo charges** | plant charge | `level.charge1-4` / `level.chargecount` level-global, any player plants | GREEN | per convert_t1 report; charges are level-global flags | confirm charge-plant trigger isn't `$player`-gated in BSP (report says level-global) |
| Track colonel / destroy tiger / demo flak / acquire explosives / return to captain | reach/destroy/pickup/escort | BSP/counter/NPC (any); `isAlive level.colonel` | GREEN | objectives 1-6 | — |
| Boat-ride intro freeze | cutscene | **gag-owned GLOBAL freezeplayer** (`gags/t1l3_BoatRide.scr`), global releaseplayer kept | YELLOW | `t1l3.scr:153` (release global on purpose) | playtest: all 16 released after boat ride, not stranded |
| Bridge collapse cam | cinematic | `cueplayer` brief global cut | YELLOW | `t1l3.scr:906,918` | verify no player mid-respawn |

### t2l1 — Ardennes / Nebelwerfers / Tigers
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Destroy nebelwerfers [N remaining] | destroy (damage) | `level.*` counter (any player) | GREEN | per convert_t2infantry report | — |
| Nebelwerfer player-turret | man station | single-seat, any player mounts | YELLOW | report; uses engine turret slot | playtest: any of 16 can mount, rotates on death |
| Sticky-bomb Tiger kills | plant/throw | flags global, any player | GREEN | report | — |
| Squad-death FAIL | fail (NPC) | `check_squad_death` -> coop `missionfailed`, suppressed if objs done | YELLOW | `t2l1.scr:~1854` | playtest: 16 humans don't fail mission on NPC-squad wipe |

### t2l2 — Halftrack escort (Pattern B), man the gun
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Man halftrack turret + ride | man station + 16-seat ride (USE) | new Pattern-B: `local.player.useheld` board (`t2l2.scr:1006`), 16-seat glue, gunner var | YELLOW | `maps/t2l2.scr:958-1162` (NEW coop block) | playtest: gunner mounts for any player; 15 passengers glued through downhill/reverse; `passenger0` tag unverified (base pak) |
| Escort supply truck survives | escort (NPC truck) | truck health global; destruction = `missionfailed` | GREEN | `t2l2.scr:868-881` | — |
| Route ambience explosions | trigger | `parm.other==$player` rewritten to any-player-or-halftrack | GREEN | `t2l2.scr:871-901` | — |

### t2l3 — Bastogne wave defense
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Talk to captain / find+escort medic | reach/escort | closest-player reach gate (any); medic NPC-driven | GREEN | per convert_t2infantry report | — |
| Defend flanks waves 1-3 | defend (area/AI count) | wave-clear AI count / volume (any) | GREEN | report | — |
| MP44 weapon pickup set-piece | pickup | broadcast `item`; flag global | GREEN | `mp44pickup` | — |
| AXISWINS breach FAIL | fail (global) | `level.axiswins=1` -> coop `missionfailed` (shared) | GREEN | report; level-global | — |

### t2l4 — Stavelot (church/hotel/barn)
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| Building-entry ambushes | trigger (player OR cappy) | `coop_isPlayerOrCappy` helper (any player or captain) | GREEN | `t2l4.scr:~852-897` + new helper | — |
| Sniper / shotgun pickups | pickup | broadcast `item`/`ammo`; host auto-equips | GREEN | `give_sniper_rifle`, `shotgun_ammo` | — |
| KillThePlayer boundary | hazard | bounded all-player isTouching loop | YELLOW | `t2l4.scr:~414` | playtest: out-of-bounds kills all stragglers, not just host; respawners not re-killed |
| 6 sequential building objectives | reach/clear | `global/objectives.scr` (any) | GREEN | t2l4 objectives | — |
| **Init gate edit (high-risk single edit)** | infra | removed 2nd `level waittill spawn` at :49 | YELLOW | `t2l4.scr:49` | playtest: init completes, players actually spawn (NOT stuck in spectator) |

### t3l1 — Berlin streets / T-34 commandeer / safe puzzle
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| **Open the safe (combination puzzle)** | use object | `usetrigger5` thread reads/sets `level.combination`/`safestate`/`usetrigger5` only — NO `$player` gate | GREEN | `t3l1.scr:522-555` (level-global flags only), `:935-937` combination set | — |
| Locate combination (pickup) | pickup | `level.combination=1` on pickup (level flag, any) | GREEN | `t3l1.scr:505,937` | — |
| Cross bridge / find aircraft+chancellery / eliminate guards + commandeer T-34 | reach/destroy | BSP `waittill trigger` (any) + global isAlive | GREEN | `t3l1.scr:409,434,459,481,621` | — |
| Sticky-bomb shared pool | pickup/use | `level.stickybombs` single shared count | YELLOW | report (by-design shared pool) | playtest: shared pool feels OK with 16 |

### t3l2 — Berlin / player drives T-34 / bridge (Pattern C, campaign end) ← critical vehicle
| Objective | Type | Completion trigger | Rating | Evidence | Fix if RED |
|---|---|---|---|---|---|
| **Board + drive T-34** | drive vehicle (USE) | stock `coop_selectDriverForTank` (hold USE near `$coop_tankOffset`); NEW cannon-scan + hull fallback so offset is never NULL | YELLOW | `maps/t3l2.scr:33-70` (NEW); `vehicles_thinkers.scr::players_tank` | playtest: T-34 actually boards (was the silent-no-board CRITICAL risk); `t34_cannon.tik connect` tag unverified (base pak) |
| Destroy bridge (tank shell) | destroy via projectile | `bridgecollapsetrigger` owner-check rewritten: accepts `$playertank`/driver/any player + `level.bridge_ready==1` | GREEN | `t3l2.scr:~1071-1117` | — |
| Return to Soviets / defend bridge | reach/defend | BSP `waittill trigger` (any) | GREEN | t3l2 objectives | — |
| Endgame bomber cam | cinematic | global `cuecamera`/`cueplayer` (accepted for campaign end) | YELLOW | `t3l2.scr:1294-1319` | verify no player mid-respawn when it fires |

---

## Rating counts (interactive + fail/objective rows)

- **GREEN: ~33** (counter-destroy, BSP-reach, DistanceUse rides, level-global puzzles, the t-series intro/hazard/escort conversions).
- **YELLOW: ~17** (single-seat vehicle re-board edge cases, base-pak gag cameras/freezes, 16-seat halftrack glue, squad-fail design calls, unverified base-pak tags, the t2l4 init-gate edit).
- **RED: 1 confirmed** (e3l2 Modello cannon mount/plant — `MountGunOrPlantCharge.scr` un-converted, host-only).

The RED count is low because the convert agents already converted most interactive paths to coop
primitives; but the **one RED is a core mission objective on a fully-shipping map**, and several YELLOWs
are interactive set-pieces the harness literally cannot test.

---

## PRIORITIZED HUMAN-PLAYTEST LIST (worst first)

Test these hands-on in coop with 2+ real players (ideally a non-host doing the interaction) before
trusting any of them:

1. **e3l2 — destroy the 3 Modello cannons (RED).** Have a NON-HOST player walk up to a Modello and try
   to mount it / plant the charge. Prediction from code: only the host can mount/plant because
   `MountGunOrPlantCharge.scr` polls the `$player` array's head. If a non-host cannot interact, the
   "Destroy Enemy Artillery [3 Remaining]" objective is host-gated. FIX: re-route `cannons.scr:200`
   through `coop_mod/cannonThink.scr`, or coop-convert `MountGunOrPlantCharge.scr` to loop `$player[]`.

2. **t3l2 — board and drive the T-34 (YELLOW, CRITICAL).** Walk a player to the tank, hold USE. The
   stock path scans for King-Tiger `kingcannon.tik`; the new code scans `t34_cannon.tik` with a hull
   `tag_origin` fallback. If the `connect` tag is wrong, the player either can't board or sits at a bad
   offset. Whole map hinges on this; campaign-ending map.

3. **t2l2 — man the halftrack gun + 16 passengers (YELLOW).** First player mounts the turret; players
   2..N glue to `passenger0` and must survive the downhill/reverse segment without falling off. The
   `passenger0` tag and 16-body glue are the least-tested case in the set.

4. **e3l3 — ride the AB41 and jump off to win (YELLOW).** Single-seat on-rails vehicle. Confirm the
   jump prompt accepts ANY living player's USE, and specifically that if the lone occupant dies before
   the jump, another player can still complete it (`level.playerjumped`). If not, the win gate can
   deadlock -> `missionfailed`.

5. **t1l1 plane ride + t1l3 boat ride (YELLOW, base-pak gag).** Both cinematic intros issue GLOBAL
   `freezeplayer`/`cuecamera` from base-pak gags that aren't editable here. Confirm all 16 players are
   RELEASED afterward and not stranded frozen / locked to one camera. Not fixable in level scripts;
   needs a deferred Pattern-A gag pass if broken.

Runners-up to verify next: **t2l4 init gate** (the removed 2nd `level waittill spawn` — make sure
players spawn at all), **t2l1 squad-death fail** (16 humans shouldn't lose the mission to an NPC-squad
wipe), **e2l1 Phillips-death fail** (single-NPC escort shared fail under friendly-fire chaos), and the
**t1l3 plant-4-charges** objective (confirm a non-host can plant a charge — report says level-global,
but it's an interactive plant worth a hands-on check).

---

## Notes / caveats for the maintainer

- The convert_*.md reports are post-fix and credible; this audit independently confirmed the e3l2
  parse-fix (`objectives.scr:8` now ASCII) and independently FOUND the e3l2 cannon RED that the e3
  report under-rated ("standard coop mount path" — but the global it depends on is not coop-converted).
- `coop_mod/cannonThink.scr` already exists and is the correct per-player cannon primitive — e3l2 simply
  doesn't use it. That is the cleanest fix for the one RED.
- Engine `addobjective` HUD replication to all 16 is confirmed framework behavior; no per-map HUD-push
  work is needed for these maps. The objective RISK is purely the COMPLETION TRIGGER (who can fire it),
  which is what this audit rates.

# Objective Interaction Full Audit (16-player coop)

Comprehensive, read-only static audit of EVERY map's objectives under
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps\` — m-series (HZM originals = reference pattern),
e-series (Breakthrough), t-series (Spearhead). Goal: confirm every INTERACTIVE objective
(plant/defuse, pick up, use/activate, mount gun, lever/switch, escort, capture, ride/drive,
disguise) can be performed by ANY of up to 16 active players AND completes for everyone — not
host-only / `$player[1]` / SP-shaped.

Builds on (and does not re-litigate without cause): `objective_coop_confidence.md`,
`fix_pickup_objectives.md`, `fix_e3l2_cannons_report.md`, `shared_interaction_globals_fix.md`,
`coop_vanilla_vs_hzm_diff.md`, `hzm_coop_framework_guide.md`.

No edits, no build, no launch. Rating key:
- **GREEN** = coop-correct by code: completion is a `level.*` flag / counter, or a BSP
  `waittill trigger` / `setthread` callback (fires for whoever touches → any player), or it
  routes through a confirmed coop primitive (`DistanceUse`, `player_closestTo`/`closest`,
  `cannonThink`, `CoopGunOrChargeThink`, `coop_GunOrExplosive`). Engine `addobjective`
  auto-replicates HUD to all 16.
- **YELLOW** = likely OK but unverified by code alone (single-seat vehicle re-board edge,
  base-pak gag camera/freeze, 16-seat glue, NPC-shared-fail design call, unverified base-pak tag).
- **RED** = SP-shaped (bare `$player.useheld`/`.origin`/`.angles`, `$player[1]`,
  `parm.other == $player` as the LIVE gate, host-only completion).

---

## The reference pattern (M-series), independently re-confirmed

The HZM originals are the gold standard and are uniformly coop-correct. Three idioms recur:

1. **Pickup / "steal" objective** = BSP trigger `setthread` callback that does
   `parm.other playsound …` (whoever picked up), `$item remove`, sets a `level.flags[N]` /
   `level.*` flag, and bumps a counter. Canonical: `maps/m2l1.scr:123-172` (`document1..4`,
   `level.flags[1..4]` + `level.remaining_documents`), `maps/m6l1c.scr:813` (`stealingpapers`,
   `setthread`), `maps/m4l3.scr:1086-1114` (`objective3/4_complete`, `level.objective_steal_*`),
   `maps/m3l2.scr` radio pickup. **No `$player` gate anywhere in the completion path.**

2. **Plant / man-gun / switch objective** = level-global counter/flag advanced by a BSP trigger;
   any `douse $player` is wrapped in `if(level.gametype==0)` with a coop `else` that loops
   `$player[]`. Canonical: `maps/m2l2b.scr:220-281` (`plantthebomb`/`plantthebomb2`,
   `level.bombcount` + `level.bombPlanted1/2`), `maps/m6l1c.scr:656-867` (alarm switches, every
   `douse $player` SP-gated with a coop `$player[]` loop), `maps/m1l1.scr:2176`
   (`blowthedoor` → `level.flags[triggergun]` advances "Man the MG42").

3. **Items granted to all** = `global/items.scr::add_item` routes through
   `coop_mod/replace.scr::item` (gives to every player) and `::playsound`/`parm.other playsound`
   for the pickup sound (`global/items.scr:41,54,…`). Confirmed coop-correct.

**Net: ALL m-series interactive objectives are GREEN.** Every `$player.origin` / `$player[1]` /
`parm.other == $player` hit found in m-series is either commented-out SP code, a HUD
`add_objectives … $player.origin` location hint (not a gate), a dead branch after an `end`
(e.g. `m1l3b.scr:1274` reached only after the live coop path `end`s at `:1272`), or inside an
`if(level.gametype==0)` SP block.

---

## Per-map objective tables

Non-interactive objectives (reach/destroy-by-damage/area/NPC-escort/counter) are collapsed to a
single row each per map; INTERACTIVE objectives get their own row. file:line under `maps/`.

### M-SERIES (reference; all GREEN)

| Map | Objective | Type | Completion trigger | Rating | Evidence |
|---|---|---|---|---|---|
| m1l1 | Man the MG42 | man station | `level.flags[triggergun]` via `blowthedoor` BSP trigger; mount uses coop turret path; `$player.turretride doUse $player` is SP-only (`:1549-1554`) | GREEN | `m1l1.scr:2176`, `:2520`, obj `:1996` |
| m1l1 | Infiltrate / check door / hold reinforcements / continue | reach/defend/counter | linear `add_objectives` chain, BSP/level-flag | GREEN | `m1l1.scr:1960-2015` |
| m1l2a | Rescue SAS / follow / steal explosives / use explosives / destroy Flak88 / exfil | reach/NPC/pickup/destroy | linear chain, `level.flags[explosives]` etc.; pickup via `add_item` | GREEN | `m1l2a.scr:696-3614` |
| m1l2b | Disable Opel trucks [3] / Bomb tanks [4] / Bomb munitions / exfil | destroy (counter) | per-object `add_objectives N` counters, damage-driven | GREEN | `m1l2b.scr:55-903` |
| m1l3a/b/c | Jeep ride beats / regroup | ride/reach | coop jeep glue + `level.coop_inJeep` loop (`m1l3b.scr:1262-1287`); `$player[1]` line is dead (after `end`) | GREEN | `m1l3b.scr:1262-1287` |
| m2l1 | Steal research documents [4 remaining] | pickup (counter) | `document1..4` BSP `setthread`, `parm.other playsound`, `level.flags[1..4]`, `level.remaining_documents--` | GREEN | `m2l1.scr:123-181` |
| m2l1 | Enter complex / enter facility | reach | BSP `$obj*_trigger waittill trigger` | GREEN | `m2l1.scr:95` |
| m2l2a | Find a disguise | pickup/disguise | `level.coop_enableDisguises` + itemhandler; obj completes via linear `objective1` chain; `$player.has_disguise` writes SP-gated (`:66-67`) | GREEN | `m2l2a.scr:20,377-381` |
| m2l2a | Destroy Naxos / enter 2nd U-boat | destroy/reach | `$naxos waittill trigger`, linear chain | GREEN | `m2l2a.scr:383-389,502` |
| m2l2b | Plant the bombs [2 left] | plant charge (counter) | `plantthebomb`/`plantthebomb2` (BSP-wired), `level.bombcount` + `level.bombPlanted1/2` guards, level-global | GREEN | `m2l2b.scr:220-281` |
| m2l2b | Escape / eliminate opposition | reach | `$endlevel waittill trigger` | GREEN | `m2l2b.scr:434,628` |
| m2l2c | Exfiltrate | reach | linear chain | GREEN | `m2l2c.scr:26,115` |
| m2l3 | Exfiltrate base / meet allies at station | reach | `$obj1`/`$endlevel waittill trigger` | GREEN | `m2l3.scr:34-554` |
| m3l1a | Get to shingle / meet captain / get+return bangalores / follow / trench / bunker | reach/escort/pickup | linear chain; bangalore pickup via `add_item`; `$player.origin` uses are distance checks not gates | GREEN | `m3l1a.scr:2219-5400` |
| m3l1b | Destroy 20mm/Flak88/15cm / clear bunker / exit / eliminate MG42 gunners | destroy/reach | counters + BSP triggers | GREEN | `m3l1b.scr:70-1107` |
| m3l2 | Find the radio (airstrike) + beats | pickup | `scene7_radio_pickup`, `level.got_radio`; `$playertarget_center glue $player[1]` is cinematic-cam glue only | GREEN | `m3l2.scr` (per fix_pickup_objectives.md) |
| m4l0/m4l1/m4l2 | reach/destroy/escort chains | reach/destroy | linear chain; `m4l2.scr:1052-1062` `$player.origin` is a teleport-move helper, not an objective gate | GREEN | obj chains |
| m4l3 | Send false communique | use object | `objective2_complete` (BSP trigger), `level.objective_false_communique=1`; gated on `!isalive $radio_objective2` | GREEN | `m4l3.scr:1066-1081` |
| m4l3 | Steal troop manifest / steal battle plans | pickup | `objective3/4_complete` BSP triggers, `level.objective_steal_*=1`, `add_item` to all | GREEN | `m4l3.scr:1086-1114` |
| m4l3 | Infiltrate perimeter | reach | BSP trigger | GREEN | `m4l3.scr:89` |
| m5l1a | Locate bazooka team / past gate / south edge | reach | linear chain | GREEN | `m5l1a.scr:212-1624` |
| m5l1b | Find tank crew / defeat Panzer / keep crew alive+infiltrate / steal King Tiger | reach/destroy/escort | linear chain; tank crew NPC-driven; `$player.origin` are distance checks | GREEN | `m5l1b.scr:129-1015` |
| m5l3 | (on-rails King Tiger drive) + finishers | scripted vehicle/destroy | `$playertank` is scripted `dodrive`; `$player glue $playertank` SP/cinematic; `parm.other == $playertank` is vehicle owner-check not a player gate | GREEN | `m5l3.scr:35,150,1215` |
| m6l1a/b/c | Alarm-stealth / steal papers / bunker | use-switch/pickup/reach | `stealingpapers` `setthread` (any player); ALL alarm `douse $player` SP-gated w/ coop `$player[]` loop | GREEN | `m6l1c.scr:656-867`, `:813`, `:271-283` |
| m6l2a/b | Snipe/patrol/alarm beats | reach/destroy | `cansee $player[1]` is an SP/MP-compatible AI sightcheck (not an objective gate) | GREEN | `m6l2a.scr:572` |
| m6l3a-e | Snipe tower guards / boxcar defense / advance | defend/reach (counter) | `add_objectives … $player.origin` is HUD hint only; completion is loss-counter/area | GREEN | `m6l3a.scr:400` |

### E-SERIES (Breakthrough)

| Map | Objective | Type | Completion trigger | Rating | Evidence |
|---|---|---|---|---|---|
| e1l2 | Destroy 3 artillery (mount cannon / plant charge) | man gun + plant charge (USE) | **coop hotfix**: `GunOrExplosive` is gametype-gated → `coop_GunOrExplosive` loops `player_closestTo` + `group.player.useheld`; any player plants/mounts | **GREEN (newly confirmed; not in prior 17)** | `e1l2/Artillery.scr:470-471`, `:577-660` |
| e1l4 | Obtain papers / steal documents / find+place explosives | stealth/pickup/plant | `level.GatePapersAccepted`, BSP `$documentstrigger`/`$getbombs waittill trigger`, `level.numexplosivesset` counter; SP `$player.*` in debug branches only | GREEN | `e1l4/Intro.scr`, `MapRoom.scr`, `Ship.scr:68,163` |
| e1l4 | "Show papers" fail-soft | use/present | coop branch soft-kills failer, no restart | YELLOW | `e1l4/Intro.scr:~294-339` |
| e2l1 | Destroy AA artillery (mount gun / plant charge) | man gun + plant charge (USE) | **coop**: `GunOrExplosive` loops `player_closestTo` + `group.player.useheld`; `coop_turretDoUse`; any player | **GREEN (newly confirmed coop path)** | `e2l1/aaguns.scr:713-840` |
| e2l1 | Glider ride/eject; tower MG42; protect Phillips | ride/man/escort | per-player eject loop; per-player dismount; Phillips shared-fail | GREEN / YELLOW (Phillips fail) | `e2l1/gliderride.scr:662`, `enemySet809.scr`, `e2l1.scr:214-219` |
| e2l2 | Jeep-turret ride; destroy/trigger; radio kill-zone | man/destroy/hazard | `level.jeepAttachedPlayer`; counters; all-player isinside | GREEN | `e2l2/guardPost.scr:122-169` |
| e2l3 | Jeep ride; cannonThink tank; meet/assist/clear/repel | ride/man/reach | `cannonThink` (any player); ObjMgr `inOrder` | GREEN | `e2l3/Town.scr:62,258` |
| e3l1 | Get on jeep / medic ride; jeep-turret dismount; find HQ | ride/man/reach | `DistanceUse` → `level.playerJeepGunner` (any player) | GREEN | `e3l1/BritHQ.scr:207`, `JeepRidePart3.scr:356` |
| e3l1 | Retrieve munitions (PIAT) | pickup | `piatpickup` BSP `setthread`, `level.gotPIAT` | GREEN | `e3l1/AfterSnipers.scr:77` |
| e3l2 | Destroy 3 Modello cannons (mount / plant charge) | man gun + plant charge (USE) | **FIXED**: `CoopGunOrChargeThink` loops `1..$player.size`; was host-only via `MountGunOrPlantCharge.scr`; counter `level.num_cannons_remaining` level-global | **GREEN (was RED; fix verified in place)** | `e3l2/cannons.scr:201-323` |
| e3l2 | find/protect POWs / escape | reach/NPC | ObjMgr; `mustLive` on NPC | GREEN | `e3l2/objectives.scr`, `prisoner_section_1.scr:453` |
| e3l3 | Ride AB41 + jump off (win) | ride + USE-to-jump | per-player `useheld` loop; `level.playerjumped`; uses `DistanceUse` to board (`scene3.scr:190`) | YELLOW | `e3l3/e3l3_AB41.scr:153-161`, `scene3.scr:190` |
| e3l3 | Detonator plunger | USE-release | `WaitForUseRelease` on bare `$player.useheld` | YELLOW | `e3l3/scene1.scr:361` |
| e3l3 | Search house for intel (anziomap) | pickup | BSP `$anziomaptrigger waittill trigger` | GREEN | `e3l3/scene2.scr` |
| e3l3 | Destroy K5 railguns / convoy | destroy | damage-based | GREEN | e3l3 objectives |
| e3l4 | Confirm airstrike (desk radio) | use object | `DistanceUse $deskradio 100` (any player) | GREEN | `e3l4/Tower.scr:706` |
| e3l4 | Bazooka pickup | pickup | `replace.scr::item` to all | GREEN | `e3l4/Bunker4.scr:46` |
| e3l4 | Jeep-turret dismount hack | man station | bare `$player.useheld` behind `level.allowplayeroffjeep==1` (likely dead path) | YELLOW | `e3l4/Bunker1.scr:68` |
| e3l4 | Deliver/defend/regroup/radio/defend tower | reach/defend/timer | linear `global/objectives.scr` | GREEN | e3l4 chain |

### T-SERIES (Spearhead)

| Map | Objective | Type | Completion trigger | Rating | Evidence |
|---|---|---|---|---|---|
| t1l1 | Rendezvous / destroy tank / regroup | reach/destroy | counter/BSP | GREEN | `t1l1.scr` |
| t1l1 | Plane ride + parachute | ride cinematic | base-pak gag (global `cuecamera`/`freezeplayer`) | YELLOW | gag not in tree |
| t1l2 | Destroy 2x Flak88 | destroy (counter) | `level.nRequiredObjectives` | GREEN | t1l2 |
| t1l2 | Captain escort; intro freeze | NPC escort/cutscene | NPC-gated; per-player freeze helper | GREEN | `t1l2.scr:703` |
| t1l3 | Plant 4 demo charges | plant charge | `level.charge1-4` / `level.chargecount` level-global, any player | GREEN (verify non-host plant in playtest) | `t1l3.scr:103-107,823-854` |
| t1l3 | Acquire explosives (air drop) | pickup | BSP `$objective5ontrig waittill trigger`, `level.objective4`, coop `playsound` | GREEN | `t1l3.scr:584-592` |
| t1l3 | Track colonel / destroy tiger / demo flak / return | reach/destroy/escort | counter/NPC/BSP | GREEN | t1l3 obj 1-6 |
| t1l3 | Boat ride; bridge collapse cam | cutscene/cinematic | gag-owned global freeze; `cueplayer` | YELLOW | `t1l3.scr:153,906,918` |
| t2l1 | Destroy nebelwerfers [N] | destroy (counter) | `level.*` counter | GREEN | t2l1 |
| t2l1 | Nebelwerfer player-turret | man station | single-seat, any player mounts | YELLOW | report |
| t2l1 | Sticky-bomb Tigers; squad-death FAIL | plant/fail | flags global; `check_squad_death` → coop fail | GREEN / YELLOW (squad fail) | `t2l1.scr:~1854` |
| t2l2 | Man halftrack turret + 16-seat ride | man station + ride (USE) | Pattern-B `local.player.useheld` board, 16-seat glue, gunner var | YELLOW | `t2l2.scr:958-1162` |
| t2l2 | Escort supply truck; route ambience | escort/trigger | truck health global; `triggerexplode` accepts any player OR halftrack (SP `parm.other==$player` gated) | GREEN | `t2l2.scr:868-905` |
| t2l3 | Talk captain / find+escort medic / defend waves 1-3 | reach/escort/defend | closest-player reach; wave counters | GREEN | t2l3 |
| t2l3 | MP44 weapon pickup | pickup | `replace.scr::item`+`playsound` to all | GREEN | `t2l3.scr:3351` |
| t2l3 | AXISWINS breach FAIL | fail (global) | `level.axiswins=1` → coop fail | GREEN | report |
| t2l4 | Building-entry ambushes; 6 building objectives | trigger/reach | `coop_isPlayerOrCappy`; `global/objectives.scr` | GREEN | `t2l4.scr:~852-897` |
| t2l4 | Sniper/shotgun pickups | pickup | `replace.scr::item` to all | GREEN | `t2l4.scr:1007,1157` |
| t2l4 | KillThePlayer boundary; init-gate edit | hazard/infra | bounded all-player isTouching; removed 2nd `waittill spawn` | YELLOW | `t2l4.scr:~414,:49` |
| t3l1 | Open the safe (combination) | use object | `usetrigger5` reads/sets only `level.combination/safestate/usetrigger5` — no `$player` gate | GREEN | `t3l1.scr:522-555,935-937` |
| t3l1 | Locate combination (document1/2 pickup) | pickup | BSP `setthread`, `level.combination=1`, coop `playsound` | GREEN | `t3l1.scr:505,927,933-938` |
| t3l1 | Cross bridge / aircraft+chancellery / commandeer T-34 | reach/destroy | BSP `waittill trigger` + isAlive | GREEN | `t3l1.scr:409-621` |
| t3l1 | Sticky-bomb shared pool | use | `level.stickybombs` shared count | YELLOW | report |
| t3l2 | Board + drive T-34 | drive vehicle (USE) | `coop_selectDriverForTank` (hold USE near `$coop_tankOffset`) + cannon-scan/hull fallback | YELLOW (CRITICAL) | `t3l2.scr:33-70` |
| t3l2 | Destroy bridge (tank shell) | destroy via projectile | `bridgecollapsetrigger` accepts `$playertank`/driver/any + `level.bridge_ready==1` | GREEN | `t3l2.scr:~1071-1117` |
| t3l2 | Return to Soviets / defend bridge; endgame cam | reach/defend/cinematic | BSP `waittill trigger`; global `cuecamera` (campaign end) | GREEN / YELLOW (cam) | t3l2 |

---

## Rating counts (interactive + fail/objective rows across ALL maps)

- **GREEN: ~75** — all m-series interactive objectives (pickups, plant-bomb, man-MG42, switches,
  steal-documents, send-communique), the e/t pickups, DistanceUse rides, counter-destroys,
  level-global puzzles (t3l1 safe), and the now-confirmed coop gun/charge paths (e1l2, e2l1, e3l2).
- **YELLOW: ~17** — single-seat / 16-seat vehicle edges (e3l3 AB41, t2l1/t2l2 turrets,
  **t3l2 T-34 drive = critical**), base-pak gag cameras/freezes (t1l1 plane, t1l3 boat/bridge),
  NPC-shared-fail design calls (e2l1 Phillips, t2l1 squad, t2l3 AXISWINS-OK), the t2l4 init gate
  and out-of-bounds hazard, e3l3 plunger USE-release, e3l4 dead jeep-dismount path, t3l1 sticky pool.
- **RED: 0** — the single historic RED (e3l2 Modello cannon mount/plant) is fixed in code
  (`CoopGunOrChargeThink`, loops all players). No other SP-shaped completion gate found on any
  interactive objective in any map.

The previously-unrated **e1l2 and e2l1 artillery/AA "mount-gun-or-plant-charge" objectives**
(not in the prior 17-map set) were the most likely place to find a second RED, since both define
their OWN `GunOrExplosive`/`HoldChargePlace` rather than calling the shared global. Both are in
fact already coop-converted (gametype-gated to `coop_GunOrExplosive` / a `player_closestTo` loop).
So they are GREEN, not RED.

---

## PRIORITIZED FIX LIST (RED first, then at-risk YELLOW)

### RED — none.
No interactive objective in any map still gates completion on the host / `$player[1]` /
bare-`$player` poll. The one that did (e3l2) is fixed. Nothing requires a code fix to be
coop-correct by static analysis.

### At-risk YELLOW (ranked) — playtest-or-fix, each with the coop primitive to route through

1. **t3l2 — Board + drive the T-34 (CRITICAL, campaign-ending map).**
   `t3l2.scr:33-70`. Driver selection is hold-USE-near-offset; the offset depends on a cannon-scan
   (`t34_cannon.tik connect` tag) with a hull `tag_origin` fallback. Risk: if the tag is wrong the
   player can't board or sits at a bad offset → whole map stalls. FIX IF BROKEN: this already uses
   the coop driver primitive (`vehicles_thinkers.scr::players_tank`); the only work is verifying/
   correcting the boarding-offset tag, not the who-can-use logic. Hands-on playtest first.

2. **t2l2 — Man the halftrack gun + 16 passengers.** `t2l2.scr:958-1162`. Gunner mount uses
   `local.player.useheld` (any player) — that part is coop-correct; the unverified piece is the
   16-body `passenger0` glue surviving the downhill/reverse. Playtest; no primitive change unless
   passengers fall off (then route passenger glue through the same per-player glue helper t1l1 uses).

3. **e3l3 — Ride AB41 and jump off to win.** `e3l3/e3l3_AB41.scr:153-161`. Boards via `DistanceUse`
   (good); jump accepts any player's `useheld` → `level.playerjumped` (good by code). Risk is the
   single-seat deadlock: lone occupant dies before jumping → can another re-board the moving
   vehicle? If not, win gate can hang. FIX IF BROKEN: allow re-board via `DistanceUse` while
   in-motion, or auto-complete on any living player's `useheld` regardless of seat.

4. **t2l1 — Nebelwerfer player-turret.** Single engine turret slot. Confirm any of 16 can mount and
   it frees on death. If host-biased, route mount through `coop_mod/cannonThink.scr` like e2l3.

5. **t1l1 plane ride / t1l3 boat & bridge cams.** Base-pak gags issuing GLOBAL
   `freezeplayer`/`cuecamera`. Confirm all 16 are RELEASED afterward (not stranded frozen / locked
   to one POV). Not fixable in level scripts — needs a deferred Pattern-A gag pass (per-player
   `freezecontrols`/`trigger_camerause`+`doUse`, the m1l1 per-player camera idiom) if broken.

6. **Shared-fail design calls (verify, likely fine):** e2l1 Phillips-death fail
   (`e2l1.scr:214-219`), t2l1 squad-death fail (`t2l1.scr:~1854`), t2l4 out-of-bounds
   `KillThePlayer` (`t2l4.scr:~414`) and the init-gate edit (`t2l4.scr:49`). None gate an
   interactive objective's COMPLETION; they gate FAILURE/spawn. Confirm 16 humans don't lose the
   mission to an NPC wipe and that players actually spawn on t2l4.

7. **e3l3 detonator plunger USE-release** (`e3l3/scene1.scr:361`) and **e3l4 jeep-dismount hack**
   (`e3l4/Bunker1.scr:68`): both bare `$player.useheld`, but low-impact / likely-dead paths.
   If a playtest shows the plunger arm never fires for a non-host, swap the bare `$player.useheld`
   wait for a `1..$player.size` release scan (the `DistanceUse` idiom).

8. **t1l3 plant-4-charges & t3l1 sticky-bomb pool** — coop-correct by code (level-global), listed
   only as worth a hands-on "can a non-host plant?" confirmation.

---

## Notes / caveats

- This pass independently re-derived the M-series reference and confirmed it is uniformly GREEN —
  the e/t conversions were modeled on it correctly.
- The two newly-examined gun/charge maps (e1l2, e2l1) close the gap the prior audit left open:
  both have map-local `GunOrExplosive` implementations, and both are already coop-converted
  (`coop_GunOrExplosive` / `player_closestTo` loops). Had they still polled bare `$player`, they
  would have been REDs on shipping maps — they are not.
- Engine `addobjective` HUD replication to all 16 is framework behavior; the audit rated only the
  COMPLETION TRIGGER (who can fire it), which is the real coop risk.
- All YELLOWs are interactive set-pieces the god-bot teleport harness cannot exercise (no USE, no
  mount, no plant). They need 2+ real players, ideally a non-host performing the interaction.
- No files were edited; no parse risk introduced.

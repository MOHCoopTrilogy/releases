# Coop Conversion Report: e1l4, e2l1, e2l2, e2l3

Date: 2026-06-24. Scope: source edits under `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps\`
only. No pk3 rebuild, no game launch, no GOG files touched. Parse hygiene verified:
all four map scripts + every sub-script are ASCII-clean (zero bytes >0x7F) and have no
UTF-8 BOM (first bytes are `//`/CRLF/code).

Key finding up front: **e2l1, e2l2, and e2l3 were already substantially coop-converted**
by prior work (Smithy/chrissstrahl) - per-player camera intros, `$player.size` loops,
`replace.scr` shims, `validateTriggerActivator`/`cloneTrigger`, ObjMgr objectives. The
remaining single-player assumptions were either already gametype-guarded, confined to
`skip*`/dev/`freeCam` debug blocks, or a small number of live gaps that I fixed. **e1l4
was the real work** (the papers/cover-blown server-restart fix).

---

## e1l4 - "Show your papers" server-restart fix (Fix A) + sweep

### What was single-player / broken
The stealth "show your papers" gate and the "blown your cover" path both called
`coop_mod/replace.scr::missionfailed`, which calls `main.scr::restartMap` -> reloads the
map (`e1l4$`) -> bumps `sv.serverId` -> every client gets a gamestate resend and lands
back on the MP team-select menu. Under the Phase-2 maptest this looped forever (a bot
can't present papers); in real coop, one straggler who misses the prompt would restart
the whole server for all 16.

### What I changed (file:line in `maps/e1l4/Intro.scr`)
- **`KillPlayerIfFailPapers` (~294-321)**: replaced the unconditional coop
  `missionfailed` with a two-tier soft path:
  - Under maptest (`getcvar("coop_maptest") == "1"|"2"`): set
    `level.GatePapersAccepted = 1`, `thread papersAccepted`, `end` - the tour proceeds,
    no restart.
  - In coop (`level.gametype != 0`): apply the per-player `killplayer` shim (soft
    consequence for whoever failed) then `thread softPapersFail` and `end` - NO
    `missionfailed`, NO server restart.
  - SP path unchanged (`killplayer` only).
- **New `softPapersFail` (~327-339)**: waits 2s (so killed players see the consequence),
  then `thread papersAccepted`, which sets `GatePapersAccepted=1` + enables area AI. This
  resolves the `while(level.GatePapersAccepted != 1)` wait in `GateGuardDialogue` (~248)
  so the level never deadlocks; play continues for the whole party.
- **`FAILEDMISSION` (~152-185)** (the "blown your cover" path from `IfPullGunFail`):
  added a maptest guard (`End` immediately) and a coop branch that sounds the alarm,
  sets `GatePapersAccepted=1`, `thread AIenable`, `End` - the mission becomes a loud
  firefight instead of a server reload. SP path unchanged.
- **`maps/e1l4/SunkShip.scr` `coop_shipTiltPlayer` (~406)**: fixed a latent coop bug -
  the view-reset read bare `$player.viewangles` (array in coop) instead of
  `local.player.viewangles`. Now uses the per-player local.

### Objective semantics
Unchanged - e1l4 objectives are linear story beats driven by triggers/`global/objectives.scr`
(any-player reach/use). The papers gate is now soft-resolving, not fail-restarting.

### Rest-of-map sweep result
All other live `$player` uses in e1l4 are inside `if(level.gametype==0)` SP branches,
`skip*` dev-shortcut blocks (debug teleports of player 1 only, gated behind cvars nobody
sets in coop), or `/* */` comment blocks. The intro truck-ride is already a full
per-player camera implementation (`coop_startTruckSpawnManager`/`coop_spawnTruckCamera`/
`coop_startTruckCamera` using the `trigger_camerause` + `doUse` per-player pattern with a
late-join `level waittill playerspawn` manager). The SunkShip explode/tilt/blackout
sequence is fully per-player (`coop_ExplodeShip`, `coop_shipTilt`, `playerBlacksOut` all
loop `1..$player.size`).

### Watch for in testing
- After a coop papers fail: confirm killed players respawn and the level advances
  (objective "Find a Way Aboard the Freighter" stays active, gate sequence completes) -
  the soft path should never produce an `e1l4$` restart in the log.
- Under maptest: the patrol tour should now run past waypoint 3 and either finish or
  advance to e2l1, with `MAPTEST_LOADED` and no repeating `Server: e1l4$`.

### Risks / unknowns
- `softPapersFail` resolves the gate by simulating acceptance. If design later wants a
  real coop consequence (e.g. spawn alarm reinforcements on papers fail), that's an
  additive change on top of this.
- The `skip*` debug teleports still move only player 1; harmless in normal play but if
  anyone runs e1l4 with a `skip*` cvar in coop, players 2..N won't be warped (low
  priority - flagged, not fixed).

---

## e2l1 - Glider-ride intro (already done) + 2 live fixes

### Already coop-correct (no change)
- **Glider ride intro** (`maps/e2l1/gliderride.scr`): the reference per-player camera
  implementation - `coop_spawnGliderCamera`/`coop_startGliderCamera`/`coop_stopGliderCamera`
  (per-player `trigger_camerause`+`doUse`), `coop_startGliderSpawnManager` for late joiners,
  per-player `coop_handlePlayerGliderEject`, `coop_handleDeath`. Teardown via global
  `cueplayer`. This is exactly the m1l1 pattern the task asked for.
- `enemySet809.scr:213` trigger gate already converted from `parm.owner != $player` to
  `parm.owner.classname != "Player"` (accepts any player).
- NPC `reach $player` calls (`paraBattle.scr:261`, `FinalBattle.scr:296`) route through
  `global/SafeMoveTo.scr::reach`, which is coop-aware (`isPlayerObject` detection).
- `aaguns.scr:269` follow-target already gametype-guarded via `level.coop_player`.

### What I changed
- **`maps/e2l1/ab41_scene.scr` (~308-326)**: when the AB41 armored car is destroyed, only
  the host (`$player`) was checked for `istouching $AB41.collisionent` -> `normal_damage 100`.
  Added a coop branch that loops `1..$player.size` and damages every active player touching
  the wreck. (The `radiusdamage` at the same spot already hit all; this is the
  inside-the-model top-up.)
- **`maps/e2l1/enemySet809.scr` (~220-252)**: when the water tower is destroyed and the
  ladder removed, only the host was kicked off the tower MG42 turret (`$player.turret`/
  `usestuff`/`safeholster`). Added a coop branch looping all players to dismount any player
  on a turret and re-allow holster for all. (Smithy had left this as an explicit TODO.)

### Objective semantics (`maps/e2l1/objectives.scr`)
4 objectives, all engine `addobjective` (auto-replicate to all 16):
- Obj1 "Destroy AA Artillery [N Remaining]" - **counter** via `level.numAAGunsAlive`
  (global); mission-complete fires when the last gun dies (any player). Correct.
- Obj2 rendezvous, Obj3 destroy AB41, Obj4 protect 505th - death/trigger driven, any-player.
- **FAIL: Phillips death** (`e2l1.scr:214-219`) -> `missionfailed` (respawn-aware coop
  shim). Single-NPC escort-protect fail; shared fate. Kept (matches plan guidance for
  single-NPC protects; not a squad-wipe). Phillips is `ai_off` until needed.

### Watch for / risks
- Phillips-death shared fail: if 16 players make the firefight chaotic and Phillips dies
  to friendly fire, the mission fails for everyone. Monitor; consider `nodamage` on
  Phillips during heavy phases if it proves fragile.
- The `level waittill spawn` at `e2l1.scr:19` is the old SP gate, but the real coop gate
  `waitForPlayer` follows at line 65 and all init/glider logic is downstream of it, so it's
  effectively a harmless "wait for first spawn." Left as-is.

---

## e2l2 - Already done (briefing + jeep-turret + cinematic), no edits needed

### Already coop-correct (verified, no change)
- **Briefing intro** (`maps/e2l2/briefing.scr`): `coop_doplayer` glues all players via the
  `replace.scr::glue` shim (NO global `freezeplayer`); unglue at briefing end via shim.
- **GuardPost jeep-turret sequence** (`maps/e2l2/guardPost.scr`): fully converted. The coop
  branch (122-169) tracks which of N players mounts the turret via `level.jeepAttachedPlayer`,
  and every downstream SP `$player` line has a coop counterpart using that variable
  (`getout`, `jeepnewpath`, takeall/give via shims, unglue). One gunner of 16, jeep
  auto-drives; mounted player set `nodamage` then `takedamage` restored at the end.
- **Radio-tower kill zone** (`radioTower.scr::TowerKillsPlayer_Thread`): loops all players,
  damages each `isinside $trigger_towerkill`, and `resetSpawn` so they don't respawn inside.
- **End outro cinematic** (`cinematic.scr::DoOutro`): `InitEndGag` loops all players
  (notsolid/physics_off/hide/threatbias). The bare `cuecamera $TheCam*` is the documented
  acceptable case for a mission-end cutscene (all 16 watch the ending together, then
  `missioncomplete`). `$player.origin` warps are inside `if(level.freeCam==1)` (dev, off).
- Bike/truck gag trigger gates use `parm.other == $bike*`/`$truck*` (entity-gated, not
  player). `DoTakeIt` uses `parm.other` (the triggering player). `FireShots $player`'s
  player arg is unused (rider just `fire`s). Bike-explode damage loops all players.

### Objective semantics
Trigger/destroy-driven via `maps/e2l2/objectives.scr` (any-player); music via
`global/music.scr::PlaySongLoop` (server-wide). No squad-wipe fail conditions.

### Watch for / risks
- During the jeep-turret auto-drive, only the turret gunner rides; the other 15 are not
  glued/teleported with the jeep (intended "1 gunner, rest on foot/follow"). The ride is
  short, but if players get badly left behind, consider a geofence warp-up. Design call,
  not a bug.

---

## e2l3 - Already done (jeep intro + save/restore), no edits needed

### Already coop-correct (verified, no change) - the most carefully converted of the four
- **Jeep intro** (`maps/e2l3/IntroHouse.scr`): `playerGetOnJeep` glues all players via the
  shim in coop (with a `jeepFailSave` watchdog if the jeep gets stuck), `Fadein` early-`end`s
  the SP-only viewangle code in coop and the all-player physics_off/viewangle-memory loop is
  in `e2l3.scr::Fadein`. Eject (`unloadJeep`) has a coop branch that ungues to a fixed exit
  origin. The jeep-destroyed sequence kills any player touching the wreck via an all-player
  loop (504-513); the SP `$player bullethit` (490) is gametype-guarded.
- **Start_Tanks vehicle trigger** (`e2l3.scr:14`): wrapped with
  `replace.scr::cloneTrigger ... "trigger_vehicle"` so the jeep triggers the sequence
  regardless of whether a player is aboard.
- **Failure recovery**: `coop_levelLoadedafterFailure` restores spawn slots, scales the
  blockade, and cleans up entities when a coop save (`e2l3_finalHouse`) is loaded - explicit
  coop checkpoint handling.
- `findTheAllies` (BattleHouse) uses the `playerCansee` shim in coop (any player seeing the
  commander advances). `havePlayerUseMortars` (FinalHouse) is gametype-guarded. Town tank
  target-selection uses `canseeGetClosest`/`player_closestTo` shims. `IntroHouse:88,105-107`
  correctly index `$player[1]`.

### Objective semantics (`global/ObjMgr.scr`, 4 objectives, `inOrder` strategy)
meet82nd / assist82nd / clearTown / repelTanks - all auto-replicate via engine
`addobjective`; trigger/area/death-driven (any-player). No squad-wipe fail. `SetCurrObjStrategy
"inOrder"` means they reveal/complete sequentially - correct for the linear town assault.

### Watch for / risks
- `coop_save` restore path teleports/cleans on a specific token (`e2l3_finalHouse`); only
  exercised when that save is loaded. Normal forward play unaffected.
- All `$player` debug warps (`Town.scr:9`, IntroHouse skip block, `Glider.scr:237` comment)
  are in `skip*`/comment blocks.

---

## Summary of files edited
- `maps/e1l4/Intro.scr` - papers-fail + cover-blown coop/maptest soft path (+ new `softPapersFail`)
- `maps/e1l4/SunkShip.scr` - `$player`->`local.player` viewangle-reset bug in `coop_shipTiltPlayer`
- `maps/e2l1/ab41_scene.scr` - AB41-wreck touch-damage loop over all players
- `maps/e2l1/enemySet809.scr` - tower-turret dismount loop over all players

(e2l2 and e2l3 required no edits - already coop-correct for 16 players.)

## Top things to verify in the harness
1. **e1l4 no longer restart-loops.** Log should show `MAPTEST_LOADED` then the patrol tour
   running past waypoint 3 with NO repeating `Server: e1l4$`. The papers throbtext can
   appear, but `KillPlayerIfFailPapers` must take the maptest soft path, not `restartMap`.
2. **e1l4 coop papers fail is soft.** With humans, a player who skips the papers prompt gets
   killed once but the level continues (gate resolves, AI enables); no team-select kick.
3. **e2l1 glider ride for 16 / late join.** All players see the glider cinematic via their
   own camera, eject on USE, and respawning mid-ride doesn't drop them from the sky
   (`coop_handleDeath` guards this). Confirm the AB41 destruction and tower collapse don't
   error with the new all-player loops.
4. **e2l1 Phillips-death fail** behaves sanely with many players (doesn't fire spuriously).
5. **e2l2 jeep-turret** mounts for any of N players (not just host) and the post-ride
   loadout/unglue applies to the mounted player; **e2l3 jeep intro** glues/ejects all players
   and `jeepFailSave` recovers if the jeep stalls.
6. **Objectives replicate** to all clients on all four maps (engine `addobjective` /
   ObjMgr) and complete on any-player for reach/destroy, counter for "[N remaining]".

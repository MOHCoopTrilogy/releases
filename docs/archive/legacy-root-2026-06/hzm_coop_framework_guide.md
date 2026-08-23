# HZM Coop Mod — Framework Integration Guide

Definitive reference for how a MOHAA/Breakthrough level script must hook into the
HaZardModding (HZM) Coop Mod framework (`coop_mod/*.scr` + overridden `global/*.scr`)
to be coop-correct. Framework-side complement to the per-map vs-vanilla diff work.

All file:line citations are from `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\` as read 2026-06-23.
Verify against current code before treating any line number as exact.

---

## 1. Per-script reference (one paragraph each)

### `coop_mod/main.scr` (1595 lines) — orchestrator + utility library
Owns the init sequence (`main:` label, line 35) and a large library of shared helpers.
`main` must run **with no `wait`/`waitframe` before or inside the critical init block** (banner
warning, lines 11-20, 33). It guards re-entry with `level.coop_mainScriptLoaded` (NIL→0→`game.true`),
runs `variables.scr::main` → `server.scr::main` → `spawnlocations.scr::main` synchronously, then
threads `player.scr::manage`, `events.scr::initialiseEvents`, `medkit`, **`officer.scr::coop_officer_init`
(line 121)**, optional maptest, and finally fires the `"mainScriptLoaded"` event (line 142). Singleplayer
short-circuits to `spWaitForPlayer` (line 93-96). Key public helpers used by maps and other framework
scripts: `startThread` (863), `playersWarpto` (427), `playerPlaceAtSpawn` (469), `playerMakeSolidAsap`
(558), `waitForMainScript` (1387), `isPlayerActive` (846)/`game.playerActive`, `getPlayerId` (881),
`inCoopMode` (1538), `isCoopEnabledMap` (1551), `printInfo` (378), `playerGlue` (1142),
`changeGameType` (1328), `loadMap`/`restartMap` (1499/1482), `getCleanMapname` (1573),
`earthquake_radius`/`earthquake_player`, the var-type introspection helpers `returnVarType`/
`returnVarTypename` (986/1095). It also dispatches the 4 optional per-map callbacks (see §3).

### `coop_mod/variables.scr` (250 lines) — global/level state init
`main:` (line 11) is the FIRST thing `main.scr::main` waits on. Sets the `game.*` function-pointer
table (lines 14-33, including `game.main`, `game.replace`, `game.waittill`, `game.event`,
`game.player`, `game.playerActive`), reads cvars into `level.*` (gametype, sv_maxclients,
dedicated detection, LMS), seeds all `level.coop_*` defaults, then (MP only, gated at line 82) inits
`level.coop_actorArray["german"/"american"]`, difficulty scalars, pain-handler exclusion list
(line 98), item-handler config, and threads `initNonCritical` → `initMissionNames` +
`levelObstacleArrays`. This is the authoritative catalog of framework state (see §4).

### `coop_mod/player.scr` (1099 lines) — player spawn/death/respawn lifecycle
`manage:` (line 19) is the per-frame player manager threaded from `main`. It (a) does first-time
`manageSetup` (line 180) setting `coop_isActive=-3`, (b) records the rolling respawn-warp
origin/angle each frame for living players (lines 82-88), (c) detects player-count change → calls
`main.scr::playerCountChanged` and (on a join) fires the **`coop_playerJustLeft`** callback
(lines 125-131 — note: fired on count INCREASE, the label name is historical), (d) runs inline LMS
bookkeeping, (e) handles name changes. Spawn handling is event-driven, **not** in this loop:
`manageAliveSpawning` (line 790, called from `main.scr::playerSpawnEvent`) does setup, team-force,
LMS, respawn-vs-firstspawn branch (lines 817-823) firing **`coop_playerJustRespawned`** (819) or
**`coop_playerJustSpawned`** (822), inventory, health, glue, FOV, then sets `coop_isActive=1`/
`coop_isAlive=game.true` and starts the dbno/thirdperson/medkit/cover monitors (884-888). Death is
handled by `manageDead` (line 1007, via `main.scr::playerDeathEvent`): 3-frame settle, DBNO branch,
else sets `coop_isActive=-2`/`coop_respawning=TRUE`, unglues, `physics_on`, and fires
**`coop_playerJustDied`** (1071).

### `coop_mod/replace.scr` (2686 lines) — SP→coop command shims + helpers
The compatibility layer that makes single-player global scripts multiplayer-safe by iterating all
`$player[]` instead of the implicit `$player`. Header (lines 5-12) is the original→replacement crib
sheet. Key entry points a map/global may call: `waitTillSpawn` (15, the coop replacement for
`level waittill spawn`), `waitForPlayer` (99, blocks until a player has spawned-and-readied; no-op in
non-coop), `waitTillPrespawn` (37), `physics_on`/`physics_off` (1555/1574, set `level.coop_physicsOff`
+ per-player flag and apply to all players), `validateTriggerActivator` (2507) and `cloneTrigger`/
`cloneBrushObject` (2535) for player-gating triggers, plus broadcast wrappers `playsound`/`ammo`/
`item`/`take`/`takeAll`/`stopwatch`/`viewangles`/`tmstart*`/`cansee`/`canseenoents`/`istouching`/
`isinside`/`getToucher`/`turnto`/`lookat`/`aimat`/`fullheal`/`nodamage`/`takedamage`, the player-query
helpers `player_closestTo` (333)/`player_closestTargetable` (375)/`player_anyValid`/`player_random`/
`player_anyCanBeSeen` (188)/`player_numActive`, and `attackplayer`/`favoriteenemy`/`open`/`create_squad`/
`join_squad` actor shims. `player_origin` (465) is a deliberate crash-trap for outdated callers.

### `coop_mod/officer.scr` (2504 lines) — boss + reinforcement system
Self-contained encounter threaded from `main.scr:121`. `coop_officer_init` (line 6) waits for a
player, registers side objectives, gates on truck-intro/`ridecomplete`, then selects a spawn anchor
in stages: authored anchor from `officer_positions.scr::getAnchor` → `$alarmspawner` (nav-valid) →
farthest living German in `level.coop_actorArray["german"]` → **skip the boss** if no infrastructure
(line 188). Honors per-map toggles `level.coop_feature_boss`/`coop_feature_waves`/`coop_feature_voice`
and `level.coop_wave_mask`. `coop_officer_spawn` (257) spawns a 1500-HP officer (`coop_actorStopPainHandler=1`,
`forceactivate`, `attackplayer`, `rendereffects +coopboss/+additivedynamiclight`) plus bodyguards,
and threads the brain/retreat/reinforcement/death monitors. Reads `level.coop_theater` for model
selection. **Framework dependency to note for maps:** the officer relies on `coop_actorArray` being
populated (so the map's actors must flow through `aihandler` via the shared TIKI) and on
`$alarmspawner`/authored anchors for placement.

### `coop_mod/eventsystem.scr` (164 lines) — named pub/sub bus
Single `ScriptSlave` named `EventSlave` (lazy-spawned by `initEventSlave`, 156). `waitTillEvent <name>`
(15) registers the event then blocks on `$EventSlave waittill trigger` until the state flips;
`doEvent <name>` (29) unregisters + `trigger $EventSlave` waking all waiters; one-shot (cleared after
fire via `clearEvent`). Exposed as `game.waittill`/`game.event`. `waittill <name>` (127) is a separate
self-scoped helper; only `"playerdeath"` is implemented (loops on `self.flags["coop_isAlive"]`). The
only framework-fired named event is `"mainScriptLoaded"`.

### `coop_mod/aihandler.scr` (667 lines) — actor registry + difficulty/pain
`main local.thread` (18) is invoked **per actor from the shared `new_generic_human.tik`** (not from a
map). It bails if not coop / not an Actor, waits for `waitForMainScript`, then threads the passed-in
behavior thread. `actorHandler` (54) stamps difficulty data, optionally swaps in the coop pain handler,
and `addActorToArray` (135) registers the actor in `level.coop_actorArray[self.team][]`;
`self waittill death` → `removeActorFromArray` + kill credit. Owns dynamic accuracy scaling by player
count (`calculateAccuracy`, 229), the 5000-HP pain-handler trick (`actorPainHandler`, 300),
friendly-fire suppression, and the disguise/cover-blown system. `updateEnemyTeamDifficulty` (192) is
re-run by `main.scr::playerCountChanged`.

### `coop_mod/vehiclehandler.scr` (86 lines) — STUB
`main:` (line 2) is **empty** (no-op). Only `storeDriveProperties`/`restoreDriveProperties`/
`stopVehicle`/`startVehicle` helpers exist, and `storeDriveProperties` immediately `end`s at line 18.
Vehicle behavior actually lives in `global/vehicles_thinkers.scr` + `level.coop_playerTank`. Not part
of the mandatory hook contract.

### `coop_mod/server.scr` / `spawnlocations.scr` / `loadout.scr` / `itemhandler.scr` / `events.scr`
Run synchronously or threaded by `main` in fixed order (§2). `server.scr::main` sets up the server
(maxclients, maplist checks). `spawnlocations.scr::main` creates the coop spawn points consumed by
`main.scr::playerPlaceAtSpawn` via `level.flags["coop_spawn"+i+"origin"/"angles"]`. `loadout.scr`
(exec'd, line 108) builds the weapon-loadout array. `itemhandler.scr` manages inventory/pickups and
`disableAllWeaponsOnMenu`. `events.scr::initialiseEvents` wires the engine `level waittill playerspawn`
→ `main.scr::playerSpawnEvent` and the player-killed → `main.scr::playerDeathEvent` bridges.

### CFGs
`coop_mod/start_server.cfg` — server boot (executed from the in-game coop_start menu). Mandatory
settings: `g_gametype 2`, `maxentities 2048`, `g_healrate 100000`, floodprotect, no time/frag/round
limits; tunables `coop_dev`/`coop_check`. Map-rotation testers use
`cfg/maptest_start.cfg` (sets `coop_maptest 1`) and `cfg/maptest_phase2_start.cfg` (`coop_maptest 2`),
read in `main` at lines 128-133; `cfg/maptest_stop.cfg` halts them. These are inert in normal play.

---

## 2. Init / call-order diagram (what `main.scr::main` fires, in sequence)

A map's `main` calls `waitthread coop_mod/main.scr::main`. That single call drives:

```
maps/<map>.scr::main
  └─ waitthread coop_mod/main.scr::main          [main.scr:35]   (NO waits allowed before/within)
        1. spawn trigger_relay "coop_levelWaitTillSpawn"          [40]
        2. re-entry guard via level.coop_mainScriptLoaded         [43-46]
        3. waitthread variables.scr::main          (SYNC)         [84]  ← game.* table, all level.coop_* defaults, coop_actorArray init
        4. if gametype==0 → thread spWaitForPlayer; end  (SP path)[93-96]
        5. waitthread server.scr::main             (SYNC)         [99]
        6. waitthread spawnlocations.scr::main      (SYNC)        [102] ← level.flags["coop_spawn*"]
        7. thread player.scr::manage               (ASYNC loop)  [105] ← per-frame player mgr; fires coop_playerJustLeft
        8. exec loadout.scr                                       [108]
        9. thread itemhandler.scr::disableAllWeaponsOnMenu        [111]
       10. thread events.scr::initialiseEvents                    [118] ← bridges engine playerspawn/killed → playerSpawnEvent/playerDeathEvent
       11. thread medkit.scr::coop_scan_health_entities           [120]
       12. thread officer.scr::coop_officer_init                  [121] ← boss system
       13. (optional) thread maptest*.scr  if coop_maptest 1/2    [128-133]
       14. level.coop_mainScriptLoaded = game.true                [136]
       15. thread eventsystem.scr::doEvent "mainScriptLoaded"     [142] ← releases all waitForMainScript waiters
```

Event-driven lifecycle (after init, via `events.scr` bridges):

```
engine: level waittill playerspawn
  → main.scr::playerSpawnEvent [232]
       → player.scr::manageSetup (first time, coop_isActive=-3)   [246]
       → player.scr::manageAliveSpawning [251/790]
            ├─ coop_respawning==TRUE  → manageAliveRespawning → fire coop_playerJustRespawned [819]
            └─ else (first spawn)     → playerPlaceAtSpawn      → fire coop_playerJustSpawned   [822]
            → inventory, health, glue, FOV; coop_isActive=1, coop_isAlive=true; start dbno/tp/medkit/cover monitors

engine: player killed (player_torso KILLED state) → events.scr → main.scr::playerDeathEvent [263]
  → player.scr::manageDead [1007]
       → DBNO branch, else coop_isActive=-2, coop_respawning=TRUE, unglue, physics_on
       → fire coop_playerJustDied [1071]
```

`startThread` mechanics (used for all 4 callbacks) — `main.scr:863`:
```
startThread local.script local.entity:
    local.trigger = spawn trigger_once setthread local.script   [866]
    waitframe                                                    [867]   ← the intentional 1-frame delay
    local.trigger doActivate (local.entity | $world)            [876]
```
`setthread` binds the trigger's use-event to `maps/<map>.scr::<callback>`; `doActivate` fires it.
If that label is absent in the map script, the engine prints
`Could not find label 'coop_playerJustXxx'` (non-fatal) every time the callback fires — this is the
spam issue addressed in §5.

---

## 3. The hook contract — MANDATORY vs OPTIONAL

### MANDATORY (exactly one requirement)

**The map's `main` must call `waitthread coop_mod/main.scr::main` at the very top, before any
`wait`/`waitframe`/entity access.** Everything else the framework needs flows from that one call.

```
main:
    level.coop_aaMap = 1                 // optional: declare AA-theater (see §6 notes)
    waitthread coop_mod/main.scr::main   // MANDATORY — start the coop framework
    ... map-specific code ...
end
```
Reference: `maps/m1l1.scr:4-9`. Pattern confirmed across the AA m-series. Notes:
- AA maps that already wrap code in `main:` only need to insert the `waitthread` line.
- t-series (Breakthrough) maps are pure vanilla and need a `main:{}` wrapper added that calls it
  (per `level_scripts_sh_bt.md`).
- Precache files (`*_precache.scr`) do **not** call `coop_mod/precache.scr` automatically — a known gap.
- Replacing `level waittill spawn` / `level waittill prespawn` with `coop_mod/replace.scr::waitTillSpawn`
  / `waitTillPrespawn` is required for any global script section that used the SP form, but this is a
  per-statement compatibility fix rather than a top-level hook.

### OPTIONAL — the 4 per-map callbacks

All four are dispatched by `main.scr::startThread` and are **optional**. The framework calls them
unconditionally; if the map does not define the label, you get the non-fatal
`Could not find label '...'` console spam (see §5 for the fix).

| Callback | Signature (self/param) | Fired from | When |
|---|---|---|---|
| `coop_playerJustSpawned` | label receives the player as the activator/`local.player`; the spawning player is passed as the `doActivate` entity | `player.scr:822` (via `manageAliveSpawning`, first-spawn branch) | A player's FIRST spawn on the map |
| `coop_playerJustRespawned` | same | `player.scr:819` (respawn branch, `coop_respawning==TRUE`) | Each respawn after death |
| `coop_playerJustDied` | same | `player.scr:1071` (via `manageDead`) | Each player death (after DBNO resolution) |
| `coop_playerJustLeft` | activator is `$world` (count-change handler) | `player.scr:129` (via `playerCountChanged`) | On player-count change (fires on a JOIN in current code; name is historical) |

Signature detail: `startThread(script, entity)` spawns `trigger_once setthread script` then
`doActivate entity` with `entity` = the player (callbacks 1-3) or `$world` (callback 4, line 129
passes `$world`). Inside the label, the activating entity is available via the standard trigger
`self`/`parm.other` mechanics; the established AA convention (e.g. m4l3) is simply to iterate
`$player[]` and act on living players rather than relying on the passed entity. Example consumers:
m4l3 `coop_playerJustSpawned` gives `pistol 80`+`grenade 6` each spawn; m1l1 defines
`coop_playerJustSpawned` (m1l1.scr:2890). Only ~23 of ~80 map scripts define ANY of these; the rest
trigger the spam.

---

## 4. Shared state catalog

### `level.*` (owned by `variables.scr` unless noted)
| Variable | Set in | Meaning |
|---|---|---|
| `level.coop_mainScriptLoaded` | main.scr:46/136 | NIL→0 (loading) → `game.true` (loaded). Re-entry guard + `waitForMainScript` gate |
| `level.coop_mapname` | variables.scr:62 | clean map name (savepoint `$…` stripped); used to build `maps/<map>.scr::` thread paths |
| `level.script` | variables.scr:64 / main.scr:90 | `"maps/<map>.scr"` |
| `level.gametype` | variables.scr:34 | 0 = SP; coop runs as 2 |
| `level.coop_dedicated` | variables.scr:47-49 | listen vs dedicated detection |
| `level.coop_svmaxclients` | variables.scr:51 | reserved entnum range for players |
| `level.coop_actorArray["german"\|"american"][]` | variables.scr:85-86, aihandler | live actor registry by team; consumed by officer + disguise systems |
| `level.coop_player` | variables.scr:69, main.scr | current AI follow-target player (friendly/squad) |
| `level.coop_playerReady` | variables.scr:54, player.scr:883 | a player has joined+picked weapon (mission may start) |
| `level.coop_gameStartedAt` | main.scr:237 | level.time of first active player |
| `level.coop_physicsOff` | replace.scr:1558/1577 | global player-physics state (applied per-frame in `manage`) |
| `level.coop_playerGlue` / `coop_playerGlueIndividual` / `coop_glueTo` / `coop_glueAngle` | variables/main | player-glue config |
| `level.coop_playerHide` | replace.scr:1600/1619 | global hide-players flag |
| `level.coop_lmsLives` / `coop_lmsAllowJoin` | variables/player | Last-Man-Standing config/state |
| `level.coop_disableSpawnWarper` / `coop_cvarRespawnDisable` | variables/cvar | disable respawn-at-death-location warp |
| `level.flags["coop_spawn"+i+"origin"/"angles"]` | spawnlocations.scr | per-slot coop spawn points (1-8) |
| `level.coop_levelObstacle["general"\|<map>]` | variables.scr:237/247 | entities a spawning player must not solidify into |
| `level.coop_actorPainHandler` / `coop_painHandlerExclusions` | variables.scr:92/98 | coop pain-handler enable + per-map exclusion list |
| `level.coop_actorAccuracyCalcs` / `coop_maxPlayerScalar` | variables.scr:90-91 | player-count difficulty scaling |
| `level.coop_aaMap` | map main (e.g. m1l1:7) | declares AA-theater map; restores AA actor props in aihandler |
| `level.coop_eventNameList[]` + `$EventSlave.events[name]` | eventsystem | named-event registry |
| `level.coop_officer` / `coop_officer_alive` / `coop_radio` / `coop_bodyguards[]` / `coop_battalion[]` | officer.scr | boss encounter runtime state |
| `level.coop_feature_boss` / `coop_feature_waves` / `coop_feature_voice` / `coop_wave_mask` / `coop_theater` / `coop_officer_*` (z_tol, z_ref, anchor, reinf_zone) | officer_positions.scr / per-map | per-map boss toggles + placement tuning |
| `game.*` (true/false/ms/frame/main/replace/player/item/ai/waittill/event/playerActive/say…) | variables.scr:14-33 | global function-pointer + constant table |

### `player.flags["coop_*"]` (owned by player.scr / events.scr / dbno / medkit)
| Flag | Meaning |
|---|---|
| `coop_isActive` | -3 new, -2 dead, -1 just-died, 1 fully active |
| `coop_isAlive` | game.true / game.false (set false on death) |
| `coop_iAmTruelyActive` | 1 when confirmed in-game and alive |
| `coop_isHost` | 1 if listen-server host (entnum 0) |
| `coop_respawning` | TRUE between death and respawn-warp |
| `coop_respawnOrigin` / `coop_respawnAngle` / `coop_respawnTime` / `coop_lastRespawn` | respawn-warp bookkeeping (recorded each living frame, player.scr:82-88) |
| `coop_spawnlocAlt` / `coop_spawnlocAltActive` / `coop_spawnlocPreviouse` | alternate-spawn / stuck-prevention |
| `coop_makesolid` | in-progress flag for `playerMakeSolidAsap` |
| `coop_deaths` / `coop_lmsForcedInSpectator` | LMS state |
| `coop_dbno_active` / `coop_dbno_dead` / `coop_dbno_cumulative` / `coop_dbno_healing` / `coop_dbno_letgo` | DBNO (down-but-not-out) state |
| `coop_medkits` / `coop_medkit_in_use` / `coop_medkit_refill_cooldown` | medkit state |
| `coop_fov` | client FOV pref |
| `coop_netname` / `coop_netnameChanged` | name-change detection (also the "was main.scr included?" tripwire, player.scr:105) |
| `coop_physicsOff` | per-player physics flag |
| `coop_playerTankExit` | pending tank-exit warp |
| `coop_lastInfoPrint` / `coop_lastInfoPrintText` | `printInfo` rate-limiting |
| `coopDevNoclip` / `coop_debug_godmode` / `coopDeveloperVerified` | dev/admin |

Actor flags (aihandler): `coop_actorStopPainHandler`, `coop_actorHandledPain`,
`coop_actorStopAccuracy`, `coop_actorAccuracy`/`coop_actorAccuracyRange`/`coop_actorNewAccuracy`,
`coop_actorActualHealth`, `coop_isAttacking`, `coop_actorResetThinkstate`.

---

## 5. Recommended fix for the missing-optional-callback error spam

**Problem.** `player.scr` (lines 819, 822, 1071) and (129) call
`startThread "maps/<map>.scr::<callback>"` unconditionally for all 4 optional callbacks. The
underlying `spawn trigger_once setthread <label>` (main.scr:866) emits a non-fatal
`Could not find label 'coop_playerJustXxx'` on every spawn/respawn/death/join for the ~57 maps that
don't define them. Confirmed in the maptest log (`Could not find label 'coop_playerJustLeft'`).

**Recommended fix (cleanest, framework-only, zero per-map churn): opt-in registry checked in
`startThread`.** Add a guarded dispatch helper in `main.scr` and have `player.scr` call it instead of
`startThread` for these four labels. A map opts in by setting a flag in its `main` (after the
`coop_mod/main.scr::main` call).

```
// main.scr — new helper
startMapCallback local.cb local.entity:
    if( level.coop_hasCallback[ local.cb ] != 1 ){ end }      // skip if map didn't opt in
    thread startThread ( "maps/" + level.coop_mapname + ".scr::" + local.cb ) local.entity
end

// player.scr — replace the 3 spawn/death sites, e.g. line 822:
//   thread coop_mod/main.scr::startThread ("maps/"+level.coop_mapname+".scr::coop_playerJustSpawned") (local.player)
// becomes:
    thread coop_mod/main.scr::startMapCallback "coop_playerJustSpawned" (local.player)
// (same pattern for coop_playerJustRespawned [819], coop_playerJustDied [1071],
//  and coop_playerJustLeft at player.scr:129)

// map opt-in (only in maps that actually implement a callback), in its main:
    level.coop_hasCallback["coop_playerJustSpawned"] = 1
```

Why this over the alternatives:
- **vs. no-op stubs in every map** — stubs require editing all ~57 silent maps and re-touching any
  future map; the registry is set once, only where a callback exists, and the 23 maps that already
  implement callbacks each add one declarative line.
- **vs. swallowing the error in `startThread`** — MOHAA script offers no `label-exists?` predicate,
  so `startThread` cannot pre-check the label; gating on an explicit registry is the only reliable,
  spam-free mechanism and it also documents intent.
- It is fully backward compatible: maps that set the flag behave exactly as today; maps that don't
  simply skip the dispatch (the callbacks are optional by design).

A lighter variant if editing 23 maps is undesirable: keep `startThread` but make
`startMapCallback` consult a framework-side allow-list array of `mapname → callbacks` (seedable in
`variables.scr`), so no map files change at all. The registry-flag form above is cleaner long-term
because the opt-in lives next to the callback it enables.

---

## 6. Helper functions available for new integrations

**Player gating / queries (`replace.scr`)** — use these instead of bare `$player`:
- `waitthread coop_mod/replace.scr::waitForPlayer` — block until a player is spawned & ready (no-op outside coop).
- `waitthread coop_mod/replace.scr::waitTillSpawn` / `waitTillPrespawn` — coop-safe replacements for `level waittill spawn`/`prespawn`.
- `( exec coop_mod/replace.scr::player_anyCanBeSeen <ent> [fov] [range] ) == TRUE` — any living player visible to ent.
- `exec coop_mod/replace.scr::player_closestTo <ent|NIL> [origin]`, `player_closestTargetable <ent>`, `player_closestInFront <ent>`, `player_anyValid`, `player_random`, `player_numActive`.
- `self thread coop_mod/replace.scr::cansee/canseenoents [fov] [range]`, `…::istouching <ent>`, `…::isinside <ent>`, `…::getToucher <ent>` — broadcast LOS/touch over all players.
- `waitthread coop_mod/replace.scr::validateTriggerActivator "threadName" <validEntity> [newTrigType newTrigName spawnFlags removeOld]` — inside a trigger thread, ensure `parm.other` is the intended activator; ends the calling thread (and optionally clones the trigger) if not.
- Broadcast item/sound wrappers: `…::item`, `…::take`, `…::takeAll [noWeapon]`, `…::ammo <type> <amt> [sound]`, `…::playsound <alias> [wait]`, `…::stopwatch <t>`, `…::viewangles <ang>`, `…::tmstart`/`tmstartloop`/`tmstop`/`tmvolume`, `…::nodamage`/`takedamage`/`fullheal`.

**Warping / placement / solidify (`main.scr`)**:
- `thread coop_mod/main.scr::playersWarpto <origin> [angle] [setSpawn]` — warp all players (origin NIL ⇒ send each to their spawn slot; setSpawn=1 ⇒ rewrite all 8 spawn slots).
- `waitthread coop_mod/main.scr::playerPlaceAtSpawn <player|index>` — place one player at their spawn slot (handles tank-exit + alt-spawn).
- `thread coop_mod/main.scr::playerMakeSolidAsap <player|index>` — solidify a player as soon as it won't telefrag.
- `thread coop_mod/main.scr::playerGlue <player> "spawn" [hide]` / `coop_mod/replace.scr::unglue`.
- `thread coop_mod/main.scr::printInfo <player> <msg> [bold] [strictTime] [wait]` — rate-limited HUD print.
- `coop_mod/replace.scr::physics_off` / `physics_on`.

**Threading / lifecycle (`main.scr`)**:
- `thread coop_mod/main.scr::startThread "<path::label>" [entity]` — spawn a `trigger_once setthread` and `doActivate` it (intentional 1-frame delay; entity defaults to `$world`).
- `waitthread coop_mod/main.scr::waitForMainScript` — block (esp. for pre-prespawn BSP items) until `main` finished loading.
- `exec coop_mod/main.scr::isPlayerActive <player>` (or `game.playerActive`) / `getPlayerId <player>` / `inCoopMode` / `isCoopEnabledMap <map>` / `getCleanMapname <dirty>`.
- `waitthread coop_mod/main.scr::changeGameType <type> [wait]` — temporary SP-spoof for disguises/sound callbacks (serialized; never run concurrently).

**Event bus (`eventsystem.scr` / `game.*`)**:
- Subscribe: `waitthread game.waittill "<eventName>"` (alias `coop_mod/eventsystem.scr::waitTillEvent`).
- Fire: `thread game.event "<eventName>"` (alias `…::doEvent`). One-shot; clears after firing.
- Player-death wait: `local.player waitthread coop_mod/eventsystem.scr::waittill "playerdeath"`.
- Known framework event: `"mainScriptLoaded"`.

**AI registry / difficulty (`aihandler.scr`)** — actors auto-register via the shared
`new_generic_human.tik` (no map call needed). Read `level.coop_actorArray["german"].size` /
`["american"]`, index with `[team][i]`. Per-actor opt-outs:
`actor.flags["coop_actorStopAccuracy"]=1`, `actor.flags["coop_actorStopPainHandler"]=1`; global:
`level.coop_actorAccuracyCalcs=0`, `level.coop_actorPainHandler=0`. Change run speed:
`exec coop_mod/aihandler.scr::updateTeamRunSpeed <team> <speed>`.

**Player API (engine + OPM)** — full command set in `script_command_catalog.md` and
`hzm_event_bus_and_player_api.md` (setfov, freezecontrols, setteam, hideent/showent, playlocalsound,
visionsetnaked, killhandler, moveSpeedScale, etc.). Use the HZM alive-check convention:
`coop_isActive==1 && coop_isAlive==game.true && coop_dbno_active!=1`.

---

## Appendix — critical gotchas for integrators
- **No delays in `main` before/inside `coop_mod/main.scr::main`** (main.scr:11-20). A `wait`/`waitframe`
  desyncs `manage`/`manageplayers` timing.
- `$world` may be NULL between map changes/restarts — `startThread` errors fatally if `$world` is NULL
  at activation (main.scr:875); guard map code accordingly.
- `level.time` is realtime and can jump on reload.
- Player entity is 1-indexed (`$player[1]`…); entnum 0 is the listen host.
- The `coop_playerJustLeft` label name is historical — it currently fires on a player-count INCREASE
  (player.scr:128-129), not a leave.
- `vehiclehandler.scr::main` is a stub; do not rely on it.

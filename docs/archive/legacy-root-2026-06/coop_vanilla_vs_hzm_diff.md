# HZM Coop vs Vanilla — The Definitive "Coop-Enable a Vanilla Map" Recipe

Derived by diffing HZM `hzm-mohaa-coop-mod/maps/*.scr` against vanilla originals
extracted (read-only) from the GOG paks:
- AA (m-series): `main/Pak5.pk3` → `maps/<map>.scr`
- Breakthrough (e-series): `maintt/pak3.pk3` (patched) / `maintt/pak1.pk3`
- Spearhead (t-series): vanilla, ships in `mainta/*.pk3`

Representative set diffed: **m1l1** (infantry + truck intro), **m1l3b** (jeep ride / glue),
**m5l2b** (player-driven tank), **m3l1a** (large D-Day infantry), **e1l1** (e-series jeep→tank ride).
Cross-checked against the full HZM map set via grep.

Builds on prior findings: `level_scripts_aa.md`, `level_scripts_sh_bt.md`,
`hzm_event_bus_and_player_api.md`, `mohaa_script_notes.md`, `officer_coverage_audit.md`.
(`coop_vehicle_onrails_plan.md` was referenced in the task but does not exist in memory;
the vehicle archetype here is derived directly from the m1l3b / m5l2b / e1l1 diffs.)

---

## 1. Canonical "coop-enable a vanilla map" recipe (ordered checklist)

The minimal, repeated diff that turns a vanilla MOHAA map script into an HZM coop map.
Steps 1–4 appear on essentially every integrated map; the rest are conditional on what
the vanilla map does.

### Step 1 — Wrap the script body in a `main:{ ... }end` block
Vanilla uses a bare `main:` label (statements at label scope). HZM wraps in a braced
function so coop can be injected as the first statements and the map has a single entry point.

Vanilla `m1l1.scr:1`:
```
main: // Mackey was here
```
HZM `maps/m1l1.scr:4-6`:
```
main:{
// Mackey was here
	level.coop_aaMap = 1
```
Exception: **m3l2** keeps coop init at top-level with no `main:{}` wrapper (documented anomaly;
any patch that targets `main:{}` specifically will miss it).

### Step 2 — Insert the coop init prologue as the FIRST executable lines
This is the single load-bearing change. Three lines (AA), two for e-series:

HZM `maps/m1l1.scr:7-9` (AA m-series):
```
	level.coop_aaMap = 1                       // m-series only: flag AA level for global scripts
	level.coop_disableSpawnWarper = game.true  // optional: maps that need fixed spawn placement
	waitthread coop_mod/main.scr::main         // BLOCKS until coop mod fully initialised
```
HZM `maps/e1l1.scr:10-14` (e-series — note: NO `coop_aaMap`, but adds `level.script`):
```
	level.script = "maps/e1l1.scr"
	level.coop_disableSpawnWarper = game.true
	waitthread coop_mod/main.scr::main
```
- `waitthread` (not `thread`) means the rest of the map runs only after coop setup completes.
  This is the universal injection point (e.g. for officer.scr).
- `level.coop_aaMap = 1` is m-series-only; e-series omits it.
- `level.coop_disableSpawnWarper = game.true` is added only on maps with a fixed-placement
  intro (truck/jeep/glider/D-Day): m1l1, m1l3a/b/c, m3l1a, e1l1, e2l1, etc. Vehicle-ride
  maps that re-enable it later set `= game.false` at the combat-start trigger (e2l1 `sparky1_on`).
- `level.script = "maps/<map>.scr"` must be set on any map that uses `validateTriggerActivator`
  / `cloneTrigger`, because those call `setthread level.script::<thread>` (see Step 6).

### Step 3 — Replace the spawn gate: `level waittill spawn` → `waitForPlayer`
Vanilla blocks the whole map on the single host player spawning. HZM replaces it with a
coop-safe gate that waits until at least one player is ready, and is a no-op passthrough in SP.

Vanilla `m1l3b.scr:21` + later `level waittill spawn`:
```
level waitTill prespawn
...
level waittill spawn
```
HZM `maps/m1l3b.scr:105-107`:
```
//level waitTill spawn //chrissstrahl
waitthread coop_mod/replace.scr::waitForPlayer //coop - start after a player has joined
```
`coop_mod/replace.scr::waitForPlayer` (`replace.scr:99-140`): in SP / non-coop it just does
`level waittill spawn; end` (line 104-107); in coop it polls `$player.size` until
`level.coop_playerReady == 1`. Subsequent calls only re-check the flag (cheap), so the same
function is safe to call once per scene (m5l3 calls it in 5 sub-threads).
`level waittill prespawn` is kept verbatim — only the `spawn` gate is replaced.

22 of 30 m-series maps use `waitForPlayer`; 5 (m2l2c, m4l0, m5l1a, m5l2b, m6l2b) intentionally
keep `level waittill spawn` (vehicle/chainspawner maps); 3 delegate it into sub-threads.

### Step 4 — Swap SP-only client commands for the `replace.scr` shims
Every vanilla command that targets the single `$player` or sends a client-side console
command must be routed through `coop_mod/replace.scr`, which loops over all players in coop
and falls back to the vanilla behavior in SP. The full shim catalog (from `replace.scr`):

| Vanilla pattern | HZM replacement | replace.scr line |
|---|---|---|
| `$player stufftext "tmstartloop ..."` | `exec coop_mod/replace.scr::tmstartloop <file>` | 553 |
| `$player stufftext "tmstop"` | `exec coop_mod/replace.scr::tmstop` | 534 |
| `$player stufftext "tmstart ..."` / `tmvolume` | `::tmstart` / `::tmvolume` | 583 / 613 |
| `$player isTouching $trig` | `exec coop_mod/replace.scr::istouching $trig` | 711 |
| `$player isinside $vol` | `::isinside` | 746 |
| (closest player to ent) | `exec coop_mod/replace.scr::player_closestTo <ent>` | 333 |
| `$player cansee/canseenoents` | `::cansee` / `::canseenoents` / `::playerCansee` | 1190 / 1229 / 1269 |
| `$player item/use/ammo/take/takeall` | `::item` / `::ammo` / `::take` / `::takeAll` | 1098 / 1013 / 1141 / 1168 |
| `$player playsound` | `::playsound` / `::playsound_wait` | 860 / 917 |
| `$player physics_on/off`, `show`/`hide` | `::physics_on` / `::physics_off` / `::show` / `::hide` | 1555 / 1574 / 1593 / 1612 |
| `$player glue/unglue` (ride maps) | `::glue` / `::glueHandle` / `::unglue` | 1453 / 1480 / 1505 |
| `$player forcelegsstate X` | `::forcelegsstate` | 1631 |
| `$player threatbias`, `holster`, `viewangles`, `say` | `::threatbias` / `::holster` / `::viewangles` / `::say_wait` | 1408 / 1804 / 517 / 975 |
| `missionfailed` | `exec coop_mod/replace.scr::missionfailed` (respawn-aware) | 2377 |
| give a pickup weapon | `::givePlayerWeapon` / `::takePlayerWeapon` | 2407 / 2460 |

Canonical SP-vs-coop body (e.g. `istouching`, `replace.scr:728-740`):
```
	if( level.gametype == 0 ){
		if( $player isTouching local.touchMeBaby ){ end 1 }
		end 0
	}
	for (local.i = 1;local.i <= $player.size;local.i++){
		local.player =  $player[local.i]
		if( local.player.health > 0 && local.player.dmteam != "spectator"
		    && local.player.flags["coop_isActive"] == 1 ){
			if( local.player isTouching local.touchMeBaby ){ end 1 }
		}
	}
end 0
```
This is the single most repeated transformation in every map.

### Step 5 — Convert bare `$player` loops to `$player.size` all-player loops
Any vanilla per-player logic done inline (not via a shim) is wrapped in
`for (local.i = 1; local.i <= $player.size; local.i++){ local.player = $player[local.i] ... }`.
`$player` in coop is an ARRAY (1-indexed); in SP it is the single player but `.size` still works.
Example: m1l1 `:645`, `:1486`, `:1499`, `:2421`, `:2871`.

### Step 6 — Wrap BSP triggers that require a player activator
Vanilla triggers fire on `parm.other == $player`. In coop the activator may be any of N
players (or the player-tank). Two helpers in `replace.scr`:
- `validateTriggerActivator local.thread local.validActivator ...` (`replace.scr:2507`) —
  drop into a trigger's thread; if `parm.other` is not the valid activator it ends the
  calling thread (and optionally clones a fresh trigger). Requires `level.script` set (Step 2).
- `cloneTrigger` / `cloneBrushObject` (`replace.scr` ~2480 / 2535) — duplicate a trigger so
  the empty vehicle or any player can re-fire it.
For player-vehicle maps, `level.coop_playerTank` is set to the tank entity so vanilla trigger
checks and `level_end` recognise the tank as the activator (`global/exploder.scr:219`,
`global/vehicles_thinkers.scr:62-91`).

### Step 7 — Define the per-player spawn/respawn callbacks you need (optional)
HZM dispatches four optional labels in `maps/<mapname>.scr` via
`coop_mod/main.scr::startThread` (which spawns a `trigger_once setthread <label>` then
`doActivate` — `main.scr:863-878`). Missing labels are silently ignored (the engine
`setthread` to a nonexistent label is a no-op), so each map defines only what it needs.

| Callback label | Dispatched from | Fires |
|---|---|---|
| `coop_playerJustSpawned` | `player.scr:822` | first spawn of a player |
| `coop_playerJustRespawned` | `player.scr:819` | each respawn |
| `coop_playerJustDied` | `player.scr:1071` | each death |
| `coop_playerJustLeft` | `player.scr:129` | disconnect |

(Note the real names are `coop_playerJust*`, not `coop_playerDied`/`Respawned`/`Left`.)

### Step 8 — Coop spawn locations + (vehicle/ride only) setup threads
- Maps update player spawn anchors as players progress, via
  `coop_mod/spawnlocations.scr::<map>_update1/2/3` (m1l1 `:2882`).
- Ride/vehicle maps add a `coop_setup` / `coop_setupAttach` thread pair guarded by
  `if(level.gametype != 0)` right after the init prologue (m1l3b `:9-12`).

### Step 9 — Precache (AA only): add `exec coop_mod/precache.scr`
All `m*_precache.scr` call `exec coop_mod/precache.scr` as the first line.
**e-series and t-series precache files do NOT** — a confirmed integration gap (coop assets
not precached for Breakthrough/Spearhead → possible late-load hitches / missing emitters).

### Step 10 — `missioncomplete` / `missionfailed` are NOT changed at the map level
Per-map calls stay vanilla: `exec global/missioncomplete.scr <next> 1`
(HZM `m1l1.scr:2772` == vanilla `m1l1.scr:2910`; same for e1l1). The coop-awareness is
centralized in the GLOBAL script: `global/missioncomplete.scr:13-14` branches to
`coop_mod/missioncomplete.scr::main` when `inCoopMode`. So you do not touch missioncomplete
calls when porting a map — only `missionfailed` (mid-level fail) is swapped for the shim.

---

## 2. Per-archetype notes

### A. Infantry combat map (m1l1, m3l1a, m3l1b)
- Steps 1–6 + spawn locations. The bulk of the diff is mechanical `replace.scr` swaps and
  `$player.size` loops; combat AI, exploders, spawners are otherwise vanilla.
- m1l1 also fixed a vanilla **infinite loop**: vanilla `while ($ending_spawner)` (m1l1 `:53`)
  became a bounded `for(...$ending_spawner.size...)` (HZM `m1l1.scr:57`) — "fixed infinity
  loop during multiplayer".
- m1l1 removes `exec global/loadout.scr` (commented out, `:23`) — coop manages loadout itself.
- D-Day (m3l1a `:165-167`): `level.coop_playerGlue = 1`, `level.coop_noDropHealth = game.true`.

### B. Ride map — player is a passenger (m1l1 truck intro, e1l1 jeep, m1l3b jeep)
- `level.coop_disableSpawnWarper = game.true` during the ride; players glued so they ride
  together. `coop_setup` (m1l3b `:985`) threads: `coop_fixTriggers` (so an empty/Grillo-only
  jeep can still fire triggers when all players are dead — `:1100`), `coop_spawnBlockers`
  (spawn invisible clip walls so players can't fall off the moving map — `:1067`, uses
  `replace.scr::spawnclip`), `coop_updateSpawns` (continuously re-anchors all 8 player spawns
  to the jeep's passenger tag — `:1021`), `coop_transporterAccident` (tele players back to the
  jeep if they fall under the map — `:1045`).
- `coop_playerJustRespawned` teleports a respawned player back to the jeep only if they are
  >3000 units away (m1l3b `:1010`) — avoids yanking nearby players.

### C. Playable-vehicle map — player drives (m5l2b tank, e1l1 tank phase)
- Most involved archetype. Vanilla calls a single BLOCKING thinker
  `$playertank waitthread global/vehicles_thinkers.scr::players_tank` (vanilla m5l2b `:33`).
- HZM forks on gametype (HZM `m5l2b.scr:48-90`):
  - SP (`level.gametype == 0`): runs the vanilla blocking `players_tank`.
  - Coop (`!= 0`): inlines only the NON-blocking setup portion (entity scan to attach
    `coop_tankOffset` / `coop_tankExit` mount tags via `attachmodel`; spawn a
    `level.playertanktarget` script_origin glued 80u above the tank so enemy flak/tanks have a
    valid aim target), sets `level.coop_playerTank = $playertank` so trigger validators and
    `level_end` see the tank as activator, then threads `coop_autoDriveTank` to move it and
    `player_tank_health` for damage + optional human boarding.
- e-series puts this logic in dedicated sub-scripts: `maps/e1l1/playerTank.scr`,
  `maps/e1l3/TankRide.scr` (camera glued to `$coop_playerTankGlue`).
- `coop_immuniseFromBullets` is applied to enemy vehicles/flak/exploder triggers on m5l2b so
  bullet damage can't bypass the intended destruction method.
- For a standard on-foot officer/boss encounter these maps are effectively non-viable.

### D. Objective / mission flow
- `missioncomplete` unchanged at map level (Step 10).
- m4l3 injects ammo on first spawn via `coop_playerJustSpawned` (`m4l3.scr:1549`):
  `local.player ammo pistol 80` / `ammo grenade 6` (guards `health<=0`, `$world`, NULL).
- Side-objective HUD pushes (slots 7/8) need an explicit `coop_objectivesSendPlayer` call;
  the ObjMgr only auto-pushes at spawn (see `coop_objectives_hud.md`).

---

## 3. Per-map callback implementation table

Confirmed by grep over `hzm-mohaa-coop-mod/maps/*.scr` (current as of 2026-06-23; several
e/t-series now define callbacks that older notes listed as "no integration"):

| Map | JustSpawned | JustRespawned | JustDied | JustLeft |
|-----|:--:|:--:|:--:|:--:|
| m1l1 | ✓ (crouch-in-truck) | | | |
| m1l3a | | ✓ | ✓ | ✓ |
| m1l3b | | ✓ (tele to jeep) | ✓ | ✓ |
| m1l2b | | | ✓ | |
| m2l3 | ✓ | | | |
| m3l1a | ✓ | | | |
| m4l3 | ✓ (ammo inject) | | | |
| m5l2a | | | ✓ | |
| m6l3d | ✓ | | | |
| e1l1–e1l4 | ✓ | ✓ | | ✓ |
| e2l1–e2l3 | ✓ | ✓ | | ✓ |
| e3l1, e3l2, e3l4 | ✓ | ✓ | | ✓ |
| t1l2, t1l3, t2l1, t2l3 | ✓ | ✓ | | ✓ |

Notes: `coop_playerJustDied` is rare (4 maps — vehicle/ride maps that must eject a dead
driver). The e/t-series rows show recent integration progress beyond the 2-day-old survey;
t-series is no longer uniformly "pure vanilla."

---

## 4. Vanilla lines that must be REMOVED or GUARDED (and why)

| Vanilla construct | HZM treatment | Why |
|---|---|---|
| `level waittill spawn` | replaced by `waitForPlayer` | host-only spawn would start combat before other coop players exist |
| `while ($ending_spawner)` (m1l1 `:53`) | bounded `for` over `.size` | the unbounded loop spins forever in MP → "infinite loop" crash |
| `exec global/loadout.scr` (m1l1 `:20`) | commented out | coop assigns loadout itself; vanilla loadout fights coop weapon mgmt |
| `$player stufftext "tm..."` music | `replace.scr::tmstartloop/tmstop` | client console command only reaches the host; others get no music |
| `$player isTouching/cansee/item/ammo/...` | `replace.scr::` shims | singular `$player` misses players 2..N; shims loop all active players |
| blocking `players_tank` thinker | gametype-forked inline setup | the blocking driver-select loop would freeze the coop main thread |
| `$player heal 1` (e3l1/e3l4) | guarded `if(!level.gametype)` | SP-only heal hack; harmless but should not fire each coop frame |
| `println` spam (m1l3b `:22`, m1l1 `:59-60`) | removed/commented | reduces server log spam in coop ("we already have sufficient spam") |

Guard idioms: `if(level.gametype == 0){ ...SP... }` and `if(level.gametype != 0){ ...coop... }`
(gametype 0 = singleplayer). Player-active test:
`local.player.health > 0 && local.player.dmteam != "spectator" && local.player.flags["coop_isActive"] == 1`.

---

## 5. Gotchas (carry these into any new port)

1. **Parse killers** (from `mohaa_script_notes.md`, all confirmed): em-dash, a bare negative
   number inside parentheses, UTF-8 BOM, spawn keyvalue args, an unknown command, and a
   multi-line `&&`/`||` condition. SPAWN RULE: spawn a bare classname only, then set
   properties on the following lines (`spawn trigger_once` then `setthread`, never
   `spawn trigger_once setthread ...` with a keyvalue arg that the parser rejects).
2. **`$player` is an ARRAY in coop, 1-indexed.** Never assume singular. Use `$player.size`
   and `$player[local.i]`. `$player[1]` is not guaranteed to be the host.
3. **`moveto`/`move`/`waitmove` SILENTLY no-op on script_models** (`script_model_movement...`):
   for moving non-actor models, origin-step each tick or use `flypath`/`SplinePath`. This bites
   ride/vehicle conversions that try to move a glued `script_model`.
4. **Camera and freeze are GLOBAL.** `cuecamera` / `freezeplayer` affect ALL players. For
   coop-safe per-player camera use `trigger_camerause` + `doUse` per player (m1l1 pattern);
   see `engine_systems_advanced.md`.
5. **`waitthread coop_mod/main.scr::main` blocks** — anything before it (other than the
   `level.coop_*` flags it reads at init) runs without coop set up. Put the flags above it,
   everything else below.
6. **Missing callback labels are safe** — `startThread` tolerates an undefined
   `maps/<map>.scr::coop_playerJust*` (no-op activation), so only define the ones you need.
7. **`level.script` must be set** before using `validateTriggerActivator`/`cloneTrigger`
   (they call `setthread level.script::<thread>`). m-series like m1l1 omit it because they
   don't use those helpers; e1l1 sets it (`e1l1.scr:10`).
8. **e/t precache gap**: e-series and t-series `*_precache.scr` do not `exec coop_mod/precache.scr`.
   Add it when porting those, or expect missing-emitter / late-load issues.
9. **Spawn warper window**: while `level.coop_disableSpawnWarper = game.true`, respawning
   players are NOT repositioned — don't spawn a boss / open combat during a glued ride intro.

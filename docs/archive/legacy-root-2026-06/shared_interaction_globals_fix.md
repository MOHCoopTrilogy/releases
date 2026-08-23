# Shared Interaction Globals - Coop Conversion

Date: 2026-06-24
Scope edited: ONLY `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\global\*.scr`
No coop_mod framework, maptest, watchdog, or individual map scripts touched. No pk3 rebuild, no launch.

Goal: make every calling map's INTERACTIVE objective (mount gun / plant charge / use-at-distance)
work for any of up to 16 coop players, by coop-converting the SP-shaped SHARED interaction globals
while keeping the single-player path and the working M-series coop paths byte-identical.

---

## Pattern learned (the coop-correct "who can interact" gate)

From `coop_mod/replace.scr::player_closestTo` (:333-371), `::withinDistanceOf` (:1651-1706),
`coop_mod/cannonThink.scr::cannonThink` (:40-71), and the e3l2 fix
`maps/e3l2/cannons.scr::CoopGunOrChargeThink` (:219-323):

- SP branch is `if (level.gametype == 0){ ... }` and uses the bare `$player`.
- Coop branch loops `for(local.i=1;local.i<=$player.size;local.i++)` and accepts a player only if:
  `health > 0` AND `dmteam != "spectator"` AND `flags["coop_isActive"] == 1` AND
  `flags["coopDevNoclip"] == NIL`.
- `DistanceUse.scr` `end`s returning the player who pressed use; callers store that player.

---

## Per-global findings

### 1. `global/MountGunOrPlantCharge.scr` - WAS SP-SHAPED -> NOW COOP-CONVERTED

- **State before:** the gun-mount / charge-plant state machine polled the bare `$player` array head
  (`$player.useheld`, `$player.angles`, `$player.origin`, `local.usable_cannon canuse $player`,
  `vector_within $player.origin ...`). In coop only `$player[1]` (the host) could ever mount the
  Modello or plant the charge. This is the single RED in `objective_coop_confidence.md`.
- **Callers (blast radius):**
  - `maps/e3l2/cannons.scr` was the ONLY consumer that referenced `global/MountGunOrPlantCharge.scr`.
    It was ALREADY re-routed to the per-player `CoopGunOrChargeThink` (the prior e3l2 fix), so it no
    longer calls this global at all. The global therefore currently has ZERO live callers.
  - `maps/e1l2/Artillery.scr` and `maps/e2l1/aaguns.scr` define their OWN local `GunOrExplosive` /
    `HoldChargePlace` threads (e1l2 already has a `coop_GunOrExplosive` hotfix). They do NOT use this
    global. Left untouched (out of scope; they are map scripts, not globals).
- **What I changed:** wrapped the existing while-loop state machine in `if (level.gametype == 0){ ... }`
  (SP, byte-identical to shipped) and added an `else { ... }` coop branch. The coop branch:
  - keeps all shared setup (geometry constants, `self.player_status="away"`, throbber-component math)
    unchanged - none of that reads `$player`;
  - each frame selects an "actor": if a player is already engaged (`status onGun`/`didSetThrobber`)
    and still valid, that player keeps ownership (so only the mounter can dismount); otherwise it
    scans all active players (the gate above) and picks the first within gun OR throbber range,
    preferring one pressing use;
  - if no eligible player, resets to `"away"`, clears help text, idles a frame;
  - otherwise runs the EXACT SAME state machine (away/nearGun/onGun/nearThrobber/didSetThrobber),
    the SAME map callbacks `self waitthread local.script_file_name::local.get_on/off/place_*`,
    and the SAME `level.mgopc_did_mount_gun` / `level.mgopc_did_set_throbber` completion flags,
    substituting `local.actor` for `$player`.
- **SP / M-series preservation:** the SP path is literally the original lines, only indented one
  brace deeper; no token inside it changed. No working M-series map calls this global, so no coop map
  regresses. Function signature, return convention (`end`), and the throbtext help wiring are unchanged.
- **Residual risk:** LOW-to-MODERATE.
  - The global has no live caller right now, so this is a forward-safety / parity conversion; it can
    only matter if a map is (re)wired to call the global directly.
  - The coop "actor" hand-off is single-occupant by design (matches the original single-gun semantics
    and `CoopGunOrChargeThink`). If the engaged player dies or leaves, ownership releases next frame and
    any other active player can take over - no deadlock.
  - Help text via `global/throbtext.scr` is a shared HUD throb (as in SP); with multiple nearby players
    it follows whichever actor is selected. Cosmetic only; does not gate completion.

### 2. `global/DistanceUse.scr` - ALREADY COOP-CORRECT (GREEN) - LEFT UNCHANGED

- **Resolution of the GREEN-vs-SP-shaped question:** GREEN is correct; it is NOT merely
  gametype-gated-coincidence. The proximity test already routes through
  `coop_mod/replace.scr::withinDistanceOf` (which is gametype-gated internally and loops all active
  players in coop). More importantly, the USE test (`DistanceUse.scr:42-52`) explicitly loops
  `1..$player.size` with the full active-player gate (`health>0 && dmteam!="spectator" &&
  coop_isActive==1 && coopDevNoclip==NIL`) and `end local.player` returns the specific player who
  pressed use. The four `$player` hits the audit counted are all COMMENTED-OUT remnants of the old SP
  code (lines 18, 29, 38) plus the loop variable - there is no LIVE bare-`$player` interactive poll.
  So DistanceUse is genuinely "any player can use it," not host-only. No change needed.
- **Callers (all store/consume the returned player correctly):**
  - `maps/e3l1/BritHQ.scr:207,209` - medic jeep board, loops until a player returns, passes to ride.
  - `maps/e3l1/JeepRidePart3.scr:356` - `level.playerJeepGunner = waitexec ... DistanceUse`.
  - `maps/e3l3/scene3.scr:190` - AB41 use.
  - `maps/e3l4/Tower.scr:706` - desk-radio "confirm airstrike" use.
  No m/t-series map calls it directly (t-series uses its own/level-global gates per the audit).

### 3. `global/stickybomb.scr` - DOES NOT EXIST

- No such file under `global/`. The only `stickybomb` references in the tree are the HUD item string
  / weapon name in `global/items.scr:331-334` (`item_stickybomb`, `stickybomb_pickup`) and weapon
  pickups in t-series map scripts (`maps/t2l1.scr`, `t2l3.scr`, `t3l1.scr`, `t3l2.scr`, etc.) and
  `ubersound`. These are weapon/HUD strings and per-map pickup logic, not a shared interaction global.
  Per the audit, sticky-bomb plant/throw completion is driven by level-global flags (any player),
  already GREEN. Nothing to convert here.

### 4. `global/democharge.scr` - DOES NOT EXIST

- No such file. `democharge` references are HUD graphic names in `global/items.scr:345-370`
  (`textures/hud/democharge0..5`) - the demo-charge ammo HUD icons. The actual t1l3 "plant 4 demo
  charges" objective is level-global (`level.charge1-4`/`level.chargecount`, any player) per the audit.
  No shared interaction global to convert.

### 5. `global/stationaryweapons.scr` - DOES NOT EXIST

- No such file. No `stationaryweapons` / `stationary_weapon` global in the tree. Stationary/turret
  mounting in coop is handled by `coop_mod/cannonThink.scr` (cannon primitive), per-map dismount loops
  (e2l1 tower MG42, e2l2 jeep turret, t2l2 halftrack), and `global/mg42.scr`/`mg42_active.scr`/
  `mg42init.scr`/`turret.scr` (not named as targets and not in the SP-shaped interactive set the task
  scopes). Nothing matching the named target to convert.

---

## Summary

- **Coop-converted:** `global/MountGunOrPlantCharge.scr` (1 file). SP path byte-identical inside
  `if(level.gametype==0)`; new `else` coop branch loops all active players and drives the identical
  state machine + completion flags. Live callers: none (e3l2 already bypasses it via
  `CoopGunOrChargeThink`); converted for forward-safety and so any future direct caller is coop-correct.
- **Already coop-correct, left as-is:** `global/DistanceUse.scr`. The audit's GREEN is accurate - it
  loops `1..$player.size` with the active-player gate and returns the using player; the bare-`$player`
  lines flagged are commented-out SP remnants. Callers: e3l1 BritHQ + JeepRidePart3, e3l3 scene3,
  e3l4 Tower.
- **Do not exist:** `global/stickybomb.scr`, `global/democharge.scr`, `global/stationaryweapons.scr`.
  Those names are HUD item/weapon strings (`global/items.scr`) and per-map pickup/flag logic, not
  shared interaction globals. No conversion possible or needed; the corresponding objectives are
  already level-global / GREEN per the audit.

## Parse hygiene (verified on the edited file)

`global/MountGunOrPlantCharge.scr`: no BOM, 0 non-ASCII bytes, no em-dash / Win-1252 quotes;
braces 63/63, parens 168/168, brackets 20/20 balanced. Compound `&&`/`||` conditions kept on one
line. No bare negative inside parens (only vectors). `$player` 1-indexed in the coop loop.

# Vehicle Scene-Test Harness

Automated board -> drive -> dismount tester for the HZM coop mod. Sibling of the
on-foot Phase 2 harness (`coop_maptest 2`, `maptest_phase2.scr`), which can teleport /
survive / die but cannot board or drive vehicles. This harness SCRIPTS the vehicle
interaction by calling the coop mod's own vehicle API directly, then verifies success
via a MOVEMENT POLL plus greppable `VTEST_` banners.

Status: staged edits only (game NOT run - a re-test is in progress).

## New files

- `hzm-mohaa-coop-mod/coop_mod/maptest_vehicle.scr` - the harness (cvar `coop_maptest_vehicle`).
- `hzm-mohaa-coop-mod/coop_mod/cfg/maptest_vehicle_start.cfg` - the launcher.

## Core primitive: the MOVEMENT POLL

`coop_vtest_pollMove <ent> <secs>` samples `ent.origin` once/sec for `secs` seconds and
returns total path length travelled. The caller compares against a per-archetype threshold:

- travel > threshold  -> `_MOVING` banner (driving works)
- travel <= threshold -> `_STUCK` banner (FLAG; e.g. the t3l2 silent-no-board risk)
- ent NULL/NIL        -> returns -1 (board never produced a vehicle to poll)

It tolerates the vehicle being deleted mid-poll (scene-end `delete`) by breaking and
keeping the distance accumulated so far.

## Per-map config table

| Map   | Archetype | Profile | Board fn (how the test boards)                                  | Vehicle ent polled            | End condition                              |
|-------|-----------|---------|------------------------------------------------------------------|-------------------------------|--------------------------------------------|
| m1l1  | A ride    | BT (2)  | auto (map spawn mgr); verify only                                | `$coop_truckOrigin` / `$introtruck` | `level.flags[ridecomplete]==1`        |
| e1l1  | A ride    | BT (2)  | auto; verify only                                                | `$jeep`                       | `level.RideOver==1`                        |
| e1l4  | A ride    | BT (2)  | auto; verify only                                                | `$starttruck`                 | `level.RideOver==1`                        |
| e2l1  | A ride    | BT (2)  | auto; verify only                                                | `$glider`                     | `level.gliderRideOver==1`                  |
| t1l1  | A ride    | SH (1)  | auto (base-pak gag; coop layer not yet built - P2 gap)           | `$playerspot_plane` / `$the_plane` | bounded wait (no coop flag yet)       |
| m1l3b | B escort  | BT (2)  | `maps/m1l3b.scr::coop_playerForceToJeep $player[1]`              | `level.playerjeep` (`$playerjeep`) | poll, then detach turret slot 0       |
| m1l3c | B escort  | BT (2)  | none present (map is on-foot) -> emits `VTEST_SKIP jeep_ent_missing` | n/a                       | skip                                       |
| t2l2  | B escort  | SH (1)  | `maps/t2l2.scr::coop_playerForceToJeep $player[1]`               | `level.playerjeep` (`$s1_jeep1`) | poll, then detach turret slot 0       |
| m5l2b | C tank    | BT (2)  | `global/vehicles_thinkers.scr::coop_setDriverForTank` on `$playertank` | `$playertank`          | detach driver slot, place at `$coop_tankExit` |
| t3l2  | C tank    | SH (1)  | `global/vehicles_thinkers.scr::coop_setDriverForTank` on `$playertank` | `$playertank`          | detach driver slot, place at `$coop_tankExit` |

Notes:
- Pattern A: the ride auto-starts when the host spawns (the map's own per-player camera
  spawn manager handles it). The harness does NOT force-board; it verifies the vehicle is
  MOVING and the ride-complete flag eventually sets and control returns.
- Pattern B: `coop_playerForceToJeep` is MAP-LOCAL (defined inside each map script, not a
  shared global), so it is dispatched per-map by namespace. The fallback raw board
  (`attachturretslot 0` + flag) is used for any Pattern-B map lacking the fn (m1l3c).
- Pattern C: `coop_setDriverForTank` IS a shared global in `vehicles_thinkers.scr`. Before
  boarding, the harness checks `$coop_tankOffset != NULL` - if it is NULL it emits
  `VTEST_TANK_BOARD_FAIL coop_tankOffset_NULL` immediately. This is the explicit detector
  for the documented t3l2 risk (T-34 cannon scan fails -> nobody can ever board, silently).

## main.scr hook line (ADD THIS - one line)

In `hzm-mohaa-coop-mod/coop_mod/main.scr::main`, alongside the existing Phase 1 / Phase 2
hooks (currently lines 128-133), add:

```
	if( getcvar( "coop_maptest_vehicle" ) == "1" ){
		thread coop_mod/maptest_vehicle.scr::coop_maptest_vehicle_tick
	}
```

Place it immediately after the existing `if( getcvar( "coop_maptest" ) == "2" ){ ... }`
block (it mirrors that block exactly). It is a no-op in normal play (cvar defaults unset).

## How to launch

From the in-game console (`~`) at the main menu, or via the watchdog launch command.

Breakthrough vehicle maps (m1l1, m1l3b, m5l2b, e1l1, e1l4, e2l1 - com_target_game 2):
```
openmohaa.exe +set com_target_game 2 +exec coop_mod/cfg/maptest_vehicle_start.cfg
```
(defaults to first map m1l1).

Spearhead t-series vehicle maps (t1l1, t2l2, t3l2 - com_target_game 1). Edit
`maptest_vehicle_start.cfg` `set ui_dmmap` to the desired t-map first, then:
```
openmohaa.exe +set com_target_game 1 +exec coop_mod/cfg/maptest_vehicle_start.cfg
```

The harness advances ONE vehicle map at a time via `^~^~^ MAPTEST_PHASE_END <next>`: the
operator updates `ui_dmmap` to the printed next vehicle map, rebuilds the pk3, and
RELAUNCHes (mirrors the on-foot batch flow). Stop with:
```
exec coop_mod/cfg/maptest_stop.cfg
```
Reuses the SAME watchdog + spawn clicker as Phase 1/2 (it emits the
`^~^~^ MAPTEST_LOADED <map>` banner the clicker watches for).

## Grep banners

```
^~^~^ MAPTEST_LOADED <map> (<idx>/<total>)   <- clicker trigger (shared)
^~^~^ VTEST_BEGIN <map> arch=<A|B|C>
^~^~^ VTEST_SKIP <map> reason=<...>          <- not a vehicle map / ent missing
^~^~^ VTEST_RIDE_START <map> ent=<name>      (A)
^~^~^ VTEST_RIDE_MOVING <map> dist=<n>       (A)  driving works
^~^~^ VTEST_RIDE_STUCK <map> dist=<n>        (A)  FLAG ride never moved
^~^~^ VTEST_RIDE_DONE <map> ridecomplete=<0|1> (A)
^~^~^ VTEST_BOARDED <map> ent=<name>         (B)
^~^~^ VTEST_BOARD_FAIL <map>                 (B)  FLAG attach never took
^~^~^ VTEST_GUN <map> slot=0                 (B)
^~^~^ VTEST_MOVING <map> dist=<n>            (B)
^~^~^ VTEST_STUCK <map> dist=<n>             (B)  FLAG boarded but static
^~^~^ VTEST_DISMOUNT <map>                   (B)
^~^~^ VTEST_TANK_BOARDED <map> ent=<name>    (C)
^~^~^ VTEST_TANK_BOARD_FAIL <map> [reason]   (C)  FLAG driver slot never took
^~^~^ VTEST_TANK_MOVING <map> dist=<n>       (C)
^~^~^ VTEST_TANK_STUCK <map> dist=<n>        (C)  FLAG t3l2 silent-no-board risk
^~^~^ VTEST_TANK_END <map>                   (C)
^~^~^ VTEST_DONE <map>
^~^~^ MAPTEST_PHASE_END <next>               <- watchdog auto-transition (shared)
^~^~^ MAPTEST_COMPLETE                        <- watchdog stop (shared)
^~^~^ MAPTEST_PAUSED <reason>
```

Quick triage grep for the failure flags:
```
grep -E "VTEST_(RIDE_STUCK|STUCK|TANK_STUCK|BOARD_FAIL|TANK_BOARD_FAIL|SKIP)" <log>
```

## Boarding method: script-force (preferred) vs USE-simulation (optional)

This harness uses SCRIPT-FORCE boarding: it calls the coop board API directly
(`coop_playerForceToJeep` / `coop_setDriverForTank`). This is deterministic and exercises
the exact attach/drive/dismount code the real gameplay uses, and cleanly separates "board
code broken" (`_BOARD_FAIL`) from "vehicle not driving" (`_STUCK`).

The OPTIONAL alternative is USE-simulation: position the host within the board volume and
`stufftext "+use"` to drive the map's own `coop_jeepNotOccupied` / `coop_selectDriverForTank`
USE-detection. It is NOT used here because it is timing fragile (depends on the player being
inside the board radius at the right frame) and would conflate "board code broken" with
"player not close enough." Script-force is the better automated-test method; USE-sim would
only be worth adding later as a secondary end-to-end check of the USE-detection loop itself.

# Fix: m5 series re-inclusion + m5l3 scene-walk (outstanding item #7)

Date: 2026-06-24. Staged edits only (no rebuild/launch). All paths under
C:\mohaa-coop-dev\hzm-mohaa-coop-mod\. ASCII, no BOM/em-dash, single-line
&&/||, balanced braces/parens, $player 1-indexed.

## PART A - m5l2b re-inclusion (DONE)

File: coop_mod/maptest.scr (coop_maptest_list block).

- Re-added m5l2b at slot 23 (between m5l2a @22 and m5l3, which moves to @24).
  Basis: MAX_MSGLEN raised to 131072 this project (Issue #14) - same basis used
  for the m6l1c re-add. Deleted the old "m5l2b SKIPPED ... exceeds MAX_MSGLEN
  (49152)" comment; replaced with a re-add note.
- Everything from the old slot 23 (m5l3) onward shifted +1. List end is now
  local.m[53] = "t3l2" (was [52]).
- WAYPOINTS: NO change to coop_mod/maptest_waypoints.scr needed. m5l2b HAS live
  spawner markers (4 $enemyspawner, per map_entities/m5l2b_parsed.txt), so the
  Phase 2 patrol resolves its source from $enemyspawner at runtime; the
  bsp_waypoints branch is only the NIL-source fallback. m5l2b is a single linear
  coop_autoDriveTank scene and tours/observes fine.

### PHASE_END index-comment fixes (shifted by one)

PHASE_END fires at multiples of batch_limit (5). After the +1 shift the maps
landing on those indices changed; comments updated accordingly:

| idx | OLD map (comment) | NEW map (comment) |
|-----|-------------------|-------------------|
| 30  | m6l3b             | m6l3a             |
| 35  | e1l2              | e1l1              |
| 40  | e2l3              | e2l2              |
| 45  | t1l2              | t1l1              |
| 50  | t2l4              | t2l3              |

(The "// PHASE_END fires here" comment now sits on the new occupant of each of
those five slots. e3l3 stays SKIPPED; t-series still need the com_target_game=1
Spearhead profile.)

## PART B - m5l3 scene-walk (DONE)

m5l3 is a single sniper-overwatch map, not a multi-BSP scene rotation. Standard
Phase 2 spawns a player (clears replace.scr::waitForPlayer) but never parks them
in a bino volume, so only Phase A (intro) runs; the vehicle spawns, exploders,
AI waves and King Tiger health HUD all go untested. The scene-walk drives the
bino-gate from OUTSIDE m5l3.scr (which is unchanged - read only).

### New files

- coop_mod/maptest_m5l3.scr - thread coop_maptest_m5l3_walk plus helpers
  parkOnBino / reportEnt / advance.
  Flow: waitForMainScript; bail unless coop_maptest==2 AND coop_maptest_m5l3==1
  AND level.coop_mapname==m5l3; wait for player; emit shared
  ^~^~^ MAPTEST_LOADED m5l3 (clicker fires); set 999999 health; banner each key
  entity (MAPTEST3_ENT for $binomid/$binoleft/$binoright/$obj5/$playertank/
  $flak88/$plunger, origin or MISSING); pick a bino volume (mid>left>right);
  PHASE B - teleport player onto the volume and RE-ASSERT origin+health every
  ~2s for ~90s (unblocks objgen:417 -> readytosnipe + playertank dodrive +
  enemytankstart), polling plungergone (MAPTEST3_PLUNGER_GONE), first vehicle
  alive (MAPTEST3_TIGER_SPAWNED / _TIMEOUT) and Artillary_Ready
  (MAPTEST3_ARTY_READY); PHASE E - FORCE the King Tiger gate by collapsing
  level.wintime to level.time (m5l3.scr inits it to time+500000) while keeping
  the player parked, poll Final_Tank_Approaches (MAPTEST3_KINGTIGER_SPAWNED /
  _TIMEOUT) for ~120s, then observe ~30s; STOP before the PHASE F win
  (King_Tiger_Lost -> objgen:587 -> missioncomplete), emit
  MAPTEST3_ALL_SCENES_OBSERVED, hand back to coop_maptest_transition (shared
  phase-end + transition logic via the advance helper).
  Banners: MAPTEST_LOADED, MAPTEST3_ENT, MAPTEST3_SCENE, MAPTEST3_PLUNGER_GONE,
  MAPTEST3_TIGER_SPAWNED/_TIMEOUT, MAPTEST3_ARTY_READY,
  MAPTEST3_KINGTIGER_SPAWNED/_TIMEOUT, MAPTEST3_ALL_SCENES_OBSERVED,
  MAPTEST3_ADVANCE, MAPTEST_PHASE_END, MAPTEST_COMPLETE.

- coop_mod/cfg/maptest_m5l3_start.cfg:
    seta coop_maptest 2
    seta coop_maptest_m5l3 1
    seta coop_maptest_dwell 600
    seta coop_dbno 0
    seta g_scriptcheck 0
    set ui_dmmap m5l3
    exec coop_mod/start_server.cfg

### New cvar

coop_maptest_m5l3 (default 0). Only meaningful when coop_maptest==2.

### main.scr hook line (FOR YOU TO ADD - I did not edit main.scr)

In coop_mod/main.scr::main, beside the existing Phase 2 hook (the
`if( getcvar( "coop_maptest" ) == "2" ){ thread .../maptest_phase2.scr::... }`
block around lines 131-133), add:

    if( getcvar( "coop_maptest" ) == "2" && getcvar( "coop_maptest_m5l3" ) == "1" ){
        thread coop_mod/maptest_m5l3.scr::coop_maptest_m5l3_walk
    }

RECOMMENDED: also gate the generic phase2 tick so only the walk runs on m5l3 -
change the existing block to:

    if( getcvar( "coop_maptest" ) == "2" && getcvar( "coop_maptest_m5l3" ) != "1" ){
        thread coop_mod/maptest_phase2.scr::coop_maptest_phase2_tick
    }

(If left ungated, both threads run on m5l3 - the generic patrol would fight the
walk's teleport-to-bino each tick. The cfg only sets coop_maptest_m5l3 for the
m5l3-specific launch, so normal Phase 2 runs are unaffected either way.)

### How to launch

1. Add the hook line(s) above to main.scr, rebuild the mod pk3.
2. From the console: exec coop_mod/cfg/maptest_m5l3_start.cfg
3. Use the same spawn clicker + watchdog as Phase 2 (MAPTEST_LOADED convention).
4. Grep the console log for ^~^~^ MAPTEST3_ banners per phase. The walk stops at
   MAPTEST3_ALL_SCENES_OBSERVED, then advances the rotation normally (or you can
   leave coop_maptest_m5l3 1 and it just re-runs the walk if you reload m5l3).

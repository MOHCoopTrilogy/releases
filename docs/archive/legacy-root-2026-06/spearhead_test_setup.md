# Spearhead (t-series) Phase-2 Test Harness Setup

Created 2026-06-24. Staged edits only (no pk3 rebuild, no launch, no GOG/watchdog changes).
All edits under C:\mohaa-coop-dev. Did NOT touch main session's owned files
(main.scr, player.scr, replace.scr, maptest_phase2.scr, spawn_clicker.ps1, watchdog).

## 1. t-series confirmed set (9 maps)
maps/*.scr under hzm-mohaa-coop-mod/maps:
  t1l1, t1l2, t1l3, t2l1, t2l2, t2l3, t2l4, t3l1, t3l2
Each has a matching <map>_precache.scr. No t-series subdirectories (all scripts flat in maps/).
All 9 already contain coop_mod/main.scr::main (per COOP_CONVERSION_MASTER.md) so the
maptest tick fires and can self-advance.

## 2. Why a separate profile
t-series BSPs live in mainta/pak*.pk3 (Spearhead). The engine mounts those ONLY under
com_target_game=1. The Breakthrough rotation (m/e maps) runs under com_target_game=2, which
does not mount mainta -> "Can't find map" / null-deref on transition. So the t-series needs
its own launch cfg + a com_target_game=1 launch. They are listed in the same rotation list
but only resolve under the Spearhead profile.

## 3. Edits made

### a. coop_mod/maptest.scr (rotation list only)
Replaced the old "t-series EXCLUDED" comment block with t-series entries appended after e3l4:
  local.m[44]=t1l1  [45]=t1l2  [46]=t1l3  [47]=t2l1  [48]=t2l2
  [49]=t2l3  [50]=t2l4  [51]=t3l1  [52]=t3l2
m/e entries left intact. PHASE_END (batch_limit=5) now fires at idx 45 (t1l2) and 50 (t2l4).
Did not touch the transition logic (coop_maptest_transition) -- the existing raw "map <next>"
path works for t-maps once mainta is mounted.

### b. coop_mod/maptest_waypoints.scr (APPENDED t1l1 only)
Added one getWaypoints branch: `} else if( local.mapname == "t1l1" )` with 32 vectors,
mirroring the existing 32-vector-per-map format exactly (tabs, ( x y z ), ASCII).
Brace/paren balanced (verified: 47/47 braces, 1464/1464 parens). 32 entries confirmed.
SOURCE: 908 info_pathnode "origin" values from map_entities/t1l1_entities.txt, sorted by X
and even-sampled to spread across the playable area (X -5076..-714, Y -5064..5480, Z authored
~-7030..-6516, a single vertical zone for this map).
Only t1l1 needed waypoints (see tour-source table below).

### c. coop_mod/cfg/maptest_start_sh.cfg (NEW)
Mirrors maptest_start.cfg: coop_maptest 2, coop_maptest_dwell 300, waypoints 20, dwell_wpt 8,
coop_dbno 0 (high-health/god + clean death test), g_scriptcheck 0. Difference:
`set ui_dmmap t1l1` and a header comment that it MUST be launched with com_target_game 1.
ASCII clean.

## 4. Per-map tour source
Determined from map_entities/<map>_entities.txt by counting the exact harness lookup keys
($enemyspawnerdestination, $enemyspawner, $alarmspawner targetnames). The phase-2 harness
prefers enemyspawnerdestination > enemyspawner > alarmspawner, then falls back to BSP waypoints.

  map    esd   es   alarm   -> tour source
  t1l1     0    0       0   -> bsp_waypoints  (NEW branch added to maptest_waypoints.scr)
  t1l2     5   89       0   -> enemyspawnerdestination (live)
  t1l3     0    3       0   -> enemyspawner (live)
  t2l1     0   52       0   -> enemyspawner (live)
  t2l2    49   42       0   -> enemyspawnerdestination (live)
  t2l3     2    0       0   -> enemyspawnerdestination (live)
  t2l4     0   58       0   -> enemyspawner (live)
  t3l1     0   79       0   -> enemyspawner (live)
  t3l2     0   27       0   -> enemyspawner (live)

No t-map has alarmspawner markers. Only t1l1 has zero spawner markers -> BSP waypoints.
(Note: enemyspawnertrigger entities exist on several maps but are trigger volumes, not the
actor-position markers the harness teleports to; they are not used as a tour source.)

## 5. Parse-killer static scan (all 18 t-series scripts incl _precache)
Scanned t1l1/t1l2/t1l3/t2l1/t2l2/t2l3/t2l4/t3l1/t3l2 .scr + each _precache.scr for:
  - UTF-8 BOM (EF BB BF)            : none
  - non-ASCII bytes >0x7F           : none (so no 0x92/0x93/0x94 Win-1252 quotes, no em-dash)
  - lines ending in && or || (multi-line condition continuation) : none
  - bare negative number inside parens : none (only legitimate 3-component vectors)
RESULT: ALL CLEAN. No parse-killers found, nothing to fix.

## 6. Watchdog launch command (Spearhead)
Breakthrough (existing m/e profile):
    openmohaa.exe +set com_target_game 2 +exec coop_mod/cfg/maptest_start.cfg
Spearhead (NEW t-series profile, this setup):
    openmohaa.exe +set com_target_game 1 +exec coop_mod/cfg/maptest_start_sh.cfg

After each RELAUNCH: kill the stale spawn_clicker (EXCLUDE current $PID in the match) and
start a fresh spawn_clicker.ps1 (per Feedback: Relaunch Procedure). With com_target_game=1
the qconsole.log path is the Spearhead game dir (mainta), not maintt -- adjust the monitor
if it is pinned to maintt.

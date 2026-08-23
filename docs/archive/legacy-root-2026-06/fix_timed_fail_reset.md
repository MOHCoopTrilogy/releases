# Timed-Fail Objectives + Clean Coop Mission RESET

Investigation + fix date: 2026-06-24. All file:line refs under
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`. Re-test was PAUSED; edits are staged only
(no rebuild/launch). Companion root-cause: `C:\mohaa-coop-dev\e1l4_respawn_loop_rootcause.md`.

---

## PART 1 - Timed-fail objectives in the trilogy

A "timed-fail" objective = a countdown / wait that, if the goal is not met in time, FAILS the
mission. Surveyed every `m/e/t` map under `maps\` for `wait <N>` -> fail, `level.time`
deadlines, timer threads, and the keywords train/board/defuse/escort/survive/countdown.

### The TRAIN-BOARD timer (the one the user spotted) -- CONFIRMED

| Map  | Objective | Timer mechanism (duration + trigger) | Fail condition | Fail call (before fix) |
|------|-----------|--------------------------------------|----------------|------------------------|
| **m2l3** (Destroyed Village / train station, AA M2L3) | "Meet up with allies at train station" -> board the departing train | `thread timetrain` (m2l3.scr:767-788), armed at end of `trainsequence` (m2l3.scr:646). Total ~110s: prints "110/90/70 seconds to get to train", then `stopwatch 60` + looping `bombtick` for the final 60s (m2l3.scr:775-777). HUD stopwatch is the visible countdown. | If `level.completednow != 1` (player has NOT reached `$inthetrain`, m2l3.scr:691) when the timer elapses -> `thread traintakeoff` (m2l3.scr:781). `traintakeoff` (m2l3.scr:795-820) drives the train away, waits 1s, then fails. | **coop:** `iprintlnbold_noloc(" =^= You failed...")` then `exec global/missioncomplete.scr m2l3` (m2l3.scr:818) -- a bsptransition re-run of m2l3, NOT the coop missionfailed path. **SP:** engine `missionfailed` (m2l3.scr:814). |

Notes:
- `endlevelthread` (m2l3.scr:689-709) sets `level.completednow = 1` and (coop)
  `level.trainisleaving = 1` the moment a player enters `$inthetrain`; that is the
  beat-the-timer success that suppresses the fail branch in `timetrain` (m2l3.scr:780-786:
  if already completed it instead threads `coop_levelComplete`).
- This is the ONLY genuine countdown-then-fail objective in the rotation.

### Non-timed mission-fail objectives (for completeness - trigger/death based, not time based)

These call `coop_mod/replace.scr::missionfailed` (or engine `missionfailed`) but on an
event, not a countdown, so they are NOT timed-fail. They DO benefit from the same clean reset
because they all funnel through the same `missionfailed -> restartMap` path:

- e1l2 `Intro.scr::IfDestroyedEndMission` / `IfPlayerRetreatEndMission` (282-301) - minesweeper
  tank destroyed/abandoned (coop fail at :300).
- e1l3 `courtyard.scr` (210/215), `JailBreak.scr` (446) - stealth cover blown.
- e2l1.scr:222 - escort NPC Phillips killed.
- e2l3 `FinalHouse.scr`:264 - protect target.
- e3l2 `prisoner_section_1.scr`:462, `medic_think.scr`:568, `final_section_pows.scr`:455 - POW/medic killed.
- e3l3.scr:95, `scene1.scr`:513 - convoy not stopped.
- e3l4 `Tower.scr`:179/488, `Bunker2.scr`:595, `Bunker3.scr`:150/216, `Escape.scr`:89 - defend objectives.
- m1l2a.scr:602 (SAS agent), m1l3c.scr:327 (drown - coop exempt at :324), m4l1.scr:346 (Lt. Baylor),
  m5l1b.scr:779 / m5l3.scr:612/1322/1831 (tank lost / bridge - debug-gated), m6l3a.scr:1205 (not enough Rangers).
- e1l4 `Intro.scr` papers gate (184) - already coop-guarded; see e1l4 root-cause doc.

Ruled out as fail-timers: m1l2b.scr:673 `stopwatch 8` (bomb cinematic, no fail), m1l1
`level.endleveltime` (friendly pacing, no fail), e1l1 jeep-ride `level.time` (cinematic),
e1l4/SunkShip `level.time` (sink animation timing). t-series maps have no scripted fail timer.

---

## PART 2 - The coop mission-fail / RESET path BEFORE the fix

Chain:  map fail logic  ->  `coop_mod/replace.scr::missionfailed` (replace.scr:2377)  ->
fade-to-red + wait 5  ->  `thread coop_mod/main.scr::restartMap` (replace.scr:2390).

`restartMap` (main.scr:1493) had a maptest guard (Fix B, main.scr:1501-1504 - suppress during
`coop_maptest` 1/2; PRESERVED), then for REAL play built `<map>$` (savepoint suffix) and called
`loadMap` -> `global/missioncomplete.scr <map>$ bsp2bsp` -> `bsptransition`.

Two problems in real coop play (per e1l4_respawn_loop_rootcause.md + maptest.scr notes):

1. **serverId churn / team-select loop.** The `<map>$` savepoint reload bumps `sv.serverId`;
   coop clients see `serverId != sv.serverId`, the engine drops + resends gamestate, and because
   the restart fires before the client settles into a team it lands back on the MP team-select
   menu. Every fresh load re-arms the same fail condition, so it can loop forever (this is exactly
   the e1l4 papers-gate infinite `e1l4$` reload).

2. **silent bsptransition crash.** `bsptransition` funnels through `G_ExitLevel -> gamemap ->
   SV_GameMap_f`, which on a live coop server (`sv.state == SS_GAME`) runs
   `SV_ArchivePersistantFile` (write-then-read). The read lands after the next map's coop
   `main.scr` has populated `game.Vars()` and crashes silently (the m1l1->m1l2a crash).

So the old path did NOT cleanly reload: it churned serverId, could drop players to team-select,
could loop, and could crash. It did not reliably respawn everyone into coop or reset state.

For m2l3 specifically the coop train-timer fail never even reached this path - it ran
`exec global/missioncomplete.scr m2l3` directly (same bsptransition hazard, plus it is a
mission-COMPLETE call masquerading as a fail, so objectives/loadout were treated as a level
advance rather than a true reset).

---

## PART 3 - The clean coop mission RESET (implemented)

The map tester already solved "reload a coop map cleanly" in
`coop_mod/maptest.scr::coop_maptest_transition` (maptest.scr:144-161): use the RAW console
command `map <name>` issued via the server builtin `stuffsrv`. Why it is clean:

- `map` -> `SV_Map_f` -> `SV_SpawnServer(..., qfalse)`: `bTransition` is hardcoded false, so NO
  persistant archive is touched -> no silent crash.
- `map` (unlike `spmap`/`spdevmap`) does NOT force `g_gametype` to single-player, so coop stays coop.
- The fresh load re-runs the level `main` -> `coop_mod/main.scr::main`, so every player re-joins
  COOP through the normal spawn flow (spectator -> `skipTeamAndWeaponSelect` -> `forceValidTeam`
  -> `manageAliveSpawning`), and the timer / objectives / level state are all re-initialised from
  scratch. No "<map>$" savepoint -> no serverId-driven team-select loop, no infinite restart.

### Edit 1 - `coop_mod/main.scr::restartMap` (main.scr:1493-1541)

- PRESERVED Fix B (maptest guard 1501-1504) unchanged.
- Replaced the `<map>$` + `loadMap`/`bsptransition` reload with a clean reset:
  - `local.mapname = waitthread getCleanMapname (getcvar "mapname")` (existing helper at
    main.scr:1593 strips any `$` savepoint suffix), with a fallback to the raw mapname if empty.
  - Mirror the safe-reload housekeeping used by `missioncomplete`/`coop_maptest_transition`:
    `g_scriptcheck 0`, `stopwatch 0`, save+blank `sv_maplist`, stop pending changeGameType.
  - `stuffsrv ("map " + local.mapname)` to reload the CLEAN current map.
  - Logs `^~^~^ COOP_MISSION_RESET <map>`.
- `loadMap` (main.scr:1519) is left intact for its other callers; `restartMap` no longer uses it
  (and no longer depends on `containsText`/`cleanText`).

### Edit 2 - `maps\m2l3.scr::traintakeoff` (m2l3.scr:813-822)

- SP branch unchanged (`missionfailed`).
- Coop branch rerouted from `exec global/missioncomplete.scr m2l3` to
  `exec coop_mod/replace.scr::missionfailed`, so the train-board countdown failure now flows
  through the now-clean coop reset (fade-to-red, then `restartMap` -> clean `map m2l3`). Every
  player resets back into coop with timer/objectives/state re-initialised, no team-select loop.

### Maps rerouted

- **m2l3** (the train map) - coop train-timer fail rerouted to `coop_mod/replace.scr::missionfailed`.

All other timed-relevant and event-fail maps already call `coop_mod/replace.scr::missionfailed`,
so they inherit the clean reset automatically with no per-map edit.

### Parse hygiene

ASCII only, no BOM (`main.scr`/`m2l3.scr` start with `//`), no em-dash, single-line conditions,
no bare negative in parens. Added code blocks are brace/paren balanced (whole-file `(`/`)`
imbalance in main.scr is pre-existing string-literal/comment content, not from these edits).
Did NOT touch objectives.scr, officer.scr, maptest*.scr, spawn_clicker.ps1, player.scr,
maptest_vehicle.scr, or the `startMapCallback` region (main.scr:881).

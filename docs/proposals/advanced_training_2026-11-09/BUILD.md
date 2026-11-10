# Advanced Training on m4l0: build record (2026-11-10)

Status: **built on branches, harness-tested (self-test), NOT deployed, needs a human playtest.**
Plan: [PLAN.md](PLAN.md) (D1-D6). Mod branch `advtrain` (off `hotfix-1.10.53` at 2294f3eb), root branch `advtrain` (off `main`).

## How to run it

- Menu: Multiplayer, Start Game, HZM Coop, page "Training / Secret": tile 2 = **Advanced Training**
  (`set coop_advTraining 1`), tile 3 = **The Farmhouse** (the raid, `set coop_advTraining 0`). Solo = a 1-player listen server.
- Dedicated: `+set coop_advTraining 1 +map m4l0`.
- Dev: `coop_atStation <0-10>` starts at that course position; `coop_atSelftest 1` makes every station drive its own
  features (headless walk); `coop_atDebug 1` prints every tap; `coop_atTimeout <s>` overrides the 240 s station timeout.
- Harness: `docs/proposals/advanced_training_2026-11-09/tools/at_test.py` (cases `pak boot_at boot_raid maptest_raid solo
  coop2 tilesrc`). Private installs `G:\mohaa-advtrain`, `G:\mohaa-advtrainb` (registered in `harness_guard.py`).

## Where the build departs from PLAN.md (the code won)

| Plan | Built | Why |
|---|---|---|
| Station objectives via `objectives.scr::coop_obj_push` | `global/objectives.scr::add_objectives` | `coop_obj_push` drives only the two side-objective lines (coop_so1/so2). `add_objectives` is the channel that drives the menu AND the New Objective card. 8 native slots: stations 0-8 use 1-8, at the ninth they are hidden and 1-4 reused. |
| `officer_positions.scr` m4l0 block reads `level.coop_trainingMap` | not touched | `level.coop_noOfficerWaves = 1` is set before `main.scr::main`; `coop_officer_init` exits before it reads the positions. |
| Final: spawn a coop officer late | the farmhouse's own retail officer + `coop_officer_death_drops` | `coop_officer_init` bails when an officer exists and re-runs 25 s policy waits; PLAN 2.3's own fallback. |
| St 8 "resupply from the paratroopers' ammo can" | row 2 = link up with the landed stick | The stick's ammo can is set dressing (`parasquad.scr:1285`, never an ammo box). |
| St 7 resupply check `chal_bump "ammoboxuse"` | the box's own ledger `level.coop_ammobox_uses[slot][entnum]` | `ammoboxuse` pays the box OWNER for a teammate's refill; a solo trainee using his own box never bumps it. |
| `lmsCheckLives` gate in `main.scr` | `player.scr::manage` | `main.scr:1888-1925` is a dead `/* */` block; the live copy is inlined in `player.scr`. |
| `level.coop_disableSpawnWarper = game.true` "as training.scr does" | left `game.false` | `training.scr` sets `game.false`; the raid's spawn-warper threads (`m4l0_update1-3`) are simply never started. |
| St 2 cover drill at the Zone B farm walls | on the range, two low bag walls (the `cover.scr` collider recipe) | No traced wall geometry; low cover is engine-recognised anywhere. Wall cover is taught by text. |
| St 3 range at (-5408,-4328), St 9 ridge at (-776,-2448) | range up the start lane, vantage (2648,-8,184) | Both sketch spots face buildings (harness stills; bsptrace + pathnode sightline search). bug-10821. The vantage sees the red smoke down a track, small at 2,680u - playtest call |
| St 5/6 at the Ranger rally (-5420,-2336) | the yard east of the barn (-4944,-2544); the Rangers are moved there in the fade | The rally is under the barn roof - dark (BSP roof trace, stills) |
| Hurt trainees with `health` | `at_course.scr::wound`, 180 hp steps 2.3 s apart | Under DBNO a 250 drop inside 2 s downs the player (bug-10822) |
| Props dropped with `droptofloor` / plain `traced` | `traced` with SOLID+FENCE+PLAYERCLIP | m4l0's ground is PLAYERCLIP (bug-10823) |
| Graduation `chal_grant` | `chal_bump "atgrad"` after the till opens | `check_challenges.py` fails a challenge with no stat writer. |
| Medal derived from the challenge | `level.coop_chal_noMedal["atgrad"] = 1` | A new row must not move anyone's capstone (the Castro precedent). |
| Attic prop + two-card screen | built: practice target on an easel, hotspot 20, opens `ui/coop_training.urc` (Basic / Advanced) | User choice 2026-11-10. Menus pak = ship71 (b3c953cd) + 14 entries, `H:\hzm_workdvtrain-ship\ship_at\` (sha 89deb29f), tools in `attic/tools/` |
| Cards launch via `start_server.cfg` | via `coop_mod/cfg/mission_start.cfg` | That is what the coop start Apply runs (pre-mission lobby first) |
| Tile art | `m4l0at_{c,s}` + prints from a clean Dig-in frame, in `docs/tools/assets/tileart`; tile-art pak rebuilt (sha 1d56a290, 272 members, `check` byte-identical) | |

User decisions (2026-11-10, all seven recommended options): practice-target attic prop for both courses; XP 100 + the Graduate row, no medal; late joiners graduate if present at the end; ready-gate restart, otherwise stay; unbound binds pointed at Controls; mentioned-only systems on the end card; basic training side fixes (`level.gametpye` typo; training_46 not played - lines 37/50/51 are correct here: the SECONDARY key IS the bash / short toss).

## Shared-file edits (all additive, all gated on `level.coop_trainingMap == 1` or a new level flag)

`challenges.scr` (tap in `chal_bump` + `atgrad` row), `xp.scr` (tap in `xp_award`), `daily.scr` (`daily_onEmote` tap,
`daily_add` off), `loot.scr` (`searched` tap, loot still given), `officer.scr` (strike veto in `binoculars_fired`),
`aircraft.scr` + `paradrop.scr` (`level.coop_noFlak`), `alarm.scr` (`alm_blocked` "training"), `dbno.scr` (600 s bleed),
`allysquad.scr` (600 s ally bleed), `player.scr` (LMS lives 0), `carry.scr` (`level.coop_noCarry`), `variables.scr`
(m4l0 description), `m0.cfg` (tiles), `m4l0_precache.scr`. Nothing touches the war map, MP contracts or any `mp_*.scr`.

## Merge

1. Mod: merge `advtrain` into the release branch. **Then re-run `HZM_MOD=<tree> python docs/tools/gen_service_record.py`**
   if Live Operations (or anyone) also added a `chal_def` - the Service Record bakes rows per index, so both additions
   must be regenerated together; `check_challenges.py` and the deploy stamp self-test catch a mismatch.
2. Root: merge `advtrain` (harness_guard registration, this folder).
3. Tile art: run `at_test.py tilesrc`, build `m4l0at` through the tile pipeline, add to the tileart pak.
4. `build.ps1` as usual (no engine change).

## Gates

See the report in the session; re-run with: scrlint, depthscan2/linecheck/quotecheck/prosecheck, check_empty_rhs,
check_challenges, gen_service_record (452 rows), unlock_audit (unchanged vs base), check_mp_isolation (22/22).

## Test matrix (2026-11-10, private clients on the 1080p screen, self-test)

| Run | Result |
|---|---|
| boot_at / boot_raid (dedicated) | clean, branch on / off |
| solo (listen, 273 s) | 11/11 stations done, course complete, real medkit heal, real search, real DBNO + ally revive, real sandbag/ammo box/paradrop/strike, props grounded (PLAYERCLIP trace) |
| coop2 (dedicated + 2) | course complete 2/2 on every station except Field medicine (the self-test's team heal never completed: needs a human two-player check of hold-USE patching) |
| maptest_raid | MAPTEST_LOADED m4l0, advanced to the next map, 0 ATRAIN lines in the raid, 0 compile errors |
| tilesrc | clean Dig-in frame -> tile |
| attic (at_attic_run.py) | hotspot 20 lit on hover, close-up, sheet; Basic card -> training (branch off), Advanced card -> m4l0 (ATRAIN branch on) |

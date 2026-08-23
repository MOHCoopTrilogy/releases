# M-series / E-series Non-Fatal Script-Error Fixes

Source tree edited: `C:\mohaa-coop-dev\hzm-mohaa-coop-mod` (the build source per `build.ps1`).
No pk3 rebuild, no game launch, no GOG files touched. All edits ASCII, no BOM, no em-dash,
compound conditions on one line, no bare-negative inside `if(...)` parens.

## Important note on the log
The live rotation log `C:\Users\curry\AppData\Roaming\openmohaa\maintt\qconsole.log`
had **rotated** by the time of this work: it now only covers maps 36/43 onward
(e1l3 at 23:36, e1l4 at 23:40+). The earlier m-series portion that produced the
task's findings list (the exact strings "Cannot cast 'none' to listener",
"command 'exec' applied to NIL", "physics_off applied to NIL", "Cannot cast 'none'
to entity", "explicit classname for misc object tik models") is **no longer present**
in the log and no backup/rotated copy exists anywhere on disk. Those specific strings
return 0 matches in the current log.

Fixes below are therefore driven by: (a) the two label errors that ARE confirmed live
and in scope, and (b) the live `applied to NULL listener` errors with exact file:line
attribution from the current log for the in-scope map e1l3, plus (c) the one findings
class ("rendereffects applied to NIL" x2) that maps cleanly and uniquely to in-scope
e1l1 spawn-local code.

---

## Fixed

### 1. Could not find label 'stop_at_end' in 'maps/m1l3b.scr'
- **Error:** `Game (Event:'setthread', Object:'Trigger') : Could not find label 'stop_at_end' in 'maps/m1l3b.scr'`
- **Map:line:** `maps/m1l3b.scr` (new label appended after `coop_giveAmmo`, ~line 1342)
- **Root cause:** A BSP trigger entity on m1l3b carries an editor-set `thread` key =
  `stop_at_end`. The engine resolves that key against the level script `maps/m1l3b.scr`.
  No version of the SP script (vanilla, HZM, extracted) ever defined that label, so the
  trigger spawn logs the error. Confirmed the canonical shipping mod UBER-MODS implements
  it as a no-op stub (`UBER-MODS-v8.00-MOHAA/maps/m1l3b.scr:1162` -> `stop_at_end:` / `end`).
- **Fix:** Added a no-op stub label `stop_at_end:` (matches UBER-MODS handling).

### 2. Could not find label 'ShadowThread' in 'maps/e1l3.scr'
- **Error:** `Game (Event:'setthread', Object:'Trigger') : Could not find label 'ShadowThread' in 'maps/e1l3.scr'` (x2, line 424-425)
- **Map:line:** `maps/e1l3.scr` (new forwarding label added before `coop_playerJustSpawned`)
- **Root cause:** The `$ShadowTrigger` BSP entity has its `thread` key = `ShadowThread`.
  The real handler lives in `maps/e1l3/Sneakers.scr:291` (`ShadowThread:`), but the engine
  resolves entity thread keys against the **level script** `maps/e1l3.scr`, where the label
  did not exist.
- **Fix:** Added a forwarding label `ShadowThread:` in `e1l3.scr` that calls
  `thread maps/e1l3/Sneakers.scr::ShadowThread`, preserving the original "Klaus died /
  mission failed" behavior.

### 3-10. e1l3 "command applied to NULL listener" (guards-missing)
All in `maps/e1l3/` subdir scripts. Each references an SP entity that is NULL in coop
(removed/never-spawned by the coop butler/replacement layer). Added HZM-style `if($x)` guards.

| # | Error (live log file:line) | Entity | Fix |
|---|---|---|---|
| 3 | `briefing.scr,98 : 'thread' applied to NULL` | `$boat_guy` | `if ($boat_guy)` guard; also guarded adjacent `$wall_mg42 thread InitMG42` |
| 4 | `briefing.scr,268 : Field 'enableEnemy' applied to NULL` | `$buddy1` | `if ($buddy1)` guard |
| 5 | `briefing.scr,269 : Field 'enableEnemy' applied to NULL` | `$buddy2` | `if ($buddy2)` guard |
| 6 | `briefing.scr,281 : 'thread' applied to NULL` | `$buddy1` | `if ($buddy1)` guard |
| 7 | `briefing.scr,282 : 'thread' applied to NULL` | `$buddy2` (orig duplicated `$buddy1` - vanilla typo, corrected to `$buddy2`) | `if ($buddy2)` guard |
| 8 | `briefing.scr,615 : 'thread' applied to NULL` | `$boat_guy_2` | `if ($boat_guy_2)` guard; also guarded `$boat_guy_1` |
| 9 | `jailbreak.scr,81 : 'lock' applied to NULL` | `$PrisonDoorOther` | `if ($PrisonDoorOther)` guard; also guarded `$WeaponRoomDoor` |
| 10 | `tankride.scr,438 & 441 : 'notsolid'/'solid' applied to NULL` | `$buddy2` | `if ($buddy2)` guards on both |

### 11. rendereffects applied to NIL (x2) - e1l1
- **Map:line:** `maps/e1l1/introSpawnGuys.scr:248` and `:258` (label `loadedTruck`)
- **Root cause:** `local.guy0 = spawn local.model` / `local.guy = spawn local.model` then
  immediately `... rendereffects "-shadow"`. If the spawn returns NIL the command hits NIL.
  These are the only two non-self, non-commented `rendereffects` calls on a spawned local in
  the in-scope maps, matching the findings count of x2.
- **Fix:** Wrapped each spawned-guy usage block in `if (local.guyX != NULL) { ... }`, and
  guarded the `local.guy0 remove` cleanup. No early `end` (would have leaked the truck cleanup).

---

## NOT fixed / could not attribute

These findings-list errors had **no matching line in the surviving log** and could not be
safely attributed to a specific m-series map:line without guessing (the m-series portion of
the log was rotated away, and the m-series maps load clean statically):

- "Cannot cast 'none' to listener" (x8)
- "command 'exec' applied to NIL" (x4)
- "command 'physics_off' applied to NIL" (x2)
- "command 'anim' applied to NIL" (x2)  [note: live log shows an `anim` NULL only in
  e1l4/preship.scr, which is OUT of the clean-tested scope]
- "Cannot cast 'none' to entity" (x2)
- "You must specify an explicit classname for misc object tik models" (x2)

Recommendation: re-run the m-series maptest rotation to regenerate the log with these errors
(they print the offending file:line), then the same guard pattern applies.

## Observed but OUT of scope (not fixed)
e1l4 is not in the clean-tested set (it has a known respawn-loop issue, see
`e1l4_respawn_loop_rootcause.md`). The live log shows the same bug classes there:
- `Could not find label 'GiveExplosives' in 'maps/e1l4/Ship.scr'` (x10) - same setthread/label pattern
- `e1l4/preship.scr` lines 9/35/44/45/46: `$drunkguy`/`$deleteGuy2` gun/anim/waittill/thread on NULL
- `global/autotruck.scr:362`: `self.collisionent connect_paths` on NULL (framework file - left for framework owner)

Ignored per instructions (asset-fallback warnings, duplicate aliases, missing sounds/textures,
`invalid waittill prespawn/spawn for 'Level'` sequencing notices, `No active weapon in slot`).

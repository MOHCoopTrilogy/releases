# Coop Objectives: Fix + Side Objectives Implementation

Date: 2026-06-22
Scope: HZM coop mod (`C:\mohaa-coop-dev\hzm-mohaa-coop-mod`). Script/UI/config only.
No cgame/engine changes. No build/deploy performed.

---

## PART 1 - Why the Objectives view did not show, and the fix

### How MOHAA / HZM coop objectives work end to end

1. Engine script API (`code/fgame/scriptthread.cpp`):
   - `addobjective <index> <status> <text> <location>` writes configstring
     `CS_OBJECTIVES + index` (status 1=hidden, 2=current/active, 3=completed).
     `MAX_OBJECTIVES = 20` (`code/qcommon/q_shared.h:1676`), so indices 1..20 are valid.
   - `setcurrentobjective <index>` writes `CS_CURRENT_OBJECTIVE`.

2. HZM coop display layer (`global/objectives.scr`):
   - `add_objectives <index> <status> <text> [location]` is the coop wrapper. It calls
     the engine `addobjective` AND drives a custom, per-player HUD built from cvars
     `coop_o1..coop_o8` (+ `...d/s/a/c` variants) and the menu `ui/coop_objectives.urc`.
   - First call lazily starts `coop_objectivesManage` and, per player, runs
     `coop_objectivesResetForPlayer`, which `stufftext`s `exec ui/coop_objectives/obj_reset.cfg`
     to the client. `obj_reset.cfg` is what sets `seta coop_obj "exec ui/coop_objectives/obj_add.cfg"`.
   - `current_objectives <index>` highlights the current objective (yellow).

3. The display menu + toggle:
   - `ui/coop_objectives.urc` defines a HUD menu named `coop_objectives` (8 objective rows,
     linked to cvars `coop_o1..coop_o8`).
   - `ui/coop_objectives/obj_add.cfg` does `ui_addhud "coop_objectives"` (show) and flips
     `coop_obj` to point at `obj_rem.cfg`.
   - `ui/coop_objectives/obj_rem.cfg` does `ui_removehud "coop_objectives"` (hide) and flips
     `coop_obj` back to `obj_add.cfg`.
   - So `coop_obj` is a toggle cvar; the player runs it with `vstr coop_obj`.

4. The key/command:
   - `ui/BIND.SCR` (the Controls menu) registers `binditem "Coop Objectives" "vstr coop_obj"`,
     so a key CAN be bound from Options > Controls. (The legacy `ui/coop_objectives/obj_bindkey.cfg`
     hard `bind m` line is intentionally commented out.)

### Verified non-causes
- The `coop_objectives` menu IS registered: the engine auto-loads every `ui/*.urc`
  (`code/client/cl_ui.cpp:5439` `FS_ListFiles("ui/","urc",...)` -> `new UILayout(...)`),
  and `ui_addhud` resolves by `menuManager.FindMenu("coop_objectives")`
  (`UI_AddHud_f`, `cl_ui.cpp:4991`). So the HUD exists and `ui_addhud` works.
- The bind entry exists in `BIND.SCR`. So the key can be bound.
- There is no multiplayer/gametype gate disabling this HUD - it is a custom coop HUD,
  not the stock `StatsScreen`/missionlog.

### ROOT CAUSE
The toggle cvar `coop_obj` is only ever defined on the client by
`ui/coop_objectives/obj_reset.cfg` (and `obj_setup.cfg`), which are only `stufftext`'d
to a player from inside `coop_objectivesResetForPlayer` (`global/objectives.scr`). That
function only runs after the first `add_objectives` / `current_objectives` call.

In coop, the vanilla per-map objective scripting is almost entirely stripped/disabled,
so on the great majority of coop maps `add_objectives` is NEVER called. Result:
- `coop_obj` is never `set` on the client -> pressing the bound Objectives key runs
  `vstr coop_obj` against an empty/undefined cvar -> nothing happens (HUD never toggles).
- Even where it would toggle, the list is empty because nothing was registered.

In short: the menu, the bind, and the engine API are all fine; the per-player
objectives **initialization is never triggered** on objective-less coop maps.

### FIX (Part 1)
Initialize the coop objectives client state for every player at coop player setup,
so the bound key always toggles the HUD regardless of whether a map registers an
objective.

- File: `coop_mod/player.scr`, function `manageSetup` (per-player, one-time).
- Added a single additive line right after `thread detectCoop local.player`:

  ```
  local.player stufftext ( "exec ui/coop_objectives/obj_setup.cfg" )
  ```

  `obj_setup.cfg` defines all `coop_o*` cvars, then execs `obj_reset.cfg`, which sets
  `seta coop_obj "exec ui/coop_objectives/obj_add.cfg"`. After this, `vstr coop_obj`
  always toggles the `coop_objectives` HUD for that client.

Part 2 (below) additionally registers two real objectives on every officer-system map,
so the list is non-empty there.

---

## PART 2 - Two optional SIDE objectives (officer / radio), all officer maps

### Requirements met
- "Eliminate the High-Ranking Officer" -> completes on officer death.
- "Destroy the Radio to Stop Reinforcements" -> completes on radio destruction.
- Both are OPTIONAL / secondary: they are registered as active and marked completed,
  but mission completion is NEVER gated on them. We never call `current_objectives`
  for them, so they do not even steal the map's "current objective" highlight, and
  no level-completion logic references them. Text is prefixed "(SECONDARY)".
- Added to ALL maps that run the coop officer system (i.e. wherever
  `coop_mod/officer.scr` spawns the officer/radio), via hooks in officer.scr.

### New file (all new logic lives here)
`coop_mod/objectives.scr` (created):
- `coop_obj_register` - registers slot 7 (officer) and slot 8 (radio) as status 2 (active),
  with no compass location (NIL) so the map's primary compass target is untouched.
  Guarded by `level.coop_sideObjReg` so it runs once.
- `coop_obj_officer_done` - sets slot 7 to status 3 (completed). Guarded by
  `level.coop_sideObjOfficerDone`. Self-heals (registers first) if needed.
- `coop_obj_radio_done` - sets slot 8 to status 3 (completed). Guarded by
  `level.coop_sideObjRadioDone`. Self-heals if needed.

Slots 7 and 8 were chosen to avoid collision with vanilla per-map primary objectives
(which use slots 1..5). All registration/update goes through the existing
`global/objectives.scr::add_objectives` wrapper - no new engine commands.

### Hooks (minimal, additive single lines in the shared file)
`coop_mod/officer.scr` - three one-line `thread` calls only; no combat logic touched:
- End of `coop_officer_spawn` (after `thread coop_officer_marker`, ~line 301):
  `thread coop_mod/objectives.scr::coop_obj_register`
  (placed after officer + radio exist and after the `coop_feature_boss == 0` early-out,
  so it only fires on maps that actually run the boss/radio encounter.)
- In `coop_officer_death_monitor`, at the existing "The officer has been eliminated!"
  point (~line 1857): `thread coop_mod/objectives.scr::coop_obj_officer_done`
- In `coop_radio_bomb_explode` (radio destroy), at the existing "Radio destroyed!"
  point (~line 2403): `thread coop_mod/objectives.scr::coop_obj_radio_done`

### Objective API used (summary)
- Register/active: `waitthread global/objectives.scr::add_objectives 7 2 "<text>"`
- Register/active: `waitthread global/objectives.scr::add_objectives 8 2 "<text>"`
- Complete:        `waitthread global/objectives.scr::add_objectives 7 3 "<text>"`
- Complete:        `waitthread global/objectives.scr::add_objectives 8 3 "<text>"`
- (status: 2 = active/in-progress, 3 = completed; underlying engine cmd = `addobjective`)

### Why these are guaranteed non-required
- Nothing in the mission-complete path (`coop_mod/missioncomplete.scr`) or map end logic
  references `coop_sideObj*` / slots 7-8. They are write-only HUD state.
- We never call `current_objectives` for them, so the map's own objective flow is intact.
- Completion hooks are downstream of events that already happen for gameplay reasons
  (officer death, radio demolition); they add HUD updates and nothing else.

---

## Files created / modified
- CREATED: `coop_mod/objectives.scr`
- MODIFIED: `coop_mod/officer.scr` (3 additive single-line `thread` hooks)
- MODIFIED: `coop_mod/player.scr` (1 additive line in `manageSetup`)

## Byte-verify results (parse-killer scan)
- `coop_mod/objectives.scr`: no BOM (`2f 2f 20`), 0 non-ASCII bytes, braces balanced 8/8,
  no bare negatives in parens, no smart quotes/em-dashes.
- `coop_mod/officer.scr`: no BOM, 0 non-ASCII bytes after edits.
- `coop_mod/player.scr`: no BOM; only 2 pre-existing non-ASCII bytes (lines 434/443,
  degree/section symbols in unrelated code) - not introduced by this change.

## cgame / engine changes needed
- NONE. All fixes are script + reuse of existing UI/config. No cgame.dll rebuild required.

## Concurrency safety
- All edits to shared files (`officer.scr`, `player.scr`) are additive single lines at
  existing landmark strings; no combat functions, `officer_positions.scr`, or `main.scr`
  were modified. New logic is isolated in `coop_mod/objectives.scr`.

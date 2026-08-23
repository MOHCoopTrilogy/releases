# HZM Coop Mod - UI-Layer Bug Fixes

Engine source referenced (read-only): `C:\mohaa-coop-dev\openmohaa-hzm`
Mod tree: `C:\mohaa-coop-dev\hzm-mohaa-coop-mod`

---

## BUG 1 - Weapon-select leaves a stuck cursor

### Root cause
`ui/coop_weaponselect_suppress.urc` tried to self-dismiss the engine-pushed
`SelectPrimaryWeapon` menu with `showcommand "popmenu 0"`. That can never work:
a `showcommand` value is NOT run as a console command. The engine builds
`Event(<value>)` and `ProcessEvent()`s it against the widget container, so it
only resolves registered **widget/Listener events**.

- `popmenu`, `hidemenu`, `globalwidgetcommand` are **console commands**
  (`client/cl_ui.cpp` ~5325-5333, registered via `Cmd_AddCommand`), NOT Listener
  events.
- `qcommon/listener.cpp` `Event::FindEventNum` matches the **entire** string
  (`"popmenu 0"`) against the event table; `command_t` does no tokenization.
  `Listener::PostEventInternal` deletes an unknown event with **no console-stuff
  fallback** (the old `uii.Cmd_Stuff` path is commented out in
  `uilib/uiwidget.cpp::ExecuteShowCommands`, replaced by `Event+ProcessEvent`
  "Fixed in 2.0").
- Result: every push logs `Event 'popmenu 0' does not exist.` +
  `Failed execution of event for class 'UIWidgetContainer'.`

There is **no widget or menu Listener event that pops the menu stack** (checked
`uilib/uiwidget.cpp` and `uilib/uimenu.cpp` class declarations; `MenuManager`
only exposes `pushmenu/lock/unlock`, the `Menu` class only `showmenu/hidemenu`,
and `showcommand` dispatches to the widget container, not to either of those).

The empty override correctly hides the picker's *contents*, but
`CG_PushMenuWeaponSelect_f` -> `pushmenu SelectPrimaryWeapon`
(`cgame/cg_consolecmds.c`) still puts the menu on the stack, and the menu stack
turns the cursor on (`uilib/uiwinman.cpp`: cursor draws while a menu is current;
`pushmenu` calls `showCursor(true)`). So the cursor remained until ESC.

Why coop hits this at all: coop runs `g_gametype 2` (GT_TEAM, see
`coop_mod/start_server.cfg`), so `CG_PushMenuWeaponSelect_f`'s `GT_SINGLE_PLAYER`
early-return does NOT fire, and `Player::UserSelectWeapon` re-pushes the picker
on (re)spawn.

### Fix applied (UI layer)
`ui/coop_weaponselect_suppress.urc` - removed the broken
`showcommand "popmenu 0"` from all five menu overrides (`SelectPrimaryWeapon`
and `_british/_russian/_german/_italian`). The empty, transparent,
non-fullscreen overrides remain (they suppress the visible picker), and an
explanatory comment documents why no showcommand can pop the menu. This stops
the per-push error spam.

### Verified engine command
The reliable dismissal is the **console** command `popmenu 0` (valid:
`UI_PopMenu_f` accepts arg "0" -> `UI_PopMenu(0)` -> `menuManager.PopMenu`),
issued via server-side `stufftext`. `main.scr` already does exactly this at a
few moments (`coop_mod/main.scr` lines 164, 199, 306, 309) and those calls are
correct - the bug was only the `.urc` showcommand.

### Script hook requested (main session to add - NOT done here)
The existing `stufftext "popmenu 0"` calls only fire at autospawn / forceTeam,
not on every respawn, so the picker can re-appear. Add one line in the
per-(re)spawn path so the picker is always popped:

- File: `coop_mod/player.scr`, thread `manageAliveSpawning` (around line 798,
  just after the spawn/respawn `if/else` block, before `//INVENTORY`):

  ```
  local.player stufftext "popmenu 0"
  ```

This covers both spawn and respawn for every player. (player.scr is not a
protected file, but per the task constraints I did not edit any `.scr`; this is
the single hook to add. If you prefer, the same line also works inside both the
`if`/`else` branches at lines 793/796.)

---

## BUG 2 - Objectives don't display on the bound key

### Root cause
This is NOT a data/two-system-mismatch problem. The native `addobjective`
registration and the custom `coop_objectives` HUD are the **same** path:
`global/objectives.scr::add_objectives` calls `addobjective` AND then drives the
custom-HUD cvars for every player via
`coop_objectivesSendPlayer` ->
`stufftext "exec ui/coop_objectives/obj_<index><status>"` (sets
`coop_o<n>d/a/c`) + `stufftext "set coop_o<n> <text>"`. The maps register through
this wrapper (e.g. `maps/m1l1.scr` "Infiltrate the German occupied village.",
`maps/e1l1/objectives.scr`), and the side objectives in
`coop_mod/objectives.scr` (slots 7/8) also go through it. So the HUD cvars DO get
the current objectives.

`ui_addhud "coop_objectives"` is also fine: `UI_AddHud_f`
(`client/cl_ui.cpp` ~4991) does `menuManager.FindMenu("coop_objectives")`
(case-insensitive) and shows it as a HUD overlay (no cursor). All `ui/*.urc` are
auto-loaded at UI init (`cl_ui.cpp` ~5439 `FS_ListFiles("ui/","urc")`), so the
`coop_objectives` menu defined in `ui/coop_objectives.urc` exists.

The actual breakage is in the **bind layer**:
1. **No default key is bound.** `ui/BIND.SCR` registers the action
   `"Coop Objectives" -> "vstr coop_obj"` in Options > Controls, but the only
   place that binds a key (`ui/coop_objectives/obj_bindkey.cfg`) has its
   `bind ... "vstr coop_obj"` line **commented out**. Out of the box, pressing
   "the bound key" does nothing because nothing is bound.
2. **The controls-menu row is unusable / errors.** The label `"Coop Objectives"`
   (and the other coop labels) has no localization entry, producing
   `LOCALIZATION ERROR: 'Coop Objectives'`; the row shows the raw reference
   string, making it awkward to find and bind.
3. **Toggle desync (latent).** `coop_obj` flip-flops add<->rem. `obj_reset.cfg`
   (run every (re)spawn via `obj_setup.cfg` and `global/objectives.scr`) forced
   `coop_obj` back to the "add" branch but did NOT hide the HUD - so if the HUD
   was open at respawn, the cvar said "add" while the HUD stayed visible, and the
   next press re-added (no-op) instead of removing.

### Fix applied (UI layer) - approach (b), make the existing custom HUD reliable
Approach (b) was chosen over (a): there is no native, non-gametype-gated
"objectives" menu/command to bind to in this build, and the custom HUD is
already fully wired and populated by the native registration path - it just was
never reachable. Fixes are low-fragility and do not require touching protected
scripts.

1. `global/localization_coop.txt` (NEW) - additive localization for all coop
   binditem labels (`Coop Objectives`, `Coop Suicide`, `Coop Admin Menu`, ...).
   The engine loads every `global/localization*.txt`
   (`sys/win_localization.cpp` ~82 `FS_ListFilteredFiles "localization*.txt"`,
   sorted, entries appended), so this does NOT override the base
   `global/localization.txt`. Silences the `LOCALIZATION ERROR` and makes the
   Options > Controls rows display cleanly and bindable.

2. `autoexec.cfg` - added `bind o "vstr coop_obj"` (with explanatory comment)
   so the objectives HUD has a working default key immediately. `o` is unbound in
   stock MOHAA, so this clobbers no default action. (Note documented in the file:
   autoexec runs AFTER the player config and `seta` always overwrites
   (`qcommon/cvar.c` `Cvar_Set2`), so a pure-cfg one-time guard isn't possible;
   to use a different key, rebind via Options > Controls - now usable - and
   edit/remove this line.)

3. `ui/coop_objectives/obj_reset.cfg` - added `ui_removehud "coop_objectives";`
   at the top of the reset so the toggle can never desync after a respawn-driven
   reset (harmless when the HUD isn't currently shown - `UI_RemoveHud_f` checks
   `hudList.ObjectInList`).

### Verified engine commands/menu
- `ui_addhud`/`ui_removehud` (`client/cl_ui.cpp` `UI_AddHud_f` / `UI_RemoveHud_f`)
  - real commands; resolve the HUD by `menuManager.FindMenu(<name>)`.
- `coop_objectives` menu exists (`ui/coop_objectives.urc`, auto-loaded).
- Localization loading: `sys/win_localization.cpp` (`localization*.txt` glob,
  additive).

### Script hook requested
None. The custom HUD is already driven by `global/objectives.scr` (read-only;
not edited). No `.scr` change is needed for objectives to display.

---

## Files changed
- `hzm-mohaa-coop-mod/ui/coop_weaponselect_suppress.urc` - removed 5x broken
  `showcommand "popmenu 0"`, added explanatory comments.
- `hzm-mohaa-coop-mod/ui/coop_objectives/obj_reset.cfg` - added
  `ui_removehud "coop_objectives";` to keep the toggle in sync.
- `hzm-mohaa-coop-mod/autoexec.cfg` - added default `bind o "vstr coop_obj"`.
- `hzm-mohaa-coop-mod/global/localization_coop.txt` - NEW, additive coop label
  localization.

## Byte-verify (ASCII, no BOM / smart quotes / em-dashes)
All four files verified ASCII-clean with no UTF-8 BOM:
- `ui/coop_weaponselect_suppress.urc` - ASCII-clean
- `ui/coop_objectives/obj_reset.cfg` - ASCII-clean
- `autoexec.cfg` - ASCII-clean
- `global/localization_coop.txt` - ASCII-clean

## Hook requests for the main session (script files - not edited here)
- BUG 1: add `local.player stufftext "popmenu 0"` in
  `coop_mod/player.scr::manageAliveSpawning` (~line 798) so the force-pushed
  weapon picker is popped on every (re)spawn, clearing the cursor.
- BUG 2: none.

# Coop Weapon-Select Menu Suppression - Findings & Fix

Date: 2026-06-22

## Symptom
Every time a player connects/spawns on the coop server, the multiplayer
**weapon-selection** screen pops up. In coop the loadout is fixed (script-given),
so the picker is useless and annoying.

## Root cause (the trigger)
The weapon picker is pushed **server-side by the engine**, not by any mod UI.

In `openmohaa-hzm/code/fgame/player.cpp`:
- During the player think/spawn flow, when the player is on a team but
  `client->pers.dm_primary[0]` is empty (no primary chosen yet), the engine calls
  `Player::UserSelectWeapon()` (called at lines 4726, 4742, 9514, 9520, 12083).
- `UserSelectWeapon()` (line 12018) sends to the client:
  `gi.SendServerCommand(... "stufftext \"pushmenu_weaponselect\"")` (line 12030),
  or for 2.0+/SH/BT protocols a per-nationality push
  `pushmenu SelectPrimaryWeapon_<british|russian|german|italian>` (lines 12056-12074).
- Client side, `cgame/cg_consolecmds.c` `CG_PushMenuWeaponSelect_f()` (line 617)
  runs `pushmenu SelectPrimaryWeapon`.
- `pushmenu_weaponselect` is whitelisted as a server->client command
  (`cgame/cg_servercmds_filter.cpp` line 62), so it always gets through.

So the menu name opened is **`SelectPrimaryWeapon`** (base MOHAA protocol) or
`SelectPrimaryWeapon_<nationality>` (2.0+/SH/BT). This menu is defined in a
base-game `.urc`.

## Loadout is script-controlled (menu is vestigial) - confirmed
`coop_mod/main.scr` sets the weapon server-side on join/spawn:
- `skipTeamAndWeaponSelect` (line 285): `join_team "allies"`,
  `primarydmweapon "rifle"`, `pickweapon`, `stufftext "popmenu 0"`.
- `forceTeam` (line 174) and `autoSpawnHost` (line 147) do the same
  (`primarydmweapon "rifle"; pickweapon; popmenu 0`).
Once script sets `dm_primary`, the engine's re-push condition
(`!client->pers.dm_primary[0]`) is false and it stops pushing. The picker only
flashes in the brief window before/while the script runs - purely vestigial.

## Fix applied (UI override, no engine change)
All `ui/*.urc` files are loaded at UI init (`client/cl_ui.cpp` ~line 5439:
`FS_ListFiles("ui/", "urc", ...)` -> `new UILayout(...)`). The coop pak
(`zzzzzz_co-op_hzm_mod_mohaa.pk3`) loads last, so a mod `.urc` that redefines a
menu by name **overrides** the base-game definition.

New file shipped: **`ui/coop_weaponselect_suppress.urc`**

It redefines `SelectPrimaryWeapon` (and the four 2.0+ per-nationality variants
`_british`, `_russian`, `_german`, `_italian`) as an **empty, transparent,
non-fullscreen menu** with a menu-level `showcommand "popmenu 0"`. When the
engine pushes the menu, it shows nothing and immediately closes itself.

Why this is safe:
- `showcommand` is a real menu/widget directive
  (`uilib/uiwidget.cpp` EV_Widget_ShowCommand; executed by
  `uimenu.cpp:136 ExecuteShowCommands()` when the menu is shown).
- The override only affects the **client UI**. The weapon is assigned
  server-side via script (`primarydmweapon`/`pickweapon`), so the scripted
  loadout is unaffected - players still get their guns.
- Even if the self-`popmenu` races the push, the menu is empty + transparent +
  non-fullscreen, so nothing visible appears either way.

### One-line summary of the mechanism
Engine pushes `SelectPrimaryWeapon`; we override that menu with an empty
self-closing one in the last-loaded pak.

## Scope / non-coop impact
The override lives only in the coop mod pak. It affects any client running with
this pak loaded. For a dedicated coop server this is exactly the target audience.
It does not touch team selection, the scripted loadout, or any engine binary.
(The team-select menu is separately handled by the script forcing allies; out of
scope for this fix.)

## Files changed
- ADDED: `hzm-mohaa-coop-mod/ui/coop_weaponselect_suppress.urc` (ASCII, no BOM)

No `.cfg` changes were needed - there is no engine cvar to disable the auto-push
on the base-MOHAA protocol path, so the UI-override is the cleanest config/UI
fix. No `coop_mod/*.scr` files were touched (other automated work owns those).

## Rebuild needed?
**No engine rebuild.** This is a pure UI data fix shipped in the mod pak.
The main session only needs to repackage the pk3 (build.ps1 / deploy) so the new
`ui/coop_weaponselect_suppress.urc` is included. (Per instructions I did NOT run
build.ps1 or deploy.)

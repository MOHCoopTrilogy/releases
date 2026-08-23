# Objective Bonus Drop - Implementation Report

Date: 2026-06-22

## Feature
On eligible maps, place ONE bonus pickup at a configured objective location per
mission. 50/50 random (`randomint 2`): a pair of Binoculars (bombing-run weapon)
OR a Signal Smoke grenade (Allied paradrop signal). Reuses the existing officer
death-drop mechanics and the existing downstream engines.

## Files created
- `coop_mod/objective_drop.scr` - logic + spawn/pickup callbacks.
- `coop_mod/objective_positions.scr` - per-map data table (officer_positions.scr style).

## Files modified (additive only)
- `coop_mod/main.scr` - one line added after the officer init thread (line 122):
  `thread coop_mod/objective_drop.scr::coop_objective_drop_init`

NO changes to officer.scr, paradrop.scr, or any combat function.

## Reused mechanics (NOT reinvented)
The bonus pickups are byte-for-byte the same spawn pattern as
`coop_officer_death_drops` in officer.scr:
- Smoke: `spawn "models/weapons/coop_smoke_grenade.tik"` + `rendereffects "+fullbright"`
  + `setthread <pickup>` + a `models/fx/dummy.tik` yellow locator glow.
- Binoc: visible `models/items/binoculars.tik` script_model + a `trigger_use`
  (`setsize ( -12 -12 0) (12 12 40)`) that grants `weapons/coop_binoculars.tik`.

The downstream engines are 100% reused, untouched:
- Smoke pickup sets `level.coop_paradrop_armed = 1` / `level.coop_smoke_player`,
  exactly the state `paradrop.scr::smokeDropZone` consumes -> `coop_paradrop_main`.
- Binoc pickup sets `level.coop_binoc_given / coop_binoc_uses / coop_binoc_owner`
  and gives the weapon, exactly the state `officer.scr::binoculars_fired` ->
  `coop_bombing_run_sequence` consumes.
- HUD is reused via cross-file calls to the existing officer helpers
  `coop_mod/officer.scr::coop_smoke_hud_show` and `::coop_binoc_update_hud`.

Because the binoc path shares the same `level.coop_binoc_*` globals as the
officer drop, the two drops can never double-grant (the `coop_binoc_given == 1`
guard short-circuits the second pickup).

All four tiks are already in `coop_mod/precache.scr`
(coop_smoke_grenade.tik, coop_binoculars.tik, binoculars.tik, fx/dummy.tik) and
`coop_radio_standby` is a valid ubersound alias - no precache/sound changes needed.

## New functions (coop_mod/objective_drop.scr)
- `coop_objective_drop_init` - entry point; idempotent + enable-guarded.
- `coop_objdrop_spawn_smoke local.pos` - spawns the smoke pickup.
- `coop_objdrop_spawn_binoc local.pos` - spawns the binoc pickup.
- `coop_objdrop_smoke_pickup` - setthread callback (self=pickup, parm.other=player).
- `coop_objdrop_binoc_wait_pickup local.binoc local.binoc_vis` - trigger_use callback.

## Data-table schema (coop_mod/objective_positions.scr::getObjectiveDrop)
Flat if/else-if chain on `level.coop_mapname`, exec'd in caller context, sets:
- `level.coop_objdrop_enable`  int    1 = place a drop on this map (default 0)
- `level.coop_objdrop_origin`  vector world position; NIL = TODO/disabled

## Hook point
`coop_mod/main.scr::main` threads `coop_objective_drop_init` once per map, right
after `coop_officer_init`. The init pulls config via
`exec coop_mod/objective_positions.scr::getObjectiveDrop`, then:
- ends if `coop_objdrop_enable != 1` (default-OFF for unlisted maps),
- ends if `coop_objdrop_origin == NIL` (TODO map, no coord yet),
- sets `level.coop_objdrop_done = 1` up front (idempotent: no double-spawn),
- waits for a player, then 50/50 spawns one pickup.

## Maps: real coord vs TODO
REAL COORD (ships active):
- m4l3 -> ( -120 -1066 9 )  (derived from verified m4l3 objective area; officer
  anchor is -263 -1066 9, offset clear of the officer's own death drop)

ELIGIBLE, enable=1 + origin=NIL (TODO coord; auto-activates when a coord is pasted):
- m6l2a, m6l3a, m1l2a, m2l1, m5l1a, m5l1b, m4l1, m4l2, e1l1, e1l2

NOT LISTED -> stays disabled by default (vehicle/cinematic/boss-disabled maps such
as m4l0, m5l2b, t2l2, t3l2, t1l1, e3l4, plus everything else).

## Byte-verify results
- objective_drop.scr      : first 3 bytes 2f 2f 20 (`// `), NO BOM, NO non-ASCII.
- objective_positions.scr : first 3 bytes 2f 2f 20 (`// `), NO BOM, NO non-ASCII.
- main.scr                : first 3 bytes 2f 2f 2f (`///`), NO BOM, NO non-ASCII.
- Negative-in-paren scan: only vector literals `( -120 -1066 9 )` (matches the
  proven officer_positions.scr literal form) and `setsize ( -12 -12 0) (12 12 40)`
  (identical to officer.scr line 1963). No bare-negative expression hazards.
- Cross-file labels confirmed present in officer.scr:
  coop_smoke_hud_show (2257), coop_binoc_update_hud (2220).
- coop_radio_standby alias confirmed in ubersound/ubersound.scr.

## NOT done (per instructions)
- Did not run build.ps1, did not deploy. Source edited + byte-verified only.

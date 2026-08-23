# Coop Vehicle / On-Rails Implementation Plan (HZM)
Source: subagent a7a93720ab9904156 (2026-06-23). Plan only; no files modified. All t-series work requires com_target_game=1 (Spearhead) to load/test.

## The 3 reusable coop patterns (how it works on maps that already have it)

### Pattern A - Cinematic passenger ride (per-player Camera + spawn manager)
Used by: m1l1 truck, e1l1 beach jeep (e1l1/scene1.scr), e1l4 truck (e1l4/Intro.scr), e2l1 glider (e2l1/gliderride.scr = BEST reference).
- A spawn-manager thread loops on `level waittill playerspawn` (handles late joiners/respawns).
- Per player: spawn a private `Camera`, attach/bind to a tag on the moving vehicle, set cam.player.
- Activate per-player view with the m1l1 trigger_camerause pattern (NOT global cuecamera):
  give the cam a UNIQUE targetname, `spawn trigger_camerause target <uniqueName>`, `doUse <player>`, delete the trigger, restore the array targetname. (Unique name is essential or everyone watches player 1's cam.)
- Players frozen via coop_mod/replace.scr::physics_off, hidden/notsolid; each frame sync cam angle to that player's viewangles (independent free-look).
- Gate on a level flag (level.flags[ridecomplete] / level.RideOver / level.gliderRideOver). On set: stop manager, delete cameras, GLOBAL `cueplayer` + physics_on.
- e2l1 extras worth copying: per-player death watcher + "hold USE to eject" dismount.

### Pattern B - Playable escort vehicle (driver mans gun, passengers glued)
Used by: m1l3b/m1l3c jeep (m1l3b.scr coop_setupAttach / coop_jeepNotOccupied / coop_playerForceToJeep / coop_playerSpawned).
- Vehicle drives a scripted path. One player on the gun via `attachturretslot 0 <player>` + perferredweapon; level.coop_inJeep tracks occupancy; coop_jeepNotOccupied shows "press USE to enter" and lets any nearby player board; free slot on death/leave.
- Extra players seated: dummy script_models (playerAttach2..8) attached to a passenger tag at offsets, each extra player glued (notsolid, forcelegsstate CROUCH_IDLE).
- PLAYER_JEEP_CONTROLLER (global/vehicles_thinkers.scr:287) already `if(level.gametype==0)` skips attaching $player in coop, deferring to the level coop layer.

### Pattern C - Player-driven tank (board/drive/dismount), optional auto-drive
Used by: e1l1 (e1l1/playerTank.scr), m5l2b King Tiger (m5l2b.scr + global/vehicles_thinkers.scr coop_selectDriverForTank/coop_setDriverForTank).
- global/vehicles_thinkers.scr::players_tank is ALREADY coop-aware (setup runs both modes; SP-only attachdriverslot gated to SP; coop branch threads coop_selectDriverForTank when gametype!=0).
- coop_selectDriverForTank: alive allied active player holding USE within 300u of $coop_tankOffset (a mg42_bipod_nonstatic.tik attached to the cannon `connect` tag). coop_setDriverForTank: attachdriverslot 0, glue to $coop_tankOffset, perferredweapon "88mm Tank Gun", hide/notsolid/nodamage, loop until USE again or death -> detach at $coop_tankExit + coop_reJoinTankDriver. Non-drivers fight on foot.
- m5l2b extra: tank needs NO human - threads coop_autoDriveTank (`drive_path`), sets level.coop_playerTank=$playertank, wraps every BSP trigger with coop_mod/replace.scr::validateTriggerActivator so only the tank fires speedup/scene triggers; geofences stray players back.

### Engine constraints (verified)
- cuecamera/freezeplayer/freezecontrols/cueplayer are GLOBAL (all players). Per-player camera MUST use spawn trigger_camerause target <name> + doUse <player>.
- moveto/move/waitmove no-op silently on script_models -> use attach/glue to a moving vehicle tag, or flypath/SplinePath for the vehicle, or per-frame origin-stepping.
- BSP triggers fire on parm.other; SP `if(parm.other==$player)` checks break in coop -> use validateTriggerActivator or "any active player / the vehicle".

## Maps lacking coop vehicle handling (the gap)
All m- and e-series vehicle/ride sections ALREADY integrated (Patterns A-C). e3l1 jeep integrated but buggy (WaitToGetOutOfJeep deattach - improvement, not new work). Gap = Spearhead t-series (baseline main hook + waitForPlayer present, but NO vehicle layer; all need com_target_game=1):

| Map | Section | Pattern | Priority |
|---|---|---|---|
| t3l2 | player DRIVES T-34 end-to-end; players_tank called; $player activator checks (bridge:976) | C | P0 (highest value, cleanest reuse) |
| t2l2 | rides halftrack on fixed path (PLAYER_JEEP_Drive 800-846) manning a gun; CONTROLLER skips $player in coop -> no seats; $player trigger checks (853) | B | P1 |
| t1l1 | plane/parachute/barn-crash cinematic intro (DoPlaneRide + t1l1_barn_crash.scr; gags in BASE pk3 -> wrap, don't edit) | A | P2 |
| t3l1 | tank is AI prop (objective only); player on foot; global freezeplayer + $player teleport intro (279-288) | none (general-coop hygiene only) | P3 |
| t2l4 | on-foot | none | n/a |

## Per-map plan (essentials)
- **t3l2 (Pattern C):** keep players_tank (returns after setup in coop); replace bare `$player` intro mutations (physics_off/takeall/holster/fullheal lines 37,44,52,53,62) with coop loops over non-spectator players (only the boarded driver gets physics_off via coop_setDriverForTank). Human drives (no auto-drive needed; optional m5l2b coop_autoDriveTank fallback if it stalls with no driver). Fix bridge exploder activator (line 976 `parm.owner==$player`) to accept the tank driver / any active player via the coop pattern. **CRITICAL RISK:** verify $coop_tankOffset attaches to the T-34's actual cannon model - players_tank scans for kingcannon.tik (King Tiger). T-34 likely differs -> add a coop setup block (copy m5l2b.scr 62-81) scanning the T-34 cannon model and attachmodel the offset/exit dummies, else driver-select never lets anyone board (silent). No new shared helper needed.
- **t2l2 (Pattern B):** port m1l3b coop_setupAttach/coop_jeepNotOccupied/coop_playerForceToJeep/coop_playerSpawned/coop_playerJustDied/coop_playerJustLeft (m1l3b.scr 1140-1336) onto $s1_jeep1/level.playerjeep; verify halftrack passenger tag name (m1l3b uses passenger0); set gun via perferredweapon or the mounted MG; fix triggerexplode $player check (853); if all players snap to one cam (camera gag), switch to Pattern A. Confirm passengers unglue at path end.
- **t1l1 (Pattern A):** mirror e2l1 gliderride coop_*; per-player camera attached to the moving plane/harness; add a level flag at cutharness (line 271) e.g. level.coop_planeRideOver and loop the manager on it, then cueplayer+physics_on+delete cams; reuse e2l1 late-join/eject. Gags in base pk3 -> wrap only.
- **t3l1 (general only):** loop the intro freeze/teleport (279-288) over all players (use coop_mod/main.scr::playersWarpto like e1l1) if a coop-correct intro is wanted; objective trigger teardown is standard coop.

## Recommended NEW shared helpers (coop_mod/vehiclehandler.scr is currently a stub)
1. startRideCameras (Pattern A generic): extract the per-player camera spawn-manager + trigger_camerause switch + late-join/eject + cueplayer teardown (5 near-duplicate copies: m1l1, e1l1/scene1, e1l4/Intro, e2l1). Needed-ish for t1l1.
2. setupEscortVehicle (Pattern B generic): extract m1l3b jeep-coop family, parameterized (vehicleEnt, passengerTag, gunName, offsets). Needed for t2l2 (shared with m1l3b/c).
3. Pattern C: no new helper (players_tank + coop_selectDriverForTank + validateTriggerActivator already cover t3l2).

## Key file references
m1l1.scr:1377-1535; e2l1/gliderride.scr:687-919 (best A ref); e1l1/scene1.scr:460-556; e1l4/Intro.scr:422-477; m1l3b.scr:1140-1336 (B); e1l1/playerTank.scr:227-392 (C); m5l2b.scr:53-122,558-576 (C auto-drive). global/vehicles_thinkers.scr:1-49 players_tank, 57-169 coop_selectDriverForTank family, 287-337 PLAYER_JEEP_CONTROLLER. coop_mod/replace.scr:99 waitForPlayer, 2507 validateTriggerActivator. Edit targets later: maps/t3l2.scr, t2l2.scr, t1l1.scr, t3l1.scr.

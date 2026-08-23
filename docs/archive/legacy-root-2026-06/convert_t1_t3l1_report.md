# 16-Player Coop Conversion Report - t1l1, t1l2, t1l3, t3l1 (Spearhead)

Date: 2026-06-24. Scope: staged script edits ONLY under
`C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps\{t1l1,t1l2,t1l3,t3l1}.scr`.
No pk3 rebuild, no game launch, no GOG/owned-file edits. All four maps already had
`waitthread coop_mod/main.scr::main` + `waitForPlayer`; this pass is per-element 16-player scaling.

Primitives used (all pre-existing): `coop_mod/replace.scr::{tmstart,tmstartloop,item,ammo,takeAll,
playsound,loopsound,stoploopsound,fullheal,physics_off,physics_on,viewangles,istouching,runto,
player_closestTo,player_anyValid}` and the engine per-player command `<player> freezecontrols 0/1`.

Parse hygiene VERIFIED on all 4 files after edits: no BOM (first bytes `//`/`$`), zero non-ASCII
lines (`perl -ne '/[^\x00-\x7F]/'` empty), no em-dash / smart quotes, all `&&`/`||` conditions on
one line, no bare negative in parens, `$player` 1-indexed loops.

A NOTE ON `replace.scr::fullheal`: the shim is SP-only (heals `$player` when gametype==0, no-op in
coop). Coop players already spawn at full health via the framework, so intro `fullheal` calls are
routed through the shim purely for SP-compatibility and are cosmetic in coop. Not a bug.

---

## t1l1 - Paratroop Drop / Barn Crash

Mostly on-foot; the plane ride + parachute + barn-crash cinematic lives in BASE-pak `gags/` scripts
(T1L1_PlaneRide.scr, t1l1_barn_crash.scr) which are NOT in the editable tree and were not touched.

Changes (file:line approximate, post-edit):
- `TruckGuyRun` (~249): `self runto $player` -> `self thread coop_mod/replace.scr::runto`
  (enemy runs to CLOSEST active player instead of host). `self waittill movedone` still works.
- `barn_hole` (~267): `$player loopsound t1_barninside` -> `exec ...::loopsound t1_barninside`
  (ambient on all players).
- `TurnOffAAGuns` (~394): `$player stoploopsound` -> `exec ...::stoploopsound`.
- `sound_barn_outside` (~413): `$player loopsound t1_barnoutside` -> `exec ...::loopsound`.

Objective semantics: 3 objectives (rendezvous / destroy tank with AA / regroup) via
`global/objectives.scr::add_objectives` - engine auto-replicates to all 16; completion is
allied/BSP-driven (any-player). No change needed. `endleveltrigger` is commented (handoff is
allied-driven). No `parm.other==$player` gates (truck triggers are entity/AI-driven).

NOT done (out of scope, base-pak gags): the plane-ride per-player camera (Pattern A, e2l1 mirror).
The level script only HOOKS `DoPlaneRide`; the cinematic camera/harness logic is in the pak.

Test-watch items / RISKS:
- HIGH: plane ride uses whatever camera the pak gag does. If `DoPlaneRide` issues a GLOBAL
  `cuecamera`/`freezeplayer`, all 16 share one POV during the ride. Cannot be fixed at level-script
  level - needs a gag-side Pattern-A pass (deferred per master plan P3). Watch the intro for all
  players locked to one camera or a stuck/frozen state after barn crash.
- Confirm `t1_barninside`/`t1_barnoutside` ambient loops start/stop for joiners (loopsound shim
  skips spectators only).

---

## t1l2 - Dutch Town / Flak88

Changes:
- Music (93): `$player stufftext "tmstart ...Emmerich.mp3"` -> `exec ...::tmstart "..."`.
- Binoculars (116): `$player item items/binoculars.tik` -> `exec ...::item ...`.
- INTRO FREEZE (was 143-150): `$player fullheal` -> `exec ...::fullheal`; replaced GLOBAL
  `freezeplayer` + singular `$player.viewangles="0 160 0"` + `releaseplayer` with
  `waitthread coop_introFreeze "0 160 0"` / `wait 3` / `waitthread coop_introRelease "0 160 0"`.
- Music Gotha x2 (Flak88GonnaGoBoom ~555/560) and Labyrinth (MG42Trigger ~719) ->
  `exec ...::tmstart "..."`.
- ADDED per-map helpers `coop_introFreeze`/`coop_introRelease` (after main's `end`):
  per-player `freezecontrols 1/0` + `replace.scr::physics_off/on` + `viewangles` shim
  (skips spectators). Late joiners during the 3s window are also frozen via
  `level.coop_physicsOff` (manage loop) and released by `physics_on`.

Objective semantics: 2x Flak88 destroy objectives use `$Objective*` HUD ents +
`level.nRequiredObjectives` counter (level-global) - shared across 16, any player's destruction
decrements. `Objective3Complete` gates on counter==0 then `missioncomplete t1l3` (global). Correct.

`parm.other` gates: `MG42Trigger` (703) gates on NPC `level.friendly3`/`friendly2` (NOT players) -
left as-is. `CappyPlayFlushout` (748) is inside a commented `/* */` block - dead. No
`validateTriggerActivator` needed on this map.

Test-watch items / RISKS:
- MED: during the 3s intro freeze all 16 are input-locked + physics-off facing yaw 160. Verify they
  release together and can move/fight after. If the boat/menu drift matters, note the singular origin
  reposition was intentionally dropped (players stay where spawned).
- Captain (`level.cappy=friendly1`) escort/dialogue is NPC-self-driven; verify it doesn't deadlock if
  the gating friendly NPC dies (existing friendly2/3 dead-branch logic preserved).

---

## t1l3 - Dutch Canal Town / Colonel / Bridge

Changes:
- INTRO LOADOUT (57-70): `$player takeall` + 6x `$player item` + 5x `$player ammo` ->
  `exec ...::takeAll` / `...::item` / `...::ammo` (full Webley/Enfield/Sten/grenades/smoke kit to
  all players; `ammo` shim also adds to loadout so joiners get it).
- Music playerstart (133) and DeadOfficer (objective1 ~520): `$player stufftext "tmstop;tmstart..."`
  -> `exec ...::tmstart "..." 1` (the `1` = stop-prev-then-start).
- `$player fullheal` (144) -> `exec ...::fullheal`.
- `$player useweaponclass smg` (154) -> explicit `for $player.size` loop calling
  `useweaponclass smg` per active player (no shim exists for it).
- objective4 pickup sound (575): `$player playsound explosives_pu` -> `exec ...::playsound`.
- Ambient sound switchers `boatsounds`/`docksounds`/`exteriorsounds`/`interiorsounds` (274/288/302/
  316): `!(self.link istouching $player)` -> `!((exec ...::istouching self.link)==1)` (any-player
  in-zone test).
- `wallchargedialog` (~387): bare `$player.origin` distance hint -> nearest player via
  `player_closestTo self` with NULL guard.

KEPT GLOBAL ON PURPOSE:
- `releaseplayer` (153): the matching `freezeplayer` is issued INSIDE the boat-ride gag
  (`gags/t1l3_BoatRide.scr::DoBoatRide`), which ships in the Spearhead pak and is NOT editable.
  A per-player release CANNOT undo a global freeze, so this stays a global `releaseplayer`. The
  global freeze during the short boat-ride cinematic is the accepted fallback (documented in plan).
- `cueplayer` (906/918) in `blowbridge`: bridge-collapse cinematic; brief global cut accepted per
  plan (set-piece, not steady combat).

Objective semantics: 6 objectives via `global/objectives.scr` (track colonel / destroy tiger w/ flak
/ demo flak / acquire explosives / plant 4 charges / return to captain). All counter- or
BSP-trigger-driven and level-global (`level.charge1-4`, `level.chargecount`) - auto-replicate; any
player plants/triggers. Colonel-elimination objective1 polls `isAlive level.colonel` (NPC) - fine.
`pushtankthread` (321) gates `parm.other.owner==$pushtank` (entity, NOT player) - safe, left as-is.

Test-watch items / RISKS:
- HIGH: intro freeze is gag-owned + global. Verify all 16 are released after `releaseplayer` (153)
  and the boat ride doesn't strand non-host players frozen. This is the most likely t1l3 coop
  failure and is NOT script-fixable here.
- MED: bridge-collapse `cueplayer` momentarily yanks all views; verify no player is mid-respawn when
  `blowbridge` fires.
- Verify the full Soviet... (British) kit + ammo reaches every player and joiners (ammo->loadout).

---

## t3l1 - Berlin Streets / T-34 commandeer / Safe puzzle

Changes:
- `level.playertanktarget = $player` (21) -> `= 0`. Assigning the `$player` ARRAY would break
  `vehicles_thinkers.scr` consumers that read `.origin`/`.centroid`/`setaimtarget`. `0` makes the
  enemy-tank think-loops wait, then a new `coop_trackTankTarget` thread repoints it to a live player.
- Removed singular `$player.angles/.origin` prespawn capture (34-35) - array read at prespawn; the
  intro no longer repositions a single host.
- INTRO LOADOUT (46-63): `$player takeall` + 6x `item` + 5x `ammo` + `fullheal` -> replace.scr shims;
  then `thread coop_trackTankTarget`.
- INTRO FREEZE `intro_fade_in` (was 279-317): replaced GLOBAL `freezeplayer` + `$player physics_off`
  + singular `$player.viewangles`/`.angles`/`.origin` + `releaseplayer` with
  `waitthread coop_introFreeze "0 0 0"` ... `viewangles "0 -90 0"` shim ...
  `waitthread coop_introRelease "0 -90 0"`. `showmenu`/`hidemenu`/`hidemouse` left global (UI
  broadcasts to all - correct). Singular origin/angles reposition dropped.
- Music Kleveburg (s10_3 ~758) -> `exec ...::tmstart "..." 1`; musicchange (~942) tmstop+tmstartloop
  -> `exec ...::tmstartloop "mus_11a_surprise.mp3"`.
- `$player playsound plane1` x3 (panzer4, ai_spawn_1002, dostuff) + `pickup_papers` x2 (document1/2)
  + `stickybomb_pickup` x3 (sticky_pickup) -> `exec ...::playsound` (all players).
- `$player takeall` at objective7 transition (627) -> `exec ...::takeAll`.
- `pole_fall` (660): bare `$player.origin` fall-direction -> nearest player (`player_closestTo self`,
  fallback `player_anyValid`) with NULL guard.
- ADDED helpers `coop_introFreeze`/`coop_introRelease` (same shape as t1l2) and `coop_trackTankTarget`.

Objective semantics: 7 objectives via `global/objectives.scr` (cross bridge / find aircraft / find
chancellery / find safe / find combination / open safe / eliminate guards + commandeer T-34). All
BSP-trigger or level-global-flag driven (`level.combination`, `level.usetrigger5`, `level.safestate`,
`level.safelocated`) - auto-replicate; ANY player solves the safe puzzle / trips a trigger for the
team. objective7 waits for all 3 tankguards dead (global isAlive) then `$objective7trigger waittill
trigger` (any player) -> `missioncomplete t3l2` (global). Correct any-player semantics throughout.
No `parm.other==$player` gates on this map.

COOP SIMPLIFICATION (by design): `level.stickybombs` is a single level-global count; pickups/uses
add/decrement it for the whole team (shared sticky-bomb pool). Acceptable; note it.

The T-34 here is an AI prop / objective (commandeered at end -> next level), NOT a player-driven
vehicle on this map, so no Pattern-C work is needed (that is t3l2's job).

Test-watch items / RISKS:
- MED: intro menu-card showcase - verify all 16 are input-locked (freezecontrols) and physics-off for
  the ~10s menu sequence, then released together facing yaw -90. Menu cards (showmenu) broadcast to
  all.
- MED: `coop_trackTankTarget` repoints `level.playertanktarget` to a live player every 1s. Verify the
  panzer/static enemy tanks actually start firing (their think-loops were waiting on
  `playertanktarget != 0`). If tanks never fire, the tracker isn't resolving a valid player - check
  `player_anyValid` returns non-NULL after spawn.
- LOW: `pole_fall` now falls away from nearest player; verify the pole still animates (NULL guard
  skips the angle set if no valid player, leaving default pole angle).

---

## Top verify items (priority order)
1. t1l3 + t1l1: gag-owned GLOBAL intro freeze/camera (boat ride, plane ride) - confirm all 16 release
   and aren't stranded. NOT fixable in level scripts (base-pak gags); flagged for deferred Pattern-A.
2. t3l1: enemy tanks fire after `coop_trackTankTarget` resolves a player (was the silent-deadlock
   risk from the `playertanktarget = 0` change).
3. t1l2 / t3l1: per-player intro freeze releases cleanly for all players incl. mid-intro joiners.
4. All maps: full per-player loadout/ammo/music reaches every client and late joiners.
5. Objectives render + advance for all 16 (engine addobjective replication) - any-player completion.

## Files edited
- hzm-mohaa-coop-mod/maps/t1l1.scr
- hzm-mohaa-coop-mod/maps/t1l2.scr
- hzm-mohaa-coop-mod/maps/t1l3.scr
- hzm-mohaa-coop-mod/maps/t3l1.scr

# Spearhead Infantry 16-Player Coop Conversion - t2l1 / t2l3 / t2l4

Date: 2026-06-24. Scope: per-element 16-player scaling of three already-hooked Spearhead
infantry maps. Edits limited to `hzm-mohaa-coop-mod/maps/t2l1.scr`, `t2l3.scr`, `t2l4.scr`.
No pk3 rebuild, no game launch, no GOG files touched. All files verified ASCII-only, no BOM,
braces balanced (t2l1 85/85, t2l3 309/309, t2l4 27/27).

All conversions use EXISTING `coop_mod/replace.scr` shims (which fall back to vanilla SP
behavior when `level.gametype == 0`, so they are safe to call unconditionally):
- `physics_off` / `physics_on` (loop all players)
- `fullheal` (no-op in coop; high-health managed by framework) / `nodamage` / `takedamage`
- `takeAll` / `item` / `ammo` / `take` (broadcast to all players + add to loadout)
- `viewangles` (set all players' view) / `threatbias`
- `tmstart` / `tmstartloop` (broadcast music) / `playsound` (broadcast VO, optional sounddone wait)
- `missionfailed` (respawn-aware; suppressed->restartMap during maptest)
- `player_closestTo <ent>` (returns closest living player, or `$player` in SP, NULL if none)
- `istouching <ent>` (returns 1 if ANY active player is touching)

---

## t2l1.scr (Ardennes / Nebelwerfers / Tiger Tanks) - 2140 lines

### Changes (file:line approximate post-edit)
- :12 intro `$player physics_off` -> `replace.scr::physics_off` (lock all 16).
- :35 music `$player stufftext "tmstart ...SniperTown..."` -> `replace.scr::tmstart`.
- :239-253 loadout block (`fullheal/takeall/item x5/ammo x5`) -> per-shim broadcasts.
- :306 `level_fadein` `freezeplayer` removed (players already physics_off); `$player.viewangles`
  -> `replace.scr::viewangles ( 0 155 0 )`.
- :337 `releaseplayer` removed; second viewangles -> shim; `$player use "Thompson"` ->
  `replace.scr::item weapons/thompsonsmg.tik 1` (all players ready it).
- :359 post-dialogue `$player physics_on` -> `replace.scr::physics_on` (this is now the single
  release point for all players, replacing the dropped global releaseplayer).
- :611 `parade_trigger_think` `while ($player istouching $parade_trigger)` ->
  `while ( exec ...::istouching $parade_trigger )` (any player sustains the MG42 parade).
- :1162 / :1185 nebeller proximity `while !($player istouching self.target)` /
  `while ($player istouching self.target)` -> istouching shim (any player engages/disengages
  the nebelwerfer crew).
- :1259 `sniper_rifle_pickup`: `$player item g43` -> broadcast `item`; `$player use "G 43"` kept
  (host auto-equips; all already have it in inventory).
- :160 / :2035 `level.playertanktarget = $player` -> `= $player[1]` (array -> single entity).
- enemy tank attack loop: added per-iteration refresh of `level.playertanktarget` via
  `player_closestTo self` so the Tiger tracks the nearest living player and never breaks on a
  dead/disconnected player[1].
- :1642 / :1790 music `$player stufftext "tmstop"+"tmstart/tmstartloop"` -> `tmstart ... 1` /
  `tmstartloop` broadcasts.

### Objective / fail semantics
- 5 objectives via `global/obj.scr` + `global/objectives.scr` ("[N remaining]" nebelwerfer
  counter). Counters are `level.*` globals; engine `addobjective` auto-replicates to all 16.
  Completion is destruction-based (any player) - no per-objective change needed.
- SQUAD-DEATH fail (`check_squad_death`, ~:1854): routed through `replace.scr::missionfailed`
  (was bare `missionfailed`). Added a guard: if all 4 core objectives are already complete when
  the 3-NPC squad wipes, the fail is suppressed (don't punish 16 humans for losing a now-redundant
  NPC squad). Intended difficulty otherwise preserved - the squad is `nodamage` until combat opens.
- `endlevel` -> `missioncomplete t2l2` unchanged (handled by global script per recipe Step 10).

### Test-watch items
- After intro: all players should be released (physics_on at :359) and able to move. If anyone
  stays frozen, the freeze/release pairing changed - check :12/:359.
- Nebelwerfer crews should stop firing when ANY player approaches the trigger volume.
- Tiger tanks should fire at whichever player is closest, and keep firing after player[1] dies.

### Risks
- `halftrack1_bomb` (~:1714) proximity self-damage still reads `$player.origin`/`.health`
  (host-only forced-kill anti-exploit). Left as-is: the `radiusdamage` already hits all players
  in radius; only the redundant host force-kill is host-scoped. Low impact.
- `$player modheight "duck"` (~:264) intro crouch is host-only cosmetic. Left.

---

## t2l3.scr (Bastogne Wave Defense) - largest, ~3370 lines

### Changes
- :18 intro `$player physics_off` -> shim.
- :121 `$player threatbias -10` -> `replace.scr::threatbias -10` (all players).
- :337-349 German loadout (p38/kar98/mp40/grenades + ammo) -> per-shim broadcasts.
- :351 `freezeplayer` removed; `$player.viewangles "0 90 0"` -> `viewangles ( 0 90 0 )`.
- :391 `releaseplayer` removed; viewangles -> shim. Physics restored at :447.
- :447 `$player physics_on` -> shim (single release point for all).
- :468 `threatbias: $player threatbias 0` -> shim.
- :476 `endthedemo` `$player nodamage` -> `replace.scr::nodamage` (protect all during victory).
- :907 `halftrack1isdead` `$player nodamage` -> shim (protects all from death radiusdamage).
- `triggersarg` / `sargetimerboost` distance gates: `$sarg.origin - $player.origin` ->
  distance to `player_closestTo $sarg` (ANY player reaching the sergeant advances objective1).
- `TwoAmericanGuysRunToLeft/RightFlank`: `$player.origin` redeploy heuristic -> per-friendly
  `player_closestTo` (and avoids `.origin` on the array).
- 5x enemy `walkto/runto $player` (wave AI) -> `player_closestTo <enemy>` target (a real player;
  avoids array errors and host-fixation).
- `GermanNoDrawManager` LOD cull: `$player.origin` -> closest-player distance.
- AXISWINS-breach fail VO (`kommanderthink`, ~:1766): 3x `$player playsound ... wait` +
  `waittill sounddone` -> `replace.scr::playsound <alias> 1` (broadcast + internal wait);
  `missionfailed` -> `replace.scr::missionfailed`.
- `takeoutplayer` / `killplayer` hazard: `$player istouching $killbrush` + `$player kill` ->
  loop over `$player[]` killing each active player touching the killbrush / each active player
  (boundary hazard now hits all, not just host).
- `mp44pickup`: `$player item mp44` -> broadcast `item`; pickup sound -> broadcast `playsound`;
  `$player use "stg 44"` kept (host equips).
- 8x ambience/callout `$player playsound` (barrage, wave, flank VO) -> broadcast `playsound`.
- 2x bazooka-ally `local.ent turnto $player` -> `player_closestTo` (face a real player).

### Objective / fail semantics
- Obj1-6 (talk-to-captain, find/escort medic, hold waves 1-3). Reach-gates now use closest-player
  distance; escort is NPC/medic-driven (player-agnostic). Wave clear is AI-count / volume based.
- FAIL via `level.axiswins=1` (Germans breach trigger5/8): level-global, kept as shared-loss coop
  behavior (correct per plan). Only routed through coop `missionfailed` + broadcast the retreat VO.
- Win after wave 3 -> `missioncomplete t2l4` (`endthedemo`) unchanged.
- NOTE: t2l3's `deathcheck` label (:482) is EMPTY - there is no separate squad-wipe `missionfailed`
  here; the only mid-level fail is the axiswins breach. (The master plan's "squad-death fail
  t2l3" maps onto the axiswins breach, which is correctly level-global.)

### Test-watch items
- Intro freeze: all 16 frozen during Bastogne menu cards, all released at artillery barrage (:447).
- Objective 1 should advance when ANY player (not just host) reaches the kneeling sergeant.
- Killbrush boundary should kill any player crossing it, not only the host.
- Wave AI should path to nearest player; verify no "no closest player" stalls when all dead
  (guarded with `!= NULL`).

### Risks
- :129 `$player.origin = (388 3811 1816)` debug teleport inside `if (getcvar(start)=="end")` -
  cvar-gated dev shortcut, host-only, left unconverted (not in normal play path).
- `local.ent = $player` (~:3031/3040) is now a dead assignment (the VO it anchored is broadcast);
  harmless plain assignment, left.

---

## t2l4.scr (Stavelot Town - Church/Hotel/Barn) - ~1210 lines

### Changes
- :49 stray second `level waittill spawn` (AFTER the :27 `waitForPlayer` gate) commented out -
  this is a coop deadlock/ordering hazard; `waitForPlayer` already gates spawn per recipe Step 3.
- :77 `$player fullheal` -> `replace.scr::fullheal`.
- `KillThePlayer` (~:414) boundary/minefield hazard: VO `$player playsound` -> broadcast; the
  `while(isalive $player){ radiusdamage $player.origin }` host-only force-kill -> a BOUNDED loop
  (6 ticks) that damages every active player currently `isTouching` one of $killtheplayer1/2/3,
  then turns the killzones off. Bounded + touch-gated so respawned (back-in-bounds) players are
  not re-killed; the $killtheplayer brushes remain the persistent volume hazard.
- 4x building-entry trigger gates `if (parm.other==$player || parm.other==$cappy)`
  (spawn_52, spawn_70_a/b/c) -> `if ( waitthread coop_isPlayerOrCappy parm.other )`.
- NEW local helper `coop_isPlayerOrCappy local.activator` (returns 1 if activator is $cappy or
  ANY player in `$player[]`) - the list-accepting equivalent of validateTriggerActivator for the
  player-OR-captain set. Any of the 16 (or the captain) now triggers the church/hotel ambushes.
- `give_sniper_rifle`: `$player item KAR98sniper` -> broadcast; `$player use` kept (host equips).
- `shotgun_ammo`: `$player take/give/ammo` -> broadcast `take`/`item`/`ammo` shims;
  `$player useweaponclass heavy` kept (host selects).
- `BeBazookaGuy` (:586): `self exec global/aimat.scr $player` -> aim at `player_closestTo self`.
- `windowguy_9999_show` `$billy turnto/lookat $player` -> `player_closestTo $billy`.

### Objective / fail semantics
- 6 sequential building objectives via `global/objectives.scr` (church -> hotel -> end).
  Engine `addobjective` auto-replicates. Building-entry spawns now gated to any-player-or-cappy.
  Ending handed off via `gags/t2l4_captain.scr::DoEnding` at the hotel/spawn_8 stage.
- No mid-level `missionfailed` in this map (the death triggers are hazards, not mission-fail);
  nothing to route. Win -> next mission via the captain ending gag (unchanged).

### Test-watch items
- CRITICAL: with the :49 spawn gate removed, confirm the map still completes init (reaches the
  `end` of main) and players spawn - this is the highest-risk single edit. If players never
  leave spectator, re-examine the gate ordering.
- Church/Hotel ambushes must fire when ANY player (or the captain) enters - verify the new
  `coop_isPlayerOrCappy` helper returns correctly (it `end 1`/`end 0`, called via `waitthread`).
- Boundary minefield should kill players who STAY out of bounds but not re-kill respawners.
  If the $killtheplayer1/2/3 brushes are not `isTouching`-testable, the bounded force-kill simply
  no-ops and the killzone brushes still handle it (acceptable degradation).

### Risks
- `coop_isPlayerOrCappy` is called via `waitthread` in a trigger condition; if `parm.other` is an
  AI/NPC other than $cappy it correctly returns 0 (spawn skipped) - matches vanilla intent.
- The bounded killzone loop's `isTouching` on brush entities is best-effort (see above).

---

## Top verify items (across all three)
1. t2l4:49 - removed second `level waittill spawn`: confirm init completes and all players spawn.
2. t2l1 squad-wipe: confirm `missionfailed` routes through the coop shim (maptest won't loop) and
   the new "objectives-complete suppresses fail" guard behaves.
3. t2l3 axiswins breach + t2l1 squad death: both now via `replace.scr::missionfailed` - verify no
   restartMap loop under maptest and sane coop respawn.
4. All intros: global freeze/cam fully removed; all 16 lock at intro and release together
   (t2l1 physics_on :359, t2l3 :447).
5. t2l4 building ambushes fire for any player or the captain via `coop_isPlayerOrCappy`.
6. Hazard zones (t2l3 killbrush/killplayer, t2l4 KillThePlayer) affect all players, not just host.
7. Enemy AI walkto/runto and tank aim-target now follow the nearest living player (no player[1]
   array errors, no host-fixation, no stall when a target dies).

# Fix: e3l2 "Destroy the 3 Modello cannons" objective for coop (up to 16 players)

## Summary

The ONE confirmed RED objective from the audit (`objective_coop_confidence.md`) is now coop-correct.
The e3l2 cannon mount + charge-plant no longer routes through the un-converted shared
`global/MountGunOrPlantCharge.scr` (which polled the bare `$player` array head and so was host-only).
It now runs a per-player think loop local to e3l2 that iterates every active player, modeled on the
framework's existing per-player cannon primitive. Any of up to 16 players can mount a Modello and any
can plant the charge; the 3-cannon counter is level-global and completes the objective for everyone.

No coop_mod framework files were changed. `global/MountGunOrPlantCharge.scr` was NOT touched (other maps
could depend on it). Only `maps/e3l2/cannons.scr` was edited. No pk3 rebuild, no launch, no GOG files.

## M-series / reference pattern I learned from

**Reference primitive: `coop_mod/cannonThink.scr::cannonThink`** (the framework's per-player gun-mount
primitive), and its only in-tree consumer, **`maps/e2l3/Town.scr`** (`$deCanonDaJa thread cannonThink`,
Town.scr:62; the thread is also inlined in that file at Town.scr:258).

What that pattern does and what I borrowed:
- It loops `for (local.i = 1; local.i <= $player.size; local.i++)` over `$player[local.i]`
  (1-indexed) instead of touching the bare `$player` head.
- Per player it gates on: `health > 0`, and in coop (`level.gametype != 0`) skips
  `dmteam == "spectator"`, `flags["coop_isActive"] != 1`, and `flags["coopDevNoclip"]` noclip devs.
  (Same guard used by `coop_mod/replace.scr::player_closestTo`.)
- It detects the player who is in range + facing + pressing `useheld`, selects THAT player, and
  acts on them (`doUse local.playerSelected`), then watches that same selected player for the exit
  press. Respawn-inside-gun is avoided via `flags["coop_respawnOrigin"]`.

### Why I did NOT call `cannonThink` verbatim

`cannonThink` only models **mount/dismount of a player-operated gun** (its completion in e2l3 is
"destroy the tank by combat", not a charge plant). e3l2 is different: the objective is completed by
**planting a charge on the throbber**, not by mounting. The mount in e3l2 is optional flavor. e3l2's
`self` inside `GunOrExplosive` is the *script* `$Cannon` (not the usable gun), and mount/dismount are
done by the map's own `PlayerMountCannon` / `PlayerDismountCannon` (show/hide + `douse`) rather than
`doUse self`. Calling the shared `cannonThink` would `doUse` the wrong entity and would have no
charge-plant path at all.

So I applied the SAME per-player iteration pattern but kept it local to e3l2, wiring it to e3l2's
existing mount/plant threads. This is the equivalent of `MountGunOrPlantCharge` (which also had both a
gun branch and a throbber/charge branch) but with the host-only `$player` polling replaced by the
coop `$player[]` loop.

## How the SP path worked (what I replaced)

- `maps/e3l2/cannons.scr::GunOrExplosive` (was line 200) called:
  `self exec global/MountGunOrPlantCharge.scr self throb 250 100 "Modello" "...Cannons.scr"
  "PlayerMountCannon" "PlayerDismountCannon" "SetCannonExplosives" usable_cannon`.
- Inside that global, every interaction (mount detection + charge-plant detection + help text) was
  driven by bare `$player.useheld` / `$player.origin` / `$player.angles` (MountGunOrPlantCharge.scr:98,
  100,115,126,140,142,143,157,161,169) = the 1-indexed array head = host only.
- Completion chain: charge plant -> `SetCannonExplosives` -> `self.throbber doUse` -> the throbber's
  BSP use-callback fires `e3l2.scr::Cannon#DestructionThread` -> `level.num_cannons_remaining--` and
  `ObjMgr.scr::CompleteObj "killModellos" #`. That chain is already level-global; the ONLY broken link
  was WHO could trigger the plant (host only).
- The mount/dismount in `cannons.scr` also used bare `$player` for `douse $player` (215, 241) and the
  off-gun teleport `$player.origin = ...` (260).

## Exactly what I changed (file:line, post-edit)

All edits in `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps\e3l2\cannons.scr`:

1. **`GunOrExplosive` (around old line 200):** removed the `self exec global/MountGunOrPlantCharge.scr ...`
   call and replaced it with `self thread CoopGunOrChargeThink local.usable_cannon local.cannon_throb 250 100`.
   (cannons.scr ~208)

2. **New thread `CoopGunOrChargeThink local.usable_cannon local.throbber local.gun_range local.throb_range`
   (cannons.scr ~219-320).** Per-frame loop while the cannon/turret exist:
   - If a player is on the gun (`self.playerinturret == 1`): watch ONLY the tracked mounter
     (`self.coopMountPlayer`). Force dismount if that player is NULL / dead / spectator /
     `coop_isActive != 1`, or presses use to leave. A `self.coopMountArmed` release-then-press latch
     prevents the same hold that mounted the gun from instantly dismounting it.
   - Otherwise loop EVERY active player (`for local.i = 1 .. $player.size`, `$player[local.i]`), apply
     the standard coop active-player guard, require `useheld`, then:
       - **Charge plant first** (objective-completing): if `self.noexplode == 0 && self.explosiveset == 0`
         and the player is `vector_within` `throb_range` of the throbber -> set `self.coopMountPlayer`
         and `self waitthread SetCannonExplosives`.
       - **Else mount the gun** (flavor): if `usable_cannon canuse player` and `vector_within gun_range`
         of the gun -> set `self.coopMountPlayer`, clear `coopMountArmed`, `self waitthread PlayerMountCannon`.
   - `.25s` debounce after any action.

3. **`PlayerMountCannon` (~227):** `self.usable_cannon douse $player` -> `self.usable_cannon douse self.coopMountPlayer`.

4. **`PlayerDismountCannon` (~341):**
   - `self.usable_cannon douse $player` -> `self.usable_cannon douse self.coopMountPlayer`.
   - off-gun teleport `$player.origin = (...)` -> guarded `if (self.coopMountPlayer != NULL &&
     self.coopMountPlayer.health > 0) { self.coopMountPlayer.origin = (...) }`, then `self.coopMountPlayer = NULL`.

## Preserved wiring (unchanged)

- The 3 cannons are still set up by `InitCannons` / `InitACannon` (cannons.scr:7-40) with their
  throbbers, turrets, and `noexplode` gating.
- Each cannon is still revealed/armed for planting elsewhere unchanged: `cannon_section_1.scr:264-265`
  (`$Cannon1_Throb show` / `noexplode = 0`), `tank_section.scr:91-92` (Cannon2),
  `final_section_pows.scr:139-140` (Cannon3).
- `SetCannonExplosives` still does `self.throbber doUse` + `self.throbber.exploded = 1`, firing the BSP
  use-callback that runs `e3l2.scr::Cannon#DestructionThread`.
- `Cannon1/2/3DestructionThread` (e3l2.scr:236-295) untouched: `level.num_cannons_remaining--`,
  `ObjMgr.scr::CompleteObj "killModellos" #`, dead-cannon collision, and the
  `if (num_cannons_remaining <= 0) SetObjDesc` finalizer.
- ObjMgr registration of `killModellos` is unchanged. Engine `addobjective` HUD state auto-replicates
  to all 16 clients (no per-map push needed).

## How completion works for N players now

`level.num_cannons_remaining` starts at 3 and is decremented by the per-cannon DestructionThread, which
is fired by the charge plant of THAT cannon. Because the plant detection now accepts ANY active player
(not just `$player[1]`), the three plants can be performed by any mix of the up to 16 players, in any
order. Each plant decrements the shared level-global counter and completes that objective slot for
everyone via ObjMgr; when the counter hits 0 the objective description finalizes ("Destroy Enemy
Artillery"). The objective is no longer host-gated.

## Parse hygiene (verified)

- File starts with `2f 2f 20` (`// `) -> no UTF-8 BOM.
- No non-ASCII bytes (no em-dash, no Win-1252 smart quotes) - grep for `[^\x00-\x7F]` returns none.
- Brace/paren/bracket balance: `{}` 44/44, `()` 61/61, `[]` 27/27.
- `$player` only appears as `$player[local.i]` and `$player.size` (1-indexed loop) - no bare
  interactive `$player` left in the cannon path (verified by negative-lookahead grep).
- No multi-line `&&`/`||` conditions; the one compound `if` that risked a NULL deref was split into
  nested `if`s. No bare negatives in parens (the `(... -local.player_detach_dist)` etc. are vector/scale
  math, which is allowed).

## Residual risk / notes

- **`canuse` semantics unverified at runtime:** the gun-mount branch gates on
  `local.usable_cannon canuse local.player`. This mirrors the original global's `canuse $player` check
  but is now per-player. If `canuse` behaves oddly with a non-host argument it would only affect the
  optional gun MOUNT, not the charge-plant completion path (plant uses pure distance, no `canuse`).
- **No facing/dot check on the plant** (the original global also checked throbber facing). I kept plant
  detection to distance-only (`vector_within throb_range`) for robustness with 16 players crowding the
  throbber; this only makes planting slightly easier, never harder, and cannot mis-complete (each
  throbber maps to exactly one cannon, `explosiveset`/`noexplode` prevent double-fire).
- **`CannonFire` still uses bare `$player.origin`** (cannons.scr ~95-117) for the SP fallback target
  when the cannon fires AT a player. That is the enemy-firing path, not an interactive objective path,
  was not flagged RED by the audit, and was left unchanged to avoid altering firing behavior.
- **Help text (throbtext) dropped:** the old global showed "Press X to plant the explosive / use the
  Modello" prompts. The new loop omits the on-screen prompt for simplicity; interaction still works by
  walking up and pressing use. If desired, a `global/throbtext.scr::throbtext` call can be added inside
  the player loop later (cosmetic only, not required for completion).
- Not runtime-tested (no launch per task constraints). Static review + parse-hygiene checks only.

## Answer to the report-back questions

- **M-series map learned from:** `maps/e2l3/Town.scr` (`$deCanonDaJa thread cannonThink`), backed by the
  framework primitive `coop_mod/cannonThink.scr` and the active-player loop in
  `coop_mod/replace.scr::player_closestTo`.
- **What I changed:** replaced the host-only `global/MountGunOrPlantCharge.scr` call in
  `maps/e3l2/cannons.scr::GunOrExplosive` with a local per-player `CoopGunOrChargeThink` loop, and
  fixed the three bare-`$player` mount/dismount references (douse x2, off-gun teleport).
- **Does the 3-cannon objective now complete for any player?** Yes. Any active player can plant any
  cannon's charge; each plant decrements the level-global `num_cannons_remaining` via the unchanged
  DestructionThread/ObjMgr chain, so the objective completes for all players when all 3 are destroyed by
  any mix of players.

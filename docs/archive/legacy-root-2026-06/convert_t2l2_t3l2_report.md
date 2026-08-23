# Coop Conversion Report — t2l2 (Pattern B) + t3l2 (Pattern C)

Scope: staged script edits only, under `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\maps\`. No pk3
rebuild, no launch, no GOG/base-pak edits. Shared files (coop_mod/*, global/vehicles_thinkers.scr,
vehiclehandler.scr) READ only — any needed shared change is documented below, not applied.

Files edited:
- `hzm-mohaa-coop-mod/maps/t3l2.scr`
- `hzm-mohaa-coop-mod/maps/t2l2.scr`

Parse hygiene verified on both: ASCII-only (no byte > 0x7F), no UTF-8 BOM, balanced braces
(t2l2 59/59, t3l2 79/79) and parens, compound conditions on one line, no bare negative as first
token inside `()` (vectors wrap each component, e.g. `( (local.back) (local.side) (local.up) )`).

---

## t3l2 — Pattern C (player-driven T-34), CRITICAL

### Vehicle setup approach
The player tank `$playertank` is `addon_vehicle_russian_T34tank`, hull model
`vehicles/t34_base.tik`, cannon subpart `vehicles/t34_cannon.tik` (confirmed in
`map_entities/t3l2_entities.txt:467-474` and `maps/t3l2_precache.scr:22`). The stock coop path in
`global/vehicles_thinkers.scr::players_tank` scans for `models/vehicles/kingcannon.tik` (King Tiger)
to attach `$coop_tankOffset`/`$coop_tankExit`. On a T-34 that scan never matches, `$coop_tankOffset`
stays NULL, and `coop_selectDriverForTank` loops forever — **nobody can ever board, silently.** This
is the CRITICAL risk the plan flagged, now confirmed by entity data.

Fix (mirrors `m5l2b.scr:62-81`), added in `main` inside an `if( level.gametype != 0 )` block
**before** the `players_tank` call so that `players_tank`'s own `if($coop_tankOffset == NULL)` guard
skips its broken kingcannon scan:
1. Scan `getentbyentnum 0..maxentities` for an entity whose `.model == "models/vehicles/t34_cannon.tik"`
   and `attachmodel "fx/fx-dummy.tik" "connect" ...` two dummies named `coop_tankOffset` / `coop_tankExit`
   (same model token + offsets the live players_tank uses; `fx/fx-dummy.tik` ships in the coop pk3).
2. **Hull fallback** — if after the scan `$coop_tankOffset` is still NULL (tag/model mismatch), attach
   the two dummies to `$playertank` itself at the `tag_origin` tag (present on every model). This
   guarantees boarding is never silently dead even if `t34_cannon.tik` lacks a `connect` tag.

`level.coop_playerTank` is intentionally **left NULL** after setup. `coop_selectDriverForTank` treats
NULL as "tank is free to board" and sets it to the boarding player; pre-setting it to `$playertank`
(as m5l2b does for its no-human King Tiger) would make the board loop exit immediately. For t3l2 a
human driver is the primary goal, so the seat stays open. `players_tank` (which threads
`player_tank_health` -> `coop_selectDriverForTank`) is still called and does the rest of the setup
(shadow, collisionent, turret nodamage, aim target).

### Driver / boarding / seat handling for 16
- 1 of 16 players drives via the stock `coop_selectDriverForTank` (hold USE within 300u of
  `$coop_tankOffset`). Driver gets `attachdriverslot 0`, glued to `$coop_tankOffset`, weapon
  "88mm Tank Gun", physics_off/notsolid/nodamage/hide. The other 15 fight on foot / ride along.
- Seat rotation on driver death/exit is handled by the stock `coop_setDriverForTank` loop (it detects
  death/team-change/USE-to-exit, places the player at `$coop_tankExit`, then re-threads
  `coop_selectDriverForTank` so the next player can board). No new seat logic needed for Pattern C.
- Optional **auto-drive fallback** (`coop_autoDriveTankFallback`, new): waits a 20 s grace window for a
  human to board; if `level.coop_playerTank` is still NULL it claims the tank for itself
  (`level.coop_playerTank = $playertank`) and runs `drive_path $playertank_trigger level.slowspeed`
  so the convoy/objectives still progress with no driver.

### Intro singular-`$player` mutations -> coop loops
- `$player physics_off` (orig 37): gated to SP only; in coop only the boarded driver gets physics_off
  via `coop_setDriverForTank`. Matching `$player physics_on` (orig 138) gated to SP only.
- `$player takeall` (orig 44 + orig 52), `$player holster` (orig 53), `$player fullheal` (orig 62):
  now loop over `1..$player.size` skipping spectators.
- Music `$player stufftext "tmstop; tmstartloop ...Schmerzen..."` (orig 139): SP path unchanged; coop
  path uses `coop_mod/replace.scr::tmstop` + `::tmstartloop` (all-player broadcast).

### Bridge exploder activator fix
`bridgecollapsetrigger` (orig line 976) gated on `parm.owner == $player` — the projectile (tank
shell) owner. `validateTriggerActivator` checks `parm.other` (toucher), not `parm.owner`, so it is
**not** applicable here; I wrote an explicit coop owner check. In coop it accepts the shell owner
being `$playertank`, `level.coop_playerTank` (the current driver), or ANY active non-spectator player.
SP behavior unchanged.

### Changes (file:line, current t3l2.scr)
- 33-70: coop T-34 cannon-scan + hull fallback setup block (NEW).
- 76-82: comment — keep `level.coop_playerTank` NULL.
- 87-89: `$player physics_off` gated to SP.
- 96-105: `$player takeall` -> all-player loop (prespawn intro).
- 113-126: post-waitForPlayer `takeall`/`holster` -> all-player loop.
- 133-145: `$player fullheal` -> all-player loop.
- 220-237: `physics_on` gated to SP; music swapped to coop tmstop/tmstartloop; start
  `coop_autoDriveTankFallback` in coop.
- 1112-1135: `coop_autoDriveTankFallback` function (NEW).
- 1071-1117 area: `bridgecollapsetrigger` owner check rewritten for coop.

### What to verify in the harness
1. **Boarding actually works** — load t3l2 in coop, walk a player to the T-34, hold USE; confirm they
   mount, get the 88mm gun, and can drive/fire. If they cannot, the `connect` tag is absent on
   `t34_cannon.tik` and the hull fallback engaged — check the tank-relative seat offset feels right.
2. `$coop_tankOffset`/`$coop_tankExit` exist after spawn (dprintln their origins if unsure).
3. Bridge collapses when the driver fires a shell into the bridge trigger after `level.bridge_ready=1`.
4. Non-driver players keep weapons/physics and can fight on foot.
5. With NO player boarding, the auto-drive fallback moves the tank after ~20 s (objective 2 path).

### Biggest risk
**Whether `t34_cannon.tik` exposes a `connect` tag (and whether that tag's offset seats the driver
sensibly).** `t34_cannon.tik` lives in the base GOG pak and could not be read here, so the tag name is
unverified. Mitigation: the hull `tag_origin` fallback guarantees `$coop_tankOffset` is always created,
so boarding can never be *silently* dead — but if the fallback path is taken, the driver's glued
position/offset on the T-34 may need a tuning pass (adjust the `(0 0 60)` / `(0 -120 60)` offsets).

---

## t2l2 — Pattern B (halftrack ride, man the gun)

### Vehicle confirmation
Player vehicle `$s1_jeep1` (= `level.playerjeep`) is `addon_vehicle_german_snowy-halftrack-antitank`,
model `vehicles/halftrack_driveable.tik` (confirmed `map_entities/t2l2_entities.txt:1607-1614`). It is
**auto-driven** on a scripted path by `PLAYER_JEEP_Drive` and carries a turret slot 0. The shared
`PLAYER_JEEP_CONTROLLER` already skips attaching `$player` in coop (`gametype!=0`), so without a coop
layer the halftrack rides empty. `$nebel1`/`$nebel1_turret0` is a *separate* mounted nebelwerfer
set-piece, not the player's seat; the player mans the halftrack turret slot 0.

### Seating approach + 16-seat handling
Ported the m1l3b Pattern B family onto `$s1_jeep1`:
- `coop_setup` — loops `level waittill playerspawn` and threads `coop_playerSpawned` (handles late
  joiners + respawns).
- `coop_setupAttach` — **extended from m1l3b's 8 seats to 16** (`playerAttach2..16`). Offsets are
  generated programmatically in rows of 3 (back/side/up stepping) and `attach`ed to the halftrack
  `passenger0` tag (same tag m1l3b uses).
- `coop_playerSpawned` — seats `$player[1]` as the turret gunner (`attachturretslot 0` + preferred
  ".30cal Machine Gun", matching the controller's SP weapon); glues seats 2..16 to their dummy
  (`notsolid` + `forcelegsstate CROUCH_IDLE` + `glue`). Extra players beyond 16 simply are not glued —
  they fall through the loop and remain on-foot (acceptable; the halftrack is slow and pauses on the
  cliff). The coop framework ungluess on death automatically.
- `coop_jeepNotOccupied` / `coop_playerForceToJeep` — "press USE to enter" for the turret seat;
  `level.coop_inJeep` tracks gunner occupancy.
- `coop_playerJustDied` / `coop_playerJustLeft` — framework auto-calls these by name
  (`coop_mod/player.scr:1071` / `:129`); they free the turret and re-open boarding when the gunner
  dies/leaves.
- `coop_giveAmmo` — tops up all players every 30 s.
- `coop_releaseAllFromJeep` (NEW) — called from `endlevel`: detaches the turret slot and ungluess +
  re-solidifies all passengers so the ride ends cleanly.

**Seat-cap decision:** chose to extend to a full 16-glued-seat handler (rows behind the gunner) rather
than walk-alongside, because the halftrack auto-drives a fixed path with a downhill/reverse segment
where stray on-foot players would be left behind. Overflow beyond 16 (shouldn't happen at maxclients
16) safely walks on foot.

### Drive gate
`PLAYER_JEEP_Drive` now waits (coop only) up to ~600 frames for `level.coop_inJeep` before driving off,
so the halftrack doesn't leave before a gunner mounts; the timeout still starts the ride if nobody
boards.

### Intro / trigger fixes
- `$player fullheal` + `$player.health = 1000` (orig 94-95) -> loop over all non-spectator players.
- `triggerexplode` `parm.other == $player` (orig 853): rewritten — coop accepts ANY active player OR
  the halftrack (`level.playerjeep`) as the toucher (these are route-ambience explosions). SP
  unchanged. (`validateTriggerActivator` was not used here because the same `triggerexplode` label is
  shared by ~20 trigger entities each doing `self waittill trigger` in a loop; an inline activator
  check keeps each trigger live without cloning churn.)

### Changes (file:line, current t2l2.scr)
- 94-108: `$player fullheal`/`health` -> all-player loop.
- 110-117: thread `coop_setupAttach` / `coop_setup` / `coop_giveAmmo` in coop, after the controller.
- 833-841: `PLAYER_JEEP_Drive` coop occupancy gate.
- 871-901: `triggerexplode` activator check rewritten for coop.
- 928-934: `endlevel` calls `coop_releaseAllFromJeep` in coop.
- 958-1162: Pattern B coop function block (NEW): coop_setup, coop_setupAttach (16 seats),
  coop_jeepNotOccupied, coop_playerJustDied, coop_playerJustLeft, coop_playerForceToJeep,
  coop_playerSpawned, coop_releaseAllFromJeep, coop_giveAmmo.

### Camera note
t2l2 uses `gags/t2l2_camera.scr` (`triggercamera`/`triggercamerab`) for scripted halftrack-wobble
cameras. These gags live in the base pak (not in the mod tree) and were NOT touched. If in the harness
all players snap to one shared camera during the wobble cutscenes, switch to a per-player Pattern A
camera (m1l1 `trigger_camerause`+`doUse` per player). Left as-is for now since the camera gag is
short and the plan rated it conditional ("if all players snap to one cam"). FLAGGED for harness check.

### What to verify in the harness
1. Gunner mount: first player gets the halftrack gun; HUD "press USE" appears for nearby players.
2. Passengers (players 2..N) are glued to the moving halftrack and don't fall off during the
   downhill/reverse segment; offsets look reasonable (tune the row offsets in `coop_setupAttach`).
3. Halftrack waits for a gunner then drives; ride still starts if nobody boards (timeout).
4. Gunner death re-opens the seat (`coop_jeepNotOccupied` re-arms).
5. At `endlevel` passengers unglue and become solid/mobile.
6. Camera gags: confirm whether the wobble cutscene cameras are per-player or shared (see Camera note).
7. `$nebel1_turret0` enemy nebelwerfer still behaves (untouched).

### Biggest risk
**The `passenger0` tag on `halftrack_driveable.tik` and the 16-seat glue offsets.** The tag name is
the standard vehicle passenger tag (m1l3b relies on it on the jeep), but `halftrack_driveable.tik` is
in the base pak and unverifiable here, and 16 glued bodies on a vehicle doing a downhill + reverse
maneuver is the heaviest, least-tested case. If `passenger0` is absent on the halftrack, the dummies
attach at the vehicle origin and riders will bunch at one point (still glued, just visually stacked) —
adjust the tag or fall back to attaching to the vehicle root.

---

## Shared-helper changes needed from the main session
**None required.** Both conversions are self-contained in the two map scripts:
- t3l2 reuses the existing `players_tank` / `coop_selectDriverForTank` / `coop_setDriverForTank`
  (`global/vehicles_thinkers.scr`) unchanged — my pre-scan just populates `$coop_tankOffset` before
  `players_tank` runs, so the stock kingcannon scan no-ops via its own guard.
- t2l2 reuses `PLAYER_JEEP_CONTROLLER` (already coop-gated) and the framework's auto-dispatched
  `coop_playerJustDied`/`coop_playerJustLeft` callbacks — no edits to shared files.

Optional future refactor (NOT needed for these maps): the plan's proposed generic
`setupEscortVehicle` Pattern-B helper in `coop_mod/vehiclehandler.scr` (currently a stub) would let
t2l2 and m1l3b/c share the 16-seat code instead of the copy here. Documented for the main session;
do NOT block on it.

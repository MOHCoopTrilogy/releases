# ARCHIVE - e2l1 (Kasserine glider) open items

Moved out of `docs/OPEN.md` on 2026-08-07 to bring that file back under its 45 KB ceiling.
**Nothing here is closed** - these are still-open items from the 2026-08-03 e2l1 round, parked
because they are one map and no longer the active front. The shipped half of that batch is in
[HISTORY.md](../HISTORY.md) (search e2l1). Move an item back into OPEN.md when work resumes.

## e2l1 glider crash-landing — post-crash arrival sequence (spec, not built)

**User spec, 2026-08-03.** Deliberately queued BEHIND the glider FX fix (bug-1301). Do not start
until the windscreen-crack / explosion-FX issue is closed.

The user supplies the spawn points for the other players; the mod supplies the arrival experience:

1. **Every** player gets the freeze/eject beat, not just those aboard at crash time.
2. Additional cover objects spawned at the crash site.
3. Everyone spawns with **dizziness + suppression** post-FX for a few seconds after the crash.

What already exists, so this is not built from zero:

| piece | state | anchor |
|---|---|---|
| per-player freeze + "Hold USE to eject" | works, but only for players present AT the crash | `maps/e2l1/gliderride.scr::coop_handlePlayerGliderEject` |
| per-player glider cameras | works, incl. mid-ride joiners | `::coop_spawnGliderCamera` + `::coop_startGliderSpawnManager` |
| suppression post-FX | shipped | `r_ppSuppress` |
| dizzy post-FX | shipped | `r_ppDizzyChroma`, `RB_HZMDizzyAmount()` (`renderergl2/tr_postprocess.c`) |
| post-crash spawn origin | **MISSING** — no `coop_respawnOrigin` anywhere in `maps/e2l1/*.scr`; a death after the crash falls back to default coop spawn logic | — |

**The actual gap** is (a) the eject loop in `handleCrash` iterates `$player` once, so anyone who
spawns later never gets `coop_handlePlayerGliderEject`, and (b) nothing assigns a crash-site spawn
origin. Both need solving together, or late arrivals appear at the map default with no arrival beat.

## e2l1 glider — remaining items after the 2026-08-03 fix round

Shipped and awaiting playtest: TIKI glass frame-keyword fix (bug-1301), position-driven flak volley
(bug-1301), restored cut pilot line GP1306 + its missing `maps "e2l1 "` spec, and six bullet-hit
sound aliases that had never been defined (bug-1303).

Still open, with what each actually requires — none are one-line content edits:

| item | state of investigation | what it needs |
|---|---|---|
| **glider smoke** | NOT root-caused. The `cloudy` / `cloudy_descent` tagemitters ARE declared (`CG4Aglider.tik:98-163`), `emitteron cloudy` IS in the idle anim's client block (`:199`), `gliderIdle` IS threaded (`gliderride.scr:967`), and `vsssource.spr` resolves via `scripts/sprites.shader` with no log complaint. So the wiring looks correct and the reason it is invisible is unknown — possibly a gl2 tagemitter regression. **Do not ship a guess**; diagnose against gl1 first. |
| **suppression / blur on hits** | root-caused, NOT content-fixable | `r_ppSuppress` is rewritten every frame by cgame (`cg_view.c:1958`), so a script `stufftext` cannot hold it. `CG_AddSuppression()` has exactly two triggers: a player health drop, and near-miss bullet zings parsed from real bullet messages (`cg_parsemsg.cpp:953`). A scripted cinematic has neither. Options: (a) scripted incoming fire that genuinely passes near the camera, (b) an engine hook adding a server->client suppression command. (b) pairs naturally with the next cgame ship. |
| **bloodied glider allies** | feasible, content-only | No blood helper exists in `coop_mod/`. `models/fx/bloodspurt.tik` is available (referenced by `buildmode_catalog.scr:1750`), so spawning/attaching blood FX on `$gliderDude1/2` during `cockpitBulletHit` is the path. Check first whether the human TIKs carry blood skin variants, which would be cheaper than attached FX. |
| **Pak guns do not destroy vehicles** | not investigated | User 2026-08-03: the AT guns on e2l1 should be able to destroy the opeltruck and tanks and appear not to. Check the Pak's projectile means-of-death vs the vehicles' immunity list, and whether the vehicles carry `nodamage`. |

## e2l1 — unresponsive truck enemy (statue), NOT from the 2026-08-03 batch

User: "a random bad guy that is not taking any shots or reacting to them at all... I think this
guy did come from the truck." Pre-existing: the same log signature appears in sessions BEFORE the
Pak/suppression changes - an actor (entnum 513 in two separate sessions) spamming
`Path not found in 'Actor::MoveToPatrolCurrentNode' ... couldn't find start node` every ~8s from
origin ~(-3238 -4321 -588). A pathless actor cannot move or acquire, which reads as a statue.

Candidates, in order:
1. a truck crewman/driver dropped at a spot with no nav connectivity - `truck_driver_unload`
   DOES restore takedamage/health 75/enable_ai (global/vehicles_thinkers.scr:740-761), so he
   would be killable but brain-dead, matching "doesn't shoot, doesn't react"
2. `$starttruckdriver` / `$truck2driver` - both `nodamage` by retail; `$truck2driver` is also
   RENAMED into `$truck2crew` (enemySet160.scr:211) so crew-wide ops hit a nodamage man
3. an `ai_off` AA-gun guard whose wake trigger never fired

Next session: live rcon probe while the user stands next to him (entnum, targetname, health,
takedamage, ai state), THEN fix at the right layer. Do not guess-fix.

## e2l1: last tank (P40, FinalBattle) "no explosion animation" (unverified chain)
tank_killed (global/vehicles_thinkers.scr:1281) plays explode_tank + spawn_fx
models/emitters/explosion_tank.tik + swaps to It_V_CarroP40_Des; no script error and no VEHZOMBIE
in the session log at the death moment, and $p40_des_hull exists in the e2l1 BSP. So the chain
looks intact - need user detail: did the wreck model appear (swap worked, only the fireball is
underwhelming -> compare emitters/explosion_tank.tik vs fx/fx_tank_explosion.tik used at :1032)
or did the live tank just vanish/stop?

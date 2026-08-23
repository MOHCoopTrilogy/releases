# Breakthrough e3l1–e3l4 — 16-Player Coop Conversion Report

Date: 2026-06-24. Scope: source edits to `hzm-mohaa-coop-mod/maps/e3l1*`, `e3l2*`, `e3l3*`,
`e3l4*` only. No pk3 rebuild, no game launch, no GOG files touched. All edits ASCII / no BOM /
no stray tokens (verified). Helpers used are pre-existing (`replace.scr`, `main.scr`).

## Headline findings
- **e3l3 was NOT blocked by a missing coop hook.** The real blocker is a **parse-killer typo**:
  `maps/e3l3/e3l3_AB41.scr:463` used `]end` instead of `}end`, silently aborting the entire AB41
  ride file at compile. That file owns `GetOnPathVehicle`, `StartJumpThread`, `FinishJumpThread`,
  etc. — i.e. the whole "ride the AB41 and jump off to win" mechanic. With the file dead, the AB41
  never drove, `level.playerjumped` stayed 0, and the map always took the `missionfailed` branch
  (e3l3.scr:91). The "missing panzer TIKs / C crash" in the plan is a separate asset concern; the
  script-side blocker is this one byte. **Fixed.**
- All four maps already had the mandatory hook (`waitthread coop_mod/main.scr::main`) and the coop
  spawn gate (`waitForPlayer`). The remaining work was per-element 16-player scaling + the parse fix.
- **No `parm.other/owner == $player` trigger gates exist in any e3 map** — the highest-risk SP
  pattern is simply absent. Player-activated mechanics use `global/DistanceUse.scr` (any-player
  use) and BSP `waittill trigger` (any-player touch), which are already coop-correct.

---

## e3l1 (City / British HQ / Medic Jeep Escort)
**SP assumptions found / status:** Well-integrated already. Medic jeep ride is NPC/path-driven;
boarding uses `DistanceUse.scr` -> `level.playerJeepGunner` (whoever boards), not bare `$player`.
The header's "JeepRidePart3 MISSION STUCK" note refers to dismount via `level.playerJeepGunner`,
which is already converted; `PlayerGetOut`/`jeepUseLoop` waits are NULL/health-guarded so they
cannot deadlock if the gunner dies/leaves. Main-flow `waitthread` objectives (`DoObjectiveFindBritHQ`,
`DoObjectiveGetOnJeep`, `DoMedicRide`) all use any-player gates (`waitWithinDistance`,
`DistanceUse`, `replace.scr::nodamage/takedamage/turnto/lookat`, `$HQTrigger waittill trigger`).
`level.rideDone`/`level.medicGo` are set by BSP-trigger threads (JeepSpeed/JeepRidePart3), not by
player input — no init hang.

**Changes (file:line):**
- `maps/e3l1/BritHQ.scr:53` — removed a **stray backtick** (`$aagun.destroyed = 1\``), a latent
  token error in the `skipobjFindBritHQ` dev-skip branch.
- `maps/e3l1/BritHQ.scr:49` — dev-skip warp `$player.origin = ...` -> `playersWarpto` (all players).

**Objective semantics:** 5 linear objectives via `global/objectives.scr` (engine `addobjective`
auto-replicates to all 16). Reach/escort gates are any-player. No change needed.

**Verify in harness:** loads clean; medic jeep ride completes; HQ trigger fires for any player;
`$nextleveltrigger` -> `missioncomplete e3l2`.

**Risks:** Low. Health-scale tweak (`SetPlayerHealthScale`) is explicitly skipped in coop
(e3l1.scr:258) — players ride at normal health (acceptable). Existing.

---

## e3l2 (N.Africa Town / Modello Cannons / POWs)
**SP assumptions found / status:** The previously-fixed 0x92 parse bytes (objectives.scr:8,
prisoner_section_1.scr:456) are confirmed clean and ASCII. `objectives.scr::InitObjectives` loads
and registers the 4 ObjMgr objectives. Cannon destruction uses `global/MountGunOrPlantCharge.scr`
+ `setusable`/`douse $player` (the standard coop mount path used by working AA maps) — any player
can mount/plant; the `level.num_cannons_remaining` counter is level-global (shared).
`PlayerUseKeyThread` (e3l2.scr:207) polls only host `$player.useheld` BUT its outputs
(`level.player_use_just_pressed` / `_held`) are **set and never read anywhere** — dead bookkeeping,
left as-is (harmless).

**Changes (file:line):**
- `maps/e3l2.scr:339` — `startsniper2` hard-targeted `$sniper2 favoriteenemy $player[1]`; replaced
  with closest-active-player (`replace.scr::player_closestTo $sniper2`, NULL-guarded fallback to
  default AI targeting). Sniper no longer ignores 15 players to chase player[1].

**Objective semantics:** ObjMgr 4 objectives (findPOWs / killModellos "[N Remaining]" counter /
protectPOWs / escape) — engine-replicated. **protectPOWs fail path is coop-correct:** `mustLive`
(prisoner_section_1.scr:453) does `self waittill death` on the **prisoner NPC** ($prisoner thread
mustLive), not on a player — so one *player* death never fails the mission; only the protected NPC
dying fails it (intended shared loss), via `replace.scr::missionfailed` (respawn-aware). Distance
checks already converted to `withinDistanceOf` (any player).

**Verify in harness:** 4 objectives render for all players (was the dead-byte symptom); destroy all
3 Modello cannons (counter decrements); prisoner escort to truck; `NextLevel` -> `missioncomplete e3l3`.

**Risks:** Low. `PlayerDismountCannon` (cannons.scr:260) sets `$player.origin` (host) on dismount —
a non-host dismounter is positioned via the shared global `MountGunOrPlantCharge.scr` mount handler
(out of e3 scope, used identically by passing AA maps). The `warp_to_section` debug block
(e3l2.scr:84-149) is cvar-gated dev-only (host-only teleports there are acceptable).

---

## e3l3 (N.Africa / K5 Railguns / AB41 ride) — was "blocked"
**Root cause of "blocked":** `maps/e3l3/e3l3_AB41.scr:463` `]end` parse-killer (see Headline).
Hook + waitForPlayer + `replace.scr::missionfailed` were already present.

**Changes (file:line):**
- `maps/e3l3/e3l3_AB41.scr:463` — **`]end` -> `}end`** (the blocker). File now compiles; brace/bracket
  balance verified.
- `maps/e3l3/e3l3_AB41.scr` `StartJumpThread` (~151) — jump prompt polled only host `$player.useheld`
  and aborted on host death. Rewrote to accept the use-key from **any** active player and to `End`
  only when **no** player is alive (so the ride can't deadlock when player[1] is dead/spectating).
- `maps/e3l3/e3l3_AB41.scr` `StartJumpThread` eject (~188, ~205) — `$AB41 douse $player` and the
  post-jump `$player.origin/viewangles` (host-only) fanned out over all active players, so the
  occupant **and** any ride-alongs are lifted clear of the imminent explosion (staggered Z to avoid
  telefrag).
- `maps/e3l3/e3l3_AB41.scr` `FinishJumpThread` (~220) — the "didn't jump" punish-damage looped over
  all active players instead of host only; the protective `$player nodamage` (~255) replaced with
  `replace.scr::nodamage` (protects all players during the scripted finale).
- `maps/e3l3.scr:29` — corrected dead path `gags/e3l3_ab41.scr` (does not exist) ->
  `maps/e3l3/e3l3_AB41.scr` (debug `startonAB41` branch; latent bug).
- `maps/e3l3.scr:174` — guarded `$player heal 1` behind `if(!level.gametype)`.
- `maps/e3l3.scr` (end) — added empty `coop_playerJustSpawned/Left/Respawned` stub labels (the other
  three e3 maps have them) to silence "Could not find label" spam (the callback-registry fix in
  player.scr is owned by the main session and not yet deployed).

**Objective semantics:** 3 objectives via `global/objectives.scr` (replicated). Convoy/railgun
destruction is damage-based (any player); compass updates are any-player BSP `waittill trigger`.
**Win gate:** `level.playerjumped != 0` -> `missioncomplete e3l4`, else `missionfailed`. The jump
flag is now set when any living player presses use in the AB41.

**Verify in harness:** map LOADS (was the open question); AB41 boards via `DistanceUse`, drives the
path; jump prompt accepts use from any player; `FinishJumpThread` doesn't kill ride-alongs;
`level.playerjumped==1` -> `missioncomplete e3l4`. Watch the AB41 as a single-seat vehicle: only the
boarding player drives/guns it; the other 15 fight on foot / ride along (acceptable on-rails design).

**Risks:** Medium. The AB41 is inherently a one-occupant on-rails vehicle (engine `douse`/turret
slots). I made the *mission-completion and eject* robust for 16 players, but did not build a
seat-rotation system (out of scope; no helper exists yet). If the lone occupant dies mid-ride before
the jump prompt, the AB41 keeps auto-driving and the jump prompt will accept any other living player
who is near/aboard — verify this empirically (it depends on whether a respawned player can re-`douse`
the moving AB41). The asset/precache "missing panzer TIK" crash flagged in the plan is separate and
out of script scope.

---

## e3l4 (N.Africa Castle / Bunkers / Radio Tower / Airstrike) — campaign end
**SP assumptions found / status:** Best-integrated of the four. Full 8-objective linear chain via
`global/objectives.scr`; bunker defends are timer/volume-based (scale fine, more players = easier);
reach/use gates are any-player (`DistanceUse $deskradio` for airstrike confirm; BSP `waittill
trigger`). Jeep intro NPCs (`$jeepdriver`/`$jeeppassenger`) decorate the start jeep — players are not
seated. The Outro is the campaign-end cinematic: `cuecamera` is global (Outro.scr:165/343/390/436/483)
which is acceptable for a mission-ending cut (all 16 watch together); every `$player.origin=` in the
Outro is gated behind `if (level.freeCam == 1)` (dev roam mode, off in play).

**Changes (file:line):**
- `maps/e3l4.scr:146` — guarded `$player heal 1` behind `if(!level.gametype)`.
- `maps/e3l4.scr` `UpdateRegroupInCastleObjective` (~241) & `UpdateGoToRadioObjective` (~257) — the
  compass breadcrumb was computed from `$player` (host) only via `FindClosestNodeOnPath`. Now anchors
  on the closest active player to the path node (`replace.scr::player_closestTo`, NULL-fallback to
  player[1]). Cosmetic-but-better; cannot deadlock.

**Objective semantics:** 8 objectives, engine-replicated. Deliver/defend/reach all any-player or
volume/timer. Airstrike confirm = any player uses the desk radio (`DistanceUse`). `GiveMedals` +
`DoOutro` are global (campaign end). No completion-semantics change needed.

**Verify in harness:** loads clean; objective chain advances 1->8; bunker defends survivable with N
players; radio confirm works for any player; Outro cinematic plays for all; campaign-end handoff.

**Risks:** Low. Two pre-existing items I did NOT change (out of scope / acceptable):
1. `maps/e3l4/Outro.scr:484` has a **stray `*`** after `thread CameraKeeper $TheCam $camera "cam1"*`.
   It is in `sceneFour` of the end-credits cinematic (only reached at campaign completion). It looks
   like a typo but the map ships/loads in SP, so the parser tolerates the trailing token; flagging
   for a maintainer rather than risk-editing the end cinematic. **Recommend a maintainer remove it.**
2. `RollTheCredits` (Outro.scr:528-546) does `$player waittill sounddone` (host) x4 — could stall the
   very-end credits if host disconnects mid-credits. Campaign is effectively over; very low risk.

---

## Cross-map parse hygiene (verified after edits)
- Non-ASCII / BOM scan of all e3 main + sub scripts: **clean** (0 findings).
- Brace/bracket balance verified on every edited file; the lone `End` I added in
  `e3l3_AB41.scr:169` is a control-flow statement (not a block closer), correctly accounting for the
  off-by-one `{`/`}` count.
- All new `exec`/`thread` targets resolve to existing labels (`replace.scr::player_closestTo`,
  `::nodamage`, `main.scr::playersWarpto`) — confirmed present.
- No compound `&&`/`||` split across lines added; no bare negative as first token in parens; vector
  Z-offset precomputed into a local to avoid inline-arithmetic-in-vector risk.

## Top things to verify in the harness (priority order)
1. **e3l3 LOADS at all** (`]end` fix) — grep MAPTEST_LOADED for e3l3; previously the AB41 file was
   dead-on-arrival.
2. **e3l3 mission completes** — the AB41 ride boards, drives, jump prompt accepts any player's use,
   `level.playerjumped==1` -> `missioncomplete e3l4` (not the `missionfailed` branch).
3. **e3l2 objectives render** for all players (4 ObjMgr objectives) and the 3 Modello cannons can be
   destroyed by any player (counter reaches 0).
4. **e3l2 protectPOWs** fails only if the prisoner NPC dies (not on a player death).
5. **e3l1 medic jeep escort** completes (any player can board; dismount detaches) and chains to e3l2.
6. **e3l4** objective chain 1->8 advances and the Outro cinematic + campaign handoff fire for all.

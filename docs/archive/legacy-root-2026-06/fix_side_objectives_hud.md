# Side-Objectives HUD Fixes (staged; no rebuild/launch)

Date: 2026-06-24. Source of evidence: `side_objectives_hud_review.md` (Gaps A/B + P2).
The two side lines live on dedicated cvars `coop_so1` (Eliminate the High-Ranking
Officer) / `coop_so2` (Destroy the Radio to Stop Reinforcements), pushed via
`coop_obj_push` and registered by `coop_obj_register` (coop_mod/objectives.scr).

All edits ASCII, no BOM, single-line conditions, no bare-negative-in-parens,
`$player` 1-indexed. Brace/paren balance preserved (the only file showing a raw
count imbalance, global/objectives.scr 103/102, is a pre-existing artifact of
commented-out `{` lines; my added block is self-balanced).

Files touched: `coop_mod/objectives.scr`, `global/objectives.scr`,
`coop_mod/officer.scr` (comment only). obj_setup.cfg / obj_reset.cfg NOT modified
(fix done in script instead of stripping the per-spawn reset, which keeps the
primary-slot reset behavior intact).

---

## FIX 1 - LATE-JOIN (Gap A, all maps)

Problem: `coop_obj_push` only iterates `$player` during the register + ~13s
reassert window. The native late-join replay
`global/objectives.scr::coop_objectivesResetForPlayer` (574-681) replays only
`level.coopObjective1..8` and knows nothing about `coop_so*`, so a player who
joins after ~13s gets blank side lines.

Approach:
- `coop_mod/objectives.scr` new thread `coop_obj_repush_player local.ent`
  (objectives.scr:88) re-pushes the CURRENT side-objective state (active vs
  completed, honoring `coop_sideObjOfficerDone` / `coop_sideObjRadioDone`) to a
  single entity, via a new single-target push helper `coop_obj_push_one`
  (objectives.scr:59). No-ops unless `level.coop_sideObjReg == 1`.
- `global/objectives.scr::coop_objectivesResetForPlayer` end (objectives.scr:687)
  now calls `waitthread coop_mod/objectives.scr::coop_obj_repush_player local.entity`
  right after the primary-slot replay. This is the native late-join hook, so any
  joiner gets the side lines restored after obj_reset.cfg/obj_setup.cfg blanked them.

## FIX 2 - RESPAWN (Gap B, officer maps)

Problem: every (re)spawn execs obj_setup.cfg which re-seeds `coop_so* = ""/0`;
obj_reset.cfg never restores them; the reassert loop has already finished by a
mid/late respawn, so the side lines go blank until (if ever) a completion push.
`coop_objectivesResetForPlayer` does NOT fire on respawn (it is gated on the
per-player `coopObjectiveSetupDone` flag / a `$player.size` change), so FIX 1's
hook alone does not cover respawn.

Approach (coop_mod/objectives.scr):
- New per-level watcher `coop_obj_player_watcher` (objectives.scr:112) loops
  `level waittill playerspawn` (same engine event the existing
  events.scr::playerSpawnEvent uses) and, on each (re)spawn, threads a 1s-delayed
  re-push to the just-spawned player (`coop_obj_repush_delayed`, objectives.scr:129,
  uses `self`). The 1s delay lets the per-player obj_setup.cfg/obj_reset.cfg reset
  run first so our re-push wins the race.
- Watcher is started from `coop_obj_register` (objectives.scr, after the reassert
  thread). Guarded by `level.coop_sideObjWatcher` so it starts once per level, and
  it only ever runs on maps where the lines were registered.

This single watcher also reinforces FIX 1 (a fresh connect fires playerspawn too),
but the explicit `coop_objectivesResetForPlayer` hook is kept as the primary
late-join path requested in the review.

## FIX 3 - NO-BOSS GATING (P2)

Problem: `coop_obj_register_delayed` (threaded from coop_officer.scr/coop_officer_init
~line 116) pushed both lines ACTIVE BEFORE the officer policy / `coop_feature_boss`
gate (~line 121 / officer.scr:340). So the 7 no-officer maps (t1l1, t2l2, t3l2,
training, + marginal m2l2b, t1l3) showed two permanently-ACTIVE, never-completable
side lines.

Approach (coop_mod/objectives.scr `coop_obj_register_delayed`, objectives.scr:140):
- Before registering, compute the SAME officer outcome officer.scr uses:
  - `exec coop_mod/officer.scr::coop_officer_policy` -> if `"none"`, end (no lines).
  - `exec coop_mod/officer_positions.scr::getAnchor` to populate
    `level.coop_feature_boss`, then if `== 0`, end (no lines).
- Both `coop_officer_policy` and `getAnchor` are pure/idempotent (only read
  `level.coop_mapname` and set level vars), so calling them early matches what
  officer_init computes later. Confirmed boss-disabled maps (t1l1 policy "none";
  t2l2 / t3l2 `coop_feature_boss=0`) now show NO side lines instead of stuck-active.
- Fallback for marginal maps: if a boss DOES end up spawning, the spawn-time
  `coop_obj_register` call already at officer.scr:475 still fires, sets
  `coop_sideObjReg=1`, shows the lines, and starts the watcher. So nothing is lost
  on maps that find dynamic infrastructure.
- The stale officer.scr:111-116 comment ("registered unconditionally / harmless
  no-op") was updated to describe the new self-gating; no code change at the call
  site (the gating lives inside `coop_obj_register_delayed`).

---

## Cross-file gating note

The gating decision is replicated in two places by design:
- `coop_obj_register_delayed` self-gates on `policy != "none" AND coop_feature_boss != 0`.
- `coop_obj_repush_player` (used by both the late-join hook in global/objectives.scr
  and the respawn watcher) gates on `level.coop_sideObjReg == 1`.

`coop_sideObjReg` is only set to 1 inside `coop_obj_register`, which is reached
either via the now-gated delayed path OR the boss-actually-spawned path
(officer.scr:475). Net effect: on no-officer maps the side lines never appear and
the late-join/respawn re-push is inert, so FIX 3's "don't show un-completable
lines" guarantee holds for late joiners and respawners too, not just the initial
push. No edits were made to obj_setup.cfg/obj_reset.cfg (the per-spawn reset of the
primary slots is left untouched; the side lines are restored in script instead).

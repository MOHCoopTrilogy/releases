# Coop Side-Objectives HUD Integration Audit (read-only)

Date: 2026-06-24. Scope: every campaign map .scr under `hzm-mohaa-coop-mod/maps/`
(m-series, e-series, t-series; 55 map scripts total). No edits made.

## How the side-objectives HUD actually wires (verified in source)

The side objectives are the two fixed lines **"Eliminate the High-Ranking Officer"**
(coop_so1) and **"Destroy the Radio to Stop Reinforcements"** (coop_so2). They are
NOT registered through the native/`add_objectives` coop path at all — they live on
dedicated cvars `coop_so1`/`coop_so2` with their own HUD widgets, decoupled from the
8 primary slots after the 2026-06-22 trilogy review.

Wiring chain (all confirmed):

1. Every map `.scr` calls `waitthread coop_mod/main.scr::main` — verified for **all 55**
   map scripts (grep: 55/55, all live `waitthread`, none commented).
2. `coop_mod/main.scr::main:121` unconditionally `thread coop_mod/officer.scr::coop_officer_init`.
3. `coop_officer.scr::coop_officer_init:116` unconditionally `thread coop_mod/objectives.scr::coop_obj_register_delayed`
   — **this runs BEFORE the officer spawn-policy decision at line 121**, so the two side
   lines are pushed ACTIVE on EVERY map regardless of whether the boss ever spawns.
4. `coop_mod/objectives.scr::coop_obj_register` (objectives.scr:66) pushes both lines via
   `coop_obj_push` (objectives.scr:32), which loops `$player` and `stufftext`s
   `set coop_soNd/a/s/<text>` directly. Then `coop_obj_reassert` (objectives.scr:85)
   re-pushes 5x over 10s to beat the per-player `obj_setup.cfg` reset race.
5. HUD draw: `ui/coop_objectives.urc` lines 618-736 define `coop_MiObjSecHdr`,
   `coop_MiObjSec1*` (gated `enabledcvar coop_so1d`), `coop_MiObjSec2*` (`coop_so2d`).
   o-key toggle path (`coop_obj` cvar, obj_add/obj_rem) is global, not per-map.
6. Completion: `coop_obj_officer_done` is threaded from the officer death monitor
   (officer.scr:2018), `coop_obj_radio_done` from radio destruction (officer.scr:2591).

### Conclusion on "integration"
Because the push is driven entirely by the shared `main -> coop_officer_init` chain that
every map runs, **the side-objectives HUD is structurally integrated on all 55 maps** —
there is no per-map registration to forget, and no map relies on the spawn-only auto-push
(the dedicated coop_so cvars are pushed explicitly via coop_obj_push). So criteria 1/2/3
(registered via coop path / HUD draws / explicitly pushed) pass uniformly.

The real findings are two systemic (non-per-map) gaps plus a content-correctness issue on
the maps where the boss/radio never actually spawn:

- **SYSTEMIC GAP A — late join / late respawn.** `coop_obj_push` only reaches players
  connected during the register + 5x-reassert window (~map start to ~+13s). It is NOT
  re-driven afterward. The native primary-objective late-join replay
  (`global/objectives.scr::coop_objectivesResetForPlayer`, lines 574-681) ONLY replays
  `level.coopObjective1..8` — it has **no knowledge of coop_so1/coop_so2**. So a player
  who connects (or whose client first runs obj_setup.cfg) after ~+13s gets blank side
  lines for the rest of the map. Affects EVERY map equally.
- **SYSTEMIC GAP B — respawn reset not re-pushed.** On every (re)spawn the client execs
  `obj_setup.cfg` -> which seeds `coop_so* = "" / d=0` and execs `obj_reset.cfg`
  (verified). `obj_reset.cfg` resets the primary slots but does nothing for coop_so. The
  only thing that re-fills coop_so after a mid/late respawn is the 5x reassert loop, which
  has already finished by then. So a player who dies and respawns after ~+13s loses the
  side lines until (if ever) a completion push fires. Affects EVERY officer map.
- **CONTENT ISSUE C — un-completable side lines on no-boss maps.** Since the register runs
  before the policy/feature/anchor gates, maps where the officer & radio never spawn still
  show both lines permanently ACTIVE (never status 3). Not a HUD-rendering bug, but the two
  side objectives are unachievable there.

## Per-map table

Columns: Reg via coop path? (side objs use dedicated coop_so push — "Yes(coop_so)") |
Side objs present? (always the 2 fixed lines) | Pushed to HUD? | HUD renders incl. late join? |
Status. Boss/radio actually spawns = policy != none AND coop_feature_boss=1 AND a usable
anchor/infrastructure exists. "OK*" = HUD fully integrated and lines are completable;
the systemic late-join/respawn gap (A/B) applies to ALL rows.

| Map | Reg via coop path | Side objs present | Pushed to HUD | Renders incl. late join | Status | Note |
|-----|-----|-----|-----|-----|-----|-----|
| m1l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; authored anchor; completable |
| m1l2a | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (alarm); lines active until loud |
| m1l2b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m1l3a (M1L3a.scr) | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m1l3b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m1l3c | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (radio destroy alarm) |
| m2l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m2l2a | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (alarm_system) |
| m2l2b | Yes(coop_so) | Yes | Yes | Push window only | UNCOMPLETABLE-IF-NOBOSS | no anchor (MARGINAL) -> dynamic fallback may skip boss; lines may stay active forever |
| m2l2c | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m2l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor (boss re-enabled) |
| m3l1a | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m3l1b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m3l2 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m3l3 (M3L3.scr) | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m4l0 | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (trigger1 alarm) |
| m4l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m4l2 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m4l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m5l1a | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m5l1b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m5l2a (M5L2A.scr) | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m5l2b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor (boss re-enabled) |
| m5l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor; wave_mask 63 |
| m6l1a | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l1b (M6L1b.scr) | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l1c | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (alarm) |
| m6l2a | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l2b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l3a | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l3b | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l3c | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (alarm) |
| m6l3d | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| m6l3e | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor |
| e1l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; afrika; anchor |
| e1l2 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; afrika; anchor |
| e1l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; afrika; anchor |
| e1l4 | Yes(coop_so) | Yes | Yes | Push window only | OK* | deferred (Ship.scr alarm); afrika |
| e2l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; wehr; anchor |
| e2l2 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; wehr; anchor |
| e2l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; wehr; anchor (verify_ingame) |
| e3l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; wehr; anchor |
| e3l2 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor. Side objs are decoupled from the e3l2 slot-9 primary false-positive (separate content bug) |
| e3l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; wehr; anchor |
| e3l4 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor (boss re-enabled) |
| t1l1 | Yes(coop_so) | Yes | Yes | Push window only | UNCOMPLETABLE | policy "none" + coop_feature_boss=0: officer/radio NEVER spawn -> both lines stuck ACTIVE all map |
| t1l2 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; wehr; anchor (verify_ingame) |
| t1l3 | Yes(coop_so) | Yes | Yes | Push window only | UNCOMPLETABLE-IF-NOBOSS | no anchor (MARGINAL); dynamic fallback may skip boss -> lines may stay active forever |
| t2l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor (verify_ingame) |
| t2l2 | Yes(coop_so) | Yes | Yes | Push window only | UNCOMPLETABLE | coop_feature_boss=0 (halftrack): officer/radio never spawn -> lines stuck ACTIVE |
| t2l3 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor (verify_ingame) |
| t2l4 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; anchor (verify_ingame) |
| t3l1 | Yes(coop_so) | Yes | Yes | Push window only | OK* | combat; russ; anchor (verify_ingame) |
| t3l2 | Yes(coop_so) | Yes | Yes | Push window only | UNCOMPLETABLE | coop_feature_boss=0 (T-34): officer/radio never spawn -> lines stuck ACTIVE |
| training | Yes(coop_so) | Yes | Yes | Push window only | UNCOMPLETABLE-LIKELY | training map; no anchor + no real German combat infra -> boss skipped, lines stuck active (cosmetically wrong on a tutorial) |

## Actionable list

No map is **MISSING the HUD push** (criteria 1/2/3 pass on all 55 — there is no
per-map registration to fix). The actionable items are the two systemic gaps and the
no-boss content issue:

### P1 — Systemic late-join / respawn re-push gap (affects ALL 55 maps)
- File/lines: `hzm-mohaa-coop-mod/coop_mod/objectives.scr:60-101` (register + 5x/10s
  reassert is the ONLY thing that ever sets coop_so cvars), and
  `hzm-mohaa-coop-mod/global/objectives.scr:574-681`
  (`coop_objectivesResetForPlayer` replays only `level.coopObjective1..8`, never coop_so).
- Missing: there is no late-join hook for the side lines. A player who joins or respawns
  after the ~13s reassert window (`coop_obj_reassert` runs 5x at 2s = ~10s, started ~3s in)
  sees blank coop_so lines. `ui/coop_objectives/obj_setup.cfg` (verified) re-seeds
  `coop_so* = ""/0` on every spawn, and `obj_reset.cfg` (verified) does not restore them.
- Evidence: `coop_obj_push` iterates `$player` only at call time; no `$player.size`-change
  watcher exists for coop_so (contrast the primary-slot watcher
  `global/objectives.scr::coop_objectivesManage:360-369`).

### P2 — Un-completable side lines where boss/radio never spawn (4 confirmed + 3 likely)
The register (objectives.scr:66) pushes both lines ACTIVE before officer.scr applies its
policy/feature/anchor gates (officer.scr:116 precedes the gate at 121), so on no-boss maps
the lines display permanently active and can never reach status 3.
- **Confirmed (boss hard-disabled):**
  - `t1l1` — policy "none" (officer.scr:38) + coop_feature_boss=0 (officer_positions.scr:390)
  - `t2l2` — coop_feature_boss=0 (officer_positions.scr:327)
  - `t3l2` — coop_feature_boss=0 (officer_positions.scr:350)
- **Likely (no authored anchor -> dynamic fallback can skip boss via the
  "no valid spawn infrastructure" / <1000u guard, officer.scr:309-336):**
  - `m2l2b`, `t1l3` (both listed MARGINAL/no-anchor, officer_positions.scr:33)
  - `training` (no anchor entry, no real German combat actors; boss almost certainly skipped)
- Fix shape (NOT applied): either gate `coop_obj_register_delayed` on the same
  policy/feature_boss result officer_init computes, or only register the lines once the
  officer actually spawns (the `coop_obj_register` call at officer.scr:475 already covers
  the spawn case). Today the early line-116 call defeats that.

### Notes / non-issues
- t-series is fully integrated now (all t* maps call main and push coop_so) — the
  "t-series needs main inserted" memory note (level_scripts_sh_bt) is **stale**.
- The e3l2 "objective slot 9 never renders" item is a primary-objective content bug and is
  fully decoupled from the side objectives (which use coop_so cvars), confirming the
  e3l2_objectives_false_positive note.
- Deferred maps (m1l2a, m1l3c, m2l2a, m4l0, m6l1c, m6l3c, e1l4) correctly show the side
  lines active from map start and complete them if/when the map goes loud and the officer
  dies; if the level never goes loud, they fall into the same P2 "stuck active" cosmetic
  state.

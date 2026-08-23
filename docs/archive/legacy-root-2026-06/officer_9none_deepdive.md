# Officer Policy: Deep-Dive of the 9 "NONE" Missions

Date: 2026-06-24
Files edited (ONLY, all under C:\mohaa-coop-dev):
- `hzm-mohaa-coop-mod/coop_mod/officer.scr` (central `coop_officer_policy` table)
- `hzm-mohaa-coop-mod/maps/m1l2a.scr` (go-loud flag set)
- `hzm-mohaa-coop-mod/maps/m1l3c.scr` (go-loud flag set)
- `hzm-mohaa-coop-mod/maps/m4l0.scr` (go-loud flag set)

Read-only references used: `officer_spawn_policy.md`, `coop_mod/officer.scr`
(`coop_officer_policy` / `coop_officer_wait_goloud` / `coop_officer_init`),
`coop_mod/officer_positions.scr` (feature toggles + authored anchors),
memory `level_scripts_aa.md` / `level_scripts_sh_bt.md`, and each map's actual
`maps/<map>.scr` (+ subdir scripts).

`coop_officer_wait_goloud` already polls `level.alarm==1`, `level.alarmSounded==1`,
and `level.alarmactive==1`. DEFERRED maps only need ONE of those flipped at the
go-loud moment; no officer.scr change beyond moving the map to the DEFERRED list.

## Final per-mission classification

| Map | Old | New | Why |
|-----|-----|-----|-----|
| e1l4  | NONE | **DEFERRED** | Papers/disguise ship infiltration that goes LOUD when cover is blown. The ship alarm path already sets the polled flags. Has an authored anchor. No map edit needed. |
| m1l2a | NONE | **DEFERRED** | Disguise saluting-checkpoint raid; goes loud when a spotlight catches an un-disguised player and the alarm spawns responders. Wired. Has an authored anchor. |
| m1l3c | NONE | **DEFERRED** | Lighthouse disguise/stealth with a DESTROY objective (all comms equipment). Destroying it spawns the combat AI = go-loud. Wired. Has an authored anchor. |
| m2l2a | NONE | **DEFERRED** | U-boat-pen disguise + "Destroy the Naxos Prototype"; shared `global/alarm_system.scr` sets `level.alarm=1` on alarm trip. No map edit needed. Boss still gated off by `coop_feature_boss=0`/no-anchor, but the bucket is now correct. |
| m2l3  | NONE | **COMBAT** | Train-station escape. Map sets `level.alarm=1` UNCONDITIONALLY at spawn (m2l3.scr:75) and combat is immediate; it is not a stealth-to-loud mission. Boss still gated off by `feature_boss=0`. |
| m5l2b | NONE | **NONE (keep)** | "TANK DRIVE 2": player is in `$playertank` for the entire map. Pure vehicle, no on-foot combat phase. |
| m4l0  | NONE | **DEFERRED** | Secret farmhouse papers raid ("Take secret German documents"); the German siege enemy AI activates at `trigger1`. Wired. Boss still gated off by `feature_boss=0`/no-anchor, bucket corrected. |
| t1l1  | NONE | **NONE (keep)** | Plane-ride + barn-crash cinematic intro; vanilla Spearhead with no stealth structure and no readable go-loud alarm flag. Pure-cinematic exemption per user rule. |
| e3l4  | NONE | **COMBAT** | Bunker defense / "Repel the Attack" from the first objectives; combat from the start (the medals + DoOutro are only the very end). Mis-marked. Boss still gated off by `feature_boss=0`, bucket corrected. |

Result: NONE 2 (m5l2b, t1l1), DEFERRED 5 of the 9 (e1l4, m1l2a, m1l3c, m2l2a, m4l0),
COMBAT 2 (m2l3, e3l4). (Plus the two pre-existing DEFERRED maps m6l1c/m6l3c are unchanged.)

## DEFERRED go-loud events + flag-set locations

- **e1l4** -> go-loud = ship cover blown / alarm sounded.
  Flag already set by the MAP (no edit): `maps/e1l4/Ship.scr` `AlarmSounded:`
  sets `level.alarmSounded = 1` (line 392) and `level.alarm = 1` (line 395).
  Also pre-set on the PreShip detection path: `maps/e1l4/PreShip.scr:460` `level.alarm = 1`.
- **m1l2a** -> go-loud = cover blown (spotlight catches player -> alarm responders spawn).
  Flag set (NEW): `maps/m1l2a.scr:3136` `level.alarm = 1` at the top of `spawnalarmguy:`.
- **m1l3c** -> go-loud = destroy objective complete (all 4 comms equipment destroyed -> combat AI `spawn 007`).
  Flag set (NEW): `maps/m1l3c.scr:290` `level.alarm = 1` in `radio_objective:` (the all-destroyed `else` branch).
- **m2l2a** -> go-loud = base alarm trips.
  Flag already set by the shared system (no edit): `global/alarm_system.scr:662` `level.alarm = 1`
  in `alarm_system_master`. m2l2a runs `alarm_system_setup` (m2l2a.scr:84).
- **m4l0** -> go-loud = German siege (enemy AI enabled at the farmhouse trigger).
  Flag set (NEW): `maps/m4l0.scr:243` `level.alarm = 1` in `trigger1:`.

## Maps that received a NEW go-loud trigger wire

1. `maps/m1l2a.scr:3136`
2. `maps/m1l3c.scr:290`
3. `maps/m4l0.scr:243`

(e1l4 and m2l2a became DEFERRED with NO map edit because their existing scripts
already set a polled flag.)

## Notes / caveats

- For m2l2a, m4l0 (DEFERRED) and m2l3, e3l4 (COMBAT) the boss is still suppressed at
  spawn time by `coop_feature_boss=0` (and/or a missing authored anchor) in
  `officer_positions.scr`. Those feature toggles were left untouched (out of scope);
  only the policy bucket was corrected so intent is centrally readable. If a boss is
  later wanted on any of them, flip `coop_feature_boss` and add an authored anchor.
- t1l1 remains NONE rather than COMBAT specifically because it is pure-vanilla SH with
  no `level.RideOver`/alarm flag the framework can read; reclassifying it COMBAT would
  let the dynamic fallback try to spawn during the cinematic. Kept NONE per the
  user's pure-cinematic exemption.

## Parse hygiene verified

- `officer.scr`: ASCII-only (no bytes >0x7F), no UTF-8 BOM. Braces balanced 506/506.
  No per-line paren imbalance in the edited policy function (lines 30-75); the small
  raw whole-file paren delta is pre-existing comment/string text only.
- All three map edits are single ASCII lines, no BOM, compound conditions untouched,
  no bare-negative-in-parens, `$player` usage unchanged.

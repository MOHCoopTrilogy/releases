# Officer-Boss Spawn Policy (Central, by mapname)

Date: 2026-06-24
File changed (ONLY): `hzm-mohaa-coop-mod/coop_mod/officer.scr`
Companion data: `officer_coverage_audit.md`, `coop_16player_scripted_events_plan.md`,
memory `level_scripts_aa.md` / `level_scripts_sh_bt.md`.

## Problem this fixes

`coop_mod/main.scr:121` threads `coop_officer_init` on every coop map, and the init used a
dynamic-anchor fallback. On stealth/cinematic maps the boss dropped into the player's scripted
location and opened fire during the intro. Observed live on **e1l4** (papers/disguise ship
infiltration): officer spawned at the truck-stop and shot during the cinematic intro.

## Design (all in officer.scr, keyed by `level.coop_mapname`)

A new `coop_officer_policy` function returns one of three buckets; `coop_officer_init` acts on it
BEFORE any intro/ride wait:

- **NONE** -> `end` immediately, no boss. Stealth/disguise/papers + pure cinematic/escort maps.
- **DEFERRED** -> hold in `coop_officer_wait_goloud` (bounded 600s) until a readable level alarm flag
  flips, then proceed. On timeout it behaves as NONE for that session.
- **COMBAT** -> proceed through the (now strengthened) intro-timing gate + anchor-distance guard.

Unclassified maps default to **COMBAT** (working maps keep their officer).

### How COMBAT timing + anchor distance are enforced

1. **Intro timing (existing + new):**
   - Existing `inTruckCamera` gate (waits while player[1] is in the truck camera).
   - Existing `level.flags[ridecomplete]` gate (m1l1 vehicle-ride; bounded 90s + 8s settle).
   - **NEW** generalized `level.RideOver` gate (BT/SH scripted ride/intro flag; bounded 90s + 4s
     settle). NIL on maps that don't use it, so behavior is unchanged there.
2. **Anchor-distance guard (NEW, all spawn paths):** after the anchor/alarmspawner/enemy-fallback
   chooses `base_pos`, a hard floor of **1000u from `level.coop_mapStartOrigin`** is enforced. If the
   chosen position is closer than that to the player start / vehicle-stop / intro location, the boss
   is skipped rather than spawned on the players. (Dynamic paths already required >=1500u; this also
   catches a mis-authored or too-close authored anchor.)

### Go-loud signal source (DEFERRED)

`coop_officer_wait_goloud` polls only level globals the MAP script already sets (no map edits):
`level.alarm == 1`, `level.alarmSounded == 1`, or `level.alarmactive == 1`.

## Per-map bucket table

Legend: bucket = NONE / DEFERRED / COMBAT. "feature_boss" = value still set in
officer_positions.scr (unchanged by this work; the policy gate runs first and is authoritative).

### AA m-series

| Map | Bucket | Why |
|-----|--------|-----|
| m1l1 | COMBAT | Combat; ridecomplete intro gate already handled |
| m1l2a | NONE | Disguise saluting-checkpoint mission; no readable go-loud flag |
| m1l2b | COMBAT | Combat |
| m1l3a | COMBAT | Combat (D-Day beach); intro + distance guard apply |
| m1l3b | COMBAT | Combat |
| m1l3c | NONE | Lighthouse disguise/stealth mission; no readable go-loud flag |
| m2l1 | COMBAT | Combat |
| m2l2a | NONE | feature_boss=0 (ship-interior escape); kept off |
| m2l2b | COMBAT | Combat (dynamic fallback) |
| m2l2c | COMBAT | Combat |
| m2l3 | NONE | feature_boss=0 (no spawn infra -> TGA crash risk) |
| m3l1a | COMBAT | Combat |
| m3l1b | COMBAT | Combat |
| m3l2 | COMBAT | Combat |
| m3l3 | COMBAT | Combat (dynamic fallback) |
| m4l0 | NONE | Secret farmhouse vehicle escort (feature_boss=0) |
| m4l1 | COMBAT | Pilot escort combat; distance guard keeps boss off pilot path |
| m4l2 | COMBAT | Combat |
| m4l3 | COMBAT | Paper Chase alarmer map; treated COMBAT (see DEFERRED note below) |
| m5l1a | COMBAT | Combat |
| m5l1b | COMBAT | Combat |
| m5l2a | COMBAT | Combat (dynamic fallback) |
| m5l2b | NONE | Tank-drive (feature_boss=0) |
| m5l3 | COMBAT | Tank bridge defense |
| m6l1a | COMBAT | Combat |
| m6l1b | COMBAT | Combat (dynamic fallback) |
| m6l1c | DEFERRED | MP44 facility stealth-alarm; waits on `level.alarm==1` |
| m6l2a | COMBAT | Comms blackout alarmer map; treated COMBAT (see DEFERRED note) |
| m6l2b | COMBAT | Combat |
| m6l3a | COMBAT | Fort Schmerzen alarmer map; treated COMBAT (see DEFERRED note) |
| m6l3b | COMBAT | Combat |
| m6l3c | DEFERRED | Stealth-alarm; waits on `level.alarm==1` |
| m6l3d | COMBAT | Combat |
| m6l3e | COMBAT | Combat |

### BT e-series

| Map | Bucket | Why |
|-----|--------|-----|
| e1l1 | COMBAT | Jeep intro -> front-line battle; intro gate + distance guard |
| e1l2 | COMBAT | Combat |
| e1l3 | COMBAT | Combat |
| **e1l4** | **NONE** | **Papers/disguise ship infiltration. Canonical fix: never spawns, never fires during the truck-stop cinematic intro.** |
| e2l1 | COMBAT | Glider cinematic intro -> Normandy combat; intro gate applies |
| e2l2 | COMBAT | Combat |
| e2l3 | COMBAT | Normandy village combat (dynamic fallback) |
| e3l1 | COMBAT | Medic-escort + combat |
| e3l2 | COMBAT | Combat (officer hook only runs once map gets coop init) |
| e3l3 | COMBAT | Combat (rotation-blocked by asset crash, separate issue) |
| e3l4 | NONE | Campaign-ender medals/outro (feature_boss=0) |

### SH t-series

| Map | Bucket | Why |
|-----|--------|-----|
| t1l1 | NONE | Plane-ride + barn-crash cinematic (feature_boss=0) |
| t1l2 | COMBAT | Combat |
| t1l3 | COMBAT | Combat; has a story-colonel NPC (see note) |
| t2l1 | COMBAT | Combat |
| t2l2 | COMBAT | feature_boss=0 (halftrack); policy COMBAT but feature gate keeps boss off |
| t2l3 | COMBAT | Bastogne wave defense |
| t2l4 | COMBAT | Town combat |
| t3l1 | COMBAT | Berlin streets combat |
| t3l2 | COMBAT | feature_boss=0 (T-34 drive); feature gate keeps boss off |

Note: t-series scripts also rely on the `coop_feature_boss=0` toggles already in
officer_positions.scr for their vehicle maps (t2l2, t3l2) - that check still runs after the policy
gate, so those stay boss-free even though their *policy* bucket is COMBAT.

## Bucket counts (51 maps classified)

- **NONE: 9** -> e1l4, m1l2a, m1l3c, m2l2a, m2l3, m5l2b, m4l0, t1l1, e3l4
- **DEFERRED (wired to a readable go-loud flag): 2** -> m6l1c, m6l3c
- **COMBAT: 40** -> everything else (default for unclassified)

e1l4 is explicitly NONE.

## DEFERRED maps whose go-loud hook still needs wiring (follow-up; MAP-script edits)

These AA maps are stealth-first but expose NO single clean go-loud level global that officer.scr can
poll today, so they are currently classified NONE/COMBAT rather than truly deferred. A follow-up
(allowed to edit the MAP script) should set one of `level.alarm` / `level.alarmSounded` /
`level.alarmactive` to 1 at the go-loud moment; once set, just move the map to the DEFERRED list in
`coop_officer_policy` and it works with no further officer.scr change.

- **m1l2a** (disguise, saluting checkpoint) - currently NONE. Add a go-loud flag set where the
  disguise is blown / first alarm in `maps/m1l2a.scr` (the disguise/combat trigger). Then -> DEFERRED.
- **m1l3c** (lighthouse disguise) - currently NONE. Same: set a go-loud flag at cover-blown / climb
  combat start in `maps/m1l3c.scr`. Then -> DEFERRED.
- **m4l3** (Paper Chase, `exec global/alarmer.scr`) - currently COMBAT (it is a full combat
  infiltration with an authored anchor). If a quieter approach is wanted, expose
  `level.alarmactive=1` from the alarmer path and move to DEFERRED.
- **m6l2a** (Comms Blackout, alarmer) - currently COMBAT. Set a go-loud flag in the alarmer hook to
  defer; otherwise COMBAT is acceptable (it is an open combat map after the radio shacks).
- **m6l3a** (Fort Schmerzen, alarmer) - currently COMBAT. Same option as m6l2a.

m6l1c and m6l3c are already DEFERRED and need NO follow-up: their map scripts already set
`level.alarm = 1` on go-loud, which `coop_officer_wait_goloud` polls.

## Parse hygiene verified

- ASCII-only (no bytes >0x7F), no UTF-8 BOM.
- Braces balanced 503/503; code-only parens balanced 557/557 (raw count difference is comment/string
  text only).
- Compound `&&` conditions kept on one line; no bare-negative-in-parens; `$player` 1-indexed.
- Return-by-`end <value>` convention matches existing helpers (coop_model_for, coop_wave_allowed,
  getAnchor).

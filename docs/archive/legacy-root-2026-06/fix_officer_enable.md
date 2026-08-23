# Officer-Enable Batch (outstanding item #3) + e2l3 Inconsistency Fix

Date: 2026-06-24
Files edited (ONLY): `hzm-mohaa-coop-mod/coop_mod/officer.scr`,
`hzm-mohaa-coop-mod/coop_mod/officer_positions.scr`
Staged edits only. No rebuild/launch. All work done centrally, keyed by `level.coop_mapname`.
No individual map scripts touched.

## What was wrong

`coop_officer_policy` (officer.scr) classifies maps correctly, but several maps that WARRANT
a boss never actually spawned one because either:
- `coop_feature_boss = 0` hard-disabled the boss in officer_positions.scr (Stage-final gate), or
- the map had no authored anchor AND its dynamic fallback could not find a safe spawn (e/t maps
  have no $alarmspawner/$enemyspawner, and e2l3 has no `ai_german` map entities at all), or
- the policy bucket itself was NONE (m5l2b).

Plus the e2l3 inconsistency: the positions-file exclude header listed e2l3 as SKIP, but
`coop_feature_boss` was never set to 0 for it -> the boss was actually LIVE on the German-actor
fallback. Intent did not match behavior.

## How spawning is gated (recap)

`getAnchor` (officer_positions.scr) sets `coop_feature_boss` + the anchor per map.
`coop_officer_init` (officer.scr): policy gate (NONE/DEFERRED/COMBAT) runs first, then intro/ride
timing gates, then anchor -> alarmspawner -> farthest-German fallback, then a hard
>=1000u-from-`coop_mapStartOrigin` guard, then the `coop_feature_boss==0` skip.
To make a boss reliably spawn a map needs: policy != NONE, `coop_feature_boss=1`, and a spawn
position >=1000u from player start (authored anchor satisfies this deterministically).

## Maps now spawning an officer

### Group 1 - re-enabled (were `coop_feature_boss=0` or policy NONE)

| Map | Policy bucket | feature_boss | paradrop | Anchor authored | Why |
|-----|---------------|--------------|----------|-----------------|-----|
| m5l2b | NONE -> **COMBAT** | 0 -> **1** | 0 (kept) | (-7160 -1906 -94) (already present) | Tank auto-drives in coop; players on foot, global/ai.scr spawns infantry -> warrants officer. ~14800u from start (7632 -2544 -80). |
| m2l2a | DEFERRED (kept) | 0 -> **1** | 0 (kept) | (-2548 -6652 -488) | U-boat destroyer escort; deep-deck kreigsmarine combat. DEFERRED holds boss until alarm_system.scr sets level.alarm=1. ~3600u from start (-4816 -3880 -36). z_ref=-488. |
| m4l0 | DEFERRED (kept) | 0 -> **1** | 0 (kept) | (-3984 7320 120) | Secret farmhouse raid; escort auto-drives, 36 enemyspawners. DEFERRED holds until trigger1 sets level.alarm=1. ~13100u from start (-5816 -5824 -176). z_ref=100. |
| m2l3 | COMBAT (already) | 0 -> **1** | 0 (kept) | (856 6928 -256) | Combat-from-start train-station escape (level.alarm=1 at spawn). Authored anchor removes the old spectator-origin TGA-crash risk that justified the SKIP. ~3100u from start (-2152 6176 -60). z_ref=-256. |
| e3l4 | NONE -> **COMBAT** (policy already routed e3l4 to combat) | 0 -> **1** | 0 (kept) | (-1536 4520 1336) | Combat-from-start fortress fight; medals/outro only at the very end. Real ai_german cluster in the elevated fortress (Z~1336-1632). ~10400u from start (320 -5632 368). z_ref=1400. |

Note: m5l2b is the only one whose policy bucket changed (NONE->COMBAT). m2l2a/m4l0 stay DEFERRED
(correct for their stealth/disguise start - boss appears once the map goes loud). m2l3/e3l4 were
already routed to COMBAT by the existing policy block; only their feature_boss flag + anchor were
missing.

### Group 2 - bucket-C anchors authored (boss was already enabled, just relied on dynamic fallback)

| Map | Policy bucket | feature_boss | Anchor authored | Reinf zone | Why |
|-----|---------------|--------------|-----------------|------------|-----|
| m3l3 | COMBAT | 1 | (3096 3984 -40) | (-3130 2827 -103) | Comrade in Arms, 44 ground German AI. Deterministic distant cluster anchor; ~9900u from start (-6800 3248 16). |
| m5l2a | COMBAT | 1 | (2152 934 458) | (1288 166 194) | A Bridge Too Far, 15 ground enemyspawners. ~5300u from start (3320 -4144 240). |
| m6l1b | COMBAT | 1 | (-2560 -4632 1816) | (-5629 3135 1856) | All Roads Lead to Rome, 17 ground AI at world Z~1816. ~8600u from start (1360 2952 1816). |
| m1l3a | COMBAT | 1 | (-3296 -3162 58) | (-2296 -2978 26) | Death Factory, 8 enemyspawners. D-Day-beach intro + playerGlue; deterministic deep anchor beats dynamic. Lower-Z cluster; ~6800u from start (3352 -6176 -88). |
| e2l3 | COMBAT | 1 | (5483 -2312 -220) | (5716 -2591 -220) | Inconsistency fix (see below). German mortar emplacement east of the village. ~11100u from start (-1688 6208 136). z_ref=-220. |

All Group-2 anchors carry `coop_officer_verify_ingame=1` (estimates pending in-game QA), matching
the existing convention for thin/elevated pools and e/t estimates.

## e2l3 inconsistency - resolution

Resolved per the audit's PREFERRED option: AUTHORED an anchor rather than disabling.
- The old exclude header said SKIP; the code never set `coop_feature_boss=0`, so the boss was
  live on the German-actor fallback. Now e2l3 has an explicit COMBAT entry with
  `coop_feature_boss=1` (default) + a deterministic authored anchor, so intent == behavior.
- e2l3 has NO `ai_german` map entities (only allied airborne are authored; Germans are spawned at
  runtime by the level script), which is why the dynamic fallback was unreliable. The anchor is
  pinned to a real German-held position: the granatwerfer mortar emplacement at (5483 -2312 -220)
  (companion mortar at (5716 -2591 -220) used as the reinf zone).
- The positions-file exclude header was rewritten so e2l3 is no longer listed as SKIP.

## Parse hygiene (verified)

- ASCII-only (no bytes >0x7F), no UTF-8 BOM, no em-dash, in both files.
- officer.scr: braces 506/506; code-only parens 571/571 (raw 691/694 difference is comment text only).
- officer_positions.scr: braces 59/59; parens 249/249 (code-only 160/160).
- All new conditions single-line; vectors like (3096 3984 -40) keep their bare negative inside the
  vector literal (allowed); no bare-negative-in-parens conditions added.
- All anchors satisfy the >=1000u-from-player-start guard (closest is m2l3 at ~3100u).

## Net result

Officers now spawn on **10** additional maps:
- Re-enabled: m5l2b, m2l2a, m4l0, m2l3, e3l4.
- Bucket-C deterministic anchors: m3l3, m5l2a, m6l1b, m1l3a, e2l3.

t1l1 remains the only SKIP (cinematic, feature_boss=0). m2l2b / t1l3 remain MARGINAL (unchanged,
per audit - need a play-test call).

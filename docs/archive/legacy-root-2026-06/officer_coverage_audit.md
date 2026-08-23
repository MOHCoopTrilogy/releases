# Officer-Boss Spawn Coverage Audit — HZM Coop Mod

Date: 2026-06-23
Scope: All campaign maps (AA m-series, BT e-series, SH t-series).
Method: Cross-referenced `coop_mod/officer_positions.scr` (authoritative anchor table),
`coop_mod/officer.scr` (spawn logic + fallbacks), `coop_mod/main.scr` (hook), the
`coop_maptest_list` rotation, `maps/*.scr`, `map_entities/SUMMARY.md`, and the level-script
surveys.

---

## How the officer system actually gates per map (key to the whole audit)

1. **The hook is unconditional.** `coop_mod/main.scr:121` runs `thread coop_mod/officer.scr::coop_officer_init`
   on *every* map that calls `waitthread coop_mod/main.scr::main`. There is no per-map `if` around it.
2. **Gating is data-driven**, inside `coop_officer_init` (officer.scr) + `getAnchor` (officer_positions.scr):
   - `getAnchor` sets `level.coop_officer_anchor` and `level.coop_feature_boss` per map.
   - officer.scr Stage 0 (officer.scr:80-91) uses the authored anchor if present.
   - If anchor is NIL, it falls through to **Stage 1 dynamic selection**: `$alarmspawner`
     (officer.scr:99-130) → farthest living German actor on the same floor (officer.scr:132-191).
   - If *no* anchor AND *no* alarmspawner AND *no* valid German actor → it **skips the boss**
     rather than spawning at the player (officer.scr:184-190), to avoid the renderer TGA crash.
   - `coop_feature_boss == 0` (officer.scr:195-198) hard-disables the boss regardless of anchor.
3. **Therefore three states exist per map:**
   - **Authored anchor** (listed in officer_positions.scr with coords) → deterministic boss. ("HAS — authored")
   - **No entry / anchor NIL, boss not disabled** → boss spawns via **dynamic fallback** if the map
     has alarmspawner/enemyspawner/German actors. ("HAS — dynamic" when infra exists; "MISSING" only if it should be authored)
   - **`coop_feature_boss = 0`** → boss intentionally off. ("EXEMPT")

A map without an explicit officer_positions.scr entry is **not automatically without an officer** —
it gets the dynamic fallback. The genuinely-missing/at-risk cases are maps that rely on dynamic
fallback but warrant a deterministic authored anchor, plus maps that are silently disabled.

---

## Summary Table

| Map | Series | Anchor? | feature_boss | TIER | Determination | Rationale |
|-----|--------|---------|--------------|------|---------------|-----------|
| m1l1 | AA | Y | 1 | 2-ENEMY | HAS (authored, verify) | Anchor (-1488 -2704 192); thin ground pool flagged |
| m1l2a | AA | Y | 1 | 2-ENEMY | HAS (authored) | Anchor (762 4234 12) |
| m1l2b | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (4496 -4152 -288) |
| m1l3a | AA | **N** | 1 | 2-ENEMY | HAS (dynamic) → consider authoring | 8 enemyspawners; dynamic works but D-Day beach + playerGlue intro is risky |
| m1l3b | AA | Y | 1 | 2-ENEMY | HAS (authored) | Anchor (-2712 7006 -6) |
| m1l3c | AA | Y | 1 | 2-ENEMY | HAS (authored, verify) | Anchor (-4948 -4868 728), high Z |
| m2l1 | AA | Y | 1 | 2-ENEMY | HAS (authored) | Anchor (1264 1592 632) |
| m2l2a | AA | N | **0** | 3-AI | EXEMPT-SKIP (questionable) | Disabled "listed in exclude header"; but 15 ground German AI exist |
| m2l2b | AA | **N** | 1 | 3-AI | HAS (dynamic) / borderline | 7 German AI; header marks MARGINAL; small escape map |
| m2l2c | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (1072 -6892 -496) |
| m2l3 | AA | N | **0** | 3-AI | EXEMPT-SKIP | Boss off: no spawner tier, dynamic lands on spectator → TGA crash |
| m3l1a | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (2624 5568 -576) |
| m3l1b | AA | Y | 1 | 3-AI | HAS (authored, verify) | Anchor (1465 -2153 -36), thin pool |
| m3l2 | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (-6731 -6253 -129) |
| m3l3 | AA | **N** | 1 | 3-AI | HAS (dynamic) → should author | 44 ground German AI; full combat map, best AI coverage in game |
| m4l0 | AA | N | **0** | 2-ENEMY(special) | EXEMPT-vehicle | Secret farmhouse vehicle escort; different gameplay model |
| m4l1 | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (-1410 -4852 -232), z_ref override |
| m4l2 | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (-4559 1852 305) |
| m4l3 | AA | Y | 1 | 1-ALARM | HAS (authored) | Anchor (-263 -1066 9), alarmer map |
| m5l1a | AA | Y | 1 | 2-ENEMY | HAS (authored) | Anchor (1672 -2608 -32) |
| m5l1b | AA | Y | 1 | 2-ENEMY | HAS (authored) | Anchor (-2307 -4115 140) |
| m5l2a | AA | **N** | 1 | 2-ENEMY | HAS (dynamic) → should author | 15 enemyspawners, all ground level; full infantry map |
| m5l2b | AA | Y | **0** | 2-ENEMY | EXEMPT-tank | Player-in-tank drive; boss+paradrop off, light waves kept |
| m5l3 | AA | Y | 1 | 2-ENEMY | HAS (authored) | Anchor (429 2036 417), wave_mask 63 |
| m6l1a | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (-801 5479 5464) |
| m6l1b | AA | **N** | 1 | 3-AI | HAS (dynamic) → should author | 17 ground German AI; full combat map |
| m6l1c | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (4530 992 143) |
| m6l2a | AA | Y | 1 | 1-ALARM | HAS (authored) | Anchor (1120 -2784 120) |
| m6l2b | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (5760 6036 50) |
| m6l3a | AA | Y | 1 | 1-ALARM | HAS (authored) | Anchor (-2424 -2568 -560) |
| m6l3b | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (416 -304 -624) |
| m6l3c | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (-776 848 -1016), z_ref override |
| m6l3d | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (568 2096 -1464) |
| m6l3e | AA | Y | 1 | 3-AI | HAS (authored) | Anchor (-6480 -1816 -492) |
| e1l1 | BT | Y | 1 | n/a | HAS (authored) | Anchor (1074 -4992 180); jeep intro window noted |
| e1l2 | BT | Y | 1 | n/a | HAS (authored) | Anchor (4192 4352 192) |
| e1l3 | BT | Y | 1 | n/a | HAS (authored) | Anchor (1720 -960 128) |
| e1l4 | BT | Y | 1 | n/a | HAS (authored) | Anchor (-5920 6224 48); disguise map |
| e2l1 | BT | Y | 1 | n/a | HAS (authored) | Anchor (-3338 -4322 4); glider intro window |
| e2l2 | BT | Y | 1 | n/a | HAS (authored) | Anchor (2352 5456 2576) |
| e2l3 | BT | **N** | 1 | n/a | HAS (dynamic, weak) → should author | Full combat village; header lists e2l3 as SKIP but boss NOT disabled; no spawner entities → relies on German-actor fallback |
| e3l1 | BT | Y | 1 | n/a | HAS (authored) | Anchor (132 5658 36) |
| e3l2 | BT | Y | 1 | n/a | HAS (authored) but **no coop init** | Anchor exists, but e3l2.scr has NO `coop_mod/main.scr::main` → hook never runs |
| e3l3 | BT | **N** | 1 | n/a | EXEMPT-broken/SKIP | No coop init in script; also rotation-SKIPPED (C crash, missing panzer TIKs) |
| e3l4 | BT | N | **0** | n/a | EXEMPT-campaign-end | Medals/DoOutro; also has no coop init at all |
| t1l1 | SH | N | **0** | n/a | EXEMPT-cinematic | Long plane-ride + barn-crash intro |
| t1l2 | SH | Y | 1 | n/a | HAS (authored, untested) but **no coop init** | Anchor exists, but t-series is pure vanilla → hook never runs |
| t1l3 | SH | **N** | 1 | n/a | EXEMPT-marginal/vanilla | Header MARGINAL; vanilla (no hook); already has story colonel NPC |
| t2l1 | SH | Y | 1 | n/a | HAS (authored, untested) but **no coop init** | Vanilla → hook never runs |
| t2l2 | SH | Y | **0** | n/a | EXEMPT-halftrack | Player drives halftrack; boss off |
| t2l3 | SH | Y | 1 | n/a | HAS (authored, untested) but **no coop init** | Vanilla → hook never runs |
| t2l4 | SH | Y | 1 | n/a | HAS (authored, untested) but **no coop init** | Vanilla → hook never runs |
| t3l1 | SH | Y | 1 | n/a | HAS (authored, untested) but **no coop init** | Vanilla → hook never runs |
| t3l2 | SH | Y | **0** | n/a | EXEMPT-T34 | Player in T-34 all map; boss off |

Notes: "verify" = `coop_officer_verify_ingame = 1` flag set. "untested" = t-series anchor TODO estimate.
TIER applies only to m-series (from map_entities/SUMMARY.md). t1l1 has no anchor and no entry except theater resolver + the boss-disable block.

---

## Bucket A — Already have an officer (authored anchor, hook runs)

AA (24): m1l1, m1l2a, m1l2b, m1l3b, m1l3c, m2l1, m2l2c, m3l1a, m3l1b, m3l2, m4l1, m4l2, m4l3,
m5l1a, m5l1b, m5l3, m6l1a, m6l1c, m6l2a, m6l2b, m6l3a, m6l3b, m6l3c, m6l3d, m6l3e.
(m1l1, m1l3c, m3l1b carry a verify-in-game flag for thin/elevated pools — encounter exists, just needs QA.)

BT with working hook (7): e1l1, e1l2, e1l3, e1l4, e2l1, e2l2, e3l1.

**Authored anchor present but hook does NOT currently run** (anchor is dead data until coop init is added to the map script):
- e3l2 — anchor (-1180 5085 47) authored, but e3l2.scr has no `waitthread coop_mod/main.scr::main` (minimal coop integration).
- t1l2, t2l1, t2l3, t2l4, t3l1 — anchors authored (untested estimates) but t-series scripts are pure vanilla; none call coop_mod/main.scr::main, so coop_officer_init never threads.

These are "data ready, plumbing missing." They are *not* in bucket C (the anchor work is done); the
blocker is coop integration of the level script, which is a separate, larger task than authoring an anchor.

## Bucket B — Correctly exempt (boss intentionally off, with reason)

- **m2l3** — `coop_feature_boss=0`. No spawner tier; dynamic fallback would land at the player's
  spectator origin and cause a renderer TGA-load crash (officer_positions.scr:318-322). Correct to skip.
- **m4l0** — `coop_feature_boss=0`. Secret farmhouse *vehicle escort*; gameplay model differs
  (officer_positions.scr:308-311). Correct to skip (vehicle map).
- **m5l2b** — `coop_feature_boss=0`. Player drives a tank the whole map; boss + paradrop disabled,
  light wave set retained (officer_positions.scr:126-131). Correct.
- **e3l4** — `coop_feature_boss=0`. Breakthrough campaign-ender (medals + DoOutro); also has zero
  coop integration. Correct to skip.
- **t1l1** — `coop_feature_boss=0`. Long plane-ride + barn-crash cinematic intro. Correct.
- **t2l2** — `coop_feature_boss=0`. Player drives a halftrack the whole map. Correct (vehicle).
- **t3l2** — `coop_feature_boss=0`. Player in a T-34 the entire (campaign-ending) map. Correct (vehicle).
- **e3l3** — no coop init in script AND rotation-skipped (silent C crash, missing panzer TIKs,
  Issue #18). Effectively exempt until the crash + integration are fixed; not an officer-design call.

Borderline-but-defensible:
- **m2l2a** — `coop_feature_boss=0` with the weak reason "listed in exclude header." Unlike m2l3
  it DOES have 15 ground-level German AI (SUMMARY.md:151-154), so dynamic fallback would likely
  succeed. This is the one disable I'd re-examine — see Ambiguous Cases.
- **t1l3** — header MARGINAL, no anchor, vanilla (no hook). Already has a *story* colonel NPC on a
  scripted path; a second boss could clash thematically. Leave exempt unless the map gets full coop
  integration first.

## Bucket C — MISSING: genuinely warrant an officer, currently rely on dynamic fallback only (ACTIONABLE)

These maps run the officer hook (or would, once integrated) with `coop_feature_boss=1` but have **no
authored anchor**. They lean entirely on dynamic selection. They are normal infantry-combat levels
comparable to maps that already have authored anchors, so they deserve a deterministic, QA'd anchor.
Priority ordering: full AA combat maps first.

1. **m3l3 — Comrade in Arms** (TIER 3, 44 ground German AI — *best AI coverage in the game*).
   Full infantry combat map, no reason to be anchor-less. Dynamic fallback will work but is non-deterministic.
   - Best anchor source: a distant ground German-AI position, e.g. SUMMARY.md sample `(3096 3984 -40)`
     or `(-3130 2827 -103)` (start (-6800 3248 16)); or HZM update spawn `update4=(5287 -873 -404)`.
     Pick the ground cluster farthest from start that satisfies the z_tol (192) filter.

2. **m5l2a — A Bridge Too Far** (TIER 2, 15 enemyspawners, all ground level).
   Standard infantry map with clean authored spawn nodes — ideal for a deterministic anchor.
   - Best anchor source: an enemyspawner origin from SUMMARY.md, e.g. `(2152 934 458)` or
     `(4176 -458 394)` (start (3320 -4144 240), z near 240±200). Use the farthest such spawner ≥1500u from start.

3. **m6l1b — All Roads Lead to Rome** (TIER 3, 17 ground German AI, elevated world Z≈1760).
   Full combat map; the case-variant script `maps/M6L1b.scr:9` confirms the coop hook runs.
   - Best anchor source: distant ground German-AI position, e.g. `(-2560 -4632 1816)` or
     `(-5629 3135 1856)` (start (1360 2952 1816)). Z is ~1816 world; anchor near that band.

4. **m1l3a — Death Factory** (TIER 2, 8 enemyspawners).
   Combat map; coop hook confirmed (`maps/M1L3a.scr:40`). Dynamic fallback will find the enemyspawners,
   BUT the map opens with a D-Day-beach intro and `level.coop_playerGlue = 1`; a deterministic anchor
   placed deep in the level (away from the glued intro) is safer than letting dynamic pick.
   - Best anchor source: lower-Z enemyspawner group, e.g. `(-3296 -3162 58)` / `(-2296 -2978 26)`
     (start (3352 -6176 -88)). Use the lower-Z cluster, farthest from start.

5. **e2l3 — Normandy Village, 82nd Airborne** (full combat map, coop hook present at e2l3.scr).
   The exclude header lists e2l3 as SKIP but `coop_feature_boss` is NOT set to 0 for it — so the boss
   is actually enabled and depends purely on the German-actor fallback (no spawner entities on e-series).
   This is a real infantry village fight that warrants a deterministic anchor; the SKIP-header label is
   inconsistent with the code. Resolve the inconsistency: either author an anchor (preferred) or, if it
   really should be skipped, add `coop_feature_boss=0` so intent matches behavior.
   - Best anchor source: no spawner entities exist (e/t maps have none); capture a ground combat-area
     coordinate in-game (village center), or reuse a known German squad spawn from the level script.
     Until captured, this is verify-in-game like the other e/t anchors.

(Lower priority / conditional in bucket C: **m2l2b** — TIER 3 but only 7 German AI and a short
U-boat *escape* sequence; it currently relies on dynamic fallback and works, but it is small/transitional.
I would NOT author an anchor here without play-testing; closer to exempt-marginal. Listed here only
because, unlike m2l3/m2l2a, its boss is left enabled.)

## Ambiguous / borderline cases (no forced call)

- **m2l2a vs m2l3 (the two disabled M2 maps).** m2l3's disable is well-justified (no infra → crash).
  m2l2a's disable reason is only "listed in exclude header," yet it has 15 ground German AI, so the
  fallback would likely succeed. Trade-off: enabling it gives M2 (Destroyer/U-boat) a boss for parity,
  but these are tight ship-interior escape maps where a 1500-HP boss + waves may not fit the pacing.
  Recommendation: re-test m2l2a with the boss enabled before deciding; low priority.

- **m2l2b** — enabled, no anchor, 7 AI, short escape map. Either author a small anchor or formally
  mark it marginal/exempt for pacing. Needs a play-test call.

- **t1l3** — has an authored *story* colonel NPC already; adding a combat boss risks two "officers."
  Vanilla (no hook) today, so moot until integrated. If integrated later, decide colonel-vs-boss then.

- **The "anchor authored but hook dead" set (e3l2, t1l2, t2l1, t2l3, t2l4, t3l1).** Anchors are done,
  but the level scripts lack `coop_mod/main.scr::main`, so the officer never spawns. These are NOT
  missing-anchor work; they are missing-integration work (a bigger task: add coop init, replace
  `$player stufftext` music, etc.). Flag separately from bucket C so the anchor effort isn't duplicated.

---

## Counts

- **Bucket A (have officer, hook runs): 31** — 24 AA + 7 BT (e1l1-e1l4, e2l1, e2l2, e3l1).
- **Anchor authored but hook not wired (data-ready, integration pending): 6** — e3l2, t1l2, t2l1, t2l3, t2l4, t3l1.
- **Bucket B (correctly exempt): 9** — m2l3, m4l0, m5l2b, e3l4, t1l1, t2l2, t3l2, e3l3, (+m2l2a/t1l3 as defensible-exempt borderline).
- **Bucket C (MISSING — should get an authored anchor): 5 actionable** — m3l3, m5l2a, m6l1b, m1l3a, e2l3
  (+m2l2b as a conditional 6th pending play-test).

### Key evidence (file:line)
- Unconditional hook: `coop_mod/main.scr:121`.
- Dynamic-fallback chain + skip-if-no-infra: `coop_mod/officer.scr:80-203`.
- `coop_feature_boss=0` disables: officer_positions.scr lines 128, 269, 292, 305, 310, 315, 321, 326.
- Maps with no anchor entry but boss enabled (fall through to dynamic): m1l3a, m3l3, m5l2a, m6l1b,
  m2l2b, e2l3, t1l3 (absence from the if/else chain in officer_positions.scr:78-329).
- Coop hook confirmed in the four "precache-only" maps: maps/M1L3a.scr:40, maps/M3L3.scr:23,
  maps/M5L2A.scr:8, maps/M6L1b.scr:9 (corrects the level_scripts_aa memory claim that they have no level script).
- e/t maps have no $alarmspawner/$enemyspawner entities (level_scripts_sh_bt survey) → e-series fallback
  is German-actor only.

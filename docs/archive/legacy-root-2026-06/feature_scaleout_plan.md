# HZM Coop — Officer Boss Feature Scale-Out Plan

Research-only plan (no code changes). Goal: deploy the full officer/wave/radio/icon/binoculars/paradrop/voice feature set onto **every** campaign map across AA (m-series), Breakthrough (e-series), and Spearhead (t-series) — including maps that currently have zero coop content — using a single data-driven injector instead of bespoke per-map code.

Date: 2026-06-22. Sources cited inline (file:line).

---

## 0. TL;DR

The architecture is **already 80% data-driven** and does not need a redesign — it needs three targeted upgrades plus integration plumbing for two campaigns.

- **Injection is already universal.** `coop_mod/main.scr::main` line 121 calls `thread coop_mod/officer.scr::coop_officer_init` unconditionally. Every map that runs `waitthread coop_mod/main.scr::main` gets the officer for free. There are **zero per-map officer hooks** (confirmed: `m4l3.scr` contains no `officer` reference).
- **Spawn anchors are already a config table.** `coop_mod/officer_positions.scr::getAnchor` is a flat `if/else-if` chain keyed on `level.coop_mapname`, returning `coop_officer_anchor` + `coop_officer_reinf_zone` + Z-override flags. It already covers 26 AA maps, 9 e-maps, and 7 t-maps. officer.scr has a 3-stage fallback (authored anchor → `$alarmspawner` → farthest living German actor → player-relative) so **any unlisted map still works dynamically**.
- **What's missing (the actual work):**
  1. **Theater-aware content.** Officer model (officer.scr:173-176) and every wave-spawn function (officer.scr:268, 835, 921, 1022, 1090, 1165, 1308, 1511, 1719) hardcode AA WaffenSS/elite/Wehrmacht models. On e1 (Afrika) and Russian-theater t3 maps these are wrong/immersion-breaking and risk loading models absent from the active pak set.
  2. **Per-map feature toggles.** No schema exists to disable boss/paradrop/binoculars on vehicle/rail/cinematic maps. Today everything fires everywhere the injector runs.
  3. **Two campaigns aren't wired.** **No t-series .scr files exist in the mod** (confirmed via glob — t-series is pure vanilla). e3l2/e3l3/e3l4 have minimal/no `coop_mod/main.scr::main`. e-series precache files **do not** `exec coop_mod/precache.scr` (confirmed: `e1l1_precache.scr`, `e2l2_precache.scr` headers). So the injector physically cannot run on those maps yet.

**Headline numbers:** 0 maps need a new officer hook (injector is central). ~17 maps need an **integration** edit (insert `waitthread coop_mod/main.scr::main` and/or fix precache) before the existing injector can fire: 9 t-series + e3l2/e3l3/e3l4 + 4 e-series precache files + 1 e2l2 partial. ~6 maps need an **in-game anchor capture** still (flagged `verify_ingame` in the table). All others are already deployed or fall back dynamically.

---

## 1. Current Deployment Inventory

### 1.1 How the officer is injected (single point)

`coop_mod/main.scr::main`:
- Line 93-96: single-player early-out (`thread spWaitForPlayer; end`) — officer never runs in true SP.
- Line 121: `thread coop_mod/officer.scr::coop_officer_init` — **the one and only injection site**.

`coop_officer_init` (officer.scr:6-167) then:
- Waits for `$player`, handles truck-intro camera, waits 25s otherwise (officer.scr:14-27).
- Picks reference player (officer.scr:30-47).
- **Stage 0** — `exec coop_mod/officer_positions.scr::getAnchor` (officer.scr:57). If an authored anchor exists, use it.
- **Stage 1** — `$alarmspawner` scan, Z-filtered, farthest ≥1500u (officer.scr:74-105).
- **Fallback** — farthest living `level.coop_actorArray["german"]` on same floor, else player-relative (officer.scr:108-162).
- Threads `coop_radio_init` + `coop_officer_spawn` (officer.scr:164-166).

**Consequence:** the officer is map-agnostic by construction. The "scale-out" is therefore not about adding hooks — it's about (a) making sure every map executes `coop_mod/main.scr::main`, and (b) feeding the injector correct per-map data.

### 1.2 Maps that currently run the system

Any map whose level script contains `waitthread coop_mod/main.scr::main` will run the officer today.

- **AA m-series:** all 30 existing `.scr` maps integrate (per `level_scripts_aa.md`), including the m3l2 top-level anomaly. The 4 precache-only maps (m1l3a, m3l3, m5l2a, m6l1b) have no level script → injector never runs.
- **BT e-series:** e1l1–e2l1 full; e2l2/e2l3 partial; e3l1 full; **e3l2/e3l3 minimal (no main.scr::main)**; **e3l4 none** (per `level_scripts_sh_bt.md`).
- **SH t-series:** **none** — all 9 are pure vanilla, no coop integration whatsoever.

### 1.3 Anchor availability (from officer_positions.scr + SUMMARY.md)

Already authored in `officer_positions.scr::getAnchor`: 26 AA maps, 9 e-maps (e1l1-e1l4, e2l1, e2l2, e3l1-e3l3), 7 t-maps (t1l2, t2l1-t2l4, t3l1, t3l2).
Explicitly excluded (anchor NIL → dynamic): `m4l0, e2l3, e3l4, t1l1, m2l3, m2l2a` (SKIP); `m2l2b, t1l3` (MARGINAL); `m1l3a, m3l3, m5l2a, m6l1b` (NO_SCRIPT_HOOK).

---

## 2. Choosing Officer-Spawn Locations on No-Content Maps

### 2.1 The three-source ladder (already implemented, keep it)

1. **Authored coords** in `officer_positions.scr` — best, used when present.
2. **`$alarmspawner` / `$enemyspawner`** entity scan at runtime — nav-guaranteed. Per `SUMMARY.md`: 3 maps have alarmspawners, 12 have enemyspawners. **Caveat:** `level_scripts_sh_bt.md` confirms **no e/t map has either entity** (the `$enemyspawnertrigger` on t1l3/e3l3 is a BSP path node, not a spawner). So entity-scan only helps AA.
3. **Farthest living German actor** (`level.coop_actorArray["german"]`) — works anywhere AI exists, Z-filtered. This is the universal floor.
4. **Player-relative** — last resort (officer.scr:159-161).

### 2.2 Recommendation for genuinely empty maps

Prefer **authored hardcoded coords** captured in-game (viewpos/noclip workflow from `coordinate_units_reference.md`) over runtime scans, because:
- e/t maps have no spawner entities, so scan tier is unavailable there.
- The actor-array fallback can place the officer wherever the deepest AI happens to be — fine for combat density but unpredictable for the radio-bomb/binoculars staging.
- The table already encodes Z-overrides (`coop_officer_z_ref`, `coop_officer_z_tol`) for the known hard cases (m4l1 entry-shaft, m6l3c deep map, m5l3/m6l3d elevated bands) — exactly the per-map knowledge a scan can't infer.

Maps still needing capture are flagged **`verify_ingame = 1`** today: m1l1, m1l3c, m3l1b, t2l1 (and t-series broadly, since they can't even run yet). Treat every t-series anchor and every `verify_ingame` entry as **"needs in-game anchor capture"** before ship.

### 2.3 Theater / pak availability gotchas (critical)

OpenMOHAA loads `main/` + the fs_game dir's paks. Per `reinforcement_variation_reference.md`, OpenMOHAA exposes **all** of `main/` + `mainta/` + `maintt/` content regardless of mode — so models are technically reachable. **But** the safe assumption for a shipped mod is:

- **fs_game = maintt (current build target, per build.ps1):** loads `main` + `maintt`. AA WaffenSS/elite models live in `main/Pak0`; Afrika + Wehrmacht_colonel live in `maintt/pak1`. Both reachable. **`mainta` is NOT loaded** — anything exclusive to mainta would be missing. (Confirmed in `ai_model_catalog.md`: `german_Wehrmacht_colonel.tik` is in mainta AND maintt, so OK under maintt.)
- **Wehrmacht spelling trap** (`ai_model_catalog.md`): filename is `german_wehrmact_*` (8 chars, no 'h' before 't'). officer.scr:174-175 already uses the correct typo'd lowercase form — preserve it byte-for-byte; never let an editor "correct" it.
- **e-series precache gap** (`level_scripts_sh_bt.md`, confirmed): e*_precache.scr do **not** `exec coop_mod/precache.scr`. Officer/paradrop/binoculars assets (radio, cardtable, c47fly, parachute_actors, smoke, dog, stuka) are therefore **not precached** on BT maps → late-load hitches or missing emitters. Must be fixed (see §5).
- **t-series precache gap:** none of t*_precache.scr reference coop at all.

---

## 3. Standardized Data-Driven Deployment

The position table proves the pattern works. Extend it from "where" to "where + who + what's enabled" by widening the existing `getAnchor` into a single per-map **profile** record, and adding a theater resolver + roster table that the wave spawners read.

### 3.1 Schema: per-map profile (extend officer_positions.scr)

Set these `level.*` vars inside the existing `getAnchor` if/else chain (same flat-chain technique already mandated by the file's comment at officer_positions.scr:19 — "exec runs in caller's context so per-map thread dispatch does not work"). One new vector + a few ints per map:

| Var | Type | Meaning | Default if NIL |
|---|---|---|---|
| `coop_officer_anchor` | vector | officer/radio anchor (existing) | dynamic ladder |
| `coop_officer_reinf_zone` | vector | wave spawn zone (existing) | `officer - fwd*500` |
| `coop_officer_z_ref` | float | Z reference for filters (existing) | mapStart Z |
| `coop_officer_z_tol` | float | Z floor tolerance (existing) | 192 |
| `coop_officer_verify_ingame` | int | needs QA capture (existing) | 0 |
| **`coop_theater`** | string | `"aa"`/`"afrika"`/`"wehr"`/`"russ"` — drives model resolver | derive from mapname prefix |
| **`coop_feature_boss`** | int | spawn the officer at all | 1 |
| **`coop_feature_waves`** | int | reinforcement waves enabled | 1 |
| **`coop_feature_paradrop`** | int | allied paradrop reward | 1 |
| **`coop_feature_binoc`** | int | binoculars bombing-run reward | 1 |
| **`coop_feature_voice`** | int | contextual combat VO | 1 |
| **`coop_wave_mask`** | int | bitmask of allowed wave types 0-7 | all (0xFF) |

`coop_theater` default rule (cheap, no table needed for most maps): mapname starts `e1`→`afrika`; `t3`→`russ` (Berlin/Soviet); `m*`→`aa`; everything else (`e2`,`e3`,`t1`,`t2`)→`wehr`. Override per-map only where a mission breaks the rule.

### 3.2 Schema: theater → model resolver (new thread in officer.scr)

Replace the hardcoded model literals with a resolver keyed on `level.coop_theater`. One helper returns the right TIK for a role:

```
coop_model_for role:           // role = "officer"|"infantry"|"elite"|"grenadier"|"sniper"|"mg"|"at"|"handler"
  aa     -> waffenss_officer / waffenss_shutze / elite_sentry / wehrmact_grenadier / wehrmact_soldier ...
  afrika -> Afrika_officer    / afrika_private / Afrika_NCO    / Afrika_grenadier_nowrap / afrika_private ...
  wehr   -> wehrmact_officer  / waffenss_shutze / wehrmact_NCO / wehrmact_grenadier / wehrmact_soldier ...
  russ   -> wehrmact_officer  / waffenss_shutze (German garrison in Berlin) — keep German; players are Soviet
  handler/dog: german_hund_hundpatrol + german_shepherd (theater-agnostic, AA pak, reachable everywhere)
```

Model paths per theater are fully enumerated in `ai_model_catalog.md` and `reinforcement_variation_reference.md`. Dog/handler/stuka/artillery are theater-agnostic. The officer skin pool (officer.scr:172-176) becomes a per-theater pool (Afrika has only one officer skin; AA/Wehr keep their 3-4).

### 3.3 Schema: wave roster (theater-tuned)

The wave dispatcher (`coop_call_reinforcements`, officer.scr:723-782) already does `local.r = randomint 8` over 8 types. Gate it by `coop_wave_mask` so vehicle/cinematic maps can drop e.g. dogs+AT, and reroll if the rolled bit is masked off. Each spawn function pulls models via `coop_model_for` instead of literals. No new wave *types* required — the 8 existing types (elite, infantry, sniper, grenadier, stuka, artillery, AT, dogs) cover all theaters; only the skins change.

### 3.4 The generic injector flow (mostly exists; formalize)

```
main.scr::main (line 121)
  └─ thread officer.scr::coop_officer_init                 // unchanged entry
       ├─ exec officer_positions.scr::getAnchor            // NOW also sets theater + feature flags
       ├─ if !coop_feature_boss -> end                     // NEW: per-map skip
       ├─ resolve anchor via ladder (unchanged)
       ├─ coop_officer_spawn:
       │    ├─ model = coop_model_for "officer"            // NEW: theater resolver
       │    ├─ (existing HP/flags/renderfx/marker/icon)
       │    ├─ if coop_feature_waves -> coop_officer_reinforcements
       │    └─ if coop_feature_binoc/paradrop armed on death (existing reward path)
       └─ wave spawners read coop_model_for + coop_wave_mask
```

Net new code: one `getAnchor` widening (data), one `coop_model_for` resolver (~30 lines), feature-flag guards at 3 call sites, and a `coop_wave_mask` reroll in the dispatcher. **No per-map scripts.** This is the whole point — the feature drops on uniformly.

---

## 4. Per-Theater Content Rules & Map Disposition

### 4.1 Models / weapons / voice by theater

| Theater | Maps | Officer model | Infantry | Weapons valid | Voice |
|---|---|---|---|---|---|
| **AA (WaffenSS)** | all m-series | waffenss_officer / wehrmact_colonel / wehrmact_officer / elite_gestapo | waffenss_shutze, elite_sentry | mp40, stg44, kar98k, kar98d sniper, shotgun (all global via TIK override) | German VO global aliases OK |
| **Afrika** | e1l1-e1l4 | Afrika_officer | afrika_private (headwrap variants) | mp40/stg44/kar98k work; Afrika TIK has kar98k case block — others fine, just no matching pouch visuals (`ai_model_catalog.md`) | German VO OK |
| **Wehrmacht** | e2*, e3*, t1*, t2* | wehrmact_officer | waffenss_shutze, wehrmact_grenadier | same set | German VO OK |
| **Russian-theater (German garrison)** | t3l1, t3l2 | wehrmact_officer | waffenss_shutze | same set | German VO OK; players carry Soviet weapons (cosmetic only for officer) |

Dogs (`german_shepherd` + `german_hund_hundpatrol`), stuka (`stuka_strafe`), artillery, smoke, paradrop assets are theater-agnostic and already cached. Dog sounds were globalized (`project_build_plan.md`).

### 4.2 Maps to SKIP the boss or get a reduced set

Driven by `coop_feature_*` flags. From `level_scripts_aa.md` + `level_scripts_sh_bt.md` + SUMMARY:

| Map | Disposition | Reason |
|---|---|---|
| m4l0 | SKIP boss | vehicle escort; gameplay model differs |
| m5l2b, m5l3 | REDUCE (no AT/dogs; waves OK) | player in/around tank; on-foot boss marginal |
| m1l3a, m3l1a | DELAY only | D-Day beach, `coop_playerGlue` during intro — already handled by truck-intro wait |
| m1l2a, m1l3c, e1l4 | DELAY | disguise maps; officer must not break disguise pre-alarm |
| m4l1 | boss OK, Z-override | entry-shaft Z already handled (z_ref=50) |
| t1l1 | SKIP boss | long plane-ride + barn-crash cinematic intro |
| t2l2 | REDUCE / SKIP | player drives halftrack entire map |
| t3l2 | SKIP boss | player in T-34 entire map |
| e2l3 | careful | checkpoint/cvar save system; officer state must be idempotent |
| e3l4 | SKIP until integrated | campaign-end, no coop at all |
| m2l3, m2l2a, m2l2b, t1l3 | MARGINAL (dynamic only) | per positions.scr exclusions; small/escort/NPC-colonel maps |

These are exactly the maps where `coop_feature_boss=0` (or a trimmed `coop_wave_mask`) should be set in the profile table.

---

## 5. Phased Rollout Plan

### Phase 0 — Theater & feature plumbing (prereq, no map edits)
1. Widen `officer_positions.scr::getAnchor` with `coop_theater` + `coop_feature_*` + `coop_wave_mask` (defaults make existing behavior identical).
2. Add `coop_model_for` resolver in officer.scr; replace the ~14 hardcoded model literals (officer.scr:173-176, 268, 835, 921, 1022, 1090, 1110, 1165, 1308, 1511, 1527, 1719).
3. Add feature-flag guards at boss-spawn, wave-dispatch, binoc-reward, paradrop-arm sites.
4. Add `coop_wave_mask` reroll in `coop_call_reinforcements` (officer.scr:748).
**Validation:** m4l3 still behaves identically (regression baseline — it's the proven map).

### Phase 1 — AA finish (lowest risk, system proven here)
- Already deployed on 26 maps. Capture in-game anchors for the 3 `verify_ingame` AA maps (m1l1, m1l3c, m3l1b).
- Decide m4l0 / m5l2b / m5l3 reductions (set flags).
- The 4 precache-only AA maps (m1l3a, m3l3, m5l2a, m6l1b) have no level script — these need the level script authored or remain dynamic-only/skipped.

### Phase 2 — Breakthrough e-series
- **Precache fix (mandatory):** add `exec coop_mod/precache.scr` (or at least the officer/paradrop asset block) to all `e*_precache.scr` — confirmed missing on e1l1/e2l2 headers.
- e1l1-e2l1, e3l1: already integrated → set `coop_theater` (afrika for e1*, wehr for e2*/e3*) and ship.
- e2l2: partial (no waitForPlayer) — officer init must stay non-blocking; verify it doesn't fire before players exist.
- **e3l2, e3l3:** insert `waitthread coop_mod/main.scr::main` at top of main: (they only swap music today).
- e3l4: insert full coop init or leave skipped.
- e2l3: respect checkpoint cvar; make officer state idempotent across reload.

### Phase 3 — Spearhead t-series (most work)
- **Every t-map needs `waitthread coop_mod/main.scr::main` inserted** at top of main: before first `level waittill prespawn`, plus `$player stufftext` music → `exec coop_mod/replace.scr::tmstartloop` swaps (per `level_scripts_sh_bt.md`).
- Precache: add coop precache to t*_precache.scr.
- Capture in-game anchors for all 7 listed t-maps + decide t1l1/t2l2/t3l2 skips.
- t1l3 has a vanilla NPC colonel — place HZM officer in a different zone or after the colonel finishes.

### Per-map validation checklist
- [ ] Map runs `coop_mod/main.scr::main` (officer init prints appear in console).
- [ ] `OFFICER: authored anchor at …` prints with the table coord (not the dynamic fallback message).
- [ ] Officer spawns on the floor, not in a wall / under map / on a roof (Z diff prints sane).
- [ ] Correct theater model (Afrika on e1, etc.).
- [ ] Radio + cardtable visible; radio-bomb objective completes and stops waves.
- [ ] Overhead icons render (eagle/swastika/star) — depends on deployed cgame.dll.
- [ ] Binoculars reward + bombing run fires; paradrop C-47 + chutes spawn on smoke.
- [ ] All 8 wave types spawn with correct models and no parse errors in console.
- [ ] No `unknown command` / `Script not properly loaded` (would kill all of officer.scr).

### Top risks
1. **Parse killers** (`mohaa_script_notes.md`): UTF-8 BOM, em-dash, bare negatives in parens, spawn-with-inline-keyvalue, unknown commands. A single one anywhere in officer.scr fails-loads the **entire** file → no officer on any map (this exact bug already happened once with `fireweapon`, per `project_build_plan.md`). Byte-verify after every edit; bisect with prints.
2. **Missing precache on e/t** → emitters/models pop in late or silently fail. Phase 2/3 precache fix is mandatory, not optional.
3. **SP-only sequences** (truck intros, glider/jeep rides with `coop_disableSpawnWarper`, disguise gates, glued players) firing the officer at the wrong moment. The truck-camera wait (officer.scr:17-27) handles some; disguise/glue maps need feature delays or skips.
4. **Anchor in unreachable geometry** on un-captured maps → officer stuck or floating. Mitigated by Z-filter + dynamic fallback, but `verify_ingame` maps and all t-maps must get real in-game capture.
5. **Theater model absent from active pak** if fs_game changes from maintt. Validate the resolver against the actual shipped pak set; keep the Wehrmacht 8-char typo'd spelling.
6. **Wave mask reroll infinite loop** if a map masks off all 8 types — guard with a max-tries fallback to a always-allowed type (e.g. infantry).

---

## 6. Anchors still needing in-game capture
- AA: m1l1, m1l3c, m3l1b (flagged `verify_ingame`); m1l3a/m3l3/m5l2a/m6l1b (no level script).
- e-series: re-verify e2l2 (Z=2576 elevated), confirm all on first live run.
- t-series: **all anchors** (t1l2, t2l1[verify], t2l2, t2l3, t2l4, t3l1, t3l2) — these maps can't run yet, so the listed coords are untested estimates. Capture once integration lands.

Use the viewpos/noclip/getchshader workflow from `coordinate_units_reference.md`; Z must be referenced to each map's own ground (player_start Z), not absolute — several maps sit at Z≈±1000-5400 (`SUMMARY.md` §KEY NOTES 4).

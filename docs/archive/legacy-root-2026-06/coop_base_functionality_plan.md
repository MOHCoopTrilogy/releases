# Base Coop Functionality Plan — Make Every Campaign Map Playable in Coop

**Scope:** the underlying coop *plumbing*, NOT the officer-boss/airstrike/paradrop combat-content scale-out.
"Base coop functional" = multiple players spawn correctly; the level script runs under coop without hanging;
SP-only scripted sequences (cinematics, forced solo events, vehicle/rail segments, camera/freeze) do not soft-lock;
objectives/triggers work for a team; precache is correct; players can progress start-to-finish.

**Sources:** HZM mod source `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\` + memory KB
(`level_scripts_aa.md`, `level_scripts_sh_bt.md`, `mohaa_script_notes.md`, `research_index.md`).
Last updated 2026-06-22.

---

## 1. What the Coop Mod Requires of a Level Script (the integration contract)

### 1.1 The canonical "known-good" pattern (from any AA m-series map, e.g. m1l1, m4l3)

Every HZM-integrated map opens `main:{}` with these first lines (confirmed in `level_scripts_aa.md` Global Pattern):

```
main:{
    level.coop_aaMap = 1                          // marks an AA-campaign map (optional flag, AA only)
    [ level.coop_disableSpawnWarper = game.true ] // ONLY on cinematic/vehicle-intro maps
    waitthread coop_mod/main.scr::main            // <-- THE injection point; blocks until coop init done
    ...
    level waittill prespawn                       // entities now accessible
    ...
    //level waittill spawn                        // vanilla line, commented out
    waitthread coop_mod/replace.scr::waitForPlayer// <-- coop-safe replacement for "level waittill spawn"
    ...                                           // combat / objectives start here
}end
```

### 1.2 How `coop_mod/main.scr::main` works (confirmed by reading the file)

- `main:` (lines 35-132) must run **in a single frame with no `wait`/`waitframe` before it** — the file header
  warns this explicitly ("ALL THIS CODE HAS TO BE STARTED IN A SINGLE FRAME, NO DELAYS").
- It is idempotent: `if(level.coop_mainScriptLoaded != NIL){ end }` (line 43) guards against double-load.
- It spawns `trigger_relay targetname "coop_levelWaitTillSpawn"` (line 40) — this is the entity
  `waitForPlayer` keys off (see below).
- **Singleplayer branch** (lines 93-96): if `level.gametype == 0` it threads `spWaitForPlayer` and `end`s early.
  So an integrated map still runs fine in SP — integration is non-destructive.
- In coop it sequentially `waitthread`s: `variables.scr::main`, `server.scr::main`,
  `spawnlocations.scr::main`, then `thread`s the per-frame managers
  (`player.scr::manage`, `events.scr::initialiseEvents`, `officer.scr::coop_officer_init`, etc.).
- Because it is `waitthread` (blocking), the rest of the level script only proceeds after coop is fully set up.
- **This is the single canonical hook for the whole mod** — every cross-map feature is launched from here,
  and any map that does NOT call it gets *none* of the coop plumbing.

### 1.3 How `waitForPlayer` works (confirmed `replace.scr` lines 99-140)

- If not in coop mode (`!inCoopMode`): falls back to vanilla `level waittill spawn` and ends — safe in SP/MP-DM.
- In coop: spins (`wait 0.25`) until `level.coop_playerReady == 1`, printing
  "HaZardModding Coop Mod is waiting for you to spawn." It is re-entrant — a second call only polls
  `level.coop_waitforPlayer`. This is what prevents combat sections from firing before any player is in the level.
- The replacement for the vanilla `level waittill spawn` line is the **single most important per-map edit**:
  any unconverted `level waittill spawn` still works but does NOT gate on all players being ready.

### 1.4 How precache is wired (confirmed)

- **AA m-series:** every `m*_precache.scr` begins with `exec coop_mod/precache.scr` (the shared cache list,
  `precache.scr` has ~165 `cache` lines: coop items, German officer/soldier models, FX, stuka, c47, markers).
- **BT e-series:** **NONE** of `e*_precache.scr` call `exec coop_mod/precache.scr` (verified e1l1, e3l2 — both
  start with `exec global/fx_precache.scr` then map assets only). **This is the precache gap.**
- **SH t-series:** no t-series files ship in the mod at all (verified: glob for `maps\t*l*.scr` returns nothing).

### 1.5 The authoritative "validated/intended" set: `coop_mod/maplist.scr`

`maplist.scr` (lines 4-57) enumerates the maps HZM has wired into the rotation / next-map chain:
- All 30 AA m-series scripts **+ m4l0** (m1l1 … m6l3e).
- BT: **e1l1, e1l2, e1l3, e1l4, e2l1, e2l2, e2l3, e3l1** (8 maps).
- Explicit `//TODO: add SH maps when we come to it` and `//TODO: add more BT maps here` — meaning
  **e3l2, e3l3, e3l4 and ALL t-series are deliberately NOT yet in the list.**
- Maps absent from this list have no `nextMap`/`previousMap` chain entry → mission-complete transitions to them
  or from them may misbehave.

> **Definition used below:** a map is "validated/believed-working" only if it (a) calls
> `coop_mod/main.scr::main`, (b) uses `waitForPlayer` (or a deliberate `level waittill spawn` exception),
> and (c) appears in `maplist.scr`. Anything missing (a) is "not integrated."

---

## 2. Full Per-Map Classification

Classes:
- **(a) Integrated & believed-working** — full pattern + in maplist.
- **(b) Integrated but untested / quirky** — has the hook but a known coop timing/sync caveat.
- **(c) NOT integrated / pure vanilla** — missing `coop_mod/main.scr::main`.
- **(d) Inherently problematic** — vehicle/rail/cinematic/escort that needs real surgery even once hooked.

A map can carry both a primary class and a (d) flag.

### 2.1 Allied Assault (m-series) — 30 scripts (+4 precache-only)

| Map | Class | Spawn wait | Notes / caveats (per `level_scripts_aa.md`) |
|-----|-------|-----------|---------------------------------------------|
| m1l1 | a | waitForPlayer | Truck intro camera; coop_disableSpawnWarper during intro |
| m1l2a | a | waitForPlayer | Disguise map (`coop_enableDisguises`) |
| m1l2b | a / **d** | waitForPlayer | Vehicle/truck level; player glued during ride |
| m1l3a | b / **d** | waitForPlayer (sub-thread) | D-Day beach; 286KB (near engine limit); `coop_playerGlue=1` |
| m1l3b | a / **d** | waitForPlayer | Jeep level; player glued to jeep |
| m1l3c | a | waitForPlayer | Lighthouse climb + disguise + elevator puzzle |
| m2l1 | a | waitForPlayer | Research complex patrol |
| m2l2a | a | waitForPlayer | U-boat pen pt1; chainspawner |
| m2l2b | a | waitForPlayer | U-boat plant bombs; escape chainspawner |
| m2l2c | b | **`level waittill spawn`** | Kept vanilla sync; immediate combat |
| m2l3 | a | waitForPlayer | Train-station escape; chainspawner |
| m3l1a | b / **d** | waitForPlayer (sub-thread) | D-Day beach; file too large to read fully; glue intro |
| m3l1b | a | waitForPlayer | D-Day bunker; MG42s gate exit |
| m3l2 | b | waitForPlayer | **ANOMALY: no `main:{}` wrapper** — coop init at file top level |
| m4l0 | b | **`level waittill spawn`** | Secret farmhouse; `coop_disableSpawnWarper=false`; dogs |
| m4l1 | a / **d** | waitForPlayer | Pilot escort; pilot death = missionfailed |
| m4l2 | a / **d** | waitForPlayer | Truck-ride infiltration; fake-truck glue for all players |
| m4l3 | a | waitForPlayer | Paper Chase; alarmer.scr; Manon NPC; campaign end |
| m5l1a | b / **d** | **`level waittill spawn`** | Sniper Town pt1; vehicle/crew system |
| m5l1b | a / **d** | waitForPlayer | Sniper Town pt2; Panzer; <2 engineers alive = fail |
| m5l2b | b / **d** | **`level waittill spawn`** | Tank-drive 2; player in `$playertank`; immune-to-bullets entities |
| m5l3 | b / **d** | waitForPlayer (5 sub-threads) | Tank bridge defense; per-scene re-sync |
| m6l1a | a | waitForPlayer | Snowy forest; destroy 2x flak |
| m6l1c | a | waitForPlayer | MP44 facility; `alarm_system.scr` stealth |
| m6l2a | a | waitForPlayer | Comms Blackout; alarmer; `coop_fixBlindSnipers` hotfix |
| m6l2b | b | **`level waittill spawn`** | Snowy rail station; AI groups; immediate combat |
| m6l3a | a / **d** | waitForPlayer (line 294) | Fort Schmerzen; armored train; alarmer |
| m6l3b | b | waitForPlayer (in elevator1 sub-thread) | Sync can race combat start (known quirk) |
| m6l3c | a | waitForPlayer | Escaping Fort Schmerzen; 17 blast threads |
| m6l3d | b | waitForPlayer | Gas level; `elevator2` pre-runs before player spawn in coop |
| m6l3e | a | waitForPlayer (in level_setup) | Fort Schmerzen escape |
| m1l3a/m3l3/m5l2a/m6l1b | n/a | — | **Precache-only, no level script** — map cut or handled by preceding level; verify they are never loaded standalone |

AA verdict: **all 30 are integrated and in maplist** — none are class (c). Risk concentrates in the (d)-flagged vehicle/escort/beach maps and the (b) timing-quirk maps.

### 2.2 Breakthrough (e-series) — per `level_scripts_sh_bt.md`

| Map | Class | Coop init | Notes |
|-----|-------|-----------|-------|
| e1l1 | a / **d** | `main.scr::main` @14 | Jeep ride intro (spawn warper off); Panzer battle. In maplist. |
| e1l2 | a | `main.scr::main` @25 | Convoy escort; dense proximity spawn triggers. In maplist. |
| e1l3 | a | `main.scr::main` @9 + butler hook | Hybrid native `prespawn` + coop; boat intro. In maplist. |
| e1l4 | a | `main.scr::main` @15 | Disguise/stealth ship infiltration. In maplist. |
| e2l1 | a / **d** | `main.scr::main` @5 | Glider cinematic (spawn warper off until `sparky1_on`). In maplist. |
| e2l2 | b | `main.scr::main` @14 (PARTIAL) | Main flow uses native `prespawn`/`spawn`, **no `waitForPlayer`** — most unsafe of partials. In maplist. |
| e2l3 | b | `main.scr::main` @7 | Checkpoint/save system (`cvar coop_save`); gametype-branched spawn. In maplist. |
| e3l1 | a / **d** | `main.scr::main` @67 | British HQ; jeep ride; coop comment block lists known NULL-listener intro errors. In maplist. |
| **e3l2** | **c** | **NONE** (verified: `prespawn`@19, `spawn`@37, no main hook) | Only music lines swapped; uses `global/ObjMgr.scr`; **precache gap**. NOT in maplist. |
| **e3l3** | **c** | **NONE** | Only `takeAll`/`physics`/`playsound`/`missionfailed` replaced; K5 railguns. NOT in maplist. |
| **e3l4** | **c / d** | **NONE** (pure vanilla-equiv) | Campaign-ending; awards medals, `DoOutro`; only comments + unguarded `$player heal 1`. NOT in maplist. |

### 2.3 Spearhead (t-series) — per `level_scripts_sh_bt.md`

**All 9 are class (c) — pure vanilla, zero integration, and none ship in the mod tree.**
Shared properties: no `main.scr::main`, no `waitForPlayer`, no `coop_` vars, SP-only `$player stufftext "tmstart..."`
music, no `coop_mod/precache.scr`.

| Map | Class | Inherent problem flag |
|-----|-------|----------------------|
| t1l1 | c / **d** | Long plane-ride + barn-crash cinematic intro |
| t1l2 | c | Dutch town; captain NPC follow; Flak88 objectives |
| t1l3 | c | Canal town; scripted colonel NPC on `officer_trig1-5` path; bridge demo |
| t2l1 | c | Ardennes; squad-death=fail; sticky bombs vs Tigers |
| t2l2 | c / **d** | Player drives halftrack most of map; truck escort = win |
| t2l3 | c | Bastogne wave defense; most complex t-series AI mgmt; German weapons given |
| t2l4 | c / **d** | Stavelot; explicit `KillThePlayer` death zones; multi-building AI |
| t3l1 | c | Berlin; Soviet weapons; tank waves; safe-combo puzzle; `stufftext` at BSP trigger `s10_3` |
| t3l2 | c / **d** | Player in T-34 entire map; campaign-ending `missiontransition` |

### 2.4 Classification totals

- **Class (a) integrated & believed-working:** ~21 AA + 6 BT (e1l1-e1l4, e2l1, e3l1) ≈ **27 maps**.
- **Class (b) integrated but untested/quirky:** ~9 AA (m1l3a, m2l2c, m3l1a, m3l2, m4l0, m5l1a, m5l2b, m5l3, m6l2b, m6l3b, m6l3d) + 2 BT (e2l2, e2l3).
- **Class (c) NOT integrated / pure vanilla:** **3 BT (e3l2, e3l3, e3l4) + 9 t-series = 12 maps.**
- **Class (d) inherently problematic (overlaps a/b/c):** ~9 AA vehicle/beach/escort + e1l1/e2l1/e3l1 + t1l1/t2l2/t2l4/t3l2.
- **Precache-only (no script):** 4 AA stubs (m1l3a/m3l3/m5l2a/m6l1b) — note m1l3a has BOTH a precache stub and a full script entry in different memory rows; reconcile during testing.

---

## 3. Common Breakage Patterns — detection signature + fix

### P1 — Missing `coop_mod/main.scr::main` (no coop plumbing at all)
- **Affects:** all class (c) — e3l2, e3l3, e3l4, all t-series.
- **Signature:** grep the map `.scr` for `coop_mod/main.scr::main` → no hit. Symptoms in-game: players never
  forced to allies, no coop spawn warper, no DBNO/loadout, AI never re-difficulty-scaled, no officer init.
- **Fix:** insert the 2-3 line header at the very top of `main:{}` (or file top for no-wrapper scripts):
  `waitthread coop_mod/main.scr::main`. Must be in the first frame, before any `wait`/`waitframe`.
  For t-series flat scripts (no `main:` label) insert before the first `level waittill prespawn`.

### P2 — SP-only `level waittill spawn` not gated for a team
- **Signature:** `level waittill spawn` present without the `waitForPlayer` replacement (and map IS coop).
- **Fix:** replace with `waitthread coop_mod/replace.scr::waitForPlayer` (comment out the vanilla line as the
  AA maps do). Exception: the 5 AA maps that intentionally keep `level waittill spawn` (m2l2c/m4l0/m5l1a/m5l2b/m6l2b)
  — leave those unless a sync bug is observed.

### P3 — Precache gap (assets not cached on e/t maps)
- **Signature:** `e*/t*_precache.scr` missing `exec coop_mod/precache.scr` (confirmed for all e-series).
- **Symptom:** late-loading hitches / missing emitters / coop markers / officer & German models fail to appear.
- **Fix:** add `exec coop_mod/precache.scr` as the **first line** of each affected `*_precache.scr`.
  Cheap, low-risk, do it for every e and t map.

### P4 — `$player stufftext "tmstart…"` music (SP-only, breaks/echoes in coop)
- **Signature:** grep for `stufftext` + `tmstart`/`tmstop`/`tmstartloop`. Common in all t-series and e3l2/e3l4.
- **Note:** `stufftext` runs on a single client; in coop only the host (or one client) hears music, and on
  BSP-triggered functions (e.g. t3l1 `s10_3`) it can fire per-client oddly.
- **Fix:** replace with `exec coop_mod/replace.scr::tmstartloop "sound/music/<file>.mp3"` /
  `::tmstop`. Edit the actual function that owns the call (including BSP-triggered ones).

### P5 — GLOBAL camera / freeze cinematics (affect ALL players)
- **Background (`mohaa_script_notes.md` + engine_systems_advanced):** `cuecamera`/`freezeplayer` are GLOBAL —
  they freeze and camera-lock *every* player simultaneously, and a cinematic written for one player can
  soft-lock the team if release is conditioned on one player's trigger/position.
- **Signature:** grep `cuecamera`, `freezeplayer`, `camera`, `viewmode`, `controls 0`/`freezecontrols`.
- **Fix options:** (1) gate the cinematic so it only plays once and releases on a level flag, not a per-player
  trigger; (2) for per-player intent use `trigger_camerause` + `doUse` per player (m1l1 pattern, per
  `engine_systems_advanced.md`); (3) if purely cosmetic, skip it in coop (`if(!level.gametype){...}` wrap).
  Always ensure an unconditional release path so no player stays frozen.

### P6 — Spawn-warper disabled across a cinematic/vehicle intro that a player can skip
- **Background:** `level.coop_disableSpawnWarper = game.true` is set during jeep/glider/truck intros and
  re-enabled by a BSP trigger (e1l1 jeep, e2l1 `sparky1_on`, m1l1 truck). If a coop player skips/misses the
  re-enable trigger, the warper stays off and late/dead players can't be repositioned.
- **Signature:** `coop_disableSpawnWarper = game.true` set but re-enable tied to a single BSP trigger.
- **Fix:** add a safety re-enable (timer fallback or `waitForPlayer`-gated re-enable) so the warper always comes back.

### P7 — Forced solo / vehicle-driver sections (one player drives, others stranded)
- **Affects (d) maps:** m1l2b, m1l3b, m4l2, m5l1a/b, m5l2b, m5l3, e1l1, t2l2, t3l2.
- **Signature:** `$playertank`/`$playertruck` glue; `player glue`; a single vehicle entity the map assumes one
  occupant. Memory notes AA tank maps use `coop_immuniseFromBullets` + `coop_teleportMaster` to cope.
- **Fix:** use the existing coop vehicle handling — `coop_mod/bt_playerTank.scr` /
  `coop_mod/vehiclehandler.scr` already model "one driver, passengers glued/teleported." Wire non-driver
  players to follow via the teleport master and ensure the win-condition (truck/tank survival) is team-shared.
  These are the **real-surgery** maps.

### P8 — NPC-escort death = mission failure (team raises the failure odds)
- **Affects:** m4l1 (pilot), t1l2/t2l1/t2l3 (squad-death=fail), m5l1b (<2 engineers).
- **Signature:** `missionfailed` tied to a friendly NPC `waittill death` or a squad-alive count.
- **Fix:** keep behavior but verify the NPC survives multi-player chaos; if needed relax the count or make the
  NPC invulnerable until the relevant objective. Lower priority than soft-lock fixes.

### P9 — `trigger_once` objectives that assume the lone SP player triggers them
- **Background (`scripting_event_reference.md`):** objectives auto-replicate to all coop clients, but a
  `trigger_once` only fires for the first toucher — fine for progression, but a gate that *waits on a specific
  player* can stall. e2l2 (native prespawn/spawn, no waitForPlayer) is the canonical risk here.
- **Signature:** objective/progress `waittill` keyed to `$player` (singular) rather than any active player.
- **Fix:** route through `waitForPlayer` and/or the coop `playerSpawnEvent` system in `main.scr`; replace
  `$player`-singular references with the active-player iteration pattern (`$player[1..size]`).

### P10 — Parser/encoding killers introduced while editing (regression risk, not pre-existing)
- From `mohaa_script_notes.md`: UTF-8 BOM, non-ASCII byte (even in comments), bare `(-N)`, inline `spawn Class key "val"`,
  unknown command, multi-line `&&`/`||` condition — each silently fails the WHOLE file.
- **Fix discipline:** edit with ASCII-only, no BOM (`-Encoding ASCII`/utf8NoBOM); validate on a dedicated server
  console for `unknown command` / `Couldn't compile`; keep boolean conditions on one line.

---

## 4. Per-Map Remediation Checklist

### 4.0 Universal minimal-injection recipe (every class (c) map)
1. **Hook:** add to top of `main:{}` (first frame, no preceding wait):
   `waitthread coop_mod/main.scr::main`. For flat/no-`main:` scripts (t1l1, t1l2, t2l1, t2l2, t3l1; m3l2-style),
   insert before the first `level waittill prespawn`.
2. **Spawn gate (P2):** replace the SP `level waittill spawn` with
   `waitthread coop_mod/replace.scr::waitForPlayer`.
3. **Precache (P3):** prepend `exec coop_mod/precache.scr` to the map's `*_precache.scr`.
4. **Music (P4):** convert `$player stufftext "tmstart…"` → `coop_mod/replace.scr::tmstartloop/tmstop`.
5. **maplist:** add the map to `coop_mod/maplist.scr` in campaign order so next/prev chaining works.
6. **Smoke test** per §5.

### 4.1 QUICK WINS — just the main hook (+ precache + maybe music), no vehicle/cinematic surgery

These have no forced-solo/vehicle gameplay; the 4-step recipe is likely sufficient:
- **e3l2** (town/POWs) — add hook (it currently has none), precache, leave `ObjMgr.scr` objectives.
- **e3l3** (K5 railguns) — add hook, precache; verify `missionfailed` replacement already present.
- **t1l2** (Dutch town) — recipe + NPC-escort check (P8 cappy).
- **t1l3** (canal town) — recipe; the vanilla colonel NPC path is cosmetic, leave it; watch `objective1` gate (P9).
- **t2l1** (Ardennes) — recipe + squad-death check (P8); sticky-bomb objective is team-friendly.
- **t2l3** (Bastogne) — recipe; complex AI but on-foot; verify wave transitions don't key on one player (P9).

### 4.2 MEDIUM — integrated-but-quirky, fix the specific caveat (no new hook needed)
- **e2l2** — add the missing `waitForPlayer` gate (P2/P9) so airfield combat doesn't fire player-less.
- **e2l3** — make any added state checkpoint-aware (`cvar coop_save`); verify gametype-branched spawn path.
- **m3l2** — confirm any tooling that patches `main:{}` also covers its top-level-init anomaly.
- **m6l3b / m6l3d** — verify elevator/spawner timing doesn't race combat before players sync.
- **e3l4** — add hook + precache + music; it is also (d) (campaign-ending medals/DoOutro) so verify the
  `missioncomplete`-equivalent transition works in coop and the unguarded `$player heal 1` is harmless.

### 4.3 HARD — real surgery (vehicle/cinematic/escort)
- **t1l1** — long plane-ride + barn-crash cinematic before combat (P5/P6). Needs coop-safe camera handling and a
  guaranteed release; consider skipping the cinematic in coop and warping the team to post-crash spawn.
- **t2l2** — player-driven halftrack for most of the map (P7). Needs vehicle passenger handling +
  shared escort win-condition.
- **t2l4** — Stavelot `KillThePlayer` death zones (P5/P9) must be made team-aware so they don't kill innocent
  coop players; multi-building AI windows need review.
- **t3l1** — Berlin: mostly on-foot but has tank waves and the `s10_3` BSP-trigger `stufftext` (P4); medium-hard.
- **t3l2** — player in T-34 the entire map (P7) + campaign-ending `missiontransition` (P9). Hardest t-series;
  needs full vehicle-coop adaptation analogous to AA m5l2b (`$playertank`, `coop_immuniseFromBullets`,
  `coop_teleportMaster`).
- **AA (d) maps already integrated** (m1l2b, m1l3a/b, m3l1a, m4l1, m4l2, m5l1a/b, m5l2b, m5l3, m6l3a) — these are
  in maplist and presumed handled by HZM's existing vehicle/glue/teleport code, but are the **highest-risk
  regression/retest targets** for base functionality validation.

---

## 5. Test / Validation Methodology

### 5.1 Per-map "coop-complete" checklist (pass/fail gate)
1. **Loads:** map starts on a dedicated/listen server with `g_gametype 2` (from `start_server.cfg`),
   no `Couldn't compile` / `unknown command` / `not properly loaded` in console.
2. **Multi-spawn:** 2+ players spawn, are forced to allies, are solid and not stuck in each other (P-makesolid).
3. **No early-exit hang:** combat/objectives only start after `waitForPlayer` reports
   "waitForPlayer DONE" in console (not before any player is present).
4. **Progression:** play start→finish with 2 players; every objective advances; no soft-lock at
   cinematic/vehicle/escort segments (P5/P6/P7).
5. **Camera/freeze:** no player remains frozen/camera-locked after any scripted sequence.
6. **Death/respawn:** a dead player respawns at the correct (warped) coop spawn; spawn-warper re-enabled after
   intros (P6).
7. **Mission end:** `missioncomplete`/transition fires for the team and chains to the maplist next map.
8. **Precache:** no missing-model warnings; coop markers + German/officer models render (P3).

### 5.2 Debugging aids (from memory KB)
- Enable per-file thread debug via `level.cMTE_coop_<file> = 1` (see `main.scr` lines 54-78) to trace whether
  a thread ran at all — distinguishes "logic bug" from "file never loaded" (`feedback_bisect_first.md`).
- Use `iprintln`/`iprint "msg" 1` bisect prints around suspected gate points before assuming a logic bug.
- Watch the dedicated-server console for the compile/parse errors in P10.

### 5.3 Phased order (lowest risk → highest)

**Phase 0 — Plumbing prerequisites (no gameplay risk):**
- Add `exec coop_mod/precache.scr` to all e* and (eventually) t* precache files (P3).
- Decide maplist ordering for the new maps.

**Phase 1 — e-series completion (closest to done):**
- e3l2, e3l3 (quick wins) → e3l4 (medium, campaign-end transition) → fix e2l2/e2l3 caveats.
- Add e3l2/e3l3/e3l4 to maplist. Validate per §5.1.

**Phase 2 — t-series on-foot quick wins:**
- t1l2, t1l3, t2l1, t2l3 — apply §4.0 recipe, validate, add to maplist.

**Phase 3 — t-series cinematic/death-zone medium:**
- t1l1 (cinematic), t2l4 (death zones), t3l1 (tank waves + BSP music).

**Phase 4 — t-series vehicle hard cases:**
- t2l2 (halftrack), t3l2 (T-34) — adapt AA vehicle-coop code (`bt_playerTank.scr`/`vehiclehandler.scr`).

**Phase 5 — AA (d) regression sweep:**
- Re-validate the already-integrated vehicle/beach/escort AA maps (m1l2b, m1l3a/b, m3l1a, m4l1, m4l2, m5l1a/b,
  m5l2b, m5l3, m6l3a) for start-to-finish coop, since they carry the most soft-lock surface area.

---

## 6. Key File Pointers
- Integration core: `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\coop_mod\main.scr` (`main:` lines 35-132; SP branch 93-96; idempotent guard 43).
- Spawn gate: `...\coop_mod\replace.scr` (`waitForPlayer` 99-140; `tmstartloop` 553; `playsound_wait` 917).
- Shared precache list: `...\coop_mod\precache.scr` (~165 cache lines).
- Validated map set: `...\coop_mod\maplist.scr` (lines 4-57; the two `//TODO` lines mark the unintegrated frontier).
- Server config (gametype 2 etc.): `...\coop_mod\start_server.cfg`.
- Vehicle-coop reference code: `...\coop_mod\bt_playerTank.scr`, `...\coop_mod\vehiclehandler.scr`.
- Class (c) map scripts present in tree: `...\maps\e3l2.scr` (no hook, prespawn@19/spawn@37), `e3l3.scr`, `e3l4.scr`.
- t-series scripts are NOT in the mod tree — source originals at `C:\mohaa-coop-dev\original-scripts\spearhead\maps\t*.scr`.
- Parser/edit safety rules: `mohaa_script_notes.md` (Parser gotchas section).

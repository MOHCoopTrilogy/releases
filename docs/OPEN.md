# OPEN — defects, unverified work, and unbuilt plans

Status vocabulary in [SOURCE_OF_TRUTH.md](SOURCE_OF_TRUTH.md#status-vocabulary).
Snapshot **2026-07-29**, trued up **09-04** (Omaha, the gl2 default) and **09-09**; every other item
carries its own date, and the buglog is live, so treat counts as of that date.

## Sections

[P0 — infrastructure](#p0) · [Never ran](#never-ran) · [Defects with evidence](#defects) ·
[gl2 open items](#gl2) · [Diagnostic pending](#diagnostic) · [Awaiting playtest](#unverified) ·
[Planned, not built](#planned) · [Record-vs-code discrepancies](#discrepancies) ·
[Tooling lost](#tooling-lost) · [Config](#config) · [Cheapest wins](#cheapest)

---

<a name="p0"></a>
## ⭐ gl2 IS NOW THE DEFAULT FOR EVERY PLAYER (2026-09-04) — re-price the gl2 section below

Until v1.5.1 essentially every player was on **gl1** - `cl_renderer` defaults to `"opengl1"` and
nothing in the mod ever set it - so the whole gl2 visual layer, the underwater pass included, was
invisible to them. Fixed in four layers (bug-2446).

**THE CONSEQUENCE FOR THIS FILE: every entry in [gl2 open items](#gl2) has just gone from "affects
almost nobody" to "affects everybody".** Re-read that section with that in mind. In particular
**bug-2190 (m3l2 renders BLACK with a WHITE sky after a straight-through transition from Omaha)** is
now on the live campaign path immediately after the mission shipped in v1.5.0/v1.5.1, and
**bug-1331** (styled-lightmap surfaces pulse red) is a gl2 renderer defect, gl1-clean.

## Omaha (m3l1a) after the v1.5.1 pass — open (2026-09-04)

- **The beach aim cone is un-tuned, and the handle is not `bulletrange`.** The turret-ownership
  question is SETTLED: the guns ARE actor-owned, so `bulletrange` is live — but it is the denominator
  of the same term whose numerator `level.coop_beachSpread` is already exposed and already named for
  what it does. Better lever still: `level.target_offset` is 55 (upper chest) while the client zing
  band is measured at the HEAD, so raising it toward 64-70 recentres the whole distribution on the
  band. Also corrects **bug-2439**: `bulletrange` is an accuracy divisor, NOT a reach limit — rounds
  travel `MAX_TRAVEL_DIST` 16216 regardless.
- **Out-of-breath audio is still owed by the user.** `coop_uw_airout` / `coop_uw_wake` are called in
  the plunge and are armed no-ops until the wavs and aliases exist (`RAMPUW airhook armed` reports it).
  22050 mono 16-bit into `sound/coop_tinnitus/` — that path is duck-exempt, anywhere else is inaudible.
- **2026-09-05/06 Omaha batch (bugs 2473-2511, shipped v1.5.2) - the per-item verification list is
  in [archive/open-omaha-2026-09-05.md](archive/open-omaha-2026-09-05.md)**, with the marker that
  proves each. Three runs on 09-06 confirmed the sequence end to end, including the Higgins sink after
  four failures. Still unseen there: beach fire landing (`BEACHLOS seen=1`, `BEACHHIT`), the hedgehog
  crowd's poses and charge, quick-draw flip, the sink's end state, urgency after the smoke. Two of its
  caveats are now closed - the smoke-advance stall by 2529 below, the seam and banding A/Bs by the
  09-07/08 pass below.
- **⭐ 2026-09-07/08 Omaha batch (bugs 2512-2529) - DEPLOYED AND READ BACK, NOTHING PLAYTESTED.**
  Everything below is verified only to "the map boots with 0 compile / 0 script errors and the bytes in
  both roots match what was packed". None of it has been seen or felt.
  - **The drowning QTE (2528) is the only thing here that can fail a player, and it is the least proven
    thing here. The bar has never been drawn, the meter has never been felt, and nobody has drowned.**
    Tap Use to claw off the seabed between BEAT 5 and BEAT 6; beats 6-8 are unchanged and run as the
    reward. Knobs, all assigned unconditionally beside `coop_uwPace` in `coopified.scr`:
    `level.coop_qteLethal 0` makes it survivable without removing it, `coop_qteOn 0` removes it,
    `coop_qteWin 18.0` / `coop_qteGain 0.070` / `coop_qteDrain 0.10` set the pace, `coop_qteHud 0`
    drops the bar alone (slots 123 curtain / 124 track / 125 fill / 179 label). Failure is **per
    player** - LMS-exempt in `coop_mod/player.scr`, and deliberately NOT `missionfailed`, which in coop
    reloads the map for everyone (TRAPS T17). The input edge is the one proven part: measured in game
    at 971 samples / 395 held / 77 edges - a 5.35 s hold gave exactly one.
  - Smoke barrage now waits on `level.coop_radiomanTxDone`, 20 s anti-strand ceiling (2529, user
    report: it was dropping over the shore-party exchange). Probe `SMOKEDROP waited= txdone=`.
  - Five extra beach medics crouched behind hedgehogs, spinning DBNO-style kits, healing on approach,
    with a break-off heal animation (2522/2523/2526). Solved 190 u seaward of a hedgehog cover trigger,
    min separation 1408 u - the first two tries were bunched, offset onto the exposed side, and posed
    holding a rifle they do not carry.
  - Ocean and surf realism (2515-2525): an open-sea mesh of three Airy components, a surf-zone bore
    layer (`docs/tools/gen_coop_surf.py`), and a trough shadow painted antiphase to the break foam
    (`gen_boreshade.py`) - **because deformed water cannot be lit here at all**, see
    [ENGINE.md](ENGINE.md) 3.6. Boat overlaps fixed; the naval "thunder" was answered as an HD sound
    pack's 2.72 s shell roll, not weather.
  - **Deferred by design and still ranked** in `docs/proposals/water_omaha_2026-09-05/`: obliquity
    shear (sign unsettled), sky sheen (doubles brightness at the proposed ceiling), aerial perspective
    (a live cvar A/B on `r_globalFogStartScale 0.556`), seaward crest and wash continuations, seabed
    depth tint, and **boats riding the waves** - which needs no engine change, since `level.time` and
    `sin` both exist, but must sample the same wave function: a fixed 6.25 s retime was refuted on
    Doppler grounds.
- **Still open from the 09-04/05 handoff:** the trench grenade an ally promises and nobody throws
  (build or leave - user's call); the coop bazooka team can throw a live rocket (probe shipped, not
  fixed); `docs/02-status-ledger.md:86` still calls gl2 'PAUSED'; bodycam DoF focus pull
  (recommended, not built); the sprint one-handed carry needs a viewmodel clip (refused as procedural, see DECISIONS.md);
  water research #1 is built (bug-2485),
  #2+ stay ranked in `docs/proposals/water_omaha_2026-09-05/`; ricochet research (feasible, engine
  pair, ~250 lines) is filed in `docs/proposals/ricochet_2026-09-06/` - not built.
- **The muffle's one unverifiable premise:** whether OpenAL Soft applies `AL_DIRECT_FILTER` to an
  `AL_SOURCE_RELATIVE` (2D) source. Only the headers are vendored, not the mixer. If it does not, the
  muffle is inert rather than broken. A ten-second A/B in game settles it (bug-2444).

## e2l1 (Kasserine glider) - parked

Four open item sets from the 2026-08-03 round (remaining glider items, the crash-landing arrival
spec, the unresponsive truck "statue", and the P40 final-tank explosion chain) are parked in
[archive/e2l1_open_items.md](archive/e2l1_open_items.md). Still open, just not the active front.

## P0 — infrastructure, fix before feature work

*Re-verified 2026-08-15 by sha256, not by mtime. Four of the five entries here were stale and have
been moved to [archive/open-p0-cleared-2026-08-15.md](archive/open-p0-cleared-2026-08-15.md). The
method matters more than the result: mtime only says when a file was written, so every claim below
was settled by hashing the live binary against the published manifest.*

**What was measured.** 8 of the 9 binaries in `manifests/manifest-1.2.9.json` are **byte-identical**
to the live copies in `G:\mohaa-gl2` — `openmohaa.exe`, `cgame.dll`, `renderer_opengl1.dll`,
`renderer_opengl2.dll`, `omohaaded.exe`, `SDL2.dll`, `OpenAL64.dll`, `libcurl.dll`. Only `game.dll`
differs, because it was rebuilt after v1.2.9 shipped and has not been published yet.

### `renderer_opengl2.dll` rollback is a manual convention (the "zero backups" claim was a regex miss)
`CORRECTED 2026-09-15` · The old "0 rollback points" was an artifact of an 2026-08-15 re-count whose regex
only matched `<binary>_pre_<feature>_bak.<ext>` and missed the ACTUAL naming in use. `G:\mohaa-gl2\` holds
**~21 `renderer_opengl2.dll` backups** today — `renderer_opengl2.dll.bak_2026-09-13_pre_visuals` beside the
live Sep-14 DLL, `renderer_opengl2_pre_terrainlight.dll.bak`, and ~19 `.dll.pre_<feature>_bak` files. The
real (fair) observation that survives: binary rollback is a **manual convention**, not automated - so keep
backing up before an engine deploy. The module is NOT unprotected.

---

<a name="never-ran"></a>
## Never ran — `SHIPPED-CODE-DISABLED`

A status class this project needed and did not have. These are wired into `main.scr` behind gates
testing `== "1"` on cvars **seeded in no shipped cfg** — `autoexec.cfg`, `coop_defaults.cfg` and
`coop_mod/*.cfg` all return zero hits. Note the gates test `== "1"` while the cvar is **unset (empty
string)**, not `"0"` — so records describing these as "default 0" imply a deliberate shipped default
that does not exist.

**Mostly resolved 2026-08-17..08-30.** Four systems NOW SEEDED (`coop_aiDynamic`/`coop_aiSquad` +
g_main.cpp archives, `coop_moraleEnable`/`coop_retreatEnable` in autoexec); `coop_aiSearch` seeded
2026-08-17 (never run before). Five closed in one sweep (bugs 2176-2181), and "seed the cvar" was right for
only ONE: `coop_aiAggrMove` (bug-2180) and stealth arm-on-hurt (bug-2178) were **DELETED** as harmful
(would ship bug-2100 / make e1l3 unwinnable), `coop_aiBound` (bug-2181) needed re-gating on squad-brain
ownership, objective-drop (bug-2179) + MP voice-wheel (bug-2176) closed. **Residuals:** objective-drop
pickups are `SOLID_BBOX` until taken; `coop_aiBound` ≈3.5% fewer repositions (a de-synchroniser, not a
tactic). **⚠️ The AI maneuver mover was verified only by the bot rig (which sets the gate itself)** — never
run for a player; see [TRAPS.md § T15](TRAPS.md#t15).

**Still unseeded** (of the 144 `coop_*` cvars seeded nowhere): `coop_aiScale`/`coop_aiScaleChance`/
`coop_aiScaleTest`, `coop_health` (750 lives as an *else-branch* at `server.scr:223-227`),
`coop_dbnoCorpseRevive`, `coop_unsponge` (on-by-default rests on a comment, `aihandler.scr:277`; a fresh
bullet-sponge fix, bug-1212). **Decision needed:** seed a deliberate default in `coop_defaults.cfg` or
document as opt-in — right now shipped behaviour is whatever a fallback branch does.

---

<a name="defects"></a>
## MP Progression + Service Record — SHIPPED v1.7.0 (2026-09-14); playtest tail only (details: buglog, FEATURES)

Engine + script verified by bot boots; the **client-rendered** parts need your machine (a dedicated boot
renders no menus): in the MP armory confirm the **3D character renders** (body + helmet at `Bip01 Head` +
weapon at `tag_weapon_right`, hold pose, SPIN), a skin/helmet tile updates it live, a locked class denies
then unlocks after 15 kills; pick a skin from **Multiplayer Options → APPEARANCE** and confirm it persists
into a match; open MP SERVICE RECORD and confirm rank/counts/badges. Helmets use coop's exact-fit recipe
(bug-2634) — confirm fit and no double on hatted skins (the charRender *preview* can double over the baked
hat — Allied skins have `_nohat` twins, Axis don't; the live spawn is correct via the nodraw path). The MP
framework engages on ALL dm maps (stock `mohdm1-6` included) + `obj/mp_*` (bug-2638, boards reverted to the
stock browser + rotation builder; Push/Base-Assault keep their own Campaign-Maps pickers for the SP maps).

## Awaiting the next playtest (2026-08-17)

- **PUSH = SINGLE FRONT push-through, redesigned + verified headless (2026-09-18, bug-2711).** Replaced the
  two-line capture model (user: read as "capturing points", axis never progressed). Now ONE front `F` (1..N):
  allies hold zones 1..F, axis the rest. Each team's progress is a PROJECTION of its furthest living man onto
  the allies-home→axis-home axis (`push_teamProgress`, 2D t 0..1) — robust where the `sptrg` checkpoint volumes
  are thin/misaligned (the old "stand inside zone F" read ~0 and axis reach stuck at home). Seam = midpoint of
  the two fronts; `F` steps 1/tick toward it (stable, no ratchet). Win = `F` reaches an end (breakthrough) else
  higher seam vs 0.5 at `coop_mpPushTime`; series to `coop_mpPushToWin`. Both teams' bot objective + compass
  point at the same front. HUD slimmed to `PUSH` + a green|red seam bar + timer (y6–16, clears the rank bar at
  x253 y30). **Headless m2l1 (8 bots):** front stable at ~6/10, allies aFrac→0.57, **axis now push xMin 1.0→
  0.625**, resolves on timer by furthest push, clean restart. Isolation 22/22. **LIMIT:** on baked-chokepoint
  maps (m2l1 gate) bots can't path to dead centre (worldspawn navmesh; runtime notsolid doesn't re-carve), so
  BOTS-ONLY stalemates near centre → timer; humans push fully. Real fix = bot traversal (engine, deferred).
  **TODO:** live playtest; per-map gate openers beyond m2l1/m1l2b/m3l3/m4l2/m5l1b.

- **MP DYNAMIC WEATHER — still DEFAULT OFF, client crash unresolved (bug-2710, 2026-09-18).** `coop_mpWeather`
  (`mp_weather.scr`) crashes the listen-server client loading m2l1 Push (snow); `set coop_mpWeather 0` fixes it.
  Client-side, load-time, NOT reproducible on the headless harness → NOT re-enabled blind. NOTE: the maps' AMBIENT
  SOUNDS (crickets/wind/fire via `ambient.scr`→`ambience.scr`) already play in MP and are all the user wants; the
  MUSICAL soundtrack (`music/<map>.mus`) is explicitly NOT wanted (a `push_startAmbient` that briefly added it was
  reverted). **TODO:** short LIVE test (`coop_mpWeather 1` on one map, watch qconsole.log for the crash line)
  before flipping default-on — do not ship blind.

- **SHADOW BLEED-THROUGH — config mitigation shipped, needs visual verify (bug-2721, 2026-09-18).** Object shadows
  (trees/buildings) render THROUGH ground, worst at long range (coarse far sun cascade); regression from the
  2026-09-13 shadow turn-up. Shipped reversible config fix via one-shot `coop_shadowFixDo`: `r_shadowCastFoliage 0`
  (tree case) + bias 4→8 (building/far case). Surgical ENGINE fix ready if bleed remains: per-cascade bias
  (`tr_shade.c:2919`) + cascade-4 bounds guard (`shadowmask_fp.glsl:139`). Needs the user's eyes on a sunlit map.

- **MP vehicle system — spawn-verified, INTERACTIVE loops need a playtest (2026-09-15, bug-2643).** Host
  toggle `coop_mpVehicles 1` (default off), on the 5 SP arena maps (m1l3a/m1l3b/m4l1/m5l2a/m5l3). All 5
  types boot-spawn cleanly: AT pickups (team-aware: allies→bazooka, axis→panzerschreck), flak88 +
  nebelwerfer (mannable FixedTurrets, native use/aim/fire), drivable jeep + tank (native driver
  `attachdriverslot 0` + gunner `attachturretslot 0`; tanks immune to all but rocket/falling, so only the
  AT pickups kill them). **Unverified in play:** board/drive/fire, exit/eject, turret manning, PvP capture
  (enemy holds [USE] beside an unoccupied enemy vehicle `coop_mpVehCaptureTime`s to flip it). **Wired +
  respawn VERIFIED** (bug-2646): destroy→explode+eject→re-place after `coop_mpVehRespawn`; live crew HUD
  (name/role, health bar, crew, exit hint). **Deferred:** crew theatre (team-kill uses `g_teamdamage`). `veh_*` in
  `coop_mod/mp_vehicles.scr`; placements harvested from UberMod into `mp_vehicle_maps.scr` (gen script).
  NOTE: force-arena on **m4l1** spams ~30 harmless "TriggerOnce setthread Script '' not loaded" (its BSP
  triggers hit the blanked map script) — cosmetic log noise, not vehicles.
- **Prop Hunt — mode shipped, human loop needs a playtest (2026-09-15, bug-2641/2659).** AXIS=props (hide as
  stock statics, [USE] cycles shape), ALLIES=hunters (frozen during `coop_mpPhHideTime`). Boot-verified:
  morph, round arm 3v3, hide phase. Unverified: hunter kills a hidden-but-solid prop; full timeout win.
  Vet added a prop-seed draft (`ph_manage` force-joins the last allies player to axis when props=0 &
  hunters≥2, native `join_team`) and a wrong-shot HP penalty (`coop_mpPhShotCost`, default 3). **Best-effort,
  needs a playtest:** the forced draft mid-warmup and the per-shot penalty edge.
- **Symmetric Demolition + Freeze Tag meltgun — need a playtest (2026-09-15, bug-2644/2645/2650/2654/2655).**
  Demolition is two-way (either team plants on the enemy's spawn-derived site; gt2 team board). Vet fixed a
  multi-planter stall (co-planting teammates flip-flopped the timer → never armed), added the `destroy` stat
  credit + `plantbomb`/`explode_tank`/`alarm_switch` audio + a `set_objective_pos` compass marker. FT meltgun
  ranged weld was DEAD (progress zeroed every tick outside 96u) — fixed (bug-2650). Plant/defuse/detonate +
  the weld still need a live playtest.
- **Spawn Protection host-rules UI toggle — deferred (2026-09-15, bug-2640).** The mechanic ships default-ON
  in MP (`coop_mpSpawnProtect`, seeded in mp.scr::main) and is console-toggleable; a board checkbox was NOT
  added because `coop_mphostrules.urc` is full (footer at y422) and a 3-column bottom row truncates the
  "Down But Not Out" label. Add a row only if the board gains vertical space. (2026-09-15 vet: the documented
  move-out early-drop is now implemented — leaving `coop_mpSpawnProtMoveDist` (256u) drops protection, bug-2658.)
- **MP MODE FULL-FUNCTIONALITY VET (2026-09-15, bug-2649–2659).** All 12 MP modes + rounds framework vetted;
  13 fixes shipped (key: round-win credit snapshotted at round-arm via `coop_mpRndTeam`/`mp_awardRoundWin`,
  not last-survivor). Verified by gates+build; **needs a playtest** — S&D detonation credit is a USE-holder
  heuristic, Prop Hunt draft, Demolition audio/marker, round-mode win credits all logic-tested only.
- **REAL UBERMOD BOMB MODES + BUILD-A-BASE MAP FIX — deployed, needs a playtest (2026-09-16, bug-2668/2669).**
  UberMod v8 has only 4 special modes: bb/cyb/snd/ft. S&D and the previously-missing **Cyber Attack** now LOAD
  the real `ubermode/cybersnd.scr` (imported + 5 custom deps under the private `ubermode/` namespace; stock
  `global/earthquake.scr`+`string_format.scr` left to vanilla) off harvested per-map bomb data
  (`cybersnd_sites.tsv` → `gen_cybersnd_maps.py` → `mp_cybersnd_stations.scr`). Freeze Tag stays ours (UberMod's
  ft is logic-only). **Build-A-Base was non-functional as shipped** (bug-2668): its UI offered `dm/mp_*` maps
  that carry no station data (data is authored for the 2001/campaign maps), and the mohdm keys lacked the
  runtime `dm/` prefix. All three now run on **18 maps** via `sv_mpForceArena` (the Base Assault/Push pattern):
  the 7 mohdm* DM maps (bsp spawns) + 11 SP campaign maps that REUSE Base Assault/Push team spawns
  (`gen_arena_spawns.py` → `mp_arena_spawns.scr`). Shared 18-map picker `hzm_arenamaps.urc` (generated), gated
  by `ui_mpIsArena`; Cyber Attack tile added to `multiplayerstart.urc`. **Verified on a dedicated boot:** all
  three engage with zero script errors, "Running <mode> game mode" / "stations placed" on mohdm1 + m1l3a; coop
  map m1l1 still loads coop with MP off and no `g_ubergametype` leak; isolation 22/22. **Needs a playtest with
  real players** (0-player boot can't verify: campaign-map spawn placement, bomb plant/defuse/round flow,
  victory). Minor: `win_snd` challenge is now orphaned (S&D uses UberMod's own scoring, not our progression).
- **MP BOT INTELLIGENCE OVERHAUL — 6 phases shipped, needs a playtest (2026-09-17).** Supersedes the old
  "bots are combat filler" decision. The engine DOES steer bots via `AttractiveNode`; the missing half was a
  script that spawns nodes at live objectives (`mp_botobj.scr::botobj_set`, v1.7.7) + a role layer
  (`mp_botdirector.scr`, Phase 6). Shipped: **P1** graded perception cones (`bot_fov_acquire` 150→`_far` 90,
  fire cone 45) so bots see off-axis threats; **P3** hearing+flank — `NoticeEvent` acquires from gunfire/impact,
  `Pain` switch-if-better (`bot_flankreact`) so a shot-in-the-back bot turns; **P2** objective scatter
  (`bot_objective_spread`, per-bot `m_vAttractScatterGoal` on the primary-attract fast path so they stop
  stacking on one point); **P4a** nav reroute (`bot_nav_reroute`, `MoveNear` relax-radius before terminal
  give-up); **P5b** aim convergence (`bot_combat_realism` — horizontal aim starts loose on a fresh enemy lock
  and tightens over ~1.4s, killing the instant-lock tell; vertical untouched); **P6** squad director — Push
  frontline contest (`dir_contest`, attackers push / defenders hold via team-filtered priority bands) +
  objective wiring extended to CTF / Demolition / Base Assault (`dir_attackEnemy`, each squad hunts the enemy
  objective). All `bot_*` cvars (default on) are live A/B/rollback toggles. **COOP-SAFE by construction:** every
  edit is in `BotController`/`BotMovement` (coop instantiates none — `actor.cpp` is separate) or in `mp*.scr`
  gated on `coop_mpRun`; isolation 22/22, coop untouched. Plan+vets: `hzm-mohaa-coop-mod/_research/mp_bot_ai_plan.md`.
  **Needs a listen/dedicated playtest at `sv_numbots 8`:** verify off-axis engagement, no clumping/stuck, aim
  feels human, and that CTF/Dem/BaseAssault/Push bots actually pursue the objective. Modes still unwired
  (delegate to imported ubermode/htr code): Cyber S&D, Cyber Attack, Countdown.
- **Panzerfaust REMOVED (2026-08-18)** - **armory id 73 is a permanent hole, never renumber.**
- **Skin system: built end-to-end, awaiting menu playtest (2026-08-18).** 357 finish variants / 45 guns,
  armory finish strip, 7 finish challenges, server-side unlock gates, 25 model variants gated on each gun's
  Elite challenge; finishes visually approved. STILL OPEN: the in-hand reload magazine keeps the stock skin
  (bug-2241: `Clip` surface reskins but the reload-mag model doesn't; needs a probe).

## Defects with evidence

### 2026-09-09 m4l3 + engine round — four fixes shipped, none seen in play yet
- **Alarm bell** (bug-2545) now carries to 6000 u with a 0.28 floor, was 1400/0.2. `^~^~^ ALARMBELL
  range= vol=` prints while it rings: if that shows and it is still inaudible, the cause is
  client-side, not the curve.
- **Guards posed armed with empty hands** (bug-2546). `CoopAuditHeldWeapon` re-attaches an active
  main weapon parented to nothing; `^~^~^ WEAPHEAL` names the weapon, tag and state, which is what
  identifies WHICH producer fires after four fixes failed to pin it.
- **Stuck in prone on slopes** (bug-2547). Watch that nobody rises THROUGH something: the escape is
  capped at 40 u out and 18 up and the destination still traces, but the reachability trace is
  skipped while embedded. `^~^~^ PRONEUNBURY` marks the last resort.
- **m4l3 barn see-through** (bug-2549). `cull none` dropped from `jh_fence1`. Check the stall fences
  read from BOTH sides - the pairing scan covers all 160 maps but is a static argument, not a look.

### e1l2 dedicated map-checksum residual (bug-2585)
`PARTIAL` - the longjmp crash is fixed (a client forcing `r_largemap 1` mismatched `sv_mapChecksum` and now
drops cleanly instead of crashing). **M2 deferred:** having the client follow `sv_mapChecksum` so it matches
rather than drops.

### global/spotlight.scr: 5 Script Errors per spotlight per map load, and a gunner that never fires
`OPEN` · *bug-2548* — `self.gun` on an Actor is an `EV_GETTER` returning a display-name STRING
(`actor.cpp:2616`), so `self.gun.angles` throws at `:286` and the next two statements cascade on the
`none`; every TurretGun event sent through `self.gun` is a no-op for the same reason. The intended
receiver is already a targetname in `self.spotter.turret` (`:400`), resolvable with `$(...)` as
`:389` does. Same family as bug-2046.


### e3l4: jeep supply run + AISpawnPoint/PathNode — RESOLVED (verified 2026-09-15), playtest-nice-to-have
`CLOSED (code)` · The jeep passenger freeze was fixed by a 2026-08-04 cluster in `maps/e3l4/Bunker1.scr`
(bug-1368 `turndone`→`wait 0.5`, bug-1369 new `passengerGetInWillys`, + 1361/1366/1370). The AISpawnPoint/
PathNode spawner death (bug-1471) was fixed hours later by bug-1480 in `global/ai.scr` (spawn-point
classnames excluded from the chain-flattening terminal test). Would benefit from one playtest confirm.

### Pinned challenges: no in-mission pin surface
Lobby and disconnected Service Record can pin; the in-mission `chal_menu` panel cannot — no cursor,
and the lobby cursor's click is `BUTTON_ATTACKLEFT` (`player.cpp:13559`) so reusing it would fire the
weapon and swing aim. Needs a `game.dll` change. Disconnected pins queue and apply on next
connect. bug-1362/1364. (The separate STUCK-pin defect, a finished challenge never leaving the list,
was fixed 2026-09-09 as bug-2544.)

### e2l2: 12× "applied to NULL listener" — UNCERTAIN (may be a decoy-log phantom)
`OPEN?` · *bug-1220* (detected 2026-07-29). No later buglog entry closes it, and `maps/e2l2.scr` still has a
few unguarded refs (`$getvickers`/`$allhell_vehicles`/`$spawnlyndon nottriggerable`, ~lines 71/151/152) - so
guarding them with BOTH `NIL` and `NULL` ([TRAPS T5](TRAPS.md#t5)) is a cheap win. BUT the original detection
came from the now-**decoy `%APPDATA%` log**, so it may already be gone. Verify on the live log before fixing.

### t2l2: 265 boot errors — RESOLVED (verified 2026-09-15)
`CLOSED` · *bug-1026* was split and fixed: bug-1891 ("VERIFIED zero boot errors", the 4× holster load) +
bug-1892, and bug-1481 (mg42-on-PathNode spam). What remains is retail TIKI data noise (`surface 'inside'`
warnings), not HZM script errors. Residual bug-1472 (3× `waittill death/drive`) is a minor diagnostic.

### Phase C stealth contain (m2l2a) — shipped, mostly unverified

The contain loop itself IS play-verified end to end (bash -> stun -> pistol -> kill -> 10s clean ->
"Situation Contained" -> papers restored; user: *"Situation contained worked"*). Everything built
around it on 2026-08-10 is deployed and **not** confirmed in play:

- the **15s loiter -> cover blown** outcome (the investigator itself IS verified: bug-1695/1696)
- escalation firing the real alarm via `trigger $waittrigger_alarm_master`
- "seeing the stun animation" as an escalation route
- the Naxos room/hold prompts and the sabotage progress bar
- the squad-wide papers free-pass CODE (bug-1693) - the observed behaviour comes from the engine
  demoting an accepting sentry to a saluter, so the new path has never run

Since confirmed in play: the contain loop, the escalation loadout (1692), the bust-time aggro
exemption (1686).

### m2l2a attackplayer-latch removal (bug-1700) — CLOSED, user-verified
`CLOSED 2026-08-11` · bug-1700 reworked the aggro funnel (`sentientIsSeen`/`attackentity` branch); the latch
split closed via bugs 1707/1708. **Acceptance test PASSED** - full m2l2a stealth run by the user, zero Script
Errors / salute flips / latch restores (vs 1789 in the broken run), verdict "m2l2a ran fine". No longer a
risk. (The line-78 array-cast that the OPEN list once cited is also gone: `$player.has_disguise` now sits in a
`gametype==0` SP-only branch, unreachable in coop.)

### `coop_stealthArmOnHurt` is dead code — and something else may be covering for it

Defined at `itemhandler.scr:1423`, **threaded by nothing anywhere** (bug-1688). It is the watchdog
that arms an unarmed player who is being shot. Deliberately not enabled mid-playtest. **Open
question:** with it dead, what arms a player shot while unarmed? `maps/m2l2a.scr::coop_blownOnDamage`
polls player health and threads `coop_armOnBlown`, so m2l2a may be covered *by the map* — which would
mean every other `coop_noWeapon` map has no such safety net at all. Worth one grep before enabling.

### A hand-rolled distance returned a wrong value once and could not be reproduced

bug-1690. `sqrt( (dx*dx) + (dy*dy) )` gave 265.965 for points 2013u apart, twice, then computed
correctly at a different position. **Mechanism unexplained; no trap entry claims one.** All affected
sites now use `vector_length` on flattened points. `coop_mod/aimaneuver.scr:129` uses the same inline
form and has never been checked.

### objectives.scr's NEW OBJECTIVE toast collides with two live features

bug-1680. It owns 135-142 (header 135, lines **computed** `136 + local.line`), overlapping the DBNO
team-revive channel (135-140) and the XP micro popup (142-144). All three are mission-time and can
co-display. Not fixed by relocation: rewriting a widget that currently works is a blind bet with no
oracle (TRAPS T3 UI corollary). Moving the toast into the menu-only 216-249 range would fix it
properly and return eight fade-exempt slots — **the ≥100 band is now completely full.**

✅ **The DBNO half is closed both ways as of 2026-08-30 (bug-2175).** The original fix only made the
toast WAIT for a player who was already down; a player who went down *while* the toast was up still
had the revive prompt and both bars zeroed by its unconditional teardown, and `local.shown` is a
latch so nothing ever redrew them — blank HUD for a 90-second bleed-out. `dbno.scr` now watches
`level.coop_objToastBusy` and clears the latch on its falling edge, so the worst case is a 0.1s
flicker. **Still open: the XP micro popup (142-144), which has no such re-assert.**

### Second vehicle-crew spawn path on t2l2 / t3l2 still unguarded
`OPEN` · *`_research/coop_2player_sweep.md` residual list* — the `vehicles_thinkers.scr` NIL-crew guard
fixed the jeep maps but a **different function** spawns the halftrack and T-34 crews (t2l2 25 casts,
t3l2 8). Named in the audit's own residual list; no follow-up found in the buglog.


### Dedicated server segfaults on bare DM maps
`OPEN` · *bug-330* — `game.dll` crashes loading `obj`/`obj_team1` under a dedicated server. Baseline
reproduces with **zero rendezvous cvars**, so it is not NAT-related. Coop maps load fine — likely a
coop hook assuming coop init ran. Fix: "none yet." ⭐ Also recorded: `omohaaded.exe` has headless env
quirks (stalls **with** `fs_homepath`, dies **without** it); the working dedicated recipe is the
**CLIENT exe with `+set dedicated 1`** from the GOG dir.



### AI crouch posture stays disabled (crouch leg was the crasher); prone is BACK
`PARTIAL` · *`anim/attack.scr`* — the recorded crash lived in the CROUCH leg only
(`AttackLongRangeCrouch`→`AttackCrouchDodge` command overflow; repro: m1l1 barrels), so crouch
stays hard-zeroed. Prone re-enabled 2026-08-18 behind `coop_aiRetailProne` honouring
`level.aipronechance`, plus a dwell loop (bug-1922) so divers stay down 3-6 volleys instead of
popping straight back up. Prone feel awaits playtest; crouch needs an engine fix first.

### ET3 engine jink is built and dormant
`OPEN` · *`actor_turret.cpp State_Turret_Combat`* — `coop_aiJinkMs` default 0 because the rig caught it
never firing. Dead member `m_iCoopJinkTime` remains. A re-do needs forcing it from the retarget path
or gating to aggr-role TURRET enemies.

### Airborne black-texture patch — 4th report in the same family
`OPEN` · *bug-921* — four separate fixes against the same visible symptom (bugs 499/525/530/921). A
later 5-round resolution via the shader-isolation recipe is attributed to bug-922, **but bug-921 was
never marked resolved.** Cannot determine from the record alone whether the airborne pouch is
currently correct. **Needs one look.**


## gl2 open items

### Non-depth-writing surfaces can't be fogged — RESOLVED (doc stale)
`CLOSED` · The screen-space-fog structural gap (bug-1296: blended, non-depth-writing surfaces leave depth
1.0, so a depth-based pass never reaches them) was closed by **bug-1304**, which shipped a **forward
per-fragment global fog** — `r_globalFogForward` (default 1, `tr_init.c`) with `ApplyGlobalFog()` in
`glsl/generic_fp.glsl` + `lightall_fp.glsl`, wired in `tr_shade.c`. That fogs per-stage in the forward pass,
exactly the "coherent hybrid" this entry's 2026-08-02 analysis said would need an expensive stencil. (History
of the rejected screen-space fixes: [archive](archive/).)

### The retail sky sources are 512×512
`OPEN` · *bug-1295* — gl2 no longer DXT1-compresses them (that was ours), but the source itself is
512² per cube face and reads soft at modern resolutions. Upscaling is possible but must be done as a
**set** — faces are upscaled independently by any tool, so cube-edge seams can drift, and ESRGAN
hallucinates detail that reads as mottling on smooth cloud gradients. User is willing "unless there is
risk of it looking worse"; decide only after seeing the uncompressed 512.

### `Z_TagMalloc` zero-size spam on the main menu
`OPEN` · *`bug-gl2-ztagmalloc`* — `Z_TagMalloc, Negative or zero size 0 tag 12` every gl2 menu frame;
the same A/B menu boot under gl1 is clean. Cause unknown. ⭐ The investigation **did** close off a
wrong theory: the widget UI otherwise renders fine under gl2 (What's New board, text, buttons all
draw), so the "`.urc`-invisible / FBO-ordering" theory is **dead**. Next step: find what tag 12 means
and grep `Z_TagMalloc` callers missing a size-0 guard.

### Bullet-hole decals render RED — RESOLVED (doc stale)
`CLOSED` · The 2026-08-02 restraint entry (`bug-gl2-decal-red-dds`, refused to guess) was superseded by
**bug-gl2-reddecals**, which found the real cause: gl2's `R_GetLightingForDecal` was an **empty stub**
leaving `vLight` as uninitialised stack garbage (cgame multiplied it into red). Now fully implemented
(`tr_light.c`, registered in `tr_init.c`). Resolved-pending a visual confirm.

### Invisible briefing NPC on e2l2 — likely fixed, PLAYTEST-GATED
`PLAYTEST` · `$lyndon` invisible in the e2l2 intro cinematic (`bug-gl2-e2l2-briefing-npc-invisible`). Very
likely fixed as a side-effect of the later gl2 root-cause fixes for the same actor class
(`bug-gl2-forcepose-skips-composite-ally`, `bug-gl2-invisible-live-char-depthprepass`), but never re-checked
for the intro. One look confirms.

### `r_globalFogDebug` is still `CVAR_TEMP`
`OPEN` · *`renderergl2/tr_init.c:1926`* — temporarily moved off `CVAR_CHEAT` because a listen server
runs `sv_cheats 0` and clamped it back to 0, so the debug views could never enable (the first run
produced 3 identical captures). **Restore it to `CVAR_CHEAT`** at scaffolding-strip time.

### Diagnostic scaffolding not yet stripped
`OPEN` (deferred deliberately) · ~90 interleaved sites, kept for cause (`CMDTRACE`/`IMM2D` solved bug-1144,
`r_globalFogDebug` still in use, heavy probes gated behind `r_skeldiag` 0). Loose ends at strip time:
`r_globalFogDebug`, and `tr_model.cpp`'s ungated `SKELREG`/`SKELDIAG`/`SKELDRAW` (deduped once per model
handle, `tr_model.cpp:50-51`, so bounded by model count not frame rate).

---

<a name="diagnostic"></a>
## Diagnostic pending — a probe exists, awaiting one boot

---

<a name="unverified"></a>
## Awaiting playtest — `SHIPPED-UNVERIFIED`

The full list is [FEATURES.md](FEATURES.md). These are the ones someone consciously stopped short on:

| Item | Note |
|---|---|
| Prone, whole feature (2026-08-25 build) | UNPLAYED. Same-day rewrite of the exit into an edge-trigger (hold crouch to go down, release does nothing, press crouch or jump to get up), plus the PM_Friction floor fix that made crawling possible at all, plus both speed floors respecting prone. Three separate defects, none of them playtested together. |
| Prone reload (3rd attempt, `coop_proneReloadFlat`) | UNPLAYED. The real per-weapon reload runs with its torso RENDER weight zeroed while prone, so the duration is unchanged (substituting an anim dropped the `reloadweapon`/`clip_fill` notetracks, bug-2115). Retail .skc: pistol_prone_reload 1.50s, Kar98 3.37s. KNOWN COSMETIC RISK: the `attachtohand` notetracks still run, so the weapon moves to the support hand and back while the body stays flat. Verify with a Kar98: prone vs standing time-to-fire-again must match. |
| Standup clearance trace | The `STANDUP` probe is deployed and unread. It is the last unknown behind BOTH 'cannot prone here' and the old stuck-prone: the trace refuses on ground where a crouch box should fit. Probe prints startsolid/allsolid and the box. |
| Stress -> weapon spread | Chain verified on the harness by forced injection (coop_stressDebug 2); the BULLET HOOK is unverified - harness AI never shot the test bots (m2l2a is stealth, and on m3l1a they stand at spawn). `coop_stressDebug 1` in a real firefight, check `hits=` climbs. |
| **Headshot gore chain** (bug-1142) | Sandbox-verified 10/10 on m1l1+m3l2 and 20/20 kills; **play rollout staged** |
| **13-bit `frameInfo` anim-index widening** | Open task **#16** to verify — may or may not fix bug-1213 |
| **`coop_unsponge`** bullet-sponge sweep (bug-1212) | Landed in the last hours of the mined window |
| **Officer heal budget** `coop_officerMaxHeals` (bug-1215) | Same |
| **gl2 frozen-clock fix** (bug-1147) | Author's own note: *"not eyeball-verified — needs a menu with an animated shader"* |
| **gl2 AO and foliage fixes** | |
| **Tank MG gunner slot** | Prototype; needs m5l2a/b tuning for seat position, weapon, exposure |
| **AI combat "feel"** (`coop_aiRetargetMs` etc.) | Verified *firing*; the felt effect needs a listen-server playtest — the bot's fixed ~350u anchor sits in the vanilla mid-band |
| **Stale-objective wedge self-heal** | Untested live |
| **All four gore tiers** | Built + deployed, untested in-game |
| **NAT hole-punch phase 1** | Signaling verified locally; **no real-world friend test** (blocked on a VM). Engine commit records an unresolved dedicated-server crash "under investigation" with no follow-up. |
| **Jeep passenger seating** | Untested multi-player |
| **XP system phase 1** | Built 2026-07-07, untested |
| **Weapon + cosmetic unlocks** | Built 2026-07-16, untested |
| **Armory carry-over volleys** | rcon-verified at the wire level; untested live |
| **Menu theme picker** (2572) | UNPLAYED. Random per launch, Next/Back, title + game. First build was compiled out; this one is checked in the exe. |
| **Leave-map audio reset** (2573) | UNPLAYED. Leave Omaha mid-cinematic, load any map: ambience audible, music normal, `AUDIORESET` logged. Also `restart` and a crash relaunch. |
| **Field Settings / Host Rules sheets** (2578) | UNOPENED. Check the invisible whole-row toggle first (fallback is in the `ui/coop_settings.urc` header), then fit, the two float sliders, and HOST RULES on Start Game. |

### Awaiting runtime verification after the next deploy (2026-09-13)
- **SEC1 layer 2** (bug-2580 follow-up, dab3af77) - built + self-tested; needs a runtime covtrace pass on a dedicated server.
- **Better shadows** (69cdb4d7) - a before/after once the raised gl2 shadow cvars deploy.
- **Modern compass bar** (2581 area) - bar/toggle/objective marker/MP isolation are verified on m1l1/m2l1/m3l3; teammate markers, vehicle seats and the resolution matrix are not.
- **Field Settings / Host Rules** (2578) - unopened in game (row above).

---

<a name="planned"></a>
## Planned, not built

| Item | State | Anchor |
|---|---|---|
| **Coop test menu** — 94 tests across 10 subsystems, each with catches/drive/verify/evidence/risk | **The largest designed-but-unexecuted work in the project.** Several named probes exist, so parts may be built. **No run log or results file found.** Either schedule it or explicitly retire it. | `_research/coop_test_menu.md` (132 KB) |
| **Bipod / supported aim** | Verdict: BUILD a weapon-stance supported aim (~250 LOC, game.dll + pk3); REJECT the turret-swap approach. Needs no new usercmd bit, no new PMF, no new stat. | `bipod_design.md` |
| **Limb dismemberment** | ⚠️ Read bug-861 and bug-892 first — the phase-0 precursor shipped and was pulled the same week. | `_research/limb_dismemberment_plan.md` |
| **Cover-peek physical step-out** | User verdict on peek v1: *"VERY janky - you dont actually pop out from the door opening."* Root cause understood: peek v1 only releases the torso and swings the camera; **the BODY never physically steps toward the corner**, so the muzzle stays behind the wall edge. Design queued: slide origin ~24–32u toward the detected open side (traced, collision-safe), slide back on release, keep velocity zero. | bug-311 |
| **Jeep .30cal manning pose** | Measure-first, explicitly not to be guessed. | bug-309 |
| **Blender sprint carry-pose** | Pipeline 100% working; **the user paused mid-edit** at arm-bone selection. | `blender_sprint_edit.md` |
| **Installer** | Built (Inno Setup 6, git-tracked). **DO NOT EXECUTE until explicitly asked.** | `installer/hzm_coop.iss` |
| **gl1 post-FX → gl2 ports** | 7 remaining; bloom is the template. | see [gl2](#gl2) |
| **Shadow mapping Phase B/C** | Not started. Phase A decal shadows shipped and user-approved. | `shadows_status.md` |
| **NAT phases 2+** | Phase 1 committed and locally verified. | `nat_holepunch_plan.md` |
| **Weapon-weight Phase 2** | Movement drag + rotational muzzle swing. | `weapon_weight_research.md` |
| **m3l1b FLAK objective v2** | Gun crews, back-field defenders, plant animation. | `m3l1b_cut_flak88_objective.md` |
| **Deployables skill tree** | **REJECTED by the user** — building their own model. Doc kept, marked superseded. | `skilltree_plan.md` |

**gl2 render upgrades** (designed 2026-09-13, `_research/gl2_render_upgrades_design.md`) — **BUILT + SHIPPED**
in `renderer_opengl2.dll`, menu-wired (`coop_postfx.urc`), seeded (`coop_defaults.cfg`). Verified in the
engine 2026-09-15: exposure-aware bloom (`r_ppBloomMode 1` default), render-scale supersampling + FSR1
(`r_renderScale`/`r_fsrSharpness`, 1.0 native default), soft particles (`r_softParticles 1`), MSAA
(`r_ext_multisample`), tonemap/exposure, per-map + night colour grade. ONLY unbuilt: **alpha-to-coverage**
(MSAA shipped as the AA path instead). **Still awaiting a PLAYTEST** to tune/confirm, not code.

**MP armories slice 2** (designed 2026-09-13, **APPROVED, not built**;
`_research/mp_armories_slice1_plan.md`) - engine hooks E1-E7, a live dispatcher, and a side picker to
make slice 1's inert MP-only screens (committed 59fa75d7) reachable.

**Security layer 2 - exe-side server-origin taint** - now **BUILT + SELF-TESTED** (2026-09-13, bug-2580
follow-up), runtime covtrace pass pending (see Awaiting-verification above). Filters EVERY server-origin
line in the exe; a refuse-list for self-vstr'd cvars (no persisted taint); `globalwidgetcommand`
laundering stays a residual; a real cgame API handshake (v3->4).

Reference design notes, do not duplicate here: `hzm-mohaa-coop-mod/_research/compass_bar_design.md`,
`mp_decisions_2026-09-13.md`, `koth_source_notes.md`.

---

<a name="discrepancies"></a>
## Record-vs-code discrepancies

Moved to [archive/open-record-vs-code.md](archive/open-record-vs-code.md) - they are documentation
corrections rather than open defects, and the code is authoritative in every case.

## Tooling lost

Still missing, all generators for already-shipped artifacts (what IS present: `docs/generated/filemap.tsv`):

| Tool | Consequence |
|---|---|
| `gen_gore_skins.py` | Blood-mask skins un-regenerable (bug-817 reverted them to a specific coverage) |
| `gen_cosmetic_unlocks.py` | Cosmetic unlock tables un-regenerable |
| `split_options_persist.py` | Named in `coop_defaults.cfg`'s own line-2 header as that file's generator |
| `coopaudit/fourplayer_trig.ps1` + `coopaudit/REVERT_botinput.md` | Cannot re-run the 4P combat rig; no recorded revert path for an engine change still live in `player.cpp` |

**Rule:** anything under `%LOCALAPPDATA%\Temp\claude\...` is session-scoped and will vanish. A tool
worth citing belongs in `docs/tools/` or `scratchpad/` with a note here.

## Config

### Nine post-FX cvars were menu-wired AND force-reset by `autoexec.cfg` every launch
`FIXED 2026-08-30` · bug-2172 · *all nine now commented out in `autoexec.cfg`; seeds live in `coop_defaults.cfg`*

`autoexec.cfg` execs **after** the saved config (`common.c:1864`) while `coop_defaults.cfg` execs
**before** it, so a `seta` in autoexec re-forced the default every launch and wiped the player's slider.
`r_ppLowHealthStart/Amount/Beat` were fixed earlier; the six left behind (`r_ppSharpen`,
`r_ppSharpenAmount`, `r_ppHeatAmount`, `r_ppRainDrops`, `r_ppRainAmount`, `r_ppMuzzleRadius`) are now
commented out too. The other 4 `r_pp*` lines (`MuzzleX`, `MuzzleY`, `SunShaftDecay`,
`SunShaftThreshold`) are correctly non-menu and stay.

⚠ **The old "strictly disjoint / zero double-seeding" note here was WRONG** — a `comm -12` on the two
files' `seta` token sets returns **17 shared names**, and `r_ppSharpenAmount` conflicted outright
(`coop_defaults` 0.779370 vs autoexec 0.35). Re-run that `comm` before trusting any disjointness claim;
the remaining 11 shared names are not yet triaged.

### `coop_*` cvars seeded nowhere — the consequential count is ~278 (not 144)
`OPEN` · Re-counted 2026-09-15 from `docs/generated/CVARS_COOP.md`: of 3380 distinct `coop_*` cvars, 1205 are
seeded nowhere, and **278 of those are read by a script** (the bucket that matters). The old "144" is stale.
For these, `getcvar` returns `""` on a clean profile and a script fallback branch silently decides behaviour
- **documenting such a cvar as "default N" describes a branch, not a default.** Consequential ones: [Never ran](#never-ran).

### The bug-595 0-byte `omconfig.cfg` decoy — REMOVED (verified 2026-09-15)
`CLOSED` · `%APPDATA%\openmohaa\maintt\omconfig.cfg` no longer exists (the dir still has autoexec/boot_*.cfg).
The 0-byte decoy is gone; the trap is closed.

---

<a name="cheapest"></a>
## Cheapest wins, roughly ordered

Effort/impact ranking was the audit's own acknowledged gap; this is an inference from signature, not a
measurement.

Most of the original 10 are resolved (2026-08/09). The two that remain:
1. **Deploy the current `openmohaa.exe` + `game.dll`.** A copy. Resolves bug-1219 and the protocol
   mismatch. Back up first. *(User action — binary deploy.)*
2. **Take one fresh look at the m3l3 courtyard.** The fix exists and was never evaluated. *(Playtest.)*

## GL2 RENDERER: styled-lightmap surfaces pulse red (was: e2l1 rails) - FIX SHIPPED, AWAITING PLAYTEST
Root cause + fix in bug-1331 (the rend2 deluxe parity heuristic in `tr_bsp.c` misfired on MOHAA BSPs;
loader now honours `r_deluxeMapping`, autoexec ships it 0). **PLAYTEST: e2l1 rails + e2l2 panels no
longer pulse; regression-check HD maps (m3l1a). If clean, flip the engine default in tr_init.c and drop
the autoexec pin.**

## Deploy infrastructure: phantom file locks + a mystery .pk3 renamer (2026-08-04)
Recurring transient locks on `G:\mohaa-gl2\maintt` pk3s (copies fail "in use", hashes verify after), and
once the GOG maintt pk3s were found renamed to `.pk3.stale` mid-deploy by an unidentified actor.
Recovered from APPDATA copies, hashes verified. Suspects: AV/indexer or a leaked watcher child. If it
recurs, audit with Sysinternals `handle.exe` before any deploy.

## GL2: distant objects pop out of / into fog instead of fading (user 2026-08-04, LOW priority)
User (e2l2, night dist=1000 bias=450): "distant objects still pop out". **Explicitly deferred - do NOT
investigate without being asked.** Leading hypothesis: the **model LOD/impostor swap distance**, not the
fog maths - gl2 swaps the oak to its impostor at ~900u (gl1 ~1352u), and at a 1000u farplane fog is only
~78% opaque there, so the swap reads as a pop. Confirm by: pop tracks the MODEL not the fog distance;
`r_uselod 0` does not remove it; gl1 does not pop at the same values. Second candidate: forward global
fog not fully opaque at the TIKI cull plane. Related: the styled-lightmap defect (bug-1331).

## Holdout mode ON HOLD (2026-08-05)
User parked the gamemode for trilogy-wide coop. Untested when parked: officer finale, death->spectate +
wave-end respawn + wipe->missionfailed + 30s cooldown, call radio (cat 44), textured ladder rails, S93
BAR look. The 24-stop candidate map tour stays deployed (`y_hzm_maptour.pk3` + `maptour.cfg`), inert
unless exec'd; round-2 verdicts (stops 15-24) never given. See memory holdout_gamemode.md.

## Coop spawn-point gaps (re-measured 2026-08-07)

**44 of 58 base map labels carry start coords**, and 26 have `_updateN` checkpoints on top; the retired
2026-08-05 audit's "20 maps author none" figure is wrong. Genuinely without start coords (14), and only
three of those are real gaps:

| Label | Status |
|---|---|
| `m2l2b` | **REAL GAP.** No start coords; first coverage is `m2l2b_update1` at a mid-map trigger, so map-load to that trigger is uncovered. Needs one point. |
| `t1l1 t1l2 t1l3 t2l1 t2l3 t2l4 t3l1 t3l2` | Labels exist but are empty, so players fall back to the engine default. The 07-22 live-boot audit verified all boot coop-ready and spawn fine - **polish, not a hole.** One start point each. |
| `m1l1`, `t2l2`, `m6l3a` | Intentionally empty - players are glued to a truck / halftrack / train at spawn, so ground points do not apply. |
| `e1l3_finalEscape`, `e1l3_lockPicking` | Not maps - sequence sub-labels. |

`m3l1b` was the one map with **zero** coverage end to end; closed 2026-08-07 (start spawns +
`m3l1b_update1` on the map's own `level.clear_bunker >= 6` gate).

**Capture note:** `viewpos` prints `cg.refdef.vieworg` - the EYE. Spawn origins are feet, so subtract
`DEFAULT_VIEWHEIGHT` (**82**) from every captured z, or actors spawn head-height in the air and clip.
Its yaw also accumulates past a full turn (-422, 667), so normalise into 0..360. Build mode's `P`
marker uses `player.origin` and needs neither correction.

## Sweep-blocking maps (2026-08-06) - RESOLVED, sweep-harness confirm outstanding
Both maps' specific blockers are fixed (verified 2026-09-15); what's unconfirmed is a clean shared-session
sweep, not a live defect:
- **m2l2a** - the spawn-killing raw waittills (bug-1458) and the `Cannot cast 'array' to listener` are both
  gone (the disguise line is now in a `gametype==0` SP-only branch; see the closed bug-1700 entry above).
  m2l2a stealth was user-verified. Residual: bug-18390 notes a gametype-restart race exposed by disguise maps.
- **m3l3** - the restart loop was closed by the bug-1463-1467 chain (2nd/"third" door + engine mission-fail
  guard + phase-3 restart gate); the sweep-miss was a `Pak*.pk3` capital-P glob (bug-17348). It has had heavy
  feature work + playtests since (church-defense objective, bugs 1806-2035) - it boots and runs normally.

### e3l4 AI spawner threads die on AISpawnPoint/PathNode (bug-1471, OPEN)
`global/ai.scr:1037` does `self waittill trigger`, but on e3l4 that thread is started on
AISpawnPoint (x5) and PathNode (x1) entities, which cannot be waited on that way - the throw kills
the spawner thread and its AI set never spawns. Confined to e3l4 across the entire trilogy sweep,
so it is that map's spawner wiring (likely a targetname collision), not a global defect. Fix the
collision at source rather than adding a blind skip, which would hide the wiring error.

### Unwired challenges — CLOSED (every challenge now has a producer)
`CLOSED 2026-09-15` · `docs/tools/check_challenges.py` (run by `build.ps1` every build) reports
`challenges: 445 | stat writers found: 188` → **"OK - every challenge has a writer, a reachable target and
a real reward."** Zero unwired. The old "25/49 still have no producer" (bugs 1596-1598) was a mid-cleanup
snapshot; the remainder were wired or cut. Caveat: the validator checks producer *existence*, not
correctness - the bug-1597 unconditional-bump class is orthogonal and, if still live, belongs in its own entry.

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

- **Omaha frame rate (bugs 3483/3487/3488/3490/3491) - 52 -> 32 ms (v1.10.20) -> 21.7 ms (release-1.10.21,
  UNRELEASED), solo, dev PC; the tester's CPU is ~0.6x.** Added since v1.10.20: worker-thread skinning, skeletal
  view cull, emitter filter, config-write fix. What is left is not skeletal: driver cost per batch, sprites, cgame.
  m3l1b solo sim is light (1.5-8.7 ms). Owed: a clean 4-player number (host server+AI ~7 ms), the tester's PC.
- **The beach aim cone is un-tuned.** The guns ARE actor-owned, so `bulletrange` is live, but it is an accuracy
  divisor, not a reach limit (rounds travel 16216 regardless, bug-2439). The named lever is
  `level.coop_beachSpread`; better, raise `level.target_offset` from 55 toward 64-70 to recentre on the
  head-height zing band.
- **Out-of-breath audio is still owed by the user.** `coop_uw_airout` / `coop_uw_wake` are armed no-ops until
  the wavs and aliases exist (`RAMPUW airhook armed`). 22050 mono 16-bit into `sound/coop_tinnitus/`
  (duck-exempt; anywhere else is inaudible).
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

Engine + script bot-verified; client-rendered parts need a real machine. The armory/appearance/service-record
detail and the preview helmet-double (Allied `_nohat` twins exist, Axis don't; live spawn correct via nodraw) are
carried by the **2026-09-20 session block below**. The MP framework engages on ALL dm maps (stock `mohdm1-6`) +
`obj/mp_*` (bug-2638); Push/Base-Assault keep their own Campaign-Maps pickers for the SP maps.

### MP session (2026-09-20) — progression persistence FIXED, rank card SHIPPED, menu-parity roadmap
- **PROGRESSION PERSISTENCE — engine fix DEPLOYED (bug-2749), needs ONE live client playtest.** The carry cvars
  were USERINFO-registered only in cgame CG_Init (connect-time, too late), so the signed blob never reached the
  server (`MPPROG load VERIFIED`=0 always). Fixed by registering all 19 at CLIENT LAUNCH in `cl_main.cpp CL_Init`.
  **VERIFY:** kills → disconnect → reconnect (same then different server); log should show `MPPROG load VERIFIED=1`.
- **MP END-OF-ROUND RANK CARD — SHIPPED + code-path verified (bug-2751).** `xp.scr::xp_mp_roundcard` draws a debrief
  in the pre-next-round pause (emblem, +XP, bar, PROMOTED; HUD 160-167), wired into `push_win`+`rounds_win`. The
  rank-up **bar + ceremony already fired in MP** via `xp_award_mp`; this card was the missing visual. **VERIFY** the
  emblem/bar render on a real client (devboot confirmed `MPROUNDCARD shown`).
- **MENU PARITY (user 2026-09-20: "MP menus as good as coop"). DONE this session (detail in buglog):** armory default
  label fixed off Panzerschreck (2752); WEAPON FINISH moved Appearance→Armory (2753); cosmetic LOCK display (padlock +
  "Unlocks at N kills") added (2755); SR graphical PROGRESS BARS added, reusing coop's `coop_bf*` art (2756);
  **preview helmet-DOUBLE FIXED** (2754 — vstr-free body-swap: viewer body = `_nohat` twin + the skin's baked hat as an
  attached Standard-Issue piece, `SKIN_STD`); **skin DEPTH** allied 12→24, axis 12→18 (2757, each with a twin + std
  piece; auto-fit menu layout). **All of these render only on a real client — the bars, the preview de-double, and the
  new skins' fit need your eyes.** **STILL OPEN (need art / an engine command / curation):**
  - **Preview fit verification.** The 30 skins' twin+piece pairings should look right (allied reuse coop's fit-tested
    pairs; axis map to matching German/Italian pieces) — but confirm on a client; report any helmet that sits wrong.
  - **Deeper skin depth** toward coop's 135: more allied is pure `skinGet` rows (twins+std already exist); more axis
    needs a `_nohat` twin generated per skin (`gen_axis_nohat.py`, ~1 line each once its headgear is classified).
  - **SR pins/favorites + MEDALS view.** Pins need a client command like coop's `coop_pintoggle` (`CL_PinToggle_f`);
    medals + page background art are **new art assets** I can't author. Coop ref: `ui/coop_sr.urc`.

## Awaiting the next playtest (2026-08-17)

Archived 2026-11-01 to `docs/archive/open-awaiting-playtest-2026-08-17.md` (stale; check there before re-reporting an August item).

## Defects with evidence

### End-of-mission debrief, take two - branch `debrief2`, not merged (2026-11-03)
cgame-drawn debrief (sheet, animated rank bar, 256 px vector insignia, one unlock card at a time with its picture,
USE/JUMP skip): mod `debrief2`, engine `debrief2`, art + `gen_debrief2.py` on workspace `debrief2` (bugs 10479-10483).
Verified on the harness at 4:3, 16:9 and 21:9 and with skips; NOT yet: sound by ear (harness is muted), a remote client
on a dedicated server, two players with different lengths (server holds `level.coop_db2Need`, cap 40 s). Ships as a SET:
cgame.dll + code pak (shader, scripts) + fixes pak (`textures/hud/coop_db2`). `proposals/debrief2_2026-11-03/README.md`.

### Aircraft call-ins - awaiting playtest (2026-10-05)
Seen in engine: smooth flight, V of three, door exits (m2l1). Not yet seen: a Stuka shot down and crashing, Doppler by ear, fog see-through (e1l1), above-sky flight (m5l1a). `proposals/aircraft_2026-10-05`.


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

### SECURITY: Report a Bug is server-injectable; desktop reports leak the webhook (bug-3276/3277) - STAGED
Servers can set any `coop_*` cvar; the shipped sender puts `coop_reportWebhook` inside `'...'` on a PowerShell
command line (code on SEND). Desktop zips carry omconfig.cfg's archived webhook, IPs, user paths, unlocks, raw dumps.
Fix: `docs/proposals/bugreport_parity_2026-09-29` (exe + pk3 + report_problem.ps1 + updater.ps1, one set); then a
relay + webhook rotation.

### e1l2 dedicated map-checksum residual (bug-2585)
`PARTIAL` - the longjmp crash is fixed (a client forcing `r_largemap 1` mismatched `sv_mapChecksum` and now
drops cleanly instead of crashing). **M2 deferred:** having the client follow `sv_mapChecksum` so it matches
rather than drops.

### Pinned challenges: no in-mission pin surface
Lobby and disconnected Service Record can pin; the in-mission `chal_menu` panel cannot — no cursor,
and the lobby cursor's click is `BUTTON_ATTACKLEFT` (`player.cpp:13559`) so reusing it would fire the
weapon and swing aim. Needs a `game.dll` change. Disconnected pins queue and apply on next
connect. bug-1362/1364. (The separate STUCK-pin defect, a finished challenge never leaving the list,
was fixed 2026-09-09 as bug-2544.)

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

### v1.10.4 integration - APPLIED 2026-09-28, awaiting playtest (all `U`)
Committed to coop-wip / hzm-coop-working, not deployed; engine candidate set = scratchpad `v1104a` (manifest.md).
- **Storm darkness** (bug-3211..3214, 3222, 3223): `coop_storm_on` now returns 1 (default ON; `coop_stormLight 0` = off),
  variable storm length + forced-value fix in. MP arenas stay off (`coop_mpStorm` default 0). Owed: a rain-map play.
- **m3l3 rocks** (bug-3210): 117 fitted clip boxes + 15u-inset path cut (`maps/m3l3/rockclips.scr`). Owed: playtest the
  field east of the start (run 26 = rock 11's shoulder, move it ~12u south if wanted).
- **Hardcore no enemy medkits** (bug-3187); **loadout once per spawn + slow-server icon hidden** (bug-3208/3209; owed:
  icon screenshot pair); **spotlight gunner fires** (bug-3194; m1l2a/m4l2 get harder); **officer client-0** (bug-3195);
  **t2l2 dismount / t3l2 driver** (bug-3196/3197); **MP F7 before first spawn** (bug-3198, owed: one client).
- **Briefing slides, cards and SH/BT films for joiners** (bug-3234, all shipped v1.10.4). The film never started
  on a LISTEN host until bug-3526 (`stuffsrv` open line; fixed 2026-10-12, unreleased).
- **StG 44 pop** (bug-3207, cgame); **foliage shadows** (bug-3224, gl1+gl2 + `zzzzzzzzzz_coop_foliage_lm.pk3`; its pak
  patches e3l1/e3l2 Monte Cassino lightmaps too - confirm vs the "never touch Omaha" rule); **loading-art pool**
  (exe + mod; jpgs in `zzzzzzzzzz_coop_loadart.pk3`). bug-3196's tik ships in `zzzzzzzzzz_coop_fixes.pk3` (bug-3251).
- Staged: sweep #2 item 8 (slot 142, needs screenshot), item 9 (m4l2 door, bug-3201). Dust (f9975dc4): GIF ok + playtest.

### m3l1a Sherman cover clips likely lie across the hulls (found on bug-3210)
A `script_model` box TURNS with its angles (ScriptSlave sets `EF_LINKANGLES`), so the Y-long clips in `coopified.scr`
~1070/5589 (sized for yaw ~90 on the opposite belief) likely cross the hulls - candidate cause of bug-2211.

### A hand-rolled distance returned a wrong value once and could not be reproduced
bug-1690, mechanism unexplained. aimaneuver.scr's four remaining sites use `vector_length` since v1.10.4 (bug-3200).

### objectives.scr's NEW OBJECTIVE toast collides with two live features

bug-1680. It owns 135-142 (header 135, lines **computed** `136 + local.line`), overlapping the DBNO
team-revive channel (135-140) and the XP micro popup (142-144). All three are mission-time and can
co-display. Not fixed by relocation: rewriting a widget that currently works is a blind bet with no
oracle (TRAPS T3 UI corollary). Moving the toast into the menu-only 216-249 range would fix it
properly and return eight fade-exempt slots — **the ≥100 band is now completely full.**

The DBNO half is closed (bug-2175). **The XP half (slot 142) is STAGED OPT-IN as bug-3199** (popup skips 142 while a
card is up and yields on the hudresend generation) - apply only after an engine screenshot of a kill during a card.

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

### Sky upscale + ground/tile texture paks - STAGED for the next deploy window (2026-09-26)
`STAGED` · *bug-2937/2938/2942/2987/2991/2994* — clouds ON; box seam pass done, `HZM_SKYHD_AUTO 1` in renderer
cee3a940 (not deployed). Staged in the mod folder: skies seam pak, tilefix v2 (120 tex, `5712772b`), terrain v4
(`a7fd6d81`, +19 MP-only ground + relief siblings; rebuild it if tilefix changes). In progress: corner rebuild for
mohnight1/lighthousesky/mohday1/mohday2/nordawn. Check in game: mp_stadt_dm church floor, mp_bazaar_dm, mohdm4
riverbed. **Omaha rule: dday2, e3l1sky, e3l2sky and all Omaha maps permanently excluded.**

### Terrain relief light grid PARKED (bug-3061, 2026-09-27)
`PARKED` · AUTO 0, code kept; revisit AFTER the B0 world-shadow fix (doubled hard shadows dominate now). m3l3 steps
are real in-engine but wall-hidden: needs an occluder-aware pose. bug-3064: likely LOD history, benign.

### Vehicle headlights - glow (Test A) SHIPPED; manager (Test S) rolled back (2026-09-26)
`PARTIAL` · *bug-2946/2990* — `HZM_HEADLIGHTS_AUTO 0`: the Phase S manager drew nothing on co_lobby8 trucks
(screenshot evidence). Diagnose, fix, re-verify by screenshot before re-enabling. Omaha Beach excluded in-engine.

### Invisible briefing NPC on e2l2 — likely fixed, PLAYTEST-GATED
`PLAYTEST` · `$lyndon` invisible in the e2l2 intro cinematic (`bug-gl2-e2l2-briefing-npc-invisible`). Very
likely fixed as a side-effect of the later gl2 root-cause fixes for the same actor class
(`bug-gl2-forcepose-skips-composite-ally`, `bug-gl2-invisible-live-char-depthprepass`), but never re-checked
for the intro. One look confirms.

### Diagnostic scaffolding not yet stripped
`OPEN` (deferred deliberately) · ~90 interleaved sites, kept for cause (`CMDTRACE`/`IMM2D` solved bug-1144,
`r_globalFogDebug` still in use, heavy probes gated behind `r_skeldiag` 0). Loose ends at strip time:
`tr_model.cpp`'s ungated `SKELREG`/`SKELDIAG`/`SKELDRAW` (deduped once per model
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
| **Loading screen** (bug-3013/3019/3059; in v1.10.1) | User's 5-min check: medal turns, hint changes, no bar. 116 plain-language hints, all code-verified (research 4.9). Next update: looping old<->new medal, installed + in-game gl2/gl1 recorded, user look pending. Memorial: 7-step smoke recipe. Residual: m1l1 ~2 s world block |
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

---

<a name="planned"></a>
## Planned, not built

### 3D Join Game door - CLOSED 2026-11-02
User: the right-hand attic door (MULTIPLAYER, `scenehot "mp"`) "should go into the multiplayer menu" - which it already does (fly-in, then `pushmenu multiplayer`, where Join Game is). Nothing to build.

### v1.10.56 playtest list
Norway hold last 45 s rush, two halftracks never stacked (east fallback + launch lock), pitched-roof perches 1-4 now allowed
(coop_asnCornerTol 6), bipod flush, storeroom gun pick-up after death, CC0 weapon sheets in game (PIAT canvas softer).

| Item | State | Anchor |
|---|---|---|
| **Coop test menu** — 94 tests across 10 subsystems, each with catches/drive/verify/evidence/risk | **The largest designed-but-unexecuted work in the project.** Several named probes exist, so parts may be built. **No run log or results file found.** Either schedule it or explicitly retire it. | `_research/coop_test_menu.md` (132 KB) |
| **Remastered main-menu room** (3D rebuild, `ui_menuRoom` twin in main.urc, default ON per user) | STAGED 09-28 (contact-gated, 2 QA rounds), not applied (mod frozen to v1.10.3). In-engine test harness ready; needs slot "menuroom". Other painted rooms (options_main, war_records ...) planned. | `docs/proposals/menu_redesign_2026-09-28/remaster_test/INTEGRATION.md` |
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
(`r_ext_multisample`), tonemap/exposure, per-map + night colour grade. (A2C: see the gfx flip entry.)
**Still awaiting a PLAYTEST** to tune/confirm, not code.

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

### autoexec / coop_defaults double-seeding - 11 shared `seta` names untriaged
`OPEN` · bug-2172 (the nine menu post-FX cvars autoexec re-forced are FIXED). A `comm -12` of the two files' `seta`
names still returns 11 shared, untriaged names - autoexec execs AFTER the saved config and wins (TRAPS T7).

### `coop_*` cvars seeded nowhere — the consequential count is ~278 (not 144)
`OPEN` · Re-counted 2026-09-15 from `docs/generated/CVARS_COOP.md`: of 3380 distinct `coop_*` cvars, 1205 are
seeded nowhere, and **278 of those are read by a script** (the bucket that matters). The old "144" is stale.
For these, `getcvar` returns `""` on a clean profile and a script fallback branch silently decides behaviour
- **documenting such a cvar as "default N" describes a branch, not a default.** Consequential ones: [Never ran](#never-ran).

### Console quiet (2026-09-27): engine half staged; 805 dead alias pools
`PLANNED` · `proposals/console_quiet_2026-09-27/apply_engine_patch.py` unbuilt. `ubersound.scr` same-name pools play 1st file only.

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
Transient "in use" locks on `G:\mohaa-gl2\maintt` pk3s, and once the GOG pk3s renamed to `.pk3.stale`
mid-deploy by an unknown actor (AV/indexer or a leaked watcher?). If it recurs, audit with `handle.exe` first.

## Distant objects pop into/out of fog (user 08-04; A+B STAGED 09-27, not built)
`docs/proposals/fog_lod_pop_2026-09-27/`. Old hypothesis (gl2 impostor 900u vs gl1 1352u) was stale, pre-bug-1300.
Sources: SSAO drawn after the fog (bug-3084); distFade/tikiDistFade + GE128 card steps; planar fog on 21:9; lightning;
terrain LOD. Fixes A (bug-3084) + B (bug-3139) STAGED, not built (STAGED.md). Next: coordinated build, Phase 0.

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

## Push bots + Coop Hardcore - 2026-09-25 session, IN PROGRESS
Pace stays `sv_dmspeedmult 0.6` (user). **Rail Yard (m4l2):** lift protocol, jump learner, corner rounding, crouch
tap, sniper hold, 2 heat passes done - soak 6 stuck 0.4-0.8% (was 13.8/14.1), axis reach the tunnels. Walk-past =
the 2048u vision cap at range (bug-2922 fixed, soak pending). New: bandage when safe (bug-2921), danger-ground sprint
(bug-2920). **Grenades:** step-1 telemetry validated (bug-2925); step 2 `bot_nadeSafe` NEXT (scratchpad
design_roomclear.md + vet_roomclear_code.md: 3 blockers - Idle/door-wait clobber the throw, the solver ignores the tiki
addvelocity, a hold beats LiftThink). Then team tactics (design_teamtactics.md + vet): corner checks eyes-only, buddy
aim sectors/alternating bounds (no follow formation), post-breach 2-man entry = roomclear step 4. **e1l1:** bots
walk through burning-wreck trigger_hurt (bug-2926).
**Coop Hardcore** (bug-2923) shipped to source + deployed; ST_HC harness passes every script rule; the user still
needs to eyeball the HUD (no crosshair/stamina/health bar/hit markers, MAGS on reload), aim assist off, the 20s
wave countdown, and "Hardcore: no self-revive" on a real 2-player down. Friendly Fire checkbox REMOVED from coop Start Game (user; bug-2929); Omaha sky stays as shipped (user). Harness: client
0 takes no damage (bug-2928, spawned task).

**gfx flip SHIPPED to source** (engine bc2c3072, mod 8e19cc14; not deployed): MSAA Auto + stable shadows on.
OPEN: alpha-to-coverage is OFF by default - at 8x it draws white foliage streaks (bug-3344: e2l1 4771 vs 7
px; crop scratchpad gfx/a2c_crop2_e2l1.png). Awaiting the user's in-game look at the flip.

Defect sweep #2 (2026-09-28): OPEN m4l2 bunkerdoor1 bot jam (bug-3201, unbuilt engine candidate); the closed
findings are in `docs/proposals/defect_sweep2_2026-09-28/`.

### Weapon view (iron sights shipped v1.10.4; close-out, pistol kick, hands: engine 26407b4b/fbd12315/6200b014, not deployed)
Playtest: bolt/reload/lean/ride while aimed, pistols aimed (`cg_vmHandFix 0` / `cg_adsPistolKick 0` = old). Prone eye ease
(bug-3317, cg_stanceEase) awaits playtest; Gewehrgranate + M1919 keep the old tune (bug-3316).

### Cover v3 (shipped v1.10.58; follow-ups on `cover-seamless` 3caf42ed + mod a60f315f, not merged)
Fixed in the follow-up: right-corner blind fire pose (left hand), the hand-back head close-up, actors read as
cover (bugs 10372-10374). Still open: (1) no true curved wall on the AA maps tested - normal-follow proven on
the m6l2b 28-degree convex bend only; (2) two-PC multiplayer not seen by the user (one PC, one remote client with
120 ms cl_packetdelay passed); (3) bodies without tag_weapon_left still get the crate spray at right corners.

### Norway ending roof blasts + "tables" fix (branch `roof-cine` mod 11f64347, map v9; not merged, bug-10397)
The "tables" were the v7 top-tier breach interiors (6, 18-21) standing 95 u above the roofline. Map v9 caps them and adds
five roof-edge notch sites (23-27); script fires a roof eruption + lingering fireball at each. Proposal + byte-exact rebuild:
`docs/proposals/roofcine_2026-11-02/README.md`. To ship: the v9 `maps/m2l3.bsp` must go into `zzzzzzzzzz_coop_maps.pk3`
(candidate `H:\hzm_work\roofcine\zzzzzzzzzz_coop_maps.pk3`) in the same release as the script. Awaiting the user's look
in-game. Known, untouched: the facade breach holes read as flat brown patches from the one-shot distance.

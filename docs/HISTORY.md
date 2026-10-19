# HISTORY — condensed chronology

One line per item. Status codes: `V` verified · `U` unverified · `D` code-disabled · `R` reverted ·
`O` open · `P` planned. Full detail in [FEATURES.md](FEATURES.md); open items in [OPEN.md](OPEN.md).

**⚠️ Coverage boundaries.** `.wolf/buglog.json` (the only structured record) begins **2026-06-26** at
`bug-535`; bugs 1-534 are absent, and ~28 ids cited in source (bug-237/239/241) have no entry. Git
history reaches 2020 but in snapshot-shaped batches, so it cannot be bisected. "Since day one" means
since 2026-06-21; earlier dates are lineage, not record.

---

## Before the buglog (2020-01 -> 2026-06-20)

Moved to **[archive/history-pre-2026-06-26.md](archive/history-pre-2026-06-26.md)** on
2026-08-17 to keep this file under budget: pre-history, the current era's opening, and the
pre-buglog months.

## 2026-06-26 -> 07-10  (archived)

Moved to [archive/history-2026-06-26-to-07-10.md](archive/history-2026-06-26-to-07-10.md) on
2026-08-24 to keep this file inside its ceiling. The buglog begins; the coop framework, officer
waves and the first engine fixes land.

## 2026-07-11 → 07-20  (archived)

Moved to [archive/history-2026-07-11-to-07-20.md](archive/history-2026-07-11-to-07-20.md)
on 2026-09-08 to keep this file inside its ceiling. Weapons-on-back, the armory and
loadout system, the entity-pool saga, and the first ADS work.

## 2026-07-21 → 07-29 (archived)

Moved to [archive/history-2026-07-21-to-07-29.md](archive/history-2026-07-21-to-07-29.md)
on 2026-09-14 to keep this file inside its ceiling. Addon-spawner restore, engine constant
limits, gl2 migration, combat-verification rig, doc set commissioning.

---

## Release line

| Version | Note |
|---|---|
| 1.1.33 (07-05) | Spawn protection, DBNO corpse-revive, sniper 3P parallax, What's New pipeline |
| 1.1.36 (07-06) | HUD fade batch |
| 1.1.39 | DBNO cinematic anims, 3P free cam |
| 1.1.40 | Cover system (EXPERIMENTAL) |
| 1.1.45 (07-11) | e1l4 alarm |
| 1.1.48 | Weapons-on-back, cut dialogue, battle chatter, 150 death cries, 7 ambience beds, helmet switcher, armory, lobby — **all in one commit** |
| 1.1.49 (07-18) | Shipped. `zzzzz_xw_weapons.pk3` sourced from here. |
| **1.2.0** | **Notes finalised 07-18, NEVER PUBLISHED.** The `_final.md` file is unmarked and reads as authoritative — a trap. |
| 1.1.50 | `renderer_opengl1.dll` still sourced from here in the current manifest |
| 1.1.51 (07-21) | `openmohaa.exe`, `cgame.dll`, `renderer_opengl2.dll` still sourced from here |
| 1.1.52 – 1.1.54 | |
| **1.1.55** (07-26) | **Current.** `game.dll` from here; everything else older. |

---

## What the timeline shows

1. **Velocity is high, verification is not** — ~75 systems in ~5 weeks, ~15 recorded confirmations; the backlog is playtests, not features.
2. **The most expensive bugs were all silent** (entity-pool stomp, grenade veto, grade uniform, `Hunk_Clear` static, snapshot discard); the biggest wins came from *proving execution*, not reading code.
3. **Two records systems degraded predictably**: the append-only ones (`memory.md`, `cerebrum.md`) became unreadable; the structured `buglog.json` kept working. **Structure + a lookup key is the whole difference.**

---

## 2026-08-02 -> 08-10  (archived)

Moved to [archive/history-2026-08-02-to-08-10.md](archive/history-2026-08-02-to-08-10.md) on 2026-09-25: the PDF
defect sweep, the limp, AA emplacement crews, squad survivability, and m2l2a stealth phases A-C.

## 2026-08-17 -> 08-26  (archived)

Moved to [archive/history-2026-08-17-to-08-26.md](archive/history-2026-08-17-to-08-26.md) on 2026-09-28 (08-27 and 09-02 lines followed on 2026-10-06): MV/Leon skin waves, v1.4.0-v1.4.5, the m1l1 notarget root cause, head tracking, prone made playable.

- **2026-09-05** - Omaha, the six in-flight lanes landed (bugs 2473-2483): flank MG42 crews fire (a
  gunner NAME mg42_active could never bind), the radioman goes silent and the player transmits, the 044a
  voices came back from a local.ok int/array collision, waders and seabed kills retimed into the swim,
  hull sparks, ocean flap calmed, obstacle wash, the quick-draw primary placed in view; then water
  research #1, the wet-sand swash (bug-2485; gl2 drops `alphaGen tCoord` without a deform, 2486).
- **2026-09-06** **v1.5.2 released** (github + discord + baked field report) after two runs: the
  Higgins sink had never moved (a clip, then a model swap, 2487/2496), beach fire vetoed since 08-31
  (2497), the captain's exchange never fired (2490); quick-draw flipped (2491/2499), ragged wet line
  (2493), hedgehog crowd (2495/2498); ricochet research filed. Evening: drowning pass (2507)
  and ocean pass (2508); sink end, caustics, urgency (2509-11).
- **2026-09-07/08** Omaha realism and the drowning QTE (2512-2529), all `U`. The ocean got an
  open-sea Airy mesh, a surf-zone bore layer and a painted trough shadow, after establishing that
  deformed water cannot be lit in this engine at all (ENGINE.md 3.6); boat overlaps and the
  shore/ocean seam closed; the "thunder" was an HD shell roll, not weather. Five beach medics in
  hedgehog cover heal on approach (2522/2523/2526). **The drowning cinematic became a tap-Use QTE
  (2528)** - per-player failure, LMS-exempt, never `missionfailed`; the input edge was proven in
  game before the feature was written. Smoke barrage now waits for the shore party (2529).
- **2026-09-09** **v1.5.3 released** (github + discord + field report card, 7 assets / 2,015 MB)
  after a round that started from four user reports. The QTE regression was mine: `+ coop_qteWatchBump`
  in both ramp watchdog CONDITIONS against a var assigned later in the beat, and a throw in a `while`
  test skips the whole loop - both watchdogs ran their timed-out branch at t=0 and forced the handoff
  one second into the ride (2530). Four more defects in the same graft (2530), and the fixer that fixed
  them re-committed the comment-lost-its-`//` trap eight times over, which produced `prosecheck.py`
  (2531). Then: the fires were sand geysers from two barrages the first fix missed (2532, 2536); the
  sink delivered 45.5 of a commanded 72 because the trim lifts the bow (2537); the beach serviced
  players sequentially so four men took 4x as long to die (2442); DBNO could never fire on this map at
  all (2539); the Higgins interior had never been upscaled and 57 installed HD textures never loaded
  (2533); the swell was deleted at the plunge and never restored (2538); the bore beat against it
  (2541); the quick-draw barrel sat 37 degrees up (2542); and shells now take landing craft down,
  written fresh after the reuse design was refuted on a 277-unit pivot offset (2543).
- **2026-09-13** - MP stops using the coop armory, which had been writing coop saves (2571). The menu theme picker had been compiled out and moved to the live sound file (2572). Cinematic audio ducks and Master volume now reset on every exit from a map (2573).
- **2026-09-13** - MP friendly fire fixed (2574): coop's same-team damage filter had covered every player; narrowed and proven with bots on a dedicated server.
- **2026-09-13** - Main-menu theme picker: drawn arrow buttons replace stretched retail icons (2575); a theme advances to the next when it ends (2576).
- **2026-09-13** - Field Settings redesigned (2578, `U`): a generated two-column sheet of 20 player rows, host rows on a new Host Rules sheet, and autoexec no longer overriding player choices.
- **2026-09-13** - The MP/coop isolation gate runs before packing with a self-test proving it can fail; a failed build aborts the release (2579).
- **2026-09-13** - Stufftext filter hardened (SEC1 layer 1, 2580): splits commands as the engine does and checks `vstr` expansions; runtime-verified with a real client.
- **2026-09-13** - SEC1 layer 2 (dab3af77): the exe filters every server-origin command by per-byte origin tag, sharing `cmd_filter.c` with cgame; API handshake v3->4; review closed 5 holes (2589-2592).
- **2026-09-13** - Modern compass bar (`U`, engine d580485a): a coop-only top-of-screen arc with ticks, cardinals, a boxed heading and an objective marker in metres, following the HUD fade (2581). Runtime-verified m1l1/m2l1/m3l3.
- **2026-09-13** - e1l2 dedicated map-checksum + longjmp crash fixed (2585): a client forcing `r_largemap 1` mismatched `sv_mapChecksum` and took a longjmp crash; it now drops cleanly (the client-follows-checksum path M2 is deferred).
- **2026-09-14** - The gl2 visual queue shipped and deployed: an ACES film grade that survives every map load with exposure-aware bloom (2584, 1149), better shadows incl. foliage (69cdb4d7), 45 per-map fog profiles (subtle depth, moodier under the HD skies), render-scale supersampling + AMD FSR 1 (c01bad53), soft particles (a63fe340) and a light per-map colour grade (120c7fc0, server-published, MP-safe). The stamina arc now hard-fades with the HUD (2593).
- **2026-09-14** - MP armories build A (2597, 2598): game.dll E4/E5 hooks (`mp_mapscript_hook` starts the framework on script-less/third-party MP maps; `mp_weaponselect_redirect` opens the side armory on team join) plus a live dispatcher (`mp_armory.scr`) that applies the kit at spawn (hp=100, bots random-class). Runtime-verified; coop airtight (zero mp leakage on m4l1); isolation clause 14 active. The always-ask chooser stays build B - it needs coop-file edits.
- **2026-09-14** - v1.6.0 "The Long View" released to MOHCoopTrilogy/releases: the visual overhaul + compass bar + Field Settings/Host Rules + security layer 2 + the MP armory groundwork, with the Discord announcement, README and in-game What's New card refreshed.
- **2026-09-14** - MP speed fix (2629): autoexec.cfg's `sv_dmspeedmult 0.6` for coop leaked into MP modes (287*0.6=172 instead of 287*1.1=316). mp.scr now resets both cvars before Hardcore captures its memo; start_server.cfg restores coop values.
- **2026-09-14** - Bot leak fix (2630): sv_maxbots/sv_numbots persisted from MP into coop. start_server.cfg now zeros them.
- **2026-09-14** - Build-A-Base and Base Assault modes shipped: two-phase build/fight and 3-base plant/defuse respectively, with full UI infrastructure (12 bridge cfgs, settings rows, menu buttons, seam switches in mp.scr). Cvar naming mismatch between bridge cfgs and mode scripts caught and fixed pre-playtest (2631).
- **2026-09-14** - Cheapest-wins sweep: omconfig decoy deleted, hzm_cvars typo fixed, 3 stale comments corrected, `r_globalFogDebug` restored to CVAR_CHEAT. 8/10 resolved.
- **2026-09-14** - MP armories build B+C: cgame.dll E1/E2/E3 (carried-kit userinfo, `hzm_armory` cmd + `coop_mp_session`, glove override), side picker + defaults screens, game.dll M8 (Gun Game melee demote) + E6 (voice reads worn model). Coop untouched.
- **2026-09-14** - GL2 styled-lightmap red pulse fixed (`U`, bug-1331): the rend2 deluxe-mapping heuristic (`renderergl2/tr_bsp.c`) misfired on MOHAA BSPs; loader now honours `r_deluxeMapping`, autoexec ships it 0. Needs playtest (e2l1/e2l2).
- **2026-09-14** - MP Progression slice 1: `mp_progression.scr` credits team-blind class + per-weapon session counters off a generated `mp_prog_wpnmap.scr` (never coop's attribution); arch A carry. Bot-verified.
- **2026-09-15** - Post-1.7.0 MP work (`U`, bot-verified; render/placement client-gated): MP walks at coop pace + `coop_mpFastRun`; loadout HOLDS on team-join. MP armory/SR rebuilt to the coop loadout (`gen_mp_armory.py`): 3D char viewer per side, marker-free cosmetics (bug-2633), Service Record ladder, coop exact-fit helmets (bug-2634). Base Builder = AlienX `basebuild.scr` port (bug-2635). **Push on the 7 SP maps** (bug-2637): `sv_mpForceArena` one-shot blanks the map script → arena → E4 starts MP; generated `mp_push_maps.scr`; new `mp_modeInit` seam. (`omohaaded` runs no scripts without `developer 1` — TRAPS T3.)
- **2026-09-15** - MP mode full-functionality vet + 13 fixes (bug-2649–2659, `U`): 8 parallel reviewers, all 12 modes + rounds framework, no blockers, isolation 22/22. Headline fix — round modes credited `rounds`/`win_<mode>` only to the last survivor (dead players spectated before the award); fixed via a round-arm team snapshot (`mp_awardRoundWin`). Details in buglog + OPEN. Gates + build pass; interactive loops playtest-pending.
- **2026-09-14** - MP Progression slices 2-6 shipped (v1.7.0): `mp_sign`/`mp_verify` HMAC builtins (SHA-256); signed userinfo `coop_mpProgBlob` carrier + per-guid anti-rollback ledger; per-class unlock thresholds + rank; every armory tile commits, server enforces in `mp_armory::applyMarker`; Service Record off pushed counters. Engine bot-verified; armory UX + SR render need a client.
- **2026-09-15** - MP feature batch (`U`; interactive loops playtest-gated): Base Assault SP treatment (2639), Spawn Protection (2640), Prop Hunt (2641), vehicle system - AT pickups, flak88/nebelwerfer, drivable jeep/tank (2643), symmetric Demolition (2645), Freeze Tag meltgun (2644); fix: MP medkit heal-ceiling exploit (2642).
- **2026-09-20** - Modern **Team Select** (`SelectTeam`/`ObjSelectTeam.urc`, Allies/Axis + Spectate + faction icons via `gen_teamselect_icons.py`; overrides stock, all entry points incl. pause menu → loadout) + **MP loadout re-open redisplays saved state** (bug-2777: vet found all 7 types already persist both sides; fixed finish `ACTIVE:` label, cosmetic name, 3D preview via new `mp_preview_defaults` engine hook, client rebuilt). Isolation 22/0/0; deployed.
- **2026-09-24** - **v1.9.1 hotfix RELEASED**: Begin Full Campaign CTD fixed (bug-2868: admin.scr compile failure + GameScript::Close double free), admin panel live, plus the 09-23 Push review batch (Rail Yard lift route, Monte Cassino, Sniper's Gauntlet, bot aim/reaction, real map names).
- **2026-09-24** - **Push bots: probe2 + anti-confusion pass** (bugs 2875-2882, user playtest "more time confused than playing the mode"). New telemetry (BOTGOAL/BOTJUMP/BOTSTATE/BOTELEV/BOTOBJ, `bot_behavior_report.py --summary`) found: per-frame objective re-path re-seating the progress reference (false blocked -> backward escapes), a 10000u objective sentinel (t2l1 bots had NO objective 69% of the time), stock ledge/step hops, a lift that stalled on bots at its door. Rail Yard confused 18% -> 3%, t2l1 79% -> 2%. Plus grenade breach/cover fighting (deployed).
- **2026-09-25** - **v1.9.2 hotfix RELEASED**: autoexec overflow (bug-2908: binds, Report a Bug, Field Report card), card hide resend (2904/2906), rate 60000 (2909), gl2 terrain (2905), Push bots (2890-2901).
- **2026-09-25** - **Coop HARDCORE host rule** built + deployed (bug-2923: 250 HP cap, scaled knock-down, half bleed-out, no self-revive while a mate is up, 1 kit, half drops, 20s respawn waves, no crosshair/health bar/stamina/hit markers/aim assist, MAGS on reload, +100 XP); ST_HC harness PASS, HUD `U`. XP death counters fixed (bug-2924). Push bots: grenade telemetry validated (bug-2925), bandage when safe (2921), rifle vision range (2922), danger-ground sprint fixed (2920) - soak pending.
- **2026-09-25** - **Vehicle headlights built, not deployed** (bug-2946): gl2 lightglow + rgbGen dot restore (Phase R) and a per-viewer cgame headlight manager, beams in fog/rain only (Phase H - chosen over the script-only Phase A, which lit hidden trucks, kept clear-air beams and starved muzzle lights); all auto-OFF until the user's Test A/B, Omaha excluded in-engine.
- **2026-09-25** - **HD moving clouds ON** for gl2 players (bug-2942: r_skyHD auto split, boxes still off pending seams); dropdown knob HD art now drawn at stock size (bug-2941: UIPulldownMenu honours ui/hd_texel_scale.cfg); deploy guard catches renamed clients + soak servers (bug-2943, after the 18:42 black-text race bug-2940).
- **2026-09-25** - Deployed: **bot grenade safety** (bug-2947 bot_nadeSafe 1: arc-simulated throws, 0/96 throwers in blast vs 29.5%; no mine-detector draws bug-2948), **bot movement** (bug-2955: 16u ledge margin on jump-over-obstacle nav links - m4l2 wedge 33 -> 0 blocks; lift boarding lanes), **headlights Phase R+H switched OFF** pending the hltest.cfg A/B (bug-2946; Omaha Beach excluded by map name). Seam/blend audit + vet: docs/proposals/seams_2026-09-25/ (bug-2950..2954).
- **2026-09-26** - Deployed: headlight **Test A default ON** (lightglow + rgbGen dot; user: "worlds better"; Omaha excluded), **searchlights S1+S2** (tower cone alphaGen dot -> RGB on additive stages; t1l1 sky beams via customShader; bug-2962), **lobby AI strip** for co_lobby2/3/7/8 (bug-2960, docs/tools/strip_lobby_axis.py), **bot respawn-noclip fix** ship build 8c9fbd25 (bug-2958; bug-2961 deploy mix-up resolved). Dev-only paks seamfix/groundfix set aside so the dev install matches players (bug-2952). Plans: docs/proposals/{searchlights,duststorm}_2026-09-26/, headlights_2026-09-25/plan_phaseS.md + vet.
- **2026-09-26** - Deployed: **dust storm roll-in** on the nine sand maps (bug-2963: fog wall to 1250-1500, per-player retail sand veil kept on the camera in 3P/cover/cutscenes by a cgame change, strong-wind loop; `coop_dust`, test cfg dusttest.cfg), lobby/briefing ambience alias spam fixed; **bot straight-link walk check** 1a02002b (bug-2964) + e1l1 navlinks blocks (bug-2965).
- **2026-09-26** - Deployed (switched OFF, AUTO 0): **headlight Phase S-a** spot cones lighting ground + soldiers and occlusion-query lamp flares (bug-2969/2970; test `hlC` in hltest.cfg); latent parallax-shadow GLSL fatal fixed (bug-2971, found by the new `glsl_variant_lint.py`). Also **MP weather default ON** - `replace.scr::waitTillSpawn` no longer boots coop main on campaign arenas (bug-2968).
- **2026-09-26** - User passed Test S -> **full headlight upgrade default ON** (spot cones, lamp flares, lamp points; renderer 6a781592 / cgame ba89b4a2); Khronos glslang pass over all shader variants (v130/v150 clean).
- **2026-09-26** - Deployed: **in-game graphics Apply / vid_restart crash fixed** (bug-2975: UI renderer imports refreshed in CL_InitRef) + its invisible-text regression (bug-2981: UI fonts wait for rendererReady); **MG42 gunners stay on their guns** (bug-2976: suppression/surrender/slide/prone reactions skip manned gunners); headlight S3a beam-stop built OFF (bug-2977); S3b soft edges + S4 spot shadows in the gfx tree (bug-2979/2980). User P0/P1 test: gfx_1 done.
- **2026-09-26** - Staged: **tilefix v2** (120 textures: relaxed gates p99<=12 + 21 MP-only; scope from the release manifest, bug-2991); deploys with the next window.
- **2026-09-26** - Staged: **terrain v4** (v3 + 19 MP-only ground textures + relief siblings, encoder-skew and BC7 fixes, bug-2994); deploys with the next window.
- **2026-09-26** - **v1.10.0 RELEASED** (GitHub + Discord + README): HD sky boxes ON + seam pass (bug-2987), tilefix v2 (bug-2991), terrain v4 (bug-2994), e1l4 gl2 MAX_DRAWIMAGES 4096 + static surfs 32768 (bug-2997/3003), co_lobby8 set_respawn guard (bug-3004), y_hzm_maptour set aside, bots 264fb662 (T2 corner checks, T3 buddy pairs bug-3000, glance comp bug-2992, per-team roles bug-2993, engage restore bug-2989), mp_arenafix (bug-2983) + mp_challenges derive (bug-3001) made cheap. Headlight manager stays OFF (bug-2990/2999 tuning next).
- **2026-09-27** - Built, not deployed: **loading screen redesign** (bug-3013/3019): turning medal + hint strip (`ui/loadingbar.txt`), 60 rotating hints (exe e9331ed3, `cl_loadProbe`), gl2 per-image + cgame alias redraw ticks (gl2 d1570a6d, cgame c2702da0): m3l2 frozen 10.3 -> 1.5 s at no measured load cost (100 ms redraw). SEC2 guard list regenerated (bug-3012).
- **2026-09-27** - Built, not deployed: **launch memorial** "In Memory of Vince Zampella" (exe 13b1749b: an intro stage before the main menu, music and What's New; art `gen_memorial.py`) and the bug-3015 joiner fix (P5b, verified on 5 paths).
- **2026-09-27** - **v1.10.1 RELEASED** (GitHub + Discord + README + card "TRIBUTE"): Vince Zampella launch memorial (exe 13b1749b), loading screen medal + 60 hints + P3 redraw ticks + joiner-freeze fix (bug-3013/3015), headlights ON as tuned (bug-2999/3008), 10 HD sky boxes (bug-3027), Use-first doors + bots never brace (bug-3042, game 700d97a0), room clear / trigger_hurt / slivers / t1l3 slab rule (bug-3024/2926/2988/3026).
- **2026-09-27** - Installed for the next update: **looping loading medal** (old MOHAA icon <-> compass, `hzmLoadMedalMorph`, shader-only, 45 deg/s, 16 s cycle); in-game gl2 + gl1 recordings; bug-3059 (clampMap + rotate needs a mip-safe margin) fixed on the way.
- **2026-09-27** - User: **red "severely injured" banner retired** (`player.scr` coop_limpWarn, coop + MP; limp/cough/muffle untouched); the real cues are 2 new loading hints: red pulse, sway, blood trail < 50%; breathing, cough, muffle.
- **2026-09-27** - User: **loading hints rewritten** for players - 116 plain-language, number-free tips covering every feature (coop/MP/all), each re-verified in code (research.md 4.9); fallback hint now aim-down-sights (the F7 line was wrong in MP).
- **2026-09-27** - Built in main .cmake, not deployed: **per-map grade survives vid_restart** (bug-3048 -> bug-3060, cgame `cg_hzmGradeKeep` AUTO 1) and **per-vertex, geomorphed terrain relief light direction** (bug-3007 -> bug-3061, gl2 `r_hzmTerrainLightGrid` AUTO 0, PARKED until the B0 shadow fix; Omaha excluded). Grade keep ships in v1.10.2.
- **2026-09-27** - User: **console quiet**. Next pak build drops ~3,000 probe lines a session (`coop_probe` 0, `coop_aiBehav` 0, `s_voxProbe`/`s_poolProbe` 0, XPKILL/NAMECMD gated); the engine half (GLSL uniform dump, SKELDISP/DRAW, SKELPOOL, SPEEDPROBE, anim-format notice, ~10,600 more) is staged in `docs/proposals/console_quiet_2026-09-27/`, unbuilt.
- **2026-09-27** - Defect sweep (bugs 3089-3104): mod - obj-hide resend only on change, helmet nodraw list skipped on the hatless twin, MP DBNO Host Rules row hidden (it never downs anyone), host vsync line dropped, Fast Dlights labelled gl1-only + generator gate; engine staged unbuilt in docs/proposals/defect_sweep_2026-09-27 (ter_restart guard, gl2 terMarks alloc, terrain APPLY, sun reset, handshake cvars, forcesubtitle alias fix, quieter console). bug-3072 was a probe artifact.
- **2026-09-27** - **Rank-bar "giant gold square" on promotion found and fixed** (bug-3076, 6th report): a width-0 huddraw quad draws at the texture's native size (`Draw_StretchPic`, both renderers); every fill now hides at 0% instead. Verified by engine screenshots of a real promotion, before/after, gl1+gl2, coop+MP. MP Service Record rank bar draws for the first time. Not yet deployed.
- **2026-09-28** - User: **Hardcore: enemies drop no medkits** - only the kits placed in the map (bug-3187).
- **2026-09-28** - **v1.10.4 integration** (applied + committed, not deployed; engine candidate v1104a): storm darkness default ON + variable storm length (bug-3222), m3l3 rock clips (3210), defect sweep #2 items 1/2/3/6/11 (3194-3200), loadout once per spawn + slow-server icon hidden (3208/3209), briefing slides + title cards for joiners (3234), StG 44 pop (3207), foliage shadows baked (3224), loading-art pool. All `U`.
- **2026-10-04** - Officer group (bugs 3302-3304, mod d89d04c6, not deployed): no wave class is truly unkillable (headless probe); bodyguard 640->420 and every wave actor now live-rescales to the active player count; officer HP thresholds are fractions of his live max (solo officer drank at spawn in v1.10.9); first contact needs sight or damage.
- **2026-10-04** - **Coop mission tiles: 67 new in-engine recon-print tiles + retail names, both menu layouts** (bug-3274 fixed, bug-3300; mod c3428856, workspace 499b2fe9; not deployed). Art in zzzzzzzzzz_coop_tileart.pk3 (gen_tileart_pak.py); e3l4/t3l2 provisional (bug-3301).
- **2026-10-04** - User: **anti-tank supply points at armour fights** (bug-3307/3308, mod b9bf86d8, not deployed): coop_mod/atsupply.scr places a respawning bazooka + 3 shells on t1l1, t1l3, e2l1, m5l3 and t3l1 (x4); t2l1 left alone (sticky-bomb-only objectives). Headless bot test passed on all 5; needs a human playtest.
- **2026-10-04** - Weapon view (bugs 3310-3317, engine 26407b4b..9a9e7fb5, not deployed): ironsights close-out (C96 0.5 px, Springfield/Vickers rows, bipod cant 0), pistol ADS kick recalibrated (Colt 3.97 deg), hands stay on the gun through ADS in/out, bolt, reload, leans and rides (`cg_vmHandFix`).
- **2026-10-04** - User: **ground variety** (bug-3318, engine 7d952435, mod bf73dea9, not deployed): gl2 `r_groundVariety` world-space hex anti-tiling + macro brightness on a generated per-map ground list, Omaha hard-off; Advanced Graphics row, **default OFF** (QA clean on m3l2/m2l1 only; cost ~0 % provisional).
- **2026-10-04** - Player report: **coop start screen Dedicated works** (bug-3321, engine a6e9482e, mod 06d3259d, not deployed): ticked, APPLY / BEGIN FULL CAMPAIGN run coop_dedStart - a separate omohaaded.exe with the screen's validated settings on a free port 12203+, the client joins it; stops on disconnect/quit unless Keep Running; servers cannot trigger it (cmd_filter coop_ded*). Harness lesson: a `wait` chain blocks the whole command buffer.
- **2026-10-04** - User: **smart paratroopers** (bug-3322, mod 56c9359e, not deployed): parasquad.scr squad brain (formation/bounding, cover, own prone/crouch, safe scripted grenades, room clearing) + a mounted .30 cal; 0 friendly damage in 4 client sessions.
- **2026-10-04** - **Dust storms** (mod f9975dc4, not deployed): full storms ~73% of 15-min missions (kinds, 300 s cooldown, 150 s grace; coop_dustFull/Dry/FullCool AUTO), moonlit grey-tan night storms; m1l1 "veil never draws" was `intro 0` leaving every player hidden (bug-3323).
- **2026-10-04** - **Aimed bolt** (bugs 3334-3338, engine 6321ce77, mod 66ddeb31, not deployed): calibrated offline ADS preview; hand-keyed Kar98k `kar98_rechamber_ads`; reviewer PASS.
- **2026-10-04** - User: **m3l2 ground** (bug-3340, not deployed): new out-of-band `zzzzzzzzzz_coop_m3l2ground.pk3` = m3l2.bsp with only its shader lump patched + new-name quilted farmyard/road textures (world-projected, 512 u repeat); the courtyard's 4 side-by-side road strips and the 128 u barnyard grid are gone; other maps (Omaha incl.) cannot change; reviewer SHIP WITH NOTES (pre-existing lightmap lines/blotches now more visible).
- **2026-10-04** - **gfx track merged, defaults OFF** (bugs 3341-3345, engine 0fe952d1, not deployed): MSAA core + stable sun shadows in gl2, legacy picture by default; flip held: A2C draws white foliage streaks at 8x (OPEN), P5 budget passes (Omaha +2.8 ms p99 accepted).
- **2026-10-04** - **srvperf** (bug-3339, mod aff62b99, engine b42ed92c, workspace 8931ca4, not deployed): m1l1 hosting is not slow (~1 ms of the 25 ms server frame, same as m3l3/m2l2a); periodic one-frame script spikes cut (medkit sweep, XP/challenge saves); updater-fed main-menu "update available" line.
- **2026-10-04** - **gfx FLIP** (bugs 3346-3347, engine bc2c3072, mod 8e19cc14, tools c4ed4d7, not deployed): MSAA Auto (8x on >=10 GB) + stable sun shadows on by default, A2C off; G1/G5/P6.3 pass on 110d72c9.
- **2026-10-04** - User: **footprints in snow/mud/soft dirt** (bugs 3349-3351, engine 68bb8881, mod 3c2e06d5, not deployed): cgame cg_footprints.c off the footstep trace, players + AI, multiplicative decals, 200-print ring, 45 s fade; Graphics menu row.
- **2026-10-05** - User: **reload audit phase A** (bugs 3363-3366, mod 441e226e, engine abdd06dc, not deployed): 13 variant/new guns routed to the server torso reload that matches their first-person hands (no more flying guns / cut clips / foreign ammo props), own torso reloads for FG42 (single magazine, 2.34 s) / Johnson / DP-28 / M10, renames Lewis Gun + Webley Mk VI; one in-engine run, 0 script errors. Phase B (new hand clips) planned in `proposals/reload_authenticity_2026-10-05/AUDIT.md`.
- **2026-10-05** - User: **sprint exhaustion + sprint speed** (bugs 3372-3373, engine fae49e72, mod b9f839e6, not deployed): an empty pool now drops to the run anim/speed in 1P and 3P (latch, server pool on STAT_MGHEAT bit 128, per-usercmd drain fixed); coop_sprintMult 1.12 -> 1.22 with the 3P sprint clip rate scaled to match.
- **2026-10-05** - User: **aircraft call-ins** (bugs 3380-3384, mod a573e8a8, engine 30ee0561, not deployed): C-47/P-47/Stuka rebuilt on `aircraft.scr` - visible on every map (+broadcast), per-map heights, smooth, realistic scale/speed, V/pair formations, door exits, shootable Stukas; Doppler + fog see-through in cgame.
- **2026-10-05** - User: **voice pools pruned + gender/nationality fixed** (bugs 3385-3387, mod eb40fadb/7bed9b98, tools a4d0d3f, not deployed): every take whisper-transcribed; orders/named/ghost lines cut; Manon takes out of male pain; per-file BT nationality; flchatter by model nation; paradrop ghosts repointed.
- **2026-10-05** - User: **water reflections / wet ground fix** (waterfix, gl2 only, not deployed): reflections no longer die near banks/quays (reflected-ray occlusion on a blurred height channel replaces the blurred straight-up test), no ruled cut-offs at object edges (3-tap feathered exposure, Smith masking), wet ground darker + saturated instead of white (sky clamped to the baked light). docs/proposals/waterfix_2026-10-05.
- **2026-10-05** - User: **quick-draw motion** (bugs 3393-3396/3398, engine cc2686fa+a15618dc, mod 1c8c3e30, not deployed): primary pushed down-left on the press (both hands, then the parked gun on the same clock), one-handed pistol snaps up, primary back from the support side; rig rotations about the eye on a front-loaded ease; ADS rig no longer seeds from the draw pose (sleeve through the camera); retime 0.18/0.25/0.30 + one-shot coop_qdrawFix1. Pistol settled 0.16-0.17 s hip (was 0.37-0.40), primary back 0.19-0.22 s (was 0.4-1.06); manual switch 0.67-1.0 s / 1.1-1.7 s.
- **2026-10-05** - User: **wordless bleed-out** (bugs 3422-3424, engine 8f9fc6ac, mod 8e142a24, not deployed): ring round the crosshair replaces BLEEDING OUT text + crawl iprint; senses fade via the existing tunnel/low-health passes; heart slows + louder; teammate medic icon + mini ring; Hardcore keeps only the senses; surrendered German = star|eagle icon.
- **2026-10-05** - User: **HUD declutter** (bugs 3426-3429, engine fa5cab0a, mod bf0b5f1e, not deployed): coop chatter -> small cgame event feed bottom-left; "You are DOWN" cut; join/health lines; LAST MISSION page.
- **2026-10-12** - **Scope view finished for release** (bug-3462 + follow-ups, engine `scopes-next` 17e118ad, not released): all 8 optics at 4 screen shapes, gl1, two clients, frame generation; housing flat black, 2D fallback opaque, no pak = retail.
- **2026-10-18** - **Text feed round 5** (bugs 4006-4008, engine `textfeed-next`, mod `textfeed-next`, not released): feed clears subtitles, every untagged coop print routed, banner back. Proof `docs/proposals/hud_textfeed_2026-10-18/`.
- **2026-10-18** - **Armory "Showroom" rebuilt** (bugs 4044-4047, mod `armory-next`, not released): generated screen - hero + finish, unlocked-first pickers, compare bars, progress. `docs/proposals/armory_redesign_2026-10-18/BUILD_RESULT.md`.

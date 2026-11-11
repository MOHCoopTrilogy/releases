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

  gunner NAME mg42_active could never bind), the radioman goes silent and the player transmits, the 044a
  voices came back from a local.ok int/array collision, waders and seabed kills retimed into the swim,
  hull sparks, ocean flap calmed, obstacle wash, the quick-draw primary placed in view; then water
  research #1, the wet-sand swash (bug-2485; gl2 drops `alphaGen tCoord` without a deform, 2486).
  Higgins sink had never moved (a clip, then a model swap, 2487/2496), beach fire vetoed since 08-31
  (2497), the captain's exchange never fired (2490); quick-draw flipped (2491/2499), ragged wet line
  (2493), hedgehog crowd (2495/2498); ricochet research filed. Evening: drowning pass (2507)
  and ocean pass (2508); sink end, caustics, urgency (2509-11).
  open-sea Airy mesh, a surf-zone bore layer and a painted trough shadow, after establishing that
  deformed water cannot be lit in this engine at all (ENGINE.md 3.6); boat overlaps and the
  shore/ocean seam closed; the "thunder" was an HD shell roll, not weather. Five beach medics in
  hedgehog cover heal on approach (2522/2523/2526). **The drowning cinematic became a tap-Use QTE
  (2528)** - per-player failure, LMS-exempt, never `missionfailed`; the input edge was proven in
  game before the feature was written. Smoke barrage now waits for the shore party (2529).
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
- **2026-08 / 09** - archived to `docs/archive/history-2026-08-27-to-09-30.md`.
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
- **2026-10-19** - **v1.10.33 built** (cutscenes, text, m3l3, flak, gun anims, pad aim). `kickoff_2026-10-18/RELEASE_NOTES_v1.10.33.md`

- **2026-11-01** - **v1.10.53-v1.10.55 shipped**: Mission 1 extra objectives removed (soft-locks); Film Room + Norway one-shot ending + braced MGs; Norway hold retuned (platform push, peak at the train, weaker allies). Notes `release_notes_1.10.5x.md`.
- **2026-11-02** - **v1.10.56**: demo studio (speed ramps, follow/look-at, clean shot + letterbox, highlights + reel, corner view, MP4, F10 stops at the end), CC0 weapon sheets (660 MB), Norway both halftracks (seen-entry fallback, launch lock, second hull stops short), pitched-roof perches (`coop_asnCornerTol`), gates open for the defence. README banner is now Norway.
- **2026-11-02** - **Cover v3** (seamless glide/edges/doorways/pop-out/camera) built + harness-verified on `cover-seamless` (engine 29e90d34, mod 7b336a7b), awaiting merge after v1.10.57.
- **2026-11-02** - **Cover v3.2** on `cover-seamless`: MGS hug camera (front, peek past edges), back-to-cover low cover, cover-frame input + S step-away, doorway pop, pose-gated blind fire for every bullet weapon (bugs 10387-10391, 10406-10408, 10413-10414).
- **2026-11-02** - **Norway flak gun + Stuka passes** on `finair-next` (df51113d): mannable Flakvierling, 5-6 strafing passes gated on the live storm, harness-verified shoot-down; awaiting merge.
- **2026-11-02** - **Attic polish + gramophone** on `attic-polish`: gramophone corner theme picker (on the object, shuffle default, persisted pick), period phones, GL2 chrome fix, phantom shadow / speck removed, New Game tags legible; awaiting merge (docs/proposals/attic_polish_2026-11-02).
- **2026-11-03** - **Norway guns on the loot path + supplies on crates + pickup sounds** on `normguns` (mod 13fa424f, engine d20a1c8b): every m2l3 placed gun is a real loot gun (German-drop prompt, death drop at the body is a loot gun, crate restock), MG42/medkits/Panzerschreck on half-size crates, ammo beside the cover crates, weapon pickup sound on the taker + every pickup alias on every coop map (bugs 10474-10478); harness-verified, awaiting merge.
- **2026-11-03** - **Emotes** on the Tab wheel (`emotes` branches): 17 rank / Service Record unlockable emotes on two EMOTES pages, generated from `docs/tools/gen_emotes.py`; harness-verified (unlock, persist, cancel), awaiting merge.
- **2026-11-03** - **v1.10.62 published** (release + Discord + README 891a92c9): emotes, the new debrief + challenge XP, Demo Studio tools, cover look/aim, Norway perches proven by actor canshoot (roof snipers + MG nests that fire), snow impacts, hit/kill/artery sounds, attic clock (PC time) / fan / door / board / toolbox, ESC in-game opens the 3D rooms. Notes were empty at publish (bug-10514, fixed in publish_release.ps1 + re-edited body).
- **2026-11-03** - **Daily Orders phase 1** on `dailies` / `dailies-eng` / `dailies-root` worktrees (H:\hzm_work\dailies-*): 94 of 100 orders, getutcday builtin, lobby panel (HUD slots 156-175), SR ORDERS OF THE DAY tab, debrief line; harness-verified, not merged.
- **2026-11-04** - **m2l3 sniper squad fix + snow impacts** on `hotfix-1.10.53`: `def_sn_squadfix` clears a sniper's squad when it blocks his shot (engine FriendlyInLineOfFire); LOS los163b/c every roof sniper >=6/9 before and after the storm; snow powder on `coop_snowPlume` (stock snowPlume_02 faded to black), grenade cloud/card/clumps unlit white; first in-game stills (coop_finSnowFx test).
- **2026-11-04** - **Demo tester fixes** on `demofix-eng` (99156eca, 2173a899) / `demofix` (a9afa46b): hosted F9 recordings are `srv_<map>_<date>_<time>` and never overwrite, `record <name>` names one, F10 renders the newest (`cl_recordPlay`), Film Room cards show the time; a demo seek clears ragdolls + wounds (living soldiers drew as corpses after a back-seek). The tester's demo then showed the gun + leg ghost are one bug: a freed model handle another configstring still used drew his Garand as an upside-down German (d73719ff, bug-10543).
- **2026-11-04** - **Cover look/aim, full-auto blind fire, cover grenades** on `coverlook-eng` (H:\hzm_work\coverlook-eng, 1f6a45c6): view held in the blind-fire sector (corner wall-side limit 19 -> 0 deg, cue stays on screen), 4 s holds empty the mag (MP40 32 vs 16), throws land 1-104u from the cue (bugs 10546-10548); harness-verified, not merged.
- **2026-11-08** - **Cover leftovers for v1.10.64** on `coverlook2-eng` / `coverlook2` (H:\hzm_work): throws from cover play the AI cover throws and leave from the hand at the measured release frame; mid-wall shoulder aim camera (cue on screen 55/68, was 0/115); short throws 25 deg low arcs (bugs 10561-10563); harness-verified, not merged.
- **2026-11-08** - **Chronological Campaign** on `chrono` (H:\hzm_work\chrono-mod) + engine `chrono-eng`: BEGIN CHRONOLOGICAL CAMPAIGN plays the AA/BT/SH missions in history order (Torch 1942 -> Berlin 1945), CONTINUE from the saved level; harness 54/54 hops; not merged.
- **2026-11-08** - **Join card** on `joincard` (H:\hzm_work\joincard-mod, c4abf17f) + engine `joincard-eng` (cf0ae79b): a spectator with nobody alive to follow gets a black screen + title card (title, rank + name, unit, place, date - time; line-by-line reveal) instead of free-roam; `coop_specHold` makes spectators follow the first live teammate, else holds them still. 53 levels from `docs/tools/joincard_titles.tsv` via `gen_joincard.py`; m6l3c/d scoreboard names fixed (bug-10586/10587). Verified in a two-client dedicated harness; not merged or deployed.
- **2026-11-08** - **Frontline BYO pilot (mfl_1_1, Seaside Stowaway)** on `frontline-tools` (C:\hzm-root-frontline, 24ccd13b) + mod `frontline` (C:\hzm-frontline\mod, 4384e090): POC GO (texture binding + .bpd entities/navpoints decoded); converter builds BSP v19 + textures + dialogue/music/subtitles from the user's own disc in 30 s, deterministic; 2-bot self-test completes all 5 objectives with 12 dialogue cues; OPEN: bot navmesh fragmented (bug-10605), GL1 trisurf colours (bug-10600). Not merged, not deployed.
- **2026-11-10** - **Per-gun recoil patterns** (UNMERGED, awaiting playtest) on engine `recoil-eng` (C:\hzm-recoil\eng) + mod `recoil-mod` + root `recoil`: a learnable per-gun pattern from real-weapon data (`coop_recoilPattern` 1), camera kick trimmed to a punch; docs/proposals/recoil_2026-11-10.
- **2026-11-02** - **v1.10.56**: demo studio (speed ramps, follow/look-at, clean shot + letterbox, highlights + reel, corner view, MP4, F10 stops at the end), CC0 weapon sheets (660 MB), Norway both halftracks (seen-entry fallback, launch lock, second hull stops short), pitched-roof perches (`coop_asnCornerTol`), gates open for the defence. README banner is now Norway.- **2026-11-10** - **Menu load** (bugs 10900-10905, engine `menuload-eng`, not released): in game -> Main Menu 10.8 s frozen -> ~1.2 s behind a veil + bar, disconnect 17.3 -> ~2 s, polluted preload lists cleaned (m4l0 load -11 s), every 3D room loaded before it is seen. `docs/proposals/menuload_2026-11-10/README.md`
- **2026-11-10** - **MP unlock progress persists** (bugs 10912/10913, branch `mpprog`, `U`): the carried MP record never reached the client (quoted stufftext + `;` in userinfo), so every session restarted at zero; rank tiers now load at join. Gate `mp_unlock_audit.py`. `docs/proposals/mpprog_2026-11-10/`
- **2026-11-11** - **v1.10.76 Liberation**: solo one-life hunt contract in Field Operations (LIB mode, 12-25 held Germans, co-op Armory kit, 2x TDM XP, radio briefing, 16-map pool; war map 18 places, table 37 entries); merged mod cd592eb0 / engine 9ad9e7b3 / root 890297bf (bugs 10957-10961). Verified by cfg-driven client runs only (win, lose, idle, TDM contract); real-kill win and OUT OF TIME need a human playtest. The click test cases need the uncommitted `hzm_ops testmouse` hook (bug-10961).

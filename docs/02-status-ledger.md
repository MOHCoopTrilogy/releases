# 02 — Status Ledger

Every claim carries a status and an anchor. Statuses are exactly the five defined in
[README.md](README.md). Where a status is downgraded from what a record asserts, the reason is
given.

**How this was classified.** `SHIPPED-VERIFIED` requires a live-test or user confirmation in the
record. `SHIPPED-UNVERIFIED` is the default for anything whose buglog entry ends "NOT YET VISUALLY
VERIFIED" / "untested" / "awaiting user go", **and** for anything shipped before the current
uncommitted engine tree that no later entry re-confirms. When in doubt the item was downgraded,
not upgraded.

---

> ⚠️ **Everything marked SHIPPED below describes the SOURCE TREE.** The deployed binary set in the
> GOG root is internally inconsistent as of 2026-07-29 — `openmohaa.exe` (07-21) and `game.dll`
> (07-24) predate protocol constants that `cgame.dll` (07-28) was built with. Engine-side items may
> therefore not be live in the user's install even where the source is correct.
> See [03-record-vs-code.md §0](03-record-vs-code.md).

---

## A. Gameplay systems (mod-side)

| Item | Status | Evidence |
|---|---|---|
| Coop framework (`main.scr` init, player lifecycle, event bus, objectives HUD) | SHIPPED-VERIFIED | 63/118 map scripts wired; full-trilogy 4-player sweep v1.1.52 |
| DBNO (down-but-not-out) + bleed-out + team revive + heartbeat | SHIPPED-VERIFIED | cerebrum 2026-07-02; log showed full down→bleed→died cycle |
| Officer boss AI (8 wave types, bodyguards, reinforcement waves) | SHIPPED-VERIFIED | `coop_mod/officer.scr`; per-map policies |
| Officer wave scaling around a **2-player** baseline (solo scales *down*) | SHIPPED-VERIFIED | `coop_officerBase*` cvars |
| Officer repeat-heal budget (`coop_officerMaxHeals`, default 2) | SHIPPED-UNVERIFIED | bug-1215 (2026-07-29, same-day) |
| Enemy count-scaling by player count (cap 80) | SHIPPED-VERIFIED | per-spawn duplication |
| AI difficulty scaling / pain buffer (`aihandler.scr`, engine hp faked to 5000) | SHIPPED-VERIFIED | `aihandler.scr::initialisePainVars` ~477-484 |
| Bullet-sponge self-healing sweep (`coop_unsponge`, default 1) | SHIPPED-UNVERIFIED | bug-1212; `autoexec.cfg:403` confirms `seta coop_unsponge 1` |
| Cover system (face-wall auto-turn, low cover, blindfire) | SHIPPED-VERIFIED | engine `Player::TickCoopCover` + `takecover.scr` |
| Sprint / walk / stamina / hold-breath | SHIPPED-VERIFIED | `BUTTON_RUN` model, cgame + game.dll |
| ADS suite (iron sights, per-gun tune table, 3P shoulder ADS, bash on V) | SHIPPED-VERIFIED | `CG_AdsForceFirstPerson` is the single decider |
| ADS per-gun tune for SVT / G43 / Breda / Springfield | PLANNED | memory `ads_pergun_tune_table` — listed pending |
| 3P free cam (360 orbit, ADS shoulder handoff) | SHIPPED-VERIFIED | vestigial `camera_offset` channel; exe+cgame pair |
| Player emotes (salute / at-ease / stretch) | SHIPPED-VERIFIED | `EMOTE_*` legs states, name-append bus 23-25 |
| Weapons-on-back (holstering) | SHIPPED-VERIFIED | 07-13; 69 TIKs uncommented + `holsterOffset` engine fix |
| Helmet pop (fly-off) — **AI only** | SHIPPED-VERIFIED | 131 human TIKs carry `sethelmet`; probe-verified |
| Helmet pop on **players** | NOT POSSIBLE | Zero of 313 `models/player/*.tik` carry `sethelmet`, so `WearingHelmet()` is always false. An earlier "verified working in coop" note referred to actors (cerebrum 2026-07-28) |
| Helmet switcher (34 helmets, attachmodel to `Bip01 Head`) | SHIPPED-VERIFIED | `helmet.scr`; gear-skd transplant recipe |
| Armory / loadout picker (69 guns, 76 skins) | SHIPPED-VERIFIED | `gen_loadout3.py`-generated; click fix = FindResponder v2 |
| Armory skin roster stale at 28 vs lobby's 76 | OPEN | bug-armory-roster76 — cosmetic; server lock gate still enforces |
| XP / ranks / emblems | SHIPPED-VERIFIED | `xp.scr` + 13 hooks |
| Challenges / Service Record (179 challenges incl. 90 per-weapon) | SHIPPED-VERIFIED | `challenges.scr`, `gen_sr4.py` |
| Weapon unlock progression (rank + challenge + tree-gated) | SHIPPED-VERIFIED | 3-route system, armory padlock gate |
| Deployables skill tree | REVERTED (rejected at design) | User vote; only weapon-unlock chains survived |
| Build mode (14 textured box primitives, blueprints, shape kit) | SHIPPED-VERIFIED | `buildmode*.scr`, `blueprint.scr`; 5 shipped templates |
| Blueprint templates: `depot`, `logwall` | REVERTED | Dropped at the connectivity gate — sources are authentically-scattered dioramas (bug-1009, bug-1002 r3) |
| Ammo box + MG42 overheat | SHIPPED-VERIFIED | deployable resupply + turret heat |
| Corpse despawn (`coop_corpseLife`) | SHIPPED-VERIFIED, **default OFF** | `autoexec.cfg:357` = `seta coop_corpseLife 0` (user chose to keep bodies) |
| Exact-ammo respawn (`coop_exactAmmo`) | SHIPPED-VERIFIED | `autoexec.cfg:532` |
| Coop lobby #1 (mannequins, ready→countdown→briefing) | SHIPPED-VERIFIED | engine `CoopLobbyPose` + `FL_IMMOBILE`; A/D/F usercmd bridge |
| Vehicle seating (t2l2 halftrack/truck, m1l3b jeep, m5l2 King Tiger) | SHIPPED-VERIFIED | seat table + `duckableglue` |
| Tank MG gunner slot (2nd player mans King Tiger MG) | SHIPPED-UNVERIFIED | memory `tank_mg_gunner_slot` — prototype, untested |
| e1l2 invisible walls | SHIPPED-VERIFIED | `cmpatch/<map>.txt` brush surgery; in-game `killwall` editor |
| Void guard (universal OOB safety net, all maps) | SHIPPED-VERIFIED | `coop_mod/voidguard.scr` |
| Reactive difficulty / AI-Director | PLANNED | `_research/director_dda_plan.md`; awaiting 8 user decisions |
| NAT hole-punch | PLANNED (phase 1 built) | rendezvous daemon verified locally; ~680 LOC MVP remains |
| Installer (Inno Setup 6) | PLANNED | explicitly "DO NOT EXECUTE until asked" |
| Bipod (hold-RMB supported aim) | PLANNED | design complete, build on go |
| Player gore (skin-bit blood tiers, drip/pool, bone wound props) | SHIPPED-VERIFIED | tiers 1-4; decals-on-skeletal proven impossible |
| Decapitation / dismemberment | **REVERTED** | See §D |

---

## B. Engine features

| Item | Status | Evidence |
|---|---|---|
| Post-FX chain gl1 (bloom, SSAO, grade, god rays, DoF, sharpen, FXAA, suppression, low-health) | SHIPPED-VERIFIED | `tr_postprocess_gl1.c`; exposed in `ui/coop_postfx.urc` |
| Tracer glow, heat haze, smoke whips, blood trails, tinnitus, suppression FX | SHIPPED-VERIFIED | cgame + renderer; each has a settings-UI control |
| Audio: full mixer (Master/Music/SFX/Ambience/Dialogue), reverb, HRTF, linear distance model, OpenAL limiter re-enabled, `AL_MAX_GAIN 8.0` | SHIPPED-VERIFIED | `snd_openal_new.cpp` |
| Death voices (484-cry pool + native-VO mute) | SHIPPED-VERIFIED | `deathvox.scr` |
| Headshot kill sound + guaranteed burst/wall-splat FX | SHIPPED-UNVERIFIED **in play** | bug-1142: sandbox-verified 10/10 on m1l1 and m3l2, but "play-install rollout STAGED awaiting user go" |
| Entity pool 2048 (`GENTITYNUM_BITS 11`) | SHIPPED-VERIFIED | `q_shared.h:1667`; closed the bugs 914-927 crash family |
| `MAX_SNAPSHOT_ENTITIES` 1024→2048 (bug-934's missed 4th member) | SHIPPED-VERIFIED | bug-1186, exe-only ship |
| `MAX_CONFIGSTRINGS` 4096→8192 | SHIPPED-VERIFIED | `q_shared.h:1787`; every serialisation path audited |
| `frameInfo[].index` 12→13 bits (disfigured-actor fix) | SHIPPED-UNVERIFIED | `msg.cpp:1355-1361`; bug-1187. Task #16 still open: "Verify disfigured actors fixed by 13-bit anim index" |
| `MAX_TIKI_LOAD_ANIMS` 4095→8192 | SHIPPED-VERIFIED | `tiki.h:36` |
| `MAX_BODYQUEUE` 5→128 | SHIPPED-VERIFIED | `actor.h:306` |
| `entityNumber` 1023 aliasing (UI preview vs world entity) | SHIPPED-VERIFIED | bug-1167; `cl_invrender.cpp:160` hardcoded 1023 → `ENTITYNUM_NONE` |
| gl2 (rend2) migration | **PAUSED / sandbox-only** | Shipping renderer is gl1 (`cl_renderer` default `"opengl1"`, `cl_main.cpp:3229`). gl2 lives at `G:\mohaa-gl2` |
| gl2 post-FX port (bloom colour-domain fix) | SHIPPED-UNVERIFIED (sandbox) | bug-1156 |
| gl2 AO / SSAO | SHIPPED-UNVERIFIED, **default forced OFF** | bug-1177 + bug-1178 |
| gl2 rain | OPEN | bug-1133 — gl1 shows drops, gl2 shows none. Frame-diff confirmed empirically |
| gl2 `#73` first-person gun over menus | OPEN → fixed? | bug-1140 diagnosed as an FBO ghost; depth-test parity fix landed (cerebrum 2026-07-28) but no verification recorded |
| gl2 `Z_TagMalloc, Negative or zero size 0 tag 12` menu spam | OPEN | bug-gl2-ztagmalloc |
| gl2 foliage billboards render opaque white | SHIPPED-UNVERIFIED | bug-gl2-foliage-white — "NOT boot-verified; needs live A/B on e2l2" |
| gl2 `vid_restart`-from-open-menu font-reload crash | **OPEN** | bug-1181/1182. Worked around by removing the APPLY→`vid_restart` path; the underlying UI-font readiness guard is **not** applied |
| Hi-DPI / typeface-swapped font atlases | SHIPPED-VERIFIED | Bahnschrift; `@3x` variant is what the engine loads |
| gl1 shadows (Phase A decal shadows) | SHIPPED-VERIFIED | gl1 shadow-mapping not started |
| Bindable coop key actions (name-append bus) | SHIPPED-VERIFIED | 3-edit recipe, no engine rebuild |
| In-game Report-a-Bug → Discord webhook | SHIPPED-VERIFIED | via PowerShell POST (no libcurl in this build) |
| Display modes (Windowed / Borderless / Exclusive) | SHIPPED-VERIFIED | HZM `r_desktopfullscreen` |

---

## C. AI behaviour work

| Item | Status | Evidence |
|---|---|---|
| AI behaviour tracker (`coop_aiBehav`) | SHIPPED-VERIFIED | measured 12× displacement on m1l1 |
| Step 1: global personality (`coop_aiDynamic`, verified roles) | SHIPPED-UNVERIFIED **in feel** | Compiles + loads; behaviour verified by displacement metric, **not** by a human |
| Step 2: engine juke/hide timers (`actor_turret.cpp`) | SHIPPED-UNVERIFIED | AIBEHAV2 aggregate cannot cleanly measure the engine turret un-pin |
| Steps 3-4: squad brain, cover nodes | PLANNED | not started |
| Autonomous combat-AI verification | **BLOCKED** | A script `damage` event applies damage but does **not** make AI acquire/engage (`engaging` stays ~0). Damage attribution ≠ target acquisition. Real fix = `Player::CoopBotDrive` usercmd injection (built; see below) |
| Engine bot (`CoopBotDrive` usercmd injection) | SHIPPED-UNVERIFIED | Built for unattended combat testing |
| AI grenade fix (`GrenadeWillHurtTeamAt` length→lengthSquared vetoed ~all AI grenades) | SHIPPED-VERIFIED | huge behavioural change |
| AI combat dialogue (engine `Anim_Say` routing) | SHIPPED-VERIFIED | retail routing audited across 1297 human TIKs and found **correct** — do not go hunting there again |
| 18 imported `xw` guns don't hip-fire | **OPEN** | memory `actor_anim_audit` |

---

## D. REVERTED — the highest-value section

These were built and then undone. Each entry says *why*, so it is not rebuilt blind.

| Reverted thing | Why | Anchor |
|---|---|---|
| **Decapitation / blast dismemberment** | v1 (bug-856) made "the AI go all glitchy" → reverted (bug-861). v2 rebuilt safely (bug-866) → stripped again from source during the `MAX_MODELS` three-binary rebuild (bug-892). **Zero decap code exists in the engine today** (verified: only stock `snd_decap` sound calls remain in `body.cpp`/`gibs.cpp`/`sentient.cpp`). The glitching that motivated the original revert was **later attributed to the entity-pool stomp** (bugs 914-927) — so the reason for the first revert no longer holds. The safe re-add pattern is documented in bug-866. | bug-856/861/866/892; code-verified 2026-07-29 |
| **`+180` roll correction on `m1l1` truck-bed allies** | Applied on an unconfirmed gimbal-lock theory; the live result was contortion, not a clean rotation. Reverted. **The underlying corruption is still OPEN** (bug-1184/1213). | bug-1173 → bug-1184; verified absent from `maps/m1l1.scr` |
| **`g_coopTurretCam` override in `vehicleturret.cpp`** | A broad MP turret-camera override (default ON) silently hijacked *every* MP vehicle turret (jeep .30cal + halftrack), discarding the correct stock eye-bone camera. The real fix was only the `SpawnTurret` `DropToFloor`/`PlaceTurret` call. A second, shared root also existed: an orphaned `bThirdPerson \|= PMF_TURRET` line in `cg_modelanim.c` left behind by a partial revert. | cerebrum 2026-07-01 (two entries, second CORRECTS the first) |
| **`maxentities 2048` in `coop_mod/server.cfg`** | `GENTITYNUM_BITS` was 10 → the oversized cvar only disabled `AllocEdict`'s overflow guard, so slot 1022 got handed out repeatedly, stomping occupants. **Producer of the entire weekend crash family.** Removed from cfgs; the compiled default in `gamecvars.cpp:323` is now `"2048"` legitimately, alongside `GENTITYNUM_BITS 11`. | bug-927; `gamecvars.cpp:320-323` |
| **`r_entlight_scale` flipped to `CVAR_ARCHIVE` for an A/B test** | The test value (0.3) was silently saved to `omconfig` and dimmed every character and vehicle ~75% across launches. Reverted to stock `CVAR_CHEAT`. | bug-918 |
| **`noPlayerClip` global experiment (e1l2 walls)** | Let players push into real wall crevices. Replaced by per-region `coop_clipStripZones`, then by `cmpatch` brush surgery. | bug-938, bug-951 |
| **Zone mask-strip for invisible walls** | Killed boundary clip too — players clipped out of bounds. | bug-951 |
| **Billboard tree-card photo reskin** | User verdict: "looks bad". Flat crossed-card + photo-on-radial-blob does not read in-game. **Do not retry.** User wants real 3D tree models via `md5_2_skX`. | cerebrum 2026-06-30 |
| **Hidden-locked cosmetics (bug-759/772 design)** | User *reversed* the design pre-release: locked skins/helmets now show with a lock icon + "UNLOCK: …" caption, because locked content should advertise how to earn it. Snap-back reverts removed. | bug-787 (Decision Log) |
| **`MAX_SOUNDS` 2000, then 1600 → 1280** | 2000 broke the configstring layout (`SV_FindIndex: bad index`); 1600 then blew `MAX_RELIABLE_COMMANDS` (512) → "Server disconnected". Reverted twice. **⚠️ The code has since moved past this record — see [03-record-vs-code.md](03-record-vs-code.md).** | bug-1179, bug-1183 |
| **`MAX_ENTITIES` (gl1) 1023→4095 and `MAX_TIKI_ALIASES` 4095→8192** | Reverted as emergency remediation when `build.ps1` carried gl2-sandbox engine changes onto the real install. `tr_types_new.h:33` still reads `1023`. | bug-1172 |
| **Post-FX APPLY button issuing `vid_restart`** | Instant crash on gl2 (renderer DLL torn down under a live UI). Button reverted to plain `popmenu 0`; AO row relabelled "needs vid_restart". | bug-1181 |
| **`r_ppSSAO` defaulted ON in gl2** | Copied gl1's long-proven default onto a path that had never executed once → ~25 MB of new full-res buffers at 3440×1440 → crash on first map load. **The code was correct; the DEFAULT was the defect.** | bug-1178 |
| **Menu panels built from textured `shader` Labels** | Raw JPG/TGA paths do not resolve in the URC material system — the whole panel drew nothing ("the folder isn't there"). Reverted to `bgcolor` fills + `borderstyle 3D_BORDER`. | bug-menu-shader-label-invisible |
| **Armory 3D preview "corrected" framing** | Derived analytically from `CL_Draw3DModel` bounds math → upside-down and off-screen. Reverted to the screenshot-proven `modeloffset "50 0 -3"` @ `modelscale 1.3`. Generator comment now forbids re-deriving without a live screenshot. | bug-594 |
| **`coop_wallProbe` / `coop_weapDebug` / `coop_allyFireDebug` defaulting to 1** | Three dev-debug cvars shipped ON for months; `coop_wallProbe`'s per-frame traces + `gi.GetShader` crashed the server under 4-player load. Defaults set to 0 in v1.1.53 — **and that fix was itself negated** by `autoexec.cfg:42` shipping `seta coop_wallProbe 2`, requiring v1.1.54. `autoexec.cfg:42` now reads `seta coop_wallProbe 0` (verified). | bug (v1.1.53/54); `autoexec.cfg:42` |

---

## E. OPEN defects

| Defect | Notes | Anchor |
|---|---|---|
| **m1l1 truck-bed allies (`2nd-ranger_private`) render mangled** | Six investigation rounds, five shipped fixes, no help. Mod data **exonerated with proof** (full TIKI+skeletor merge simulated offline). Captain in the same truck renders correctly. Candidate remaining: the corrupted retail `truck_idle/twitch_guy01.skc` files, or the per-frame `gettagangles` puppeteering. | bug-1184, bug-1213 |
| **m1l2a crash** | `DetachAllActiveWeapons+0x1D` near-NULL read at `CS_PRIMED`. Next step: ASan. | memory `m1l2a_crash_hunt` |
| **Reload camera dip not visible** | Signal chain source-verified end to end; effect still invisible at `cg_reloadCamDip 6`. | bug-165 |
| **Rain falls inside enclosed buildings** | Drops spawn legitimately under open sky then drift + render *through* geometry. Snow (slant 1) barely drifts, which is why snow maps never showed it. | bug-134 |
| **Dedicated server segfaults on bare DM maps** (`obj`, `obj_team1`) | Coop maps load fine. Baseline reproduces with zero rendezvous cvars. | bug-330 |
| **Cover peek is "very janky"** — no physical step-out | Design queued: slide origin 24-32u toward the open side during peek. | bug-311 |
| **t2l2 throws 265 script errors on coop boot** | 36× `Couldn't load model`; panzerwerfer + nests degraded. Map reaches coop-ready but degraded. | bug-1026 |
| **e3l4 `outro.scr` fails to compile** | End-of-campaign credits run with uninitialised data. | bug-1027 |
| **e1l2 mine detector after respawn** | Unknown whether genuinely absent or present-but-holstered. Needs live confirmation. | bug-898 |
| **Airborne first-aid pouch black** (bug-499 family, 5 rounds) | Every static check passes; name-resolution failure at runtime never pinned. **Worked around** by total shader isolation (fresh name + private texture path). | bug-921, bug-922 |
| **AI dropped weapons float and spin forever** | Toss-stuck detection added; not confirmed closed. | bug-923 |
| **18 imported `xw` guns don't hip-fire** | | memory `actor_anim_audit` |
| **Dedicated headless smoke boots don't work on this fork** | `omohaaded` never executes buffered commands. Not a bug to fix — a constraint to work around. | bug-999 |
| **~40 coop sub-tests need dynamic orchestration; ~22 need a human** | live client add/drop, soaks, active vehicle rides, spawn-protection window, LMS gameover, 4p-specific, held input. | memory END6 |

---

## F. Test assets that exist (use them before writing new ones)

- **`coop_selftest*.scr`** — 78 probes across 10 validated suites, all run error-free. Definitively
  PASS: xp ownership/cap/popup/rank, objective wrap/idempotency/side-objectives, trigger event bus,
  DBNO exact-ammo respawn, officer accuracy, engine entity cap, scaling math, reconnect 54/54
  zero-crash-on-drop. **Permanent regression asset.**
- **`coop_mod/tracescan.scr`** — invisible-wall triage, server-side grid traces, fwd/rev asymmetry.
- **`coop_mod/helmtest.scr`** — the cvar-gated runtime-probe pattern for engine-behaviour questions.
- **`killwall` / `markwall` / `cm_restorebrush`** — in-game invisible-wall editor writing to a loose
  homepath `cmpatch/<map>.txt`.
- **`ui_clickdebug 1`** — engine click tracer; first tool for any "menu clicks do nothing" report.
- **`coop_lobbycycleanim ±1`** — live pose finder; IDs a `.skc` visually in one pass.
- **`tikiprobe <model> <alias…>`** — headless TIKI ground truth, writes `tikiprobe_result.txt`.
- **`scratchpad/depthscan2.py`** — brace running-depth scan (necessary, **not sufficient** — see
  [10-script-conventions.md](10-script-conventions.md)).

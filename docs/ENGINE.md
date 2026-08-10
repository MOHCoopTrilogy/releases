# ENGINE — what this fork changed vs upstream OpenMOHAA

Repo: `C:\mohaa-coop-dev\openmohaa-hzm\`. Branch `hzm-coop-working`, HEAD `819a6e93` (2026-07-23).
Remotes: `origin` (joncurry94-tech/openmohaa), `org` (MOHCoopTrilogy/openmohaa), `upstream`
(openmoh/openmohaa).

---

## 0. Repo state — read before anything else

**Committed HZM work since the merge-base `a72bc153` (2025-08-03):** ~12,100 added lines over 125
files.

| Area | Files | Lines |
|---|---:|---|
| `fgame` | 37 | +3,600 / −127 |
| `cgame` | 18 | +3,503 / −76 |
| `renderergl1` | 12 | +1,983 / −9 |
| `client` | 18 | +1,530 / −93 |
| `tools` | 7 | +655 / −78 |
| `qcommon` | 12 | +358 / −13 |
| `uilib` | 5 | +161 / −6 |
| `renderergl2` | 2 | +70 / −11 |
| plus `tiki`, `sys`, `server`, `sdl`, `skeletor`, `renderercommon` | | |

**⚠️ UNCOMMITTED on top of that: 119 files, ~10,750 insertions, 483 deletions, plus 20 untracked
files.** (Measured 2026-07-29; a concurrent workflow is actively editing `renderergl2/`, so this is a
moving target — it grew during the audit.)

| Area | Files | Lines (uncommitted) |
|---|---:|---|
| `renderergl2` | 29 | +5,794 / −281 |
| `fgame` | 33 | +1,828 / −70 |
| `cgame` | 10 | +554 / −23 |
| `client` | 10 | +547 / −21 |
| `renderergl1` | 12 | +402 / −31 |
| `qcommon` | 7 | +385 / −26 |
| `tiki` | 4 | +215 / −3 |
| `uilib` | 7 | +203 / −8 |

**Untracked and therefore not backed up by git at all:** `renderergl1/tr_gore.c`,
`renderergl2/tr_gore.c`, and 17 `renderergl2/glsl/*.glsl` post-FX shaders (`bloom_blur`,
`bloom_bright`, `chromab`, `dof`, `filmgrain`, `frost`, `fxaa`, `globalfog_fp`+`vp`, `heathaze`,
`lowhealth`, `raindrops`, `sharpen`, `suppression`, `tonemap_hzm`, `underwater`). That is the gore
pipeline and the entire post-FX chain. Also present: `player.cpp.bak_botinput`, `player.h.bak_botinput`
— **`.bak` files used as the rollback mechanism instead of commits.**

**Consequences:**
1. Every binary currently deployed or released was built from a tree state **no commit can reproduce**.
2. A single `git checkout` destroys ~10k lines with no restore point.
3. Engine claims must be anchored to `file:line`, **not** to history. Not one buglog entry cites a
   commit hash.

**Upstream drift:** upstream tip is `a2f34019` (2026-04-23). The fork has not been rebased in roughly
nine months, so a future merge carries ~9 months of upstream drift on top of a working tree already
~10k lines ahead of its own HEAD.

---

## 1. Protocol coupling — the rules that matter most
<a name="protocol-coupling"></a>

### Which binaries must ship together, and why

| If you change… | You must rebuild and ship |
|---|---|
| `GENTITYNUM_BITS`, `MAX_GENTITIES` | **exe + cgame + game + renderer** — the renderer consumes `ENTITYNUM_WORLD` and had a hardcoded `GORE_MAX_ENTNUM 1024` (bug-930) |
| `MAX_SOUNDS`, `sound_index` width | **exe + cgame + game** (wire format) |
| `MAX_CONFIGSTRINGS` | **exe + cgame** minimum — `gameState_t` is sized by it and `memcpy`'d **whole** across the exe↔cgame boundary (`CL_GetGameState`) **with no API version guard** |
| `MAX_MODELS` | exe + cgame + game (configstring layout) |
| Any `usercmd` bit | exe + cgame + game, **and every remote client** |
| Anything cgame-visible over stufftext | **remote clients need the updated `cgame.dll` too** |
| Renderer-local constants only | that renderer alone — these **cannot** corrupt a mixed set |
| `MAX_CVARS` | **exe alone** — `qcommon/cvar.c` is the only file that names it (grepped 2026-08-08) and the table is exe-side storage, not a wire field. The DLLs reach it through syscalls. |

**⚠️ `build.ps1` ships only 2 of the 4** (`cgame.dll`, `renderer_opengl1.dll`). `openmohaa.exe`,
`game.dll` and `renderer_opengl2.dll` are **manual copies**. A `build.ps1` run that refreshes
`cgame.dll` while leaving a week-old exe in place is exactly the protocol-mismatch shape bug-930
describes — **and that is the state of the real install right now.** See
[TRAPS.md § T10](TRAPS.md#t10).

### Current constants (verified in source 2026-07-29)

| Constant | Value | Anchor | Note |
|---|---|---|---|
| `GENTITYNUM_BITS` | **11** | `qcommon/q_shared.h:1667` | → `MAX_GENTITIES` 2048 (`:1668`) |
| `MAX_MODELS` | **2048** | `q_shared.h:1680` | ⚠️ comment credits **bug-866**; the actual work is **bug-892** |
| `MAX_SOUNDS` | **1600** | `q_shared.h:1742` | 512→1024→1280→**1600**; credited bug-1180 (correct) |
| `SOUND_INDEX_BITS` | **11** | `q_shared.h:1749` | `#error` guard at `:1750-1752` — hard cap 2048 |
| `MAX_CONFIGSTRINGS` | **8192** | `q_shared.h:1787` | was 4096 |
| `MAX_GAMESTATE_CHARS` | **98304** | `q_shared.h:1805` | was 41952 |
| `MAX_CVARS` | **8192** | `qcommon/cvar.c:41` | 2048→4096 (bug-598) →**8192** (bug-1582); one-shot 80% warning in `Cvar_Get`. Consumed by ARCHIVED content, so it grows between sessions — see [TRAPS.md § T4](TRAPS.md#t4). |
| `MAX_RELIABLE_COMMANDS` | **1024** | `qcommon/qcommon.h:215` | **must stay a power of two** — `& (N-1)` masked; in-code note at `:211`. Cost: 1024 × `MAX_STRING_CHARS` = **2 MB per buffer, per `client_t` AND per client-side `clc`** — never measured. |
| `MAX_SNAPSHOT_ENTITIES` | **2048** | `server/sv_snapshot.c:285` | file-local; the missed 4th member (bug-1186) |
| `MAX_ENTITIES_IN_SNAPSHOT` | **2048** | `cgame/cg_public.h:41` | bug-934 |
| `MAX_PARSE_ENTITIES` | **8192** | `client/client.h:98` | a power-of-two ring that wrapped inside a single busy 2048-entity snapshot at 2048 |
| `MAX_TIKI_LOAD_ANIMS` | **8192** | `qcommon/tiki.h:36` | was 4095 |
| `MAX_BODYQUEUE` | **128** | `fgame/actor.h:306` | was 5. ⚠️ its comment still says "MAX_GENTITIES 1024" |
| `MAX_SKELMORPH` | **131072** | — | was 12800; bug-1214, silent OOB write |
| `MAX_ENTITIES` (renderer refentity cap) | **1023** | `renderercommon/new/tr_types_new.h:33` | ⚠️ note the `new/` path — a grep at `renderercommon/tr_types_new.h` returns nothing and reads as "already fixed" |

### The reference implementation of how to record a limit

**Read `qcommon/q_shared.h:1690-1755` before touching any capacity constant.** ~60 lines enumerating
the four binding constraints **in the order they bite**, each tagged with the bug that discovered it
**including the two failed attempts**, backed by a compile-time `#error`. It is the best piece of
institutional memory in the codebase. Detail in [TRAPS.md § T4](TRAPS.md#t4).

Note constraint (1) — the configstring layout `CS_AXIS = MAX_SOUNDS + 2393 < MAX_CONFIGSTRINGS` — is
**no longer binding** since the 4096→8192 raise (it would now permit ~5800). The binding ceiling is
now the 11-bit wire cap of 2048, **and that one fails at build time.**

---

## 2. By subsystem

### `fgame` — server game logic (the largest coop surface)

| Change | Anchor |
|---|---|
| **Entity-pool integrity** — symbolic `AllocEdict` clamp, ~25 NULL/type guards upgraded from non-NULL to `item && item->isSubclassOf(Item)`, `g_droppeditemlife 60`, `PruneStaleInventory` heals rather than skips, `AddItem` duplicate-check | bugs 914–935 |
| **AI grenade un-veto** — `GrenadeWillHurtTeamAt` `length()` → `lengthSquared()`; un-vetoed ~all AI grenades and the entire kick/return chain | `actor.cpp:10361`, `actor_grenade.cpp:393/401/408/423` |
| **AI combat tuning** — retarget un-pin, suppress bypass, plant-band, jink (`m_iCoopJinkTime`, dormant) | `actor_turret.cpp:151`, `actor_cover.cpp:27` |
| **Corpse persistence** — `MAX_BODYQUEUE` 5→128, `EV_DeathSinkStart` gated to `GT_SINGLE_PLAYER` | `actor.h:306`, `actor.cpp:11148`, `~12059` |
| **Corpse blast impulse** — already-dead sentients flip to `MOVETYPE_TOSS` with outward+up velocity (the vanilla knockback path excludes `MOVETYPE_NONE`, so corpses never flew). `g_corpseImpulse 1.0` | `weaputils.cpp RadiusDamage ~3112` |
| **Blast tinnitus ping** — `RadiusDamage` stamps `coop_blastPing` (a pure-script fix is impossible: the sight trace means zero damage = zero script signal) | `weaputils.cpp` |
| **Wounded-AI blood trails** — `Sentient::TryDropBloodTrail` from `Actor::Think` | `sentient.cpp` |
| **Headshot kill cue** — hook moved `BulletAttack` → `ArmorDamage` alive→dead edge | bug-1142 |
| **Helmet pop** — `EV_Stop`→`HelmetTouch` (`G_Impact` skips `SOLID_NOT` so `EV_Touch` never arrives), `g_helmetlife`, clank, `VectorScale`→`VectorMA` velocity fix | bugs 614/615 |
| **Holster offset** — was stored but never passed to `attach()` | bug-616, `weapon.cpp AttachGun` |
| **Sprint / walk / stamina** — `TickSprint`, `ClientMove`, `BUTTON_COOPWALK (1<<12)` | `player.cpp ~11851`, `~4062` |
| **ADS on its own bit** — `BUTTON_COOPADS` bit 13, **the last free usercmd bit** | `player_conditionals.cpp CondCoopAds` |
| **Cover system** — `Player::TickCoopCover`, `PMF_COOP_COVER` (pm_flags bit 13) | bugs 303–329 |
| **Lobby input bridge** — `Player::TickCoopLobbyInput` reads A/D/F from usercmd so remote clients need no binds | `coop_lobby1_build` |
| **Bot rig** — `Player::CoopBotDrive`, `coop_botInput 1` injects the host client's usercmd and fires **real bullets** | still live in `player.cpp` |
| **Exact ammo** — new Sentient `getammo`/`setammo` events (the stock `ammo` event only **adds**) | `sentient_combat.cpp` |
| **Landmine contents** — `TriggerLandmine::SetDamageable` → `CONTENTS_WEAPONCLIP` (still in `MASK_SHOT`, movement passes, touch still detonates) | bug-938, `trigger.cpp:3240` |
| **Vehicle-turret owner view** — `UpdateOwner` now `m_bCoopView3p \|\| !m_pViewModel` + proper singleClient | bug-647, `vehicleturret.cpp` |
| **MG42 overheat** — player and AI heat cycles | `weapturret.cpp TurretGun::P_ThinkActive` |
| **e3l4 set-piece guards** — 5 NULL-deref/loop guards incl. a **retry CAP** in `G_PushEntity` (an earlier guard made the projectile survive, so the engine's goto-retry loop spun forever) | `entity.cpp`, `weaputils.cpp`, `g_phys.cpp`, `player.cpp`, `vehicle.cpp` |
| **m1l2a/b, m1l3c connect crash** — `Actor::MoveOnPathWithSquad` obstacle branches call `G_GetEntity(0)`, NULL while client 0 is CONNECTING (`CS_PRIMED`, pre-`ClientBegin`) | `actor.cpp ~3341/~3361`, `sentient.cpp:3016` |
| **Print gating** — `ScriptThread::Println` early-returns on `!developer->integer` at **three** sites | `scriptthread.cpp:2858`, `:2869`, `:2883` |
| **Removed: decapitation** — `CoopGoreTryDecapitate`, its `ArmorDamage` call, header decl, `HeadGibObject`, `coop_decap*` cvars all removed **at source level** so a rebuild cannot reintroduce them. `object.h`/`object.cpp` restored byte-identical to HEAD. **Verified: zero symbols remain.** | bug-892 |

### `cgame` — client game / prediction / view

- **`CG_AdsForceFirstPerson`** — the **single decider** for staged 3P shoulder ADS, used by both 3P
  call sites. Edit the helper, never the sites.
- **`CG_LockRiderOriginToVehicle`** (`cg_predict.c`) — the smooth-ride root cause fix: a
  `PMF_NO_MOVE` rider's view was interpolated independently of the vehicle; now pegged to the nearest
  `ET_VEHICLE`'s own `lerpOrigin`. This is what made **solid** vehicle riders possible.
- **`CG_UpdateHudFade`** (`cg_drawtools.cpp`) + `UI_ApplyHudFadeAlpha` (`cl_ui.cpp`) — post-Motion
  `SetHudFadeMul`, **never** `m_alpha` (urc `fadein` widgets re-pin it every frame).
- **`CG_UpdateEnvReverb`** (`cg_view.c:362`) — the auto-reverb driver, already present and forgotten.
- **`CG_OffsetFirstPersonView`** (`~771-825`) — weapon weight spring lag.
- **`CG_OffsetThirdPersonView`** + `cl_input.cpp:894-912` — 3P free cam. **⭐ Zero-ABI client→cgame
  bridge:** the FAKK-era globals `camera_offset`/`camera_active` (`cl_main.cpp:147-149`) are never
  written by anything, but `cgi.get_camera_offset()` returns a live `float*`.
- **`CG_EntityShadow`** (`cg_modelanim.c ~674`) — directional decal shadows.
- **`CG_ActorOverheadIcon`** (`cg_modelanim.c CG_PlayerTeamIcon:56`) — ~40 lines, zero fgame changes,
  because `EF_AXIS` is already set on every German actor's entity state every frame.
- **`CG_MakeBulletTracerInternal`** (`cg_parsemsg.cpp`) — suppression FX reusing the engine's own ZING
  closest-approach computation, which already excludes the first/last 128u of flight.
- **`SFX_COOP_GUNSMOKE`** (`cg_specialfx.cpp`).
- **`cg_servercmds_filter.cpp:304-316`** — scoped exemptions to the Reborn-exploit whitelist. See
  [TRAPS.md § T8](TRAPS.md#t8).
- **`s_adsGunTune[]`** (`cg_modelanim.c`) — per-gun ADS pose table, 45 guns hand-dialled.

### `renderergl1` — the shipping renderer

- **`tr_postprocess_gl1.c`** — the full post-FX chain: SSAO, DoF, bloom, god rays, grade, FXAA,
  sharpen, heat haze, rain. **⭐ Root cause of two failed attempts:** raw `qgl*` calls desynced the
  engine's `glState` **cache**. Drive everything through `GL_State`/`GL_Bind`; `glPushAttrib` is
  unlinkable in this DLOPEN renderer.
- **⚠️ The 3D→2D hook MUST live in `Set2DWindow` (`tr_draw.c`), not `RB_SetGL2D`** — cgame enters 2D
  via the exported `re.Set2DWindow` directly. Anything added to `RB_PostFxApply` is therefore
  automatically HUD-safe.
- **`RE_RenderScene` sun bridge** (`tr_scene.c`) — publishes `r_coopSunAz`/`El`/`Valid` from
  `tr.sunDirection` so shadows follow each map's real sun.
- **`tr_gore.c`** (836 lines, **untracked**) — UV wound rendering. Required **adding**
  `qglGetTexImage` to `QGL_DESKTOP_1_1_PROCS` (bug-734).
- **`LoadTGA` softened** (`tr_image.c ~1670`) — an unsupported base-game TGA lazy-loading mid-scene
  hit `ri.Error(ERR_DROP)` and crashed the whole server, with an error string that didn't even name
  the file. Now `PRINT_WARNING` + default texture. ⚠️ **The first fix attempt patched the WRONG file —
  there are FIVE TGA parsers in-tree** and the active one is `renderergl1/tr_image.c`, not
  `renderercommon/tr_image_tga.c`. `cm_fencemask.c` and `cg_lightstyles.cpp` still `ERR_DROP`.
- **`tr_local.h:1446`** — `skel_index` sized by `MAX_GENTITIES`, not a bare `[1024]` (bug-932).

### `renderergl2` — the sandbox renderer (29 uncommitted files, +5,794 lines)

**Not shipping — but a v1.1.51-era `renderer_opengl2.dll` IS in the shipped manifest.** `cl_renderer`
defaults to `"opengl1"` (`client/cl_main.cpp:3231`).

| Fixed | Detail |
|---|---|
| **Invisible actors — two independent mechanisms** | (a) `R_AllocModel` slot reuse never re-stamped `mod->index`: `R_FreeModel` memsets the whole `model_t` **including index**, so the next model into a freed slot loaded fine but `R_RegisterModelInternal` returned index 0 = "registration failed" and the cgame stored handle 0 — undrawable for the rest of the session. One line: `mod->index = i;` (`tr_model.cpp:383`, bug-1135). (b) `skel_index[MAX_GENTITIES]` was a bare `[1024]` — the OOB read in `R_UpdatePoseInternal` can spuriously equal `frame_skel_index` and skip `TIKI_SetPoseInternal`, so a **high-entnum** character never gets posed (`tr_local.h:2339`). **Two distinct fixes for one symptom family — remember both.** |
| **Gun over menus** | Menu quads were being **depth-REJECTED**, never mis-ordered. gl1 force-disables depth test for every 2D stage; gl2 never did. Default `LIGHTMAP_2D` shaders carry the bit themselves, which is why plain pics/text hid the bug and only *scripted* menu shaders failed — exactly in the view-model silhouette. Gated on `backEnd.projection2D` in `RB_IterateStagesGeneric` (bug-1144). **Verified by an explicit A/B: a pre-fix DLL was built by disabling only the new branch, both kept, deployed file swapped between runs.** |
| **Settings-apply crash** | `CL_ShutdownRef`/`CL_InitRef` unload and reload the renderer DLL, so **every `cvar_t*` and every function-scope static is zeroed**. `CL_Vid_Restart_f` then re-registered every UI menu shader into a renderer whose `R_Init` had not run. gl1 survives because it calls `R_Init` from `GetRefAPI` (DLL load); gl2/rend2 calls it from `RE_BeginRegistration`. Fixed by dropping the premature `UI_ResolutionChange()` + `R_ShaderSystemReady()` guards on 5 `RE_Register*` entry points. Verified over 3 consecutive `vid_restart`s (bug-1145). |
| **Renderer-zone leak** | +53 MB and +69,600 blocks per Advanced-Graphics apply. The pre-clear sat behind a **function-scope `static`** — but `vid_restart` reloads the DLL, so the static reset every time and `ri.Hunk_Clear()` **never ran**; the earlier bug-1128 fix had never once executed on a runtime restart. Real precondition was `R_LevelMarksFree` dereferencing `dcl_editmode`, a cvar gl2 doesn't register until later in the same function. Measured 57.6→111.1→164.4→217.8 MB pre-fix, flat 57.6→57.7 post (bug-1146). **⭐ In this engine a function-scope static in a renderer DLL is NOT persistent state.** Measure with `rcon meminfo`. |
| **Frozen 2D shader clock** | `Set2DWindow` set `backEnd.projection2D = qtrue` at the top then tested `if (!backEnd.projection2D)` at the bottom — dead branch, so `tess.shaderTime` stayed stale from the last 3D scene. Fixed by capturing `wasIn2D` first (bug-1147). ⚠️ **Explicitly never eyeball-verified.** |
| **HZM grade never executed** | `FBO_Blit` passes `UNIFORM_COLOR`, whose name is `u_Color`; the shader declared `u_Grade`. Location −1, every set silently dropped. Compounded by an archived `r_toneMap 0`. Measured near-band delta +27.3 → −1.0. **Dissolved the entire "gl2 is 40% brighter" thread — that reading was taken with `r_toneMap 0`, which is not a bypass** (`tr_backend.c:1894-1904` falls through to an `r_cameraExposure` blit defaulting to 1, i.e. a 2× multiply) (bug-1148). |
| **Framebuffer ghosting** | `tr.renderFbo` persists across frames, so a frame with **no scene submitted** (fullscreen menu) still shows the last 3D content. Fix was a first-2D-draw clear (`R_Ensure2DClear`), **not** a draw-order change (bug-1140). |
| **Character sun-cascade shadows, SSAO, dynamic-light shadows, MSAA cvar, sun bridge** | bugs 1154, 1209, 1210, 1211, 1123; `r_hzmDlightShadows` |
| **Bloom ported** | Byte-ports of gl1's `BRIGHT_FS`/`BLUR_FS` on `tr.quarterFbo[0..1]`. ⚠️ **A no-op at the shipped threshold** — gl2 thresholds the **pre-tone HDR** buffer while gl1 thresholds its display-referred LDR backbuffer. Same chain position, different numeric domain: the slider does not mean the same thing on both renderers (bug-1149). |

**⚠️ `r_globalFogDebug` is still registered `CVAR_TEMP` at `renderergl2/tr_init.c:1926`** — it was
temporarily moved off `CVAR_CHEAT` because a listen server runs `sv_cheats 0` and clamped it back to
0 so the debug views could never enable. **Restore it.**

**Diagnostic scaffolding is deliberately NOT stripped** — inventoried at ~90 interleaved sites
(`tr_shade.c` 36, `tr_model.cpp` 53 → now 31, `tr_scene.c` 4, plus `CMDTRACE`/`IMM2D`). Deferred for
good reasons (`CMDTRACE`/`IMM2D` solved bug-1144; the heavy probes are gated behind `r_skeldiag`
default 0; a 90-site edit is not a safe tail-of-session change). `tr_model.cpp`'s
`SKELREG`/`SKELDIAG`/`SKELDRAW` are ungated but **deduped to once per model handle** — bounded by
model count, not frame rate (`tr_model.cpp:50-51`).

### `qcommon` / `server` / `client`

- **`cm_load.c:856`** — reads `cmpatch/<map>.txt` from the pak and zeroes listed brush contents. This
  is the brush-surgery mechanism that replaced regional playerclip zones. **⭐ The SERVER loads
  `maps/<name>_sml.bsp`, so the suffix must be stripped.**
- **`sv_snapshot.c:549-553`** — the silent-discard branch now has a warning naming the constant to
  raise. ⭐ **When you fix a silent limit, add the warning too.**
- **`common.c`** — engine hook exec'ing `coop_defaults.cfg` **before** the saved config, so its values
  are true defaults a menu change can override and persist (bug-710).
- **`cl_main.cpp:2347`** — the client **re-latches** the server address to whoever answers
  `getchallenge`. This is why NAT port remaps work for free.
- **`CL_SendReport_f`** + `sys_win32.c Sys_SendReport` — the bug-report path. **This build has no
  libcurl at all**; it writes a payload file and spawns a no-window PowerShell.
- **`Sys_SigHandler`** — no longer converts hardware faults to anonymous aborts, so dumps carry true
  context. `CL_Init` terminate-handler → `hzm_fatal.log`.
- **`alias.c`** — `convalias[40]` bounds guard (the m3l1a dog-model crash).
- **`MAX_CVARS 4096`**, `Com_Error` guard.
- **`sdl_glimp.c GLimp_SetMode`** + `r_desktopfullscreen` — display-mode selector.
- **Sound**: `s_sfxvolume` in `snd_dma_new.cpp S_StartSound`; `AL_MAX_GAIN 8.0` and a music-exempt
  duck in `snd_openal_new.cpp openal_channel::set_gain`; distance model `INVERSE` →
  `LINEAR_DISTANCE_CLAMPED` at context init; `s_openaldevice` sanitised once per process.

### `tiki` / `skeletor`

- **`MAX_TIKI_LOAD_ANIMS` 4095→8192** — and **⭐ two companion STACK arrays** (`order[]`,
  `temp_aliases[]`) were still sized by `MAX_TIKI_ALIASES 4095`, so any model with >4095 anims
  (exactly `new_generic_human.tik`) tripped the `/GS` cookie = `0xc0000409` in `ucrtbase.dll`.
  **⭐ Lesson: when raising a `MAX_*`, grep for sibling arrays sized by a RELATED BUT DIFFERENT
  constant indexed by the same count.** Diagnosis came from the **Windows Application event log**, not
  the game log. The "Box data is corrupted for `allied_pilot.skd`" line is a **red herring**.
- **`MAX_SKELMORPH` 12800→131072** — a silent OOB write in `skeletorMorphCache` (bug-1214).
- **`tiki/tiki_tag.cpp TIKI_GetFrameInternal`** — the `^~^~^ POSECHK` diagnostic behind
  `tiki_posecheck 1`, added instead of another guess at bug-1213.
- `loadsurfaces` / `headmodels` / `headskins` / `AddChannel` / `fAnimWeights` guards.

### `uilib`

- **`FindResponder` v2** — stacked `enabledcvar`-gated Buttons were unclickable because hit-testing
  ran in reverse file order checking only `m_visible`. **The ARMORY requires this exe** (bug-587).
- ⚠️ **`Menu::GetContainerWidget` returns only item #1** — a Menu is a **flat sibling list**.
- ⚠️ **An unregistered font in a `.urc` crashes the game at UI init** — only `verdana-12` and
  `facfont-20` are safe (bug-519).
- ⚠️ **Never trigger a renderer restart from inside a menu** — `ui_checkrestart` on an APPLY button
  issues `vid_restart` while UI fonts are live; gl2 then tears down and re-initialises →
  `0xC0000005` in `InitShaderEx+0xE7`, stack `UIFont::CheckRefreshFont` (bug-1181, `REVERTED`).
- **`R_LoadFont_sgl`** (`renderergl2/tr_font.cpp`) — HZM hi-DPI feature: builds `<name>@3x` and, when
  `fonts/<name>@3x.RitualFont` exists, loads **that**, resolving the sheet as
  `gfx/fonts/<name>@3x.tga`. **This is why a plain `gfx/fonts/*.tga` swap is silently inert.**

### `tools`

- **`md5_2_skX`** — MD5 ⇄ skd/skc/tik converter, round-trip validated. ⚠️ **Raw output is
  engine-lethal (bug-1002):** writes `ofsCollapse`/`ofsCollapseIndex` = 0, read unconditionally →
  `TIKI_SortLOD` stack OOB → access violation in `Entity::setModel`. Every converted skd must go
  through `skd_add_collapse.py` + `skx_validate.py`. Hardcodes a −90 X roll on the root bone.
- **`hzm_rendezvous.c`** + `qcommon/net_rendezvous.c` — NAT hole-punch phase 1.

---

## 3. Engine cvars

**217 unique HZM cvars over 303 registration sites.** Families: 57 `r_pp*`, 11 `r_char*` (gl2 only),
147 `coop_*`, plus `r_goreUV`/`r_goreDebug` registered separately in **both** renderers. Full table:
[32-inventory-engine-cvars.md](32-inventory-engine-cvars.md).

**⚠️ 8 cvars are registered twice with different values, so the effective default depends on which
renderer module loads:**

| Cvar | gl1 | gl2 |
|---|---|---|
| `r_ppSSAO` | `"1"` `CVAR_ARCHIVE` (`renderergl1/tr_init.c:1459`) | `"0"` `CVAR_ARCHIVE\|CVAR_LATCH` (`renderergl2/tr_init.c:1492`) — **differs in both default and latching** |
| `r_ppFXAA` | `"0"` (`tr_init.c:1472`) | `"1"` (`renderergl2/tr_postprocess.c:758`) |
| `r_ppExposure` | `"1.0"` | `"0.889971"` |
| `r_ppContrast` | `"1.0"` | `"0.951289"` |
| `r_ppSaturation` | `"1.0"` | `"1.031519"` |
| `r_ppHeatAmount`, `r_ppLowHealthAmount`, `r_ppSuppressAmount` | `"1.0"` | `"1"` — harmless, but reveals **three independent registration sites** for one cvar (cgame + gl1 + gl2) |

The gl2 trio `0.889971 / 0.951289 / 1.031519` are somebody's session-tuned values baked into C++ as
defaults.

**Whether these actually bite at runtime is UNRESOLVED** — it depends on module load order and on
`Cvar_Get` re-registration semantics (does the second default win, or is it ignored?). Read
`qcommon/cvar.c` before calling them defects rather than untidiness. **Note `Cvar_Get` OR-combines
flags** — that is a confirmed real defect class (bug-1125), and `r_lodscale`'s instance is **fixed**:
both `renderergl2/tr_init.c:1799` and `:1945` now register `"5"` `CVAR_ARCHIVE`, with the explanatory
comment at `:1799`.

**`coop_defaults.cfg` vs `autoexec.cfg`:** verified strictly disjoint (zero shared cvar names), so
they never fight. See [TRAPS.md § T7](TRAPS.md#t7).

---

## 4. Known engine-side unknowns

- **What is inside the ~10,750 uncommitted lines.** Measured in aggregate, not read. A concurrent
  workflow is editing `renderergl2/`.
- **Whether the deployed `openmohaa.exe` was actually built from the older sources.** mtime proves
  when a file was written, not what it was compiled from. Needs binary inspection.
- **Whether `maintt\cgame.dll` shadows the GOG-root copy for MODULE loading.** A 33-day-old copy
  (2026-06-26, 570,880 B) sits in **both** maintt trees while the root has a current one (617,984 B).
  Needs reading the engine's module-load path (`sys_dll` / `qcommon/files.c`).
- **A conceptual upstream-vs-HZM feature diff.** The fork is quantified (125 files / ~12,100 committed
  lines) but the changes are not classified into "HZM added X" vs "HZM modified upstream Y." That
  needs a per-hunk read of `fgame` and `cgame` — a pass comparable in size to this whole audit.
- **The `MAX_RELIABLE_COMMANDS` 512→1024 cost** — 2 MB per buffer, per `client_t` and per client-side
  `clc`. Never measured in any record.

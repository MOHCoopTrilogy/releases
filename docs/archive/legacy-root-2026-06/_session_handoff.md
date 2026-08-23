# SESSION HANDOFF — 2026-07-28 (gl2)
Read me first in a fresh session. Companion: _phillips_dossier.md.

## ✅ CLOSED THIS SESSION

### #73 GUN OVER MENUS — FIXED, capture-verified (bug-1144)
Not draw order, not the stale-FBO ghost, not the frame-start clear, not `cl_invrender.cpp`.
The command trace proved menu 2D IS drawn last, so it was never ordering — the menu quads were
being **depth-rejected**.
- `renderergl1` force-disables depth test for every 2D stage
  (`tr_shade.c` RB_StageIteratorGeneric: `if (backEnd.in2D) GL_State(stateBits | GLS_DEPTHTEST_DISABLE)`).
  `renderergl2` never did.
- Default `LIGHTMAP_2D` shaders carry that bit themselves → plain pics/text hid the bug. Every
  **scripted** menu/HUD shader (`escmenu`, `menu_button_trans`, `m_buttonhighlight`, weapon-bar art)
  keeps Q3's depth-test-ON default. The view model rasterises into the **near** depth slice, so those
  quads were rejected exactly in the weapon silhouette.
- UI-only frames keep the same stale near depth (`RB_DrawBuffer`'s ghost clear is COLOR-only) → the
  main-menu gun shadow.
- FIX: `renderergl2/tr_shade.c` RB_IterateStagesGeneric, gate on `backEnd.projection2D` (gl2's `in2D`).
- VERIFIED with a real before/after (pre-fix DLL built by disabling only the new branch, both DLLs
  kept, deployed file swapped between runs): ESC board (matches gl1 reference), weapons bar (pre-fix
  truncated on the hand silhouette, grenade+heavy slots missing), main-menu gun shadow.
- ⭐ Main-menu repro needs a FULLSCREEN menu over a LIVE session (`rcon pushmenu main`).
  **Disconnecting does NOT reproduce it** — `UI_ClearBackground` clears depth once `clc.state <= CA_PRIMED`.
  Every earlier hunt went out via disconnect and saw a clean menu.

### SETTINGS-APPLY CRASH — FIXED, verified (bug-1145)
Repro without the UI: `rcon seta r_ext_framebuffer_multisample 8` + `rcon vid_restart` (APPLY only
runs `ui_checkrestart`, which auto-issues vid_restart for a latched knob).
- `CL_ShutdownRef`/`CL_InitRef` **unload and reload the renderer DLL**, so every renderer global —
  every `cvar_t*`, every function-scope `static` — is back to zero.
- `CL_Vid_Restart_f` then called `UI_ResolutionChange()` BEFORE `CL_StartHunkUsers()`, re-registering
  every UI menu shader into a renderer whose `R_Init` had not run. gl1 survives because it calls
  `R_Init()` from `GetRefAPI` (DLL load); gl2/rend2 calls it from `RE_BeginRegistration`.
- Dumps: `InitShaderEx+0xE7` read 0x30 off RAX=0 (`cvar_t.integer` = `r_pbr->integer`), then after
  guarding shaders a second fault `R_LoadImage+0x85`, same NULL-cvar-at-0x30 signature.
- FIX (a) dropped the premature `UI_ResolutionChange()` — `CL_StartHunkUsers` already calls it right
  after `CL_BeginRegistration`, and `cls.rendererRegistered` was just cleared so it always runs;
  (b) `R_ShaderSystemReady()` guards on the 5 `RE_Register*` entry points in `tr_shader.c`.
- VERIFIED: 3 consecutive vid_restarts (MSAA 8→4→8) with respawn — no crash, no dump, world /
  viewmodel / HUD / menus / fonts / rain all fine, ESC board over the gun.

### RENDERER-ZONE LEAK — FIXED, measured (bug-1146)
`RE_BeginRegistration`'s pre-clear block sat behind `static qboolean s_bReregistration`, but
vid_restart reloads the DLL so that static reset every time — `ri.Hunk_Clear()` **never ran**, i.e.
the bug-1128 fix had never actually executed on a runtime restart.
Measured with `rcon meminfo` (TAG_STATIC_RENDERER = "static renderer memory pool"):

| | before pass 1 | after 1 | after 2 | after 3 |
|---|---|---|---|---|
| pre-fix  | 57.6 MB / 69,517 blk | 111.1 MB | 164.4 MB | 217.8 MB |
| post-fix | 57.6 MB / 69,525 blk | 57.7 MB  | 57.7 MB  | 57.7 MB  |

= **+53 MB and +69,600 blocks leaked per Advanced-Graphics apply**, now flat.
FIX: deleted the static and made the block unconditional (gl1 parity) after fixing the real
precondition — `R_LevelMarksFree` now checks `!dcl_editmode || !dcl_editmode->integer` (it
dereferenced a cvar gl2 does not register until `R_Init` runs LATER in the same function).
⭐ `rcon meminfo` is the measurement tool for any renderer-zone question.

### FROZEN 2D SHADER CLOCK — FIXED (bug-1147)
`Set2DWindow` set `backEnd.projection2D = qtrue` at the top then tested `if (!backEnd.projection2D)`
at the bottom — a dead branch, so `refdef.time`/`floatTime` never refreshed. The UI's immediate 2D
path (`Draw_StretchPic` → `RB_BeginSurface`) never goes through `RB_SetGL2D`, the only other
refresher, so `tess.shaderTime` was stale from the last 3D scene ⇒ animated menu/HUD shaders were
frozen. Fixed by capturing `wasIn2D` before raising the flag (gl1's `in2D` semantics).
NOTE: not eyeball-verified — needs a menu with an animated shader to confirm visually.

### GRADE WAS NEVER RUNNING — FIXED (bug-1148) ⭐ dissolves the near-band defect
Two stacked faults meant the ported gl1 grade had, as far as I can tell, never once executed:
1. **Uniform name.** `FBO_Blit` hands the grade over as `UNIFORM_COLOR`, and `GLSL_InitUniforms`
   resolves uniforms by the NAME in `tr_glsl.c uniformsInfo`, which is `u_Color` — but
   `tonemap_hzm_fp.glsl` declared `uniform vec4 u_Grade`. Location -1, every set dropped, and the
   shader would have rendered a flat mid-grey frame if it had run.
2. **Archive poisoning.** An earlier rcon probe set `r_toneMap 0` (and `cg_drawviewmodel 0`); both
   are CVAR_ARCHIVE, so they were written into the sandbox `home_test` omconfig and silently
   retained by every later boot. With `r_toneMap 0`, `RB_ToneMap` is never called at all.

Measured on e2l2 (mean/near/far), gl1 shipped = **42.7 / 51.7 / 43.4**:

| gl2 configuration | mean | near | far |
|---|---|---|---|
| poisoned, no tone stage at all | 46.1 | 78.8 | 41.1 |
| rend2 Hable (`r_tonemapMode 0`) | 34.3 | 46.5 | 33.6 |
| **HZM parity grade (`r_tonemapMode 1`)** | **36.9** | **50.7** | **36.1** |

**Near-band delta went from +27.3 to −1.0.** The "+26 near band" that drove this whole thread was
an artifact of the tone stage not running. The residual is now UNIFORM (−6 mean, −7 far), which is
a different problem: gl2's raw scene is much brighter than gl1's (46.1 vs 32.8 pre-grade), so the
same ACES curve lands differently. That is upstream of all post-FX.

### BLOOM PORTED — first stage of the gl1 chain (bug-1149)
`glsl/bloom_bright_fp.glsl` + `glsl/bloom_blur_fp.glsl` are byte-ports of gl1's `BRIGHT_FS`/`BLUR_FS`;
`RB_HZMBloom` (tr_postprocess.c) does bright-pass → H blur → V blur → additive, on the existing
`tr.quarterFbo[0..1]` (already half-res, exactly gl1's bloom buffer size). No new uniforms — the
threshold rides `UNIFORM_COLOR.x` and the blur direction rides `UNIFORM_INVTEXRES`; the additive
composite is `FBO_Blit` with a NULL program (= `tr.textureColorShader` = gl1's `ADD_FS`). Dispatched
immediately before the tone stage, matching gl1's order, driven by the **same**
`r_ppBloom` / `r_ppBloomThreshold` / `r_ppBloomIntensity` levers.
PROVEN at deliberately extreme settings (threshold 0.05, intensity 8) on m3l1a: mean 123.5 → 171.4,
near 58.0 → 178.8, correct wide Gaussian glow.
⚠️ OPEN: at the shipped threshold 0.664756 it is a **no-op** on e2l2 and m3l1a, because gl2
thresholds the PRE-tone **HDR** buffer while gl1 thresholds its display-referred **LDR** backbuffer
— same position in the chain, different numeric domain, so the slider does not mean the same thing
on both. (gl1's own non-grade post-FX also moves e2l2's mean by only +0.3, so this is not a
regression.) Decide: re-map the threshold into the HDR domain, or move gl2's bloom after the tone.

### REMAINING gl1 POST-FX WITH NO gl2 EQUIVALENT
gl1 order: SSAO → DoF → **bloom (done)** → god rays → **grade (done)** → FXAA → sharpen → heat haze
→ rain. Your shipped config has `r_ppSSAO 0`, `r_ppDoF 1`, `r_ppSunShafts 1`, `r_ppFXAA 1`,
`r_ppSharpen 1`. All live in `renderergl1/tr_postprocess_gl1.c` as self-contained GLSL — the bloom
port is the template for each.

### SCENE-BRIGHTNESS DELTA - RETRACTED (my earlier conclusion was wrong)
I previously reported "gl2 pre-grade 46.1 vs gl1 pre-grade 32.8, so gl2's scene render is ~40%
brighter". **That is wrong.** The 46.1 reading was taken with `r_toneMap 0`, which I treated as
"no tone stage". It is not a bypass: `tr_backend.c:1894-1904` falls through to
`else if (r_cameraExposure->value != 0.0f)` and blits `pow(2, r_cameraExposure)` with
`GLS_SRCBLEND_DST_COLOR|GLS_DSTBLEND_ZERO` - and `r_cameraExposure` defaults to **"1"**
(`tr_init.c:1423`), i.e. a **2x multiply**. So that measurement was an exposure-doubled frame, not a
raw scene, and there is no evidence of a large raw-scene divergence.
The honest remaining number is the graded comparison: gl1 42.7 vs gl2 36.9 mean (-5.8), near band
within 1.0. Note `r_cameraExposure` is CVAR_CHEAT, so it snaps back to 1 on map change whenever
`sv_cheats` is 0 - it cannot be used as a lever on a listen server.

## 🔎 INVESTIGATED, NEEDS USER INPUT

### LOADOUT "not applied" — COULD NOT REPRODUCE
Ran the real path (`loadout_hostSeed` → `loadout_set` → `loadout_rebuild`) five ways: e2l2 first
spawn, m1l1 (scripted-kit map), e2l2 death→respawn, the user's exact picks (`coop_lo1..4` =
04 G43 / 12 SPRINGFIELD SNIPER / 48 COLT M1911 / 64 M2 FRAG), and finally the user's own `qkey` +
`omconfig.cfg` + `save/*.dat` cloned into the isolated sandbox with **nothing seeded** — all four
picks equipped every time, correct guns on screen.
⭐ THE ONE FAILURE MODE THAT DOES REPRODUCE: an **empty unlock record** → every pick denied
(`Armory: X is LOCKED`) → silent fallback to the MAP DEFAULT kit = exactly the reported symptom.
Record = `coop_mod/save/unlocks_<cl_guid-hash>.dat`, identity from `player.coop_guid`
(`xp.scr::xp_identify`). User's file `unlocks_609F287B3808BAD639F214D3732FCB5D.dat` (50 entries,
contains g43 + springfield) is intact.
**ASK: which map, what gun did they actually get, and did an `is LOCKED` line flash at spawn?**

### GROUND SEAM (m3l3) — gl1 CONFIRMED, evidence is STALE
- Their play install runs `cl_renderer "opengl1"` and `shot0245.tga` came from it → the seam is in
  gl1 → content, not a gl2 defect. Question closed.
- Texture identified: `textures/wilderness/m3l3grass_bocroad_new`. Tiled 3×3 it is obvious: a **cart
  road with dark grass verges baked into the top/bottom edges**. Tiled over a wide ground area the
  verges repeat as hard parallel stripes. NOT a wrap seam (hence the 275-texture pass did nothing)
  and NOT a scale mismatch.
- Row-band measurement: vanilla 512 spread 59.2 / σ15.0 · **HD world 1024 spread 72.1 / σ20.0** ·
  groundfix 1024 spread 59.7 / σ14.9. The HD upscale amplified the verge ~22%.
- ⭐ `zzzzzzzz_hd_groundfix.pk3` already fixes this exact texture, is the winning pak (seamfix does
  NOT contain it), and was built **18:02 Jul 27 — 19 minutes AFTER the 17:43 screenshot**. The later
  "seamfix didn't resolve it" note was drawn from that same pre-fix shot. **No post-fix look exists.**
- NEXT: one fresh look at that courtyard before any more texture or UV work.

### FOG — near band EXONERATED (and see bug-1148 above: the defect was the grade not running)
`r_globalFogDebug 2` capture on e2l2 (scratchpad/gl2test/fogdbg.ps1, output in gl2test/fog/).
Latched params `start=-256.0 end=3000.0 color=0.250/0.260/0.280 projZNear=4 projZFar=5008
centerDist=352.1 centerFrac=0.187 identityLight=1.000` — identical to what gl1 feeds fixed-function
`GL_FOG_LINEAR` (`renderergl1/tr_backend.c` RB_SetupFog uses `farplane_bias`/`farplane_distance`/
colour × identityLight), so the parameters match by construction.
**Measured fraction: near band 1.6%, far band 22.5%, sky ~fully fogged.**
⭐ VERDICT: fog contributes essentially nothing near the camera, so the e2l2 near-band **+26 luma is
the tone/grade stage, not the fog**. Do not touch the fog curve for it.
⚠️ `r_globalFogDebug` was CVAR_CHEAT and a listen server runs `sv_cheats 0`, so it was clamped back
to 0 and the debug views could never be enabled (first run gave 3 identical captures). Changed to
CVAR_TEMP in `tr_init.c` with an in-code note to revert at the strip.
Still open from the earlier pass: t2l1 within 2.5 luma (good), e2l2 mean +9.4 / near +26.6.
FALSIFIED, do not retry: HDR clamp before ACES; autoexec/`r_mapOverBrightBits`; fog-pre-tone alone.

## ❌ NOT DONE (deliberate)

### #6 SCAFFOLDING STRIP — deferred, inventoried
Reasons: the CMDTRACE/IMM2D probes are what solved #73 today and `r_globalFogDebug` is in active use
for the open fog item; the heavy SKEL* probes in `tr_shade.c` (occlusion queries + `glReadPixels`)
are already gated behind `r_skeldiag` default 0 so they cost nothing at runtime — the strip is log
hygiene, not perf; and ~90 interleaved sites is not a safe tail-of-session edit.
One thing DOES leak today: `tr_model.cpp`'s SKELREG/SKELDIAG/SKELDRAW fire once per model handle
with **no cvar gate** and spam every log.
Inventory: `tr_shade.c` (SKELCLR/SKELPIX/SKELVIEW/SKELPROG/SKELNDC/SKELCOL/SKELROW/SKELZ/SKELFLOOD/
SKELTEST — 36 hits) · `tr_model.cpp` (SKELREG/SKELDIAG/SKELDRAW/SKELAGG/SKELVERTS/SKELTRACK — 53) ·
`tr_scene.c` (4) · `tr_draw.c` + `tr_font.cpp` + `tr_backend.c` (CMDTRACE/IMM2D) · plus
`r_globalFogDebug` back to CVAR_CHEAT and `seta r_cmdtrace` out of the user's sandbox omconfig.

## HARNESSES (scratchpad/gl2test/)
- `gun73.ps1 -renderer opengl1|opengl2` — game / ESC board / armory / main menu on either renderer.
- `confirm73.ps1` — weapons bar (`ui_weaponsbar 2` pins it) + in-game main menu + disconnect menu.
- `vidrestart.ps1` — MSAA change + vid_restart ×3 with respawn and captures; reports new crash dumps.
- `loadouttest.ps1` — seeds `coop_lo1..4` + `coop_lockLoadout`, any map, captures first spawn /
  post-resend / post-death-respawn and greps the Armory lines. `-p1 "" -lock -1` = seed nothing.
- `fogdbg.ps1` — normal + fog-fraction + fog-distance captures, logs the latched GLOBALFOG params.
- `dumpan.py` / `stackscan.py` (in scratchpad/) — minidump exception + linker-.map symbol, and a
  naive stack scan for the call chain. WER dumps here use MemoryListStream (type 5), not Memory64.
  **The .map must match the binary loaded at crash time** — a rebuild invalidates it.

## RULES / GOTCHAS
- gl2 NEVER ships. Engine deploys to `G:\mohaa-gl2` only.
- Never boot a test instance while the user's game is running or a fullscreen session is closing.
- `r_tonemapMode` / `r_globalFogPreTone` / `r_uiFrameClear` are CVAR_ARCHIVE — the test homepath
  retains them silently. Force them in the boot cfg AND on the command line.
- **The ESC menu cannot be opened with `keybd_event`** (SDL ignores synthetic keys) — use
  `rcon pushmenu dm_main` / `rcon popmenu 0`. `dm_main` IS the ESC board.
- **Every scratchpad `rcon.py` needs the connectionless DIRECTION byte** (`b"\xff\xff\xff\xff\x02"`,
  bug-1143). Without it the server logs `bad connectionless packet` and silently runs nothing — the
  harness looks successful and every capture is wrong.
- Coop join needs ~3 clicks and a ~20s settle before the 1P view model appears; capture earlier and
  you get the 3P spawn pose with no HUD.
- Webhook URLs secret. Never say "Boom Library".

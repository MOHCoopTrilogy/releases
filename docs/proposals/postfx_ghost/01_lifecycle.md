# AUDIT 1 — gl1 post-FX: lifecycle and reset

Scope: `openmohaa-hzm/code/renderergl1/tr_postprocess_gl1.c` (1221 lines) + its hooks
(`tr_backend.c`, `tr_draw.c`, `tr_init.c`) + the cgame cvar publishers (`cg_view.c`,
`cg_drawtools.cpp`, `cg_main.c`) + the live cfg seeds. READ-ONLY audit; every claim cites file:line.
Bug under investigation: at random mission starts the frame is muddy/washed-out, world textures look
low-quality, and a texture appears ghosted over the screen that moves with the camera; sometimes
clears on the next mission.

Companion legacy pass audited too: `RB_DepthOfField` (tr_backend.c:1475) — a pre-GLSL screen-capture
DoF that is NOT part of the r_pp chain but runs at every buffer swap and composites capture copies.

---

## A. Where the pass actually runs (hook topology)

| Hook | Site | Gate |
|---|---|---|
| Inline (primary) | `RB_DrawSurfs` tr_backend.c:1299-1303, immediately after the world surface list, before `R_DrawGrass` | `!isPortal && !isPortalSky && !(rdflags & RDF_NOWORLDMODEL)`; does **not** check `s_postfx_applied` before applying (sets it at :1301) |
| 3D→2D fallback | `Set2DWindow` tr_draw.c:445-447 → `RB_PostFxMaybeApply` tr_backend.c:1032-1038 | `!backEnd.in2D`, `!s_postfx_applied`, `s_postfx_scene3D`. **No main-view gate** — see F7 |
| Swap fallback | `RB_SwapBuffers` tr_backend.c:1570 | same flags |
| Legacy DoF-vignette | `RB_SwapBuffers` tr_backend.c:1573 → `RB_DepthOfField` :1475 | **only** `r_dofBlur > 0` (:1483). No `sv_running`, no `R_PostFxActive`, runs on menus/loading screens too |

`s_postfx_scene3D` is set at tr_backend.c:1286 for **every** `RB_DrawSurfs` command, including
portal, portal-sky and `RDF_NOWORLDMODEL` views. Both flags reset once per frame in `RB_SwapBuffers`
(tr_backend.c:1612-1613). `R_PostFxActive` (tr_postprocess_gl1.c:721-729) gates the r_pp chain on
`sv_running` + `s.inited` + `r_postProcess`.

## B. Persistent renderer-side state — allocation / reset reachability

The entire module state is one zero-initialized file static: `static postFxGl1_t s`
(tr_postprocess_gl1.c:118, struct :76-116). It holds the scene FBO + color/depth textures, the two
half-res bloom scratch FBOs/textures, 16 GLSL programs, the per-effect `*Ok` flags and `width/height`.

| State | Allocated | Reset | (a) vid_restart | (b) map change, no vid_restart | (c) first frame of first map |
|---|---|---|---|---|---|
| `s` (all GL objects + flags) | `R_InitPostFxGL1` :594-692, called ONLY from `R_Init` (tr_init.c:1839) | `R_ShutdownPostFxGL1` :694-719 (memset :718), called from `RE_Shutdown` (tr_init.c:1866) and defensively at init (:596) | YES — RE_Shutdown → R_Init rebuilds everything | **NO — `RE_BeginRegistration` (tr_init.c:1897-1931) never touches post-FX.** GL objects and their **contents** persist across missions | Objects exist from engine boot; texture contents are garbage (allocated with `data=NULL` at :564, :615, :623) until first written |
| `s_postfx_scene3D` / `s_postfx_applied` | file statics tr_backend.c:1029-1030 | per frame, RB_SwapBuffers :1612-1613 | zero-init on DLL reload | n/a (per-frame) | qfalse — correct |
| `RB_DepthOfField` `dofTex`, `potW`, `potH` | function statics tr_backend.c:1476-1477, lazily created :1495-1509 | **NEVER.** Not freed in RE_Shutdown, not resized except when the POT size changes (:1501) | **NOT RESET — defect F5** | persists (texture name only; content recaptured at :1512 each use) | 0 — allocated on first use |
| Cvar-pointer caches | `R_PostFxActive::svRunning` :725-726; `RB_PostFxApply::pBeat` :775, `pMuz*` :815-819, `pRain*` :836-839 | never (engine cvars are never freed → pointers stay valid) | pointers re-fetched after renderer DLL reload | safe | safe |

**There is no renderer-side accumulation/lerp/history state in the gl1 chain.** Every per-frame
intensity (`hurt`, `suppress`, `heat`, `muzHeat`, `rainWet`, `sunU/V`) is a local recomputed from
cvars each call (tr_postprocess_gl1.c:739-744, 747-864). **Refutation:** the "MotionBlur history
buffer" from the task brief does not exist in gl1 — motion blur / Frost / Hit / Dizzy / Underwater /
FilmGrain / ChromaticAberration / Temp are gl2-only (`renderergl2/tr_postprocess.c`, bugs 1158/1233/1239).
The corresponding `r_ppDizzy*`, `r_ppFrost`, `r_ppFilmGrain*`, `r_ppTemp`, `r_ppUnderwaterFx`,
`r_ppChromaticAberration*` seeds in coop_defaults.cfg:137-163 are inert on gl1.

**Refutation #2:** `r_ppPassthrough` ("master bypass") is registered (tr_init.c:1455, seeded
coop_defaults.cfg:155) but **never read anywhere** — grep hits only its declaration/registration.
The only master switch is `r_postProcess` (tr_postprocess_gl1.c:728).

## C. Capture textures — write-before-read audit

Happy path is sound: every texture sampled by a pass is written earlier in the same frame.

- Base copy backbuffer→`sceneColor` :867-871; depth copy :873-877 (only when `doSSAO||doDoF`).
- Per-pass re-copies before sampling: tonemap :1091-1093, FXAA :1110-1112, sharpen :1128-1130,
  heat :1148-1150, rain :1169-1171, low-health :1188-1190, suppression :1204-1206.
- Scratch (`bloomTex[0/1]`) is rendered into before being composited: SSAO :899-927 → :929-936,
  DoF :948-969 → :971-990, bloom :1004-1024 → :1026-1033, god rays :1043-1061 → :1063-1071.

So stale content across map change is harmless **as long as every scratch render actually lands** —
which is exactly what F2 breaks.

## D. Cvar channels — publisher, reset-at-map-start, cvar class

Registration: tr_init.c:1454-1491 (chain) + in-function registrations tr_postprocess_gl1.c:775,
815-819, 836-839. Per-frame "signal" channels are supposed to be flags 0 (non-archived).

| Channel | Publisher | Published when | Cleared at CG_Init (cg_main.c:817-830)? | Cvar class | Stuck-risk |
|---|---|---|---|---|---|
| `r_ppHealthFrac` | cg_view.c:1936 (CG_CalcFov) | every rendered frame with a snapshot | yes → "1" (:829) | flags 0 (tr_init.c:1477) | none — self-heals before the first world frame is rendered (CalcFov runs in CG_DrawActiveFrame before the scene is submitted) |
| `r_ppSuppress` | cg_view.c:2016 | unconditional in CalcFov | yes (:819) | flags 0 (:1481) | none |
| `r_ppHit` (gl2-only consumer) | cg_view.c:2031 | unconditional | yes (:819) | flags 0 | none |
| `r_ppHeat` | cg_view.c:2051 | unconditional | yes (:819) | flags 0 (:1484) | none |
| `r_ppMuzzleHeat` | cg_view.c:2058 | unconditional | **NO** | **CVAR_ARCHIVE — tr_postprocess_gl1.c:816 (WRONG CLASS)** | crash/quit mid-firefight persists a nonzero shimmer to omconfig.cfg; self-heals on the first CalcFov frame of the next session, so in-mission exposure is ~1 frame — but the archive write-back is a standing bug-1202-class hazard (F3) |
| `r_ppRainWet` | cg_view.c:2095 | unconditional | yes (:819) | flags 0 (:838) | none |
| `r_ppUnderwater` (gl2-only consumer) | cg_view.c:2143 | unconditional | **NO** | flags 0 | self-heals; inert on gl1 |
| **`r_dofBlur`** | **cg_drawtools.cpp:1848 ONLY** (CG_DrawAdsVignette, from CG_Draw2D :2278) | only when the 2D path runs AND the vignette shader registered — early return at cg_drawtools.cpp:1812-1814 **above the publish** | **NO — absent from the clear list** | **CVAR_ARCHIVE — tr_init.c:1490 (WRONG CLASS)** | **the one channel in the game that can silently stick nonzero for a whole mission — F1** |

The CG_Init clear block (cg_main.c:808-830) exists precisely because "whatever value was live when
the connection dropped stays live forever" (its own comment). It clears r_ppHeat / r_ppSuppress /
r_ppHit / r_ppRainWet / coop_dbnoView / coop_suppHold / coop_suppBump and sets r_ppHealthFrac=1.
**It does not clear `r_dofBlur`, `r_ppMuzzleHeat`, `r_ppUnderwater`.**

cgame-side ease state (fAlpha/fBreath cg_drawtools.cpp:1804-1805; s_rainWet cg_view.c:2067;
s_underwater :2129; s_coopSuppress/Hit/Heat/MuzzleHeat file statics ~:439-476; s_peakHealth :1902):
these are function/file statics that persist if the cgame DLL stays resident across map changes, but
each has a defensive clamp (dt clamped at :1955, :2047, :2073, :2135; peak reset on h<=0 at :1922)
and each decays toward a freshly computed target, so no cross-mission latch was found there.

## E. Findings (ranked)

### F1 — `r_dofBlur`: archived, per-frame, publisher can silently die, consumer never gated
- Registered `CVAR_ARCHIVE` with the comment "cgame drives on ADS": tr_init.c:1490. A per-frame
  signal value in the archive class — the exact defect class the cg_main.c:808-830 block was built
  to kill (it de-archived `coop_dbnoView` for this reason), and `r_dofBlur` is missing from that list.
- Publisher: cg_drawtools.cpp:1848, inside `CG_DrawAdsVignette`, which **early-returns at
  :1812-1814 before the publish** if `R_RegisterShaderNoMip("textures/hud/coop_ads_vignette")`
  returned 0. CG_Draw2D itself is engine-gated (cl_uiview3d.cpp:499-504: skipped under
  `cls.no_menus` — screenshots, cl_main.cpp:5057 — or debug/timegraph).
- Consumer: `RB_DepthOfField` tr_backend.c:1475-1558 runs at **every** swap with zero gating beyond
  `r_dofBlur > 0` (:1483) — menus, loading screens, every mission frame. It captures the frame
  (:1512) and composites **5 offset copies** of it through a radial alpha (:1540-1553) — i.e. a
  screen-anchored multi-image ghost that moves with the camera, plus edge blur (muddy).
- Latch scenario: the mod's mission transition is an instant `stuffsrv "map"` (no intermission). A
  player aiming at the transition instant leaves `r_dofBlur` at up to `(1+0.4)*cg_dofStrength`
  (~0.84). Nothing clears it during load; if the next mission's publisher is dead (hVig=0 that map,
  or any future gate on CG_Draw2D), the ghost persists the whole mission and "clears on the next
  mission" when the publisher runs again. A crash writes the value to omconfig.cfg (ARCHIVE) and it
  survives the relaunch.
- Reachability of hVig==0 in the field is the open question (openmohaa's R_RegisterShaderNoMip
  usually returns a nonzero default-shader handle on a missing image); flagging for AUDIT 2 to
  verify the actual failure modes (MAX_SHADERS exhaustion on heavy maps, name-length, pk3 mismatch).
  Note the failure is completely silent.

### F2 — `ssaoOk/dofOk/godRaysOk` ignore FBO completeness → composites of never-written scratch
- `R_PostFx_MakeColorFbo` returns completeness (:560-575), but only `bloomOk` consumes it
  (`f0 && f1` folded in at :652). `ssaoOk` (:660-661), `dofOk` (:667-668) and `godRaysOk` (:687-688)
  test only the **nonzero object IDs** `s.bloomFbo[0] && s.bloomFbo[1]` — which are nonzero even
  when the FBO is INCOMPLETE.
- If either bloom FBO is incomplete: all SSAO/DoF/god-ray scratch renders are silently dropped
  (draws into an incomplete FBO no-op with a GL error), and the composites at :929-936 (multiply,
  `GLS_SRCBLEND_DST_COLOR|GLS_DSTBLEND_ZERO`!), :971-990 (alpha blend) and :1063-1071 (additive)
  sample `bloomTex[*]` whose storage was allocated with `data=NULL` (:564) and **never written** —
  uninitialized VRAM, which on real drivers frequently contains recycled old texture/framebuffer
  images. A multiply-composite of a random old texture over the whole frame = literally "a texture
  ghosted over the screen that moves with the camera" + heavy muddying.
- Lifecycle shape: this latches at `R_Init` (per session / per vid_restart), not per map — a session
  that boots with an incomplete FBO stays broken until vid_restart. The boot log discriminates it
  instantly: `postfx: scene FBO ... COMPLETE/FAILED` and `postfx: bloom ... ready/DISABLED`
  (:638-641, :653) — a log showing `bloom DISABLED` together with `ssao ready` (:662) is this
  defect live. The user's config has SSAO, DoF and SunShafts all ON (coop_defaults.cfg:40,49,56).

### F3 — `r_ppMuzzleHeat` registered CVAR_ARCHIVE inside the render loop
- tr_postprocess_gl1.c:816: `pMuzH = ri.Cvar_Get("r_ppMuzzleHeat", "0", CVAR_ARCHIVE)` — a
  per-frame decaying signal in the archive class (contrast r_ppHeat: flags 0, tr_init.c:1484).
  A crash mid-firefight persists a nonzero heat shimmer; it self-heals one CalcFov frame into the
  next session, but the archived value also leaks into every config snapshot (coop_defaults.cfg:151
  carries `seta r_ppMuzzleHeat 0` — evidence it is being archived). Should be flags 0 + added to
  the cg_main.c clear list.

### F4 — CG_Init clear-list omissions
- cg_main.c:818-819 list: add `r_dofBlur` (critical — no self-heal path), `r_ppMuzzleHeat`,
  `r_ppUnderwater` (cheap completeness). This is the mod's own bug-1202 pattern applied to the
  channels added after that fix.

### F5 — `RB_DepthOfField` statics survive vid_restart with a destroyed context
- `dofTex/potW/potH` (tr_backend.c:1476-1477) are never reset; `RE_Shutdown` frees the r_pp
  resources (tr_init.c:1866) but not this texture. After a context-destroying vid_restart at the
  SAME resolution: the old name is stale, `nw==potW && nh==potH` skips `qglTexImage2D` (:1501), so
  the re-created texture object has no storage; the capture (:1512) errors and the composite draws
  an incomplete texture (fixed-function samples as white/disabled) — a washed-out wash at the
  screen edges whenever `r_dofBlur > 0`. Reachable: Advanced-Graphics apply (vid_restart) then ADS.

### F6 — init-time GL_Bind cache desync (one-frame window)
- `R_InitPostFxGL1` and `R_PostFx_MakeColorFbo` raw-bind textures (:563, :614, :622) without
  updating `glState.currenttextures`, so after `R_Init` the cached texnum lies about the actual
  binding until the first real `GL_Bind`. Worst case is one surface drawn with a post-FX scratch
  texture on the first frame after boot/vid_restart. Momentary; not the reported bug; cheap to fix
  (end init with `GL_Bind(tr.whiteImage)` like :1219 does).
- Inside `RB_PostFxApply` the same raw-bind pattern is used for scratch textures (:909, :921, :926,
  :935, :963, :968, :1010, :1018, :1023, :1032, :1049, :1060, :1070), but the audit traced every
  path: each copy-block re-syncs `currenttextures[0]` (:870, :875, :1092, :1111, :1129, :1149,
  :1170, :1189, :1205), DoF restores unit 1 (:993-996), and the terminal `GL_Bind(tr.whiteImage)`
  (:1219) always performs a real bind because the cache can only hold a scratch-texture id at that
  point (never white's). **The "glState desync corrupts world textures" reading is REFUTED for the
  current pass ordering** — consistent at exit, fragile to reordering. Keep the invariant in mind
  for any edit.

### F7 — structural once-per-frame hazards (unknown reachability, document + guard)
- The inline apply (tr_backend.c:1299-1303) does not check `s_postfx_applied` — a frame containing
  two qualifying world views would double-apply grade/sharpen/SSAO (double ACES + double sharpen at
  the user's 0.78 = exactly "muddy, washed-out, crunchy textures"). No such frame shape was found in
  the current client, but nothing prevents one.
- The fallbacks (tr_draw.c:445, tr_backend.c:1570) have no main-view gate while
  `s_postfx_scene3D` is set by ANY drawSurfs including portal/`RDF_NOWORLDMODEL` views
  (tr_backend.c:1286) — a frame whose only 3D content is a UI 3D inset (sv_running=1) gets
  post-processed with that view's `viewParms` (SSAO with a garbage zFar). Transient frames only.

### F8 — CONFIG-LEVEL prime suspect for "muddy at random mission starts": fixed-focus DoF is live
Not a lifecycle defect but found during the audit and it matches the symptom too well to omit:
- The live seed file ships **`seta r_ppDoF 1` with `seta r_ppDoFFocus 744.985718` and
  `r_ppDoFRange 2256.7`, intensity 0.55** (coop_defaults.cfg:40-43). The intended default is
  focus **0 = auto-focus on center-screen depth** (tr_init.c:1465, coop_fxdefaults.cfg:22); the
  six-decimal value is a leaked live-tune write-back.
- Effect (tr_postprocess_gl1.c:261-277, :941-997): everything outside the fixed ~745±2257-unit band
  gets the half-res 9-tap-blurred scene composited over it at up to 0.55 alpha. On close-quarters
  maps almost nothing leaves the band → looks fine; on open maps (Crete e2l1, beach approaches)
  most of the scene is outside it → a translucent smeared duplicate of the world overlaid on the
  sharp render (half-res + bilinear upsample = visibly offset "ghost" of the scene, camera-locked),
  textures read as low-quality, whole frame muddy. Map-dependent presentation reads to a player as
  "random mission starts, sometimes fine next mission", with no trigger.
- Also note the live grade: `r_ppTonemap 1` + `r_ppExposure 0.70` + saturation 1.08
  (coop_defaults.cfg:59,44,54) — a deliberately darker/flatter baseline that compounds the "washed
  out" read whenever anything else goes wrong.

## F. Symptom readings — verify/refute

| Reading | Verdict |
|---|---|
| (1) ghost = pass compositing stale/uninitialized capture | CONFIRMED as a real mechanism in two places: F2 (never-written bloomTex composited when FBO incomplete — uninit VRAM can be an actual old texture) and F1 (RB_DepthOfField 5-tap self-ghost when r_dofBlur sticks). F8 produces the same visual via a *live* half-res copy. |
| (2) muddy = grade double-applied OR glState desync corrupting world textures | Double-grade: no reachable double-apply found (F7 documents the missing guard); grade itself is live for this user (tonemap 1, exposure 0.7). glState desync: REFUTED for the current code path (F6) — the pass exits cache-consistent. The muddiness is better explained by F8/F2/F1. |
| (3) intermittent-per-map-start = lifecycle/reset | Split verdict. The r_pp signal channels genuinely cannot stick (published unconditionally from CG_CalcFov before any world frame renders — section D). The stickable state is: `r_dofBlur` (F1, archived + gated publisher), FBO-completeness latched per session (F2), and the map-dependent presentation of fixed-focus DoF (F8). Renderer scratch contents surviving map change are benign on the happy path (section C). |

## G. Live-repro discriminator (run these the moment it looks bad)

In console (or rcon) while the ghost is on screen:
```
r_dofBlur; r_ppDoF; r_ppDoFFocus; r_ppDoFIntensity; r_ppMuzzleHeat; r_ppSuppress; r_ppHeat; r_ppRainWet; r_ppTonemap; r_ppExposure
```
- `r_dofBlur` nonzero while NOT aiming → F1 confirmed.
- Toggle `r_ppDoF 0`: ghost/mud gone → F8 (or DoF leg of F2). Toggle `r_ppSSAO 0`: mud gone → SSAO leg of F2.
- `r_postProcess 0` kills the whole r_pp chain but NOT RB_DepthOfField — a ghost surviving
  `r_postProcess 0` is F1 by elimination.
- Boot log check (`%APPDATA%\openmohaa\maintt\qconsole.log`): the `postfx:` init block
  (tr_postprocess_gl1.c:638-691). `bloom ... DISABLED` while `ssao ready` = F2 live.

## H. Handoff to the next audits

- AUDIT 2 (ordering/first-frame): verify hVig failure modes for F1; hunt real frame shapes for F7
  (UI 3D insets while sv_running=1, double world views).
- Fix-pass candidates (smallest first): de-archive `r_dofBlur` + `r_ppMuzzleHeat` (flags 0); add
  both + `r_ppUnderwater` to the cg_main.c clear list; fold `f0/f1` into `ssaoOk/dofOk/godRaysOk`
  (or gate the composites on `bloomOk`); publish `r_dofBlur` from CG_CalcFov (unconditional, like
  every other channel) instead of behind the vignette early-return; reset `r_ppDoFFocus` seed to 0
  (auto) in coop_defaults.cfg; delete/re-create `dofTex` on RE_Shutdown.

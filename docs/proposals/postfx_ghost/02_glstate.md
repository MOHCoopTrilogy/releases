# Audit 2 — GL state discipline in the gl1 post-FX layer

Scope: every raw GL call in `code/renderergl1/tr_postprocess_gl1.c` that mutates state the engine
caches, plus the hook sites in `tr_backend.c` / `tr_draw.c` / `tr_init.c` and the code that runs
immediately after the hook. READ-ONLY audit; all paths relative to `C:\mohaa-coop-dev\openmohaa-hzm\`.

## 0. The engine's cached-state contract (what a desync can break)

`glstate_t` (tr_local.h:1283-1294) caches: `currenttextures[2]`, `currenttmu`, `texEnv[2]`,
`faceCulling`, `cntTexEnvExt`, `glStateBits` / `externalSetState`, `fFogColor`.

- `GL_Bind` (tr_backend.c:52-74) **skips the real `glBindTexture` when
  `currenttextures[currenttmu] == texnum`**. A stale cache entry that happens to equal the next
  requested texnum makes the engine render with whatever is *actually* bound.
- `GL_SelectTexture` (tr_backend.c:79-104) early-outs on `currenttmu == unit`, and when it does
  switch it sets **both** `qglActiveTextureARB` *and* `qglClientActiveTextureARB` (:88-98). The
  invariant is: server active unit == client active unit == `currenttmu`. Client active unit decides
  which unit `qglTexCoordPointer` feeds (tr_shade.c:404, 468, 1828, 1846) — desync it and the world
  renders with stale texcoords.
- `GL_State` (tr_backend.c:221-555) diffs `glStateBits ^ (externalSetState | stateBits)` and, on a
  `GLS_CLAMP_EDGE` diff, **mutates the wrap parameters of whatever textures are currently bound on
  units 0 AND 1** (tr_backend.c:448-491: `qglTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S/T, ...)`
  on unit 0 then unit 1). This is MOHAA's per-stage clamp implementation: `GL_State` is only safe to
  call when the textures bound are the ones the clamp transition is *meant* for.
- NOT cached (raw is legal, but the exit state must match what the next consumer expects): viewport,
  matrices, FBO binding, GLSL program, client array enables, draw/read buffer.

Not in the namespace-collision class: engine images get their texnum from `qglGenTextures`
(tr_image.c:885-889, an explicit OPM fix replacing MOHAA's fixed `1024 + i`), and the post-FX layer
also uses `qglGenTextures` (tr_postprocess_gl1.c:562, 613, 621). GL guarantees live gen'd names are
unique, so a post-FX texture id can never equal a live engine `image->texnum`. Several verdicts
below are sound **only because of this** — flagged where load-bearing.

## 1. Hook sites and what runs after the post-pass

- Primary hook: `RB_DrawSurfs`, **mid-frame**, right after the world surface list and *before*
  `R_DrawGrass`, the sprite pass and the 2D HUD (tr_backend.c:1291-1305). Anything the post-pass
  leaves desynced is inherited by grass (tr_grass_gl1.c:256), `RB_SpriteSurfs`
  (tr_backend.c:1317-1334) and the HUD.
- Secondary hook: `Set2DWindow` (tr_draw.c:445-447) — safe seam: lines 449-467 re-establish
  viewport/scissor/matrices/`GL_State`/blend immediately after, so leaks die there.
- Fallback hook: `RB_SwapBuffers` (tr_backend.c:1570), followed immediately by the *other*
  screen-capture effect, `RB_DepthOfField` (tr_backend.c:1573). Per-frame gates reset at
  tr_backend.c:1612-1613.
- Init/shutdown: `R_InitPostFxGL1` is the **last** call in `R_Init` (tr_init.c:1839), after
  `InitOpenGL`/`R_InitImages`/`R_LoadFont` (tr_init.c:1820-1832); `R_ShutdownPostFxGL1` runs in
  `RE_Shutdown` while the context is valid (tr_init.c:1866). `R_Init` runs from `GetRefAPI`
  (tr_init.c:1991) — once per renderer-DLL load, NOT per map (`RE_BeginRegistration`,
  tr_init.c:1897-1931, does not call it).

## 2. Findings, ranked

### F1 — `GL_State` clamp-edge side-channel fires with foreign textures bound
**tr_postprocess_gl1.c:882 (first `GL_State` of the frame’s post-pass). Conditional per frame —
the intermittent one.**

At line 882 the bound state is: unit 0 = `s.sceneColor` (bound raw at :869) or `s.sceneDepth`
(:874, when SSAO/DoF are on); unit 1 = whatever the last multitextured world stage left there
(typically a lightmap, tr_shade.c:444-474). If the **last world surface drawn** carried
`GLS_CLAMP_EDGE` in its stateBits, the diff at tr_backend.c:448 fires and stamps
`GL_TEXTURE_WRAP_S/T = GL_REPEAT` onto **both** of those textures (tr_backend.c:471-484).

Consequences:
- `s.sceneColor` / `s.sceneDepth` lose the `GL_CLAMP_TO_EDGE` they were given once at init
  (tr_postprocess_gl1.c:618-619, 626-627) and **nothing ever restores it** — the flip is sticky
  until the next `R_InitPostFxGL1` (= vid_restart). Every effect that samples off the [0,1] square
  then wraps to the opposite screen edge: heat-haze warp up to ~3-4.5% UV
  (tr_postprocess_gl1.c:420-434), rain refraction (:490-491), suppression edge blur (:394-399),
  FXAA/sharpen/blur 1-4px taps at the borders. Visible as smears/ghost-fringes at screen edges,
  worst while heat or rain effects are live.
- The engine texture on unit 1 also gets flipped, but the engine flips bound-texture wrap itself as
  its normal clamp idiom, and lightmap UVs live inside the atlas — negligible.
- Trigger is **draw-order + material dependent** (does the last surface of the world list use a
  clamped stage?), i.e. per-map/per-view random — the only per-frame conditional in this file.

Fix shape: before the first `GL_State`, force the clamp bit to a known value while *our* textures
are bound (e.g. call `GL_State(GLS_DEPTHTEST_DISABLE)` once **before** binding sceneColor, while the
engine's own textures are still bound), or re-assert wrap params on sceneColor/sceneDepth after any
`GL_State` sequence, or strip `GLS_CLAMP_EDGE` handling from the post-pass path by masking
`glState.glStateBits` first.

### F2 — Half-repair of the texture-unit selector breaks the GL_SelectTexture invariant
**tr_postprocess_gl1.c:867-868. Every frame the post-pass runs; damage is latent.**

```c
qglActiveTextureARB( GL_TEXTURE0_ARB );
glState.currenttmu = 0;
```
sets the **server** active unit and the cache, but not `qglClientActiveTextureARB` — the one thing
`GL_SelectTexture` guarantees to keep in lockstep (tr_backend.c:88-98). If this is ever entered with
`currenttmu == 1`, the result is: cache says 0, server unit 0, **client unit still 1**. Every later
`GL_SelectTexture(0)` early-outs on the lying cache, so `qglTexCoordPointer` calls
(tr_shade.c:404, 1828) feed unit 1 while unit 0 keeps stale texcoords — the world renders with wrong
texture coordinates ("textures look really bad") until the first multitextured surface runs a real
`GL_SelectTexture(1)`→`(0)` pair (tr_shade.c:444/484) and resyncs both sides.

Reachability today: I could not find a mainline path that exits at unit 1 — both multitexture
iterators end with `GL_SelectTexture(0)` (tr_shade.c:484, 1864), image upload restores unit 0
(tr_image.c:955-957), and `GL_State`'s clamp path restores the saved tmu (tr_backend.c:473-483). So
this is **latent**: it only bites combined with some other desync (which is exactly why the raw
"force repair" was written). Note the irony: the half-repair is *worse* than trusting the wrapper —
with `GL_SelectTexture(0)` a genuine mismatch fixes both sides; with the half-repair the poisoned
cache *blocks* the wrapper's future self-heal.

Fix shape: add `qglClientActiveTextureARB(GL_TEXTURE0_ARB);` next to :867, keeping the raw
belt-and-braces character.

### F3 — Init leaves the bind cache stale (one bad batch per renderer load / vid_restart)
**tr_postprocess_gl1.c:613-654 (+ helper :562-575). Once per DLL load.**

`R_InitPostFxGL1` raw-binds sceneColor, sceneDepth, bloomTex[0], bloomTex[1] with **no
`glState.currenttextures` update and no restore**. It is the last thing in `R_Init`
(tr_init.c:1839), right after `R_LoadFont` (tr_init.c:1832), so after init: actual unit-0 binding =
`s.bloomTex[1]` (last `R_PostFx_MakeColorFbo`, :648), cache = the last font/image texnum. The first
`GL_Bind` of that same image silently skips (tr_backend.c:67) and one draw batch samples an
**uninitialized RGBA texture** until any other bind lands. One-shot cosmetic at boot/vid_restart;
never per-mission (R_Init is not per-map, tr_init.c:1897-1931).

Fix shape: end init with the engine's own idiom `glState.currenttextures[0] = -1;`
(cf. tr_image.c:954) or `GL_Bind(tr.whiteImage)`.

### F4 — 18 internal raw binds with no cache update: exit-repaired, but the repair is load-bearing
**tr_postprocess_gl1.c:885, 909, 921, 926, 935, 954, 963, 968, 1010, 1018, 1023, 1032, 1049, 1060,
1070, 1104, 1121, 1141, 1162, 1181, 1198, 1214. Every frame / per-effect. VERDICT: currently safe.**

Between the entry copy and the exit line no engine code runs (single-threaded backend, no `GL_Bind`
callers in between), and the function ends with `qglUseProgram(0); GL_Bind(tr.whiteImage)`
(:1218-1219), which re-syncs actual and cache **provided the stale cache value cannot equal
`tr.whiteImage->texnum`**. That holds solely because of the shared `glGenTextures` namespace
(tr_image.c:889). Two load-bearing notes:
- **Do not revert tr_image.c:885-889 to MOHAA's fixed `1024 + i` texnums** — with hardcoded engine
  texnums the driver may gen a post-FX name that collides with an engine image, and then the :1219
  repair (and `R_DrawGrass`'s `GL_Bind(tr.whiteImage)` at tr_grass_gl1.c:294) can silently skip →
  whole-world wrong textures. If that line ever changes, this file's exit discipline breaks with it.
- The mid-function windows (e.g. :885 binds sceneColor while cache still says sceneDepth from :875)
  are harmless only by the "no engine code in between" property. Any future `ri.Printf`-triggered
  console render, error path, or early `return` inserted after :871 would ship a desynced cache.
  There are no early returns after GL work begins today (verified :745 is the only return).

DoF's unit-1 usage is properly bracketed and cache-correct (:972-977, :993-996) — the only fully
disciplined multi-unit sequence in the file.

### F5 — Viewport not restored to the view's viewport at the mid-frame hook
**tr_postprocess_gl1.c:881, 931, 980, 1027, 1065, 1096, 1115, 1133, 1153, 1174, 1193, 1209. Every
frame. LOW.**

Every composite ends with `qglViewport(0, 0, glConfig.vidWidth, glConfig.vidHeight)` — full window —
and `backEnd.viewParms.viewport*` is never re-applied. At the `RB_DrawSurfs` hook the frame is still
mid-3D: `R_DrawGrass` (tr_backend.c:1305) and the subsequent sprite pass inherit the full-window
viewport. Benign in normal play (3D viewport == full window); wrong for any letterboxed or
sub-rect view. Also note viewport is *not* part of `glState`, so no cache lie — just a contract gap.

### F6 — Backbuffer copy ordering assumes FB0 is already bound
**tr_postprocess_gl1.c:869-877. Every frame. LOW / fragility note.**

The scene capture (`qglCopyTexSubImage2D`, :871/:876) executes **before** the explicit
`qglBindFramebuffer(GL_FRAMEBUFFER, 0)` at :880. Correct today because every internal path re-binds
FB0 before returning (:930, :979, :1026, :1064, :1095, :1114, :1132, :1152, :1173, :1192, :1208) and
no other gl1 code binds FBOs mid-frame — but the correctness is inherited, not local. Moving the
:880 bind above :869 makes it unconditional.

### F7 — Adjacent at the hook seam: `R_DrawGrass` desyncs the cull cache right after the post-pass
**tr_grass_gl1.c:293, 331. Every frame grass is on. Not a post-FX defect, but the hook placed it
directly downstream.**

Grass raw-toggles `qglDisable/qglEnable(GL_CULL_FACE)` without touching `glState.faceCulling`
(`GL_Cull`, tr_backend.c:138-176). If the last world shader was `CT_TWO_SIDED` (cache says culling
off) the :331 raw enable leaves culling **actually on**; the sprite pass's next
`GL_Cull(CT_TWO_SIDED)` early-outs on the stale cache → intermittently one-sided/missing
sprites/effects, dependent on the last material drawn. Same class of conditional intermittency as
F1. Otherwise grass is disciplined (GL_State :292, GL_Bind :294 — the latter depending on F4's
namespace note).

### F8 — The sibling capture effect `RB_DepthOfField`: state-clean; statics only survive because of the DLL build
**tr_backend.c:1475-1558. Only when `r_dofBlur > 0` (cgame sets it during ADS,
cg_drawtools.cpp:1848).**

Bind discipline is correct (raw binds immediately mirrored into the cache, :1499-1500, :1537-1538;
exit `GL_Bind(tr.whiteImage)` :1557; capture-then-draw is same-frame so it cannot composite stale
content). The `static GLuint dofTex` + `static potW/potH` (:1476-1477) would be a textbook
stale-name / skipped-`TexImage2D` hazard across vid_restart — the exact bug-1148 class — **but this
build runs the renderer as a reloadable DLL** (`USE_RENDERER_DLOPEN:BOOL=ON` in
`.cmake/CMakeCache.txt`; loader cl_main.cpp:3230-3255; `renderer_opengl1.dll` ships in the GOG
root), so vid_restart resets all renderer statics. Residual: `dofTex` is never deleted
(`RE_Shutdown` doesn't know it) → one leaked GL name per vid_restart. If the project ever flips
`USE_RENDERER_DLOPEN` OFF (bug-108's note already describes a statically-linked-renderer era),
`dofTex`/`potW`/`potH` become live stale-context handles: skipped realloc + per-frame
`CopyTexSubImage` into a recycled name — a genuine "random texture ghosted over the screen"
generator. Guard it with a context-generation check before any such build change.

## 3. Verdict against the reported symptoms

The file's own header claim ("All state goes through the engine's cached helpers … so glState stays
consistent", tr_postprocess_gl1.c:5-6) is not literally true — 18 raw binds, a half TMU repair, and
an unrestored init bind — but the **exit** state at both hook seams is consistent today, resting on
two non-local invariants (gen'd-name uniqueness, no-engine-code-mid-function).

- Symptom match "textures all look really bad": F2 is the only in-scope mechanism that produces
  exactly this, and it is latent (needs entry `currenttmu==1`, unreachable in-tree today).
- Symptom match "ghosted texture that moves with the camera": no in-scope violation composites stale
  content per-frame. F1 produces sticky **edge** ghost-smears (wrap-around sampling) gated on a
  material-order coincidence — intermittent onset, but it does NOT self-clear on the next mission
  (persists to vid_restart), which fails the "sometimes clears" observation.
- Symptom "random mission starts, sometimes clears next mission": nothing in this audit is keyed to
  map load — `R_InitPostFxGL1` is per-DLL-load, and the per-frame paths have no per-map state. The
  map-load-keyed candidates live in the **lifecycle/content** axis (stale `s.sceneDepth` sampled by
  SSAO/DoF on frames whose 3D view didn't run, `sv_running`-gated loading-screen frames via the
  Set2DWindow hook, and the composite-math ordering) — audits 1/3.

Recommended hardening order (cheap, all local): F2 one-liner (add the client-active call), F3
one-liner (`currenttextures[0] = -1` at init end), F1 (mask or pre-consume `GLS_CLAMP_EDGE` before
binding post-FX textures; optionally re-assert wrap on sceneColor/sceneDepth each init AND after
each frame's first GL_State), F6 (hoist the FB0 bind above the copy), F7 (grass: use `GL_Cull`).

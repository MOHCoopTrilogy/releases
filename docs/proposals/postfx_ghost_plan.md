# PostFX ghost + wash at random mission starts — SYNTHESIS PLAN

Date: 2026-08-09. Synthesized from three read-only audits in `docs/proposals/postfx_ghost/`:
`01_lifecycle.md` (lifecycle/reset), `02_glstate.md` (GL state discipline), `03_composite.md`
(composite math/ordering). All paths in `C:\mohaa-coop-dev\openmohaa-hzm\` unless noted;
cfg paths in `C:\mohaa-coop-dev\hzm-mohaa-coop-mod\`. Spot-verified against source 2026-08-09:
DoF focus<=0 = auto (tr_postprocess_gl1.c:267,273); CG_Init clear list contents
(cg_main.c:818-829); init log wording + `*Ok` completeness gap (tr_postprocess_gl1.c:638-691).

**Symptom triad**: (a) texture ghosted over the screen, moves with the camera; (b) muddy /
washed-out frame; (c) world textures look low-quality. Intermittent at mission start, sometimes
clears on the next mission, no known trigger.

**Two corrections to the task brief, established by all three audits (do not re-litigate):**
- There is **no MotionBlur history buffer in gl1** — motion blur, Frost, Hit, Dizzy, Underwater,
  FilmGrain, ChromAb, Temp are gl2-only (`renderergl2/tr_postprocess.c`). gl1 implements exactly
  eleven passes (03_composite.md §0). Field reports must record `cl_renderer` first — bug-1189
  was the same symptom on gl2 with an unrelated cause.
- **`r_ppPassthrough` is a dead cvar on gl1** (registered tr_init.c:1455, never read). The only
  master bypass is `r_postProcess` (tr_postprocess_gl1.c:728). The bisect must not start with it.

**One symptom reading refuted:** "post-FX desynced glState → world renders with wrong textures"
does NOT hold for the current code — the pass exits cache-consistent at both hook seams
(02_glstate.md F4/§3; the exit repair rests on gen'd-texture-name uniqueness, tr_image.c:885-889,
and on no engine code running mid-function — both hold today, both are fragile to edits).

---

## 1. Ranked suspects

### S1 — Stale/failed `sceneDepth` capture, expressed through SSAO + DoF (prime)
`tr_postprocess_gl1.c:873-877` — one `qglCopyTexSubImage2D` depth readback from the default
framebuffer (the most driver-fragile op in the chain) fills the single texture that BOTH
shipped-ON heavy passes consume: SSAO (`r_ppSSAO 1`, coop_defaults.cfg:49) and DoF
(`r_ppDoF 1`, cfg:40). Failure is silent: no error check, `r_ignoreGLErrors` defaults 1
(tr_init.c:1493), texture NULL-allocated at :621-623 (undefined VRAM until first good copy).

- **Ghost**: SSAO computes AO of the OLD/garbage depth and multiplies it over the current frame
  (:930-936, `DST_COLOR/ZERO`) — soft half-res dark silhouettes of geometry that is not there,
  screen-locked, moving with the camera.
- **Wash/mud**: the same multiply globally darkens; bloom (threshold 0.349, cfg:38) then
  bright-passes and re-adds on top (:1026-1033) = milky wash.
- **Bad textures**: DoF evaluates CoC from the same wrong depth (:271-276, :984-990) and smears
  the half-res blurred scene over large areas at 0.55 alpha (cfg:42).
- **Intermittency**: capture runs only while `sv_running` && a world view exists
  (R_PostFxActive :721-729); the GL objects and contents persist across missions because
  `RE_BeginRegistration` (tr_init.c:1897-1931) never touches post-FX (01_lifecycle.md §B).
  Whether the first mission frame refreshes depth before first use is a per-map-load ordering
  event; the next load can re-succeed → "sometimes clears next mission". The D4 hazard
  (s_postfx_scene3D set by EVERY RB_DrawSurfs incl. RDF_NOWORLDMODEL, tr_backend.c:1286)
  gives the fallback hooks (tr_draw.c:445-447, tr_backend.c:1570) a path to run the chain on
  frames with no main world view, consuming whatever depth that view left.

### S2 — Shipped fixed-focus DoF seed (config defect, certainly live)
`coop_defaults.cfg:40-43` ships `seta r_ppDoFFocus 744.985718` + `r_ppDoFRange 2256.7` +
intensity 0.55 — a leaked live-tune write-back. Intended default is 0 = auto-focus on
center-screen depth (tr_init.c:1465, verified in shader tr_postprocess_gl1.c:267,273).
- **Ghost/bad textures**: on open maps most of the scene sits outside the ~745±2257u band → a
  translucent half-res, bilinearly-upsampled duplicate of the world composited at up to 0.55
  over the sharp render — camera-locked, reads as "ghosted texture" + "low-quality textures".
- **Wash**: compounds the deliberately soft baseline (`r_ppExposure 0.70` + always-ACES means
  peak white ≈ 0.72, cfg:44,59; 03_composite.md §2.3).
- **Intermittency**: purely map-geometry-dependent — close-quarters maps look fine, open maps
  (Crete, beaches) look bad → the player reads "random mission starts, cleared next mission".
- This is not a maybe: the seed is in the shipped file. It may not be the WHOLE bug, but it is
  producing exactly this presentation on open maps today.

### S3 — Stuck cgame envelope cvars: `r_ppRainWet` (ghost-beads) + `r_ppSuppress` (wash)
Publishers run unconditionally in CG_CalcFov (cg_view.c:2016, 2095) — but CG_CalcFov itself is
skipped on snapshot loss, cinematics, menus (cg_main.c comment :810-812). A value spiked just
before such a window freezes: suppression ≥0.5 = 40-80% desaturation + edge darkening every
frame (SUPPRESSION_FS :386-404) = "muddy and washed out"; rainWet >0 = permanent refractive
bead layer (RAINDROPS_FS :443-494) = camera-locked "texture ghosted over the screen".
Pre-bug-1206, the rain test even classified 8 sandstorm maps as rain.
- **Intermittency + self-clear**: matches verbatim — the shipped CG_Init clear
  (cg_main.c:808-830, bugs 1202/1307) zeroes these on every map change, so "clears on next
  mission" is literally what the fix does. On current builds a stuck envelope cannot survive
  INTO a mission start but can still appear DURING one; long-standing sightings are plausibly
  mostly this, pre-fix. Treat pre-/post-clear sightings as different populations.
- **Gap remaining**: the clear list omits `r_dofBlur`, `r_ppMuzzleHeat`, `r_ppUnderwater`
  (verified cg_main.c:818-829), and `r_ppMuzzleHeat` is wrongly CVAR_ARCHIVE
  (tr_postprocess_gl1.c:816).

### S4 — `ssaoOk/dofOk/godRaysOk` ignore FBO completeness → composites of never-written scratch
Verified at tr_postprocess_gl1.c:660-661, 667-668, 687-688: the flags test the nonzero object
IDs `s.bloomFbo[0] && s.bloomFbo[1]`, while only `bloomOk` consumes the completeness results
`f0 && f1` (:652). If either half-res FBO is incomplete, all SSAO/DoF/god-ray scratch renders
silently no-op and the composites (:929-936 multiply, :971-990 alpha, :1063-1071 additive)
sample `bloomTex[*]` storage that was NULL-allocated (:564) and never written — uninitialized
VRAM, which on real drivers is frequently a recycled OLD texture/framebuffer image.
- **Ghost**: literally a random old texture multiplied/blended over the whole frame.
- **Wash/mud**: the multiply leg darkens/dirties globally.
- **Intermittency**: latches at `R_Init` — per SESSION (boot/vid_restart), not per map. A bad
  session stays bad until vid_restart. Boot log discriminates instantly:
  `postfx: bloom ... DISABLED` together with `postfx: ssao ready` (:653 vs :662) = S4 live.

### S5 — Archived `r_dofBlur` + the ungated legacy `RB_DepthOfField` (5-tap radial ghost)
`r_dofBlur` is CVAR_ARCHIVE (tr_init.c:1490) for a per-frame cgame-driven value, published only
from `CG_DrawAdsVignette` (cg_drawtools.cpp:1848) BELOW an early-return at :1812-1814
(vignette shader handle == 0 kills the publisher silently), and CG_Draw2D itself can be
engine-gated (cl_uiview3d.cpp:499-504). Consumer `RB_DepthOfField` (tr_backend.c:1475-1558)
runs at every swap gated ONLY by `r_dofBlur > 0` (:1483) — menus and loading screens included —
compositing 5 offset copies of the captured frame through a radial alpha (:1540-1553).
- **Ghost + mud**: a screen-anchored multi-image ghost + edge blur, by construction.
- **Intermittency**: aiming at the instant of the mod's instant `stuffsrv "map"` transition
  leaves up to ~0.84 latched; archive class persists it across a crash. Self-heals as soon as
  the publisher runs again → "clears next mission".
- Audits disagree on rank (01 F1 top vs 03 #4 minor): the publisher normally rewrites every HUD
  frame, and the dead-publisher precondition (hVig==0) is unverified in the field — so ranked
  here below the always-live suspects. The archive class is a standing bug-1202-class hazard
  regardless.

### S6 — `GLS_CLAMP_EDGE` side-channel flips `sceneColor`/`sceneDepth` wrap to GL_REPEAT
First `GL_State` of the post-pass (tr_postprocess_gl1.c:882) runs with post-FX textures bound;
if the LAST world surface drawn carried `GLS_CLAMP_EDGE`, the diff path (tr_backend.c:448-491)
stamps `GL_REPEAT` onto them, sticky until vid_restart. Off-screen taps then wrap to the
opposite edge: heat-haze warp, rain refraction, suppression edge blur, FXAA/sharpen border taps
→ smears/ghost-fringes at screen EDGES.
- **Intermittency**: draw-order + material dependent (per-map/per-view random onset).
- **Weakness**: does NOT self-clear next mission (persists to vid_restart) and produces
  edge-local, not full-screen, artifacts — fails half the report. Ranked last of the real
  suspects; still worth the one-line hardening.

### Amplifier (not a suspect): the shipped soft baseline
`r_ppExposure 0.70` + unconditional ACES whenever tonemap||grade (tr_postprocess_gl1.c:289-290,
750-751), bloom threshold 0.349, and DoF-erases-SSAO ordering (03_composite.md D6) all push the
clean frame toward "soft and washed", lowering the threshold at which any of S1-S6 reads as
"everything is muddy". Tuning decision, not a defect — but it explains report severity.

---

## 2. THE FIELD BISECT — run in console (`~`) while the bug is on screen (~90 s)

All toggles are live on gl1 (no latches in this set; the cfg:131 "SSAO needs relaunch" comment
is gl2-only). Record the last step that changed anything; finish with `condump`.

```
1.  cl_renderer                      // print. "opengl1" -> this card applies.
                                     // "opengl2" -> different suspect set (bug-1189/1211); still run 2-4.
2.  condump postfx_bug.txt           // captures the boot "postfx:" block. If it shows
                                     //   "bloom ... DISABLED" but "ssao ready"  ->  S4 CONFIRMED.
3.  r_postProcess 0                  // MASTER KILL (r_ppPassthrough is dead - ignore it).
                                     //   clean now  -> chain guilty, go 4.   still bad -> go 8.
4.  r_postProcess 1                  // bring it back, then PRINT (no visual judgment needed):
    r_ppSuppress; r_ppRainWet; r_ppHeat; r_ppMuzzleHeat; r_ppHealthFrac
                                     // calm+dry+unhurt, yet any nonzero (HealthFrac != 1)?
                                     //   -> S3 STUCK ENVELOPE; the nonzero name is the guilty effect.
5.  r_ppSSAO 0                       // dark blotch-ghost / global mud gone?
                                     //   -> S1 (SSAO leg)  [or S4 if step 2 flagged bloom DISABLED]
                                     // then restore: r_ppSSAO 1
6.  r_ppDoFFocus 0                   // THE S1-vs-S2 discriminator. DoF stays ON, focus -> auto.
                                     //   smear/ghost gone  -> S2 (fixed-focus seed) - config fix.
                                     //   unchanged -> r_ppDoF 0: gone NOW -> S1 (DoF leg, bad depth).
                                     // restore: r_ppDoF 1; r_ppDoFFocus 744.985718
7.  r_ppSunShafts 0; r_ppBloom 0     // wash/streaks change -> S4 legs or bloom amplifier.
                                     // restore both to 1. DONE - report which step cleared it.
8.  (only if step 3 changed nothing)
    r_dofBlur                        // print while NOT aiming. nonzero -> S5 (archived ADS blur).
    cg_dofStrength 0                 //   kills it via the product (r_dofBlur is rewritten per HUD frame).
    r_grass 0                        // raw-GL neighbor (audit-2 class).
    vid_restart                      // clears it with NO cvar changed -> per-session GL latch (S4/S6).
```

Report shorthand: "cleared at step N, command X" + `postfx_bug.txt`. Step 4 alone can convict
S3 with zero visual judgment; step 6 alone separates the two DoF-shaped suspects; step 2 alone
convicts S4. One occurrence is enough to sort all six.

Restore afterwards: `r_postProcess 1; r_ppSSAO 1; r_ppDoF 1; r_ppBloom 1; r_ppSunShafts 1;
cg_dofStrength 0.6; r_grass 1` (shipped values coop_defaults.cfg:35-59).

---

## 3. Proposed fixes, by confidence

### Tier 1 — one-liners, do regardless of bisect outcome (each closes a confirmed defect)

| # | Suspect | Fix | Site |
|---|---|---|---|
| 1 | S2 | `seta r_ppDoFFocus 0` (restore intended auto-focus; delete the leaked 744.985718 tune) | `hzm-mohaa-coop-mod/coop_defaults.cfg:41` |
| 2 | S3/S5 | Add `"r_dofBlur", "r_ppMuzzleHeat", "r_ppUnderwater"` to the `hzmClearFx[]` clear list | `code/cgame/cg_main.c:818-823` |
| 3 | S5 | `CVAR_ARCHIVE` → `0` on `r_dofBlur` (per-frame signal, wrong class) | `code/renderergl1/tr_init.c:1490` |
| 4 | S3 | `CVAR_ARCHIVE` → `0` on `r_ppMuzzleHeat` (contrast r_ppHeat, tr_init.c:1484) | `code/renderergl1/tr_postprocess_gl1.c:816` |
| 5 | S4 | Persist `f0 && f1` (e.g. `s.scratchOk`) and AND it into `ssaoOk` (:660), `dofOk` (:667), `godRaysOk` (:687) — completeness currently only reaches `bloomOk` (:652) | `code/renderergl1/tr_postprocess_gl1.c:647-688` |
| 6 | brief-D1 | Delete `r_ppPassthrough` registration (dead decoy that burns bisect time) or wire it into `R_PostFxActive` | `code/renderergl1/tr_init.c:1455` |

### Tier 2 — small targeted changes (order by bisect verdict)

| # | Suspect | Fix | Site |
|---|---|---|---|
| 7 | S1 | Validate the depth copy: drain `qglGetError()`, do the copy, check once; on error set a `s.depthValid=qfalse` for the frame, skip the SSAO and DoF blocks, and one-shot `ri.Printf("postfx: depth capture FAILED err=0x%x\n")`. Turns the prime suspect from conjecture into a log line (audit-3 D2) | `code/renderergl1/tr_postprocess_gl1.c:873-877`, gates at :888/:941 |
| 8 | S1 | Main-view-gate the per-frame flag: set `s_postfx_scene3D` only under the same `!isPortal && !isPortalSky && !RDF_NOWORLDMODEL` condition as the inline apply, so the Set2DWindow/swap fallbacks can never run the chain on a no-world-view frame (audit-3 D4) | `code/renderergl1/tr_backend.c:1286` (condition at :1299-1303) |
| 9 | S5 | Publish `r_dofBlur` unconditionally from CG_CalcFov (like every other channel) instead of below the vignette early-return; or hoist the publish above `cg_drawtools.cpp:1812-1814` | `code/cgame/cg_drawtools.cpp:1848` → `cg_view.c` |
| 10 | S6 | Consume the clamp diff before our textures are bound: call `GL_State(GLS_DEPTHTEST_DISABLE)` BEFORE the :869 bind (engine textures still bound), and/or re-assert `GL_CLAMP_TO_EDGE` on `sceneColor`/`sceneDepth` after the pass's first `GL_State` (audit-2 F1) | `code/renderergl1/tr_postprocess_gl1.c:867-886` |
| 11 | latent | `qglClientActiveTextureARB(GL_TEXTURE0_ARB);` beside the server-side force (half TMU repair currently poisons GL_SelectTexture's cache; audit-2 F2) | `code/renderergl1/tr_postprocess_gl1.c:867-868` |
| 12 | latent | End `R_InitPostFxGL1` with `glState.currenttextures[0] = -1;` (init leaves the bind cache stale one batch per DLL load; audit-2 F3, engine idiom tr_image.c:954) | `code/renderergl1/tr_postprocess_gl1.c:692` |
| 13 | latent | Inline-apply guard: add `&& !s_postfx_applied` so a future second world view can't double-ACES/double-AO (audit-1 F7 / audit-3 D3) | `code/renderergl1/tr_backend.c:1299` |

### Tier 3 — hardening / hygiene (no observed reachability today)

- Hoist `qglBindFramebuffer(GL_FRAMEBUFFER, 0)` (:880) above the :869 capture (audit-2 F6).
- Grass: replace raw `qglDisable/qglEnable(GL_CULL_FACE)` with `GL_Cull`/cache update
  (`tr_grass_gl1.c:293,331`; audit-2 F7 — sprite-level artifacts, not this bug).
- Delete `dofTex` in `RE_Shutdown` / add a context-generation guard (audit-1 F5, audit-2 F8 —
  only a name leak while `USE_RENDERER_DLOPEN` is ON; becomes live if ever linked static).
- Fix the `coop_defaults.cfg:131` comment ("SSAO is CVAR_LATCH") — true only on gl2.
- Tuning review (amplifier, user's call): bloom threshold 0.349 and exposure 0.70+always-ACES.

**Do-not-break invariants for any of the above (audit 2):** the exit-repair at
tr_postprocess_gl1.c:1218-1219 is sound only because gen'd texture names are unique
(never revert tr_image.c:885-889 to fixed texnums) and because no engine code runs
mid-`RB_PostFxApply` (no early returns / ri.Printf-triggered renders after :871).

---

## 4. Permanent telemetry hook — self-diagnosing map loads

One line per map load, greppable in `%APPDATA%\openmohaa\maintt\qconsole.log` (already
line-flushed via `logfile 2`). Add `void R_PostFxLogStatus(void)` to
`tr_postprocess_gl1.c` (it owns the static `s`) and call it from `RE_BeginRegistration`
(`code/renderergl1/tr_init.c:1897-1931` — the one per-map renderer entry point, which today
never touches post-FX):

```c
ri.Printf(PRINT_ALL,
  "postfx: mapload rend[init=%d bloom=%d ssao=%d dof=%d rays=%d %dx%d depthErr=%d] "
  "cv[pp=%d ssao=%d dof=%d focus=%.1f bloom=%d rays=%d tone=%d grade=%d] "
  "env[sup=%.2f rain=%.2f heat=%.2f muz=%.2f hp=%.2f dofBlur=%.2f]\n",
  s.inited, s.bloomOk, s.ssaoOk, s.dofOk, s.godRaysOk, s.width, s.height, s.depthErrCount, ...);
```

- `rend[...]` exposes S4 (bloomOk=0 while ssao/dof composite anyway) and, with the Tier-2 #7
  counter, S1 (`depthErr` nonzero = failed depth captures this session).
- `env[...]` exposes S3/S5 at the exact boundary where a stuck value would survive into a
  mission (any nonzero here, or hp != 1.00, at map load = latch caught red-handed).
- `focus=` exposes S2 at a glance (should read 0.0 after fix #1).
- Keep the existing `postfx:` prefix — consistent with the init block (:638-691) so one grep
  (`findstr /c:"postfx:" qconsole.log`) returns boot state + every map load. Cost: one printf
  per map load; no per-frame work beyond the #7 error check.

With #1-#6 shipped and the telemetry line in, the next field occurrence should identify itself
in the log without the user running anything; the bisect card remains the interactive fallback.

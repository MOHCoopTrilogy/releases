# AUDIT 3 — gl1 post-FX composite math and ordering

Scope: `openmohaa-hzm/code/renderergl1/tr_postprocess_gl1.c` (1221 lines) + its hook sites
(`tr_backend.c`, `tr_draw.c`, `tr_init.c`) + the cgame publishers (`cg_view.c`,
`cg_drawtools.cpp`, `cg_main.c`) + the shipped defaults (`hzm-mohaa-coop-mod/coop_defaults.cfg`).
Read-only audit; every claim cites file:line. Date: 2026-08-09.

---

## 0. Corrections to the task's assumed effect roster (verified, not assumed)

The "40+ r_pp* effects" list mixes the two renderers. The **gl1** layer implements exactly
eleven passes: bloom, SSAO, DoF, tonemap/grade, FXAA, sharpen, low-health, suppression,
heat-haze (+muzzle heat), rain-on-lens, god rays (`tr_postprocess_gl1.c:76-116` state struct;
`736-1220` the whole chain). The following DO NOT EXIST in gl1 — they are gl2-only
(`renderergl2/tr_postprocess.c`, `renderergl2/glsl/*`):

- **MotionBlur (history buffer)** — gl2 only (`renderergl2/tr_postprocess.c:799-881`,
  `motionblur_fp.glsl`, bug-1239). **There is no history buffer anywhere in gl1.** The only
  frame-persistent gl1 textures are `sceneColor`, `sceneDepth`, `bloomTex[0/1]`
  (`tr_postprocess_gl1.c:79-87`) and the legacy ADS-DoF scratch `dofTex`
  (`tr_backend.c:1476`), and every consumer overwrites its input in the same frame it reads
  it — **except when a copy silently fails** (see §3.1). So "what does MotionBlur blend on the
  first frame after map load" has answer: N/A on gl1; on gl2 it is a real question, out of
  scope here.
- FilmGrain, Frost, Hit/HitBlood, Dizzy, Underwater, ChromAb — gl2 only
  (`renderergl2/tr_postprocess.c:766-1136, 1411-1433`). Frost's publisher was deleted 08-07
  (`cg_view.c:2097-2102`).
- **`r_ppTemp`** — gl2 only (`renderergl2/tr_postprocess.c:93-101`). In gl1 the equivalent
  is the `u_temp` white-balance uniform inside the tonemap shader, driven only by the
  `r_ppGrade` presets (`tr_postprocess_gl1.c:286, 294-295, 1084-1089`). It is not an effect.
- **`r_ppPassthrough` is a DEAD CVAR on gl1.** It is registered (`renderergl1/tr_init.c:1455`,
  default `1`, CVAR_ARCHIVE) and declared (`tr_local.h:1457`) but **never read anywhere** —
  grep of `renderergl1/` finds only the declaration and registration. The chain's real master
  bypass is `r_postProcess` (`tr_init.c:1454`, live, checked every frame in `R_PostFxActive`,
  `tr_postprocess_gl1.c:728`). **The field bisect must NOT start with `r_ppPassthrough 1` —
  it does nothing.** (Defect D1 below.)

Which renderer is the player on? `cl_renderer` (default `"opengl1"`, ARCHIVE|LATCH,
`client/cl_main.cpp:3231`). Recent buglog work (1144–1304) is heavily gl2, so field reports
must record `cl_renderer` first — bug-1189 was an identical "ghost that moves with me" on the
**gl2** build with a completely different cause (unported portal-entity gate in
`renderergl2/tr_main.c`; gl1 has the gate at `renderergl1/tr_main.c:1417-1435` and was
verified clean in that incident).

---

## 1. Frame trace (gl1, verified order)

Design: "Approach B" — the engine renders the frame normally to the **backbuffer**;
the post pass copies it out, runs shader passes, draws results back. No render-target
redirect (`tr_postprocess_gl1.c:1-8`).

### 1.1 Hook placement

1. `RB_DrawSurfs` renders the world surface list (`tr_backend.c:1273-1289`). It sets
   `s_postfx_scene3D = qtrue` **unconditionally — including for portal, portal-sky and
   RDF_NOWORLDMODEL views** (`tr_backend.c:1286`).
2. The chain runs **inline, immediately after the world surfaces**, gated to the main view
   only: `!isPortal && !isPortalSky && !(rdflags & RDF_NOWORLDMODEL)`
   (`tr_backend.c:1299-1303`). It sets `s_postfx_applied = qtrue` **without checking it
   first** (defect D3).
3. `R_DrawGrass()` runs AFTER the chain, with raw immediate-mode GL
   (`tr_backend.c:1305`, comment 1291-1298: grass before the chain used to silently break it).
4. `RB_SpriteSurfs` (sprites: muzzle flashes, smoke, fire billboards) is a **separate later
   command with no post-FX call** (`tr_backend.c:1317-1334`) — sprites are never captured,
   graded, AA'd or AO'd. Consequence for this hunt: **no sprite effect can be the source of a
   post-FX ghost**; conversely nothing the chain does can distort sprites.
5. Fallback A: `Set2DWindow` (the universal 3D→2D chokepoint) calls `RB_PostFxMaybeApply()`
   on the frame's first transition (`tr_draw.c:437-447`).
6. Fallback B: `RB_SwapBuffers` calls `RB_PostFxMaybeApply()` again (`tr_backend.c:1570`),
   then the **separate legacy ADS blur `RB_DepthOfField`** (`tr_backend.c:1573`, body
   1475-1557 — NOT part of the r_pp chain, gated only by `r_dofBlur`), then resets both
   per-frame flags (`tr_backend.c:1612-1613`).
7. Master gate `R_PostFxActive`: procs loaded && FBO inited && `r_postProcess` && `sv_running`
   (`tr_postprocess_gl1.c:721-729`). Menus (sv_running 0) are skipped, which means the
   persistent textures **carry the previous mission's content across the whole menu/loading
   period** — harmless only as long as every consumer's overwrite-before-read holds.

### 1.2 Pass order inside `RB_PostFxApply` (736-1220)

| # | pass | source | blend onto backbuffer | gate (shipped value, coop_defaults.cfg) |
|---|------|--------|----------------------|------------------------------------------|
| 0 | capture | backbuffer → `sceneColor` (871); depth → `sceneDepth` only if SSAO\|\|DoF (873-877) | — | always |
| 1 | base | `sceneColor` | **replace** (879-886) | always |
| 2 | SSAO | **`sceneDepth`** → AO half-res → bilateral blur | **multiply** `DST_COLOR/ZERO` (930-936) | `r_ppSSAO 1` (cfg:49) |
| 3 | DoF | `sceneColor` (pre-FX capture) blurred + **`sceneDepth`** per-pixel CoC | alpha `SRC_ALPHA/1-SRC_ALPHA` (979-990) | `r_ppDoF 1` (cfg:40) |
| 4 | Bloom | `sceneColor` (pre-FX capture) bright-pass 0.349→blur | **additive** `ONE/ONE` (1026-1033) | `r_ppBloom 1` (cfg:36) |
| 5 | GodRays | `sceneColor` bright-pass → radial march | **additive** (1064-1071) | `r_ppSunShafts 1` (cfg:56) |
| 6 | Tonemap/Grade | fresh re-copy of live backbuffer (1091-1093) | **replace** (1095-1105) | `r_ppTonemap 1` **OR** `r_ppGrade>0` (750-751; cfg:59 = ON) |
| 7 | FXAA | fresh re-copy | replace (1109-1122) | `r_ppFXAA 1` (cfg:45) |
| 8 | Sharpen | fresh re-copy | replace (1126-1142) | `r_ppSharpen 1` (autoexec:706) |
| 9 | HeatHaze+muzzle | fresh re-copy, UV warp | replace (1147-1163) | `r_ppHeatHaze 1` × envelope `r_ppHeat`/`r_ppMuzzleHeat` |
| 10 | Rain-on-lens | fresh re-copy, refractive beads | replace (1168-1182) | `r_ppRainDrops 1` (837) × envelope `r_ppRainWet` |
| 11 | LowHealth | fresh re-copy | replace (1187-1199) | `r_ppLowHealth 1` × `r_ppHealthFrac < 0.5` |
| 12 | Suppression | fresh re-copy | replace (1203-1215) | `r_ppSuppression 1` × envelope `r_ppSuppress` |

Exit: `qglUseProgram(0)` + `GL_Bind(tr.whiteImage)` (1218-1219). Viewport is left at full
window (not restored — see D5).

Note the two source generations: passes 2-5 all read the **frame-start capture**; passes 6-12
each re-copy the **evolving backbuffer**. Two small math consequences: (a) DoF's blurred
source is the un-AO'd capture, so wherever DoF mixes (55% shipped) it **erases the AO** laid
down one pass earlier — distant areas are systematically brighter/flatter than intended
(D6); (b) bloom bright-passes the raw capture, so it re-adds light that AO removed. Both are
constants of the design, not the intermittent bug, but they push the shipped baseline toward
"soft and washed" (see §2.3).

---

## 2. Which single effect, fed a stale/garbage input, produces BOTH symptoms

### 2.1 The one fragile input: `sceneDepth` — feeds the two shipped-ON passes at once

Every other input is rewritten in-frame by the pass that reads it. `sceneDepth` is filled by a
single `qglCopyTexSubImage2D` **depth readback from the default framebuffer**
(`tr_postprocess_gl1.c:874-876`) — the most driver-fragile operation in the whole chain —
and its two consumers, SSAO and DoF, are both ON in the shipped config (cfg:49, cfg:40).
Failure is **silent**: `r_ignoreGLErrors` defaults to `1` (`tr_init.c:1493`) and the chain
never checks. The texture is allocated with a NULL upload (`tr_postprocess_gl1.c:621-623`),
so before the first successful copy it is undefined VRAM (gl2 precedent: bug-1211's
NULL-upload SSAO image was driver zero-fill = black screen).

If `sceneDepth` is **stale** (holds an earlier scene's depth) or structured garbage:

- **SSAO** computes the AO of the OLD scene and **multiplies it over the current frame**
  (930-936): dark blotch silhouettes of geometry that is not there, at half resolution,
  bilinearly upsampled (644-645, comment 186-190) — i.e. a soft, blurry, screen-locked
  **ghost image that moves with the camera**, and a global **dirty/muddy darkening**.
- **DoF** evaluates its per-pixel circle-of-confusion from the same wrong depth
  (271-276, 984-989) and mixes the half-res blurred scene at up to `r_ppDoFIntensity`
  **0.55 shipped** (cfg:42) with a **fixed** focus 745u (cfg:41). Wrong depth ⇒ sharp/blur
  regions shaped like the old scene ⇒ a second ghost mask, plus large areas of the world
  smeared with a half-res blur — precisely "**world textures look really bad/low-quality**".
- Bloom (threshold **0.349** shipped, cfg:38 — very low, most of the frame passes it) then
  bright-passes and **adds** on top (1026-1033), milking the already-darkened image —
  "**washed out**".

One failed/stale copy therefore yields the full reported triad — ghost tracking the camera,
mud, bad textures — through two independently-visible passes. Uniform garbage (zero-fill)
is comparatively benign: depth 0 ⇒ `lin()` = zNear everywhere ⇒ neighbor diffs 0 ⇒ AO = 1
(191-213), and DoF CoC uniform ≈ |4−745|/2257×0.55 ≈ 0.18 ⇒ a subtle all-over softening
with no ghost — a milder "textures look slightly worse" presentation of the same root.

**Verdict: prime suspect for the single-effect explanation = the shared `sceneDepth`
capture, expressed through SSAO (ghost+mud) and DoF (bad textures), with bloom amplifying
the wash.** It also fits the lifecycle: the capture only runs while `sv_running` and a world
view exists (§1.1.7), so whether the first mission frame refreshes it before first use is a
per-map-load ordering event, and a next-mission load can re-succeed — matching
"random mission starts, sometimes clears next mission".

### 2.2 The competing explanation: stuck cgame envelope cvars (two effects, one mechanism)

`r_ppSuppress`, `r_ppHeat`, `r_ppMuzzleHeat`, `r_ppRainWet`, `r_ppHealthFrac` are engine
cvars written every frame by `CG_CalcFov` (`cg_view.c:1936, 2016, 2051, 2058, 2095`). The
publisher block is **skipped on snapshot loss, during cinematics, and at the menu**
(cg_main.c comment 810-812), so a value spiked just before such a window **freezes**:

- `r_ppSuppress` frozen ≳0.5 ⇒ 40-80% desaturation + up to 72% edge darkening + peripheral
  smear every frame (`SUPPRESSION_FS`, 386-404) — the single best "**muddy and washed
  out**" producer in the chain.
- `r_ppRainWet` frozen >0 ⇒ permanent refractive beads + downward trickles + glint
  (`RAINDROPS_FS`, 443-494) — screen-space, camera-locked — the single best
  "**texture ghosted over the screen that moves with the camera**" producer. Historical
  trigger: the pre-bug-1206 rain test classified the 8 **sandstorm** maps as rain
  (`cg_view.c:2075-2078`) — beads on random dry missions.

**Both** symptoms together = two cvars stuck at once, which one frozen-publisher window
produces. And the fix already shipped matches the report's "clears on next mission"
verbatim: CG_Init now zeroes all five signals on every map change/reconnect
(`cg_main.c:808-830`, code-comment bugs 1202/1307). So for **old builds** this was almost
certainly the dominant cause; on **current builds** the CG_Init clear bounds it to
mid-mission windows (a stuck effect now cannot survive INTO a mission start, but can still
appear DURING a mission after a cinematic/snapshot-loss window). The report is
long-standing/intermittent — treat pre- and post-clear sightings as different populations.

### 2.3 Rejected / secondary suspects

- **Tonemap/Grade double-apply**: cannot occur through the fallbacks (`s_postfx_applied`
  guard, `tr_backend.c:1033`), and the inline site runs once per main view; a double apply
  would need two non-portal world views in one frame, which nothing currently produces
  (latent D3). Not the live bug.
- **Tonemap as designed**: the pass applies ACES **unconditionally** whenever
  `r_ppTonemap||r_ppGrade` (289-290, 750-751). With shipped `r_ppExposure 0.7` (cfg:44),
  peak white maps to ACES(0.7) ≈ **0.72** — the shipped baseline literally cannot show a
  full-white pixel. Constant, so not the intermittent delta, but it lowers the
  "washed-out" threshold the bug is judged against, and explains why the bug reads as
  "everything muddy" so quickly.
- **GodRays**: shipped ON (cfg:56) but additive-only from a same-frame bright-pass; its gate
  needs a real sun in front of the camera (851-864). Wrong-sun artifacts are streaks, not
  mud. (gl2 had that bug: bug-1169.)
- **FilmGrain/Frost/Hit/Dizzy "stuck at nonzero"**: not gl1 passes (§0).
- **Legacy `RB_DepthOfField` ADS blur**: recaptures every frame (`tr_backend.c:1512`) so no
  stale ghost; but `r_dofBlur` is CVAR_ARCHIVE (`tr_init.c:1490`) while being a per-frame
  cgame-driven value written only when the HUD path runs (`cg_drawtools.cpp:1841-1848`) — a
  session can start with an archived nonzero blur until the first HUD frame rewrites it
  (D7). A 5-tap offset composite at radius 3 (1540-1553) is a faint double-image + smear:
  a plausible *minor* contributor, self-healing, bisectable via `cg_dofStrength 0`.
- **Base-pass replace with stale `sceneColor`** (copy at 871 fails): would replace the live
  frame with a frozen old frame — a much louder symptom than reported. Kept as the "screen
  frozen/whole-frame ghost" variant only.

---

## 3. Defects found (composite/ordering; all read-only findings)

- **D1 — `r_ppPassthrough` dead.** Registered default 1 (`tr_init.c:1455`), never read.
  Either wire it into `R_PostFxActive`/`RB_PostFxApply` as the documented bypass or delete
  it; today it is a decoy that would burn a field bisect's first minute.
- **D2 — depth capture failure is invisible.** No error check around 871/876, sceneDepth
  NULL-allocated (623), `r_ignoreGLErrors 1` default (1493). One `qglGetError` after the
  copies + a one-shot `ri.Printf` would turn §2.1 from conjecture into a log line.
- **D3 — inline apply sets but never tests `s_postfx_applied`** (`tr_backend.c:1301`) —
  latent double-apply (double AO multiply + double bloom add + double ACES = instant
  mud+wash) if any future feature renders a second non-portal world view per frame.
- **D4 — `s_postfx_scene3D` set by every RB_DrawSurfs** (1286), including portal-sky and
  RDF_NOWORLDMODEL views, so the Set2DWindow/swap fallbacks can run the full chain on a
  frame with **no main world view** while sv_running=1 (loading/UI-model frames): it
  captures a non-scene backbuffer and SSAO/DoF read whatever depth that view left.
  Transient (one frame per occurrence) but a genuine wrong-time composite.
- **D5 — viewport not restored** after the chain (left full-window, e.g. 1096/1115/...);
  `RB_SpriteSurfs` never re-sets a viewport (1317-1334). Invisible at full-screen views;
  wrong for any sub-rect view.
- **D6 — DoF erases SSAO** (order 2→3 with a pre-FX source): blurred regions composite the
  un-AO'd capture over the AO'd backbuffer (949-990). At shipped DoF 0.55 the distant world
  loses over half its AO. Cosmetic-constant, not the bug.
- **D7 — `r_dofBlur` is CVAR_ARCHIVE for a per-frame-driven value** (`tr_init.c:1490`,
  writer `cg_drawtools.cpp:1848`): persists a mid-ADS value to disk on exit; also churns
  the config every session.
- **Doc bug** — `coop_defaults.cfg:131` claims "r_ppSSAO is CVAR_LATCH - needs relaunch".
  True only on gl2; gl1 registers it CVAR_ARCHIVE, read live per frame (`tr_init.c:1459`,
  `tr_postprocess_gl1.c:747`). On gl1 it bisects instantly.

---

## 4. THE FIELD BISECT — run while the bug is on screen (< 1 minute)

All toggles are live on gl1 (no latches in this set). Open console (`~`). After each step,
look for 2-3 seconds. Record the last step that changed anything.

```
step 0  (2s)   cl_renderer                     // just print it. "opengl1" -> this audit applies.
                                               // "opengl2" -> different suspect set (motion-blur
                                               // history, bug-1211/1189 class) - still run steps 1-3.

step 1  (2s)   r_postProcess 0                 // MASTER KILL. (NOT r_ppPassthrough - dead cvar, D1.)
        -> everything clean?  chain guilty -> step 2.
        -> ghost/mud REMAINS? chain innocent -> step 5.

step 2  (10s)  r_postProcess 1                 // bring the bug back (confirms it's reproducible)
               r_ppSuppress                    // print-only: each of these should be ~0 when calm,
               r_ppRainWet                     // dry, unhurt. ANY nonzero while calm = STUCK
               r_ppHeat                        // ENVELOPE (SS2.2): the printed name is the guilty
               r_ppHealthFrac                  // effect (HealthFrac should read 1, not <0.5).
                                               // Fix check: does a map change clear it? (CG_Init
                                               // clear, cg_main.c:808-830)

step 3  (10s)  r_ppSSAO 0                      // ghost/mud gone -> STALE DEPTH via SSAO (SS2.1)
               r_ppDoF 0                       // texture smear gone -> STALE DEPTH via DoF (SS2.1)
                                               // (either hit = same root: the sceneDepth capture,
                                               // tr_postprocess_gl1.c:873-877)

step 4  (15s)  r_ppBloom 0                     // milky wash gone -> bloom (input = frame capture)
               r_ppTonemap 0; r_ppGrade 0      // BOTH: either one alone forces the ACES pass (750-751)
               r_ppHeatHaze 0                  // constant shimmer/warp gone -> heat envelope leak
               r_ppRainDrops 0                 // beads gone -> rain pass (master, renderer-side)
               r_ppSharpen 0; r_ppFXAA 0       // edge crunch / smear

step 5  (only if step 1 changed nothing)
               cg_dofStrength 0                // kills the SEPARATE ADS radial blur via its product
                                               // (r_dofBlur is rewritten every HUD frame - set the
                                               // strength, not r_dofBlur itself; cg_drawtools.cpp:1848)
               r_grass 0                       // raw-GL state-desync suspect (audit 2 scope;
                                               // tr_backend.c:1291-1298 precedent)
               vid_restart                     // clears it with NO cvar changed -> stale GL object /
                                               // glState desync, not a cvar-driven effect. Rebuilds
                                               // the postfx FBOs+programs (R_InitPostFxGL1,
                                               // tr_postprocess_gl1.c:594-692).
```

Reporting shorthand for players: "bug cleared at step N, command X" + a `condump`. Step 2 is
print-only and needs no visual judgment — if any envelope reads nonzero while calm, that IS
the answer regardless of the toggles.

Restore afterwards: `r_postProcess 1; r_ppSSAO 1; r_ppDoF 1; r_ppBloom 1; r_ppTonemap 1;
r_ppHeatHaze 1; r_ppRainDrops 1; r_ppSharpen 1; r_ppFXAA 1; cg_dofStrength 0.6`
(shipped values: coop_defaults.cfg:35-59, autoexec.cfg:318,706).

---

## 5. Suspect ranking (for the fix phase)

1. **Stale/failed `sceneDepth` capture → SSAO multiply + DoF CoC** — one root, both
   symptoms, both passes shipped ON, failure silenced by `r_ignoreGLErrors 1`
   (`tr_postprocess_gl1.c:873-877, 888-937, 941-997`; cfg:40-43, 49-53).
2. **Stuck cgame envelopes (`r_ppRainWet` ghost-beads + `r_ppSuppress` wash)** — fully
   explains historical sightings incl. "clears next mission"; on current builds bounded by
   the CG_Init clear (`cg_main.c:808-830`) but still reachable mid-mission via
   publisher-skip windows (`cg_view.c:1985-2016, 2065-2095`).
3. **Bloom over-add on a soft baseline** (threshold 0.349, exposure 0.7 + always-ACES) —
   amplifier, not initiator (cfg:38,44,59; `tr_postprocess_gl1.c:289-290, 1026-1033`).
4. **Archived `r_dofBlur` / ADS radial blur at session start** — minor, self-healing
   (`tr_init.c:1490`, `tr_backend.c:1475-1557`, `cg_drawtools.cpp:1841-1848`).
5. **glState desync from raw-GL neighbors (grass) ghosting the world render itself** —
   matches all symptoms too but is outside composite scope; flagged for audit 2
   (`tr_backend.c:1291-1298, 1305`).

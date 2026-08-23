# PHILLIPS DOSSIER — gl2 invisible-actor bug (handoff-ready)

## ✅ RESOLVED 2026-07-27 ~21:55 (bug-1135) — ROOT CAUSE + ONE-LINE FIX, RIG-VERIFIED
**Root cause:** gl2 `R_AllocModel` (tr_model.cpp) slot-REUSE branch never re-stamped `mod->index`.
`R_FreeModel` memsets the whole model_t (index included), so the next model registered into a
freed slot LOADED fine but `R_RegisterModelInternal` returned `mod->index == 0` — "registration
failed" — and its caller (cgame modelindex map) stored handle 0: the model could never be drawn
again that session. gl1 re-stamps `tr.models[i].index = i` on EVERY alloc (gl1 tr_model.cpp:102);
the gl2 pointer-pool port dropped it. **Fix:** `mod->index = i;` in the reuse branch.
**Trigger chain on e2l2:** initPlayer's `$lyndon gun "vickers"` → server frees his old
`weapon|m1 garand|…` composite (slot 961) → new `weapon|vickers|…` composite reuses slot 961 →
returned 0 (broken) / 961 (fixed). Vanilla coin flip = WHICH late registration lands in a freed
slot varies per boot. Stacked on (distinct from) bug-1131's parentEntity garbage-lighting defect.
**Evidence:** SKELREG `weapon|vickers|…` handle=0 result=ok tot=664/1024 (pool NOT full, load OK);
SKELTRACK submit probe = zero renderer submissions post-swap pre-fix, continuous submissions with
7 drawSurfs/frame post-fix; fixed1_3.png = Phillips visible in gl2 at the freeze spot with the
Vickers. gl1/gl2 same-spot A/B rig killed the script, hide→show, dark-but-correct, and
pool-exhaustion hypotheses first. Magenta flood (r_skeldiag 7) showed not-drawn, not drawn-dark.
**Still to strip before any release-quality gl2 build:** all SKEL* probes incl. new SKELCLR/
SKELTRACK/SKELFLOOD (tr_shade.c, tr_model.cpp, tr_scene.c). Vanilla-flow ×N boots + $brit
(later-mission Lyndon) check pending at write time. Consider gl1-parity MAX_MOD_KNOWN 1024→2048
(headroom: 664 registrations in a light freeze boot) as a follow-up hardening.

**One-line problem:** In the gl2 (rend2/GLSL) renderer of openmohaa-hzm, the e2l2 intro briefer
"Lt. Joe Phillips" (entity `$lyndon`, BSP classname `addon_ai_allied_brit_Commander`, model
`human/Sc_Al_Brit_Cmd.tik`, scale 0.52, renderfx FRAMELERP|EXTRALIGHT|SHADOW|SHADOW_PRECISE)
is invisible on SOME boots and visible on others — same dll, same script. gl1 renders him always.

## Verified facts (all instrumented, do not re-derive)
- INVISIBLE boots: his surfaces execute in the MAIN opaque color pass (depthFill=0),
  main view (no portal/portalsky), tr.renderFbo, drawBuf0=GL_COLOR_ATTACHMENT0, GL program 529
  (IDENTICAL to a visible German control in the same frame), colorMask 0xf, blend off, scissor full,
  depth LEQUAL. Occlusion query: 39k–48k samples PASS. Draw-time tess.xyz projects to the CORRECT
  screen box (NDC-verified). Framebuffer readback at 9 in-silhouette pixels: BYTE-IDENTICAL
  before/after his draw — nothing written. German control writes normally at his own pixels.
- VISIBLE boots: same everything → he writes color and appears (captures exist).
- State persists for a whole session (per-boot latch, not per-frame flicker).
- Refuted: PVS/frustum, wrong FBO/view, depth prepass (drawbuf NONE), program binding, geometry
  displacement, mirror cull, renderfx gates, pose-cache skip (byte-identical to gl1), shader defs
  (plain single-stage rgbGen lightingSpherical), MSAA, fog-paint (readbacks show NO write, not grey),
  corrupt skd box data (shared code, both renderers), model identity (vanilla-correct; e2l1 names
  the same combo "Lieutenant Phillips" / ai_allied_1st-ranger_lieutenant).
- Key asymmetries vs the working German control: Phillips is BSP-placed addon_ai (German was
  script-spawned), scale 0.52 (German 1.0), composite of 5 skelmodels + attached Vickers.
- The GL-legal loopholes left: NaN vertex colors / NaN uniforms (NVIDIA writes nothing but depth
  passes), or an equally-exotic driver-state latch. Prime suspect: uninitialized per-entity lighting
  data (RB_FillModelLightingColors / lightingSpherical CGEN inputs) that differs per boot.
- Recent renderer changes that grew/changed memory layout (could gate the boot coin-flip):
  MAX_POLYS 600→131072 (backEndData ~17MB), ri.Hunk_Clear added to RE_BeginRegistration,
  r_sequencenumber++ added, R_ShutdownFont wired.

## Rig (all working, reuse)
- Isolated build G:\mohaa-gl2 (junctioned data, own homepath). Boot harness:
  scratchpad\gl2test\lyndonface.ps1 (spawns, captures burst, greps probes). Override pk3 recipe:
  loose maps/e2l2.scr in G:\mohaa-gl2\home\maintt\zzzzzz_zzz_gl2lyndon.pk3 — freeze
  ($lyndon disable_ai/nodamage/notsolid/hide), wait for player, teleport to (6296 -5720 2510),
  show, anim idle. Briefing disabled by commenting the `briefing.scr::init` line.
- Diagnostic probes compiled in renderergl2 (SKELREG/SKELPIX/SKELZ/SKELAGG/SKELVIEW/SKELCOL/
  SKELROW/SKELNDC in tr_shade.c + tr_model.cpp, `^~^~^` log lines; one-shot ≤6 frames per model
  handle per boot — hide-until-placed to aim them). RB_SkelProbeShutdown hooked in
  R_ShutDownQueries (context-loss safety). STRIP ALL SKEL* WHEN CLOSED.
- Deep agent already tasked with the NaN/uninitialized-lighting hunt (report may exist in
  .wolf/memory.md or the session when you read this).

## Next experiments (in value order)
1. Print his tess.color[0..3] + the entity's ambientLight/lighting inputs on a VISIBLE boot and an
   INVISIBLE boot; diff. (NaN shows immediately.)
2. If NaN: trace source (R_SetupEntityLighting / spherical lighting tables / BSP-entity fields) and
   sanitize at source; verify with boot loop (≥5 boots, count visible).
3. If not NaN: capture glGetError + all glGet state deltas between his draw and the German's in the
   same frame (dump-diff), then driver-level (NVIDIA GL threaded optimization off, etc.).
4. Acceptance: vanilla-flow e2l2 boot ×5, Phillips visible in the intro every time; then check the
   later-mission Lyndon (`$brit`, sc_al_brit_pilot.tik — user says the real "Lyndon" appears later)
   and other maps' scripted-briefing allies.

## Also open on e2l2 (separate from rendering)
- User heard NO briefing dialogue with volume on (never had volume before) — verify Phillips' VO
  (dfrus_e2l2_jp* / A_22_Phillips_*) actually plays in coop; the mod has an established dialogue-
  restoration pattern if aliases are missing.
- User: model wears no visible commander cap in some captures — check AL_Brit_CMDHAT surface.

## UPDATE 07-27 ~19:15 — parentEntity fix landed, did NOT close it
- IMPLEMENTED (KEEP — real gl1-parity bug regardless): gl2 RE_AddRefEntityToScene2 dropped
  parentEntityNumber → grid-light walk chased refdef slot 0's uninitialized iGridLighting.
  Fixed in renderergl2/tr_scene.c (sanitize + gl1-style translate) + bounds guards in
  tr_light.c RB_SetupEntityGridLighting (both walks) + 2 walkers in tr_sphere_shade.cpp
  (bug-1131). Built + deployed to G:\mohaa-gl2.
- POST-FIX VERIFY: 3 deterministic freeze boots — reveal marker fired, 48k samples pass,
  SKELROW shows his fragments WRITING dark-olive values ([36,36,29]..[54,55,46]) — yet he is
  NOT visible in any capture. Earlier in the day, boots with the SAME written-value magnitudes
  had him plainly visible. So either (a) another garbage-color source persists (agent's
  residual-gap note: any refEntity submission path bypassing the memset local → stale large
  parentEntity indexing a never-initialized slot — but now bounds-guarded → falls back to
  computed lighting... unless bLightGridCalculated garbage?), or (b) the written dark values
  blend into the scene at 120u fog and "visible vs invisible" boots differ by LIGHTING VALUE
  (garbage bright = visible, garbage dark = invisible) — i.e. the fix's computed value for
  this dark map is LEGITIMATELY dark-but-correct and he's simply hard to see?? Refute via:
  compare a gl1 boot's Phillips pixel values at the same spot (gl1 A/B harness exists).
- NEXT (fresh session, in order):
  1. SKELCLR probe (agent's exact code, see agent report in this session/bug-1131 notes):
     print iGridLighting + parentEnt for ent 213 AND a German control per boot → is the color
     SOURCE now sane? If iGridLighting is a plausible packed RGBA and matches the German's
     magnitude, the render is CORRECT and the "invisibility" = brightness/contrast (then
     compare gl1's grid color for the same spot — RB_GetEntityGridLighting parity).
  2. Magenta flood (agent's probe b) — instantly separates "not drawn" from "drawn dark".
  3. r_fastentlight 0 boot — alternate lighting path comparison.
  4. gl1 freeze-boot at the same spot + same captures → pixel-value ground truth for how
     bright Phillips SHOULD be there.
- The 3 verification boot logs: last one at G:\mohaa-gl2\home\maintt\qconsole.log; captures
  scratchpad\gl2test\allycap\pfix*.png. Freeze override pk3 currently DEPLOYED at
  G:\mohaa-gl2\home\maintt\zzzzzz_zzz_gl2lyndon.pk3 (REMOVE for vanilla flow).

## UPDATE 07-27 ~20:45 — gl1-vs-gl2 same-spot A/B: INVISIBLE CONFIRMED, dark-hypothesis DEAD
- New rig (fresh session): override pk3 REBUILT (freeze + teleport ~130u in front of player,
  relative placement, GL2TEST-LYNDON markers) at G:\mohaa-gl2\home_test\maintt (ISOLATED
  homepath — old home\maintt pk3 was gone; harness cvar pollution had also stomped the user's
  omconfig r_customwidth/fullscreen = the "4:3 bars" report, bug-1134, fixed).
  Harness: <session-scratchpad>\gl2test\lyndonboot.ps1 (-renderer opengl1|opengl2).
- gl1 GROUND TRUTH (gl1truth_*.png): Phillips VISIBLE at placement, WITH hat. Torso pixels
  genuinely dark: meanRGB ~18, luma p10-p90 = 13-24. So "correct" brightness IS dark here —
  visibility comes from contrast, and gl1 delivers it.
- gl2 SAME BOOT FLOW same dll as yesterday's verify (18:42 parentEntity-fix build),
  gl2check_*.png: Phillips COMPLETELY ABSENT at placement (path behind him fully visible).
  User eyewitnessed both boots live: "he spawns in" (gl1) / "now he isnt spawning" (gl2).
- This boot's SKELROW: before==after EVERYWHERE (no writes) — BUT the one-shot probes burned
  their 6 frames EARLY: freeze thread ran after waitForPlayer, so he stood un-hidden at BSP
  spawn during the spectator wait and got probed there. Rig fix for next round: start freeze
  thread right after `level waittill spawn` (before waitForPlayer).
- Verdict: parentEntity fix did NOT close the latch. Yesterday's "writes 36-55 but invisible"
  and today's "no writes" are both post-fix boots — the latch varies per boot in WHERE it
  manifests. Next = SKELCLR (color source + first tess.color NaN check) + magenta flood
  (r_skeldiag>=7 override of tess.color in RB_FillModelLightingColors entity path) + rebuild.
  NOTE: rebuild now includes the fog agent's uncommitted globalfog work (bug-1132/1133 in
  buglog; dll built 18:53 never deployed) — fog verify (fogab.ps1) still pending separately.

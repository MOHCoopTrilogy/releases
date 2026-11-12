# Real reflections: study and costed recommendation (2026-11-11)

Read-only study. Nothing was built, launched, deployed or committed. Engine anchors are relative to
`H:\hzm_work\eng-hotfix13661\code\` (branch `rel-1.10.38-engine`), read on 2026-11-11.
**Every frame cost below is an estimate from reading the code, not a measurement** (no client was run).
"Mid-range GPU" means a GTX 1660 / RX 580 class card at 1080p.

## 1. Short answer

Most of the hard part is already in the engine and switched off:

- **Baked cubemap probes work on campaign maps** (auto-placed on AI pathnodes since bug-1237) but
  `r_cubeMapping` defaults to 0 and nothing that looks like glass samples them.
- **A planar water reflection exists** (`r_hzmWaterPlanar`, default 0, cold-water preset only).
- **No screen-space reflection exists anywhere.** Water and wet ground reflect a two-colour sky.
- Every window, rail, helmet, weapon finish and scope lens uses a fixed 2D picture slid around by
  `tcGen environment`. None of them shows the room or street the player is in.

Recommended first stage: feed the existing probes into the existing `tcGen environment` stages on
world glass and metal, in gl2 only, at draw time. No asset or map changes, no per-frame render cost,
gl1 keeps today's look. Details in section 5.

## 2. What the engine has today

| Feature | Compiled in | Default | Per-frame cost when on | Anchor |
|---|---|---|---|---|
| Cubemap probes (bake at map load) | yes | **off** (`r_cubeMapping 0`, latched) | none to bake; one cube lookup per lit pixel | `renderergl2/tr_init.c:1613`, `tr_bsp.c:4009` |
| Probe auto-placement on `info_pathnode` | yes | 16 probes, radius 1200 | none (map load) | `tr_bsp.c:2675`, `tr_init.c:1641-1642` |
| Parallax-corrected probe lookup | yes | sphere form; box form at `r_cubeMapping 2` | a few shader instructions | `glsl/lightall_fp.glsl:1146-1151`, `tr_glsl.c:1580-1585` |
| Live (per-frame) probe refresh | stubbed out | `if (0)` | six scene renders per probe | `tr_scene.c:836` |
| Planar water reflection | yes | **off** (`r_hzmWaterPlanar 0`) | one extra half-size scene render | `tr_hzm_water.c:692`, `:998-1050`, `:611-612` |
| Water pass (sky Fresnel, ripples, glint) | yes | on (`r_hzmWater -1` = auto) | one extra draw over allow-listed water | `tr_hzm_water.c:689`, `:835` |
| Wet ground film (rain) | yes | on (`r_hzmWet -1` = auto) | part of the lit world shader | `tr_hzm_wet.c:1-40`, `glsl/lightall_fp.glsl:620` |
| Stock mirror / portal view | yes | reachable, unused | one extra scene render per mirror | `tr_main.c:1443`, `:1810` |
| Scope lens pass (2D optics) | yes | on while scoped | one full-screen pass | `tr_hzm_scope.c:1-16`, `tr_backend.c:2645` |
| Scope picture-in-picture | yes | on while scoped | one half-size world view + rifle layer | `tr_hzm_lens.c:1-22`, `tr_backend.c:2540` |
| Scene depth as a texture | yes | used by SSAO, water contact | one depth copy when used | `tr_backend.c:3017`, `tr_image.c:3711` |
| SSAO | yes | off (`r_ssao 0`, latched) | half-size pass | `tr_init.c:1574`, `tr_image.c:3767` |
| Screen-space reflections | **no** | - | - | no `ssr` shader in `renderergl2/glsl/` |

Notes that matter for the options:

- **Probe sources.** `R_LoadEnvironmentJson`, then `misc_cubemap`, then `info_player_deathmatch`,
  then the HZM pathnode fallback (`tr_bsp.c:4012-4029`). On campaign maps only the last one fires.
  Probes are picked by farthest-point sampling, so 16 spread over the playable volume
  (`tr_bsp.c:2645-2674`).
- **Probe bake.** Loaded from `cubemaps/<map>/NNN.dds` if present (`tr_bsp.c:2909`), otherwise
  rendered at load: 6 faces per probe at `r_cubemapSize` 128 (`tr_bsp.c:2917-2932`, `tr_init.c:1614`),
  after terrain and static models exist (`tr_bsp.c:4078-4086`). 16 probes is 96 small scene renders
  at load and about 2 MB of VRAM (about 8 MB at 256).
- **Who samples a probe.** Only the lit-world program, only when `USE_CUBEMAP` is compiled in
  (`tr_glsl.c:1580`), weighted by specular reflectance (`glsl/lightall_fp.glsl:1139-1165`). With the
  fork's `r_hzmSpecular 0` (`tr_init.c:1741`) that weight is near zero, so turning `r_cubeMapping`
  on as it stands shows almost nothing and still adds a cube lookup to every lit pixel.
- **Who gets a probe index.** BSP world surfaces (`tr_bsp.c:2865-2895`, nearest probe to the surface
  centre, `tr_light.c:517`). MOHAA skeletal models, static models and terrain pass 0, that is "no
  probe" (`tr_model.cpp:1931`, `tr_staticmodels.cpp:626`, `tr_terrain.c:1504`). So guns, vehicles
  and characters cannot use a probe today.
- **`tcGen environment` in gl2** is a texture-coordinate trick in the generic program
  (`glsl/generic_vp.glsl:152-159`, parsed at `tr_shader.c:1789-1795`). It never reads a cubemap.
- **Planar water** mirrors the camera through one waterline height per map (`tr_hzm_water.c:607`,
  `:1032`), renders without viewmodel, cubemaps or sun shadows (`:1029`), and skips Omaha
  (`:1005`). Known defect: the oblique clip renders black in this fork, so it runs without it
  (`:1018-1021`); geometry below the waterline can therefore appear in the reflection.
- **Stock mirror path.** `R_MirrorViewBySurface` is live, but bug-4273 recorded that MOHAA treats
  `isPortal` as the portal sky and drops normal entities, which is why the water code sets
  `isPortal = qfalse` and `isMirror = qtrue` by hand (`tr_hzm_water.c:1027-1028`). The stock path
  is not usable for mirrors without that same workaround. Retail shaders carry only 9 `portal`
  keyword lines (in `common.shader` and `interior.shader`); no campaign mirror was found.
- **gl1** still ships (`renderer_opengl1.dll`). `renderergl1` has no HZM water, wet, scope or probe
  file (only `tr_hzm_demopip.c` and `tr_hzm_dynimage.c`). Everything here is gl2 only; gl1 keeps
  the fixed pictures.
- **Post chain order**: SSAO, lens composite, DOF, bloom, tone map, screen effects, scope, filter
  (`tr_backend.c:2477-2648`).

## 3. Which surfaces are involved

Method: a read-only sweep of the 17 retail `Pak*.pk3` files (main, mainta, maintt) and the shader and
surface lumps of the 54 campaign BSPs. Script kept outside the repo; counts are world BSP surfaces,
not models.

| Measure | Count |
|---|---:|
| Retail shaders | 7,041 |
| Retail shaders with a `tcGen environment` / `environmentmodel` stage | 155 (91 / 64) |
| ...of which named glass / window / lens | 65 |
| Campaign maps with at least one such world surface | 40 of 54 |
| World surfaces using them | about 4,500 of about 650,000 |
| ...glass and windows | about 1,900 |
| ...railway rails (`general_industrial/rrtieenv`, m2l2a/b/c only) | 1,981 |
| World surfaces whose shader is named glass / window at all | about 5,800 |
| World surfaces whose shader is named water | about 490, none with an environment stage |
| Mod shader stages with `tcGen environment` | 542 in 15 files |
| ...weapon finishes (`scripts/coop_skins.shader`, generated) | 492 |
| ...scope glass (`scripts/coop_scopeglass.shader`) | 3 |

What this says:

- The typical retail window is three stages: a fixed picture with `tcGen environment`, the window
  texture alpha-blended over it, then the lightmap (`textures/mohcommon/jh_window1` in
  `Pak0.pk3 scripts/mohcommon.shader`). The reflection slot is already there; only its source is fake.
- About two thirds of window surfaces (roughly 3,900) are plain painted textures with no reflection
  stage. They would need a new overlay rule keyed on the shader name, which is a later, riskier step.
- Heaviest glass maps: t2l4 (266), t1l3 (253), e1l3 (170), e2l2 (162), m5l3 (161), m5l2b (138),
  m5l1b (136), m4l2 (100). These are the test maps for stage 1.
- The 64 `environmentmodel` shaders are model skins (helmets, vehicles). They need the model probe
  index that does not exist yet.
- Stock BSPs cannot be recompiled, and nothing here needs it: probe positions come from the entity
  lump at load, and the surface-to-probe link is computed at load.
- Omaha (the five BSPs the engine already refuses by name, `tr.hzmOmahaWorld`) stays excluded from
  every stage, as the water and wet passes already do.

## 4. The four options

### (a) Baked probes sampled by glass and metal

- **Look.** Windows and rails show a soft, correct-colour picture of the street or room around
  them that shifts properly as the player walks. At 128 px per face it reads as a blurred real
  reflection, not a mirror. No moving things (soldiers, vehicles, muzzle flashes) appear in it.
- **Engine work.** About 250-400 lines, gl2 only.
  1. A bake-only switch so probes exist without compiling `USE_CUBEMAP` into every lit shader
     (gates at `tr_bsp.c:4009`, `tr_light.c:521`, `tr_shade.c:2613`, `tr_glsl.c:1580`).
  2. A cube-sampling variant of the generic program used for a stage whose `tcGen` is
     `TCGEN_ENVIRONMENT_MAPPED` when the surface has a probe (`tr_shader.c:1789`,
     `glsl/generic_vp.glsl:152`, bind as at `tr_shade.c:2613-2627`). The stage's own colour and
     blend stay, so each material keeps its strength and tint.
  3. Parallax correction reusing `u_CubeMapInfo` (`glsl/lightall_fp.glsl:1146`).
  4. Probe choice by the side of the pane the camera is on (see failure cases).
- **Frame cost.** One cube lookup on the affected pixels only: under 0.1 ms. Map load: 96 small
  renders, estimated 1-3 s once per map, removable by shipping baked `cubemaps/<map>/NNN.dds`
  files (`tr_bsp.c:2909`) generated offline.
- **Failure cases.**
  - Nearest-probe-to-surface can be on the far side of the wall, so an interior window reflects the
    street. Fix: keep two candidates per surface (nearest probe to a point pushed out along each
    side of the face normal) and pick by which side the camera is on.
  - Probes are baked once: the weather system can darken the world afterwards. Fix: scale the probe
    by the storm uniforms the water pass already uses (`tr_hzm_water.c:41`).
  - Only 16 probes; a long corridor map may show the wrong room. `r_cubemapAuto` raises the count
    without a restart (`tr_init.c:1641`).
  - `r_cubeMapping` is latched and needs GL 3.0 (`tr_init.c:518`). A changed value needs a renderer
    restart, which is a known crash from an open menu (bug-1181), so the new switch must be read at
    map load like `r_cubemapAuto`.
  - gl1: unchanged fixed pictures.
- **Menu.** Yes. A `P(...)` row beside Wet in Rain in `docs/tools/gen_menu_graphics.py:260`, `:380`,
  with the same "-1 = auto" pattern as `r_hzmWet`.

### (b) Screen-space reflections for water and wet ground

- **Look.** Water shows the actual quay, hull, lamps and far bank, moving things included, wherever
  the reflected thing is on screen. It fades at screen edges and cannot show what the camera cannot
  see (the underside of a bridge, anything behind the player).
- **Engine work.** Water: about 300-450 lines. Take a colour copy next to the depth snapshot the
  water pass already takes at its first batch (`tr_backend.c:966`, `:3017`), march the reflected
  ray in `glsl/hzmwater_fp.glsl` (16-24 steps), and fall back to today's sky and height-map march
  on a miss. Wet ground is harder: the wet film is computed inside the opaque lit pass
  (`tr_hzm_wet.c:33-37`), before the frame it would reflect exists. It needs either last frame's
  picture reprojected or a separate pass after opaque: about 500-800 more lines.
- **Frame cost.** Water: one half-size colour copy plus the march on water pixels, estimated
  0.3-0.8 ms with water on screen, zero otherwise. Wet ground over a whole street: 1-2 ms.
- **Failure cases.** Edge fade and missing off-screen content; shimmer on rippled water unless the
  march is jittered and filtered; MSAA needs a resolved copy (the depth snapshot already handles
  that case); the viewmodel can leak into the reflection if it is already in the buffer at copy time.
- **Menu.** Yes, as a level of the same row (Off / Probes / Probes + water).

### (c) Planar reflections through the mirror path

- **Look.** A true mirror image on one flat water level: exact, includes moving things, no edge
  fade. This is what the U-boat pen water was built for.
- **Engine work.** It exists (`tr_hzm_water.c:998`). Outstanding: fix the oblique clip
  (`:1018-1021`) so nothing below the waterline shows, about 50-150 lines in `R_SetupProjection`;
  extend beyond the cold preset if wanted (`:591`). A wall mirror would need a new surface hook,
  because the stock portal path drops entities in this fork; there is no retail mirror to serve.
- **Frame cost.** A second scene render at half size without shadows: estimated +30-50 % of the
  frame's CPU scene cost and +2-4 ms GPU while that water is in view. This engine is CPU-bound on a
  4-core machine, so this is the most expensive option per frame.
- **Failure cases.** One water height per map (`:607`); rippled water needs the image distorted in
  the shader; cost is paid whenever the water is visible, however small on screen.
- **Menu.** Yes (`r_hzmWaterPlanar` already exists), but it should stay a high-end choice.

### (d) Live low-rate cubemap around the player for the viewmodel

- **Look.** Scope lenses at the hip, polished finishes and bayonets pick up the real surroundings,
  including light changes and weather.
- **Engine work.** Two routes.
  - *Static first (recommended):* give first-person models a probe index (nearest probe to the
    camera, `tr_light.c:517`, into the zero argument at `tr_model.cpp:1931`) and reuse option (a)'s
    stage variant. About 80-150 lines on top of (a). Blend the two nearest probes so walking
    through a doorway does not pop.
  - *Live:* revive the dynamic path (`tr_scene.c:836`, `R_RenderCubemapSide` at `tr_main.c:3897`)
    for one 64 px probe at the camera, one face per frame. About 200-300 lines.
- **Frame cost.** Static: nil. Live: one extra small scene view each frame; the pixel cost is
  trivial but the CPU scene setup is not, estimated 0.5-1.5 ms.
- **Failure cases.** Static: no moving things, pops without blending. Live: each face is up to six
  frames stale; a 64 px face on a flat lens is only a colour wash, so the gain over static is
  small. All 492 finish stages are generated (`docs/tools/gen_skins.py`), so strength can be tuned
  in one place if finishes look too shiny with a real source.
- **Menu.** Yes, as part of the same row.

## 5. Recommended order

| Stage | What | Engine size | Frame cost | Visible win |
|---|---|---|---|---|
| 0 | Prove the probes on the release line | none (cvars on a test client) | - | none; it is a gate |
| 1 | Probes feed world glass and rails | 250-400 lines | under 0.1 ms | windows reflect their street or room |
| 2 | Probes feed the viewmodel, vehicles, helmets | 80-150 lines | nil | scope glass and finishes react to where you stand |
| 3 | Probe replaces the two-colour sky in water and wet ground | 100-200 lines | nil | puddles and canals reflect buildings, not just sky |
| 4 | Water screen-space reflections | 300-450 lines | 0.3-0.8 ms | moving things and lamps in the water |
| 5 | Planar clip fix; overlay rule for unreflective windows; live viewmodel cube | separate decisions | 1-4 ms | optional high-end extras |

Why this order: stages 1-3 share one piece of machinery (the baked probes) and cost nothing per
frame, which suits a CPU-bound engine. Stage 4 is the first one that spends frame time and is the
only way to get moving things into water short of the planar render. Stage 5 items are each
optional and independent.

How each stage is checked on screen:

- **Stage 0.** `r_cubeMapping 1` on a private test client on t2l4 and m5l1b; the load log must show
  probes placed and no "outside the lightgrid or inside a wall" warnings (`tr_main.c:3981`); the
  built-in probe viewer (`tr_backend.c:2815-2821`) must show a recognisable room, with terrain and
  props present. Record the added map load time. If the bake is wrong, stop here.
- **Stage 1.** Fixed-camera before/after stills at three windows each on t2l4, t1l3 and m5l3: one
  seen from the street, one from inside, one broken pane. Pass: the interior shot shows the room,
  the exterior shot shows the street, the reflection slides correctly in a short walk-past clip,
  and gl1 stills are byte-identical to today. Also the m2l2a rail yard for the rails.
- **Stage 2.** Hip-view stills of the scoped StG 44 and a polished finish, indoors then outdoors on
  the same map, plus a doorway walk clip to catch a pop. Aimed-view stills must be unchanged.
- **Stage 3.** Rain stills on m4l2 and m5l2b (maps bug-3406 measured) and the t1l2 water; no M3
  map is used, to stay clear of Omaha. Pass: a building edge
  is recognisable in a puddle, no new hard edges round objects (bug-3407's symptom).
- **Stage 4.** A clip on t1l2 water with a soldier walking the bank: the figure appears in the
  water, the reflection fades at screen edges without a hard line, and frame time with water on
  screen is logged against stage 3.

## 6. Open questions for the user

1. Is a soft, static reflection (no soldiers in the glass) acceptable for windows, or is moving
   content in glass a requirement? Moving content in glass is not affordable with any option here.
2. Should probes be baked at map load (1-3 s longer loads, estimated) or shipped as files (larger
   download, no load cost)?
3. Should the roughly 3,900 painted windows with no reflection stage be given one (stage 5), or
   left as the map authors drew them?

## 7. Things this study did not do

- No frame times or load times were measured; all are estimates.
- The probe bake was not run on the release line; bug-1237's fix dates from July and predates the
  weather, cloud and water work, so stage 0 may find new problems (for example clouds or storm
  state captured in the probe).
- Model shaders (`environmentmodel`, 64 retail) and static-model glass were counted by shader, not
  by placed instance.
- `m3l2` appears in the surface sweep (79 glass surfaces); no judgement was made about whether it
  counts as Omaha for the engine's exclusion list. The engine's own list decides.

## 8. What was built (2026-11-11, same day) and what was measured

Engine commit `95ccd08a` on `rel-1.10.38-engine`, mod commit `775eebd3`. Not deployed, not released.
Stills: `stills/`. Runner and spot finder: `tools/reflect_run.py`, `tools/spots.py`.

- **Setting.** `r_hzmReflect`: -1 auto (= 1), 0 off, 1 probes, 2 probes + mirrored view. Menu:
  Post-FX, ATMOSPHERE page, REFLECTIONS, "Real Reflections" (Off / Real / Real + You). It is not on
  Advanced Graphics because that sheet has no free row and its generator table no longer matches the
  shipped sheet (bug-11014). Off <-> on applies at the next map load; Real <-> Real + You is live.
- **Stage 0 found two defects in the probe bake**: 23 of 24 probes sat on one point (bug-11009), and
  the stock `R_inPVS` crashed the client (bug-11010). Both fixed or avoided.
- **Stage 1 as built** differs from section 4(a) in three ways. gl2 folds a window's env stage and
  lightmap stage into one lit stage, so the hook is in both draw paths (bug-11011). The pane's
  lightmap is not multiplied in. Parallax is a ray against a 600-unit sphere, not the stock shortcut.
- **Own reflection as built**: one mirrored half-size view a frame for the nearest flat glass pane
  within 320 units that the camera faces; panes on that plane show it, fading into the probe over
  the last 40 % of the range. cgame submits a mirror-only copy of the player's body.

Measured on this machine, m5l1b, 1600x900, frame cap off, median of one-second means (run `r17`):

| Where | Off | Real | Real + You |
|---|---:|---:|---:|
| 86 units in front of a pane | 1.47 ms | 1.51-1.55 ms | 3.88-4.01 ms |
| Street, no pane in range | 1.21-1.38 ms | 1.23-1.24 ms | 1.26-1.33 ms |

So: probes cost nothing measurable per frame; the mirrored view costs about 2.5 ms while a pane is
in range and nothing otherwise. That 2.5 ms is a whole second scene, so it scales with the scene,
and on a busy coop map it will be more. Map-load cost of the bake was not timed.

Verified on screen (stills QA'd by me): window glass off / probe / mirrored view at three angles on
m5l1b; the player's body in the pane; a metal rail on m2l2a off / probe. The cube lookup convention
was proven against its opposite (`r_hzmReflectDbg 128`).

Not verified, or known weak:

- **Water: not delivered.** The water pass showed no reflection at all in the single-player test
  client, with its planar view on or off and with `r_hzmWater 0`, so nothing about water could be
  judged. The water's planar view stays on its own switch (`r_hzmWaterPlanar`, default 0). Its clip
  plane pointed the wrong way (bug-11012, fixed, unseen on water).
- The probe picture is soft and approximate: one 128 px cube up to several hundred units away. At a
  grazing angle it can show sky where the mirrored view shows ground.
- The body in the mirror has no rifle (the gun belongs to the first-person rig) and is absent while
  scoped, prone, on a turret or in cover.
- Only one map was walked. No coop server, no second player, no AI in a pane, no storm, no Omaha
  refusal check, no gl1 check, no menu screenshot.
- The retail window frame stage is unlit in gl2 (cream mullions glow at night). Pre-existing.
- A red dotted arc appeared in one probe still and not in the retake; it looked like a HUD element.

## 9. Interiors behind windows (user idea, 2026-11-11) - costed note, nothing built

Idea: windows on buildings nobody can enter should look as if a room is behind the glass, under the
reflection. Estimates below are estimates.

**Approach: interior mapping in the fragment shader.** From the window plane, intersect the view ray
with an imaginary box (floor, ceiling, back and side walls) and sample a room texture at the hit.
One draw, no extra geometry, about 20 shader instructions and one texture read. Estimated cost under
0.1 ms. It fits in the program this work added: interior first, then the Fresnel-weighted probe or
mirrored view over it.

- **Variation.** A hash of the window's world position picks one of N rooms, mirrors it, and decides
  lit or dark. Night maps get a small share of lit windows; the share has to be a per-map number.
- **Art.** Either 6-8 small room cubemaps or one atlas of wall / floor / ceiling tiles with two or
  three props baked in. It must be made by us (render simple rooms offline); nothing from disc
  assets. At 256 px a face it is about 3 MB. This is the part that decides whether it looks good:
  rooms seen through dirty glass at night can be very plain, but they must not look pasted on.
- **Which surfaces.** Two groups, very different in risk:
  1. *Glass that already has an env stage* (about 1,900 surfaces, the ones this work touches). The
     glass area is already separate from the frame, so no mask is needed. Estimated 150-250 lines.
  2. *Painted windows* (about 3,900). The texture is one opaque picture with frame, shutters,
     curtains or broken panes painted in. There is no alpha for the glass, so each texture needs a
     mask: derived (dark, low-saturation regions inside a frame) and then checked by eye, or drawn
     per texture. Roughly 230 window-named shaders with no env stage; a few dozen textures cover
     most surfaces. Estimated 2-4 days of mask work and review, plus 300-500 lines.
- **Choosing per surface.** A shader-name rule is cheap but wrong for windows that open onto real
  rooms. A load-time test is better: trace a short ray inward from the pane centre (the collision
  model is available at load) and treat the window as fake only if it hits solid within about 32
  units. That also leaves real see-through windows alone, as the user asked.

**Alternatives.** A flat parallax-offset room picture (cheaper art, falls apart at an angle). Real
box geometry behind each window (impossible: stock BSPs cannot be recompiled, and brush entities per
window would cost entities and draw calls). Dark glass with a faint lit-curtain picture for a share
of windows (very cheap, no depth, good enough at night).

**Risks.** Masks for painted windows are the main cost and the main way it goes wrong. Shutters and
doors named "window" must be excluded by the mask or a name list. The map authors' look changes on
every building at once, so it needs its own level on the same row (Off / Real / Real + You /
+ Interiors) rather than riding the default. Omaha excluded as everywhere. gl2 only.

**Recommendation.** Worth a prototype on group 1 only: it is small, needs no masks, and the 1,900
panes are exactly where the reflection now draws attention to the flat glass. Group 2 should wait
for that prototype and a look at the mask problem on one building. Not started: one window on t2l4
or m5l3 with stills at two angles, a walk-past clip and a measured frame cost is the next step.

## 10. Second round (2026-11-11, evening): water found and fixed, rooms behind glass, mask samples

Engine commit `53fb4bf5`. Not deployed. Supersedes the "Water: not delivered" line of section 8.

**Why the water pass showed nothing (bug-11021).** Commit `f8f8ff40` (2026-10-26, moving wave sheets)
made the pass send the current orientation's transform matrix to the water shader. The world has
none: `R_RotateForViewer` clears `tr.or` and fills `modelMatrix` only; `R_RotateForEntity` is the one
writer (`renderergl2/tr_main.c:581`). So every BSP water surface got a zero matrix, a zero normal,
and the shader's first test threw the fragment away. Since that commit only water drawn by an entity
showed the improved look; world water drew its retail stages.

Evidence: the pass gate passed all along (`fade=1.00 ready=1`, run `r19`); the picture did not change
with `r_hzmWater` 0, body x10 or the bypass (`r20`); the shipped renderer of 2026-11-11 05:32 behaves
the same (`r21`), so it is not from this work and not about single player, settings or the renderer
choice; with an identity matrix for the world the water appears (`r22`, `stills/water_pens.jpg`).
This also explains the canal the user saw as a flat blue texture. The water's mirrored view was also
repaired (clip plane, bug-11012) and now runs at Real + You.

Measured on m2l2a, 1600x900, cap off, facing the pens (`r24`): Off / Real 5.5-6.0 ms, Real + You
9.8-9.9 ms (+4 ms, 100 fps); open water with nothing to mirror +0.13 ms. The cost of the repaired
water pass on its own was not separated out.

**Rooms behind glass (built).** Every flat upright glass pane with separate glass gets a room that
exists only in the shader (`glsl/generic_fp.glsl` HzmRoom): no texture, no geometry, nothing from
disc assets. Per pane, from a hash of its position: room size, wallpaper, a door or cupboard, a
picture, side or closed curtains, and at night a lamp in a share of rooms. On under Real and
Real + You; `r_hzmReflectRooms 0` turns it off live. m5l3: 125 of 145 panes; m5l1b: 112 of 112.
Cost (m5l3, two large panes filling the view, `s3`): 1.28-1.30 ms off, 1.41-1.50 ms on.
Stills `stills/rooms_*.jpg`, clip `stills/rooms_walkpast.gif`.

**Also changed.** 48 probes (bake measured: 182 ms for 48 on m5l1b, 82 ms for 24 on m2l2a), cube
read unblurred. In daylight the probe now reads as a recognisable sky and street
(`stills/rooms_angle.jpg`, middle frame).

**Painted windows: mask samples, nothing applied.** `masks/_sample_sheet.jpg` (tool:
`tools/masks.py`). Of eight textures the automatic mask is usable on two (plain dark glass); it
fails on windows with curtains or light painted in and on textures that are dark all over. So masks
need a per-texture decision, and painted lit windows should get no room at all.
Correction to sections 3 and 9: the earlier counts matched "panel" as "pane" (bug-11023). Window-
named world surfaces without separate glass, non-Omaha campaign maps: 2,909, of which 1,390 are one
alpha-masked frame texture (`mohcommon/window32_p1`) that needs its own look before anything else.

**Still not verified.**
- No co-op server, second player or AI was in any view. No storm. gl1 and Omaha untested.
- Rooms were looked at on two maps only. On the night map no lit room happened to be in frame, so
  the lamp was seen only in the debug view.
- A pane whose texture does not repeat once per pane would get a room cut in the wrong place; none
  was seen, none was searched for.
- Metal: the only env-mapped metal found on screen is dark girders (`stills/metal_girder.jpg`); the
  change is visible but it is not a showcase.
- Small green specks in the mirrored water are the player's own body floating in the fly camera.
- The red dotted arc of section 8 is the HUD's hit-direction mark (AI firing at the test player).

## 11. Water: one look, and water that does not stop (2026-11-11 night)

Engine commit `7682500b`. Not deployed. Audit: `WATER_AUDIT.md` (generated by `tools/water_audit.py`).

**One look for all water (user: the U-boat pen sea, "It looks the best of all").** Every allowlisted
water shader on every non-Omaha map now gets the cold-sea preset: sea, shoreline, canal, river, pond,
dock. Decisions made on the way, for the user to overrule:

- Frozen rivers stay ice. The Omaha maps keep exactly the presets they had.
- The ice plates along quay walls stay on the four maps the preset was made for (m2l2a/b/c and the
  lobby copy); they are not spread to other maps.
- Swell and chop scale with the area a water shader covers, so a pond or canal is calm
  (`stills/pond_looks_m4l0.jpg`, `stills/pond_m4l0.gif`). The colour is the same everywhere.
- This preset is opaque by design, so the bed and what stands in the water are not seen: the "more
  depth" request for the Sealed Orders canal is met by the preset itself, not by new code.
- Side by side with the harbour look on a pond and a canal: `stills/pond_looks_m4l0.jpg`,
  `stills/canal_looks_m3l2.jpg`. On the pond the harbour look lets the stock tiles show through.

**Water that does not stop (bug-11030).** Two causes. Most of what was seen was the dead water pass
(section 10): the retail sheet is not fogged, so its corner stood out against the sky
(`stills/uboat_cutscene_m2l2b.jpg`). The second is real: on open maps the water brush ends inside
the view (`stills/sea_extension_m1l3c.jpg`, middle frames; `stills/sea_extension_others.jpg`).
Fix, in the renderer, no map edits: when the map's main water body reaches the edge of the map, one
sheet at the waterline is drawn out to the far plane with the same water look.

- Inside the map it is drawn only where the sea reaches: the top-down height grid is flood-filled
  at map load from the real water through open or submerged cells. A dry dock, or a street below
  sea level behind a wall, stays dry. Land hides it by depth like anything else.
- Shorelines: the real water and its shore sheet draw over it; the plane sits half a unit lower.
- The skybox's painted sea is covered below the plane's horizon; above it the sky is untouched.
- Fog and far plane: the sheet is fogged like the water itself and fades out over the last 12 % of
  the view distance, so its end is never a line.
- Rule for which maps (generated, see the audit): 15 campaign maps qualify; a canal inside a town
  or a pond never does. `r_hzmWaterFar 0` turns it off live.
- Cost, m1l3c looking out to sea, cap off (`x_m1l3c_perf`): 1.52-1.70 ms on, 1.53-1.54 ms off.

**Reflections on water.** At Real + You the mirrored view now serves the level with the most water
on any map (it was the pens only). The cheaper "baked snapshot" route (water reading the probes
instead of the two-colour sky) is not built.

**Not verified / known gaps.**
- A still per map was attempted for all 15 (`H:\hzm_work\reflect\wm_*`). Usable: m1l3c, m2l2a,
  m2l2b, m2l2c, plus m4l0 and m3l2 for the look. On e1l3, e1l4, t1l3, m5l2b the test player is
  locked in a scripted ride, and on the rest the automatic camera landed outside the map, so those
  maps are unseen. t1l2 and t1l3 (bridge and rowboat) were only seen at night, where on / off look
  alike.
- The plane is drawn only in a view that already shows some real water.
- The converted Sealed Orders canal was not loaded in this client.
- No co-op server, no storm, no gl1, no Omaha refusal check.
- River water in daylight was not seen at all.

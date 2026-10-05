# Water reflections + wet ground: three user-reported defects (2026-10-05)

User report: reflections "only seem to work in some areas of maps"; around the edges of objects they "perfectly cut
off at angles"; water on the ground "sometimes looks too white/obvious".

What shipped in v1.10.3 (plan in `../water_wetness_2026-09-27/`): there is **no SSR and no probe**. Both the water pass
(`glsl/hzmwater_fp.glsl`) and the wet film (`glsl/lightall_fp.glsl` HzmWet) reflect a two-colour fogged SKY
(zenith/horizon), gated by a top-down 8 u max-height "rain-occlusion" raster (`tr_hzm_wet.c`).

## Causes (from the code, confirmed on the captures)

1. **Only some areas.**
   - Wet ground: exposure was ONE bilinear tap of the 8 u max-height raster with a sharp compare. Any cell whose centre
     falls under a wall top, roof, curb or crate reads that height, so a dry strip hugged every object, and anything
     overhead at any height killed the reflection outright. Puddles came from a single 170-680 u noise band at 25 %
     coverage: 3-12 m sheets in some streets, none in others.
   - Water: the water pass tested a Gaussian-blurred (sigma 48 u) copy of the same HEIGHT map straight up. Blurring
     heights lifts every bank and quay wall over the water beside it, so reflections died along canals and banks and
     survived only in open water. (Shader eligibility is not the cause: offline, 85-97 % of the up-facing world area on
     m5l1b, m4l2, m5l2b and t1l2 collapses to lit lightall stage 0 - `wf_cover.py` in the scratchpad.)
2. **Hard angular cut-offs.** The same one-tap sharp compare: the sky sheen ran at full strength up to a ruled line
   that traced each object's outline in 8 u steps; and the wet sun/moon glint used `1 / (4 n.v)`, which grows without
   bound on any face seen edge-on - the bright white lines along the m4l2 rock slab top, the m5l2b bank crest and the
   m5l1b rubble mound.
3. **Too white.** The film and puddles mirrored the raw fogged horizon colour (near white on overcast/fogged maps)
   with no relation to the light at that spot, plus a 0.45 "lightmap sheen" and a 1.5-capped glint; wet albedo
   darkened only to 0.60-0.72 and lost saturation in the mix.

## Fixes (renderer + GLSL only; gl1, cgame, mod data untouched; Omaha still refused by name)

- **Exposure, 5 taps** (lightall): floors average five taps on a 15-41 u ring whose rotation/radius follow a smooth
  world-space jitter, half-way to their max (a strip not under anything stays wet); walls march the 20 deg rain ray
  (5 taps, min). Irregular rain shadows feathered over ~60 u; no ruled lines.
- **Reflection-ray occlusion with a fallback** (both): the reflected ray is marched through a BLURRED copy of the
  height map (wet: 36/150 u, jittered; water: 40/140/380 u, a quarter of the ripple tilt), compared against the
  blurred height under the pixel itself (so a wall's blur lift does not block rays pointing away from it). A blocked
  ray shows a dim stand-in for the mirrored scenery (wet 0.5 x sky, water 0.55 x horizon x local lightmap), never
  nothing. The occlusion texture is RG16: r = sharp heights (exposure), g = half-res 2x2 mean + Gaussian sigma 40 u.
  The v1.10.3 water-only soft map is deleted.
- **Bounded glint**: Smith-Schlick view+light masking replaces `1 / (4 n.v)`, which blew up on faces seen edge-on -
  the white line along the m4l2 rock slab. Film Fresnel gets Smith view masking too (puddles keep their mirror).
- **Realistic wet look**: darker (generic 0.62, porous 0.55, wood 0.66) and +30 % saturated albedo; reflected sky
  clamped to 0.04 + 0.45 x the baked light's luminance and x0.8; lightmap sheen 0.45 -> 0.25; glint x0.35 (was
  0.5), cap 0.8 (was 1.5).
- **Puddles**: zones (170-680 u) mixed 40 % with a 73-146 u detail band, 20 % coverage (was 25 %), wider
  footprint-filtered rim, a soaked darker halo, noise fetch bias -1 (detail keeps its shape far off).
- **Test view**: `r_hzmWetDebug 1` (flags 0) paints eligible pixels red = sheltered, green = exposed with sky
  reflection, blue = puddle.
- Fetches per wet pixel 5 occlusion + 2 ray + 1 noise = 8 (was 5 + 1); per water pixel 4 (was 1).

## How it was found and tested (4 batched slot runs - `waterfix_run.py`)
Private client `G:\mohaa-wwtest` with the live v1.10.13 set (exe d23dd662, cgame d563b759, game 6f68255a). BEFORE gl2
= the live flip DLL (md5 16b8534d, sha256 731f1ad5). AFTER = final gl2 **md5 1d932269, sha256 74c4b145**. Coop rain
held dry, wetness forced to full (film 1, puddles 1), identical camera poses, MSAA 8x (+ canal at MSAA off).
- Run 1 (c3ece61b): the first fix drew a NEW ruled rectangle on the m3l2 canal (sharp-map ray taps).
- Run 2 (3311395c): blurred ray channel; reviewer: dark bands at building bases, near-black river edge, slab line kept.
- Run 3 (53be8798): 360-degree sweeps (6 deg steps) at 21 spots on m3l2, m5l1b, m4l2, t1l2, m5l1a, m5l2b, BEFORE and
  AFTER, every-frame contact sheets (`sweep_sheets.py`) - this is where the clear defect spots came from.
- Run 4 (1d932269, final): the defect spots again + stills, GPU, canal pan.

## Evidence (`evidence/`, final build)
- **Angled white lines at object edges (complaint 2), gone:** `m4l2_night_slab_line.jpg` + `_pan.gif` (rock slab
  top), `m5l2b_river_bank_line.jpg` + `_pan.gif` (bank crest), `wet_day_*` (rubble mound rim).
- **Chalky white puddle sheets (complaint 3):** `m3l2_white_sheet.jpg` + `m3l2_white_sheets_pan.gif` (courtyard);
  `wet_day_P_before_after.jpg`, `wet_night_P_before_after.jpg`.
- **Water:** `canal_W/P/F_before_after.jpg`, `canal_pan_before_after.gif`, `canal_P_msaa8_vs_off.jpg`.
- `*_debug_coverage.jpg` (`r_hzmWetDebug 1`); `gpu.md`.
- **GPU (GPUTIME main pass p50, feature on minus off, same pose, 8 s each):** final AFTER -0.05 / +0.04 / +0.03 ms
  (canal / wet_day / wet_night), BEFORE -0.35 / +0.01 / +0.63 ms in the same run. Run-to-run noise is ~0.3 ms:
  no measurable cost change, but the noise is larger than the fetches added.

## Not fixed / left as is
- **Complaint 1 is only partly shown.** Measured offline, the v1.10.3 soft-map dead zones were small (8 % of open
  water on m3l2, ~0 elsewhere); the visible "only some areas" causes found are the one-tap strips/sheltering, the
  puddle zones, and shader eligibility. Not changed: deform water and blended `nextbundle` decals (m4l2
  `ties_decal`, the railway ties) are drawn by gl2's generic program and never get wet; static models and brush
  entities stay dry (by design).
- The soft white ORB above the far end of the m4l2 track in some GIF frames is the watchtower SEARCHLIGHT's glow (the
  map's own sweeping `global/spotlight.scr`), not the waterfix: at one fixed pose it shows in BEFORE and AFTER alike,
  with wetness off and on, depending only on where the sweeping beam points at capture time
  (`evidence/m4l2_orb_is_the_searchlight.jpg`, 6 same-pose captures from runs 2 and 4).
- m4l2's blue "frost" on the ballast is the DRY moonlit look (dry RGB 62/83/104, wet 45/63/81) - not the wetness.
- m3l2 courtyard: faint grey puddles remain (now darker than the dry ground's sky glare, not white).
- The flip guard applies: `publish_release.ps1` ships a flip-marked renderer_opengl2.dll only if its sha256 is in
  `docs/tools/gfx_flip_gate.json`; the release build's hash must be recorded there.

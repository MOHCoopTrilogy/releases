# Weapon HD textures: audit, pipeline, pilot (2026-10-05)

**Status: PHASE 1 (audit + pilot). Nothing deployed, nothing committed, no shipped file changed.**
Staged under this folder only. The one repo edit is the harness registration line in
`docs/tools/harness_guard.py` (`G:\mohaa-weaponhd`, slot "weaponhd"), which the harness rules require.

## 1. What draws a weapon (the facts the plan rests on)

- **First person and third person use the same weapon TIK and the same texture.** There is no separate
  view-model skin. The weapon is its own entity attached to the player; in first person cgame re-parents it onto
  the FPS hands (`cg_modelanim.c`, the tag_weapon_left/right whitelist, see bug-2241), and both views copy the
  entity's surface bits (`cg_modelanim.c:3435`). So "1P and 3P match" holds by construction. AI soldiers,
  dropped pickups and the `_lite` TIKs use the same sheet too. The reload magazines (`models/ammo/colt_clip.tik`,
  `thompson_clip.tik`) and `static_kar98` also paint from the gun's sheet, so they follow automatically.
- **Image precedence** (TRAPS T6): `.dds` first, then `.jpg`, then `.tga`. Within one extension the last pak in
  sort order wins. The pak name must beat every pak that holds a weapon sheet today. That includes
  `zzzzzzzzzz_coop_hd_m3l1a.pk3` (the Omaha pak), which wins **14 weapon sheets on every map**: m1clip, s93_bar,
  mg42, bazookashell, 30cal_crate and others. `zzzzzzzzzz_coop_hd_weapons.pk3` (10 z) sorts after it
  (`w` > `m`) and after `_hd_a_tilefix`/`_hd_skies`, and before `_tileart`/`_m3l2ground`/`_loadart`. None of those
  three holds a weapon sheet. **The Omaha pak is not modified**; the new pak just out-sorts it for weapon paths.
- **gl2 normal/specular maps do not work on weapons.** gl2 auto-loads `<diffuse>_n` / `_s`, but skeletal meshes
  write no tangents. A normal map on a gun would be rotated by a garbage basis (measured during the generated-
  normals work, comment at `autoexec.cfg:1682+`). `r_specularMapping` also ships 0, because MOHAA has 39 diffuse
  textures named `*_s` (bug-1155). **So all detail goes into the diffuse.** Real relief would need tangent output in
  the skeletal draw path, which is an engine change and is not proposed here.
- **Alpha:** none of the pilot sheets uses alpha (measured: HRRTM DXT5 alpha is 255 everywhere), so the output is
  **DXT1**. That is half the VRAM per texel of today's DXT5.

## 2. Inventory

The full table is generated: **[AUDIT_TABLE.md](AUDIT_TABLE.md)**, by `tools/inventory.py` and `tools/audit.py`.
They resolve TIK -> shader -> image with the engine's own precedence rules, read-only against the install.
It covers 72 base weapon TIKs with 178 sheet rows, their skin variants and their finish counts.

| status of a base sheet | sheets | meaning |
|---|---:|---|
| HD (HRRTM) | 21 | Real high-resolution retexture, photo-sourced, with real markings. The lossless TGA source in `HRRTM_Pak4c` is 1280-1792 px; what ships is a 2048 DXT5 resample. Kar98, Garand, Thompson, Colt, MP40, StG44, P38, Springfield, Panzerschreck, shotgun, BAR source. |
| 4x upscale in the Omaha pak | 14 | `hd_m3l1a`'s Real-ESRGAN 4x (2048 DXT1), applied globally |
| AI/upscale pak (hdmem / dds_override) | 18 | Third-party 1024 sheets (Italian/British/minedetector set, PPSh, Webley, DeLisle) |
| 1024 native | 11 | xw imports (Arisaka, Luger, Type 100, Thompson 50), DP-28 |
| **LOW (<= 800)** | **113** | Mostly the xw imports (Carbine 6 sheets at ~500, Sten, Grease Gun, PPK, Welrod, the S93 silenced set, scopes), retail Enfield/G43/Mosin/SVT at 512, FG42 512, Johnson/M10/C96 at 640x480 non-POT |

Variants:
- **Finishes:** 7 per gun. Gold, chrome and blued are shader stages over the base diffuse, so they **inherit the
  HD base for free**. Bloody and the 3 camos are baked: 437 files, 24 MB, mostly **128-620 px**. In the full set
  these must be re-baked from the new HD bases (`docs/tools/gen_skins.py` / `bake_skins.py`), or a camo gun will
  look far softer than its plain twin. Recommended cap: 2048.
- **Skin variants** (`coop_v3/*`, `coop_*`, Hobbs/Guan/LV/DH packs): 512-1600 px, about 60 sheets. They are
  distinct art, so they get the same upscale + wear pass, each with its own seed.
- **Stray file:** `models/weapons/p38 - Copy.tik` comes from the third-party `HRRTM_Pak4_Weapons.pk3`, not from our
  paks. It is harmless and left alone (bug-3378). The table lists it as `p38 - copy`.

## 3. Pipeline (`tools/weaponhd.py`)

1. **Source = the best lossless art on disk.** HRRTM's Pak4c TGA where it exists. Never the shipped DXT5. Upscaling
   block-compressed art also upscales the 4x4 block artefacts.
2. **Real-ESRGAN x4plus** (the project's own `_tools/realesrgan`, the same recipe as `upscale_vehicles.py` /
   `upscale_m3l1a.py`), then Lanczos down to the target. ESRGAN removes the source's JPEG crosshatch and sharpens
   edges and real markings. **Hallucination guard:** where ESRGAN departs from the source's own Lanczos picture by
   more than a soft threshold, the pass falls back to sharpened Lanczos. It caught the Colt rear-sight serrations,
   which ESRGAN had turned into crackle (the bug-1129 worm-noise family); about 4% of Colt texels fell back.
3. **Masks from the real mesh** (`tools/skd.py` reads the SKD): UV coverage, CONVEX edges (dihedral > 28 deg,
   outward-tested against the authored normals) for edge wear, and CONCAVE edges for grime. Material (steel / wood /
   bakelite) comes from source colour, with per-gun overrides. No wear lands outside a UV island.
4. **Material micro-detail:** ESRGAN flattens metal into plastic, so material is added back. Blued gets a fine
   polish grain with a blue-black bias. Parkerized gets a coarser, matte, slightly grey-green phosphate speckle.
   Wood gets pores streaked along the local grain direction (structure tensor). Bakelite gets nothing.
5. **Wear**, seeded per gun so every gun differs and a re-run is identical:
   - edge wear broken into chips to bare steel, never a continuous outline (a first try drew wire outlines; caught in QA)
   - contact zones per gun: thinned plum-brown bluing at the bolt, hand-oil darkening on stocks and wrists, polished bakelite
   - holster wear on pistols
   - short scratches biased along the part
   - wood dents and edge rub
   - oil and grime in concave corners
6. **No text or markings are generated.** HRRTM's real markings ("COLT'S PT.F.A.MFG.CO / HARTFORD,CT.U.S.A" and
   the patent dates, "AUTO-ORDNANCE CORPORATION") are kept.
7. **DDS DXT1 with a full box-mip chain**, using the project's deterministic mean-holding BC1 encoder
   (`gen_terrain_pak_v4.bc1_encode_dc`, bug-2953), not Pillow's.
8. **Gates, which fail loudly:**
   - luma correlation vs source >= 0.90
   - mean brightness shift within 6%
   - no NaN
   - ESRGAN black-output guard (bug-247)
   - decoded DDS mean within 1.5 levels of level 0

Period finishes used in the pilot:
- **Kar98k:** blued receiver with walnut-tone stock. The art is HRRTM's laminate/walnut photo; colour is not changed.
- **Thompson:** the art carries "M1A1" markings, so parkerized, with a walnut stock.
- **Colt:** M1911A1, so parkerized, with brown plastic grips treated as bakelite, not wood.

## 4. Per-instance variation ("unique even if it randomizes")

Mechanisms found in this engine:
- **(a) Per-surface skin rows.** A TIK surface can carry up to `MAX_TIKI_SHADER` = 8 shader rows. The renderer
  draws row `skinNum + MDL_SURFACE_SKININDEX(surface bits)` (both renderers, `tr_model.cpp`). The 3-bit per-surface
  index is already networked and already used: the armory glove (bug-2080) and finished reload magazines (bug-2241).
  Weapons use no skin bits today; finishes are whole-TIK swaps.
- **(b) entityState.skinNum.** Also networked and added to the row, but `CG_ModelAnim` does not copy it, so using it
  needs a cgame change. Not recommended.
- **(c) A gl2 shader that blends a wear mask by an entity seed.** gl2 only, needs GLSL + uniform work, and gl1 would
  differ. Rejected.

**Recommendation:**

**Tier A (ship first, no code).** One unique, seeded wear per gun, baked into the HD diffuse. This is the pilot.
Every gun model looks individually worn. All instances of that model look alike.

**Tier B (optional, needs approval: game.dll + TIK rows).**
- Content: add 2 extra wear rows per main sheet (`surface KAR981 shader KAR98 shader KAR98_w1 shader KAR98_w2`).
- Code: about 30 lines in game.dll. In `Weapon::AttachToOwner`, set that weapon entity's surface skin bits to
  `hash(owner name + weapon class) % 3` (per-player persistent: "your" rifle always looks like yours). Or seed it
  by entity number for pure randomness.
- Because 1P and 3P draw the same entity, they always agree.
- Cost: download +2 x 2048 DXT1 per gun (about 5.6 MB per gun). VRAM is paid only for variants present on the map.
- Variants at full 4096 would cost +22 MB per gun, which is not worth it.
- The 2x-modulate overlay idea was rejected: modulate cannot lift near-black bluing to bare-steel bright (it is
  capped at 2x), and an additive stage would glow in the dark.
- It must be checked against `CoopClipFinishIndex` (bug-2241). That stamps the attached magazine, not the gun, so
  there is no conflict, but the gun's own Clip surface would show the variant.

## 5. Pilot results

See the report section at the end of README.md (filled in after the build and the in-engine run).

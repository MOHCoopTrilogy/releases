# Gun repaint 2026-10-13 - the first three shortlist items (all metal, painted by script)

Shortlist and cost notes: `../gun_sources_2026-10-13/REPORT.md` sections 4 and 5. Everything here is STAGED
(`assets/` mirrors game paths); nothing in the mod tree or in `docs/tools/assets/fixes` was touched.
Meshes, UVs, tiks and shaders are unchanged - only texture files.

## State

| # | item | state |
|---|---|---|
| 1 | shared silencer sheet `colt45s2` (six guns) | **DONE** - staged, seen in the engine on all six guns |
| 2 | M3 grease gun `greaser` | not started (UVs looked at - see "Grease gun: what the layout allows") |
| 3 | pump shotgun receiver top | not started |

## 1. Silencer - `tools/silencer.py`

* Users (grep of the winning shader + tiks, `tools/shgrep.py`): shader `colt45s2` (scripts/american_weapons.shader,
  zzzzz_xw_weapons.pk3) on surface `Cylinder1` of `colt_silenced.tik`, `berettasilenced.tik`, `garand_silenced.tik`,
  `greasegun_silenced.tik`, `kar98snipersilenced.tik`, `nagant_snipersilenced.tik`. The six skds carry identical UVs
  and triangles on that surface (asserted by the generator). None of the six has finish tiks (no bloody / camo /
  blued / chrome / gold variants exist for them) - nothing to re-bake.
* Wins today: `textures/models/weapons/colt/colt45s2.tga`, 320x240, zzzzz_xw_weapons.pk3 (the only copy in any pak;
  the engine holds it as 256x128 DXT1a). Staged: `assets/textures/models/weapons/colt/colt45s2.dds`, 2048x2048 DXT1 +
  mips, 2.8 MB. A `.dds` of the stem beats the `.tga` from any pak, so it wins from the fixes pak. Proof:
  `evidence/silencer_imagelist_before.txt` / `_after.txt`.
* Paint: no source pixels at all. The two half shells are planar projections, so everything is painted in tube
  coordinates baked from the mesh (continuous across both seams). Dark blued steel, lathe lines, broken sheen on
  both shells (the six guns mount the tube with different roll), joint groove + knurled cap at each end, worn muzzle
  rim, muzzle face with turning rings, recess step, bore and soot.
* Run: `python tools/silencer.py --preview` (85 s, the DXT encode). `--draft` = previews only, no asset.

## Engine stills - `tools/run_rp.py`, `tools/mkov.py`, `tools/sheet.py`

Harness `G:/mohaa-hudfeed3` (slot hudfeed3, port 12741), the RELEASED binaries copied from the GOG root under their own
names (`openmohaa_rel1013.exe`, `games/game_rel1013.dll`, `cgames/cgame_rel1013.dll`, `renderers/gl2_rel1013.dll`); the
harness root's previous `game.dll` / `cgame.dll` / `renderer_opengl2.dll` are kept beside as `*.pre_repaint` and put
back after every run. Overlay = the double-barrel lane's `build/ovbase_cur.pk3` (plumbing on the deployed weather.scr)
+ a test-only prop spawner + the staged files. `before` = plumbing only.

Runs (moved to `H:/hzm_archive/repaint/<run>/`, file counts checked): rp_sil_t0_after_m3l2 (smoke), rp_sil_r1_before /
after_m3l2 (hip + aim, six guns, light + dark), rp_sil_r2_before_m3l2 (props, superseded layout), rp_sil_r3_before /
after_m3l2 (props), rp_sil_r3_before / after_m4l1 (night: hip + props).

## Evidence (item 1; every file looked at)

| file | what |
|---|---|
| `evidence/silencer_sheet_old_new.jpg` | the sheet, today's (upscaled) beside the repaint (decoded DXT1) |
| `evidence/silencer_sheet_crops_1to1.jpg` | 1:1 crops of the decoded dds: rear cap + knurl, mid tube, muzzle end, muzzle face |
| `evidence/silencer_soft3d.jpg` | software render on the mesh, old / new: shell centre, side seam, muzzle and rear three-quarter |
| `evidence/silencer_engine_hip_light_m3l2.jpg`, `..._hip_dark_m3l2.jpg` | in the hand, six guns, before / after, x2.5 crops |
| `evidence/silencer_engine_aim_m3l2.jpg` | aim, Colt / Beretta / grease gun: the silencer is behind the gun (no change to see); scoped guns have no aim still |
| `evidence/silencer_engine_world_m3l2.jpg` | world model crops x2: grease gun, Beretta, Colt side-on; Mosin, Kar98, Garand on the ground; light + dark |
| `evidence/silencer_engine_world_frames_m3l2.jpg` | the whole frames those crops come from (in the rifle side view the Mosin's and Kar98's silencer run out of the frame - use the ground crops for those two) |
| `evidence/silencer_engine_night_m4l1.jpg` | night: side, ground, hip - nothing glows |

Not seen in the engine: the muzzle face from the front (software render only); the engine's own third-person camera
(it sits behind the shoulder and hides the gun - the world-model stills stand in for it); gl1 renderer.

## Grease gun: what the layout allows (looked at, not painted yet)

`greaser.skd` (= the mesh in `greasegun_silenced.skd`, one bone) does not follow the art of its 512 sheet: the receiver
halves share the top strip (mirrored), the magazine sits in a narrow column, several small parts overlap the receiver
strip, and a handful of triangles have UVs thrown across the whole sheet (two magazine vertices at 0,0 - the black
slashes on today's magazine). A repaint therefore has to be painted in gun space per island, with no black gutters
anywhere on the sheet. `work/uv_gg_*.png` (not committed) are the island overlays; `tools/uvdump.py` rebuilds them.

## Integration file list (fixes pak `zzzzzzzzzz_coop_fixes.pk3`)

* `textures/models/weapons/colt/colt45s2.dds` <- `assets/textures/models/weapons/colt/colt45s2.dds`

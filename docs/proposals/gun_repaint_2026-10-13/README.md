# Gun repaint 2026-10-13 - the first three shortlist items (all metal, painted by script)

**PAUSED 2026-10-13 14:30 on the coordinator's PAUSE (usage cap). Read "Where it stands" and "Next steps".**

Shortlist and cost notes: `../gun_sources_2026-10-13/REPORT.md` sections 4 and 5. Everything here is STAGED
(`assets/` mirrors game paths); nothing in the mod tree or in `docs/tools/assets/fixes` was touched.
Meshes, UVs, tiks and shaders are unchanged - only texture files. No pixels from outside: both sheets are fully
procedural (no source image at all).

## Where it stands

| # | item | state |
|---|---|---|
| 1 | shared silencer sheet `colt45s2` (six guns) | **DONE** - staged, seen in the engine on all six guns, every evidence file looked at |
| 2 | M3 grease gun `greaser` | **STAGED, PARTLY CHECKED** - final sheet built and run in the engine (m3l2 + m4l1, before / after); only the light-spot crops were looked at (hip, aim, right side). Dark spot, night, silenced gun, AI copy, ground, left side: stills exist, NOT looked at |
| 3 | pump shotgun receiver top | **NOT STARTED** (nothing read, nothing staged) |

## 1. Silencer - `tools/silencer.py`

* Users (winning shader + tiks, `tools/shgrep.py`): shader `colt45s2` (scripts/american_weapons.shader,
  zzzzz_xw_weapons.pk3) on surface `Cylinder1` of `colt_silenced.tik`, `berettasilenced.tik`, `garand_silenced.tik`,
  `greasegun_silenced.tik`, `kar98snipersilenced.tik`, `nagant_snipersilenced.tik`. The six skds carry identical UVs
  and triangles on that surface (asserted by the generator). None of the six has finish tiks (no bloody / camo /
  blued / chrome / gold variants exist for them) - nothing to re-bake.
* Wins today: `textures/models/weapons/colt/colt45s2.tga`, 320x240, zzzzz_xw_weapons.pk3 (the only copy in any pak;
  the engine holds it as 256x128 DXT1a). Staged: `assets/textures/models/weapons/colt/colt45s2.dds`, 2048x2048 DXT1 +
  mips, 2.8 MB. A `.dds` of the stem beats the `.tga` from any pak, so it wins from the fixes pak. Proof:
  `evidence/silencer_imagelist_before.txt` / `_after.txt`.
* Paint: the two half shells are planar projections, so everything is painted in tube coordinates baked from the
  mesh (continuous across both seams). Dark blued steel, lathe lines, broken sheen on both shells (the six guns mount
  the tube with different roll), joint groove + knurled cap at each end, worn muzzle rim, muzzle face with turning
  rings, recess step, bore and soot.
* Run: `python tools/silencer.py --preview` (85 s, the DXT encode). `--draft` = previews only, no asset.

## 2. Grease gun - `tools/greasegun.py` (+ `gg_probe.py`, `gg_geom.py`)

* Users: shader `greaser` on `surface all` of `greasegun.tik`, `greasegun_silenced.tik` (zzzzz_xw_weapons.pk3) and
  `coop_greasegun_ai.tik` (mod). `greaser.skd` is the same mesh as the gun inside `greasegun_silenced.skd` (asserted).
  No finish tiks exist for the grease gun - nothing to re-bake.
* Wins today: `textures/models/weapons/greasegun/greaser.jpg`, 512x512, zzzzz_xw_weapons.pk3 (the only copy).
  Staged: `assets/textures/models/weapons/greasegun/greaser.dds`, **4096x4096** DXT1 + mips, 11.2 MB (imagelist:
  `4096x4096 DXT1 12Mb`). 4096 because this mesh uses a third of its sheet and squeezes its main parts; `--n 2048`
  builds a 2.8 MB one with the same paint (not run in the engine in its final state).
* The mesh does not follow the art of its sheet (measured, `gg_probe.py`): 269 of 2567 triangles have UVs thrown
  across the sheet, the lower receiver and magazine sides are squeezed 7-11 : 1, the receiver halves share one
  strip, small parts lie on that strip, the magazine's front / back faces share texels with the stock guide tubes.
  So the sheet is baked in GUN SPACE (position, normal, part, texel density per texel): solid 3D noise, wear from the
  3D distance to hard edges, plain material where two parts share texels, no black gutters.
* What is on it: phosphate-grey receiver with stains, a broken highlight band, handling scratches, the weld bead of
  the two halves along the top and bottom centre line, a crimp ring at the rear cap and at the collar; turned rear
  cap (rings, groove, centre); turned darker barrel and collar, worn muzzle; press line on the trigger housing and
  on the magazine housing's lip; magazine darker blued; wire stock bare worn steel with patina; rubbed grip straps.
* **Not possible on these UVs (mesh untouched):** the ejection-port cover's own outline (its island lies inside the
  receiver strip - an outline there would be drawn on both receiver sides); a clean magazine floor plate and a few
  magazine / port triangles (thrown UVs - they still sample across the sheet, now through low-contrast steel
  instead of black gaps); the stock guide tubes take the magazine's shared tone (they read as shaded rails).
* Run: `python tools/greasegun.py --preview --n 4096`; `--draft` = previews only.

## Engine stills - `tools/run_rp.py`, `tools/mkov.py`, `tools/sheet.py`

Harness `G:/mohaa-hudfeed3` (slot hudfeed3, port 12741), the RELEASED binaries copied from the GOG root under their own
names (`openmohaa_rel1013.exe`, `games/game_rel1013.dll`, `cgames/cgame_rel1013.dll`, `renderers/gl2_rel1013.dll`); the
harness root's previous `game.dll` / `cgame.dll` / `renderer_opengl2.dll` are kept beside as `*.pre_repaint` and put
back after every run (they are back now; no client of this lane is running, the slot is free). Overlay = the
double-barrel lane's `build/ovbase_cur.pk3` + a test-only prop spawner + the staged files; `before` = plumbing only.
World model = props (same skd and shader): three guns floating side-on at 48 u, both sides, and laid on the ground.

Runs, all moved to `H:/hzm_archive/repaint/<run>/` (file counts checked): rp_sil_t0_after_m3l2, rp_sil_r1_before /
after_m3l2, rp_sil_r2_before_m3l2, rp_sil_r3_before / after_m3l2, rp_sil_r3_before / after_m4l1;
rp_grease_g1_before_m3l2, rp_grease_g1_before_m4l1 (the BEFORE of item 2), rp_grease_g1_after_m3l2 (first, too light
paint - superseded), rp_grease_g2_after_m3l2, rp_grease_g2_after_m4l1 (the AFTER of item 2, final sheet).

## Evidence

Item 1 - every file looked at:

| file | what |
|---|---|
| `evidence/silencer_sheet_old_new.jpg` | the sheet, today's (upscaled) beside the repaint (decoded DXT1) |
| `evidence/silencer_sheet_crops_1to1.jpg` | 1:1 crops of the decoded dds |
| `evidence/silencer_soft3d.jpg` | software render on the mesh, old / new |
| `evidence/silencer_engine_hip_light_m3l2.jpg`, `..._hip_dark_m3l2.jpg` | in the hand, six guns, before / after, x2.5 crops |
| `evidence/silencer_engine_aim_m3l2.jpg` | aim, Colt / Beretta / grease gun: the silencer is behind the gun; scoped guns have no aim still |
| `evidence/silencer_engine_world_m3l2.jpg` | world model crops x2, light + dark |
| `evidence/silencer_engine_world_frames_m3l2.jpg` | the whole frames (rifle side view: the Mosin's and Kar98's silencer run out of the frame - use the ground crops) |
| `evidence/silencer_engine_night_m4l1.jpg` | night: side, ground, hip - nothing glows |

Item 2:

| file | looked at? | what |
|---|---|---|
| `evidence/greasegun_engine_light_m3l2.jpg` | **yes** - clean | before / after, light spot: hip, aim (rear cap), right side of the world model |
| `evidence/greasegun_engine_frames_m3l2_NOT_LOOKED_AT.jpg` | **no** | whole frames: hip light / dark, silenced hip, dark aim, world side both sides, dark side, ground |
| `evidence/greasegun_engine_night_m4l1_NOT_LOOKED_AT.jpg` | **no** | night: hip, aim, side, ground |
| `evidence/greasegun_soft3d_zoom.jpg` | the 2048 draft of the same paint yes; this 4096 file no | software render of the repaint, x2 |
| `evidence/greasegun_soft3d.jpg`, `greasegun_sheet_old_new.jpg` | an earlier paint state yes; these files no | old / new on the mesh; the sheet (not readable as a picture - it is a gun-space bake) |
| `evidence/greasegun_imagelist_before.txt` / `_after.txt` | yes | 512x512 DXT1a -> 4096x4096 DXT1 |

Not seen in the engine at all: the silencer's muzzle face from the front; the engine's own third-person camera (it
sits behind the shoulder and hides the gun - the props stand in); the gl1 renderer; the AI copy in an AI's hands.

## Next steps (in order)

1. Item 2: look at the two `_NOT_LOOKED_AT` sheets and the three regenerated software renders; if clean, rename
   the sheets (drop the suffix) and mark item 2 done. Known things to judge there: the tone at the dark spot and at
   night, the left side, the magazine from the side (rails / shared tone), the silenced gun's joint with the new
   silencer. If the 11 MB size is not wanted: `--n 2048` and one engine run to confirm.
2. Item 3 (shotgun receiver top) - not started. Start by reading
   `../ads_twohand_2026-10-11/heavy/README.md` ("Shotgun sight": the new surfaces `coop_groove` / `coop_bead` on the
   fixes pak's `models/weapons/shotgun/shotgun.skd` - leave them alone), then `tools/uvdump.py` on that skd (file under
   `docs/tools/assets/fixes/models/weapons/shotgun/`) with stem `textures/models/weapons/winchester/winchester`.
   Known already: the base sheet that wins today is `winchester.dds` 2048x2048 DXT5 in zzzzzz-HRRTM_Pak4_Weapons.pk3
   (a staged `.dds` of the same stem in the fixes pak wins: the fixes pak sorts above it); the four baked finishes are
   `textures/coop_skins/shotgun/winchester_{bloody,camo_woodland,camo_winter,camo_desert}.jpg` (mod tex pak) - re-bake
   them with the mod's recipe `docs/tools/weapon_hd/build_finishes.py` (bake_skins.py functions; output `.dds` of the
   same stem); skin variants with their own sheets: `coop_authwinch/winchester`, `coop_v3/{dhshotblack,dhshotchrome,
   guanshotty,hobbsshotty,lv_ttshotgun}/shotgun` (1024 each; whether they share the blurred island is NOT checked).
   `run_rp.py` already has a `shotgun` item (eight finish tiks); the test thread gives no shotgun shells (stills only).
3. Before any engine run: `python docs/tools/harness_guard.py status` (slot hudfeed3 must be free).

## Integration file list (fixes pak `zzzzzzzzzz_coop_fixes.pk3`)

* `textures/models/weapons/colt/colt45s2.dds` <- `assets/textures/models/weapons/colt/colt45s2.dds` (item 1, ready)
* `textures/models/weapons/greasegun/greaser.dds` <- `assets/textures/models/weapons/greasegun/greaser.dds` (item 2,
  only after step 1 above)

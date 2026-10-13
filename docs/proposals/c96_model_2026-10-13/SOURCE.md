# Mauser C96 replacement model - source record and look test (2026-10-13)

Status: **look test only**. Nothing converted, nothing in the mod changed, the game not run.

## Source

| | |
|---|---|
| Title | Mauser C96 |
| Author | no12u (Sketchfab) |
| Page | https://sketchfab.com/3d-models/mauser-c96-be41cc2ed9844b8bba3a700cce93bab9 |
| Licence | CC BY 4.0 (credit required) |
| Credit line the mod needs | `Mauser C96 model by no12u (Sketchfab), CC BY 4.0` |
| Downloaded | 2026-10-13, by the user |
| File | `source/mauser-c96.zip` (not committed) |
| Size | 95,847,082 bytes |
| sha256 | `706eafad885679ad4fa4ad792d30cad41d27b0c22e752f33810337eafaf40f2a` |

Archive contents (5 files, all dated 2022-09-19; no executables, scripts or add-ons):

| bytes | path | what |
|---:|---|---|
| 849,628 | `source/Mauser_Final.fbx` | mesh + rig + one animation |
| 35,308,804 | `textures/Mauser_L_Baker_BaseColor.1001.png` | 4096x4096, 16-bit RGB |
| 50,305,462 | `textures/Mauser_L_Baker_Normal.1001.png` | 4096x4096, 16-bit RGB |
| 7,022,922 | `textures/Mauser_L_Baker_Roughness.1001.png` | 4096x4096, 16-bit grey |
| 2,359,490 | `textures/Mauser_L_Baker_Metallic.1001.png` | 4096x4096, 16-bit grey |

Unpacked to `source/unpacked/` (not committed). The FBX points at `source\Textures\...`, which is not where the archive
puts them, so the maps have to be wired by hand (the render tool does).

## Facts (Blender 5.1.2, `tools/bl_inspect.py` + `tools/bl_render.py --stats`; raw output in `tools/inspect_out.json`, `tools/parts.json`)

- **Formats**: FBX only (no glTF, no .blend), four PNG maps. No ambient-occlusion map.
- **Objects**: ONE mesh `Frame_L` (12,509 vertices, 24,600 triangles, one material `MauserFinal`, one UV set inside 0..1)
  and ONE armature `MauserRig` with 10 bones. Every vertex is weighted to exactly one bone (0 blended vertices), so the
  mesh splits cleanly by bone:

| bone | triangles | what it is |
|---|---:|---|
| Root | 7,451 | frame, barrel, barrel extension, rear sight, safety, grip panels, magazine |
| Slide | 1,671 | the bolt |
| Hammer | 620 | hammer |
| Trigger | 242 | trigger |
| Ring | 576 | lanyard ring |
| **pistol total** | **10,560** | |
| Clip | 9,692 | 10-round stripper clip with its rounds, standing above the action |
| FreshBullet | 956 | one loose round |
| EjectBullet | 702 | one loose spent case |
| Stock + StockCup | 1,808 + 882 | wooden holster stock with its hinged lid |
| **everything** | **24,600** | |

- **Moving parts**: bolt, hammer, trigger, lanyard ring, stock lid, clip, two rounds are bones. NOT separate: rear sight
  slider and leaf, safety lever, magazine follower, grip panels (all part of `Root`; the mesh has 48 loose shells, so they
  can still be cut apart by hand).
- **The one animation** (`MauserRigAction`, frames 1-77 at 30 fps): a single shot. Trigger pulls (1-11) and returns (to 37),
  hammer falls from 64 degrees to 0 (11-19) and comes back (19-27), the spent case flies out and shrinks to nothing (19-77).
  **The bolt does not move in it**, and there is no reload. The rest pose is hammer DOWN.
- **Scale and axis** (as imported): muzzle +Y, up +Z, left side -X. Not real-world scale: the pistol is 2.17 units long
  (a real C96 is about 312 mm, so one unit is about 144 mm). It has to be rescaled for the game anyway.
- **Interior**: yes. With the bolt drawn back the chamber, the bolt's own body and the magazine well are modelled and
  textured (`media/boltback_top.jpg`). The bore is open at the muzzle.
- **Faults**: none that show. 278 open edges on 15 open shells (expected on a game model: bore, hidden joints), 9 loose
  vertices, 1 zero-area face, 36 n-gons, 0 non-manifold edges, 0 inside-out closed shells. Markings read the right way
  round (not mirrored).

## The mod's current C96, for comparison (`tools/old_c96_dump.py`)

`models/weapons/coop_c96/c96.skd` (East's model, moh-db.com/mods/13664): **4,788 triangles** in 12 surfaces, 12 textures
of 640x480 each (upscaled from 320x240). Nine tiks use that mesh (base + 8 finishes).

## Renders (`media/`, EEVEE, the model's own maps, 1600 px wide)

`left.jpg` `right.jpg` `top.jpg` `front34.jpg` `aim.jpg` (hammer down) `aim_cocked.jpg` `aim_cocked_zoom.jpg`
`boltback.jpg` `boltback_top.jpg` `delivered.jpg` (everything in the file) `old_left.jpg` (the current model),
plus the sheets `c96_look_sheet.jpg` and `c96_old_vs_new.jpg`.

The bolt-back pose is made here (bolt bone moved 13 % of the pistol's length to the rear, hammer at the animation's
cocked angle); the file itself has no such pose.

## Reproduce

```
blender --background --factory-startup --disable-autoexec --python tools/bl_inspect.py -- <fbx> tools/inspect_out.json
blender --background --factory-startup --disable-autoexec --python tools/bl_render.py -- --fbx <fbx> --tex <unpacked/textures> --out media --stats tools/parts.json
python tools/old_c96_dump.py tools/old_c96.json
blender ... --python tools/bl_render.py -- --fbx <fbx> --tex <dir> --out media --old tools/old_c96.json --views delivered,left,right,top,front34,boltback,boltback_top,old_left
blender ... --python tools/bl_render.py -- --fbx <fbx> --tex <dir> --out media --views aim,aim_cocked --aim 0.542,0.306,2.262,0.277 --aimlens 170
blender ... --python tools/bl_render.py -- --fbx <fbx> --tex <dir> --out media --views aim_cocked --aim 0.542,0.306,2.262,0.277 --aimlens 600 --suffix _zoom
python tools/sheet.py
```

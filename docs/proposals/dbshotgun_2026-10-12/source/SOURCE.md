# Source of the double-barrel shotgun model

| | |
|---|---|
| Title | Double Barrel Shotgun |
| Author | Jean PFP (OpenGameArt user) |
| Page | https://opengameart.org/content/double-barrel-shotgun |
| Licence, as shown on the page | **CC0** (link on the page: https://creativecommons.org/publicdomain/zero/1.0/) |
| File, as named on the page | `Shotgun.zip`, 9.2 Mb |
| File, as linked | https://opengameart.org/sites/default/files/Shotgun_1.zip |
| Downloaded | 2026-10-12, with curl, into this directory as `Shotgun.zip` |
| Size | 9,200,938 bytes |
| sha256 | `112b1979d64423713f128a94bc10772398eb130715544449afc9eeaf33de0f35` |

Nothing else was downloaded for this weapon.

## Contents of the zip (`Shotgun/`)

| File | Bytes | What |
|---|---:|---|
| `doubleBarrelLow.blend` | 4,453,192 | game mesh, 4,220 triangles in 3 objects (barrels + forend, body, triggers), UVs for the baked sheets |
| `doubleBarrelHight.blend` | 3,536,760 | modelling file: 12 objects with bevel / subdivision / mirror modifiers, 25,054 triangles as shown; procedural materials, **no baked textures** |
| `doubleBarrelD.png` | 543,365 | 2048 x 2048 diffuse (wood only - the steel is black: metal workflow) |
| `doubleBarrelG.png` | 1,364,771 | 2048 x 2048 glossy colour (the steel's colour and scratches) |
| `doubleBarrelR.png` | 471,199 | 2048 x 2048 roughness |
| `doubleBarrelAO.png` | 812,084 | 2048 x 2048 ambient occlusion |
| `doubleBarrel.obj` / `.mtl` | 297,662 / 388 | the low mesh as OBJ |
| `readme.txt` | 75 | "Low Poly: 4.500+ Tris. Hight Poly: 22.200+ Tris. Thanks for download :D" |

The author's readme carries no further conditions.

## Handling (untrusted data)

- The zip and its unpacked files live only here; our scripts live in `..\tools\` and are never run from this directory.
- The `.blend` files are opened only by `blender --background --factory-startup --disable-autoexec` with
  `use_scripts=False`; neither file contains a text block (checked: `bpy.data.texts` is empty in both).
- Python that reads these files runs with `python -I`.
- Only `SOURCE.md` is committed. The zip (9.2 MB) and the unpacked files are not; the sha256 above identifies them.

## What of the author's work is in the game files (2026-10-12 b)

**Only his MESH** (the high file's geometry, CC0) - cut into five rigid parts and triangulated by `tools/bl_build.py`.
Everything else is ours:

| Game file | Made from |
|---|---|
| `coop_dbshotgun.skd` | the author's mesh; **our** UV atlas (Blender smart project in `bl_build.py`); our bones, bead and shells |
| `coop_dbshotgun.jpg` (2048) | painted by `tools/dbs_skin.py` (seeded, reproducible) into that atlas from: the mesh's positions / normals / curvature, the material-slot flag "this face is wood" (a face attribute of the mesh, not a texture), ambient occlusion **we** bake from the geometry, the RETAIL Kar98 sheet's butt-stock wood (`main/Pak2.pk3`, `textures/models/weapons/kar98/kar98.dds`, 1024 x 512, shading divided out) for the walnut's colour and figure, and procedural steel (no source image) |
| `coop_dbshotgun_parts.jpg` (256) | procedural (`tools/dbs_build.py` `parts_sheet`): brass, shell hull, primer |

**No pixel of the author's baked sheets is used any more** (`doubleBarrelD.png`, `doubleBarrelG.png`, `doubleBarrelR.png`,
`doubleBarrelAO.png`), and nothing from the three images packed inside his .blend files
(`TexturesCom_MetalBare0207_2_seamless_S.jpg`, `TexturesCom_WoodFine0061_12_seamless_S.jpg`, `proxy.duckduckgo.com.jpg` -
the inputs of his procedural materials and an environment picture) was ever extracted, read or shipped. The first
pass (commit 2bd2958 / f2dacd4) DID compose the sheet from his baked diffuse and glossy sheets, which were presumably
made from those two Textures.com images; that sheet is replaced, and `tools/dbs_tex.py`, which made it, is deleted.
`bl_build.py --own` (the mode the build now uses) opens neither his baked sheets nor his low file; its mesh / atlas
output was compared with the first pass's and is identical to the last digit, so the skd did not change.

Not from the author either: the HRRTM / HD retexture paks on this machine were looked at only to find the retail file
(`tools/srclist.py` lists which pak carries a texture and saves the copy from a pak named `pak*.pk3`).

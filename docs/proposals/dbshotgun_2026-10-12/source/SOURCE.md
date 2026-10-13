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

## Note on the textures inside the .blend files

Both .blend files have two packed images named `TexturesCom_MetalBare0207_2_seamless_S.jpg` and
`TexturesCom_WoodFine0061_12_seamless_S.jpg` (the inputs of the author's procedural materials) and one
`proxy.duckduckgo.com.jpg` (an environment picture). **None of these three is used, extracted or shipped by us.** The
game textures are made only from the author's own baked sheets in the zip (`doubleBarrelD.png`, `doubleBarrelG.png`)
and from ambient occlusion we bake ourselves from the geometry. The baked sheets are the author's CC0 release; they
were presumably derived from those two Textures.com images inside his materials - if that provenance matters for a
public release, it is the one point to look at (open point in the README).

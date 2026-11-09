# finishes2 (2026-11-09) - new finish sets for every gun

Period/unit finishes (battle-worn, trench art, parade, captured, airborne 82nd / 101st, FFI, DAK, Kriegsmarine), camo
(splinter, pea, telo, amoeba, whitewash) and nose art. Offline compositor + orientation build gate done; in-game look tests
on the private client; shipping build (shader composites through gen_skins) not started.

## Id ranges (agreed with the new-guns agent: Bren, MP28, Panzerfaust - 2026-11-09)

| what | finishes2 | new-guns |
|---|---|---|
| finish tik `rank` | **1240 and up** | 1210-1239 |
| `coop_skinN` rows | **600 and up** | up to 599 |
| Armory ids | **85 and up** (if any) | 82-84 |
| finish slots (fid: `coop_skinGive[<gun>][<fid>]`) | **40 and up** | 1-7 on its own 3 guns (model variants hold 8-18) |

`gen_skins.py` checks ranks only against the files on disk, so **whichever branch merges second re-runs
`python docs/tools/gen_skins.py add ...`** after rebasing on the other.

## Layout

- `tools/finishlib.py` - the gun in its TRUE frame (x muzzle, y gun-left, z up; the skd frame is rolled 180 deg - bug-10666),
  texel -> model maps, wear mask, decal islands and the UV->model fit.
- `tools/orient_check.py` - build gate: every gun's default decal rendered as an F + up-arrow glyph and read back
  (`assets/orient_check.tsv`, `media/orient_all.jpg`). Armory/viewer side = gun right, first person = gun left.
- `tools/finish_sheet.py` - offline preview sheets; `tools/fs2_ingame.py` - baked look-test paks for the private client.
- `tools/patterns.py`, `decals.py`, `medals.py`, `noseart.py`, `export_decals.py` - art; `decals/` + `decals/manifest.json`
  is the Customize-bench set (mirror_safe flag, finish presets as bench spots). Asymmetric decals go on as the engrave
  agent's bench quads (docs/proposals/engrave_2026-11-09/PLAN.md); texture-painted only where the texels are not shared.

## Paint / camo finishes in game: size (measured 2026-11-09, before building)
Option B (coordinator): masked bakes only for whitewash, DAK, Kriegsmarine, airborne OD (airborne101 shares it) and the 5
camos. Measured on Kar98k / MP40 / Colt bakes (premultiplied paint JPEG q85 + one shared per-gun mask PNG); 126 body sheets
over the 70 guns (139 textures, sights / clips / glass excluded). Totals for the 8 bakes + masks:
half base res 802 MB, cap 1024 366 MB, cap 512 95 MB, **cap 384 54 MB**, cap 320 37 MB, cap 256 24 MB
(main sheet per gun only: cap 512 44 MB, cap 384 25 MB). At cap 384 a rifle sheet is ~1 mm per texel - camo shapes
(3-6 cm) and edge wear still resolve. Plan: the gun's own HD texture stays; the paint is two stages over it - the per-gun
mask darkens (GL_ZERO GL_ONE_MINUS_SRC_ALPHA), the premultiplied paint is added and lit (GL_ONE GL_ONE, lightingSpherical).

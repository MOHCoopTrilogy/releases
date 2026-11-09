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

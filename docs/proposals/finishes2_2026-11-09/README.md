# finishes2 (2026-11-09) - new finish sets for every gun

Period/unit finishes (battle-worn, trench art, parade, captured, airborne 82nd / 101st, FFI, DAK, Kriegsmarine), camo
(splinter, pea, telo, amoeba, whitewash) and nose art. Offline compositor + orientation build gate done; in-game look tests
on the private client; shipping build (shader composites through gen_skins) not started.

## Id ranges (agreed with the new-guns agent: Bren, MP28, Panzerfaust - 2026-11-09)

| what | finishes2 | new-guns |
|---|---|---|
| finish tik `rank` | ~~1240 and up~~ **2000-2909** (1240+ collided with shipped finishes, see WIRED) | 1210-1239 |
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

## Paint / camo build (2026-11-09) - real size
User raised the cap to 1024 px (higher quality). Built by tools/fs2_build.py into H:\hzm_work\finishes2_build (staging, not
deployed): **zzzzzzzzzz_coop_finishes_hd.pk3 = 177.2 MB** - 126 sheets, 70 guns, 8 coats (134.4 MB of q85 JPEG), grey PNG
masks 40.6 MB (grey JPEG was larger: 49.8, RGBA PNG 58.7), 630 variant tiks (9 per gun: the 8 coats + Airborne 101st on
the airborne coat; ranks 1240+, fids 40-48 in rows.tsv for loadoutskins.scr). Paint is opaque now (only the broad shading of
the gun shows through, no wood grain); Splittertarn / pea / telo mid-toned. Verified in game: media/ingame_built_3guns.jpg.
Open: wiring into gen_skins (loadoutskins rows, finish picker names, unlock ladder), the four shader-composited finishes.
Rebuilt after the whitewash / shading QA: 188.2 MB (the brushed whitewash and the mid-scale shading compress a little worse).

## WIRED (2026-11-09, wiring agent; target v1.10.68) - mod branch `finishes2`, root branch `finishes2-tools`
- **Ranks moved to 2000-2909.** The agreed 1240+ band collided with 350+ shipped ranks (the standard seven finishes and the model
  variants occupy 1000-1724; 3000-3006 are taken too). `fs2_finish2.py rerank 2000`; `gen_skins.py check` now asserts every
  finishes2 rank against every other weapon tik (mod tree, fixes / wpnfix sources, every out-of-band pak in the base checkout).
- **Splittertarn rebuilt** (QA: rounded blobs on the MP40 / Colt): the tile is now an anisotropic Voronoi partition (straight edges,
  hard corners, ~88 shards, -25 deg lean) and its physical size scales with the gun (half its length, 12-34 cm:
  `finish_sheet.tile_cm`). `fs2_finish2.py rebake splitter` re-baked all 126 sheets from the gun that baked each one (mask
  registration asserted: mean error 0.000). Offline: media/sheet5_splitter.jpg.
- **The four layered finishes built** (fids 49-52: battle-worn, trench art, parade, captured): shader stages over the gun's own
  texture + 4 shared tiles (`fs2_finish2.py layers`), tcMod scale per sheet from its world-per-UV. 280 more variant tiks.
- Pak: `fs2_finish2.py pack` (deterministic: sorted, fixed timestamp) = 910 variant tiks (70 guns x 13), 1690 shaders,
  13 Armory swatches (textures/coop_finishes_hd/sw), ~190 MB.
- Wiring, all through generators (`docs/tools/finishes2.tsv` + `finishes2.py` = the one table):
  `gen_skins.py fs2 [write]` / `check` (loadoutskins.scr block, scripts/hzm_finish_decals.txt, pak audit);
  `finish_challenges.py` (13 interleaved rungs per gun, 75-750, slow ladder 30-350); `unlock_audit.py` section 5 (writer,
  reachable target, reward in the pak); `gen_finish_ui.py` (ported from killchal-docs, wired into gen_loadout) + gen_loadout
  (finp previews, reqf hovers) + gen_armory (fail-locked defaults) + `gen_armory_urc.py` (the second chip row, finish name moved
  to the hero's top right); `gen_weapon_viewer.py` (1557 entries, history / credits from finishes2.tsv);
  loadoutpick.scr / challenges.scr by `tools/wire_loadoutpick.py`; build.ps1 / publish_release.ps1 ship the pak.
- In-game stills: `tools/run_fs2.py` on the private client G:\mohaa-finishes.

## Wiring into the game (the plan, kept for reference) - what has to change, all through generators
The finish system is built around fids 1-7 (finishes) and 8-19 (model variants). fids 40-48 touch:
1. `docs/tools/gen_skins.py` - a `fs2` mode that adopts H:\hzm_work\finishes2_build (tiks into the finishes pak, not the mod
   tree; rows.tsv -> `level.coop_skinGive[give][40..48]` in coop_mod/loadoutskins.scr, coop_skinN recount; shaders stay in
   the pak's own scripts/coop_finishes_hd.shader).
2. `coop_mod/loadoutpick.scr` - the fid dispatch: 40-48 take the FINISH path (the <=7 branch: loadout_finOpen gate,
   coop_loS<n>F, finp re-preview), not the model-variant cycle (8-19); `level.coop_skinFinName[40..48]`.
3. `docs/tools/finish_challenges.py` - FINISHES gains 40-48 (+ the 4 layered finishes later) with their own ladder rungs
   on the per-gun kill ladder (user: "extend the per-gun kill ladder"); regenerates the challenge defs.
4. `docs/tools/gen_loadout.py` - finp<id>_<fid>.cfg previews and the finish row of the Armory page (it hard-codes the 7
   keys); `gen_armory_urc.py` - a second finish row / page for the new finishes.
5. `docs/tools/gen_weapon_viewer.py` - viewer entries for the new variants.
6. Release: the pak ships as its own file (zzzzzzzzzz_coop_finishes_hd.pk3) so the updater re-downloads it only on change.

# v1.10.66 fg42hd: the FG 42 Irons on Shorty_Digitan's FG42 (2026-11-08)

User pick (OPTIONS.md, `../fg42_upgrade_2026-11-08`): the wood-stock FG42, "FG42" by **Shorty_Digitan**
(sketchfab.com/3d-models/none-d699ac259bd74f70a51125a7e4320f4b), **CC BY 4.0**, modified. Downloaded by the user to
`H:\hzm_work\fg42_src` (source/FG42.fbx + per-part PBR maps; untrusted data, read only).
Credit: `docs/SKIN_CREDITS.md` "Weapon models (CC)", `hzm_credits.txt`, and `credits/coop_cc_models.txt` inside the wpnfix pak.

Branches: mod `fg42hd`, engine `fg42hd-eng` (cgame only: the irons sight rows). Ships in `zzzzzzzzzzzzzzzz_coop_wpnfix.pk3`, the
last-sorting pak (the irons tik's winner was the stress pak, the skd's fixes2).

## Unscoped (FG 42 Irons): done
| | before | after |
|---|---|---|
| mesh | 914 tris, EA's 2002 mesh + in-house sights | **5,363 tris** (from 16.9k; collapse-decimated per part), its own diopter + hooded front post |
| sheet | `textures/fg42/fg42` 512 art (8x-upscaled dds) | **2048** `textures/models/weapons/coop_fg42hd/fg42hd.jpg`, the PBR baked to one diffuse |

Pipeline (`tools/`, Blender 5.1, the C96 recipe of `../c96_model_2026-10-18`):
1. `bl_extract.py`: decimate and extract every triangle corner.
2. `atlas.py`: one 2048 sheet, one tile per material. Normal-map relief, edge darkening and wear are baked in. The tone is matched
   to the shipped FG42's sheet, because the menus' lightingSpherical turns a brighter sheet near-chrome.
3. `fglib.py`: the fit.
   - The gun is uniformly scaled to the shipped length.
   - It is pitched 1.27 degrees so its sight line has the shipped irons' slope.
   - It is placed so the magazine and pistol grip sit where the shipped ones are (the reload and grip hands).
   - `media/fit_new_over_shipped_mesh.png` shows the result.
4. `build_mesh.py`: an skd on the **shipped skeleton**: origin, FG42, tag_eject, tag_barrel, coop_chg. Consequences:
   - DaRKaNGeL's `fg42.skc` and every coop clip drive it unchanged.
   - The magazine is the `fg42clip` surface that the reload frame commands hide.
   - The charging handle is the shipped `coop_handle`.
5. `stage_irons.py` points the adopted tik at the new skd and sheet; the sheet's shader is `coop_fg42hd` (coop_wpnfix.shader).
6. Sight rows:
   - `tools/posefit.py` solves the shipped mesh's exact bone-local to gun-frame map.
   - The new aperture and post go through it into `ads_twohand_2026-10-11/heavy/sights_override.json` and from there into
     `cg_adssights.h` (`sightrow_h.py`).
   - Relief is 5, so the aperture ring frames the post: `media/fg42_irons_ads_diopter.jpg`.
7. Finishes: `gen_skins.py add coop_fg42_irons`, 7 finishes on the new sheet. It now overrides finishes another pak ships, pinned
   to the copy they replace, and bakes from a sheet that the wpnfix pak itself carries.

QA (private client, DISPLAY2, coop m2l1, 0 Script Errors every run):
- `media/fg42_irons_before_after.jpg`: viewer (base and woodland), Armory hero, hip, ADS, hip reload (magazine in hand), ADS reload,
  third person.
- `media/fg42_irons_viewer_vs_scoped_armory.jpg`: new irons next to the shipped scoped gun in the viewer, plus the Armory hero.
- Armory framing re-measured for 79: within tolerance.

Gates: gen_loadout check EXACT, gen_weapon_viewer 0 stale, gen_wpnfix_pak OK, tik-surfaces clean, check_mp_isolation 22/0,
check_anim_aliases OK.

## Open
- **Scoped FG42: not started.** It needs a realistic scope. TastyTony's was rejected by the user; FF_Morph's "Kar98k with ZF4" is
  CC BY 4.0 per the API (OPTIONS.md) and textured, so it is the donor. Its download needs a Sketchfab sign-in:
  **https://sketchfab.com/3d-models/1ba37f4c9b104fa9ba981d22ab2d08aa** (please download it to `H:\hzm_work\fg42_src\zf4\`). The
  fallback is a scope modelled in-house.
- **Brass:** `tag_eject` comes from the clips and still sits where the shipped gun's port was. The new port is about 8 units further
  back, so brass leaves ahead of it.
- **World model on the ground:** not shot. `weapdrop` does nothing in coop, and `spawn` needs `+set cheats 1` on the command line.
  The third-person still shows the world model.
- **Bipod:** it is the model's own, folded and static, like the shipped one.

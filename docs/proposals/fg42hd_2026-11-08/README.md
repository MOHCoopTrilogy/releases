# v1.10.66 fg42hd: both FG 42s on Shorty_Digitan's FG42, the scoped one with an in-house ZFG 42 (2026-11-08)

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
   to the shipped FG42's sheet, because the menus' lightingSpherical turns a brighter sheet near-chrome. [QA] the wood is a
   darker, ~45 %-saturation oiled walnut with the source grain boosted as luminance (`WOOD_*`), checked beside the Kar98k's
   stock in the same viewer light: `media/fg42_wood_vs_kar98k.jpg`.
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
   - [QA 2026-11-08] the source diopter's aperture is real size, a pin-hole at game scale, and the ADS view looked at the back of
     the range drum (a black block in the lower centre; relief alone cannot fix it, the engine clamps the move to 4 u off the
     cheek weld). `build_mesh.py` drops the aperture loop and adds a thin GHOST RING (`fglib.RING_*`, 0.86 / 0.70 u) raised
     clear of the drum on a stem; R = the ring centre, relief 6. The eye looks through a ring around the post, centre clear:
     `media/fg42_irons_ads_diopter.jpg`.
7. Finishes: `gen_skins.py add coop_fg42_irons`, 7 finishes on the new sheet. It now overrides finishes another pak ships, pinned
   to the copy they replace, and bakes from a sheet that the wpnfix pak itself carries.

QA (private client, DISPLAY2, coop m2l1, 0 Script Errors every run):
- `media/fg42_irons_before_after.jpg`: viewer (base and woodland), Armory hero, hip, ADS, hip reload (magazine in hand), ADS reload,
  third person.
- `media/fg42_irons_viewer_vs_scoped_armory.jpg`: new irons next to the shipped scoped gun in the viewer, plus the Armory hero.
- Armory framing re-measured for 79: within tolerance.

Gates: gen_loadout check EXACT, gen_weapon_viewer 0 stale, gen_wpnfix_pak OK, tik-surfaces clean, check_mp_isolation 22/0,
check_anim_aliases OK.

## Brass (QA): fixed
`eject_tag.py` moves `tag_eject` in every frame of the adopted `coop_fg42_fire.skc` (both FG 42s fire with it) to the new port's
right face, about 8 units behind the shipped port.

## Scoped (FG 42): done, the ZFG 42 modelled in-house
The user said not to wait for a Sketchfab download. `scope_mesh.py` models a period ZFG 42 (4x): a short ~14 cm tube, a small
objective bell, an ocular bell with a rubber eyecup, the elevation drum on top and windage on the right, two rings on a claw
base clamped by a plate on the receiver's LEFT side with two screws. It is lathe profiles and boxes in the FG42 bone's local frame
on the SHIPPED scope's optical axis, so the scope rows in `cg_adssights_scope.h` and the PiP stay valid, unchanged.
- `atlas.py` adds a Scope tile (the barrel's paint combed along the tube and blued, darker than the receiver) and a matte Rubber
  tile in the sheet's free corner; every other tile is byte-identical, so the Irons are untouched.
- `FG_SCOPE=1 build_mesh.py` -> `coop_fg42hd.skd`: the body without the diopter, the scope as `fg42hdsc*`, glass as `fg42lens`
  (coop_scope_glass_blue, as before), the shipped `coop_handle`.
- `stage_scoped.py` adopts `models/weapons/FG42.tik` (winner: the scopeglass pak), points it at the new skd, ships the sheet.
- `gen_skins.py add fg42`: the 7 finishes reuse the Irons' blocks for the new sheet and the shipped `coop_skin_fg42_*` for the
  handle. gen_skins now reuses a gun's OWN shipped blocks, keeps a shipped finish's rank and loadoutskins rows, and does not
  re-bake a bake another pak ships.
- Armory hero refit for gun 39 (`armoryfix_2026-11-08/tools/armory_fit.py`, converged); the card stays within tolerance.
- Viewer credits for 39 / 79 name Shorty_Digitan's model (`weapon_history.tsv`).

QA: `media/fg42_scoped_before_after.jpg` (ADS through the irons, ADS through the scope, hip, viewer, Armory hero), 0 Script
Errors. `build/cmp_side.png` is the side / top wireframe over the shipped scoped mesh.

## Scope QA #2 (user: "looks bad up close"): the riflescope recipe, a ZFG 42 reticle, a real eyecup
The user picked option 1: aiming uses the same scope view as the Kar98k / Springfield. That view is not a separate system: every scoped
rifle (FG 42 included) runs cgame `cg_hzmscope.c`'s lens pass - the live magnified picture composited into the gun's own GLASS
surface, the world blurred round it, the reticle per optic from `zzzzzzzzzz_coop_scopes.pk3` (`gen_scope_reticles.py`). What made the FG 42
read badly was our geometry and its reticle, so that is what changed:
- **Eyepiece = the Kar98k's recipe**: the eyepiece itself is the dark ring round the picture. The cup's opening and the recessed ocular
  glass are `GLASS_R` 1.14, measured against the pass's picture circle (gR, from the scope row's relief) so the picture edge is the
  rubber lip, never a band of bare glass; the cup is 1.62 outside (the tube is 1.48), so the ring is about a third of the picture.
  The first cup (2.18 outside, glass 1.70) gave the thick black double ring and the hazy grey band.
- Tried and dropped: hiding the cup at the eye (`coop_scopeEyeHide`, the G43 / StG 44 route) left a small scope floating inside the
  pass's own ring, and hiding the GLASS kills the picture (the pass composites into the glass pixels). cgame keeps the original lists.
- **Closed dark bore** inside the tube, and the turret saddle / windage drum kept outside the tube: the gun layer is drawn over the
  picture, so through a hollow tube the turret block showed as a notch at the top of the eyepiece.
- **Reticle `zfg42`** (new optic in `cg_hzmscope.c`, 4x like the ZF4; FG 42 mapped to it): a fine long-tapered post and fine
  horizontal lines that step to short heavier bars near the rim. The G43 / StG 44 keep `zf4`. `gen_scope_reticles.py` draws it;
  `HZM_MOD` builds the scopes pak into a worktree. **The base tree's scopes pak must be rebuilt when this merges** (its `check` fails until then).
- **Hip look**: the eyecup is a real cup (outer wall, rolled lip in lighter worn rubber, straight inner wall, glass recessed 0.9 inside),
  smooth-shaded lathe normals; the scope steel is lifted to a worn blued grey (atlas `SCOPE_MEAN` 0.26 - 0.165 still read black in the hand).
- Harness: `wpnview_run.py` takes `WV_DISPLAY_RES=3440x1440` (the test display picked by resolution: the user's ultrawide, not the TV);
  `run_fg42.py` takes `WV_RES` (1080 / uw) and `WV_RAISE` (lit hip + raise frames); `qa2_batch.py` runs the set one client at a time.

## Open
- **World model on the ground:** not shot. `weapdrop` does nothing in coop, and `spawn` needs `+set cheats 1` on the command line.
  The third-person still shows the world model.
- **Bipod:** it is the model's own, folded and static, like the shipped one.
- m2l1's spawn is backlit: the hip stills read dark for the shipped gun too.

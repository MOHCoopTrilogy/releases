# Mauser C96 replacement: no12u model (Sketchfab, CC BY 4.0), 2026-10-18

Status: **built and run in the engine (private harness copy, live engine set, released mod + overlay); STAGED, not in the fixes pak, nothing deployed.**
Credit line (done in the mod worktree, branch `c96-next`, hzm_credits.txt): `Mauser C96 model by no12u (Sketchfab), CC BY 4.0`.
Source record and look test: `../c96_model_2026-10-13/SOURCE.md`. Base for the hands / rows / Trench: the pistol lane's `../ads_twohand_2026-10-11/ship2/` (prerequisite; this cut supersedes its gun mesh, gun clips and 8 tiks).

## What is in `ship/` (fixes-pak paths; no file under the mod's textures/ or models/)
| | |
|---|---|
| `models/weapons/coop_c96n/c96n.skd` | 14 surfaces, 10,560 tris (was 4,788), 8 bones; NEW path, so the `newanim/` and base-pak precedence traps do not apply |
| `models/weapons/coop_c96n/c96n_*.skc` | idle, idle_empty, fire (8 frames, bolt + hammer + trigger every shot), reload_hip, reload_empty, reload_ads_loaded, reload_ads_empty (73 frames, the timeline of the server's torso row) |
| `models/weapons/mauser_c96*.tik` | base + 7 finishes: ship2's text with mesh, surfaces, finish shaders, clips swapped (override entries with base pins; the Trench tik is untouched) |
| `scripts/coop_c96n.shader`, `textures/models/weapons/coop_c96n/*.jpg` | 2048 sheet (+ 4 baked finish sheets; gold / chrome / blued are shader stages as the mod's recipe) |
`FILES.txt` = sizes + md5. Apply with the integrate machinery (`ads_twohand_2026-10-11/integrate/intlib.py`): new paths -> `{"new": "True"}`, the 8 tiks -> base pins from the mod tree. NOT applied here. Also needed from ship2: its hands clips, rows (`ROWS_fps_anims_pistol.txt`), Trench files.

## Pipeline (`tools/`, run from this folder; Blender 5.1)
`bl_extract.py` (FBX -> per-corner npz, REST pose) -> `c96lib.py` (fit) -> `build_mesh.py` (skd) -> `bl_tex.py` + `paint_sheet.py` (sheet) -> `finishes.py bake|build` -> `gen_clips.py` -> `gen_ship.py` (tiks) -> `mkbase_c96.py` + `mkov_c96.py` (test overlay) -> `run_final.sh` (harness) -> `mkgif.py`. Offline checks: `view_skd.py`, `prop_in_gun.py`, ads `c96view.py`.
* **Fit** (`c96lib.py`): uniform scale (17.3 scaled units long, as the old model), 1.64 deg pitch, so the new rear leaf / front post lie ON the line of the mod's sight row (`cg_adssights.h` F, R) - no engine change. Hammer pin, trigger top, muzzle and port tag come from the source's bones.
* **Bones**: `coop_slide` = bolt (3.8 raw units back), `coop_tog` = hammer (64.1 deg cocked, as the source), `coop_trig` = trigger; the P38 skeleton's `origin tag_barrel tag_eject Box01 p38clip` kept. Frame, grips, safety, sights, magazine well and the lanyard ring ride on `origin`.
* **Not separable**: magazine floorplate, safety, sight leaf, grip panels are faces of one shell with the frame; no floorplate bone was made (the C96 has no moving floorplate). Stock, holster, source Clip and loose rounds are not in the game mesh: the server's stripper-clip prop is used.
* **Sheet**: the shader has no spec / normal stage, so the PBR look is baked into the diffuse: metal re-toned to blued steel (gain tuned against engine frames of the old gun side by side), wood x1.45, normal-map edge darkening, roughness polish.
* **Clip seat**: the server prop's seat lands over the new model's own clip-guide slot (checked, `tools/prop_in_gun.py` + top view), so the pistol lane's reload hands are used unchanged.

## Proof (`media/`, from `G:\mohaa-hudfeed2`, run ids g1..g5, frames in the session scratch; 1280x720, 16 ms frames)
idle 1p, hip fire, ADS shot, ADS reload (rounds left, emptied), hip reload, third person, finishes sheet. In engine log: no TIKI / script error for these files.

## Not verified
Armory preview framing and inspect view (xfm of id 74 was fitted to the old bounds; the lanyard ring moves the bounding box about 1 unit down), dropped weapon (`weapdrop` did nothing in the harness), pickup in the world, AI holding it, dedicated server, other players' view of the bolt in the hip reload, prone / crouch / lean / braced ADS reloads, ADS-in-cover and mounted use, stronger ADS shimmer and Colt slide items (engine / other guns, not this lane), sounds, Trench C96 (unchanged), the stripper clip's own mesh (still the Kar98 prop), the old gun's `coop_port` / bolt-bar hacks (gone).
Traps hit: bug-4041 (overlay lacked the harness plumbing), bug-4042 (sheet far too dark), bug-4043 (shared harness copy locked).
